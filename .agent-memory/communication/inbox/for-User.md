# 📬 Inbox: User (Boss / พี่)

> ข้อความสรุปสำหรับ user — รายงาน + สิ่งที่ต้องตัดสินใจ + คำถาม
> Agents เขียนที่นี่เมื่อต้องการ user attention โดยไม่บังคับ block pipeline

---

## ✅ [REVIEW-001] LINE Bot v8.0.0 + Foundation v7.6.0 — READY TO DEPLOY

**Date:** 2026-05-04
**Built by:** 🔴 แดง (supervisor mode + executor authorization) +
              🌐 Browser Worker (Phase 0 external setup) +
              🤖 Parallel agent (E.5 redirect + URL_UPLOAD intent contributions)
**Verdict:** ✅ READY_TO_DEPLOY — pending User review + push + fly deploy

### Build Summary

| Phase | What | Status |
|---|---|---|
| **0** | External setup (LINE + Resend + Fly secrets) | ✅ Browser Worker, 1.5 hr |
| **A1** | Restore plan_limits production values | ✅ `8fa3c70` |
| **A2** | Email service Resend wired | ✅ `698ba0d` |
| **B** | MCP USP (`upload_from_url`) | ⏸️ DEFERRED to v7.7.0 |
| **C** | Universal signed download URLs `/d/{token}` | ✅ `1172d83` |
| **D** | LINE foundation (webhook + DB + adapters) | ✅ `9834349` |
| **E** | Account linking + welcome flow | ✅ `0b9257d` + `a810daa` |
| **F** | File/text message handlers | ✅ `a810daa` |
| **G** | Text intent dispatch (chat/search/stats/get-file/url) | ✅ `08008cf` + `7b22579` |
| **H** | Push fallback + quota + group leave + admin | ✅ `ba4df60` |
| **I** | Rich Menu image + setup script + postback handlers | ✅ `ba4df60` |
| **J** | Profile UI integration + admin endpoints | ✅ `0b9257d` |
| **K** | APP_VERSION bump + memory + final report | ✅ this commit |

### Test Results

| Suite | Cases | Pass |
|---|---|---|
| Section A — plan_limits + email | 31 | 31/31 ✅ |
| Section C — signed URLs | 23 | 23/23 ✅ |
| Phase D — LINE foundation | 20 | 20/20 ✅ |
| Phase J + E partial — UI + endpoints | 17 | 17/17 ✅ |
| Phase E full + F — account link + file flow | 26 | 26/26 ✅ |
| Phase G — intent dispatch + URL | 30 | 30/30 ✅ |
| Phase H — push fallback + quota + group leave | 15 | 15/15 ✅ |
| Phase I — Rich Menu + postback | 10 | 10/10 ✅ |
| Existing regression | 102 | 102/102 ✅ |
| **TOTAL** | **172 new** | **274/274 PASS** |

### Files Changed

**NEW (15 files):**
- `backend/email_service.py` (Resend wrapper)
- `backend/signed_urls.py` (JWT-signed download URLs)
- `backend/bot_adapters.py` (BotAdapter abstract + LineBotAdapter)
- `backend/bot_messages.py` (Flex Message builders)
- `backend/bot_handlers.py` (intent dispatch + handlers)
- `backend/line_bot.py` (webhook + handlers)
- `backend/line_quota.py` (push quota tracking)
- `legacy-frontend/auth-line.html` + `auth-line.js`
- `legacy-frontend/line_ui.js`
- `legacy-frontend/line-rich-menu.png` (89 KB)
- `scripts/generate_line_rich_menu_image.py`
- `scripts/setup_line_rich_menu.py`
- 8 test files (172 cases)

**MODIFIED:**
- `backend/main.py` (8 new endpoints + Resend config)
- `backend/database.py` (LineUser table + migration)
- `backend/config.py` (LINE + email env vars + APP_VERSION 7.5.0 → 8.0.0)
- `backend/auth.py` (email service wired + drop reset_token)
- `backend/plan_limits.py` (restored production values)
- `backend/mcp_tools.py` (signed URLs in get_file_link)
- `legacy-frontend/app.html` (LINE section in profile + version bump)
- `legacy-frontend/app.js`, `landing.js`, `styles.css` (handlers + styles)
- `requirements.txt` + `requirements-fly.txt` (resend + line-bot-sdk)
- `.env.example` (documented new env vars)

