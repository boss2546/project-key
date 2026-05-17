# 📬 Inbox: เขียว (Khiao) — นักพัฒนา

> ข้อความที่ส่งถึงเขียว — เขียวอ่านก่อนเริ่มงานทุกครั้ง

## 🔴 New (ยังไม่อ่าน)

_ไม่มี — Phase 1 รอ user decide (stop checkpoint)_

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-V11-PHASE1-REVIEW-RESULT — ✅ APPROVE · Phase 1 Hybrid Clustering

**From:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-17
**Status:** 👁️ Read by เขียว 2026-05-17 — ✅ APPROVE acknowledged · stop checkpoint pending user
**Acknowledgment:**
- 161/161 tests PASS (24+20+42+35+40 = ครบทั้ง Phase 0 + Phase 1)
- 1 LOW finding noted: temp_id collision risk ใน `_llm_label_cluster()` — Phase 2 จะ fix
- 1 INFO: pipeline-state HEAD outdated → updated ใน session แล้ว
- Production: v10.0.19 live + Phase 1 code deployed + flags OFF → behavior unchanged
**Re:** MSG-V11-PHASE1-REVIEW-REQUEST
**Verdict:** ✅ **APPROVED** — pipeline = `stop_checkpoint`

สวัสดีเขียว 🟢

ตรวจสอบ Phase 1 (Hybrid Clustering) ครบแล้ว — **✅ APPROVE**

═══════════════════════════════════════════════════════════════
🧪 ผลการทดสอบสรุป (161/161 PASS)
═══════════════════════════════════════════════════════════════

| Suite | Tests | Result |
|---|---|---|
| Phase 0 regression (`_test_embeddings` + `_test_v11_migration` + `_test_v11_flags`) | 86 | ✅ 86/86 PASS |
| `backend/_test_clustering.py` (ฟ้าเขียน) | 35 | ✅ 35/35 PASS |
| `backend/_test_importance.py` (ฟ้าเขียน) | 40 | ✅ 40/40 PASS |
| **Grand total** | **161** | **✅ 161/161 PASS** |

5 deselected = TestRealAPI (ยัง skip ได้ถูกต้อง — ต้องการ GOOGLE_API_KEY)

═══════════════════════════════════════════════════════════════
📋 Code Review — ผลต่อแต่ละไฟล์
═══════════════════════════════════════════════════════════════

**backend/clustering.py (404 lines) ✅**
- UMAP edge case fix (MSG-V11-UMAP-EDGE-CASE Option A): `N<5` → skip UMAP, `N≥5` → `n_comp = min(UMAP_N_COMPONENTS, max(2, N-2))` — ถูกต้อง, ป้องกัน crash ทุก boundary ✅
- `_compute_centrality()`: noise=0.5, single-member=1.0, centroid=max — logic ถูกต้อง ✅
- `_llm_label_cluster()`: top-3 most-central → prompt → fallback gracefully บน exception ✅
- `cluster_files_hybrid([])` → `{"clusters": []}` early return ✅
- RuntimeError เมื่อ embeddings ไม่มี API key → organizer catch + fallback to legacy ✅
- Output shape ตรงกับ legacy `_cluster_files()` — drop-in compatible ✅

**backend/importance.py (130 lines) ✅**
- 5 factors: text_length(0-40 log) + centrality(0-30) + recency(0-15) + source_of_truth(0-10) + references(0-5) — sum ≤ 100 ✅
- tz-naive `uploaded_at` handled (replace tzinfo=UTC) ✅
- Negative `reference_count` clamped to 0 ✅
- Centrality >1 clamped to 1, <0 clamped to 0 ✅
- `heuristic_score()` shortcut matches full dict ✅

**backend/embeddings.py (LOW findings applied) ✅**
- `empty_indices` dead variable ลบแล้ว ✅
- `EMBEDDING_MODEL` + `EMBEDDING_BATCH_SIZE` import จาก config แล้ว (ไม่ duplicate) ✅
- File verified compiles cleanly (py_compile + pytest) ✅

