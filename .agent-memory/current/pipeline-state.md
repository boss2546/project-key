# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current State: `idle` ✅ (ready for next plan — 2026-05-07)

**Master HEAD:** `7a1625d` v9.2.1 (= origin/master, deployed to Fly.io)
**APP_VERSION:** 9.2.1
**Production:** ✅ live at https://personaldatabank.fly.dev/

**Working tree:** clean (after this commit)

---

## 🔴 Pending plan (queued — รอ user approve)

### v9.3.0 Share Context Pack — `plan_pending_approval`
- **Plan:** [plans/share-pack-v9.3.0.md](../plans/share-pack-v9.3.0.md)
- **Author:** แดง (Daeng) — 2026-05-07
- **Effort:** เขียว ~3 วัน + ฟ้า ~1 วัน
- **Risk:** 🟠 Medium-High — privacy-sensitive
- **Architecture:** Email whitelist + view/clone permission + audit log + revocable + TTL 30 วัน default
- **Schema:** 2 ตารางใหม่ (`pack_shares` + `pack_share_accesses`)
- **API:** 6 endpoints ใหม่ + 1 HTML page (`/shared/pack/{token}`)
- **Frontend:** share modal + manager + recipient view (standalone shared_pack.html)
- **Plan limits:** Free 1/เดือน, Starter 50/เดือน, Admin unlimited
- **Privacy guards:** confirmation checkbox + locked-pack guard + email whitelist + revoke + audit
- **Open Questions:** Q1-Q8 มี default ทุกข้อ (ดูใน plan section "Open Questions")

**Pending action:** User review plan + approve → state `plan_approved` → เขียวเริ่ม build

---

## ✅ Recently Released (เรียงจากใหม่ไปเก่า)

| Version | Feature | Released | Plan archive |
|---|---|---|---|
| **v9.2.1** | Parallel uploads + UX progress fixes + mobile audit | 2026-05-07 | [archive/2026-05-07-ui-mobile-fixes-v9.2.1.md](../plans/archive/2026-05-07-ui-mobile-fixes-v9.2.1.md) |
| **v9.2.0** | AI Pack Builder (clarify→propose→confirm + 3-LLM flow) | 2026-05-07 | [archive/2026-05-07-ai-pack-builder-v9.2.0.md](../plans/archive/2026-05-07-ai-pack-builder-v9.2.0.md) |
| **v9.1.0** | Raw File Vault (file_kind=processed/vault_only + promote) | 2026-05-07 | [archive/2026-05-07-raw-vault-v9.1.0.md](../plans/archive/2026-05-07-raw-vault-v9.1.0.md) |
| **v9.0.1** | Context Pack correctness fixes (vector sync + is_locked + cluster_ids) | 2026-05-07 | [archive/2026-05-07-context-pack-correctness-v9.0.1.md](../plans/archive/2026-05-07-context-pack-correctness-v9.0.1.md) |
| **v9.0.0** | Multimodal expansion (HEIC/HEIF/GIF/BMP/TIFF + audio/video AI ingest) | 2026-05-06/07 | [archive/2026-05-07-multimodal-expansion-v9.0.0.md](../plans/archive/2026-05-07-multimodal-expansion-v9.0.0.md) |
| **v8.2.0** | Admin Panel (`/admin` + 10 endpoints + audit log) | 2026-05-06 | [archive/2026-05-05-admin-system-v8.2.0.md](../plans/archive/2026-05-05-admin-system-v8.2.0.md) |
| **v8.1.0** | Google Sign-In (PKCE S256) | 2026-05-04 | [archive/google-login-v8.1.0.md](../plans/archive/google-login-v8.1.0.md) |
| **v8.0.0–8.0.7** | LINE Bot Integration (10 intents + Rich Menu) | 2026-05-04 | [archive/line-bot-v8.0.0.md](../plans/archive/line-bot-v8.0.0.md) |
| **v7.6.0** | Email service (Resend) + signed download URLs | 2026-05-02 | [archive/foundation-v7.6.0.md](../plans/archive/foundation-v7.6.0.md) |
| **v7.5.0** | Upload Resilience (OCR + map-reduce + 14 formats) | 2026-05-02 | [archive/2026-05-02-upload-resilience-v7.5.0.md](../plans/archive/2026-05-02-upload-resilience-v7.5.0.md) |

---

## 🚧 Active Blockers

ไม่มี — ดู [blockers.md](blockers.md)

---

## 📊 Pipeline States (อ้างอิง)

| State | ความหมาย | ขั้นตอนต่อไป |
|-------|---------|-------------|
| `idle` | ไม่มีงานใน pipeline | รอ user มอบหมาย → เริ่ม planning |
| `planning` | แดงกำลังวาง plan | รอแดงเสร็จ → user approve |
| `plan_pending_approval` | Plan เสร็จ รอ user approve | User บอก approve/revise |
| `plan_approved` | Plan approved พร้อม build | เขียวเริ่ม build |
| `building` | เขียวกำลังเขียน code | รอเขียวเสร็จ |
| `built_pending_review` | Code เสร็จ รอ ฟ้า review | ฟ้าเริ่ม review |
| `reviewing` | ฟ้ากำลัง review + เขียน tests | รอฟ้าเสร็จ |
| `review_passed` | Review ผ่าน รอ user merge | User merge → done |
| `review_needs_changes` | Review เจอปัญหา ต้องกลับไปเขียว | เขียวแก้ → กลับ review |
| `done` | Merged + deployed | กลับ idle |
| `paused` | Pipeline หยุดชั่วคราว | รอ blocker resolve |

---

## ⚠️ กฎสำคัญ

1. **ห้าม 2 features อยู่ใน pipeline พร้อมกัน** (default — user override ได้เป็น parallel)
2. **State เปลี่ยน → update ที่นี่ทันที** — ห้ามรอ
3. **Agent ที่ไม่ใช่ owner ปัจจุบัน** → อย่าเริ่มทำงาน รอจนกว่าจะถึงรอบตัวเอง
4. **User เป็นคนสั่งให้เริ่ม pipeline ใหม่ (กลับ idle → planning)**

---

## 📜 Long-term Backlog (deferred — ไม่มี timeline)

- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user) — Phase 2 of BYOS
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications (currently 5-min poll)
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
- [ ] [BACKLOG-005] Custom domain (replace `personaldatabank.fly.dev`)
- [ ] [BACKLOG-006] Submit Google OAuth verification (ก่อน public >100 users)
- [ ] [BACKLOG-007] Frontend migration to React/Vue (per FE-001 — defer)

---

## 🧪 Pre-launch gates ที่ user ต้องทำเอง

- 📝 Submit Google OAuth verification (openid+email+profile, 1-3 วัน, ฟรี)
- 🔁 Token rotation (LINE + Resend) — Browser Worker logs exposure risk
- 📱 LINE Rich Menu deploy script (post-deploy: `python scripts/setup_line_rich_menu.py`)

---

**Last updated:** 2026-05-07 — แดง (Daeng) cleanup session
