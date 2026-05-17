# 🔍 UX/UI Audit Report — Personal Data Bank
## TC-UX-001 · Full Application Audit

**รายงานโดย:** ฟ้า (QA Agent)  
**วันที่ทดสอบ:** 2026-05-17  
**Build ที่ทดสอบ:** v10.0.17 (Production — personaldatabank.fly.dev)  
**ขอบเขต:** ทุก section ของแอป + Landing Page + Mobile Viewport  
**สถานะโดยรวม:** ⚠️ **2 High · 14 Medium · 12 Low · 5 Info**

---

## สรุปผลรวม

| ระดับ | จำนวน | รายละเอียด |
|-------|--------|------------|
| 🔴 High | 2 | Security + Data integrity |
| 🟠 Medium | 14 | UX blocking / confusing flows |
| 🔵 Low | 12 | Polish / consistency issues |
| ⚪ Info | 5 | Cosmetic / enhancement ideas |

---

## Section 1 — Landing Page (LP)

### 🔴 LP-001 — ไม่มีปุ่มปิด (X) บน Login/Register Modal
**Severity:** 🔴 High  
**อาการ:** Modal เข้าสู่ระบบ / สมัครสมาชิก ไม่มีปุ่ม X ที่มองเห็นได้ — ปิดได้เฉพาะการคลิกพื้นหลัง (backdrop) หรือกด ESC เท่านั้น  
**ผลกระทบ:** User ใหม่ที่ไม่คุ้นเคยอาจติดอยู่ใน modal ไม่รู้วิธีออก — โดยเฉพาะบน mobile ที่ไม่มี ESC key  
**แนวทาง:** เพิ่มปุ่ม X ที่มุมบนขวาของทุก modal

---

### 🟠 LP-002 — พื้นที่ว่างขนาดใหญ่กลางหน้า Landing Page
**Severity:** 🟠 Medium  
**อาการ:** หลัง hero section ลงมาประมาณ 2 viewport height เป็นพื้นที่มืดว่างเปล่า ก่อนถึง feature cards — รวม scroll height ทั้งหน้า 3,961px  
**ผลกระทบ:** User คิดว่าหน้าจบแล้วหรือ content โหลดไม่ขึ้น จะไม่ scroll ต่อ — สูญเสีย engagement กับ feature section  
**สาเหตุที่เป็นไปได้:** Scroll-animation / parallax element ที่ไม่ trigger เพราะ viewport ไม่แคบพอ หรือ CSS transform ค้างที่ off-screen  
**แนวทาง:** ตรวจสอบ Intersection Observer / AOS animation trigger — ลด gap หรือทำ fallback ให้ content แสดงแม้ animation ไม่ทำงาน

---

### 🟠 LP-003 — Register Modal ไม่มี Confirm Password
**Severity:** 🟠 Medium  
**อาการ:** ฟอร์มสมัครสมาชิกมีช่องรหัสผ่านเพียงช่องเดียว ไม่มี "ยืนยันรหัสผ่าน"  
**ผลกระทบ:** User พิมพ์รหัสผ่านผิด (typo) → ล็อกอินไม่ได้ → ต้อง reset password ทันที  
**แนวทาง:** เพิ่มช่อง "ยืนยันรหัสผ่าน" หรืออย่างน้อยแสดง password strength indicator

---

### 🟠 LP-004 — Root URL Redirect ผ่าน /admin (Black Screen Flash)
**Severity:** 🟠 Medium  
**อาการ:** User ที่ login อยู่แล้วไปที่ root URL → redirect ไป `/admin` → แสดง "คุณไม่ใช่ admin — กำลังพากลับหน้าผู้ใช้..." บนหน้าจอดำ → redirect ไป `/app`  
**ผลกระทบ:** User เห็นหน้าจอดำ + ข้อความ error ชั่วคราว แทนที่จะ redirect ตรงไป `/app` โดยไม่มีการแวะผ่าน `/admin`  
**แนวทาง:** Login redirect logic ควร check role ก่อน redirect — ไม่ควรส่ง non-admin ไปที่ `/admin` เลย

---

### 🔵 LP-005 — Footer Version ไม่ตรง
**Severity:** 🔵 Low  
**อาการ:** Footer แสดง `v7.5.0` — production JS จริงทำงานที่ `v10.0.17`  
**แนวทาง:** ต่อ footer version string กับ build version จริง (อาจ inject ตอน build)

---

