# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview สั้นๆ
> Pipeline ตอนนี้ = `plan_pending_approval` 🔴 (v11.0.0 Organize Refactor)

---

## 🔄 Current Pipeline

**State:** `built_pending_review · phase_0` 🔵
**Master HEAD:** `ca63115` (Phase 0 complete)
**APP_VERSION:** 10.0.14 (still deployed — v11 flags default OFF, not deployed yet)
**Production:** ✅ v10.0.14 live (untouched by Phase 0 commits)
**Active plan:** [organize-refactor-v11.md](../plans/organize-refactor-v11.md) — Major pipeline refactor
**Plan Author:** 🔴 แดง (Daeng) — 2026-05-17
**Current Agent:** 🟢 เขียว (Khiao) — Phase 0 build complete, awaiting ฟ้า review
**Mode:** Sequential pipeline (แดง→เขียว→ฟ้า) — user requested thorough planning

### Active plan summary

**Feature:** Organize Pipeline Refactor (v10.0.14 → v11.0.0)
**Why:** organize-new พังที่ ~50 ไฟล์ (LLM context overflow + O(N²) graph + 2× duplicate calls)
**Solution:** Industry-standard pipeline (BERTopic + RAPTOR + Microsoft GraphRAG)
**Effort:** ~4-5 weeks, 4 phases, 51+ touchpoints, feature-flagged rollout

### Phase 0 (Foundation) — ✅ COMPLETE 2026-05-17

| Step | Commit | Verify |
|---|---|---|
| 0.1 Deps | `559ddd9` | ✅ 6 imports |
| 0.2 embeddings.py | `bde0715` | ✅ 5 manual tests |
| 0.3 Schema migration | `48b4d95` | ✅ 3 scenarios |
| 0.4 Feature flags | `545c006` | ✅ 5 tests |
| 0.5 Test harness | `ca63115` | ✅ CLI works |

**Next:** ฟ้า review (MSG-V11-PHASE0-HANDOFF) → APPROVE → Phase 1

---

## 📋 Known Backlog (จาก ฟ้า audit 2026-05-12)

### 🟡 Medium priority
- [ ] **BACKLOG-009: Re-enable Duplicate Detection** — `_DEDUP_DISABLED = True` ใน [backend/duplicate_detector.py](../../backend/duplicate_detector.py)
  - **Why disabled:** v9.3.2 (2026-05-08) — UnicodeEncodeError surrogate crash บน PDF text edge case
  - **Why ready to re-enable:** v9.3.3 + v9.3.4 ใส่ `strip_surrogates` ที่ extraction + LLM + ai_ingest boundary แล้ว
  - **Steps:** verify guard ครอบคลุม → เพิ่ม pytest case lone surrogate → flip flag → smoke
  - **Effort:** ~1-2 ชม. รวม audit + test + flip
  - **Risk:** 🟢 LOW (low-blast-radius · 1 flag)

### 🟢 Low priority (housekeeping)
- [ ] **Update contracts** — `contracts/api-spec.md` + `contracts/data-models.md` ยังขาด v9.4.0+ schema (7 cols + WAL) + endpoints (`/api/upload-status`, `/api/upload/{id}/retry|dismiss-error|cancel`, `/api/healthz/queue`)
  - **When:** ทำตอนแตะ upload pipeline รอบหน้า · ไม่ต้องทำตอนนี้
- [ ] **Update `project/overview.md`** — ยังบอก production = v6.0.0 + ในdev = v7.0.0 BYOS · จริง = v9.4.8 ทั้งคู่
  - **When:** ทำพร้อม contracts update

### 📜 Long-term backlog (deferred · no timeline)
- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user)
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications (currently 5-min poll)
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
- [ ] [BACKLOG-005] Custom domain (replace `personaldatabank.fly.dev`)
- [ ] [BACKLOG-006] Submit Google OAuth verification (pairs with pre-launch gate)
- [ ] [BACKLOG-007] Frontend migration to React/Vue (per FE-001 — defer)

---

## ✅ Recent Releases (เรียงจากใหม่ไปเก่า — รายละเอียดใน pipeline-state.md)

- **v9.4.8** (2026-05-12, deployed) — DELETE guard + ai_pack filter + rolling avg cap
- **v9.4.0–9.4.7** (2026-05-10/11, deployed) — Upload Queue + Visible Progress + 7 hotfix iterations (3-in-1 mode)
- **v9.3.5** (2026-05-10, deployed) — BYOS Reconnect UX FINAL (last formal sequential pass)
- **v9.3.0–9.3.4** (2026-05-08, deployed) — UI Foundation tokens + Stability patches (surrogate boundary)
- **v9.0–v9.2** (2026-05-07) — Context Pack correctness + Raw Vault + AI Pack Builder + Parallel uploads
- **v8.x** — LINE Bot + Admin + Google Sign-In

---

## 🧪 Pre-launch Gates (user-side · ไม่ใช่ code work)

- 📝 Submit Google OAuth verification (openid+email+profile, 1-3 วัน, ฟรี — ก่อน public >100 users)
- 🔁 Token rotation (LINE + Resend) — ถ้ามี exposure
- 📱 LINE Rich Menu deploy: script removed in 2026-05-14 cleanup; restore from git history (`git show 8a89eee~1:scripts/setup/setup_line_rich_menu.py`) before re-running

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
Sequential (แดง→เขียว→ฟ้า · 1 feature at a time):
1. User เลือก feature → แดง วาง plan
2. User approve plan → เขียว build code
3. เขียว เสร็จ → ฟ้า review + tests
4. User approve review → Merge → ย้ายไป Completed

3-in-1 single-agent mode (per user authorization):
- 1 agent ทำทั้ง plan + build + review (Claude Code Opus 4.7 1M context)
- Used for: hot iterations, hotfix flurries, small patches
- Recent use: v9.4.0 → v9.4.8 (11 versions)
```

Default = sequential. 3-in-1 = explicit user override (ปกติทำเมื่อ velocity > governance สำคัญกว่า).

---

**Last updated:** 2026-05-12 — 🔵 ฟ้า (Fah) · Track A1 pipeline-state drift fix
