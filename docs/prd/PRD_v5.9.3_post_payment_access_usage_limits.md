# PRD v5.9.3 — Post-Payment Access & Usage Limit System

**Project:** Personal Data Bank / Project KEY  
**Version:** v5.9.3  
**Document Type:** Product Requirements Document  
**Scope:** ระบบหลังบ้านหลังจ่ายเงิน / สิทธิ์การใช้งาน / Usage Limits  
**Status:** ✅ Phase 2 Complete — Enforcement + Dashboard + Upgrade CTA  
**Last Updated:** 2026-04-28  
**Related PRDs:**
- PRD v5.9.1 — Frontend Pricing Update
- PRD v5.9.2 — Stripe Payment System (✅ Done)

---

## 1. เป้าหมายของ PRD นี้

PRD ฉบับนี้กำหนดระบบหลังบ้านที่ทำงานหลังจากผู้ใช้สมัครหรือจ่ายเงินแล้ว เพื่อให้ระบบสามารถ:

1. แยกสิทธิ์การใช้งานระหว่าง Free และ Starter ได้ชัดเจน
2. ปลดล็อก Starter limits หลังจาก Stripe ยืนยันการจ่ายเงินสำเร็จ
3. จำกัดการใช้งานของ Free และ Starter ตาม quota ที่กำหนด
4. แสดง usage ให้ผู้ใช้เห็นใน dashboard
5. block การใช้งานเมื่อผู้ใช้ถึง limit
6. reset monthly quota ตามรอบบิล
7. จัดการกรณียกเลิกแผน จ่ายเงินไม่ผ่าน และ downgrade จาก Starter กลับ Free
8. ป้องกันการลบข้อมูลผู้ใช้โดยไม่ตั้งใจเมื่อ downgrade

เป้าหมายหลักคือ:

> ผู้ใช้ฟรีต้องได้ตาม Free limits เท่านั้น และผู้ใช้ที่จ่าย Starter ต้องได้ Starter limits ทันทีหลัง payment สำเร็จ

---

## 2. Scope ของ PRD นี้

### อยู่ใน scope

- Plan logic
- Usage limits
- Usage counters
- Monthly quota reset
- Dashboard usage display
- Limit blocking
- Starter access unlock
- Downgrade behavior
- Locked data behavior
- Subscription status mapping จาก Stripe
- Grace period กรณีจ่ายเงินไม่ผ่าน
- Cancel at period end
- Billing state ที่ระบบต้องใช้ภายใน

### ไม่อยู่ใน scope

- Stripe Checkout UI
- Stripe webhook implementation รายละเอียดเชิง payment
- Payment method management
- Tax invoice
- Executive plans payment
- Core / Pro / Elite / Legacy backend
- Digital Twin features
- MCP connection
- Voice Clone
- Avatar
- Decision Matrix
- Sensitive data vault

สิ่งเหล่านี้จะอยู่ใน PRD อื่นหรือ phase ถัดไป

### Implementation Status

| Component | File | Status |
|---|---|---|
| Plan Limits Config | `backend/plan_limits.py` | ✅ Done — PLAN_LIMITS dict (source of truth) |
| Usage Query Helpers | `backend/plan_limits.py` | ✅ Done — get_file_count, get_storage_used, get_pack_count, monthly counters |
| Enforcement Checks | `backend/plan_limits.py` | ✅ Done — check_upload_allowed, check_pack_create_allowed, check_summary_allowed, etc. |
| UsageLog Table | `backend/database.py` | ✅ Done — tracks ai_summary, export, refresh per user |
| Upload Enforcement | `backend/main.py` | ✅ Done — file count, file size, file type, storage limits per plan |
| Pack Enforcement | `backend/main.py` | ✅ Done — pack count limit per plan |
| Usage API | `GET /api/usage` | ✅ Done — returns full usage summary for dashboard |
| Plan Limits API | `GET /api/plan-limits` | ✅ Done — returns current plan's limits |
| Summary Enforcement | `backend/main.py` | ✅ Done — log AI summary usage + block at monthly limit |
| Refresh Enforcement | `backend/main.py` | ✅ Done — block regenerate when refresh quota = 0 |
| Dashboard Usage UI | `legacy-frontend/app.js` | ✅ Done — 5 progress bars + color coding (red/yellow/blue) |
| Sidebar Stats | `legacy-frontend/app.js` | ✅ Done — shows used/limit format (e.g. 5/5 ไฟล์) |
| Upload Hint Dynamic | `legacy-frontend/app.js` | ✅ Done — shows file size limit per plan |
| Upgrade CTA Modal | `legacy-frontend/app.js` | ✅ Done — glassmorphism popup on 403 quota errors |
| Stripe Checkout Flow | `backend/billing.py` | ✅ Done — tested: Pricing → Stripe Checkout → test card |
| Export Enforcement | `backend/main.py` | ⏳ Future — log export usage + check before export |
| Downgrade Logic | `backend/billing.py` | ⏳ Future — lock packs/files on downgrade |
| Upgrade Unlock | `backend/billing.py` | ⏳ Future — unlock packs/files on upgrade |
| Webhook Payment Complete | `backend/billing.py` | ✅ Done — updates plan to starter_active on checkout.session.completed |

