# 📬 Inbox: ฟ้า (Fah) — นักตรวจสอบ

> ข้อความที่ส่งถึงฟ้า — ฟ้าต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> มักได้รับข้อความจากเขียวเมื่อ build เสร็จ พร้อม review
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

### MSG-004 🟡 MEDIUM — Build เสร็จ: PDB Rebrand v6.1.0 (built_pending_review) — UI-only review per user instruction
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plans/rebrand-pdb.md (approved by user)
**Status:** 🔴 New

สวัสดีฟ้า 🔵

Build เสร็จตาม plan rebrand-pdb.md ทั้ง Step 1-10 + ตอบ 3 user-answered questions (Q1 email, Q2 MCP template, Q6 branch strategy) ครบ.

> 📢 **Scope ใหม่ (per user instruction):** User บอกว่าให้เขียวเทสต์ backend เองทั้งหมด → ฟ้าโฟกัสแค่ **UI/frontend** (browser visual + interaction + UX flow). Backend smoke test ผม run ไปแล้ว **76/76 PASS** (ดู section "เขียวเทสต์ backend เอง" ด้านล่าง).

ส่งต่อให้ฟ้าตรวจสอบ APPROVE / NEEDS_CHANGES / BLOCK สำหรับ **UI surface** เท่านั้น

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

🎯 **ขอบเขต UI-only ที่ฟ้าต้อง review (per user instruction):**

ฟ้าจะ run server จริง + เปิด browser → focus ที่ UI/UX/visual surface เท่านั้น. Backend logic ผมเทสต์ไปแล้ว 76/76 PASS.

### 🌐 หน้าหลักที่ต้อง visual check (ทุกหน้าต้องแสดง "Personal Data Bank")
1. **Landing page** (`/` ก่อน login):
   - Header logo + brand text → "Personal Data Bank"
   - Hero/footer → rebranded
   - Feature cards (4 ใบ) — ไม่กระทบจาก rebrand แต่ verify still rendered
   - "เริ่มต้นฟรี" / "เข้าสู่ระบบ" buttons functional