### 🔵 LP-006 — ภาษาไม่สม่ำเสมอบน Landing Page
**Severity:** 🔵 Low  
**อาการ:**
- Hero headline: ภาษาอังกฤษ "Start with context. Grow into your Digital Twin"
- Body copy + CTA: ภาษาไทย
- Feature cards: ผสม เช่น "Knowledge Graph", "AI Chat 7 ชั้น", "จัดเก็บอัจฉริยะ"
- Footer tagline: ผสม "สร้างด้วย · v7.5.0 — Start with context. Grow into your Digital Twin."

**แนวทาง:** เลือก tone ภาษาเดียวให้ consistent — ถ้า target คนไทย ควร Thai-first, English สำหรับ technical terms เท่านั้น

---

### ⚪ LP-007 — Register Modal ไม่มี ToS / Privacy Policy
**Severity:** ⚪ Info  
**อาการ:** ฟอร์มสมัครสมาชิกไม่มี checkbox ยืนยันเงื่อนไขการใช้งาน  
**แนวทาง:** เพิ่ม "ฉันยอมรับ [เงื่อนไขการใช้งาน] และ [นโยบายความเป็นส่วนตัว]" — สำคัญด้านกฎหมาย

---

## Section 2 — ข้อมูลของฉัน / Home (HOME)

### 🟠 HOME-001 — Orphan Nodes แสดงใน Sidebar แม้ไฟล์ = 0
**Severity:** 🟠 Medium  
**อาการ:** Sidebar แสดง "โหนด 13" แม้ "ไฟล์ 0" — orphan nodes จาก session ก่อนหน้าที่ยังไม่ถูกลบ  
**ผลกระทบ:** User เห็นตัวเลข nodes ไม่สัมพันธ์กับไฟล์ → คิดว่าระบบมีข้อมูลลับหรือ bug  
**หมายเหตุ:** Known baseline จาก QA session — แต่ user จริงอาจเจอปัญหานี้หลัง delete ไฟล์ทั้งหมด  
**แนวทาง:** แสดง tooltip หรือข้อความอธิบายเมื่อ nodes > 0 แต่ files = 0

---

### 🟠 HOME-002 — Upload Zone แสดง 80+ File Types Inline
**Severity:** 🟠 Medium  
**อาการ:** Drop zone มีรายชื่อ extension ยาว 2 บรรทัดเต็ม (HEIF, GIF, PDF, JSON, ENV, FLAC, MP4, SCSS, XLSX, JAVA, H, TXT...) แสดงทุกประเภทตลอดเวลา  
**ผลกระทบ:** Visual noise ที่ฝังอยู่ใน upload area — ดูล้นหลาม โดยเฉพาะ mobile  
**แนวทาง:** แสดงเฉพาะประเภทหลัก (PDF, TXT, MD, DOCX, รูปภาพ...) พร้อม "และอีก 70+ ประเภท" link สำหรับ full list

---

### 🟠 HOME-003 — Privacy Warning สีส้ม ดูเหมือน Error
**Severity:** 🟠 Medium  
**อาการ:** คำเตือน "กรุณาอย่าอัปโหลดข้อมูลส่วนมนุคดลที่อ่อนไหว..." แสดงด้วยพื้นหลังสีส้มภายใน upload zone  
**ผลกระทบ:** สีส้มในบริบท upload มักหมายถึง error/warning state — user อาจคิดว่ามีปัญหากับ upload ก่อนจะเริ่ม  
**แนวทาง:** เปลี่ยนเป็น gray/subtle info style หรือย้ายไปนอก upload drop zone

---

### 🔵 HOME-004 — Empty State ไม่มีปุ่ม CTA
**Severity:** 🔵 Low  
**อาการ:** เมื่อไม่มีไฟล์ แสดง "ยังไม่มีไฟล์" แต่ไม่มีปุ่ม "อัปโหลดไฟล์แรก" — user ต้อง scroll ขึ้นไปหาปุ่ม + อัปโหลด  
**แนวทาง:** เพิ่มปุ่ม CTA ใน empty state โดยตรง

---

### 🔵 HOME-005 — Unsupported File Types ไม่แสดง Error Message
**Severity:** 🔵 Low (previously SF-UPLOAD-001)  
**อาการ:** อัปโหลด .exe, .zip → HTTP 200 + `vault_only` — ไม่มี toast/warning แจ้งว่าไฟล์ไม่ได้รับการ process  
**แนวทาง:** แสดง toast: "ไฟล์ประเภทนี้ถูกเก็บในคลัง แต่ไม่ได้รับการจัดระเบียบ"

---

