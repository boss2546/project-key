"""Context Pack service — MVP v2.

Generates high-level context from multiple files/collections.
Context packs are reusable AI-ready context blocks.
"""
import os
import json
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import ContextPack, File, Cluster, FileClusterMap, ChatQuery, ContextInjectionLog, PackShare, gen_id
from .llm import call_llm_json, call_llm_pro
from .config import CONTEXT_PACKS_DIR
from . import vector_search

logger = logging.getLogger(__name__)

PACK_TYPE_LABELS = {
    "profile": "โปรไฟล์",
    "study": "การเรียน",
    "work": "การทำงาน",
    "project": "โปรเจกต์"
}

PACK_TYPE_ICONS = {
    "profile": "👤",
    "study": "📚",
    "work": "💼",
    "project": "🎯"
}


async def list_packs(db: AsyncSession, user_id: str) -> list:
    """List all context packs for a user."""
    result = await db.execute(
        select(ContextPack)
        .where(ContextPack.user_id == user_id)
        .order_by(ContextPack.updated_at.desc())
    )
    packs = result.scalars().all()
    return [_serialize_pack(p) for p in packs]


async def get_pack(db: AsyncSession, pack_id: str, user_id: str) -> dict | None:
    """Get a single context pack."""
    result = await db.execute(
        select(ContextPack).where(
            ContextPack.id == pack_id,
            ContextPack.user_id == user_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        return None
    return _serialize_pack(pack)


async def create_pack(
    db: AsyncSession,
    user_id: str,
    pack_type: str,
    title: str,
    source_file_ids: list[str],
    source_cluster_ids: list[str],
    intent: str = "",
    scope: str = "",
    created_via: str = "manual",
    override_summary: str | None = None,
) -> dict:
    """Create a new context pack by distilling source content with LLM.

    v9.2.0 — เพิ่ม intent/scope/created_via params + override_summary
    - intent: "ใช้ทำอะไร" (default "" สำหรับ manual flow ที่ไม่กรอก)
    - scope: "ครอบคลุมอะไร" (default "")
    - created_via: "manual" | "ai_builder" — track ที่มา
    - override_summary: ถ้า caller ส่งมา → ใช้แทน LLM distill (สำหรับ AI Pack Builder
      ที่ confirm draft user แก้ summary แล้ว ไม่ต้องเรียก LLM ซ้ำ)
    """

    # Gather source content
    source_texts = []

    if source_file_ids:
        files_result = await db.execute(
            select(File).where(
                File.id.in_(source_file_ids),
                File.user_id == user_id
            ).options(selectinload(File.summary))
        )
        files = files_result.scalars().all()
        for f in files:
            text = ""
            if f.summary and f.summary.summary_text:
                text = f.summary.summary_text
            elif f.extracted_text:
                text = f.extracted_text[:3000]
            if text:
                source_texts.append(f"[{f.filename}]:\n{text}")

    if source_cluster_ids:
        clusters_result = await db.execute(
            select(Cluster).where(
                Cluster.id.in_(source_cluster_ids),
                Cluster.user_id == user_id
            )
        )
        clusters = clusters_result.scalars().all()
        for c in clusters:
            if c.summary:
                source_texts.append(f"[Collection: {c.title}]:\n{c.summary}")

    if not source_texts:
        raise ValueError("No source content found for the selected files/collections")

    # v9.2.0 — ถ้า caller ส่ง override_summary มา (เช่น AI Pack Builder confirm
    # หลัง user แก้ summary) → ไม่ distill ใหม่ ประหยัด LLM 1 ครั้ง
    if override_summary is not None:
        summary_text = override_summary
    else:
        combined_source = "\n\n---\n\n".join(source_texts)
        summary_text = await _generate_pack_content(
            pack_type, title, combined_source, intent=intent, scope=scope,
        )

    # v9.2.0 — frontmatter เก็บ intent + scope ด้วย เพื่อให้ .md export มีบริบทครบ
    fm_lines = [f"type: {pack_type}", f"title: {title}"]
    if intent:
        fm_lines.append(f"intent: {intent}")
    if scope:
        fm_lines.append(f"scope: {scope}")
    fm_lines.append(f"created_via: {created_via}")
    frontmatter = "\n".join(fm_lines)

    # Write .md file
    md_filename = f"{pack_type}-context-{gen_id()}.md"
    md_path = os.path.join(CONTEXT_PACKS_DIR, md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"---\n{frontmatter}\n---\n\n{summary_text}")

    # Save to DB
    pack = ContextPack(
        id=gen_id(),
        user_id=user_id,
        type=pack_type,
        title=title,
        summary_text=summary_text,
        md_path=md_path,
        source_file_ids=json.dumps(source_file_ids),
        source_cluster_ids=json.dumps(source_cluster_ids),
        intent=intent,           # v9.2.0
        scope=scope,             # v9.2.0
        created_via=created_via, # v9.2.0 ("manual" หรือ "ai_builder")
    )
    db.add(pack)
    await db.commit()

    # Index in vector search
    vector_search.index_file(
        file_id=f"pack-{pack.id}",
        filename=f"context-pack:{title}",
        text=summary_text,
        cluster_title=f"context-pack-{pack_type}",
        user_id=user_id,  # v5.1 — per-user index
    )

    logger.info(f"Created context pack '{title}' (type={pack_type}) for user {user_id}")
    return _serialize_pack(pack)


async def delete_pack(db: AsyncSession, pack_id: str, user_id: str) -> bool:
    """Delete a context pack."""
    result = await db.execute(
        select(ContextPack).where(
            ContextPack.id == pack_id,
            ContextPack.user_id == user_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        return False

    # Delete .md file
    if pack.md_path and os.path.exists(pack.md_path):
        os.remove(pack.md_path)

    # v10.0.8 — strip pack_id ออกจาก ContextInjectionLog.context_pack_ids (JSON array)
    # เดิมเหลือ stale id ใน log → audit ดูแล้วงงว่า pack อะไร
    from sqlalchemy import delete as sql_delete
    log_res = await db.execute(
        select(ContextInjectionLog).join(
            ChatQuery, ChatQuery.id == ContextInjectionLog.chat_query_id
        ).where(
            ChatQuery.user_id == user_id,
            ContextInjectionLog.context_pack_ids.like(f"%{pack_id}%"),
        )
    )
    for log in log_res.scalars().all():
        try:
            ids = json.loads(log.context_pack_ids or "[]")
            if pack_id in ids:
                log.context_pack_ids = json.dumps([i for i in ids if i != pack_id])
        except (ValueError, TypeError):
            pass

    # v10.0.8 — ลบ PackShare rows ที่ point ไปยัง pack นี้ (FK ไม่มี ondelete=CASCADE)
    await db.execute(sql_delete(PackShare).where(PackShare.pack_id == pack_id))

    await db.delete(pack)
    await db.commit()

    # v9.0.1 — Bug fix: ลบ pack ออกจาก TF-IDF index ด้วย กัน ghost results ใน
    # chat/MCP search หลัง delete (เดิมใช้ index_file ตอน create แต่ไม่มี cleanup
    # ตอน delete → search ยัง hit pack ที่ลบไปแล้วจน restart server)
    # remove_file ปลอดภัย no-op ถ้า pack-id ไม่อยู่ใน index (เช่นหลัง restart ก่อน rebuild)
    vector_search.remove_file(f"pack-{pack_id}", user_id=user_id)

    return True


async def regenerate_pack(db: AsyncSession, pack_id: str, user_id: str) -> dict | None:
    """Regenerate a context pack from its original sources."""
    result = await db.execute(
        select(ContextPack).where(
            ContextPack.id == pack_id,
            ContextPack.user_id == user_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        return None

    source_file_ids = json.loads(pack.source_file_ids) if pack.source_file_ids else []
    source_cluster_ids = json.loads(pack.source_cluster_ids) if pack.source_cluster_ids else []

    # Gather source content again
    source_texts = []
    if source_file_ids:
        files_result = await db.execute(
            select(File).where(
                File.id.in_(source_file_ids),
                File.user_id == user_id
            ).options(selectinload(File.summary))
        )
        for f in files_result.scalars().all():
            text = f.summary.summary_text if f.summary else (f.extracted_text[:3000] if f.extracted_text else "")
            if text:
                source_texts.append(f"[{f.filename}]:\n{text}")

    if source_cluster_ids:
        clusters_result = await db.execute(
            select(Cluster).where(Cluster.id.in_(source_cluster_ids))
        )
        for c in clusters_result.scalars().all():
            if c.summary:
                source_texts.append(f"[Collection: {c.title}]:\n{c.summary}")

    if not source_texts:
        return _serialize_pack(pack)

    combined_source = "\n\n---\n\n".join(source_texts)
    new_summary = await _generate_pack_content(pack.type, pack.title, combined_source)

    pack.summary_text = new_summary
    pack.updated_at = datetime.utcnow()

    # Update .md file
    if pack.md_path:
        with open(pack.md_path, 'w', encoding='utf-8') as f:
            f.write(f"---\ntype: {pack.type}\ntitle: {pack.title}\n---\n\n{new_summary}")

    await db.commit()

    # v9.0.1 — Bug fix: re-index TF-IDF เพื่อให้ chat/MCP search เห็น summary ใหม่
    # (เดิม regenerate อัปเดตแค่ DB row + .md file → search ยังคืน summary เก่า
    # จน user upload/regenerate ไฟล์อื่นแล้ว IDF ถูก rebuild ทั้งหมด)
    # index_file overwrites by file_id key — idempotent ปลอดภัย
    vector_search.index_file(
        file_id=f"pack-{pack.id}",
        filename=f"context-pack:{pack.title}",
        text=new_summary,
        cluster_title=f"context-pack-{pack.type}",
        user_id=user_id,
    )

    return _serialize_pack(pack)


async def _generate_pack_content(
    pack_type: str,
    title: str,
    source_content: str,
    intent: str = "",
    scope: str = "",
) -> str:
    """Use LLM to generate distilled context pack content.

    v9.2.0 — รับ intent + scope hint เพื่อให้ AI distill เน้นทิศทางที่ถูก
    (ถ้า manual flow ที่ไม่กรอก → empty strings → behave เหมือน v9.0.x เดิม)
    """

    type_label = PACK_TYPE_LABELS.get(pack_type, pack_type)

    # v9.2.0 — ใส่ INTENT + SCOPE ใน system prompt ถ้ามีค่า (AI builder flow)
    intent_block = ""
    if intent or scope:
        intent_block = "\n\nADDITIONAL CONTEXT (use to focus the distillation):"
        if intent:
            intent_block += f"\n- INTENT (ใช้สำหรับ): {intent}"
        if scope:
            intent_block += f"\n- SCOPE (ครอบคลุม): {scope}"

    system_prompt = f"""You are a context distillation AI. Your job is to create a high-level, reusable context document from multiple source documents.

This is a "{type_label}" context pack titled "{title}".{intent_block}

Rules:
- Write ALL output in THAI language
- Distill key themes, patterns, and important information from ALL sources
- Focus on information that would be useful as persistent context for AI conversations
- Structure the output clearly with sections
- Be comprehensive but concise — this is a "ready-to-use context" not a raw dump
- Include specific facts, names, dates, decisions when relevant
- The output should help an AI understand the user's {type_label} context quickly
- If INTENT/SCOPE are provided, prioritize content that matches them"""

    user_prompt = f"Distill the following source documents into a cohesive {type_label} context:\n\n{source_content[:8000]}"

    return await call_llm_pro(system_prompt, user_prompt, temperature=0.3, max_tokens=8192)


def get_pack_context_text(packs: list[dict]) -> str:
    """Convert relevant packs to a text block for AI context injection."""
    if not packs:
        return ""

    parts = []
    for pack in packs:
        icon = PACK_TYPE_ICONS.get(pack.get("type", ""), "📦")
        parts.append(
            f"=== CONTEXT PACK: {icon} {pack['title']} ({pack['type']}) ===\n"
            f"{pack.get('summary_text', '')}\n"
            f"=== END PACK ==="
        )

    return "\n\n".join(parts)


def _serialize_pack(pack: ContextPack) -> dict:
    """Serialize a ContextPack to dict."""
    return {
        "id": pack.id,
        "type": pack.type,
        "type_label": PACK_TYPE_LABELS.get(pack.type, pack.type),
        "type_icon": PACK_TYPE_ICONS.get(pack.type, "📦"),
        "title": pack.title,
        "summary_text": pack.summary_text or "",
        "source_file_ids": json.loads(pack.source_file_ids) if pack.source_file_ids else [],
        "source_cluster_ids": json.loads(pack.source_cluster_ids) if pack.source_cluster_ids else [],
        "source_count": len(json.loads(pack.source_file_ids or "[]")) + len(json.loads(pack.source_cluster_ids or "[]")),
        "created_at": pack.created_at.isoformat() if pack.created_at else "",
        "updated_at": pack.updated_at.isoformat() if pack.updated_at else "",
        # v9.0.1 — UI guard: client รู้ก่อนกด regenerate ว่า pack ล็อคอยู่ไหม
        # (เดิม API ไม่ expose → user กดแล้วเพิ่งเจอ 403 ทำให้สับสน)
        # locked_reason: null | "exceeds_free_plan_limit" | "subscription_expired"
        "is_locked": bool(getattr(pack, "is_locked", False)),
        "locked_reason": getattr(pack, "locked_reason", None),
        # v9.2.0 — บริบทของ pack + ที่มา (สำหรับ frontend แสดง badge / guidance)
        "intent": getattr(pack, "intent", "") or "",
        "scope": getattr(pack, "scope", "") or "",
        "created_via": getattr(pack, "created_via", "manual") or "manual",
    }
