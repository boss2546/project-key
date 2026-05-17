# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current State: `review_passed · phase_1 · stop_checkpoint` 🔵 (v11.0.0 Organize Refactor)

**Active task:** v11.0.0 — Organize Pipeline Refactor (Hybrid Clustering + Structured Summary + Entity Graph)
**Active plan:** [`.agent-memory/plans/organize-refactor-v11.md`](../plans/organize-refactor-v11.md)
**Plan Author:** 🔴 แดง (Daeng) — Plan created 2026-05-17 · UMAP fix added 2026-05-17 (3-in-1 mode)
**Current Agent:** 🔵 ฟ้า (Fah) — Phase 1 review complete · APPROVE
**Status:** `review_passed · stop_checkpoint` — ฟ้า อนุมัติ Phase 1 แล้ว 2026-05-17 · รอ user validate + start Phase 2
**Master HEAD:** `5e41ac5` (v10.0.21 · button rename "จัดระเบียบ"→"วิเคราะห์" · tests + reports committed)
**Production:** ✅ **v10.0.21 deployed live** with Phase 1 code (USE_HYBRID_CLUSTERING=false → behavior unchanged)

### Approved Defaults (Q1-Q7)
| # | Question | Approved |
|---|---|---|
| Q1 | Embedding model | Gemini text-embedding-001 |
| Q2 | HDBSCAN min_cluster_size | 2 |
| Q3 | Embedding storage | BLOB ใน SQLite |
| Q4 | Phase strategy | Phase 1 only first (stop checkpoint หลัง Phase 1) |
| Q5 | Batch API | Skip |
| Q6 | Test corpus | Admin user's prod copy → local test DB |
| Q7 | Gemini JSON mode | Use immediately |

### Workflow Decisions
- **Docker**: Skip local Docker → Use `flyctl deploy --remote-only` for deploy verification (user approved workflow B)
- **Branch**: master (project convention) + feature flags default OFF for safety
- **Pace**: ค่อยๆ ทำ ช้าๆ + เน้น test ละเอียด (user directive)

### Phase 0 Progress (24 milestones total across 4 phases)
- [x] Step 0.1 — Add deps to requirements-fly.txt + verify imports in venv ✅ (commit 559ddd9)
- [x] Step 0.2 — Create backend/embeddings.py + Verify gate ✅ (commit bde0715, partial — API-deferred)
- [x] Step 0.3 — Schema migration (additive) + Verify gate ✅ (commit 48b4d95, 3 scenarios)
- [x] Step 0.4 — Feature flag system + Verify gate ✅ (commit 545c006, 5 tests)
- [x] Step 0.5 — Test harness baseline + Verify gate ✅ (commit ca63115, CLI verified)
- [x] **Phase 0 COMPLETE** — built_pending_review by 🔵 ฟ้า
- [x] **Phase 0 APPROVED** — ✅ APPROVE by 🔵 ฟ้า (2026-05-17) — 86/86 unit tests PASS, 5/5 E2E PASS

### Phase 1 Progress — built_pending_review by 🔵 ฟ้า
- [x] Step 1.1 — Create backend/clustering.py ✅ (commit Phase 1 · 404 lines · UMAP fix Option A)
- [x] Step 1.2 — Create backend/importance.py ✅ (130 lines · 5-factor heuristic)
- [x] Step 1.3 — Route in organizer.py ✅ (organize_files + organize_new_files both routed)
- [x] Step 1.4 — Update frontend phase metadata ✅ (5 new PHASE_META entries)
- [x] ฟ้า LOW findings folded in ✅ (empty_indices removed + EMBEDDING_MODEL consolidated)
- [x] UMAP fix Option A in plan + clustering.py ✅ (MSG-V11-UMAP-EDGE-CASE resolved)
- [x] **Deploy v10.0.18 prod with Phase 1 code** ✅ (flags OFF → no behavior change)
- [x] **Phase 1 review by ฟ้า** — ✅ APPROVE 2026-05-17 · 161/161 tests PASS
- [ ] **🛑 Stop Checkpoint** — user enable USE_HYBRID_CLUSTERING=true + validate cluster quality in prod
- [ ] **Phase 2** — Structured Summary (เริ่มหลัง user validate + confirm)

