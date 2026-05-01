# 📡 API Specification

> Source of truth สำหรับ API contracts ระหว่าง frontend ↔ backend
> **เปลี่ยน API → update ไฟล์นี้ก่อนเขียนโค้ดเสมอ**

---

## Base URL
- Local: `http://localhost:8000`
- Production: `https://project-key.fly.dev` (Fly.io app name คงเดิมตาม rebrand v6.1.0 Q2)
- API prefix: `/api`

## Authentication
- Header: `Authorization: Bearer <jwt_token>`
- Token ได้จาก POST `/api/auth/login` หรือ `/api/auth/register`
- Endpoint ที่ต้อง auth: ทุกตัวยกเว้น `/api/auth/register|login`, `/api/personality/reference`, `/api/drive/oauth/callback`, MCP secret-URL routes, public pages

## Error Response Format
สอง patterns ที่ใช้ในระบบ (FastAPI default + custom convention):

```json
// FastAPI default (Pydantic validation, generic HTTPException)
{ "detail": "MESSAGE" }
// หรือ
{ "detail": [{"type": "value_error", "loc": ["body", "field"], "msg": "..."}] }
```

```json
// Custom convention (BYOS endpoints + structured errors)
{
  "error": {
    "code": "ERROR_CODE_UPPER_SNAKE",
    "message": "ข้อความภาษาไทยสำหรับผู้ใช้"
  }
}
```

---

## Endpoints

> ⚠️ **หมายเหตุ:** ส่วนนี้เป็น summary — agents ต้อง verify endpoints จริงโดยอ่าน `backend/main.py`
> เมื่อเพิ่ม / แก้ / ลบ endpoint → update ไฟล์นี้ทันที

### 🔐 Auth
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register` | สมัครสมาชิก (email + password + display_name) | ❌ |
| POST | `/api/auth/login` | เข้าสู่ระบบ → returns `{token, user}` | ❌ |
| GET  | `/api/auth/me` | ดู profile ตัวเอง | ✅ |
| POST | `/api/auth/request-reset` | ขอ reset password | ❌ |
| POST | `/api/auth/reset-password` | reset ด้วย token | ❌ |

### 📁 Files / Data
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/upload` | Upload file (v7.1: เพิ่ม `?detect_duplicates=true` + return `duplicates_found`) | ✅ |
| GET  | `/api/files` | List files | ✅ |
| GET  | `/api/files/{id}/content` | ดู text content | ✅ |
| GET  | `/api/files/{id}/download` | Download raw file | ✅ |
| POST | `/api/files/{id}/share` | สร้าง share link | ✅ |
| GET  | `/api/shared/{token}` | Public share view | ❌ |
| POST | `/api/files/{id}/reprocess` | Re-extract text | ✅ |
| DELETE | `/api/files/{id}` | ลบไฟล์ | ✅ |
| POST | `/api/files/skip-duplicates` | **v7.1** — ลบไฟล์ใหม่ที่ user เลือก "ข้ามที่ซ้ำ" หลัง duplicate popup | ✅ |
| GET  | `/api/unprocessed-count` | `{unprocessed, total, processed}` | ✅ |
| GET  | `/api/stats` | User stats summary | ✅ |

### 🤖 AI / Organize / Chat
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/organize` | จัดระเบียบด้วย AI | ✅ |
| POST | `/api/organize-new` | Organize เฉพาะไฟล์ใหม่ | ✅ |
| GET  | `/api/clusters` | ดู collections | ✅ |
| PUT  | `/api/clusters/{id}` | แก้ชื่อ/รายละเอียด collection | ✅ |
| GET  | `/api/summary/{file_id}` | ดูสรุปไฟล์ | ✅ |
| PUT  | `/api/summary/{file_id}` | แก้ summary | ✅ |
| POST | `/api/chat` | AI chat with retrieval | ✅ |

### 🌐 Knowledge Graph
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/graph/build` | สร้าง graph ใหม่ | ✅ |
| GET  | `/api/graph/global` | ดู global graph | ✅ |
| GET  | `/api/graph/nodes` | List nodes | ✅ |
| GET  | `/api/graph/nodes/{id}` | Node details | ✅ |
| GET  | `/api/graph/neighborhood/{id}` | Neighbors | ✅ |
| GET  | `/api/graph/edges` | List edges | ✅ |

### 🔗 Relations
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/relations/backlinks/{node_id}` | Backlinks | ✅ |
| GET  | `/api/relations/outgoing/{node_id}` | Outgoing | ✅ |
| GET  | `/api/suggestions` | AI relation suggestions | ✅ |
| POST | `/api/suggestions/{id}/accept` | Accept suggestion | ✅ |
| POST | `/api/suggestions/{id}/dismiss` | Dismiss | ✅ |

### 👤 Profile / Personality (v6.0)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/profile` | get profile + 4 personality systems | ✅ |
| PUT  | `/api/profile` | partial update (`exclude_unset` — null = clear) | ✅ |
| GET  | `/api/personality/reference` | reference data for 4 systems + test links | ❌ public |
| GET  | `/api/profile/personality/history` | append-only history (filter `?system=`, `?limit=` ≤200) | ✅ |

