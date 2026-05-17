# 🟢 Fix Plan: เขียว-B — Perf + Thai + Frontend + Ops

> **Created:** 2026-05-17 · **Author:** เขียว-B (derived from plan A coordination matrix + scope)
> **Target version:** v10.1.0 (cumulative through sprints) · **Pipeline:** 4 sprints · ~3.5 weeks full-time
> **Mirror of:** [fix-plan-เขียว-A.md](fix-plan-เขียว-A.md) — เขียว-B = parallel agent

> ⚠️ **DRAFT — derived from coordination signals.** Original B0.1-B3.11 planning chat ไม่ได้อยู่ใน
> session context ของผม. ผม derive milestones จาก: (1) A's coordination matrix (B0.4/B1.9/B2.7/B2.11
> ที่ระบุชื่อชัด), (2) scope user ระบุ "Perf + Thai + Frontend + Ops", (3) audit findings ที่อยู่ใน
> file ownership ของ B. **User ต้อง review + approve ก่อนเริ่ม Sprint 0.**

---

## 🎯 Mission Statement

แก้ **Performance** ที่ทำให้ระบบช้า/พังที่ scale + **Thai-first quality** ที่ระบบไม่ครอบคลุม + **Frontend XSS/UX** ที่ยังไม่ปลอดภัย + **Ops infrastructure** ที่ขาด (CI/CD, observability, deployment safety)

เจ้าหน้าที่: เขียว-B (ผม) — รับผิดชอบ frontend ทั้งหมด, ingestion/extraction/worker, processors, infra
ทำงาน **คู่ขนาน** กับ เขียว-A (Security + DB + API) แต่ **คนละไฟล์**

---

## 📋 Pipeline State Header

```yaml
plan_id: fix-plan-เขียว-B
sprint_count: 4 (Sprint 0, 1, 2, 3)
milestones: 38 (B0.1-B0.5, B1.1-B1.10, B2.1-B2.12, B3.1-B3.11)
parallel_with: เขียว-A
review_gate: ฟ้า (review หลัง sprint end + final UI test)
target_p0_closure: 12/12 (B scope)
estimated_effort: 16 sprint-days
```

---

## 🗂 Scope: Files Owned

### ✅ เขียว-B เป็นเจ้าของ (แตะได้คนเดียว)

```
# Backend ingestion + perf
backend/vector_search.py
backend/duplicate_detector.py
backend/extraction.py
backend/organizer.py
backend/upload_worker.py
backend/progress_tracker.py
backend/shared_links.py
backend/drive_oauth.py
backend/embeddings.py
backend/ai_ingest.py
backend/retriever.py
backend/processors/*

# Test files (สร้างใหม่)
backend/_test_extraction.py
backend/_test_organizer.py
backend/_test_upload_worker.py
backend/_test_processors.py
backend/_test_embeddings.py     # มีอยู่แล้ว (จาก v11 Phase 0)
backend/_test_v11_migration.py  # มีอยู่แล้ว (จาก v11 Phase 0)

# Frontend ทั้งหมด
legacy-frontend/*.html
legacy-frontend/*.js
legacy-frontend/*.css
legacy-frontend/guide/*

# Infra + Ops
Dockerfile
fly.toml
pyproject.toml
requirements-fly.txt
.github/workflows/*
scripts/*
.gitignore
.dockerignore
```

### ❌ เขียว-B ห้ามแตะ (เป็นของ A)

```
backend/main.py
backend/auth.py
backend/admin.py
backend/database.py       # Schema + migrations
backend/config.py         # ❗ B request changes via inbox
backend/llm.py            # LLM API client + validation
backend/line_quota.py
backend/schemas/*
backend/migrations/*
backend/_test_{auth,endpoints,database,config,llm}.py
backend/conftest.py
```

### 🤝 จุดประสาน (ทั้งคู่ต้องคุย)

```
backend/config.py    — A owns, B requests via inbox
backend/main.py      — A owns เต็มไฟล์, แต่ B อาจขอแก้ specific helper
                       (เช่น integrate magic bytes ใน upload handler) — ผ่าน inbox เสมอ
backend/llm.py       — A defines API contract, B uses (e.g., call_llm_json from extraction)
```

---

## 🚦 Rules of Engagement (ห้ามฝ่าฝืน)

1. **1 branch per sprint**: `fix/B-sprint-0`, `fix/B-sprint-1`, etc.
2. **Commit tag**: ทุก commit message ขึ้นต้น `[B0.X]` หรือ `[B1.X]` ตาม milestone
3. **Co-Authored-By footer**: ใส่ทุก commit (เขียว-B + Claude)
4. **No force push** บน sprint branch หลัง push แล้ว
5. **Deploy gate**: ห้าม deploy prod กลาง sprint — รวบทุก milestone end of sprint deploy ครั้งเดียว
   ยกเว้น B0.X (ops/security emergency)
6. **Backwards compat**: ทุก frontend change ต้อง support legacy backend response 30 วัน (during A migration)
7. **Test first, then code**: เขียน test ก่อน implement (TDD where reasonable)
8. **Inbox protocol**: ขอ A แก้ไฟล์ของ A → เขียน `.agent-memory/communication/inbox/for-เขียว-A.md`
9. **Pre-merge**: ทุก sprint end ส่ง ฟ้า review ก่อน merge
10. **v11 coexistence**: feature flag ใหม่ของ B ต้อง default OFF ใน prod · enable per-user only

---

## 📅 Sprint Roadmap Overview

| Sprint | Theme | Days | Milestones | Deploy |
|--------|-------|-----:|-----------|:------:|
| **0** | Ops + XSS + Worker Emergency | 1 | B0.1-B0.5 | ✅ Day 1 emergency |
| **1** | Performance Optimization | 5 | B1.1-B1.10 | ✅ Day 6 |
| **2** | Thai-first + Magic Bytes | 5 | B2.1-B2.12 | ✅ Day 11 |
| **3** | Frontend Refactor + CI/CD | 5 | B3.1-B3.11 | ✅ Day 16 (final) |

---

# 🚨 Sprint 0 — Stop the Bleeding (Day 1)

**Goal:** ปิดรู ops/security ฝั่ง B ที่ผมต้องแก้ก่อน + เริ่ม coordination กับ A ใน 4-6 ชม.

---

## B0.1 — Tighten `.gitignore` + `.dockerignore` (orphan artifacts)

### What

เพิ่ม pattern ที่ขาด:
- `.fuse_hidden*` (FUSE filesystem tombstones — เจอตอน cleanup session 2026-05-17)
- `.venv*/` (any venv variant — `.venv_v11_test/` เคยโผล่)
- `.archive/` (mentioned in current `.gitignore` แต่ commit ไม่ครอบคลุม)
- `*.fuse_*` patterns
- IDE artifacts ที่ยังหลุดเข้า `.vscode/`, `.idea/`