### ⚪ HOME-006 — Filter Chip "📦 คลัง" มี Emoji
**Severity:** ⚪ Info  
**อาการ:** Filter chip ใช้ emoji 📦 ซึ่งไม่ consistent กับ UI สีเข้มสไตล์ professional  
**แนวทาง:** ใช้ icon SVG แทน emoji ให้ consistent กับ design system

---

## Section 3 — มุมมองความรู้ (KV)

### 🔴 KV-001 — คลิก Entity ใน Notes Tab → นำทางไป Graph โดยไม่แจ้งเตือน
**Severity:** 🔴 High  
**อาการ:** คลิก entity node ใน Notes & สรุป tab → ระบบ navigate ไป Graph section ทันทีโดยไม่มี warning, breadcrumb, หรือปุ่มกลับ  
**ผลกระทบ:** User สูญเสีย context — ไม่รู้ว่ากลับไป Notes อย่างไร, เสียงาน  
**แนวทาง:** เพิ่ม breadcrumb "← กลับไป Notes" หลัง navigate, หรือเปิด graph node detail ใน side panel แทนการ navigate ออก

---

### 🟠 KV-002 — Notes Tab แสดง Ghost Entities จากไฟล์ที่ลบแล้ว
**Severity:** 🟠 Medium  
**อาการ:** Notes & สรุป tab แสดง entity cards จาก orphan nodes — ข้อมูลที่ไม่มี source file อยู่แล้ว  
**ผลกระทบ:** User เห็นข้อมูล "ลอยอยู่" ไม่มีที่มา — สับสน และอาจเชื่อข้อมูลผิด  
**แนวทาง:** กรอง Notes view ไม่ให้แสดง entity ที่ไม่มี source_file เชื่อมอยู่

---

### 🔵 KV-003 — Tab ชื่อ "Notes & สรุป" ผสมภาษา
**Severity:** 🔵 Low  
**อาการ:** Tab ใช้ชื่อ "Notes & สรุป" — English + Thai ในชื่อเดียว  
**แนวทาง:** เลือกอย่างใดอย่างหนึ่ง: "บันทึกและสรุป" (Thai) หรือ "Notes & Summary" (English)

---

### 🔵 KV-004 — Collections Empty State ไม่มี Icon และ CTA
**Severity:** 🔵 Low  
**อาการ:** Collections tab ว่างเปล่า ไม่มี icon, ไม่มีปุ่ม "สร้าง Collection แรก"  
**แนวทาง:** เพิ่ม empty state illustration + CTA button

---

## Section 4 — AI แชท (CHAT)

### 🟠 CHAT-001 — Right Panel "หลักฐานที่ใช้" ว่างเปล่า แต่ยังใช้พื้นที่ 30%
**Severity:** 🟠 Medium  
**อาการ:** Panel ขวาแสดงทุกรายการเป็น "—" แต่ยังคงแสดง panel เต็มรูปแบบ กินพื้นที่ 30% ของ viewport  
**ผลกระทบ:** เหลือพื้นที่สำหรับ chat content น้อยลง — เสีย real estate โดยไม่ได้ประโยชน์  
**แนวทาง:** Collapse panel โดยอัตโนมัติเมื่อไม่มีหลักฐาน, หรือซ่อน panel จนกว่าจะมี AI response ที่มี citations

---

### 🟠 CHAT-002 — Context Chips ทุกอันมีสีเดียว ไม่รู้ว่า Active หรือไม่
**Severity:** 🟠 Medium  
**อาการ:** Chips สำหรับ Profile, Packs, Files ฯลฯ ทุกอันเป็นสีส้มเหมือนกัน — ไม่มี visual state ที่ชัดเจนว่า active/inactive  
**แนวทาง:** Active chip = filled สว่าง, Inactive = outline หรือ muted — ต้องเห็นความแตกต่างได้ชัด

---

### 🔵 CHAT-003 — "Profile: Not set" แสดงเป็นจุดเล็กๆ สังเกตยาก
**Severity:** 🔵 Low  
**อาการ:** แจ้งเตือน "Profile ยังไม่ได้ตั้งค่า" เป็นจุดสีส้มเล็กมากบนปุ่ม — ไม่ดึงดูดสายตา  
**แนวทาง:** เพิ่ม onboarding prompt ที่ชัดกว่า เช่น banner หรือ tooltip แรกเข้า

---

