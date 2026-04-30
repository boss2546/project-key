# Plan: Rebrand "Project KEY" → "Personal Data Bank" (PDB)

**Author:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** approved (user confirmed defaults 2026-04-30)
**Estimated effort:** เขียว 1 วัน + ฟ้า 2-3 ชม.
**Target version:** v6.1.0

---

## 🎯 Goal

ปรับ branding ของโปรเจกต์จาก **"Project KEY"** เป็น **"Personal Data Bank" (PDB)** ทุกที่ที่ user มองเห็นและ developer แตะต้อง โดย **คงโครงสร้าง infrastructure ไว้ทั้งหมด** เพื่อไม่ให้กระทบลูกค้าเก่าหรือต้อง migrate ข้อมูล

**ทำเสร็จแล้วได้อะไร:**
1. ทุกหน้าเว็บแสดง "Personal Data Bank" (TH: "ธนาคารข้อมูลส่วนตัว")
2. MCP server ตอบ user ว่าชื่อ "personal-data-bank"
3. README + docs สะท้อน brand ใหม่
4. Test suite ตรวจ brand ใหม่ — pass 100%
5. **Code base พร้อม**สำหรับ feature BYOS ที่จะตามมา (ไม่ต้องแก้ branding 2 รอบ)

---

## ✅ Resolved Decisions (defaults from แดง — user accepted 2026-04-30)

| # | Decision | Locked value |
|---|---|---|
| Q1 | Branding strategy | Display **"Personal Data Bank"** + Code/short **"PDB"** |
| Q2 | Domain | **Keep** `project-key.fly.dev` (Fly.io app rename = สูง risk; ใช้ custom domain ภายหลัง) |
| Q3 | DB filename | **Keep** `projectkey.db` (ไม่กระทบ user, ลด migration risk) |
| Q4 | MCP server name | **Change** `serverInfo.name = "personal-data-bank"` + ส่ง notice ลูกค้าเก่า |
| Q5 | Repo name | **Keep** `github.com/boss2546/project-key` (ภายหลังเปลี่ยนได้) |
| Q6 | ภาษาไทย | UI = **"ธนาคารข้อมูลส่วนตัว"**, Code = "Personal Data Bank" |
| Q7 | Logo | **Keep** logo เดิม (icon 4 สี่เหลี่ยม) |

---

## 📚 Context

