# PRD v5.9.1 — Frontend Pricing & Messaging Update

## Project
Personal Data Bank / Project KEY

## Version
v5.9.1

## Document Type
Frontend PRD

## Status
✅ **Done** — Implemented 2026-04-27

## Goal
อัปเดต “หน้าบ้านเว็บไซต์” ให้สื่อสารแพ็กเกจ Free และ Starter ชัดเจนขึ้น โดยยังคงแบ่งราคาเป็น 2 กลุ่มใหญ่:

1. **Personal AI Context**
   - Free: 0 บาท / เดือน
   - Starter: 99 บาท / เดือน

2. **Executive Digital Twin**
   - Core: 12,000 บาท / เดือน
   - Pro: 25,000 บาท / เดือน
   - Elite: 45,000 บาท / เดือน
   - Legacy: 8,000 บาท / เดือน

เป้าหมายของ PRD ฉบับนี้คือ **อัปเดตข้อมูลและ UX บนหน้าเว็บเท่านั้น** ยังไม่ทำระบบจ่ายเงินจริง ยังไม่ทำระบบจำกัดสิทธิ์หลังบ้าน และยังไม่เชื่อม Stripe

---

## 1. Why This Update Matters

เว็บไซต์ v5.8 มี pricing section แล้ว แต่ต้องอัปเดตให้ชัดขึ้นว่า:

- Free ได้อะไร
- Starter ได้อะไร
- Starter ราคา 99 บาท/เดือน
- Free / Starter เป็นแผน Personal AI Context ไม่ใช่ Digital Twin
- Executive Digital Twin ยังเป็นแผนที่ต้อง Book Demo หรือ Request Access เท่านั้น
- ผู้ใช้เข้าใจความต่างระหว่างแผนฟรี แผนเริ่มต้น และแผนผู้บริหารได้เร็วขึ้น

---

## 2. Core Positioning

### Main Message

```text
Start with context. Grow into your Digital Twin.
```

### Thai Message

```text
เริ่มจากบริบทส่วนตัว แล้วเติบโตสู่ Digital Twin ของคุณ
```

### Supporting Copy

```text
Personal Data Bank helps you turn scattered files, notes, and knowledge into AI-ready context, so AI can understand your work, study, style, and goals without starting from zero every time.
```

### Thai Supporting Copy

```text
Personal Data Bank ช่วยเปลี่ยนไฟล์ โน้ต และความรู้ที่กระจัดกระจาย ให้กลายเป็นบริบทที่พร้อมใช้กับ AI เพื่อให้ AI เข้าใจงาน การเรียน สไตล์ และเป้าหมายของคุณมากขึ้น โดยไม่ต้องเริ่มใหม่ทุกครั้ง
```

---

## 3. Product Grouping

หน้าเว็บต้องแยก pricing เป็น 2 กลุ่มอย่างชัดเจน

```text
Personal AI Context
Free / Starter

Executive Digital Twin
Core / Pro / Elite / Legacy
```

### Important Rule

ห้ามทำให้ Free / Starter ดูเหมือนเป็น Digital Twin เต็มระบบ

Free / Starter ต้องใช้คำว่า:

- Personal AI Context
- Context Pack
- AI-ready Profile
- Personal Context Workspace

Core / Pro / Elite / Legacy ถึงจะใช้คำว่า:

- Digital Twin
- Identity Vault
- Decision Matrix
- MCP Gateway
- Executive Twin

---

## 4. Scope

## In Scope

- อัปเดต Hero copy บางส่วนถ้าจำเป็น
- อัปเดต Pricing Section
- เพิ่มตารางเปรียบเทียบ Free vs Starter
- เพิ่มคำอธิบายว่า Executive Plans ต้องคุยก่อน
- เพิ่ม FAQ เรื่อง Free / Starter / Executive Plans
- เพิ่ม Trust Note ใต้ Pricing
- อัปเดต CTA ให้ตรงกับแต่ละ plan
- ปรับ responsive layout ของ pricing ให้ชัดเจนบนมือถือ

## Out of Scope

