# 06 — External API Setup Guide

> **Purpose:** Step-by-step การสร้าง account + ตั้งค่า external services ที่ PDB ใช้
> **Coverage:** Gemini / OpenRouter / Google OAuth (Login + Drive) / Stripe / Resend / LINE
> **Time:** 1-2 ชม. ครั้งแรก (รอ verification ของบางตัว 2-4 สัปดาห์)

---

## ตารางสรุป

| Service | Required? | Cost | Setup Time | Verification Time |
|---|---|---|---|---|
| **Google AI Studio** (Gemini) | ✅ Critical | Free 1500 RPD → paid | 5 min | Instant |
| **OpenRouter** | ✅ Critical | Pay-per-token | 5 min | Instant |
| **Google Cloud Console** (OAuth) | 🟡 Optional | Free | 30 min | 2-4 weeks (production mode) |
| **Stripe** | 🟡 Optional | 2.9% + 30¢/tx | 30 min | Instant test, ~1 day live |
| **Resend** | 🟡 Optional | Free 100/day | 10 min | Instant |
| **LINE Developers** | 🟡 Optional | Free | 30 min | Instant |
| **Fly.io** | ✅ Critical | $2-5/mo Hobby | 15 min | Instant |

---

## 1. Google AI Studio (Gemini Multimodal)

**Used for:** Audio/video/image extraction via Gemini Files API (`ai_ingest.py`)

### 1.1 Create API Key

1. Visit https://aistudio.google.com/
2. Sign in with Google account
3. Click **"Get API key"** (top right)
4. Click **"Create API key in new project"** หรือเลือก existing project
5. Copy the key (starts with `AIza...`)

### 1.2 Verify Free Tier

- **Free quota:**
  - 15 requests per minute (RPM)
  - 1,500 requests per day (RPD)
  - 1M tokens per minute (TPM)
- พอสำหรับ ~50-100 free tier users

### 1.3 Upgrade to Paid (เมื่อ scale)

1. Visit https://aistudio.google.com/app/apikey
2. Click **"Set up Billing"**
3. Add Google Cloud billing account
4. After billing: **360 RPM, ∞ RPD**

### 1.4 Set in PDB

```bash
flyctl secrets set GOOGLE_API_KEY=AIza...
flyctl secrets set GEMINI_FILE_MODEL=gemini-2.5-flash
```

**Test:**
```bash
# Upload an MP3 file via UI — should extract transcription
```

---

## 2. OpenRouter (LLM Gateway)

**Used for:** Chat, organize, summary, JSON parsing (`llm.py` → `call_llm()` + variants)

### 2.1 Create Account

1. Visit https://openrouter.ai/
2. Sign up (Google / GitHub / email)
3. Add credit balance ($5 minimum)

### 2.2 Generate API Key

1. Visit https://openrouter.ai/keys
2. Click **"Create Key"**
3. Name: `pdb-production`
4. Copy key (starts with `sk-or-v1-`)

### 2.3 Verify Model Access

PDB ใช้:
- `google/gemini-3-flash-preview` (LLM_MODEL + LLM_MODEL_PRO)

ตรวจสอบ access:
```bash
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer sk-or-v1-..." \
  | grep gemini
```

### 2.4 Set Provider Routing

PDB ใช้ provider order ใน `llm.py`:
```python
provider={"order": ["Google"], "allow_fallbacks": True}
```

ไม่ต้องตั้งค่าเพิ่ม — handled in code

### 2.5 Set in PDB

```bash
flyctl secrets set OPENROUTER_API_KEY=sk-or-v1-...
```

### 2.6 Pricing

Gemini 3 Flash via OpenRouter (approximate):
- $0.075 / 1M input tokens
- $0.30 / 1M output tokens

Typical PDB usage per user/month:
- 50 chat queries × ~3K tokens = $0.05
- 30 summaries × ~5K tokens = $0.05
- ≈ **$0.10-0.30/user/month**

---

## 3. Google Cloud Console (OAuth + Drive BYOS)

**Used for:** Google Sign-In + Google Drive BYOS feature

### 3.1 Create Google Cloud Project

1. Visit https://console.cloud.google.com/
2. Click project dropdown → **"New Project"**
3. Name: `personal-data-bank`
4. Create

### 3.2 Enable APIs

Navigate to **APIs & Services → Library**, enable:
- **Google Drive API** (สำหรับ BYOS)
- **People API** (สำหรับ Sign-In profile)