---

## 3. Product Principle

ระบบ Free / Starter ต้องถูกวางเป็น **Personal AI Context** เท่านั้น ไม่ใช่ Digital Twin

คำที่ใช้ได้:

- Personal AI Context
- Context Pack
- AI-ready Profile
- Personal Context Workspace
- AI-ready Summary
- Export Prompt

คำที่ห้ามใช้กับ Free / Starter:

- Digital Twin
- AI Clone
- Second Self
- Decision Advisor
- Executive Twin
- Voice Clone
- Avatar
- Decision Matrix

เหตุผล: Free และ Starter เป็น entry layer สำหรับผู้ใช้ทั่วไป ส่วน Digital Twin เป็น product คนละระดับสำหรับ Executive plans

---

## 4. Plan Definitions

ระบบ v1 จะมี 2 plan ที่ใช้งานจริงก่อน:

```text
free
starter
```

### 4.1 Free Plan

Free คือแผนทดลองใช้งาน เพื่อให้ผู้ใช้เห็นคุณค่าของ Context Pack

| Feature | Limit |
|---|---:|
| ราคา | 0 บาท / เดือน |
| User Profile | 1 profile |
| Context Packs | 1 pack |
| Files | 5 files |
| Storage | 50 MB |
| Max file size | 10 MB / file |
| AI Summaries | 5 / month |
| Export Prompts | 10 / month |
| Context Refresh | 0 / month |
| Search | Basic |
| Semantic Search | ไม่มี |
| Version History | ไม่มี |
| Support | FAQ / Self-service |
| Payment | ไม่ใช้ Stripe |

### 4.2 Starter Plan

Starter คือแผนใช้งานจริงแบบเบา ๆ สำหรับนักศึกษา คนทำงาน Creator และผู้ใช้ AI ประจำ

| Feature | Limit |
|---|---:|
| ราคา | 99 บาท / เดือน |
| User Profile | 1 profile |
| Context Packs | 5 packs |
| Files | 50 files |
| Storage | 1 GB |
| Max file size | 20 MB / file |
| AI Summaries | 100 / month |
| Export Prompts | 300 / month |
| Context Refresh | 10 / month |
| Search | Basic + Semantic Search เบื้องต้น |
| Version History | 7 วัน |
| Support | Email basic |
| Payment | Stripe Subscription |

---

## 5. Source of Truth สำหรับ Plan Limits

ระบบต้องมี source of truth กลางสำหรับ plan limits ห้าม hardcode กระจัดกระจายในหลายไฟล์

ตัวอย่าง configuration:

```json
{
  "free": {
    "context_pack_limit": 1,
    "file_limit": 5,
    "storage_limit_mb": 50,
    "max_file_size_mb": 10,
    "ai_summary_limit_monthly": 5,
    "export_limit_monthly": 10,
    "refresh_limit_monthly": 0,
    "semantic_search_enabled": false,
    "version_history_days": 0,
    "support_level": "faq"
  },
  "starter": {
    "context_pack_limit": 5,
    "file_limit": 50,
    "storage_limit_mb": 1024,
    "max_file_size_mb": 20,
    "ai_summary_limit_monthly": 100,
    "export_limit_monthly": 300,
    "refresh_limit_monthly": 10,
    "semantic_search_enabled": true,
    "version_history_days": 7,
    "support_level": "email_basic"
  }
}
```

---

## 6. Subscription Status

ระบบต้องรองรับ subscription status เหล่านี้:

