# 📌 Key Design Decisions

> Decisions สำคัญพร้อมเหตุผล — เพื่อให้ agents ใหม่ไม่ตัดสินใจสวนทางโดยไม่รู้ตัว

---

## DB-001: ใช้ SQLite ไม่ใช่ Postgres
**Why:** เน้น simplicity, deploy ง่ายบน Fly.io ใน volume เดียว
**Implication:** ห้ามแนะนำ migrate ไป Postgres ถ้าไม่มี requirement ใหม่

## DB-002: ใช้ ChromaDB แบบ embedded
**Why:** ไม่ต้องรัน vector DB แยก
**Implication:** อยู่ใน `/chroma_db/` ห้าม commit ลง git

## DB-003: Migration safety rules (codified in `init_db()`)
**Why:** Production DB อยู่ใน Fly volume — broken migration = lost data
**Implication:**
- ADD only — ห้ามลบ table/column, ห้าม rename
- Idempotent — `PRAGMA table_info()` check before ALTER
- Auto-backup before migrate (5-most-recent rotation)
- `CREATE INDEX IF NOT EXISTS` syntax always

## FE-001: Frontend ยังเป็น Legacy (HTML/JS)
**Why:** ยังไม่มี budget/เวลา migrate, ยังพอใช้งานได้
**Implication:** ไม่แนะนำ migrate ไป React/Vue ในงานเล็กๆ — รอ task เฉพาะ

## AUTH-001: JWT-based auth
**Why:** stateless, เข้ากับ MCP integration ได้ดี
**Implication:** Token signing key อยู่ใน `.jwt_secret`

## MCP-001: MCP เป็น first-class feature
**Why:** จุดขายหลักของโปรเจกต์คือให้ Claude/AI access ข้อมูลได้
**Implication:** API ใหม่ทุกตัวควรพิจารณาว่ามี MCP equivalent ไหม

## MCP-002: URL-secret based auth (per-user secret in `/mcp/{secret}` path)
**Why:** Compatible with Claude Desktop / Antigravity / mcp-remote that don't always send Bearer
**Implication:** Bearer token additional but URL secret = primary identity. Initialize call open with valid secret URL.

## BILL-001: Stripe เป็น payment provider เดียว
**Why:** v5.9.3 ลงทุนกับ Stripe integration เยอะแล้ว
**Implication:** ห้ามเสนอเพิ่ม PayPal / อื่นๆ ถ้าไม่มี request ใหม่

## TEST-001: Real DB tests, ไม่ใช่ mocks
**Why:** กันปัญหา mock/prod divergence
**Implication:** Integration tests ใช้ test DB จริง (in-process TestClient with real SQLite)

## TEST-002: In-process smoke tests for sandbox-blocked port binding
**Why:** Sandbox doesn't allow uvicorn binding — but FastAPI TestClient runs in-process
**Implication:** All BYOS smoke tests use TestClient + mock DriveClient injection (`_from_service`/`_from_client`). Real Drive E2E test = ฟ้า does manually with browser.

## SEC-001: Locked-data guards (v5.9.3)
**Why:** ป้องกันการแก้ไข share/reprocess/regenerate ที่ทำให้ข้อมูลเสียหาย
**Implication:** ถ้าจะเพิ่ม endpoint ที่แก้ไขไฟล์ → ต้องคิดเรื่อง lock state ด้วย

## SEC-002: Encryption keys at-rest (v7.0)
**Why:** Refresh tokens ของ user's Drive = key to user's data; DB leak alone shouldn't expose
**Implication:** Use Fernet (AES-128 + HMAC) for `drive_connections.refresh_token_encrypted`. Key stored in `DRIVE_TOKEN_ENCRYPTION_KEY` env var (separate from DB). **ห้าม commit key value ใน docs / examples — ใช้ placeholder เท่านั้น** (lesson learned from `d75d5ea` leak fixed in `58e8b9d`)

## DEPLOY-001: Fly.io เป็น production target
**Why:** มี Dockerfile + fly.toml พร้อม
**Implication:** ทุกการเปลี่ยนแปลงต้อง compatible กับ Fly volumes

## DEPLOY-002: Keep Fly.io app name `project-key` (per rebrand v6.1.0 Q2)
**Why:** Fly.io app rename ต้องสร้าง app ใหม่ + migrate volume + DNS — high risk + downtime
**Implication:** Domain `project-key.fly.dev` คงเดิม. Custom domain (e.g., `personaldatabank.com`) defer ภายหลัง — DNS swap ไป Fly.io app เดิมได้