### Plan Summary
- **Scope:** 4-phase refactor (~4-5 สัปดาห์), 51+ touchpoints
- **Goal:** Scale organize-new จาก 50 ไฟล์ → 1,000+ ไฟล์, ลด AI cost 10×, ลดเวลา 6-9×
- **Strategy:** BERTopic + RAPTOR + Microsoft GraphRAG patterns (industry standard)
- **Safety:** Feature flags + additive schema + sequential phases + rollback ทุก phase

### Phase Roadmap
- **Phase 0** — Foundation (deps, schema, flags, embeddings) — 1-2 วัน
- **Phase 1** — Hybrid Clustering (embeddings + HDBSCAN + LLM label) — 1-2 วัน
- **🛑 Stop Checkpoint** — Validate Phase 1 results ก่อนทำต่อ
- **Phase 2** — Structured Summary (merge sum+tag in 1 call) — 1-2 วัน
- **Phase 3** — Entity Graph + Leiden Community Detection — 2-3 วัน
- **Phase 4** — Polish + Cache + Cleanup — 1-2 วัน

### Open Decisions (รอ user)
1. Embedding model: Gemini (A) / OpenAI (B) / Local (C)
2. HDBSCAN min_cluster_size: 2 (A) / 3 (B) / Adaptive (C)
3. Storage: BLOB (A) / File (B)
4. Phase order: Sequential (A) / Phase 1 only first (B) / Parallel 1+2 (C)
5. Batch API: Yes (A) / Skip (B)
6. Test corpus: Prod copy (A) / Synthetic (B) / Public (C)
7. Gemini JSON mode: Use now (A) / Skip (B)

---

## 📜 Previous State (v10.0.14 deploy completed)

**Master HEAD:** `9dc5ae6`
**Production:** ✅ **v10.0.14 deployed live**
**Completed in this session:**
- v10.0.13 — badge "บางส่วนถูกตัด" removal + drive OAuth scope drift fix
- v10.0.14 — Phase A-D fix bundle: rate-limit login (5 fails/15min) + retry-on-chunk-fail + structured error response + cleanup (dead code, httpx context, env override)

**Health audit findings remaining:**
- Plaintext password footgun (ALLOW_ADMIN_VIEW_PASSWORD env, default false)
- LINE/Email user login fails (Safari autofill issue, user-side)
- BYOS push log flood (synthetic QA leftover files in DB — recommended cleanup)

---

## 🎯 Previous State: `idle` 🟢 (no active feature in pipeline)

**Master HEAD:** `7a2f84a` (v9.4.8 · 2026-05-12 08:54 +07)
**APP_VERSION:** **9.4.8**
**Production:** ✅ **v9.4.8 deployed live** ที่ `https://personaldatabank.fly.dev`
- Worker uptime ~11 นาที (เพิ่ง deploy v9.4.8) · queue ว่าง · success_24h = 100% · error_24h = 0
- avg_extract_sec_by_class: class 1 = 1.0s · class 2 = 13.27s · class 3 = 74.29s (post-cap healthy)

**Mode:** ปัจจุบันไม่มี feature ใน pipeline · pipeline state = idle · พร้อมรับงานใหม่

---

## ⚠️ Pipeline drift notice (2026-05-11 → 2026-05-12)

**Memory ไฟล์เคย stale หลายรอบ** — sync ใหม่ 2026-05-12 (ฟ้า) ให้ตรง master HEAD จริง.

**Session gap:** ระหว่าง 2026-05-10 ถึง 2026-05-12 มี **8 versions shipped ใน 3-in-1 mode** (user รันตรงผ่าน Claude Code Opus 4.7 1M context · ไม่ผ่าน sequential pipeline แดง→เขียว→ฟ้า · เห็นจาก commit `Co-Authored-By` trailer):