| Status | ความหมาย | Plan ที่ใช้ |
|---|---|---|
| `free` | ผู้ใช้ฟรี | Free limits |
| `starter_active` | ผู้ใช้ Starter จ่ายสำเร็จ | Starter limits |
| `starter_incomplete` | เริ่ม checkout แต่ยังไม่จ่ายสำเร็จ | Free limits |
| `starter_past_due` | จ่ายรอบล่าสุดไม่ผ่าน | Starter limits ชั่วคราวใน grace period |
| `starter_canceled` | ยกเลิกแล้ว แต่ยังไม่หมดรอบบิล | Starter limits จนถึง `current_period_end` |
| `starter_expired` | หมดรอบบิลหลังยกเลิกหรือจ่ายไม่ผ่านเกิน grace period | Free limits + locked data |

---

## 7. Stripe → Internal Plan Mapping

ระบบชำระเงินอยู่ใน PRD v5.9.2 แต่ระบบหลังบ้านต้องรู้ว่า Stripe event แปลเป็นสิทธิ์อะไร

| Stripe / Billing Event | Internal Result |
|---|---|
| Checkout สำเร็จ | `plan = starter`, `status = starter_active` |
| Subscription active | ใช้ Starter limits |
| Payment succeeded | ต่ออายุ Starter + reset monthly usage |
| Payment failed | `status = starter_past_due` |
| Cancel at period end | `status = starter_canceled`, ใช้ Starter ต่อถึงวันหมดรอบ |
| Subscription deleted / expired | downgrade เป็น Free |

หลักสำคัญ:

> ระบบต้องปลดล็อก Starter limits เฉพาะเมื่อ backend ได้รับและ verify Stripe webhook สำเร็จแล้วเท่านั้น

ห้าม frontend ส่งค่า `plan=starter` แล้วระบบเชื่อทันที

---

## 8. Data Model Requirements

### 8.1 User Table / User Model

ต้องมี field อย่างน้อย:

```text
user_id
email
name
plan
subscription_status
stripe_customer_id
stripe_subscription_id
current_period_start
current_period_end
cancel_at_period_end
created_at
updated_at
```

### 8.2 Usage Table / Usage Model

ควรแยก usage เป็นรายเดือน

```text
usage_id
user_id
billing_month
context_packs_count
files_count
storage_used_mb
ai_summary_used
export_used
refresh_used
last_reset_at
created_at
updated_at
```

ตัวอย่าง `billing_month`:

```text
2026-04
2026-05
```

### 8.3 Context Pack Model ต้องมีสถานะ lock

```text
pack_id
user_id
title
type
status
is_locked
locked_reason
created_at
updated_at
```

ตัวอย่าง `locked_reason`:

```text
exceeds_free_plan_limit
subscription_expired
storage_over_limit
```

### 8.4 Source File Model ต้องมีสถานะ lock

```text
file_id
pack_id
user_id
file_name
file_size_mb
file_type
is_locked
locked_reason
created_at
updated_at
```

---

## 9. Usage Counters

ระบบต้องนับ usage อย่างน้อย 6 ตัว:

```text
context_packs_count
files_count
storage_used_mb
ai_summary_used
export_used
refresh_used
```

### 9.1 Counter แบบสะสมตลอดเวลา

- Context Packs
- Files
- Storage

### 9.2 Counter แบบรายเดือน

- AI Summary
- Export Prompt
- Context Refresh

---

## 10. Dashboard Usage Display

Dashboard ต้องแสดง usage ให้ผู้ใช้เห็นชัดเจน

### 10.1 Free User

```text
Current Plan: Free

Context Packs: 1 / 1
Files: 3 / 5
Storage: 28 MB / 50 MB
AI Summary: 2 / 5 this month
Export: 4 / 10 this month
Context Refresh: 0 / 0 this month

CTA: Upgrade to Starter — 99 บาท / เดือน
```

### 10.2 Starter User

```text
Current Plan: Starter
Status: Active
Next billing date: 27 May 2026

Context Packs: 3 / 5
Files: 18 / 50
Storage: 420 MB / 1 GB
AI Summary: 25 / 100 this month
Export: 80 / 300 this month
Context Refresh: 2 / 10 this month

CTA: Manage Billing
```

### 10.3 Past Due User

```text
Current Plan: Starter
Status: Payment issue

We could not process your latest payment.
Please update your payment method to keep Starter active.

CTA: Update Payment Method
```