## STORAGE-001: Hybrid storage architecture for BYOS (v7.0)
**Why:** Pure cloud-storage = slow search; pure server-storage = no user sovereignty. Hybrid = best of both.
**Implication:**
- **Drive = source of truth** (when storage_mode=byos)
- **Server = cache + index** (rebuildable from Drive in 5 min)
- Conflict resolution: Drive wins (last-write-wins on Drive timestamp)
- 2-way sync: user writes via UI OR via Drive directly — both flows valid

## STORAGE-002: `drive.file` scope for BYOS Phase 1 (deferred full `drive` to Phase 2)
**Why:** Full `drive` scope requires CASA verification ($25K-85K/yr + 6 months). `drive.file` is FREE, takes 2-4 weeks verification.
**Implication:**
- Phase 1: app sees only files it created OR user picked via Google Picker SDK
- Phase 2 (post-revenue): apply for full `drive` scope to enable "open existing PDF in Drive" without Picker

## STORAGE-003: Coexist managed + BYOS modes (per Plan Q1)
**Why:** Don't force users to migrate. New users default to managed; opt-in to BYOS.
**Implication:**
- `users.storage_mode` column with default 'managed' (backward-compat)
- `is_byos_configured()` check + 503 fallback when env vars missing → managed users unaffected if BYOS broken
- All `storage_router` helpers no-op for managed users

## STORAGE-004: Transparent JSON in Drive (per Plan Q3 — no encryption of content)
**Why:** Trust + debug + verifiability ("Open your Drive right now and verify — we hide nothing")
**Implication:**
- profile.json / graph.json / etc. stored as plaintext in Drive
- Refresh tokens still encrypted (server-side; SEC-002)
- Users can manually edit Drive JSON → next sync picks up changes

## STORAGE-005: Testing Mode for BYOS MVP launch (defer Google verification)
**Why:** Verification = 2-4 weeks; closed beta with 50-100 users doesn't need it
**Implication:**
- Use OAuth Testing Mode (max 100 test users in Cloud Console)
- Refresh tokens expire 7 days (acceptable for early adopters)
- Submit for verification when ready for public launch — feature switch via `GOOGLE_OAUTH_MODE` env var

## REBRAND-001: Keep `projectkey.db` filename + localStorage keys + fly.toml (per rebrand v6.1.0)
**Why:** Internal/non-user-facing renames = high risk + zero benefit
**Implication:**
- DB filename `projectkey.db` stays
- localStorage keys `projectkey_token` / `projectkey_user` / `projectkey_lang` stay (changing breaks login of existing users)
- `fly.toml` app name + volume name stay (Fly.io constraint)

## REBRAND-002: Source-of-truth for app version
**Why:** Multiple display points (Swagger, /api/mcp/info, MCP serverInfo, frontend logo)
**Implication:**
- `backend/config.py:APP_VERSION` is canonical
- All version strings exposed to clients should read from here (current minor exception: `legacy-frontend/index.html:509` `<span class="logo-version">` is hardcoded — flagged as drift, manual sync until refactored)

## DUP-001: SHA-256 + TF-IDF (no LLM) for duplicate detection (v7.1)
**Why:** Free + fast (≤ 100ms ต่อไฟล์), reuses existing `vector_search` per-user index ที่ build ตอน organize, ดีพอสำหรับ ≥ 80% similar
**Implication:**
- ไม่เจอ paraphrase หนัก (similarity 50-80%) — เป็น MVP trade-off, deep diff via LLM = Phase 2
- `files.content_hash` indexed column → exact-match lookup O(1) per query
- Algorithm reused: `backend/vector_search.hybrid_search()` — same per-user isolation as chat retrieval
- **Critical invariant:** ไฟล์ที่ status="uploaded" (ยังไม่ organize) **ห้าม** index เข้า vector_search — จะแตกที่ retriever.py:91 + mcp_tools.py:743 ที่คาดว่า indexed = "ready" only. Plan Risk #9: intra-batch SEMANTIC = miss (accepted).
- Cost = ฿0 (no LLM call ทั้ง upload-time detection)

