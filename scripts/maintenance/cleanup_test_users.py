"""Cleanup test users — pattern-match emails ที่ดูเหมือน test data.

Patterns ที่ลบ:
- email contains "test_"  (เช่น test_admin_check_9987@...)
- email ends in @example.com  (test convention)
- email ends in @x.com / @y.com / @z.com  (sandbox testing)
- email ends in @testserver

Patterns ที่ห้ามลบเด็ดขาด:
- bossok2546@gmail.com (founder)
- ทุก email ที่มี is_admin=1 (admin protection)

Run modes:
  python -m scripts.cleanup_test_users           # preview only
  python -m scripts.cleanup_test_users --apply   # actually delete

ลบ + cascade related data:
- files (+ raw_path on disk)
- file_summaries / file_insights / file_cluster_map
- context_packs (+ md files)
- context_memories
- line_users
- drive_connections
- mcp_tokens / mcp_usage_logs
- audit_logs
- chat_queries / context_injection_logs
- usage_logs
- graph_nodes / graph_edges / suggested_relations / note_objects / graph_lenses
- canvas_objects / personality_history
"""
import asyncio
import os
import re
import shutil
import sys
from datetime import datetime

from sqlalchemy import select, delete, or_

from backend.database import (
    AsyncSessionLocal, User, File, FileSummary, FileInsight, FileClusterMap,
    ContextPack, ContextMemory, LineUser, DriveConnection,
    MCPToken, MCPUsageLog, AuditLog, ChatQuery, ContextInjectionLog,
    UsageLog, GraphNode, GraphEdge, SuggestedRelation, NoteObject, GraphLens,
    CanvasObject, PersonalityHistory, UserProfile,
)
from backend.config import UPLOAD_DIR, CONTEXT_PACKS_DIR, SUMMARIES_DIR, DATA_DIR


# ─── Detection patterns ───
TEST_EMAIL_PATTERNS = [
    re.compile(r"^test_", re.IGNORECASE),
    re.compile(r"@example\.com$", re.IGNORECASE),
    re.compile(r"@(x|y|z)\.com$", re.IGNORECASE),
    re.compile(r"@testserver$", re.IGNORECASE),
    re.compile(r"@example\.org$", re.IGNORECASE),
]

PROTECTED_EMAILS = {"bossok2546@gmail.com"}


def is_test_email(email: str | None) -> bool:
    if not email:
        return False
    e = email.lower().strip()
    if e in PROTECTED_EMAILS:
        return False
    return any(p.search(e) for p in TEST_EMAIL_PATTERNS)


async def find_test_users() -> list[User]:
    """List users ที่ match test patterns (ไม่รวม admin + protected emails)."""
    async with AsyncSessionLocal() as db:
        all_users = (await db.execute(select(User))).scalars().all()
        candidates = [
            u for u in all_users
            if is_test_email(u.email) and not getattr(u, "is_admin", False)
        ]
        return candidates


