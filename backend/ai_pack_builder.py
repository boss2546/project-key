"""AI Pack Builder — v9.2.0

ระบบให้ AI ช่วยสร้าง Context Pack จาก natural-language prompt:

Flow:
  1. /clarify — AI ตัดสินใจว่า prompt ละเอียดพอไหม
       - ถ้าครบ ≥2/3 (SOURCE/SCOPE/FOCUS) → skip_clarify=true → frontend ข้ามไป /propose ทันที
       - ถ้าไม่ครบ → gen 4 quality options + freetext + skip ให้ user เลือก
  2. /propose — AI build draft (select sources + draft metadata + distill summary)
       2-step internal LLM:
         (i)  call_llm_json — select sources + suggest title/type/intent/scope
         (ii) call_llm_pro  — distill summary จาก source content
  3. /confirm — บันทึก pack จริง (เรียก create_pack ของ context_packs.py แต่ส่ง
                override_summary เพื่อไม่ distill ซ้ำ) + log_usage("ai_summary")
  4. /discard — ยกเลิก draft (cleanup cache)

Caches (in-memory, ไม่ persist — หาย restart, lazy GC):
  _SESSION_CACHE — ผลของ /clarify (inventory snapshot + options)
  _DRAFT_CACHE   — ผลของ /propose (draft pack ที่รอ user confirm)

Vault filter (v9.1.0 dependency):
  ทั้ง _build_inventory_for_clarify + _build_inventory_for_propose
  ใช้ File.file_kind == "processed" — ไม่รวม vault file (extracted_text ว่าง
  → AI distill ออกมาห่วย)
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import File, Cluster, ContextPack
from .llm import call_llm_json
from .context_packs import create_pack, _generate_pack_content
from .plan_limits import (
    check_pack_create_allowed, check_summary_allowed, log_usage,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Caches + TTL
# ═══════════════════════════════════════════

_TTL_SECONDS = 1800   # 30 นาที — ทั้ง session + draft

# session_id -> {user_id, prompt, user_lang, inventory_snapshot, options, skip_clarify, created_at}
_SESSION_CACHE: dict[str, dict[str, Any]] = {}

# draft_id -> {user_id, payload, created_at}
_DRAFT_CACHE: dict[str, dict[str, Any]] = {}


def _gc_expired() -> None:
    """Lazy GC ทั้ง 2 caches — เรียกทุกครั้งที่ /clarify หรือ /propose ใหม่"""
    now = datetime.utcnow()
    for cache in (_SESSION_CACHE, _DRAFT_CACHE):
        expired = [
            k for k, v in cache.items()
            if (now - v["created_at"]).total_seconds() > _TTL_SECONDS
        ]
        for k in expired:
            del cache[k]


def _gen_session_id() -> str:
    """ID prefix 'ses_' — distinguish จาก draft_id ที่ขึ้น 'drf_'"""
    return f"ses_{secrets.token_urlsafe(9)}"


def _gen_draft_id() -> str:
    return f"drf_{secrets.token_urlsafe(9)}"


# ═══════════════════════════════════════════
# Inventory builders (vault-filtered)
# ═══════════════════════════════════════════

async def _build_inventory_for_clarify(
    db: AsyncSession, user_id: str, max_files: int = 30
) -> tuple[str, list[dict]]:
    """Inventory format สำหรับ /clarify — เน้น compact (file names + cluster names + counts)
    เพื่อให้ AI quote ใน option summary ได้.

    Returns (formatted_string, snapshot_list) — snapshot ใช้เก็บใน session cache
    """
    # ⚠️ v9.1.0 vault filter — ห้าม include vault files (extracted_text ว่าง)
    from sqlalchemy.orm import selectinload
    files_q = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.processing_status == "ready",
            File.file_kind == "processed",
        ).options(selectinload(File.cluster_maps))   # eager-load กัน async lazy-load
        .order_by(desc(File.uploaded_at)).limit(max_files)
    )
    files = files_q.scalars().all()

    clusters_q = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id)
    )
    clusters = clusters_q.scalars().all()
    cluster_count_map: dict[str, int] = {}
    # นับจำนวนไฟล์ต่อ cluster ผ่าน file_cluster_map (ถ้ามี relation)
    for f in files:
        for cm in getattr(f, "cluster_maps", []) or []:
            cluster_count_map[cm.cluster_id] = cluster_count_map.get(cm.cluster_id, 0) + 1

    # Snapshot สำหรับ session (เก็บ id + name เท่านั้น — กัน memory blowup)
    snapshot = {
        "files": [
            {"id": f.id, "filename": f.filename, "filetype": f.filetype}
            for f in files
        ],
        "clusters": [
            {"id": c.id, "title": c.title, "file_count": cluster_count_map.get(c.id, 0)}
            for c in clusters
        ],
    }

    # Format text สำหรับ LLM
    parts = [f"=== FILES (newest {len(files)}, file_kind='processed' only) ==="]
    for f in files:
        cluster_titles = []
        for cm in getattr(f, "cluster_maps", []) or []:
            c_obj = next((c for c in clusters if c.id == cm.cluster_id), None)
            if c_obj:
                cluster_titles.append(c_obj.title)
        cluster_str = ", ".join(cluster_titles) if cluster_titles else "—"
        text_len = len(f.extracted_text or "")
        parts.append(f"- {f.filename} (cluster: {cluster_str}, {text_len:,} chars)")

    parts.append("\n=== CLUSTERS ===")
    for c in clusters:
        parts.append(f"- {c.title} ({cluster_count_map.get(c.id, 0)} files)")

    return "\n".join(parts), snapshot


async def _build_inventory_for_propose(
    db: AsyncSession, user_id: str, max_files: int = 50
) -> str:
    """Inventory สำหรับ /propose — เพิ่ม summary preview เพื่อให้ AI เลือก source ได้แม่น
    ใช้ pattern เดียวกับ retriever._build_inventory แต่ filter vault.
    """
    from sqlalchemy.orm import selectinload

    files_q = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.processing_status == "ready",
            File.file_kind == "processed",  # vault filter
        ).options(selectinload(File.summary), selectinload(File.cluster_maps))
        .order_by(desc(File.uploaded_at)).limit(max_files)
    )
    files = files_q.scalars().all()

    clusters_q = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id)
    )
    clusters = clusters_q.scalars().all()
    cluster_map = {c.id: c for c in clusters}

    parts = ["=== AVAILABLE FILES (file_kind='processed' only) ==="]
    for f in files:
        cluster_titles = []
        cluster_ids_str = []
        for cm in f.cluster_maps:
            c = cluster_map.get(cm.cluster_id)
            if c:
                cluster_titles.append(c.title)
                cluster_ids_str.append(c.id)
        summary_preview = (f.summary.summary_text[:200] if f.summary else "")
        parts.append(
            f"FILE_ID: {f.id}\n"
            f"FILENAME: {f.filename}\n"
            f"CLUSTERS: {', '.join(cluster_titles) or '—'} (IDs: {', '.join(cluster_ids_str)})\n"
            f"SUMMARY_PREVIEW: {summary_preview}\n"
            f"TEXT_LENGTH: {len(f.extracted_text or ''):,} chars\n"
            f"---"
        )

    parts.append("\n=== AVAILABLE CLUSTERS ===")
    for c in clusters:
        parts.append(
            f"CLUSTER_ID: {c.id}\n"
            f"TITLE: {c.title}\n"
            f"SUMMARY: {(c.summary or '')[:200]}\n"
            f"---"
        )

    return "\n".join(parts)


# ═══════════════════════════════════════════
# /clarify — Step 0
# ═══════════════════════════════════════════

CLARIFY_SYSTEM_PROMPT = """You are an AI Pack Builder assistant. Given a user's prompt and their data inventory, you must:

