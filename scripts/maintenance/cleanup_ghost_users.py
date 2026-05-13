"""Aggressive cleanup — ลบทุก user ที่ไม่มีหลักฐานการใช้งานจริง.

Criteria สำหรับ "real user" (ห้ามลบ):
1. is_admin = True  (founder + promoted admins)
2. file_count > 0  (เคย upload)
3. stripe_customer_id != NULL  (เคยติดต่อ Stripe — checkout/portal)
4. google_sub != NULL  (login ผ่าน Google จริง)
5. มี LINE link (line_users.line_user_id != NULL)
6. มี active MCP token

Everything else = ghost user → ลบทิ้ง

Run modes:
  python -m scripts.cleanup_ghost_users           # preview
  python -m scripts.cleanup_ghost_users --apply   # delete
"""
import asyncio
import os
import shutil
import sys
from datetime import datetime

from sqlalchemy import select, delete, func

from backend.database import (
    AsyncSessionLocal, User, File, FileSummary, FileInsight, FileClusterMap,
    Cluster, ContextPack, ContextMemory, LineUser, DriveConnection,
    MCPToken, MCPUsageLog, AuditLog, ChatQuery, ContextInjectionLog,
    UsageLog, GraphNode, GraphEdge, SuggestedRelation, NoteObject, GraphLens,
    CanvasObject, PersonalityHistory, UserProfile,
)
from backend.config import UPLOAD_DIR, DATA_DIR


PROTECTED_EMAILS = {"bossok2546@gmail.com"}

# Email patterns ที่เป็น test data — ลบทันทีไม่ว่ามี signal อะไร
import re
TEST_EMAIL_RE = re.compile(
    r"(@test\.local$|@test\.com$|@example\.com$|@example\.org$|"
    r"@(x|y|z)\.com$|@testserver$|@t\.local$|@smoke\.test$|"
    r"^test_|^smoke_|^e2e_|^fah_|^stress_|^ui_\d+|"
    r"^mcp_smoke|^final_|^router_|^redirect|^demo|^modal@|^paiduser@|"
    r"^freeuser@|^quotatest@|^flowtest|^usagetest|^detailtest@|"
    r"^plantest@|^billing@|^price99@|^t@test|^boss@key|^boss@test|"
    r"^test1?@gmil|^testuser@contextbank)",
    re.IGNORECASE,
)


def is_test_pattern(email: str | None) -> bool:
    if not email:
        return True  # NULL email = ghost
    e = email.lower().strip()
    if e in PROTECTED_EMAILS:
        return False
    return bool(TEST_EMAIL_RE.search(e))


async def classify_user(db, u: User) -> dict:
    """Return signals + verdict ('real' | 'ghost')."""
    file_count = (await db.execute(
        select(func.count(File.id)).where(File.user_id == u.id)
    )).scalar() or 0

    pack_count = (await db.execute(
        select(func.count(ContextPack.id)).where(ContextPack.user_id == u.id)
    )).scalar() or 0

    line_linked = (await db.execute(
        select(func.count(LineUser.id)).where(
            LineUser.pdb_user_id == u.id,
            LineUser.line_user_id.isnot(None),
        )
    )).scalar() or 0

    drive_connected = (await db.execute(
        select(func.count(DriveConnection.id)).where(DriveConnection.user_id == u.id)
    )).scalar() or 0

    active_token = (await db.execute(
        select(func.count(MCPToken.id)).where(
            MCPToken.user_id == u.id,
            MCPToken.is_active == True,  # noqa: E712
        )
    )).scalar() or 0

    test_pattern = is_test_pattern(u.email)
    signals = {
        "is_admin": bool(u.is_admin),
        "files": int(file_count),
        "packs": int(pack_count),
        "stripe": bool(u.stripe_customer_id),
        "google": bool(u.google_sub),
        "line": int(line_linked) > 0,
        "drive": int(drive_connected) > 0,
        "mcp_token": int(active_token) > 0,
        "email_protected": (u.email or "").lower() in PROTECTED_EMAILS,
        "test_pattern": test_pattern,
    }
    # Real = ไม่ใช่ test pattern AND มีอย่างใดอย่างหนึ่ง:
    #   admin, มี files, มี packs, มี Stripe, มี Google sub,
    #   มี LINE link, มี Drive (real), มี MCP token (real)
    # หรือเป็น protected email (founder)
    if signals["email_protected"]:
        is_real = True
    elif test_pattern:
        is_real = False  # ลบทันที ไม่ว่ามี signal อะไร
    else:
        is_real = (
            signals["is_admin"]
            or signals["files"] > 0
            or signals["packs"] > 0
            or signals["stripe"]
            or signals["google"]
            or signals["line"]
            or signals["drive"]
            or signals["mcp_token"]
        )
    return {"verdict": "real" if is_real else "ghost", "signals": signals}


async def scan_all() -> dict:
    """Categorize all users. Return {real:[], ghost:[]}."""
    async with AsyncSessionLocal() as db:
        all_users = (await db.execute(select(User))).scalars().all()
        real, ghost = [], []
        for u in all_users:
            info = await classify_user(db, u)
            entry = {"user": u, **info}
            if info["verdict"] == "real":
                real.append(entry)
            else:
                ghost.append(entry)
        return {"real": real, "ghost": ghost, "total": len(all_users)}


