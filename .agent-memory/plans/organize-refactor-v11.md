# Plan: v11.0.0 — Organize Pipeline Refactor (Production-Grade Hybrid Clustering + Structured Summary + Entity Graph)

**Author:** แดง (Daeng)
**Date:** 2026-05-17
**Status:** `draft` — รอ user approve
**Foundation:** master HEAD (v10.0.14 deployed live ที่ `https://personaldatabank.fly.dev`)
**Target version:** **11.0.0** (major bump — design overhaul; behavior-compatible behind feature flags)
**Effort:** เขียว ~8-12 วัน (split 4 phases) + ฟ้า ~2-3 วัน = **~10-15 วัน total**
**Risk:** 🟠 **HIGH-MEDIUM** — pipeline-wide refactor, 51+ touchpoints, แต่มี feature flag rollback + additive schema

---

## 🎯 Goal

แก้ปัญหา **องค์รวมของ `/api/organize-new`**: ปัจจุบันพังเมื่อ user อัพไฟล์ 50-100 ไฟล์แล้วกดจัดระเบียบ. Refactor เป็น production-grade architecture ตามมาตรฐานตลาด 2026 (BERTopic + RAPTOR + Microsoft GraphRAG patterns)

**ผู้ใช้จะได้รับ:**

1. **Scale**: รองรับ 1,000-10,000 ไฟล์ (เดิมพังที่ ~50)
2. **เร็วขึ้น**: 100 ไฟล์ใช้ 5-15 นาที (เดิม 30-90 นาที, เร็วขึ้น 6-9 เท่า)
3. **ถูกลง**: AI bill ลด 10 เท่า (~$2-5/run → ~$0.20-0.50/run)
4. **เสถียร**: success rate 95% → 99.5%, crash recovery via checkpoint
5. **Quality**:
   - Cluster deterministic (กดสองครั้งได้ผลเดิม)
   - Knowledge graph มี community detection
   - Chat retrieval ครอบคลุมกว่าเดิม (entity-based + relationship-based search)
   - `.md` files มี Entities + Relationships sections → port ไป Obsidian/Logseq ได้

**Developer จะได้รับ:**

- Code path เก่ายังอยู่ครบ — feature flag ปิดเปิด, rollback ทันที
- Schema additive 100% — ไม่มี breaking migration
- Test harness side-by-side (เก่า vs ใหม่)
- 51+ touchpoints documented + ระบุไฟล์/บรรทัดทุกจุด

---

## 📚 Context

### ทำไมต้อง refactor ตอนนี้

User รายงานว่าอัพไฟล์ 50-100 ไฟล์แล้วกดจัดระเบียบ → **ค้าง/พัง/ไม่ทำงาน**. หลังวิเคราะห์เจอว่าดีไซน์ปัจจุบันมีปัญหาเชิงสถาปัตยกรรม 3 จุดใหญ่ที่ผิดมาตรฐานตลาด:

#### Bottleneck #1 — ขั้น CLUSTER (organizer.py:249-306)
**ของเดิม**: ส่งทุกไฟล์ (8K chars × N files) ให้ LLM ใน 1 call → ขอให้ AI จัดกลุ่ม+ตั้งชื่อ+ให้คะแนน

**ที่ผิด**:
- เกิน context window ของ Gemini Flash (32K) เมื่อ ≥ 50 ไฟล์
- Cost O(N) tokens ต่อ re-cluster
- Non-deterministic (กดซ้ำได้ผลต่าง)
- ทำ 3 งานพร้อมกัน (จัด+ตั้งชื่อ+ให้คะแนน) → accuracy drop
- LLM-as-clusterer คือ **anti-pattern** ในงานวงการ NLP

**มาตรฐานตลาด** (BERTopic, Dropbox Dash, OpenAI cookbook, RAPTOR):
1. Embed ไฟล์ทั้งหมด (batch call → vector 1536-d)
2. UMAP reduce dimensionality (1536 → 30-d เพื่อเลี่ยง curse of dimensionality)
3. HDBSCAN density-based clustering (auto-detect k, marks outliers)
4. LLM label เฉพาะกลุ่ม (1 call ต่อ 1 cluster) — ส่งแค่ 3-5 ตัวอย่างต่อ cluster

#### Bottleneck #2 — ขั้น SUMMARY + ENRICH (organizer.py:309 + metadata.py:14)
**ของเดิม**: 2 LLM calls ต่อไฟล์ — call 1 ทำ summary, call 2 ดึง tags/aliases/sensitivity

**ที่ผิด**:
- ส่งไฟล์เดิมให้ AI อ่าน 2 รอบ → cost 2× ที่ควรเป็น 1×
- 100 ไฟล์ = 200 calls แทนที่จะเป็น 100
- การแยก context ลำดับชั้น ทำให้ AI ไม่ได้ใช้ holistic understanding ของไฟล์

**มาตรฐานตลาด** (LangChain, LlamaIndex PropertyGraphIndex, RAPTOR):
- 1 LLM call ต่อไฟล์ + **structured output**
- JSON schema ดึง: summary + key_topics + key_facts + entities + relationships + tags
- ใช้ Gemini JSON mode เพื่อ enforce schema → parse fail < 0.1%

#### Bottleneck #3 — ขั้น KNOWLEDGE GRAPH (graph_builder.py + relations.py:177)
**ของเดิม**: heuristic suggestions + (theoretically) LLM per pair = O(N²)

**ที่ผิด**:
- 100 ไฟล์ = 10,000 คู่ → 10,000 LLM calls (ในความจริงไม่เคยทำเต็มเพราะแพง → graph ออกมา sparse)
- Entity เดียวกัน ชื่อต่างกัน = 2 node ("MTL" vs "เมืองไทยประกันชีวิต" vs "Muang Thai Life")
- ไม่มี community detection → user เห็น web of edges มั่ว