(A) DECIDE if the prompt is detailed enough to skip clarification
(B) IF NOT, generate ONE clarifying question with 4 high-quality options

DECISION CRITERIA — set "skip_clarify": true if user prompt has >= 2 of 3:
  1. SOURCE specified (file/cluster names or specific count + topic that matches inventory)
  2. SCOPE specified (include/exclude clearly stated)
  3. FOCUS specified (specific lens — exam prep / formulas / summary / etc.)

Otherwise set "skip_clarify": false and generate options.

QUALITY RULES for options (when skip_clarify=false):
  - CONCRETE: quote real file names or cluster names FROM THE INVENTORY (not generic placeholders)
  - ACTIONABLE: user must understand exactly what pack they get if they pick this option
  - DIFFERENTIATED: each option's scope must be clearly distinct
  - SCOPED: state both include AND exclude when relevant
  - LENGTH: each "summary" field must be 25-60 words (not a short label)

Respond ONLY with valid JSON (no markdown fences):

CASE A (skip_clarify=false):
{
  "skip_clarify": false,
  "question": "<one-sentence question in user_lang>",
  "options": [
    {"id": 1, "title": "<3-6 words>", "summary": "<25-60 words concrete description quoting real inventory items>"},
    {"id": 2, "title": "<...>", "summary": "<...>"},
    {"id": 3, "title": "<...>", "summary": "<...>"},
    {"id": 4, "title": "<...>", "summary": "<...>"}
  ],
  "freetext_hint": "<example wording user can type>",
  "reasoning": "<brief why this question>"
}