- ยังไม่เชื่อม Stripe
- ยังไม่ทำ checkout จริง
- ยังไม่ทำระบบ subscription backend
- ยังไม่ทำ usage limit backend
- ยังไม่ทำ dashboard หลังบ้าน
- ยังไม่ทำ file upload จริง
- ยังไม่ทำ AI summary จริง
- ยังไม่ทำ MCP connection
- ยังไม่ทำ Digital Twin จริง

---

## 5. Target Users

### Primary for This Update

1. คนทั่วไปที่ใช้ AI อยู่แล้ว
2. นักศึกษา
3. Creator
4. Freelancer
5. คนทำงานที่อยากให้ AI เข้าใจบริบทมากขึ้น

### Secondary

1. Founder
2. Executive
3. C-Suite
4. Thought Leader
5. Family Business Owner

---

## 6. Pricing Section Structure

## Section Headline

```text
Start with context. Grow into your Digital Twin.
```

## Section Subheadline

```text
Choose the right layer for how deeply you want AI to understand your data, your work, your style, and your judgment.
```

## Thai Version

```text
เลือกชั้นของผลิตภัณฑ์ตามระดับที่คุณต้องการให้ AI เข้าใจข้อมูล งาน สไตล์ และวิธีคิดของคุณ
```

---

# 7. Personal AI Context Section

## Section Title

```text
Personal AI Context
```

## Section Description

```text
For students, creators, and everyday AI users who want AI to understand their context without starting from zero.
```

## Thai Description

```text
สำหรับนักศึกษา ครีเอเตอร์ และคนใช้ AI ที่อยากให้ AI เข้าใจบริบทของตัวเองมากขึ้น โดยไม่ต้องเริ่มใหม่ทุกครั้ง
```

---

## 7.1 Free Plan Card

### Plan Name

```text
Free
```

### Price

```text
0 บาท / เดือน
```

### Tagline

```text
Try your first AI-ready context.
```

### Thai Description

```text
เริ่มทดลองสร้างบริบทแรกของคุณ เพื่อให้ AI เข้าใจเป้าหมาย ไฟล์ และข้อมูลพื้นฐานของคุณมากขึ้น
```

### Feature List

- 1 Personal Context Pack
- Basic profile summary
- อัปโหลดไฟล์ได้สูงสุด 5 ไฟล์
- พื้นที่เก็บข้อมูล 50 MB
- AI Summary 5 ครั้ง / เดือน
- Export Prompt 10 ครั้ง / เดือน
- Basic search
- เหมาะสำหรับทดลองระบบ

### CTA

```text
Start Free
```

### CTA Behavior for This PRD

- ปุ่มสามารถพาไปหน้า signup หรือ placeholder ได้
- ยังไม่ต้องเชื่อมระบบจริง
- ถ้ายังไม่มี signup ให้ทำ modal หรือ anchor ไปยัง waitlist/contact form ได้

---

## 7.2 Starter Plan Card

### Plan Name

```text
Starter
```

### Price

```text
99 บาท / เดือน
```

### Tagline

```text
For students and everyday AI users.
```

### Badge

```text
Best for beginners
```

### Thai Description

```text
ใช้ AI ได้ต่อเนื่องขึ้น ด้วยบริบทส่วนตัวสำหรับการเรียน งาน โปรเจกต์ และสไตล์การทำงานเบื้องต้น
```

### Feature List

- 5 Context Packs
- Study / Work / Creator context
- Writing style เบื้องต้น
- อัปโหลดไฟล์ได้สูงสุด 50 ไฟล์
- พื้นที่เก็บข้อมูล 1 GB
- AI Summary 100 ครั้ง / เดือน
- Export Prompt 300 ครั้ง / เดือน
- Context Refresh 10 ครั้ง / เดือน
- Basic + Semantic Search เบื้องต้น
- Version History 7 วัน

### CTA

```text
Get Starter
```

### CTA Behavior for This PRD

- ปุ่มยังไม่ต้องเชื่อม Stripe ใน PRD นี้
- ปุ่มสามารถพาไปหน้า coming soon / waitlist / payment-interest ได้
- ให้ใส่ note ว่า Stripe payment จะมาใน PRD v5.9.2

---

# 8. Free vs Starter Comparison Table

ต้องเพิ่มตารางเปรียบเทียบแบบอ่านง่าย