## DUP-002: Skip action does soft delete + BYOS Drive trash (v7.1)
**Why:** Skip = user เลือก "ไม่เอาไฟล์ใหม่" → ต้องลบครบทุกที่ที่ไฟล์ถูก mirror ไปแล้ว (disk + DB + index + Drive)
**Implication:**
- DB delete ใช้ cascade FK → FileInsight + FileSummary + FileClusterMap ลบเองอัตโนมัติ
- BYOS-aware ผ่าน public helper `storage_router.delete_drive_file_if_byos()` (ตาม pattern `push_*_to_drive_if_byos`) — ห้าม use private `_get_byos_user_with_connection` จาก main.py
- Drive delete = trash (recoverable 30 วัน) ไม่ใช่ permanent — เผื่อ user เปลี่ยนใจ
- Best-effort: ทุก step (raw, Drive, index) ห้าม raise — ถ้า fail ขั้นใดให้ log warning + ดำเนินต่อ (DB delete เป็น primary success criterion)

## BILL-002: plan_limits ×10 baseline kept for public launch (v8.0.2, decided 2026-05-05)
**Why:** v8.0.2 commit `1c8d139` bumped Free + Starter ×10 จาก v7.6.0 baseline เป็น "testing period". User decision 2026-05-05: ไม่ revert → ค่า ×10 = production baseline จริง (พ่วง pricing strategy).
**Current values (production):**
- Free: 50 files / 500MB / 100MB max / 50 summaries/mo / 100 exports/mo
- Starter: 500 files / 10GB / 200MB max / 1000 summaries/mo / 3000 exports/mo / semantic search
- Admin: 999999 ทุก field
**Implication:**
- ห้าม agent revert ค่าเป็น pre-v7.6.0 (Free 5/50MB, Starter 50/1GB) โดยไม่มี user instruction
- Pricing strategy ต้องสอดคล้อง — ถ้า revenue ไม่คุ้ม cost ที่ Free 50 files / 500MB → user เปลี่ยน pricing ก่อน revisit limits
- Comment ใน `backend/plan_limits.py:24` documented this — ห้ามลบหรือเปลี่ยนเป็น "Reduce before launch"
- BACKLOG-008 = CLOSED (production gate ผ่าน)

## DUP-003: Duplicate detection trigger = organize-time (not upload-time) (v7.1, user override 2026-05-01)
**Why:** Original plan trigger ตอน upload — แต่ user override ให้ย้ายไป organize-new หลังจากที่ฟ้า approve round แรกแล้ว. เหตุผลของ trigger location ใหม่:
1. **vector_search index พร้อมเต็ม** — ตอน organize เสร็จ ทุกไฟล์ใหม่ถูก index แล้ว → semantic detection ทำงานได้เต็มที่
2. **Risk #9 หาย** — intra-batch SEMANTIC detection ทำได้ (ตอน upload-time ไม่ทำได้เพราะห้าม index ก่อน organize per invariant retriever.py:91 + mcp_tools.py:743)
3. **UX trade-off ที่ user ยอมรับ** — popup เด้งช้าลง (organize-time vs upload-time) แต่ผลลัพธ์ครอบคลุมกว่า + ไฟล์ที่ organize แล้วมี summary/topics ครบ → modal แสดง matched_topics ที่ meaningful
**Implication:**
- `compute_content_hash` ยังถูกเรียกตอน upload (เก็บ hash ใน DB เพื่อใช้ตอน organize)
- `detect_duplicates_for_batch` ถูกเรียกใน `/api/organize-new` หลัง `organize_new_files()` + post enrich/graph/suggestions
- Frontend hook ย้ายจาก `uploadFiles()` → `runOrganizeNew()`
- Response field `duplicates_found` ย้ายจาก upload response → organize-new response
- `organize_new_files()` return value เพิ่ม `file_ids` array (เพื่อให้ caller รัน detection ตามได้)
- **ห้าม** ใส่ `duplicates_found` กลับเข้า upload response (frontend จะสับสน 2 จุด)

## STORAGE-006: invalid_grant graceful coverage = ALL push helpers (v9.3.5, 2026-05-10)
**Why:** v9.3.0 patch (commit `91cb37c`) added `_is_refresh_failure` + `_mark_drive_connection_errored` helpers แต่ใช้แค่ใน `push_profile_to_drive_if_byos` (1 ใน 9 helpers). 8 helpers ที่เหลือ + sync flow silent-fail บน RefreshError → user upload ไฟล์ → background push fail เงียบ → UI ยังเขียว "เชื่อมต่อแล้ว" → user ไม่รู้ต้อง re-auth จนกว่าจะเปิด Drive ดูเอง.