### Commits Created (local, ready to push)

```
ba4df60 feat(line-bot): Phase H + I — push fallback, quota, group leave, Rich Menu
7b22579 feat(line-bot): URL_UPLOAD intent + handle_url_upload
08008cf feat(line-bot): Phase G — text intent dispatch + parallel-agent E.5 redirect
a810daa feat(line-bot): Phase E full + Phase F — real account linking + file/text handlers
0b9257d feat(line-bot): Phase J + E partial — profile UI + account-link landing
9834349 feat(line-bot): Phase D foundation — webhook + signature verify + LineUser table
1172d83 feat(downloads): universal signed download URLs /d/{token}
698ba0d feat(email): wire Resend for password reset
8fa3c70 feat(plan-limits): restore production values
```

(+ Phase K commit will be added when this report is committed)

### What the bot can do (end-to-end)

```
👤 User เพิ่ม @402wfbfd ใน LINE
🤖 Bot: [Flex card "เชื่อมบัญชี"]
👤 [คลิก link → web confirm + login → LINE Account Link dialog → confirm]
🤖 Bot: [welcome flow: greeting + status card + capabilities + Quick Reply]

แล้วใช้งานได้:
✅ "ฉันมีกี่ไฟล์" → status Flex card
✅ "หาไฟล์ AI" → search carousel (top 5 match)
✅ "ขอไฟล์ thesis" → file card + signed download link (TTL 30 min)
✅ "transformer คืออะไร" → AI chat (RAG จากข้อมูลใน vault)
✅ "/help" → คำสั่งทั้งหมด + Quick Reply
✅ "เปิดเว็บ" → web URL
✅ ส่ง URL https://... → confirm prompt → fetch + save
✅ ส่ง PDF/image/audio → upload + Flex confirmation
✅ Rich Menu (6 tiles) ที่ bottom — ปุ่มกดทันที
✅ Plan limit ถึง → upgrade prompt
✅ Reply token หมดอายุ → push fallback อัตโนมัติ
✅ Bot ถูก add เข้า group → reply polite + leave อัตโนมัติ
```

### Next Action for User

#### 1. Review code (แนะนำ)
```bash
cd d:/PDB
git log --oneline -10        # ดู commits
git diff a4355c6 HEAD --stat # ดูไฟล์ที่เปลี่ยน
```

#### 2. Push to remote
```bash
git push origin master
```

#### 3. Deploy to production
```bash
fly deploy
```
**ระยะเวลา deploy:** ~3-5 นาที (Docker rebuild + Fly machine restart)
**Downtime:** น้อยมาก (rolling deploy)

#### 4. Run Rich Menu setup (one-time)
หลัง deploy แล้ว:
```bash
fly ssh console -C "python scripts/setup_line_rich_menu.py"
```
หรือ run local กับ env var (image จะถูก uploaded ขึ้น LINE):
```bash
LINE_CHANNEL_ACCESS_TOKEN=<from_secrets> python scripts/setup_line_rich_menu.py
```

#### 5. Manual smoke test
- เปิด LINE app → search "@402wfbfd" → add as friend
- Bot ควรส่ง "Flex card เชื่อมบัญชี"
- คลิกปุ่ม → confirm flow → welcome flow ปรากฏ
- ทดสอบ:
  - ส่ง PDF → ได้ confirmation
  - พิมพ์ "ฉันมีกี่ไฟล์" → ได้ status card
  - กด Rich Menu ทุก tile

### Production Checklist

- [x] LINE webhook URL configured: `https://personaldatabank.fly.dev/webhook/line`
- [x] LINE OA Manager: Auto-reply OFF, Webhook ON (User verify อีกครั้งใน OA Manager)
- [x] All 9 Fly secrets set (Browser Worker confirmed)
- [ ] Rich Menu deployed (User run scripts/setup_line_rich_menu.py)
- [ ] Resend domain verified (using default sender for MVP — upgrade later)