PUT /api/profile body adds 4 optional personality fields (Pydantic v2):
- `mbti`: `{"type": "INTJ" | "INTJ-A" | "INTJ-T", "source": "official"|"neris"|"self_report"} | null`
- `enneagram`: `{"core": 1-9, "wing": int|null}` (wing must be ±1 of core, wrap-around 9↔1)
- `clifton_top5`: `list[str]` (1-5 items, ห้ามซ้ำ, must match 34 canonical themes)
- `via_top5`: `list[str]` (1-5 items, ห้ามซ้ำ, must match 24 canonical strengths)

Pydantic raises 422 for invalid type/source/core/wing. Service raises 400 for INVALID_CLIFTON_THEME / INVALID_VIA_STRENGTH / DUPLICATE_THEMES.

**v7.0 BYOS hook:** Successful PUT → `storage_router.push_profile_to_drive_if_byos()` (best-effort write `personal/profile.json` to Drive ของ user — no-op for managed users)

### 📦 Context Packs
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/context-packs` | List packs | ✅ |
| POST | `/api/context-packs` | Create pack | ✅ |
| GET  | `/api/context-packs/{id}` | Get pack | ✅ |
| DELETE | `/api/context-packs/{id}` | Delete pack | ✅ |
| POST | `/api/context-packs/{id}/regenerate` | Regenerate | ✅ |

### 🧠 Context Memory (v5.5)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/contexts` | List context memory | ✅ |
| POST | `/api/contexts` | Save new context | ✅ |
| PUT  | `/api/contexts/{id}` | Update | ✅ |
| DELETE | `/api/contexts/{id}` | Delete | ✅ |
| GET  | `/api/contexts/{id}` | Get one | ✅ |

### 💳 Billing (Stripe)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/billing/create-checkout-session` | Stripe Checkout | ✅ |
| POST | `/api/billing/create-portal-session` | Customer Portal | ✅ |
| POST | `/api/stripe/webhook` | Stripe webhook (signed) | ❌ |
| GET  | `/api/billing/info` | Subscription summary | ✅ |
| GET  | `/api/usage` | Usage stats | ✅ |
| GET  | `/api/plan-limits` | Plan limits | ✅ |

### 🔌 MCP (v5.0+)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/mcp/info` | Server info + connector URL | ✅ JWT |
| POST | `/api/mcp/tokens` | Create MCP token | ✅ JWT |
| GET  | `/api/mcp/tokens` | List MCP tokens | ✅ JWT |
| DELETE | `/api/mcp/tokens/{id}` | Revoke MCP token | ✅ JWT |
| POST | `/api/mcp/test` | Test MCP call | ✅ JWT |
| POST | `/api/mcp/tools/call` | Internal tool call (admin) | ✅ JWT |
| GET  | `/api/mcp/logs` | Usage logs | ✅ JWT |
| GET/PUT | `/api/mcp/permissions` | Tool permissions | ✅ JWT |
| POST | `/mcp/{user-secret}` | **JSON-RPC endpoint** (initialize, tools/list, tools/call) | ✅ MCP token (Bearer + URL secret) |

### 🟢 BYOS — Google Drive (v7.0, NEW)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/drive/status` | Feature availability + connection state | ✅ JWT |
| GET  | `/api/drive/oauth/init` | Generate Google auth URL (returns `{auth_url}`) | ✅ JWT |
| GET  | `/api/drive/oauth/callback` | OAuth callback (Google redirects here) | ❌ (CSRF state token) |
| POST | `/api/drive/disconnect` | Revoke + cleanup (`?keep_files=true|false`) | ✅ JWT |
| PUT  | `/api/storage-mode` | Switch managed ↔ byos (body: `{"mode": "managed"|"byos"}`) | ✅ JWT |

**`/api/drive/status` response:**
```json
{
  "feature_available": true,    // false if env vars not configured
  "storage_mode": "managed" | "byos",
  "drive_connected": false,
  "drive_email": null | "user@gmail.com",
  "drive_root_folder_name": "Personal Data Bank",
  "drive_schema_version": "1.0",
  "last_sync_at": null | "2026-04-30T10:00:00",
  "last_sync_status": "pending" | "syncing" | "success" | "error",
  "oauth_mode": "testing" | "production"
}
```

**Status codes:**
- `503 GOOGLE_OAUTH_NOT_CONFIGURED` — env vars missing (BYOS feature disabled)
- `400 INVALID_OAUTH_STATE` — CSRF state mismatch / expired
- `400 MISSING_OAUTH_PARAMS` — code or state missing in callback
- `400 INVALID_STORAGE_MODE` — body.mode not in {managed, byos}
- `400 BYOS_REQUIRES_DRIVE_CONNECTION` — switch to byos without connection
- `404 NO_DRIVE_CONNECTION` — disconnect without active connection
- `500 OAUTH_INIT_FAILED` — Google API or Fernet key error