### 3.3 Configure OAuth Consent Screen

1. Navigate to **APIs & Services → OAuth consent screen**
2. User type: **External**
3. Fill in:
   - App name: `Personal Data Bank` (หรือชื่อของคุณ)
   - User support email: your@email.com
   - App logo: (optional, 120x120 PNG)
   - App domain: `https://yourdomain.com`
   - Privacy policy: `https://yourdomain.com/privacy` ⚠️ Required
   - Terms of service: `https://yourdomain.com/terms` ⚠️ Required
   - Developer contact email
4. **Scopes** (click "Add or Remove Scopes"):
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/drive.file` (Phase 1 — non-sensitive, free)
5. **Test users** (during testing mode):
   - Add up to 100 emails ที่ใช้ทดสอบได้
6. Save

### 3.4 Create OAuth Client ID

1. Navigate to **APIs & Services → Credentials**
2. Click **"+ Create Credentials" → OAuth client ID**
3. Application type: **Web application**
4. Name: `PDB Web Client`
5. **Authorized JavaScript origins:**
   - `https://yourdomain.com`
   - `http://localhost:8000` (สำหรับ local dev)
6. **Authorized redirect URIs:**
   - `https://yourdomain.com/api/drive/oauth/callback`
   - `https://yourdomain.com/api/auth/google/callback`
   - `http://localhost:8000/api/drive/oauth/callback` (local dev)
   - `http://localhost:8000/api/auth/google/callback` (local dev)
7. Create — copy **Client ID** + **Client Secret**

### 3.5 Set in PDB

```bash
flyctl secrets set \
  GOOGLE_OAUTH_CLIENT_ID="<copy>.apps.googleusercontent.com" \
  GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-..." \
  GOOGLE_OAUTH_REDIRECT_URI="https://yourdomain.com/api/drive/oauth/callback" \
  GOOGLE_OAUTH_MODE="testing"
```

### 3.6 Submit for Verification (Production Mode)

⚠️ Testing mode = refresh tokens หมดอายุ **7 วัน** → user ต้อง reconnect ทุกสัปดาห์

**To get permanent tokens:**

1. Navigate to **APIs & Services → OAuth consent screen**
2. Click **"Publish App"**
3. ต้อง submit for verification:
   - Privacy Policy URL (required)
   - Terms of Service URL (required)
   - Justification for each scope
   - For `drive.file`: **non-sensitive** → free verification, ~2-4 weeks
4. รอ Google review
5. หลังผ่าน → `flyctl secrets set GOOGLE_OAUTH_MODE=production`

**Scopes that need CASA verification ($25K-85K/year):**
- `https://www.googleapis.com/auth/drive` (full Drive access)
- ⚠️ PDB **ห้าม** ใช้ scope นี้ — `drive.file` พอ (ตาม ADR STORAGE-002)

---

## 4. Stripe (Billing & Subscriptions)

**Used for:** Checkout + Customer Portal + Subscription webhooks

### 4.1 Create Account

1. Visit https://stripe.com/
2. Sign up
3. Complete business profile (สำหรับ Thailand: ต้องมีบริษัท + bank account)

### 4.2 Get API Keys

1. Visit https://dashboard.stripe.com/apikeys
2. Copy:
   - **Publishable key**: `pk_test_...` (test) / `pk_live_...` (live)
   - **Secret key**: `sk_test_...` (test) / `sk_live_...` (live)

### 4.3 Create Products

1. Visit https://dashboard.stripe.com/products
2. Click **"+ Add product"**
3. Name: `PDB Starter`
4. Price: ฿99 / monthly recurring
5. Tax: included (or exclusive per local law)
6. Save → copy **Price ID** (`price_...`)

ทำซ้ำสำหรับ tiers อื่นๆ ถ้ามี (Pro, Elite, etc.)

### 4.4 Configure Customer Portal

1. Visit https://dashboard.stripe.com/settings/billing/portal
2. Enable: Update payment method, View invoices, Cancel subscription
3. Branding: Logo + color match PDB
4. Save

### 4.5 Setup Webhook

1. Visit https://dashboard.stripe.com/webhooks
2. Click **"+ Add endpoint"**
3. Endpoint URL: `https://yourdomain.com/api/stripe/webhook`
4. Events to listen:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Save → copy **Webhook signing secret** (`whsec_...`)

### 4.6 Set in PDB