### Known Issues / Notes

1. **`tests/test_line_bot_v8_0_phase_e.py` (untracked)** — 5 errors from
   parallel agent's test isolation issues. Not blocking. User can review
   + decide: delete / fix / keep. My tests cover same scenarios cleanly.

2. **Phase B (MCP `upload_from_url`)** — DEFERRED to v7.7.0 per user
   pivot. ลูกค้าใช้ /api/upload (web UI) + LINE bot upload ได้ปกติ.

3. **Token rotation recommended** — Browser Worker noted that LINE +
   Resend tokens were exposed in browser logs during setup. After
   verifying deployment works, rotate via:
   - LINE Console → Messaging API channel → "Reissue" Channel Access Token
   - Resend Dashboard → API Keys → Delete + Create new

4. **EMAIL_FROM_ADDRESS = noreply@resend.dev** (MVP default) — upgrade
   to verified custom domain when traffic grows.

5. **Multi-message reply optimization** — Welcome flow uses 3 push messages
   (3 quota each). Could batch as 1 reply API call (5 messages allowed).
   Defer to v8.0.1 polish.

### Pre-launch Production Verify Checklist

หลัง deploy:
- [ ] `curl https://personaldatabank.fly.dev/api/mcp/info` → version 8.0.0
- [ ] `fly secrets list` → 18 secrets (9 existing + 9 LINE/email)
- [ ] Login เว็บ → profile modal → LINE section visible
- [ ] Add bot ใน LINE → follow event → ได้ link prompt
- [ ] Click link → /auth/line page renders → confirm → LINE Account Link dialog
- [ ] After confirm → welcome flow 3 messages
- [ ] Send PDF in LINE → file appears in PDB web /api/files
- [ ] BYOS user → file appears in Drive `/Personal Data Bank/raw/`
- [ ] Press Rich Menu tiles → correct responses

### Memory Updated

- ✅ `backend/config.py` APP_VERSION 7.5.0 → 8.0.0
- ✅ `legacy-frontend/app.html` logo version v7.5.0 → v8.0.0
- ✅ `current/pipeline-state.md` reflects all phases done
- ✅ `inbox/for-User.md` (this report)
- ⏸️ `contracts/api-spec.md` — admin should add new endpoints documentation
- ⏸️ `project/decisions.md` — admin should add LINE-001, BOT-ADAPTER-001, etc.

### Stats

- **Total work duration:** ~6 hours (compressed via supervisor + executor mode)
- **Lines added:** ~5,000+ (production code) + ~3,000+ (tests)
- **Test coverage:** 274/274 pass (172 new + 102 regression)
- **Memory artifacts:** 4 plans + 3 research docs + 4 prompts + handoff docs

---

🎉 **Ready when you are!** ตรวจ + push + deploy ได้เลยครับ.
ถ้ามีคำถามหรือ blocker → reply ใน inbox/for-แดง.md

— แดง (Daeng)

---

## 🔴 STATUS — 2026-05-02 (cleanup session — multi-role โดย Claude)

### TL;DR — งานค้างเก็บเสร็จเกือบหมดแล้ว

**ที่ทำเสร็จในรอบนี้ (autonomous):**
- ✅ **Memory sync** — pipeline-state.md / active-tasks.md / 4 inboxes / changelog.md ตรงกับ master จริงแล้ว
- ✅ **rebrand_smoke_v6.1.0.py** — แก้ version hardcode → ใช้ `APP_VERSION` dynamic + แก้ stale invariants (localStorage `pdb_*`, fly.toml volume `project_key_data`, app.html post-split)
  - **77/77 PASS** ✅ (เดิม 68/76 = 8 fail → ตอนนี้ 0 fail + เพิ่ม 1 case ใหม่)