### Why

- ลด noise ใน `git status` (ตอน cleanup เจอ `.fuse_hidden*` 10+ ไฟล์)
- ป้องกัน venv leak ในอนาคต (test venv ขนาด GB ไม่ควรอยู่ใน repo)

### How

```diff
# .gitignore additions
+ # FUSE filesystem tombstones (Windows + WSL artifact)
+ .fuse_hidden*
+ *.fuse_*
+
+ # Any venv variant (defensive)
+ .venv*/
+ venv*/
+
+ # IDE
+ .idea/
+ .vscode/
+ *.swp
+ *.swo
```

```diff
# .dockerignore additions
+ .fuse_hidden*
+ .venv*/
+ .archive/
+ tests/
+ qa-report-*.md
+ bug-report-*.md
+ docs/
+ .agent-memory/
```

### Test

```bash
# Verify .fuse_hidden* ignored
touch .fuse_hidden_test
git status --short | grep -q "fuse_hidden" && echo "FAIL: still tracked" || echo "PASS"
rm .fuse_hidden_test

# Verify .venv ignored
mkdir .venv_test && touch .venv_test/lib
git status --short | grep -q ".venv_test" && echo "FAIL" || echo "PASS"
rm -rf .venv_test

# Docker image size check (should drop)
docker build --tag pdb:before .
docker build --tag pdb:after .  # after .dockerignore update
docker images | grep pdb  # verify size diff
```

### Rollback

revert commit — patterns ที่เพิ่มเป็น additive ไม่ break อะไร

### Files Touched

```
.gitignore              (+10 lines)
.dockerignore           (+8 lines)
```

### Time Estimate: 15 min

---

## B0.2 — Pre-commit Hook with Secret Scanner

### What

ติดตั้ง pre-commit + gitleaks เพื่อ scan secrets ก่อน commit
ป้องกัน `.env` re-leak หลังจาก A0.1 cleanup git history

### Why

- A0.1 ลบ `.env` จาก history แล้ว — แต่ไม่มี mechanism ป้องกัน leak ครั้งใหม่
- Pre-commit hook = automatic gate ที่ดีกว่า manual review

### How

```yaml
# .pre-commit-config.yaml (NEW)
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        args: ["protect", "--staged", "--verbose"]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=500"]  # 500 KB warning threshold
```

```bash
# Install + activate
pip install pre-commit
pre-commit install

# Test on staged file with fake secret
echo "API_KEY=sk-test-1234567890abcdef" > test.env
git add test.env
git commit -m "test"  # should fail
rm test.env
git reset HEAD .
```

### Test

```bash
# 1. Hook installed
ls -la .git/hooks/pre-commit  # should exist

# 2. Detects fake secret
echo "OPENROUTER_API_KEY=sk-or-v1-fake1234567890" > fake.env
git add fake.env
git commit -m "test" 2>&1 | grep -q "gitleaks" && echo "PASS" || echo "FAIL"
git reset HEAD fake.env && rm fake.env

# 3. Allows clean commit
echo "# Just a comment" > clean.md
git add clean.md
git commit -m "test clean"  # should succeed
git reset HEAD~1 && rm clean.md
```

### Rollback

```bash
pre-commit uninstall
rm .pre-commit-config.yaml
```

### Files Touched

```
.pre-commit-config.yaml   (NEW ~25 lines)
.github/workflows/        (later in B3.5 — add gitleaks to CI too)
README.md                 (add setup instructions ~5 lines)
```

### Time Estimate: 1 hour

---

## B0.3 — Frontend XSS Audit (emergency hotfix)

### What

Audit `app.js` (6,627 lines) + `landing.js` (634 lines) สำหรับ `innerHTML = ...` patterns
ที่ใช้ user-controlled content โดยไม่ escape

### Why

- Frontend ใช้ `innerHTML` กับ template strings (per memory frontend_architecture.md)
- ถ้ามีจุดไหน user data → `escapeHtml` ไม่ถูกเรียก → stored XSS
- เปิด public launch โดยมีรูนี้ = risk

### How

**Step 1: Grep all innerHTML usage**

```bash
grep -nE "innerHTML\s*=" legacy-frontend/app.js | head -50
grep -nE "innerHTML\s*=" legacy-frontend/landing.js
grep -nE "innerHTML\s*=" legacy-frontend/storage_mode.js
grep -nE "innerHTML\s*=" legacy-frontend/line_ui.js
```

**Step 2: ตรวจแต่ละ instance**

```javascript
// ❌ DANGEROUS
container.innerHTML = `<div>${user.name}</div>`;  // ถ้า name = "<script>..."

// ✅ SAFE
container.innerHTML = `<div>${escapeHtml(user.name)}</div>`;

// ✅ SAFE (alt pattern)
const div = document.createElement('div');
div.textContent = user.name;  // browser auto-escape
container.appendChild(div);
```

**Step 3: Categorize findings**

- A: user-controlled, no escape → 🔴 fix immediately
- B: API response, no escape → 🟠 fix if string field
- C: hardcoded HTML → 🟢 safe (verify)

### Test

```javascript
// tests/e2e-ui/xss-injection.spec.js (NEW)
test('filename with <script> tag does not execute', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000/app');
  // ... login

  // Upload file ที่ตั้งชื่อมีของอันตราย
  await page.locator('input[type=file]').setInputFiles({
    name: '<script>window.xss=true</script>.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('hello'),
  });

  // Wait for file list render
  await page.waitForSelector('.file-item');

  // Verify script ไม่ run
  const xss = await page.evaluate(() => window.xss);
  expect(xss).toBeUndefined();

  // Verify display escaped
  const text = await page.locator('.file-item').first().textContent();
  expect(text).toContain('<script>');  // literal text, not interpreted
});
```

### Rollback

revert commit — escape calls เป็น additive, ไม่ break อะไร

### Files Touched

```
legacy-frontend/app.js        (~30-50 sweep sites)
legacy-frontend/landing.js    (~5-10 sites)
tests/e2e-ui/xss-injection.spec.js  (NEW)
```

### Time Estimate: 2-3 hours

---

## B0.4 — Request A: Embedding Default Change

### What

ส่ง MSG ใน `for-เขียว-A.md` ขอเปลี่ยน `EMBEDDING_MODEL` default จาก
`text-embedding-001` → `gemini-embedding-001` ใน `backend/config.py`

### Why

