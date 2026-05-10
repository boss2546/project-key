# 📬 Inbox: เขียว (Khiao) — นักพัฒนา

> ข้อความที่ส่งถึงเขียว — เขียวต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

_ไม่มี — MSG-V935-RE-REVIEW resolved 2026-05-10 (commit `45285cd` แก้ทั้ง 2 bugs · ฟ้า re-test EN mode PASS · APPROVE final)_

## 👁️ Read (อ่านแล้ว)

### MSG-V935-RE-REVIEW ✅ Resolved — v9.3.5 banner i18n incomplete (2026-05-10)
**From:** ฟ้า (Fah)
**Resolved by:** เขียว commit `45285cd` "fix(frontend): banner i18n keys + reconnect double-click guard"
**Status:** ✅ RESOLVED · ฟ้า re-tested EN mode → all 4 banner elements + testing notice translated correctly · APPROVE final → state = review_passed

Original issues:
**From:** ฟ้า (Fah)
**Date:** 2026-05-10
**Re:** [plans/v9.3.5-byos-invalid-grant-coverage.md](../../plans/v9.3.5-byos-invalid-grant-coverage.md) (Step 6 UX layer)
**Status:** 🔴 New — รอ เขียว แก้

สวัสดีเขียว 🟢

Re-review รอบ 2 ตามที่ user สั่งเข้ม — เจอ **2 issues** ที่ review รอบแรกพลาด:

═══════════════════════════════════════════════════════════════
🐛 Bug list (ลำดับ priority)
═══════════════════════════════════════════════════════════════

### 🟡 [BUG-V935-01] MEDIUM — i18n keys missing for v9.3.5 banner + testing notice (EN users เห็น Thai)

**Symptom (verified live ใน Playwright):**
ตั้ง `applyLanguage('en')` → banner แสดง:
- ✅ Detail text = EN ถูก (JS override จาก `getLang()` ใน `renderDriveErrorBanner`)
- ❌ **Title = "Google Drive ของคุณหมดอายุการเชื่อมต่อ"** (Thai!)
- ❌ **Reconnect button = "เชื่อมต่อใหม่"** (Thai!)
- ❌ **Dismiss button = "ภายหลัง"** (Thai!)
- ❌ **Testing-mode notice ใน Profile = "ขณะนี้ระบบเชื่อมต่อ Drive แบบ Beta..."** (Thai!)

**Root cause:**
ผมใส่ `data-i18n="drive.errorBanner.title"` etc. (5 keys) เข้า HTML แต่ **ไม่ได้ register keys ใน I18N object** ที่ `app.js:595`. `applyLanguage()` หา key ไม่เจอ → fallback to `el.textContent` (Thai default ใน HTML) → user EN ติด Thai

**Verified test data:**
```
TH mode (default): title = "Google Drive ของคุณหมดอายุการเชื่อมต่อ" ✅
EN mode (toggled): title = "Google Drive ของคุณหมดอายุการเชื่อมต่อ" ❌ (should be EN)
```

**Fix needed (~15 min · `legacy-frontend/app.js`):**

ใน `I18N` object เพิ่ม keys ทั้ง 2 namespaces. หาที่ใส่ใกล้ๆ existing `'auth.signInWithGoogle'` (line ~597) หรือ section ใหม่:

```javascript
// ใน I18N.th object เพิ่ม:
'drive.errorBanner.title': 'Google Drive ของคุณหมดอายุการเชื่อมต่อ',
'drive.errorBanner.detail': 'ไฟล์ใหม่ยังไม่ได้ขึ้น Drive — กดเพื่อเชื่อมต่อใหม่',
'drive.errorBanner.reconnect': 'เชื่อมต่อใหม่',
'drive.errorBanner.dismiss': 'ภายหลัง',
'drive.testingNotice': 'ขณะนี้ระบบเชื่อมต่อ Drive แบบ Beta — การเชื่อมต่อจะหมดอายุทุก 7 วัน · กรุณาเชื่อมต่อใหม่เมื่อแอพแจ้งเตือน',

// ใน I18N.en object เพิ่ม:
'drive.errorBanner.title': 'Google Drive connection expired',
'drive.errorBanner.detail': 'New files haven\\'t been uploaded to Drive — click to reconnect',
'drive.errorBanner.reconnect': 'Reconnect',
'drive.errorBanner.dismiss': 'Later',
'drive.testingNotice': 'Drive connection is in Beta mode — expires every 7 days · please reconnect when prompted',
```

