# Plan: Foundation — Pre-launch + Signed URLs (LINE-Focused)

> 🔄 **REVISED 2026-05-02 (3rd time)** — User pivot: Focus LINE bot, defer other systems
>
> **Original scope:** A (pre-launch backlog) + B (MCP USP) + C (signed URLs)
> **New scope:** A ✅ (already done) + C only — Section B (MCP USP) **deferred** to v7.7.0 หลัง LINE ship

**Author:** แดง (Daeng)
**Date:** 2026-05-02 (3rd revision)
**Status:**
- Section A: ✅ **DONE** (Phase A1 + A2 complete, 31/31 tests pass, awaiting commit)
- Section B: ⏸️ **DEFERRED** to v7.7.0 (defer per user 2026-05-02)
- Section C: 🔴 `draft` — proceeding to build (REQUIRED for LINE bot file delivery)
**Target version:** **v7.6.0** — minimum LINE-prerequisite foundation
**Estimated effort:** Section C only ~1-2 working days
**Strategic direction:** LINE-first per user 2026-05-02 — ทำ minimum primitive ก่อน → จับ LINE bot v8.0.0 เป็น focus หลัก

---

## 🎯 Goal (REVISED — LINE-focused minimum)

วาง **minimum primitive ที่ LINE bot ต้องใช้** ใน v7.6.0 — ที่เหลือเลื่อนหลัง LINE ship

**Sections:**
- ✅ **Section A (DONE):** Pre-launch backlog
  - A.1 Plan limits restored (BACKLOG-008)
  - A.2 Email service via Resend (BACKLOG-009)
  - **31/31 tests pass** + 133/133 regression pass
  - **Awaiting commit** (working tree)
- ⏸️ **Section B (DEFERRED):** MCP USP (`upload_from_url` + wire `upload_text`)
  - Defer to **v7.7.0** หลัง LINE ship
  - ไม่เกี่ยว LINE bot โดยตรง (web/MCP feature)
- 🔴 **Section C (TODO):** Universal signed download URLs
  - **REQUIRED** สำหรับ LINE bot — ใช้แทน "ส่ง PDF กลับ user" (LINE limitation)
  - ~1-2 working days

**ทำเสร็จแล้วได้อะไร:**
1. ✅ Plan limits enforce + email service ทำงาน (Section A done)
2. 🆕 Universal `/d/{token}` endpoint — primitive สำหรับ LINE file delivery + web sharing
3. 🚀 Foundation พร้อมสำหรับ v8.0.0 LINE Bot ทันที (Section A + C ครบ)

**สิ่งที่ skip ไว้ก่อน:**
- ❌ MCP `upload_from_url` (Section B) — defer v7.7.0
- ❌ MCP `upload_text` wiring (Section B) — defer v7.7.0
- ❌ `url_fetcher.py` (Section B) — defer v7.7.0

---

## ✅ Resolved Decisions (จาก user 2026-05-02)

| # | Decision | สถานะ |
|---|---|---|
| D1 | **Foundation-first strategy** — ไม่ทำ LINE bot ตอนนี้ | ✅ baked-in |
| D2 | **No new external dependency** — reuse what's already in PDB | ✅ baked-in |
| D3 | LINE bot plan v8.0.0 = **defer** ไม่ลบ — เก็บไว้เป็น reference เมื่อพร้อม | ✅ baked-in |
| D4 | **Email service: Resend** (per BACKLOG-009 recommendation) — modern API, free 3000/month, simple Python SDK | 🟡 default — user ยืนยัน |
| D5 | **Plan limits: restore + keep v7.5.0 file type expansion** — file types ที่ extend ใน v7.5.0 (xlsx/pptx/html/json/rtf/webp/jpeg) คงไว้ทั้ง 2 plans | 🟡 default — user ยืนยัน |
| D6 | **MCP upload primary path = URL fetch** (Phase 1) — Base64 file upload เลื่อน Phase 2 | ✅ baked-in (per research) |
| D7 | **Signed URL TTL = 30 min default, configurable up to 1 hour** | 🟡 default — user ยืนยัน |
| D8 | **Auto-organize default = true** สำหรับ MCP upload tools — UX ลื่น | ✅ baked-in (per research) |

---

## 📚 Context

### Current State (v7.5.0 ที่ ship แล้ว)
- Production: https://personaldatabank.fly.dev/
- 80+ endpoints, 30 MCP tools, 21 DB tables
- Plan limits **neutered** — `999999` ทุก field ทุก plan (testing mode)
- Password reset **returns reset_token in JSON** — ไม่ส่ง email
- MCP `upload_text` ทำงานแบบ **partial** — ขาด:
  - ❌ ไม่เรียก `check_upload_allowed()`
  - ❌ ไม่คำนวณ `content_hash`
  - ❌ ไม่เรียก `push_raw_file_to_drive_if_byos()`
  - ❌ ไม่ trigger organize อัตโนมัติ
- ไม่มี MCP tool สำหรับ binary file ingestion (URL fetch หรือ base64)

### Research Foundations (verify ใน .agent-memory/research/)
- [mcp-file-upload-deep-dive.md](../research/mcp-file-upload-deep-dive.md) — MCP spec ไม่มี first-class binary upload, base64-in-string เป็น path เดียว, URL fetch = realistic primary
- [chat-bot-platforms-feasibility.md](../research/chat-bot-platforms-feasibility.md) — LINE/TG/Discord deep dive
- [competitor-deep-dive.md](../research/competitor-deep-dive.md) — Global + Thai market — PDB unique 5 USPs (auto-organize + graph + MCP + BYOS + personality)

### Why these 3 sections together
ทั้ง 3 sections form a **coherent launch-ready release**:
- **Section A (Pre-launch backlog)** = unblock public launch
- **Section B (MCP USP)** = differentiator ที่จับต้องได้ + ขายได้
- **Section C (Signed download URLs)** = primitive ที่ MCP responses ใช้ทันที + web sharing + future channels reuse

**Coupling rationale:** Section B (MCP upload) ต้องใช้ Section C (signed URLs) ใน response เมื่อ AI ขอไฟล์กลับ. Section A (plan limits) ต้องเปิดก่อน Section B ship เพราะ MCP จะทะลุ quota ได้ทันทีถ้าไม่ enforce

---

## 📁 Files to Create / Modify

### Section A — Pre-launch Backlog

#### 🆕 Create
- `backend/email_service.py` (~120 lines) — Resend API wrapper + email templates
- `tests/test_email_service.py` (~80 lines) — mock Resend SDK + verify template rendering
- `docs/EMAIL_SETUP.md` (~50 lines) — Resend account setup walkthrough + DNS records

#### 🔧 Modify
- `backend/plan_limits.py` — restore production values (lines 18-44):
  - Free: 1 pack, 5 files, 50MB storage, 10MB max file, 5 summaries/mo, 10 exports/mo, 0 refresh, semantic disabled, 0 history days
  - Starter: 5 packs, 50 files, 1024MB storage, 20MB max file, 100 summaries/mo, 300 exports/mo, 10 refresh/mo, semantic enabled, 7 history days
  - Keep v7.5.0 expanded `allowed_file_types` (xlsx/pptx/html/json/rtf/webp/jpeg) — engineering investment ที่ไม่ throwaway
  - Remove ⚠️ TESTING MODE comment
- `backend/auth.py` — `request_password_reset()` (lines 249-282):
  - Wire `email_service.send_password_reset_email()`
  - Drop `reset_token` from JSON response (security fix)
  - Add fallback: ถ้า email service fail → log + return generic success (anti-enumeration)
- `backend/config.py` — เพิ่ม env vars + `is_email_configured()` helper:
  - `RESEND_API_KEY`
  - `EMAIL_FROM_ADDRESS` (e.g., `noreply@personaldatabank.fly.dev`)
  - `EMAIL_FROM_NAME` (e.g., `Personal Data Bank`)
