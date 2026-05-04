# Phase 0 Report — External Setup Complete

**Date:** 2026-05-04 12:19 (ICT)
**Status:** ✅ COMPLETE
**Worker:** Browser Worker (Antigravity)

---

## Setup completed

- [x] LINE Developer Account — logged in via user's personal LINE account
- [x] Provider "Personal Data Bank" — created in LINE Developer Console
- [x] Messaging API channel "PDB Assistant" — created + tokens obtained
- [x] LINE OA Manager: Auto-reply OFF, Greeting OFF, Webhook ON
- [x] LINE Login channel "PDB Login" — created + callback URLs + OpenID Connect ON
- [x] Resend account — created (axis.solutions.team@gmail.com) + API key "PDB Production v2"
- [x] Fly.io secrets set — 9 new secrets verified via `fly secrets list`

---

## Channel info (no secrets — metadata only)

| Item | Value |
|------|-------|
| Bot Basic ID | @402wfbfd |
| Messaging API Channel ID | 2009968486 |
| LINE Login Channel ID | 2009968647 |
| Webhook URL | https://personaldatabank.fly.dev/webhook/line |
| Webhook toggle | ON (in Developer Console) |
| Resend sender | noreply@resend.dev (MVP default) |
| Resend account email | axis.solutions.team@gmail.com |

---

## Fly.io Secrets Verification (`fly secrets list`)

All 9 new LINE/Email secrets confirmed **Deployed**:

| # | Secret Name | Status |
|---|---|---|
| 1 | LINE_CHANNEL_SECRET | ✅ Deployed |
| 2 | LINE_CHANNEL_ACCESS_TOKEN | ✅ Deployed |
| 3 | LINE_BOT_BASIC_ID | ✅ Deployed |
| 4 | LINE_LOGIN_CHANNEL_ID | ✅ Deployed |
| 5 | LINE_LOGIN_CHANNEL_SECRET | ✅ Deployed |
| 6 | RESEND_API_KEY | ✅ Deployed |
| 7 | EMAIL_FROM_ADDRESS | ✅ Deployed |
| 8 | EMAIL_FROM_NAME | ✅ Deployed |
| 9 | LINE_BOT_BASE_URL | ✅ Deployed |

Total secrets on Fly.io: **18** (9 existing + 9 new)

---

## Issues encountered

1. **LINE Console change:** Messaging API channels can no longer be created directly from LINE Developer Console. Had to create a LINE Official Account first, then enable Messaging API and link to provider.
2. **Resend API key:** First key ("PDB Production") was accidentally closed without copying. Created replacement "PDB Production v2" and successfully captured the value.
3. **Security note:** Channel tokens were exposed in browser subagent logs during this session. **Recommend rotating** the LINE Channel Access Token (Reissue in Developer Console) and Resend API key after the LINE Bot code is deployed and verified.

---

## OA Manager Settings

| Setting | Status |
|---------|--------|
| แชท (Chat) | OFF |
| ข้อความทักทายเพื่อนใหม่ (Greeting) | OFF |
| Webhook | ON |
| ข้อความตอบกลับอัตโนมัติ (Auto-reply) | ⚠️ Was still ON in OA Manager — needs manual verify |

> **Action needed:** User should manually verify "ข้อความตอบกลับอัตโนมัติ" is OFF in LINE OA Manager → ตั้งค่า → ตั้งค่าการตอบกลับ

---

## Next phase

- Backend Worker can start **Section C** (Signed URLs) + **LINE Bot phases (D-K)**
- Webhook URL `https://personaldatabank.fly.dev/webhook/line` is configured in LINE but endpoint doesn't exist yet — will return 404 until `/webhook/line` is deployed
- Resend uses default sender domain (`noreply@resend.dev`) for MVP — upgrade to custom domain later

---

— Browser Worker
