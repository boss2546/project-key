# 💾 Data Models

> Database schema + key data structures
> **เปลี่ยน schema → update ไฟล์นี้ + เขียน migration ก่อนเสมอ**

---

## Database
- **Engine:** SQLite
- **File:** `projectkey.db` (root ของ repo — filename ไม่เปลี่ยนตาม rebrand v6.1.0 Q3)
- **Vector store:** ChromaDB ใน `/chroma_db/`
- **Connection:** จัดการผ่าน `backend/database.py`
- **Auto-backup:** ทุกครั้งก่อน migration → `/backups/projectkey_<timestamp>.db` (เก็บ 5 ตัวล่าสุด)

---

## Tables

> ⚠️ Agents ต้อง verify schema จริงโดยอ่าน `backend/database.py` หรือ `backend/main.py`
> ส่วนนี้เป็น overview — ถ้าไม่ตรงกับโค้ดจริง → trust โค้ดแล้ว update ไฟล์นี้

### users (extended through v7.0)
ข้อมูลผู้ใช้ + auth + subscription + storage mode
- `id` — primary key (12-char UUID hex slice)
- `name`, `email` (unique, nullable for legacy default-user)
- `password_hash` (bcrypt)
- `is_active` (Boolean)
- `mcp_secret` (per-user MCP connector secret URL)
- `plan`, `subscription_status` (Stripe)
- `stripe_customer_id`, `stripe_subscription_id`, `stripe_price_id`
- `current_period_start`, `current_period_end`, `cancel_at_period_end`
- `created_at`, `updated_at`
- **NEW v7.0:** `storage_mode` (TEXT, default 'managed') — `"managed"` | `"byos"`
  - `managed`: เก็บใน Fly.io volume (default, backward-compat)
  - `byos`: เก็บใน Google Drive ของ user (Phase 1 = `drive.file` scope)

### files (extended through v7.1)
ข้อมูลไฟล์ที่ผู้ใช้ upload + processing state
- `id`, `user_id` (FK → users)
- `filename`, `filetype`, `raw_path`
- `uploaded_at`, `extracted_text`, `processing_status`
- v3 metadata: `tags` (JSON), `aliases` (JSON), `sensitivity`, `freshness`, `source_of_truth`, `version`
- v5.9.3 locked-data: `is_locked`, `locked_reason`
- **v7.0:** Drive linkage (NULL ถ้า managed)
  - `drive_file_id` (TEXT, indexed) — Google Drive file ID
  - `drive_modified_time` (DateTime) — last modified timestamp from Drive (drift detection)
  - `storage_source` (TEXT, default 'local') — `"local"` | `"drive_uploaded"` | `"drive_picked"`
- **NEW v7.1:** Duplicate detection
  - `content_hash` (TEXT, nullable, indexed) — SHA-256 hex ของ normalized extracted_text. NULL ถ้า text สั้น (< 50 chars) / extraction error / ไฟล์เก่าก่อน v7.1
- Indexes: `idx_files_drive_file_id` (v7.0), `idx_files_content_hash` (v7.1)

### clusters / file_cluster_map / file_insights / file_summaries
Collections + AI insights + summaries (no v7.0 changes — JSON projections to Drive via storage_router)

### chat_queries
Chat history (no schema changes for BYOS)

### user_profiles (v6.0)
- เดิม: `identity_summary`, `goals`, `working_style`, `preferred_output_style`, `background_context`
- v6.0:
  - `mbti_type` (TEXT, nullable) — "INTJ" | "INTJ-A" | "INTJ-T"
  - `mbti_source` (TEXT, nullable) — "official" | "neris" | "self_report"
  - `enneagram_data` (TEXT JSON, nullable) — `{"core": 1-9, "wing": int|null}`
  - `clifton_top5` (TEXT JSON, nullable) — `["Strategic", "Learner", ...]`
  - `via_top5` (TEXT JSON, nullable) — `["Curiosity", ...]`

### personality_history (v6.0 — append-only log)
Snapshot ทุกครั้งที่ผู้ใช้อัปเดตบุคลิกภาพ. Dedup ที่ service-level.
- `id` (autoincrement), `user_id` (FK)
- `system` ("mbti"|"enneagram"|"clifton"|"via")
- `data_json` (JSON snapshot — `{"cleared": true}` ถ้า user clear field)
- `source` ("user_update"|"mcp_update")
- `recorded_at` (DateTime, indexed)
- Composite index: `(user_id, system, recorded_at desc)`

### context_packs / context_injection_logs / contexts
Context Pack + Memory features

### note_objects / graph_nodes / graph_edges / suggested_relations / graph_lenses
Knowledge graph (graph snapshot can be projected to Drive via `storage_router.push_graph_to_drive_if_byos`)

### canvas_objects
Canvas annotations

### context_memory
Cross-platform context save (v5.5)

### mcp_tokens / mcp_usage_logs
MCP access tokens + audit log