- `requirements.txt` — เพิ่ม `resend>=2.0.0` (Python SDK)
- `.env.example` — document new env vars
- `legacy-frontend/landing.html` — auth modal: ลบ "reset_token" debug display ถ้ามี (verify ก่อน)
- `legacy-frontend/landing.js` — `doForgotPassword()`: handle response shape ที่ไม่มี reset_token แล้ว → show "ตรวจอีเมลของคุณ" message
- `tests/test_production.py` — update tests ที่ expect `reset_token` ใน response

### Section B — MCP File Ingestion (USP)

#### 🆕 Create
- `backend/url_fetcher.py` (~180 lines) — SSRF-safe URL fetch helper:
  - `fetch_url_safely(url, max_size_bytes, allow_http=False, timeout_seconds=30) -> tuple[bytes, str, str]`
  - Returns (content, filename, mime_type)
  - Block private IPs (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, IPv6 private)
  - Force HTTPS (allow HTTP only ในกรณี explicit override flag — default off)
  - Limit redirects (max 5) + re-check SSRF after each redirect
  - Timeout 30s
  - Max content-length check (10 MB / configurable)
  - Filename inference: Content-Disposition → URL path → fallback `download_<timestamp>`
- `tests/test_url_fetcher.py` (~150 lines) — SSRF tests + redirect chain + size limits
- `tests/fixtures/mock_files/` — small test fixtures (sample.pdf, sample.txt, sample.png) สำหรับ url_fetcher tests

#### 🔧 Modify
- `backend/mcp_tools.py` — 2 changes:
  1. **Wire `upload_text` properly** (lines 1275-1325):
     - เรียก `check_upload_allowed()` (file_size_bytes, file_ext)
     - คำนวณ `compute_content_hash(content)`
     - เก็บ `content_hash` ใน DB
     - เรียก `push_raw_file_to_drive_if_byos()` (best-effort)
     - Add `auto_organize: bool = True` param — ถ้า True → trigger organize หลัง commit
     - Return enriched response: `{file_id, filename, organized: bool, drive_file_id?, content_hash}`
  2. **Add new tool `upload_from_url`** (TOOL_REGISTRY entry + handler `_tool_upload_from_url`):
     - Params: `url: str` (required), `filename: str` (optional), `auto_organize: bool` (default True)
     - Reuse: `url_fetcher.fetch_url_safely()` → `extract_text()` → same path as upload_text
     - Include `content_hash`, `BYOS push`, `plan limit check`, `auto_organize`
- `backend/main.py` — verify nothing breaks ใน `/mcp/{secret}` JSON-RPC endpoint
- `backend/organizer.py` — refactor: extract `organize_new_files_for_user(db, user_id)` ถ้าตอนนี้อยู่ใน main.py (กัน circular import)
- `tests/test_mcp_tools.py` — เพิ่ม tests สำหรับ:
  - `_tool_upload_text` ใหม่ (5 cases): plan limit, content_hash, BYOS push, auto-organize on/off, error path
  - `_tool_upload_from_url` (8 cases): SSRF, size limit, content-type detection, plan limit, auto-organize, BYOS push, redirects, malformed URL

### Section C — Signed Download URLs (Universal Primitive)

#### 🆕 Create
- `backend/signed_urls.py` (~80 lines):
  - `sign_download_token(file_id, user_id, ttl_seconds=1800) -> str` — JWT signed
  - `verify_download_token(token) -> dict` — raises on expired/invalid/wrong-scope
  - Default TTL 30 min, max 1 hour (configurable per call)
- `tests/test_signed_urls.py` (~100 lines) — JWT sign/verify/expiry/cross-user/scope tests

#### 🔧 Modify
- `backend/main.py` — เพิ่ม endpoint:
  - `GET /d/{token}?ttl=N` — public, JWT-verified
    - Decode token → load File → verify user_id ตรงกัน → FileResponse via storage_router (BYOS-aware)
    - Errors: 401 (invalid), 410 (expired), 403 (wrong user), 404 (file not found)
    - Cache headers: `Cache-Control: private, no-store`
- `backend/mcp_tools.py` — `_tool_get_file_link` (existing tool):
  - **Update implementation** ให้ใช้ `signed_urls.sign_download_token()`
  - Add `ttl_minutes` param (default 30, range 5-60)
  - Update tool description

---

## 📡 API Changes

### MCP Tool: `upload_text` — UPDATED (existing tool, fix gaps)

**Updated description:**
> "Upload text content as a new file. Auto-organizes by default. Respects plan limits and BYOS storage."

**Updated params:**
```json
{
  "filename": {"type": "string", "required": true},
  "content": {"type": "string", "required": true},
  "auto_organize": {"type": "boolean", "required": false, "default": true,
    "description": "Run AI organize immediately after upload (cluster + summary + graph)"}
}
```

**Updated response (success):**
```json
{
  "status": "uploaded" | "uploaded_and_organized",
  "file_id": "abc123",
  "filename": "notes.md",
  "filetype": "md",
  "text_length": 1234,
  "content_hash": "sha256-...",
  "drive_file_id": "drive-id-or-null",
  "storage_source": "local" | "drive_uploaded",
  "organized": true | false,
  "cluster_title": "AI Research"
}
```

**Errors (returned via MCP error response, not raise):**
- `PLAN_LIMIT_EXCEEDED` — file count, storage, file size, file type → include `upgrade: bool`
- `EMPTY_CONTENT` — content is empty
- `INTERNAL_ERROR` — unexpected

---

### MCP Tool: `upload_from_url` — NEW

**Tool name:** `upload_from_url`
**Category:** edit

**Description:**
> "Download a file from a public URL and ingest it into your Personal Data Bank. Auto-organizes by default. Supports PDF, DOCX, images, audio, plain text, and more. Max 10 MB. The URL must be publicly accessible (Google Drive shared link, Dropbox public link, web URL)."

**Params:**
```json
{
  "url": {"type": "string", "required": true,
    "description": "HTTPS URL of the file to fetch (max 10 MB)"},
  "filename": {"type": "string", "required": false,
    "description": "Optional override for filename. If omitted, inferred from Content-Disposition or URL"},
  "auto_organize": {"type": "boolean", "required": false, "default": true}
}
```

**Annotations:**
```json
{
  "title": "Upload from URL",
  "readOnlyHint": false,
  "destructiveHint": false,
  "idempotentHint": false,
  "openWorldHint": true
}
```

**Response 200 (success):**
```json
{
  "status": "uploaded" | "uploaded_and_organized",
  "file_id": "abc123",
  "filename": "thesis-2026.pdf",
  "filetype": "pdf",
  "text_length": 12345,
  "content_hash": "sha256-...",
  "drive_file_id": "drive-id-or-null",
  "storage_source": "local" | "drive_uploaded",
  "organized": true | false,
  "source_url": "https://example.com/thesis.pdf",
  "fetched_size_bytes": 234567
}
```

**Errors (MCP error response):**
- `INVALID_URL` — not a valid HTTP(S) URL
- `BLOCKED_HOST` — private IP / localhost / cloud metadata IP
- `HTTP_INSECURE` — HTTP not HTTPS (unless override flag)
- `FETCH_FAILED` — DNS error, timeout, 4xx/5xx response
- `SIZE_EXCEEDED` — Content-Length or actual size > 10 MB
- `UNSUPPORTED_MIME` — server returned MIME type ที่ไม่ใช่ allowed_file_types
- `EMPTY_RESPONSE` — 0 bytes returned
- `PLAN_LIMIT_EXCEEDED` — file count, storage, size — include `upgrade: bool`
- `INTERNAL_ERROR`

---

### REST: `GET /d/{token}` — NEW (public, JWT-verified)

**Auth:** ไม่มี JWT — token เอง = signed JWT (no Authorization header needed)

**Response 200:**
- `Response` (binary) — `Content-Type: application/octet-stream` + `Content-Disposition: attachment; filename="..."`

**Errors:**
- 401 `INVALID_TOKEN` — JWT decode fail / wrong scope
- 410 `LINK_EXPIRED` — token expired (`exp` past)
- 403 `WRONG_USER` — file.user_id ≠ token.user_id
- 404 `FILE_NOT_FOUND` — file deleted after token signed
- 503 `STORAGE_UNAVAILABLE` — BYOS Drive read fail