### ทำไม "Personal Data Bank"?
- ตรงกับ tagline ที่มีอยู่ใน [mcp_tools.py:1093](../../backend/mcp_tools.py#L1093) แล้ว: `"Project KEY v4.1 — Personal Data Bank"`
- ตรงกับ working directory: `d:\PDB\` (already named PDB!)
- สื่อความหมายชัด: "ธนาคารข้อมูลส่วนตัว" — user ฝากข้อมูล + AI ช่วยจัดการ
- ตรงกับ vision: **user-sovereign data** (สำคัญสำหรับ BYOS feature ที่จะตามมา)

### ทำไม keep domain `project-key.fly.dev`?
- Fly.io app name **ผูกกับ subdomain** บน fly.dev → rename app = ต้องสร้าง app ใหม่ + migrate volume + DNS — ยุ่งและ risky
- ลูกค้าที่ bookmark ไว้แล้วจะใช้ต่อได้
- **ทางออกอนาคต:** ซื้อ custom domain (เช่น `personaldatabank.com`) → point ไปที่ Fly.io app เดิม → ได้ branding URL ใหม่โดยไม่ต้องย้าย infrastructure

### Special: existing MCP users
- Claude Desktop config ของ user เก่ามี `"project-key"` เป็น server key (ใน mcpServers section)
- **Server key ใน config = user เลือกเอง** — เราไม่ได้ฝืน
- ที่เปลี่ยนคือ `serverInfo.name` (ที่ Claude UI แสดง) → user เห็นชื่อใหม่ใน Claude แต่ config ไม่ต้องแก้
- เพิ่ม in-app notice: "Brand updated to Personal Data Bank — your Claude Desktop config still works"

---

## 📐 Strategy: 5 Patterns to Transform

```
┌────────────────────────────────────────────────────────┐
│  Pattern              │  Action                          │
├────────────────────────────────────────────────────────┤
│  "Project KEY"        │  → "Personal Data Bank"          │
│                       │     (display, marketing, headings)│
├────────────────────────────────────────────────────────┤
│  "project-key"        │  → "personal-data-bank"          │
│                       │     EXCEPT: domain, fly.toml,    │
│                       │     URLs to project-key.fly.dev   │
├────────────────────────────────────────────────────────┤
│  "project_key"        │  → "personal_data_bank"          │
│                       │     EXCEPT: fly volume name      │
├────────────────────────────────────────────────────────┤
│  "projectkey"         │  KEEP (DB filename only)         │
├────────────────────────────────────────────────────────┤
│  "PROJECT_KEY"        │  N/A (no current usage)          │
└────────────────────────────────────────────────────────┘
```

### Domain Strategy
```
✅ project-key.fly.dev — KEEP (Fly.io constraint)
   - In code: refer to as "production URL"
   - Branding around it: "Personal Data Bank, hosted at project-key.fly.dev"
   - Future: get custom domain → swap when ready
```

---

## 🛡️ Out-of-Scope (ห้ามเปลี่ยน)

```
❌ fly.toml: app = "project-key"          ← Fly.io app rename = create new app
❌ fly.toml: source = "project_key_data"  ← Volume name tied to app
❌ projectkey.db                          ← Internal, no user impact
❌ /app/data/backups/projectkey_*.db      ← Auto-generated paths
❌ MCP secret URL path /mcp/{secret}      ← User config compatibility
❌ Git remote URL                          ← Defer to later
❌ User-generated content (summaries, etc.) ← Never touch user data
❌ Historical PRDs in docs/prd/*.md       ← Dated artifacts, preserve as history
❌ Personality/BYOS plan files            ← Will fix after this rebrand merges
```

---

## 📁 Files to Modify (Total: 256 occurrences in 50 files)

### 🔥 Tier 1 — User-facing (HIGHEST IMPACT — change first)

| File | Occurrences | What to change |
|---|---|---|
| `legacy-frontend/index.html` | 9 | `<title>`, hero, footer, meta description |
| `legacy-frontend/app.js` | 22 | toast messages, alt text, i18n strings, console.log |
| `legacy-frontend/pricing.html` | 7 | header, descriptions |
| `README.md` | 10 | title, examples, badges |

### 🟡 Tier 2 — Backend (MEDIUM IMPACT)

| File | Line | Current | New |
|---|---|---|---|
| `backend/main.py` | 1 | `"""Project KEY — FastAPI Backend"""` | `"""Personal Data Bank (PDB) — FastAPI Backend"""` |
| `backend/main.py` | 46 | `app = FastAPI(title="Project KEY", ...)` | `app = FastAPI(title="Personal Data Bank", ...)` |
| `backend/main.py` | (search) | `serverInfo.name = "project-key"` (in MCP) | `"personal-data-bank"` |
| `backend/llm.py` | 20 | `"HTTP-Referer": "https://project-key.fly.dev"` | **KEEP** (real URL) |
| `backend/llm.py` | 21 | `"X-Title": "Project KEY"` | `"X-Title": "Personal Data Bank"` |
| `backend/billing.py` | 1 | docstring | rebrand |
| `backend/mcp_tools.py` | 3 | docstring | rebrand |
| `backend/mcp_tools.py` | 263 | example: `'Project KEY v5.4 progress'` | `'Personal Data Bank v5.4 progress'` |
| `backend/mcp_tools.py` | 1093 | `"Project KEY v4.1 — Personal Data Bank"` | `"Personal Data Bank — v4.1 (PDB)"` |
| `backend/config.py` | 2 | comments | rebrand |
| `backend/__init__.py` | 1 | docstring | rebrand |
| `backend/auth.py` | 1 | log message | rebrand |
| `backend/database.py` | 2 | comments / docstring | rebrand |
| `backend/shared_links.py` | 1 | docstring | rebrand |

### 🟢 Tier 3 — Config files

| File | Action |
|---|---|
| `package.json` | `"name": "project-key"` → `"personal-data-bank"`, `"description"` rebrand |
| `playwright.config.js` | comments/test names rebrand |
| `.env.example` | comments rebrand (if any) |
| `.gitignore` | comments rebrand (if any) |
| `.dockerignore` | comments rebrand (if any) |
| `fly.toml` | **NO CHANGE** (infrastructure) |

### 📋 Tier 4 — Tests

| File | Action |
|---|---|
| `tests/test_production.py` | 4 occurrences — update assertions to match new title/brand |
| `tests/e2e-ui/ui.spec.js` | 28 occurrences — update Playwright assertions |
| `tests/e2e/test_full_e2e.py` | 1 occurrence — update assertion |
| `tests/fixtures/user_research.txt` | 1 occurrence — fixture content (rebrand if it's part of test logic, else keep) |
| `tests/fixtures/tech_architecture.md` | 3 occurrences — same logic |

### 📚 Tier 5 — Docs (selective)

**ACTIVE docs — UPDATE:**
- `README.md` ✅
- `docs/guides/USER_GUIDE_V3.md` ✅ (4 occurrences)
- `DESIGN.md` ✅ (if brand mentioned)

**HISTORICAL docs — KEEP AS-IS** (PRDs are dated artifacts):
- `docs/PROJECT_REPORT.md` (16 occ) — reflects history
- `docs/EXPERT_TECHNICAL_REPORT.md` (13 occ) — technical history
- `docs/v5.8_implementation_report.md` (2 occ) — version snapshot
- `docs/prd/Project_KEY_PRD_*.md` (any version) — PRD history

> **กฎ:** ถ้าไฟล์มี `_v\d` หรืออยู่ใน `docs/prd/` → KEEP. ถ้าเป็น living doc → UPDATE.

### 🤖 Tier 6 — Agent memory (selective)

**UPDATE:**
- `.agent-memory/00-START-HERE.md`
- `.agent-memory/project/overview.md` ⭐ (2 occ — primary project description)
- `.agent-memory/project/tech-stack.md`
- `.agent-memory/project/architecture.md`
- `.agent-memory/contracts/api-spec.md`
- `.agent-memory/contracts/data-models.md`
- `.agent-memory/current/pipeline-state.md`
- `.agent-memory/current/last-session.md`
- `.agent-memory/prompts/prompt-แดง.md`
- `.agent-memory/prompts/prompt-เขียว.md`
- `.agent-memory/prompts/prompt-ฟ้า.md`

**WAIT (will update after this plan merges):**
- `.agent-memory/plans/personality-profile.md` (4 occ — already done feature, ok to update)
- `.agent-memory/plans/google-drive-byos.md` (37 occ — pending feature; แดงจะ revise plan หลัง rebrand เสร็จ)
- `.agent-memory/plans/rebrand-pdb.md` (this file — meta-references OK)

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Pre-flight (~15 min)
1. `git checkout -b rebrand-pdb-v6.1.0`
2. Run baseline tests: `pytest tests/test_production.py -v` — record pass count
3. Take screenshot ของหน้าหลัก (สำหรับ before-after compare)
4. `grep -rIn "Project KEY" --exclude-dir={.git,node_modules,__pycache__,backups,uploads}` — save output to `/tmp/before.txt` (จะ verify ตอน done)

### Step 2: Tier 2 Backend (~30 min)
แก้ตามตาราง Tier 2 ข้างบน บรรทัดต่อบรรทัด

```bash
# Verify backend still starts
python -m uvicorn backend.main:app --port 8001 &
sleep 3
curl -s http://localhost:8001/api/mcp/info | grep -i "personal data bank"
kill %1
```

**สำคัญ:** ดู `serverInfo.name` ใน MCP — แก้จาก `"project-key"` → `"personal-data-bank"` (ใน `_build_mcp_tools_list` หรือ initialize handler)

### Step 3: Tier 1 Frontend (~45 min)
1. `legacy-frontend/index.html` — แก้ทุกที่ที่ user เห็น:
   - `<title>Project KEY — Knowledge Workspace</title>` → `<title>Personal Data Bank — Knowledge Workspace</title>`
   - `<meta name="description">` → rebrand
   - Hero header
   - Footer
   - Logo text "Project KEY" → "Personal Data Bank"
2. `legacy-frontend/pricing.html` — header, breadcrumb
3. `legacy-frontend/app.js` (22 ที่ — ต้องอ่าน context ก่อน):
   - **i18n strings** ภาษาไทย: เปลี่ยนเป็น "ธนาคารข้อมูลส่วนตัว"
   - **i18n strings** ภาษาอังกฤษ: เปลี่ยนเป็น "Personal Data Bank"
   - Toast messages
   - Console.log (low priority)
   - localStorage keys: `projectkey_token`, `projectkey_user` → ⚠️ **KEEP** (จะ break login ของ user เดิม)

> ⚠️ **Critical:** อย่าแตะ `localStorage.getItem('projectkey_token')` หรือ `projectkey_user` — keys นี้ user เก่ามีค่าอยู่แล้ว เปลี่ยน = logout ทุกคน

4. ตรวจ visual: เปิด browser → reload → ทุกหน้าต้องแสดง "Personal Data Bank"

### Step 4: Tier 3 Config (~10 min)
```json
// package.json
{
  "name": "personal-data-bank",
  "description": "Personal Data Bank — AI-powered personal knowledge workspace + MCP connector"
}
```

`playwright.config.js`: รีบ-rebrand comments แต่ test selectors อาจต้องปรับใน Step 5

### Step 5: Tier 4 Tests (~20 min)
1. `tests/test_production.py:69`: เปลี่ยน `assert "Project KEY" in r.text` → `assert "Personal Data Bank" in r.text`
2. `tests/test_production.py:75`: เหมือนกัน
3. `tests/e2e-ui/ui.spec.js`: 28 ที่ — ดู context ทีละ assertion
4. `tests/e2e/test_full_e2e.py`: 1 ที่ — assertion update
5. Run: `pytest tests/test_production.py -v` + `npx playwright test --reporter=list`
6. ทุก test ต้อง pass

### Step 6: Tier 5 Active Docs (~15 min)
1. `README.md` — แก้ title, badges, examples (10 ที่)
2. `docs/guides/USER_GUIDE_V3.md` — 4 ที่
3. `DESIGN.md` (ถ้ามี brand) — keep design philosophy unchanged
4. **อย่าแตะ** `docs/prd/*.md` หรือ `docs/PROJECT_REPORT.md` — historical

### Step 7: Tier 6 Agent Memory (~15 min)
อัปเดต living docs:
- `00-START-HERE.md`
- `project/overview.md` ⭐ (สำคัญ — เป็นเอกสาร context หลักของทุก agent)
- `project/tech-stack.md`
- `project/architecture.md`
- `contracts/*.md`
- `current/*.md`
- `prompts/*.md`

### Step 8: Add in-app notice (~10 min)
ใน `legacy-frontend/app.js` — เพิ่ม banner แสดงครั้งแรกหลัง deploy:

```javascript
// Show once via localStorage flag
const REBRAND_NOTICE_KEY = 'pdb_rebrand_notice_seen';
if (!localStorage.getItem(REBRAND_NOTICE_KEY) && state.currentUser) {
  showToast(getLang() === 'th'
    ? '🎉 เราเปลี่ยนชื่อเป็น "Personal Data Bank" — ฟีเจอร์เดิมไม่กระทบ'
    : '🎉 We rebranded to "Personal Data Bank" — all features unchanged',
    'info', 8000);
  localStorage.setItem(REBRAND_NOTICE_KEY, '1');
}
```

### Step 9: Verify (~15 min)
```bash
# 1. ที่ควร "ไม่เจอ" (เหลือแต่ historical docs)
grep -rIn "Project KEY" \
  --exclude-dir={.git,node_modules,__pycache__,backups,uploads,docs/prd} \
  --exclude="docs/PROJECT_REPORT.md" \
  --exclude="docs/EXPERT_TECHNICAL_REPORT.md" \
  --exclude="docs/v5.8_implementation_report.md" \
  --exclude="rebrand-pdb.md"
# Expected output: 0 lines (or only acceptable references)

# 2. ที่ "ควรเจอ" (infrastructure exceptions)
grep -rIn "project-key" --exclude-dir={.git,node_modules,__pycache__}
# Expected: fly.toml + URL references in llm.py + docs about hosting

# 3. Test suite
pytest tests/test_production.py -v
npx playwright test --reporter=list

# 4. Manual browser check
python -m uvicorn backend.main:app --port 8001
# Open http://localhost:8001 → ทุกหน้าควรแสดง "Personal Data Bank"
```

### Step 10: Commit + Deploy (~10 min)

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(brand): rename Project KEY → Personal Data Bank (PDB) — v6.1.0

Comprehensive rebrand across UI, API, MCP, and active docs.

Changed (256 occurrences in 50 files):
- Display name: "Project KEY" → "Personal Data Bank"
- Thai brand: → "ธนาคารข้อมูลส่วนตัว"
- FastAPI title, X-Title (OpenRouter), MCP serverInfo.name
- Frontend (index, app.js, pricing) + i18n (TH+EN)
- README + active docs + agent memory
- package.json name + description
- Test assertions

Kept stable (infrastructure / data integrity):
- Fly.io app name "project-key" (rename = high risk)
- Domain "project-key.fly.dev" (tied to Fly.io app)
- DB file "projectkey.db" (internal, no user impact)
- MCP secret URL path /mcp/{secret} (existing user configs)
- localStorage keys (projectkey_token, projectkey_user)
- Historical PRDs in docs/prd/* (dated artifacts)

Added: in-app rebrand notice (one-time toast on first visit)

Refs: plans/rebrand-pdb.md
Author-Agent: เขียว (Khiao)
EOF
)"

git push origin rebrand-pdb-v6.1.0
# → Open PR → review → merge → fly deploy
```

หลัง deploy production:
```bash
# Smoke test
curl -s https://project-key.fly.dev/api/mcp/info | jq '.version'   # → "v6.1.0"
curl -s https://project-key.fly.dev/ | grep -o "Personal Data Bank"  # → matches
```

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. **Frontend:** เปิด `https://project-key.fly.dev/` → ทุกหน้า (landing, my-data, knowledge, chat, profile, mcp, guide, pricing) แสดง "Personal Data Bank" ใน header/title/footer
2. **Backend health:** `GET /api/mcp/info` → `version: "v6.1.0"`
3. **MCP serverInfo:** เรียก `POST /mcp/{secret}` method `initialize` → `result.serverInfo.name === "personal-data-bank"`
4. **OpenRouter integration:** chat → ตรวจ HTTP request ที่ส่งไป OpenRouter → `X-Title: Personal Data Bank`
5. **Stripe:** ลองสร้าง checkout session → ตรวจ Stripe Customer description (ถ้ามี string)

### Regression
6. **Login:** user เก่า login ได้ไหม (test ว่า localStorage `projectkey_token` ยัง work)
7. **MCP existing user:** Claude Desktop ที่ตั้ง config ไว้แล้ว — ยังเรียก tool ได้
8. **Stripe webhook:** event มาแล้ว process ได้ปกติ
9. **AI Chat:** chat retrieval + LLM call ทำงานได้ปกติ
10. **File upload + organize + summary:** end-to-end flow ทำงาน

### Edge Cases
11. **localStorage cache:** user เก่าที่มี `projectkey_user` ใน localStorage — UI โหลดได้ปกติ
12. **Old domain:** `https://project-key.fly.dev/` ยังเปิดได้ (ต้องเปิดได้ — เพราะ Fly.io domain คงเดิม)
13. **Rebrand notice:** แสดง toast 1 ครั้งหลัง login → reload หน้า → ไม่แสดงซ้ำ
14. **Historical docs:** `docs/prd/Project_KEY_PRD_v4.md` — ยังคงชื่อเดิม (intentional)
15. **Test fixtures:** `tests/fixtures/user_research.txt` — ดู context ก่อนแก้ (อาจเป็น part ของ test data ที่ต้องคงเดิม)

### Search Validation
- `grep -rIn "Project KEY" backend/ legacy-frontend/ tests/` → 0 hits
- `grep -rIn "project-key" backend/ legacy-frontend/` → only infrastructure references
- `grep -rIn "Personal Data Bank" backend/ legacy-frontend/` → many hits (positive signal)

---

## ✅ Done Criteria

- [ ] User-facing pages ทุกหน้าแสดง "Personal Data Bank" / "ธนาคารข้อมูลส่วนตัว" (TH)
- [ ] FastAPI title = "Personal Data Bank"
- [ ] MCP `serverInfo.name = "personal-data-bank"`
- [ ] OpenRouter X-Title = "Personal Data Bank"
- [ ] README + active docs updated
- [ ] Agent memory updated (overview.md, prompts/, contracts/)
- [ ] All tests pass (pytest + playwright)
- [ ] In-app rebrand notice ทำงาน (แสดงครั้งเดียว)
- [ ] Login + MCP + Stripe + Chat — regression OK
- [ ] Production deploy → smoke test pass
- [ ] Bump version → v6.1.0 in `config.py:APP_VERSION`
- [ ] Commit message + Author-Agent ครบ

---

## ⚠️ Risks / Known Issues

### Risk 1: Test fixtures ที่อาจ break
- `tests/fixtures/tech_architecture.md` (3 occ) — ถ้าเป็น content ที่ test logic ใช้ค้นหาคำว่า "Project KEY" → ต้องอัปเดตทั้ง fixture และ test
- **Mitigation:** อ่าน test ที่ใช้ fixture นี้ก่อน decide

### Risk 2: ลูกค้าเก่ามี Claude Desktop config "project-key"
- Server key ที่ user ตั้งใน config (`mcpServers.project-key`) — เราไม่บังคับ
- ที่เปลี่ยน = `serverInfo.name` ที่ Claude UI แสดง
- **Mitigation:** in-app notice แจ้งให้ทราบ + อาจ update Claude Desktop config ใน MCP setup page

### Risk 3: SEO / external links
- Backlinks ภายนอกใช้ "Project KEY" → ใน content meta description ใส่ทั้ง 2 ชื่อช่วงเปลี่ยนผ่าน
- **Mitigation (optional):** meta description = "Personal Data Bank (formerly Project KEY) — AI-powered..."

### Risk 4: localStorage keys break
- ถ้าเขียวพลาดเปลี่ยน `projectkey_token` → user เก่า logout หมด → trust crisis
- **Mitigation:** plan ระบุชัดเจนว่า KEEP, เพิ่ม regression test

### Risk 5: PRD docs version mention
- `docs/prd/PRD_v5.5_Context_Memory.md` etc. — ใช้ "Project KEY" → ส่วนหนึ่งของ history
- **Mitigation:** keep historical, only update README + active guides

### Risk 6: Trademark check
- "Personal Data Bank" — ไม่ใช่ trademark ที่ Google/Apple/etc. เป็นเจ้าของ
- ใน Thailand: "ธนาคารข้อมูลส่วนตัว" — common term, ไม่น่ามี TM issue
- **Mitigation:** quick check ที่ Thailand TM database (DIP) ก่อน launch สาธารณะ — defer ทำตอน OAuth verification

---

## 📌 Notes for เขียว

### กฎที่ห้ามลืม
1. **อย่าแตะ `fly.toml`** — Fly.io app name + volume name ตายตัว
2. **อย่าแตะ `projectkey.db`** filename — internal, ลด migration risk
3. **อย่าแตะ localStorage keys** `projectkey_token`, `projectkey_user` — break login
4. **อย่าแตะ historical PRDs** `docs/prd/*.md` + `docs/PROJECT_REPORT.md` + `docs/EXPERT_TECHNICAL_REPORT.md` — dated artifacts
5. **อย่าแตะ user-generated content** ใน DB (summaries, chat history) — never modify user data
6. **`Author-Agent: เขียว (Khiao)`** ในทุก commit
7. **ห้าม commit** `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`

### Search-replace tactics
**ห้าม mass replace ทันที!** ใช้ approach นี้:

```bash
# Step 1: ดู context ทั้งหมดก่อน
grep -rIn "Project KEY" \
  --exclude-dir={.git,node_modules,__pycache__,backups,uploads} \
  | tee /tmp/all_occurrences.txt

# Step 2: แยกเป็น categories
# - User-facing display strings (UI labels) → CHANGE
# - URL references (project-key.fly.dev) → KEEP
# - DB filenames (projectkey.db) → KEEP
# - Historical doc references → KEEP
# - localStorage keys → KEEP

# Step 3: แก้ทีละ category ด้วยมือหรือ sed targeted
sed -i 's/title="Project KEY"/title="Personal Data Bank"/' backend/main.py
sed -i 's/"X-Title": "Project KEY"/"X-Title": "Personal Data Bank"/' backend/llm.py
# ฯลฯ ทีละจุด — ปลอดภัยกว่า global sed
```

### Order of files matters!
1. **Backend ก่อน** (main.py, llm.py, mcp_tools.py) — server เริ่มได้ → smoke test
2. **Frontend** (index.html, app.js, pricing.html) — visual ตรวจ browser
3. **Config** (package.json) — quick
4. **Tests** — เพราะถ้า frontend เปลี่ยนแล้ว test เก่าจะ fail → update assertions พร้อมกัน
5. **Active docs** (README, USER_GUIDE)
6. **Memory** (00-START-HERE, overview, prompts)
7. **Notice in app**

### Specific i18n keys ที่ต้องเปลี่ยน
ใน `legacy-frontend/app.js` มี LANG dictionary — ต้องค้น keys ที่มี brand:
```javascript
// ตัวอย่างที่ต้องเปลี่ยน:
'app.name': 'Project KEY' → 'Personal Data Bank' (en) / 'ธนาคารข้อมูลส่วนตัว' (th)
'app.tagline': '...' → rebrand
'landing.hero.title': '...' → rebrand
// ฯลฯ — ต้อง search ทุก key ที่มี "Project KEY"
```

### Pre-commit checklist (เขียวต้องตรวจก่อน push)
- [ ] Server start ได้ (uvicorn)
- [ ] หน้า landing โหลดได้, แสดง "Personal Data Bank"
- [ ] หน้า my-data, profile, MCP setup, pricing โหลดได้
- [ ] Login flow ทำงาน (account เก่ายัง login ได้)
- [ ] `pytest tests/test_production.py -v` pass
- [ ] `npx playwright test --reporter=list` pass
- [ ] `grep -rIn "Project KEY" backend/ legacy-frontend/` → 0 hits (excluding docstrings ที่เปลี่ยนแล้ว)
- [ ] No `.env` / secrets committed
- [ ] Memory updated

### Time budget
- Pre-flight: 15 min
- Backend: 30 min
- Frontend: 45 min
- Config: 10 min
- Tests: 20 min
- Docs: 15 min
- Memory: 15 min
- Notice: 10 min
- Verify: 15 min
- Commit + Deploy: 10 min
- **Total: ~3 ชม.** (1/3 วันทำงาน)

### Commit strategy
1 commit ก็พอ (ไม่ต้องแยก) เพราะเป็นการเปลี่ยนเดียวกัน — branding refresh

### หลัง deploy
1. Smoke test production (curl + browser)
2. ส่ง message ใน `inbox/for-User.md` แจ้ง deploy เสร็จ + version v6.1.0
3. Update pipeline-state → state = `done`
4. **อย่าลืม:** ส่งต่อให้ฟ้า review ก่อน — ผ่าน `inbox/for-ฟ้า.md` (ดู workflow ปกติ)

---

## 🔄 Pipeline Workflow

```
Plan approved ✅
    ↓
เขียว build (1 วัน หรือเร็วกว่า) — state: building
    ↓
เขียวเสร็จ → state: built_pending_review → ส่ง MSG ถึงฟ้า
    ↓
ฟ้า review + run tests (2-3 ชม.) — state: reviewing
    ↓
ฟ้า approve → state: review_passed → แจ้ง user
    ↓
User merge + deploy → state: done
    ↓
แดงเริ่ม revise plan google-drive-byos.md ให้ใช้ "Personal Data Bank"
    (ไม่เร่ง — แดงทำได้ทันที่ user พร้อมเริ่ม BYOS)
```
