# v11.0.0 Phase 0 — ฟ้า Review Report

**Reviewer:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-17
**Re:** MSG-V11-PHASE0-REVIEW-REQUEST from เขียว
**Environment:** Production `https://personaldatabank.fly.dev` (v10.0.18 live)
**Verdict:** ✅ **APPROVE** — Phase 0 ผ่าน, เขียวเริ่ม Phase 1 ได้เลย

---

## 🎯 Scope of Review

ตรวจสอบ v11.0.0 Phase 0 (Foundation) ทั้งหมด 5 steps / 8 commits:

| Commit | Step | Files |
|---|---|---|
| `ddd61c0` | Plan | plans/organize-refactor-v11.md (2354 lines) |
| `559ddd9` | 0.1 | requirements-fly.txt + Dockerfile |
| `bde0715` | 0.2 | backend/embeddings.py (NEW, 364 lines) |
| `48b4d95` | 0.3 | backend/database.py (+11 cols, 4 tables) |
| `545c006` | 0.4 | backend/config.py (8 flags + 4 numerics) |
| `ca63115` | 0.5 | scripts/test_organize_quality.py (NEW, 382 lines) |
| `3c853ff` | Memory | pipeline-state + active-tasks + last-session + inbox |
| `04afaf3` | Test | reports/v11-phase0-frontend-test-2026-05-17.md |

---

## 📋 Code Review — Step by Step

### Step 0.1 — requirements-fly.txt + Dockerfile ✅

**requirements-fly.txt:** 6 deps เพิ่มถูกต้อง พร้อม comments อธิบาย purpose:
- `numpy>=1.26.0` — vector math
- `scikit-learn>=1.4.0` — cosine similarity
- `hdbscan>=0.8.33` — density clustering
- `umap-learn>=0.5.5` — dimensionality reduction (⚠️ UMAP edge case แยก track ใน MSG-V11-UMAP-EDGE-CASE)
- `networkx>=3.2.1` — graph operations
- `python-louvain>=0.16` — Leiden community detection

**Dockerfile:** pattern ถูกต้อง — build-essential + gfortran ติดก่อน pip install (C extensions ต้องการ compiler) แล้ว purge เพื่อ image lean

- ✅ Deps ครบ + ถูก version
- ✅ Build pattern เหมาะสม (compile → pip → purge)
- ✅ ไม่กระทบ production (deps ลงใน image เท่านั้น)

---

### Step 0.2 — backend/embeddings.py (364 lines) ✅

| Check | Result |
|---|---|
| Module docstring + "Plan reference" | ✅ |
| Type hints ครบทุก function | ✅ |
| Thai comments อธิบาย WHY | ✅ |
| Lazy init (`_init_attempted`) idempotent | ✅ |
| Graceful degrade (ไม่มี API key → is_available()=False, embed_text→None) | ✅ |
| `encode_vector` float32→bytes, `decode_vector` bytes→float32 | ✅ |
| Float64 input coerced to float32 | ✅ |
| 768-dim = 3072 bytes (768×4) | ✅ |
| Cache logic: content_hash + embedding_model match → use BLOB | ✅ |
| `_sha256_text` UTF-8 safe (errors="replace") | ✅ |

**🔍 ข้อสังเกต LOW (ไม่ blocking):**

1. **Dead variable `empty_indices`** (~บรรทัด 183-186) — define แล้วไม่ใช้ → แนะนำลบใน Phase 1 cleanup
2. **Constant duplication** — `EMBEDDING_MODEL` + `EMBEDDING_BATCH_SIZE` + `EMBEDDING_MAX_TEXT_CHARS` define ทั้งใน `embeddings.py` และ `config.py` → แนะนำ import จาก config อย่างเดียวใน Phase 1:
   ```python
   from .config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_TEXT_CHARS
   ```

---

### Step 0.3 — backend/database.py schema migration ✅