| Feature | Free | Starter |
|---|---:|---:|
| ราคา | 0 บาท/เดือน | 99 บาท/เดือน |
| Context Packs | 1 | 5 |
| Files | 5 ไฟล์ | 50 ไฟล์ |
| Storage | 50 MB | 1 GB |
| Max file size | 10 MB / file | 20 MB / file |
| AI Summary | 5 / เดือน | 100 / เดือน |
| Export Prompt | 10 / เดือน | 300 / เดือน |
| Context Refresh | ไม่มี | 10 / เดือน |
| Search | Basic | Basic + Semantic |
| Version History | ไม่มี | 7 วัน |
| Support | FAQ | Email basic |
| Payment | ไม่ต้องใช้บัตร | Stripe subscription ในเฟสถัดไป |

---

# 9. Executive Digital Twin Section

## Section Title

```text
Executive Digital Twin
```

## Section Description

```text
For founders, executives, and high-impact leaders who want AI to work with their judgment, voice, and decision context.
```

## Thai Description

```text
สำหรับ Founder ผู้บริหาร และผู้นำที่ต้องการให้ AI ทำงานด้วยวิธีคิด สไตล์ เสียง และบริบทการตัดสินใจของตัวเอง
```

## Important Message

Executive plans are not self-service checkout plans.

ให้แสดงข้อความเล็กใต้หัวข้อว่า:

```text
Executive plans require private onboarding and are available by demo or request only.
```

ภาษาไทย:

```text
แพ็กเกจ Executive ต้องมี private onboarding ก่อนเริ่มใช้งาน และยังไม่เปิดให้ซื้อผ่านหน้าเว็บโดยตรง
```

---

## 9.1 Core Plan

### Price

```text
12,000 บาท / เดือน
```

### Tagline

```text
Start your private Digital Twin.
```

### Short Description

```text
เริ่มสร้าง Digital Twin ส่วนตัว ให้ AI เข้าใจบริบท วิธีคิด และสไตล์พื้นฐานของคุณมากขึ้น
```

### Features

- Private Identity Vault
- Basic Decision Matrix
- Text-based Digital Twin
- MCP connection
- Context retrieval
- 50,000 API calls / month

### CTA

```text
Book Private Demo
```

---

## 9.2 Pro Plan

### Price

```text
25,000 บาท / เดือน
```

### Badge

```text
Recommended
```

### Tagline

```text
Most recommended for leaders.
```

### Short Description

```text
สำหรับผู้บริหารและ Founder ที่ต้องการให้ AI ช่วยคิด เขียน สรุป และทำงานในสไตล์ของตัวเองอย่างต่อเนื่อง
```

### Features

- ทุกอย่างใน Core
- Advanced Decision Matrix
- Voice Clone
- Priority Support
- 3 Delegated Users
- Monthly Twin Calibration
- 200,000 API calls / month

### CTA

```text
Book Private Demo
```

### Design Rule

Pro card ต้องเด่นที่สุดในกลุ่ม Executive

- มี Recommended badge
- มี gold glow หรือ border เด่น
- ปุ่ม CTA เด่นกว่าการ์ดอื่น
- card อาจยกสูงขึ้นเล็กน้อยบน desktop

---

## 9.3 Elite Plan

### Price

```text
45,000 บาท / เดือน
```

### Tagline

```text
A private digital twin experience.
```

### Short Description

```text
Digital Twin ระดับพรีเมียม พร้อมการปรับแต่งเชิงลึก ทีมดูแลส่วนตัว และประสบการณ์ที่ออกแบบสำหรับผู้นำระดับสูง
```

### Features

- ทุกอย่างใน Pro
- Avatar UI
- Dedicated CSM
- Deep Decision Calibration
- Annual Deep Review
- Priority Onboarding
- 500,000 API calls / month

### CTA

```text
Request Elite Access
```

---

## 9.4 Legacy Plan

### Price

```text
8,000 บาท / เดือน
```

### Tagline

```text
Preserve wisdom. Pass on judgment.
```

### Short Description

```text
สำหรับการเก็บรักษาวิธีคิด ความรู้ และบทเรียนระยะยาว ให้ครอบครัว ทีม หรือผู้สืบทอดเข้าถึงได้ภายใต้สิทธิ์ที่กำหนด
```

