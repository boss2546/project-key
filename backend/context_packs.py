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

from .database import ContextPack, File, Cluster, FileClusterMap, gen_id
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
    source_cluster_ids: list[str]
) -> dict:
    """Create a new context pack by distilling source content with LLM."""

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

    # Generate distilled context via LLM
    combined_source = "\n\n---\n\n".join(source_texts)
    summary_text = await _generate_pack_content(pack_type, title, combined_source)

    # Write .md file
    md_filename = f"{pack_type}-context-{gen_id()}.md"
    md_path = os.path.join(CONTEXT_PACKS_DIR, md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"---\ntype: {pack_type}\ntitle: {title}\n---\n\n{summary_text}")

    # Save to DB
    pack = ContextPack(
        id=gen_id(),
        user_id=user_id,
        type=pack_type,
        title=title,
        summary_text=summary_text,
        md_path=md_path,
        source_file_ids=json.dumps(source_file_ids),
        source_cluster_ids=json.dumps(source_cluster_ids)
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

    await db.delete(pack)
    await db.commit()
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
    return _serialize_pack(pack)


async def _generate_pack_content(pack_type: str, title: str, source_content: str) -> str:
    """Use LLM to generate distilled context pack content."""

    type_label = PACK_TYPE_LABELS.get(pack_type, pack_type)

    system_prompt = f"""You are a context distillation AI. Your job is to create a high-level, reusable context document from multiple source documents.

This is a "{type_label}" context pack titled "{title}".

Rules:
- Write ALL output in THAI language
- Distill key themes, patterns, and important information from ALL sources
- Focus on information that would be useful as persistent context for AI conversations
- Structure the output clearly with sections
- Be comprehensive but concise — this is a "ready-to-use context" not a raw dump
- Include specific facts, names, dates, decisions when relevant
- The output should help an AI understand the user's {type_label} context quickly"""

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
        "updated_at": pack.updated_at.isoformat() if pack.updated_at else ""
    }