- ใช้ตอน v11 Phase 1 — `gemini-embedding-001` accuracy ดีกว่าและ price/perf match
- A0.X security work ไม่ block — A merge ได้ทันที (1 บรรทัด)

### How

```markdown
### MSG-B-TO-A-001 🆕 Request: Change EMBEDDING_MODEL default
**From:** เขียว-B
**Date:** 2026-05-17
**Re:** Sprint 0 — coordination with v11 Phase 1
**Priority:** P1 (not blocking, but unblocks B1.x perf work)

A — ขอเปลี่ยน 1 บรรทัดใน `backend/config.py`:

```diff
- EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-001")
+ EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
```

**Reason:** v11 Phase 1 ใช้ gemini-embedding-001 ดีกว่า (accuracy + cost)
**Test:** existing v11 embedding tests ครอบคลุม
**ETA from A:** Sprint 0 (merge ตอน A0.X commits)

ขอบคุณครับ
```

### Test

```bash
# After A merges
grep "EMBEDDING_MODEL" backend/config.py | head -1
# expected: ... "gemini-embedding-001")
```

### Files Touched

```
.agent-memory/communication/inbox/for-เขียว-A.md  (+15 lines)
# B ไม่แก้ config.py โดยตรง
```

### Time Estimate: 5 min

---

## B0.5 — Worker Startup Probe + Readiness Gate

### What

เพิ่ม readiness gate ใน `backend/upload_worker.py`:
- ถ้า worker ไม่ healthy (no heartbeat ≥30s) → `/api/upload` คืน 503
- ปัจจุบัน upload accept ทั้งที่ worker ตาย → ไฟล์ค้างใน queue ตลอด

### Why

- v9.4.0 มี heartbeat แล้ว แต่ไม่ block upload
- ถ้า worker crash → user upload ต่อ → frontend ค้าง progress bar ไม่จบ
- เปิด public launch โดยไม่มี readiness gate = bad UX ตอน worker ปัญหา

### How

```python
# backend/upload_worker.py — เพิ่ม public helper
def is_worker_ready() -> bool:
    """True ถ้า worker started + heartbeat ใหม่กว่า HEARTBEAT_STALE_SEC.

    เรียกจาก /api/upload ก่อน accept request:
      - ready=True → accept ปกติ
      - ready=False → คืน 503 SERVICE_UNAVAILABLE
    """
    if not HEARTBEAT_FILE.exists():
        return False
    age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    return age < HEARTBEAT_STALE_SEC


# backend/main.py — A ต้องเพิ่ม import + guard (request via inbox)
# ผมเขียน inbox ขอ A integrate
```

**Coordination:** ผมเขียน `backend/upload_worker.py` ส่วน `is_worker_ready()` แล้วส่ง MSG ให้ A
integrate ใน `/api/upload` handler (เพราะ main.py เป็นของ A)

### Test

```python
# backend/_test_upload_worker.py
async def test_is_worker_ready_when_heartbeat_fresh():
    HEARTBEAT_FILE.write_text(str(time.time()))
    assert is_worker_ready() is True

async def test_is_worker_ready_false_when_stale():
    HEARTBEAT_FILE.write_text(str(time.time() - 60))  # > 30s old
    assert is_worker_ready() is False

async def test_is_worker_ready_false_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.upload_worker.HEARTBEAT_FILE", tmp_path / "nope.txt")
    assert is_worker_ready() is False
```

### Rollback

revert commit + remove import from main.py (coordinate with A)

### Files Touched

```
backend/upload_worker.py            (+10 lines)
backend/_test_upload_worker.py      (NEW ~30 lines)
.agent-memory/communication/inbox/for-เขียว-A.md  (request integration MSG)
```

### Time Estimate: 1 hour

---

## ✅ Sprint 0 Acceptance Gate

ก่อน close Sprint 0:
1. [ ] `.gitignore` + `.dockerignore` patterns updated · verify `.fuse_hidden*` no longer noisy
2. [ ] Pre-commit hook installed + gitleaks test pass
3. [ ] XSS audit ครบทุก `innerHTML` site · escape applied
4. [ ] MSG B0.4 ส่ง A — A merge ภายใน Sprint 0
5. [ ] `is_worker_ready()` helper + test pass · MSG ส่ง A integrate
6. [ ] Deploy to prod + `/health` 200 + version bump = `10.0.30-sprint0-b`
7. [ ] **ส่งฟ้า review** ผ่าน `for-ฟ้า.md`
8. [ ] ฟ้า verdict = APPROVED → close Sprint 0

---

# 🚀 Sprint 1 — Performance Optimization (Days 2-6)

**Goal:** ทำให้ระบบรองรับ 10K+ ไฟล์/user + reduce frontend bundle + speed up ingestion

---

## B1.1 — Frontend Bundle Audit + app.js Module Split (intro)

### What

- Audit `app.js` 6,627 lines → identify split boundaries
- เริ่ม Phase 1 split: extract `legacy-frontend/app/{router, fileList, chat}.js`
- ยังไม่ split ทั้งหมด — เก็บ phase 2/3 สำหรับ B3.11

### Why

- 6627 lines = single file load = slow first paint
- ยาก maintain (per memory frontend_architecture.md)
- Split = lazy load + cache benefit

### How

**Step 1: Identify natural boundaries** (จาก grep)

```bash
grep -nE "^function (load|render|switch|init)" legacy-frontend/app.js | head -30
# Expected categories:
# - Router: switchPage, init, applyLanguage
# - File ops: loadFiles, renderFiles, deleteFile, uploadFiles
# - Chat: askAI, renderChatMessage, ...
# - Graph: loadGraph, renderGraph, ...
# - MCP: loadMcpInfo, regenMcpToken, ...
# - Profile: loadProfile, savePersonality, ...
```

**Step 2: Create module structure**

```
legacy-frontend/
├── app.js              (entry + router only · ~500 lines after split)
├── app/                (NEW dir)
│   ├── router.js       (switchPage + page transitions)
│   ├── fileList.js     (loadFiles + renderFiles + ops)
│   ├── chat.js         (askAI + chat state)
│   ├── graph.js        (D3 + lenses)
│   ├── mcp.js          (MCP info + tokens)
│   ├── profile.js      (profile + personality)
│   └── utils.js        (escapeHtml, authFetch, i18n helpers)
```

**Step 3: Use `<script type="module">` + ESM imports**

```html
<!-- app.html -->
<script type="module" src="/app.js?v=10.1.0"></script>
```

```javascript
// legacy-frontend/app.js (new — slim entry)
import { initRouter } from './app/router.js';
import { initI18n } from './app/utils.js';

document.addEventListener('DOMContentLoaded', () => {
  initI18n();
  initRouter();
});
```