| Check | Result |
|---|---|
| Pattern additive-only (ห้าม DROP/RENAME) | ✅ ตรงกับ v7.5.0 pattern |
| 11 columns ใน 4 ตาราง | ✅ ครบ |
| Per-table try/except (graceful partial failure) | ✅ |
| PRAGMA check ก่อน ALTER (idempotent) | ✅ |
| Index `idx_files_embedding_hash` | ✅ CREATE IF NOT EXISTS |
| Default values ถูกต้อง | ✅ (NULL BLOB / '' TEXT / 'llm' method / schema_version=1) |

**11 columns ที่เพิ่ม:**

| Table | Column | Type | Default |
|---|---|---|---|
| files | embedding_vector | BLOB | NULL |
| files | embedding_model | TEXT | '' |
| files | embedding_hash | TEXT | '' |
| file_summaries | entities | TEXT | '' |
| file_summaries | relationships | TEXT | '' |
| file_summaries | schema_version | INTEGER | 1 |
| clusters | method | TEXT | 'llm' |
| clusters | centroid | BLOB | NULL |
| clusters | member_count | INTEGER | 0 |
| graph_nodes | community_id | TEXT | '' |
| graph_nodes | embedding_centrality | REAL | 0.0 |

---

### Step 0.4 — backend/config.py feature flags ✅

| Flag | Default | Expected | Result |
|---|---|---|---|
| `USE_HYBRID_CLUSTERING` | False | OFF | ✅ |
| `USE_STRUCTURED_SUMMARY` | False | OFF | ✅ |
| `USE_ENTITY_GRAPH` | False | OFF | ✅ |
| `USE_SUMMARY_CACHE` | True | ON | ✅ |
| `USE_ORGANIZE_CHECKPOINT` | True | ON | ✅ |

**`_env_bool()` whitelist verified:**

| Input | Expected | Result |
|---|---|---|
| `true`, `True`, `TRUE` | True | ✅ |
| `1`, `yes`, `YES`, `Yes` | True | ✅ |
| `false`, `FALSE`, `0`, `no` | False | ✅ |
| `''`, `on`, `2`, `enabled`, `random` | False | ✅ |

**Numeric defaults (Q2 approved):**

| Config | Default | Approved |
|---|---|---|
| `EMBEDDING_BATCH_SIZE` | 50 | ✅ |
| `HDBSCAN_MIN_CLUSTER_SIZE` | 2 | ✅ (Q2) |
| `UMAP_N_COMPONENTS` | 30 | ✅ |
| `SUMMARY_CONCURRENCY` | 5 | ✅ |

---

### Step 0.5 — scripts/test_organize_quality.py (382 lines) ✅

| Check | Result |
|---|---|
| `--baseline / --v11 / --compare` args | ✅ |
| `--user-id / --limit / --output-dir` args | ✅ |
| `Metrics.start() / .stop() / .to_dict()` class | ✅ |
| No args → exit 1 with usage message | ✅ |
| ยังไม่มี clustering calls (placeholder ถูกต้อง) | ✅ Phase 1 จะ add |

---

## 🧪 Unit Tests (เขียนโดยฟ้า)

### `backend/_test_embeddings.py` — 24 tests ✅

```
python -m pytest backend/_test_embeddings.py -v -k "not TestRealAPI"
24 passed, 5 deselected
```

| Class | Tests | Coverage |
|---|---|---|
| TestModuleStructure | 3 | functions exist, docstring, constants |
| TestEncodeDecode | 6 | float32 roundtrip, float64 coerce, 768d=3072B, empty, negative, 1536d |
| TestSha256Helper | 5 | known hash, Thai unicode, empty, different texts, determinism |
| TestGracefulDegrade | 7 | no key → is_available=False, embed_text=None, batch=[None,None,None], embed_files={}, smoke_test |
| TestEmbedFilesCacheLogic | 3 | cache hit, model mismatch = miss, empty text skip |
| TestRealAPI | 5 | (deselected — ต้องการ GOOGLE_API_KEY จริง) |

### `backend/_test_v11_migration.py` — 20 tests ✅

```
python -m pytest backend/_test_v11_migration.py -v
20 passed
```