**มาตรฐานตลาด** (Microsoft GraphRAG 2024-2026):
1. ดึง entities + relationships ระหว่าง chunk-by-chunk (1 call/chunk หรือ 1 call/file ใน v11 รวม Bottleneck #2)
2. Entity dedup ด้วย name + embedding similarity → merge homonyms
3. Build NetworkX graph → run **Leiden community detection** (python-louvain)
4. LLM ใช้แค่ summarize community
5. Cost: O(chunks) ไม่ใช่ O(N²)

### Industry references

- **BERTopic**: https://maartengr.github.io/BERTopic/ (BERT embeddings + UMAP + HDBSCAN — de-facto standard)
- **RAPTOR**: arXiv:2401.18059 — recursive clustering + summarization (ICLR 2024)
- **Microsoft GraphRAG**: https://microsoft.github.io/graphrag/ — entity extraction + Leiden communities
- **LangChain Map-Reduce + Refine**: https://python.langchain.com/docs/tutorials/summarization/
- **LlamaIndex PropertyGraphIndex**: structured-output entity extraction
- **Anthropic Message Batches / OpenAI Batch API**: 50% cheaper สำหรับ async-tolerant work

### Performance / Quality เทียบเทียบ (target)

| Metric | ของเดิม (v10.0.14) | ของใหม่ (v11.0.0) | Improvement |
|---|---|---|---|
| **เวลา 100 ไฟล์** | 30-90 นาที | 5-15 นาที | **6-9×** |
| **LLM calls / organize 100 ไฟล์** | ~10,000+ | ~110 | **90×** |
| **AI cost / organize 100 ไฟล์** | ~$2-5 USD | ~$0.20-0.50 | **10×** |
| **Memory peak** | 400-600 MB | 80-120 MB | **5×** |
| **Network LLM** | 50-100 MB | 5-10 MB | **10×** |
| **Scale max** | ~50 ไฟล์ (พังเกินนั้น) | 1,000-10,000 ไฟล์ | **20-200×** |
| **Concurrent users** | 1-2 | 10-20 | **10×** |
| **Cluster determinism** | ❌ Non-deterministic | ✅ Deterministic | — |
| **Cluster accuracy** | 70% (mood-based) | 80% (HDBSCAN+label) | +10% |
| **Cluster outlier detection** | ❌ ไม่มี | ✅ HDBSCAN noise label | — |
| **Summary completeness** | 95% | 99% | +4% |
| **Summary fidelity (no halluc.)** | 90% | 95% | +5% |
| **Entity extraction** | ❌ ไม่มี | ✅ มี (avg 5-15/file) | — |
| **Graph density** | 30% (sparse) | 90% (rich) | **3×** |
| **Graph communities** | 0 (ไม่มี) | 5-8 (Leiden) | — |
| **Chat retrieval coverage** | 70% | 90% | +20% |
| **Importance score** | Subjective | Explainable | — |
| **Crash recovery** | 0% (restart from 0) | ~95% (resume) | — |
| **Success rate (organize)** | ~95% | ~99.5% | +4.5% |
| **JSON parse fail rate** | ~2% | <0.1% | **20×** better |

### สิ่งที่ user คาดหวัง (จาก discussion)

1. **คุณภาพ > ความเร็ว** — ทำดีตั้งแต่แรก, อย่ารีบ, อย่าตัด corner
2. **ครอบคลุม 100%** — รวมทุกจุดที่คุยมา, ทุกไฟล์ที่กระทบ, แม้เล็กน้อยก็เก็บ
3. **อนุญาตใช้ token เต็มที่** — quality cost คุ้มกว่าทำพังต้องแก้

---

## 📁 Files to Create / Modify

### Backend — Create (4 ไฟล์ใหม่)

- [ ] **`backend/embeddings.py`** (create) — Embedding service
  - `embed_text(text: str) -> np.ndarray` — wrap Gemini text-embedding API
  - `embed_files(files: list[File]) -> dict[str, np.ndarray]` — batch embed, cached
  - `embed_text_batch(texts: list[str], batch_size=50) -> list[np.ndarray]` — batch helper
  - Cache strategy: ดูใน File.embedding_hash + content_hash, skip ถ้าตรง
  - Storage: numpy float32 → bytes → File.embedding_vector (LargeBinary BLOB)

- [ ] **`backend/clustering.py`** (create) — Hybrid clustering module
  - `cluster_files_hybrid(files: list[File], min_cluster_size=2) -> dict` — main entry
  - `_reduce_dimensions(vectors: np.ndarray, n_components=30) -> np.ndarray` — UMAP wrapper
  - `_run_hdbscan(reduced: np.ndarray, min_cluster_size: int) -> np.ndarray` — clusterer
  - `_compute_centrality(vectors, labels) -> dict[file_id, float]` — embedding centrality per file
  - Output shape: เหมือน `_cluster_files()` เดิม (drop-in replacement) — `{"clusters": [{"title", "summary", "files": [...]}]}`

- [ ] **`backend/importance.py`** (create) — Deterministic importance scorer
  - `heuristic_importance(f: File, centrality: float = 0.5, refs: int = 0) -> dict`
  - Factors: text_length (log-scale), embedding_centrality, recency (uploaded_at), source_of_truth_flag, reference_count
  - Returns: `{"score": int 0-100, "label": "high"|"medium"|"low", "factors": {...}}` (explainable)

- [ ] **`backend/entity_resolver.py`** (create) — Entity deduplication
  - `resolve_entities(db, user_id) -> dict[canonical_name, EntityInfo]`
  - Strategy:
    1. Collect all FileSummary.entities → flat list
    2. Group by lowercase name (exact match)
    3. Union aliases
    4. For similar names (Levenshtein < 3 OR cosine-sim of name embedding > 0.9): merge
  - Returns: `{canonical_name: {type, aliases, file_ids, embedding}}`

### Backend — Modify (12 ไฟล์)

- [ ] **`backend/config.py`** (modify) — Feature flags + version bump
  - Bump `APP_VERSION = "11.0.0"` (after final phase done) — ระหว่างทาง bump เป็น 11.0.0-alpha.X
  - Add feature flags (default OFF for safety):
    ```python
    USE_HYBRID_CLUSTERING = os.getenv("USE_HYBRID_CLUSTERING", "false").lower() == "true"
    USE_STRUCTURED_SUMMARY = os.getenv("USE_STRUCTURED_SUMMARY", "false").lower() == "true"
    USE_ENTITY_GRAPH = os.getenv("USE_ENTITY_GRAPH", "false").lower() == "true"
    USE_SUMMARY_CACHE = os.getenv("USE_SUMMARY_CACHE", "true").lower() == "true"  # safe default ON
    USE_ORGANIZE_CHECKPOINT = os.getenv("USE_ORGANIZE_CHECKPOINT", "true").lower() == "true"
    ```
  - Embedding model config:
    ```python
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-text-embedding-001")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))  # Gemini default
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
    ```
  - HDBSCAN config:
    ```python
    HDBSCAN_MIN_CLUSTER_SIZE = int(os.getenv("HDBSCAN_MIN_CLUSTER_SIZE", "2"))
    UMAP_N_COMPONENTS = int(os.getenv("UMAP_N_COMPONENTS", "30"))
    ```

- [ ] **`backend/database.py`** (modify) — Schema additions (additive only)
  - File model add:
    - `embedding_vector = Column(LargeBinary, default=None)` (numpy float32 bytes)
    - `embedding_model = Column(String(64), default="")` (e.g. "gemini-text-embedding-001")
    - `embedding_hash = Column(String(64), default="")` (content_hash when embedded, for cache invalidation)
  - FileSummary model add:
    - `entities = Column(Text, default="")` (JSON list[{type, name, aliases}])
    - `relationships = Column(Text, default="")` (JSON list[{from, to, type, evidence}])
    - `schema_version = Column(Integer, default=1)` (1=legacy, 2=structured)
  - Cluster model add:
    - `method = Column(String(32), default="llm")` ("llm" | "hdbscan")
    - `centroid = Column(LargeBinary, default=None)` (cluster center vector for re-cluster delta)
    - `member_count = Column(Integer, default=0)`
  - GraphNode model add:
    - `community_id = Column(String(64), default="")` (Leiden community label)
    - `embedding_centrality = Column(Float, default=0.0)` (0-1, distance from community center)
  - **Migration code**: ใน `init_db()` migration block (pattern เดียวกับ v7.5.0 [database.py:807-832](../../backend/database.py#L807-L832))
    - ALTER TABLE files ADD COLUMN embedding_vector BLOB
    - ALTER TABLE files ADD COLUMN embedding_model TEXT DEFAULT ''
    - ALTER TABLE files ADD COLUMN embedding_hash TEXT DEFAULT ''
    - ALTER TABLE file_summaries ADD COLUMN entities TEXT DEFAULT ''
    - ALTER TABLE file_summaries ADD COLUMN relationships TEXT DEFAULT ''
    - ALTER TABLE file_summaries ADD COLUMN schema_version INTEGER DEFAULT 1
    - ALTER TABLE clusters ADD COLUMN method TEXT DEFAULT 'llm'
    - ALTER TABLE clusters ADD COLUMN centroid BLOB
    - ALTER TABLE clusters ADD COLUMN member_count INTEGER DEFAULT 0
    - ALTER TABLE graph_nodes ADD COLUMN community_id TEXT DEFAULT ''
    - ALTER TABLE graph_nodes ADD COLUMN embedding_centrality REAL DEFAULT 0.0
  - **CRITICAL**: ใช้ `try/except OperationalError` แต่ละ ALTER (column อาจมีแล้วถ้า rerun)

- [ ] **`backend/organizer.py`** (modify) — Pipeline routing + new functions
  - Section 1: `_cluster_files()` (line 249-306) — เก็บไว้, เพิ่ม `_cluster_files_hybrid()` คู่กัน
  - Section 2: `organize_files()` (line 17-246) — เพิ่ม feature flag routing:
    ```python
    from .config import USE_HYBRID_CLUSTERING, USE_STRUCTURED_SUMMARY, USE_ENTITY_GRAPH
    
    if USE_HYBRID_CLUSTERING:
        from .clustering import cluster_files_hybrid
        clusters_data = await cluster_files_hybrid(files, min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE)
    else:
        clusters_data = await _cluster_files(files)
    ```
  - Section 3: `organize_new_files()` (line 513-650+) — เพิ่ม routing เดียวกัน
  - Section 4: `_generate_summary()` (line 309-322) — แตกเป็น v1 (เดิม) + v2 (structured):
    ```python
    async def _generate_summary(file, cluster_title, importance) -> dict:
        from .config import USE_STRUCTURED_SUMMARY
        if USE_STRUCTURED_SUMMARY:
            return await _generate_summary_v2(file, cluster_title, importance)
        return await _generate_summary_v1(file, cluster_title, importance)  # legacy path
    ```
  - Section 5: เพิ่ม `_generate_summary_v2()` (structured output) — เพิ่ม fields: entities, relationships, tags
  - Section 6: เพิ่ม `_generate_summary_mapreduce_v2()` — รวม entities/relationships ของแต่ละ chunk ใน merge step
  - Section 7: เพิ่ม checkpoint logic (Task 4.2)
  - Section 8: เพิ่ม cache check ก่อน LLM call (Task 4.1)

- [ ] **`backend/main.py`** (modify) — Endpoint routing
  - Line 1454-1513 `/api/organize` — เพิ่ม phase metadata ใหม่ใน progress_tracker.report calls
  - Line 1586-1673 `/api/organize-new` — same
  - Line 1494-1495, 1629-1630 — skip `enrich_all_files()` ถ้า `USE_STRUCTURED_SUMMARY=true` (เพราะ tags ได้จาก summary call แล้ว):
    ```python
    if not USE_STRUCTURED_SUMMARY:
        await enrich_all_files(db, current_user.id, force=force)
    ```
  - Line 1499-1501, 1634-1636 — switch generate_suggestions ตาม USE_ENTITY_GRAPH:
    ```python
    if USE_ENTITY_GRAPH:
        from .relations import generate_community_suggestions
        await generate_community_suggestions(db, current_user.id)
    else:
        await generate_suggestions(db, current_user.id)
    ```
  - Line 1676-1690 `/api/organize-status` — return phase ใหม่ (embedding, cluster_math, cluster_label)

- [ ] **`backend/graph_builder.py`** (modify) — Graph v2 with entities + Leiden
  - Line 21-50 `build_full_graph()` — เพิ่ม routing:
    ```python
    async def build_full_graph(db, user_id, force=False):
        from .config import USE_ENTITY_GRAPH
        if USE_ENTITY_GRAPH:
            return await _build_graph_v2(db, user_id, force)
        return await _build_graph_v1(db, user_id, force)  # legacy
    ```
  - เพิ่ม `_build_graph_v2()` — entity resolve + NetworkX graph + Leiden community detection
  - Update GraphNode rows ด้วย community_id + embedding_centrality
  - GraphEdge rows: เพิ่ม edge_type จาก FileSummary.relationships
  - **Dependencies**: import networkx + community (python-louvain) lazily

- [ ] **`backend/relations.py`** (modify) — Add community-based suggestions
  - Line 177-249 `generate_suggestions()` — เก็บไว้เป็น legacy
  - เพิ่ม `generate_community_suggestions(db, user_id)`:
    - Loop GraphNode by community_id
    - LLM call 1 ครั้งต่อ community → label + summary
    - สร้าง SuggestedRelation ที่เชื่อมระหว่าง community
  - **Cost**: ~1 LLM call ต่อ 5-10 communities (เดิม heuristic + LLM ต่อ pair)

- [ ] **`backend/metadata.py`** (modify) — Deprecate enrich_all_files in v2 path
  - Line 110-137 `enrich_all_files()` — เก็บไว้, **ห้ามลบ** จนกว่า v11.1
  - Add comment: "v11.0.0: ขั้นนี้ skipped ถ้า USE_STRUCTURED_SUMMARY=true (tags ได้จาก summary call แล้ว)"
  - Keep `enrich_file_metadata()` สำหรับ standalone enrich (admin re-enrich endpoint)

- [ ] **`backend/markdown_store.py`** (modify) — เพิ่ม sections ใหม่
  - Line 25-90 `write_summary_md()`:
    - เพิ่ม params: `entities: list = None`, `relationships: list = None`, `community_id: str = ""`, `embedding_centrality: float = 0.0`
    - Frontmatter เพิ่ม: `community_id`, `embedding_centrality`, `schema_version: 2`
    - Body เพิ่ม sections:
      - `# Entities` (loop เป็น `- **{type}**: {name} (aliases: ...)` format)
      - `# Relationships` (loop เป็น `- {from} — *{type}* — {to}` format with evidence quote)
      - `# Community` (id + member files)
  - **Backward compat**: parser ใน `read_summary_md()` ยังอ่าน frontmatter เก่าได้ (extra fields default ignored)

- [ ] **`backend/progress_tracker.py`** (modify) — Phase metadata เพิ่ม
  - เพิ่ม comment block อธิบาย phase ใหม่:
    - `embedding` — กำลังคำนวณ embeddings
    - `cluster_math` — กำลังรัน HDBSCAN
    - `cluster_label` — กำลังตั้งชื่อ cluster
    - `entity_resolve` — กำลัง dedup entities
    - `community_detect` — กำลังหา communities
  - **ไม่ต้องเปลี่ยน function signature** — phase string เป็น free-form ใน organizer

- [ ] **`backend/llm.py`** (modify) — เพิ่ม Gemini JSON mode helper (optional)
  - Line 80-118 `call_llm_json()` — เพิ่ม optional param `response_schema: dict = None`
  - ถ้า schema ระบุ → set `response_mime_type: "application/json"` + `response_schema` ใน Gemini config
  - ✅ ได้ JSON parse fail < 0.1% (vs ปัจจุบัน ~2%)
  - **Fallback**: ถ้า schema ระบุแต่ provider ไม่รองรับ → silently ใช้ prompt-based JSON

- [ ] **`backend/vector_search.py`** (modify) — **NO CHANGE to TF-IDF system!**
  - TF-IDF index ยังใช้ต่อสำหรับ chat search (separate from neural embeddings)
  - เพียงเพิ่ม comment ที่หัวไฟล์ระบุว่า embeddings ใหม่อยู่ที่ `embeddings.py` (สำหรับ clustering, ไม่ทับ TF-IDF)
  - **เหตุผล**: TF-IDF เร็ว, lightweight, ดีกับ exact-keyword chat search. Neural embeddings overkill สำหรับ chat search

- [ ] **`backend/duplicate_detector.py`** (modify) — Re-enable + use new embeddings
  - Line 78 `_DEDUP_DISABLED = True` — เปลี่ยนเป็น `False` ใน Phase 4
  - Hook ใช้ embeddings ใหม่ (เร็วกว่า TF-IDF ใน semantic matching)
  - **BACKLOG-009** ในตอนนี้ — ปิดให้สมบูรณ์ใน Phase 4

### Frontend — Modify (2 ไฟล์)

- [ ] **`legacy-frontend/app.js`** (modify) — Phase metadata + file card
  - Line 329-339 `PHASE_META` — เพิ่ม phase ใหม่:
    ```javascript
    const PHASE_META = {
      // เก่า
      starting: {...}, scanning: {...}, clustering: {...},
      enrich: {...}, graph: {...}, suggest: {...}, summary: {...},
      // ใหม่ (v11.0.0)
      embedding: {icon: '🧮', th: 'วิเคราะห์ความคล้าย', en: 'Computing similarity'},
      cluster_math: {icon: '📐', th: 'จัดกลุ่ม', en: 'Grouping'},
      cluster_label: {icon: '🏷️', th: 'ตั้งชื่อกลุ่ม', en: 'Labeling clusters'},
      entity_resolve: {icon: '🔗', th: 'รวมเอนทิตี้', en: 'Resolving entities'},
      community_detect: {icon: '🕸️', th: 'หา community', en: 'Detecting communities'},
    };
    ```
  - Line 2885-2913 file card render — เพิ่ม community badge (ถ้า file.community_id):
    ```javascript
    const communityBadge = f.community_id
      ? `<span class="community-badge" title="${...}">🕸️ ${f.community_id}</span>`
      : '';
    ```
  - Line 321-361 `startOrganizeStatusPoll()` — extend watchdog timeout if เริ่มที่ embedding phase (เพราะ embedding 100+ ไฟล์อาจใช้ 1-2 นาที):
    - `WATCHDOG_PHASE_STALL_MS`: 240s → keep 240s (sufficient for new phases)
    - `WATCHDOG_HARD_LIMIT_MS`: 15min → 20min (allow for 1000+ file scale)
  - Cache buster bump: v10.0.14 → v11.0.0 (รอ alpha → final)

- [ ] **`legacy-frontend/styles.css`** (modify) — Community badge style
  - เพิ่ม `.community-badge` (subtle purple, matching other badges)
  - เพิ่ม `.cluster-method-hdbscan` (optional debug badge for admin)

### Tests (สำหรับฟ้า)

- [ ] **`scripts/test_organize_quality.py`** (create) — A/B comparison harness
  - Load 50/100/200 ไฟล์ตัวอย่างจาก prod DB copy
  - รัน organize 2 รอบ — flag OFF (legacy) + flag ON (v2)
  - เก็บ metrics:
    - Wall-clock time per phase
    - LLM call count + tokens
    - Memory peak (psutil)
    - Cluster count + member distribution
    - Cluster purity (manual ground truth labels)
    - JSON parse success rate
    - .md file structure validation
  - Output: `reports/organize-quality-v11-{timestamp}.md`

- [ ] **`scripts/load_test_organize.py`** (create) — Concurrent users
  - Simulate 5 users × 100 files พร้อมกัน
  - Watch: rate-limit, lock conflicts, memory, DB locks
  - Output: load profile graph

- [ ] **`scripts/migrate_to_v11.py`** (create) — One-time migration
  - คำนวณ embedding ของทุก File ที่ extracted_text != "" และยังไม่มี embedding_vector
  - Batch size 50, sleep 100ms ระหว่าง batch (rate-limit safe)
  - Idempotent — รัน rerun ปลอดภัย
  - Output: count succeeded + failed + estimated cost

- [ ] **`backend/_test_embeddings.py`** (create) — unit tests
- [ ] **`backend/_test_clustering.py`** (create) — unit tests
- [ ] **`backend/_test_importance.py`** (create) — unit tests
- [ ] **`backend/_test_entity_resolver.py`** (create) — unit tests
- [ ] **`backend/_test_organizer_v2.py`** (create) — integration tests with feature flags

### Dependencies

- [ ] **`requirements-fly.txt`** (modify) — Phase 0 additions
  ```
  # v11.0.0 — Hybrid clustering + entity graph
  scikit-learn>=1.4.0      # KMeans fallback + centrality utils
  hdbscan>=0.8.33          # density-based clustering
  umap-learn>=0.5.5        # dimensionality reduction
  networkx>=3.2.1          # graph data structure
  python-louvain>=0.16     # Leiden/Louvain community detection
  ```
  - **Image size impact**: +~80MB (Docker layer)
  - **Build time**: +30s (pip install)
  - **Memory idle**: +10MB

- [ ] **`requirements-local.txt`** (modify ถ้ามี) — same additions

- [ ] **`Dockerfile`** (modify ถ้าจำเป็น) — เช็คว่า hdbscan + umap-learn build ผ่าน (ต้องการ gcc/numpy ก่อน)
  - HDBSCAN ต้อง compile C extension → ระวัง `python:3.11-slim` อาจขาด build tools
  - แก้: ใช้ `python:3.11` (full image) หรือ `apt-get install -y build-essential` ก่อน pip install

### Documentation + Memory

- [ ] **`README.md`** (modify)
  - Architecture section — update organize flow diagram
  - Versions section — bump to 11.0.0
  - New section: "Hybrid Clustering Architecture" — อธิบาย design

- [ ] **`docs/handoff/09-flow-charts.md`** (modify) — Redraw organize flow
  - เก่า: 10-step linear LLM-heavy
  - ใหม่: 7-step hybrid (embed → math → label → extract → resolve → community → suggest)

- [ ] **`docs/handoff/04-architecture-diagrams.md`** (modify) — Update component diagram
  - เพิ่ม embeddings.py, clustering.py, importance.py, entity_resolver.py
  - แสดง relationship กับ vector_search.py (separate concerns)

- [ ] **`.agent-memory/reference_v10_ingestion_pipeline.md`** (memory) — Bump to v11
  - Update with new pipeline architecture
  - Reference Industry standards

- [ ] **`.agent-memory/current/pipeline-state.md`** (memory)
  - Update with "plan_pending_approval" status
  - Reference this plan

- [ ] **`docs/reports/REPORT-v11.0.0.md`** (create) — Release notes
  - Performance comparison table
  - Migration guide for self-hosted users
  - Feature flag rollout instructions

### "Small things" ที่เก็บมาด้วย (จาก discussion)

- [ ] **`backend/config.py`** Line 18 — `LLM_MODEL_PRO = Flash (TEMP)` → กลับเป็น Pro ตอนพร้อม (ปัจจุบัน comment ว่า "TEMP")
- [ ] **`backend/markdown_store.py`** Line 1-10 — Update docstring with v11 schema
- [ ] **`backend/duplicate_detector.py`** Line 78 — `_DEDUP_DISABLED = True` → re-enable in Phase 4
- [ ] **`backend/database.py`** — Audit deprecated columns (e.g. legacy index_status if any) — comment but don't drop
- [ ] **Memory: `.agent-memory/current/active-tasks.md`** — Track this refactor
- [ ] **Memory: `.agent-memory/current/last-session.md`** — Log session
- [ ] **Memory: `.agent-memory/history/session-logs/2026-05-17-แดง.md`** — Session log

**TOTAL: 4 create + 12 modify backend, 2 frontend, 8 tests/scripts, 4 docs, 7 small things, 3 memory = ~40 file touches**

---

## 📡 API Changes

### Endpoint shape: **NO breaking changes**

ทุก endpoint behavior เหมือนเดิม — output schema เพิ่ม fields, ไม่ลบ/เปลี่ยน

### `/api/organize-new` (POST)
**Auth:** Required (JWT)

**Request body:** (no change)
```json
{}
```

**Response 200:** (เพิ่ม optional fields)
```json
{
  "status": "ok",
  "message": "จัดระเบียบไฟล์ใหม่ 50 ไฟล์เรียบร้อย",
  "new_files": 50,
  "graph": {
    "nodes": 35,
    "edges": 142,
    "communities": 6                    ← 🆕 (only when USE_ENTITY_GRAPH=true)
  },
  "duplicates_found": [],
  "method": "hybrid"                    ← 🆕 "hybrid" | "legacy" (debug field)
}
```

**Errors:** (no new codes)
- 403 `QUOTA_EXCEEDED`
- 409 `ORGANIZE_IN_PROGRESS`
- 500 `ORGANIZE_FAILED`

### `/api/organize-status` (GET)
**Response:** เพิ่ม phase ใหม่ใน enum
```json
{
  "running": true,
  "phase": "embedding",                 ← 🆕 valid: embedding|cluster_math|cluster_label|entity_resolve|community_detect|...legacy
  "step_th": "วิเคราะห์ความคล้าย",
  "step_en": "Computing similarity",
  "current": 50,
  "total": 100,
  "history": [...]
}
```

### `/api/files` (GET)
**Response file objects:** เพิ่ม optional fields
```json
{
  "files": [
    {
      "id": "...",
      "filename": "...",
      "community_id": "comm-3",         ← 🆕 (v11)
      "embedding_centrality": 0.85,     ← 🆕 (v11)
      "entities": [...],                ← 🆕 (v11, parsed from FileSummary.entities)
      ...
    }
  ]
}
```

### Internal: `/api/admin/embeddings/recompute` (POST) **🆕 admin only**
**Auth:** Required (admin)

**Request:**
```json
{
  "user_id": "..." | "all",
  "force": false
}
```

**Response 200:**
```json
{
  "status": "ok",
  "files_processed": 234,
  "files_skipped": 12,
  "estimated_cost_usd": 0.05
}
```

---

## 💾 Data Model Changes

### Additions (no deletions, no renames — additive only)

#### `File` table
| Column | Type | Default | Description |
|---|---|---|---|
| `embedding_vector` | LargeBinary (BLOB) | None | numpy float32 bytes (1536-d × 4 bytes = ~6 KB/file) |
| `embedding_model` | String(64) | "" | e.g. "gemini-text-embedding-001" |
| `embedding_hash` | String(64) | "" | content_hash when embedded (cache invalidation key) |

**Storage impact**: 1000 files × 6KB = ~6MB total. SQLite handles BLOB efficiently.

#### `FileSummary` table
| Column | Type | Default | Description |
|---|---|---|---|
| `entities` | Text | "" | JSON list[{type, name, aliases, evidence}] |
| `relationships` | Text | "" | JSON list[{from, to, type, evidence}] |
| `schema_version` | Integer | 1 | 1=legacy, 2=structured |

#### `Cluster` table
| Column | Type | Default | Description |
|---|---|---|---|
| `method` | String(32) | "llm" | "llm" or "hdbscan" |
| `centroid` | LargeBinary | None | cluster center vector |
| `member_count` | Integer | 0 | denormalized for fast queries |

#### `GraphNode` table
| Column | Type | Default | Description |
|---|---|---|---|
| `community_id` | String(64) | "" | Leiden community label |
| `embedding_centrality` | Float | 0.0 | 0-1 — distance to centroid |

### Migration plan

**ใน `init_db()` migration block** ([database.py:807-832](../../backend/database.py#L807-L832)), pattern เดียวกับ v7.5.0 migrations:

```python
# v11.0.0 — Hybrid clustering + structured summary columns
try:
    file_cols_v110 = {row[1] for row in (await conn.execute(text("PRAGMA table_info(files)"))).all()}
    if "embedding_vector" not in file_cols_v110:
        await conn.execute(text("ALTER TABLE files ADD COLUMN embedding_vector BLOB"))
        await conn.execute(text("ALTER TABLE files ADD COLUMN embedding_model TEXT DEFAULT ''"))
        await conn.execute(text("ALTER TABLE files ADD COLUMN embedding_hash TEXT DEFAULT ''"))
        print("  → Added: files.embedding_* columns (v11.0.0)")
except Exception as e:
    print(f"  ⚠️ v11 file migration warning: {e}")

try:
    fs_cols_v110 = {row[1] for row in (await conn.execute(text("PRAGMA table_info(file_summaries)"))).all()}
    if "entities" not in fs_cols_v110:
        await conn.execute(text("ALTER TABLE file_summaries ADD COLUMN entities TEXT DEFAULT ''"))
        await conn.execute(text("ALTER TABLE file_summaries ADD COLUMN relationships TEXT DEFAULT ''"))
        await conn.execute(text("ALTER TABLE file_summaries ADD COLUMN schema_version INTEGER DEFAULT 1"))
        print("  → Added: file_summaries.entities/relationships (v11.0.0)")
except Exception as e:
    print(f"  ⚠️ v11 file_summaries migration warning: {e}")

# ... ทำเดียวกันสำหรับ clusters + graph_nodes
```

**Rollback safety**: ถ้า migration fail บางส่วน → log warning + ทำต่อ (ไม่ raise). Code paths ที่ใช้ column ใหม่ต้อง handle `None` gracefully.

**One-time data backfill**: ใช้ `scripts/migrate_to_v11.py` ระหว่าง maintenance window (~5-10 นาที สำหรับ 200 ไฟล์)

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

> **🎯 ทำตามลำดับ — แต่ละ phase deploy ได้แยก, มี feature flag ปิดได้ทันที**

---

### 📦 Phase 0 — Foundation (1-2 วัน)

> **เป้าหมาย**: ติดตั้ง infrastructure ที่ phase 1-3 ใช้ โดยไม่กระทบ flow ปัจจุบัน. End state: USE_HYBRID_CLUSTERING=false → behavior เหมือน v10.0.14 ทุกประการ

#### Step 0.1 — เพิ่ม dependencies + verify Docker build
1. แก้ `requirements-fly.txt`:
   ```
   scikit-learn>=1.4.0
   hdbscan>=0.8.33
   umap-learn>=0.5.5
   networkx>=3.2.1
   python-louvain>=0.16
   ```
2. แก้ `Dockerfile` (ถ้าจำเป็น) — เพิ่ม `apt-get install -y build-essential` ก่อน pip install (HDBSCAN ต้อง compile C)
3. Build Docker image locally: `docker build -t pdb-v11-test .`
4. ✅ ตรวจ image size diff (เทียบกับเดิม) — บันทึก
5. ✅ Run container + import test: `python -c "import hdbscan, umap, networkx, community; print('ok')"`

#### Step 0.2 — สร้าง `backend/embeddings.py`
1. Create file with:
   - `async def embed_text(text: str) -> np.ndarray` — call Gemini text-embedding API (HTTP via httpx)
   - `async def embed_files(files: list[File]) -> dict[str, np.ndarray]` — batch wrapper with cache
   - `_encode_vector(arr: np.ndarray) -> bytes` / `_decode_vector(b: bytes) -> np.ndarray` — float32 serialization
2. Cache logic:
   ```python
   for f in files:
       if f.embedding_vector and f.embedding_hash == f.content_hash and f.embedding_model == EMBEDDING_MODEL:
           result[f.id] = _decode_vector(f.embedding_vector)  # cache hit
       else:
           to_embed.append(f)  # need fresh embed
   # batch call API for to_embed
   ```
3. **Rate-limit safety**: sleep 100ms ระหว่าง batch (Gemini text-embedding free tier = 1500 RPM)
4. Logging: log batch size + duration + cache hit rate

**🔬 Verify gate (ก่อน step ถัดไป):**
- [ ] `backend/_test_embeddings.py` 4 unit tests pass
- [ ] Manual: embed 3 files → run again → log "cache HIT 3/3"
- [ ] Manual: edit file content → re-embed → log "cache MISS 1/3, embed 1"
- [ ] Manual: rate limit safety — embed 60 files batch → no 429 error from Gemini

#### Step 0.3 — Schema migration (additive)
1. แก้ `backend/database.py`:
   - เพิ่ม columns ใน Class definitions (File, FileSummary, Cluster, GraphNode)
   - เพิ่ม migration block ใน `init_db()` (pattern v7.5.0)
2. Test migration:
   - Local SQLite: ลบ DB → start app → ทุก column สร้าง
   - Local with existing DB: start app → migration sees missing column → ADD
   - Rerun: idempotent (no error)
3. Verify columns via `sqlite3 projectkey.db ".schema files"`

**🔬 Verify gate:**
- [ ] `sqlite3 projectkey.db ".schema files"` แสดง 3 columns ใหม่ (embedding_vector, embedding_model, embedding_hash)
- [ ] `sqlite3 projectkey.db ".schema file_summaries"` แสดง entities, relationships, schema_version
- [ ] `sqlite3 projectkey.db ".schema clusters"` แสดง method, centroid, member_count
- [ ] `sqlite3 projectkey.db ".schema graph_nodes"` แสดง community_id, embedding_centrality
- [ ] Rerun app start → log "Added: ..." ไม่ปรากฏ (idempotent)
- [ ] อ่าน file ที่มีอยู่แล้ว → ทำงานปกติ (no NULL crash)

#### Step 0.4 — Feature flag system
1. แก้ `backend/config.py`:
   - เพิ่ม env vars (USE_HYBRID_CLUSTERING etc.)
   - Default OFF for new features, ON for safe cache/checkpoint
2. Verify ใน organizer.py ว่า `if USE_X` check pattern compile ผ่าน

**🔬 Verify gate:**
- [ ] `flyctl secrets set USE_HYBRID_CLUSTERING=true` → restart → log "USE_HYBRID_CLUSTERING=True"
- [ ] `flyctl secrets set USE_HYBRID_CLUSTERING=false` → restart → log shows legacy path
- [ ] Python REPL: `from backend.config import USE_HYBRID_CLUSTERING` → no ImportError

#### Step 0.5 — Test harness baseline
1. Create `scripts/test_organize_quality.py`:
   - Load 50 sample files (copy from prod DB หรือ generate test corpus)
   - Run organize with flag OFF → save baseline report
2. **ห้าม push prod ที่ phase 0** — ทำใน feature branch อย่างเดียว

**🔬 Verify gate:**
- [ ] `python scripts/test_organize_quality.py --baseline` runs → output `reports/organize-quality-baseline.md`
- [ ] Baseline report has: wall_clock_sec, llm_calls, memory_peak_mb, cluster_count
- [ ] All numbers > 0 (sanity)

#### Phase 0 Done Criteria
- [ ] Docker build ผ่าน, image size บันทึก (image_size_v10.txt vs image_size_v11.txt)
- [ ] DB migration ทำงาน (test 3 scenarios: fresh / existing / rerun)
- [ ] `USE_HYBRID_CLUSTERING=false` → behavior เหมือนเดิม 100% (manual smoke test 5 ไฟล์)
- [ ] `embed_files()` ทำงาน + cache works (test ด้วย 3 file same hash → 1 API call)
- [ ] `test_organize_quality.py` baseline report generated
- [ ] เขียวเขียน session log ใน `.agent-memory/history/session-logs/`
- [ ] Memory `pipeline-state.md` updated → "phase_0_complete"

#### Phase 0 Rollback
- ปิด feature flags → ระบบกลับเป็น v10.0.14 (code path เก่ายัง intact)
- Schema columns เก่งใหม่ที่เพิ่ม → idempotent, ไม่ต้อง rollback
- หากต้องการ remove deps → revert requirements-fly.txt + rebuild

---

### 🔵 Phase 1 — Hybrid Clustering (1-2 วัน)

> **เป้าหมาย**: แทน "Cluster" step ด้วย embeddings + HDBSCAN + LLM-label. ลด LLM calls ในขั้นนี้จาก 1 mega call → ~5-10 small calls

#### Step 1.1 — สร้าง `backend/clustering.py`
1. Create file:
   ```python
   """Hybrid clustering: embeddings + UMAP + HDBSCAN + LLM-label.
   
   Replaces _cluster_files() (one big LLM call) with industry-standard
   embedding-based approach. Returns same output shape (drop-in replacement).
   
   Reference: BERTopic, RAPTOR (arXiv:2401.18059), Microsoft GraphRAG.
   """
   import logging
   import numpy as np
   from collections import defaultdict
   
   from .config import (
       EMBEDDING_DIM, UMAP_N_COMPONENTS, HDBSCAN_MIN_CLUSTER_SIZE,
   )
   from .embeddings import embed_files
   from .llm import call_llm_json
   
   logger = logging.getLogger(__name__)
   
   async def cluster_files_hybrid(files: list, min_cluster_size: int = 2) -> dict:
       """Drop-in replacement for _cluster_files().
       
       Returns: {"clusters": [{"title", "summary", "files": [{"file_id", "relevance", ...}]}]}
       """
       if not files:
           return {"clusters": []}
       
       # 1. Get embeddings (batch, cached)
       vectors_dict = await embed_files(files)
       file_ids = [f.id for f in files]
       vectors = np.array([vectors_dict[fid] for fid in file_ids])
       
       # 2. UMAP reduce (if N > min for UMAP to be useful)
       if len(files) >= 5:
           import umap
           reducer = umap.UMAP(
               n_components=UMAP_N_COMPONENTS,
               metric="cosine",
               random_state=42,
               n_neighbors=min(15, len(files) - 1),
           )
           reduced = reducer.fit_transform(vectors)
       else:
           reduced = vectors  # too few files, skip UMAP
       
       # 3. HDBSCAN clustering
       import hdbscan
       clusterer = hdbscan.HDBSCAN(
           min_cluster_size=min_cluster_size,
           metric="euclidean",
           cluster_selection_method="eom",
       )
       labels = clusterer.fit_predict(reduced)
       # labels: array of cluster ids (-1 = noise)
       
       # 4. Group files by cluster
       cluster_groups = defaultdict(list)
       for f, label in zip(files, labels):
           cluster_groups[int(label)].append(f)
       
       # 5. Compute centrality per file (distance to cluster centroid)
       centralities = _compute_centrality(reduced, labels)
       file_centrality = {fid: c for fid, c in zip(file_ids, centralities)}
       
       # 6. Label each cluster with LLM (parallel, semaphore=3)
       import asyncio
       sem = asyncio.Semaphore(3)
       
       async def _label_one(label_id, group_files):
           async with sem:
               return label_id, await _llm_label_cluster(group_files, file_centrality)
       
       label_results = await asyncio.gather(*[
           _label_one(lbl, grp) for lbl, grp in cluster_groups.items()
       ])
       
       # 7. Assemble output in legacy shape
       cluster_output = []
       for label_id, cluster_data in label_results:
           if label_id == -1:
               # Noise — each file is its own pseudo-cluster
               for f in cluster_groups[-1]:
                   cluster_output.append({
                       "temp_id": f"c_noise_{f.id[:8]}",
                       "title": f.filename,
                       "summary": "Standalone file (no related group)",
                       "files": [{
                           "file_id": f.id,
                           "relevance": 1.0,
                           "importance_score": _heuristic_importance(f, file_centrality[f.id]),
                           "importance_label": "medium",
                           "is_primary": True,
                           "why_important": "Standalone document",
                       }],
                   })
           else:
               cluster_output.append(cluster_data)
       
       logger.info(
           f"Hybrid cluster: {len(files)} files → {len(cluster_output)} clusters "
           f"(noise={len(cluster_groups.get(-1, []))})"
       )
       return {"clusters": cluster_output}
   
   
   def _compute_centrality(reduced: np.ndarray, labels: np.ndarray) -> np.ndarray:
       """Compute per-file centrality (1 - normalized distance to cluster centroid).
       
       Centrality 1.0 = at centroid, 0.0 = at edge. Used for importance scoring.
       """
       centralities = np.zeros(len(labels))
       for label in set(labels):
           if label == -1:
               continue
           mask = labels == label
           members = reduced[mask]
           centroid = members.mean(axis=0)
           distances = np.linalg.norm(members - centroid, axis=1)
           max_dist = distances.max() or 1.0
           centralities[mask] = 1.0 - (distances / max_dist)
       return centralities
   
   
   async def _llm_label_cluster(group_files: list, centralities: dict) -> dict:
       """Single LLM call: label + score importance for cluster members.
       
       Uses top-3 most central files as samples (preview each 1500 chars).
       Token budget: ~10K input, ~2K output → fits easily.
       """
       # Pick top-3 by centrality as cluster representatives
       sorted_files = sorted(group_files, key=lambda f: -centralities.get(f.id, 0))
       samples = sorted_files[:3]
       
       file_descriptions = []
       for f in samples:
           preview = (f.extracted_text or "")[:1500]
           file_descriptions.append(
               f"FILE: {f.filename}\nPREVIEW:\n{preview}\n---"
           )
       
       system_prompt = """You are a document organization AI. Given 3 sample files from a cluster of related documents, name the cluster and explain why these files belong together.

Respond with ONLY valid JSON:
{
  "title": "Cluster name (in Thai)",
  "summary": "Brief description of what unifies these files (in Thai)",
  "is_meaningful": true/false   // false if files don't actually share a theme
}

Rules:
- Title: 3-8 words, descriptive, in Thai
- Summary: 1-2 sentences, in Thai
- is_meaningful: false ถ้าไฟล์ดูไม่เข้าพวก (HDBSCAN อาจจัด false-positive ได้)"""
       
       user_prompt = (
           f"Cluster has {len(group_files)} files total. Top 3 samples:\n\n"
           + "\n\n".join(file_descriptions)
       )
       
       label_data = await call_llm_json(system_prompt, user_prompt)
       
       # Build files array with importance scores
       files_array = []
       for f in group_files:
           centrality = centralities.get(f.id, 0.5)
           files_array.append({
               "file_id": f.id,
               "relevance": float(centrality),  # use centrality as relevance proxy
               "importance_score": _heuristic_importance(f, centrality),
               "importance_label": _score_to_label(_heuristic_importance(f, centrality)),
               "is_primary": f.id == sorted_files[0].id,  # most central
               "why_important": f"Member of cluster '{label_data.get('title', '')}'",
           })
       
       return {
           "temp_id": f"c_{label_data.get('title', 'untitled')[:16]}",
           "title": label_data.get("title", "Untitled Group"),
           "summary": label_data.get("summary", ""),
           "files": files_array,
       }
   
   
   def _score_to_label(score: int) -> str:
       if score >= 70: return "high"
       if score >= 40: return "medium"
       return "low"
   ```

2. Test locally:
   ```python
   from backend.clustering import cluster_files_hybrid
   from backend.database import get_db_session
   
   async def test():
       async with get_db_session() as db:
           files = ...  # query 10 test files
           result = await cluster_files_hybrid(files)
           print(result)
   ```

#### Step 1.2 — สร้าง `backend/importance.py`
1. Create file:
   ```python
   """Deterministic importance scoring (replaces LLM-judge importance).
   
   Factors:
   - text_length: log-scale (longer = potentially more content)
   - embedding_centrality: position within cluster (centroid = important)
   - recency: uploaded_at (newer = potentially more relevant)
   - source_of_truth: explicit user flag
   - reference_count: graph in-degree (how many other docs link to this)
   """
   import math
   from datetime import datetime, timezone
   
   def heuristic_importance(
       file,
       centrality: float = 0.5,
       reference_count: int = 0,
   ) -> dict:
       """Returns: {"score": int 0-100, "label": str, "factors": {...}}"""
       text_len = len(file.extracted_text or "")
       len_score = min(40, math.log10(max(text_len, 1)) * 10)  # 0-40
       
       cent_score = centrality * 30  # 0-30
       
       # Recency: 7 days = max points, decays to 0 at 365 days
       if file.uploaded_at:
           age_days = (datetime.now(timezone.utc) - file.uploaded_at).days
           rec_score = max(0, 15 * (1 - min(age_days / 365, 1)))  # 0-15
       else:
           rec_score = 7.5  # neutral
       
       sot_score = 10 if getattr(file, "source_of_truth", False) else 0  # 0-10
       
       ref_score = min(5, reference_count * 0.5)  # 0-5
       
       total = int(len_score + cent_score + rec_score + sot_score + ref_score)
       total = max(0, min(100, total))
       
       label = "high" if total >= 70 else "medium" if total >= 40 else "low"
       
       return {
           "score": total,
           "label": label,
           "factors": {
               "text_length": int(len_score),
               "centrality": int(cent_score),
               "recency": int(rec_score),
               "source_of_truth": int(sot_score),
               "references": int(ref_score),
           },
       }
   ```

2. Update `backend/clustering.py` ให้ import + ใช้:
   ```python
   from .importance import heuristic_importance
   
   def _heuristic_importance(f, centrality: float = 0.5) -> int:
       return heuristic_importance(f, centrality)["score"]
   ```

#### Step 1.3 — Route ใน organizer.py
1. แก้ `backend/organizer.py:62-66` ใน `organize_files()`:
   ```python
   from .config import USE_HYBRID_CLUSTERING
   
   # 1. Cluster
   if USE_HYBRID_CLUSTERING:
       from .clustering import cluster_files_hybrid
       _pt.report(user_id, phase="embedding", step_th="วิเคราะห์ความคล้าย", step_en="Computing similarity")
       clusters_data = await cluster_files_hybrid(files, min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE)
   else:
       clusters_data = await _cluster_files(files)
   ```
2. แก้ `backend/organizer.py:554` ใน `organize_new_files()` — same pattern

**🔬 Verify gate:**
- [ ] Flag ON: organize 5 files → Fly log shows phase=embedding → cluster_math → cluster_label
- [ ] Flag OFF: organize 5 files → Fly log shows phase=clustering (legacy)
- [ ] Both paths complete without error

#### Step 1.4 — Update progress_tracker phase metadata
1. แก้ `legacy-frontend/app.js:329-339` — เพิ่ม PHASE_META entries (embedding, cluster_math, cluster_label)
2. Test ใน browser: เปิด /app → check console → กดจัดระเบียบ → ดูว่า overlay แสดง phase ใหม่

**🔬 Verify gate:**
- [ ] Playwright spec `tests/v11-phase1-clustering.spec.js` passes
- [ ] Browser console: no JS errors
- [ ] Phase icons correct (🧮 📐 🏷️)
- [ ] Cache buster v10.0.14 → v11.0.0-alpha.1 in 5 HTMLs

#### Step 1.5 — Migration script (one-time embed)
1. สร้าง `scripts/migrate_to_v11.py`:
   ```python
   """Compute embeddings for all existing files. Idempotent."""
   import asyncio
   from backend.database import get_db_session, File
   from backend.embeddings import embed_files
   from sqlalchemy import select
   
   async def main():
       async with get_db_session() as db:
           result = await db.execute(
               select(File).where(
                   File.extracted_text != "",
                   (File.embedding_vector == None) | (File.embedding_hash == "")
               )
           )
           files = result.scalars().all()
           print(f"Files needing embed: {len(files)}")
           
           # Batch in groups of 50
           batch_size = 50
           for i in range(0, len(files), batch_size):
               batch = files[i:i+batch_size]
               vectors = await embed_files(batch)
               # Save back to DB
               for f in batch:
                   if f.id in vectors:
                       f.embedding_vector = _encode_vector(vectors[f.id])
                       f.embedding_model = EMBEDDING_MODEL
                       f.embedding_hash = f.content_hash
               await db.commit()
               print(f"  Embedded {min(i+batch_size, len(files))}/{len(files)}")
               await asyncio.sleep(0.5)  # rate-limit safe
   
   if __name__ == "__main__":
       asyncio.run(main())
   ```

#### Phase 1 Done Criteria
- [ ] `USE_HYBRID_CLUSTERING=true` → organize 50 ไฟล์ทดสอบ ทำงานครบ (manual)
- [ ] Quality test: cluster purity vs baseline ≥ 75% (ใช้ test_organize_quality.py)
- [ ] Wall-clock time < 50% ของเก่า สำหรับ 50 ไฟล์
- [ ] Cost: LLM calls < 30% ของเก่า
- [ ] No regression: USE_HYBRID_CLUSTERING=false ยัง work เหมือนเดิม 100%
- [ ] Migration script รัน + verify embeddings ใน DB
- [ ] Frontend overlay แสดง phase ใหม่ (embedding/cluster_math/cluster_label)
- [ ] เขียวเขียน session log
- [ ] Memory updated

#### Phase 1 Rollback
1. `flyctl secrets set USE_HYBRID_CLUSTERING=false` → restart Fly machines (instant)
2. Code path เก่ายังอยู่ใน `organizer.py:_cluster_files()` — ไม่มีอะไรลบ
3. Embedding vectors ใน DB ยังอยู่ (ใช้สำหรับ chat search ในอนาคต ไม่เสียเปล่า)

---

### 🟢 Phase 2 — Structured Summary (รวม sum + tag) (1-2 วัน)

> **เป้าหมาย**: รวมขั้น 5 (Summary) + 7 (Enrich/tag) เป็น **1 LLM call ต่อไฟล์** ด้วย structured output. ลด LLM calls ครึ่งหนึ่ง

#### Step 2.1 — Update prompt schema
1. แก้ `backend/organizer.py` — สร้าง `_generate_summary_v2()` (เก็บ `_generate_summary_simple()` เดิมไว้ rename เป็น `_generate_summary_v1_simple()`)
2. v2 prompt:
   ```python
   async def _generate_summary_v2(file, cluster_title, importance) -> dict:
       """Structured output: summary + entities + relationships + tags ใน 1 call."""
       text_preview = (file.extracted_text or "")[:8000]
       
       system_prompt = """You are a document analysis AI. Analyze the document and produce a comprehensive structured summary.

Respond with ONLY valid JSON matching this exact schema:

{
  "summary": "...",                       // 2-4 paragraphs in Thai
  "key_topics": ["topic1", ...],           // 3-6 items in Thai
  "key_facts": ["fact1", ...],             // 3-8 specific items: numbers, dates, names (Thai)
  "why_important": "...",                  // Why this file matters (Thai)
  "suggested_usage": "...",                // How AI should use this (Thai)
  "entities": [
    {
      "type": "person|company|product|date|place|document|other",
      "name": "canonical name",
      "aliases": ["alt name 1", "alt name 2"]   // 0-3 aliases
    }
  ],
  "relationships": [
    {
      "from": "entity_name",
      "to": "entity_name",
      "type": "owned_by|signed_by|part_of|mentions|references|other",
      "evidence": "short quote from document"
    }
  ],
  "tags": ["tag1", "tag2", ...]            // 3-8 short Thai tags for search
}

Rules:
- All Thai language fields in Thai
- Entities: extract 3-15 named things (concrete: คน, บริษัท, สินค้า, วันที่, สถานที่)
- Relationships: 2-8 connections; must use entity names from `entities` array
- Tags: short keywords for search (e.g. "ประกันสุขภาพ", "MTL", "เมืองไทย")
- Be specific and useful, not generic"""
       
       user_prompt = (
           f"FILENAME: {file.filename}\n"
           f"FILETYPE: {file.filetype}\n"
           f"CLUSTER: {cluster_title}\n"
           f"IMPORTANCE: {importance.get('label', 'medium')} ({importance.get('score', 50)}/100)\n\n"
           f"FULL TEXT:\n{text_preview}"
       )
       
       return await call_llm_json(system_prompt, user_prompt)
   ```

3. Routing in `_generate_summary()`:
   ```python
   async def _generate_summary(file, cluster_title, importance) -> dict:
       from .config import USE_STRUCTURED_SUMMARY, LARGE_FILE_THRESHOLD
       text = file.extracted_text or ""
       
       if USE_STRUCTURED_SUMMARY:
           if len(text) > LARGE_FILE_THRESHOLD:
               return await _generate_summary_mapreduce_v2(file, cluster_title, importance)
           return await _generate_summary_v2(file, cluster_title, importance)
       
       # Legacy path
       if len(text) > LARGE_FILE_THRESHOLD:
           return await _generate_summary_mapreduce(file, cluster_title, importance)
       return await _generate_summary_simple(file, cluster_title, importance)
   ```

**🔬 Verify gate:**
- [ ] Unit test: mock LLM returns valid JSON with entities/relationships → parsed OK
- [ ] Unit test: mock LLM returns malformed JSON → fallback / retry
- [ ] Manual: run on 1 Thai PDF → output JSON has entities (3-15) + relationships (2-8) + tags (3-8)
- [ ] Manual: run on 1 English DOCX → output JSON valid + Thai output
- [ ] Validate: all entity names appear in document text (no hallucination check)

#### Step 2.2 — Map-reduce v2 (big files)
1. สร้าง `_generate_summary_mapreduce_v2()` — เหมือนเดิม + รวม entities/relationships ของแต่ละ chunk:
   ```python
   async def _generate_summary_mapreduce_v2(file, cluster_title, importance) -> dict:
       chunks = chunk_text(file.extracted_text or "")
       file.chunk_count = len(chunks)
       file.is_truncated = False
       
       mini_results = []  # v2: each has entities + relationships
       for i, chunk in enumerate(chunks):
           mini = None
           for attempt in range(3):
               try:
                   mini = await _summarize_chunk_v2(chunk, file.filename, i+1, len(chunks))
                   break
               except Exception as e:
                   if attempt < 2:
                       await asyncio.sleep(2 ** attempt)
           if mini is None:
               file.is_truncated = True
               mini = {"summary": f"[ส่วนที่ {i+1} อ่านไม่ได้]", "entities": [], "relationships": [], "tags": []}
           mini_results.append(mini)
       
       return await _merge_summaries_v2(mini_results, file, cluster_title, importance)
   ```

2. `_merge_summaries_v2()` — รวม entities (dedup by name), relationships (dedup by from+to+type), tags (dedup)

#### Step 2.3 — DB write — เก็บ entities + relationships + tags
1. แก้ `backend/organizer.py:172-195` (DB write loop):
   ```python
   from .config import USE_STRUCTURED_SUMMARY
   
   if USE_STRUCTURED_SUMMARY and summary_data.get("entities"):
       file_summary = FileSummary(
           file_id=f.id,
           summary_text=summary_data.get("summary", ""),
           key_topics=json.dumps(summary_data.get("key_topics", []), ensure_ascii=False),
           key_facts=json.dumps(summary_data.get("key_facts", []), ensure_ascii=False),
           why_important=summary_data.get("why_important", ""),
           suggested_usage=summary_data.get("suggested_usage", ""),
           entities=json.dumps(summary_data.get("entities", []), ensure_ascii=False),
           relationships=json.dumps(summary_data.get("relationships", []), ensure_ascii=False),
           schema_version=2,
       )
       # Tags ก็เก็บใน File.tags
       f.tags = json.dumps(summary_data.get("tags", []), ensure_ascii=False)
   else:
       # legacy path
       file_summary = FileSummary(...)  # ของเดิม
   ```

#### Step 2.4 — Skip enrich step ถ้า structured
1. แก้ `backend/main.py:1494-1495`:
   ```python
   from .config import USE_STRUCTURED_SUMMARY
   
   if not USE_STRUCTURED_SUMMARY:
       _pt.report(current_user.id, phase="enrich", ...)
       await enrich_all_files(db, current_user.id, force=force)
   # else: tags ถูก inline ใน summary call แล้ว, ข้าม enrich phase
   ```
2. Same at line 1629-1630 in /api/organize-new

#### Step 2.5 — Markdown store: เพิ่ม sections
1. แก้ `backend/markdown_store.py:25`:
   ```python
   def write_summary_md(
       file_id: str, filename: str, filetype: str, cluster_title: str,
       importance_score: int, importance_label: str, is_primary: bool,
       summary_text: str, key_topics: list, key_facts: list,
       why_important: str, suggested_usage: str,
       uploaded_at: str = "",
       # v11.0.0 new params (optional for backward compat)
       entities: list = None,
       relationships: list = None,
       community_id: str = "",
       embedding_centrality: float = 0.0,
   ) -> str:
       ...
       # Frontmatter — เพิ่ม community + centrality + schema_version
       frontmatter = {
           "file_id": file_id,
           # ... ของเดิม
           "schema_version": 2 if entities else 1,
       }
       if community_id:
           frontmatter["community_id"] = community_id
       if embedding_centrality:
           frontmatter["embedding_centrality"] = round(embedding_centrality, 3)
       
       # Body — เพิ่ม Entities + Relationships sections
       # ... ของเดิม (Summary, Key Topics, Key Facts, Why Important, Suggested Usage)
       
       if entities:
           body_parts.append("# Entities\n")
           for e in entities:
               aliases = e.get("aliases", [])
               alias_str = f" (aka {', '.join(aliases)})" if aliases else ""
               body_parts.append(f"- **{e.get('type', 'other')}**: {e.get('name', '')}{alias_str}")
           body_parts.append("")
       
       if relationships:
           body_parts.append("# Relationships\n")
           for r in relationships:
               evidence = f" — _\"{r.get('evidence', '')}\"_" if r.get('evidence') else ""
               body_parts.append(
                   f"- {r.get('from', '')} — *{r.get('type', '')}* — {r.get('to', '')}{evidence}"
               )
           body_parts.append("")
       
       # ... rest
   ```

2. Caller ใน organizer ส่ง params ใหม่:
   ```python
   md_path = write_summary_md(
       ...,
       entities=summary_data.get("entities", []) if USE_STRUCTURED_SUMMARY else None,
       relationships=summary_data.get("relationships", []) if USE_STRUCTURED_SUMMARY else None,
       community_id=f.community_id or "",
       embedding_centrality=f.embedding_centrality or 0.0,
   )
   ```

#### Phase 2 Done Criteria
- [ ] FileSummary.entities + .relationships มีข้อมูลจริงใน DB (sample query)
- [ ] LLM calls per file ลดจาก ~2 → 1 (verify via log count)
- [ ] tags ใน File เพิ่มจาก summary call (ไม่ต้อง enrich แยก)
- [ ] .md file มี Entities + Relationships sections (manual inspect)
- [ ] Backward-compat: schema_version=1 ไฟล์เก่ายังอ่านได้ + ใช้งานปกติ
- [ ] JSON parse fail rate < 0.5% (ดูจาก logs)
- [ ] Smoke test: organize 30 ไฟล์ → tags + entities + relationships ครบ

#### Phase 2 Rollback
- `USE_STRUCTURED_SUMMARY=false` → กลับใช้ flow เก่า
- ไฟล์ที่ organize ด้วย v2 schema ยังอยู่ใน DB (data ไม่หาย, frontend อาจไม่แสดง entities แต่ไม่พัง)

---

### 🟣 Phase 3 — Entity Graph + Leiden Community (2-3 วัน)

> **เป้าหมาย**: แทนที่ "LLM per pair" graph build ด้วย entity dedup + Leiden community detection

#### Step 3.1 — สร้าง `backend/entity_resolver.py`
1. Create file (เนื้อหา detailed):
   ```python
   """Entity deduplication across files.
   
   Merges entities that refer to the same real-world thing:
   - "MTL" + "เมืองไทยประกันชีวิต" + "Muang Thai Life" → same canonical entity
   
   Strategy:
   1. Collect all FileSummary.entities → flat list
   2. Group by lowercase name (exact match)
   3. Union aliases within each group
   4. For similar names (Levenshtein < 3 OR cosine-sim > 0.9 on name embedding):
      merge into canonical form
   """
   import json
   import logging
   from collections import defaultdict
   from sqlalchemy import select
   from .database import FileSummary, File
   
   logger = logging.getLogger(__name__)
   
   class EntityInfo:
       def __init__(self):
           self.canonical_name: str = ""
           self.entity_type: str = ""
           self.aliases: set[str] = set()
           self.file_ids: set[str] = set()
   
   async def resolve_entities(db, user_id: str) -> dict[str, EntityInfo]:
       """Returns: {canonical_name: EntityInfo}"""
       
       # 1. Collect all entities from FileSummary
       result = await db.execute(
           select(FileSummary, File.id).join(File).where(
               File.user_id == user_id,
               FileSummary.entities != "",
           )
       )
       
       raw_entities = []  # list of (entity_dict, file_id)
       for fs, file_id in result.all():
           try:
               entities = json.loads(fs.entities)
               for e in entities:
                   raw_entities.append((e, file_id))
           except (json.JSONDecodeError, TypeError):
               continue
       
       # 2. Group by lowercase name (exact match)
       groups = defaultdict(list)
       for e, fid in raw_entities:
           name_norm = e.get("name", "").strip().lower()
           if name_norm:
               groups[name_norm].append((e, fid))
       
       # 3. Build canonical entities
       resolved = {}
       for name_norm, members in groups.items():
           canonical = EntityInfo()
           canonical.canonical_name = members[0][0].get("name", "")  # original case
           canonical.entity_type = members[0][0].get("type", "other")
           for e, fid in members:
               for a in e.get("aliases", []):
                   canonical.aliases.add(a)
               canonical.file_ids.add(fid)
           resolved[canonical.canonical_name] = canonical
       
       # 4. Fuzzy merge across canonical names (Levenshtein-based)
       _fuzzy_merge_entities(resolved)
       
       logger.info(f"Entity resolve: {len(raw_entities)} raw → {len(resolved)} canonical")
       return resolved
   
   
   def _fuzzy_merge_entities(resolved: dict) -> None:
       """In-place merge of similar names (Levenshtein distance ≤ 2)."""
       from difflib import SequenceMatcher
       
       names = list(resolved.keys())
       to_merge = []  # list of (loser_name, winner_name)
       
       for i, n1 in enumerate(names):
           for n2 in names[i+1:]:
               # Same entity type required for fuzzy merge
               if resolved[n1].entity_type != resolved[n2].entity_type:
                   continue
               
               ratio = SequenceMatcher(None, n1.lower(), n2.lower()).ratio()
               if ratio > 0.85:  # similar enough
                   # Pick winner: more file_ids or longer name
                   if len(resolved[n1].file_ids) >= len(resolved[n2].file_ids):
                       to_merge.append((n2, n1))
                   else:
                       to_merge.append((n1, n2))
       
       # Apply merges
       for loser, winner in to_merge:
           if loser not in resolved or winner not in resolved:
               continue  # already merged
           winner_info = resolved[winner]
           loser_info = resolved[loser]
           winner_info.aliases.update(loser_info.aliases)
           winner_info.aliases.add(loser_info.canonical_name)
           winner_info.file_ids.update(loser_info.file_ids)
           del resolved[loser]
   ```

#### Step 3.2 — Graph build v2
1. แก้ `backend/graph_builder.py:21`:
   ```python
   async def build_full_graph(db, user_id, force=False):
       from .config import USE_ENTITY_GRAPH
       if USE_ENTITY_GRAPH:
           return await _build_graph_v2(db, user_id, force)
       return await _build_graph_v1(db, user_id, force)  # legacy
   
   # Keep legacy build as _build_graph_v1 (rename current code)
   ```

2. เพิ่ม `_build_graph_v2()`:
   ```python
   async def _build_graph_v2(db, user_id, force=False):
       """Entity-based graph + Leiden community detection.
       
       Steps:
       1. Resolve entities → canonical names
       2. Build NetworkX graph: file nodes + entity nodes + edges
       3. Run Leiden community detection
       4. Save GraphNode + GraphEdge rows
       5. Update File.community_id
       """
       import networkx as nx
       import community as community_louvain
       from .entity_resolver import resolve_entities
       
       # 1. Resolve entities
       entities = await resolve_entities(db, user_id)
       
       # 2. Build graph
       G = nx.Graph()
       
       # File nodes
       files_result = await db.execute(
           select(File).where(File.user_id == user_id, File.extracted_text != "")
       )
       files = files_result.scalars().all()
       for f in files:
           G.add_node(f"file:{f.id}", type="file", label=f.filename, file_id=f.id)
       
       # Entity nodes
       for canonical, info in entities.items():
           node_id = f"entity:{canonical}"
           G.add_node(node_id, type="entity", label=canonical, entity_type=info.entity_type)
           # Edges: file mentions entity
           for fid in info.file_ids:
               G.add_edge(f"file:{fid}", node_id, edge_type="mentions")
       
       # Relationship edges from FileSummary
       summaries_result = await db.execute(
           select(FileSummary).join(File).where(
               File.user_id == user_id,
               FileSummary.relationships != "",
           )
       )
       for fs in summaries_result.scalars().all():
           try:
               rels = json.loads(fs.relationships)
               for r in rels:
                   src = f"entity:{r.get('from', '')}"
                   tgt = f"entity:{r.get('to', '')}"
                   if src in G and tgt in G:
                       G.add_edge(src, tgt, edge_type=r.get("type", "related"))
           except (json.JSONDecodeError, TypeError):
               continue
       
       # 3. Run Leiden community detection
       partition = community_louvain.best_partition(G)
       # partition: {node_id: community_id (int)}
       
       # 4. Save to DB
       # Clear old graph
       await db.execute(GraphEdge.__table__.delete().where(GraphEdge.user_id == user_id))
       await db.execute(GraphNode.__table__.delete().where(GraphNode.user_id == user_id))
       
       for node_id, data in G.nodes(data=True):
           comm_id = f"comm-{partition.get(node_id, 0)}"
           graph_node = GraphNode(
               id=gen_id(),
               user_id=user_id,
               object_type=data["type"],
               object_id=data.get("file_id", "") or data.get("label", ""),
               label=data["label"],
               community_id=comm_id,
               # ... other fields
           )
           db.add(graph_node)
       
       # ... save edges similarly
       
       # 5. Update File.community_id
       for f in files:
           comm_id = partition.get(f"file:{f.id}", 0)
           f.community_id = f"comm-{comm_id}"
       
       await db.commit()
       
       return {"nodes": len(G.nodes), "edges": len(G.edges), "communities": len(set(partition.values()))}
   ```

#### Step 3.3 — Community-based suggestions
1. เพิ่ม `backend/relations.py:generate_community_suggestions()`:
   ```python
   async def generate_community_suggestions(db, user_id):
       """LLM call per community → suggest cluster name + summary.
       
       Replaces heuristic-based generate_suggestions.
       Cost: O(communities) << O(file_pairs)
       """
       # ... group GraphNodes by community_id, call LLM to summarize each
   ```

**🔬 Verify gate:**
- [ ] After organize 30 files → SuggestedRelation rows count ≈ N(communities) (not N(file_pairs))
- [ ] Each suggestion has clear `relation_type` + `confidence` > 0.5
- [ ] LLM calls in this step ≤ 10 (not 100s)

#### Step 3.4 — Frontend community badge
1. แก้ `legacy-frontend/app.js:2885-2913` (file card render):
   ```javascript
   const communityBadge = f.community_id
     ? `<span class="community-badge" title="${isThai ? 'Community ' + f.community_id : 'Community ' + f.community_id}">🕸️ ${f.community_id}</span>`
     : '';
   // ... include in render template
   ```

2. แก้ `legacy-frontend/styles.css` — เพิ่ม `.community-badge`

#### Phase 3 Done Criteria
- [ ] GraphNode มี community_id หลัง organize
- [ ] Edge count เพิ่มขึ้น 2-4× vs legacy (richer graph)
- [ ] Entity dedup: "MTL" + "เมืองไทยประกันชีวิต" merge เป็น 1 node (manual verify)
- [ ] Graph build < 30s สำหรับ 100 ไฟล์
- [ ] LLM calls ≈ 0 ใน graph build phase (math เท่านั้น)
- [ ] Community-based suggestions ใช้แทน heuristic

#### Phase 3 Rollback
- `USE_ENTITY_GRAPH=false` → กลับใช้ graph_builder เก่า
- GraphNode rows ที่มี community_id ยังอยู่ (ignored by legacy code)

---

### 🟡 Phase 4 — Polish + Cache + Cleanup (1-2 วัน)

> **เป้าหมาย**: เพิ่ม cache layer + checkpoint + cleanup small things + (optional) Batch API

#### Step 4.1 — `.md` cache layer
1. แก้ `backend/organizer.py` — เพิ่ม cache check ก่อน LLM call:
   ```python
   from .config import USE_SUMMARY_CACHE
   
   async def _fetch_summary(file):
       async with sem:
           # Check cache first
           if USE_SUMMARY_CACHE:
               cached = _load_cached_summary(file)
               if cached and _cache_is_valid(file, cached):
                   logger.info(f"Cache HIT for {file.filename}")
                   return (file, cluster_title, importance_data, cached, None)
           
           # No cache or stale → compute
           summary_data = await _generate_summary(file, cluster_title, importance_data)
           return (file, cluster_title, importance_data, summary_data, None)
   
   def _load_cached_summary(file) -> dict | None:
       """Load .md file → parse → return summary_data shape."""
       from .markdown_store import read_summary_md
       md_data = read_summary_md(file.filename)
       if not md_data:
           return None
       fm = md_data.get("frontmatter", {})
       # ... extract entities, relationships, etc.
   
   def _cache_is_valid(file, cached) -> bool:
       """Cache valid if file content unchanged."""
       return file.content_hash == cached.get("file_hash", "")
   ```

#### Step 4.2 — Checkpoint + resume
1. แก้ `backend/organizer.py` — commit ทุก N ไฟล์:
   ```python
   from .config import USE_ORGANIZE_CHECKPOINT
   
   CHECKPOINT_EVERY = 10
   
   for idx, (f, cluster_title, importance_data, summary_data, err) in enumerate(results):
       # ... write DB
       if USE_ORGANIZE_CHECKPOINT and idx % CHECKPOINT_EVERY == 0:
           await db.commit()
           logger.info(f"Checkpoint: {idx}/{len(results)}")
   ```

2. Resume logic: ใน `organize_new_files()` ตอนเริ่ม — query files ที่ยังเป็น `processing_status="processing"` (จาก crash ก่อนหน้า) → resume

**🔬 Verify gate (critical — simulates real failure):**
- [ ] Manual: organize 30 files → mid-organize (~ไฟล์ที่ 15) → `flyctl machine stop <id>` → `flyctl machine start` → log shows "Resume: 15 files already processed, continuing from 16"
- [ ] Verify: ไฟล์ 1-15 ยัง status="ready" หลัง restart
- [ ] Verify: ไฟล์ 16-30 ค้างที่ status="processing" → resume → status="ready"
- [ ] Edge: ถ้า resume แต่ flag ปิด → ไฟล์ "processing" ยังค้างอยู่ → ต้อง admin endpoint reset

#### Step 4.3 — Batch API (optional, defer ถ้า Phase 4 ใช้เวลาเยอะ)
- ใช้ Anthropic Message Batches หรือ Gemini Batch API สำหรับ async-tolerant work
- ลด AI cost 50%
- Implementation: serialize calls → submit batch → poll → parse results
- **Skip ถ้าเวลาไม่พอ** — Phase 1-3 ก็ลด cost เยอะแล้ว

#### Step 4.4 — Re-enable duplicate detector
1. แก้ `backend/duplicate_detector.py:78`:
   ```python
   _DEDUP_DISABLED = False  # v11.0.0: re-enabled with new embeddings
   ```
2. Update detect_duplicates_for_batch() ให้ใช้ embedding similarity (faster than TF-IDF semantic)

#### Step 4.5 — Cleanup "small things"
1. `backend/config.py:18` — กลับ `LLM_MODEL_PRO` เป็น Pro model (ถ้าพร้อม):
   ```python
   LLM_MODEL_PRO = "google/gemini-3.1-pro-preview"  # v11.0.0: back to Pro for quality
   ```
2. `backend/markdown_store.py:1-10` — Update docstring "v11.0.0: entities + relationships sections"
3. `README.md` — Update Architecture section
4. `docs/handoff/09-flow-charts.md` — Redraw flow chart
5. `docs/handoff/04-architecture-diagrams.md` — Update components
6. `.agent-memory/reference_v10_ingestion_pipeline.md` — Bump to v11

#### Step 4.6 — Version bump + cache buster
1. `backend/config.py` — `APP_VERSION = "11.0.0"`
2. `legacy-frontend/*.html` — bump `?v=10.0.14` → `?v=11.0.0` (5 files)
3. README + changelog

#### Phase 4 Done Criteria
- [ ] `.md` cache hit rate > 50% สำหรับ re-organize (verify via logs)
- [ ] Checkpoint: simulate crash mid-organize → resume work (manual test)
- [ ] Duplicate detector re-enabled + smoke test pass
- [ ] All small things cleaned (LLM_MODEL_PRO, docstrings, docs)
- [ ] Version 11.0.0 deployed
- [ ] /health endpoint returns `{"version": "11.0.0"}`

#### Phase 4 Rollback
- Cache: `USE_SUMMARY_CACHE=false` → bypass cache, force LLM
- Checkpoint: `USE_ORGANIZE_CHECKPOINT=false` → revert to single-commit
- Dedup: revert `_DEDUP_DISABLED = True`

---

## 🧪 Test Scenarios (สำหรับฟ้า)

> **🎯 Per-Milestone Test Matrix** — ทุก step (milestone) มี "Verify" gate ที่ต้องผ่านก่อนเดินต่อ.
> เขียวห้าม commit step ถัดไป ถ้า "Verify" ของ step ก่อนหน้ายังไม่ผ่าน. ฟ้าใช้ matrix นี้ใน review.

---

### 📋 Master Test Matrix (24 milestones × verification)

| Step | Milestone | Test Type | Acceptance Criteria | Effort |
|---|---|---|---|---|
| **Phase 0 — Foundation** | | | | |
| 0.1 | Deps + Docker build | Smoke | Docker image build ผ่าน · imports OK · size diff < +100MB | 15 min |
| 0.2 | `embeddings.py` | Unit + Smoke | 4 unit tests pass + manual embed 3 files → cache hit on rerun | 30 min |
| 0.3 | Schema migration | Smoke | 3 scenarios pass: fresh / existing / rerun · sqlite3 `.schema` shows new cols | 15 min |
| 0.4 | Feature flags | Smoke | Toggle USE_HYBRID_CLUSTERING=true/false → log shows correct branch | 5 min |
| 0.5 | Test harness baseline | Smoke | `test_organize_quality.py --baseline` runs + report saved | 30 min |
| **Phase 1 — Hybrid Clustering** | | | | |
| 1.1 | `clustering.py` | Unit + Integration | 5 unit tests pass + cluster 10 real files locally | 1 hr |
| 1.2 | `importance.py` | Unit | 4 unit tests pass + heuristic explainable | 20 min |
| 1.3 | Organizer routing | Integration | Flag ON → embedding phase log appears · Flag OFF → legacy log | 20 min |
| 1.4 | Frontend phase meta | Browser (Playwright) | Spec verifies overlay shows new phase icons | 30 min |
| 1.5 | Migration script | Smoke + Integration | Run on test corpus 50 files · idempotent rerun · embeddings in DB | 30 min |
| **Phase 2 — Structured Summary** | | | | |
| 2.1 | `_generate_summary_v2` | Unit + Integration | JSON schema valid · entities/relationships fields populated | 45 min |
| 2.2 | Map-reduce v2 | Unit + Integration | 50K text file → chunks + merged result has all entities aggregated | 45 min |
| 2.3 | DB write v2 | Integration | FileSummary.entities/relationships JSON valid · schema_version=2 · tags in File.tags | 20 min |
| 2.4 | Skip enrich | Integration | Flag ON → enrich_all_files NOT called (log verify) · Flag OFF → still called | 15 min |
| 2.5 | Markdown sections | Integration + Manual | .md file has Entities + Relationships sections · YAML frontmatter valid | 30 min |
| **Phase 3 — Entity Graph** | | | | |
| 3.1 | `entity_resolver.py` | Unit | 5 unit tests · "MTL" + "เมืองไทยประกันชีวิต" merge → 1 canonical | 1 hr |
| 3.2 | Graph build v2 | Integration | GraphNode.community_id populated · Leiden communities > 1 · edges ≥ 2× legacy | 1 hr |
| 3.3 | Community suggestions | Integration | SuggestedRelation rows มี (1 per community pair) | 30 min |
| 3.4 | Frontend community badge | Browser (Playwright) | Spec verifies badge renders + correct community ID | 20 min |
| **Phase 4 — Polish** | | | | |
| 4.1 | Cache layer | Integration | First organize → LLM called · re-organize same file → cache HIT (log verify) | 30 min |
| 4.2 | Checkpoint + resume | Integration | Kill machine mid-organize · restart · verify files committed stay processed | 45 min |
| 4.3 | Batch API (optional) | Integration | (If implemented) Batch job submitted + polled + parsed | 1 hr |
| 4.4 | Re-enable dedup | Integration | Upload duplicate file → detected · BACKLOG-009 closed | 30 min |
| 4.5 | Cleanup small things | Smoke | LLM_MODEL_PRO back to Pro · docstrings updated · README updated | 30 min |
| 4.6 | Version bump | Smoke | /health → version=11.0.0 · cache buster bumped · cold-start OK | 15 min |

**Total verification effort:** ~13 hours (spread across 4-5 weeks)

---

### 🔁 Continuous Regression Checklist

> **ทุก phase deploy ต้องรันทั้ง list นี้** — ห้าม regression v10.x features

#### v10.x Features ที่ต้องไม่พัง
- [ ] Login (email/pass + LINE + Google removed) → 200 OK
- [ ] Rate-limit login: 5 fails → 429 → reset on success (v10.0.14)
- [ ] Upload file: small (PDF/TXT) → processed
- [ ] Upload file: big (60K+ chars) → map-reduce + chunks
- [ ] Organize 5 small files → ทำงานครบ
- [ ] Chat: "สรุปไฟล์ X" → answer with citations
- [ ] Drive OAuth: connect → callback → sync (BYOS)
- [ ] Drive disconnect: keep_files=True / False both work
- [ ] Admin panel: stats + user list + view password (test phase) + delete user
- [ ] LINE bot: webhook → reply ทำงาน
- [ ] /api/auth/me → return current user
- [ ] /api/files?kind=all → list ครบ + badges
- [ ] /api/clusters → list ครบ
- [ ] /api/organize-status → live polling
- [ ] /api/drive/status → reports connected state
- [ ] Unified error response: `detail` + `error.code` (v10.0.14)
- [ ] Retry chunk: chunk fail → 3 retries → fallback placeholder (v10.0.14)
- [ ] .md files: read_summary_md ปรับ frontmatter เก่าได้ (backward compat)

#### Healthcheck endpoints
- [ ] `/health` → 200 + version
- [ ] `/api/healthz/queue` → 200 + queue state
- [ ] No 5xx in last 10 min of Fly logs

#### Performance baseline (อย่าให้แย่ลง)
- [ ] Cold start ≤ 30s
- [ ] /app load < 2s
- [ ] Average API response < 500ms

---

### 🎯 Test Data Setup (ใช้ทุก phase)

> **Important**: ใช้ admin user's data เท่านั้น (`bossok2546@gmail.com`). ห้ามใช้ data ของ user อื่นใน testing.

#### Test corpus tiers

**Tier 1 — Smoke (5 files)**
- 2 short Thai PDFs (insurance docs จาก user real)
- 1 long Thai PDF (60K+ chars)
- 1 mixed Thai+English DOCX
- 1 CSV / TXT

**Tier 2 — Regression (30 files)**
- Snapshot จาก admin user's current files
- Mix: PDF (15) + DOCX (5) + TXT (5) + CSV (3) + XLSX (2)
- Some big (>30K), some small (<5K), some empty extraction

**Tier 3 — Scale (100 files)**
- Synthetic: duplicate Tier 2 with hash modification (different files, similar content)
- Stress test: lots of small files + few huge ones

**Tier 4 — Stress (500+ files)**
- Generated from Wikipedia Thai subset (public, no privacy)
- 80% similar topic → expect 5-10 clusters
- 20% diverse → expect HDBSCAN noise

#### Setup script
`scripts/setup_test_corpus.py`:
- Copy `projectkey.db` → `projectkey_test.db`
- Filter to admin user's files only
- Strip extracted_text shorter than 100 chars
- Index counts: Tier 1/2/3 file IDs
- Output: `tests/fixtures/test_corpus_manifest.json`

---

### 🖥️ Browser Tests (Playwright Test for VS Code)

> **Environment**: Claude Code (VS Code) — ใช้ **Playwright Test for VS Code extension** เขียน .spec.js files (ตามที่ระบุใน bootstrap prompt)

#### Specs ที่ต้องเขียน

**`tests/v11-phase1-clustering.spec.js`** (Phase 1)
```javascript
test('organize 10 files with USE_HYBRID_CLUSTERING=true shows embedding phase', async ({ page }) => {
  await loginAsAdmin(page);
  await uploadFiles(page, tier1Files);
  await page.click('#btn-organize-new');
  
  // Verify new phase appears in overlay
  await expect(page.locator('.organize-phase-history')).toContainText('วิเคราะห์ความคล้าย');
  await expect(page.locator('.organize-phase-history')).toContainText('จัดกลุ่ม');
  await expect(page.locator('.organize-phase-history')).toContainText('ตั้งชื่อกลุ่ม');
  
  // Verify completion < 3 min for 10 files
  await expect(page.locator('.toast-success')).toBeVisible({ timeout: 180000 });
});
```

**`tests/v11-phase2-structured.spec.js`** (Phase 2)
```javascript
test('summary v2 includes entities and relationships', async ({ page }) => {
  await loginAsAdmin(page);
  await organizeFiles(page, tier1Files);
  await page.click(`.file-item[data-id="${tier1Files[0]}"]`);
  
  // File detail panel should have Entities section
  await expect(page.locator('.file-detail-entities')).toBeVisible();
  await expect(page.locator('.file-detail-relationships')).toBeVisible();
});
```

**`tests/v11-phase3-graph.spec.js`** (Phase 3)
```javascript
test('community badges render on file cards', async ({ page }) => {
  await loginAsAdmin(page);
  await organizeFiles(page, tier2Files);
  
  // Community badge should appear
  const badges = page.locator('.community-badge');
  await expect(badges).toHaveCount(tier2Files.length, { timeout: 60000 });
});
```

**`tests/v11-phase4-cache.spec.js`** (Phase 4)
```javascript
test('re-organize uses cache (no LLM calls)', async ({ page, request }) => {
  await loginAsAdmin(page);
  await organizeFiles(page, tier1Files);
  
  // First organize: count LLM calls via /api/admin/usage
  const usage1 = await request.get('/api/admin/usage');
  const calls1 = (await usage1.json()).llm_calls_total;
  
  await page.click('#btn-organize-new');  // Re-organize
  await expect(page.locator('.toast-success')).toBeVisible({ timeout: 60000 });
  
  const usage2 = await request.get('/api/admin/usage');
  const calls2 = (await usage2.json()).llm_calls_total;
  
  expect(calls2 - calls1).toBeLessThan(3);  // cache hit, < 3 calls
});
```

**`tests/v11-regression.spec.js`** (every deploy)
- Login flow (3 paths)
- Upload flow (5 file types)
- Chat flow (3 queries)
- Drive OAuth (mock)
- Admin panel
- Rate-limit verification

---

### Phase 0 Tests

#### Unit tests
- `backend/_test_embeddings.py`:
  - embed_text returns shape (1536,)
  - embed_files batch: 3 same text → 1 API call (cached)
  - cache invalidation: file content_hash change → re-embed
  - Error: API fail → raises specific exception

#### Smoke tests
- Build Docker image → no error
- `python -c "import hdbscan, umap, networkx, community; print('ok')"` → ok
- DB migration: fresh DB / existing DB / rerun → all 3 work

### Phase 1 Tests

#### Unit tests
- `backend/_test_clustering.py`:
  - cluster_files_hybrid([single_file]) → 1 cluster with that file
  - cluster_files_hybrid([10 similar]) → 1-2 clusters
  - cluster_files_hybrid([10 diverse]) → 5+ clusters
  - Empty input → empty output
  - HDBSCAN noise: outlier files → standalone clusters

- `backend/_test_importance.py`:
  - heuristic_importance with high centrality → score > 60
  - With short text + low centrality → score < 30
  - Edge: text_length = 0 → score = some baseline

#### Integration tests
- Happy path: USE_HYBRID_CLUSTERING=true → organize 30 files → no error, clusters appear in DB
- Comparison: same 30 files with flag ON vs OFF → both work, results differ
- Edge: 1 file only → 1 cluster
- Edge: 5 identical files → 1 cluster
- Edge: 100 mixed files → completes in <10 min

#### Quality tests (manual + scripts)
- `scripts/test_organize_quality.py` baseline vs v1 → cluster purity ≥ 75%
- Wall-clock time < 50% of legacy for 50 files
- LLM call count < 30% of legacy
- Memory peak < 200 MB for 50 files

### Phase 2 Tests

#### Unit tests
- `backend/_test_organizer_v2.py`:
  - `_generate_summary_v2` returns valid JSON with entities + relationships
  - `_merge_summaries_v2` dedupes entities by name
  - Map-reduce v2: 50K text → chunks + final has all entities aggregated

#### Integration tests
- Happy: USE_STRUCTURED_SUMMARY=true → organize 10 files → FileSummary.entities non-empty
- Verify: enrich_all_files() skipped when flag ON
- Verify: tags in File.tags populated from summary call (not enrich)
- Verify: .md file has Entities + Relationships sections
- Edge: file with no entities (e.g. blank doc) → entities=[] (not error)

#### Compatibility tests
- v1 file (schema_version=1) → frontend renders OK (no entity sections shown)
- v2 file → frontend renders OK (with entity sections)
- Mix: half v1 / half v2 in same user → both render

#### Quality tests
- JSON parse fail rate < 0.5% over 50 organize calls
- Entity extraction: at least 3 entities per file with substantive text

### Phase 3 Tests

#### Unit tests
- `backend/_test_entity_resolver.py`:
  - Exact name match → 1 canonical
  - "MTL" + "เมืองไทยประกันชีวิต" + "Muang Thai Life" → 1 canonical (after fuzzy merge)
  - Same name, different type → 2 canonical (no cross-type merge)
  - Empty input → empty output

#### Integration tests
- USE_ENTITY_GRAPH=true → graph build → GraphNode.community_id populated
- Leiden communities > 1 for 30+ files
- Community-based suggestions generated

#### Quality tests
- Graph edge density: 2-4× of legacy
- Entity dedup: manual inspect for known duplicates → merged

### Phase 4 Tests

#### Cache tests
- First organize: LLM called for all files
- Re-organize same files: LLM call count ~0 (cache hit)
- Edit file content → re-organize → re-call LLM (cache miss)

#### Checkpoint tests
- Manual: kill Fly machine mid-organize → restart → resume from last checkpoint
- Verify: files committed before crash stay processed
- Verify: files in 'processing' status restart

#### Concurrent users
- `scripts/load_test_organize.py`:
  - 5 users × 100 files concurrent → all complete
  - No DB lock conflicts
  - No rate-limit cascading failures

### End-to-end User Journey

1. User uploads 100 mixed files (PDF/DOCX/TXT, Thai/English)
2. User clicks "จัดระเบียบด้วย AI"
3. Overlay shows progress: embedding → cluster_math → cluster_label → summary → ... → done
4. Time elapsed < 15 min
5. User sees:
   - File list with cluster names
   - Community badges on file cards
   - File detail: summary + entities + relationships sections
   - .md file in /Drive/Personal Data Bank/summaries/ (if BYOS)
6. User asks chat: "สรุปทุกอย่างเรื่อง MTL" → response includes entities-based search
7. User refreshes → state persists

### Browser test (frontend regression)

ทำผ่าน Playwright Test for VS Code (เพราะ Claude Code environment):
- spec file: `tests/v11-organize-flow.spec.js`
- Test: login → upload 5 files → click organize → wait 5 min → verify badges
- Snapshots at each phase

---

## ✅ Done Criteria (Overall)

### Functional
- [ ] All 4 phases deployed (Phase 0 → 1 → 2 → 3 → 4) with feature flags
- [ ] Each phase rollback verified by toggling flag OFF
- [ ] All 51+ touchpoints addressed (or explicitly deferred with reason)
- [ ] Tests pass in CI (or local before deploy)
- [ ] User can organize 100 files in < 15 min
- [ ] User can organize 500+ files (was: impossible)
- [ ] No regression: organize 5 files still works fast

### Quality
- [ ] LLM call reduction ≥ 80% for 100-file organize
- [ ] Wall-clock time reduction ≥ 60% for 100-file organize
- [ ] AI cost reduction ≥ 80%
- [ ] Success rate ≥ 99%
- [ ] JSON parse fail rate < 0.5%
- [ ] Cluster determinism: same input → same clusters (idempotent)

### Documentation
- [ ] README.md updated
- [ ] docs/handoff/* updated
- [ ] .agent-memory/* updated
- [ ] Release notes (docs/reports/REPORT-v11.0.0.md)
- [ ] In-code comments อธิบาย design decisions

### Security
- [ ] No new SQL injection vectors
- [ ] No new file system access without validation
- [ ] Embedding API key in env (no leak)
- [ ] No regression in rate-limit (v10.0.14 features intact)

### Compatibility
- [ ] Schema migration tested on prod-like DB
- [ ] Frontend backward-compat: v1 .md + v2 .md both render
- [ ] BYOS sync still works
- [ ] LINE bot still works (no organize touchpoint there but verify)
- [ ] MCP tools still work

---

## ⚠️ Risks / Open Questions

### Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | HDBSCAN ภาษาไทย accuracy ต่ำกว่าคาด | M | H | Test quality ก่อน rollout admin; ถ้าผลแย่ → fallback to k-means (configurable) |
| R2 | Embedding cost จริงสูงกว่าประมาณ | L | M | Cache aggressive (content_hash); rate-limit batches |
| R3 | User เห็น cluster เปลี่ยน (deterministic) แล้วงง vs เก่าที่ random | H | L | UI toast: "ระบบจัดกลุ่มใหม่ — แม่นยำกว่าเดิม"; document in release notes |
| R4 | Migration (one-time embed) ช้า/fail สำหรับ user ใหญ่ | M | M | Run แค่ก่อน deploy, monitor, defer per-user ถ้าจำเป็น |
| R5 | JSON parse fail ใน structured output (entities/relationships ผิด schema) | L | H | Gemini JSON mode + Pydantic validation + retry + fallback to v1 path |
| R6 | Memory blowup ตอน batch embed 1000+ files | L | H | Chunked batches of 50; psutil monitor |
| R7 | Docker image size เพิ่ม 80MB → Fly cold-start ช้าลง | M | L | Multi-stage build; verify cold-start time | 
| R8 | HDBSCAN/UMAP/networkx native deps build fail บน Fly | L | H | Test Docker build ใน Phase 0; have alternative (e.g. sentence-transformers) ready |
| R9 | Concurrent users hit embedding API rate limit | M | M | Per-user semaphore on embedding API; global rate limiter |
| R10 | Entity resolver merge ผิด (false-positive merge) | M | M | Conservative threshold (Levenshtein > 0.85); manual review for top entities |
| R11 | Phase staging order ทำให้บางคน user เห็น partial v2 (cluster v2 + summary v1) | L | L | Feature flags อิสระ — แต่ document ว่าผลผสมก็ยังใช้งานได้ |
| R12 | progress_tracker.history โต ใหญ่ขึ้นเพราะ phase ใหม่ | L | L | Truncate to last 50 events |

### Open Questions (ต้องให้ user ตัดสินใจก่อนเริ่ม)

#### Q1 — Embedding Model
**ตัวเลือก:**
- (A) **Gemini text-embedding-001** (1536-d) — consistent กับ stack เดิม, Thai support OK, ราคาถูก
- (B) **OpenAI text-embedding-3-small** (1536-d) — Thai support ดีกว่าเล็กน้อย, ต้องเพิ่ม OpenAI account
- (C) **Local sentence-transformers** (paraphrase-multilingual-MiniLM-L12-v2, 384-d) — ฟรี, ไม่ต้อง API, ช้ากว่า, ไม่ต้องส่งข้อมูลออก

**ผมแนะนำ**: (A) Gemini — น้ำหนัก: low cost + low ops overhead + ใช้ key ที่มีอยู่แล้ว
**ถ้า privacy concerns**: (C) Local

#### Q2 — HDBSCAN min_cluster_size
**ตัวเลือก:**
- (A) `2` — ทุกคู่ของไฟล์เป็นกลุ่ม → กลุ่มเยอะ, granular
- (B) `3` — อย่างน้อย 3 ไฟล์ → กลุ่มใหญ่ขึ้น, ไฟล์เดี่ยวเข้า noise มากขึ้น
- (C) Adaptive: `max(2, N/20)` — scale ตาม corpus

**ผมแนะนำ**: (A) `2` — matches user's small workspace pattern (10-100 ไฟล์), granular ดีกว่า over-merge

#### Q3 — Embedding Storage
**ตัวเลือก:**
- (A) **BLOB ใน SQLite** — atomic with DB, easy backup, ~6KB/file × 1000 = 6MB
- (B) **File ใน volume** — separate from DB, scalable เกิน TB, ต้อง manage paths

**ผมแนะนำ**: (A) BLOB — corpus ปัจจุบัน <10MB, simpler

#### Q4 — Phase Order
**ตัวเลือก:**
- (A) **Sequential**: Phase 0 → 1 → 2 → 3 → 4 (low risk, ~2 weeks)
- (B) **Phase 1 only first**: ทำแค่ cluster, ดูผล 1-2 สัปดาห์ ค่อย Phase 2-3
- (C) **Parallel Phase 1+2**: ทำพร้อมกัน (saves 2-3 days, higher risk)

**ผมแนะนำ**: (B) — Phase 1 ลด pain ทันที 80%, validate ทฤษฎีก่อน. Phase 2-3 ค่อยทำใน sprint ถัดไป

#### Q5 — Batch API
**ตัวเลือก:**
- (A) ทำ Phase 4 (saves 50% AI cost)
- (B) Skip — Phase 1-3 ก็ลด cost เยอะแล้ว, simpler

**ผมแนะนำ**: (B) Skip — เพิ่ม complexity 24h SLA, do it ถ้า cost ยังสูงหลัง Phase 3

#### Q6 — Test Corpus
**ตัวเลือก:**
- (A) Copy DB จาก prod (user's real files) — accuracy แต่ privacy
- (B) Generate synthetic corpus
- (C) ใช้ public dataset (เช่น Thai Wikipedia subset)

**ผมแนะนำ**: (A) สำหรับ admin user เท่านั้น (bossok2546@gmail.com), DB ของ user คนอื่นห้ามใช้

#### Q7 — Gemini JSON Mode
**ตัวเลือก:**
- (A) ใช้ทันที (response_schema) — JSON parse fail < 0.1%, ต้อง check ว่า Gemini 3 Flash รองรับ
- (B) Skip — pure prompt + Pydantic validate + retry ก็พอ

**ผมแนะนำ**: (A) — quality win, low cost. Verify support ใน Phase 0

---

## 📌 Notes for เขียว (นักพัฒนา)

### Critical reminders

1. **ห้ามลบ code เก่า** — ทุกฟังก์ชันเดิม (_cluster_files, enrich_all_files, generate_suggestions, _build_graph_v1) ต้องอยู่ครบ. ใช้ feature flag routing เท่านั้น. ลบใน v11.1.0 หลัง stable 2 weeks
2. **Schema additive only** — ห้ามลบ column, ห้าม rename. ถ้าต้องเปลี่ยน semantic → เพิ่ม column ใหม่
3. **Feature flag default OFF** — ทุก flag ใหม่ตั้ง default `false`. Production จะเปิดทีละขั้น (rollout plan)
4. **Logging แน่นๆ** — เพิ่ม `logger.info` ทุก phase entry/exit + duration + LLM call count. ต้องดูใน Fly logs ได้ว่าตอนนี้อยู่ phase ไหน
5. **Async/await ทุก LLM call** — เคยพลาดได้ ระวัง deadlock with semaphore
6. **อ่าน code เก่ารอบๆ ก่อนแก้** — pattern v7.5.0 migrations เป็น reference สำคัญ ([database.py:807-832](../../backend/database.py#L807-L832))
7. **ห้ามแตะ vector_search.py TF-IDF** — system นั้นทำงานดี ดูแค่ comment header เพิ่ม
8. **Test ก่อน push** — รัน `scripts/test_organize_quality.py` baseline + feature ตรงทุก phase
9. **Cache buster bump** — ทุกครั้งที่แก้ frontend JS หรือเพิ่ม cache buster ใน HTML 5 ไฟล์
10. **Commit message** — `feat(organize): phase X — [description] [v11.0.0-alpha.X]` + `Author-Agent: เขียว (Khiao)`

### Gotchas

- **Gemini text-embedding API**: HTTP endpoint ต่างจาก chat. ตรวจ docs ก่อนใช้
- **HDBSCAN ใน Docker**: ต้องการ libstdc++ + numpy ก่อน install. ถ้า slim image → ต้อง apt-get install build-essential
- **UMAP randomness**: set `random_state=42` ทุก instantiation เพื่อ determinism
- **NetworkX vs igraph**: ใช้ NetworkX (Python-native), ไม่ต้อง igraph (C lib, complex install)
- **python-louvain vs networkx.community**: ใช้ python-louvain (มาตรฐานกว่า)
- **JSON parsing**: ถ้า Gemini ตอบ markdown ```json ... ``` → `call_llm_json()` มี logic strip อยู่แล้ว ([llm.py:88-118](../../backend/llm.py#L88-L118))
- **Thai filename in .md**: `_safe_filename()` strip non-alphanumeric → อาจมี collision สำหรับ Thai. ตรวจ uniqueness ด้วย file_id suffix ถ้าจำเป็น
- **Drive sync timing**: push_summary_to_drive_if_byos เป็น best-effort. ถ้า fail → log warning, ไม่ raise
- **DB session timeout**: Long-running organize อาจ hit aiosqlite timeout. Commit ตอน checkpoint = สำคัญ
- **Frontend watchdog**: ของเดิม v10.0.9 มี 4-min phase stall + 16-min hard. Phase ใหม่ "embedding" อาจใช้ 1-2 นาทีต่อเนื่อง → ตรวจว่า activity signature เปลี่ยน

### Style

- Type hints ทุก function (v10.x convention)
- Thai comments สำหรับ business logic (WHY), English ID/var (convention)
- Docstring บอกว่าทำอะไร + reference design decision
- Error messages → ใช้ unified error response format (v10.0.14):
  ```python
  raise HTTPException(status_code=400, detail={"error": {"code": "X", "message": "Y"}})
  ```

### What "เขียวห้ามทำ"

- ❌ ห้ามแก้ Plan เอง — ส่ง message ไป for-แดง.md ถ้าเจอปัญหา
- ❌ ห้าม implement Phase 2 ก่อน Phase 1 (sequential)
- ❌ ห้ามทำ "phase 1.5" / unauthorized feature
- ❌ ห้าม merge to master ก่อน ฟ้า approve
- ❌ ห้าม disable feature flag ของ phase ก่อนหน้าเพื่อให้ test ผ่าน
- ❌ ห้ามแตะ `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`
- ❌ ห้ามเขียน tests (ฟ้าทำ)

---

## 📅 Timeline (Recommended)

> **Note**: User บอก "ค่อยๆทำไม่ต้องรีบ" — ให้ priority quality > speed. ตัวเลขด้านล่างคือ minimum, ถ้าใช้เวลามากกว่านี้เพื่อ test ครบ → OK

```
Week 1 — Phase 0 (Foundation)
  Day 1-2:  Dependencies + schema migration + feature flag
  Day 3:    embeddings.py + cache logic
  Day 4:    test_organize_quality.py baseline + smoke
  Day 5:    Documentation + memory updates + ฟ้า review checkpoint

Week 2 — Phase 1 (Hybrid Clustering)
  Day 1-2:  clustering.py + importance.py
  Day 3:    Route ใน organizer + frontend phase metadata
  Day 4:    Migration script + run on test corpus
  Day 5:    Quality benchmark + ฟ้า review

[STOP CHECKPOINT — ถาม user ว่าจะทำ Phase 2-3 ต่อไหม]

Week 3-4 — Phase 2 (Structured Summary) + Phase 3 (Entity Graph)
  Week 3:   Phase 2 (5 วัน)
  Week 4:   Phase 3 (5 วัน)

Week 5 — Phase 4 (Polish + Cleanup)
  Day 1-2:  Cache + checkpoint
  Day 3:    Re-enable dedup + small things cleanup
  Day 4-5:  Release notes + final QA + version 11.0.0 ship

Total: 4-5 weeks (ใส่ buffer แล้ว)
```

### Rollout Plan (หลัง deploy ทุก phase)

- **Day 1**: Phase X deployed, feature flag OFF
- **Day 2-3**: Enable for admin user (`bossok2546@gmail.com`) only via per-user check
- **Day 4-7**: Monitor logs, fix bugs found
- **Day 8**: Enable for all users
- **Day 15**: Cleanup legacy code (next minor version)

---

## 🔖 Memory Updates ที่ต้องทำตอนเสร็จ Plan

หลัง user approve plan นี้:

1. **`.agent-memory/current/pipeline-state.md`** → state = "plan_approved · v11.0.0 refactor · ready for เขียว Phase 0"
2. **`.agent-memory/current/active-tasks.md`** → add task "v11.0.0 Phase 0"
3. **`.agent-memory/current/last-session.md`** → log session
4. **`.agent-memory/history/session-logs/2026-05-17-แดง.md`** → full session log
5. **`.agent-memory/communication/inbox/for-เขียว.md`** → notify เขียว ว่า plan พร้อม, อ่าน plans/organize-refactor-v11.md

---

## 📚 References

### Industry Standards
- BERTopic: https://maartengr.github.io/BERTopic/
- BERTopic algorithm: https://maartengr.github.io/BERTopic/algorithm/algorithm.html
- BERTopic best practices: https://maartengr.github.io/BERTopic/getting_started/best_practices/best_practices.html
- RAPTOR paper: arXiv:2401.18059
- Microsoft GraphRAG: https://microsoft.github.io/graphrag/
- GraphRAG methods: https://microsoft.github.io/graphrag/index/methods/
- LangChain summarization: https://python.langchain.com/docs/tutorials/summarization/
- LangChain map-reduce: https://python.langchain.com/docs/how_to/summarize_map_reduce/
- LlamaIndex PropertyGraphIndex: https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/
- Clustering with OpenAI + HDBSCAN + UMAP: https://dylancastillo.co/posts/clustering-documents-with-openai-langchain-hdbscan.html
- Dropbox Dash architecture: https://blog.bytebytego.com/p/how-dropbox-built-an-ai-product-dash
- RAG Anti-Patterns: https://www.kapa.ai/blog/rag-gone-wrong-the-7-most-common-mistakes-and-how-to-avoid-them
- LLM RAG Anti-Patterns (Context Stuffing): https://medium.com/@2nick2patel2/llm-rag-anti-patterns-stop-stuffing-context-c79c11a2529d
- PostHog LLM trace clustering: https://posthog.com/blog/llm-analytics-clustering-how-it-works
- GraphRAG implementation guide 2026: https://blog.premai.io/graphrag-implementation-guide-entity-extraction-query-routing-when-it-beats-vector-rag-2026/
- RAPTOR improvement: https://superlinked.com/vectorhub/articles/improve-rag-with-raptor

### Internal References
- v10.0.14 health audit findings: this conversation
- Plan template: `.agent-memory/plans/README.md`
- Conventions: `.agent-memory/contracts/conventions.md`
- Architecture: `.agent-memory/project/architecture.md`
- Database migrations pattern: [backend/database.py:807-832](../../backend/database.py#L807-L832)

---

## ✅ Approval Checklist (สำหรับ user)

ก่อน approve plan นี้ ขอให้ตรวจ:

- [ ] เห็นด้วยกับ design philosophy (BERTopic + RAPTOR + GraphRAG pattern)?
- [ ] เห็นด้วยกับ feature flag rollback strategy?
- [ ] เห็นด้วยกับ timeline 4-5 สัปดาห์?
- [ ] เห็นด้วยกับ Docker image +80MB?
- [ ] ตัดสินใจ Open Questions Q1-Q7 (ดูข้างบน) — หรือ "เริ่มตามที่แดงแนะนำ"?
- [ ] เห็นด้วยกับการแบ่ง phase + stop checkpoint หลัง Phase 1?
- [ ] OK กับ migration script รันก่อน deploy phase 1?

ถ้า ✅ ทั้งหมด → ส่งต่อให้เขียว เริ่ม Phase 0

ถ้ามี ❌ → แดง revise plan ตาม feedback

---

**Plan Author:** 🔴 แดง (Daeng)
**Plan Date:** 2026-05-17
**Plan Status:** `draft` — รอ user approve