**backend/organizer.py (routing) ✅**
- `organize_files()` L66: `if USE_HYBRID_CLUSTERING: ... except RuntimeError: fallback` ✅
- `organize_new_files()` L577: same pattern ✅
- Flag default=False → legacy path active → production behavior unchanged ✅

**legacy-frontend/app.js (PHASE_META) ✅**
- 5 new entries: embedding, cluster_math, cluster_label, entity_resolve, community_detect ✅
- ไม่กระทบ existing phases ✅

═══════════════════════════════════════════════════════════════
🔬 Scenarios A/C/D
═══════════════════════════════════════════════════════════════

| Scenario | Method | Result |
|---|---|---|
| A — Production live | `curl /health` → `ok=True, version=10.0.19` + HTTP 200 landing | ✅ PASS |
| C — Edge cases N=0/3/5/50 | `_reduce_dimensions` live + unit tests TestReduceDimensions | ✅ PASS |
| D — Rollback (flag=false) | `USE_HYBRID_CLUSTERING=False` confirmed from config · organizer `else: _cluster_files(files)` at L84, L593 | ✅ PASS |

หมายเหตุ Scenario B (enable flag ใน prod): ต้องใช้ `flyctl secrets set USE_HYBRID_CLUSTERING=true` — user action, ไม่ใช่ QA sandbox สามารถทำได้

═══════════════════════════════════════════════════════════════
🔍 ข้อสังเกต LOW (ไม่ blocking)
═══════════════════════════════════════════════════════════════

1. **[LOW] `temp_id` collision risk** — `f"c_{title[:16].replace(' ', '_')}"` — ถ้า 2 clusters มี title ไทยขึ้นต้นเหมือนกัน 16 chars → temp_id ซ้ำ
   - Impact: cosmetic (temp_id ใช้เป็น frontend key ชั่วคราวเท่านั้น)
   - แนะนำ: เพิ่ม label_id หรือ hash ต่อท้าย เช่น `f"c{label_id}_{title[:12]}"` ใน Phase 2+ cleanup

2. **[INFO] Production at v10.0.19** — เขียวหรือ user deploy Batch 2a (commit `90eb0c8`) ระหว่าง context sessions — ฟ้าตรวจสอบแล้ว: ไม่กระทบ Phase 1 code (separate UX fixes), pipeline-state.md ยัง reference `9c0c655` → เขียวควร update HEAD ใน pipeline-state.md เมื่อ resume

═══════════════════════════════════════════════════════════════
✅ Sign-off Checklist
═══════════════════════════════════════════════════════════════

### Code
- [x] clustering.py: UMAP fix correct + _compute_centrality + _llm_label + fallback shape
- [x] importance.py: 5 factors, sum ≤ 100, label thresholds, edge cases clamped
- [x] embeddings.py: LOW findings applied (dead code + constant consolidation)
- [x] organizer.py: USE_HYBRID_CLUSTERING routing at 2 locations + RuntimeError fallback
- [x] app.js: 5 PHASE_META entries correct

### Tests (ฟ้าเขียน)
- [x] `_test_clustering.py` — 35 tests: _reduce_dimensions N=3/4/5/10/31/50, _compute_centrality, cluster_files_hybrid empty+mock, _llm_label_cluster schema
- [x] `_test_importance.py` — 40 tests: all 5 factors, score range, label thresholds, factor consistency, heuristic_score shortcut
- [x] Phase 0 regression — 86/86 PASS (ไม่มี regression จาก Phase 1)

### Runtime verification
- [x] Production v10.0.19 live ✅ (Phase 1 on master, flags OFF — no behavior change)
- [x] USE_HYBRID_CLUSTERING=False (default) → legacy `_cluster_files()` path active
- [x] cluster_files_hybrid([]) → {"clusters": []} ✅
- [x] UMAP edge cases N=3,5,50 verified (no crash) ✅

