# PRD v5.9.2 — Stripe Payment System

## 1. Document Control

| Item | Detail |
|---|---|
| Project | Personal Data Bank / Project KEY |
| PRD | v5.9.2 — Stripe Payment System |
| Scope | ระบบชำระเงินสำหรับ Starter Plan 99 บาท/เดือน |
| Related PRD | PRD v5.9.1 — Frontend Pricing Update |
| Next PRD | PRD v5.9.3 — Post-Payment Access & Usage Limits |
| Status | **✅ Done** — Implemented 2026-04-27 |
| Stripe Account ID | `<REDACTED — see Stripe dashboard>` |
| Stripe Mode | **Test Mode** |
| Keys Location | `.env` (local) / Fly.io secrets (production) |
| Last Updated | 2026-04-27 (v2 — added Pricing Page) |

---

## 2. Goal

สร้างระบบชำระเงินด้วย Stripe เพื่อให้ผู้ใช้สามารถอัปเกรดจาก Free Plan เป็น Starter Plan ราคา **99 บาท/เดือน** ได้อย่างปลอดภัยและตรวจสอบได้

เป้าหมายของ PRD นี้คือ:

1. ให้ผู้ใช้กดอัปเกรดเป็น Starter ได้
2. ให้ผู้ใช้จ่ายเงินผ่าน Stripe Checkout
3. ให้ระบบรับผลการจ่ายเงินผ่าน Stripe Webhook
4. ให้ระบบอัปเดตสถานะ subscription ของผู้ใช้
5. ให้ผู้ใช้จัดการ billing ผ่าน Stripe Customer Portal

> PRD นี้ไม่รวมระบบจำกัด quota หลังจ่ายเงิน รายละเอียด quota จะอยู่ใน PRD v5.9.3

---

## 3. Scope

### In Scope

- Stripe Checkout สำหรับ Starter Plan
- Stripe Subscription รายเดือน
- Stripe Webhook
- Payment success handling
- Payment failed handling
- Cancel subscription
- Customer Portal
- Subscription status ในระบบ
- Basic billing page integration

### Out of Scope

- Usage limits enforcement
- Context Pack quota logic
- File upload quota logic
- AI Summary quota logic
- Export quota logic
- Executive plan payment
- Core / Pro / Elite / Legacy checkout
- Usage-based billing
- Tax invoice เต็มรูปแบบ
- Coupon / discount system
- Trial system

---

## 4. Plan ที่ใช้ Stripe

ใน v1 ใช้ Stripe เฉพาะแผนเดียว:

| Plan | Price | Payment Method |
|---|---:|---|
| Free | 0 บาท/เดือน | ไม่ใช้ Stripe |
| Starter | 99 บาท/เดือน | Stripe Subscription |
| Core | 12,000 บาท/เดือน | ไม่ใช้ Stripe Checkout ใน v1 |
| Pro | 25,000 บาท/เดือน | ไม่ใช้ Stripe Checkout ใน v1 |
| Elite | 45,000 บาท/เดือน | ไม่ใช้ Stripe Checkout ใน v1 |
| Legacy | 8,000 บาท/เดือน | ไม่ใช้ Stripe Checkout ใน v1 |

Executive Plans ต้องใช้ private demo / lead form / manual sales process เท่านั้นใน v1

---

## 5. Stripe Product Setup

ต้องสร้าง Product และ Price ใน Stripe Dashboard ดังนี้:

```text
Product Name: Personal AI Context — Starter
Price: 99 THB / month
Billing Type: Recurring monthly
Currency: THB
Trial: None for v1
```

### 5.1 Stripe Account Info (Actual)

```text
Stripe Account ID: <REDACTED — see Stripe dashboard>
Mode: Test
Publishable Key: <REDACTED — see .env>
Secret Key: <REDACTED — see .env / Fly secrets>
Webhook Secret: <REDACTED — see .env / Fly secrets>
Starter Product ID: <REDACTED — see Stripe dashboard>
Starter Price ID: <REDACTED — see .env>
Webhook Endpoint ID: <REDACTED — see Stripe dashboard>
Portal Config ID: <REDACTED — see Stripe dashboard>
```