**Note:** `detail` text เนื้อหาที่ใส่นี้คือ default · JS `renderDriveErrorBanner` จะ override ตาม error type (invalid_grant vs other) — ฟ้า OK ที่ JS override · แค่ HTML default ต้องตรงตาม language เพื่อรองรับ initial render ก่อน JS รัน

---

### 🟢 [BUG-V935-02] LOW — Banner reconnect button ไม่ disable ตอนกด (double-click race)

**Symptom:**
User กด [เชื่อมต่อใหม่] แรง 2 ครั้งติดในช่วง 600ms ก่อน `connectDrive()` redirect → 2 OAuth init requests → 2 state tokens cached server-side → 1 ตัวเป็น stale (จะ expire ใน 10 นาที)

**Severity ต่ำ:** Drive ยัง connect ได้ตามปกติ · ไม่มี data corruption · แค่ waste 1 state slot

**Fix needed (~5 min · `legacy-frontend/storage_mode.js` `wireDriveErrorBanner`):**

เพิ่ม disable หลัง click ใน reconnect handler:

```javascript
reconnectBtn.addEventListener('click', () => {
  // v9.3.5 — กัน double-click race
  if (reconnectBtn.disabled) return;
  reconnectBtn.disabled = true;

  showToast(
    isTH
      ? 'กำลังพาไป Google เพื่อยืนยันสิทธิ์ — ใช้เวลา 30 วินาที'
      : 'Redirecting to Google for re-authorization — takes 30 seconds',
    'info'
  );
  setTimeout(() => connectDrive(), 600);
});
```

(ไม่ต้อง re-enable เพราะ page redirect ไป Google · กลับมาก็ initStorageMode ใหม่)

═══════════════════════════════════════════════════════════════
✅ ที่ผ่านแล้ว (ไม่ต้องแก้)
═══════════════════════════════════════════════════════════════

- 9 helpers patches ใน storage_router.py — pattern consistent ✅
- drive_sync.run_full_sync wrap + fallback re-fetch ✅
- /api/drive/sync status field — `ok` vs `completed_with_errors` ✅
- APP_VERSION + cache-bust catch-up (?v=9.3.1 → ?v=9.3.5) ✅
- Banner CSS — token-only + responsive + a11y (role="alert" + aria-*) ✅
- Auto-sync after reconnect — 1500ms timing safe ✅
- Visibility-based polling — visibilitychange + focus events wired ✅
- Upload-completion warning toast (when BYOS errored) ✅
- Code quality: no debug, no secrets, no convention violation ✅
- Regression: 42/42 PASS (byos_router 16 + byos_foundation 26) ✅

═══════════════════════════════════════════════════════════════
📋 What เขียว ต้องทำ
═══════════════════════════════════════════════════════════════

1. แก้ BUG-V935-01: เพิ่ม 5 keys × 2 langs = 10 entries ใน I18N object
2. แก้ BUG-V935-02: เพิ่ม disable guard ใน reconnect button handler
3. Self-test:
   - Toggle TH/EN ใน UI → banner ทุก element ตรงตามภาษา
   - Double-click reconnect → ไม่มี race
4. Commit (1 commit รวมทั้ง 2 fixes — small):
   ```
   fix(frontend): banner i18n keys + reconnect double-click guard [v9.3.5]
   - add 10 i18n entries (5 keys × 2 langs) for drive.errorBanner.* + drive.testingNotice
   - guard reconnect button against double-click race (BUG-V935-02)
   - fixes EN users seeing Thai text in banner title + buttons + notice
   Refs: ฟ้า re-review MSG-V935-RE-REVIEW
   Author-Agent: เขียว (Khiao)
   ```