### ⚪ CHAT-004 — Empty State แนะนำให้ถามคำถาม ทั้งที่ยังไม่มีข้อมูล
**Severity:** ⚪ Info  
**อาการ:** Empty chat state ให้กำลังใจ user ถาม AI แต่ถ้ายังไม่มีไฟล์อัปโหลด AI ตอบได้จำกัดมาก  
**แนวทาง:** Empty state ควร detect ว่า user มีไฟล์หรือยัง — ถ้าไม่มี ให้แสดง "อัปโหลดไฟล์ก่อนเพื่อให้ AI ช่วยได้มากขึ้น" แทน

---

## Section 5 — Context Memory (CTX)

### 🔵 CTX-001 — Empty State ไม่มี Icon และไม่ชี้ไปที่ปุ่ม CTA
**Severity:** 🔵 Low  
**อาการ:** Empty state แสดง "ยังไม่มี Context — AI จะเริ่มบันทึกให้อัตโนมัติ เมื่อคุณใช้งาน" แต่ปุ่ม "+ สร้าง Context" อยู่ที่มุมบนขวา ห่างมาก  
**แนวทาง:** เพิ่ม icon + ปุ่ม "+ สร้าง Context" ในตัว empty state โดยตรง

---

### ⚪ CTX-002 — Search + Filter แสดงทั้งที่ไม่มีข้อมูล
**Severity:** ⚪ Info  
**อาการ:** Search bar และ dropdown "ทุกประเภท" render ตลอดเวลา แม้ list ว่างเปล่า  
**แนวทาง:** Disable หรือซ่อน search/filter เมื่อ list ว่าง เพื่อลด confusion

---

## Section 6 — ตั้งค่า MCP (MCP)

### 🔴 MCP-001 — `admin_login` Tool ปรากฏใน User MCP Tool List
**Severity:** 🔴 High  
**อาการ:** Tool ชื่อ `admin_login` ("ยืนยันรหัสผ่านแอดมิน เพื่อเข้าถึงเครื่องมือที่ปิดอยู่") ปรากฏใน tool list ของ user ทั่วไปพร้อม toggle เปิด/ปิด  
**ผลกระทบ:** Security concern — user สามารถเห็นว่ามี admin authentication mechanism อยู่, อาจพยายาม invoke tool นี้ผ่าน AI/API  
**แนวทาง:** กรอง admin-only tools ออกจาก user tool list โดยสมบูรณ์ — ควรมองเห็นเฉพาะ admin account

---

### 🟠 MCP-002 — Connector URL มี Secret Key แสดงเต็มหน้าจอ
**Severity:** 🟠 Medium  
**อาการ:** Connector URL (เช่น `https://personaldatabank.fly.dev/mcp/xVfJ3vhiLDA5-U75Mj8PqjCIFKmCTJjiods2zdW805I`) แสดงแบบ plaintext ใน card และใน JSON config block  
**ผลกระทบ:** ใครที่มองเห็นหน้าจอ (shoulder surfing) หรือ screenshot สามารถขโมย MCP access ได้ทันที  
**แนวทาง:** Mask URL บางส่วน (แสดงแค่ `https://personaldatabank.fly.dev/mcp/xVf...I`) พร้อมปุ่ม "คลิกเพื่อดูครบ" และ "คัดลอก"

---

### 🟠 MCP-003 — Tool Descriptions ภาษาไม่สม่ำเสมอ
**Severity:** 🟠 Medium  
**อาการ:** Tool ส่วนใหญ่มี description ภาษาไทย แต่ `export_file_to_chat` และ `reprocess_file` มี description ภาษาอังกฤษล้วน  
**แนวทาง:** แปล description ให้ครบทุก tool ให้ consistent

---

### 🟠 MCP-004 — ลิสต์ Tools 30 รายการพร้อมกัน ดูล้นหลาม
**Severity:** 🟠 Medium  
**อาการ:** แสดง tool cards ทั้ง 30 ตัวพร้อมกัน พร้อม description และ parameter badges — page ยาวมากและไม่มีปุ่ม "ย่อทั้งหมด"  
**แนวทาง:** เพิ่ม accordion collapse per category, หรือ "ขั้นสูง" toggle สำหรับ power user

---

### 🟠 MCP-005 — Destructive Tools มีหน้าตาเหมือน Read-Only Tools
**Severity:** 🟠 Medium  
**อาการ:** `delete_file`, `delete_pack` มี toggle style เหมือนกับ `get_profile`, `list_files` — ไม่มีสีเตือน ไม่มี label "อันตราย"  
**แนวทาง:** เพิ่ม visual indicator สำหรับ destructive tools เช่น สีแดงบน toggle, icon ⚠️, หรือย้ายไป section "เครื่องมืออันตราย" แยกต่างหาก

