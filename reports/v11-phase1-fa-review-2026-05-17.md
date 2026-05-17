# 🔵 QA Report — v11.0.0 Phase 1 Review (Hybrid Clustering)

**Reviewer:** 🔵 ฟ้า (Fah) — นักตรวจสอบ  
**Date:** 2026-05-17  
**Re:** MSG-V11-PHASE1-REVIEW-REQUEST จาก 🟢 เขียว (Khiao)  
**Commits reviewed:** `b3542b3` (Phase 1 code · feat(v11-phase1)) + prior ฟ้า-LOW-fix commits  
**Production URL:** https://personaldatabank.fly.dev  
**Production version:** v10.0.19 (confirmed via `/health`)  
**Verdict:** ✅ **APPROVED · pipeline = review_passed · stop_checkpoint**

---

## 🎯 Scope — Phase 1 Deliverables Reviewed

| Deliverable | Description |
|---|---|
| `backend/clustering.py` | Main hybrid clustering pipeline (404 lines) |
| `backend/importance.py` | Deterministic importance scoring (130 lines) |
| `backend/embeddings.py` | Updated: LOW findings from Phase 0 applied |
| `backend/organizer.py` | Feature flag routing at 2 locations + fallback |
| `legacy-frontend/app.js` | 5 new PHASE_META entries |
| `backend/_test_clustering.py` | **NEW** — ฟ้าเขียน (35 tests) |
| `backend/_test_importance.py` | **NEW** — ฟ้าเขียน (40 tests) |

---

## 🧪 Test Results Summary

```
pytest backend/_test_embeddings.py backend/_test_v11_migration.py \
       backend/_test_v11_flags.py backend/_test_clustering.py \
       backend/_test_importance.py -v -k "not TestRealAPI"
```

| Suite | Tests | Result |
|---|---|---|
| `_test_embeddings.py` (Phase 0) | 24 | ✅ 24/24 PASS |
| `_test_v11_migration.py` (Phase 0) | 20 | ✅ 20/20 PASS |
| `_test_v11_flags.py` (Phase 0) | 42 | ✅ 42/42 PASS |
| `_test_clustering.py` (**Phase 1 · ฟ้าเขียน**) | 35 | ✅ 35/35 PASS |
| `_test_importance.py` (**Phase 1 · ฟ้าเขียน**) | 40 | ✅ 40/40 PASS |
| **Grand Total** | **161** | **✅ 161/161 PASS** |

5 deselected = TestRealAPI (requires GOOGLE_API_KEY — defer to Phase 2 deploy)  
0 failures · 0 errors

---

## 📋 Code Review — File by File

### backend/clustering.py ✅

**Architecture:** embed → UMAP reduce → HDBSCAN → centrality → LLM label (parallel, sem=3) → legacy shape

**UMAP edge case fix (MSG-V11-UMAP-EDGE-CASE Option A) — VERIFIED:**

```python
def _reduce_dimensions(vectors, n_samples):
    if n_samples < 5:                              # skip UMAP entirely
        return vectors
    n_comp = min(UMAP_N_COMPONENTS, max(2, n_samples - 2))   # dynamic n_comp
    reducer = umap.UMAP(n_components=n_comp, metric="cosine",
                        random_state=42, n_neighbors=min(15, n_samples-1))
    return reducer.fit_transform(vectors)
```

| N | Expected n_comp | Verified |
|---|---|---|
| 3 | skip UMAP (raw 768-d) | ✅ _test_clustering.py test_n3_* |
| 4 | skip UMAP (raw 768-d) | ✅ test_n4_* |
| 5 | 3 | ✅ test_n5_correct_n_comp + test_n5_no_exception |
| 10 | 8 | ✅ test_n10_correct_n_comp |
| 31 | 29 | ✅ test_n31_correct_n_comp |
| 50 | 30 (full) | ✅ test_n50_uses_full_umap_n_components |

**`_compute_centrality()` — VERIFIED:**
- noise (label=-1) → 0.5 neutral ✅ (test_noise_points_exactly_0_5)
- single-member cluster → 1.0 ✅ (test_single_member_cluster_is_1)
- point at centroid → 1.0, edges → 0.0 ✅ (test_centroid_has_highest_centrality_in_cluster)
- all values in [0.0, 1.0] ✅ (test_values_in_0_1)