**Cache headers:**
- `Cache-Control: private, no-store` — prevent CDN caching

---

### MCP Tool: `get_file_link` — UPDATED (use signed_urls.py)

**Updated description:**
> "Get a temporary public download URL for a file. The URL is valid for 30 minutes (configurable up to 1 hour) and requires no authentication. Returns the signed URL — share with anyone, anywhere."

**Updated params:**
```json
{
  "file_id": {"type": "string", "required": true},
  "ttl_minutes": {"type": "integer", "required": false, "default": 30,
    "description": "URL validity in minutes. Min 5, max 60."}
}
```

**Updated response:**
```json
{
  "url": "https://personaldatabank.fly.dev/d/eyJhbGc...",
  "filename": "thesis-2026.pdf",
  "expires_at": "2026-05-02T15:30:00Z",
  "ttl_minutes": 30
}
```

---

## 💾 Data Model Changes

**No new tables** — Section A/B/C ทั้งหมด **reuse existing schema**:
- `users` (existing) — plan_limits ใช้ field เดิม
- `files` (existing) — `content_hash`, `drive_file_id`, `storage_source` columns ที่มีอยู่แล้ว
- ไม่มี migration ใหม่
- ไม่มี breaking schema change

**Why no schema change:** ทั้ง 3 sections เป็น code-level changes (logic + new tools + new endpoint). DB structure พอใช้อยู่แล้วจาก v6.x/v7.x

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Phase A — Pre-launch Backlog (~3-4 working days)

#### Step A.1: Restore plan_limits.py (~30 min) [BACKLOG-008]
1. แก้ `backend/plan_limits.py` lines 15-44:
   - ลบ comment `⚠️ TESTING MODE` + `TODO: Restore...`
   - ตั้งค่าใหม่ตาม **Original + v7.5.0 file type expansion (D5 default)**:
     ```python
     PLAN_LIMITS = {
         "free": {
             "context_pack_limit": 1,
             "file_limit": 5,
             "storage_limit_mb": 50,
             "max_file_size_mb": 10,            # original (NOT 200)
             "ai_summary_limit_monthly": 5,
             "export_limit_monthly": 10,
             "refresh_limit_monthly": 0,
             "semantic_search_enabled": False,
             "version_history_days": 0,
             "allowed_file_types": {"pdf", "docx", "txt", "md", "csv"},
         },
         "starter": {
             "context_pack_limit": 5,
             "file_limit": 50,
             "storage_limit_mb": 1024,
             "max_file_size_mb": 20,            # original (NOT 200)
             "ai_summary_limit_monthly": 100,
             "export_limit_monthly": 300,
             "refresh_limit_monthly": 10,
             "semantic_search_enabled": True,
             "version_history_days": 7,
             "allowed_file_types": {"pdf", "docx", "txt", "md", "csv",
                                    "png", "jpg", "jpeg", "webp",
                                    "xlsx", "pptx", "html", "json", "rtf"},
         },
     }
     ```
   - **Decision Q1 (open):** keep max_file_size original (10/20MB) หรือ recognize v7.5.0 work ด้วย bump (25/100MB)? — **default: keep original**, ค่อย bump ในแผน Pro/Power ทีหลัง
2. รัน `python -m pytest tests/test_production.py -k plan_limits` → verify pass
3. Manual smoke: register Free account → upload 6th file → expect 403 PLAN_LIMIT_EXCEEDED

#### Step A.2: Create email_service.py (~3 hours) [BACKLOG-009]
1. สร้าง `backend/email_service.py`:
   - `send_password_reset_email(to_email, user_name, reset_token) -> bool`
   - Bilingual HTML template (Thai primary + English fallback)
   - Plain text fallback
   - Async wrapper around sync Resend SDK (`run_in_executor`)
   - Graceful degradation: log + return False ถ้า Resend fail
2. แก้ `backend/config.py` เพิ่ม env vars + `is_email_configured()` helper
3. เพิ่ม `requirements.txt`: `resend>=2.0.0`
4. Update `.env.example` document

#### Step A.3: Wire request_password_reset (~1 hour) [BACKLOG-009]
1. แก้ `backend/auth.py` `request_password_reset()` (lines 249-282):
   - Import `email_service.send_password_reset_email`
   - Generate token เหมือนเดิม
   - Call email_service ส่ง email
   - **ลบ `response["reset_token"] = token`** (security fix)
   - ถ้า email send fail → log + return generic success
2. แก้ `tests/test_production.py` ที่ check `assert "reset_token" in response`

#### Step A.4: Frontend cleanup (~1 hour)
1. Verify `legacy-frontend/landing.html` + `landing.js` — ดูว่ามี debug display ของ reset_token ไหม
2. แก้ `landing.js` `doForgotPassword()` ให้ handle response ใหม่ (ไม่มี reset_token)
3. Manual test: forgot password flow → email arrives

#### Step A.5: Resend setup + Fly.io secrets (~30 min, ทำพร้อมกัน)
1. สมัคร Resend account: https://resend.com/api-keys
2. Verify domain `personaldatabank.fly.dev`:
   - Add DNS records (TXT + CNAME) ที่ Fly.io domain
   - Wait verification (5-60 min)
3. Generate API key + Fly secret:
   ```bash
   fly secrets set RESEND_API_KEY=re_xxx EMAIL_FROM_ADDRESS=noreply@personaldatabank.fly.dev
   ```

**Done criteria Phase A:**
- [ ] `plan_limits.py` restored → Free 5 files / 50MB / 10MB max / 1 pack / no semantic
- [ ] `request_password_reset()` ส่ง email จริงผ่าน Resend
- [ ] `reset_token` ไม่อยู่ใน response anymore
- [ ] Tests updated + passing
- [ ] Production deploy + manual smoke test password reset → email arrives in inbox

---

### Phase B — MCP File Ingestion USP (~4-5 working days)

#### Step B.1: Create url_fetcher.py (~5 hours)
1. สร้าง `backend/url_fetcher.py` (full implementation in plan above):
   - `URLFetchError` exception (with `code` for MCP error response)
   - `_is_blocked_host(hostname)` — DNS resolve + check against `_BLOCKED_NETS`
   - `_infer_filename(url, response, override)` — Content-Disposition → URL path → fallback
   - `fetch_url_safely(url, max_size_bytes, allow_http, timeout_seconds)` — main async function
2. **Why httpx (not requests):**
   - httpx รองรับ async natively (FastAPI ของ PDB เป็น async stack)
   - Manual redirect handling เพื่อ check SSRF หลังทุก redirect
   - Streaming + size cap mid-flight
3. Test cases (ทดสอบใน `tests/test_url_fetcher.py`):
   - Block 10.0.0.1, 127.0.0.1, 169.254.169.254 (AWS metadata)
   - Block IPv6 link-local (fe80::*)
   - Block redirect chain → private IP
   - Reject HTTP without `allow_http=True`
   - Reject Content-Length > max_size
   - Reject 0-byte response
   - Strip MIME params (`text/html; charset=utf-8` → `text/html`)
   - Filename inference from Content-Disposition (RFC 5987 `filename*`)

#### Step B.2: Refactor `organize_new_files` first (~1-2 hours)
1. **Verify** ว่า `organize_new_files` อยู่ที่ไหน (`grep -n "organize_new_files" backend/`)
2. ถ้าอยู่ใน main.py → ย้ายไป `backend/organizer.py` เป็น `organize_new_files_for_user(db, user_id)` (pure function)
3. ใน `main.py` `/api/organize-new` endpoint → call function ใหม่
4. **Why first:** กัน circular import ตอน B.3/B.4 import จาก organizer
5. Run regression tests → verify ไม่มีอะไรแตก

