# 📋 External Setup Checklist — Phase 0 ✅ COMPLETE

**Owner:** 🤖 Browser Worker (Antigravity) — completed 2026-05-04 12:19 ICT
**Actual time:** ~1.5 hours
**Pre-requisites:** Domain `personaldatabank.fly.dev` running on Fly.io ✅

> ✅ Phase 0 COMPLETE — All 9 secrets deployed to Fly.io — Backend Worker can start Phase D-K

---

## 🎯 ภาพรวม — ต้อง setup อะไรบ้าง

| # | Service | Purpose | Time | Cost |
|---|---|---|---|---|
| 1 | LINE Developer Account | สมัครเข้าระบบ LINE Developers | ~5 min | Free |
| 2 | LINE Provider | กลุ่ม channels ของเรา | ~2 min | Free |
| 3 | LINE Messaging API channel | Bot สำหรับรับ/ส่งข้อความ | ~10 min | Free (Communication plan) |
| 4 | LINE Login channel | OAuth สำหรับ account linking | ~5 min | Free |
| 5 | Resend account + DNS verify | ส่ง password reset email | ~30 min (DNS prop) | Free 3000/mo |
| 6 | Fly.io secrets | เก็บ tokens บน production | ~5 min | Free |
| 7 | (Optional) ngrok | Test webhook local | ~3 min | Free |

---

## STEP 1 — LINE Developer Account (5 นาที)

### 1.1 สมัคร LINE Developer
1. ไป https://developers.line.biz/
2. คลิก "Log in" → ใช้ LINE personal account ของคุณ login
3. ครั้งแรก จะให้กรอก:
   - Developer name
   - Email (ใช้ axis.solutions.team@gmail.com หรืออื่น)
   - Country: Thailand
4. **Accept Terms** + Submit

### 1.2 ✅ Done criteria
- เข้า https://developers.line.biz/console/ ได้
- เห็นหน้า Console ว่างๆ (ยังไม่มี provider)

---

## STEP 2 — สร้าง Provider (2 นาที)

> **Provider** = container สำหรับ channels ของ business เดียวกัน

### 2.1 Create Provider
1. ใน Console → คลิก "Create"
2. กรอก:
   - **Provider name:** `Personal Data Bank`
   - (อื่นๆ optional)
3. Click "Create"

### 2.2 ✅ Done criteria
- เห็น Provider "Personal Data Bank" ใน Console

---

## STEP 3 — Messaging API Channel (10 นาที)

> **Channel นี้ = bot ที่รับ/ส่งข้อความ + รับ webhook**

### 3.1 Create channel
1. ใน Provider → คลิก "Create a Messaging API channel"
2. กรอก:
   - **Channel type:** Messaging API
   - **Provider:** Personal Data Bank
   - **Channel icon:** อัปโหลดรูป (square 1:1, ≥40KB) — ใช้ logo PDB
   - **Channel name:** `PDB Assistant`
   - **Channel description:** `ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ`
   - **Category:** Computers and Internet (or similar)
   - **Subcategory:** Chatbot
   - **Email:** axis.solutions.team@gmail.com
3. Accept terms
4. Click "Create"

### 3.2 Get tokens (สำคัญมาก — copy ให้ครบ)
1. เปิด channel ที่สร้าง
2. ไปแท็บ "Basic settings" → copy:
   - **Channel ID** (ตัวเลข ~10 หลัก)
   - **Channel secret** (string ~32 chars) — กด "Show"
3. ไปแท็บ "Messaging API" → scroll ลง:
   - **Channel access token (long-lived):** กด "Issue" → copy ทันที (จะเห็นแค่ครั้งเดียว)
   - **Bot basic ID** (เริ่มด้วย `@`) — เช่น `@123abcde`

### 3.3 Disable Auto-reply (สำคัญ!)
1. ไปแท็บ "Messaging API" → "LINE Official Account features"
2. คลิก link ไป OA Manager
3. **Settings → Response settings:**
   - Auto-reply messages: **OFF** (กัน LINE ตอบเองทับ bot)
   - Greeting message: **OFF** (เราจะใช้ webhook handle follow event)
   - Webhook: **ON**
4. Save

### 3.4 ✅ Done criteria — เก็บไว้ใน password manager / safe note:
```
LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINE_BOT_BASIC_ID=@xxxxxxxx
```

⚠️ **อย่าโพสต์ tokens ในแชท/Telegram/email ใดๆ** — เก็บใน 1Password หรือ secure note

---

## STEP 4 — LINE Login Channel (5 นาที)

> **Channel แยก** สำหรับ OAuth account linking — ห้ามใช้ Messaging API channel ทำ login