### 10.4 Downgraded User

```text
Current Plan: Free

Your account has returned to the Free plan.
Your data is safe, but some packs or files are locked because they exceed Free limits.

CTA: Upgrade to Starter to unlock all packs
```

---

## 11. Limit Enforcement Rules

ระบบต้องตรวจ limit ก่อนทำ action ต่อไปนี้:

1. Create Context Pack
2. Upload File
3. Generate AI Summary
4. Export Prompt
5. Refresh Context
6. Use Semantic Search

---

## 12. Blocking Rules และข้อความแจ้งเตือน

### 12.1 Create Context Pack เกิน limit

ถ้า Free สร้าง pack เกิน 1:

```text
Free plan includes 1 Context Pack.
Upgrade to Starter to create up to 5 packs.
```

ถ้า Starter สร้าง pack เกิน 5:

```text
Starter includes up to 5 Context Packs.
You have reached your current plan limit.
```

### 12.2 Upload file เกินจำนวนไฟล์

```text
You have reached your file upload limit.
Starter gives you up to 50 files and 1 GB storage.
```

### 12.3 Upload file เกินขนาดต่อไฟล์

Free:

```text
Free plan supports files up to 10 MB.
Upgrade to Starter to upload files up to 20 MB.
```

Starter:

```text
Starter supports files up to 20 MB.
Please upload a smaller file.
```

### 12.4 Storage เต็ม

```text
You have reached your storage limit.
Upgrade or delete unused files to continue uploading.
```

### 12.5 AI Summary เกิน limit

Free:

```text
You have used all free AI summaries this month.
Upgrade to Starter for 100 summaries per month.
```

Starter:

```text
You have used all Starter AI summaries this month.
Your summary quota will reset next billing cycle.
```

### 12.6 Export Prompt เกิน limit

Free:

```text
You have reached your monthly export limit.
Starter includes 300 exports per month.
```

Starter:

```text
You have reached your monthly export limit.
Your export quota will reset next billing cycle.
```

### 12.7 Context Refresh เกิน limit

Free:

```text
Context Refresh is available on Starter.
Upgrade to refresh your context packs.
```

Starter:

```text
You have used all 10 context refreshes this month.
Your refresh quota will reset next billing cycle.
```

### 12.8 Semantic Search สำหรับ Free

```text
Semantic Search is available on Starter.
Upgrade to search your context by meaning, not just keywords.
```

---

## 13. Monthly Reset Logic

Monthly quota ต้อง reset ตามรอบบิลของผู้ใช้

### 13.1 Free User

Free reset ทุกเดือนตาม calendar month หรือ user billing anchor ที่ระบบกำหนด

```text
ai_summary_used = 0
export_used = 0
refresh_used = 0
```

### 13.2 Starter User

Starter reset เมื่อ Stripe ยืนยัน `invoice.payment_succeeded` สำหรับรอบใหม่

```text
ai_summary_used = 0
export_used = 0
refresh_used = 0
current_period_start = Stripe period start
current_period_end = Stripe period end
```

หาก webhook ล่าช้า ระบบควร sync กับ Stripe API ได้ใน admin/debug mode

---

## 14. Upgrade Behavior: Free → Starter

เมื่อผู้ใช้ upgrade สำเร็จ:

1. `plan` เปลี่ยนเป็น `starter`
2. `subscription_status` เปลี่ยนเป็น `starter_active`
3. เพิ่ม limits เป็น Starter ทันที
4. ปลดล็อก pack/file ที่เคยถูก lock จาก Free limit ถ้ายังอยู่ใน Starter limit
5. อัปเดต Dashboard ให้แสดง Starter usage
6. แสดง success message

ข้อความ:

```text
Starter is now active.
You can now create up to 5 Context Packs, upload up to 50 files, and use 100 AI summaries per month.
```

---

## 15. Cancel Behavior

การยกเลิกควรเป็นแบบ:

```text
cancel_at_period_end = true
```

ไม่ตัดสิทธิ์ทันที

### Flow

```text
User clicks Cancel Plan
↓
Stripe marks subscription cancel_at_period_end
↓
System keeps Starter active until current_period_end
↓
After period end, user downgrades to Free
```

ข้อความ:

```text
Your Starter plan will remain active until the end of your billing period.
After that, your account will return to the Free plan.
```

---