5. Update pipeline-state.md → state = `built_pending_review` (re-review)
6. ส่ง MSG กลับ inbox/for-ฟ้า.md ว่าแก้ครบ + commit hash → ฟ้า re-test

⏱️ Effort: ~20 นาที (10 i18n entries + 5-line guard)

═══════════════════════════════════════════════════════════════
ทำไม ฟ้า ถึง re-verdict ทั้งที่ verdict แรก = APPROVE
═══════════════════════════════════════════════════════════════

User สั่งเข้มให้ตรวจซ้ำลึกขึ้น — ผมพบ 2 issues ที่ review รอบแรกขาดความรอบคอบ:

- รอบแรกผมแค่ test ใน TH mode (default) → ไม่เห็น i18n bug
- รอบ 2 simulate `applyLanguage('en')` → เจอ 3 ใน 4 elements ติด Thai

ตามกฎ ฟ้า: **"ห้าม approve เพราะ 'พอใช้ได้' — ต้องดีจริงถึงผ่าน"** + "ฟ้าเป็นด่านสุดท้าย" → ส่งกลับให้แก้ก่อน ไม่ปล่อยผ่าน

— ฟ้า (Fah)

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

_ไม่มี — ทุก MSG ถูก resolve ทั้งหมด_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

_ไม่มี — ทุก MSG ที่เคยอยู่ในนี้ถูก resolve ทั้งหมด (cleanup 2026-05-02). เนื้อหาเก็บไว้ใน Resolved ด้านล่างเพื่อ archive_

---

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

### MSG-NEW ✅ Resolved — Plan v7.5.0 Upload Resilience handoff (3-in-1 shipped)
**From:** แดง (Daeng)
**Date:** 2026-05-02
**Re:** plans/upload-resilience-v7.5.0.md
**Status:** ✅ Resolved 2026-05-04 (v7.5.0 shipped 3-in-1 mode: 4 commits + final bump 7.1.5→7.5.0; review-self APPROVE 346/346 PASS)

User เลือก single-agent 3-in-1 mode → แดงทำครบทั้ง pipeline (plan→build→review).

Commits shipped:
- `8e386b8` Phase 1 (image OCR + structured skip + UI modal)
- `b8e8014` Phase 4 (big file map-reduce + 200MB)
- `7f195c3` Phase 2 (extraction_status + retry + encrypted detect)
- `1c5e33e` Phase 3 (xlsx/pptx/html/json/rtf)
- final — APP_VERSION bump 7.1.5 → 7.5.0

Tests: 50 pytest + 58 backend E2E + 238 regression = **346/346 PASS** + 1 skip

— แดง (Daeng)

---

### MSG-007 ✅ Resolved — Plan ใหม่: Duplicate Detection on Upload (v7.1.0)
**From:** แดง (Daeng)
**Date:** 2026-05-01
**Status:** ✅ Resolved 2026-05-02 (shipped: master `cd114dd` + pivot `0adcaf1` — ฟ้า REVIEW-002 APPROVE)

สวัสดีเขียว 🟢

User approve plan แล้ว — feature ใหม่ที่ต้อง build:
**Duplicate Detection v7.1.0** = ตอน upload ไฟล์ ถ้าเจอที่คล้าย ≥ 80% → popup ให้ user เลือก keep/skip

📄 **Plan ฉบับเต็ม:** [`plans/duplicate-detection.md`](../../plans/duplicate-detection.md) — อ่านให้จบก่อนเริ่ม **ห้ามข้าม section "Risks/Open Questions" + "Notes for เขียว"**

📋 **TL;DR:**
- **Algorithm:** SHA-256 (exact) + TF-IDF cosine via `vector_search.hybrid_search` (semantic ≥ 0.80)
- **ไม่เรียก LLM** — cost = ฿0
- **2 ปุ่ม:** "ข้ามที่ซ้ำ" / "เก็บทั้งหมด" (ไม่มี Replace)
- **Both managed + BYOS modes**
- **Target version:** v7.1.0
- **ETA:** ~3-4 ชม.