### webhook_logs
Stripe webhook events

### usage_logs
Usage tracking (uploads, AI ops, exports per month)

### audit_logs (v5.9.3)
Audit trail สำหรับ billing events

### drive_connections (v7.0 — NEW for BYOS)
OAuth connection ของ user ไปยัง Google Drive
- `id` (autoincrement)
- `user_id` (FK → users, **unique** — 1 user : 1 connection in Phase 1)
- `drive_email` (TEXT) — Drive owner email (for display)
- `refresh_token_encrypted` (TEXT) — **encrypted with Fernet** (key in env `DRIVE_TOKEN_ENCRYPTION_KEY`)
- `drive_root_folder_id` (TEXT) — Google Drive folder ID of `/Personal Data Bank/`
- `last_sync_at` (DateTime, nullable)
- `last_sync_status` (TEXT, default 'pending') — `"pending"|"syncing"|"success"|"error"`
- `last_sync_error` (TEXT, nullable)
- `connected_at` (DateTime)
- `revoked_at` (DateTime, nullable)
- Relationship: `User.drive_connection` (one-to-one)

---

## Drive Folder Structure (v7.0 — for BYOS users)

ของจริงทุกชิ้นเก็บใน user's Google Drive at `/Personal Data Bank/`. Server เก็บแค่ index + cache (rebuildable from Drive).

```
/Personal Data Bank/
├── _meta/
│   ├── version.txt        ← schema version (current "1.0")
│   └── manifest.json      ← file index + roles
├── raw/
│   └── {file_id}_{original_name}    ← original files preserved
├── extracted/
│   └── {file_id}.txt                ← extracted plain text
├── summaries/
│   └── {file_id}.md                 ← AI summaries (markdown)
├── personal/
│   ├── profile.json                 ← MBTI/Enneagram/Clifton/VIA + identity (v6.0 personality fields)
│   └── contexts.json                ← context memory
├── data/
│   ├── clusters.json                ← collections snapshot
│   ├── graph.json                   ← knowledge graph snapshot
│   ├── relations.json               ← relations + suggestions
│   └── chat_history.json            ← optional, last 100 chats
└── _backups/                        ← weekly backup zips (rotated)
```

**Constants:** ดู `backend/drive_layout.py` (DRIVE_ROOT_FOLDER_NAME, SUB_FOLDERS, path helpers)

**Sync direction (per Plan Q4):**
- **Drive = source of truth** — conflict resolution: Drive wins
- **Cache (DB) = rebuildable** — disconnect + reconnect = full re-sync from Drive
- **Write path:** DB first → push to Drive (best-effort via `storage_router`)
- **Read path:** DB always (fast); Drive used for rebuild/recovery

**Encryption:**
- Refresh tokens at rest: Fernet AES-128 + HMAC (key = `DRIVE_TOKEN_ENCRYPTION_KEY`)
- File content in Drive: **plaintext** (transparency over encryption — per Plan Q3)

---

## Plan Limits
ดู `backend/plan_limits.py` สำหรับ source of truth

แต่ละ plan มี limits:
- จำนวนไฟล์สูงสุด
- ขนาด storage รวม (managed mode only — BYOS users use their own Drive quota)
- AI operations ต่อเดือน
- MCP requests ต่อเดือน

---

## ChromaDB Collections
- เก็บ embeddings ของ file chunks
- ใช้สำหรับ semantic search + relations
- Collection name format: `user_<user_id>_files`
- BYOS impact: embeddings ยังเก็บฝั่ง server (rebuildable from extracted/ in Drive)

---

## Migration history (in `backend/database.py:init_db()`)

| Version | Migration | Date |
|---|---|---|
| v5.0 | email/password_hash/is_active columns | 2025 |
| v5.1 | mcp_secret per-user | 2025 |
| v5.9.2 | Stripe subscription columns | 2025 |
| v5.9.3 | files.is_locked + context_packs.is_locked | 2026 |
| v6.0 | user_profiles personality columns + personality_history table + index | 2026-04-30 |
| v7.0 | users.storage_mode + drive_connections table + files.drive_* + idx_files_drive_file_id | 2026-04-30 |
| **v7.1** | **files.content_hash + idx_files_content_hash (duplicate detection)** | **2026-05-01** |

---

## วิธี update schema

1. เขียน migration script ใน `backend/database.py:init_db()`:
   - Use `PRAGMA table_info(<table>)` to detect existing columns
   - `CREATE INDEX IF NOT EXISTS` (idempotent)
   - `await db.commit()` only if `migrated = True`
2. Update ORM class definitions (User, File, etc.)
3. Update ไฟล์นี้
4. ทดสอบกับ test DB ก่อน production
5. ⚠️ **สำคัญ:** Production DB อยู่ใน Fly volume — migrate ต้อง compatible
   - **ห้าม:** drop tables/columns, rename columns, change column types
   - **ต้อง:** ADD only, idempotent, safe re-run, auto-backup before