```bash
flyctl secrets set \
  STRIPE_SECRET_KEY="sk_live_..." \
  STRIPE_WEBHOOK_SECRET="whsec_..." \
  STRIPE_PRICE_ID_STARTER="price_..."
```

### 4.7 Test

```bash
# Use test card: 4242 4242 4242 4242
# Any future date, any CVC
# Should:
# 1. Create checkout session
# 2. Webhook fires
# 3. User's subscription_status='starter_active'
```

### 4.8 Go Live

1. Complete business verification
2. Switch toggle from "Test mode" → "Live mode"
3. Regenerate keys (`sk_live_...`)
4. Update PDB secrets
5. Test with real card

---

## 5. Resend (Transactional Email)

**Used for:** Password reset emails

### 5.1 Create Account

1. Visit https://resend.com/
2. Sign up

### 5.2 Add Domain

1. Visit https://resend.com/domains
2. Click **"+ Add Domain"**
3. Enter `yourdomain.com`
4. Add DNS records (SPF + DKIM + DMARC) ใน DNS provider
5. Wait for verification (5-30 min)

### 5.3 Create API Key

1. Visit https://resend.com/api-keys
2. Click **"+ Create API key"**
3. Name: `pdb-production`
4. Permission: **Sending access** only
5. Domain: `yourdomain.com`
6. Copy key (starts with `re_`)

### 5.4 Set in PDB

```bash
flyctl secrets set RESEND_API_KEY=re_...
```

### 5.5 Configure Email Templates

PDB ใช้ Resend SDK ใน `email_service.py` — template hardcoded ใน code

ตรวจ:
- From: `noreply@yourdomain.com` (ต้อง verified domain)
- Reply-to: support@yourdomain.com

### 5.6 Test

```bash
# Request password reset via UI → check email arrived
```

### 5.7 Free Tier Limits

- 100 emails/day
- 3,000 emails/month
- Upgrade: $20/mo → 50K emails

---

## 6. LINE Developers (LINE Bot)

**Used for:** LINE bot integration (ingest messages, link accounts)

### 6.1 Create Provider

1. Visit https://developers.line.biz/console/
2. Sign in with LINE account
3. Click **"Create"** → **"Create a new provider"**
4. Provider name: `Personal Data Bank`

### 6.2 Create Messaging API Channel

1. Click **"Create a Messaging API channel"**
2. Fill in:
   - Channel name: `Personal Data Bank`
   - Channel description: `AI knowledge workspace`
   - Category: `Productivity`
   - Subcategory: `Personal assistant`
   - Email: your@email.com
   - Privacy policy URL: `https://yourdomain.com/privacy` ⚠️ Required
   - Terms of use URL: `https://yourdomain.com/terms` ⚠️ Required
3. Agree to terms → Create

### 6.3 Get Credentials

In channel settings:
- **Channel secret**: Tab "Basic settings" → copy
- **Channel access token**: Tab "Messaging API" → Click "Issue" → copy (long-lived token)

### 6.4 Configure Webhook

1. Tab "Messaging API"
2. Webhook URL: `https://yourdomain.com/webhook/line`
3. **Use webhook**: Enable ✓
4. **Verify** → should return 200
5. **Webhook redelivery**: Enable (recommended)

### 6.5 Disable Default Behavior

In Tab "Messaging API":
- **Auto-reply messages**: Disable (PDB handles all responses)
- **Greeting messages**: Disable

### 6.6 Set in PDB

```bash
flyctl secrets set \
  LINE_CHANNEL_SECRET="..." \
  LINE_CHANNEL_ACCESS_TOKEN="..."
```

### 6.7 Configure Rich Menu

