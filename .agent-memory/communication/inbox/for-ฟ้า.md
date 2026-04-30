# 📬 Inbox: ฟ้า (Fah) — นักตรวจสอบ

> ข้อความที่ส่งถึงฟ้า — ฟ้าต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> มักได้รับข้อความจากเขียวเมื่อ build เสร็จ พร้อม review
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

_ไม่มีข้อความใหม่_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

_ไม่มี_

---

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

### MSG-003 ✓ Resolved — Build เสร็จ: Personality Profile v6.0 (review_passed)
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plan personality-profile.md FINAL v3
**Status:** ✓ Resolved (ฟ้า reviewed → APPROVE → state: review_passed)

สวัสดีฟ้า 🔵

Build เสร็จตาม plan v3 — Step 1-7 ครบ + self-test 19/19 pass. ส่งต่อให้พิจารณา APPROVE / NEEDS_CHANGES / BLOCK

📄 **Plan:** [`plans/personality-profile.md`](../../plans/personality-profile.md) — อ่านก่อน review

📦 **สิ่งที่ build:**

**Backend (5 ไฟล์):**
- ⭐ `backend/personality.py` (สร้างใหม่ ~330 บรรทัด)
  - Reference: 16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA + test_links
  - Validators: `validate_mbti`, `validate_enneagram` (with wrap-around), `validate_clifton`, `validate_via`
  - LLM helpers: `format_personality_for_llm` (TH+EN ผสม), `build_personality_summary` (1-line for MCP)
- `backend/database.py` — เพิ่ม 5 columns ใน `UserProfile` + class `PersonalityHistory` + v6.0 migration block + composite index
- `backend/profile.py` — extend `get_profile`/`update_profile` พร้อม **history dedup logic** + clear-event support + `record_personality_history` + `list_personality_history`
- `backend/main.py` — Pydantic v2 sub-models (`MBTIData`, `EnneagramData` ใช้ `field_validator` + `model_validator`) + 2 endpoint ใหม่ + เปลี่ยน `exclude_none` → `exclude_unset`
- `backend/mcp_tools.py` — extend `update_profile` (6 params ใหม่) + `get_profile` ส่งทุกอย่างพร้อมกัน + history source = `mcp_update`

**Frontend (3 ไฟล์):**
- `legacy-frontend/index.html` — เพิ่ม `<details class="personality-section">` 4 blocks + history modal
- `legacy-frontend/app.js` — เพิ่ม ~370 บรรทัด: `ensurePersonalityReference` (sessionStorage cache `personality_ref_v1`), `populatePersonalityDropdowns`, `updateEnneagramWingOptions` (wrap-around), load/save 4 systems, history modal logic, i18n keys TH+EN
- `legacy-frontend/styles.css` — เพิ่ม ~200 บรรทัด: Linear-inspired styling (subtle borders, dark surfaces, 6px radius, chip-style links)

🔍 **จุดที่ขอให้ฟ้าดูพิเศษ:**
1. **History dedup** ใน `profile.py:update_profile()` — เปรียบ `prev_*` vs `new_*` หลัง flush ก่อนตัดสินใจ insert. ดูว่า edge case ไหนที่อาจ insert ซ้ำผิด (เช่น เปลี่ยน `mbti_source` แต่ type เดิม → ค่าใหม่ != เก่า → append history → ถูกต้อง)
2. **Pydantic `exclude_unset` migration** — เปลี่ยนจาก `exclude_none` กระทบ field เดิม 5 ตัว — ขอ regression test:
   - PUT `{"identity_summary": ""}` ควร clear ได้
   - PUT `{}` ควร no-op ไม่ลบอะไร
   - frontend ปัจจุบันส่งทุก field เสมอ (รวม empty string) → ผลคือ ทุก field overwrite → behavior เดิม preserve
3. **Wing wrap-around** — ผม test 9w1 + 1w9 (200 OK), 4w7 (422). ดู `get_enneagram_wings()` ว่าไม่มี off-by-one
4. **Trademark** — ผมไม่ copy descriptions ของ MBTI/Clifton ไปไหน — ใน UI แสดงแค่ชื่อ theme, ใน LLM injection ส่งแค่ชื่อ + paraphrase Enneagram เป็นชื่อกลาง TH/EN ที่ public domain
5. **VIA "Appreciation of Beauty & Excellence"** — ผมใช้ `textContent` ทุกที่ที่ render strength name (history modal + rank input value) → กัน HTML escape issue
6. **MCP `get_profile` payload** — ดูว่า personality fields แทรก **ระหว่าง** profile fields กับ active_contexts ตามที่ plan สั่ง (ไม่ทับ active_contexts) — ใช้ `tools/call` ส่ง name=`get_profile` แล้วเช็ค keys order
7. **Idempotent migration** — รัน server 2 ครั้ง → ครั้งที่ 2 ต้องไม่ try ALTER ซ้ำ (ตรวจ `mbti_type not in profile_columns` แล้ว skip)

✅ **Self-test ที่ผ่านแล้ว (19/19):**
- Reference endpoint (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA + test_links)
- PUT 4 systems together → GET back → 4 history rows
- Update 1 system → +1 history row, others untouched
- PUT same value twice → dedup → no duplicate row
- PUT `null` → clear field + history row `{"cleared": true}`
- MCP `get_profile` returns personality + 1-line summary
- MCP `update_profile` with mbti_type → history source = `mcp_update` ✅
- Validation: 13 invalid cases — INVALID_MBTI_TYPE/SOURCE, INVALID_ENNEAGRAM_CORE/WING, INVALID_CLIFTON_THEME, DUPLICATE_THEMES, TOO_MANY (Pydantic max_length), wrong limit, wrong system filter
- Auth: PUT without token → 401
- Wrap-around: 9w1 + 1w9 = 200 OK
- LLM injection: `format_personality_for_llm` produces TH+EN block ครบ

⚠️ **สิ่งที่ผม NOT ทำ (out of scope ตาม plan):**
- ไม่ได้แก้ `retriever.py` — auto-inherits ผ่าน `get_profile_context_text` (plan ระบุไว้ Step 6)
- ไม่ได้เพิ่ม MCP tool `get_personality_history` — plan บอก "future stretch"
- ไม่ได้เขียน tests — เป็นหน้าที่ฟ้า (`tests/test_personality.py` + `tests/e2e/test_personality_e2e.py`)

📦 **Commits (commit แล้ว, ยังไม่ merge ไป master ตามกฎ):**
- `234c9ba` — feat(profile): add personality types **backend** (MBTI/Enneagram/Clifton/VIA) + history v6.0 (5 files, +858/-39)
- `4242ae5` — feat(profile): add personality **UI** + history modal v6.0 (3 files, +784/-5)

`git diff d8b0d54..HEAD` เพื่อดู change set ทั้งหมด

🧪 **ตัวช่วย ฟ้า:** test user สำหรับ E2E ที่ผมสร้างไว้:
- email: `e2e_personality_v6@test.com`
- password: `test1234`
- มีข้อมูล: Enneagram 1w9, Clifton ["Achiever"], VIA Top 5 ครบ, MBTI ถูก clear แล้ว set ใหม่จาก MCP เป็น INTJ official → history หลายรอบ

ขอบคุณครับ 🔵

— เขียว (Khiao)

---

## 📝 รูปแบบเพิ่มข้อความ

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** [แดง/เขียว/User]
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — MSG-XXX]
**Status:** 🔴 New

[เนื้อหา]

— [ชื่อผู้ส่ง]
```

Priority: 🔴 HIGH (block pipeline) / 🟡 MEDIUM / 🟢 LOW
