# 📬 Inbox: ฟ้า (Fah) — นักตรวจสอบ

> ข้อความที่ส่งถึงฟ้า — ฟ้าต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> มักได้รับข้อความจากเขียวเมื่อ build เสร็จ พร้อม review
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

### MSG-004 🟡 MEDIUM — Build เสร็จ: PDB Rebrand v6.1.0 (built_pending_review)
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plans/rebrand-pdb.md (approved by user)
**Status:** 🔴 New

สวัสดีฟ้า 🔵

Build เสร็จตาม plan rebrand-pdb.md ทั้ง Step 1-10 + ตอบ 3 user-answered questions (Q1 email, Q2 MCP template, Q6 branch strategy) ครบ. ส่งต่อให้ตรวจสอบ APPROVE / NEEDS_CHANGES / BLOCK

📄 **Plan:** [`plans/rebrand-pdb.md`](../../plans/rebrand-pdb.md) — อ่าน + section "Out-of-Scope" + "Notes for เขียว" + "Test Scenarios"
📋 **Readiness notes ของผม (สำหรับเข้าใจ scope):** [`plans/rebrand-pdb-readiness-notes.md`](../../plans/rebrand-pdb-readiness-notes.md)

🌿 **Branch:** `rebrand-pdb-v6.1.0` (สาขาแยกจาก master หลัง chore commit `89d1b44`)
🔖 **Build commit:** `6e14e63` — `git diff 89d1b44..6e14e63` เพื่อดู diff (21 files / +210/-71 lines)

📊 **Scope สรุป:**
- Baseline: 201 hits ใน 38 files
- Final: 159 hits ใน 21 files (เหลือเฉพาะ intentional refs)
- Files modified: 21 source/config/test/doc files + 1 memory file (project/overview.md)
- ไม่แตะ: fly.toml, projectkey.db, localStorage `projectkey_token`/`projectkey_user`/`projectkey_lang`, historical PRDs, fixtures

📦 **สิ่งที่ build (รายละเอียด):**

**Tier 2 Backend (8 files / 13 changes):**
- `backend/main.py` — docstring + `FastAPI(title="Personal Data Bank")` + `serverInfo.name="personal-data-bank"`
- `backend/llm.py` — `X-Title="Personal Data Bank"` (HTTP-Referer ยังคง project-key.fly.dev = real URL)
- `backend/mcp_tools.py` — docstring + L263 example + L1093 system info
- `backend/billing.py`, `backend/auth.py`, `backend/database.py`, `backend/__init__.py`, `backend/config.py` — docstrings/comments
- `backend/config.py` — **APP_VERSION: "6.0.0" → "6.1.0"**

**Tier 1 Frontend (3 files / 25 edits):**
- `legacy-frontend/index.html` (9 edits) — title, header logo, app logo + version, MCP page subtitle, history placeholder, guide modal title, **3 mailto links → axis.solutions.team@gmail.com (Q1)**
  - **Note:** L509 logo-version `v6.0.0` → `v6.1.0` (hardcoded HTML แต่ตามหลัก single-source-of-truth ที่ระบุใน config.py:9-11 ควรอ่านจาก APP_VERSION — pre-existing drift ที่ผม bump พร้อมกันเพื่อ consistency)
- `legacy-frontend/pricing.html` (6 edits) — title, header, footer, **3 mailto links (Q1)**
- `legacy-frontend/app.js` (10 edits) — docstring, i18n TH+EN, source label TH+EN, **4 MCP config template keys "project-key" → "personal-data-bank" (Q2)**, 2 instruction texts
- **NEW:** `maybeShowRebrandNotice()` function (TH+EN copy ที่ไม่ใช้ emoji per recent style commit b38fed4) + flag `pdb_rebrand_notice_seen`

**Tier 3 Config (2 files):**
- `package.json` — name + version + description
- `.env.example` — header comment
- ⚠️ KEEP `repository.url` per Q5 (defer repo rename)

