# Rebrand PDB v6.1.0 — Readiness Notes (Pre-Build Review)

**Author:** เขียว (Khiao)
**Date:** 2026-04-30
**Status:** `paused` — รอ user ตัดสินใจ 6 ข้อ + มีงานอื่นแทรก
**Plan ที่อ้างอิง:** [2026-05-01-rebrand-pdb.md](2026-05-01-rebrand-pdb.md)

> เอกสารนี้คือผลการอ่าน-วิเคราะห์ทุกไฟล์ที่เกี่ยวข้องกับ rebrand **ก่อน** เริ่ม build จริง
> เก็บไว้เพื่อ resume งานต่อได้เลยโดยไม่ต้องอ่านซ้ำ

---

## 🎯 TL;DR เพื่อ Resume งาน

1. อ่าน Plan ฉบับเต็มใน [2026-05-01-rebrand-pdb.md](2026-05-01-rebrand-pdb.md) แล้ว
2. Grep ทุกไฟล์: 343 raw hits ใน 52 files (Plan ระบุ 256/50 — ต่างเพราะ Plan ไม่นับ `.agent-memory/`)
3. หลังตรวจ context ทีละจุด: **มีจุดที่ต้อง CHANGE จริงๆ ~56 จุด** ที่เหลือ ~141 = KEEP (URLs, DB filenames, localStorage keys)
4. **มี 6 จุดที่ Plan ไม่ครอบคลุม** → ต้องการ user confirm ก่อนเริ่ม
5. เมื่อ resume: ตอบ 6 ข้อใน "Decision Points" ด้านล่าง → ลุยตาม Plan Step 1-10 ได้เลย

---

## 📊 Scope Inventory (หลังตรวจ context ทีละจุด)

### Summary table

| Tier | Files | Raw hits | Actual CHANGE | KEEP | Notes |
|---|---|---|---|---|---|
| 1 Frontend | 3 | 38 | ~18 | 20 | localStorage `projectkey_*` (13) + 6 mailto = KEEP |
| 2 Backend | 9 | 15 | ~12 | 3 | URLs + DB filename ref = KEEP |
| 3 Config | 5 | 5 | ~3 | 2 | repository URL + `projectkey.db*` = KEEP |
| 4 Tests | 5 | 33 | ~8 | 25 | localStorage ops + URL = KEEP; fixtures KEEP per plan rule |
| 5 Docs | 2 | 14 | ~11 | 3 | URLs + `projectkey.db` = KEEP |
| 6 Memory | 10 | 17 | ~2 | 15 | ส่วนใหญ่เป็น `projectkey.db` filename ref (KEEP) |
| **ห้ามแตะ** | fly.toml + historical PRDs | 73 | 0 | 73 | per plan |
| **NEW (เพิ่มใหม่)** | app.js + config.py | — | 2 | — | rebrand notice toast + APP_VERSION bump |
| **TOTAL** | 52 | 343 | **~56** | ~141 | + 2 additions |

> **Insight:** Plan บอก 256 occurrences ดูใหญ่ — แต่ ~141 จากนี้คือ KEEP (infrastructure / DB / localStorage). **จริงๆ ที่ต้องแก้คือ ~56 จุด เท่านั้น** ทำไม่ถึง 1 วัน

---

## 📁 รายละเอียดทีละไฟล์ (เพื่อ resume เร็ว)

### Tier 1 — Frontend (3 files)

#### [legacy-frontend/index.html](../../legacy-frontend/index.html) (9 hits / 6 CHANGE)
- **L6** `<title>Project KEY — Knowledge Workspace</title>` → CHANGE
- **L31** `<span>Project KEY</span>` (header logo text) → CHANGE
- **L508** `<span class="logo-text">Project KEY</span>` → CHANGE
- **L1045** placeholder `เช่น Project KEY v5.5 progress` → CHANGE
- **L1098** `Connect your Project KEY data to Claude via remote MCP` → CHANGE
- **L1620** `คู่มือ Project KEY` (guide modal title) → CHANGE
- **L1551, L1566, L1580** `mailto:boss@projectkey.dev` → ❓ **Q1 — KEEP per default**