| Version | Commit | Date | Scope |
|---|---|---|---|
| v9.4.0 | `aa26ed2` … `ee07e27` (~7 commits) | 2026-05-10 | Upload Queue + Visible Progress (worker · UI tray · 4 endpoints · WAL) |
| v9.4.0.1 | `2c93a1d` | 2026-05-10 | UI hotfix · tray position + toast text |
| v9.4.0.2 | `d81369c` | 2026-05-10 | UI hotfix · opaque BG + suppress queue toast |
| v9.4.1 | `a314a42` | 2026-05-10 | Comprehensive Drive cleanup async + UI feedback |
| v9.4.2 | `f45ab96` | 2026-05-10 | Gemini 2.5 Flash + Vision + truthful classification |
| v9.4.3 | `c738ff0` | 2026-05-10 | LINE UX 5 fixes + nonce + countdown timer |
| v9.4.4 | `f2e707e` | 2026-05-10 | i18n error CODE boundary + reprocess hardening |
| v9.4.5 | `015628c` | 2026-05-10 | Worker heartbeat task + startup recovery + cancel endpoint |
| v9.4.6 | `9f94765` | 2026-05-11 | Progress+cancel main loop ref + always-on Cancel button |
| v9.4.7 | `e658c74` | 2026-05-11 | Filename 255-byte ext4 limit (Thai filename UTF-8 overflow fix) |
| v9.4.8 | `7a2f84a` | 2026-05-12 | DELETE guard + ai_pack filter + rolling avg cap |

**Status ของ formal ฟ้า review:** ❌ ไม่มี · `MSG-V940-UPLOAD-QUEUE` ใน `inbox/for-ฟ้า.md` ยังค้างใน 🔴 New แต่ของ deploy + ใช้งานจริงไป 11 versions แล้ว · gap นี้ยอมรับเป็น operational reality.

---

## 📋 Known unresolved issues (จาก audit 2026-05-12 by ฟ้า)

| # | Issue | Severity | Status |
|---|---|---|---|
| **P9** | Duplicate detection disabled ตั้งแต่ v9.3.2 — `_DEDUP_DISABLED = True` ใน `backend/duplicate_detector.py` | 🟡 MED | BACKLOG-009 · pending re-enable + pytest case |
| **P5** | Untracked files หลายกลุ่มใน working tree (smoke scripts ใหม่ · screenshots · `data/`/`datame/`) | 🟡 MED | Track A2/A3 (in progress) |
| **P4** | v9.4.2/4/5/6/7/8 ไม่มี plan files (shipped ใน 3-in-1 mode) | 🟢 LOW | Defer · ไม่กระทบ production · ทำ retro changelog ถ้าจำเป็น |
| **P1** | v9.4.0 Truthfulness Contract TC-1..6 ไม่เคย E2E audit · ของ deploy แล้ว · worker health green | 🟢 LOW | Defer · prod stable 24h+ · ทำตอนแตะ upload pipeline รอบหน้า |

**ที่เคยอยู่ใน Issue list · resolved แล้ว:**
- ✅ **P7 (PDF 219.6s slow)** — v9.4.8 rolling avg cap (class 2: 60s outlier cap) · prod stat ลด 219.6 → 13.27s
- ✅ **P3 (pipeline-state stale)** — sync วันนี้ (ไฟล์ที่คุณกำลังอ่าน)

---

## 📜 Reference — historical state snapshots

ก่อนหน้า v9.4.x · pipeline เคยอยู่ใน sequential mode ปกติ (แดง→เขียว→ฟ้า). ดู git log สำหรับ chronology + ดู `plans/` archive สำหรับ formal plans ที่ shipped:

- v9.3.5 BYOS Reconnect UX FINAL — เป็น last formal sequential pipeline pass (ฟ้า re-review APPROVE 2026-05-10)
- v9.3.4 LLM/AI surrogate boundary — 3-in-1 mode
- v9.3.3 extraction surrogate guard — 3-in-1 mode
- v9.3.2 disable duplicate detection — 3-in-1 mode (current BACKLOG-009)
- v9.3.0 Phase A-E UI foundation + Share Pack — sequential
- v9.2.0 AI Pack Builder — sequential
- v9.1.0 Raw File Vault — sequential
- v9.0.1 Context Pack correctness — 3-in-1 mode
- v8.x line bot + admin + google login — sequential

---

**Last sync:** 2026-05-17 by 🟢 เขียว (Khiao) — **Phase 0 COMPLETE** (5/5 steps verified) · awaiting ฟ้า review · master HEAD `ca63115`
