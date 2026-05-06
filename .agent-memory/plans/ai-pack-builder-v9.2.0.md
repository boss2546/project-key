# Plan: AI Pack Builder — v9.2.0 (REVISED)

> **Status:** `plan_pending_approval` (revised 2026-05-07 — added clarifying-questions step)
> **Author:** 🔴 แดง (Daeng) — 2026-05-07
> **Foundation:** v9.1.0 (current master — APP_VERSION ใน config.py = 9.1.0; รวม v9.0.1 correctness fixes + v9.1.0 Raw Vault ที่ ship แล้ว)
> **⚠️ Raw Vault dependency (verified 2026-05-07):** `files.file_kind` column มีแล้ว (values: "processed" | "vault_only"). organizer.py filter `file_kind="processed"` แล้ว — AI Pack Builder ต้องทำเหมือนกันใน inventory builders
> **Estimated effort:** เขียว ~3–3.5 วัน + ฟ้า ~0.5–1 วัน (เพิ่ม 0.5 วัน จาก revision)
> **Risk:** 🟡 Medium — 3 LLM calls per build (clarify + select + distill), schema migration, draft cache
>
> **Revision note (2026-05-07):** User clarified flow ว่าต้อง "AI ถามกลับเป็นตัวเลือก 1-4 ให้เลือก" ก่อนสร้าง draft. เดิมเป็น 1-shot (prompt → draft) ตอนนี้เป็น 2-shot (prompt → clarifying choice → draft).

---

## 🎯 Goal & Context

### Why
ระบบ Context Pack ปัจจุบัน adoption = 0% ใน production (76 users / 0 packs) เพราะ workflow create pack ต้องการ user effort สูง:
1. คิดเองว่าจะรวมไฟล์ไหน
2. ตั้งชื่อ + เลือก type
3. กดสร้างทีละ 1-2 packs
4. ผลลัพธ์เป็น "summary นิ่งๆ" — ไม่มี metadata อธิบายว่า pack นี้ใช้ทำอะไร

**User vision (verbatim 2026-05-07):**
> "อยากให้มีระบบจัดคอนแท็คแพ็กด้วย AI เช่นบอกว่า 'ช่วยจัด context pack ให้หน่อย เป็น context pack เกี่ยวกับ.....' และเมื่อ AI จัดเสร็จก็จะมาให้ผู้ใช้คอนเฟิร์มว่าทุกอย่างที่จัดให้เป็นแบบนี้นะ จะแก้ไขอะไรไหม อยากให้มีบริบทของ context pack นั้นๆด้วย"

**User clarification (2026-05-07 revised):**
> "มีปุ่มในหน้าคอนแท็คแพ็คเลย แล้วก็ให้เราพิมพ์ว่าอยากได้คอนแท็คแพ็คอะไร แล้วก็บริบทคือ ขึ้นให้ตอบคำถามเป็นตัวเลือก 1 2 3 4 ให้เลือก หรือใส่ข้อความอธิบายเพิ่ม หรือสกิป ให้ AI จัดการเอง"

→ Flow มี **clarifying-questions step** หลัง user พิมพ์ prompt. AI สร้างคำถาม clarify 1 ครั้ง (ไม่ใช่ multi-turn) พร้อมตัวเลือก 4 ตัว + free-text + skip option.

### Goals
1. **Lower friction** — user แค่บอก intent ภาษาธรรมชาติ AI ทำที่เหลือ
2. **Confirm-before-commit** — user ยืนยันก่อน save จริง (ไม่ใช่ AI สร้างแล้ว user ลบทีหลัง)
3. **Edit ได้** — ถ้า AI ทำพลาดเล็กน้อย user แก้ field เองได้ ไม่ต้อง regen ใหม่
4. **Pack มีบริบท** — เพิ่ม fields `intent` + `scope` ให้ pack มี metadata ที่ AI ใช้ตัดสินใจได้ดีขึ้นว่าควร inject ตอนไหน

### Non-goals (เลื่อน v9.3.0+)
- ❌ Chat-style multi-turn revise (user คุยกลับไปกลับมา) — ใช้ retry button + form edit แทน
- ❌ Quota แยก `ai_pack_builder` — reuse `ai_summary` quota
- ❌ Auto-suggest หลัง organize-new (จะเป็น v9.3.0 — pair กับ feature นี้)
- ❌ Pack pinning ใน chat
- ❌ Graph nodes/notes เป็น source ของ AI builder (ใช้แค่ files + clusters)
- ❌ `usage_hint` field (ทับซ้อนกับ intent — เก็บไว้ทำภายหลัง)

### Design decisions (per user 2026-05-07)
- **Q1 บริบท fields:** `intent` + `scope` (2 fields)
- **Q2 User edit:** Form-based edit หลัง AI propose (ตัด source + แก้ทุก field ได้)
- **Q3 AI source pool:** Files + Clusters (matches manual create flow)
- **Q4 ลองใหม่:** Retry button (rerun AI ทั้งหมด, ไม่ใช่ chat revise)
- **Q5 Cost guard:** Nab `ai_summary` quota รายเดือน (Free 50, Starter 1000) — นับ 1 ครั้งต่อ confirmed pack (รวม clarify + select + distill = 3 LLM calls)
- **Q6 Clarifying step (ใหม่ 2026-05-07):** 1 round, 4 options + free-text + skip — AI ถามคำถาม clarify ครั้งเดียวแล้วสร้าง draft (ไม่ multi-turn)

---

## 📁 Files to Create / Modify