#### [legacy-frontend/app.js](../../legacy-frontend/app.js) (22 hits / 9 CHANGE)
- **L2** docstring `Project KEY v5.1 — Frontend Logic` → CHANGE
- **L781** i18n TH `'เชื่อมต่อข้อมูล Project KEY ของคุณ...'` → CHANGE → `Personal Data Bank` / `ธนาคารข้อมูลส่วนตัว`
- **L982** i18n EN `'Connect your Project KEY data...'` → CHANGE
- **L2877** display string `'อัปเดตจาก: เว็บไซต์ project-key'` / `'Updated via: project-key web'` → CHANGE
- **L3854, L3872** instruction text `ใส่ชื่อ "Project KEY"` → CHANGE
- **L3012, L3022, L3192, L3890** MCP config TEMPLATE keys `"project-key": {...}` → ❓ **Q2 — CHANGE per default**
- **L25, L26, L222, L223, L255, L256, L270, L271, L344, L345** localStorage `projectkey_token`/`projectkey_user` → KEEP (per plan)
- **L1033, L1044** localStorage `projectkey_lang` → ❓ **Q3 — KEEP per default**
- **NEW:** เพิ่ม rebrand notice toast (ดู Plan Step 8)

#### [legacy-frontend/pricing.html](../../legacy-frontend/pricing.html) (7 hits / 3 CHANGE)
- **L6** `<title>เลือกแพลน — Project KEY</title>` → CHANGE
- **L266** `<span>Project KEY</span>` → CHANGE
- **L389** footer `© 2026 Project KEY — Personal AI Context...` → CHANGE
- **L343, L362, L380** `mailto:boss@projectkey.dev` → ❓ **Q1 — KEEP per default**
- **L397** `localStorage.getItem('projectkey_token')` → KEEP

### Tier 2 — Backend (9 files / 12 CHANGE / 3 KEEP)

| File | Line | Action |
|---|---|---|
| [main.py](../../backend/main.py) | 1 | CHANGE docstring |
| [main.py](../../backend/main.py) | 46 | CHANGE `FastAPI(title="Project KEY")` → `"Personal Data Bank"` |
| [main.py](../../backend/main.py) | 1587 | CHANGE `serverInfo.name = "project-key"` → `"personal-data-bank"` |
| [llm.py](../../backend/llm.py) | 20 | KEEP `HTTP-Referer = "https://project-key.fly.dev"` (real URL) |
| [llm.py](../../backend/llm.py) | 21 | CHANGE `X-Title = "Project KEY"` → `"Personal Data Bank"` |
| [mcp_tools.py](../../backend/mcp_tools.py) | 3 | CHANGE docstring |
| [mcp_tools.py](../../backend/mcp_tools.py) | 263 | CHANGE example `'Project KEY v5.4 progress'` → `'Personal Data Bank v5.4 progress'` |
| [mcp_tools.py](../../backend/mcp_tools.py) | 1093 | CHANGE `"system": "Project KEY v4.1 — Personal Data Bank"` → `"Personal Data Bank — v4.1 (PDB)"` |
| [billing.py](../../backend/billing.py) | 1 | CHANGE docstring |
| [config.py](../../backend/config.py) | 1 | CHANGE docstring |
| [config.py](../../backend/config.py) | 30 | KEEP `DATABASE_URL` ใช้ `projectkey.db` |
| [config.py](../../backend/config.py) | (APP_VERSION) | **NEW: bump → "6.1.0"** |
| [\_\_init\_\_.py](../../backend/__init__.py) | 1 | CHANGE comment |
| [auth.py](../../backend/auth.py) | 1 | CHANGE docstring |
| [database.py](../../backend/database.py) | 1 | CHANGE docstring |
| [database.py](../../backend/database.py) | 454 | KEEP `f"projectkey_{...}.db"` (auto backup filename) |
| [shared_links.py](../../backend/shared_links.py) | 52 | KEEP `BASE_URL` fallback URL |

### Tier 3 — Config