---

### 🔵 MCP-006 — English Labels ใน Thai UI (Context Packs, Storage Mode, MANAGED)
**Severity:** 🔵 Low  
**อาการ:** Labels เช่น "Context Packs", "Storage Mode", "MANAGED" ใน Profile modal และ MCP page เป็น English ขณะที่ text อื่นเป็น Thai  
**แนวทาง:** แปลเป็น Thai หรือกำหนด style guide ว่า term ไหนเป็น proper noun ที่ไม่แปล

---

## Section 7 — โปรไฟล์ (PROF)

### 🟠 PROF-001 — Profile Modal ไม่มีปุ่มปิด (X)
**Severity:** 🟠 Medium  
**อาการ:** Modal "โปรไฟล์ของฉัน" ไม่มีปุ่ม X — ปิดได้เฉพาะ click ที่ backdrop เท่านั้น  
**ผลกระทบ:** User ที่กรอกข้อมูลไปแล้วบางส่วนอาจกด backdrop โดยไม่ตั้งใจ → ข้อมูลหาย  
**แนวทาง:** เพิ่มปุ่ม X + confirmation dialog ถ้ามีการแก้ไขที่ยังไม่บันทึก

---

### ⚪ PROF-002 — ฟิลด์โปรไฟล์ 5 ช่อง ไม่มีคำแนะนำความยาวหรือรูปแบบ
**Severity:** ⚪ Info  
**อาการ:** ช่อง "ฉันเป็นใคร", "เป้าหมายของฉัน", "สไตล์การทำงาน" ฯลฯ มีแค่ placeholder ตัวอย่างสั้นๆ ไม่บอกว่าควรกรอกมากน้อยแค่ไหน  
**แนวทาง:** เพิ่ม character count, tip "ยิ่งละเอียด AI ยิ่งตอบได้ตรงกว่า" หรือ example responses

---

### 🔵 PROF-003 — ปุ่ม "เชื่อม LINE" อยู่ใน Profile Modal (ไม่ตรงที่)
**Severity:** 🔵 Low  
**อาการ:** ปุ่ม integration LINE อยู่กลาง profile form ระหว่างฟิลด์ต่างๆ — รู้สึกแปลกที่  
**แนวทาง:** ย้าย integrations ไปอยู่ใน section แยก "การเชื่อมต่อ" หรือ settings page

---

## Section 8 — Mobile Viewport (MOB)

### 🟠 MOB-001 — ปุ่ม "จัดระเบียบไฟล์ใหม่" ซ่อนบน Mobile
**Severity:** 🟠 Medium  
**อาการ:** `#btn-organize-new` และ `#btn-new-context` ถูกซ่อนด้วย `display: none !important` บน viewport ≤ 768px — มี FAB เป็น alternative แต่ label ไม่ชัด  
**ผลกระทบ:** User mobile อาจไม่รู้ว่า FAB ทำหน้าที่เดียวกัน — organize workflow ขาดหาย  
**แนวทาง:** ตรวจสอบ FAB tooltip/label บน mobile ให้ชัดเจน หรือแสดงปุ่ม organize ใน compact form

---

### 🟠 MOB-002 — Context Card Actions ซ่อนบน Mobile ทั้งหมด
**Severity:** 🟠 Medium  
**อาการ:** `.ctx-card-actions` ถูก `display: none !important` บน mobile — user ไม่สามารถจัดการ Context Packs บน mobile ได้เลย  
**ผลกระทบ:** Mobile user ไม่มีทางแก้ไข/ลบ context pack — feature ขาดหายโดยสมบูรณ์  
**แนวทาง:** เพิ่ม kebab menu (⋮) บน context card สำหรับ mobile เหมือนกับ file-action-mobile pattern ที่ใช้อยู่แล้ว

---

## ตารางสรุป UX/UI Issues ทั้งหมด