| File | Action | Reason |
|------|--------|--------|
| `backend/database.py` | **modify** | เพิ่ม 3 columns ใน `ContextPack`: `intent` Text, `scope` Text, `created_via` String + idempotent migration block ใน `init_db()` |
| `backend/ai_pack_builder.py` | **create** (~280 lines) | New module: `propose_pack()` 2-step LLM flow + `confirm_pack()` save → real ContextPack + draft cache (in-memory dict + 30 min TTL) |
| `backend/main.py` | **modify** | 2 Pydantic request models + 3 endpoints (`/propose`, `/confirm`, `DELETE /drafts/{id}`) + import + เช็ค check_pack_create_allowed + check_summary_allowed |
| `backend/context_packs.py` | **modify** | `create_pack()` รับ `intent`, `scope`, `created_via` parameters (default `""`, `""`, `"manual"`) + `_serialize_pack()` expose 3 fields ใหม่ |
| `backend/mcp_tools.py` | **no change** | MCP tool `create_context_pack` ไม่ครอบ AI builder ใน v9.2.0 (เลื่อน v9.3.0) |
| `legacy-frontend/app.html` | **modify** | เพิ่มปุ่ม "🪄 ให้ AI สร้างให้" ใน packs-header + AI Builder modal (#ai-pack-builder-modal) — 3 view states (input / preview / loading) |
| `legacy-frontend/app.js` | **modify** | 4 functions: `openAIPackBuilder()`, `submitAIBuilderPrompt()`, `confirmAIDraft()`, `discardAIDraft()` + render preview card + i18n keys ~10 อัน |
| `legacy-frontend/styles.css` | **modify** | สไตล์ `.ai-builder-modal` + `.ai-draft-preview` + `.ai-source-checkbox` (~70 บรรทัด) |
| `backend/config.py` + `legacy-frontend/app.html` | **modify** | bump APP_VERSION 9.0.1 → 9.2.0 (skip v9.1.0 — reserved for Raw Vault parallel plan) |
| `scripts/ai_pack_builder_smoke.py` | **create** (~200 lines) | 18-case smoke test (mock LLM, verify flow + edge cases) |

**ไม่แตะ:** retriever.py, graph_builder.py, plan_limits.py (just reuse existing helpers), billing, auth — out of scope

---

## 🗄️ Data Model Changes

### `ContextPack` table — เพิ่ม 3 columns

```python
class ContextPack(Base):
    # ...existing fields...
    
    # v9.2.0 — บริบทของ pack ที่ AI builder + manual create ใช้ตัดสินใจ inject ตอนไหน
    intent = Column(Text, default="")          # "ใช้สำหรับอะไร" — short description
    scope = Column(Text, default="")           # "ครอบคลุมอะไร / ไม่ครอบคลุมอะไร"
    
    # v9.2.0 — track ว่า pack สร้างยังไง (analytics + UX hints)
    created_via = Column(String, default="manual")   # "manual" | "ai_builder"
```

### Migration plan
ที่ `init_db()` ใน `database.py` — เพิ่ม idempotent ALTER block (pattern เดียวกับ `is_admin` v8.2.0 + `google_sub` v8.1.0):

```python
# v9.2.0 — เพิ่ม intent/scope/created_via ใน context_packs (idempotent)
result = await conn.execute(text("PRAGMA table_info(context_packs)"))
existing_cols = {row[1] for row in result.fetchall()}
if "intent" not in existing_cols:
    await conn.execute(text("ALTER TABLE context_packs ADD COLUMN intent TEXT DEFAULT ''"))
if "scope" not in existing_cols:
    await conn.execute(text("ALTER TABLE context_packs ADD COLUMN scope TEXT DEFAULT ''"))
if "created_via" not in existing_cols:
    await conn.execute(text("ALTER TABLE context_packs ADD COLUMN created_via TEXT DEFAULT 'manual'"))
```

**Backward compat:** ✅ Additive — DEFAULT values ทำให้ existing rows ใช้งานต่อได้

---

## 🔌 API Changes (REVISED — 4 endpoints แทน 3)

### Flow overview

```
User พิมพ์ prompt
       ↓
[1] POST /ai-build/clarify     — AI gen 4 options + free-text + skip
       ↓
User เลือก 1 option / พิมพ์ free-text / กด skip
       ↓
[2] POST /ai-build/propose     — AI build draft จาก prompt + clarification
       ↓
User edit form / กด confirm / กด retry
       ↓
[3] POST /ai-build/confirm     — save real pack + log quota
       ↓
[4] DELETE /ai-build/drafts/{id}  — discard (ถ้า user ยกเลิก)
```

### 1. `POST /api/context-packs/ai-build/clarify` — NEW (revision)

ขั้นตอนก่อน propose — AI generate clarifying question + 4 options ให้ user เลือก

**Request:**
```json
{
  "prompt": "ช่วยสร้าง pack เกี่ยวกับการเรียน term นี้"
}
```

**Response 200 — case A (prompt ไม่ละเอียดพอ, ถาม clarify):**
```json
{
  "session_id": "ses_xyz789",
  "skip_clarify": false,
  "question": "ต้องการ pack เกี่ยวกับการเรียนแบบไหนครับ? เลือกตัวเลือกหรือพิมพ์อธิบายเพิ่มได้",
  "options": [
    {
      "id": 1,
      "title": "วิชาคำนวณเชิงลึก",
      "summary": "ใช้ 5 ไฟล์ในกลุ่ม 'วิชาคำนวณ' (calculus-midterm-notes.pdf, linear-algebra-textbook.pdf, multivariable-calc-problems.pdf, ...) — focus สูตร + ตัวอย่างโจทย์ + วิธีคิด ไม่รวม assignment ที่ส่งไปแล้ว"
    },
    {
      "id": 2,
      "title": "ภาษา + การเขียน",
      "summary": "ใช้ 3 ไฟล์ในกลุ่ม 'ภาษา' (english-essay-draft.docx, business-writing-notes.md, idioms-collection.txt) — focus คำศัพท์ + structure การเขียน + แนวข้อสอบ ไม่รวม creative writing"
    },
    {
      "id": 3,
      "title": "ครอบคลุมทุกวิชาภาคนี้",
      "summary": "รวม 8 ไฟล์ + 2 collection (วิชาคำนวณ + ภาษา) — ภาพรวมทั้งภาคเรียน เน้นจุดเชื่อมโยงระหว่างวิชา ดีสำหรับใช้ตอบคำถามเรื่องการเรียนเทอมนี้แบบกว้าง"
    },
    {
      "id": 4,
      "title": "เน้น Assignment + การสอบ",
      "summary": "ใช้เฉพาะไฟล์ที่ tag 'assignment' หรือ 'exam' (3 ไฟล์: midterm-prep-list.md, hw-tracker.xlsx, sample-questions-final.pdf) — focus deadline, รายการงาน, แนวข้อสอบ ไม่รวมเนื้อหาวิชา"
    }
  ],
  "allow_freetext": true,
  "freetext_hint": "เช่น 'เอาทั้งวิชาคำนวณและภาษา แต่ไม่เอา business writing'",
  "allow_skip": true,
  "expires_at": "2026-05-07T10:30:00",
  "ai_calls_used": 1
}
```

**Response 200 — case B (prompt ละเอียดพอ, ข้าม clarify):**
```json
{
  "session_id": "ses_xyz789",
  "skip_clarify": true,
  "reasoning": "prompt ระบุครบ: source ('5 ไฟล์ calculus + linear algebra'), scope ('ไม่รวม assignment'), focus ('สูตร + โจทย์ตัวอย่าง') — proceed ไป /propose ได้เลย",
  "expires_at": "2026-05-07T10:30:00",
  "ai_calls_used": 1
}
```

**LLM behavior:**

1. **Decision step** — AI ตัดสินใจว่า prompt มี context ครบไหม โดยเช็ค:
   - มี source ระบุชัดไหม (ชื่อไฟล์/cluster หรือจำนวน + topic ชัด)
   - มี scope ระบุไหม (include/exclude)
   - มี focus ระบุไหม (เน้นอะไร)
   - ถ้า ≥2 ใน 3 ครบ + match กับ inventory ได้ → `skip_clarify: true`
   - ถ้าไม่ครบ → `skip_clarify: false` พร้อม gen options คุณภาพ

2. **Quality criteria สำหรับ options (เมื่อ skip_clarify=false):**
   - ✅ **CONCRETE** — ระบุชื่อไฟล์จริง / จำนวนไฟล์จริง / cluster จริง (อ้างจาก inventory)
   - ✅ **ACTIONABLE** — user อ่านแล้วเข้าใจทันทีว่าเลือกแล้วจะได้ pack แบบไหน
   - ✅ **DIFFERENTIATED** — แต่ละ option ต่างกันชัด ไม่ทับซ้อน
   - ✅ **SCOPED** — บอกทั้ง "include อะไร" และ "exclude อะไร" (ถ้า relevant)
   - ✅ **LENGTHY ENOUGH** — `summary` ต้อง 25-60 คำ (ไม่สั้นเกินจน abstract)
   - ❌ **ห้าม** — generic label สั้นๆ เช่น "เน้นวิชาคำนวณ" — ต้องบอกว่าใช้ไฟล์ไหน focus อะไร

3. **Schema option ใหม่** — แต่ละ option มี 3 fields: `id` (1-4), `title` (สั้น 3-6 คำ), `summary` (25-60 คำ concrete description)

**Errors:**
- `400 PROMPT_TOO_SHORT` (< 10 chars)
- `400 PROMPT_TOO_LONG` (> 500 chars)
- `403 PACK_LIMIT_REACHED` — pre-check pack quota (กัน user ใช้ LLM ฟรีแล้วไม่ได้ pack)
- `403 AI_QUOTA_REACHED` — pre-check ai_summary quota
- `400 NO_SOURCES_AVAILABLE` — user มี 0 files + 0 clusters
- `503 LLM_UNAVAILABLE`

### 2. `POST /api/context-packs/ai-build/propose` — NEW

**Request:**
```json
{
  "session_id": "ses_xyz789",          // จาก /clarify response
  "clarification": {
    "selected_option_id": 1,            // user เลือก option 1 (mutually exclusive)
    // OR
    "freetext": "เอาทั้งวิชาคำนวณและ english แต่ไม่เอาเรื่อง business writing"
    // OR
    "skipped": true                      // user กด skip → AI ตัดสินใจเอง
  },
  "preferred_type": "study"            // optional — ถ้าไม่ส่ง AI เดาเอง
}
```

**Validation:** ใน `clarification` ต้องมี **เพียง 1 ใน 3** field (`selected_option_id`, `freetext`, `skipped`) — ถ้ามาหลาย field → 400 INVALID_CLARIFICATION

**Response 200 (success):**
```json
{
  "draft_id": "drf_abc123",        // 12-char id, expires 30 min
  "title": "การเรียน Term 2/2026 — สรุปวิชาคำนวณ + ภาษา",
  "type": "study",
  "intent": "ใช้ตอบคำถามเกี่ยวกับการเรียนภาคนี้ — เนื้อหาวิชา assignment การสอบ",
  "scope": "ครอบคลุม 4 วิชา (calculus, linear algebra, advanced English, business writing). ไม่รวม โปรเจกต์จบ",
  "summary_text": "...summary ที่ AI distill มาจาก source ทั้งหมด...",
  "sources": [
    {"id": "f_001", "kind": "file",    "title": "calculus-notes.pdf",   "preview": "...", "included": true},
    {"id": "f_002", "kind": "file",    "title": "english-essay.docx",   "preview": "...", "included": true},
    {"id": "c_005", "kind": "cluster", "title": "วิชาคำนวณ",            "preview": "...", "included": true}
  ],
  "expires_at": "2026-05-07T10:30:00",
  "ai_calls_used": 2                 // distill + select — informational
}
```

**Errors:**
- `404 SESSION_NOT_FOUND` — session_id expired หรือ id ผิด
- `400 INVALID_CLARIFICATION` — มี > 1 field ใน clarification หรือไม่มีเลย
- `403 PACK_LIMIT_REACHED` — re-check (user อาจสร้าง pack อื่นไประหว่างนี้)
- `403 AI_QUOTA_REACHED` — re-check
- `503 LLM_UNAVAILABLE`
- `400 LLM_RESPONSE_INVALID` (มี retry 1 ครั้ง)

### 3. `POST /api/context-packs/ai-build/confirm` — NEW

**Request:**
```json
{
  "draft_id": "drf_abc123",
  "edits": {                       // optional — partial overrides
    "title": "Term 2 Study Pack",  // user แก้ title
    "type": "study",                // unchanged
    "intent": "...",                // user แก้ intent
    "scope": "...",                 // unchanged (ส่งทั้งหมดเพื่อ atomic update)
    "summary_text": "...",          // user แก้ summary
    "included_source_ids": ["f_001", "f_002"]   // user uncheck f_005 ออก
  }
}
```

**Response 200:**
```json
{
  // serialized ContextPack ตาม pattern เดิม + 3 fields ใหม่
  "id": "...",
  "type": "study",
  "title": "Term 2 Study Pack",
  "intent": "...",
  "scope": "...",
  "created_via": "ai_builder",
  "summary_text": "...",
  "source_file_ids": ["f_001", "f_002"],
  "source_cluster_ids": [],
  "is_locked": false,
  "locked_reason": null,
  "created_at": "...",
  "updated_at": "..."
}
```

**Behavior:** เรียก `create_pack()` (ของเดิม) + เพิ่ม `intent`, `scope`, `created_via="ai_builder"` → log_usage("ai_summary") (กิน quota รายเดือน) → ลบ draft ออกจาก cache → return serialized pack

**Errors:**
- `404 DRAFT_NOT_FOUND` — draft expired หรือ id ผิด
- `403 PACK_LIMIT_REACHED` — re-check (user อาจสร้าง pack อื่นไประหว่างนี้)
- `400 INVALID_TYPE` — type ไม่อยู่ใน {profile, study, work, project}
- `400 NO_SOURCES_SELECTED` — user uncheck ทุกอันใน included_source_ids

### 4. `DELETE /api/context-packs/ai-build/drafts/{draft_id}` — NEW

**Request:** path param `draft_id`

**Response 200:**
```json
{ "status": "discarded" }
```

**Behavior:** ลบ draft ออกจาก cache (no-op ถ้าไม่เจอ — graceful)

**Use case:** user กดปิด modal → ลบ draft ทันที (กัน memory leak)

### 5. `GET /api/context-packs` + `GET /api/context-packs/{id}` — additive

เพิ่ม fields ใน response: `intent`, `scope`, `created_via`

---

## 🤖 AI Workflow (ภายใน `ai_pack_builder.py` — REVISED 3-step)

### Step 0: Clarify decision + question generation (call_llm_json) — NEW (REVISED)

**System prompt:**
```
You are an AI Pack Builder assistant. Given a user's prompt and their data 
inventory, your job is to:

(A) DECIDE if the prompt is detailed enough to skip clarification
(B) IF NOT, generate ONE clarifying question with 4 high-quality options

DECISION CRITERIA — set "skip_clarify: true" if user prompt has ≥2 of 3:
  1. SOURCE specified (ชื่อไฟล์/cluster/จำนวนไฟล์ที่ชัด + match inventory)
  2. SCOPE specified (include/exclude clearly stated)
  3. FOCUS specified (เน้นอะไร — บทสรุป/exam prep/ตัวอย่าง/etc.)

Otherwise set "skip_clarify: false" and gen options.

QUALITY RULES for options (when skip_clarify=false):
  ✓ CONCRETE — ระบุชื่อไฟล์จริง หรือ cluster จริง หรือจำนวนไฟล์จริง 
    (อ้างจาก inventory ที่ให้ — NOT generic placeholders)
  ✓ ACTIONABLE — user อ่าน summary แล้วเข้าใจทันทีว่าเลือกแล้วจะได้ pack แบบไหน
  ✓ DIFFERENTIATED — แต่ละ option scope ต่างกันชัด ไม่ทับซ้อน
  ✓ SCOPED — บอก include + exclude (ถ้า relevant)
  ✓ LENGTH — summary 25-60 คำ (ไม่ใช่ short label)

ตัวอย่าง BAD option:
  ❌ {"id": 1, "title": "วิชาคำนวณ", "summary": "เน้นวิชาคำนวณ"}
ตัวอย่าง GOOD option:
  ✅ {
    "id": 1,
    "title": "วิชาคำนวณเชิงลึก",
    "summary": "ใช้ 5 ไฟล์ในกลุ่ม 'วิชาคำนวณ' (calculus-midterm-notes.pdf, linear-algebra-textbook.pdf, multivariable-calc-problems.pdf, ...) — focus สูตร + ตัวอย่างโจทย์ + วิธีคิด ไม่รวม assignment ที่ส่งไปแล้ว"
  }

Respond ONLY with valid JSON:

CASE A (skip_clarify=false):
{
  "skip_clarify": false,
  "question": "1 ประโยคถามภาษาไทย (หรือ EN ตาม user lang)",
  "options": [
    {"id": 1, "title": "...", "summary": "..."},
    {"id": 2, "title": "...", "summary": "..."},
    {"id": 3, "title": "...", "summary": "..."},
    {"id": 4, "title": "...", "summary": "..."}
  ],
  "freetext_hint": "ตัวอย่าง wording ที่ user พิมพ์ตอบได้",
  "reasoning": "เหตุผลสั้นๆ ทำไมเลือกถามแบบนี้"
}

CASE B (skip_clarify=true):
{
  "skip_clarify": true,
  "reasoning": "prompt มี SOURCE + SCOPE + FOCUS ครบ — proceed ไป /propose ได้เลย"
}

Rules:
- options ต้อง 4 ตัว (CASE A only)
- ถ้า user มี > 50 files หรือ inventory ใหญ่ → focus options บน cluster level
- ภาษาของ options follow user_lang (TH/EN)
```

**User prompt:**
```
USER PROMPT: {user_prompt}
USER LANGUAGE: {user_lang}     // "th" or "en" — follow getLang()

USER'S INVENTORY (newest 30 files + all clusters with file counts):
{_build_inventory_for_clarify(...)}
```

**Inventory format ที่ใส่ใน prompt** (ต้องมี file names ที่จริง เพื่อให้ AI quote ได้ใน option summary):
```
=== FILES (newest 30, file_kind='processed' only) ===
- calculus-midterm-notes.pdf (cluster: วิชาคำนวณ, 12,345 chars)
- linear-algebra-textbook.pdf (cluster: วิชาคำนวณ, 45,678 chars)
- english-essay-draft.docx (cluster: ภาษา, 8,234 chars)
... (max 30)

=== CLUSTERS ===
- วิชาคำนวณ (5 files)
- ภาษา (3 files)
- ข้อมูลส่วนตัว (2 files)
... (all clusters)
```

**⚠️ Vault filter (v9.1.0 dependency):** Both `_build_inventory_for_clarify()` + `_build_inventory_for_pack_builder()` ต้องเพิ่ม `File.file_kind == "processed"` ใน WHERE clause (ตาม pattern ใน [organizer.py:25, 439](../../backend/organizer.py#L25)). Vault files (file_kind="vault_only") = AI อ่านไม่ได้ → ห้ามใส่เป็น source

**Result handling:**
- **Case A (skip_clarify=false):** เก็บ session ใน `_SESSION_CACHE` พร้อม inventory snapshot + options + question → return ให้ frontend
- **Case B (skip_clarify=true):** เก็บ session แบบ flagged → frontend เรียก /propose ทันทีด้วย `clarification: {skipped: true}`

**Why session even when skip_clarify:** /propose ใช้ session_id เพื่อ get inventory snapshot ที่ consistent — ไม่ดึง inventory ใหม่ (กัน race condition)

### Step 1: Source selection (call_llm_json)

**System prompt:**
```
You are an AI Pack Builder for Personal Data Bank. Your job is to select 
the most relevant source items (files + clusters) for a Context Pack 
that matches the user's intent.

You have access to the user's full inventory. Select 3-10 items that 
are most relevant. Prefer items with higher importance and clear 
topical match.

Respond ONLY with valid JSON:
{
  "selected_files": ["file_id_1", "file_id_2", ...],
  "selected_clusters": ["cluster_id_1", ...],
  "suggested_title": "ชื่อ pack ที่เหมาะ — ภาษาไทย",
  "suggested_type": "profile|study|work|project",
  "suggested_intent": "1-2 ประโยคบอกว่า pack นี้ใช้ทำอะไร — ภาษาไทย",
  "suggested_scope": "1-2 ประโยคบอกว่าครอบคลุมอะไร / ไม่รวมอะไร — ภาษาไทย",
  "reasoning": "เหตุผลสั้นๆ เป็นภาษาไทย"
}

Rules:
- Total selected items ≥ 1, ≤ 10
- suggested_type: pick best fit, ไม่ใช่ default project
- ถ้า user prompt match กับ inventory ไม่ดี → คืน reasoning อธิบาย + select item ที่พอจะ match
```

**User prompt (REVISED — เพิ่ม clarification context):**
```
USER PROMPT: {prompt}
PREFERRED TYPE (optional hint): {preferred_type or "ไม่ระบุ — เลือกเอง"}

CLARIFICATION:
{
  if selected_option_id: "User chose: {option.label}"
  if freetext: "User additional context: {freetext}"
  if skipped: "User skipped clarification — use your best judgment"
}

USER'S INVENTORY:
{_build_inventory_for_pack_builder(...)}
```

**Inventory format (reuse pattern จาก retriever.py):**
```
=== AVAILABLE FILES ===
FILE_ID: f_001
FILENAME: calculus-notes.pdf
CLUSTER: วิชาคำนวณ (ID: c_005)
SUMMARY_PREVIEW: เนื้อหา calculus เบื้องต้น...
TEXT_LENGTH: 12,345 chars
---
... (max 50 most-recently-updated files — กัน prompt ใหญ่เกิน)

=== AVAILABLE CLUSTERS ===
CLUSTER_ID: c_005
TITLE: วิชาคำนวณ
FILE_COUNT: 3
SUMMARY: รวมเอกสารวิชา calculus + linear algebra
---
... (all clusters — มักไม่เกิน 20)
```

### Step 2: Distillation (call_llm_pro)

หลังเลือก source ได้ → gather content (ตาม `create_pack()` pattern เดิม) → call `_generate_pack_content()` (function เดิมใน context_packs.py) แต่ส่ง `intent` + `scope` เพิ่มเข้า prompt เพื่อให้ AI distill เน้นทิศทางที่ถูก:

**System prompt update (เพิ่มจากของเดิม):**
```
You are a context distillation AI...

This is a "{type_label}" context pack titled "{title}".

INTENT (ใช้สำหรับ): {intent}
SCOPE (ครอบคลุม): {scope}

Rules:
- Write ALL output in THAI language
- Distill key themes that match the INTENT and SCOPE
- ...rest unchanged...
```

### Caches (in-memory dicts) — REVISED 2 caches

```python
# in ai_pack_builder.py
_SESSION_CACHE: dict = {}  # session_id -> {user_id, prompt, inventory_snapshot, options, created_at}
_DRAFT_CACHE: dict = {}    # draft_id -> {user_id, payload, created_at}
_TTL_SECONDS = 1800        # 30 นาที (ทั้ง session + draft)

def _gc_expired():
    """Lazy GC — เรียกตอน clarify หรือ propose ใหม่"""
    now = datetime.utcnow()
    for cache in (_SESSION_CACHE, _DRAFT_CACHE):
        expired = [k for k, v in cache.items() 
                   if (now - v["created_at"]).total_seconds() > _TTL_SECONDS]
        for k in expired:
            del cache[k]

# ตอน clarify: _SESSION_CACHE[session_id] = {user_id, prompt, inventory_snapshot, options, created_at: now}
# ตอน propose: ตรวจ session ของ user → ใช้ inventory_snapshot จาก cache → gen draft → เก็บใน _DRAFT_CACHE
# ตอน confirm: ตรวจ draft user_id match → pop draft → save real pack
```

**ทำไมต้องมี inventory snapshot ใน session:** ถ้า user upload ไฟล์ใหม่ระหว่างทาง (clarify → propose) → AI จะเห็น inventory ที่เปลี่ยนไป → options ที่เคยกำหนดไว้อาจไม่ match. ใช้ snapshot ของตอน clarify ทำให้ session consistent

**ทำไม in-memory ไม่ใช่ DB:** Draft เป็น ephemeral (30 min) + parallel กับ `MCP_PERMISSIONS` pattern ที่มีอยู่ + simpler (ไม่ต้อง schema migration). Trade-off: หาย restart — แต่ไม่กระทบ user (สามารถ propose ใหม่ได้)

---

## 🛠️ Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — Backend foundation (~2 days, REVISED)

**1.1 Schema migration** (`backend/database.py`)
- เพิ่ม 3 Column declarations ใน `class ContextPack`
- เพิ่ม idempotent ALTER block ใน `init_db()` (ตาม pattern v8.1/v8.2)

**1.2 `create_pack()` extension** (`backend/context_packs.py`)
- เพิ่ม parameters `intent: str = ""`, `scope: str = ""`, `created_via: str = "manual"`
- update `_generate_pack_content()` ให้รับ optional `intent` + `scope`
- update `_serialize_pack()` expose 3 fields ใหม่

**1.3 New module `backend/ai_pack_builder.py`** (~380 lines, REVISED +100 lines)
- `_SESSION_CACHE` + `_DRAFT_CACHE` + `_TTL_SECONDS = 1800`
- `_gc_expired()` lazy GC ทั้ง 2 caches
- `_build_inventory_for_pack_builder(db, user_id, max_files=50) -> str` — used by /propose
- `_build_inventory_for_clarify(db, user_id, max_files=30) -> str` — used by /clarify (เล็กกว่า เพื่อ token efficiency)
- `clarify_prompt(db, user_id, prompt: str) -> dict` — Step 0 LLM call → cache session → return question + 4 options
- `propose_pack(db, user_id, session_id: str, clarification: dict, preferred_type: str | None) -> dict` — Step 1+2 LLM flow + cache draft
- `confirm_pack(db, user, draft_id: str, edits: dict | None) -> dict` — apply edits + create_pack + log_usage + drop draft + drop session
- `discard_draft(user_id, draft_id) -> bool`

**1.4 New endpoints** (`backend/main.py`)
- 3 Pydantic models: `AIBuilderClarifyRequest`, `AIBuilderProposeRequest`, `AIBuilderConfirmRequest`
- 4 endpoints: /clarify, /propose, /confirm, DELETE /drafts/{id}
- Pre-checks ที่ /clarify (pack quota + ai quota) → กัน user เริ่ม flow ที่ทำไม่จบได้

**1.5 Version bump** — `config.py` APP_VERSION 9.1.0 → 9.2.0 (foundation = 9.1.0 ที่ ship Raw Vault + correctness fixes)

### Phase 2 — Frontend modal (~1.5 days, REVISED — 4 view states)

**2.1 HTML** — เพิ่มใน `app.html`:
- ปุ่ม "🪄 ให้ AI สร้างให้" ใน Packs tab header (ข้างปุ่ม "+ สร้าง Pack")
- Modal #ai-pack-builder-modal (4 view states: **input → clarify → loading → preview**)

**2.2 JS** — `app.js`:
- `openAIPackBuilder()` — show modal, state="input", reset
- `submitInitialPrompt()` — POST `/ai-build/clarify`
  - **ถ้า response.skip_clarify=true** → state="loading" → POST `/ai-build/propose` ทันทีด้วย `clarification: {skipped: true}` → state="preview"
  - **ถ้า response.skip_clarify=false** → state="clarify" (แสดง question + 4 option cards + textarea + skip button)
- `submitClarification()` — POST `/ai-build/propose` (ส่ง session_id + clarification) → state="loading" → "preview"
- `selectClarifyOption(id)` — คลิก option card 1-4 → highlight selected + enable "ยืนยันตัวเลือก" button
- `submitClarifyFreetext()` — เก็บ textarea value → submit ด้วย `freetext`
- `skipClarify()` — submit ด้วย `skipped: true`
- `renderAIDraftPreview(draft)` — render checkbox sources + form inputs ครบทุก field
- `confirmAIDraft()` — POST `/ai-build/confirm`
- `regenerateAIDraft()` — clear draft, กลับไป state="input" (prompt เดิมยังอยู่)
- `discardAIDraft()` — DELETE draft + close modal + reset
- 16 i18n keys (TH+EN) — เพิ่ม 6 keys สำหรับ clarify state (question label, freetext placeholder, skip button label, "loading: AI กำลังคิด...", "preview: นี่คือสิ่งที่จัดให้", "auto-skipped: AI เข้าใจ prompt ของคุณแล้ว ข้ามคำถาม")

**2.3 CSS** — `styles.css`:
- `.ai-builder-modal` (wide modal)
- `.ai-clarify-state` (NEW — radio button options + textarea + skip button)
- `.ai-clarify-option` (clickable card — radio + label + hover effect)
- `.ai-draft-preview`
- `.ai-source-checkbox-list`
- `.ai-loading-state`, `.ai-error-state`

### Phase 3 — Smoke test (~0.5 day, REVISED — 24 cases)

**3.1** `scripts/ai_pack_builder_smoke.py` — 24 cases (Group A 6 + B 5 + C 5 + D 5 + E 3) ครอบคลุม happy path + skip-clarify path + quality assertions

**Quality assertions (T-A2 + T-A3) ตัวอย่าง:**
```python
# T-A2: option summary ต้อง quote ชื่อไฟล์/cluster จริง
inventory_filenames = {f.filename for f in user_files}
inventory_clusters = {c.title for c in user_clusters}
for opt in clarify_response["options"]:
    quoted = any(name in opt["summary"] for name in inventory_filenames | inventory_clusters)
    assert quoted, f"Option '{opt['title']}' ไม่ quote ชื่อไฟล์/cluster จริง"

# T-A3: summary length quality
for opt in clarify_response["options"]:
    word_count = len(opt["summary"].split())
    assert 25 <= word_count <= 80, f"Option summary {word_count} คำ — ต้อง 25-60"
```

---

## 🧪 Test Scenarios (REVISED — 22 cases, เพิ่ม clarify flow)

### Group A: Clarify flow + skip logic + vault filter (7 cases — NEW)
- **T-A1** Vague prompt ("ช่วยสร้าง pack") → /clarify คืน skip_clarify=false + 4 options + question
- **T-A2** Options ที่ AI gen อ้างอิง file/cluster names จาก inventory จริง (assert: option.summary contains ≥1 ชื่อไฟล์ หรือชื่อ cluster จาก inventory)
- **T-A3** Each option.summary ความยาว ≥25 คำ (quality criterion)
- **T-A4** Detailed prompt ("สร้าง pack จากไฟล์ calculus.pdf + algebra.pdf focus สูตรไม่รวม assignment") → /clarify คืน skip_clarify=true (ไม่ gen options)
- **T-A5** Session expire after 30 min → /propose 404 SESSION_NOT_FOUND
- **T-A6** /clarify call นับ 1 LLM call (informational ai_calls_used = 1)
- **T-A7** Vault filter: setup user มี 2 ไฟล์ processed + 1 ไฟล์ vault_only → /clarify inventory ต้องไม่มี vault file (assert vault filename ไม่ปรากฏใน prompt context)

### Group B: Propose with clarification (5 cases)
- **T-B1** Propose with `selected_option_id: 1` → AI build draft ที่ scope ตรงกับ option
- **T-B2** Propose with `freetext: "..."` → AI ใช้ freetext เป็น context
- **T-B3** Propose with `skipped: true` → AI ตัดสินใจเอง (ใช้แค่ initial prompt)
- **T-B4** Propose with > 1 field ใน clarification → 400 INVALID_CLARIFICATION
- **T-B5** Propose without any clarification field → 400 INVALID_CLARIFICATION

### Group C: Happy path end-to-end (5 cases)
- **T-C1** Full flow (clarify → propose → confirm with no edits) → ContextPack row created with `created_via="ai_builder"` + intent + scope
- **T-C2** Confirm with edits (uncheck source + แก้ title) → DB row เก็บ edits ของ user
- **T-C3** API list returns `intent`, `scope`, `created_via` ใน response
- **T-C4** Total LLM calls per confirmed pack = 3 (clarify + select + distill) → log_usage("ai_summary") นับครั้งเดียวต่อ confirm
- **T-C5** Vector index มี pack-{id} หลัง confirm (parity กับ manual create)

### Group D: Validation (3 cases)
- **T-D1** Prompt < 10 chars → /clarify 400 PROMPT_TOO_SHORT
- **T-D2** Prompt > 500 chars → /clarify 400 PROMPT_TOO_LONG
- **T-D3** User มี 0 files + 0 clusters → /clarify 400 NO_SOURCES_AVAILABLE
- **T-D4** Confirm with empty `included_source_ids` → 400 NO_SOURCES_SELECTED
- **T-D5** Invalid type ใน edits → 400 INVALID_TYPE

### Group E: Quota / Auth (3 cases)
- **T-E1** Free user ที่มี pack 10 อันแล้ว → /clarify 403 PACK_LIMIT_REACHED (ก่อน hit LLM)
- **T-E2** Free user ที่ใช้ ai_summary ครบ 50/เดือน → /clarify 403 AI_QUOTA_REACHED
- **T-E3** User A clarify session → User B propose ด้วย session_id ของ A → 404 (กัน steal)

### Group F: Edge cases (2 cases)
- **T-F1** LLM return invalid JSON → retry 1 ครั้ง → ถ้ายัง fail → 400 LLM_RESPONSE_INVALID
- **T-F2** Discard draft แล้ว confirm → 404 DRAFT_NOT_FOUND

### Frontend integration (4 — manual smoke โดย user)
- **F1a** Vague prompt → state="input" → submit → state="clarify" แสดง 4 options + textarea + skip → user เลือก option → loading → preview
- **F1b** Detailed prompt → state="input" → submit → **ข้าม clarify** → loading → preview ทันที
- **F2** Uncheck source 1 อัน + แก้ title → confirm → toast success → modal ปิด → list refresh มี pack ใหม่
- **F3** กด "ลองใหม่" จาก preview → กลับไป state="input" (prompt เดิมยังอยู่) → submit ใหม่

### Regression (run after change)
- ✅ 21/21 ของ context_pack_correctness_smoke (v9.0.1) ยัง pass
- ✅ 25/25 admin_e2e (v8.2.0) ยัง pass
- ✅ existing manual create pack flow ยัง work (ไม่ break เพราะ create_pack signature เปลี่ยนแบบ default param)
- ✅ Python syntax + JS syntax clean

---

## ✅ Done Criteria

- [ ] Schema migration: 3 columns ใน context_packs + idempotent ALTER block
- [ ] backend/ai_pack_builder.py module ครบ + 3 endpoints + 2 Pydantic models
- [ ] backend/context_packs.py: create_pack รับ 3 params ใหม่, _serialize_pack expose ครบ
- [ ] Frontend: ปุ่ม + modal + 4 functions + i18n + CSS — desktop + mobile (375px) ใช้งานได้
- [ ] scripts/ai_pack_builder_smoke.py: 18/18 PASS
- [ ] Regression v9.0.1 + v8.2.0 ยังผ่านทั้งหมด
- [ ] APP_VERSION bump 9.0.1 → 9.2.0 (skip 9.1.0 — reserved for Raw Vault)
- [ ] Commits แยก 5 logical:
  1. `feat(db): context_packs intent/scope/created_via columns + migration [v9.2.0]`
  2. `feat(api): create_pack accept intent/scope/created_via [v9.2.0]`
  3. `feat(ai): ai_pack_builder module + 4 endpoints (clarify/propose/confirm/discard) [v9.2.0]`
  4. `feat(frontend): AI Pack Builder modal + clarify→preview→edit flow [v9.2.0]`
  5. `chore: bump APP_VERSION 9.2.0 + plan + smoke + memory [v9.2.0]`
- [ ] pipeline-state.md updated → built_pending_review

---

## ⚠️ Risks / Open Questions

### Risks
1. **R1 — LLM cost เพิ่มต่อ user (2 calls per propose)** → Mitigation: nab `ai_summary` quota รายเดือน + check ก่อน hit LLM
2. **R2 — Draft cache memory growth** → Mitigation: lazy GC ตอน propose + 30 min TTL + max 1 draft/user (overwrite old)
3. **R3 — User confuse ระหว่าง manual + AI flow** → Mitigation: 2 ปุ่มแยกชัดเจน (`+ สร้าง Pack` vs `🪄 ให้ AI สร้างให้`) + AI badge บนการ์ด pack ที่ created_via="ai_builder"
4. **R4 — LLM ตอบ JSON ผิด format** → Mitigation: retry 1 ครั้ง + 400 error ที่ user-friendly + log warning
5. **R5 — User มี file/cluster ใหม่กว่า 50 ไม่ปรากฏใน inventory** → Mitigation: order by updated_at DESC limit 50 (ใหม่สุดก่อน) + แจ้ง user ใน reasoning ถ้า inventory ใหญ่เกิน 50
6. **R6 — In-memory draft หาย restart** → Acceptable trade-off: user re-propose ได้ + ไม่ persist แค่ 30 min ไม่กระทบ
7. **R7 — `created_via` field expose แต่ frontend ยังไม่ใช้แสดง badge** → ไม่ใช่ regression (additive field) — feature จะใช้ display badge ใน v9.3.0+

### Open Questions (มี default ทุกข้อ — ถ้า user ไม่ตอบใช้ default)
- **Q1** Inventory cap 50 files พอไหม? (กัน prompt ใหญ่ + LLM cost) → **Default: 50** สำหรับ /propose, **30** สำหรับ /clarify (เพื่อ token efficiency)
- **Q2** `preferred_type` field ใน request โผล่ใน UI ไหม? → **Default: ไม่มี** ใน UI v9.2.0 (AI เดาเอง) — preserve ไว้ใน API เผื่อ MCP ใช้
- **Q3** ปุ่ม "🪄 ให้ AI สร้างให้" จะ label ว่ายังไง? → **Default: TH = "🪄 ให้ AI สร้างให้", EN = "🪄 AI Build for me"**
- **Q4** TTL 30 นาทีพอไหม (ทั้ง session + draft)? → **Default: 30 min**
- **Q5** ปุ่ม "ลองใหม่" จาก preview → กลับไป state ไหน? → **Default: state="input"** (prompt เดิมยังอยู่ในช่อง — user แก้ได้ก่อน submit ใหม่)
- **Q6** Clarify step ทำทุกครั้งหรือ skip ได้ถ้า prompt ละเอียด? → **Default: AI ตัดสินใจเอง** — เกณฑ์: prompt มี ≥2 ใน 3 (SOURCE/SCOPE/FOCUS) → skip clarify, ไปสร้าง draft ทันที. ถ้าไม่ครบ → ถาม. ผู้ใช้ที่พิมพ์ละเอียดไม่ต้องตอบคำถามซ้ำซ้อน
- **Q7** ถ้า user เลือก option แล้ว เปลี่ยนใจ → กลับไปเลือก option อื่นได้ไหม? → **Default: ใช่** (radio button — เลือกใหม่ทับได้ ก่อนกด submit)
- **Q8** AI gen options ภาษาไทยเสมอ หรือ follow getLang()? → **Default: follow getLang()** — TH user ได้ TH options, EN user ได้ EN options

---

## 📝 Notes for เขียว (gotchas + reuse patterns)

### Gotchas
0. **🆕 Vault filter ต้องอยู่ทั้ง 2 inventory builders** — ใช้ `File.file_kind == "processed"` ใน WHERE clause (ตาม pattern organizer.py:25). ลืมจะทำให้ AI เลือก vault file ที่มี extracted_text ว่าง → pack คุณภาพแย่
1. **`check_pack_create_allowed` + `check_summary_allowed` ต้องเรียกก่อน LLM** — กัน user หมด quota แล้วยังกิน LLM token. ลำดับ: pack_limit check → ai_quota check → LLM call
2. **Draft cache user_id ผูกแน่น** — `confirm_pack()` ต้องตรวจ `_DRAFT_CACHE[draft_id]["user_id"] == user.id` ก่อน apply (กัน steal id)
3. **`log_usage("ai_summary")` เรียกใน `confirm_pack()` หลัง create_pack สำเร็จ** — ไม่ใช่ใน `propose_pack()` (กัน user propose แล้วทิ้ง = quota หาย)
4. **`create_pack()` signature เปลี่ยน — default params ทำให้ backward compat** แต่ MCP `_tool_create_context_pack` ต้อง update ให้ส่ง `created_via="ai_builder"` หรือ default? → **Default: "manual" — MCP ไม่กระทบ** (ใช้ default ของ create_pack)
5. **Frontend modal: form-based edit** — gather ทุก field ตอน confirm, ส่ง full payload ไม่ใช่ partial diff (atomic update)
6. **Modal CSS reuse `.modal-overlay` + `.modal` ของ shared.css** — เพิ่มแค่ child class `.ai-builder-modal` สำหรับ width override
7. **`vector_search.index_file()` เรียกใน `create_pack()` อัตโนมัติอยู่แล้ว** — AI builder confirm ได้ pack ที่ index พร้อมใช้งาน chat ได้ทันที
8. **Bump APP_VERSION 9.0.1 → 9.2.0 (skip 9.1.0)** — เหตุผล: v9.1.0 ถูกจองให้ Raw Vault plan parallel ที่อยู่ใน pipeline แล้ว
9. **AI prompt response parsing**: ใช้ `call_llm_json()` ที่มีอยู่แล้ว — มัน strip ```json fence + auto-find { } อัตโนมัติ + raise exception ถ้า fail (catch แล้ว retry 1 ครั้ง)
10. **Inventory format: `_build_inventory_for_pack_builder` แยกจาก `_build_inventory` ใน retriever.py** — ของ retriever ใช้สำหรับ chat selection (มี importance/primary), ของ builder ใช้สำหรับ pack creation (ใส่ summary preview ครบ)

### Reuse patterns
- ดู [scripts/context_pack_correctness_smoke.py](../../scripts/context_pack_correctness_smoke.py) เป็น template สำหรับ smoke test (mock LLM, sandbox DB, in-process TestClient)
- ดู [backend/admin.py](../../backend/admin.py) เป็น template สำหรับ module structure (single file, dependency injection, ValueError → HTTPException ที่ endpoint)
- ดู [backend/context_packs.py:131-137](../../backend/context_packs.py#L131-L137) เพื่อตามแบบ vector_search.index_file call ใน create_pack
- ดู [backend/retriever.py:320-363](../../backend/retriever.py#L320-L363) เพื่อตามแบบ inventory format
- ดู [legacy-frontend/admin.html:172-201](../../legacy-frontend/admin.html#L172-L201) เพื่อตาม pattern modal + form + footer buttons

### Out of scope guard
ระหว่าง build ถ้าเจอประเด็นพวกนี้ — **อย่าทำในรอบนี้**:
- เพิ่ม MCP tool `ai_build_pack` (เลื่อน v9.3.0)
- Auto-suggest หลัง organize-new (เลื่อน v9.3.0)
- Chat-style multi-turn revise (Q4 user เลือก retry — ไม่ทำ v9.2.0)
- AI badge บน pack card (frontend visual — เลื่อน v9.3.0)
- `usage_hint` field (เลื่อน — Q1 user เลือกแค่ 2 fields)

ถ้าเจอประเด็นใหม่ที่ต้องตัดสิน → แจ้งผ่าน [inbox/for-แดง.md](../communication/inbox/for-แดง.md) ก่อนตัดสินใจ

---

## 📋 Pipeline Next

1. 🔴 **User review plan** — ตอบ Q1-Q5 (หรือยอมรับ default)
2. 🟢 **เขียวเริ่ม build** — Phase 1 → 2 → 3 ตาม step-by-step (~2.5-3 วัน)
3. 🟢 **เขียว self-test** — รัน `scripts/ai_pack_builder_smoke.py` (T1-T18) + manual F1-F3 ใน browser
4. 🔵 **ฟ้า review** — verify 18/18 + regression + commit messages + memory updates
5. 🔴 **User approve + push + deploy**

---

## 📊 Why this plan is good (self-check)

✅ **Scope ชัด** — 5 design decisions ตอบครบ Q1-Q5 จาก user, ไม่มี ambiguity
✅ **Reuse heavy** — leverage `create_pack`, `check_*_allowed`, `_build_inventory` pattern, `call_llm_json`, vector_search auto-index — โค้ดใหม่จริง ~280 + 200 lines
✅ **Backward compat** — schema additive, API additive, frontend เพิ่ม button ไม่กระทบ flow เดิม
✅ **Cost guard** — quota check ก่อน LLM, draft cache TTL, inventory cap
✅ **Test ครอบคลุม** — 18 cases (5 happy + 5 validation + 4 quota/auth + 4 edge + 3 manual) + regression suite
✅ **Out-of-scope guarded** — แต่ละ deferred item ระบุชัดว่าไป v9.3.0+
✅ **Risks ระบุ + mitigation ครบ** — 7 risks มี mitigation ทุกข้อ