## 16. Downgrade Behavior: Starter → Free

เมื่อผู้ใช้ downgrade จาก Starter กลับ Free:

ระบบต้องไม่ลบข้อมูลทันที

### หลักการ

```text
Data is safe, but access is limited by the Free plan.
```

### Rules

1. ข้อมูลเดิมยังอยู่
2. ผู้ใช้ต้องเลือก 1 active context pack สำหรับ Free
3. Context packs ที่เกิน 1 จะถูก lock
4. Files ที่เกิน 5 หรือ storage ที่เกิน 50 MB จะถูก lock
5. Locked data ดูชื่อ/metadata ได้ แต่เปิดใช้ export/refresh/summary ไม่ได้
6. ถ้าอัปเกรดกลับ Starter ข้อมูลที่ถูก lock จะปลดล็อกอีกครั้ง หากยังอยู่ใน Starter limits

### UI Message

```text
You are now on the Free plan.
Your data is safe, but some packs are locked because they exceed Free plan limits.
Choose 1 active pack to continue using, or upgrade to Starter to unlock all packs.
```

---

## 17. Locked Data Rules

### 17.1 Locked Context Pack

ผู้ใช้สามารถ:

- เห็นชื่อ pack
- เห็น type
- เห็นจำนวนไฟล์
- เห็นวันที่อัปเดตล่าสุด
- ลบ pack ได้
- อัปเกรดเพื่อ unlock ได้

ผู้ใช้ไม่สามารถ:

- เปิด AI-ready summary
- export prompt
- refresh context
- upload file เพิ่มเข้า pack นั้น
- edit pack detail

### 17.2 Locked File

ผู้ใช้สามารถ:

- เห็นชื่อไฟล์
- เห็นขนาดไฟล์
- เห็น type
- ลบไฟล์ได้

ผู้ใช้ไม่สามารถ:

- เปิดเนื้อหาไฟล์
- ใช้ไฟล์ในการ summary
- export context จากไฟล์นั้น
- semantic search ไฟล์นั้น

---

## 18. Past Due Behavior

เมื่อ Stripe แจ้ง payment failed:

1. `subscription_status = starter_past_due`
2. แสดง payment warning
3. ให้ grace period 7 วัน
4. ระหว่าง grace period ยังใช้ Starter ได้
5. ถ้าจ่ายสำเร็จใน grace period กลับเป็น `starter_active`
6. ถ้าเกิน grace periodและยังจ่ายไม่สำเร็จ downgrade เป็น Free

ข้อความ:

```text
We could not process your latest payment.
Please update your payment method within 7 days to keep Starter active.
```

เมื่อเกิน grace period:

```text
Your Starter plan has expired because payment was not completed.
Your account has returned to the Free plan. Your data is safe, but some items may be locked.
```

---

## 19. Sensitive Data Policy สำหรับ Free / Starter

ใน v1 ระบบต้องห้ามหรือเตือนอย่างชัดเจนว่า Free / Starter ไม่รองรับข้อมูลอ่อนไหวสูง

ห้ามรับหรือไม่ควรให้ผู้ใช้อัปโหลด:

```text
ID card
Passport
Bank statement
Medical record
Genetic data
Biometric identity data
Criminal record
Sensitive political/religious/sexual data
Audio/video files in v1
```

UI ต้องมี note:

```text
Please do not upload sensitive personal data such as ID cards, passports, bank statements, or medical records. This version is designed for study, work, creator, and personal knowledge context only.
```

---

## 20. File Type Policy

### Free

รองรับ:

```text
PDF
DOCX
TXT
MD
CSV
```

ไม่รองรับ:

```text
Audio
Video
ID documents
Medical files
Financial statements
```

### Starter

รองรับ:

```text
PDF
DOCX
TXT
MD
CSV
PNG
JPG
```

ไม่รองรับใน v1:

```text
Audio
Video
ID documents
Medical files
Financial statements
```

---

## 21. Admin Requirements

Admin ควรดูข้อมูลเหล่านี้ได้:

- User plan
- Subscription status
- Stripe customer ID
- Stripe subscription ID
- Current period end
- Usage counters
- Locked packs count
- Locked files count
- Payment status

Admin actions ใน v1:

- manually sync Stripe subscription
- manually downgrade user
- manually unlock user for support case
- view usage summary

Admin ห้าม:

