"""Personal Data Bank (PDB) — FastAPI Backend (v5.0 — Multi-User + Auth)"""
import os
import re
import json
import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, UploadFile, File as FastAPIFile, Depends, HTTPException, BackgroundTasks, Query, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    init_db, get_db, gen_id,
    User, File, Cluster, FileClusterMap, FileInsight, FileSummary,
    ContextPack, GraphNode, GraphEdge, NoteObject, SuggestedRelation, GraphLens,
    MCPToken, MCPUsageLog, UsageLog, AuditLog,
    DriveConnection,
    ChatQuery, ContextInjectionLog, ContextMemory, PersonalityHistory, CanvasObject,
    PackShare, LineUser,
)
from .organizer import organize_files
from .retriever import chat_with_retrieval
from .duplicate_detector import detect_duplicates_for_batch
# v7.1: detect_duplicates_for_batch ถูกเรียกใน /api/organize-new (post-organize)
# v9.4.0: extract_text + classify_extraction_status + compute_content_hash ย้ายไป
# upload_worker.py — main.py ไม่ extract เองแล้ว (save+queue mode)
from .profile import get_profile, update_profile, is_profile_complete
from .context_packs import list_packs, get_pack, create_pack, delete_pack, regenerate_pack
from .graph_builder import build_full_graph, get_graph_data, get_node_detail, get_neighborhood
from .relations import get_backlinks, get_outgoing, get_suggestions, accept_suggestion, dismiss_suggestion, generate_suggestions
from .metadata import enrich_file_metadata, enrich_all_files, get_file_metadata, update_file_metadata
from .config import UPLOAD_DIR, BASE_DIR, ADMIN_PASSWORD, APP_VERSION
from .mcp_tokens import generate_token, validate_token, list_tokens, revoke_token, get_active_token_count
from .mcp_tools import call_tool, get_usage_logs, TOOL_REGISTRY
from .auth import register_user, login_user, get_current_user, get_optional_user, request_password_reset, reset_password, require_admin
from . import admin as _admin_mod
# Billing (Stripe) removed in v9.6.0 — see docs/restoration/billing-restore.md
from .plan_limits import (
    check_upload_allowed, check_pack_create_allowed, check_summary_allowed,
    check_refresh_allowed, check_export_allowed, get_usage_summary, log_usage, get_limits, PLAN_LIMITS,
    lock_excess_data, unlock_data_for_plan, log_audit
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="Personal Data Bank", version=APP_VERSION)

# CORS — pinned to known origins. `*` + allow_credentials is unsafe (any site can
# issue credentialed XHR with the user's JWT). Override via CORS_ORIGINS env (comma list).
_default_origins = "https://personaldatabank.fly.dev,http://localhost:8000,http://127.0.0.1:8000"
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# v10.0.14 — Unified HTTPException response shape.
# เดิม: code ในโปรเจกต์ raise สองรูปแบบสลับกัน:
#   - HTTPException(detail="message")            → {"detail": "message"}
#   - HTTPException(detail={"error": {"code":...,"message":...}})  → {"detail": {"error":...}}
# Frontend ต้อง fallback parsing สองชั้น → fragile.
#
# Handler นี้ normalize ทุก HTTPException ให้ response shape เดียวกัน:
#   {
#     "detail": "<human-readable message>",     ← legacy field (frontend เก่าอ่าน)
#     "error":  { "code": "<CODE>", "message": "<msg>" }  ← new field
#   }
# ไม่ต้องแก้ raise site → backward-compat 100%
# (HTTPException + JSONResponse import แล้วด้านบน)
@app.exception_handler(HTTPException)
async def _unified_http_exception_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    code = "HTTP_" + str(exc.status_code)
    message = ""

    if isinstance(detail, str):
        message = detail
    elif isinstance(detail, dict):
        # Already structured: {"error": {"code":..., "message":...}}
        if "error" in detail and isinstance(detail["error"], dict):
            code = detail["error"].get("code", code)
            message = detail["error"].get("message", "")
        # หรือ flat: {"code":..., "message":...}
        elif "code" in detail or "message" in detail:
            code = detail.get("code", code)
            message = detail.get("message", "")
        else:
            message = str(detail)
    else:
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": message,                     # legacy compatibility
            "error": {"code": code, "message": message},
        },
        headers=exc.headers,
    )


@app.on_event("startup")
async def startup():
    await init_db()
    # Rebuild TF-IDF search index from existing data (survives restart).
    # v10.0.0 -- previously this was O(N^2) for two reasons:
    #   1) per-file cluster lookup did 2 separate SELECTs (N+1)
    #   2) vector_search.index_file rebuilt IDF on every call (walks all
    #      chunks each time)
    # Now: bulk-fetch cluster titles in 2 queries, skip per-call IDF rebuild,
    # finalize IDF once per user at the end.
    async for db in get_db():
        try:
            from . import vector_search
            files_res = await db.execute(
                select(File).where(File.processing_status == "ready")
            )
            ready_files = files_res.scalars().all()

            # Bulk cluster-title lookup (1 query for maps, 1 for clusters)
            file_ids = [f.id for f in ready_files if f.extracted_text]
            cluster_title_by_file: dict[str, str] = {}
            if file_ids:
                cm_rows = (await db.execute(
                    select(FileClusterMap.file_id, FileClusterMap.cluster_id)
                    .where(FileClusterMap.file_id.in_(file_ids))
                )).all()
                file_to_cluster = {fid: cid for fid, cid in cm_rows}
                cluster_ids = list({cid for cid in file_to_cluster.values()})
                cluster_titles = {}
                if cluster_ids:
                    cl_rows = (await db.execute(
                        select(Cluster.id, Cluster.title).where(Cluster.id.in_(cluster_ids))
                    )).all()
                    cluster_titles = {cid: (title or "") for cid, title in cl_rows}
                for fid, cid in file_to_cluster.items():
                    cluster_title_by_file[fid] = cluster_titles.get(cid, "")

            indexed = 0
            users_touched: set[str] = set()
            for f in ready_files:
                if not f.extracted_text:
                    continue
                vector_search.index_file(
                    file_id=f.id,
                    filename=f.filename,
                    text=f.extracted_text,
                    cluster_title=cluster_title_by_file.get(f.id, ""),
                    user_id=f.user_id,           # v5.1 — per-user index
                    skip_idf_rebuild=True,        # v10.0.0 — finalize once
                )
                users_touched.add(f.user_id)
                indexed += 1
            for uid in users_touched:
                vector_search.finalize_bulk_index(uid)
            if indexed:
                logger.info(
                    f"Startup: rebuilt search index for {indexed} files "
                    f"({len(users_touched)} users, bulk-IDF)"
                )
        except Exception as e:
            logger.warning(f"Startup: search index rebuild failed: {e}")
        break

    # v10.0.2 — HANDOFF Pattern: startup probe for ingestion deps.
    # Logs warnings (not errors — fallbacks cover all paths) so admin
    # can see at boot which paths are degraded.
    try:
        from .processors.startup_probe import run_startup_probe
        run_startup_probe(logger)
    except Exception as e:
        logger.warning(f"Startup probe failed (non-fatal): {e}")

    # v9.4.0 — start upload_worker (background async task)
    # ทำหน้าที่ poll DB queue + extract files ที่ status='queued'
    # Recovery: reset stale 'extracting' (> 30 min) → 'queued' ก่อนเริ่ม loop
    try:
        from .upload_worker import start_worker
        await start_worker()
    except Exception as e:
        logger.warning(f"Startup: upload_worker start failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    """v9.4.0 — graceful worker shutdown (max 5s timeout)."""
    try:
        from .upload_worker import stop_worker
        await stop_worker()
    except Exception as e:
        logger.warning(f"Shutdown: upload_worker stop failed: {e}")


# ═══════════════════════════════════════════
# AUTH APIs (v5.0 + v5.1 Password Reset)
# ═══════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = "User"

class LoginRequest(BaseModel):
    email: str
    password: str

class ResetRequestModel(BaseModel):
    email: str

class ResetPasswordModel(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/register")
async def api_register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    return await register_user(db, req.email, req.password, req.name)

# v10.0.14 — In-memory login rate limiter (5 fails / 15 min per IP).
# Prevents brute-force. Sliding window via timestamp list. Single-machine only;
# multi-machine deploy ต้องย้ายเป็น Redis (Fly app ปัจจุบัน 2 machines แต่ load
# กระจายกันแบบ stateless → rate-limit ไม่ฝั่งเดียวก็ acceptable trade-off).
import time as _time
_LOGIN_FAIL_WINDOW_SEC = 15 * 60
_LOGIN_FAIL_MAX = 5
_login_fail_history: dict[str, list[float]] = {}


def _check_login_rate_limit(ip: str) -> None:
    """Raise 429 if IP exceeded fail threshold in the sliding window."""
    now = _time.time()
    history = _login_fail_history.get(ip, [])
    # Drop old entries outside window
    history = [t for t in history if now - t < _LOGIN_FAIL_WINDOW_SEC]
    _login_fail_history[ip] = history
    if len(history) >= _LOGIN_FAIL_MAX:
        retry_after = int(_LOGIN_FAIL_WINDOW_SEC - (now - history[0]))
        raise HTTPException(
            status_code=429,
            detail=f"พยายาม login ผิดเกิน {_LOGIN_FAIL_MAX} ครั้ง — ลองใหม่ในอีก {retry_after // 60 + 1} นาที",
            headers={"Retry-After": str(retry_after)},
        )


def _record_login_fail(ip: str) -> None:
    """Append a failure timestamp for the IP."""
    _login_fail_history.setdefault(ip, []).append(_time.time())


def _clear_login_fails(ip: str) -> None:
    """Clear all failures after successful login."""
    _login_fail_history.pop(ip, None)


@app.post("/api/auth/login")
async def api_login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Rate-limited 5 fails / 15 min per IP."""
    # Behind Fly proxy → real client IP ใน Fly-Client-IP header; fallback ไป request.client
    ip = request.headers.get("fly-client-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    _check_login_rate_limit(ip)
    try:
        result = await login_user(db, req.email, req.password)
    except HTTPException as e:
        if e.status_code == 401:
            _record_login_fail(ip)
        raise
    _clear_login_fails(ip)
    return result

@app.get("/api/auth/me")
async def api_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "mcp_secret": current_user.mcp_secret,
    }

# v5.1 — Password Reset
@app.post("/api/auth/request-reset")
async def api_request_reset(req: ResetRequestModel, db: AsyncSession = Depends(get_db)):
    """Step 1: Verify email and get reset token."""
    return await request_password_reset(db, req.email)

@app.post("/api/auth/reset-password")
async def api_reset_password(req: ResetPasswordModel, db: AsyncSession = Depends(get_db)):
    """Step 2: Reset password with token."""
    return await reset_password(db, req.token, req.new_password)


# Google Sign-In endpoints removed in v9.5.0.
# See docs/restoration/google-login-restore.md to re-enable.


# ─── REQUEST MODELS ───

class ChatRequest(BaseModel):
    question: str

class MBTIData(BaseModel):
    """MBTI sub-model — type + source. v6.0"""
    type: str
    source: str = "self_report"

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        from .personality import validate_mbti
        if not validate_mbti(v):
            raise ValueError("INVALID_MBTI_TYPE")
        return v

    @field_validator("source")
    @classmethod
    def _check_source(cls, v: str) -> str:
        from .personality import MBTI_SOURCES
        if v not in MBTI_SOURCES:
            raise ValueError("INVALID_MBTI_SOURCE")
        return v


class EnneagramData(BaseModel):
    """Enneagram sub-model — core 1-9 + optional wing (with wrap-around). v6.0"""
    core: int
    wing: int | None = None

    @field_validator("core")
    @classmethod
    def _check_core(cls, v: int) -> int:
        if not isinstance(v, int) or not (1 <= v <= 9):
            raise ValueError("INVALID_ENNEAGRAM_CORE")
        return v

    @model_validator(mode="after")
    def _check_wing(self) -> "EnneagramData":
        # ใช้ get_enneagram_wings เพื่อกัน off-by-one ของ wrap (9→1, 1→9)
        if self.wing is None:
            return self
        from .personality import validate_enneagram
        if not validate_enneagram(self.core, self.wing):
            raise ValueError("INVALID_ENNEAGRAM_WING")
        return self


class ProfileRequest(BaseModel):
    # ─── existing 5 text fields (unchanged) ───
    identity_summary: str | None = None
    goals: str | None = None
    working_style: str | None = None
    preferred_output_style: str | None = None
    background_context: str | None = None
    # ─── v6.0 — personality fields (ทุกตัว optional, partial update) ───
    # ส่ง None เพื่อ clear, ไม่ส่ง field เลย = ไม่เปลี่ยน
    mbti: MBTIData | None = None
    enneagram: EnneagramData | None = None
    clifton_top5: list[str] | None = Field(default=None, max_length=5)
    via_top5: list[str] | None = Field(default=None, max_length=5)

class ContextPackRequest(BaseModel):
    type: str  # profile, study, work, project
    title: str
    source_file_ids: list[str] = []
    source_cluster_ids: list[str] = []

# ─── v9.2.0 AI Pack Builder ─────────────────────────────────────
class AIBuilderClarifyRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=500)

class AIBuilderClarification(BaseModel):
    """ต้องมี exactly 1 ใน 3 fields — validate ที่ ai_pack_builder.propose_pack"""
    selected_option_id: int | None = None
    freetext: str | None = Field(default=None, max_length=500)
    skipped: bool | None = None

class AIBuilderProposeRequest(BaseModel):
    session_id: str
    clarification: AIBuilderClarification
    preferred_type: str | None = None  # profile|study|work|project (validate ที่ AI level)

class AIBuilderConfirmEdits(BaseModel):
    title: str | None = None
    type: str | None = None
    intent: str | None = None
    scope: str | None = None
    summary_text: str | None = None
    included_source_ids: list[str] | None = None

class AIBuilderConfirmRequest(BaseModel):
    draft_id: str
    edits: AIBuilderConfirmEdits | None = None

# v9.3.0 — Pack Share request models
class PackShareCreateRequest(BaseModel):
    include_files: bool = False

class PackShareUpdateRequest(BaseModel):
    include_files: bool

class MetadataUpdateRequest(BaseModel):
    tags: list[str] | None = None
    aliases: list[str] | None = None
    sensitivity: str | None = None
    source_of_truth: bool | None = None
    freshness: str | None = None
    version: str | None = None


# ═══════════════════════════════════════════
# v8.2.0 — Admin Request Models
# ═══════════════════════════════════════════
# ใช้กับ /api/admin/* endpoints. ทุก mutation request ต้องมี reason
# (บันทึกใน audit_logs.old_value/new_value เพื่อ accountability)

class AdminChangePlanRequest(BaseModel):
    """PUT /api/admin/users/{user_id}/plan body."""
    plan: str  # "free" | "starter" | "admin" — validate ใน admin module
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


class AdminResetPasswordRequest(BaseModel):
    """POST /api/admin/users/{user_id}/reset-password body."""
    new_password: str
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


class AdminToggleRequest(BaseModel):
    """PUT /api/admin/users/{user_id}/active หรือ /admin body.

    `value` = is_active หรือ is_admin ขึ้นกับ endpoint.
    """
    value: bool
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


class AdminDeleteUserRequest(BaseModel):
    """DELETE /api/admin/users/{user_id} body · v10.0.x.

    `confirm_email` ต้องตรงกับ email ของ target เพื่อ double-confirm (กัน misclick).
    `reason` คำอธิบายว่าทำไมลบ · เข้า audit log ถาวร.
    """
    confirm_email: str
    reason: str

    @field_validator("confirm_email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_CONFIRM_EMAIL")
        return v.strip().lower()

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


# ═══════════════════════════════════════════
# FILE APIs (v1 — preserved)
# ═══════════════════════════════════════════

# v7.5.0 — Structured skip schema
# `reason` (legacy str) ถูกแทนด้วย `{filename, code, message, suggestion}` เพื่อให้
# frontend แสดง per-file actionable card แทน flat toast comma-join
SKIP_TEMPLATES = {
    "UNSUPPORTED_TYPE": {
        "message": "ไฟล์ .{ext} ยังไม่รองรับ",
        "suggestion": "ลองบันทึกเป็น PDF, Word, หรือ TXT แล้วอัปอีกครั้ง",
    },
    "FILE_TOO_LARGE": {
        "message": "ไฟล์ใหญ่เกิน {limit}MB",
        "suggestion": "บีบอัดด้วย Smallpdf หรือแยกเป็นไฟล์ย่อย",
    },
    "QUOTA_EXCEEDED": {
        "message": "ครบจำนวนไฟล์ที่เก็บได้แล้ว ({limit} ไฟล์)",
        "suggestion": "ลบไฟล์เก่าที่ไม่ใช้ หรืออัปเกรดแพลน",
    },
    "EMPTY_FILE": {
        "message": "ไฟล์ว่างเปล่า",
        "suggestion": "ตรวจว่าไฟล์ไม่เสียหายก่อนอัปใหม่",
    },
    # v9.4.0 — per-user upload queue cap (multi-tenant fairness)
    "QUEUE_FULL": {
        "message": "คิว upload เต็ม ({limit} ไฟล์) — รอบางไฟล์เสร็จก่อน",
        "suggestion": "รอประมาณ 1-2 นาทีแล้วลองอีกครั้ง หรืออัปเกรดแพลน",
    },
}


def _make_skip(code: str, filename: str, **fmt_args) -> dict:
    """Build per-file skip entry with structured code + actionable suggestion (v7.5.0)."""
    tpl = SKIP_TEMPLATES[code]
    return {
        "filename": filename,
        "code": code,
        "message": tpl["message"].format(**fmt_args),
        "suggestion": tpl["suggestion"],
        # legacy field — kept for backward compat กับ test/script เดิมที่ยัง parse "reason"
        "reason": tpl["message"].format(**fmt_args),
    }


# v9.2.0 — Per-user quota lock for parallel uploads.
# Frontend may now POST /api/upload concurrently (one file per request) to
# speed up multi-file uploads. Without this lock, two parallel requests for
# the same user could each read `current_count = N` and both pass the
# `N+1 < limit` check, blowing past file_limit. The lock serializes ONLY the
# atomic "count + reserve slot via placeholder INSERT" critical section —
# slow work (extract_text, ai_ingest) still runs outside the lock so parallel
# uploads from the same user remain genuinely parallel at the CPU/IO layer.
_USER_QUOTA_LOCKS: dict[str, asyncio.Lock] = {}
_USER_QUOTA_LOCKS_GUARD = asyncio.Lock()

async def _get_user_quota_lock(user_id: str) -> asyncio.Lock:
    async with _USER_QUOTA_LOCKS_GUARD:
        lock = _USER_QUOTA_LOCKS.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            _USER_QUOTA_LOCKS[user_id] = lock
        return lock


# v10.0.0 -- Per-user organize "in-progress" sentinel set.
# Plain asyncio.Lock has TOCTOU race when used as "fast-fail" (check + acquire
# are not atomic). We use a set protected by a guard lock so adding the user
# id and checking "already in" are one critical section -> rapid double-click
# gets a clean 409 instead of waiting + duplicating LLM spend.
_ORGANIZE_IN_PROGRESS: set[str] = set()
_ORGANIZE_GUARD = asyncio.Lock()


async def _try_start_organize(user_id: str) -> bool:
    """Return True if no organize is running -> caller may proceed.
    Return False if one is in progress -> caller should 409."""
    async with _ORGANIZE_GUARD:
        if user_id in _ORGANIZE_IN_PROGRESS:
            return False
        _ORGANIZE_IN_PROGRESS.add(user_id)
        return True


async def _end_organize(user_id: str) -> None:
    """Clear the in-progress sentinel. Always call from a finally block."""
    async with _ORGANIZE_GUARD:
        _ORGANIZE_IN_PROGRESS.discard(user_id)