**Folder layout created in user's Drive on first connect:**
```
/Personal Data Bank/
├── raw/         ← original files
├── extracted/   ← extracted text
├── summaries/   ← AI summaries
├── personal/    ← profile.json, contexts.json
├── data/        ← clusters.json, graph.json, relations.json
├── _meta/       ← version.txt, manifest.json
└── _backups/    ← weekly backup zips
```

**Required env vars** (server-side only, not via API):
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_PICKER_API_KEY`
- `GOOGLE_PICKER_APP_ID`
- `GOOGLE_OAUTH_MODE` (`testing` | `production`)
- `DRIVE_TOKEN_ENCRYPTION_KEY` (Fernet 44-char base64)

ดู [`docs/BYOS_SETUP.md`](../../docs/BYOS_SETUP.md) สำหรับ admin setup walkthrough

---

## 🔁 Duplicate Detection (v7.1, NEW)

### `POST /api/upload` — additions in v7.1
- **Query param:** `detect_duplicates` (bool, default `true`) — set false เพื่อ skip duplicate check
- **Response field added:** `duplicates_found` (array, อาจว่าง)
  ```json
  {
    "uploaded": [...],
    "count": 1,
    "skipped": [],
    "duplicates_found": [
      {
        "new_file_id": "abc123",
        "new_filename": "thesis_v3.pdf",
        "match_file_id": "old456",
        "match_filename": "thesis_v2.pdf",
        "similarity": 0.87,
        "match_kind": "exact" | "semantic",
        "matched_topics": ["AI", "deep learning"]
      }
    ]
  }
  ```
- **Algorithm:** SHA-256 exact (file.content_hash) + TF-IDF cosine semantic (≥ 0.80 threshold) — ไม่เรียก LLM
- **Detection ทำหลัง DB commit** — ไฟล์ทุกตัว upload สำเร็จก่อนเสมอ; popup เป็น UX hint ไม่ใช่ blocker

### `POST /api/files/skip-duplicates` (NEW)
**Request:**
```json
{ "file_ids": ["abc123", "def789"] }
```
**Response 200:**
```json
{ "status": "ok", "deleted": ["abc123", "def789"], "count": 2, "skipped": [] }
```
**Behavior:**
- Validate ทุก `file_id` ต้องเป็นของ current user (ของ user อื่น → silently `skipped[]`, ไม่ leak existence)
- ลบ raw_path จาก disk + cascade ลบ FileInsight/FileSummary/FileClusterMap (FK)
- ลบจาก vector_search index ถ้าเคย organize แล้ว
- **BYOS-aware:** ถ้า `file.drive_file_id != NULL` → trash file บน Drive ผ่าน `storage_router.delete_drive_file_if_byos()` (best-effort, ไม่ raise)
**Errors:**
- 400 `EMPTY_FILE_IDS` — `file_ids` array ว่าง
- 401 — JWT missing/expired

---

## Common Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `UNAUTHORIZED` | 401 | ไม่ได้ login / token หมดอายุ |
| `FORBIDDEN` | 403 | login แล้วแต่ไม่มีสิทธิ์ |
| `NOT_FOUND` | 404 | ไม่พบ resource |
| `VALIDATION_ERROR` | 400/422 | input ไม่ถูกต้อง |
| `PLAN_LIMIT_EXCEEDED` | 403 | เกิน limit ของ plan |
| `LOCKED_DATA` | 423 | ข้อมูลถูก lock (v5.9.3) |
| `INTERNAL_ERROR` | 500 | server error |
| `STRIPE_ERROR` | 502 | Stripe API error |
| `GOOGLE_OAUTH_NOT_CONFIGURED` | 503 | BYOS env vars missing (v7.0) |
| `INVALID_OAUTH_STATE` | 400 | CSRF state mismatch (v7.0) |
| `INVALID_STORAGE_MODE` | 400 | mode not in {managed, byos} (v7.0) |
| `BYOS_REQUIRES_DRIVE_CONNECTION` | 400 | switch to byos w/o Drive (v7.0) |
| `NO_DRIVE_CONNECTION` | 404 | disconnect w/o connection (v7.0) |
| `EMPTY_FILE_IDS` | 400 | skip-duplicates `file_ids` array ว่าง (v7.1) |

---

## วิธี update ไฟล์นี้

เมื่อ agent เพิ่ม / แก้ / ลบ endpoint:

1. แก้ table ด้านบนให้สะท้อนความจริง
2. ถ้า request/response complex → สร้าง section แยกด้านล่างพร้อม example
3. Commit พร้อม code change ใน commit เดียวกัน
4. แจ้ง agent อื่นผ่าน `/communication/inbox/for-[ชื่อ].md`