#### Step B.3: Wire `upload_text` properly (~2 hours)
แก้ `backend/mcp_tools.py` `_tool_upload_text` (lines 1275-1325):
- Import: `check_upload_allowed`, `compute_content_hash`, `push_raw_file_to_drive_if_byos`, `organize_new_files_for_user`
- Load user from DB (needed for plan limit + BYOS routing)
- เรียก `check_upload_allowed(db, user, len(content_bytes), ext)` — return MCP error ถ้าไม่ผ่าน
- คำนวณ `compute_content_hash(content)` + เก็บใน DB
- หลัง commit → `push_raw_file_to_drive_if_byos()` (best-effort)
- ถ้า `auto_organize=True` (default) → call `organize_new_files_for_user()`
- Return enriched response (file_id, content_hash, drive_file_id, organized, etc.)
- Error format: `{error: {code, message, upgrade?}}` (consistent with new tool)

#### Step B.4: Add `upload_from_url` tool (~3 hours)
1. แก้ `backend/mcp_tools.py` — เพิ่ม TOOL_REGISTRY entry:
   ```python
   "upload_from_url": {
       "name": "upload_from_url",
       "description": "Download a file from a public URL and ingest into PDB. Max 10 MB. Auto-organizes by default.",
       "params": [...],
       "category": "edit",
       "annotations": {...}
   }
   ```
2. เพิ่ม handler `_tool_upload_from_url(db, user_id, params)`:
   - `url_fetcher.fetch_url_safely(url, max_size_bytes=10*1024*1024)` → bytes + filename + mime
   - Plan limit check
   - Save to disk + DB (เหมือน /api/upload pattern)
   - `extract_text(raw_path, ext)` (reuse existing)
   - `compute_content_hash(extracted)`
   - BYOS push (best-effort)
   - Auto-organize (if flag)
3. Register dispatcher: ใน `call_tool()` function เพิ่ม case สำหรับ `upload_from_url`

**Done criteria Phase B:**
- [ ] `url_fetcher.py` SSRF tests pass (private IP / redirect chain / size / timeout / IPv6)
- [ ] `upload_text` tool: plan limit + content_hash + BYOS + auto-organize ทำงานทุกตัว
- [ ] `upload_from_url` tool: full pipeline ผ่าน end-to-end
- [ ] MCP usage logs แสดง tool calls
- [ ] Manual test: เรียกผ่าน Claude Desktop / mcp-remote → file ปรากฏใน PDB web

---

### Phase C — Universal Signed Download URLs (~1-2 working days)

#### Step C.1: Create signed_urls.py (~1.5 hours)
1. สร้าง `backend/signed_urls.py`:
   - `DownloadTokenError(code, message)` exception
   - `sign_download_token(file_id, user_id, ttl_seconds=1800)` — JWT (HS256), require fields: file_id, user_id, exp, iat, scope="download"
   - `verify_download_token(token)` — decode + check scope + raise on expired/invalid
2. Tests (`tests/test_signed_urls.py`):
   - Sign + verify round-trip
   - Expired token → DownloadTokenError("LINK_EXPIRED")
   - Wrong scope (e.g., login token) → DownloadTokenError("INVALID_TOKEN")
   - Garbage token → DownloadTokenError("INVALID_TOKEN")
   - Required fields enforced (file_id missing → invalid)
   - TTL clamp 60-3600 seconds

#### Step C.2: Add `GET /d/{token}` endpoint (~1 hour)
1. แก้ `backend/main.py` เพิ่ม endpoint:
   - Decode token via `verify_download_token`
   - Map errors:
     - `LINK_EXPIRED` → 410
     - `INVALID_TOKEN` → 401
   - Load File from DB → check user_id match (else 403)
   - Read bytes via `storage_router.fetch_file_bytes(file, db)` (BYOS-aware automatic)
   - Return `Response` with `Content-Disposition` + `Cache-Control: private, no-store`

#### Step C.3: Update `get_file_link` MCP tool (~30 min)
1. ดู existing `_tool_get_file_link` ใน mcp_tools.py
2. Update implementation:
   - Use `signed_urls.sign_download_token(file_id, user_id, ttl_seconds=ttl_minutes*60)`
   - URL = `f"{APP_BASE_URL}/d/{token}"`
   - Add `ttl_minutes` param (default 30, clamp 5-60)
3. Update tool description ใน TOOL_REGISTRY

**Done criteria Phase C:**
- [ ] `signed_urls.py` tests pass (sign + verify + expired + wrong scope + cross-user)
- [ ] `GET /d/{token}` works for managed user (read from disk)
- [ ] `GET /d/{token}` works for BYOS user (read from Drive via storage_router)
- [ ] `get_file_link` tool returns signed URL ที่ download ผ่านได้จริง
- [ ] Manual test: `get_file_link → curl URL → ได้ไฟล์`

---

## 🧪 Test Scenarios (สำหรับฟ้า) — DETAILED

> **ฟ้า อ่านที่นี่:** ทุก test case ต้องเขียนเป็น code (pytest หรือ smoke script)
> ห้ามทำแค่ "manual verify". ใช้ `monkeypatch` / `unittest.mock.patch` สำหรับ external (Resend, httpx, time)
> ทุก case มี **expected outcome** ระบุชัด — ไม่ใช่ "ทำงานปกติ"
> Test count target: **80+ cases** total (ก่อนหน้าผมเขียนไว้ 50 — เพิ่มเป็น 80+ ละเอียดกว่า)

---

### Section A — Pre-launch Backlog Tests (~20 cases)

#### Test File: `tests/test_plan_limits_restored.py`