@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """v9.4.0 — save + queue mode.

    Extract + AI ingest ย้ายไป upload_worker (background async loop).
    Returns ทันที (~100-200ms ต่อไฟล์ vs 30-120s ใน v9.3.4).

    Per-user quota lock + per-plan upload_queue_cap (ADR-007 multi-tenant fairness).
    BYOS Drive push ย้ายไปทำใน worker (post-extract) — แทน BackgroundTask เดิม.

    Vault files (ext ไม่อยู่ใน allowed_types) ไม่เข้า queue — extract = name only,
    ทำตรงๆ ใน request นี้ (เร็วอยู่แล้ว).
    """
    # M-2 fix v2: explicit imports (pattern เดิม = local import inside function)
    from sqlalchemy import func
    from .plan_limits import get_limits as _gl, get_file_count as _fc
    from .upload_worker import get_priority_class, get_avg_sec

    uploaded = []
    skipped = []
    _limits = _gl(current_user)
    allowed_types = _limits["allowed_file_types"]
    max_bytes = _limits["max_file_size_mb"] * 1024 * 1024
    file_limit = _limits["file_limit"]
    queue_cap = _limits.get("upload_queue_cap", 10)

    # v9.2.0 — per-user lock for atomic quota reservation across parallel requests
    quota_lock = await _get_user_quota_lock(current_user.id)

    for upload_file in files:
        # Strip any client-supplied directory components — `upload_file.filename`
        # is attacker-controlled. `os.path.basename` defangs `../` traversal,
        # absolute paths, and Windows-style `..\\` on POSIX servers.
        original_name = os.path.basename(upload_file.filename or "") or "unnamed"
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

        # v9.1.0 — Raw File Vault: ext ที่ไม่อยู่ใน allowed_types
        is_vault = ext not in allowed_types

        # v10.0.0 -- cheap pre-checks BEFORE loading bytes into memory.
        # Trust upload_file.size when present (FastAPI fills from Content-Length).
        declared_size = getattr(upload_file, "size", None)
        if declared_size is not None:
            if declared_size == 0:
                skipped.append(_make_skip("EMPTY_FILE", original_name))
                continue
            if declared_size > max_bytes:
                skipped.append(_make_skip("FILE_TOO_LARGE", original_name, limit=_limits["max_file_size_mb"]))
                continue

        contents = await upload_file.read()

        # Fallback validation (when size header was missing / unreliable)
        if len(contents) == 0:
            skipped.append(_make_skip("EMPTY_FILE", original_name))
            continue
        if len(contents) > max_bytes:
            skipped.append(_make_skip("FILE_TOO_LARGE", original_name, limit=_limits["max_file_size_mb"]))
            continue

        # ── Atomic quota reservation (per-user lock) ──────────────────────
        # Re-read live count from DB inside the lock so concurrent requests
        # see each other's reservations. Insert+commit a placeholder row
        # immediately to "claim" the slot before releasing the lock.
        file_id = gen_id()
        user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
        os.makedirs(user_upload_dir, exist_ok=True)
        # v9.4.7 — truncate filename to fit Linux ext4 255-byte limit (UTF-8).
        # Thai = 3 bytes/char → 120 Thai chars = 360 bytes → OSError [Errno 36].
        # Reserve 20 bytes for {file_id}_ prefix + ext + safety; keep extension intact.
        prefix = f"{file_id}_"
        budget = 255 - len(prefix.encode("utf-8"))
        ext_part = ""
        stem_part = original_name
        if "." in original_name:
            stem_part, ext_part = original_name.rsplit(".", 1)
            ext_part = "." + ext_part
        ext_bytes = len(ext_part.encode("utf-8"))
        stem_budget = budget - ext_bytes
        stem_bytes = stem_part.encode("utf-8")
        if len(stem_bytes) > stem_budget:
            stem_part = stem_bytes[:stem_budget].decode("utf-8", errors="ignore")
        safe_filename = f"{prefix}{stem_part}{ext_part}"
        raw_path = os.path.join(user_upload_dir, safe_filename)

        async with quota_lock:
            # File limit check (existing v9.2.0)
            live_count = await _fc(db, current_user.id)
            if live_count >= file_limit:
                skipped.append(_make_skip("QUOTA_EXCEEDED", original_name, limit=file_limit))
                continue

            # v9.4.0 — Per-plan upload queue cap (ADR-007)
            queue_count = await db.scalar(
                select(func.count()).select_from(File).where(
                    File.user_id == current_user.id,
                    File.processing_status.in_(["queued", "extracting"]),
                )
            )
            if (queue_count or 0) >= queue_cap:
                skipped.append(_make_skip("QUEUE_FULL", original_name, limit=queue_cap))
                continue

            now = datetime.utcnow()

            # v10.0.0 -- ORDER REVERSED to fix the upload race condition.
            # Old order: commit DB row -> release lock -> write file.
            # That left a window where the worker (polls every 2s) could claim
            # a 'queued' row whose raw_path didn't exist on disk yet, marking
            # the file as FILE_MISSING even though the upload was valid.
            # New order: write file first -> commit DB.  Worker can only see
            # rows AFTER the file is on disk.  Lock is held during the write
            # but it is *per-user*, so other users are unaffected.
            def _write_bytes(path: str, data: bytes) -> None:
                with open(path, "wb") as f:
                    f.write(data)
            try:
                await asyncio.to_thread(_write_bytes, raw_path, contents)
            except OSError as e:
                logger.error("upload_files: disk write failed for %s: %s", raw_path, e)
                skipped.append(_make_skip("DISK_ERROR", original_name))
                continue

            if is_vault:
                # Vault path — ไม่เข้า queue, extract = name-based, ทำตรงๆ
                from .vault import build_vault_searchable_text
                vault_text = build_vault_searchable_text(original_name, ext)
                placeholder = File(
                    id=file_id,
                    user_id=current_user.id,
                    filename=original_name,
                    filetype=ext,
                    raw_path=raw_path,
                    extracted_text=vault_text,
                    processing_status="vault_only",
                    extraction_status="vault",
                    file_kind="vault_only",
                    queued_at=now,
                    extract_completed_at=now,
                    progress_pct=100,
                )
            else:
                # v9.4.0 — Queue path: insert placeholder + return ทันที
                # worker จะ pickup → extract → update status='uploaded'
                placeholder = File(
                    id=file_id,
                    user_id=current_user.id,
                    filename=original_name,
                    filetype=ext,
                    raw_path=raw_path,
                    extracted_text="",
                    processing_status="queued",
                    content_hash=None,
                    extraction_status="pending",
                    file_kind="processed",
                    queued_at=now,
                )
            db.add(placeholder)
            await db.commit()

        # คำนวณ queue_position + estimated_wait_sec (TC-4 truthful)
        if is_vault:
            queue_position = 0
            estimated_wait_sec = 0
            wait_source = "rolling_avg"
        else:
            # Position = #queued rows ของ user คนนี้ที่ queued_at <= now
            qp_res = await db.execute(
                select(File.filetype).where(
                    File.user_id == current_user.id,
                    File.processing_status == "queued",
                    File.queued_at <= now,
                )
            )
            ahead = qp_res.fetchall()
            queue_position = len(ahead)
            # Sum rolling avg for files ahead in queue (TC-4)
            estimated_wait_sec = int(sum(
                get_avg_sec(get_priority_class(f[0])) for f in ahead
            ))
            wait_source = "rolling_avg"

        uploaded.append({
            "id": file_id,
            "filename": original_name,
            "filetype": ext,
            "uploaded_at": now.isoformat() + "Z",
            "processing_status": placeholder.processing_status,
            "queue_position": queue_position,
            "estimated_wait_sec": estimated_wait_sec,
            "estimated_wait_source": wait_source,
            "file_kind": placeholder.file_kind,
        })

    return {
        "uploaded": uploaded,
        "count": len(uploaded),
        "skipped": skipped,
    }


_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "csv": "text/csv",
    "json": "application/json",
    "html": "text/html",
    "rtf": "application/rtf",
}


# Phase 1.11 — strict MIME pattern: type/subtype, no params/whitespace.
# Anything else (e.g. crafted `text/html; <script>`) is treated as untrusted
# and dropped in favour of the extension map.
_MIME_RE = re.compile(r"^[\w.+-]+/[\w.+-]+$")


def _guess_mime(ext: str, header_hint: str | None) -> str:
    """Pick a safe Drive MIME.

    Strategy: trust the extension map first (server-known, deterministic).
    Only fall back to the browser-provided Content-Type when the extension
    is unknown AND the header value matches a strict `type/subtype` regex.
    `Content-Type` is attacker-controlled (multipart upload header), so we
    never let it override a known-safe MIME for a recognised extension.
    """
    ext_norm = (ext or "").lower()
    if ext_norm in _MIME_BY_EXT:
        return _MIME_BY_EXT[ext_norm]
    if header_hint:
        candidate = header_hint.split(";", 1)[0].strip()
        if _MIME_RE.match(candidate):
            return candidate
    return "application/octet-stream"


async def _push_uploads_to_drive(
    user_id: str,
    payloads: list[tuple[str, str, bytes, str, str]],
) -> None:
    """Background task — push raw file + extracted text to Drive for BYOS users.

    Opens its own DB session (the request session is already closed when this runs).
    Each payload: (file_id, filename, raw_bytes, mime_type, extracted_text).
    Failures are logged + swallowed — DB is the source of truth, Drive is mirror.
    """
    from .database import AsyncSessionLocal
    from .storage_router import (
        push_extracted_text_to_drive_if_byos,
        push_raw_file_to_drive_if_byos,
    )
    async with AsyncSessionLocal() as bg_db:
        for file_id, filename, content, mime_type, extracted in payloads:
            try:
                drive_id = await push_raw_file_to_drive_if_byos(
                    user_id, bg_db, file_id, filename, content, mime_type,
                )
                if drive_id and extracted:
                    await push_extracted_text_to_drive_if_byos(
                        user_id, bg_db, file_id, extracted,
                    )
            except Exception as e:
                logger.warning(
                    "Background Drive push failed for user %s file %s: %s",
                    user_id, file_id, e,
                )


# v9.3.5.5 — async Drive cleanup for deleted files
# Why: Drive trash can timeout 60s/call · 3 calls × 60s = 180s · เกิน HTTP timeout
# (Cloudflare/Fly ~100s) → 504 ยิง user · response เร็วขึ้น ~200ms · cleanup รัน background
# storage_source guard: drive_picked = user's external file → ห้าม trash (F5 protection)
async def _cleanup_drive_for_deleted_file(
    user_id: str,
    file_id: str,
    drive_file_id: str,
    storage_source: str,
) -> None:
    """Background task: trash Drive raw/ + extracted/ + summaries/ for a deleted File row."""
    from .database import AsyncSessionLocal
    from .storage_router import (
        _should_trash_drive_file,
        delete_drive_file_if_byos,
        delete_extracted_text_from_drive_if_byos,
        delete_summary_from_drive_if_byos,
    )

    if not _should_trash_drive_file(storage_source):
        logger.info(
            "delete_file cleanup: skipped %s · storage_source=%s",
            file_id, storage_source,
        )
        return

    async with AsyncSessionLocal() as bg_db:
        # Drive raw/
        try:
            await delete_drive_file_if_byos(user_id, bg_db, drive_file_id)
        except Exception as e:
            logger.warning("_cleanup_drive raw failed for %s: %s", file_id, e)
        # Drive extracted/
        try:
            await delete_extracted_text_from_drive_if_byos(user_id, bg_db, file_id)
        except Exception as e:
            logger.warning("_cleanup_drive extracted failed for %s: %s", file_id, e)
        # Drive summaries/
        try:
            await delete_summary_from_drive_if_byos(user_id, bg_db, file_id)
        except Exception as e:
            logger.warning("_cleanup_drive summary failed for %s: %s", file_id, e)


async def _cleanup_file_references(
    db: AsyncSession,
    user_id: str,
    file_id: str,
    md_path: str | None = None,
) -> dict:
    """v10.0.x — รวบ orphan cleanup ที่ FK cascade ไม่ครอบคลุม.

    หลัง delete file row, references หลายที่ค้างเป็น orphan:
      - GraphNode (object_type='source_file', object_id=file_id) + edges/suggestions
      - FileSummary.md_path บน disk (DB row cascade · ไฟล์ค้าง)
      - JSON arrays: ContextPack.source_file_ids / ChatQuery.selected_file_ids / ContextInjectionLog.file_ids

    เรียก BEFORE `db.delete(file)` · ไม่รวม empty-cluster cleanup (ต้องรอ FK cascade fire = หลัง commit)

    Returns stats dict สำหรับ logging + test verification.
    """
    from sqlalchemy import delete as sql_delete, or_
    from .database import ChatQuery, ContextInjectionLog

    stats = {
        "graph_nodes_removed": 0,
        "graph_edges_removed": 0,
        "suggestions_removed": 0,
        "summary_md_removed": False,
        "packs_updated": 0,
        "chats_updated": 0,
        "injection_logs_updated": 0,
    }

    # ─── 1. Graph nodes ของไฟล์นี้ + edges/suggestions ที่ touch ───
    node_ids_res = await db.execute(
        select(GraphNode.id).where(
            GraphNode.user_id == user_id,
            GraphNode.object_type == "source_file",
            GraphNode.object_id == file_id,
        )
    )
    node_ids = [r[0] for r in node_ids_res.all()]
    if node_ids:
        # edges (both directions)
        edge_del = await db.execute(
            sql_delete(GraphEdge).where(
                GraphEdge.user_id == user_id,
                or_(
                    GraphEdge.source_node_id.in_(node_ids),
                    GraphEdge.target_node_id.in_(node_ids),
                )
            )
        )
        stats["graph_edges_removed"] = edge_del.rowcount or 0
        # suggestions
        sug_del = await db.execute(
            sql_delete(SuggestedRelation).where(
                SuggestedRelation.user_id == user_id,
                or_(
                    SuggestedRelation.source_node_id.in_(node_ids),
                    SuggestedRelation.target_node_id.in_(node_ids),
                )
            )
        )
        stats["suggestions_removed"] = sug_del.rowcount or 0
        # nodes themselves
        node_del = await db.execute(
            sql_delete(GraphNode).where(GraphNode.id.in_(node_ids))
        )
        stats["graph_nodes_removed"] = node_del.rowcount or 0

    # ─── 2. Summary .md บน local disk ───
    # FileSummary.md_path cascade ลบ DB row แต่ไฟล์ .md ค้าง
    if md_path and os.path.exists(md_path):
        try:
            os.remove(md_path)
            stats["summary_md_removed"] = True
        except OSError as e:
            logger.warning("cleanup_file_refs: remove md_path %s failed: %s", md_path, e)

    # ─── 3. ContextPack.source_file_ids JSON (ตัด file_id ออก) ───
    pack_res = await db.execute(
        select(ContextPack).where(ContextPack.user_id == user_id)
    )
    for p in pack_res.scalars().all():
        try:
            ids = json.loads(p.source_file_ids or "[]")
            if file_id in ids:
                p.source_file_ids = json.dumps([i for i in ids if i != file_id])
                stats["packs_updated"] += 1
        except (ValueError, TypeError):
            pass

    # ─── 4. ChatQuery.selected_file_ids JSON ───
    # pre-filter ด้วย LIKE %file_id% เพื่อไม่ scan ทุก row
    chat_res = await db.execute(
        select(ChatQuery).where(
            ChatQuery.user_id == user_id,
            ChatQuery.selected_file_ids.like(f"%{file_id}%"),
        )
    )
    for c in chat_res.scalars().all():
        try:
            ids = json.loads(c.selected_file_ids or "[]")
            if file_id in ids:
                c.selected_file_ids = json.dumps([i for i in ids if i != file_id])
                stats["chats_updated"] += 1
        except (ValueError, TypeError):
            pass

    # ─── 5. ContextInjectionLog.file_ids JSON (filter via chat_query.user_id JOIN) ───
    log_res = await db.execute(
        select(ContextInjectionLog).join(
            ChatQuery, ChatQuery.id == ContextInjectionLog.chat_query_id
        ).where(
            ChatQuery.user_id == user_id,
            ContextInjectionLog.file_ids.like(f"%{file_id}%"),
        )
    )
    for l in log_res.scalars().all():
        try:
            ids = json.loads(l.file_ids or "[]")
            if file_id in ids:
                l.file_ids = json.dumps([i for i in ids if i != file_id])
                stats["injection_logs_updated"] += 1
        except (ValueError, TypeError):
            pass

    return stats


async def _cleanup_empty_clusters(db: AsyncSession, user_id: str) -> int:
    """ลบ Cluster ที่ไม่เหลือ file_cluster_map (orphan หลัง file delete + FK cascade fire).

    เรียก AFTER `await db.commit()` ของ db.delete(file) · ตอนนั้น FileClusterMap cascade fired แล้ว
    คืนจำนวน clusters ที่ลบ (รวมถึง cleanup graph_node+edges สำหรับ cluster ที่ลบ).
    """
    from sqlalchemy import delete as sql_delete, or_, text

    # find empty clusters (no file_cluster_map entries left)
    empty_res = await db.execute(text("""
        SELECT c.id FROM clusters c
        WHERE c.user_id = :uid
        AND NOT EXISTS (SELECT 1 FROM file_cluster_map fcm WHERE fcm.cluster_id = c.id)
    """), {"uid": user_id})
    empty_ids = [r[0] for r in empty_res.all()]
    if not empty_ids:
        return 0

    # also clean cluster graph nodes + their edges
    cl_node_res = await db.execute(
        select(GraphNode.id).where(
            GraphNode.user_id == user_id,
            GraphNode.object_type == "cluster",
            GraphNode.object_id.in_(empty_ids),
        )
    )
    cl_node_ids = [r[0] for r in cl_node_res.all()]
    if cl_node_ids:
        await db.execute(sql_delete(GraphEdge).where(
            GraphEdge.user_id == user_id,
            or_(
                GraphEdge.source_node_id.in_(cl_node_ids),
                GraphEdge.target_node_id.in_(cl_node_ids),
            )
        ))
        await db.execute(sql_delete(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            or_(
                SuggestedRelation.source_node_id.in_(cl_node_ids),
                SuggestedRelation.target_node_id.in_(cl_node_ids),
            )
        ))
        await db.execute(sql_delete(GraphNode).where(GraphNode.id.in_(cl_node_ids)))

    # finally delete the clusters
    del_res = await db.execute(
        sql_delete(Cluster).where(Cluster.id.in_(empty_ids))
    )
    return del_res.rowcount or 0


# ═══════════════════════════════════════════════════════════════
# v9.4.0 — Upload Queue endpoints
# ═══════════════════════════════════════════════════════════════


def _why_slow(f: File, queue_position: int = 0, estimated_wait_sec: int = 0) -> str | None:
    """v9.4.0 TC-3 — explain ทำไมไฟล์ช้า ในภาษาที่ user เข้าใจ.

    Return None ถ้าไม่ใช่ scenario ที่ "ช้า" (queue position 1-3 ไม่ต้องอธิบาย).
    """
    from .ai_ingest import AUDIO_FORMATS, VIDEO_FORMATS

    ext = (f.filetype or "").lower()
    status = f.processing_status

    if status == "queued" and queue_position > 3:
        if estimated_wait_sec > 60:
            mins = estimated_wait_sec // 60
            return f"อันดับ {queue_position} — ประมาณ {mins} นาที"
        return f"อันดับ {queue_position} — ประมาณ {estimated_wait_sec} วินาที"

    if status == "extracting":
        step = (f.progress_step or "").lower()
        if "ocr" in step:
            return "ไฟล์ใหญ่ — OCR ใช้เวลานาน"
        if ext in AUDIO_FORMATS:
            return "Gemini ถอดเสียง — รอประมาณ 1-3 นาที"
        if ext in VIDEO_FORMATS:
            return "Gemini วิเคราะห์วิดีโอ — รอประมาณ 2-5 นาที"

    return None


@app.get("/api/upload-status")
async def upload_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.0 — list ไฟล์ของ user ที่อยู่ใน queue/extracting/error (24hr window).

    Frontend Upload Tray polls endpoint นี้ทุก 2s ระหว่าง tray เปิด.
    Response shape ออกแบบเป็น flat (event-stream-compatible) สำหรับ FH-2 SSE upgrade.
    """
    from sqlalchemy import func
    from datetime import timedelta
    from .upload_worker import get_priority_class, get_avg_sec, MAX_RETRY_ATTEMPTS, get_worker_health

    # Active = queued + extracting (เรียง queued_at)
    active_res = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status.in_(["queued", "extracting"]),
        ).order_by(File.queued_at.asc())
    )
    active_files = active_res.scalars().all()

    # Failed = error ภายใน 24hr (ไม่โชว์ของเก่ามาก)
    failed_cutoff = datetime.utcnow() - timedelta(hours=24)
    failed_res = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status == "error",
            File.extract_completed_at >= failed_cutoff,
        ).order_by(File.uploaded_at.desc())
    )
    failed_files = failed_res.scalars().all()

    now = datetime.utcnow()
    active_payload = []
    queued_idx = 0
    queued_eta_acc = 0  # accumulated estimated wait for queued items
    for f in active_files:
        if f.processing_status == "queued":
            queued_idx += 1
            qp = queued_idx
            queued_eta_acc += get_avg_sec(get_priority_class(f.filetype or ""))
            step = f.progress_step or f"อันดับที่ {qp} — กำลังรอคิว"
        else:
            qp = 0
            step = f.progress_step or "กำลังประมวลผล"

        # Elapsed = now - extract_started_at (extracting) or now - queued_at (queued)
        ref_time = f.extract_started_at if f.processing_status == "extracting" else f.queued_at
        elapsed_sec = int((now - ref_time).total_seconds()) if ref_time else 0
        why_slow = _why_slow(f, qp, int(queued_eta_acc) if f.processing_status == "queued" else 0)

        active_payload.append({
            "id": f.id,
            "filename": f.filename,
            "filetype": f.filetype,
            "processing_status": f.processing_status,
            "extraction_status": f.extraction_status,
            "queue_position": qp,
            "progress_step": step,
            "progress_pct": f.progress_pct,
            "progress_pct_known": f.progress_pct is not None,
            "stages": {
                "queued_at": (f.queued_at.isoformat() + "Z") if f.queued_at else None,
                "extract_started_at": (f.extract_started_at.isoformat() + "Z") if f.extract_started_at else None,
                "extract_completed_at": (f.extract_completed_at.isoformat() + "Z") if f.extract_completed_at else None,
            },
            "elapsed_sec": elapsed_sec,
            "attempt_count": f.attempt_count or 0,
            "is_retryable": False,
            "why_slow": why_slow,
        })

    failed_payload = []
    for f in failed_files:
        is_retryable = (
            (f.attempt_count or 0) < MAX_RETRY_ATTEMPTS
            and bool(f.raw_path)
            and os.path.exists(f.raw_path)
        )
        failed_payload.append({
            "id": f.id,
            "filename": f.filename,
            "filetype": f.filetype,
            "processing_status": "error",
            "extraction_status": f.extraction_status,
            "extract_error": f.extract_error or "ไม่ทราบสาเหตุ",
            "attempt_count": f.attempt_count or 0,
            "is_retryable": is_retryable,
            "stages": {
                "queued_at": (f.queued_at.isoformat() + "Z") if f.queued_at else None,
                "extract_started_at": (f.extract_started_at.isoformat() + "Z") if f.extract_started_at else None,
                "extract_completed_at": (f.extract_completed_at.isoformat() + "Z") if f.extract_completed_at else None,
            },
        })

    # System status (TC-6 banner trigger)
    worker_health = get_worker_health()
    if worker_health["status"] not in ("running", "disabled"):
        system_status = "stopped"
    elif active_files:
        oldest_queued = min(
            (f.queued_at for f in active_files if f.queued_at),
            default=None,
        )
        if oldest_queued and (now - oldest_queued).total_seconds() > 300:
            system_status = "degraded"
        else:
            system_status = "ok"
    else:
        system_status = "ok"

    queued_count = sum(1 for f in active_files if f.processing_status == "queued")
    extracting_count = sum(1 for f in active_files if f.processing_status == "extracting")

    return {
        "active": active_payload,
        "failed": failed_payload,
        "summary": {
            "queued_count": queued_count,
            "extracting_count": extracting_count,
            "failed_count": len(failed_payload),
            "total_active": len(active_payload),
            "system_status": system_status,
        },
    }


@app.post("/api/upload/{file_id}/retry")
async def retry_upload(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.0 — reset failed file → 'queued' (worker จะ pickup ทำใหม่)."""
    from sqlalchemy import func
    from .upload_worker import MAX_RETRY_ATTEMPTS

    res = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if f.processing_status != "error":
        raise HTTPException(409, detail={"error": {"code": "NOT_RETRYABLE", "message": "ไฟล์นี้ไม่อยู่ในสถานะ error"}})
    if (f.attempt_count or 0) >= MAX_RETRY_ATTEMPTS:
        raise HTTPException(409, detail={"error": {"code": "NOT_RETRYABLE", "message": f"เกิน retry limit ({MAX_RETRY_ATTEMPTS} ครั้ง)"}})
    if not f.raw_path or not os.path.exists(f.raw_path):
        raise HTTPException(410, detail={"error": {"code": "FILE_GONE", "message": "ไฟล์ดิบหายไปแล้ว — ต้องอัปใหม่"}})

    # Reset to queued
    f.processing_status = "queued"
    f.extract_started_at = None
    f.extract_completed_at = None
    f.extract_error = None
    f.progress_step = None
    f.progress_pct = None
    f.attempt_count = (f.attempt_count or 0) + 1
    f.queued_at = datetime.utcnow()
    await db.commit()

    # คำนวณ queue_position ใหม่
    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= f.queued_at,
        )
    )
    return {
        "id": f.id,
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
        "attempt_count": f.attempt_count,
    }