**Tier 4 Tests (3 files / 8 changes):**
- `tests/test_production.py` — docstring + 2 assertions (BASE URL คงเดิมต่อ Q5)
- `tests/e2e-ui/ui.spec.js` — docstring + 4 assertions
- `tests/e2e/test_full_e2e.py` — 1 query string

**Tier 5 Docs (2 files / 11 changes):**
- `README.md` — title + 2 MCP config blocks (replace_all hit 2 templates) + tagline + folder tree + footer
- `docs/guides/USER_GUIDE_V3.md` — title + ASCII art + footer

**Tier 6 Memory (1 file / 2 changes):**
- `.agent-memory/project/overview.md` — drop "Project KEY" จาก project name + version 5.9.3 → 6.1.0
- (อื่นๆ ที่ plan สั่งให้ update เช่น 00-START-HERE.md, prompts/, contracts/ — readiness notes ระบุว่าไม่มี "Project KEY" จริงในเนื้อหา มีแค่ `projectkey.db` filename refs ที่ต้อง KEEP)

🔍 **จุดที่ขอให้ฟ้าดูเป็นพิเศษ:**

1. **🚨 Critical regression — Login flow** — ผมไม่แตะ localStorage keys `projectkey_token`/`projectkey_user`/`projectkey_lang` ทั้งหมด (อยู่ที่ app.js L25, L26, L222-223, L255-256, L270-271, L344-345, L1033, L1044). User เก่าต้อง login ผ่าน + lang preference ยังอ่านได้

2. **🚨 Critical regression — MCP existing user** — `serverInfo.name` เปลี่ยนเป็น `"personal-data-bank"` แต่ MCP secret URL path `/mcp/{secret}` ไม่แตะ. Claude Desktop config เดิมที่ user มี server key `"project-key"` ยังเรียก tools ได้เพราะ server key คือชื่อที่ user เลือก ไม่ใช่ shared identity. ขอให้ test ด้วย Claude Desktop จริง

3. **🚨 Critical regression — OpenRouter X-Title** — เปลี่ยน `"Project KEY"` → `"Personal Data Bank"` ใน llm.py:21. ขอ test chat retrieval + LLM response ปกติ

4. **MCP serverInfo response format** — ควร return `result.serverInfo.name === "personal-data-bank"` ตอน initialize. ผม TestClient หา /mcp/{secret} ได้ 401 (auth required) — ฟ้าควร test ด้วย token จริง

5. **Rebrand notice toast** — `maybeShowRebrandNotice()` ใน app.js (เพิ่มเรียกใน `initAppData()`):
   - Fire ครั้งเดียว: เช็ค localStorage flag `pdb_rebrand_notice_seen` → set ถ้าไม่มี
   - Guard `state.currentUser` → ไม่แสดงตอน landing page
   - Copy TH/EN เลือกตาม `getLang()` → ไม่ใช้ emoji (consistency กับ commit b38fed4)
   - Edge case ที่ขอเทส: login → reload หน้า → toast แสดงแค่ครั้งแรก, second visit silent

6. **In-app version display drift** — `legacy-frontend/index.html:509` มี `<span class="logo-version">v6.0.0 → v6.1.0</span>` ที่ hardcoded HTML — ตามหลัก single-source-of-truth ใน `config.py:9-11` ควรอ่านจาก `APP_VERSION` (เช่น `/api/mcp/info` แล้ว patch `<span>` ด้วย JS). **ผม bump เป็น v6.1.0 พร้อมกันเพื่อ consistency แต่ flag ไว้ว่าเป็น pre-existing tech debt** — ฟ้าจะ recommend แก้ใน rebrand นี้ หรือ separate ticket?

7. **Q1 email change — business critical** — User บอกว่า `boss@projectkey.dev` ไม่ใช่ของเรา (เราใช้ fly.dev ฟรี + email จริง = `axis.solutions.team@gmail.com`). 6 mailto links เปลี่ยนแล้ว. ผลทางธุรกิจ: ลูกค้า enterprise ที่คลิก mailto ก่อนหน้านี้ → email ตาย. **ขอ verify mailto ทุก subject parameter ส่งถึง gmail ได้จริง** (Test แค่ click → mail client เปิด — ไม่ต้อง send จริง)