### 4.1 Create channel
1. กลับไป Provider "Personal Data Bank"
2. คลิก "Create a LINE Login channel"
3. กรอก:
   - **Channel type:** LINE Login
   - **App types:** ✓ Web app, ✓ Native app (uncheck) — แค่ web พอ
   - **Channel name:** `PDB Login`
   - **Channel description:** `เข้าสู่ระบบ Personal Data Bank ด้วย LINE`
   - **App icon:** ใช้ logo PDB (เหมือน Messaging API)
   - **Email:** axis.solutions.team@gmail.com
4. Click "Create"

### 4.2 Configure callback URL
1. เปิด channel ที่สร้าง
2. ไปแท็บ "LINE Login" → "Callback URL":
   - เพิ่ม: `https://personaldatabank.fly.dev/auth/line/callback`
   - (สำหรับ local test) เพิ่ม: `http://localhost:8000/auth/line/callback`
3. ไปแท็บ "OpenID Connect" — ✅ enable
4. Save

### 4.3 Get tokens
1. ไปแท็บ "Basic settings" → copy:
   - **Channel ID** (ตัวเลข)
   - **Channel secret** (string)

### 4.4 ✅ Done criteria เก็บใน safe note:
```
LINE_LOGIN_CHANNEL_ID=xxxxxxxxxx
LINE_LOGIN_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## STEP 5 — Resend Account + DNS Verify (~30 min)

> **Resend** = email service ที่ส่ง password reset email — ต้อง verify domain ก่อนใช้งาน

### 5.1 สมัคร Resend
1. ไป https://resend.com/signup
2. Sign up ด้วย email (อาจเป็น axis.solutions.team@gmail.com)
3. Verify email
4. Login → Dashboard

### 5.2 Add domain
1. Dashboard → "Domains" → "Add Domain"
2. Enter: `personaldatabank.fly.dev`
3. Click "Add"
4. Resend จะแสดง DNS records ที่ต้อง add:
   - **TXT record** (SPF) — เช่น `v=spf1 include:amazonses.com ~all`
   - **CNAME records** (DKIM) — 3 records:
     - `resend._domainkey` → `resend._domainkey.amazonses.com`
     - (อื่นๆ ตามที่ Resend ระบุ)

### 5.3 Add DNS records
**ถ้าใช้ Fly.io จัดการ DNS:**
- Fly.io ไม่ provide DNS hosting สำหรับ subdomain ของ `.fly.dev`
- ต้องใช้ **custom domain แทน** (เช่น `app.personaldatabank.com`) แล้ว verify domain นั้น
- **Workaround:** ใช้ domain อื่นที่ control DNS ได้ (Cloudflare/Namecheap/etc.) หรือ
- **Alternative:** ใช้ Resend's default sender domain (`onboarding@resend.dev`) สำหรับ MVP — แต่ deliverability จะแย่ลง

> ⚠️ **Action needed:** User ตัดสินใจ:
> - 🟢 ใช้ Resend default sender (`noreply@resend.dev`) — ไม่ต้อง DNS — ทำต่อได้ทันที
> - 🟡 ซื้อ custom domain (`personaldatabank.com`) แล้ว verify — ใช้เวลา ~30 min DNS prop
> - 🔴 ข้าม email service ก่อน (skip BACKLOG-009) — password reset ยังไม่ผ่าน email — จะกระทบการ launch

**แนะนำ:** Option 🟢 (Resend default) สำหรับ MVP → upgrade ภายหลัง

### 5.4 Get API key
1. Dashboard → "API Keys" → "Create API Key"
2. Name: `PDB Production`
3. Permission: "Sending access" (read+write)
4. Click "Add"
5. Copy API key (เห็นแค่ครั้งเดียว!) — เก็บใน safe note

### 5.5 ✅ Done criteria
```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM_ADDRESS=noreply@resend.dev   # หรือ noreply@yourdomain.com ถ้า custom
EMAIL_FROM_NAME=Personal Data Bank
```

---

## STEP 6 — Set Fly.io Secrets (5 นาที)

> เก็บ tokens ทั้งหมดเป็น Fly secrets (ไม่ commit ลง git)

### 6.1 Open terminal ใน project root
```bash
cd /path/to/PDB
```

### 6.2 Verify Fly CLI authenticated
```bash
fly auth whoami
```
ควรเห็น email ของคุณ — ถ้าไม่ → `fly auth login`

### 6.3 Set secrets ทีละกลุ่ม

**LINE Messaging API:**
```bash
fly secrets set \
  LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxx \
  LINE_BOT_BASIC_ID=@xxxxxxxx
