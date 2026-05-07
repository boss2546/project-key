# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview สั้นๆ
> Pipeline ตอนนี้ = `idle` ✅

---

## 🔄 Current Pipeline

**State:** `idle` — พร้อมรับ feature ใหม่
**Master HEAD:** `7a1625d` v9.2.1 (= origin/master, deployed)
**APP_VERSION:** 9.2.1
**Production:** ✅ live https://personaldatabank.fly.dev/

---

## 🔴 Pending Plan (รอ user approve)

- **v9.3.0 Share Context Pack** — [plans/share-pack-v9.3.0.md](../plans/share-pack-v9.3.0.md)
  - Email whitelist + view/clone permission + audit + revocable + TTL
  - Effort: เขียว ~3 วัน + ฟ้า ~1 วัน
  - Privacy-sensitive — ต้อง user approve ก่อน build

---

## ✅ Recent Releases (เรียงจากใหม่ไปเก่า — ดูรายละเอียดใน pipeline-state.md)

- **v9.2.1** (2026-05-07) — Parallel uploads + UX progress + mobile audit
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