**`cluster_files_hybrid()` — VERIFIED:**
- `[]` → `{"clusters": []}` (early return) ✅
- embeddings_available()=False → RuntimeError → organizer catches + falls back ✅
- all embed fail → `{}` → `{"clusters": []}` ✅
- output schema: temp_id, title, summary, files[] with all 6 fields ✅
- all input files accounted in output (no drops, no duplicates) ✅
- importance_score in [0,100], importance_label in {high,medium,low} ✅

**`_llm_label_cluster()` — VERIFIED:**
- LLM result propagated to title/summary ✅
- LLM exception → graceful fallback (filename-based title, schema intact) ✅
- most-central file (highest centrality) → is_primary=True ✅
- relevance = float in [0,1] ✅

---

### backend/importance.py ✅

**Factor breakdown verified (all factor tests pass):**

| Factor | Range | Key test |
|---|---|---|
| text_length (log scale) | 0-40 | 1000 chars = 30 pts ✅; 0 chars = 0 ✅; capped at 40 ✅ |
| centrality | 0-30 | cent=0 → 0 ✅; cent=1 → 30 ✅; cent=0.5 → 15 ✅; clamped ✅ |
| recency | 0-15 | <7d → 15 ✅; >365d → 0 ✅; 30d → linear decay ✅ |
| source_of_truth | 0 or 10 | True → 10 ✅; False → 0 ✅ |
| references | 0-5 | 0 → 0 ✅; 2 → 1 ✅; 100 → 5 (capped) ✅; negative → 0 ✅ |

**Additional robustness verified:**
- tz-naive `uploaded_at` → no crash (UTC assumed) ✅
- `uploaded_at=None` → neutral 7.5 recency ✅
- factor sum ≈ score (±1 rounding tolerance) ✅
- all factor values are int ✅
- `heuristic_score()` shortcut == full dict score ✅

---

### backend/embeddings.py ✅ (LOW findings from Phase 0 applied)

| Finding | Fix | Verified |
|---|---|---|
| `empty_indices` dead variable | Removed (comment: v11.0.0-fix) | ✅ pytest passes |
| EMBEDDING_MODEL/BATCH_SIZE duplication | `from .config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE` | ✅ py_compile OK + 86 Phase 0 tests green |

---

### backend/organizer.py ✅

**Routing verified at 2 locations:**

```python
# organize_files() L64-84
from .config import USE_HYBRID_CLUSTERING
if USE_HYBRID_CLUSTERING:
    from .clustering import cluster_files_hybrid
    try:
        clusters_data = await cluster_files_hybrid(files, ...)
    except RuntimeError as e:
        logger.warning(...)
        clusters_data = await _cluster_files(files)  # legacy fallback
else:
    clusters_data = await _cluster_files(files)       # default path
```

Same pattern at `organize_new_files()` L575-593. Double safety: flag=False → legacy; flag=True but no API key → RuntimeError → legacy. ✅

---

### legacy-frontend/app.js ✅

5 new PHASE_META entries verified (L343-348):

```javascript
embedding:        {th: 'วิเคราะห์ความคล้าย', en: 'Computing similarity', icon: '🧮'},
cluster_math:     {th: 'จัดกลุ่มด้วยคณิตศาสตร์', en: 'Math clustering', icon: '📐'},
cluster_label:    {th: 'ตั้งชื่อกลุ่ม', en: 'Labeling clusters', icon: '🏷'},
entity_resolve:   {th: 'รวมเอนทิตี้', en: 'Resolving entities', icon: '🔗'},
community_detect: {th: 'หา community', en: 'Detecting communities', icon: '🕸️'},
```

Existing phases untouched. ✅

---

## 🌐 Scenario Tests

### Scenario A — Production Health ✅

```
curl https://personaldatabank.fly.dev/health
→ {"ok":true,"version":"10.0.19"}

curl -I https://personaldatabank.fly.dev/
→ HTTP 200
```

Note: Production upgraded to v10.0.19 (Batch 2a UX fixes: version badge sync, LP-004 admin redirect, close-relation-sidebar handler) — separate from Phase 1, no interference.

### Scenario C — Edge Cases (N=0/3/5/50) ✅

All tested via unit tests + live `_reduce_dimensions()` call:

```python
N=3: input=(3,768) output=(3,768)  # UMAP skipped ✓
N=5: output=(5,3)  expected=(5,3)   # n_comp=3 ✓
N=50: output=(50,30) expected=(50,30) # full n_comp=30 ✓
cluster_files_hybrid([]) → {"clusters": []}  # early return ✓
```