```

**LINE Login:**
```bash
fly secrets set \
  LINE_LOGIN_CHANNEL_ID=xxxxxxxxxx \
  LINE_LOGIN_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Email service:**
```bash
fly secrets set \
  RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  EMAIL_FROM_ADDRESS=noreply@resend.dev \
  EMAIL_FROM_NAME="Personal Data Bank"
```

**Bot base URL:**
```bash
fly secrets set LINE_BOT_BASE_URL=https://personaldatabank.fly.dev
```

### 6.4 Verify
```bash
fly secrets list
```
ควรเห็นทุก secret ที่ set (Fly จะ mask values — ไม่แสดง full value)

### 6.5 ✅ Done criteria
- `fly secrets list` แสดงครบ 8 secrets:
  - LINE_CHANNEL_SECRET
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_BOT_BASIC_ID
  - LINE_LOGIN_CHANNEL_ID
  - LINE_LOGIN_CHANNEL_SECRET
  - RESEND_API_KEY
  - EMAIL_FROM_ADDRESS
  - EMAIL_FROM_NAME
  - LINE_BOT_BASE_URL

⚠️ **หลัง set secrets, Fly จะ restart machines อัตโนมัติ** (downtime ~30 sec)

---

## STEP 7 — (Optional) ngrok สำหรับ Local Test (3 นาที)

> ใช้เฉพาะเมื่อ executor ต้องการ test webhook local ก่อน deploy

### 7.1 Install ngrok
- Download: https://ngrok.com/download
- หรือ `brew install ngrok` (macOS)
- หรือ `winget install ngrok` (Windows)

### 7.2 Sign up + auth
- Sign up: https://dashboard.ngrok.com/signup (free)
- Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
- `ngrok config add-authtoken <YOUR_TOKEN>`

### 7.3 Use
```bash
ngrok http 8000
```
จะได้ URL เช่น `https://abc123.ngrok-free.app`

→ Set ใน LINE Messaging API channel "Webhook URL" temporarily สำหรับ local testing

---

## 🎯 Final Verification Checklist

ก่อน signal "approve CP-0" → ตรวจ:

- [ ] เข้า LINE Developer Console ได้
- [ ] สร้าง Provider "Personal Data Bank" สำเร็จ
- [ ] Messaging API channel สร้าง + tokens เก็บไว้แล้ว
- [ ] Auto-reply messages: OFF, Webhook: ON ใน OA Manager
- [ ] LINE Login channel สร้าง + tokens เก็บไว้แล้ว
- [ ] Callback URL ตั้งค่า: `https://personaldatabank.fly.dev/auth/line/callback`
- [ ] Resend account + API key ได้แล้ว
- [ ] Fly.io secrets set ครบ 8-9 secrets
- [ ] (Optional) ngrok พร้อมใช้

---

## 🚨 Security Reminders

1. ⚠️ **อย่า commit `.env` ลง git** — `.gitignore` ครอบคลุมไว้แล้วแต่ check ทุกครั้ง
2. ⚠️ **อย่า share tokens ในแชท** — ใช้ password manager / 1Password
3. ⚠️ **ห้าม screenshot tokens** — แล้วโพสต์ที่ไหน
4. ⚠️ **Channel access token = full bot authority** — ถ้าหลุด → bot โดน hijack
5. ⚠️ **Resend API key** — ถ้าหลุด → spam emails ผิด domain
6. ✅ ถ้าหลุด → Rotate ทันที:
   - LINE: Issue new token + revoke old (ใน LINE console)
   - Resend: Delete + Create new API key
   - แล้ว `fly secrets set` ใหม่

---

## 📞 Help & Troubleshooting

### LINE channel ไม่ทำงาน
- Verify webhook URL = HTTPS (HTTP ไม่รับ)
- Verify channel access token issued (long-lived, ไม่ expired)
- Check OA Manager: Auto-reply OFF + Webhook ON

### Resend DNS ไม่ verify
- รอ DNS propagation ~5-60 นาที
- Use https://www.whatsmydns.net/ ตรวจ TXT/CNAME
- ถ้า > 24 ชม. ยังไม่ verify → support@resend.com

### Fly secrets set แล้ว machine restart fail
- `fly status` — ดู machine state
- `fly logs` — ดู error
- ถ้า config error → revert + retry

---

## ✅ เมื่อทำครบ — แจ้ง executor agent

User สามารถบอก executor agent ว่า:
> "Phase 0 external setup ครบแล้ว — ทุก secret อยู่ใน Fly secrets, channels active, webhooks configured. Approve CP-0 — start Phase A1."

→ Executor agent เริ่ม Phase A1 (Restore plan_limits)

---

**End of checklist.** เก็บไฟล์นี้ไว้เป็น reference ก่อน setup จริง