### Features

- Read-only Digital Twin
- Knowledge Preservation Mode
- Consultation Mode
- Access control สำหรับผู้รับสิทธิ์
- Legacy archive
- Limited support

### CTA

```text
Explore Legacy
```

### Design Rule

Legacy ไม่ควรวางแข่งกับ Pro / Elite โดยตรง ควรเป็น card ที่สงบกว่า หรือวางแยกเป็นแถวล่าง

---

# 10. CTA Rules

| Plan | CTA |
|---|---|
| Free | Start Free |
| Starter | Get Starter |
| Core | Book Private Demo |
| Pro | Book Private Demo |
| Elite | Request Elite Access |
| Legacy | Explore Legacy |

## CTA Behavior in This PRD

- Free / Starter ยังไม่ต้องทำระบบจริง
- Starter ยังไม่ต้องเชื่อม Stripe
- Executive CTA ให้ไป demo / contact / lead form เท่านั้น
- ห้ามใช้คำว่า Buy Now กับ Executive Plans

---

# 11. Trust Note Under Pricing

ต้องมี note ใต้ Pricing Section:

```text
Free and Starter are Personal AI Context plans. They are designed for AI-ready context packs, not full Digital Twins.
Executive Digital Twin plans require private onboarding and explicit consent before any sensitive data is used.
```

ภาษาไทย:

```text
Free และ Starter เป็นแผน Personal AI Context สำหรับสร้างบริบทพร้อมใช้กับ AI ยังไม่ใช่ Digital Twin เต็มระบบ ส่วน Executive Digital Twin ต้องมี private onboarding และ consent ที่ชัดเจนก่อนใช้ข้อมูลสำคัญใด ๆ
```

---

# 12. Safety & Privacy Messaging

เพิ่มหรือคงไว้ใน Trust & Privacy Section:

## Trust Principles

- Private by default
- User-controlled context
- Export anytime
- Delete anytime
- Revoke access
- No training without consent
- Only selected data is used
- Start with low-risk study, work, and personal knowledge data

## Important Website Copy

```text
We start with low-risk study, work, and personal knowledge context. Please do not upload identity documents, financial records, medical data, or highly sensitive personal information in this early version.
```

ภาษาไทย:

```text
ช่วงเริ่มต้นเราจะโฟกัสข้อมูลความรู้ การเรียน งาน และบริบทส่วนตัวที่มีความเสี่ยงต่ำ กรุณาอย่าอัปโหลดบัตรประชาชน เอกสารการเงิน ข้อมูลสุขภาพ หรือข้อมูลอ่อนไหวสูงในเวอร์ชันแรก
```

---

# 13. FAQ Updates

เพิ่ม FAQ อย่างน้อย 5 ข้อ

## FAQ 1 — Free กับ Starter ต่างกันอย่างไร?

```text
Free เหมาะสำหรับทดลองสร้าง Context Pack แรก ส่วน Starter เหมาะสำหรับคนที่ต้องการใช้บริบทหลายชุดกับการเรียน งาน หรือการสร้างคอนเทนต์เป็นประจำ
```

## FAQ 2 — Starter เป็น Digital Twin หรือไม่?

```text
ไม่ใช่ Starter เป็น Personal AI Context plan สำหรับสร้าง context pack และ AI-ready profile เบื้องต้น ส่วน Digital Twin เริ่มที่แผน Core ขึ้นไปและต้องมี onboarding แยกต่างหาก
```

## FAQ 3 — Starter จ่ายผ่านอะไร?

```text
Starter จะใช้ Stripe subscription ในเฟสถัดไป ตอนนี้หน้านี้ใช้เพื่อสื่อสารราคาและรับความสนใจจากผู้ใช้ก่อน
```

## FAQ 4 — Executive Plans ซื้อผ่านหน้าเว็บได้ไหม?

```text
ยังไม่ได้ Executive Plans ต้อง Book Private Demo หรือ Request Access เพราะต้องมี private onboarding, consent และการประเมินความเหมาะสมก่อนเริ่มใช้งาน
```

## FAQ 5 — อัปโหลดข้อมูลอ่อนไหวได้ไหม?

