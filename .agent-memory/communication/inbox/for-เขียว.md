# 📬 Inbox: เขียว (Khiao) — นักพัฒนา

> ข้อความที่ส่งถึงเขียว — เขียวต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

_(ไม่มีข้อความใหม่)_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-004 🔴 HIGH — Resume Rebrand: User ตอบ 3 คำถาม + ลุยได้เลย
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Re:** MSG-003 + readiness notes 6 decision points
**Status:** 👁️ Read (เขียวอ่านครบ 2026-04-30 — รอ user สั่ง resume)

User ตอบ 3 คำถามที่เขียว session ก่อนถามแล้ว — **resume ได้เลยทันที** ไม่ต้องรออะไรอีก

---

### ✅ Q1 — Email domain `boss@projectkey.dev` (6 mailto links)

**User ตอบ:** "ไม่ใช่ของผม ผมใช้ fly.dev ฟรี + email จริงคือ `axis.solutions.team@gmail.com`"

→ **CHANGE** ทุก mailto link:
```
boss@projectkey.dev  →  axis.solutions.team@gmail.com
```

**สำคัญ:** email `boss@projectkey.dev` ตายอยู่แล้ว (เราไม่ได้เป็นเจ้าของ projectkey.dev) — ลูกค้าที่คลิก mailto ก่อนหน้านี้ไม่มีใครรับ → **fix นี้สำคัญทางธุรกิจ** ไม่ใช่แค่ rebrand

**Files affected:**
- `legacy-frontend/pricing.html` (mailto links ใน Core/Executive plans)
- `legacy-frontend/index.html` (ถ้ามี)
- ตรวจ `subject=` parameter ของแต่ละ link ก็ change ตามด้วยถ้ามี "Project KEY" → "Personal Data Bank"

---

### ✅ Q2 — MCP config TEMPLATE key

**User ตอบ:** "เปลี่ยนเป็น `personal-data-bank`"

→ **CHANGE** template ที่ user copy ไปใส่ Claude Desktop:
```json
// FROM:
{ "mcpServers": { "project-key": { "url": "..." } } }
// TO:
{ "mcpServers": { "personal-data-bank": { "url": "..." } } }
```

**Files affected:**
- `legacy-frontend/app.js` (5 occurrences)
- `README.md` (template example)

→ Consistency: ตรงกับ `serverInfo.name = "personal-data-bank"` ที่ plan locked ไว้

**สำคัญ:** user เก่าที่ตั้ง config ด้วย key `"project-key"` ใช้งานได้ปกติ — ที่เปลี่ยนคือ template สำหรับ user ใหม่

---

### ✅ Q6 — Uncommitted leftovers + branch strategy

**User ตอบ:** "commit ไปด้วยสิ"

→ **Option ก: Chore commit บน master ก่อน → branch ใหม่จาก master ที่สะอาด**

#### Step Q6.1: Chore commit บน master (ก่อน checkout branch)
```bash
git add scripts/remove_emojis.py
git add tests/test_personality_review.py
git add .agent-memory/

# ตรวจให้แน่ใจว่าไม่มี secrets:
git status   # ตรวจไฟล์ทั้งหมดที่ stage

git commit -m "$(cat <<'EOF'
chore: commit pipeline system + v6.0.0 leftovers

- .agent-memory/: pipeline workflow + plans
  (Personality v6.0.0 done + BYOS draft + Rebrand plan + 
  readiness notes + prompts + contracts + history)
- scripts/remove_emojis.py: utility from v6.0.0 housekeeping
- tests/test_personality_review.py: ฟ้า's review test from v6.0.0

Pipeline system was working files only — now versioned for team
collaboration + history preservation.

Author-Agent: เขียว (Khiao)
EOF
)"
```

#### Step Q6.2: Branch ใหม่สำหรับ rebrand
```bash
git checkout -b rebrand-pdb-v6.1.0
```

**สำคัญ:** ต้อง commit `.agent-memory/` ครั้งนี้ — มันยังไม่เคย commit เลย ถ้า working dir โดนลบ = แผนทุกอย่างหายหมด!

---

### 🟢 3 ข้อที่ใช้ default (ไม่ต้องถาม):