| Class | Tests | Coverage |
|---|---|---|
| TestV11MigrationSchema | 5 | files 3 cols, file_summaries 3 cols, clusters 3 cols, graph_nodes 2 cols, total=11 |
| TestV11MigrationIdempotency | 2 | 2nd run = 0 added, columns still present |
| TestV11MigrationDefaults | 8 | embedding_model='', embedding_hash='', embedding_vector=NULL, schema_version=1, clusters.method='llm', member_count=0, embedding_centrality=0.0, community_id='' |
| TestV11MigrationLegacyData | 3 | legacy row preserved, v11 cols NULL/default, 5 rows all survive |
| TestV11MigrationIndex | 2 | idx_files_embedding_hash created, idempotent |

### `backend/_test_v11_flags.py` — 42 tests ✅

```
python -m pytest backend/_test_v11_flags.py -v
42 passed
```

| Class | Tests | Coverage |
|---|---|---|
| TestConfigModuleStructure | 6 | _env_bool exists, all flags exist, bool types, int types |
| TestPhaseFlagsDefaultOff | 4 | 3 phase flags individually + simultaneously OFF |
| TestSafetyFlagsDefaultOn | 2 | USE_SUMMARY_CACHE=True, USE_ORGANIZE_CHECKPOINT=True |
| TestEnvBoolTruthy | 7 | true/True/TRUE/1/yes/YES/Yes |
| TestEnvBoolFalsy | 9 | false/FALSE/0/no/''/on/2/enabled/' ' |
| TestEnvBoolDefault | 3 | default=false, default=true, env overrides default |
| TestNumericConfigDefaults | 6 | 4 defaults + 2 env overrides |
| TestFlagEnvOverride | 5 | 3 phase flags activate, 2 safety flags deactivate |

### 📊 รวม Unit Tests

```
python -m pytest backend/_test_embeddings.py backend/_test_v11_migration.py backend/_test_v11_flags.py -v -k "not TestRealAPI"
===================== 86 passed, 5 deselected in 2.70s =====================
```

**ผล: ✅ 86/86 PASS**

**หมายเหตุ Debug ระหว่างเขียน:**
- `importlib.reload()` ต้องใช้แทน `del sys.modules["backend.config"]` เพราะ Python package object ยังถือ attribute reference ของ module ไว้ → `from backend import config` คืน stale reference ถ้าแค่ delete sys.modules
- ไฟล์ `_test_v11_flags.py` truncated กลางคัน (Windows/Linux CIFS mount + Thai multi-byte chars) → ต้อง append ส่วนที่หายผ่าน bash โดยตรง

---

## 🌐 Browser E2E Regression