```text
ยังไม่ควรอัปโหลดข้อมูลอ่อนไหว เช่น บัตรประชาชน เอกสารการเงิน ข้อมูลสุขภาพ หรือข้อมูลที่เกี่ยวกับบุคคลอื่นโดยไม่มีสิทธิ์ เวอร์ชันแรกเน้นข้อมูลการเรียน งาน ความรู้ส่วนตัว และบริบทที่มีความเสี่ยงต่ำ
```

---

# 14. Design Requirements

## Overall Style

- Dark premium background
- Cinematic but professional
- Indigo / blue accent สำหรับ Personal AI Context
- Gold accent สำหรับ Executive Digital Twin
- Glassmorphism cards
- Clear price hierarchy
- Plenty of spacing
- Easy to read on mobile

## Personal Cards

- Friendly
- Approachable
- Indigo / blue / purple accent
- Free card simple
- Starter card slightly highlighted

## Executive Cards

- Premium
- Gold / dark navy accent
- Pro card most highlighted
- Elite card premium but not louder than Pro
- Legacy calm and archival

---

# 15. Responsive Requirements

## Desktop

```text
Personal AI Context:
[Free] [Starter]

Executive Digital Twin:
[Core] [Pro Recommended] [Elite]
[Legacy wide or separated]
```

## Tablet

```text
Personal:
[Free]
[Starter]

Executive:
[Core] [Pro]
[Elite] [Legacy]
```

## Mobile

```text
Headline
Subheadline

Personal AI Context
[Free]
[Starter]

Comparison Table

Executive Digital Twin
[Core]
[Pro]
[Elite]
[Legacy]

FAQ
Trust Note
```

Mobile cards must show:

1. Plan name
2. Price
3. Tagline
4. Top 4-6 features
5. CTA

without excessive scrolling inside the card.

---

# 16. Implementation Notes

## Files likely to update

- `legacy-frontend/index.html`
- `legacy-frontend/styles.css`
- Any frontend component file if the site has been migrated to components later

## Do Not Implement Yet

- Stripe checkout
- Payment backend
- Webhook
- Usage counter
- Subscription table
- Actual file upload
- Actual AI summary

---

# 17. Acceptance Criteria

งานนี้ถือว่าผ่านเมื่อ:

1. หน้าเว็บแสดง Free และ Starter ชัดเจน
2. ผู้ใช้เห็นทันทีว่า Free = 0 บาท / Starter = 99 บาทต่อเดือน
3. มีตารางเปรียบเทียบ Free vs Starter
4. Free / Starter ถูกจัดอยู่ใต้ Personal AI Context
5. Core / Pro / Elite / Legacy ถูกจัดอยู่ใต้ Executive Digital Twin
6. Pro card เด่นที่สุดในกลุ่ม Executive
7. Starter card เด่นกว่า Free เล็กน้อย แต่ไม่เกิน Pro
8. Executive Plans ไม่ใช้ปุ่ม Buy Now
9. มีข้อความว่า Executive Plans ต้อง private onboarding
10. มี Trust Note ว่า Free / Starter ไม่ใช่ Digital Twin เต็มระบบ
11. มีคำเตือนว่าเวอร์ชันแรกไม่ควรอัปโหลดข้อมูลอ่อนไหว
12. FAQ ตอบคำถาม Free / Starter / Stripe / Executive / Sensitive Data
13. Mobile layout อ่านง่ายและไม่แน่นเกินไป
14. Design ยังดูเป็นบริษัท AI/Data ที่น่าเชื่อถือ ไม่ใช่ consumer toy

---

# 18. Final Summary

PRD v5.9.1 นี้มีเป้าหมายเดียวคือ:

```text
อัปเดตหน้าบ้านให้สื่อสารราคาและแพ็กเกจ Free / Starter ชัดเจนขึ้น โดยยังไม่ทำระบบจ่ายเงินจริงและยังไม่ทำระบบหลังบ้าน
```

Frontend ต้องทำให้ผู้ใช้เข้าใจว่า:

```text
Free = ลองสร้าง context แรก
Starter = ใช้ context กับชีวิตจริงแบบเบา ๆ ในราคา 99 บาท/เดือน
Executive Digital Twin = สำหรับผู้บริหาร ต้องคุยและ onboarding ก่อน
```