CASE B (skip_clarify=true):
{
  "skip_clarify": true,
  "reasoning": "<why prompt is detailed enough — list which of SOURCE/SCOPE/FOCUS are present>"
}

Hard rules:
- options array must have exactly 4 entries (CASE A only)
- All natural-language fields must be in the user's language (TH if user_lang='th', else EN)
- Never invent file names that aren't in the inventory
"""


async def clarify_prompt(
    db: AsyncSession, user_id: str, user_prompt: str, user_lang: str = "th"
) -> dict:
    """Step 0: AI ตัดสินใจว่าต้องถาม clarify ไหม + (ถ้าใช่) gen 4 options คุณภาพ"""
    _gc_expired()

    # Pre-check inventory ว่ามีอะไรให้ทำงานไหม
    files_count_q = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.processing_status == "ready",
            File.file_kind == "processed",
        ).limit(1)
    )
    has_files = files_count_q.scalar_one_or_none() is not None
    clusters_count_q = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id).limit(1)
    )
    has_clusters = clusters_count_q.scalar_one_or_none() is not None
    if not has_files and not has_clusters:
        raise ValueError("NO_SOURCES_AVAILABLE")

    inventory_text, snapshot = await _build_inventory_for_clarify(db, user_id)

    user_message = (
        f"USER PROMPT: {user_prompt}\n"
        f"USER LANGUAGE: {user_lang}\n\n"
        f"USER'S INVENTORY:\n{inventory_text}"
    )

    # Retry once on JSON parse failure
    response = None
    last_err = None
    for attempt in range(2):
        try:
            response = await call_llm_json(CLARIFY_SYSTEM_PROMPT, user_message, temperature=0.3)
            break
        except Exception as e:
            last_err = e
            logger.warning(f"clarify_prompt LLM attempt {attempt+1} failed: {e}")
    if response is None:
        raise RuntimeError(f"LLM_RESPONSE_INVALID: {last_err}")

    skip_clarify = bool(response.get("skip_clarify", False))
    session_id = _gen_session_id()

    # เก็บ session ทั้ง 2 case (skip_clarify=true ก็ใช้ session_id ใน /propose)
    _SESSION_CACHE[session_id] = {
        "user_id": user_id,
        "prompt": user_prompt,
        "user_lang": user_lang,
        "inventory_snapshot": snapshot,
        "skip_clarify": skip_clarify,
        "options": response.get("options", []) if not skip_clarify else [],
        "created_at": datetime.utcnow(),
    }
    expires_at = (
        datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    )  # informational

    if skip_clarify:
        return {
            "session_id": session_id,
            "skip_clarify": True,
            "reasoning": response.get("reasoning", ""),
            "expires_at": expires_at,
            "ai_calls_used": 1,
        }

    # Validate options shape (LLM อาจส่ง < 4 บางที)
    options = response.get("options", [])
    if not isinstance(options, list) or len(options) != 4:
        raise RuntimeError(f"LLM_RESPONSE_INVALID: expected 4 options, got {len(options) if isinstance(options, list) else 'non-list'}")

    return {
        "session_id": session_id,
        "skip_clarify": False,
        "question": response.get("question", ""),
        "options": options,
        "allow_freetext": True,
        "freetext_hint": response.get("freetext_hint", ""),
        "allow_skip": True,
        "expires_at": expires_at,
        "ai_calls_used": 1,
    }


# ═══════════════════════════════════════════
# /propose — Step 1+2
# ═══════════════════════════════════════════

PROPOSE_SYSTEM_PROMPT = """You are an AI Pack Builder. Select the most relevant source items (files + clusters) from the user's inventory and draft pack metadata.