**Live test (2026-05-10):** bossok2546 user ติด token revoked (testing mode 7-day expire) · 8 ไฟล์ stuck local · `/api/drive/sync` คืน HTTP 500 (RefreshError ที่ `load_connection` ก่อน try-block)

**Implementation (v9.3.5):**
- ทุก push_*_to_drive_if_byos + delete_drive_file_if_byos เรียก `_mark_drive_connection_errored` ใน `_is_refresh_failure(e) = True` case
- `drive_sync.run_full_sync` wrap `load_connection()` ใน try-block + fallback re-fetch DriveConnection ถ้า self._connection ยังไม่ bind
- `/api/drive/sync` คืน 200 + `status='completed_with_errors'` (เดิม raise 500)
- Frontend: persistent error banner ที่ top of /app + auto-sync หลัง reconnect + visibility-based polling

**UX outcome:**
- User เห็น "🔌 Google Drive ของคุณหมดอายุการเชื่อมต่อ" banner ทันทีที่เกิด invalid_grant
- 1-click reconnect → auto-sync ไฟล์ stuck → ไม่ต้องกด sync เอง
- Testing mode notice reworded จาก jargon เป็น user-friendly text

**Implication:**
- ทุก push helper ใหม่ที่เพิ่มใน future ต้อง follow pattern เดียวกัน (else regress UX)
- Plan v9.3.5 = canonical pattern reference

**See also:** [plans/v9.3.5-byos-invalid-grant-coverage.md](../plans/v9.3.5-byos-invalid-grant-coverage.md)

## STORAGE-007: Submit Google OAuth verification (recommended, 2026-05-10)
**Why:** ปัจจุบัน `GOOGLE_OAUTH_MODE=testing` → Google revoke refresh_token หลัง 7 วัน → user เจอ invalid_grant → ต้อง reconnect ทุก 7 วันตลอดไป. ไม่ใช่ "best UX" ระยะยาว.

**Action items (founder ต้องทำเอง — agent ทำให้ไม่ได้):**
1. Google Cloud Console → OAuth consent screen → "Submit for verification"
2. Privacy Policy URL + Terms URL ของ PDB
3. Scope = `drive.file` + `openid` + `email` + `profile` = **non-sensitive** (ฟรี · ไม่ต้อง security audit)
4. รอ Google review 2-4 weeks
5. หลัง verified → `flyctl secrets set GOOGLE_OAUTH_MODE=production -a personaldatabank`
6. ทำตามขั้นตอนนี้แล้ว → token ที่ออกใหม่ทั้งหมดไม่หมดอายุ (จนกว่า user จะ revoke เอง) → UX ดีถาวร

**Effort:** ~30 นาที setup + 2-4 weeks waiting · ไม่ block code ของ v9.3.5

**Status:** OPEN — pending founder action