async def delete_user_cascade(db, user: User) -> dict:
    """ลบ user + related data ทั้งหมด. Return stats ของสิ่งที่ลบ."""
    uid = user.id
    stats = {"files_db": 0, "files_disk": 0, "packs": 0, "contexts": 0,
             "tokens": 0, "audits": 0, "chats": 0, "graph_nodes": 0,
             "graph_edges": 0, "personality": 0, "other": 0}

    # 1. Files — ลบ raw_path บน disk ก่อน + DB rows (cascade FileSummary, FileInsight, FileClusterMap)
    files = (await db.execute(select(File).where(File.user_id == uid))).scalars().all()
    for f in files:
        if f.raw_path and os.path.exists(f.raw_path):
            try:
                os.remove(f.raw_path)
                stats["files_disk"] += 1
            except OSError as e:
                print(f"  ⚠️ failed to remove {f.raw_path}: {e}")
    stats["files_db"] = len(files)
    # File row ลบ → cascade FileInsight + FileSummary + FileClusterMap (FK on delete)
    # แต่ SQLAlchemy ไม่ define cascade — ลบ explicit
    file_ids = [f.id for f in files]
    if file_ids:
        await db.execute(delete(FileSummary).where(FileSummary.file_id.in_(file_ids)))
        await db.execute(delete(FileInsight).where(FileInsight.file_id.in_(file_ids)))
        await db.execute(delete(FileClusterMap).where(FileClusterMap.file_id.in_(file_ids)))
    await db.execute(delete(File).where(File.user_id == uid))

    # 2. Context Packs (+ md files on disk)
    packs = (await db.execute(select(ContextPack).where(ContextPack.user_id == uid))).scalars().all()
    for p in packs:
        if p.md_path and os.path.exists(p.md_path):
            try:
                os.remove(p.md_path)
            except OSError:
                pass
    stats["packs"] = len(packs)
    await db.execute(delete(ContextPack).where(ContextPack.user_id == uid))

    # 3. Context Memory
    cm_count = (await db.execute(
        select(ContextMemory).where(ContextMemory.user_id == uid)
    )).scalars().all()
    stats["contexts"] = len(cm_count)
    await db.execute(delete(ContextMemory).where(ContextMemory.user_id == uid))

    # 4. LINE / Drive
    await db.execute(delete(LineUser).where(LineUser.pdb_user_id == uid))
    await db.execute(delete(DriveConnection).where(DriveConnection.user_id == uid))

    # 5. MCP
    tok_count = (await db.execute(
        select(MCPToken).where(MCPToken.user_id == uid)
    )).scalars().all()
    stats["tokens"] = len(tok_count)
    await db.execute(delete(MCPUsageLog).where(MCPUsageLog.user_id == uid))
    await db.execute(delete(MCPToken).where(MCPToken.user_id == uid))

    # 6. Audit + usage
    audit_rows = (await db.execute(
        select(AuditLog).where(AuditLog.user_id == uid)
    )).scalars().all()
    stats["audits"] = len(audit_rows)
    await db.execute(delete(AuditLog).where(AuditLog.user_id == uid))
    await db.execute(delete(UsageLog).where(UsageLog.user_id == uid))

    # 7. Chat + context injection logs
    chat_q = (await db.execute(
        select(ChatQuery).where(ChatQuery.user_id == uid)
    )).scalars().all()
    stats["chats"] = len(chat_q)
    chat_ids = [c.id for c in chat_q]
    if chat_ids:
        await db.execute(delete(ContextInjectionLog).where(
            ContextInjectionLog.chat_query_id.in_(chat_ids)
        ))
    await db.execute(delete(ChatQuery).where(ChatQuery.user_id == uid))

    # 8. Graph
    nodes = (await db.execute(
        select(GraphNode).where(GraphNode.user_id == uid)
    )).scalars().all()
    stats["graph_nodes"] = len(nodes)
    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.user_id == uid)
    )).scalars().all()
    stats["graph_edges"] = len(edges)
    await db.execute(delete(SuggestedRelation).where(SuggestedRelation.user_id == uid))
    await db.execute(delete(GraphEdge).where(GraphEdge.user_id == uid))
    await db.execute(delete(GraphNode).where(GraphNode.user_id == uid))
    await db.execute(delete(NoteObject).where(NoteObject.user_id == uid))
    await db.execute(delete(GraphLens).where(GraphLens.user_id == uid))

    # 9. Other
    await db.execute(delete(CanvasObject).where(CanvasObject.user_id == uid))
    pers_count = (await db.execute(
        select(PersonalityHistory).where(PersonalityHistory.user_id == uid)
    )).scalars().all()
    stats["personality"] = len(pers_count)
    await db.execute(delete(PersonalityHistory).where(PersonalityHistory.user_id == uid))
    await db.execute(delete(UserProfile).where(UserProfile.user_id == uid))

    # 10. Clusters (NB: clusters มี user_id แต่ไม่ direct relation — ลบโดย user_id)
    from backend.database import Cluster
    await db.execute(delete(Cluster).where(Cluster.user_id == uid))

    # 11. User upload dir
    user_dir = os.path.join(UPLOAD_DIR, uid)
    if os.path.isdir(user_dir):
        try:
            shutil.rmtree(user_dir)
        except OSError as e:
            print(f"  ⚠️ failed to remove dir {user_dir}: {e}")

    # 12. Finally — User row
    await db.execute(delete(User).where(User.id == uid))

    return stats


async def preview():
    candidates = await find_test_users()
    print(f"=== Test User Preview (matched {len(candidates)} users) ===")
    print()
    for u in candidates:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import func
            f_count = (await db.execute(
                select(func.count(File.id)).where(File.user_id == u.id)
            )).scalar() or 0
        created = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—"
        flags = []
        if u.is_admin: flags.append("ADMIN")
        if not u.is_active: flags.append("inactive")
        if u.stripe_subscription_id: flags.append("stripe-sub")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        print(f"  {u.email:50s}  {created}  files={f_count:3d}{flag_str}")
    print()
    print(f"Total: {len(candidates)} users")
    print()
    print("Run with --apply to delete.")


async def apply():
    candidates = await find_test_users()
    if not candidates:
        print("No test users to delete.")
        return

    # Backup first
    db_path = os.path.join(DATA_DIR, "projectkey.db")
    backup_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(
        backup_dir, f"projectkey_pre_cleanup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    )
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"✅ DB backup: {backup_path}")
    print()

    print(f"=== Deleting {len(candidates)} test users ===")
    print()
    total_stats = {}
    async with AsyncSessionLocal() as db:
        for u in candidates:
            print(f"  • {u.email} ({u.id})")
            stats = await delete_user_cascade(db, u)
            for k, v in stats.items():
                total_stats[k] = total_stats.get(k, 0) + v
        await db.commit()
    print()
    print(f"=== DONE — {len(candidates)} users deleted ===")
    print(f"Files: {total_stats.get('files_db', 0)} DB rows, {total_stats.get('files_disk', 0)} disk")
    print(f"Packs: {total_stats.get('packs', 0)}, Contexts: {total_stats.get('contexts', 0)}, Tokens: {total_stats.get('tokens', 0)}")
    print(f"Audits: {total_stats.get('audits', 0)}, Chats: {total_stats.get('chats', 0)}, Personality: {total_stats.get('personality', 0)}")
    print(f"Graph: {total_stats.get('graph_nodes', 0)} nodes / {total_stats.get('graph_edges', 0)} edges")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        asyncio.run(apply())
    else:
        asyncio.run(preview())