PDB ใช้ rich menu สำหรับ user actions. สามารถ:
- Auto-create ผ่าน LINE Bot Manager (https://manager.line.biz/)
- หรือ upload image (2500x1686 px) + JSON layout

### 6.8 Quota Limits

Free tier:
- 500 messages/month outbound
- Unlimited inbound (webhook)

Upgrade plans:
- Developer Trial: 1000/mo (free)
- Light: 5000/mo (¥5,500)
- Standard: 30,000/mo (¥10,000)

### 6.9 Test

1. Search bot @ID in LINE app → add as friend
2. Send "hi" → bot should reply
3. Tap "Link Account" in rich menu → flex card with link button
4. Tap link → opens `/auth/line?linkToken=...` → user confirms → linked

---

## 7. Fly.io (Production Hosting)

ดู [05-deployment-runbook.md §2](05-deployment-runbook.md) — full Fly.io setup

---

## 8. Privacy Policy & Terms of Service

⚠️ **CRITICAL:** ต้องมีก่อน publish OAuth + Stripe + LINE

### 8.1 Required Coverage

**Privacy Policy ต้องระบุ:**
- ข้อมูลที่เก็บ (email, uploaded files, AI processing logs)
- ระยะเวลาเก็บ
- การใช้ third-party (Gemini, OpenRouter, Stripe)
- สิทธิ์ user (export, delete, ดู audit)
- Contact info
- PDPA (Thailand) / GDPR (EU) compliance

**Terms ต้องระบุ:**
- Subscription terms (auto-renewal, cancellation)
- Refund policy
- User content ownership
- Acceptable use
- Liability limits
- Governing law

### 8.2 Generation Tools

- **Free template:** https://www.termsfeed.com/ (Generator + Editor)
- **Paid (recommended):** https://termly.io/ ($10-30/mo, auto-updates)
- **Custom:** Local lawyer — ฿5,000-15,000

### 8.3 Host on PDB

Add static endpoints in `main.py`:
```python
@app.get("/privacy")
async def privacy():
    return FileResponse('legacy-frontend/privacy.html')

@app.get("/terms")
async def terms():
    return FileResponse('legacy-frontend/terms.html')
```

---

## 9. Cloudflare (Optional — Custom Domain + Edge)

### 9.1 Sign Up

https://cloudflare.com/ — Free plan พอสำหรับ small-medium scale

### 9.2 Add Domain

1. Add site → enter `yourdomain.com`
2. Choose **Free** plan
3. Update nameservers ที่ registrar ของคุณ → Cloudflare's NS

### 9.3 Add DNS Records (per Doc 05 §8.2)

### 9.4 SSL/TLS Settings

- **Mode:** Full (strict)
- **Always Use HTTPS:** On
- **Min TLS Version:** 1.2

### 9.5 Performance

- **Auto Minify:** JS + CSS + HTML ✓
- **Brotli:** On
- **Rocket Loader:** Off (vanilla JS — เสี่ยง break)

---

## 10. Summary Setup Checklist

### Critical (Must Have)
- [ ] Google AI Studio API key (`GOOGLE_API_KEY`)
- [ ] OpenRouter API key (`OPENROUTER_API_KEY`)
- [ ] Fly.io account + app + volume
- [ ] JWT_SECRET_KEY generated
- [ ] ADMIN_PASSWORD set

### Important (Most Features)
- [ ] Google Cloud OAuth credentials (`GOOGLE_OAUTH_CLIENT_ID` + `SECRET`)
- [ ] Privacy Policy + Terms hosted at `/privacy` + `/terms`
- [ ] Resend domain verified + API key

### Optional (Per Feature)
- [ ] Stripe products + webhook (สำหรับ billing)
- [ ] LINE channel + webhook (สำหรับ LINE bot)
- [ ] Cloudflare custom domain
- [ ] Google OAuth verification submission (for production mode)

---

## 11. Cost Estimate (Monthly)

### Minimum Viable Setup
| Service | Cost |
|---|---|
| Fly.io Hobby (2 GB shared-cpu) | $2-5 |
| Google AI Studio (Free tier) | $0 |
| OpenRouter (light usage) | $1-5 |
| Resend (Free tier) | $0 |
| Domain (.com) | $1 |
| **Total** | **~$5-15/mo** |

### Production Scale (~100 active users)
| Service | Cost |
|---|---|
| Fly.io (4 GB shared-cpu-2x) | $10-20 |
| Google AI Studio (paid tier) | $5-20 |
| OpenRouter | $10-30 |
| Stripe fees | 2.9% of revenue |
| Resend (Pro $20/mo) | $20 |
| Cloudflare | $0 (free plan) |
| **Total** | **~$50-100/mo** + Stripe fees |

### At 1000 Users
| Service | Cost |
|---|---|
| Fly.io (multi-machine) | $50-100 |
| Google AI Studio (heavy) | $50-150 |
| OpenRouter | $100-300 |
| Stripe fees | 2.9% |
| Resend Business | $80 |
| **Total** | **~$300-700/mo** |

---

**End — Complete external API setup guide for PDB v9.4.8**

**Pro tip:** ทำตามลำดับ #1 → #2 → #3 ก่อน (critical) — ส่วนที่เหลือทำหลังก็ได้