Respond ONLY with valid JSON:
{
  "selected_files": ["file_id_1", ...],     // 0-10 items, file IDs only
  "selected_clusters": ["cluster_id_1", ...], // 0-5 items, cluster IDs only
  "suggested_title": "<3-8 words pack title>",
  "suggested_type": "profile|study|work|project",
  "suggested_intent": "<1-2 sentences: what this pack is for>",
  "suggested_scope": "<1-2 sentences: what's included AND excluded>",
  "reasoning": "<brief why this selection>"
}

Rules:
- Total selected items >= 1, <= 12
- All IDs MUST come from the inventory provided
- All natural-language fields in the user's language
- suggested_type: pick best fit, do not default to "project"
- If user clarification was provided, prioritize sources that match it
"""


async def propose_pack(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    clarification: dict,
    preferred_type: str | None = None,
    user_lang: str = "th",
) -> dict:
    """Step 1+2: AI build draft proposal.

    clarification ต้องมี exactly 1 ใน 3 keys:
      - selected_option_id: int (1-4)
      - freetext: str
      - skipped: True
    """
    _gc_expired()

    # Validate session
    session = _SESSION_CACHE.get(session_id)
    if not session:
        raise ValueError("SESSION_NOT_FOUND")
    if session["user_id"] != user_id:
        # กัน user A steal session ของ user B
        raise ValueError("SESSION_NOT_FOUND")

    # Validate clarification (ต้องมี exactly 1 field)
    keys_present = [
        k for k in ("selected_option_id", "freetext", "skipped")
        if clarification.get(k) not in (None, "", False)
    ]
    if len(keys_present) != 1:
        raise ValueError(f"INVALID_CLARIFICATION: expected exactly 1 of selected_option_id/freetext/skipped, got {keys_present}")

    # Build clarification text สำหรับ prompt
    if "selected_option_id" in keys_present:
        opt_id = clarification["selected_option_id"]
        chosen = next((o for o in session.get("options", []) if o.get("id") == opt_id), None)
        if not chosen:
            raise ValueError("INVALID_CLARIFICATION: selected_option_id not in session options")
        clarif_text = f"User chose option {opt_id}: {chosen.get('title')} — {chosen.get('summary')}"
    elif "freetext" in keys_present:
        clarif_text = f"User additional context: {clarification['freetext']}"
    else:
        clarif_text = "User skipped clarification — use your best judgment based on inventory"

    user_prompt = session["prompt"]

    # Build inventory (full version with summaries)
    inventory_text = await _build_inventory_for_propose(db, user_id)

    user_message = (
        f"USER PROMPT: {user_prompt}\n"
        f"USER LANGUAGE: {user_lang}\n"
        f"PREFERRED TYPE: {preferred_type or 'not specified — pick best fit'}\n\n"
        f"CLARIFICATION:\n{clarif_text}\n\n"
        f"USER'S INVENTORY:\n{inventory_text}"
    )

    # Step 1: LLM select sources + metadata (retry once on parse failure)
    selection = None
    last_err = None
    for attempt in range(2):
        try:
            selection = await call_llm_json(PROPOSE_SYSTEM_PROMPT, user_message, temperature=0.3)
            break
        except Exception as e:
            last_err = e
            logger.warning(f"propose_pack select LLM attempt {attempt+1} failed: {e}")
    if selection is None:
        raise RuntimeError(f"LLM_RESPONSE_INVALID: {last_err}")

    selected_file_ids = [str(x) for x in selection.get("selected_files", []) if isinstance(x, str)]
    selected_cluster_ids = [str(x) for x in selection.get("selected_clusters", []) if isinstance(x, str)]
    title = selection.get("suggested_title", "Untitled Pack")
    pack_type = selection.get("suggested_type", "project")
    if pack_type not in {"profile", "study", "work", "project"}:
        pack_type = "project"
    intent = selection.get("suggested_intent", "")
    scope = selection.get("suggested_scope", "")

    if not selected_file_ids and not selected_cluster_ids:
        raise RuntimeError("LLM_RESPONSE_INVALID: AI selected zero sources")

    # Step 2: Distill summary (call_llm_pro ผ่าน _generate_pack_content เดิม)
    # ดึง content ของ source ที่ AI เลือก
    from sqlalchemy.orm import selectinload
    source_texts = []
    if selected_file_ids:
        files_res = await db.execute(
            select(File).where(
                File.id.in_(selected_file_ids),
                File.user_id == user_id,
                File.file_kind == "processed",   # safety: AI อาจ hallucinate vault file id
            ).options(selectinload(File.summary))
        )
        for f in files_res.scalars().all():
            text = ""
            if f.summary and f.summary.summary_text:
                text = f.summary.summary_text
            elif f.extracted_text:
                text = f.extracted_text[:3000]
            if text:
                source_texts.append(f"[{f.filename}]:\n{text}")
    if selected_cluster_ids:
        clusters_res = await db.execute(
            select(Cluster).where(
                Cluster.id.in_(selected_cluster_ids),
                Cluster.user_id == user_id,
            )
        )
        for c in clusters_res.scalars().all():
            if c.summary:
                source_texts.append(f"[Collection: {c.title}]:\n{c.summary}")

    if not source_texts:
        raise RuntimeError("LLM_RESPONSE_INVALID: selected sources had no content")

    combined = "\n\n---\n\n".join(source_texts)
    summary_text = await _generate_pack_content(
        pack_type, title, combined, intent=intent, scope=scope,
    )

    # Build sources list สำหรับ frontend (ติ๊ก checkbox ได้)
    sources_payload = []
    for fid in selected_file_ids:
        f = next((x for x in session["inventory_snapshot"]["files"] if x["id"] == fid), None)
        if f:
            sources_payload.append({"id": fid, "kind": "file", "title": f["filename"], "included": True})
    for cid in selected_cluster_ids:
        c = next((x for x in session["inventory_snapshot"]["clusters"] if x["id"] == cid), None)
        if c:
            sources_payload.append({"id": cid, "kind": "cluster", "title": c["title"], "included": True})

    # Cache draft
    draft_id = _gen_draft_id()
    _DRAFT_CACHE[draft_id] = {
        "user_id": user_id,
        "payload": {
            "title": title,
            "type": pack_type,
            "intent": intent,
            "scope": scope,
            "summary_text": summary_text,
            "sources": sources_payload,
            "selected_file_ids": selected_file_ids,
            "selected_cluster_ids": selected_cluster_ids,
        },
        "created_at": datetime.utcnow(),
    }

    expires_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    return {
        "draft_id": draft_id,
        "title": title,
        "type": pack_type,
        "intent": intent,
        "scope": scope,
        "summary_text": summary_text,
        "sources": sources_payload,
        "expires_at": expires_at,
        "ai_calls_used": 2,  # Step 1 + Step 2
    }


# ═══════════════════════════════════════════
# /confirm — save real pack
# ═══════════════════════════════════════════

async def confirm_pack(
    db: AsyncSession, user, draft_id: str, edits: dict | None = None
) -> dict:
    """Save draft as real ContextPack. user is User ORM object (มี .id)

    edits = optional partial overrides:
      title, type, intent, scope, summary_text, included_source_ids
    ถ้า included_source_ids ส่งมา → filter sources ให้เหลือเฉพาะที่ user tick ไว้
    """
    _gc_expired()

    draft = _DRAFT_CACHE.get(draft_id)
    if not draft:
        raise ValueError("DRAFT_NOT_FOUND")
    if draft["user_id"] != user.id:
        raise ValueError("DRAFT_NOT_FOUND")  # กัน steal — message เดียวกัน

    payload = dict(draft["payload"])  # copy

    # Apply edits
    edits = edits or {}
    if "title" in edits and edits["title"]:
        payload["title"] = edits["title"]
    if "type" in edits and edits["type"]:
        if edits["type"] not in {"profile", "study", "work", "project"}:
            raise ValueError("INVALID_TYPE")
        payload["type"] = edits["type"]
    if "intent" in edits:
        payload["intent"] = edits["intent"] or ""
    if "scope" in edits:
        payload["scope"] = edits["scope"] or ""
    if "summary_text" in edits and edits["summary_text"]:
        payload["summary_text"] = edits["summary_text"]

    # Filter sources by user selection
    included_ids = edits.get("included_source_ids")
    if included_ids is not None:
        included_set = set(included_ids)
        file_ids = [fid for fid in payload["selected_file_ids"] if fid in included_set]
        cluster_ids = [cid for cid in payload["selected_cluster_ids"] if cid in included_set]
        if not file_ids and not cluster_ids:
            raise ValueError("NO_SOURCES_SELECTED")
    else:
        file_ids = payload["selected_file_ids"]
        cluster_ids = payload["selected_cluster_ids"]

    # Re-check pack quota (user อาจสร้าง pack อื่นไประหว่างนี้)
    err = await check_pack_create_allowed(db, user)
    if err:
        raise RuntimeError(f"PACK_LIMIT_REACHED: {err.get('error')}")

    # Save real pack — pass override_summary เพื่อไม่ distill ซ้ำ
    pack_dict = await create_pack(
        db,
        user_id=user.id,
        pack_type=payload["type"],
        title=payload["title"],
        source_file_ids=file_ids,
        source_cluster_ids=cluster_ids,
        intent=payload["intent"],
        scope=payload["scope"],
        created_via="ai_builder",
        override_summary=payload["summary_text"],
    )

    # Log usage (1 ครั้งต่อ confirmed pack แม้ใช้ 3 LLM calls)
    await log_usage(db, user.id, "ai_summary")
    await db.commit()

    # Cleanup cache
    _DRAFT_CACHE.pop(draft_id, None)
    # Cleanup associated session (optional — รอ TTL ก็ได้ แต่ proactive ดีกว่า)

    return pack_dict


# ═══════════════════════════════════════════
# /discard
# ═══════════════════════════════════════════

def discard_draft(user_id: str, draft_id: str) -> bool:
    """Drop draft from cache. Returns True if deleted, False if not found / not yours."""
    draft = _DRAFT_CACHE.get(draft_id)
    if not draft:
        return False
    if draft["user_id"] != user_id:
        return False
    del _DRAFT_CACHE[draft_id]
    return True