### Test

```javascript
// tests/e2e-ui/module-split.spec.js (NEW)
test('app.js loads as module + all pages still render', async ({ page }) => {
  const requests = [];
  page.on('request', r => requests.push(r.url()));

  await page.goto('http://127.0.0.1:8000/app');
  // login...

  // Verify modules loaded
  const moduleRequests = requests.filter(r => r.includes('/app/') && r.endsWith('.js'));
  expect(moduleRequests.length).toBeGreaterThanOrEqual(5);

  // Verify all pages still work
  for (const pageName of ['my-data', 'knowledge', 'graph', 'chat', 'mcp-setup']) {
    await page.click(`[data-page="${pageName}"]`);
    await expect(page.locator(`#page-${pageName}.active`)).toBeVisible();
  }
});
```

### Rollback

revert commit → ใช้ monolithic `app.js` เดิม

### Files Touched

```
legacy-frontend/app.js                (~6000 lines moved out)
legacy-frontend/app/router.js         (NEW)
legacy-frontend/app/fileList.js       (NEW)
legacy-frontend/app/chat.js           (NEW)
legacy-frontend/app/utils.js          (NEW)
legacy-frontend/app.html              (script tag → module)
tests/e2e-ui/module-split.spec.js     (NEW)
```

### Time Estimate: 1 day

### Coordination

ใน Phase 1 ของ split — ยังไม่แตะ MCP/Graph/Profile modules (เก็บใน app.js เดิมส่วน untouched)
Phase 2 ใน B3.11 จะ finalize ทั้งหมด

---

## B1.2 — D3.js Lazy Load

### What

ปัจจุบัน D3.js v7 (300+ KB) โหลดบนทุกหน้า — ใช้จริงแค่หน้า Graph
เปลี่ยนเป็น dynamic import เมื่อ user สลับมาหน้า Graph

### Why

- 300 KB JS = ~150ms parse time บน mobile
- 90% ของ user ไม่เปิดหน้า Graph → wasted bandwidth + CPU

### How

```javascript
// legacy-frontend/app/router.js
async function switchPage(page) {
  // ... existing logic

  if (page === 'graph' && !window.d3) {
    // Lazy load D3
    await loadScript('https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js');
  }

  // ... render
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}
```

### Test

```javascript
test('D3 not loaded until graph page visited', async ({ page }) => {
  const requests = [];
  page.on('request', r => requests.push(r.url()));

  await page.goto('http://127.0.0.1:8000/app');
  // login + go to My Data
  expect(requests.some(r => r.includes('d3'))).toBe(false);

  await page.click('[data-page="graph"]');
  await page.waitForTimeout(500);  // wait for lazy load
  expect(requests.some(r => r.includes('d3'))).toBe(true);
});
```

### Files Touched

```
legacy-frontend/app/router.js    (+15 lines)
legacy-frontend/app.html         (remove <script> tag for D3)
tests/e2e-ui/d3-lazy.spec.js     (NEW)
```

### Time Estimate: 2 hours

---

## B1.3 — Image Asset Optimization (PNG → WebP)

### What

แปลง 6 PNG ใน `legacy-frontend/guide/` (chatgpt-*.png) เป็น WebP
+ keep PNG fallback ผ่าน `<picture>` element

### Why

- chatgpt-6-use.png = 148 KB → WebP ~30 KB (80% smaller)
- Total guide PNGs = 400 KB → ~80 KB
- Faster MCP setup page load

### How

```bash
# Convert
for f in legacy-frontend/guide/chatgpt-*.png; do
  cwebp -q 85 "$f" -o "${f%.png}.webp"
done
```

```html
<!-- app.js HTML render — เปลี่ยน <img> → <picture> -->
<picture>
  <source srcset="/guide/chatgpt-2-settings.webp" type="image/webp">
  <img src="/guide/chatgpt-2-settings.png" alt="..." loading="lazy">