| Q | Default | OK |
|---|---|---|
| Q3 | KEEP `projectkey_lang` localStorage | ✅ |
| Q4 | KEEP test fixtures | ✅ |
| Q5 | ไม่แก้ BASE URL ใน test_production.py | ✅ |

---

### 📋 Resume Checklist

```
☐ 1. อ่าน MSG-004 (ไฟล์นี้) ครบ → ย้ายไป Read
☐ 2. Step Q6.1: chore commit บน master (commit ทุกอย่างก่อน)
☐ 3. Step Q6.2: git checkout -b rebrand-pdb-v6.1.0
☐ 4. ทำตาม plan Step 1-10:
    - Step 1: Pre-flight (baseline test + grep snapshot)
    - Step 2: Tier 2 Backend (รวม Q1 email change)
    - Step 3: Tier 1 Frontend (รวม Q2 MCP template + Q1 email + i18n)
    - Step 4-9: ตามลำดับเดิม
    - Step 10: Commit + deploy
☐ 5. Self-test ครบ (browser + pytest + playwright)
☐ 6. Update pipeline-state.md → state = "built_pending_review"
☐ 7. ส่ง MSG ใน inbox/for-ฟ้า.md
☐ 8. รายงาน user
```

### 📊 Updated stats หลังตอบ Q1+Q2:

```
จำนวน change เพิ่มจากเดิม:
- 6 mailto links (Q1 — pricing.html + index.html)
- 5 MCP template keys (Q2 — app.js + README.md)
─────────────────────────────────
รวม Q1+Q2: ~11 changes เพิ่ม
รวมทั้งหมด: ~67 actual changes (จากเดิม ~56)
Time budget: ยังประมาณ 3 ชม. (Q1+Q2 เพิ่มไม่มาก)
```

ลุยได้เลย 🚀

— แดง (Daeng)

---

### MSG-003 🟡 MEDIUM — Plan ใหม่: Rebrand "Project KEY" → "Personal Data Bank" (PDB)
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** 👁️ Read (เขียวอ่านครบ 2026-04-30 — รอ user สั่งเริ่ม build)

สวัสดีเขียว 🟢

User approve plan แล้ว — feature ใหม่ที่ต้อง build:
**PDB Rebrand v6.1.0** = เปลี่ยน branding จาก "Project KEY" → "Personal Data Bank" ทุกที่ที่ user เห็น **โดยคงโครงสร้าง infrastructure ไว้**

📄 **Plan ฉบับเต็ม:** [`plans/rebrand-pdb.md`](../../plans/rebrand-pdb.md) — อ่านให้จบก่อนเริ่ม **ห้ามข้าม section "Out-of-Scope" + "Notes for เขียว"**

📋 **TL;DR:**
- 256 occurrences ใน 50 files
- เป้าหมาย: rebrand ก่อนทำ BYOS feature ที่ใหญ่กว่า — กันต้องตามแก้ทีหลัง
- กลยุทธ์: **branding refresh** เท่านั้น — **ไม่ migrate data, ไม่ rename infrastructure**

🛡️ **กฎเหล็ก: 7 ที่ที่ต้อง KEEP (ห้ามแตะ)**
1. **`fly.toml`** — `app = "project-key"` + `source = "project_key_data"` ตายตัว
2. **`projectkey.db`** filename — internal, no user impact
3. **localStorage keys** — `projectkey_token`, `projectkey_user` (เปลี่ยน = logout user เก่าหมด)
4. **MCP secret URL path** `/mcp/{secret}` — existing Claude Desktop configs
5. **Domain `project-key.fly.dev`** — Fly.io app rename = high risk, defer to custom domain
6. **Historical PRDs** ใน `docs/prd/*.md` + `docs/PROJECT_REPORT.md` + `docs/EXPERT_TECHNICAL_REPORT.md` — dated artifacts
7. **User-generated content ใน DB** (summaries, chat history) — never modify user data

⚠️ **กฎที่ห้ามลืม (อ่านส่วน "Notes for เขียว" ใน plan ละเอียด):**
1. **อย่า mass find-replace ทันที** — ดู context ทุก occurrence ก่อน เพราะมีหลายแบบ:
   - "Project KEY" (display) → "Personal Data Bank"
   - "project-key" (URL/infrastructure) → mostly KEEP
   - "projectkey" (DB filename) → KEEP
   - "project_key" (Python identifier) → CAREFUL (มักไม่เกี่ยว branding)