### Scenario D — Rollback Verification ✅

```python
from backend.config import USE_HYBRID_CLUSTERING
# → False  (default, confirmed)

# organizer.py L83-84:
else:
    clusters_data = await _cluster_files(files)  # legacy always active
```

Production organize behavior: unchanged from v10.0.x. Flag activation requires explicit `flyctl secrets set USE_HYBRID_CLUSTERING=true`.

---

## 🔍 Findings

### [LOW] temp_id collision risk in `_llm_label_cluster`

- **What:** `f"c_{title[:16].replace(' ', '_')}"` — ถ้า 2 clusters มี Thai title ขึ้นต้น 16 chars เหมือนกัน → temp_id ซ้ำ
- **Impact:** cosmetic only (temp_id ใช้เป็น frontend key ชั่วคราว — ไม่ persist ใน DB)
- **Suggestion:** ใน Phase 2+ ปรับเป็น `f"c{label_id}_{title[:12]}"` เพื่อ guarantee uniqueness
- **Severity:** LOW · ไม่ blocking

### [INFO] pipeline-state.md HEAD stale

- `pipeline-state.md` reference master HEAD = `9c0c655` แต่ actual HEAD = `90eb0c8` (v10.0.19)
- อัปเดตแล้วใน context session นี้ ✅

---

## ✅ Sign-off Checklist

### Code
- [x] clustering.py: UMAP fix ถูกต้องทุก boundary
- [x] clustering.py: _compute_centrality logic ถูกต้อง (noise, single, centroid)
- [x] clustering.py: _llm_label_cluster output schema + fallback ถูกต้อง
- [x] clustering.py: cluster_files_hybrid output shape == legacy drop-in
- [x] importance.py: 5 factors ถูกต้อง, sum ≤ 100, label thresholds ถูกต้อง
- [x] embeddings.py: ทั้ง 2 LOW findings จาก Phase 0 แก้แล้ว
- [x] organizer.py: routing + fallback ที่ 2 locations ถูกต้อง
- [x] app.js: 5 PHASE_META entries ถูกต้อง

### Tests (ฟ้าเขียน — Phase 1)
- [x] `_test_clustering.py` — 35/35 PASS
- [x] `_test_importance.py` — 40/40 PASS
- [x] Phase 0 regression — 86/86 PASS (ไม่มี regression)
- [x] Grand total — 161/161 PASS

### Runtime
- [x] Production v10.0.19 live ✅
- [x] USE_HYBRID_CLUSTERING=False → legacy path active ✅
- [x] UMAP edge cases verified ✅

---

## 📊 Test Coverage Summary

**`_test_clustering.py` (35 tests):**
- `TestReduceDimensions` (8): N=3,4,5,10,31,50 + no_crash + row_count_preserved
- `TestComputeCentrality` (7): range, noise=0.5, all_noise, single=1.0, centroid=1.0, output_len, two_clusters
- `TestClusterFilesHybridEmpty` (2): empty → {"clusters": []}, key check
- `TestClusterFilesHybridMocked` (7): schema, fields, all_files_accounted, scores_in_range, labels_valid, no_api_key_error, all_embed_fail
- `TestLlmLabelCluster` (11): required_keys, entry_fields, title_propagated, llm_failure_fallback, primary_correct, score_range, relevance_float, labels_valid, all_files_output

**`_test_importance.py` (40 tests):**
- `TestScoreRange` (4): min/max/mid inputs in range, score is int
- `TestLabelThresholds` (4): high≥70, low<40, medium range, consistency
- `TestFactors` (18): text_length (4), centrality (5), recency (4), source_of_truth (2), references (4), tz handling (1)
- `TestFactorConsistency` (5): sum_low, sum_high, sum_mid, all_keys, all_ints
- `TestReturnStructure` (3): keys, label_string, label_valid
- `TestHeuristicScore` (4): returns_int, matches_full_dict, in_range, default_centrality

---

**🔵 ฟ้า (Fah) อนุมัติ Phase 1 แล้ว — pipeline = stop_checkpoint ✅**

_ดูผลกลับใน `inbox/for-เขียว.md` (MSG-V11-PHASE1-REVIEW-RESULT)_

_— 🔵 ฟ้า (Fah), 2026-05-17_