| ID | Section | ระดับ | สรุปปัญหา |
|----|---------|-------|-----------|
| LP-001 | Landing | 🔴 High | ไม่มีปุ่มปิด modal login/register |
| KV-001 | Knowledge | 🔴 High | คลิก entity → navigate ออกโดยไม่แจ้ง |
| MCP-001 | MCP | 🔴 High | admin_login tool ปรากฏใน user list |
| LP-002 | Landing | 🟠 Medium | พื้นที่ว่างขนาดใหญ่กลางหน้า landing |
| LP-003 | Landing | 🟠 Medium | ไม่มี confirm password ในการสมัคร |
| LP-004 | Landing | 🟠 Medium | Redirect ผ่าน /admin → black screen |
| HOME-001 | Home | 🟠 Medium | Sidebar แสดง ghost nodes แม้ files=0 |
| HOME-002 | Home | 🟠 Medium | Upload zone แสดง 80+ file types |
| HOME-003 | Home | 🟠 Medium | Privacy warning สีส้มดูเหมือน error |
| KV-002 | Knowledge | 🟠 Medium | Notes tab แสดง ghost entities |
| CHAT-001 | AI Chat | 🟠 Medium | Right panel ว่างแต่ยังใช้พื้นที่ 30% |
| CHAT-002 | AI Chat | 🟠 Medium | Context chips ทุกอันสีเดียว (ไม่รู้ active/inactive) |
| MCP-002 | MCP | 🟠 Medium | Secret key URL แสดงแบบ plaintext |
| MCP-003 | MCP | 🟠 Medium | Tool descriptions ภาษาไม่สม่ำเสมอ |
| MCP-004 | MCP | 🟠 Medium | 30 tools พร้อมกัน ดูล้นหลาม |
| MCP-005 | MCP | 🟠 Medium | Destructive tools หน้าตาเหมือน read-only |
| PROF-001 | Profile | 🟠 Medium | Profile modal ไม่มีปุ่มปิด |
| MOB-001 | Mobile | 🟠 Medium | Organize button ซ่อนบน mobile |
| MOB-002 | Mobile | 🟠 Medium | Context card actions ซ่อนบน mobile |
| LP-005 | Landing | 🔵 Low | Footer version ผิด (v7.5.0 vs v10.0.17) |
| LP-006 | Landing | 🔵 Low | ภาษาไม่สม่ำเสมอบน landing page |
| HOME-004 | Home | 🔵 Low | Empty state ไม่มีปุ่ม CTA |
| HOME-005 | Home | 🔵 Low | Unsupported file ไม่แจ้ง error |
| KV-003 | Knowledge | 🔵 Low | Tab "Notes & สรุป" ผสมภาษา |
| KV-004 | Knowledge | 🔵 Low | Collections empty state ไม่มี CTA |
| CHAT-003 | AI Chat | 🔵 Low | "Profile: Not set" dot สังเกตยาก |
| CTX-001 | Context | 🔵 Low | Empty state ไม่มี icon และ CTA |
| MCP-006 | MCP | 🔵 Low | English labels ใน Thai UI |
| PROF-003 | Profile | 🔵 Low | LINE button อยู่ผิดที่ใน profile |
| HOME-006 | Home | ⚪ Info | Filter chip มี emoji |
| LP-007 | Landing | ⚪ Info | ไม่มี ToS checkbox ใน register |
| CHAT-004 | AI Chat | ⚪ Info | Empty state แนะนำถาม AI ก่อนมีข้อมูล |
| CTX-002 | Context | ⚪ Info | Search/filter แสดงแม้ list ว่าง |
| PROF-002 | Profile | ⚪ Info | ฟิลด์โปรไฟล์ไม่มีคำแนะนำ |

---

## แนวทางการแก้ไขตามลำดับความสำคัญ

### ด่วนที่สุด (Sprint นี้)
1. **MCP-001** — ซ่อน `admin_login` จาก user tool list
2. **LP-001** — เพิ่มปุ่ม X บน Login/Register modal
3. **KV-001** — เพิ่ม breadcrumb "← กลับไป Notes" หลัง entity click navigate
4. **LP-002** — Debug blank section บน landing page
5. **MCP-002** — Mask secret key URL

### Sprint ถัดไป
6. **LP-003** — เพิ่ม confirm password field
7. **HOME-002** — ย่อ file types list บน upload zone
8. **HOME-003** — เปลี่ยน privacy warning style จากสีส้ม
9. **KV-002** — กรอง ghost entities จาก Notes tab
10. **MOB-001/002** — Fix mobile UX สำหรับ organize + context actions

### Backlog (Quality Polish)
- Language consistency ทั้งระบบ
- Footer version auto-sync
- Empty states ทุก section + CTA buttons
- Profile modal X button + unsaved changes warning

---

*QA ดำเนินการโดย ฟ้า (QA Agent) บน personaldatabank.fly.dev · 2026-05-17*  
*v10.0.17 confirmed via JS query strings · Test account: axis.solutions.team+qatest001@gmail.com*