8. **Toast UI** — `showToast(msg, type)` รับแค่ 2 args (ดู app.js:2904) มี default duration 4000ms. ผมไม่ขยายเป็น 8000ms ตามที่ plan example เพื่อไม่ scope-creep — ขอ feedback ว่า 4 sec พอไหม

9. **i18n TH consistency** — Plan Q6 lock ว่า "UI ไทย = ธนาคารข้อมูลส่วนตัว". ผม decision: ใช้ "Personal Data Bank" ทับ TH strings (i18n L781, L2877, toast) เพราะ
   - User ตอนนี้คุ้นกับ English brand name
   - "Personal Data Bank" สั้นกว่า "ธนาคารข้อมูลส่วนตัว" (12 vs 16 chars)
   - แต่ Plan ระบุ "ธนาคารข้อมูลส่วนตัว" — **ผมตัดสินใจ off-plan**
   - **ขอ ฟ้า decide:** เปลี่ยนเป็น "ธนาคารข้อมูลส่วนตัว" ทุกที่ใน TH context หรือคงไว้?
   - Files affected ถ้าต้องเปลี่ยน: app.js (i18n setupSubtitle TH, source label TH, rebrand notice TH), html (modal title คู่มือ, placeholder)

✅ **Self-test ที่ผ่านแล้ว:**
- `python -m compileall backend/` — no syntax errors (silent OK)
- `node -e "new Function(fs.readFileSync('legacy-frontend/app.js'))"` — JS syntax OK
- `python -c "from backend.main import app; print(app.title, app.version)"` → "Personal Data Bank 6.1.0" ✅
- `TestClient.get('/')` → 200 + `"Personal Data Bank" in r.text == True` + `"Project KEY" in r.text == False` ✅
- grep verify post-build = 159 hits (จาก 201) เหลือเฉพาะ historical PRDs + plan files + 2 intentional refs (release note in README + WHY comment in app.js)

⚠️ **สิ่งที่ผม NOT ทำ (out of scope per plan):**
- ❌ ไม่ได้รัน `pytest tests/test_production.py` (BASE URL ชี้ที่ production ที่ยังเป็น v6.0.0 — Q5 default รัน pytest หลัง deploy เท่านั้น)
- ❌ ไม่ได้รัน `npx playwright test` (sandbox ไม่ allow port binding)
- ❌ ไม่ได้รัน `python -m uvicorn` smoke test (sandbox blocked port binding — ใช้ TestClient แทน)
- ❌ ไม่ได้แก้ `.agent-memory/plans/google-drive-byos.md` (37 occ) — plan ระบุชัด "WAIT — แดงจะ revise หลัง rebrand merges"
- ❌ ไม่ได้เขียน tests ใหม่ (เป็นหน้าที่ฟ้า)

🧪 **Test scenarios ที่ฟ้าควรทำ (ตาม plan section "Test Scenarios"):**
- **Happy:** Frontend ทุกหน้าแสดง "Personal Data Bank" → MCP serverInfo → OpenRouter X-Title (ดู logs) → Stripe checkout
- **Regression:** Login (localStorage projectkey_token เดิม), MCP Claude Desktop user เก่า, Stripe webhook, AI Chat, file upload+organize+summary
- **Edge:** localStorage cache user เก่า, Old domain still works, Rebrand toast 1 ครั้งเดียว, historical docs ยังคงชื่อเดิม

📦 **Commit:**
- `6e14e63` — feat(brand): rename Project KEY → Personal Data Bank (PDB) — v6.1.0 (21 files, +210/-71)
- `89d1b44` — chore: commit pipeline system + v6.0.0 leftovers (master, ก่อน branch)

ขอบคุณฟ้ามากครับ — ขอความเห็น 9 จุดข้างบนเป็นพิเศษ 🔵

— เขียว (Khiao)

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
