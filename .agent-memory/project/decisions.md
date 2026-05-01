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