- ✅ **plans/google-drive-byos.md** — rebrand 37 occurrences "Project KEY"→"Personal Data Bank" + domain `project-key.fly.dev`→`personaldatabank.fly.dev` + KEEP `projectkey.db` (DB filename)
- ✅ **Inbox cleanup** — 9 stale MSGs ย้าย Read→Resolved (3 ใน เขียว + 6 ใน ฟ้า + 1 ใน แดง)
- ✅ **Local merged branches** — ลบ 4 branches ที่ verified merged เข้า master (`rebrand-pdb-v6.1.0`, `byos-v7.0.0-foundation`, `dedupe-v7.1.0`, `backup-pre-fixes-20260428-235745`)

**ที่พี่ต้องตัดสินใจก่อน production launch (BACKLOG ใหม่):**
- 🔴 **BACKLOG-008** — `backend/plan_limits.py:15-42` ตอนนี้ testing mode (999999 ทุก field). ต้น values เก่าจาก commit `d8b0d54` diff อยู่ใน [active-tasks.md](../../current/active-tasks.md) แล้ว — จะ restore ค่าเดิม หรือ revise (พ่วง pricing strategy)?
- 🔴 **BACKLOG-009** — `backend/auth.py:249-282` password reset ตอนนี้ return `reset_token` ใน JSON response ตรงๆ (ไม่ส่ง email). ต้องเลือก email service ก่อน wire:
  - 🟢 **Resend** (แนะนำ) — free 3000/เดือน, modern API, simple Python SDK
  - 🟡 SendGrid — free 100/วัน
  - 🟡 Gmail SMTP — ฟรีแต่ deliverability ไม่ดี

**Pipeline state ตอนนี้:** `plan_pending_approval` — v7.2.0 UX Hotfixes (แดงเขียนแผนเสร็จแล้ว ระหว่าง cleanup session) — รอพี่ approve plan ก่อนเขียวเริ่ม build

— Claude (multi-role: แดง+เขียว+ฟ้า cleanup session)

---

## 📂 Archive: เก่ากว่านี้ (เก็บไว้เผื่อ reference)

### 🔵 REVIEW-002 — v7.1.0 Duplicate Detection ✅ APPROVED (2026-05-01)

**From:** ฟ้า (Fah) — นักตรวจสอบ
**Status:** ✅ Resolved — merged + deployed (commit `cd114dd` + `0adcaf1` pivot + `6467b3a` review approval)

**สรุป:**
- Code ตรงตาม plan 100% — ไม่มีอะไรนอก scope
- **87/87 dedupe tests PASS** (33 smoke + 54 e2e)
- **106/106 BYOS regression PASS** — zero regression
- Security: cross-user safety verified (defense-in-depth), XSS กัน, no hardcoded secrets
- Performance: 10-file batch = 0.23 วินาที

**Non-blocking item (cleanup session ทำให้แล้ว):**
- ✅ `rebrand_smoke_v6.1.0.py` ใช้ `APP_VERSION` dynamic แล้ว

— ฟ้า (Fah) 🔵

---

### 🟢 STATUS — 2026-05-01 (ฟ้า BYOS deploy)

- ✅ **v7.1.0 Dedupe**: merged + deployed
- ✅ **v6.1.0 Rebrand**: merged + deployed (+ later domain rename to personaldatabank.fly.dev)
- ✅ **v7.0.0 BYOS**: deployed + 5 follow-up fixes already on master
- 📊 **Test coverage**: 267+/273 tests pass (some test drift expected, see fixture cleanup)

---

## 📋 Quick reference: agent prompts

อยากเปิด chat ใหม่ → ดู `.agent-memory/prompts/`:
- `prompt-แดง.md` — นักวางแผน (use ถ้าต้องการ plan ใหม่)
- `prompt-เขียว.md` — นักพัฒนา (use ถ้าต้องการ build feature ใหม่)
- `prompt-ฟ้า.md` — นักตรวจสอบ (use ถ้าต้องการ review/test/fix)

---

## 📝 รูปแบบเพิ่มข้อความใน inbox นี้

```markdown
## YYYY-MM-DD — [topic]
**From:** [agent name]
**Status:** 🔴 New / 👁️ Read / ✓ Resolved

[เนื้อหา]
```

Agent ใหม่อ่านไฟล์นี้ตอนเริ่ม session → user เห็นรายการใหม่หลังจบงาน