@app.post("/api/upload/{file_id}/dismiss-error")
async def dismiss_upload_error(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.0 — ลบ failed row + raw file + Drive copy (ถ้ามี)."""
    res = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if f.processing_status != "error":
        raise HTTPException(409, detail={"error": {"code": "NOT_DISMISSIBLE", "message": "ไฟล์นี้ไม่ใช่สถานะ error"}})

    # ลบ raw file (best-effort)
    if f.raw_path and os.path.exists(f.raw_path):
        try:
            os.remove(f.raw_path)
        except OSError as e:
            logger.warning(f"dismiss_error: rm raw_path failed for {file_id}: {e}")

    # ลบ Drive copy (BYOS only)
    try:
        from .storage_router import delete_drive_file_if_byos
        await delete_drive_file_if_byos(current_user.id, db, file_id)
    except Exception as e:
        logger.warning(f"dismiss_error: Drive delete failed for {file_id}: {e}")

    await db.delete(f)
    await db.commit()
    return {"deleted": True}


@app.post("/api/upload/{file_id}/cancel")
async def cancel_upload(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.5 — ยกเลิกไฟล์ใน queue (queued/extracting) + ลบ raw + Drive copy.

    Why: ไฟล์ใหญ่ค้างคิวนาน user อยากยกเลิก; เดิม endpoint dismiss-error รับเฉพาะ
    status='error'. Endpoint นี้รับ queued/extracting → set ลบทิ้งทันที.
    Worker จะเห็น row หายไป (เพราะ `delete f`) → claim/process ตัดเอง (rowcount=0).
    """
    res = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if f.processing_status not in ("queued", "extracting"):
        raise HTTPException(409, detail={"error": {
            "code": "NOT_CANCELLABLE",
            "message": "ยกเลิกได้เฉพาะไฟล์ที่ queued/extracting",
        }})

    if f.raw_path and os.path.exists(f.raw_path):
        try:
            os.remove(f.raw_path)
        except OSError as e:
            logger.warning(f"cancel_upload: rm raw_path failed for {file_id}: {e}")

    try:
        from .storage_router import delete_drive_file_if_byos
        await delete_drive_file_if_byos(current_user.id, db, file_id)
    except Exception as e:
        logger.warning(f"cancel_upload: Drive delete failed for {file_id}: {e}")

    await db.delete(f)
    await db.commit()
    return {"cancelled": True}


@app.get("/health")
async def health():
    """v10.0.8 — ultra-light health probe สำหรับ Fly.io http_checks.

    No DB query · ไม่แตะ filesystem · ไม่ต้อง auth · ตอบทันที.
    เป้าหมาย: ให้ Fly probe ทุก 30s เพื่อกัน VM idle → cold start หลัง login.
    หลัง deploy ให้ตั้ง [[http_service.checks]] ใน fly.toml ชี้ที่ /health.
    """
    return {"ok": True, "version": APP_VERSION}


@app.get("/api/healthz/queue")
async def healthz_queue(db: AsyncSession = Depends(get_db)):
    """v9.4.0 — public health endpoint สำหรับ Fly.io probe + frontend banner.

    Returns 200 ปกติ · 503 ถ้า worker stopped/crashed หรือ oldest queued > 5 นาที.
    No auth — public probe (เหมือน /api/healthz เดิม).
    """
    from sqlalchemy import func
    from datetime import timedelta
    from .upload_worker import get_worker_health
    import asyncio

    worker = get_worker_health()
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    # v10.0.x — เปลี่ยน asyncio.gather() → sequential await
    # เดิม: gather() บน 5 queries · share session เดียว · SQLAlchemy aiosqlite ไม่อนุญาต
    #       concurrent ops บน session เดียว → throws InvalidRequestError 500
    # ใหม่: รัน sequential (5 queries · ~5-10ms รวม · ไม่กระทบ Fly probe 10s cadence)
    queued = await db.scalar(
        select(func.count()).select_from(File).where(File.processing_status == "queued")
    )
    extracting = await db.scalar(
        select(func.count()).select_from(File).where(File.processing_status == "extracting")
    )
    error_24h = await db.scalar(
        select(func.count()).select_from(File).where(
            File.processing_status == "error",
            File.extract_completed_at >= cutoff_24h,
        )
    )
    success_24h = await db.scalar(
        select(func.count()).select_from(File).where(
            File.processing_status == "uploaded",
            File.extract_completed_at >= cutoff_24h,
        )
    )
    oldest_queued = await db.scalar(
        select(func.min(File.queued_at)).where(File.processing_status == "queued")
    )
    oldest_age = int((datetime.utcnow() - oldest_queued).total_seconds()) if oldest_queued else 0

    total_24h = (success_24h or 0) + (error_24h or 0)
    success_rate = round((success_24h or 0) / total_24h, 3) if total_24h > 0 else 1.0

    body = {
        "worker": worker,
        "queue": {
            "queued": queued or 0,
            "extracting": extracting or 0,
            "error_24h": error_24h or 0,
            "oldest_queued_age_sec": oldest_age,
        },
        "metrics": {
            "avg_extract_sec_by_class": worker.get("avg_extract_sec_by_class", {}),
            "extract_success_rate_24h": success_rate,
        },
    }

    # 503 ถ้า degraded (Fly.io probe จะ restart machine)
    alerts = []
    if worker["status"] not in ("running", "disabled"):
        alerts.append({"code": "WORKER_NOT_RUNNING", "status": worker["status"]})
    if oldest_age > 300:
        alerts.append({"code": "OLDEST_QUEUED_OVER_5MIN", "value_sec": oldest_age})

    if alerts:
        body["alerts"] = alerts
        return JSONResponse(body, status_code=503)
    return body


@app.post("/api/organize")
async def organize(
    force: bool = Query(False, description="Re-summarize all files even if summary exists"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the organization pipeline on all uploaded files, then build graph.

    v10.0.0:
      - default: skip files that already have a summary (cheap re-runs)
      - ?force=true: re-summarize everything (refresh)
      - Per-user organize lock prevents double-LLM-spend from rapid double clicks
    """
    # v5.9.3 — check summary quota
    limit_err = await check_summary_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])

    # v10.0.0 -- atomic check-and-set: only one organize per user at a time.
    if not await _try_start_organize(current_user.id):
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "ORGANIZE_IN_PROGRESS",
                "message": "Organization already running for this user — please wait",
            }},
        )
    from . import progress_tracker as _pt
    _pt.start(current_user.id, phase="starting",
              step_th="กำลังเริ่มจัดระเบียบทั้งหมด", step_en="Starting full organize")
    try:
        _pt.report(current_user.id, phase="clustering",
                   step_th="AI จัดกลุ่มไฟล์ทั้งหมด", step_en="Clustering all files")
        await organize_files(db, current_user.id, force=force)
        await log_usage(db, current_user.id, "ai_summary")
        await db.commit()

        # v3: Auto-build knowledge graph after organizing
        logger.info("Auto-building knowledge graph...")
        _pt.report(current_user.id, phase="enrich",
                   step_th="กำลังเสริม metadata", step_en="Enriching metadata")
        await enrich_all_files(db, current_user.id, force=force)
        _pt.report(current_user.id, phase="graph",
                   step_th="สร้าง Knowledge Graph", step_en="Building knowledge graph")
        graph_result = await build_full_graph(db, current_user.id)
        _pt.report(current_user.id, phase="suggest",
                   step_th="สร้าง Suggestions", step_en="Generating suggestions")
        await generate_suggestions(db, current_user.id)
        logger.info(f"Graph built: {graph_result}")

        _pt.done(current_user.id, step_th="จัดระเบียบเสร็จสมบูรณ์", step_en="Organize complete")
        return {"status": "ok", "message": "Organization + graph build complete", "graph": graph_result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Organization failed: {e}")
        _pt.error(current_user.id, f"จัดระเบียบล้มเหลว: {str(e)[:200]}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await _end_organize(current_user.id)


@app.get("/api/unprocessed-count")
async def unprocessed_count(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Count + list files that haven't been organized yet (no summary).

    v10.0.4: return up to 50 unprocessed filenames so the badge can show
    a hover/click dropdown — user can see WHICH files are pending instead
    of a mystery "17". no-cache header ensures the badge refresh after
    delete/upload always reads fresh DB state (no stale browser cache).
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    from sqlalchemy import func, exists

    # Same single-query approach: files with extracted_text but no FileSummary row.
    # Single round-trip + accurate (vs. two count queries which can race if a
    # summary lands between them).
    summary_exists = exists(
        select(FileSummary.file_id).where(FileSummary.file_id == File.id)
    )
    unprocessed_files = (await db.execute(
        select(File.id, File.filename, File.filetype, File.uploaded_at,
               File.processing_status, File.extraction_status)
        .where(
            File.user_id == current_user.id,
            File.extracted_text != "",
            File.file_kind == "processed",
            ~summary_exists,
        )
        .order_by(File.uploaded_at.desc())
        .limit(50)
    )).all()

    # Count total — same condition, faster than .all() for big result sets
    total_unprocessed = (await db.execute(
        select(func.count(File.id)).where(
            File.user_id == current_user.id,
            File.extracted_text != "",
            File.file_kind == "processed",
            ~summary_exists,
        )
    )).scalar() or 0

    total_with_text = (await db.execute(
        select(func.count(File.id)).where(
            File.user_id == current_user.id, File.extracted_text != ""
        )
    )).scalar() or 0

    return {
        "unprocessed": total_unprocessed,
        "total": total_with_text,
        "processed": total_with_text - total_unprocessed,
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "filetype": f.filetype,
                "uploaded_at": (f.uploaded_at.isoformat() + "Z") if f.uploaded_at else None,
                "processing_status": f.processing_status,
                "extraction_status": f.extraction_status,
            }
            for f in unprocessed_files
        ],
        "files_truncated": total_unprocessed > 50,
    }


@app.post("/api/organize-new")
async def organize_new(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Run the organization pipeline only on NEW files that don't have summaries yet.

    v7.1: รัน duplicate detection หลัง organize เสร็จ (ตรงนี้ vector_search index
    มีไฟล์ใหม่แล้ว → semantic detection ทำงานเต็ม + intra-batch SEMANTIC ไม่ miss
    ต่างจาก v7.1 round แรกที่ detect ตอน upload แล้ว Risk #9 บังคับ accept)
    Return field `duplicates_found` ให้ frontend แสดง popup ให้ user ตัดสินใจ keep/skip.
    """
    # v5.9.3 — check summary quota
    limit_err = await check_summary_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])
    # v10.0.0 -- atomic check-and-set shared with /api/organize.
    if not await _try_start_organize(current_user.id):
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "ORGANIZE_IN_PROGRESS",
                "message": "Organization already running for this user — please wait",
            }},
        )
    from .organizer import organize_new_files
    from . import progress_tracker as _pt
    _pt.start(current_user.id, phase="starting",
              step_th="กำลังเริ่มจัดระเบียบ", step_en="Starting organize")
    try:
        try:
            result = await organize_new_files(db, current_user.id)
            if result.get("skipped"):
                _pt.done(current_user.id, step_th="ไม่มีไฟล์ใหม่", step_en="No new files")
                return {
                    "status": "ok",
                    "message": "ไม่มีไฟล์ใหม่ที่ต้องจัดระเบียบ",
                    "new_files": 0,
                    "duplicates_found": [],
                }

            await log_usage(db, current_user.id, "ai_summary")
            await db.commit()

            # Enrich + graph for new files
            _pt.report(current_user.id, phase="enrich",
                       step_th="กำลังเสริม metadata", step_en="Enriching metadata")
            await enrich_all_files(db, current_user.id)
            _pt.report(current_user.id, phase="graph",
                       step_th="สร้าง Knowledge Graph", step_en="Building knowledge graph")
            graph_result = await build_full_graph(db, current_user.id)
            _pt.report(current_user.id, phase="suggest",
                       step_th="สร้าง Suggestions", step_en="Generating suggestions")
            await generate_suggestions(db, current_user.id)

            # v7.1 — Duplicate detection หลัง organize เสร็จ
            duplicates_found: list = []
            new_file_ids = result.get("file_ids") or []
            if new_file_ids:
                _pt.report(current_user.id, phase="duplicates",
                           step_th="ตรวจหาไฟล์ซ้ำ", step_en="Detecting duplicates")
                try:
                    duplicates_found = await detect_duplicates_for_batch(
                        db, current_user.id, new_file_ids,
                    )
                except Exception as e:
                    logger.warning(f"Duplicate detection failed post-organize: {e}")

            _pt.done(current_user.id,
                     step_th=f"จัดระเบียบสำเร็จ {result.get('count', 0)} ไฟล์",
                     step_en=f"Organized {result.get('count', 0)} files")
            return {
                "status": "ok",
                "message": f"จัดระเบียบไฟล์ใหม่ {result.get('count', 0)} ไฟล์เรียบร้อย",
                "new_files": result.get("count", 0),
                "graph": graph_result,
                "duplicates_found": duplicates_found,
            }
        except HTTPException:
            raise  # quota/auth ที่ raise ภายในไม่ควรเปลี่ยน status code
        except Exception as e:
            # v10.0.8 — log full traceback + return structured error ที่ frontend อ่านได้
            # เดิม: detail=str(e) → frontend หา .new_files ไม่เจอ → toast "(undefined ไฟล์)"
            logger.exception("Organize new files failed for user %s: %s", current_user.id[:8], e)
            _pt.error(current_user.id, f"จัดระเบียบล้มเหลว: {str(e)[:200]}")
            raise HTTPException(status_code=500, detail={"error": {
                "code": "ORGANIZE_FAILED",
                "message": f"จัดระเบียบล้มเหลว: {type(e).__name__}: {str(e)[:200]}",
            }})
    finally:
        await _end_organize(current_user.id)


@app.get("/api/organize-status")
async def organize_status(current_user: User = Depends(get_current_user)):
    """v10.0.3 — live status of /api/organize-new pipeline for current user.

    Frontend polls this every 2s while loading overlay is visible. Returns
    `running: false` when pipeline finished (frontend stops polling).
    """
    from . import progress_tracker as _pt
    snapshot = _pt.get(current_user.id)
    if snapshot is None:
        return {"running": False, "snapshot": None}
    return {
        "running": snapshot.get("phase") not in ("done", "error"),
        "snapshot": snapshot,
    }


@app.get("/api/files")
async def list_files(
    kind: str = Query("all", regex="^(all|processed|vault)$"),
    include_deleted_in_drive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all files for the user.

    v9.1.0: support `?kind=` filter:
        - "all" (default) — return both processed + vault
        - "processed" — only file_kind="processed" (AI pipeline files)
        - "vault" — only file_kind="vault_only" (raw storage, ext not supported)

    v9.3.5.5 (F16): default ซ่อน processing_status='deleted_in_drive' (ghost rows)
        - ไฟล์ที่ user ลบใน Drive UI โดยตรง · sync mark cache row เป็น ghost
        - Frontend ปกติไม่ควรเห็น · admin/debug ใช้ ?include_deleted_in_drive=true
    """
    query = select(File).where(File.user_id == current_user.id)
    if not include_deleted_in_drive:
        query = query.where(File.processing_status != "deleted_in_drive")
    if kind == "processed":
        query = query.where(File.file_kind == "processed")
    elif kind == "vault":
        query = query.where(File.file_kind == "vault_only")
    query = query.options(selectinload(File.insight), selectinload(File.summary)).order_by(File.uploaded_at.desc())
    result = await db.execute(query)
    files = result.scalars().all()
    return {"files": [_serialize_file(f) for f in files]}


@app.get("/api/clusters")
async def list_clusters(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all clusters with their files."""
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == current_user.id)
    )
    clusters = clusters_result.scalars().all()

    files_result = await db.execute(
        select(File).where(File.user_id == current_user.id)
        .options(
            selectinload(File.insight),
            selectinload(File.summary),
            selectinload(File.cluster_maps)
        )
    )
    files = files_result.scalars().all()

    # Get context packs for each cluster
    packs_result = await db.execute(
        select(ContextPack).where(ContextPack.user_id == current_user.id)
    )
    all_packs = packs_result.scalars().all()

    cluster_list = []
    for c in clusters:
        cluster_files = []
        for f in files:
            for cm in f.cluster_maps:
                if cm.cluster_id == c.id:
                    cluster_files.append(_serialize_file(f))
                    break

        # Find packs derived from this cluster
        derived_packs = []
        for p in all_packs:
            source_cluster_ids = json.loads(p.source_cluster_ids) if p.source_cluster_ids else []
            if c.id in source_cluster_ids:
                derived_packs.append({
                    "id": p.id,
                    "type": p.type,
                    "title": p.title
                })

        cluster_list.append({
            "id": c.id,
            "title": c.title,
            "summary": c.summary,
            "file_count": len(cluster_files),
            "files": cluster_files,
            "derived_packs": derived_packs
        })

    return {
        "clusters": cluster_list,
        "total_clusters": len(cluster_list),
        "total_files": len(files),
        "total_ready": sum(1 for f in files if f.processing_status == "ready")
    }


class ClusterUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None

@app.put("/api/clusters/{cluster_id}")
async def update_cluster(cluster_id: str, req: ClusterUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update a cluster title or summary."""
    result = await db.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.user_id == current_user.id)
    )
    cluster = result.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    if req.title is not None:
        cluster.title = req.title
    if req.summary is not None:
        cluster.summary = req.summary
    await db.commit()
    return {"status": "ok", "id": cluster_id, "title": cluster.title, "summary": cluster.summary}


@app.get("/api/summary/{file_id}")
async def get_summary(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get the full markdown summary for a file."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
        .options(selectinload(File.summary), selectinload(File.insight), selectinload(File.cluster_maps))
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # v5.9.3 — locked file check
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค — อัปเกรดเพื่อดูสรุปไฟล์ที่ล็อค")

    if not file.summary:
        raise HTTPException(status_code=404, detail="Summary not yet generated")

    # Find cluster name
    cluster_title = "Unclustered"
    if file.cluster_maps:
        for cm in file.cluster_maps:
            cluster_result = await db.execute(select(Cluster).where(Cluster.id == cm.cluster_id))
            cluster = cluster_result.scalar_one_or_none()
            if cluster:
                cluster_title = cluster.title
                break

    return {
        "file_id": file.id,
        "filename": file.filename,
        "filetype": file.filetype,
        "cluster": cluster_title,
        "importance_score": file.insight.importance_score if file.insight else 50,
        "importance_label": file.insight.importance_label if file.insight else "medium",
        "is_primary": file.insight.is_primary_candidate if file.insight else False,
        "summary_text": file.summary.summary_text,
        "key_topics": json.loads(file.summary.key_topics) if file.summary.key_topics else [],
        "key_facts": json.loads(file.summary.key_facts) if file.summary.key_facts else [],
        "why_important": file.summary.why_important,
        "suggested_usage": file.summary.suggested_usage
    }


@app.get("/api/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    offset: int = Query(0, ge=0, description="Character offset to start from"),
    limit: int = Query(0, ge=0, description="Max characters to return (0 = all)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file extracted text content — v5.2 with pagination support.
    
    - offset=0, limit=0: returns full text (backward-compatible)
    - offset=0, limit=5000: returns first 5000 chars
    - offset=5000, limit=5000: returns chars 5000-10000
    """
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # v5.9.3 — locked file check (locked = เกิน quota ของ plan)
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค (เกินโควต้าแพลน) — ติดต่อแอดมินเพื่อปลดล็อก")
    
    text = file.extracted_text or ""
    total = len(text)
    
    if limit > 0:
        chunk = text[offset:offset + limit]
        has_more = (offset + limit) < total
    else:
        chunk = text[offset:] if offset > 0 else text
        has_more = False
    
    return {
        "file_id": file.id,
        "filename": file.filename,
        "filetype": file.filetype,
        "text": chunk,
        "total_length": total,
        "offset": offset,
        "returned_length": len(chunk),
        "has_more": has_more,
        "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else ""
    }


@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """v5.2 — Download original raw file (PDF, DOCX, TXT, MD)."""
    # v5.9.3 — Export quota check
    limit_err = await check_export_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # v5.9.3 — locked file check
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค — อัปเกรดเพื่อดาวน์โหลดไฟล์ที่ล็อค")
    
    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail="Original file not available on server")
    
    # Log export usage
    await log_usage(db, current_user.id, "export")
    await db.commit()

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
    }
    media_type = media_types.get(file.filetype, "application/octet-stream")
    
    return FileResponse(
        path=file.raw_path,
        filename=file.filename,
        media_type=media_type,
    )


# ─── SIGNED TEMPORARY LINKS (for MCP / AI access) ───

from .shared_links import generate_share_token, get_share_link, build_share_url