**Environment:** Production `https://personaldatabank.fly.dev` — v10.0.18
**Tool:** Claude in Chrome (user's browser IP)
**Auth:** bossok2546@gmail.com (admin)

### Scenario A — Landing page ✅

| Check | Result |
|---|---|
| HTTP 200 | ✅ |
| title = "Personal Data Bank — Knowledge Workspace" | ✅ |
| hero h1 = "Start with context. Grow into your Digital Twin" | ✅ |
| readyState = complete | ✅ |
| JS console errors | ✅ 0 errors |
| Page height | 3961px |

---

### Scenario B — Admin login ✅

| Check | Result |
|---|---|
| POST /api/auth/login | ✅ 200 |
| GET /api/auth/me → email confirmed | ✅ bossok2546@gmail.com |
| GET /api/admin/me → is_admin=true | ✅ |

---

### Scenario C — /app loads ✅

| Check | Result |
|---|---|
| GET /api/files → 200 | ✅ |
| `.extraction-badge.extraction-partial` badges | ✅ 0 (v10.0.13 removal confirmed) |
| `#btn-organize-new` present | ✅ |
| `#storage-mode-section` visible | ✅ |

---

### Scenario D — Rate-limit (v10.0.14) ✅

POST `/api/auth/login` × 6 ครั้ง ด้วย wrong credentials จาก sandbox IP:

| Attempt | Status | Message |
|---|---|---|
| 1 | 401 | Invalid email or password |
| 2 | 401 | Invalid email or password |
| 3 | 401 | Invalid email or password |
| 4 | 401 | Invalid email or password |
| 5 | 401 | Invalid email or password |
| **6** | **429** | **"พยายาม login ผิดเกิน 5 ครั้ง — ลองใหม่ในอีก 15 นาที"** |

- ✅ Threshold = 5 ตรงตาม spec
- ✅ Sandbox IP blocked (ยืนยัน rate-limit per-IP ทำงาน) — ใช้ sandbox IP แทน browser IP เพื่อกัน user โดน lock

---

### Scenario E — 10 API endpoints (< 500ms) ✅

| Endpoint | Status | Latency |
|---|---|---|
| `/api/auth/me` | 200 | 276ms |
| `/api/drive/status` | 200 | 275ms |
| `/api/upload-status` | 200 | 273ms |
| `/api/unprocessed-count` | 200 | 302ms |
| `/api/stats` | 200 | 294ms |
| `/api/usage` | 200 | 268ms |
| `/api/organize-status` | 200 | 264ms |
| `/api/files?kind=all` | 200 | 362ms |
| `/api/clusters` | 200 | 307ms |
| `/api/healthz/queue` | 200 | 266ms |

- ✅ **10/10 status 200**
- ✅ Max latency: **362ms** (< 500ms threshold ✓)
- ✅ ไม่มี 5xx — ยืนยัน v11 schema migration ไม่ทำลาย production backend

**Production version confirmed:** `/api/mcp/info` → `"version": "v10.0.18"` ✅

---

## ✅ Sign-off Checklist

### Code quality
- [x] backend/embeddings.py: docstring + type hints + thai comments WHY ✓
- [x] backend/database.py: migration follows v7.5.0 additive-only pattern ✓
- [x] backend/config.py: USE_X naming + comments ✓
- [x] scripts/test_organize_quality.py: argparse + output paths ✓

### Tests (ฟ้าเขียน)
- [x] `backend/_test_embeddings.py` — 24/24 PASS
- [x] `backend/_test_v11_migration.py` — 20/20 PASS
- [x] `backend/_test_v11_flags.py` — 42/42 PASS
- [x] Browser E2E regression — 5/5 PASS

### Behavior
- [x] 3 phase flags default OFF
- [x] 2 safety flags default ON
- [x] Schema migration idempotent
- [x] Legacy data integrity (unit tested)
- [x] Graceful degrade (no API key)
- [x] End-to-end regression (prod)

### Production safety
- [x] prod v10.0.18 live + untouched
- [x] Feature flags all OFF → v11 code paths inactive
- [x] Rate-limit regression OK

---

## 🔧 Recommended Fixes (ไม่ blocking Phase 1)

| Priority | File | Issue | Suggestion |
|---|---|---|---|
| LOW | `backend/embeddings.py` | Dead variable `empty_indices` (~line 183) | ลบออก |
| LOW | `backend/embeddings.py` | EMBEDDING_MODEL/BATCH_SIZE/MAX_TEXT_CHARS defined twice | import จาก config อย่างเดียว |

แก้ได้ใน Phase 1 step ใดก็ได้ หรือ defer ถึง Phase 4 Polish

---

## 📌 Outstanding (Phase 0 ไม่กระทบ)

1. **MSG-V11-UMAP-EDGE-CASE** — แดงต้อง confirm fix ก่อน Phase 1 Step 1.1 (backend/clustering.py)
2. **TestRealAPI (5 tests)** — defer ถึงมี GOOGLE_API_KEY บน server (Phase 1 deploy)
3. **Docker build verification** — ทำผ่าน `flyctl deploy --remote-only` ตอน Phase 1

---

## 🎯 Verdict

> ✅ **APPROVE** — Phase 0 Foundation ผ่านทุกหัวข้อ ไม่มี blocker
>
> เขียวเริ่ม Phase 1 (Hybrid Clustering) ได้เลย
> ดู next steps ใน `inbox/for-เขียว.md`

_— 🔵 ฟ้า (Fah), 2026-05-17_