| File | Action |
|---|---|
| [package.json](../../package.json) L2 `name` | CHANGE `"project-key"` → `"personal-data-bank"` |
| [package.json](../../package.json) L4 `description` | CHANGE rebrand |
| [package.json](../../package.json) L14 `repository.url` | KEEP `git+https://github.com/boss2546/project-key.git` (per plan Q5) |
| [.env.example](../../.env.example) L1 | CHANGE comment |
| [playwright.config.js](../../playwright.config.js) L12 `baseURL` | KEEP (real URL) |
| [.gitignore](../../.gitignore) L16-18 | KEEP `projectkey.db*` |
| [.dockerignore](../../.dockerignore) L32 | KEEP `projectkey.db*` |
| [fly.toml](../../fly.toml) | KEEP all (per plan — Out-of-Scope) |

### Tier 4 — Tests

#### [tests/test_production.py](../../tests/test_production.py) (4 hits / 3 CHANGE)
- **L2** docstring → CHANGE
- **L15** `BASE = "https://project-key.fly.dev"` → KEEP (real URL — ดู **Q5**)
- **L69** `assert "Project KEY" in r.text` → CHANGE assertion → `"Personal Data Bank"`
- **L75** same → CHANGE

#### [tests/e2e-ui/ui.spec.js](../../tests/e2e-ui/ui.spec.js) (28 hits / 4 CHANGE)
- **L3** docstring → CHANGE
- **L77** `await expect(footer).toContainText("Project KEY")` → CHANGE
- **L352** `test("Logo แสดง Project KEY", ...)` → CHANGE test name
- **L353** `await expect(page.locator(".logo-text")).toContainText("Project KEY")` → CHANGE
- **L656** `await expect(page).toHaveTitle(/Project KEY/)` → CHANGE regex
- **L26-27, L103-104, L177-178, L238-239, L331-332, L374-376, L428-429, L471-472, L521-522, L571-572, L613-614** localStorage operations → KEEP

#### [tests/e2e/test_full_e2e.py](../../tests/e2e/test_full_e2e.py) (1 hit / 1 CHANGE)
- **L89** `q2 = "Tech stack ของ Project KEY ใช้อะไรบ้าง..."` → CHANGE → `"Personal Data Bank"`