@app.post("/api/files/{file_id}/share")
async def create_share_link(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a temporary public link for a file (30 min expiry).
    
    Use this to generate a URL that AI clients can access without authentication.
    """
    # v5.9.3 — Export quota check
    limit_err = await check_export_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # v5.9.3 — locked file check (PRD section 17.2 — locked files cannot be exported)
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค — อัปเกรดเพื่อแชร์ลิงก์ไฟล์ที่ล็อค")

    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail="Original file not available")

    # Log export usage
    await log_usage(db, current_user.id, "export")
    await db.commit()

    token = generate_share_token(file.id, current_user.id, file.filename)
    url = build_share_url(token)
    
    return {
        "url": url,
        "token": token,
        "filename": file.filename,
        "expires_in": "30 minutes",
    }


@app.get("/api/shared/{token}")
async def download_shared_file(token: str, db: AsyncSession = Depends(get_db)):
    """Download a file via temporary shared link — NO authentication required.
    
    AI clients (ChatGPT, Claude) can access this URL directly.
    """
    link = get_share_link(token)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found or expired")
    
    result = await db.execute(
        select(File).where(File.id == link["file_id"], File.user_id == link["user_id"])
    )
    file = result.scalar_one_or_none()
    if not file or not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail="File no longer available")
    
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
    }
    media_type = media_types.get(file.filetype, "application/octet-stream")
    
    return FileResponse(
        path=file.raw_path,
        filename=file.filename,
        media_type=media_type,
    )


# ─── v7.6.0 — Universal Signed Download URLs ───
# Stateless JWT-signed download endpoint — replaces in-memory shared_links pattern.
# ใช้กับ MCP get_file_link, future LINE/Telegram bot file delivery, web sharing.
# BYOS-aware: route ผ่าน storage_router.fetch_file_bytes() อัตโนมัติ
@app.get("/d/{token}")
async def signed_download(token: str, db: AsyncSession = Depends(get_db)):
    """Universal signed download endpoint — JWT-verified, BYOS-aware.

    Errors:
        401 INVALID_TOKEN — JWT decode fail / wrong scope / missing fields
        403 WRONG_USER — file.user_id ≠ token.user_id (cross-user attack)
        404 FILE_NOT_FOUND — file deleted after token signed
        410 LINK_EXPIRED — exp passed
        503 STORAGE_UNAVAILABLE — BYOS Drive read fail
    """
    from .signed_urls import verify_download_token, DownloadTokenError
    from .storage_router import fetch_file_bytes

    try:
        payload = verify_download_token(token)
    except DownloadTokenError as e:
        if e.code == "LINK_EXPIRED":
            raise HTTPException(
                status_code=410,
                detail={"error": {"code": e.code, "message": e.message}},
            )
        # INVALID_TOKEN
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": e.code, "message": e.message}},
        )

    file_id = payload["file_id"]
    user_id = payload["user_id"]

    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}},
        )

    # Cross-user check — token user must match file owner
    if file.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "WRONG_USER", "message": "ไม่มีสิทธิ์เข้าถึงไฟล์นี้"}},
        )

    # Read bytes — storage_router auto-routes managed (disk) vs BYOS (Drive)
    try:
        content = await fetch_file_bytes(file, db)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไฟล์หายจาก storage"}},
        )
    except Exception as e:
        logger.error(f"Storage read failed for /d/ file={file_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "STORAGE_UNAVAILABLE", "message": "ดาวน์โหลดไม่สำเร็จ"}},
        )

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
    }
    media_type = media_types.get(file.filetype, "application/octet-stream")

    # Cache-Control: private, no-store — กัน CDN cache user files
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "Cache-Control": "private, no-store",
        },
    )


# ─── v8.0.0 — LINE Bot Webhook ───
# LINE webhook endpoint — receives events จาก LINE platform
# Signature: HMAC-SHA256(channel_secret, raw_body) ต้อง match X-Line-Signature header
# 503 ถ้า LINE_CHANNEL_SECRET ยังไม่ set (feature ปิดเงียบ)
# 401 ถ้า signature ผิด
# 200 + ack ทันที — events handled async via BackgroundTasks
@app.post("/webhook/line")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None),
):
    """LINE Messaging API webhook — receives events จาก LINE.

    Spec: https://developers.line.biz/en/reference/messaging-api/#webhook-event-objects
    """
    from .config import is_line_configured
    from .line_bot import verify_signature, handle_line_event

    if not is_line_configured():
        return JSONResponse(
            {"error": {"code": "LINE_NOT_CONFIGURED", "message": "LINE bot not configured on this server"}},
            status_code=503,
        )

    body = await request.body()
    if not verify_signature(body, x_line_signature):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "Invalid X-Line-Signature"}},
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PAYLOAD", "message": "Body is not valid JSON"}},
        )

    events = payload.get("events", [])
    for event in events:
        # Background tasks — ack ทันที, handler ทำงาน async
        background_tasks.add_task(handle_line_event, event)

    return {"status": "ok", "events_received": len(events)}


# ─── v8.0.0 Phase H — Admin: LINE push quota ───
@app.get("/api/line/admin/quota")
async def line_quota_status(
    current_admin: User = Depends(require_admin),
):
    """Admin: get LINE push quota usage for current month.

    v10.0.12 — gated to admin only (was any-authenticated). Exposes system-wide
    quota state; regular users shouldn't see internal capacity metrics.

    Returns: pushes_used / limit / percent / remaining / exceeded.
    """
    from . import line_quota
    return line_quota.get_current_usage()


# ═══════════════════════════════════════════
# v8.2.0 — Admin System endpoints
# ═══════════════════════════════════════════
# Pattern: ทุก endpoint ใช้ Depends(require_admin) — ถ้า user ไม่ใช่ admin → 403 NOT_ADMIN
# Mutation endpoints ใช้ Pydantic models (AdminChangePlanRequest / AdminResetPasswordRequest /
# AdminToggleRequest) ที่ define ไว้ตอนต้นไฟล์

@app.get("/api/admin/me")
async def api_admin_me(current_admin: User = Depends(require_admin)):
    """Verify admin role + return identity. Frontend ใช้เป็น auth guard ก่อน render /admin."""
    from .plan_limits import _effective_plan
    return {
        "id": current_admin.id,
        "email": current_admin.email,
        "name": current_admin.name,
        "is_admin": bool(current_admin.is_admin),
        "effective_plan": _effective_plan(current_admin),
    }


@app.get("/api/admin/stats")
async def api_admin_stats(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard aggregate stats — users / files / Stripe / LINE / system."""
    return await _admin_mod.get_admin_stats(db)


@app.get("/api/admin/users")
async def api_admin_list_users(
    q: str | None = Query(None, description="Search by email substring"),
    plan: str | None = Query(None, pattern="^(free|starter|admin|inactive)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated user list with optional search + filter."""
    return await _admin_mod.list_users(db, q, plan, page, page_size)


@app.get("/api/admin/users/{user_id}")
async def api_admin_user_detail(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """User detail + usage + Stripe + downgrade-block info."""
    return await _admin_mod.get_user_detail(db, user_id)


@app.put("/api/admin/users/{user_id}/plan")
async def api_admin_change_plan(
    user_id: str,
    body: AdminChangePlanRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change user plan (free/starter/admin) with Stripe-aware guard."""
    return await _admin_mod.change_user_plan(db, current_admin, user_id, body.plan, body.reason)


@app.post("/api/admin/users/{user_id}/reset-password")
async def api_admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set new password for user — return ครั้งเดียว, ไม่ส่ง email."""
    return await _admin_mod.reset_user_password(db, current_admin, user_id, body.new_password, body.reason)


@app.put("/api/admin/users/{user_id}/active")
async def api_admin_toggle_active(
    user_id: str,
    body: AdminToggleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle is_active flag (deactivate/reactivate)."""
    return await _admin_mod.set_user_active(db, current_admin, user_id, body.value, body.reason)


@app.put("/api/admin/users/{user_id}/admin")
async def api_admin_toggle_admin(
    user_id: str,
    body: AdminToggleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle is_admin flag (promote/demote)."""
    return await _admin_mod.set_user_admin(db, current_admin, user_id, body.value, body.reason)


@app.post("/api/admin/users/{user_id}/view-password")
async def api_admin_view_password(
    user_id: str,
    body: AdminToggleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """⚠️ v10.0.x · TEST PHASE ONLY · View user plaintext password.

    Body: `{ value: false (ignored), reason: str }` · reused AdminToggleRequest schema
    เพื่อความ consistent · `value` ไม่ใช้ แต่ schema เดิม require · ใส่ false ได้

    Returns: `{ status, user_id, email, password_available, password, hint }`
    - password_available=false → user สมัครก่อน feature นี้ · ต้อง reset ก่อน
    - audit log ทุก view (event_type='admin_viewed_password')

    Gated: env ALLOW_ADMIN_VIEW_PASSWORD=true · 403 ถ้า disabled
    """
    return await _admin_mod.get_user_password(db, current_admin, user_id, body.reason)


@app.delete("/api/admin/users/{user_id}")
async def api_admin_delete_user(
    user_id: str,
    body: AdminDeleteUserRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """v10.0.x — Hard-delete user + cascade ทุก data ของเขา (irreversible).

    Body params:
      - `confirm_email`: ต้องตรงกับ email ของ target user (double-confirm)
      - `reason`: เหตุผลที่ลบ (audit log ถาวร)

    Guards: CANNOT_DELETE_SELF · LAST_ADMIN_GUARD · CONFIRM_EMAIL_MISMATCH
    Cascade: files (+ disk) · clusters · graph nodes/edges · packs · chats ·
             contexts · personality history · tokens · Drive · profile · etc.
    Audit logs: KEEP (historical trail)
    """
    # Pre-fetch target เพื่อ verify confirm_email
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})
    if (target.email or "").lower() != body.confirm_email:
        raise HTTPException(400, detail={"error": {
            "code": "CONFIRM_EMAIL_MISMATCH",
            "message": "confirm_email ไม่ตรงกับ email ของ user ที่จะลบ — ยกเลิกการลบเพื่อความปลอดภัย",
        }})
    return await _admin_mod.delete_user(db, current_admin, user_id, body.reason)


@app.get("/api/admin/audit-logs")
async def api_admin_audit_logs(
    event_type: str | None = Query(None),
    user_id: str | None = Query(None),
    triggered_by: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit log with optional filters."""
    return await _admin_mod.list_audit_logs(db, event_type, user_id, triggered_by, limit, offset)


@app.get("/api/admin/extraction-stats")
async def api_admin_extraction_stats(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """v10.0.0 — Ingestion pipeline health/config readout.

    Shows which processors are configured + per-format counts of files
    currently in the system. Used by the admin panel to verify
    LlamaParse rollout + monitor extraction status distribution.
    """
    from .config import (
        is_llamaparse_configured, USE_LLAMAPARSE_FOR_PDF,
        LLAMA_PARSE_MODE, LOCAL_EXTRACT_MAX_MB,
        LOCAL_EXTRACT_CONCURRENCY, is_byos_configured,
    )
    from sqlalchemy import func as _func

    # File counts per filetype + extraction_status
    rows = (await db.execute(
        select(File.filetype, File.extraction_status, _func.count(File.id))
        .group_by(File.filetype, File.extraction_status)
    )).all()
    by_type: dict[str, dict[str, int]] = {}
    for ft, status, count in rows:
        ft = ft or "unknown"
        by_type.setdefault(ft, {})[status or "unknown"] = count

    return {
        "config": {
            "llamaparse_enabled": is_llamaparse_configured(),
            "llamaparse_flag": USE_LLAMAPARSE_FOR_PDF,
            "llamaparse_mode": LLAMA_PARSE_MODE,
            "local_extract_max_mb": LOCAL_EXTRACT_MAX_MB,
            "local_extract_concurrency": LOCAL_EXTRACT_CONCURRENCY,
            "byos_configured": is_byos_configured(),
        },
        "files_by_type": by_type,
    }


# ═══════════════════════════════════════════════════════════════
# v10.0.x — Orphan cleanup admin endpoint
# ═══════════════════════════════════════════════════════════════
# Sweeps orphan records ที่เกิดก่อนมี cleanup helpers (v10.0.x ก่อนหน้านี้).
# หลังจาก v10.0.x ทุก DELETE/skip-duplicates clean ครบ → endpoint นี้ไว้ใช้ครั้งเดียวเพื่อ
# ล้างของเก่า (หรือใช้กู้สถานการณ์ถ้ามี orphan โผล่จาก code path ที่เราไม่เห็น)


async def _sweep_orphans_for_user(
    db: AsyncSession,
    user_id: str,
    dry_run: bool = False,
) -> dict:
    """Bulk orphan cleanup สำหรับ user เดียว.

    ต่าง _cleanup_file_references ตรงที่ตัวนั้นทำงาน PER-FILE ระหว่าง DELETE (มี file_id).
    ตัวนี้สแกนหา orphan ที่ค้างอยู่แล้ว (file row หายไปนานแล้ว · cleanup ตอน DELETE ไม่ทำ).

    dry_run=True → return counts โดยไม่ลบจริง · ใช้ตรวจก่อน execute
    """
    from sqlalchemy import delete as sql_delete, or_, text
    from .database import ChatQuery, ContextInjectionLog

    stats = {
        "orphan_source_file_nodes_removed": 0,
        "orphan_graph_edges_removed": 0,
        "orphan_suggestions_removed": 0,
        "empty_clusters_removed": 0,
        "empty_cluster_nodes_removed": 0,
        "packs_updated": 0,
        "chats_updated": 0,
        "logs_updated": 0,
    }

    # ─── 1. Orphan source_file graph nodes (file row หายแล้ว) ───
    orphan_node_res = await db.execute(text("""
        SELECT gn.id FROM graph_nodes gn
        LEFT JOIN files f ON f.id = gn.object_id
        WHERE gn.user_id = :uid
        AND gn.object_type = 'source_file'
        AND f.id IS NULL
    """), {"uid": user_id})
    orphan_node_ids = [r[0] for r in orphan_node_res.all()]
    stats["orphan_source_file_nodes_removed"] = len(orphan_node_ids)

    if orphan_node_ids and not dry_run:
        e_del = await db.execute(sql_delete(GraphEdge).where(
            GraphEdge.user_id == user_id,
            or_(
                GraphEdge.source_node_id.in_(orphan_node_ids),
                GraphEdge.target_node_id.in_(orphan_node_ids),
            )
        ))
        stats["orphan_graph_edges_removed"] = e_del.rowcount or 0
        s_del = await db.execute(sql_delete(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            or_(
                SuggestedRelation.source_node_id.in_(orphan_node_ids),
                SuggestedRelation.target_node_id.in_(orphan_node_ids),
            )
        ))
        stats["orphan_suggestions_removed"] = s_del.rowcount or 0
        await db.execute(sql_delete(GraphNode).where(GraphNode.id.in_(orphan_node_ids)))

    # ─── 2. Empty clusters + their graph nodes ───
    empty_res = await db.execute(text("""
        SELECT c.id FROM clusters c
        WHERE c.user_id = :uid
        AND NOT EXISTS (SELECT 1 FROM file_cluster_map fcm WHERE fcm.cluster_id = c.id)
    """), {"uid": user_id})
    empty_ids = [r[0] for r in empty_res.all()]
    stats["empty_clusters_removed"] = len(empty_ids)

    if empty_ids and not dry_run:
        # cluster graph nodes + their edges/suggestions
        cl_node_res = await db.execute(
            select(GraphNode.id).where(
                GraphNode.user_id == user_id,
                GraphNode.object_type == "cluster",
                GraphNode.object_id.in_(empty_ids),
            )
        )
        cl_node_ids = [r[0] for r in cl_node_res.all()]
        stats["empty_cluster_nodes_removed"] = len(cl_node_ids)
        if cl_node_ids:
            await db.execute(sql_delete(GraphEdge).where(
                GraphEdge.user_id == user_id,
                or_(
                    GraphEdge.source_node_id.in_(cl_node_ids),
                    GraphEdge.target_node_id.in_(cl_node_ids),
                )
            ))
            await db.execute(sql_delete(SuggestedRelation).where(
                SuggestedRelation.user_id == user_id,
                or_(
                    SuggestedRelation.source_node_id.in_(cl_node_ids),
                    SuggestedRelation.target_node_id.in_(cl_node_ids),
                )
            ))
            await db.execute(sql_delete(GraphNode).where(GraphNode.id.in_(cl_node_ids)))
        await db.execute(sql_delete(Cluster).where(Cluster.id.in_(empty_ids)))

    # ─── 3. Stale file_id ใน JSON arrays (ContextPack / ChatQuery / ContextInjectionLog) ───
    valid_ids_res = await db.execute(
        select(File.id).where(File.user_id == user_id)
    )
    valid_ids = {r[0] for r in valid_ids_res.all()}

    # ContextPack.source_file_ids
    packs = await db.execute(
        select(ContextPack).where(ContextPack.user_id == user_id)
    )
    for p in packs.scalars().all():
        try:
            ids = json.loads(p.source_file_ids or "[]")
            clean = [i for i in ids if i in valid_ids]
            if len(clean) != len(ids):
                stats["packs_updated"] += 1
                if not dry_run:
                    p.source_file_ids = json.dumps(clean)
        except (ValueError, TypeError):
            pass

    # ChatQuery.selected_file_ids
    chats = await db.execute(
        select(ChatQuery).where(ChatQuery.user_id == user_id)
    )
    for c in chats.scalars().all():
        try:
            ids = json.loads(c.selected_file_ids or "[]")
            clean = [i for i in ids if i in valid_ids]
            if len(clean) != len(ids):
                stats["chats_updated"] += 1
                if not dry_run:
                    c.selected_file_ids = json.dumps(clean)
        except (ValueError, TypeError):
            pass

    # ContextInjectionLog.file_ids (JOIN กับ chat_queries เพื่อ filter by user)
    logs_res = await db.execute(
        select(ContextInjectionLog).join(
            ChatQuery, ChatQuery.id == ContextInjectionLog.chat_query_id
        ).where(ChatQuery.user_id == user_id)
    )
    for l in logs_res.scalars().all():
        try:
            ids = json.loads(l.file_ids or "[]")
            clean = [i for i in ids if i in valid_ids]
            if len(clean) != len(ids):
                stats["logs_updated"] += 1
                if not dry_run:
                    l.file_ids = json.dumps(clean)
        except (ValueError, TypeError):
            pass

    return stats


def _sweep_orphan_md_files(valid_md_paths: set[str], dry_run: bool = False) -> dict:
    """ลบไฟล์ .md ใน SUMMARIES_DIR ที่ไม่มี DB row reference.

    valid_md_paths: set ของ md_path values ใน file_summaries (preload จาก caller)
    dry_run: ตรวจอย่างเดียว ไม่ลบ
    """
    from .config import SUMMARIES_DIR
    stats = {"orphan_md_found": 0, "orphan_md_removed": 0, "remove_errors": 0}
    if not os.path.isdir(SUMMARIES_DIR):
        return stats
    valid_basenames = {os.path.basename(p) for p in valid_md_paths if p}
    for fn in os.listdir(SUMMARIES_DIR):
        if not fn.endswith(".md"):
            continue
        if fn in valid_basenames:
            continue
        stats["orphan_md_found"] += 1
        if not dry_run:
            try:
                os.remove(os.path.join(SUMMARIES_DIR, fn))
                stats["orphan_md_removed"] += 1
            except OSError as e:
                logger.warning("sweep_orphan_md: remove %s failed: %s", fn, e)
                stats["remove_errors"] += 1
    return stats


@app.post("/api/admin/cleanup-orphans")
async def api_admin_cleanup_orphans(
    dry_run: bool = Query(True, description="If true, count only · false = actually delete"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """v10.0.x — Admin sweep ของ orphan records ที่ค้างจาก pre-v10.0.x deletes.

    Scans ทุก user · ลบ:
      - GraphNode (object_type='source_file', object_id ไม่มีใน files) + edges/suggestions
      - Empty Cluster (ไม่มี file_cluster_map เหลือ) + cluster graph nodes/edges
      - file_id ใน JSON arrays ของ ContextPack/ChatQuery/ContextInjectionLog
      - orphan .md files ใน SUMMARIES_DIR (ไม่มี file_summaries row)

    **Default dry_run=true** — เรียกครั้งแรกได้สถิติว่าจะลบเท่าไหร่ · ไม่กระทบ data
    ส่ง `?dry_run=false` เมื่อพร้อมจะลบจริง

    Idempotent: รัน 2 รอบ → ครั้งที่ 2 ทุก count = 0
    """
    import time as _time
    start = _time.monotonic()

    # ทุก user
    users_res = await db.execute(select(User.id))
    user_ids = [r[0] for r in users_res.all()]

    per_user_with_findings = 0
    totals = {
        "orphan_source_file_nodes_removed": 0,
        "orphan_graph_edges_removed": 0,
        "orphan_suggestions_removed": 0,
        "empty_clusters_removed": 0,
        "empty_cluster_nodes_removed": 0,
        "packs_updated": 0,
        "chats_updated": 0,
        "logs_updated": 0,
    }

    for uid in user_ids:
        try:
            stats = await _sweep_orphans_for_user(db, uid, dry_run=dry_run)
        except Exception as e:
            logger.warning("cleanup_orphans: user %s sweep failed: %s", uid[:8], e)
            continue
        if any(v > 0 for v in stats.values()):
            per_user_with_findings += 1
        for k, v in stats.items():
            if k in totals:
                totals[k] += v

    # Disk sweep (global · ไม่ผ่าน user)
    md_paths_res = await db.execute(
        select(FileSummary.md_path).where(FileSummary.md_path != "")
    )
    valid_md_paths = {r[0] for r in md_paths_res.all() if r[0]}
    disk_stats = _sweep_orphan_md_files(valid_md_paths, dry_run=dry_run)

    if not dry_run:
        await db.commit()

    duration_ms = int((_time.monotonic() - start) * 1000)

    return {
        "status": "ok",
        "dry_run": dry_run,
        "users_scanned": len(user_ids),
        "users_with_orphans": per_user_with_findings,
        "totals": totals,
        "disk": disk_stats,
        "duration_ms": duration_ms,
    }


# ─── v8.0.0 — LINE Bot UI endpoints (Profile section) ───
@app.get("/api/line/status")
async def line_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return LINE bot connection status for current PDB user.

    Used by /app profile modal to render link/unlink UI.
    """
    from .config import is_line_configured, LINE_BOT_BASIC_ID
    from .database import LineUser

    feature_available = is_line_configured()
    if not feature_available:
        return {
            "feature_available": False,
            "linked": False,
        }

    # Find LineUser row for this PDB user (must have line_user_id != NULL = actually linked,
    # not just nonce-pending)
    result = await db.execute(
        select(LineUser).where(
            LineUser.pdb_user_id == current_user.id,
            LineUser.line_user_id.isnot(None),
            LineUser.unlinked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()

    bot_url = None
    if LINE_BOT_BASIC_ID:
        # Format @PDBBot → https://line.me/R/ti/p/%40PDBBot
        bid = LINE_BOT_BASIC_ID.lstrip("@")
        bot_url = f"https://line.me/R/ti/p/%40{bid}"

    if not row:
        return {
            "feature_available": True,
            "linked": False,
            "bot_basic_id": LINE_BOT_BASIC_ID or None,
            "bot_url": bot_url,
        }

    return {
        "feature_available": True,
        "linked": True,
        "line_user_id": row.line_user_id,
        "line_display_name": row.line_display_name,
        "linked_at": row.linked_at.isoformat() if row.linked_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "bot_basic_id": LINE_BOT_BASIC_ID or None,
        "bot_url": bot_url,
    }


@app.post("/api/line/connect")
async def line_connect(
    current_user: User = Depends(get_current_user),
):
    """Start LINE Login OAuth flow — returns redirect URL.

    `current_user` parameter required เป็น auth gate ผ่าน Depends — Phase E
    จะใช้ user.id ใน state nonce. db dependency จะ inject กลับตอน Phase E
    ตอนต้อง insert/update LineUser row.
    """
    from .config import is_line_login_configured, APP_BASE_URL
    if not is_line_login_configured():
        return JSONResponse(
            {"error": {"code": "LINE_LOGIN_NOT_CONFIGURED",
                       "message": "LINE Login not configured on this server"}},
            status_code=503,
        )

    # Phase E will implement full OAuth flow with state + PKCE.
    # For Phase D, return a placeholder pointing to auth-line.html landing
    # which Phase E will turn into a real OAuth start.
    return {
        "redirect_url": f"{APP_BASE_URL.rstrip('/')}/auth/line",
        "user_id": current_user.id,  # placeholder — Phase E will sign into state
    }


@app.post("/api/line/disconnect")
async def line_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-unlink LINE account from current PDB user.

    Sets unlinked_at timestamp instead of deleting row (preserve history).
    Future re-link → new row (or reuse if same line_user_id).
    """
    from datetime import datetime as _dt
    from .database import LineUser

    result = await db.execute(
        select(LineUser).where(
            LineUser.pdb_user_id == current_user.id,
            LineUser.line_user_id.isnot(None),
            LineUser.unlinked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return JSONResponse(
            {"error": {"code": "NOT_LINKED", "message": "No linked LINE account"}},
            status_code=404,
        )

    row.unlinked_at = _dt.utcnow()
    await db.commit()
    return {"status": "disconnected"}


# ─── v8.0.0 — LINE Bot account-link landing page ───
@app.get("/auth/line")
async def serve_auth_line():
    """Serve auth-line.html — landing page เมื่อ user คลิก 'เชื่อมบัญชี' จาก LINE bot."""
    return _serve_html("auth-line.html")


class LineConfirmLinkRequest(BaseModel):
    link_token: str


@app.post("/api/line/confirm-link")
async def line_confirm_link(
    body: LineConfirmLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User confirms ใน auth-line.html → server insert/update LineUser row + nonce.

    Phase D scope = skeleton:
    - Validate link_token (Phase E จะ decode JWT)
    - Insert/update LineUser row + generate nonce
    - Return redirect URL (Phase E = LINE accountLink dialog URL)

    Phase E จะ implement:
    - Decode link_token ที่ embedded LINE linkToken
    - Generate proper nonce (32 bytes urlsafe base64)
    - Build LINE accountLink URL with linkToken + nonce
    - Match nonce ใน accountLink webhook event
    """
    import secrets as _secrets
    from datetime import datetime as _dt, timedelta as _td
    from .config import is_line_configured, LINE_BOT_BASIC_ID
    from .database import LineUser

    if not is_line_configured():
        return JSONResponse(
            {"error": {"code": "LINE_NOT_CONFIGURED",
                       "message": "LINE bot not configured on this server"}},
            status_code=503,
        )

    if not body.link_token or not body.link_token.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "MISSING_LINK_TOKEN", "message": "link_token is required"}},
        )

    # v9.4.3 (C1) — Log linkToken arrival for observability ใน flyio logs
    # Note: ไม่ log token เต็มเพราะ sensitive · log ความยาว + first 6 chars พอ
    link_token_len = len(body.link_token)
    link_token_prefix = body.link_token[:6]
    logger.info(
        "line_confirm_link: user=%s linkToken_len=%d prefix=%s",
        current_user.id[:8] + "..", link_token_len, link_token_prefix,
    )

    # v9.4.2 (L11) — Generate nonce as 64 hex chars (256-bit entropy · alphanumeric-only)
    # Why: LINE Account Link spec กำหนด nonce ต้อง 10-255 ALPHANUMERIC chars เท่านั้น
    # (https://developers.line.biz/en/docs/messaging-api/linking-accounts/).
    # เดิมใช้ token_urlsafe() ที่ produce base64url → มี '-' กับ '_' → LINE reject
    # ที่ access.line.me ด้วยข้อความ "ไม่สามารถเชื่อมต่อกับ LINE ได้" ก่อนถึง webhook.
    # token_hex(32) → 64 chars จาก [0-9a-f] · alphanumeric ตาม spec · entropy พอเหลือเฟือ.
    nonce = _secrets.token_hex(32)
    nonce_expires = _dt.utcnow() + _td(minutes=10)

    # Find existing LineUser row for this PDB user (could be from previous link attempt)
    result = await db.execute(
        select(LineUser).where(LineUser.pdb_user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # v9.4.3 (B1) — log if previous nonce was already expired (defensive observability)
        # Why: ถ้า user มี row ค้างจาก attempt ก่อนหน้า · บอกใน log ว่า "stale recovery"
        # ช่วย debug case "เพื่อนต่อไม่ได้" — ดูว่า user หลุด stuck กี่รอบก่อนสำเร็จ
        if (existing.link_nonce_expires_at
                and existing.link_nonce_expires_at < _dt.utcnow()):
            logger.info(
                "line_confirm_link: stale nonce recovered for user=%s (was expired %s ago)",
                current_user.id[:8] + "..",
                _dt.utcnow() - existing.link_nonce_expires_at,
            )
        # Reuse row — update nonce + expiry, clear unlinked_at if was unlinked before
        existing.link_nonce = nonce
        existing.link_nonce_expires_at = nonce_expires
        if existing.unlinked_at:
            existing.unlinked_at = None
            existing.welcomed = False  # show welcome again on re-link
    else:
        new_row = LineUser(
            pdb_user_id=current_user.id,
            link_nonce=nonce,
            link_nonce_expires_at=nonce_expires,
            welcomed=False,
        )
        db.add(new_row)

    await db.commit()

    # v9.4.2 (L11) — URL-encode both params (defense in depth · linkToken from LINE
    # อาจมี chars ที่ต้อง encode ใน URL · nonce hex ไม่ต้อง encode แต่ encode ไว้ปลอดภัยกว่า)
    # Phase E: return real LINE accountLink dialog URL
    # link_token = LINE linkToken จาก bot follow event → /auth/line?linkToken=X
    # nonce = random hex string ที่ LINE echo back ใน accountLink webhook event
    from urllib.parse import quote as _urlquote
    redirect_url = (
        f"https://access.line.me/dialog/bot/accountLink"
        f"?linkToken={_urlquote(body.link_token, safe='')}"
        f"&nonce={_urlquote(nonce, safe='')}"
    )

    return {
        "status": "pending_link",
        "redirect_url": redirect_url,
    }


@app.post("/api/files/{file_id}/reprocess")
async def reprocess_file(
    file_id: str,
    mode: str = Query("cleanup", regex="^(cleanup|reextract)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """v5.2 / v7.5.0 — Re-extract or LLM-cleanup an existing file.

    Modes (v7.5.0):
      - mode=cleanup (default, legacy) — re-extract from raw_path + LLM Thai cleanup
      - mode=reextract — re-extract from raw_path WITHOUT LLM cleanup (faster,
        for cases like encrypted PDF that user just unlocked + re-uploaded over)

    Use cases:
    - Image-only PDFs that returned no text → cleanup or reextract
    - PDFs with broken Thai spacing → cleanup
    - Encrypted PDF user just unlocked → reextract
    - extraction_status badge says "encrypted/empty/ocr_failed" → reextract

    v7.5.0 also updates `extraction_status` based on the new extracted text.
    """
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # v5.9.3 — locked file check (PRD section 17.2 — cannot re-extract content of locked files)
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค — อัปเกรดเพื่อประมวลผลใหม่")

    # v10.0.0 -- reject reprocess while worker is mid-flight on this file.
    # Without this, user can race the worker: reprocess sets status='queued'
    # while worker still has it as 'extracting' -> when worker finishes,
    # it writes status='uploaded' which overwrites our re-queue request.
    if file.processing_status in ("queued", "extracting"):
        raise HTTPException(409, detail={"error": {
            "code": "FILE_IN_QUEUE",
            "message": "ไฟล์กำลังประมวลผลอยู่ — กดยกเลิกก่อนหรือรอให้เสร็จก่อน",
        }})

    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail="Original file not available — cannot reprocess")

    # v9.4.0 — async reprocess via queue (was inline extract in v9.3.4)
    # Reset row → 'queued' → worker pickup → re-extract → 'uploaded'
    # mode='cleanup' (LLM Thai cleanup) deferred to v9.5.0 — treat as 'reextract'
    from sqlalchemy import func

    if mode == "cleanup":
        logger.info(
            f"reprocess_file: mode=cleanup deferred to v9.5.0 — using reextract for {file_id}"
        )

    # v9.4.3 — respect MAX_RETRY (parity with /api/upload/{id}/retry)
    from .upload_worker import MAX_RETRY_ATTEMPTS
    if (file.attempt_count or 0) >= MAX_RETRY_ATTEMPTS:
        raise HTTPException(409, detail={"error": {
            "code": "NOT_RETRYABLE",
            "message": f"เกิน retry limit ({MAX_RETRY_ATTEMPTS} ครั้ง)",
        }})

    file.processing_status = "queued"
    file.extract_started_at = None
    file.extract_completed_at = None
    file.extract_error = None
    file.progress_step = None
    file.progress_pct = None
    file.queued_at = datetime.utcnow()
    # v9.4.3 — clear stale text/status (เดิมไม่ล้าง → search/summary ใช้ text เก่า)
    file.extracted_text = ""
    file.extraction_status = ""
    file.attempt_count = (file.attempt_count or 0) + 1
    await db.commit()

    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= file.queued_at,
        )
    )
    return {
        "status": "ok",
        "file_id": file.id,
        "filename": file.filename,
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
        "extraction_method": "reextract",  # v9.4.0: cleanup mode deferred
    }



class SummaryUpdateRequest(BaseModel):
    # v10.0.x — P2-7 · เพิ่ม filename field สำหรับ rename file
    # (ไม่กระทบ raw_path หรือ Drive copy · เปลี่ยนแค่ display name)
    filename: str | None = None
    summary_text: str | None = None
    key_topics: list[str] | None = None
    key_facts: list[str] | None = None
    why_important: str | None = None
    suggested_usage: str | None = None

@app.put("/api/summary/{file_id}")
async def update_summary(file_id: str, req: SummaryUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update the summary (and optionally filename) for a file."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
        .options(selectinload(File.summary))
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # v10.0.x — P2-7: filename rename ไม่ต้องมี summary (ทำได้กับไฟล์ที่ยังไม่ organize)
    if req.filename is not None:
        new_name = (req.filename or "").strip()
        if not new_name:
            raise HTTPException(400, detail={"error": {
                "code": "FILENAME_REQUIRED",
                "message": "ชื่อไฟล์ห้ามว่าง",
            }})
        if len(new_name) > 255:
            raise HTTPException(400, detail={"error": {
                "code": "FILENAME_TOO_LONG",
                "message": f"ชื่อไฟล์ยาวเกิน 255 ตัวอักษร (ปัจจุบัน {len(new_name)})",
            }})
        file.filename = new_name

    # Summary field updates ต้องมี summary row อยู่
    summary_fields_provided = any(getattr(req, f) is not None for f in
                                  ('summary_text', 'key_topics', 'key_facts', 'why_important', 'suggested_usage'))
    if summary_fields_provided:
        if not file.summary:
            raise HTTPException(status_code=404, detail="Summary not yet generated")
        if req.summary_text is not None:
            file.summary.summary_text = req.summary_text
        if req.key_topics is not None:
            file.summary.key_topics = json.dumps(req.key_topics, ensure_ascii=False)
        if req.key_facts is not None:
            file.summary.key_facts = json.dumps(req.key_facts, ensure_ascii=False)
        if req.why_important is not None:
            file.summary.why_important = req.why_important
        if req.suggested_usage is not None:
            file.summary.suggested_usage = req.suggested_usage

    await db.commit()
    return {"status": "ok", "file_id": file_id, "filename": file.filename}


@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete file — fast sync DB/disk + async Drive cleanup (v9.3.5.5).

    Why background_tasks (F6): Drive trash 60s × 3 sub-folders = 180s · เกิน Cloudflare/Fly
    timeout (~100s) → 504 ยิง user. Now: API ตอบ ~200ms · cleanup รัน background.

    drive_cleanup field บอก client ผลของ Drive cleanup:
      - "scheduled"            — BYOS + drive_uploaded · running in background
      - "skipped:drive_picked" — ไฟล์ user import จาก Picker · ห้าม trash (F5)
      - "skipped:managed"      — managed mode · ไม่มี Drive copy
      - "skipped:no_drive_id"  — file ไม่เคยขึ้น Drive (drive_file_id NULL)
    """
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # v9.4.8 — guard DELETE-while-extracting race
    # Worker อาจกำลังอ่าน raw_path → os.remove() บน Linux สำเร็จ (worker ยัง read fd ได้)
    # แต่ DB row หาย → worker UPDATE rowcount=0 + vector index inconsistent.
    # บังคับให้ user กด Cancel ก่อน (/api/upload/{id}/cancel) ในสถานะ queue
    if file.processing_status in ("queued", "extracting"):
        raise HTTPException(409, detail={"error": {
            "code": "FILE_IN_QUEUE",
            "message": "ไฟล์อยู่ในคิวประมวลผล — กดยกเลิกก่อนลบ",
        }})

    # Capture for background task ก่อน db.delete (ORM ออบเจกต์ detach หลัง commit)
    file_storage_source = file.storage_source
    file_drive_file_id = file.drive_file_id
    file_id_for_bg = file.id

    # ── v10.0.x — capture FileSummary.md_path BEFORE cascade ลบ DB row ──
    # ต้องใช้ก่อน db.delete(file) เพื่อให้ helper รู้ว่าต้องลบไฟล์ .md ตัวไหนบน disk
    # ใช้ explicit select แทน file.summary lazy access (lazy ไม่ทำงานใน async session)
    summary_row = (await db.execute(
        select(FileSummary.md_path).where(FileSummary.file_id == file.id)
    )).scalar_one_or_none()
    summary_md_path = summary_row or None

    # 1. Disk: best-effort ลบ raw file
    # v10.0.8 — purge LlamaParse cache ก่อนลบไฟล์ (ต้อง hash bytes ของ raw_path)
    # มิฉะนั้น extracted markdown จาก LlamaParse จะเหลือใน .llamaparse_cache/<sha>.md
    if file.raw_path and os.path.exists(file.raw_path):
        try:
            from .processors.llamaparse import purge_cache_for_file
            n = purge_cache_for_file(file.raw_path)
            if n:
                logger.info("delete_file %s: purged %d llamaparse cache entries", file_id, n)
        except Exception as e:
            logger.warning("delete_file: llamaparse cache purge failed for %s: %s", file_id, e)
        try:
            os.remove(file.raw_path)
        except OSError as e:
            logger.warning(f"delete_file: failed to remove raw_path {file.raw_path}: {e}")

    # 2. Vector index: best-effort remove (sync · เร็ว · in-process)
    try:
        from . import vector_search as _vs
        _vs.remove_file(file.id, user_id=current_user.id)
    except Exception as e:
        logger.warning(
            f"delete_file: vector_search remove failed for {file_id}: {e}"
        )

    # 3. v10.0.x — Cleanup orphan references ที่ FK cascade ไม่ครอบคลุม
    #    (graph nodes/edges/suggestions, summary .md disk, JSON arrays)
    #    เรียก BEFORE db.delete(file) เพื่อให้ file.id ยัง resolve ได้
    try:
        cleanup_stats = await _cleanup_file_references(
            db, current_user.id, file.id, summary_md_path
        )
        logger.info(
            "delete_file %s: orphan cleanup stats=%s", file_id, cleanup_stats
        )
    except Exception as e:
        # Best-effort · ห้าม raise · DELETE primary success criterion = file row gone
        logger.warning(
            "delete_file: orphan cleanup failed for %s: %s", file_id, e
        )

    # 4. DB cascade (FK ลบ FileInsight + FileSummary + FileClusterMap อัตโนมัติ)
    await db.delete(file)
    await db.commit()

    # 5. v10.0.x — Empty cluster cleanup (หลัง commit · เพราะ FileClusterMap cascade fired แล้ว)
    try:
        empty_cluster_count = await _cleanup_empty_clusters(db, current_user.id)
        if empty_cluster_count:
            await db.commit()
            logger.info(
                "delete_file %s: removed %d empty clusters", file_id, empty_cluster_count
            )
    except Exception as e:
        logger.warning(
            "delete_file: empty cluster cleanup failed for %s: %s", file_id, e
        )

    # 4. Drive cleanup (async background · ไม่ block response)
    from .storage_router import _should_trash_drive_file
    drive_cleanup = "skipped:no_drive_id"
    if file_drive_file_id:
        if _should_trash_drive_file(file_storage_source):
            background_tasks.add_task(
                _cleanup_drive_for_deleted_file,
                current_user.id,
                file_id_for_bg,
                file_drive_file_id,
                file_storage_source,
            )
            drive_cleanup = "scheduled"
        elif file_storage_source == "drive_picked":
            drive_cleanup = "skipped:drive_picked"
            logger.info(
                "delete_file: drive_picked file %s unlinked · external preserved",
                file_id,
            )
        else:
            drive_cleanup = "skipped:managed"

    return {"status": "ok", "drive_cleanup": drive_cleanup}


@app.post("/api/files/cleanup-ghosts")
async def cleanup_ghost_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v10.0.16 — Two-phase orphan purge: ghost file rows + derived entity nodes.

    Phase 1 (v10.0.15): drive-side ghosts
      drive_sync marks File rows as processing_status='deleted_in_drive' when it
      detects user deleted the file from Drive UI directly. /api/files hides
      these ghosts (per F16) but graph entities tied to them lingered.

    Phase 2 (v10.0.16): orphan derived nodes
      AI extracts note/entity/tag/concept/person nodes from files. Normal file
      delete (_cleanup_file_references) only removes the `source_file` GraphNode
      projection — derived NoteObject + their GraphNode projections persist as
      orphans. After all files gone, sidebar still showed 62 phantom nodes.

      Phase 2 finds GraphNodes that have no incoming/outgoing graph_edges AND no
      suggested_relations, with object_type NOT IN ('cluster','context_pack').
      For (note/entity/tag/concept/person/project) types we also drop the linked
      NoteObject row. Cluster/pack types are left alone — they have their own
      lifecycle (_cleanup_empty_clusters handles empty clusters · packs are
      user-created and stay until user deletes them).

    Idempotent: re-running with 0 orphans returns stats with all zeros (no-op).
    Skips Drive trash for ghosts (files already gone from Drive — that's why
    they're ghosts).
    """
    from sqlalchemy import delete as sql_delete, text

    ghost_q = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status == "deleted_in_drive",
        )
    )
    ghosts = ghost_q.scalars().all()

    stats = {
        "ghosts_purged": 0,
        "graph_nodes_removed": 0,
        "graph_edges_removed": 0,
        "suggestions_removed": 0,
        "summaries_md_removed": 0,
        "packs_updated": 0,
        "chats_updated": 0,
        "injection_logs_updated": 0,
        "empty_clusters_removed": 0,
        # v10.0.16 — orphan derived nodes
        "orphan_nodes_removed": 0,
        "orphan_notes_removed": 0,
    }

    # ─── Phase 1: ghost file rows ───
    for ghost in ghosts:
        summary_md_path = (await db.execute(
            select(FileSummary.md_path).where(FileSummary.file_id == ghost.id)
        )).scalar_one_or_none() or None

        try:
            ref_stats = await _cleanup_file_references(
                db, current_user.id, ghost.id, summary_md_path
            )
            stats["graph_nodes_removed"] += ref_stats.get("graph_nodes_removed", 0)
            stats["graph_edges_removed"] += ref_stats.get("graph_edges_removed", 0)
            stats["suggestions_removed"] += ref_stats.get("suggestions_removed", 0)
            if ref_stats.get("summary_md_removed"):
                stats["summaries_md_removed"] += 1
            stats["packs_updated"] += ref_stats.get("packs_updated", 0)
            stats["chats_updated"] += ref_stats.get("chats_updated", 0)
            stats["injection_logs_updated"] += ref_stats.get("injection_logs_updated", 0)
        except Exception as e:
            logger.warning("cleanup_ghosts: refs cleanup failed for %s: %s", ghost.id, e)

        await db.delete(ghost)
        stats["ghosts_purged"] += 1

    await db.commit()

    if stats["ghosts_purged"]:
        try:
            stats["empty_clusters_removed"] = await _cleanup_empty_clusters(db, current_user.id)
            await db.commit()
        except Exception as e:
            logger.warning("cleanup_ghosts: empty cluster cleanup failed: %s", e)

    # ─── Phase 2 (v10.0.16): orphan derived GraphNodes + their NoteObject rows ───
    # Run AFTER ghost cleanup so this also catches orphans freed by phase 1.
    try:
        orphan_q = await db.execute(text("""
            SELECT n.id, n.object_type, n.object_id
            FROM graph_nodes n
            WHERE n.user_id = :uid
            AND n.object_type NOT IN ('cluster', 'context_pack')
            AND NOT EXISTS (
                SELECT 1 FROM graph_edges e
                WHERE e.user_id = :uid
                AND (e.source_node_id = n.id OR e.target_node_id = n.id)
            )
            AND NOT EXISTS (
                SELECT 1 FROM suggested_relations s
                WHERE s.user_id = :uid
                AND (s.source_node_id = n.id OR s.target_node_id = n.id)
            )
        """), {"uid": current_user.id})
        orphan_rows = orphan_q.all()

        # NoteObject-backed types — drop the underlying NoteObject too
        note_obj_types = ('note', 'entity', 'tag', 'concept', 'person', 'project')
        note_obj_ids = [r[2] for r in orphan_rows if r[1] in note_obj_types]
        orphan_node_ids = [r[0] for r in orphan_rows]

        if note_obj_ids:
            r = await db.execute(sql_delete(NoteObject).where(
                NoteObject.id.in_(note_obj_ids),
                NoteObject.user_id == current_user.id,
            ))
            stats["orphan_notes_removed"] = r.rowcount or 0

        if orphan_node_ids:
            r = await db.execute(sql_delete(GraphNode).where(
                GraphNode.id.in_(orphan_node_ids),
                GraphNode.user_id == current_user.id,
            ))
            stats["orphan_nodes_removed"] = r.rowcount or 0

        if orphan_node_ids:
            await db.commit()
    except Exception as e:
        logger.warning("cleanup_ghosts: orphan node cleanup failed: %s", e)

    logger.info(
        "cleanup_ghosts: user=%s ghosts=%d ghost_nodes=%d orphan_nodes=%d orphan_notes=%d clusters=%d",
        current_user.id[:8] + "..",
        stats["ghosts_purged"], stats["graph_nodes_removed"],
        stats["orphan_nodes_removed"], stats["orphan_notes_removed"],
        stats["empty_clusters_removed"],
    )

    return {"status": "ok", "stats": stats}


@app.post("/api/files/{file_id}/promote")
async def promote_vault_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.1.0 — ลอง extract vault file → ย้ายเป็น processed.

    Use case:
    - User เพิ่งเปิดใช้ GOOGLE_API_KEY → audio/video file ใน vault ก็ extract ได้แล้ว
    - Admin ขยาย allowed_file_types → ext ที่เคย vault อาจ extract ได้แล้ว
    - User กดปุ่ม "ลองวิเคราะห์อีกครั้ง" บน vault file card

    Errors:
    - 400 NOT_VAULT — file_kind != "vault_only" (ไม่ต้อง promote)
    - 403 LOCKED — file ถูก lock ด้วย downgrade quota
    - 404 FILE_NOT_FOUND — ไม่มี file หรือไม่ใช่ของ user (no info leak)
    - 404 RAW_MISSING — raw_path file หาย disk

    Success response (200):
    - promoted=true: file_kind ย้ายเป็น "processed", text_length>0
    - promoted=false: ext ยังไม่อยู่ใน allowed_types → ยังเป็น vault
    """
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found"}})
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail={"error": {"code": "LOCKED", "message": "ไฟล์ถูกล็อค"}})
    if file.file_kind != "vault_only":
        raise HTTPException(status_code=400, detail={"error": {"code": "NOT_VAULT", "message": "ไฟล์นี้ไม่ใช่ vault file"}})
    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail={"error": {"code": "RAW_MISSING", "message": "Raw file หายจาก disk"}})

    # Re-check ext กับ allowed_types ปัจจุบัน (อาจขยายแล้วหลัง user upload)
    from .plan_limits import get_limits as _gl
    limits = _gl(current_user)
    if file.filetype not in limits["allowed_file_types"]:
        return {
            "status": "ok",
            "file_id": file_id,
            "promoted": False,
            "file_kind": "vault_only",
            "extraction_status": "vault",
            "message": f"ไฟล์ .{file.filetype} ยังไม่รองรับ — เก็บใน vault ต่อไป",
        }

    # v9.4.0 — async vault → processed via queue (was inline extract+ai_ingest in v9.3.4)
    # Worker จะ pickup → extract → file_kind='processed' + status='uploaded'
    from sqlalchemy import func

    file.file_kind = "processed"
    file.processing_status = "queued"
    file.extraction_status = "pending"
    file.extracted_text = ""  # clear vault searchable text — worker จะใส่ extracted จริง
    file.content_hash = None
    file.extract_started_at = None
    file.extract_completed_at = None
    file.extract_error = None
    file.progress_step = None
    file.progress_pct = None
    file.queued_at = datetime.utcnow()
    await db.commit()

    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= file.queued_at,
        )
    )
    return {
        "status": "ok",
        "file_id": file_id,
        "promoted": True,
        "file_kind": "processed",
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
    }


# ─── v7.1 — Duplicate Detection ─────────────────────────────────────────
class SkipDuplicatesRequest(BaseModel):
    """Request body สำหรับ /api/files/skip-duplicates."""
    file_ids: list[str]


@app.post("/api/files/skip-duplicates")
async def skip_duplicates(
    req: SkipDuplicatesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ลบไฟล์ที่ user เลือก "ข้ามที่ซ้ำ" หลังเห็น duplicate popup (v7.1).

    Validation:
      - file_ids ต้องไม่ว่าง (400 EMPTY_FILE_IDS)
      - ทุก file_id ต้องเป็นของ current_user — กัน cross-user delete leak
      - file ที่ไม่มี / ไม่ใช่ของ user → silently skip (ใส่ใน `skipped` array
        เพื่อให้ frontend แสดง partial-success แทน hard fail)

    Cleanup ที่ทำต่อ 1 ไฟล์:
      1. ลบ raw_path จาก disk (ถ้ามี + exists)
      2. BYOS-aware: ถ้า file.drive_file_id != NULL → trash บน Drive ด้วย
         (best-effort ผ่าน storage_router.delete_drive_file_if_byos)
      3. ลบจาก vector_search index (ถ้าไฟล์เคย organize แล้ว index อยู่)
      4. DB delete → cascade ลบ FileInsight, FileSummary, FileClusterMap (FK)

    Errors เฉพาะ:
      - 400 EMPTY_FILE_IDS — array ว่าง
      - 401 — JWT missing / expired (handled โดย Depends(get_current_user))
    """
    if not req.file_ids:
        raise HTTPException(status_code=400, detail={
            "error": {
                "code": "EMPTY_FILE_IDS",
                "message": "ต้องระบุ file_ids อย่างน้อย 1 ไฟล์",
            }
        })

    deleted: list[str] = []
    skipped_ids: list[str] = []

    for file_id in req.file_ids:
        result = await db.execute(
            select(File).where(
                File.id == file_id,
                File.user_id == current_user.id,
            )
        )
        f = result.scalar_one_or_none()
        if not f:
            # file ไม่มี / ไม่ใช่ของ user → silently skip (ไม่ leak ว่ามีอยู่ที่ user อื่น)
            skipped_ids.append(file_id)
            continue

        # ── v10.0.x — capture summary.md_path BEFORE cascade ──
        summary_row = (await db.execute(
            select(FileSummary.md_path).where(FileSummary.file_id == f.id)
        )).scalar_one_or_none()
        summary_md_path = summary_row or None

        # 1. Best-effort: ลบ raw file จาก disk
        if f.raw_path and os.path.exists(f.raw_path):
            try:
                os.remove(f.raw_path)
            except OSError as e:
                logger.warning(f"skip-duplicates: failed to remove raw_path {f.raw_path}: {e}")

        # 2. Best-effort: BYOS — trash ไฟล์บน Drive ด้วย ถ้ามี drive_file_id
        # (no-op สำหรับ managed users / not configured / not connected)
        if f.drive_file_id:
            try:
                from .storage_router import delete_drive_file_if_byos
                await delete_drive_file_if_byos(
                    current_user.id, db, f.drive_file_id,
                )
            except Exception as e:
                # Defensive: helper ภายในไม่ควร raise แต่ wrap กัน edge case
                logger.warning(
                    f"skip-duplicates: BYOS Drive delete failed for {file_id}: {e}"
                )

        # 3. ลบจาก vector_search index (no-op ถ้า file ยังไม่ organize)
        try:
            from . import vector_search as _vs
            _vs.remove_file(f.id, user_id=current_user.id)
        except Exception as e:
            logger.warning(
                f"skip-duplicates: vector_search remove failed for {file_id}: {e}"
            )

        # 4. v10.0.x — Cleanup orphan references (graph/JSON/summary .md)
        try:
            await _cleanup_file_references(db, current_user.id, f.id, summary_md_path)
        except Exception as e:
            logger.warning(
                f"skip-duplicates: orphan cleanup failed for {file_id}: {e}"
            )

        # 5. ลบ DB row → cascade ลบ FileInsight + FileSummary + FileClusterMap
        await db.delete(f)
        deleted.append(file_id)

    await db.commit()

    # 6. v10.0.x — Empty cluster cleanup (one pass หลัง loop เสร็จ · ประหยัด query)
    try:
        empty_cluster_count = await _cleanup_empty_clusters(db, current_user.id)
        if empty_cluster_count:
            await db.commit()
            logger.info(
                "skip-duplicates: removed %d empty clusters", empty_cluster_count
            )
    except Exception as e:
        logger.warning(f"skip-duplicates: empty cluster cleanup failed: {e}")

    logger.info(
        f"skip-duplicates: user {current_user.id[:8]}.. deleted {len(deleted)} "
        f"files, skipped {len(skipped_ids)}"
    )

    return {
        "status": "ok",
        "deleted": deleted,
        "count": len(deleted),
        "skipped": skipped_ids,
    }


# ═══════════════════════════════════════════
# CHAT API (v2 — enhanced with injection)
# ═══════════════════════════════════════════

@app.post("/api/chat")
async def chat(req: ChatRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """AI Chat with automatic context injection from all layers."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = await chat_with_retrieval(db, current_user.id, req.question)
        return result
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# PROFILE APIs (v2)
# ═══════════════════════════════════════════

@app.get("/api/profile")
async def api_get_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get user profile."""
    return await get_profile(db, current_user.id)

@app.get("/api/personality/reference")
async def api_personality_reference():
    """Public reference data — 4 ระบบบุคลิกภาพ + test links.

    ไม่ต้อง auth — frontend cache ใน sessionStorage เพื่อลด round-trip
    """
    from .personality import (
        MBTI_TYPES, MBTI_SOURCES, MBTI_TEST_LINKS,
        ENNEAGRAM_TYPES, ENNEAGRAM_TEST_LINKS,
        CLIFTON_THEMES, CLIFTON_ALL_THEMES, CLIFTON_TEST_LINKS,
        VIA_STRENGTHS, VIA_ALL_STRENGTHS, VIA_TEST_LINKS,
    )
    return {
        "mbti": {
            "types": MBTI_TYPES,
            "sources": MBTI_SOURCES,
            "test_links": MBTI_TEST_LINKS,
        },
        "enneagram": {
            # JSON keys ต้องเป็น string — แปลง int key เป็น str
            "types": {str(k): v for k, v in ENNEAGRAM_TYPES.items()},
            "test_links": ENNEAGRAM_TEST_LINKS,
        },
        "clifton": {
            "domains": CLIFTON_THEMES,
            "all": CLIFTON_ALL_THEMES,
            "test_links": CLIFTON_TEST_LINKS,
        },
        "via": {
            "virtues": VIA_STRENGTHS,
            "all": VIA_ALL_STRENGTHS,
            "test_links": VIA_TEST_LINKS,
        },
    }


@app.get("/api/profile/personality/history")
async def api_get_personality_history(
    system: str | None = Query(None, description="Filter: mbti | enneagram | clifton | via"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List personality history snapshots (most recent first)."""
    from .profile import list_personality_history
    from .personality import SUPPORTED_SYSTEMS
    if system and system not in SUPPORTED_SYSTEMS:
        raise HTTPException(status_code=400, detail=f"INVALID_SYSTEM: must be one of {SUPPORTED_SYSTEMS}")
    history = await list_personality_history(db, current_user.id, system, limit)
    return {"history": history, "count": len(history)}


@app.put("/api/profile")
async def api_update_profile(req: ProfileRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create or update user profile (v6.0 — supports personality fields + history).

    ⚠️ Convention เปลี่ยนจาก v5: ใช้ exclude_unset แทน exclude_none
    → ส่ง null = clear field (DB NULL + history บันทึก clear event)
    → ไม่ส่ง field = ไม่เปลี่ยน
    """
    # Clifton/VIA — validate ที่ service-level เพื่อให้ error message ละเอียด
    # (Pydantic v2 max_length คุม count ให้แล้ว แต่ไม่รู้จัก theme name)
    if req.clifton_top5:
        from .personality import validate_clifton
        ok, invalid = validate_clifton(req.clifton_top5)
        if not ok:
            if invalid == ["DUPLICATE"]:
                raise HTTPException(status_code=400, detail=f"DUPLICATE_THEMES: clifton_top5 มีค่าซ้ำ")
            raise HTTPException(status_code=400, detail=f"INVALID_CLIFTON_THEME: {invalid}")
    if req.via_top5:
        from .personality import validate_via
        ok, invalid = validate_via(req.via_top5)
        if not ok:
            if invalid == ["DUPLICATE"]:
                raise HTTPException(status_code=400, detail=f"DUPLICATE_THEMES: via_top5 มีค่าซ้ำ")
            raise HTTPException(status_code=400, detail=f"INVALID_VIA_STRENGTH: {invalid}")

    # exclude_unset: เก็บเฉพาะ field ที่ user ส่งมาจริง (รวม null) เพื่อให้ clear ทำงาน
    data = req.model_dump(exclude_unset=True)
    # Mark source สำหรับ history — ผ่าน web → "user_update"
    data["_history_source"] = "user_update"
    return await update_profile(db, current_user.id, data)


# ═══════════════════════════════════════════
# CONTEXT PACK APIs (v2)
# ═══════════════════════════════════════════

@app.get("/api/context-packs")
async def api_list_packs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all context packs."""
    packs = await list_packs(db, current_user.id)
    return {"packs": packs, "count": len(packs)}

@app.post("/api/context-packs")
async def api_create_pack(req: ContextPackRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a new context pack from source files/clusters."""
    valid_types = {"profile", "study", "work", "project"}
    if req.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {valid_types}")
    if not req.source_file_ids and not req.source_cluster_ids:
        raise HTTPException(status_code=400, detail="Must provide source_file_ids or source_cluster_ids")
    # v5.9.3 — enforce pack limit
    limit_err = await check_pack_create_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])
    try:
        pack = await create_pack(db, current_user.id, req.type, req.title, req.source_file_ids, req.source_cluster_ids)
        return pack
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pack creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/context-packs/{pack_id}")
async def api_get_pack(pack_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get a single context pack."""
    pack = await get_pack(db, pack_id, current_user.id)
    if not pack:
        raise HTTPException(status_code=404, detail="Context pack not found")
    return pack

@app.delete("/api/context-packs/{pack_id}")
async def api_delete_pack(pack_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a context pack."""
    deleted = await delete_pack(db, pack_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Context pack not found")
    return {"status": "ok"}

@app.post("/api/context-packs/{pack_id}/regenerate")
async def api_regenerate_pack(pack_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Regenerate a context pack from its original sources."""
    # v5.9.3 — locked pack check (PRD section 17.1 — locked packs cannot be refreshed)
    pack_check = await db.execute(
        select(ContextPack).where(ContextPack.id == pack_id, ContextPack.user_id == current_user.id)
    )
    existing_pack = pack_check.scalar_one_or_none()
    if not existing_pack:
        raise HTTPException(status_code=404, detail="Context pack not found")
    if getattr(existing_pack, "is_locked", False):
        raise HTTPException(status_code=403, detail="Context Pack นี้ถูกล็อค — อัปเกรดเพื่อ refresh pack ที่ล็อค")

    # v5.9.3 — check refresh quota
    limit_err = await check_refresh_allowed(db, current_user)
    if limit_err:
        raise HTTPException(status_code=403, detail=limit_err["error"])
    try:
        pack = await regenerate_pack(db, pack_id, current_user.id)
        if not pack:
            raise HTTPException(status_code=404, detail="Context pack not found")
        await log_usage(db, current_user.id, "refresh")
        await db.commit()
        return pack
    except Exception as e:
        logger.error(f"Pack regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════
# v9.2.0 — AI PACK BUILDER (clarify → propose → confirm)
# ═══════════════════════════════════════════

@app.post("/api/context-packs/ai-build/clarify")
async def api_ai_build_clarify(
    req: AIBuilderClarifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 0: AI gen clarifying question + options (หรือ skip ถ้า prompt ละเอียดพอ).

    Pre-checks pack quota + ai_summary quota ก่อนเรียก LLM — กัน user เริ่ม flow
    ที่ทำต่อไม่ได้ (เปลือง LLM)
    """
    from .ai_pack_builder import clarify_prompt

    # Quota guards — pack count + monthly ai_summary
    pack_err = await check_pack_create_allowed(db, current_user)
    if pack_err:
        raise HTTPException(status_code=403, detail=pack_err["error"])
    ai_err = await check_summary_allowed(db, current_user)
    if ai_err:
        raise HTTPException(status_code=403, detail=ai_err["error"])

    # ดึง user lang จาก profile หรือ default ไทย — frontend ก็ส่งมาเองได้ในอนาคต
    user_lang = "th"
    try:
        result = await clarify_prompt(db, current_user.id, req.prompt, user_lang=user_lang)
        return result
    except ValueError as e:
        msg = str(e)
        if "NO_SOURCES_AVAILABLE" in msg:
            raise HTTPException(
                status_code=400,
                detail="ยังไม่มีไฟล์หรือ collection ในระบบ — อัปโหลดไฟล์ก่อน",
            )
        raise HTTPException(status_code=400, detail=msg)
    except RuntimeError as e:
        msg = str(e)
        if "LLM_RESPONSE_INVALID" in msg:
            raise HTTPException(status_code=400, detail="AI ตอบกลับไม่ถูกต้อง — ลองใหม่อีกครั้ง")
        raise HTTPException(status_code=503, detail="ระบบ AI ไม่พร้อมใช้งาน — ลองใหม่ภายหลัง")
    except Exception as e:
        logger.exception(f"clarify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context-packs/ai-build/propose")
async def api_ai_build_propose(
    req: AIBuilderProposeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 1+2: AI build draft proposal (select sources + distill summary)."""
    from .ai_pack_builder import propose_pack

    # Re-check quota (user อาจสร้าง pack อื่นไประหว่างทาง)
    pack_err = await check_pack_create_allowed(db, current_user)
    if pack_err:
        raise HTTPException(status_code=403, detail=pack_err["error"])
    ai_err = await check_summary_allowed(db, current_user)
    if ai_err:
        raise HTTPException(status_code=403, detail=ai_err["error"])

    clarification_dict = req.clarification.model_dump(exclude_none=True)
    user_lang = "th"
    try:
        return await propose_pack(
            db, current_user.id, req.session_id,
            clarification_dict, preferred_type=req.preferred_type,
            user_lang=user_lang,
        )
    except ValueError as e:
        msg = str(e)
        if "SESSION_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail="Session หมดอายุ — เริ่มใหม่")
        if "INVALID_CLARIFICATION" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except RuntimeError as e:
        msg = str(e)
        if "LLM_RESPONSE_INVALID" in msg:
            raise HTTPException(status_code=400, detail="AI ตอบกลับไม่ถูกต้อง — ลองใหม่อีกครั้ง")
        raise HTTPException(status_code=503, detail="ระบบ AI ไม่พร้อมใช้งาน")
    except Exception as e:
        logger.exception(f"propose failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context-packs/ai-build/confirm")
async def api_ai_build_confirm(
    req: AIBuilderConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 3: Save draft as real ContextPack."""
    from .ai_pack_builder import confirm_pack

    edits_dict = req.edits.model_dump(exclude_none=True) if req.edits else None
    try:
        return await confirm_pack(db, current_user, req.draft_id, edits_dict)
    except ValueError as e:
        msg = str(e)
        if "DRAFT_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail="Draft หมดอายุ — สร้างใหม่")
        if "INVALID_TYPE" in msg:
            raise HTTPException(status_code=400, detail="type ต้องเป็น profile/study/work/project")
        if "NO_SOURCES_SELECTED" in msg:
            raise HTTPException(status_code=400, detail="ต้องเลือก source อย่างน้อย 1 อัน")
        raise HTTPException(status_code=400, detail=msg)
    except RuntimeError as e:
        msg = str(e)
        if "PACK_LIMIT_REACHED" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        logger.exception(f"confirm failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/context-packs/ai-build/drafts/{draft_id}")
async def api_ai_build_discard(
    draft_id: str,
    current_user: User = Depends(get_current_user),
):
    """Discard draft (cleanup cache) — graceful no-op ถ้าไม่เจอ"""
    from .ai_pack_builder import discard_draft
    discarded = discard_draft(current_user.id, draft_id)
    return {"status": "discarded" if discarded else "not_found"}


# ═══════════════════════════════════════════
# v9.3.0 — PACK SHARE (Share Context Pack with others)
# ═══════════════════════════════════════════

@app.post("/api/context-packs/{pack_id}/share")
async def api_pack_share_create(
    pack_id: str,
    req: PackShareCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — สร้างลิงก์ share สำหรับ pack (idempotent — กดซ้ำได้ลิงก์เดิม)"""
    from .pack_share import create_share
    from .plan_limits import check_pack_share_create_allowed, log_usage

    try:
        # Check existing active share first — idempotent (ไม่ count quota เพิ่ม)
        from sqlalchemy import select as _sel
        from .database import PackShare as _PackShare
        existing_res = await db.execute(
            _sel(_PackShare).where(
                _PackShare.pack_id == pack_id,
                _PackShare.owner_user_id == current_user.id,
                _PackShare.revoked_at.is_(None),
            )
        )
        is_existing = existing_res.scalar_one_or_none() is not None

        if not is_existing:
            # Pre-check quota only when creating new
            err = await check_pack_share_create_allowed(db, current_user)
            if err:
                raise HTTPException(status_code=403, detail=err["error"])

        result = await create_share(db, current_user, pack_id, req.include_files)

        # Log usage only for new shares
        if not is_existing:
            await log_usage(db, current_user.id, "pack_share")
            await db.commit()

        return result
    except ValueError as e:
        msg = str(e)
        if "PACK_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail="Pack ไม่พบ")
        if "PACK_LOCKED" in msg:
            raise HTTPException(status_code=400, detail="Pack ถูกล็อค — แชร์ไม่ได้")
        raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Pack share create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/context-packs/shares/{share_id}")
async def api_pack_share_update(
    share_id: str,
    req: PackShareUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — Toggle include_files (URL ไม่เปลี่ยน)"""
    from .pack_share import update_share_files
    try:
        return await update_share_files(db, current_user, share_id, req.include_files)
    except ValueError as e:
        if "SHARE_NOT_FOUND" in str(e):
            raise HTTPException(status_code=404, detail="Share ไม่พบ")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/context-packs/shares/{share_id}")
async def api_pack_share_revoke(
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — Revoke share (idempotent)"""
    from .pack_share import revoke_share
    try:
        return await revoke_share(db, current_user, share_id)
    except ValueError as e:
        if "SHARE_NOT_FOUND" in str(e):
            raise HTTPException(status_code=404, detail="Share ไม่พบ")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/context-packs/{pack_id}/shares")
async def api_pack_shares_list(
    pack_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — List shares ของ pack (เฉพาะของ user)"""
    from .pack_share import list_shares_for_pack
    shares = await list_shares_for_pack(db, current_user, pack_id)
    return {"shares": shares, "count": len(shares)}


@app.get("/api/shared/pack/{token}")
async def api_pack_share_preview(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — Recipient preview (NO AUTH REQUIRED). Increment view_count."""
    from .pack_share import get_preview, ShareTokenError
    try:
        return await get_preview(db, token)
    except ShareTokenError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ValueError as e:
        msg = str(e)
        if "SHARE_REVOKED" in msg:
            raise HTTPException(status_code=403, detail="ลิงก์ถูกยกเลิกแล้ว")
        if "SHARE_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail="ลิงก์ไม่มีอยู่")
        if "PACK_DELETED" in msg:
            raise HTTPException(status_code=404, detail="Pack ถูกลบแล้ว")
        raise HTTPException(status_code=400, detail=msg)


@app.post("/api/shared/pack/{token}/claim")
async def api_pack_share_claim(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.3.0 — Recipient claim → clone pack เข้า workspace"""
    from .pack_share import claim_to_workspace, ShareTokenError
    try:
        return await claim_to_workspace(db, current_user, token)
    except ShareTokenError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ValueError as e:
        msg = str(e)
        if "SHARE_REVOKED" in msg:
            raise HTTPException(status_code=403, detail="ลิงก์ถูกยกเลิกแล้ว")
        if "SHARE_NOT_FOUND" in msg or "PACK_DELETED" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except PermissionError as e:
        msg = str(e)
        if "PACK_LIMIT_REACHED" in msg or "STORAGE_LIMIT_REACHED" in msg:
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=403, detail=msg)
    except Exception as e:
        logger.exception(f"Pack claim failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/p/{token}")
async def serve_shared_pack_page(token: str):
    """v9.3.0 — Serve recipient preview HTML page (no auth)"""
    return _serve_html("shared_pack.html")


# ═══════════════════════════════════════════
# CONTEXT MEMORY APIs (v5.5)
# ═══════════════════════════════════════════

@app.get("/api/contexts")
async def api_list_contexts(
    limit: int = 20,
    context_type: str = None,
    is_pinned: bool = None,
    search: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contexts for this user."""
    from .context_memory import list_contexts
    return await list_contexts(db, current_user.id, limit=limit, context_type=context_type, is_pinned=is_pinned, search=search)

@app.post("/api/contexts")
async def api_save_context(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Save a new context."""
    from .context_memory import save_context
    body = await request.json()
    return await save_context(
        db, current_user.id,
        title=body.get("title", ""),
        content=body.get("content", ""),
        summary=body.get("summary", ""),
        context_type=body.get("context_type", "conversation"),
        platform=body.get("platform", "web"),
        tags=body.get("tags", []),
        related_file_ids=body.get("related_file_ids", []),
        is_pinned=body.get("is_pinned", False),
    )

@app.put("/api/contexts/{context_id}")
async def api_update_context(context_id: str, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update a context."""
    from .context_memory import update_context
    body = await request.json()
    result = await update_context(db, current_user.id, context_id, **body)
    if result.get("error") == "context_not_found":
        raise HTTPException(status_code=404, detail="Context not found")
    return result

@app.delete("/api/contexts/{context_id}")
async def api_delete_context(context_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a context."""
    from .context_memory import delete_context
    result = await delete_context(db, current_user.id, context_id)
    if result.get("error") == "context_not_found":
        raise HTTPException(status_code=404, detail="Context not found")
    return result

@app.get("/api/contexts/{context_id}")
async def api_get_context(context_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Load a specific context — returns flat object."""
    from .context_memory import load_context
    result = await load_context(db, current_user.id, context_id=context_id)
    if result.get("error") == "context_not_found":
        raise HTTPException(status_code=404, detail="Context not found")
    # Unwrap for REST API convenience (frontend expects flat object)
    contexts = result.get("contexts", [])
    if contexts:
        return contexts[0]
    return result


# ═══════════════════════════════════════════
# GRAPH APIs (v3 — new)
# ═══════════════════════════════════════════

@app.post("/api/graph/build")
async def api_build_graph(
    force: bool = Query(False, description="Force full rebuild · skip idempotent count check"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build/rebuild the knowledge graph from all data.

    ?force=true → tear down + rebuild even ถ้า node_count == file_count (กัน orphan ค้าง)
    """
    try:
        result = await build_full_graph(db, current_user.id, force=force)
        await generate_suggestions(db, current_user.id)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/global")
async def api_global_graph(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get full graph data for global graph visualization."""
    data = await get_graph_data(db, current_user.id)
    return data


@app.get("/api/graph/nodes")
async def api_list_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    family: str | None = None,
    limit: int = Query(5000, ge=1, le=20000),  # v10.0.0 -- hard cap
    offset: int = Query(0, ge=0),
):
    """List all graph nodes, optionally filtered by family.

    v10.0.0 pagination: ``limit`` default 5000 (well above any realistic user),
    hard ceiling 20000 to prevent runaway responses. Frontend doesn't need
    to pass these for the common case.
    """
    query = select(GraphNode).where(GraphNode.user_id == current_user.id)
    if family:
        query = query.where(GraphNode.node_family == family)
    query = query.limit(limit).offset(offset)
    nodes = (await db.execute(query)).scalars().all()
    return {"nodes": [
        {
            "id": n.id,
            "object_type": n.object_type,
            "object_id": n.object_id,
            "label": n.label,
            "node_family": n.node_family,
            "importance": n.importance_score,
            "freshness": n.freshness_score,
        }
        for n in nodes
    ]}


@app.get("/api/graph/nodes/{node_id}")
async def api_get_node(node_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get detailed info about a single graph node."""
    detail = await get_node_detail(db, node_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail


@app.get("/api/graph/neighborhood/{node_id}")
async def api_neighborhood(
    node_id: str,
    depth: int = Query(1, ge=1, le=3),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get N-hop neighborhood around a node for local graph."""
    data = await get_neighborhood(db, node_id, depth, current_user.id)
    return data


@app.get("/api/graph/edges")
async def api_list_edges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    edge_type: str | None = None,
    limit: int = Query(10000, ge=1, le=50000),  # v10.0.0 -- hard cap
    offset: int = Query(0, ge=0),
):
    """List all graph edges, optionally filtered by type.

    v10.0.0: hard cap 50000 prevents pathological responses.
    """
    query = select(GraphEdge).where(GraphEdge.user_id == current_user.id)
    if edge_type:
        query = query.where(GraphEdge.edge_type == edge_type)
    query = query.limit(limit).offset(offset)
    edges = (await db.execute(query)).scalars().all()
    return {"edges": [
        {
            "id": e.id,
            "source": e.source_node_id,
            "target": e.target_node_id,
            "edge_type": e.edge_type,
            "weight": e.weight,
            "confidence": e.confidence,
            "evidence": e.evidence_text,
        }
        for e in edges
    ]}


# ═══════════════════════════════════════════
# RELATIONS APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/relations/backlinks/{node_id}")
async def api_backlinks(node_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all backlinks (nodes pointing TO this node)."""
    return {"backlinks": await get_backlinks(db, node_id)}


@app.get("/api/relations/outgoing/{node_id}")
async def api_outgoing(node_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all outgoing links (nodes FROM this node)."""
    return {"outgoing": await get_outgoing(db, node_id)}


@app.get("/api/suggestions")
async def api_suggestions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get pending suggested relations."""
    suggestions = await get_suggestions(db, current_user.id)
    return {"suggestions": suggestions, "count": len(suggestions)}


@app.post("/api/suggestions/{suggestion_id}/accept")
async def api_accept_suggestion(suggestion_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Accept a suggested relation — creates real edge."""
    result = await accept_suggestion(db, suggestion_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


@app.post("/api/suggestions/{suggestion_id}/dismiss")
async def api_dismiss_suggestion(suggestion_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Dismiss a suggested relation."""
    result = await dismiss_suggestion(db, suggestion_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


# ═══════════════════════════════════════════
# METADATA APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/metadata/{file_id}")
async def api_get_metadata(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get enriched metadata for a file."""
    meta = await get_file_metadata(db, file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    return meta


@app.put("/api/metadata/{file_id}")
async def api_update_metadata(file_id: str, req: MetadataUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update file metadata manually."""
    updates = req.model_dump(exclude_none=True)
    result = await update_file_metadata(db, file_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    return result


@app.post("/api/metadata/enrich")
async def api_enrich_metadata(
    force: bool = Query(False, description="Re-enrich files that already have tags"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enrich metadata for all files using LLM.

    v10.0.0: by default skips files that are already enriched (have tags).
    Pass ?force=true to re-run on every file (refresh).
    """
    try:
        result = await enrich_all_files(db, current_user.id, force=force)
        return result
    except Exception as e:
        logger.error(f"Metadata enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# LENSES APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/lenses")
async def api_list_lenses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List saved graph lenses."""
    lenses = (await db.execute(
        select(GraphLens).where(GraphLens.user_id == current_user.id)
    )).scalars().all()
    return {"lenses": [
        {"id": l.id, "name": l.name, "type": l.type,
         "filter_json": json.loads(l.filter_json or "{}"),
         "layout_json": json.loads(l.layout_json or "{}")}
        for l in lenses
    ]}


# ═══════════════════════════════════════════
# STATS API (v3 — enhanced)
# ═══════════════════════════════════════════

@app.get("/api/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get storage/processing stats including v3 graph data and v4 MCP data.

    v10.0.15 — exclude `processing_status='deleted_in_drive'` ghost rows from
    file count so sidebar matches what /api/files returns (which also hides
    these per F16). Without this filter, ghosts inflated sidebar counter while
    file list showed 0 → looked like a sync bug.
    Graph/cluster/pack counts still include orphans tied to ghosts — those get
    cleaned by POST /api/files/cleanup-ghosts.
    """
    files_result = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status != "deleted_in_drive",
        )
    )
    files = files_result.scalars().all()

    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == current_user.id))
    clusters = clusters_result.scalars().all()

    packs_result = await db.execute(select(ContextPack).where(ContextPack.user_id == current_user.id))
    packs = packs_result.scalars().all()

    nodes_result = await db.execute(select(GraphNode).where(GraphNode.user_id == current_user.id))
    nodes = nodes_result.scalars().all()

    edges_result = await db.execute(select(GraphEdge).where(GraphEdge.user_id == current_user.id))
    edges = edges_result.scalars().all()

    suggestions_result = await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == current_user.id,
            SuggestedRelation.status == "pending"
        )
    )
    suggestions = suggestions_result.scalars().all()

    profile = await get_profile(db, current_user.id)

    # v4 — MCP stats
    active_tokens = await get_active_token_count(db, current_user.id)

    return {
        "total_files": len(files),
        "total_clusters": len(clusters),
        "processed": sum(1 for f in files if f.processing_status == "ready"),
        "processing": sum(1 for f in files if f.processing_status == "processing"),
        "errors": sum(1 for f in files if f.processing_status == "error"),
        # v9.1.0 — Vault stats (separate count for UI filter chip badge)
        "processed_files": sum(1 for f in files if getattr(f, "file_kind", "processed") == "processed"),
        "vault_files": sum(1 for f in files if getattr(f, "file_kind", "processed") == "vault_only"),
        "total_context_packs": len(packs),
        "profile_set": is_profile_complete(profile),
        # v3 — graph stats
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_suggestions": len(suggestions),
        "graph_built": len(nodes) > 0,
        # v4 — MCP stats
        "active_tokens": active_tokens,
    }


# ═══════════════════════════════════════════
# USAGE & PLAN APIs (v5.9.3)
# ═══════════════════════════════════════════

@app.get("/api/usage")
async def api_get_usage(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return usage summary for the current user — dashboard display."""
    return await get_usage_summary(db, current_user)

@app.get("/api/plan-limits")
async def api_get_plan_limits(current_user: User = Depends(get_current_user)):
    """Return the limits for the user's current plan."""
    return {"plan": current_user.plan or "free", "limits": get_limits(current_user)}


@app.delete("/api/reset")
async def reset_all(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Comprehensive reset — synchronous cleanup with progress stats (v9.3.5.5).

    Why synchronous (vs background_tasks): user คาดหวังว่า "Reset เสร็จ = ทุกอย่างเคลียร์
    + stats accurate". Slowness acceptable for explicit destructive action.

    storage_source guard ปกป้อง drive_picked (user's external) — ไม่ trash.
    """
    from sqlalchemy import delete as sql_delete
    from .storage_router import (
        _should_trash_drive_file,
        delete_drive_file_if_byos,
        delete_extracted_text_from_drive_if_byos,
        delete_summary_from_drive_if_byos,
    )

    stats = {
        "files_deleted": 0,
        "drive_files_trashed": 0,
        "drive_extracted_trashed": 0,
        "drive_summaries_trashed": 0,
        "drive_cleanup_skipped_picked": 0,  # F5 guard hits
        "vector_index_cleaned": 0,
        "llamaparse_cache_purged": 0,        # v10.0.8
        "chat_queries_cleared": 0,           # v10.0.8
        "context_memories_cleared": 0,       # v10.0.8
        "canvas_objects_cleared": 0,         # v10.0.8
        "personality_history_cleared": 0,    # v10.0.8
        "errors": 0,
    }

    # v10.0.8 — Clear chat history first (FK cascade ลบ context_injection_logs ตาม)
    # เดิม /api/reset ทิ้ง chat_queries ไว้ที่มี stale file_ids/cluster_ids/pack_ids
    chat_del = await db.execute(sql_delete(ChatQuery).where(ChatQuery.user_id == current_user.id))
    stats["chat_queries_cleared"] = chat_del.rowcount or 0

    # Clear graph data first (FK dependencies)
    await db.execute(sql_delete(SuggestedRelation).where(SuggestedRelation.user_id == current_user.id))
    await db.execute(sql_delete(GraphEdge).where(GraphEdge.user_id == current_user.id))
    await db.execute(sql_delete(GraphNode).where(GraphNode.user_id == current_user.id))
    await db.execute(sql_delete(NoteObject).where(NoteObject.user_id == current_user.id))
    await db.execute(sql_delete(GraphLens).where(GraphLens.user_id == current_user.id))

    # v10.0.8 — Clear other user-scoped data tables (เดิมค้างหลัง reset)
    cm_del = await db.execute(sql_delete(ContextMemory).where(ContextMemory.user_id == current_user.id))
    stats["context_memories_cleared"] = cm_del.rowcount or 0
    co_del = await db.execute(sql_delete(CanvasObject).where(CanvasObject.user_id == current_user.id))
    stats["canvas_objects_cleared"] = co_del.rowcount or 0
    ph_del = await db.execute(sql_delete(PersonalityHistory).where(PersonalityHistory.user_id == current_user.id))
    stats["personality_history_cleared"] = ph_del.rowcount or 0

    files_result = await db.execute(select(File).where(File.user_id == current_user.id))
    for f in files_result.scalars().all():
        # 1. Disk + LlamaParse cache (purge cache ก่อนลบ raw — ต้อง hash bytes)
        if f.raw_path and os.path.exists(f.raw_path):
            try:
                from .processors.llamaparse import purge_cache_for_file
                stats["llamaparse_cache_purged"] += purge_cache_for_file(f.raw_path)
            except Exception as e:
                logger.warning(f"reset_all: llamaparse purge failed for {f.id}: {e}")
            try:
                os.remove(f.raw_path)
            except OSError as e:
                logger.warning(f"reset_all: remove raw_path {f.raw_path} failed: {e}")

        # 2. Drive cleanup (raw + extracted + summary) · with storage_source guard
        if f.drive_file_id and _should_trash_drive_file(f.storage_source):
            try:
                ok = await delete_drive_file_if_byos(current_user.id, db, f.drive_file_id)
                if ok:
                    stats["drive_files_trashed"] += 1
            except Exception as e:
                logger.warning(f"reset_all: drive raw delete failed for {f.id}: {e}")
                stats["errors"] += 1
            try:
                ok = await delete_extracted_text_from_drive_if_byos(current_user.id, db, f.id)
                if ok:
                    stats["drive_extracted_trashed"] += 1
            except Exception as e:
                logger.warning(f"reset_all: drive extracted delete failed for {f.id}: {e}")
                stats["errors"] += 1
            try:
                ok = await delete_summary_from_drive_if_byos(current_user.id, db, f.id)
                if ok:
                    stats["drive_summaries_trashed"] += 1
            except Exception as e:
                logger.warning(f"reset_all: drive summary delete failed for {f.id}: {e}")
                stats["errors"] += 1
        elif f.storage_source == "drive_picked":
            stats["drive_cleanup_skipped_picked"] += 1

        # 3. Vector index
        try:
            from . import vector_search as _vs
            _vs.remove_file(f.id, user_id=current_user.id)
            stats["vector_index_cleaned"] += 1
        except Exception as e:
            logger.warning(f"reset_all: vector remove failed for {f.id}: {e}")

        # 4. DB cascade
        await db.delete(f)
        stats["files_deleted"] += 1

    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == current_user.id))
    for c in clusters_result.scalars().all():
        await db.delete(c)

    # v10.0.8 — PackShare rows ที่ user เป็น owner (FK ไม่มี ondelete=CASCADE)
    await db.execute(sql_delete(PackShare).where(PackShare.owner_user_id == current_user.id))

    packs_result = await db.execute(select(ContextPack).where(ContextPack.user_id == current_user.id))
    for p in packs_result.scalars().all():
        if p.md_path and os.path.exists(p.md_path):
            try:
                os.remove(p.md_path)
            except OSError as e:
                logger.warning(f"reset_all: remove pack md failed: {e}")
        await db.delete(p)

    await db.commit()

    logger.info(
        "reset_all: user=%s files=%d drive_raw=%d drive_extracted=%d drive_summaries=%d picked_skip=%d errors=%d",
        (current_user.id[:8] + ".."), stats["files_deleted"], stats["drive_files_trashed"],
        stats["drive_extracted_trashed"], stats["drive_summaries_trashed"],
        stats["drive_cleanup_skipped_picked"], stats["errors"],
    )

    return {"status": "ok", "message": "All data cleared", "stats": stats}


class DeleteAccountRequest(BaseModel):
    confirm_email: str  # client must echo back current_user.email — guard against accidental call


@app.delete("/api/auth/me")
async def delete_my_account(
    req: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v10.0.8 — Full account purge (GDPR-grade). Removes EVERY trace of the user.

    Differs from /api/reset (which keeps user row + profile + tokens):
    - Deletes user row (cascade clears profile, drive_connection)
    - Deletes MCP tokens, MCP usage logs, usage_logs, audit_logs
    - Deletes ALL data /api/reset clears (files, graph, packs, chat, etc.)
    - Drive raw/extracted/summary trashed (best-effort)
    - LlamaParse cache purged for every file
    - Vector index entries removed

    Guards:
    - Requires `confirm_email` to match current_user.email (prevents accidental UI call)
    - Returns stats summary
    """
    from sqlalchemy import delete as sql_delete
    from .storage_router import (
        _should_trash_drive_file,
        delete_drive_file_if_byos,
        delete_extracted_text_from_drive_if_byos,
        delete_summary_from_drive_if_byos,
    )

    if (req.confirm_email or "").strip().lower() != (current_user.email or "").strip().lower():
        raise HTTPException(status_code=400, detail={"error": {
            "code": "EMAIL_MISMATCH",
            "message": "Confirm email ไม่ตรงกับบัญชีนี้",
        }})

    user_id = current_user.id
    stats = {
        "files_deleted": 0,
        "drive_files_trashed": 0,
        "vector_index_cleaned": 0,
        "llamaparse_cache_purged": 0,
        "errors": 0,
    }

    # 1. Chat history (FK cascade → context_injection_logs)
    await db.execute(sql_delete(ChatQuery).where(ChatQuery.user_id == user_id))

    # 2. Graph + lens + notes + suggestions
    await db.execute(sql_delete(SuggestedRelation).where(SuggestedRelation.user_id == user_id))
    await db.execute(sql_delete(GraphEdge).where(GraphEdge.user_id == user_id))
    await db.execute(sql_delete(GraphNode).where(GraphNode.user_id == user_id))
    await db.execute(sql_delete(NoteObject).where(NoteObject.user_id == user_id))
    await db.execute(sql_delete(GraphLens).where(GraphLens.user_id == user_id))

    # 3. Other user-scoped tables
    await db.execute(sql_delete(ContextMemory).where(ContextMemory.user_id == user_id))
    await db.execute(sql_delete(CanvasObject).where(CanvasObject.user_id == user_id))
    await db.execute(sql_delete(PersonalityHistory).where(PersonalityHistory.user_id == user_id))

    # 4. Files (disk + Drive + vector + LlamaParse cache)
    files_result = await db.execute(select(File).where(File.user_id == user_id))
    for f in files_result.scalars().all():
        if f.raw_path and os.path.exists(f.raw_path):
            try:
                from .processors.llamaparse import purge_cache_for_file
                stats["llamaparse_cache_purged"] += purge_cache_for_file(f.raw_path)
            except Exception as e:
                logger.warning("delete_account: llamaparse purge failed for %s: %s", f.id, e)
            try:
                os.remove(f.raw_path)
            except OSError as e:
                logger.warning("delete_account: raw remove %s failed: %s", f.raw_path, e)

        if f.drive_file_id and _should_trash_drive_file(f.storage_source):
            try:
                if await delete_drive_file_if_byos(user_id, db, f.drive_file_id):
                    stats["drive_files_trashed"] += 1
                await delete_extracted_text_from_drive_if_byos(user_id, db, f.id)
                await delete_summary_from_drive_if_byos(user_id, db, f.id)
            except Exception as e:
                logger.warning("delete_account: drive cleanup failed for %s: %s", f.id, e)
                stats["errors"] += 1

        try:
            from . import vector_search as _vs
            _vs.remove_file(f.id, user_id=user_id)
            stats["vector_index_cleaned"] += 1
        except Exception:
            pass

        await db.delete(f)
        stats["files_deleted"] += 1

    # 5. Clusters
    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == user_id))
    for c in clusters_result.scalars().all():
        await db.delete(c)

    # 6a. PackShare BEFORE ContextPack (FK: pack_shares.pack_id → context_packs.id NOT NULL)
    await db.execute(sql_delete(PackShare).where(PackShare.owner_user_id == user_id))

    # 6b. Context packs (md files)
    packs_result = await db.execute(select(ContextPack).where(ContextPack.user_id == user_id))
    for p in packs_result.scalars().all():
        if p.md_path and os.path.exists(p.md_path):
            try:
                os.remove(p.md_path)
            except OSError:
                pass
        await db.delete(p)

    # 6c. LineUser (linked LINE account) — no FK cascade
    await db.execute(sql_delete(LineUser).where(LineUser.pdb_user_id == user_id))

    # 7. MCP tokens + logs + audit/usage logs
    await db.execute(sql_delete(MCPUsageLog).where(MCPUsageLog.user_id == user_id))
    await db.execute(sql_delete(MCPToken).where(MCPToken.user_id == user_id))
    await db.execute(sql_delete(UsageLog).where(UsageLog.user_id == user_id))
    await db.execute(sql_delete(AuditLog).where(AuditLog.user_id == user_id))

    # 8. Finally — delete user row (cascade: UserProfile + DriveConnection)
    user_row = await db.get(User, user_id)
    if user_row:
        await db.delete(user_row)

    await db.commit()

    # 9. Disk: remove per-user upload directory (empty after files deleted)
    try:
        import shutil
        user_upload_dir = os.path.join(UPLOAD_DIR, user_id)
        if os.path.isdir(user_upload_dir):
            shutil.rmtree(user_upload_dir, ignore_errors=True)
    except Exception as e:
        logger.warning("delete_account: rmtree upload dir failed: %s", e)

    # 10. Vector index in-memory dict — drop user's entry entirely
    try:
        from . import vector_search as _vs
        _vs._user_indexes.pop(user_id, None)
        _vs._user_doc_counts.pop(user_id, None)
        _vs._user_idf.pop(user_id, None)
    except Exception:
        pass

    logger.info(
        "delete_account: user=%s files=%d drive=%d vector=%d cache=%d errors=%d",
        user_id[:8] + "..", stats["files_deleted"], stats["drive_files_trashed"],
        stats["vector_index_cleaned"], stats["llamaparse_cache_purged"], stats["errors"],
    )
    return {"status": "ok", "message": "Account permanently deleted", "stats": stats}


# ═══════════════════════════════════════════
# MCP / CONNECTOR APIs (v4 — new)
# ═══════════════════════════════════════════

class MCPTokenRequest(BaseModel):
    # v10.0.x — P3-12 · validation · กัน UI layout พังจาก empty/over-long token names
    label: str = Field("Default Token", min_length=1, max_length=80)

    @field_validator("label")
    @classmethod
    def _strip_and_validate_label(cls, v: str) -> str:
        if v is None:
            return "Default Token"
        s = v.strip()
        if not s:
            raise ValueError("Token name ห้ามว่าง")
        if len(s) > 80:
            raise ValueError(f"Token name ยาวเกิน 80 ตัวอักษร (ปัจจุบัน {len(s)})")
        return s

class MCPToolCallRequest(BaseModel):
    tool: str
    params: dict = {}


@app.get("/api/mcp/info")
async def api_mcp_info(request: Request, current_user: User = Depends(get_current_user)):
    """Get MCP server info and available tools — per-user URL."""
    base_url = str(request.base_url).rstrip('/')
    # Fly.io reverse proxy sends X-Forwarded-Proto
    if request.headers.get("x-forwarded-proto") == "https":
        base_url = base_url.replace("http://", "https://", 1)
    return {
        "mcp_server_url": f"{base_url}/api/mcp/tools/call",
        "mcp_connector_url": f"{base_url}/mcp/{current_user.mcp_secret}",
        "auth_type": "bearer",
        "scope": "read+write",
        "version": f"v{APP_VERSION}",
        "available_tools": list(TOOL_REGISTRY.values()),
        "tool_count": len(TOOL_REGISTRY),
    }


@app.post("/api/mcp/tokens")
async def api_generate_token(
    req: MCPTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a new MCP Bearer token."""
    result = await generate_token(db, current_user.id, req.label)
    return result


@app.get("/api/mcp/tokens")
async def api_list_tokens(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all MCP tokens."""
    tokens = await list_tokens(db, current_user.id)
    return {"tokens": tokens, "count": len(tokens)}


@app.delete("/api/mcp/tokens/{token_id}")
async def api_revoke_token(token_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Revoke an MCP token."""
    revoked = await revoke_token(db, token_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "ok", "message": "Token revoked"}


@app.post("/api/mcp/test")
async def api_test_connection(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Test MCP connection with a Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"status": "error", "message": "Missing or invalid Authorization header"}

    raw_token = authorization.split(" ", 1)[1]
    token_info = await validate_token(db, raw_token)

    if not token_info:
        return {"status": "error", "message": "Invalid or revoked token"}

    return {
        "status": "success",
        "message": "Connection successful",
        "user_id": token_info["user_id"],
        "scope": token_info["scope"],
        "token_label": token_info["label"],
    }


@app.post("/api/mcp/tools/call")
async def api_mcp_tool_call(
    req: MCPToolCallRequest,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Main MCP tool dispatcher — called by Claude custom connector."""
    # Validate token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = authorization.split(" ", 1)[1]
    token_info = await validate_token(db, raw_token)

    if not token_info:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")

    # Call tool
    result = await call_tool(
        db=db,
        user_id=token_info["user_id"],
        token_id=token_info["token_id"],
        tool_name=req.tool,
        params=req.params,
    )
    return result


@app.get("/api/mcp/logs")
async def api_mcp_logs(
    tool: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get MCP usage logs."""
    logs = await get_usage_logs(db, current_user.id, tool, status, limit)
    return {"logs": logs, "count": len(logs)}


# ─── MCP TOOL PERMISSIONS (v5.1 — per-user) ───

# In-memory permissions store — per user (persists until restart)
MCP_PERMISSIONS: dict = {}  # user_id -> {tool_name -> bool}

@app.get("/api/mcp/permissions")
async def api_get_permissions(current_user: User = Depends(get_current_user)):
    """Get current tool permissions for this user."""
    user_perms = MCP_PERMISSIONS.get(current_user.id, {})
    return {"permissions": user_perms}

@app.put("/api/mcp/permissions")
async def api_set_permissions(request: Request, current_user: User = Depends(get_current_user)):
    """Set tool permissions for this user."""
    body = await request.json()
    perms = body.get("permissions", {})
    if current_user.id not in MCP_PERMISSIONS:
        MCP_PERMISSIONS[current_user.id] = {}
    MCP_PERMISSIONS[current_user.id].update(perms)
    return {"status": "ok", "permissions": MCP_PERMISSIONS[current_user.id]}


# ─── HELPERS ───

def _serialize_file(f: File) -> dict:
    # v7.0.1 — surface storage location so UI can show "on Drive" badge + open link
    drive_id = getattr(f, "drive_file_id", None)
    storage_source = getattr(f, "storage_source", "local") or "local"
    if drive_id:
        drive_link: str | None = f"https://drive.google.com/file/d/{drive_id}/view"
        storage_location = "drive"
    else:
        drive_link = None
        storage_location = "server"

    return {
        "id": f.id,
        "filename": f.filename,
        "filetype": f.filetype,
        "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else "",
        "processing_status": f.processing_status,
        "text_length": len(f.extracted_text or ""),
        "importance_score": f.insight.importance_score if f.insight else None,
        "importance_label": f.insight.importance_label if f.insight else None,
        "is_primary": f.insight.is_primary_candidate if f.insight else False,
        "has_summary": f.summary is not None,
        "snippet": (f.summary.summary_text[:120] + "...") if f.summary and f.summary.summary_text else "",
        # v3 — metadata
        "tags": json.loads(f.tags or "[]"),
        "sensitivity": f.sensitivity or "normal",
        "freshness": f.freshness or "current",
        "source_of_truth": f.source_of_truth or False,
        # v5.9.3 — locked data
        "is_locked": getattr(f, "is_locked", False) or False,
        "locked_reason": getattr(f, "locked_reason", None),
        # v7.0.1 — BYOS storage location surface
        "storage_location": storage_location,    # "drive" | "server"
        "storage_source": storage_source,        # "local" | "drive_uploaded" | "drive_picked"
        "drive_file_id": drive_id,
        "drive_web_link": drive_link,
        # v7.5.0 — extraction status + big-file metadata for badge UI
        "extraction_status": getattr(f, "extraction_status", "ok") or "ok",
        "chunk_count": getattr(f, "chunk_count", 0) or 0,
        "is_truncated": bool(getattr(f, "is_truncated", False)),
        # v9.1.0 — Raw File Vault classification
        "file_kind": getattr(f, "file_kind", "processed") or "processed",
        "vault_reason": (
            "format not supported by AI extraction"
            if getattr(f, "file_kind", "") == "vault_only"
            else None
        ),
        # v9.4.0 — Upload Queue + Visible Progress fields
        "progress_step": getattr(f, "progress_step", None),
        "progress_pct": getattr(f, "progress_pct", None),
        "queued_at": (
            f.queued_at.isoformat() + "Z" if getattr(f, "queued_at", None) else None
        ),
        "extract_started_at": (
            f.extract_started_at.isoformat() + "Z" if getattr(f, "extract_started_at", None) else None
        ),
        "extract_completed_at": (
            f.extract_completed_at.isoformat() + "Z" if getattr(f, "extract_completed_at", None) else None
        ),
        "extract_error": getattr(f, "extract_error", None),
        "attempt_count": getattr(f, "attempt_count", 0) or 0,
    }


# ═══════════════════════════════════════════
# MCP STREAMABLE HTTP TRANSPORT (for Claude Custom Connector)
# ═══════════════════════════════════════════

def _build_mcp_tools_list():
    """Convert our tool registry to MCP-spec tool format."""
    tools = []
    for tool in TOOL_REGISTRY.values():
        # Build JSON Schema for inputSchema
        properties = {}
        required = []
        for p in tool.get("params", []):
            if p["type"] == "array":
                prop = {"type": "array", "items": {"type": "string"}}
            else:
                prop = {"type": p["type"]}
            if "default" in p:
                prop["default"] = p["default"]
            properties[p["name"]] = prop
            if p.get("required"):
                required.append(p["name"])

        tool_def = {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        # v5.4: Add MCP annotations for AI client behavior hints
        if "annotations" in tool:
            tool_def["annotations"] = tool["annotations"]
        tools.append(tool_def)
    return tools


@app.post("/mcp/{secret}")
async def mcp_streamable_http(secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    """MCP Streamable HTTP transport — JSON-RPC 2.0 endpoint for Claude Custom Connector.
    
    v5.1: Each user has their own secret URL. The secret maps to a specific user.
    All data operations are scoped to that user only.
    """
    # v5.1 — Resolve user from per-user secret (no global fallback)
    user_result = await db.execute(
        select(User).where(User.mcp_secret == secret, User.is_active == True)
    )
    mcp_owner = user_result.scalar_one_or_none()
    if not mcp_owner:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid MCP secret — user not found"}, "id": None},
            status_code=401,
        )
    mcp_user_id = mcp_owner.id
    
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
        )

    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    logger.info(f"MCP request: method={method}, id={msg_id}, user={mcp_owner.email}")

    # ── Notification (no id) — return 202 Accepted ──
    if msg_id is None:
        return JSONResponse(content=None, status_code=202)

    # ── initialize ──
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "personal-data-bank",
                    "version": APP_VERSION,
                },
            },
        })

    # ── tools/list ──
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": _build_mcp_tools_list(),
            },
        })

    # ── tools/call ──
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in TOOL_REGISTRY:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            })


        # Check if tool is disabled by this user's permissions
        user_perms = MCP_PERMISSIONS.get(mcp_user_id, {})
        if user_perms.get(tool_name) is False:
            if arguments.get("admin_key") != ADMIN_PASSWORD:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Tool '{tool_name}' is disabled. Enable it in MCP Setup or use admin_login to get the admin_key."}],
                        "isError": True,
                    },
                })

        # Call the tool using our existing dispatcher
        tool_result = await call_tool(db, mcp_user_id, "mcp-connector", tool_name, arguments)

        # Format result as MCP content
        if tool_result["status"] == "success":
            result_data = tool_result["result"]
            
            # v5.4: Check for special __mcp_content key (used by export_file_to_chat)
            # This allows tools to return rich MCP content (EmbeddedResource, etc.)
            if isinstance(result_data, dict) and "__mcp_content" in result_data:
                content = result_data["__mcp_content"]
            else:
                text_content = json.dumps(result_data, ensure_ascii=False, indent=2)
                content = [{"type": "text", "text": text_content}]
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": content,
                },
            })
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {tool_result['result'].get('error', 'Unknown error')}"}],
                    "isError": True,
                },
            })

    # ── ping ──
    elif method == "ping":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {},
        })

    # ── Unknown method ──
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


# Billing (Stripe) endpoints removed in v9.6.0.
# Quota / plan system ยังทำงานอยู่ผ่าน plan_limits.py — admin upgrade ผ่าน
# /api/admin/users/.../plan ได้. See docs/restoration/billing-restore.md.


# ═══════════════════════════════════════════════════════════════════
# BYOS — Google Drive (v7.0 — foundation only, full flow pending creds)
# ═══════════════════════════════════════════════════════════════════
# กฎ: ทุก endpoint ตรงนี้ short-circuit เป็น 503 ถ้า env vars ยังไม่ครบ
# (is_byos_configured()) — ทำให้ BYOS feature "ปิดเงียบๆ" ใน production จนกว่า
# ผู้ดูแลจะ deploy พร้อม Google OAuth credentials. Managed Mode ไม่กระทบ.
from . import config as _byos_cfg  # dynamic resolution — รองรับ config reload ใน tests
from . import drive_oauth as _drive_oauth
from .drive_layout import (
    DRIVE_ROOT_FOLDER_NAME,
    DRIVE_SCHEMA_VERSION,
    STORAGE_MODE_BYOS,
    STORAGE_MODE_MANAGED,
    VALID_STORAGE_MODES,
)


def _byos_503_error():
    """Standard 503 response เมื่อ BYOS env vars ยังไม่ครบ — endpoint จะ return อันนี้"""
    raise HTTPException(
        status_code=503,
        detail={
            "error": {
                "code": "GOOGLE_OAUTH_NOT_CONFIGURED",
                "message": (
                    "BYOS feature ยังไม่พร้อมใช้งาน — กำลังรอ Google OAuth credentials "
                    "ของผู้ดูแลระบบ. Managed Mode ใช้งานได้ปกติ"
                ),
            }
        },
    )


@app.get("/api/drive/status")
async def api_drive_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ดู BYOS status ของ user — ใช้สำหรับ frontend ตัดสินใจ render UI.

    Public-ish endpoint (auth required) — ไม่ short-circuit 503 เพราะ frontend
    ต้องเรียกได้เพื่อรู้ว่า feature available หรือไม่.
    """
    drive_email: str | None = None
    last_sync_at: str | None = None
    last_sync_status: str | None = None
    last_sync_error: str | None = None
    if user.storage_mode == STORAGE_MODE_BYOS:
        result = await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == user.id)
        )
        conn = result.scalar_one_or_none()
        if conn:
            drive_email = conn.drive_email
            last_sync_at = conn.last_sync_at.isoformat() if conn.last_sync_at else None
            last_sync_status = conn.last_sync_status
            # v9.3.0 — expose last_sync_error so UI can render "เชื่อมต่อใหม่"
            # prompt with reason (e.g., invalid_grant after token revoke / app migrate).
            last_sync_error = conn.last_sync_error

    return {
        "feature_available": _byos_cfg.is_byos_configured(),
        "storage_mode": user.storage_mode,
        "drive_connected": drive_email is not None,
        "drive_email": drive_email,
        "drive_root_folder_name": DRIVE_ROOT_FOLDER_NAME,
        "drive_schema_version": DRIVE_SCHEMA_VERSION,
        "last_sync_at": last_sync_at,
        "last_sync_status": last_sync_status,
        "last_sync_error": last_sync_error,
        "oauth_mode": "testing",  # หลัง Google verification → "production"
    }


@app.get("/api/drive/oauth/init")
async def api_drive_oauth_init(user: User = Depends(get_current_user)):
    """เริ่ม OAuth flow — return auth_url ให้ frontend redirect."""
    if not _byos_cfg.is_byos_configured():
        _byos_503_error()
    try:
        return _drive_oauth.init_oauth(user.id)
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "OAUTH_INIT_FAILED", "message": str(e)}},
        )


@app.get("/api/drive/oauth/callback")
async def api_drive_oauth_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Google redirect กลับมาที่นี่หลัง user grant consent.

    Note: ไม่มี JWT auth — verify ผ่าน CSRF state token แทน.
    หลัง process เสร็จ redirect ไป frontend (success or error param).
    """
    from fastapi.responses import RedirectResponse

    if not _byos_cfg.is_byos_configured():
        _byos_503_error()

    # User denied consent → Google redirect with ?error=access_denied
    if error:
        return RedirectResponse(
            url=f"/app?drive_connected=false&error={error}",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url="/app?drive_connected=false&error=missing_params",
            status_code=302,
        )

    # v10.0.8 — wrap ALL non-ValueError ใน redirect ไม่ raw-500 หน้าจอ.
    # เดิม: googleapiclient.HttpError / RuntimeError / network exception จาก
    # _drive_oauth.handle_callback() bubble เป็น Internal Server Error
    try:
        result = await _drive_oauth.handle_callback(code, state)
    except ValueError as e:
        # state หมดอายุ / ถูกใช้แล้ว — มักเกิดหลัง server restart ระหว่าง OAuth flow
        logger.warning("drive_oauth callback: invalid state — %s", e)
        return RedirectResponse(
            url="/app?drive_connected=false&error=invalid_state",
            status_code=302,
        )
    except Exception as e:
        # PKCE mismatch / Google API error / network — log full + friendly redirect
        logger.exception("drive_oauth callback: handle_callback failed: %s", e)
        return RedirectResponse(
            url="/app?drive_connected=false&error=oauth_callback_failed",
            status_code=302,
        )

    # v10.0.8 — DB-write phase ก็ wrap เผื่อ encrypt_refresh_token / DB commit fail
    try:
        # Save connection to DB (encrypted refresh_token)
        encrypted = _drive_oauth.encrypt_refresh_token(result["refresh_token"])
        new_conn = DriveConnection(
            user_id=result["user_id"],
            drive_email=result["drive_email"],
            refresh_token_encrypted=encrypted,
            drive_root_folder_id=result["drive_root_folder_id"],
            last_sync_status="pending",
        )

        # Upsert: ถ้า user re-connect (เดิมมี connection อยู่) → update แทน insert
        existing_q = await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == result["user_id"])
        )
        existing = existing_q.scalar_one_or_none()
        if existing:
            existing.drive_email = new_conn.drive_email
            existing.refresh_token_encrypted = new_conn.refresh_token_encrypted
            existing.drive_root_folder_id = new_conn.drive_root_folder_id
            existing.last_sync_status = "pending"
            existing.last_sync_error = None
            existing.revoked_at = None
        else:
            db.add(new_conn)

        # Auto-flip user เป็น byos mode (ถ้ายังไม่ใช่) — convenience: connect = opt in
        user_q = await db.execute(select(User).where(User.id == result["user_id"]))
        user_obj = user_q.scalar_one_or_none()
        if user_obj and user_obj.storage_mode != STORAGE_MODE_BYOS:
            user_obj.storage_mode = STORAGE_MODE_BYOS

        await db.commit()
    except Exception as e:
        logger.exception("drive_oauth callback: DB save failed: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
        return RedirectResponse(
            url="/app?drive_connected=false&error=db_save_failed",
            status_code=302,
        )

    logger.info(
        "BYOS: user %s connected Drive (email=%s, folder_id=%s)",
        result["user_id"], result["drive_email"], result["drive_root_folder_id"],
    )

    # Initialize folder layout (root + 7 sub-folders + _meta/version.txt) — best effort
    try:
        from .storage_router import init_drive_folder_layout
        await init_drive_folder_layout(result["user_id"], db)
    except Exception as e:
        logger.warning("BYOS: layout init wrapper failed (non-fatal): %s", e)

    return RedirectResponse(url="/app?drive_connected=true", status_code=302)


@app.post("/api/drive/disconnect")
async def api_drive_disconnect(
    keep_files: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ตัดการเชื่อมต่อ Drive ของ user.

    keep_files=True (default): เก็บ cache ฝั่งเรา + หยุด sync — user เปิด Drive ดูเองได้
    keep_files=False: ลบ File rows ที่ link กับ Drive ฝั่งเรา (Drive content ไม่แตะ)

    Drive folder ของ user ใน /Personal Data Bank/ จะไม่ถูกลบ — user ลบเองถ้าต้องการ.
    """
    if not _byos_cfg.is_byos_configured():
        _byos_503_error()

    result = await db.execute(
        select(DriveConnection).where(DriveConnection.user_id == user.id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NO_DRIVE_CONNECTION",
                    "message": "User นี้ยังไม่ได้เชื่อมต่อ Drive",
                }
            },
        )

    # Revoke token ที่ Google (best-effort — ไม่ raise ถ้า fail)
    try:
        plaintext = _drive_oauth.decrypt_refresh_token(conn.refresh_token_encrypted)
        revoked = _drive_oauth.revoke_refresh_token(plaintext)
        logger.info("BYOS: revoke_refresh_token result for user %s: %s", user.id, revoked)
    except RuntimeError as e:
        # encryption key เปลี่ยน — ทำต่อได้ (ลบ DB row อยู่ดี)
        logger.warning("BYOS: could not decrypt token for revoke: %s", e)

    if not keep_files:
        # Soft-cleanup: mark file rows ที่ผูก Drive ว่า unlinked (ไม่ลบจริง — protect against
        # accidental data loss; ผู้ใช้ที่ต้องการลบจริงใช้ delete file endpoint แยกต่อ)
        await db.execute(
            File.__table__.update()
            .where(File.user_id == user.id, File.drive_file_id.isnot(None))
            .values(drive_file_id=None, storage_source="local")
        )

    # Switch user back to managed mode
    user.storage_mode = STORAGE_MODE_MANAGED

    # Delete connection row (revoke complete)
    await db.delete(conn)
    await db.commit()

    return {"status": "disconnected", "keep_files": keep_files}


@app.put("/api/storage-mode")
async def api_set_storage_mode(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """สลับโหมดเก็บข้อมูลระหว่าง managed ↔ byos.

    Body: {"mode": "managed" | "byos"}

    หมายเหตุ: ใน foundation rev นี้ยัง **ไม่** trigger migration job
    (managed → byos จะ upload ไฟล์เก่าขึ้น Drive). Migration logic จะมาใน Phase 2 —
    endpoint นี้แค่ flip column ตอนนี้ + ต้องมี drive_connection ก่อนถึง byos
    """
    if not _byos_cfg.is_byos_configured():
        _byos_503_error()

    mode = body.get("mode") if isinstance(body, dict) else None
    if mode not in VALID_STORAGE_MODES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_STORAGE_MODE",
                    "message": f"mode ต้องเป็น {sorted(VALID_STORAGE_MODES)}",
                }
            },
        )

    if mode == STORAGE_MODE_BYOS:
        # ตรวจว่า user เชื่อม Drive แล้วก่อน switch
        result = await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "BYOS_REQUIRES_DRIVE_CONNECTION",
                        "message": "ต้องเชื่อมต่อ Drive ก่อน switch ไป BYOS mode",
                    }
                },
            )

    user.storage_mode = mode
    await db.commit()
    return {"status": "ok", "storage_mode": mode}


@app.post("/api/drive/sync")
async def api_drive_sync(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a bi-directional sync between Drive and local cache.

    Push: any local files (storage_source='drive_uploaded' but no drive_file_id)
          → upload to /Personal Data Bank/raw/
    Pull: any new/updated/deleted files in /Personal Data Bank/raw/
          → reflect into local cache (Drive wins on conflict)

    Returns sync stats (files pulled/pushed, conflicts, errors, duration).
    Requires: BYOS configured + user.storage_mode='byos' + Drive connected.
    """
    if not _byos_cfg.is_byos_configured():
        _byos_503_error()

    if user.storage_mode != STORAGE_MODE_BYOS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "NOT_BYOS_MODE",
                    "message": "Sync is only available in BYOS storage mode",
                }
            },
        )

    conn_q = await db.execute(
        select(DriveConnection).where(DriveConnection.user_id == user.id)
    )
    if not conn_q.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "NO_DRIVE_CONNECTION",
                    "message": "ยังไม่ได้เชื่อมต่อ Drive — กดปุ่ม Connect Drive ก่อน",
                }
            },
        )

    from .drive_sync import sync_user_drive
    stats = await sync_user_drive(user.id, db)
    # v9.3.5 — แยก status ระหว่าง clean sync vs partial failure
    # frontend ใช้ stats.errors > 0 เพื่อแสดง toast warning อยู่แล้ว
    # status field ตอนนี้ consistent: "ok" = errors=0, "completed_with_errors" = errors>0
    sync_status = "completed_with_errors" if stats.get("errors", 0) > 0 else "ok"
    return {"status": sync_status, "stats": stats}


# Billing redirect routes (/billing/success, /pricing, /billing/cancelled)
# removed in v9.6.0. See docs/restoration/billing-restore.md.


# ─── SERVE FRONTEND (legacy-frontend/) ───

FRONTEND_DIR = os.path.join(BASE_DIR, "legacy-frontend")


def _serve_html(filename: str):
    """Helper: serve a frontend HTML file with no-cache headers."""
    path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(path):
        resp = FileResponse(path, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    raise HTTPException(status_code=404, detail=f"{filename} not found")


@app.get("/")
async def serve_landing():
    """Public landing page — for unauthenticated visitors."""
    return _serve_html("landing.html")


@app.get("/app")
async def serve_app():
    """Authenticated workspace shell — JS guards redirect to / if no token."""
    return _serve_html("app.html")


@app.get("/admin")
async def serve_admin():
    """v8.2.0 — Admin panel (separate page, JS calls /api/admin/me to verify role).

    ห้าม server-side gate — ปล่อยให้ admin.js เรียก /api/admin/me ตรวจสิทธิ์เอง
    (ถ้าไม่ admin → backend return 403 → JS redirect /app). Pattern เดียวกับ /app.
    """
    return _serve_html("admin.html")

@app.get("/reset-password")
async def serve_reset_password_page():
    """Serve landing page which will catch the token parameter and show reset modal."""
    return _serve_html("landing.html")


@app.get("/legacy")
async def serve_legacy():
    """Alias — same as root (backward compatibility)."""
    return _serve_html("landing.html")


@app.get("/legacy/{filename}")
async def serve_legacy_static(filename: str):
    """Serve frontend static files via /legacy/ prefix."""
    filepath = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        resp = FileResponse(filepath)
        if filename.endswith(('.js', '.css', '.html')):
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    raise HTTPException(status_code=404)


@app.get("/guide/{filename}")
async def serve_guide_static(filename: str):
    """Serve guide images."""
    filepath = os.path.join(FRONTEND_DIR, "guide", filename)
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404)


@app.get("/{filename}")
async def serve_static(filename: str):
    """Serve static files from frontend directory."""
    filepath = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        resp = FileResponse(filepath)
        if filename.endswith(('.js', '.css', '.html')):
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    raise HTTPException(status_code=404)