รายงานเต็ม: [`reports/v11-phase1-fa-review-2026-05-17.md`](../../../reports/v11-phase1-fa-review-2026-05-17.md)

═══════════════════════════════════════════════════════════════
⏭️ Next Step
═══════════════════════════════════════════════════════════════

**🛑 Stop Checkpoint (per plan Q4 approved)** — ก่อนเริ่ม Phase 2 user ควร:
1. `flyctl secrets set USE_HYBRID_CLUSTERING=true` บน prod (หรือ staging)
2. ทดสอบ organize จริงกับไฟล์ admin user — ดู cluster quality
3. ถ้า quality OK → เริ่ม Phase 2 (Structured Summary)
4. ถ้าต้องการปรับ min_cluster_size หรือ UMAP params → แก้ใน config + redeploy

หรือถ้า user สั่ง "ข้าม checkpoint ทำ Phase 2 ต่อ" → เขียวเริ่ม Phase 2 ได้เลย

**Verdict: ✅ APPROVED · Phase 1 complete · pipeline = stop_checkpoint**

_— 🔵 ฟ้า (Fah), 2026-05-17_

---

### MSG-UX-BATCH1-RESULT — ✅ APPROVE · UX Audit Batch 1 (v10.0.18 commit 082011f)

**From:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-17
**Re:** MSG-UX-BATCH1-001 จากเขียว
**Pipeline state:** `resolved · ux-batch-1`
**Commit tested:** `082011f` · Production: v10.0.18

สวัสดีเขียว 🟢

ตรวจสอบ 4 TC ครบแล้ว — ทั้งหมดผ่าน ✅ APPROVE

═══════════════════════════════════════════════════════════════
🧪 ผลการทดสอบสรุป
═══════════════════════════════════════════════════════════════

| TC | Fix | Method | Result |
|---|---|---|---|
| TC-MCP001 | admin_login hidden from non-admin | API live test (non-admin: 29 tools, no admin_login) + code review | ✅ PASS |
| TC-LP001 | Login modal × | Browser E2E — เปิด modal + ตรวจ ::before + click × | ✅ PASS |
| TC-PROF001 | Profile modal × | Browser E2E — เปิด modal + ตรวจ ::before + click × | ✅ PASS |
| TC-KV001 | Notes → Graph breadcrumb | jsdom 12/12 unit tests + code review | ✅ PASS |
| TC-MCP002 | URL masked + reveal + copy | Browser E2E — ตรวจ DOM + toggle + source review | ✅ PASS |

═══════════════════════════════════════════════════════════════
📋 รายละเอียดแต่ละ TC
═══════════════════════════════════════════════════════════════

**TC-MCP001** — admin_login ซ่อนจาก non-admin ✅
- Non-admin user (peradol.ch@gmail.com) → `/api/mcp/info` → 29 tools, ไม่มี `admin_login` ✅
- `TOOL_REGISTRY` มี 30 tools รวม `admin_login` ✅
- Code review: `is_admin_user` path → all 30 tools; else → filter `ADMIN_ONLY_TOOL_NAMES` ✅
- หมายเหตุ: Admin browser test (bossok2546@gmail.com) ทำผ่าน code review — production OAuth credential ไม่มีใน QA sandbox

**TC-LP001 + TC-PROF001** — Modal × ✅
- Login modal (`#auth-modal`): `::before { content: "×" }` = 24px ✅, no `&times;` double ✅, click × → closed ✅
- Register modal (tab สมัครสมาชิก): `::before { content: "×" }` = 24px ✅, no double ✅, click × → closed ✅
- Profile modal: `::before { content: "×" }` = 24px ✅, no double ✅, click × → closed ✅
- ตรวจ 3 modals ครบ — ไม่มี ×× ในทุก modal ✅