async def preview():
    data = await scan_all()
    print(f"=== Total users: {data['total']} ===")
    print(f"  Real users (keep): {len(data['real'])}")
    print(f"  Ghost users (delete): {len(data['ghost'])}")
    print()

    # Real users — show summary
    print("=== Real users (KEEP) — top signals ===")
    by_reason = {}
    for r in data["real"]:
        s = r["signals"]
        if s["is_admin"]: by_reason.setdefault("admin", []).append(r["user"].email)
        elif s["files"] > 0: by_reason.setdefault("has_files", []).append(f"{r['user'].email} ({s['files']}f)")
        elif s["stripe"]: by_reason.setdefault("stripe", []).append(r["user"].email)
        elif s["google"]: by_reason.setdefault("google", []).append(r["user"].email)
        elif s["line"]: by_reason.setdefault("line", []).append(r["user"].email)
        elif s["packs"] > 0: by_reason.setdefault("has_packs", []).append(r["user"].email)
        elif s["mcp_token"]: by_reason.setdefault("mcp_token", []).append(r["user"].email)
        elif s["drive"]: by_reason.setdefault("drive", []).append(r["user"].email)
        else: by_reason.setdefault("protected", []).append(r["user"].email)
    for reason, emails in by_reason.items():
        print(f"  [{reason}] {len(emails)} users")
        for e in emails[:5]:
            print(f"    • {e}")
        if len(emails) > 5:
            print(f"    ... ({len(emails) - 5} more)")
    print()

    # Ghost users — sample
    print(f"=== Ghost users (DELETE — {len(data['ghost'])}) sample top 20 ===")
    for g in data["ghost"][:20]:
        u = g["user"]
        created = u.created_at.strftime("%Y-%m-%d") if u.created_at else "?"
        print(f"  • {u.email or '(no email)':50s}  created={created}")
    if len(data["ghost"]) > 20:
        print(f"  ... ({len(data['ghost']) - 20} more)")
    print()
    print("Run with --apply to delete all ghost users.")


async def delete_user_cascade(db, user: User) -> None:
    """ลบ user + cascade related data."""
    uid = user.id

    # Files + raw_path on disk
    files = (await db.execute(select(File).where(File.user_id == uid))).scalars().all()
    for f in files:
        if f.raw_path and os.path.exists(f.raw_path):
            try: os.remove(f.raw_path)
            except OSError: pass
    file_ids = [f.id for f in files]
    if file_ids:
        await db.execute(delete(FileSummary).where(FileSummary.file_id.in_(file_ids)))
        await db.execute(delete(FileInsight).where(FileInsight.file_id.in_(file_ids)))
        await db.execute(delete(FileClusterMap).where(FileClusterMap.file_id.in_(file_ids)))
    await db.execute(delete(File).where(File.user_id == uid))

    # Packs
    packs = (await db.execute(select(ContextPack).where(ContextPack.user_id == uid))).scalars().all()
    for p in packs:
        if p.md_path and os.path.exists(p.md_path):
            try: os.remove(p.md_path)
            except OSError: pass
    await db.execute(delete(ContextPack).where(ContextPack.user_id == uid))

    # Other
    await db.execute(delete(ContextMemory).where(ContextMemory.user_id == uid))
    await db.execute(delete(LineUser).where(LineUser.pdb_user_id == uid))
    await db.execute(delete(DriveConnection).where(DriveConnection.user_id == uid))
    await db.execute(delete(MCPUsageLog).where(MCPUsageLog.user_id == uid))
    await db.execute(delete(MCPToken).where(MCPToken.user_id == uid))
    await db.execute(delete(AuditLog).where(AuditLog.user_id == uid))
    await db.execute(delete(UsageLog).where(UsageLog.user_id == uid))

    chat_q = (await db.execute(select(ChatQuery).where(ChatQuery.user_id == uid))).scalars().all()
    chat_ids = [c.id for c in chat_q]
    if chat_ids:
        await db.execute(delete(ContextInjectionLog).where(
            ContextInjectionLog.chat_query_id.in_(chat_ids)
        ))
    await db.execute(delete(ChatQuery).where(ChatQuery.user_id == uid))

    await db.execute(delete(SuggestedRelation).where(SuggestedRelation.user_id == uid))
    await db.execute(delete(GraphEdge).where(GraphEdge.user_id == uid))
    await db.execute(delete(GraphNode).where(GraphNode.user_id == uid))
    await db.execute(delete(NoteObject).where(NoteObject.user_id == uid))
    await db.execute(delete(GraphLens).where(GraphLens.user_id == uid))
    await db.execute(delete(CanvasObject).where(CanvasObject.user_id == uid))
    await db.execute(delete(PersonalityHistory).where(PersonalityHistory.user_id == uid))
    await db.execute(delete(UserProfile).where(UserProfile.user_id == uid))
    await db.execute(delete(Cluster).where(Cluster.user_id == uid))

    # User upload dir
    user_dir = os.path.join(UPLOAD_DIR, uid)
    if os.path.isdir(user_dir):
        try: shutil.rmtree(user_dir)
        except OSError: pass

    # Finally — User
    await db.execute(delete(User).where(User.id == uid))


async def apply():
    data = await scan_all()
    ghosts = data["ghost"]
    if not ghosts:
        print("No ghost users to delete.")
        return

    # Backup
    db_path = os.path.join(DATA_DIR, "projectkey.db")
    backup_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(
        backup_dir, f"projectkey_pre_ghost_cleanup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    )
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"✅ DB backup: {backup_path}")
    print()

    print(f"=== Deleting {len(ghosts)} ghost users ===")
    print(f"(Real users kept: {len(data['real'])})")
    print()

    async with AsyncSessionLocal() as db:
        for i, g in enumerate(ghosts, 1):
            u = g["user"]
            await delete_user_cascade(db, u)
            if i % 100 == 0:
                await db.commit()  # commit periodically — กัน transaction ใหญ่เกิน
                print(f"  ... {i}/{len(ghosts)} done")
        await db.commit()
    print()
    print(f"=== DONE — deleted {len(ghosts)} ghost users ===")
    print(f"Real users remaining: {len(data['real'])}")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        asyncio.run(apply())
    else:
        asyncio.run(preview())