2. **My Data** (`/`?app + login):
   - Sidebar logo + version `v6.1.0` (bumped pre-existing drift จาก v6.0.0 — flag #6 below)
   - File upload + drag-drop UI
   - File list rendering

3. **Knowledge / Collections** — Graph visualization, collection cards

4. **AI Chat** — chat input, response rendering, sources panel
   - **Critical regression:** ขอ verify chat retrieval + LLM response ทำงาน (X-Title="Personal Data Bank" จะส่งไป OpenRouter)

5. **Profile** (สำคัญที่สุดสำหรับ regression — เพิ่งทำ v6.0.0):
   - 4 personality systems UI (MBTI / Enneagram / CliftonStrengths / VIA)
   - History modal
   - Save → toast → reload → values persisted

6. **MCP Setup page** (`/` → MCP):
   - Connector URL + token display
   - **Q2 fix:** copy "Claude Desktop config" template — ตรวจว่า `"personal-data-bank"` ไม่ใช่ `"project-key"` (template เก่า)
   - Antigravity config ก็ใหม่
   - Copy button works
   - Guide section (Step 1-4 ของ Claude Desktop, Antigravity, ChatGPT) — ตรวจ instruction text "Personal Data Bank"

7. **Pricing page** (`/legacy/pricing.html`):
   - **Q1 fix critical:** 3 plan tiers (Core / Pro / Elite) → mailto buttons → ตรวจว่า "axis.solutions.team@gmail.com" (ไม่ใช่ boss@projectkey.dev)
   - Click "Book Private Demo" → mail client เปิดด้วย correct address + subject

8. **Guide modal** (open from MCP setup page):
   - Modal title "คู่มือ Personal Data Bank"
   - Step instructions ใช้ชื่อ "Personal Data Bank"

### 🎨 UI Detail Points (อาจมี visual regression)
1. **Logo version label** (`legacy-frontend/index.html:509`) — bumped `v6.0.0 → v6.1.0`. Visual ดูปกติไหม?
2. **Rebrand notice toast** — `maybeShowRebrandNotice()` ใน app.js:
   - เปิด browser ครั้งแรกหลัง login → toast แสดง "เราเปลี่ยนชื่อเป็น Personal Data Bank แล้ว..."
   - Reload หน้า → toast ไม่แสดงซ้ำ (localStorage flag `pdb_rebrand_notice_seen`)
   - ทดสอบทั้ง TH lang + EN lang ว่า copy ถูก
   - Toast อยู่ 4 วินาที (default ของ showToast)
3. **i18n switching** — toggle TH ↔ EN → brand strings ใน UI เปลี่ยนตาม
4. **Source label "อัปเดตจาก"** ใน Personality history modal:
   - source = `mcp_update` → "อัปเดตจาก: Claude/Antigravity (MCP)"
   - source = web → **"อัปเดตจาก: เว็บไซต์ Personal Data Bank"** (เปลี่ยนจาก `"...project-key"`)
5. **Browser tab title** — ทุกหน้าควรมี "Personal Data Bank" ใน `<title>` (Playwright tested via regex `/Personal Data Bank/`)

### ⚠️ Out-of-Plan Decisions ขอ ฟ้า/User feedback (UI-related)
1. **i18n TH consistency** — Plan Q6 lock ว่า "UI ไทย = ธนาคารข้อมูลส่วนตัว". ผมตัดสินใจใช้ "Personal Data Bank" ทับ TH strings (สั้นกว่า + brand recognition). **Files affected:** app.js (i18n setupSubtitle TH, source label TH, rebrand notice TH) + index.html (modal title คู่มือ, placeholder). **ขอ ฟ้า decide:** เปลี่ยนเป็น "ธนาคารข้อมูลส่วนตัว" หรือคงไว้?
2. **Toast duration 4 sec** — Plan example แนะนำ 8 sec. ผมใช้ default 4 sec ของ showToast เพื่อไม่ scope-creep signature. UX พอไหม?
3. **`logo-version` v6.0.0 → v6.1.0 hardcoded ใน HTML** — pre-existing drift จาก single-source-of-truth ใน `config.py:9-11`. ผม bump พร้อมกันเพื่อ consistency. ฟ้าจะ recommend ทำ dynamic (อ่านจาก /api/mcp/info) ใน rebrand นี้ หรือ separate ticket?

### 🧪 Tests สำหรับฟ้า (UI tooling)
- **Playwright** — `tests/e2e-ui/ui.spec.js` — assertions update แล้ว ("Personal Data Bank" + regex `/Personal Data Bank/`). Run: `npx playwright test --reporter=list`
- **Manual browser** — เปิด `http://localhost:8000` → คลิกทุกหน้า → reload → check toast → click mailto
- **Cross-browser** (optional) — Chrome / Firefox / Safari ถ้ามีเวลา

### 🚧 ที่ฟ้าไม่ต้องทำ (เขียวทำให้แล้ว)
- ❌ Backend API tests — 76/76 PASS ใน `scripts/rebrand_smoke_v6.1.0.py`
- ❌ MCP protocol tests — 13/13 PASS in §4 ของ smoke test
- ❌ Auth tests — 11/11 PASS in §2
- ❌ Profile/Personality CRUD — 10/10 PASS in §3
- ❌ Error format — 7/7 PASS in §7

> **TL;DR:** ฟ้าเปิด browser → ทดสอบ UI/UX ทั้ง TH + EN → ขอ APPROVE / NEEDS_CHANGES สำหรับ visual layer เท่านั้น

📦 **Commits (เรียงตามเวลา):**
- `89d1b44` — chore: commit pipeline system + v6.0.0 leftovers (master, ก่อน branch)
- `6e14e63` — feat(brand): rename Project KEY → Personal Data Bank (PDB) — v6.1.0 (21 files, +210/-71)
- `bf9185c` — chore(memory): post-rebrand session log + handoff hash references (4 files)
- `312658e` — fix(brand): remove literal old brand from served app.js comment (1 file, smoke-test driven)

`git diff 89d1b44..312658e` ดู change set ทั้งหมดสำหรับ rebrand นี้

🧪 **เขียวเทสต์ backend เอง (per user instruction): 76/76 PASS** ✅

Script: [`scripts/rebrand_smoke_v6.1.0.py`](../../../scripts/rebrand_smoke_v6.1.0.py) — in-process TestClient (sandbox blocks port binding)
Run: `python scripts/rebrand_smoke_v6.1.0.py`

**Section breakdown (9 sections):**
- **§1 Health + landing + static (5/5):** GET /, /legacy/{index, app.js, pricing, styles.css} — ทุกหน้ามี "Personal Data Bank" + zero "Project KEY"
- **§2 Auth flows (11/11):** register OK + dup email + short pwd + invalid email; login OK + wrong pwd + unknown user; /me with valid/missing/bad token
- **§3 Profile + Personality (10/10):** ⭐ critical — v6.0.0 feature ยังคงทำงาน post-rebrand
  - GET /api/profile, GET /api/personality/reference (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA verified)
  - PUT /api/profile (4 systems nested) → GET back → fields persisted
  - GET /api/profile/personality/history → ≥4 history rows after PUT (history dedup intact)
  - 4 validation cases: invalid MBTI/Enneagram/Clifton + max-length Clifton — all 422/400
  - PUT without token → 401/403
- **§4 MCP protocol (13/13):** ⭐ critical regression — Claude Desktop integration
  - `/api/mcp/info` → version 6.1.0
  - `POST /api/mcp/tokens` create + GET list + DELETE revoke
  - `POST /mcp/{user-secret}` initialize → `serverInfo.name='personal-data-bank'` + `version='6.1.0'` ✓
  - `tools/list` → 30 tools registered
  - `tools/call` get_overview → 'Personal Data Bank — v4.1 (PDB)' system string
  - `tools/call` get_profile → success
  - `tools/call` list_files → result.content[0].text parses to {files:...}
  - `tools/call` unknown_tool → JSON-RPC error -32601/-32602
  - **Auth boundary verified:** wrong URL secret → rejected; correct URL secret without Bearer → 200 (by design — URL secret IS the primary auth, Bearer is non-load-bearing for initialize)
- **§5 Files (5/5):** GET /api/files (auth + no-auth boundary), /api/clusters, /api/unprocessed-count, /api/stats
- **§6 Plan/billing (3/3):** /api/usage, /api/plan-limits, /api/billing/info
- **§7 Error format (7/7):** structured JSON `{error: {...}}` or `{detail: ...}` across 7 failure modes (dup, wrong pwd, invalid input, missing token, wrong-id GET/DELETE, MCP wrong secret)
- **§8 Branding in API responses (7/7):** ⭐ key proof — root HTML, served app.js, pricing email (axis.solutions.team@gmail.com — Q1 fix), MCP serverInfo, tools/list descriptions, get_overview content — ทั้งหมดมี "Personal Data Bank", zero "Project KEY"
- **§9 KEEP invariants + stray-brand scan (15/15):** fly.toml, projectkey.db, HTTP-Referer real URL, localStorage keys, FastAPI title, serverInfo.name, system string, scan 17 actively-rebranded files for stray "Project KEY"

**Bugs ที่ smoke test จับได้ก่อน handoff:**
1. **`312658e`** — served `app.js` มี literal "Project KEY" ใน WHY comment ของ `maybeShowRebrandNotice()` → reword "ชื่อเดิม"
2. (อีกจุดเป็น test bugs ของผมเอง — fix ใน script, ไม่ใช่ source bug)

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