**TC-KV001** — Notes → Graph breadcrumb ✅ (12/12 jsdom tests)
- T1: `sessionStorage.pdb_graph_from` = `"notes"` หลัง `showNodeInGraph()` จาก Notes tab ✅
- T2-T3: `switchPage("graph")` + `state.localNodeId` set ✅
- T4-T7: `_renderGraphBreadcrumb()` สร้าง `#graph-breadcrumb` + button "← กลับไป Notes" + insert before page-header ✅
- T8-T10: click back → `sessionStorage` cleared + `switchPage("knowledge")` + breadcrumb removed ✅
- T11: negative — ไม่มี flag → ไม่มี breadcrumb ✅
- T12: negative — `showNodeInGraph()` จาก non-Notes page → ไม่ set sessionStorage ✅
- หมายเหตุ: Browser E2E ทำผ่าน jsdom (prod auth ไม่มีใน QA sandbox) — logic ครบถ้วน

**TC-MCP002** — URL masked + reveal + copy ✅
- `#mcp-url-value` แสดง `https://personaldatabank.fly.dev/mcp/sAQs…13cU` (มี `…`) ✅
- `dataset.fullUrl` = full URL, `dataset.showingFull = "0"` ✅
- `title = "คลิกเพื่อแสดงเต็ม"`, `cursor: pointer` ✅
- Click 1 → full URL, `title = "คลิกเพื่อซ่อนใหม่"`, `showingFull = "1"` ✅
- Click 2 → masked อีกครั้ง (hasDots=true) ✅
- Copy handler: `const url = el?.dataset.fullUrl || el?.textContent` → ใช้ full URL เสมอ (source confirmed) ✅

═══════════════════════════════════════════════════════════════
🔍 ข้อสังเกตเพิ่มเติม (ไม่ใช่ regression · ไม่ blocking)
═══════════════════════════════════════════════════════════════

1. **[LOW] Sidebar version badge แสดง v10.0.14** ทั้งที่ backend เป็น v10.0.18
   - `/health` → `{"version":"10.0.18"}` ✅ (backend ถูกต้อง)
   - Badge ใน DOM ยังเป็น v10.0.14 (browser cache issue)
   - ไม่กระทบ functionality — แนะนำ: เพิ่ม `cache-busting` หรือ fetch version จาก API แทน hardcode
   - Category: cosmetic · defer ถึง Batch 2 ได้

2. **[OUT-OF-SCOPE] close-relation-sidebar ยังไม่มี handler** — เขียวรับทราบแล้วใน known out-of-scope

═══════════════════════════════════════════════════════════════
✅ Sign-off
═══════════════════════════════════════════════════════════════

- [x] TC-MCP001: non-admin filter ทำงาน — API verified (29 tools) + code review
- [x] TC-LP001: Login modal × ปรากฏ + ปิด ได้จริง (browser)
- [x] TC-PROF001: Profile modal × ปรากฏ + ปิด ได้จริง (browser)
- [x] TC-KV001: breadcrumb logic ถูกต้อง — jsdom 12/12 + code review
- [x] TC-MCP002: URL masking ครบ — browser + source review
- [x] ไม่มี regression จาก batch นี้
- [x] Production v10.0.18 ยัง live ✅

รายงานเต็ม: [`reports/ux-batch1-fa-review-2026-05-17.md`](../../../reports/ux-batch1-fa-review-2026-05-17.md)

**Verdict: ✅ APPROVED · pipeline=resolved · UX Batch 1 complete**

_— 🔵 ฟ้า (Fah), 2026-05-17_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-V11-PHASE0-REVIEW-RESULT — ✅ APPROVE Phase 0 (Foundation)

**From:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-17
**Status:** 👁️ Read by เขียว 2026-05-17 — ✅ APPROVE acknowledged, 2 LOW findings noted for Phase 1
**Acknowledgment:**
- 86/86 unit tests PASS, 5/5 E2E PASS — Phase 0 approved
- 2 LOW findings ที่ฟ้าพบ — เขียวจะแก้ใน Phase 1 step ใดก็ได้:
  1. Dead variable `empty_indices` ใน embeddings.py ~บรรทัด 183 → ลบออก
  2. Constant duplication EMBEDDING_MODEL/BATCH_SIZE/MAX_TEXT_CHARS → import จาก config อย่างเดียว
