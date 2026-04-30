# 💾 Data Models

> Database schema + key data structures
> **เปลี่ยน schema → update ไฟล์นี้ + เขียน migration ก่อนเสมอ**

---

## Database
- **Engine:** SQLite
- **File:** `projectkey.db` (root ของ repo)
- **Vector store:** ChromaDB ใน `/chroma_db/`
- **Connection:** จัดการผ่าน `backend/database.py`

---

## Tables (สำคัญ)

> ⚠️ Agents ต้อง verify schema จริงโดยอ่าน `backend/database.py` หรือ `backend/main.py`
> ส่วนนี้เป็น overview — ถ้าไม่ตรงกับโค้ดจริง → trust โค้ดแล้ว update ไฟล์นี้

### users
ข้อมูลผู้ใช้ + auth
- `id` — primary key
- `email` — unique
- `password_hash`
- `created_at`
- `plan` — current subscription plan
- `stripe_customer_id`

### files
ข้อมูลไฟล์ที่ผู้ใช้ upload
- `id`
- `user_id` — FK → users
- `name`, `mime_type`, `size`
- `content_hash`
- `created_at`
- `is_locked` — locked-data flag (v5.9.3)

### collections
กลุ่มไฟล์ที่ AI จัดให้
- `id`
- `user_id`
- `name`, `description`

### file_collections
Many-to-many relation
- `file_id`, `collection_id`

### relations
ความเชื่อมโยงระหว่างไฟล์
- `from_file_id`, `to_file_id`
- `relation_type`, `confidence`

### subscriptions
Stripe subscription tracking
- `user_id`
- `stripe_subscription_id`
- `plan`, `status`
- `current_period_end`

### audit_log (v5.9.3)
Audit trail สำหรับ billing events
- `user_id`, `event_type`, `data`, `created_at`

### user_profiles (v6.0 — เพิ่ม 5 columns)
- เดิม: `identity_summary`, `goals`, `working_style`, `preferred_output_style`, `background_context`
- ใหม่ v6.0:
  - `mbti_type` (TEXT, nullable) — "INTJ" | "INTJ-A" | "INTJ-T"
  - `mbti_source` (TEXT, nullable) — "official" | "neris" | "self_report"
  - `enneagram_data` (TEXT JSON, nullable) — `{"core": 1-9, "wing": int|null}`
  - `clifton_top5` (TEXT JSON, nullable) — `["Strategic", "Learner", ...]`
  - `via_top5` (TEXT JSON, nullable) — `["Curiosity", ...]`

### personality_history (v6.0 — append-only log)
Snapshot ทุกครั้งที่ผู้ใช้อัปเดตบุคลิกภาพ. Dedup ที่ service-level (ไม่ append ถ้าค่าใหม่==ล่าสุด).
- `id` (autoincrement)
- `user_id` (FK)
- `system` ("mbti"|"enneagram"|"clifton"|"via")
- `data_json` (JSON snapshot — `{"cleared": true}` ถ้า user clear field)
- `source` ("user_update"|"mcp_update")
- `recorded_at` (DateTime, indexed)
- Composite index: `(user_id, system, recorded_at desc)`

### mcp_tokens
MCP access tokens
- `token_hash`
- `user_id`
- `scopes`, `expires_at`

---

## Plan Limits
ดู `backend/plan_limits.py` สำหรับ source of truth

แต่ละ plan มี limits:
- จำนวนไฟล์สูงสุด
- ขนาด storage รวม
- AI operations ต่อเดือน
- MCP requests ต่อเดือน

---

## ChromaDB Collections
- เก็บ embeddings ของ file chunks
- ใช้สำหรับ semantic search + relations
- Collection name format: `user_<user_id>_files`

---

## วิธี update schema

1. เขียน migration script (manual SQL หรือ Python migration)
2. Update `backend/database.py`
3. Update ไฟล์นี้
4. ทดสอบกับ test DB ก่อน production
5. ⚠️ **สำคัญ:** อย่าลืมว่า production DB อยู่ใน Fly volume — migrate ต้อง compatible