**A.1 — Free Plan Limits (10 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| A1.1 | Free upload 5th file | user.plan='free', has 4 files (5MB each) | Upload 5MB pdf | ✅ Allowed (count 5/5) |
| A1.2 | Free upload 6th file rejected | user.plan='free', has 5 files | Upload 5MB pdf | ❌ `PLAN_LIMIT_EXCEEDED` + `upgrade=True` + msg ถึง "5 ไฟล์" |
| A1.3 | Free file size 10MB allowed | user.plan='free' | Upload exactly 10MB pdf | ✅ Allowed |
| A1.4 | Free file size 10.1MB rejected | user.plan='free' | Upload 10.1MB pdf | ❌ `PLAN_LIMIT_EXCEEDED` + msg ถึง "10MB" |
| A1.5 | Free file type .pdf allowed | user.plan='free' | Upload .pdf | ✅ Allowed |
| A1.6 | Free file type .docx allowed | user.plan='free' | Upload .docx | ✅ Allowed |
| A1.7 | Free file type .png REJECTED | user.plan='free' | Upload .png | ❌ `PLAN_LIMIT_EXCEEDED` + msg "ไฟล์ .png ไม่รองรับในแพลนปัจจุบัน" |
| A1.8 | Free storage 50MB exact | user.plan='free', storage=49MB | Upload 1MB | ✅ Allowed (sum=50MB) |
| A1.9 | Free storage 50.1MB rejected | user.plan='free', storage=50MB | Upload 100KB | ❌ `PLAN_LIMIT_EXCEEDED` + msg "พื้นที่ Free (50MB) เต็มแล้ว" |
| A1.10 | Free pack limit 1 | user.plan='free', has 1 pack | Create pack | ❌ `PLAN_LIMIT_EXCEEDED` + msg "1 Context Pack" |

**A.2 — Starter Plan Limits (5 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| A2.1 | Starter upload 50th file | user.plan='starter', has 49 files | Upload | ✅ Allowed |
| A2.2 | Starter file size 20.1MB rejected | user.plan='starter' | Upload 20.1MB | ❌ msg "รองรับไฟล์สูงสุด 20MB" |
| A2.3 | Starter .png allowed | user.plan='starter' | Upload .png | ✅ Allowed |
| A2.4 | Starter .xlsx allowed | user.plan='starter' | Upload .xlsx | ✅ Allowed |
| A2.5 | Starter pack 5 | user.plan='starter', has 5 packs | Create | ❌ msg "5 packs" |

**A.3 — Plan Transitions (3 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| A3.1 | Subscription past_due grace | user.subscription_status='starter_past_due' | check_upload_allowed | ✅ Treated as starter (grace) |
| A3.2 | Subscription canceled before period_end | user.status='starter_canceled', period_end=future | check | ✅ Still starter |
| A3.3 | Subscription canceled after period_end | user.status='starter_canceled', period_end=past | check | ❌ Falls back to free |

**A.4 — Existing Testing Users Migration (2 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| A4.1 | Existing user >5 files restored | user.plan='free', 20 files (testing era) | Re-deploy v7.6.0 | Soft-locked: `is_locked=True`, `locked_reason='exceeds_free_plan_limit'` |
| A4.2 | Locked file no breaks reads | locked file | `GET /api/files/{id}/content` | ✅ Read OK (lock is for write/share/regenerate only — per SEC-001) |

---

#### Test File: `tests/test_email_service.py`

**A.5 — Email Service Unit Tests (10 cases)**

| # | Scenario | Mock | Action | Expected |
|---|---|---|---|---|
| A5.1 | Resend API key missing | `is_email_configured()=False` | `send_password_reset_email(...)` | Return False, no API call, log warning |
| A5.2 | Happy path send | `resend.Emails.send` mocked → `{id: 'eml_abc'}` | call function | Return True, log info ID |
| A5.3 | Resend SDK exception | `resend.Emails.send` raises Exception | call function | Return False, log error |
| A5.4 | HTML template renders | configured + valid params | render template | HTML contains user_name (escaped), reset_url, "รีเซ็ตรหัสผ่าน" |
| A5.5 | Plain text template | call `_render_password_reset_text()` | inspect output | Contains user_name + URL + Thai text |
| A5.6 | XSS user_name escape | user_name=`<script>alert(1)</script>` | render HTML | Output contains `&lt;script&gt;` (escaped) |
| A5.7 | Reset URL format | APP_BASE_URL='https://pdb.fly.dev', token='abc' | render | URL = `https://pdb.fly.dev/reset-password?token=abc` |
| A5.8 | Bilingual content | render HTML | inspect | มี both Thai section + English section |
| A5.9 | Subject line Thai | call function | inspect resend.send args | subject="รีเซ็ตรหัสผ่าน Personal Data Bank" |
| A5.10 | From address format | call function | inspect | from=`{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>` |

---

#### Test File: `tests/test_auth_password_reset_v7_6.py` (regression of existing + new)

**A.6 — Password Reset Integration (5 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| A6.1 | Happy reset → email sent | Real user, mock email_service | POST `/api/auth/request-reset {email}` | 200 + `{message, email}` only — **no `reset_token` field** |
| A6.2 | Unknown email anti-enum | non-existent email | POST | 200 + same shape (no info leak) |
| A6.3 | Inactive account anti-enum | user.is_active=False | POST | 200 + same shape |
| A6.4 | Email send fail still success | mock email_service to return False | POST | 200 + same shape (graceful), email error logged |
| A6.5 | Frontend receives no token | mock browser fetch | response | `data.reset_token === undefined` |

---

### Section B — MCP File Ingestion Tests (~35 cases)

#### Test File: `tests/test_url_fetcher_ssrf.py`

**B.1 — SSRF Defense IPv4 (8 cases)**

| # | URL | Mock DNS | Expected |
|---|---|---|---|
| B1.1 | `http://10.0.0.1/file.pdf` | resolves to 10.0.0.1 | `URLFetchError("BLOCKED_HOST")` |
| B1.2 | `http://172.16.0.1/file.pdf` | resolves to 172.16.0.1 | `BLOCKED_HOST` |
| B1.3 | `http://192.168.1.1/file.pdf` | resolves to 192.168.1.1 | `BLOCKED_HOST` |
| B1.4 | `http://127.0.0.1/file.pdf` | resolves to 127.0.0.1 | `BLOCKED_HOST` |
| B1.5 | `http://localhost/file.pdf` | hostname check | `BLOCKED_HOST` |
| B1.6 | `http://169.254.169.254/latest/meta-data/` | AWS metadata | `BLOCKED_HOST` |
| B1.7 | `http://metadata.google.internal/...` | GCP metadata | `BLOCKED_HOST` |
| B1.8 | `http://0.0.0.0/file.pdf` | resolves to 0.0.0.0 | `BLOCKED_HOST` |

**B.2 — SSRF Defense IPv6 (4 cases)**

| # | URL | Expected |
|---|---|---|
| B2.1 | `http://[::1]/file.pdf` | `BLOCKED_HOST` (IPv6 loopback) |
| B2.2 | `http://[fe80::1]/file.pdf` | `BLOCKED_HOST` (link-local) |
| B2.3 | `http://[fc00::1]/file.pdf` | `BLOCKED_HOST` (unique local) |
| B2.4 | `http://[2001:db8::1]/file.pdf` | (documentation prefix — let through, real test only) |

**B.3 — DNS Rebind & Redirect Attacks (5 cases)**

| # | Scenario | Expected |
|---|---|---|
| B3.1 | Mock DNS rebind: hostname resolves to public IP first, private IP second | `BLOCKED_HOST` (re-check after redirect) |
| B3.2 | Public URL → 302 redirect to `http://10.0.0.1/...` | `BLOCKED_HOST` (redirect blocked) |
| B3.3 | Public URL → 302 → public URL → 302 → private IP | `BLOCKED_HOST` (chain detected) |
| B3.4 | Public URL → 6 redirects (chain too long) | `FETCH_FAILED` "Redirect chain เกิน 5 ครั้ง" |
| B3.5 | DNS resolution fails (NXDOMAIN) | `BLOCKED_HOST` (fail-closed, don't leak existence) |

**B.4 — URL Validation (5 cases)**

| # | URL | Expected |
|---|---|---|
| B4.1 | `not-a-url` (no scheme) | `INVALID_URL` |
| B4.2 | `ftp://example.com/file.pdf` | `INVALID_URL` (only http/https) |
| B4.3 | `file:///etc/passwd` | `INVALID_URL` |
| B4.4 | `http://example.com/file.pdf` (no allow_http) | `HTTP_INSECURE` |
| B4.5 | `https://` (no host) | `INVALID_URL` |

**B.5 — Size Limits (5 cases)**

| # | Scenario | Expected |
|---|---|---|
| B5.1 | Content-Length=11MB, max=10MB | `SIZE_EXCEEDED` (early reject) |
| B5.2 | Content-Length=9MB, actual body=11MB | `SIZE_EXCEEDED` (mid-flight reject) |
| B5.3 | Content-Length=0 | `EMPTY_RESPONSE` |
| B5.4 | Exactly at limit (10MB) | ✅ Allowed |
| B5.5 | No Content-Length header, body=5MB | ✅ Allowed |

**B.6 — Network Errors (5 cases)**

| # | Scenario | Expected |
|---|---|---|
| B6.1 | Connection timeout (slowloris) | `FETCH_FAILED` "Timeout" |
| B6.2 | Read timeout (server stops sending) | `FETCH_FAILED` "Timeout" |
| B6.3 | HTTP 404 | `FETCH_FAILED` (HTTPStatusError caught) |
| B6.4 | HTTP 500 | `FETCH_FAILED` |
| B6.5 | Connection refused | `FETCH_FAILED` |

**B.7 — Filename + MIME Inference (5 cases)**

| # | Scenario | Expected |
|---|---|---|
| B7.1 | Content-Disposition: `attachment; filename="report.pdf"` | filename="report.pdf" |
| B7.2 | Content-Disposition: `filename*=UTF-8''thesis%202026.pdf` | filename="thesis 2026.pdf" (decoded) |
| B7.3 | URL: `https://example.com/path/file.docx` (no CD) | filename="file.docx" |
| B7.4 | URL: `https://example.com/` (no path) | filename matches `download_<timestamp>` pattern |
| B7.5 | Override `filename="../../../etc/passwd"` | sanitized → `passwd` (basename strip) |

| # | MIME header | Expected mime_type |
|---|---|---|
| B7.6 | `application/pdf` | `application/pdf` |
| B7.7 | `text/html; charset=utf-8` | `text/html` (params stripped) |
| B7.8 | (missing) | `application/octet-stream` (default) |

---

#### Test File: `tests/test_mcp_upload_text_v7_6.py`

**B.8 — `upload_text` (8 cases)**

| # | Scenario | Setup | Expected |
|---|---|---|---|
| B8.1 | Happy + auto_organize=true | free user, 0 files | Response: `status='uploaded_and_organized'`, file_id, content_hash, organized=true |
| B8.2 | Happy + auto_organize=false | free user, 0 files | Response: `status='uploaded'`, organized=false |
| B8.3 | Plan limit file count | free user, 5 files | Response: `{error: {code: PLAN_LIMIT_EXCEEDED, upgrade: true}}` |
| B8.4 | Plan limit file size | content > 10MB worth of bytes | Response: `PLAN_LIMIT_EXCEEDED` |
| B8.5 | Empty content | content="" | Raises ValueError "content is required" |
| B8.6 | BYOS user push success | user.storage_mode='byos', mock drive client | drive_file_id ใน response, storage_source='drive_uploaded' |
| B8.7 | BYOS Drive push fail | mock to raise | drive_file_id=None, storage_source='local', warning log |
| B8.8 | Auto-organize fail still success | mock organize to raise | organized=false, organize_error in response, file still saved |

---

#### Test File: `tests/test_mcp_upload_from_url_v7_6.py`

**B.9 — `upload_from_url` (10 cases)**

| # | Scenario | Mock | Expected |
|---|---|---|---|
| B9.1 | Happy public PDF URL | mock httpx 200 + 5MB pdf | file ingested, organized=true, source_url preserved |
| B9.2 | Override filename | params filename="custom.pdf" | filename="custom.pdf" |
| B9.3 | Plan limit | 5/5 files | `PLAN_LIMIT_EXCEEDED` MCP error |
| B9.4 | SSRF private IP | URL=10.0.0.1 | `BLOCKED_HOST` |
| B9.5 | Size exceeded | server lies, body=11MB | `SIZE_EXCEEDED` |
| B9.6 | HTTP not HTTPS | http://example.com | `HTTP_INSECURE` |
| B9.7 | DOCX file | mock 200 + .docx body | filetype='docx', extracted_text populated |
| B9.8 | Image PNG | mock 200 + png | filetype='png', extracted_text='[Image — OCR not run]' or similar |
| B9.9 | Auto-organize off | params auto_organize=false | organized=false, processing_status='uploaded' |
| B9.10 | URL fetch fail mid-fly | network error after partial body | `FETCH_FAILED`, no DB row created |

---

### Section C — Signed URL Tests (~15 cases)

#### Test File: `tests/test_signed_urls_v7_6.py`

**C.1 — Sign + Verify Round-trip (8 cases)**

| # | Scenario | Action | Expected |
|---|---|---|---|
| C1.1 | Default TTL sign+verify | sign(file_id, user_id) → verify | Payload returned with all fields, exp ≈ now+1800s |
| C1.2 | Custom TTL 5 min | sign(..., ttl=300) | Verify success, exp ≈ now+300s |
| C1.3 | Custom TTL 1 hour | sign(..., ttl=3600) | Verify success |
| C1.4 | TTL too small (59s) | sign(..., ttl=59) | Raises ValueError |
| C1.5 | TTL too large (3601s) | sign(..., ttl=3601) | Raises ValueError |
| C1.6 | Expired token | sign with ttl=60, sleep 70, verify | `DownloadTokenError("LINK_EXPIRED")` |
| C1.7 | Garbage token | verify("not-a-jwt") | `DownloadTokenError("INVALID_TOKEN")` |
| C1.8 | Wrong scope | manually craft JWT scope='login' | `DownloadTokenError("INVALID_TOKEN")` |

**C.2 — Token Tampering (3 cases)**

| # | Scenario | Action | Expected |
|---|---|---|---|
| C2.1 | Different secret | sign with secret A, verify with secret B | `DownloadTokenError("INVALID_TOKEN")` |
| C2.2 | Algorithm none attack | craft `{"alg":"none"}` JWT | Rejected (require explicit algorithm) |
| C2.3 | Missing required field | craft JWT without `file_id` | `DownloadTokenError("INVALID_TOKEN")` (jwt require enforced) |

**C.3 — Endpoint `GET /d/{token}` (10 cases)**

| # | Scenario | Setup | Action | Expected |
|---|---|---|---|---|
| C3.1 | Happy managed user | user.storage_mode='managed', file exists | GET /d/{valid_token} | 200 + binary + Content-Disposition header |
| C3.2 | Happy BYOS user | byos user, file in Drive | GET /d/{valid_token} | 200 + bytes from Drive |
| C3.3 | Expired token | sleep until exp | GET | 410 + `{error: {code: LINK_EXPIRED}}` |
| C3.4 | Invalid token | random string | GET /d/garbage | 401 + INVALID_TOKEN |
| C3.5 | Cross-user attack | sign for User B, file is User A | GET | 403 + WRONG_USER |
| C3.6 | File not found | valid token, file deleted | GET | 404 + FILE_NOT_FOUND |
| C3.7 | BYOS Drive fail | mock storage_router raises | GET | 503 + STORAGE_UNAVAILABLE |
| C3.8 | Cache headers | any | GET success | Header `Cache-Control: private, no-store` present |
| C3.9 | Filename in disposition | file.filename="thesis-2026.pdf" | GET | Header `Content-Disposition: attachment; filename="thesis-2026.pdf"` |
| C3.10 | Concurrent downloads | 5 simultaneous GET | parallel curl | All 5 return 200 (no race condition) |

**C.4 — `get_file_link` MCP Tool (5 cases)**

| # | Scenario | Action | Expected |
|---|---|---|---|
| C4.1 | Happy default TTL | tool call file_id only | URL valid 30 min, expires_at ISO |
| C4.2 | Custom TTL 60 min | params ttl_minutes=60 | TTL = 3600s |
| C4.3 | TTL clamp min | ttl_minutes=2 | Clamped to 5 min default + warning, OR clamped to 5 min |
| C4.4 | TTL clamp max | ttl_minutes=120 | Clamped to 60 min |
| C4.5 | Wrong user file | request file_id ของ user คนอื่น | `{error: {code: FORBIDDEN}}` |

---

### E2E / Integration Tests (~10 cases)

#### Test File: `scripts/foundation_v7_6_e2e_smoke.py` (in-process via TestClient)

**E.1 — Full User Journey** (1 mega-case = 8 sub-steps)

```
1. POST /api/auth/register {email, password, name}
   → expect 200 + token

2. POST /api/auth/request-reset {email}
   → expect 200 + {message, email} (NO reset_token)
   → mock email_service captures token

3. POST /api/auth/reset-password {token, new_password}
   → expect 200 + new auth token

4. POST /api/upload (5 files via web)
   → expect 5 success

5. POST /api/upload (6th file)
   → expect 403 PLAN_LIMIT_EXCEEDED

6. POST /mcp/{secret} {tools/call: upload_text {filename, content}}
   → expect file ingested + organized=True
   → expect content_hash returned

7. POST /mcp/{secret} {tools/call: upload_from_url {url}}
   → mock httpx response with PDF
   → expect 200, file in DB

8. POST /mcp/{secret} {tools/call: get_file_link {file_id}}
   → expect signed URL
   → GET signed URL → expect 200 + file bytes
```

**E.2 — SSRF Production Verify**

ใน real environment ที่ Fly.io machine มี internal IPs:
1. Deploy v7.6.0 to staging
2. Try MCP `upload_from_url("http://172.16.X.X/admin")` (Fly internal)
3. Expect `BLOCKED_HOST` (verifying real DNS check works in production env)

**E.3 — BYOS Round-trip**

1. User A connect Drive (BYOS mode)
2. MCP `upload_text` → expect drive_file_id in response
3. Open Drive in browser → file at `/Personal Data Bank/raw/{file_id}_{filename}` ✅
4. MCP `get_file_link` → curl URL → expect bytes match

**E.4 — Existing Test Users Migration**

1. Pre-deploy: create user with 20 files (testing era)
2. Deploy v7.6.0 + run migration
3. Expect 15 of 20 files have `is_locked=True`, `locked_reason='exceeds_free_plan_limit'`
4. User can still read all 20, but can't share/regenerate locked ones

**E.5 — Email Deliverability (production smoke)**

1. Deploy v7.6.0 to production
2. Manual: trigger password reset for test account ที่ email อยู่ Gmail/Outlook
3. Verify within 60 sec:
   - Email arrives in inbox (NOT spam folder)
   - SPF + DKIM passes (check email source)
   - HTML renders correctly
   - Reset link works end-to-end

**E.6 — Concurrent Stress (load test)**

```python
# 50 concurrent /d/{token} requests for same file
async with asyncio.TaskGroup() as tg:
    for _ in range(50):
        tg.create_task(client.get(f"/d/{token}"))
# All 50 should return 200, no DB lock errors
```

**E.7 — MCP Error Format Consistency**

- Call upload_text with empty content → check error shape
- Call upload_from_url with invalid URL → check error shape
- Call upload_from_url with private IP → check error shape

All errors must match: `{error: {code: STRING, message: STRING, upgrade?: BOOL}}`
NO Python tracebacks in MCP response (catch + format)

**E.8 — Backward Compat — Existing MCP Tools**

After v7.6.0 deploy, verify ALL 30 existing tools still work:
- `list_files` → 200
- `get_profile` → 200
- `chat` (if applicable) → 200
- ... (full TOOL_REGISTRY iteration)

**E.9 — Webhook Signature (no scope change but verify)**

`/api/stripe/webhook` HMAC verification still works (unrelated but checked because shared signature pattern)

**E.10 — Memory Tests**

- ตรวจ `current/pipeline-state.md` ถูก update
- ตรวจ `contracts/api-spec.md` มี new endpoints
- ตรวจ `project/decisions.md` มี LIMIT-001, EMAIL-001, SEC-003, URL-001

---

### Edge Cases & Adversarial Tests

#### EDGE.1 — Concurrency
- **Same file, multiple uploads:** User uploads file A 3 times in parallel via MCP. Expected: 3 distinct file_ids (no dedup at upload — that's organize-time)
- **Plan limit race:** User has 4 files, fires 3 concurrent uploads. Expected: 1 succeeds (5th file), 2 fail with PLAN_LIMIT_EXCEEDED. Atomic check via DB transaction
- **Token sign + delete:** Sign URL → delete file → use URL. Expected: 404 FILE_NOT_FOUND

#### EDGE.2 — Adversarial URL
- **Private GitHub raw** `https://raw.githubusercontent.com/private/repo/master/x.txt` requires auth → 404 from URL fetch (not BLOCKED_HOST since github.com public)
- **Redirect to data: URI** `https://example.com/redirect → data:text/plain,xxx` → expected: redirect not followed (data: not http/https)
- **Long URL** 10,000 chars → expected: still parseable, fetch attempt
- **URL with credentials** `https://user:pass@example.com/file.pdf` → strip credentials before logging (security)
- **Punycode IDN** `https://xn--80aaeauh.xn--p1ai/file.pdf` (Russian Wikipedia) → resolve, fetch normally

#### EDGE.3 — File Content
- **PDF that's actually image** (mismatched MIME) → extract_text handles gracefully, doesn't crash
- **Encrypted PDF** (password-protected) → extract_text returns marker, classify_extraction_status=encrypted
- **Empty PDF** (0 pages) → extract_text returns empty, content_hash NULL
- **PDF with embedded SVG with XSS** → extract returns text only, no script execution
- **HUGE valid file (exactly 10MB):** ใช้ time ≤ 30 sec
- **File with unicode filename** `เอกสาร-2569.pdf` → save + retrieve correctly

#### EDGE.4 — BYOS Edge
- **BYOS user, Drive disconnected mid-flight:** upload_from_url → file saves to local + storage_source='local' + warning log. NOT errors.
- **BYOS user, Drive quota full:** push fails → fall back to local + log
- **BYOS user, Drive token expired:** auto-refresh attempts → if fails → push skipped + log

#### EDGE.5 — JWT Edge
- **Clock skew:** server clock ahead 30s → token signed at T0 verified at T-30. Should still work (jwt allows leeway by default? — verify lib behavior)
- **Token used twice (replay):** Use signed URL twice within TTL → both should work (no nonce, intentional — Stripe/AWS S3 same)
- **Token rotation:** JWT_SECRET rotated → all old tokens invalidated. Acceptable. Document in ops runbook.

#### EDGE.6 — Email Edge
- **User name with emoji** `name="สวัสดี 🎉"` → renders correctly in Thai email body
- **User name SQL injection** `name="'; DROP TABLE users;--"` → escape in HTML, no DB issue (parameterized queries)
- **Invalid email format** request reset for `not-an-email` → still 200 generic (anti-enum)
- **Email service rate limited** (Resend 429) → log + return generic success
- **DKIM record missing** → email arrives but flagged as spam — manual verify on staging

---

## ✅ Done Criteria

- [ ] All 3 phases (A/B/C) implemented + tested
- [ ] **`tests/`** ≥ **80 new test cases** pass (per detailed test plan above):
  - **Section A — Pre-launch (~20 cases):**
    - 10 plan_limits Free
    - 5 plan_limits Starter
    - 3 plan transitions
    - 2 existing-user migration
    - 10 email_service unit
    - 5 password reset integration
  - **Section B — MCP (~35 cases):**
    - 8 SSRF IPv4
    - 4 SSRF IPv6
    - 5 DNS rebind / redirect attacks
    - 5 URL validation
    - 5 size limits
    - 5 network errors
    - 5 filename + MIME inference
    - 8 upload_text
    - 10 upload_from_url
  - **Section C — Signed URLs (~15 cases):**
    - 8 sign + verify round-trip
    - 3 token tampering
    - 10 endpoint behavior
    - 5 get_file_link tool
  - **E2E (~10 cases):**
    - Full user journey (8 sub-steps)
    - SSRF production verify
    - BYOS round-trip
    - Existing users migration
    - Email deliverability (manual smoke)
    - Concurrent stress
    - Error format consistency
    - Backward compat MCP tools
    - Webhook signature regression
    - Memory tests
  - **Edge cases (~25 sub-cases) covering:**
    - Concurrency (race, replay, sign-then-delete)
    - Adversarial URLs (auth, redirect to data:, IDN, credentials, long)
    - File content (encrypted PDF, image-as-pdf, unicode filename, 10MB exact)
    - BYOS edge (disconnect mid-flight, quota full, token expired)
    - JWT edge (clock skew, replay, rotation)
    - Email edge (emoji, escape, rate limit, DKIM)
- [ ] Existing 346/346 tests still pass (no regression)
- [ ] **Real E2E manual** on staging Fly.io:
  - Free user → upload 5 files → 6th rejected with upgrade prompt
  - Password reset → email arrives at inbox (Thai + English render)
  - MCP `upload_from_url` from Claude Desktop → file appears in PDB web
  - MCP `get_file_link` → curl URL → ได้ไฟล์
  - BYOS user MCP upload → file appears in Drive
- [ ] **No security regressions:**
  - SSRF tests pass
  - JWT secret stays in `.jwt_secret` (not committed)
  - No `reset_token` ใน JSON response anywhere
  - Signed URLs reject expired/cross-user/wrong-scope
- [ ] **Memory updated:**
  - `current/pipeline-state.md` → state = `done`
  - `contracts/api-spec.md` — เพิ่ม:
    - `GET /d/{token}` endpoint
    - `upload_from_url` MCP tool spec
    - `upload_text` updated spec
    - `get_file_link` updated params/response
    - Error codes (BLOCKED_HOST, HTTP_INSECURE, SIZE_EXCEEDED, etc.)
  - `project/decisions.md` — เพิ่ม:
    - LIMIT-001 — restored production values rationale
    - EMAIL-001 — Resend chosen over SendGrid/Gmail (free tier + modern API)
    - SEC-003 — SSRF defense via custom URL fetcher (not requests)
    - URL-001 — Universal signed download URL pattern
- [ ] **Convention compliance:** Thai comments, English vars, error format, FastAPI conventions
- [ ] **Deployment:**
  - Resend domain verified at DNS level
  - `RESEND_API_KEY` set as Fly.io secret
  - Deploy to staging → smoke test → deploy to production
  - APP_VERSION bumped 7.5.0 → 7.6.0

---

## ⚠️ Risks / Open Questions

### 🔴 Critical Risks

1. **Resend domain verification delay**
   - DNS propagation 5-60 min — first deploy might fail to send
   - **Mitigation:** Setup DNS ก่อน start coding (Step A.5 ทำได้ตั้งแต่วันแรก)

2. **organize_new_files refactor — circular import**
   - ถ้าอยู่ใน main.py และต้อง refactor → tests + endpoint impacted
   - **Mitigation:** Step B.2 ทำเป็น first thing ใน Phase B; verify imports ไม่แตก

3. **MCP error response format ไม่ standard**
   - PDB ปัจจุบันไม่มี mcp-tools error convention ที่ชัดเจน — บาง tools raise, บาง return
   - **Mitigation:** Phase B ใช้ `{error: {code, message, upgrade?}}` ทุก tool ใหม่. ฟ้าตรวจ existing tools ว่าควร refactor ด้วยไหม (ใหญ่ — defer ถ้าไม่จำเป็น)

### 🟡 Medium Risks

4. **HTTPS-only default = ลูกค้าบ่น**
   - Reasonable URLs บางตัวยังเป็น HTTP (เช่น old uni servers)
   - **Mitigation:** Phase 2 เพิ่ม `allow_http=true` flag (admin-controlled)

5. **Auto-organize timeout via MCP**
   - `organize_files` ใช้เวลา ~10-30s — MCP client อาจ timeout
   - **Mitigation:** auto_organize=True ปกติทำงานใน background. ถ้า MCP ทำ sync → return หลัง upload (organize ตามมาทีหลัง)
   - **Open question Q4 below**

6. **plan_limits restore กระทบ existing testing users**
   - Test users ที่อยู่ใน DB ปัจจุบันมีหลายไฟล์มากกว่า limit
   - **Mitigation:** ใช้ `lock_excess_data` mechanism จาก v5.9.3 (existing code) — soft-lock ไฟล์ส่วนเกินแทน hard-delete

### 🟢 Low Risks

7. **JWT secret rotation** — ถ้า secret เปลี่ยน → signed URLs invalidate ทั้งหมด (acceptable — TTL 30 min anyway)
8. **Fly.io egress for URL fetch** — outbound ไม่จำกัด

### Open Questions for User (8 ข้อ — มี default แนะนำทุกข้อ)

| # | Question | แนะนำ default |
|---|---|---|
| **Q1** | `max_file_size_mb` — restore original (10/20MB) หรือ recognize v7.5.0 work (25/100MB)? | 🟢 **Original (10/20MB)** — ค่อย bump ในแผน paid Pro/Power ทีหลัง |
| **Q2** | Email service = Resend? หรือ SendGrid/Gmail SMTP? | 🟢 **Resend** — modern API + free 3000/mo + simple Python SDK |
| **Q3** | URL fetch HTTPS-only? หรือ allow HTTP สำหรับ legacy URLs? | 🟢 **HTTPS-only** — security default. HTTP เปิดได้ถ้า user complaint |
| **Q4** | MCP auto-organize sync (block until done) หรือ async (return + organize background)? | 🟡 **Sync (default)** — ตรงตาม MCP semantics. User override `auto_organize=false` ถ้าอยาก fast |
| **Q5** | ลูกค้า existing ที่มี > 5 ไฟล์ (testing) — soft-lock หรือ grandfather? | 🟢 **Soft-lock** — reuse `lock_excess_data` v5.9.3 mechanism |
| **Q6** | Signed URL default TTL = 30 min พอไหม? | 🟢 ใช่ — Stripe/AWS S3 ก็ใช้ TTL ใกล้เคียงกัน |
| **Q7** | URL fetch max size = 10MB เท่า max_file_size? หรือ separate limit? | 🟢 **เท่า plan max_file_size** — consistent UX |
| **Q8** | `upload_text` default ext = .md (existing behavior)? หรือ .txt? | 🟢 **คงเดิม .md** — backward compat |

---

## 📌 Notes for เขียว

### Critical gotchas
1. **organize_new_files location** — verify อยู่ที่ไหนก่อน import. Phase B.2 อาจต้องทำก่อน B.3/B.4
2. **mcp_tools error pattern** — ดู existing tools ว่า raise vs return — Phase B ใช้ return dict + key `error` (consistent)
3. **httpx async required** — FastAPI ของ PDB เป็น async. ห้ามใช้ `requests.get` ใน url_fetcher (จะ block event loop)
4. **JWT scope check** — verify_download_token ต้อง check `scope == "download"` กัน token reuse (เช่น JWT ของ login session)
5. **Signed URL ห้าม leak token ใน Referer** — frontend ที่ render link ต้องใช้ `rel="noreferrer"` เมื่อ user click external

### Best practices
- ใช้ `httpx.AsyncClient(timeout=...)` เป็น context manager — auto cleanup connections
- `socket.getaddrinfo()` synchronous — wrap ใน executor ถ้าจำเป็น
- Mock Resend SDK ใน tests — ห้าม hit real API
- ใช้ `monkeypatch` หรือ `unittest.mock.patch` สำหรับ external calls

### Don'ts
- ❌ ห้ามแตะ `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`
- ❌ ห้ามใช้ `requests.get` (sync, blocks event loop)
- ❌ ห้าม return `reset_token` ใน JSON response
- ❌ ห้าม trust `Content-Type` จาก server URL (verify against extension เป็น secondary check)
- ❌ ห้ามให้ `signed_url.ttl > 3600` (security policy — 1 hour max)
- ❌ ห้าม cache signed URLs ใน CDN (Cache-Control: private, no-store)

### Do's
- ✅ Test SSRF defense ด้วย hosts จริง (10.0.0.1, 169.254.169.254) ก่อน deploy
- ✅ Verify Resend DNS ก่อน rely on email
- ✅ Manual smoke test password reset flow บน staging ก่อน production
- ✅ Update api-spec.md + decisions.md ใน same commit กับ code change

---

## 🎁 Future Phases (out of scope for v7.6.0)

- **v7.7.0 — MCP base64 binary upload** — `upload_file({filename, content_base64, mime_type})` สำหรับไฟล์เล็กที่ AI generate เอง (~1 week)
- **v7.8.0 — Email-to-PDB** — unique email per user → forward attachment → ingest (~1.5 weeks)
- **v8.0.0 — LINE Bot Integration** — full plan ที่ defer ไว้ใน [plans/line-bot-v8.0.0.md](line-bot-v8.0.0.md) (~3-4 weeks)
- **v8.1.0 — Telegram Bot** — reuse signed URL primitive + adapter pattern (~1 week)
- **v8.2.0 — Discord Bot** — reuse same primitives (~3-5 days)
- **Pre-launch landing v1** — refresh landing.html positioning ตาม competitor research (separate plan)
- **Pricing tier setup** — Stripe products + checkout for Pro ฿199 + Power ฿590 (separate plan)

---

## 📊 Success Metrics (post-deploy)

- **Plan limit enforcement:** % of upload requests rejected with PLAN_LIMIT_EXCEEDED (target: > 0% — proves enforcement working)
- **Email deliverability:** Resend dashboard — bounce rate < 5%, deliverability > 95%
- **MCP USP adoption:** count of `upload_from_url` + `upload_text` calls per day (target: > 10 within first 2 weeks)
- **SSRF security:** zero successful attacks (monitor logs for BLOCKED_HOST / FETCH_FAILED rates)
- **Signed URL usage:** count of `/d/{token}` requests per day
- **No regression:** existing test suite 346/346 still pass

---

**End of plan v7.6.0.** รอ user approve + ตอบ Q1-Q8 → state เปลี่ยน → ส่งต่อให้ "เขียว" (นักพัฒนา)