</picture>
```

### Test

```javascript
test('webp variant served when supported', async ({ page }) => {
  const responses = [];
  page.on('response', r => responses.push({ url: r.url(), type: r.headers()['content-type'] }));

  await page.goto('http://127.0.0.1:8000/app#mcp-setup');
  await page.click('[data-tab="chatgpt"]');

  const webpServed = responses.some(r => r.url.includes('chatgpt-') && r.type?.includes('webp'));
  expect(webpServed).toBe(true);
});
```

### Files Touched

```
legacy-frontend/guide/*.webp     (NEW · 6 files)
legacy-frontend/app.js           (6 <img> → <picture> rewrites)
```

### Time Estimate: 2 hours

---

## B1.4 — Extraction Performance Audit + OCR Cache

### What

- Audit `backend/extraction.py` + `backend/processors/*` hotspots
- เพิ่ม OCR result cache (sha256 of PDF → text) ที่ `.ocr_cache/`
- Skip re-OCR ถ้าไฟล์ hash เหมือนเดิม

### Why

- LlamaParse + OCR เป็น cost driver หลัก
- User reprocess ไฟล์เดิม → call LlamaParse ใหม่ทุกครั้ง (waste $$ + time)
- OCR cache pattern เหมือน `.llamaparse_cache/` ที่มีอยู่

### How

```python
# backend/processors/ocr_cache.py (NEW)
import hashlib
from pathlib import Path

CACHE_DIR = Path("data/.ocr_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def get_cached_ocr(file_path: Path) -> str | None:
    """Return cached OCR text ถ้ามี."""
    file_hash = _hash_file(file_path)
    cache_file = CACHE_DIR / f"{file_hash}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    return None

def cache_ocr_result(file_path: Path, text: str) -> None:
    file_hash = _hash_file(file_path)
    cache_file = CACHE_DIR / f"{file_hash}.txt"
    cache_file.write_text(text, encoding="utf-8")
```

```python
# backend/extraction.py — hook ก่อนเรียก Tesseract
def _extract_with_ocr(pdf_path: Path) -> str:
    # Check cache
    cached = ocr_cache.get_cached_ocr(pdf_path)
    if cached is not None:
        logger.info(f"OCR cache hit: {pdf_path.name}")
        return cached

    # Existing OCR logic
    text = _run_tesseract(pdf_path)
    ocr_cache.cache_ocr_result(pdf_path, text)
    return text
```

### Test

```python
# backend/_test_processors.py
def test_ocr_cache_returns_same_result(tmp_path, monkeypatch):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    # First call: runs OCR
    call_count = [0]
    def mock_tesseract(p): call_count[0] += 1; return "extracted text"
    monkeypatch.setattr("backend.extraction._run_tesseract", mock_tesseract)

    text1 = _extract_with_ocr(pdf)
    text2 = _extract_with_ocr(pdf)

    assert text1 == text2 == "extracted text"
    assert call_count[0] == 1, "OCR should be called only once (cached on second)"
```

### Files Touched

```
backend/processors/ocr_cache.py     (NEW ~40 lines)
backend/extraction.py               (~10 lines: hook cache check)
backend/_test_processors.py         (+30 lines)
.gitignore                          (+1 line: data/.ocr_cache/)
```

### Time Estimate: 4 hours

---

## B1.5 — Organizer Parallel Hotspot Audit

### What

- Audit `backend/organizer.py` ที่ใช้ `asyncio.gather` แล้ว (Semaphore 5)
- หา hotspot ที่ยัง sequential (เช่น enrich loop)
- เพิ่ม parallelization where safe

### Why

- v10.0.4 parallel summary แล้ว แต่ enrich/relations อาจยัง sequential
- 100 ไฟล์ × 2s enrich = 200s vs parallel ≈ 40s

### How

```bash
# Find sequential await in organizer
grep -nE "for.*await" backend/organizer.py
# Identify which loops can be gather'd
```

```python
# backend/organizer.py — ตัวอย่าง
# OLD
for file in files:
    await enrich_file(file)

# NEW
sem = asyncio.Semaphore(5)
async def _enrich_with_sem(f):
    async with sem:
        return await enrich_file(f)

await asyncio.gather(*[_enrich_with_sem(f) for f in files])
```

### Test

```python
async def test_enrich_parallel_completes_faster_than_serial(monkeypatch):
    # Mock enrich_file to sleep 1s
    async def slow_enrich(f): await asyncio.sleep(1.0)
    monkeypatch.setattr("backend.organizer.enrich_file", slow_enrich)

    files = [File(id=i) for i in range(10)]

    start = time.monotonic()
    await organize_files_enrich_step(files)
    elapsed = time.monotonic() - start

    # 10 files × 1s = 10s serial, parallel 5 = ~2s
    assert elapsed < 3.0, f"Expected parallel < 3s, got {elapsed}s"
```

### Files Touched

```
backend/organizer.py              (~30 lines refactor)
backend/_test_organizer.py        (+40 lines)
```

### Time Estimate: 4 hours

---

## B1.6 — Upload Worker Concurrency Tuning

### What

- Audit `UPLOAD_WORKER_CONCURRENCY` (default 4)
- Add adaptive throttle: ถ้า memory > 80% → reduce workers
- Add metrics: ขนาด queue + uptime + avg extract time per class

### Why

- Default 4 อาจไม่เหมาะกับ Fly machine size
- ถ้า worker เยอะเกิน → OOM → server crash
- Need adaptive throttle for safety

### How

```python
# backend/upload_worker.py
import psutil

MEMORY_THRESHOLD_PCT = 80

def _get_target_concurrency() -> int:
    """Adaptive: reduce if memory pressure."""
    mem_pct = psutil.virtual_memory().percent
    if mem_pct > MEMORY_THRESHOLD_PCT:
        return max(1, WORKER_CONCURRENCY // 2)
    return WORKER_CONCURRENCY


# Background monitor task
async def _adjust_workers():
    while not _shutdown_event.is_set():
        target = _get_target_concurrency()
        active = len([t for t in _worker_tasks if not t.done()])

        if active > target:
            # Cancel surplus
            for t in _worker_tasks[target:]:
                t.cancel()

        await asyncio.sleep(30)
```

### Test

```python
async def test_workers_scale_down_under_memory_pressure(monkeypatch):
    # Mock high memory
    monkeypatch.setattr("psutil.virtual_memory", lambda: SimpleNamespace(percent=85))

    target = _get_target_concurrency()
    assert target == WORKER_CONCURRENCY // 2
```

### Files Touched

```
backend/upload_worker.py            (~50 lines)
backend/_test_upload_worker.py      (+40 lines)
requirements-fly.txt                (+1 line: psutil)
```

### Time Estimate: 3 hours

---

## B1.7 — Vector Search Index Rebuild Optimization

### What

- ปัจจุบัน `vector_search.py` rebuild TF-IDF index ทุก startup (per memory)
- เพิ่ม `.vector_index_cache` ที่เก็บ pickled TfidfVectorizer + matrix
- Invalidate cache เมื่อ files modified

### Why

- Startup time = O(N_files) × tokenize → ช้าถ้ามี user มากๆ
- Cache = O(1) load + invalidate-on-write

### How

```python
# backend/vector_search.py
CACHE_FILE = Path("data/.vector_index.pkl")

def load_or_rebuild_index():
    if CACHE_FILE.exists() and _cache_valid():
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    index = rebuild_full_index()
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(index, f)
    return index

def invalidate_cache():
    CACHE_FILE.unlink(missing_ok=True)
```

```python
# Hook: invalidate after upload/delete
# In upload_worker.py after successful extract:
vector_search.invalidate_cache()
```

### Test

```python
async def test_index_rebuild_uses_cache():
    # Build index, save cache
    idx1 = await load_or_rebuild_index()

    # Reload (should hit cache)
    start = time.monotonic()
    idx2 = await load_or_rebuild_index()
    elapsed = time.monotonic() - start

    assert elapsed < 0.1, "Cache hit should be fast"
    assert idx1.vocabulary_ == idx2.vocabulary_
```

### Files Touched

```
backend/vector_search.py            (~40 lines)
backend/upload_worker.py            (+2 lines: invalidate hook)
backend/_test_vector_search.py      (NEW ~30 lines)
.gitignore                          (+1: data/.vector_index.pkl)
```

### Time Estimate: 4 hours

---

## B1.8 — Drive Sync Memory Footprint

### What

- Audit `backend/drive_sync.py` — ตอน sync 1000+ ไฟล์ มี memory leak ไหม
- Stream Drive listing แทน load all in memory
- Batch writes ลด DB transaction lock time

### Why

- User BYOS หลายร้อย/พันไฟล์ — sync ครั้งเดียวอาจ OOM
- Memory profiling = key for safety

### How

```python
# backend/drive_sync.py
async def _stream_drive_files(service, folder_id):
    """Generator: yield batches of 100 files."""
    page_token = None
    while True:
        result = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="nextPageToken, files(id, name, modifiedTime)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        yield result.get("files", [])
        page_token = result.get("nextPageToken")
        if not page_token: break

# Use:
async for batch in _stream_drive_files(svc, root_id):
    await _process_batch(batch)  # bounded memory
```

### Test

```python
async def test_drive_sync_bounded_memory(monkeypatch):
    # Mock Drive to return 10K files
    # Measure peak memory during sync
    # Assert < 200MB
    ...
```

### Files Touched

```
backend/drive_sync.py             (~80 lines refactor)
backend/_test_drive_sync.py       (NEW)
```

### Time Estimate: 3 hours

---

## B1.9 — Request A: Login Fail History Cap

### What

ส่ง MSG ใน `for-เขียว-A.md` ขอ cap `_login_fail_history` ใน `backend/main.py`
- ปัจจุบัน in-memory dict — growth ไม่จำกัด
- เพิ่ม LRU cap 10K IPs + TTL 1 hr

**Note:** A's plan A2.1 = login throttle DB persist (ถาวรกว่า). B1.9 = interim cap จนกว่า A2.1 done.

### Why

- Memory leak risk: ถ้า IP rotation attack → dict โต unbounded
- A2.1 จะแก้แบบถาวร (DB persist) แต่ระหว่าง Sprint 1 ต้องมี interim guard

### How

```markdown
### MSG-B-TO-A-002 🆕 Request: cap _login_fail_history (interim)
**From:** เขียว-B
**Date:** 2026-05-17
**Re:** Sprint 1 — coordinate with A2.1 (login throttle DB persist)
**Priority:** P1 (memory safety bridge until A2.1 done)

A — ขอ cap `_login_fail_history` ใน main.py:

```diff
+ from collections import OrderedDict
+
- _login_fail_history: dict = {}
+ _login_fail_history: OrderedDict = OrderedDict()
+ _LOGIN_HISTORY_MAX = 10_000
+ _LOGIN_HISTORY_TTL = 3600  # 1 hour

  def _record_login_fail(ip: str):
      now = time.time()
+     # TTL evict
+     while _login_fail_history:
+         oldest_ip = next(iter(_login_fail_history))
+         if now - _login_fail_history[oldest_ip] < _LOGIN_HISTORY_TTL:
+             break
+         _login_fail_history.pop(oldest_ip)
+     # LRU evict
+     while len(_login_fail_history) >= _LOGIN_HISTORY_MAX:
+         _login_fail_history.popitem(last=False)
      _login_fail_history[ip] = now
+     _login_fail_history.move_to_end(ip)
```

**Reason:** memory leak prevention until A2.1 DB persist replaces in-memory
**Test:** A เพิ่ม test ใน _test_auth.py: spam 11K IPs → dict size ≤ 10K
**ETA from A:** Sprint 1 หรือ Sprint 2 (รวมกับ A2.1)
```

### Files Touched

```
.agent-memory/communication/inbox/for-เขียว-A.md  (+30 lines MSG)
```

### Time Estimate: 5 min (MSG only)

---

## B1.10 — Performance Benchmark Suite

### What

สร้าง `scripts/benchmarks/` พร้อม 3 benchmarks:
- `organize_new_benchmark.py` — measure time for 10/50/100 files
- `upload_benchmark.py` — measure throughput pdf/docx/audio
- `chat_benchmark.py` — measure retrieval + LLM latency p50/p95

### Why

- Currently zero perf baseline
- Need to detect regression after B1.x changes
- ฟ้า will use for sprint review

### How

```python
# scripts/benchmarks/organize_new_benchmark.py
import asyncio, time, httpx, csv

async def benchmark_organize(num_files: int) -> dict:
    """Upload N files → trigger organize → measure end-to-end."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Login
        token = await _login(client)

        # Upload N
        upload_start = time.monotonic()
        for i in range(num_files):
            await _upload(client, token, f"bench-{i}.txt")
        upload_elapsed = time.monotonic() - upload_start

        # Organize-new
        org_start = time.monotonic()
        await client.post("/api/organize-new", headers={"Authorization": f"Bearer {token}"})
        org_elapsed = time.monotonic() - org_start

        return {
            "num_files": num_files,
            "upload_total_s": upload_elapsed,
            "organize_total_s": org_elapsed,
            "upload_per_file_s": upload_elapsed / num_files,
        }

if __name__ == "__main__":
    results = []
    for n in [10, 50, 100]:
        r = asyncio.run(benchmark_organize(n))
        results.append(r)
        print(r)

    # Save CSV
    with open("benchmarks/organize-baseline.csv", "w") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
```

### Test

ตัว benchmark **คือ** test — รัน + verify ผลลัพธ์ stable across runs (CV < 10%)

### Files Touched

```
scripts/benchmarks/organize_new_benchmark.py   (NEW)
scripts/benchmarks/upload_benchmark.py          (NEW)
scripts/benchmarks/chat_benchmark.py            (NEW)
scripts/benchmarks/README.md                    (NEW · how to run)
benchmarks/*.csv                                (output, gitignored)
.gitignore                                      (+1: benchmarks/)
```

### Time Estimate: 1 day

---

## ✅ Sprint 1 Acceptance Gate

1. [ ] Frontend bundle audit + Phase 1 split done · 5+ modules created
2. [ ] D3 lazy load — verify network panel
3. [ ] PNG → WebP done · 80% size reduction verified
4. [ ] OCR cache hit on second run · `.ocr_cache/` populated
5. [ ] Organizer parallel hotspots done · 100 files < 60s
6. [ ] Worker adaptive concurrency · scales down at 80% mem
7. [ ] Vector index cache · startup < 1s when cached
8. [ ] Drive sync streamed · no OOM on 1K+ files
9. [ ] MSG B0.4 + B1.9 — A merged
10. [ ] Benchmark suite runnable · baseline CSV committed
11. [ ] Deploy + smoke test pass
12. [ ] **ส่งฟ้า review** → APPROVED

---

# 🇹🇭 Sprint 2 — Thai-first Quality + Magic Bytes (Days 7-11)

**Goal:** ทำให้ระบบ Thai-first จริง ไม่ใช่แค่ translate UI · เพิ่ม file safety

> รายละเอียดเต็มตามรูปแบบเดียวกัน — ขอย่อให้กระชับเหมือน A Sprint 2

## B2.1 — Thai UI Consistency Audit
- Audit i18n keys: TH coverage 100% vs EN
- Fallback chain: missing TH → EN → key name
- **Files:** `legacy-frontend/app.js` (`I18N` dict), `landing.js`
- **Time:** 4h

## B2.2 — Thai Filename Safety Verify
- v9.4.7 fix 255-byte ext4 limit แล้ว — audit ว่าทุก path ถูก guard
- Test: upload ไฟล์ชื่อยาวมาก + emoji + zero-width chars
- **Files:** `backend/upload_worker.py`, `backend/extraction.py`
- **Time:** 2h

## B2.3 — Thai Search Tokenization
- ปัจจุบัน TF-IDF ใช้ regex tokenizer (split whitespace)
- Thai ไม่มี space → token = whole sentence
- Integrate `PyThaiNLP` `word_tokenize` หรือ `attacut`
- **Files:** `backend/vector_search.py`
- **Time:** 6h

## B2.4 — Thai PDF Extraction Quality Audit
- Compare LlamaParse vs Docling vs Gemini Files API บน 10 Thai PDF
- เลือก default ที่ accuracy ดีที่สุด
- **Files:** `backend/processors/routing.py` (decision logic)
- **Time:** 4h

## B2.5 — Thai Number/Date Locale Formatting
- Frontend: `toLocaleDateString('th-TH')`, Buddhist Era option
- Backend: respond ISO 8601, frontend format
- **Files:** `legacy-frontend/app/utils.js`
- **Time:** 3h

## B2.6 — LLM Prompts Audit (Thai vs English mix)
- Audit `backend/{organizer, retriever, ai_pack_builder, ai_ingest, metadata}.py`
- ทุก system prompt ต้องบอก AI "ตอบเป็นภาษาไทย" ชัดเจน
- **Files:** ~5 files
- **Time:** 4h

## B2.7 — Request A: LLM_MODEL_PRO upgrade
- MSG ใน for-เขียว-A.md ขอเปลี่ยน `LLM_MODEL_PRO` → `gemini-2.5-pro` ใน config.py
- ตอนนี้ใช้ flash temp (ตาม config.py:18 comment)
- **Files:** `for-เขียว-A.md` (+15 lines MSG)
- **Time:** 5 min

## B2.8 — Thai Accessibility (aria-labels + alt text)
- audit `.html` + `.js` template strings
- aria-label / alt ต้องเป็น Thai
- **Files:** `legacy-frontend/*.html`, `app.js`
- **Time:** 3h

## B2.9 — Thai Error Messages Consistency
- Coordinate with A1.1 (unified error) — error.message ต้องเป็น Thai
- Frontend i18n สำหรับ error codes (ERR_FILE_TOO_LARGE → "ไฟล์ใหญ่เกิน...")
- **Files:** `legacy-frontend/app/utils.js`
- **Time:** 3h

## B2.10 — Drive Metadata Thai-safe
- Drive folder names + file names ถูก encode/decode ถูกต้อง
- Audit `backend/drive_sync.py`, `drive_storage.py` (but A owns? — verify ownership)
- **Files:** `backend/drive_oauth.py` + drive_storage.py (B owned)
- **Time:** 2h

## B2.11 — File Magic Bytes Detection (B writes + A integrates)
- เพิ่ม `python-magic` หรือ `filetype` lib
- Verify file extension vs actual content (`.pdf` ต้องเริ่ม `%PDF-`)
- **Files:** `backend/extraction.py` + send MSG ให้ A integrate ใน main.py upload handler
- **Time:** 4h (+coordination)

## B2.12 — Multimodal Thai Audit
- Audio transcription Thai (Gemini Files API)
- Image OCR Thai (Tesseract `tha` lang pack)
- Test: 5 Thai audio + 5 Thai image
- **Files:** `backend/ai_ingest.py`, `backend/processors/local.py`
- **Time:** 4h

## ✅ Sprint 2 Acceptance Gate
ทุก milestone ผ่าน test + ส่งฟ้า review

---

# 🎨 Sprint 3 — Frontend Refactor + CI/CD + Ops (Days 12-16)

**Goal:** Complete frontend architecture · ตอบสนอง A's API changes · CI/CD pipeline

## B3.1 — Frontend Error Contract Integration (per A1.1)
- Frontend parser ใหม่: `{"error": {"code", "message", "request_id"}}`
- Display `request_id` ใน toast error สำหรับ support
- **Files:** `legacy-frontend/app/utils.js` (authFetch error handler)
- **Time:** 2h

## B3.2 — Frontend MCP Credentials Flow (per A1.3)
- เปลี่ยนจาก `/api/me.mcp_secret` → POST `/api/mcp/credentials` (password reauth)
- Add password prompt modal
- **Files:** `legacy-frontend/app/mcp.js`
- **Time:** 3h

## B3.3 — Frontend Pagination (per A1.5)
- Files list + clusters list ใช้ `next_cursor`
- Infinite scroll หรือ "Load more" button
- **Files:** `legacy-frontend/app/fileList.js`
- **Time:** 6h

## B3.4 — Frontend API v1 Migration (per A3.6)
- เปลี่ยน fetch URLs `/api/*` → `/api/v1/*` (with feature flag)
- Grace period: ถ้า /v1/ 404 → fall back /api/
- **Files:** `legacy-frontend/app/utils.js` (authFetch base URL)
- **Time:** 4h

## B3.5 — CI/CD via .github/workflows/
- `lint.yml`: ruff (Python) + eslint (JS) + prettier
- `test.yml`: pytest + playwright on PR
- `deploy.yml`: auto-deploy to staging on merge to master
- **Files:** `.github/workflows/{lint,test,deploy}.yml`
- **Time:** 1 day

## B3.6 — Dockerfile Multi-stage Build
- Stage 1: builder (full deps + compile)
- Stage 2: runtime (slim, only runtime deps)
- Result: smaller image + faster cold start
- **Files:** `Dockerfile`
- **Time:** 3h

## B3.7 — fly.toml Health Probes + Autoscale
- HTTP health check ทุก 10s
- Autoscale min=1 max=3 based on CPU
- **Files:** `fly.toml`
- **Time:** 2h

## B3.8 — Structured Logging + request_id
- Replace `print()` → `logger` everywhere
- JSON log format with `request_id`, `user_id`, `level`
- **Files:** `backend/*.py` (B owned only — A สาง ของ A เอง)
- **Time:** 4h

## B3.9 — Frontend Playwright Regression Suite
- Add 10 critical-path tests:
  upload → organize → chat → graph → MCP setup → BYOS → admin → settings → logout → reset
- **Files:** `tests/e2e-ui/regression-suite.spec.js`
- **Time:** 1 day

## B3.10 — Pre-commit Hook Expansion
- + ruff (auto-format)
- + eslint
- + prettier (CSS/HTML)
- + secret scanner re-verify
- **Files:** `.pre-commit-config.yaml`
- **Time:** 2h

## B3.11 — Frontend Module Split — Phase 2 (Final)
- Complete split started in B1.1
- Add: graph.js, mcp.js, profile.js, billing.js (if restored)
- Document module boundaries
- **Files:** `legacy-frontend/app/*.js`
- **Time:** 2d

## ✅ Sprint 3 Acceptance Gate
- Coverage ≥ 25%
- CI green
- ส่งฟ้า FINAL review

---

# 🧪 Test Infrastructure

## Where Tests Live

```
backend/_test_extraction.py
backend/_test_organizer.py
backend/_test_upload_worker.py
backend/_test_processors.py
backend/_test_vector_search.py
backend/_test_drive_sync.py
backend/_test_embeddings.py        # มีอยู่ (v11 Phase 0)
backend/_test_v11_migration.py     # มีอยู่ (v11 Phase 0)

tests/e2e-ui/xss-injection.spec.js
tests/e2e-ui/module-split.spec.js
tests/e2e-ui/d3-lazy.spec.js
tests/e2e-ui/regression-suite.spec.js
tests/e2e-ui/thai-i18n.spec.js
```

## How to Run

```bash
# All B's backend tests
pytest backend/_test_extraction.py backend/_test_organizer.py \
       backend/_test_upload_worker.py backend/_test_processors.py \
       backend/_test_vector_search.py backend/_test_drive_sync.py -v

# E2E
npx playwright test tests/e2e-ui/

# Coverage (B files)
pytest backend/_test_*.py --cov=backend/extraction --cov=backend/organizer \
       --cov=backend/upload_worker --cov=backend/processors \
       --cov=backend/vector_search --cov-report=term-missing
```

---

# 🤝 Coordination with เขียว-A

## A จะส่ง request ให้ B (มาที่ for-เขียว-B.md):

| When | What | B ทำอะไร |
|------|------|----------|
| Sprint 1 A1.1 | Unified error shape change | B3.1 integrate (Sprint 3 — รอ A เสร็จก่อน) |
| Sprint 1 A1.3 | mcp_secret removed | B3.2 update MCP flow |
| Sprint 1 A1.5 | Pagination spec | B3.3 frontend pagination |
| Sprint 3 A3.6 | API v1 ready | B3.4 migrate URLs |

## B จะส่ง request ให้ A (ผ่าน for-เขียว-A.md):

| When | What | A ทำอะไร |
|------|------|----------|
| Sprint 0 B0.4 | EMBEDDING_MODEL default → gemini-embedding-001 | Merge 1 line (immediate) |
| Sprint 0 B0.5 | Integrate `is_worker_ready()` ใน /api/upload | Add 5-line guard (immediate) |
| Sprint 1 B1.9 | Cap _login_fail_history LRU 10K | รวมกับ A2.1 (Sprint 2) |
| Sprint 2 B2.7 | LLM_MODEL_PRO → gemini-2.5-pro | Merge 1 line |
| Sprint 2 B2.11 | Magic bytes integration ใน upload handler | รวมกับ A1.10 input validation |

**Inbox protocol:**
- เขียนใน `.agent-memory/communication/inbox/for-เขียว-A.md` (B → A)
- A ตอบใน `.agent-memory/communication/inbox/for-เขียว-B.md` (A → B)
- ใช้ MSG ID format `MSG-B-TO-A-NNN` + Reply chain

---

# ⚠️ Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| B0.3 XSS audit miss site → public risk | MED | HIGH | Grep + automated test + ฟ้า review |
| B1.1 module split break existing pages | MED | HIGH | Phased rollout · keep app.js with stubs · regression test |
| B1.4 OCR cache stale (file edited but hash same) | LOW | MED | TTL 30d + manual invalidate endpoint |
| B1.7 vector index cache → stale results | MED | MED | Invalidate on every write + version cache file |
| B2.3 Thai tokenizer breaks existing search | MED | MED | Feature flag + side-by-side test corpus |
| B2.4 LlamaParse default change → cost spike | MED | HIGH | Budget guard via existing LLAMAPARSE_BUDGET_CENTS |
| B3.3 pagination break old clients | MED | MED | Grace period: return both `items` (legacy) + `next_cursor` (new) |
| B3.5 CI flaky → block merges | HIGH | LOW | Mark flaky as `pytest.mark.flaky(reruns=3)` |
| B3.11 final split = massive PR | HIGH | MED | Multiple sub-PRs by domain (one per module) |

---

# 🔵 ฟ้า Review Cadence

| Sprint End | ฟ้า ทำอะไร |
|-----------|-----------|
| **Sprint 0** | Ops smoke: pre-commit hook + gitignore + XSS audit + worker readiness |
| **Sprint 1** | Perf benchmarks · regression check · bundle size verify |
| **Sprint 2** | Thai quality: i18n coverage + tokenization + multimodal test |
| **Sprint 3** | CI/CD verify + Playwright suite + module split regression |
| **FINAL** | UI test ครบ Phase 1-7 + cross-check ทำงานคู่กับ A's final |

---

# ✅ Definition of Done (per milestone)

1. ✅ Code committed + push to `fix/B-sprint-X`
2. ✅ Unit/integration tests pass locally
3. ✅ CI green (after B3.5)
4. ✅ Manual smoke test ผ่าน
5. ✅ Memory file updated (`.agent-memory/current/pipeline-state.md`)
6. ✅ Inbox update — ส่งฟ้า ตอน sprint end
7. ✅ Merge หลัง ฟ้า APPROVED

---

# 📞 Communication Touchpoints

- **Daily:** Self-status update ใน `.agent-memory/current/last-session.md`
- **Inbox check:** ทุกเช้า + ก่อน start milestone (A อาจมี handoff)
- **Sprint end:** ส่ง MSG ให้ฟ้า review ใน `for-ฟ้า.md`
- **Blocker:** ถ้าติด > 2 ชม. ใน 1 milestone → flag ใน inbox + ขอความช่วยเหลือ user/A

---

# 📊 Success Metrics

| Metric | Baseline | Target (End Sprint 3) |
|--------|----------|----------------------|
| P0 findings closed (B scope) | 0 / 12 | 12 / 12 |
| Test coverage (B files) | ~10% | ≥25% |
| Frontend bundle size (app.js) | 6,627 lines | ≤ 1,000 lines (rest in modules) |
| D3.js initial load | 300 KB | 0 KB (lazy) |
| Guide PNG total size | 400 KB | ~80 KB (WebP) |
| OCR re-run cost (cached) | 100% | 0% (cache hit) |
| organize-new 100 files time | unknown (no baseline) | < 60s |
| Thai i18n key coverage | unknown | 100% |
| CI/CD pipelines | 0 | 3 (lint/test/deploy) |
| `print()` in B files | unknown count | 0 (logger replaces) |
| Frontend XSS injection points | unknown | 0 (verified by spec) |

---

**End of plan — เขียว-B รอ user approve ก่อนเริ่ม Sprint 0**

**Last sync:** 2026-05-17 by เขียว-B (Khiao-B) — DRAFT for user review