- ดูเนื้อหาไฟล์ผู้ใช้โดยไม่จำเป็น
- เปลี่ยน plan โดยไม่มี audit log
- ลบข้อมูลผู้ใช้โดยไม่มี explicit request

---

## 22. Audit Log Requirements

ระบบต้องบันทึกเหตุการณ์สำคัญ:

```text
plan_changed
subscription_status_changed
usage_limit_reached
file_locked
pack_locked
file_unlocked
pack_unlocked
quota_reset
payment_failed_status_received
downgrade_completed
manual_admin_override
```

Audit log ควรมี:

```text
event_id
user_id
event_type
old_value
new_value
triggered_by
created_at
```

`triggered_by` อาจเป็น:

```text
user
stripe_webhook
system
admin
```

---

## 23. Edge Cases

### 23.1 User จ่าย Starter แล้ว webhook มาช้า

- หน้า success ควรบอกว่า payment กำลังตรวจสอบ
- backend ต้อง sync เมื่อ webhook มาถึง
- ถ้าเกินเวลาที่กำหนด ให้มีปุ่ม refresh billing status

### 23.2 User เปิดหลาย tab แล้วพยายามสร้าง pack เกิน limit

- ต้อง enforce limit ที่ backend
- frontend validation อย่างเดียวไม่พอ

### 23.3 User downgrade แล้วมี 5 packs

- ให้เลือก 1 active pack
- ถ้าไม่เลือก ระบบเลือก pack ล่าสุดเป็น active pack ชั่วคราว
- pack อื่น lock

### 23.4 User storage เกิน Free หลัง downgrade

- ห้าม upload เพิ่ม
- ห้าม summary/export จาก locked files
- ลบไฟล์ได้เสมอ

### 23.5 User upgrade กลับ Starter

- ปลดล็อก packs/files ที่อยู่ใน Starter limits
- ถ้ายังเกิน Starter limits ให้ lock ส่วนเกินต่อ

---

## 24. Acceptance Criteria

PRD นี้ถือว่าผ่านเมื่อ:

1. Free user ถูกจำกัดที่ 1 pack, 5 files, 50 MB, 5 summaries, 10 exports
2. Starter user ถูกจำกัดที่ 5 packs, 50 files, 1 GB, 100 summaries, 300 exports, 10 refreshes
3. ผู้ใช้ที่ยังไม่จ่ายเงินไม่สามารถได้ Starter limits
4. ผู้ใช้ที่จ่ายเงินสำเร็จผ่าน Stripe ได้ Starter limits หลัง webhook สำเร็จ
5. Dashboard แสดง usage ปัจจุบันเทียบกับ limit ได้ถูกต้อง
6. ระบบ block action เมื่อเกิน quota
7. Monthly quota reset ได้ถูกต้องตามรอบบิล
8. Cancel plan แล้วยังใช้ Starter ได้ถึงวันหมดรอบบิล
9. Payment failed เข้าสู่ past_due พร้อม grace period
10. Downgrade แล้วข้อมูลไม่ถูกลบทันที แต่ถูก lock เฉพาะส่วนที่เกิน Free limit
11. Upgrade กลับ Starter แล้วข้อมูลถูก unlock ตาม Starter limits
12. Free / Starter ไม่ใช้คำว่า Digital Twin
13. ระบบห้ามหรือเตือนเรื่อง sensitive data ใน v1
14. Backend enforce limit จริง ไม่ใช่แค่ frontend
15. มี audit log สำหรับ event สำคัญ

---

## 25. Final Summary

ระบบหลังบ้านหลังจ่ายเงินของ v5.9.3 ต้องทำให้ Free และ Starter ใช้งานต่างกันอย่างชัดเจน

```text
Free
= ทดลองสร้าง AI-ready context แรก
= 1 pack, 5 files, 50 MB, 5 summaries/month, 10 exports/month

Starter
= ใช้งาน Personal AI Context จริงแบบเบา ๆ
= 5 packs, 50 files, 1 GB, 100 summaries/month, 300 exports/month, 10 refreshes/month
```

หลักสำคัญที่สุด:

> Stripe มีหน้าที่ยืนยันว่าผู้ใช้จ่ายเงินแล้ว แต่ระบบของเรามีหน้าที่ปลดล็อกสิทธิ์ จำกัด quota และรักษาข้อมูลผู้ใช้เมื่อเกิด downgrade