- Phase 1 Step 1.1 (backend/clustering.py) ยัง block — รอ Daeng confirm UMAP edge case fix
**Re:** MSG-V11-PHASE0-REVIEW-REQUEST
**Verdict:** ✅ **APPROVE** — เขียวเริ่ม Phase 1 ได้เลย

---

## 🎯 Verdict: APPROVE

Phase 0 (Foundation) ผ่านการตรวจสอบครบทุก checklist. ไม่มี blocker. มีข้อสังเกต LOW severity 2 รายการที่เขียวแก้ได้ใน Phase 1 หรือ defer ได้โดยไม่กระทบ production.

---

## 📋 Code Review Summary

### ✅ Step 0.1 — requirements-fly.txt + Dockerfile
- 6 deps เพิ่มถูกต้อง (numpy, scikit-learn, hdbscan, umap-learn, networkx, python-louvain) พร้อม comments
- Dockerfile build-essential + gfortran install → pip → purge = image lean ✓
- Pattern ตรงกับ v10.0.x Dockerfile convention ✓

### ✅ Step 0.2 — backend/embeddings.py (364 lines)
- Docstring มี "Plan reference" ✓, type hints ครบ ✓, Thai comments อธิบาย WHY ✓
- Lazy init pattern (`_init_attempted`) + graceful degrade (no crash ถ้าไม่มี API key) ✓
- `encode_vector`/`decode_vector` float32 ↔ bytes roundtrip ถูกต้อง ✓
- Cache logic ใน `embed_files`: content_hash + embedding_model match → use cached BLOB ✓

**🔍 ข้อสังเกต LOW (ไม่ blocking):**
1. `empty_indices` variable (ประมาณบรรทัด 183-186) ถูก define แต่ไม่ได้ใช้ → dead code เล็กน้อย แนะนำลบใน Phase 1 cleanup
2. `EMBEDDING_MODEL` + `EMBEDDING_BATCH_SIZE` define ทั้งใน `embeddings.py` และ `config.py` → duplication design smell แนะนำให้ `embeddings.py` import จาก `config` อย่างเดียว (Phase 1)

### ✅ Step 0.3 — backend/database.py schema migration
- Pattern additive-only ตรงกับ v7.5.0 (ห้าม DROP/RENAME — ✓)
- 11 columns ใน 4 ตาราง: `files` (3) + `file_summaries` (3) + `clusters` (3) + `graph_nodes` (2) ✓
- Per-table try/except → graceful partial failure ✓
- Index `idx_files_embedding_hash` สร้างถูก ✓
- ตรวจสอบด้วย unit test: idempotent (2nd run = 0 "Added:" messages), defaults ถูกต้อง ✓

### ✅ Step 0.4 — backend/config.py feature flags
- 3 phase flags default OFF: `USE_HYBRID_CLUSTERING=False`, `USE_STRUCTURED_SUMMARY=False`, `USE_ENTITY_GRAPH=False` ✓
- 2 safety flags default ON: `USE_SUMMARY_CACHE=True`, `USE_ORGANIZE_CHECKPOINT=True` ✓
- `_env_bool()` whitelist: `true/True/TRUE/1/yes/YES` → True; ทุกอื่น → False (รวม `on`, `2`, `enabled`) ✓
- Numeric defaults: EMBEDDING_BATCH_SIZE=50, HDBSCAN_MIN_CLUSTER_SIZE=2 (Q2 approved), UMAP_N_COMPONENTS=30, SUMMARY_CONCURRENCY=5 ✓

### ✅ Step 0.5 — scripts/test_organize_quality.py (382 lines)
- `--baseline / --v11 / --compare / --user-id / --limit / --output-dir` argparse ✓
- `Metrics.start() / .stop() / .to_dict()` class ✓
- No args → exit 1 ✓
- ยังไม่มี clustering/summary/graph calls (placeholder ถูกต้อง — Phase 1 add) ✓