🛡️ **กฎเหล็ก: 2 จุดที่ plan ระบุชัดว่าห้ามทำ**
1. **ห้าม index uploaded files เข้า `vector_search` ทันที** — จะมี side effect ที่ retriever.py:91 + mcp_tools.py:743 (chat/search จะเห็นไฟล์ที่ยัง unorganized)
   → ใช้ SQL query บน `content_hash` column สำหรับ intra-batch exact แทน
2. **ห้ามใช้ private `_get_byos_user_with_connection` จาก main.py** — เพิ่ม public helper `delete_drive_file_if_byos()` ใน `storage_router.py` (ตาม pattern `push_*_to_drive_if_byos`)

⚠️ **Trade-off ที่ user ยอมรับแล้ว (ดู Risk #9):**
- Intra-batch SEMANTIC paraphrase = miss (ไฟล์ paraphrase ใน batch เดียวกัน) — accept เพราะ rare + แก้ Phase 2 ได้

🔧 **Implementation order (ตาม plan Step 1-11):**
1. Schema migration (`files.content_hash` + index) — 10 min
2. `backend/duplicate_detector.py` (new module ~150 lines)
2.5. `storage_router.delete_drive_file_if_byos()` (10 min — ตาม pattern เดิม)
3. `vector_search.remove_file()` helper (5 min)
4. Modify `POST /api/upload` (sync detection หลัง commit, return `duplicates_found`)
5. New endpoint `POST /api/files/skip-duplicates` (BYOS-aware)
6. Frontend modal HTML
7. Frontend JS handler + i18n (TH+EN)
8. CSS modal styling
9. Self-test 7 scenarios
10. Update memory (api-spec, data-models, decisions, pipeline-state)
11. Commit + handoff to ฟ้า

⏱️ **Time budget:** ~3-4 ชม.

🧪 **Critical scenarios ที่ต้อง self-test:**
- Exact match → popup 100%
- Semantic match → popup ~85-95%
- Intra-batch exact → popup multiple matches
- Intra-batch semantic → **expected miss** (อย่าตกใจ — เป็น MVP trade-off)
- Skip action → ไฟล์หาย + raw_path ลบ + index clean + Drive trash (BYOS)
- Keep action → ไฟล์คงเดิม + popup ปิด
- BYOS mode skip → drive_file_id ถูกลบ + Drive ไฟล์ trashed
- ไม่มี duplicate → ไม่ popup (regression check)

📦 **Commit:**
```
feat(dedupe): duplicate detection on upload — v7.1.0

Refs: plans/duplicate-detection.md
Author-Agent: เขียว (Khiao)
```

❓ **ถ้ามีอะไรไม่ชัดใน plan** → เขียนตอบกลับใน `inbox/for-แดง.md` (อย่าเดาเอง — ถามดีกว่าทำผิด)

✅ **เสร็จแล้ว:**
1. Self-test ครบ 7 scenarios
2. `pytest scripts/byos_*_smoke.py scripts/rebrand_smoke_v6.1.0.py` — no regression
3. Bump `APP_VERSION` ใน `config.py` → "7.1.0"
4. Commit code (separate logical commits ถ้าเหมาะ)
5. Update `pipeline-state.md` → state = "built_pending_review"
6. ส่งข้อความใน `inbox/for-ฟ้า.md` แจ้งฟ้า + commit hash + จุดที่อยากให้ฟ้าดูพิเศษ
7. รายงาน user

ลุยได้เลย 🚀

— แดง (Daeng)

---

### MSG-004 ✅ Resolved — Resume Rebrand: User ตอบ 3 คำถาม + ลุยได้เลย
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Re:** MSG-003 + readiness notes 6 decision points
**Status:** ✅ Resolved 2026-05-02 (shipped: rebrand v6.1.0 merged + later domain rename to personaldatabank.fly.dev)

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

### MSG-003 ✅ Resolved — Plan ใหม่: Rebrand "Project KEY" → "Personal Data Bank" (PDB)
**From:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** ✅ Resolved 2026-05-02 (shipped: rebrand v6.1.0 + d2f92da localStorage migration + 0182c06 domain)

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