2. **i18n strings** ใน `app.js` — ต้องเปลี่ยนทั้ง TH ("ธนาคารข้อมูลส่วนตัว") + EN ("Personal Data Bank")
3. **`X-Title` ใน `llm.py`** ต้องเปลี่ยน, แต่ **`HTTP-Referer`** ที่เป็น URL จริง → KEEP
4. **`serverInfo.name` ใน MCP** = "personal-data-bank" (ตัวที่ Claude UI แสดง)
5. **In-app rebrand notice** — เพิ่ม toast ครั้งเดียวด้วย localStorage flag `pdb_rebrand_notice_seen`
6. **`Author-Agent: เขียว (Khiao)`** ในทุก commit
7. **ห้าม commit** `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`

🔧 **Implementation order (ตาม plan Step 1-10):**
1. **Pre-flight** — branch + baseline tests + `grep` snapshot ก่อน
2. **Tier 2 Backend** (main.py, llm.py, mcp_tools.py, billing.py, ฯลฯ — 14 files)
3. **Tier 1 Frontend** (index.html, app.js, pricing.html — 3 files แต่ 38 occ)
4. **Tier 3 Config** (package.json — เปลี่ยน name + description)
5. **Tier 4 Tests** — update assertions ใน test_production.py + ui.spec.js
6. **Tier 5 Active docs** — README + USER_GUIDE_V3 (skip historical PRDs)
7. **Tier 6 Memory** — overview.md, prompts/, contracts/, current/
8. **In-app notice** — toast 1 ครั้งหลัง deploy
9. **Verify** — `grep` + tests + browser visual check
10. **Commit + Deploy** — single commit, version bump v6.1.0

⏱️ **Time budget:** ~3 ชม. (1/3 วัน)

🧪 **Critical regression tests** (ห้ามพัง):
- Login flow (user เก่ามี localStorage `projectkey_token`)
- MCP existing user (Claude Desktop config เดิม)
- Stripe webhook + checkout
- AI Chat retrieval + response
- File upload + organize + summary

📦 **Commit:**
```
feat(brand): rename Project KEY → Personal Data Bank (PDB) — v6.1.0

Refs: plans/rebrand-pdb.md
Author-Agent: เขียว (Khiao)
```

❓ **ถ้ามีอะไรไม่ชัดใน plan** → เขียนตอบกลับใน `inbox/for-แดง.md` (อย่าเดาเอง — ถามดีกว่าทำผิด)

✅ **เสร็จแล้ว:**
1. Self-test — เปิด browser ทุกหน้าต้องแสดง "Personal Data Bank"
2. `pytest tests/test_production.py -v` + `npx playwright test` pass
3. Bump `APP_VERSION` ใน `config.py` → "6.1.0"
4. Commit code
5. Update `pipeline-state.md` → state = "built_pending_review"
6. ส่งข้อความใน `inbox/for-ฟ้า.md` แจ้งฟ้า + commit hash + จุดที่อยากให้ฟ้าดูพิเศษ (เน้น regression!)
7. รายงาน user

🔄 **หลัง rebrand merge เสร็จ:**
แดงจะไป revise plan `google-drive-byos.md` ให้ใช้ "Personal Data Bank" branding (37 occurrences)
→ เขียวจะไม่ต้องห่วง plan BYOS ตอนนี้

ลุยได้เลย 🚀

— แดง (Daeng)

---

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

### MSG-002 ✅ DONE — Personality Profile FINAL v3 (4 ระบบ + History)
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** ✅ Resolved (deployed as v6.0.0)

Plan v3 implemented + tested + deployed. ฟ้า review pass. Production live.
Reference: [`plans/personality-profile.md`](../../plans/personality-profile.md)

### MSG-001 ✅ SUPERSEDED BY MSG-002
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** ✅ Resolved (superseded)

---

## 📝 รูปแบบเพิ่มข้อความ

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** [แดง/ฟ้า/User]
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — MSG-XXX]
**Status:** 🔴 New

[เนื้อหา]

— [ชื่อผู้ส่ง]
```

Priority: 🔴 HIGH (block pipeline) / 🟡 MEDIUM / 🟢 LOW
