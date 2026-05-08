# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview สั้นๆ
> Pipeline ตอนนี้ = `plan_pending_approval` 🔴 (v9.3.0 Stability Patch)

---

## 🔄 Current Pipeline

**State:** `plan_pending_approval` 🔴 (v9.3.0 Stability Patch — 2026-05-08)
**Master HEAD:** `dbf08cf` v9.3.0 Phase A foundation (ahead of origin)
**APP_VERSION:** 9.3.0
**Production:** 🟡 v9.2.1 live · master ahead of origin (Share Pack + Phase A foundation รอ deploy)
**Active plan:** [plans/v9.3.0-stability-patch.md](../plans/v9.3.0-stability-patch.md)

---

## 🔴 Pending Plan (รอ user approve)

- **v9.3.0 Stability Patch** — [plans/v9.3.0-stability-patch.md](../plans/v9.3.0-stability-patch.md)
  - 5 fixes: cache-bust + iOS Phase 1+2 + JWT warn-log + Drive invalid_grant + memory cleanup
  - Effort: เขียว ~2 ชม + ฟ้า ~1 ชม = half-day
  - Mode: 3-in-1 single-agent

## 📋 In-flight (uncommitted, will be picked up by patch)

- 5 HTML cache-bust changes (need correction `?v=9.2.2` → `?v=9.3.0`)
- landing.css iOS Phase 3 fallback (committed below master HEAD = correct)
- iOS plan + spec file untracked → จะ rename + finalize ใน patch

## 🟢 Plans archived (post-Share Pack ship)

- ~~v9.3.0 Share Context Pack~~ → `plans/archive/2026-05-08-share-pack-v9.3.0.md` (shipped 5 commits in master, included in `dbf08cf` chain)

---

## ✅ Recent Releases (เรียงจากใหม่ไปเก่า — ดูรายละเอียดใน pipeline-state.md)

- **v9.3.0 Phase A** (2026-05-08, master) — UI foundation tokens + canonical atoms (committed `dbf08cf`)
- **v9.3.0 Share Pack** (2026-05-08, master) — Pack share/clone (committed `9fa78f8` chain)
- **v9.2.1** (2026-05-07, deployed) — Parallel uploads + UX progress + mobile audit
- **v9.2.0** (2026-05-07) — AI Pack Builder
- **v9.1.0** (2026-05-07) — Raw File Vault
- **v9.0.1** (2026-05-07) — Context Pack correctness
- **v9.0.0** (2026-05-06/07) — Multimodal expansion (HEIC/audio/video)
- **v8.2.0** (2026-05-06) — Admin Panel
- **v8.1.0** (2026-05-04) — Google Sign-In
- **v8.0.0–8.0.7** (2026-05-04) — LINE Bot

---

## 🧪 Pre-launch Gates (ที่ user ต้องทำเอง — ไม่ใช่ code work)

- 📝 Submit Google OAuth verification (openid+email+profile, 1-3 วัน, ฟรี — สำคัญก่อน public >100 users)
- 🔁 Token rotation (LINE + Resend) — Browser Worker logs exposure
- 📱 LINE Rich Menu deploy: `fly ssh console -C "python scripts/setup_line_rich_menu.py"`

---

## 📜 Long-term Backlog (deferred — no timeline)

- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user)
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications (currently 5-min poll)
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
- [ ] [BACKLOG-005] Custom domain (replace `personaldatabank.fly.dev`)
- [ ] [BACKLOG-006] Submit Google OAuth verification (pairs with pre-launch gate above)
- [ ] [BACKLOG-007] Frontend migration to React/Vue (per FE-001 — defer)
- [ ] [BACKLOG-009] **Re-enable duplicate detection** — fix UnicodeEncodeError surrogate bug. Flip `_DEDUP_DISABLED = False` in [backend/duplicate_detector.py](../../backend/duplicate_detector.py) after adding pytest case. See [decisions.md DUP-004](../project/decisions.md#dup-004) + [plan v9.3.2](../plans/v9.3.2-disable-duplicate-detection.md).

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
Default sequential (1 feature at a time):
1. User เลือก feature
2. แดง วาง plan
3. User approve plan
4. เขียว build code
5. ฟ้า review + tests
6. User approve review
7. Merge → ย้ายไป Completed

3-in-1 single-agent mode (per user authorization):
- 1 agent ทำทั้ง plan + build + review (ไม่มี inter-session reload)
- Used for: v9.0.1, v9.2.0
```

Default = sequential. 3-in-1 = explicit user override only.

---

**Last updated:** 2026-05-07 — แดง (Daeng) cleanup session