---

## 🧪 Unit Test Results

```
python -m pytest backend/_test_embeddings.py backend/_test_v11_migration.py backend/_test_v11_flags.py -v -k "not TestRealAPI"
```

| Test file | Tests | Result |
|---|---|---|
| `_test_embeddings.py` | 24 | ✅ 24/24 PASS |
| `_test_v11_migration.py` | 20 | ✅ 20/20 PASS |
| `_test_v11_flags.py` | 42 | ✅ 42/42 PASS |
| **Total** | **86** | **✅ 86/86 PASS** |

TestRealAPI: 5 deselected (skipped — ต้องใช้ GOOGLE_API_KEY จริง, defer ถึง Phase 1 deploy)

**หมายเหตุ Debug:** ระหว่างเขียน `_test_v11_flags.py` เจอ 2 ปัญหาเล็กน้อยที่แก้แล้ว:
- `importlib.reload()` ต้องใช้แทน `del sys.modules[...]` (Python package attribute cache issue)
- ไฟล์ truncated กลางคัน (Windows/Linux mount encoding) → append ส่วนที่หายไปผ่าน bash

---

## 🌐 Browser E2E Regression (prod v10.0.18)

Base URL: `https://personaldatabank.fly.dev`

| Scenario | Result | หมายเหตุ |
|---|---|---|
| A — Landing page loads | ✅ PASS | title ✓, hero ✓, JS errors = 0 ✓ |
| B — Admin login | ✅ PASS | login 200, `/api/admin/me` 200, is_admin=true ✓ |
| C — /app loads + file checks | ✅ PASS | files API 200, extraction-partial badges = 0 ✓, #btn-organize-new ✓, storage-mode-section visible ✓ |
| D — Rate-limit (v10.0.14) | ✅ PASS | 5× 401 → ครั้งที่ 6 = 429 + Thai message ✓ |
| E — 10 API endpoints | ✅ PASS | 10/10 status 200, max latency 362ms (< 500ms) ✓ |

**Scenario E latency detail:**
```
✅ 200 276ms /api/auth/me
✅ 200 275ms /api/drive/status
✅ 200 273ms /api/upload-status
✅ 200 302ms /api/unprocessed-count
✅ 200 294ms /api/stats
✅ 200 268ms /api/usage
✅ 200 264ms /api/organize-status
✅ 200 362ms /api/files?kind=all
✅ 200 307ms /api/clusters
✅ 200 266ms /api/healthz/queue
```

**Production version confirmed:** `v10.0.18` (via `/api/mcp/info`) — ไม่มี v11 code path active ✓

---

## ✅ Sign-off Checklist

### Code quality
- [x] backend/embeddings.py: docstring ครบ + type hints + thai comments อธิบาย WHY
- [x] backend/database.py: migration block follows v7.5.0 pattern (additive-only)
- [x] backend/config.py: flag naming consistent (USE_X) + comments อธิบาย rollout
- [x] scripts/test_organize_quality.py: argparse + clear output paths

### Tests written (ฟ้าเขียน)
- [x] `backend/_test_embeddings.py` — 24 tests (encode/decode + graceful degrade + real API skip-if)
- [x] `backend/_test_v11_migration.py` — 20 tests (ALTER ADD + idempotency + legacy intact + defaults)
- [x] `backend/_test_v11_flags.py` — 42 tests (defaults + parsing + numeric override + env override)
- [x] Browser E2E regression — 5 scenarios on prod ✓

### Behavior verification
- [x] 3 phase flags default OFF / 2 safety flags default ON
- [x] Schema migration runs cleanly (86-test suite green)
- [x] Idempotent (2nd run = 0 "Added:") — unit tested
- [x] Legacy data integrity — unit tested
- [x] embeddings.py graceful degrade (no API key) — unit tested
- [x] End-to-end regression — all 5 scenarios PASS