#### Fixtures (KEEP per plan rule — verified ไม่อยู่ใน test logic)
- [tests/fixtures/user_research.txt](../../tests/fixtures/user_research.txt) L1 — KEEP
- [tests/fixtures/tech_architecture.md](../../tests/fixtures/tech_architecture.md) L1, L5, L54 — KEEP
- ตรวจแล้ว: [test_full_e2e.py:25-26](../../tests/e2e/test_full_e2e.py#L25-L26) + [test_upload.py:21](../../tests/e2e/test_upload.py#L21) แค่ upload เป็น raw content เฉยๆ — ไม่มี assertion search

### Tier 5 — Active Docs

#### [README.md](../../README.md) (10 hits / 8 CHANGE)
- **L1** `# 🔑 Project KEY — Personal Data Bank` → CHANGE → `# 🔑 Personal Data Bank (PDB)`
- **L7** badge `Production-project--key.fly.dev` + URL link → KEEP (real URL)
- **L116** example query `*"Project KEY เกี่ยวข้องกับอะไรบ้าง"*` → CHANGE
- **L175, L187** mcpServers config keys `"project-key"` → ❓ **Q2 — CHANGE per default**
- **L176, L189** URLs `https://project-key.fly.dev/mcp/...` → KEEP
- **L217** `Project KEY/` (folder name in tree) → CHANGE display
- **L288** comment `# เว็บไซต์: https://project-key.fly.dev/` → URL KEEP
- **L346** footer `*สร้างด้วย ❤️ โดยทีม Project KEY*` → CHANGE

#### [docs/guides/USER_GUIDE_V3.md](../../docs/guides/USER_GUIDE_V3.md) (4 hits / 3 CHANGE)
- **L1** `# 📖 คู่มือการใช้งาน Project KEY v3.0` → CHANGE
- **L478** `| ฐานข้อมูล | projectkey.db (SQLite) |` → KEEP (real filename)
- **L551** ASCII art `Project KEY v3.0` → CHANGE
- **L572** footer attribution → CHANGE

#### [DESIGN.md](../../DESIGN.md) — 0 brand mentions → ไม่ต้องแก้

### Tier 6 — Memory (ส่วนใหญ่ไม่ต้องแก้!)

| File | Hits | CHANGE | Notes |
|---|---|---|---|
| [00-START-HERE.md](../00-START-HERE.md) | 2 | 0 | ทั้ง 2 hits = `projectkey.db` filename ref → KEEP |
| [project/overview.md](../project/overview.md) | 2 | **2** | L4 ลบ "— Project KEY"; L7 bump version 5.9.3 → 6.1.0 |
| [project/tech-stack.md](../project/tech-stack.md) | 1 | 0 | `projectkey.db` → KEEP |
| [project/architecture.md](../project/architecture.md) | 2 | 0 | ทั้ง 2 = `projectkey.db` → KEEP |
| [contracts/api-spec.md](../contracts/api-spec.md) | 1 | 0 | URL → KEEP |
| [contracts/data-models.md](../contracts/data-models.md) | 1 | 0 | filename → KEEP |
| [prompts/prompt-แดง.md](../prompts/prompt-แดง.md) | 1 | 0 | filename → KEEP |
| [prompts/prompt-เขียว.md](../prompts/prompt-เขียว.md) | 1 | 0 | filename → KEEP |
| [prompts/prompt-ฟ้า.md](../prompts/prompt-ฟ้า.md) | 1 | 0 | filename → KEEP |
| [current/last-session.md](../current/last-session.md) | 2 | 0 | filenames → KEEP |
| [current/pipeline-state.md](../current/pipeline-state.md) | 6 | 0 | timeline records ของ rebrand นี้ → KEEP เป็น history |

> **Surprise finding:** Plan สั่งให้ update prompts/, contracts/, 00-START-HERE.md, architecture.md, tech-stack.md — **แต่จริงๆ ไม่มี "Project KEY" ในเนื้อหา** มีแค่ `projectkey.db` filename references ที่ plan สั่ง KEEP อยู่แล้ว

---

## ⚠️ 6 Decision Points — รอ user confirm

### Q1: Email domain `boss@projectkey.dev` (6 จุด)
**ไฟล์:** [pricing.html:343,362,380](../../legacy-frontend/pricing.html), [index.html:1551,1566,1580](../../legacy-frontend/index.html)
**Plan ไม่ระบุ.** active mailto link ใน pricing pages
- 🟢 **Default: KEEP** — สอดคล้องกับ logic "fly.dev URL = KEEP จนกว่ามี custom domain"
- หรือ CHANGE: ต้อง setup email ใหม่ก่อน (`boss@personaldatabank.com`?)

### Q2: MCP config TEMPLATE key `"project-key"` (5 จุด)
**ไฟล์:** [app.js:3012,3022,3192,3890](../../legacy-frontend/app.js), [README.md:175,187](../../README.md)
Template ที่ user copy-paste ไป Claude Desktop config
- 🟢 **Default: CHANGE** เป็น `"personal-data-bank"` — สอดคล้องกับ `serverInfo.name = "personal-data-bank"`
- หรือ KEEP: user เก่าไม่ได้กระทบเพราะ server key ใน config ของเค้าเป็นชื่อที่เค้าเลือกเอง

### Q3: localStorage key `projectkey_lang` (3 จุด)
**ไฟล์:** [app.js:1033,1044](../../legacy-frontend/app.js), [ui.spec.js:376](../../tests/e2e-ui/ui.spec.js)
Plan ระบุ KEEP แค่ `projectkey_token`/`projectkey_user` ไม่กล่าวถึง `_lang`
- 🟢 **Default: KEEP** — same logic (เปลี่ยน = user เก่า reset เป็น default 'th')
- หรือ CHANGE → `pdb_lang`: branding consistent แต่ user เก่าเสีย preference (low-impact)

### Q4: Test fixtures (`user_research.txt`, `tech_architecture.md` — 4 จุด)
ตรวจแล้ว: tests แค่ upload เป็น raw content — ไม่มี assertion search "Project KEY"
- 🟢 **Default: KEEP** (per Plan rule "rebrand if test logic uses, else keep")

### Q5: `tests/test_production.py` BASE URL hardcoded → production
[test_production.py:15](../../tests/test_production.py#L15) hits prod ซึ่งยังเป็น "Project KEY" ก่อน deploy
- 🟢 **Default: ไม่แก้ BASE** — ใช้ uvicorn localhost + manual browser check ตอน self-test; รัน `pytest tests/test_production.py` เป็น smoke test **หลัง deploy** เท่านั้น (ตรงตาม Plan Step 10)

### Q6: Branch strategy + uncommitted leftovers
**Working tree:**
- `scripts/remove_emojis.py` (จาก v6.0.0 polish)
- `tests/test_personality_review.py` (ของฟ้า — review test)
- `.agent-memory/` ทั้งโฟลเดอร์ (pipeline system — ไม่เคย commit)
- modifications ใน `inbox/for-เขียว.md` (ผม move MSG-003 → Read)

🟢 **Default plan:**
1. **Commit chore บน master** ก่อน:
   ```
   chore: add agent pipeline system + utility scripts
   ```
   (รวม `.agent-memory/` + `scripts/` + `tests/test_personality_review.py`)
2. **Branch ใหม่** `rebrand-pdb-v6.1.0` แยก
3. **Build บน branch** → 1 commit ตาม Plan Step 10
4. ผม **ไม่ merge เข้า master** เอง — ส่งฟ้า review → user merge

---

## 🔄 Resume Protocol (ทำตามลำดับเมื่อกลับมา)

1. ✅ User ตอบ 6 ข้อข้างบน (หรือ confirm "ใช้ default ทั้งหมด")
2. ✅ Update [pipeline-state.md](../current/pipeline-state.md) → state = `plan_approved` → `building`
3. ✅ ทำตาม Plan Step 1-10 ใน [2026-05-01-rebrand-pdb.md](2026-05-01-rebrand-pdb.md):
   - Step 1 Pre-flight (branch + grep snapshot)
   - Step 2 Backend (12 changes ในตาราง Tier 2)
   - Step 3 Frontend (18 changes ใน 3 ไฟล์)
   - Step 4 Config (3 changes)
   - Step 5 Tests (8 changes)
   - Step 6 Active Docs (11 changes)
   - Step 7 Memory (2 changes — แค่ `project/overview.md`)
   - Step 8 In-app rebrand notice
   - Step 9 Verify (grep + manual browser)
   - Step 10 Commit + bump APP_VERSION
4. ✅ ส่ง MSG ใน [inbox/for-ฟ้า.md](../communication/inbox/for-ฟ้า.md) → ฟ้า review
5. ✅ User merge → deploy → smoke test → state = `done`

---

## 🧪 Critical Regression Tests (ต้องผ่านทุกข้อหลัง deploy)
จาก Plan + ที่ผมตรวจมา:
- [ ] **Login flow** — user เก่าที่มี `projectkey_token` ใน localStorage ยัง login ได้
- [ ] **MCP existing user** — Claude Desktop config เดิมยัง call tools ได้ (server key เก่ายังใช้ได้แม้ template เปลี่ยน)
- [ ] **Stripe webhook + checkout** — payment flow ครบ
- [ ] **AI Chat** — retrieval + LLM call (X-Title เปลี่ยนแล้วต้องไม่ break OpenRouter)
- [ ] **File upload + organize + summary** — end-to-end
- [ ] **Browser visual** — title, header, footer ทุกหน้าแสดง "Personal Data Bank" / "ธนาคารข้อมูลส่วนตัว"
- [ ] **In-app rebrand toast** — แสดง 1 ครั้งหลัง login → reload ไม่แสดงซ้ำ (`pdb_rebrand_notice_seen` flag)

---

## 📌 หมายเหตุเพิ่ม

- **Time budget เดิม:** Plan = ~3 ชม. — ผมเชื่อว่าเป็นไปได้เพราะ ~56 actual changes mostly mechanical
- **เกี่ยวกับ APP_VERSION:** ใน [overview.md](../project/overview.md#L7) ระบุ `5.9.3` — แต่ Production จริงเป็น v6.0.0 (Personality Profile feature เพิ่ง deploy แล้ว) → จะ bump เป็น `6.1.0` ตาม plan
- **เกี่ยวกับ test_production.py BASE:** ถ้าต้องการให้ pytest รันบน localhost ระหว่าง dev → suggest เพิ่ม env var override ในรอบ refactor หน้า (ไม่ใช่งานนี้)

---

> **เมื่อกลับมาทำงานต่อ:** อ่านไฟล์นี้ + อ่าน [2026-05-01-rebrand-pdb.md](2026-05-01-rebrand-pdb.md) ก็พอ ไม่ต้อง grep ใหม่