### 5.2 สิ่งที่ต้องทำใน Stripe Dashboard

1. ✅ สร้าง Stripe Account แล้ว
2. ✅ ได้ Test API Keys แล้ว (บันทึกใน `.env`)
3. ✅ สร้าง Product "Personal AI Context — Starter" → `<REDACTED>`
4. ✅ สร้าง Price 99 THB/month Recurring → `<REDACTED>`
5. ✅ สร้าง Webhook Endpoint → `<REDACTED>` (rotated 2026-05-01)
6. ✅ ตั้งค่า Customer Portal → `<REDACTED>`

ระบบต้องเก็บค่า mapping ไว้ใน environment variables:

```text
STRIPE_PUBLISHABLE_KEY    ← ✅ มีแล้ว
STRIPE_SECRET_KEY         ← ✅ มีแล้ว
STRIPE_STARTER_PRICE_ID   ← ✅ <REDACTED — see .env>
STRIPE_WEBHOOK_SECRET     ← ✅ <REDACTED — see .env / Fly secrets>
APP_BASE_URL              ← ✅ ตั้งไว้ http://localhost:8000
```

### 5.3 Backend Implementation (Completed)

| Component | File | Status |
|---|---|---|
| Config | `backend/config.py` | ✅ Stripe vars loaded from .env |
| DB Schema | `backend/database.py` | ✅ User subscription fields + WebhookLog table |
| Billing Module | `backend/billing.py` | ✅ Checkout, Portal, Webhook handler |
| API Routes | `backend/main.py` | ✅ 4 billing API + 3 page routes (/, /pricing, /billing/*) |
| Dependencies | `requirements-fly.txt` | ✅ stripe>=8.0.0 |

### 5.4 Frontend Implementation (Completed)

| Component | File | Status |
|---|---|---|
| Pricing Page | `legacy-frontend/pricing.html` | ✅ Standalone page — ทั้ง 🧠 Personal AI Context + 👑 Executive Digital Twin |
| Landing Page | `legacy-frontend/index.html` | ✅ Profile Modal billing section + Plan Modal (deprecated in favor of /pricing) |
| App Logic | `legacy-frontend/app.js` | ✅ Register → redirect /pricing, Upgrade → navigate /pricing, Checkout + Portal |
| Styles | `legacy-frontend/styles.css` | ✅ Billing section CSS + plan card CSS |

---

## 6. User Flow

### 6.1 New Registration → Plan Selection

```text
User visits landing page
↓
User clicks "เริ่มต้นฟรี" → Registration form
↓
User registers (name, email, password)
↓
Backend creates user + returns token
↓
Frontend saves token + redirects to /pricing?welcome=1
↓
User sees Pricing Page with all plans
↓
User chooses Free → goes to workspace
  OR
User chooses Starter → Stripe Checkout → pays 99 THB
```

### 6.2 Existing User → Upgrade to Starter

```text
User logs in → enters workspace
↓
User opens Profile → sees billing section
↓
User clicks "Upgrade to Starter" → navigates to /pricing
↓
User clicks "Get Starter" → Stripe Checkout
↓
User pays 99 THB/month on Stripe Checkout
↓
Stripe redirects user back to /billing/success
↓
Stripe sends webhook to backend
↓
Backend verifies webhook signature
↓
Backend updates user subscription status
↓
User sees Starter status in Profile billing section
```

Important:

> ระบบต้องเชื่อ Stripe Webhook เป็น source of truth เท่านั้น ไม่เชื่อ query parameter จาก success URL ว่าจ่ายสำเร็จแล้ว

---

## 7. Checkout Button Behavior

### ปุ่ม Get Starter

ตำแหน่งที่มีปุ่ม:

- `/pricing` page (standalone) — ✅ implemented
- Landing page pricing section → redirects to `/pricing` (if logged in) or register first
- Profile modal billing section → navigates to `/pricing`

เมื่อคลิก:

```text
POST /api/billing/create-checkout-session
```

Request:

```json
{
  "plan": "starter"
}
```

Response:

```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

Frontend redirect ไปที่ `checkout_url`

---

## 8. Success and Cancel URLs

### Success URL

```text
/billing/success?session_id={CHECKOUT_SESSION_ID}
```

ข้อความที่แสดง:

```text
Payment received.
Your Starter plan is being activated.
This may take a few seconds.
```

ถ้า webhook ทำงานแล้ว ให้แสดง:

```text
Your Starter plan is active.
```

### Cancel URL

```text
/billing/cancelled
```

ข้อความที่แสดง:

```text
Payment was cancelled.
You are still on the Free plan.
You can upgrade to Starter anytime.
```

---

## 9. Subscription Status

ระบบต้องรองรับ status ต่อไปนี้:

| Status | Meaning | User Access |
|---|---|---|
| free | ผู้ใช้ Free | Free limits |
| starter_incomplete | เริ่ม checkout แต่ยังจ่ายไม่สำเร็จ | Free limits |
| starter_active | จ่ายสำเร็จและ subscription active | Starter limits |
| starter_past_due | จ่ายรอบล่าสุดไม่ผ่าน | Grace period / warning |
| starter_canceled | ยกเลิกแล้ว | Starter จนหมดรอบบิล แล้วกลับ Free |

---

## 10. Database Requirements

ต้องมีตารางหรือ field สำหรับ subscription อย่างน้อย:

```text
user_id
plan
subscription_status
stripe_customer_id
stripe_subscription_id
stripe_price_id
current_period_start
current_period_end
cancel_at_period_end
created_at
updated_at
```

ตัวอย่าง:

```json
{
  "user_id": "user_123",
  "plan": "starter",
  "subscription_status": "starter_active",
  "stripe_customer_id": "cus_xxx",
  "stripe_subscription_id": "sub_xxx",
  "stripe_price_id": "price_xxx",
  "current_period_start": "2026-04-27T00:00:00Z",
  "current_period_end": "2026-05-27T00:00:00Z",
  "cancel_at_period_end": false
}
```

---

## 11. Stripe Webhooks

ระบบต้องรองรับ webhook ต่อไปนี้:

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.payment_succeeded
invoice.payment_failed
```

### 11.1 checkout.session.completed

เมื่อ checkout สำเร็จ:

```text
- verify webhook signature
- get user_id จาก metadata
- save stripe_customer_id
- save stripe_subscription_id
- set plan = starter
- set subscription_status = starter_active
- save current_period_end
```

### 11.2 customer.subscription.created

เมื่อ subscription ถูกสร้าง:

```text
- link subscription กับ user
- set subscription_status ตาม Stripe status
- save billing period
```

### 11.3 customer.subscription.updated

เมื่อ subscription เปลี่ยน เช่น cancel at period end:

```text
- update subscription_status
- update cancel_at_period_end
- update current_period_end
```

### 11.4 customer.subscription.deleted

เมื่อ subscription ถูกยกเลิกหรือหมดอายุ:

```text
- set plan = free
- set subscription_status = free
- keep stripe_customer_id for history
```

### 11.5 invoice.payment_succeeded

เมื่อจ่ายรอบใหม่สำเร็จ:

```text
- set plan = starter
- set subscription_status = starter_active
- update current_period_start
- update current_period_end
- trigger monthly quota reset in PRD v5.9.3
```

### 11.6 invoice.payment_failed

เมื่อจ่ายเงินไม่ผ่าน:

```text
- set subscription_status = starter_past_due
- show billing warning
- keep access during grace period if defined in PRD v5.9.3
```

---

## 12. Webhook Security

ข้อกำหนดสำคัญ:

1. ต้อง verify Stripe webhook signature ทุกครั้ง
2. ห้าม update plan จาก frontend โดยตรง
3. ห้ามเชื่อ success URL อย่างเดียว
4. ต้องเก็บ webhook event id เพื่อป้องกัน duplicate processing
5. ถ้า webhook ซ้ำ ต้องไม่ทำให้ข้อมูลผิดพลาด

ตัวอย่าง field สำหรับ webhook log:

```text
event_id
event_type
stripe_object_id
processed_at
status
error_message
```

---

## 13. Customer Portal

ผู้ใช้ Starter ต้องสามารถกดปุ่ม:

```text
Manage Billing
```

เพื่อไปที่ Stripe Customer Portal

Customer Portal ใช้สำหรับ:

- ดู subscription
- เปลี่ยนบัตร
- ดูใบเสร็จ
- ยกเลิก subscription
- แก้ billing information

API:

```text
POST /api/billing/create-portal-session
```

Response:

```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

---

## 14. Cancel Subscription Policy

ใช้รูปแบบ:

```text
Cancel at period end
```

ไม่ตัดสิทธิ์ทันที

ตัวอย่าง:

ถ้าผู้ใช้จ่ายวันที่ 1 และ cancel วันที่ 15 ผู้ใช้ยังใช้ Starter ได้ถึงวันที่ 30 จากนั้นค่อยกลับเป็น Free

ข้อความใน UI:

```text
Your Starter plan will remain active until the end of your billing period.
After that, your account will return to the Free plan.
```

---

## 15. Payment Failed Policy

เมื่อชำระเงินรอบใหม่ไม่สำเร็จ:

```text
- status = starter_past_due
- แสดง warning ใน Billing page
- ส่ง email แจ้งผู้ใช้ถ้ามีระบบ email
- ให้ผู้ใช้แก้ payment method ผ่าน Customer Portal
```

ข้อความใน UI:

```text
We could not process your latest payment.
Please update your payment method to keep your Starter plan active.
```

Grace period และ downgrade logic จะกำหนดละเอียดใน PRD v5.9.3

---

## 16. Pricing Page & Billing UI

### 16.1 Pricing Page (`/pricing`)

Standalone page สำหรับเลือกแพลน แสดง 2 กลุ่ม:

**🧠 Personal AI Context** (สมัครได้จริง)

| Plan | Price | CTA | Action |
|---|---|---|---|
| Free | ฿0/เดือน | "เริ่มต้นฟรี" | Navigate to / (workspace) |
| Starter | ฿99/เดือน | "⚡ Get Starter" | POST /api/billing/create-checkout-session → Stripe Checkout |

**👑 Executive Digital Twin** (แสดงแต่ contact sales)

| Plan | Price | CTA | Action |
|---|---|---|---|
| Core | ฿12,000/เดือน | "Book Private Demo" | mailto:boss@projectkey.dev |
| Pro | ฿25,000/เดือน | "Book Private Demo" | mailto:boss@projectkey.dev |
| Elite | ฿45,000/เดือน | "Request Elite Access" | mailto:boss@projectkey.dev |

### 16.2 Profile Modal Billing Section

อยู่ใน Profile modal (`#profile-modal`) แสดงตาม status:

**Free User:**
```text
[FREE] Personal AI Context
แพลนปัจจุบัน: Free — อัปเกรดเพื่อปลดล็อกฟีเจอร์เพิ่ม
[⚡ Upgrade to Starter — ฿99/mo]  ← navigates to /pricing
```

**Starter Active User:**
```text
[STARTER] Personal AI Context
แพลนปัจจุบัน: Starter (Active)
[จัดการการชำระเงิน]  ← opens Stripe Customer Portal
```

**Starter Canceled User:**
```text
[STARTER] Personal AI Context
แพลนปัจจุบัน: Starter — Cancels at end of period
[จัดการการชำระเงิน]
⚠️ สมาชิกภาพจะสิ้นสุดเมื่อหมดรอบบิลปัจจุบัน
```

---

## 17. Executive Plans Payment Rule

Core / Pro / Elite / Legacy ต้องไม่ใช้ Stripe Checkout ใน v1

CTA ที่ถูกต้อง:

| Plan | CTA |
|---|---|
| Core | Book Private Demo |
| Pro | Book Private Demo |
| Elite | Request Elite Access |
| Legacy | Explore Legacy |

เหตุผล:

Executive Digital Twin เป็น high-touch product ต้องมี private onboarding, consent, setup fee และการประเมินความเหมาะสมก่อนใช้งาน

---

## 18. Error Handling

### Checkout creation failed

ข้อความ:

```text
We could not start checkout right now.
Please try again in a moment.
```

### User already has Starter

ข้อความ:

```text
You are already on the Starter plan.
```

### No Stripe customer found

ข้อความ:

```text
Billing account not found.
Please contact support.
```

### Webhook failed internally

ระบบต้อง log error และ retry ได้

---

## 19. Environment Requirements

ต้องแยก environment:

```text
Development: Stripe test mode
Production: Stripe live mode
```

ห้ามใช้ live key ใน local development

### 19.1 Environment Variables (Actual Status)

| Variable | Status | Location | Value |
|---|---|---|---|
| `STRIPE_PUBLISHABLE_KEY` | ✅ บันทึกแล้ว | `.env` | `<REDACTED>` |
| `STRIPE_SECRET_KEY` | ✅ บันทึกแล้ว | `.env` | `<REDACTED>` |
| `STRIPE_WEBHOOK_SECRET` | ✅ บันทึกแล้ว | `.env` | `<REDACTED — rotated 2026-05-01>` |
| `STRIPE_STARTER_PRICE_ID` | ✅ บันทึกแล้ว | `.env` | `<REDACTED>` |
| `APP_BASE_URL` | ✅ ตั้งแล้ว | `.env` | `http://localhost:8000` |

### 19.2 Production (Fly.io)

เมื่อพร้อม deploy ต้องตั้ง secrets ใน Fly.io:

```bash
fly secrets set STRIPE_SECRET_KEY=sk_live_xxx
fly secrets set STRIPE_PUBLISHABLE_KEY=pk_live_xxx
fly secrets set STRIPE_WEBHOOK_SECRET=whsec_xxx
fly secrets set STRIPE_STARTER_PRICE_ID=price_xxx
fly secrets set APP_BASE_URL=https://personaldatabank.fly.dev
```

---

## 20. Acceptance Criteria

งานนี้ถือว่าผ่านเมื่อ:

1. ✅ สมัครใหม่ → redirect ไป `/pricing?welcome=1` อัตโนมัติ
2. ✅ หน้า `/pricing` แสดง Free + Starter + Core + Pro + Elite ครบ
3. ✅ กด "เริ่มต้นฟรี" → เข้า workspace ได้
4. ✅ กด "Get Starter" → Stripe Checkout เปิดพร้อมราคา ฿99/เดือน
5. ✅ ผู้ใช้จ่ายเงินด้วย test card (4242...) สำเร็จ
6. ✅ Stripe webhook ส่งกลับมาอัปเดต subscription status
7. ✅ Profile billing section แสดง STARTER + Active หลังจ่ายสำเร็จ
8. ✅ ผู้ใช้กด Manage Billing → Stripe Customer Portal เปิดได้
9. ✅ ผู้ใช้ cancel subscription ผ่าน Portal ได้
10. ✅ ปุ่ม Upgrade ใน Profile → navigate ไป `/pricing`
11. ✅ Executive plans แสดง "Book Private Demo" (mailto:) ไม่มี Stripe Checkout
12. ✅ ไม่มีการปลดล็อกจาก frontend โดยตรงโดยไม่ผ่าน webhook

---

## 21. Non-Goals

PRD นี้ไม่ต้องทำ:

- บังคับ quota Free / Starter
- lock ข้อมูลเมื่อ downgrade
- reset usage monthly แบบละเอียด
- comparison table logic
- AI Summary counter
- file upload counter
- semantic search access control
- tax invoice เต็มรูปแบบ
- refund automation
- coupon / promo code
- trial period

สิ่งเหล่านี้ไปอยู่ใน PRD v5.9.3 หรือ future PRD

---

## 22. Final Summary

PRD v5.9.2 มีเป้าหมายเดียว:

> ทำให้ผู้ใช้สามารถจ่าย Starter Plan 99 บาท/เดือนผ่าน Stripe ได้อย่างปลอดภัย และให้ระบบอัปเดตสถานะ subscription ได้ถูกต้องผ่าน webhook

ขอบเขตที่ต้องล็อก:

```text
Free = ไม่ใช้ Stripe
Starter = Stripe Subscription 99 บาท/เดือน
Executive Plans = ไม่ใช้ Stripe Checkout ใน v1
Webhook = source of truth
Customer Portal = ใช้จัดการ billing
```