## STORAGE-008: Comprehensive Delete + Sync cleanup contract (v9.4.1, 2026-05-10)
**Why:** หลัง v9.3.5.4 ship ยังเจอ 10 edge cases ใน delete + sync flow (3 audit rounds):
- DELETE ลบ raw/ แต่ sub-folders (extracted/ + summaries/) ไม่ลบ → Drive storage บวม
- MCP `_tool_delete_file` + `/api/reset` ขาด Drive cleanup → ไฟล์ "งอก" หลัง sync
- DELETE blocking 60s × 3 calls = 180s → 504 ยิง user
- `keep_files=False` reconnect → push re-upload → Drive duplication (silent data dup)
- `drive_picked` files (user's external) อาจโดน trash โดยมิได้ตั้งใจ
- Sync orphan-cleanup ไม่มี retry budget → spam Drive API
- Frontend ไม่รู้ว่า Drive cleanup สำเร็จหรือไม่

**Decision:** บังคับ contract ใหม่:
1. **storage_source guard** — `_should_trash_drive_file(s) = (s == 'drive_uploaded')` ทุก code path ที่ trash Drive file
2. **3 sub-folders cleanup** — raw + extracted + summaries (helpers ใน storage_router.py)
3. **DELETE async pattern** — DB/disk/vector sync · Drive trash ใน BackgroundTasks · response < 500ms
4. **Reset sync pattern** — synchronous loop + stats response (ใช้ slowness สำหรับ accuracy)
5. **F24 push guard** — pre-fetch Drive listing before push · re-link ถ้าเจอ existing file pattern
6. **Retry budget** — orphan cleanup max 3 attempts per session (in-memory dict)
7. **deleted_in_drive filter** — `/api/files` default-hidden ghost rows
8. **drive_cleanup field** — DELETE response บอก client `scheduled` / `skipped:drive_picked` / `skipped:managed` / `skipped:no_drive_id`

**Implication:**
- ทุก code path ที่ลบ File row ต้องเรียก `_should_trash_drive_file` guard ก่อน trash Drive
- Sync stats เพิ่ม 4 fields: `relinked`, `orphans_cleaned`, `orphans_skipped_budget`, `duplicate_push_prevented`
- MCP tool response เพิ่ม `drive_cleanup` field
- HTTP DELETE response เพิ่ม `drive_cleanup` field

**See also:** [plan v9.3.5.5/v9.4.1](../plans/v9.3.5.5-comprehensive-delete-cleanup.md) (10 findings · 8 steps)

## DUP-004: Duplicate detection DISABLED temporarily (v9.3.2, 2026-05-08)
**Why:** `compute_content_hash()` crashes กับ `UnicodeEncodeError: surrogates not allowed` สำหรับ PDF text ที่มี lone surrogate code points (PDF font encoding edge case). Manifests เป็น HTTP 500 บน `POST /api/files/{id}/reprocess` ตามที่เห็นใน Fly.io log 2026-05-08 11:31:36 position 12562-12563.

User decision: ตัด duplicate detection ออกชั่วคราว · ใช้ AI organizer (LLM clustering) จัดกลุ่มไฟล์ซ้ำเข้า cluster เดียวกันโดย implicit (semantic similarity ใน organize prompts) · กลับมาเปิดเมื่อ fix bug แล้ว.

**Implementation:**
- `_DEDUP_DISABLED = True` flag ที่ top of [backend/duplicate_detector.py](../../backend/duplicate_detector.py) — single source of truth
- 3 public functions early-return no-op: `compute_content_hash → None`, `find_duplicate_for_file → None`, `detect_duplicates_for_batch → []`
- Original logic preserved underneath — flip flag + verify smoke = full re-enable
- `errors="replace"` ถูกใส่ใน `compute_content_hash` encode line แล้ว — เปิดกลับ = bug fix อัตโนมัติไม่ต้อง patch แยก

**Implication:**
- `files.content_hash` column ใน DB → NULL สำหรับไฟล์ใหม่ที่ upload หลัง v9.3.2 (existing rows ไม่กระทบ)
- `/api/organize-new` response → `duplicates_found: []` เสมอ (contract preserved)
- Frontend popup `dup-modal-overlay` ไม่ trigger (HTML/CSS/JS ทุกอย่างคงเดิม)
- `/api/files/skip-duplicates` endpoint ยัง functional · แต่ไม่ถูกเรียกจาก UI
- `pytest scripts/duplicate_detection_smoke.py` (33 cases) → จะ fail เพราะ no-op return · เก็บไว้เป็น "red flag" reminder
- **Limited regression:** AI organizer + chat retrieval + vector search ไม่กระทบ — ระบบหลักทำงาน 100%

**Re-enable steps (DO IN ORDER):**
1. Confirm `errors="replace"` ยังอยู่ใน `compute_content_hash.encode()` (มีอยู่แล้วใน v9.3.2)
2. Add pytest case: `compute_content_hash("normal\ud800text")` ต้องไม่ raise
3. Flip `_DEDUP_DISABLED = False` ใน duplicate_detector.py (1-line change)
4. รัน `python scripts/duplicate_detection_smoke.py` → expect 33/33 PASS
5. Manual smoke: upload duplicate file → click "จัดระเบียบไฟล์ใหม่" → popup "ไฟล์ซ้ำ" ปรากฏ
6. Update DUP-004 status → CLOSED + delete this section หรือ mark resolved

**See also:**
- [plan v9.3.2](../plans/v9.3.2-disable-duplicate-detection.md) — full impact analysis
- [active-tasks.md](../current/active-tasks.md) BACKLOG-009 — re-enable tracking
- [conventions.md](../contracts/conventions.md) — disabled-features list