### Production safety
- [x] Production v10.0.18 running + untouched (feature flags all OFF)
- [x] Phase 0 commits on master — ready to push after this APPROVE
- [x] Rate-limit regression confirmed working (5→429)

---

## 🔧 Recommended Fixes (ไม่ blocking Phase 1)

เขียวแก้ได้ใน Phase 1 step ใดก็ได้ หรือ defer ถึง Phase 4 Polish:

1. **[LOW] Dead variable `empty_indices`** ใน `backend/embeddings.py` ~บรรทัด 183-186
   - ถูก define แต่ไม่ได้ใช้ → `del empty_indices` หรือลบออก

2. **[LOW] Constant duplication** `EMBEDDING_MODEL` + `EMBEDDING_BATCH_SIZE` ใน embeddings.py และ config.py
   - แนะนำ: ให้ `embeddings.py` import จาก `config.py` อย่างเดียว
   - `from .config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_TEXT_CHARS`

---

## 📌 Outstanding (Phase 0 ไม่กระทบ — อยู่ใน plan แล้ว)

1. **MSG-V11-UMAP-EDGE-CASE** → แดงต้อง confirm fix ก่อน Phase 1 Step 1.1
2. **TestRealAPI** → defer ถึง Phase 1 (ต้องมี GOOGLE_API_KEY บน server)
3. **Docker build verification** → ทำผ่าน Fly remote build ตอน Phase 1 deploy

---

**ฟ้า อนุมัติ Phase 0 แล้ว — เขียวเริ่ม Phase 1 ได้เลย 🟢**

_— 🔵 ฟ้า (Fah), 2026-05-17_

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-UXUI-AUDIT-2026-05-16 — UX/UI Audit Phase 3-4 (Production v10.0.11)

**From:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-16
**Status:** 👁️ Read by เขียว 2026-05-17 — **Backlog (not blocking v11.0.0)**
**Acknowledgment:** เขียวอ่านครบแล้ว · จะแก้หลัง v11.0.0 Phase 0+1 เสร็จ (priority: medium UX, not P0)

**Original report:**

จากการตรวจสอบระบบ PDB บน Production (`https://personaldatabank.fly.dev/`) ในพาร์ทที่ 3 และ 4 (Knowledge, AI, Ecosystem & Mobile) พบว่าระบบมีความเสถียรในเชิงเทคนิค แต่ยังมีจุดที่ต้องปรับปรุงเรื่อง **"Micro-UX"** และ **"Touch Targets"** ในโหมด Mobile

#### Action Items (Backlog หลัง v11.0.0)

**1. Mobile Navigation & Spacing (High Priority)**
- ปุ่ม **"TH | EN"**, **"โปรไฟล์"**, **"ออกจากระบบ"** ชิดกันเกินไป → miss-click logout
- ข้อเสนอแนะ: เพิ่ม `padding-y` หรือ `gap` ระหว่างรายการเมนู + ทำให้ปุ่ม Logout มีสีแดงจางๆ

**2. Touch Target Optimization**
- ปุ่ม "การกระทำเพิ่มเติม" (⋮) ใน Mobile เล็กเกินไป (< 44px)
- ข้อเสนอแนะ: ขยายขอบเขตการคลิกของปุ่ม ⋮

**3. AI Chat Navigation Friction**
- การสลับหน้าไปยัง "AI แชท" บางครั้งใช้เวลานาน, Input ไม่ปรากฏทันที
- ข้อเสนอแนะ: ตรวจ State Management ของ Chat render + เพิ่ม Loading Indicator

**4. Managed Mode Clarity**
- ไอคอน 🗄️ ควรเพิ่ม Tooltip

#### หมายเหตุของเขียว
- เขียวรับทราบ — บันทึกเป็น UX backlog
- ทำหลัง v11.0.0 Phase 0+1 เสร็จ (ป้องกัน CSS conflict กับ frontend changes ใน Phase 1.4 — community badge + phase metadata)
- ไม่ block งาน refactor ปัจจุบัน

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

_ไม่มี_
