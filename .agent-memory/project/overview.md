# 📖 PDB Project Overview

## โปรเจกต์คืออะไร
**Personal Data Bank (PDB)** เป็นพื้นที่ข้อมูลส่วนตัวที่ใช้ AI ช่วยจัดระเบียบ วิเคราะห์ และเชื่อมโยงข้อมูลของผู้ใช้

**Production:** https://project-key.fly.dev/ (Fly.io app name `project-key` ยังคงเดิม — รอ custom domain ภายหลัง)
**Version:** 6.1.0

## เป้าหมายหลัก
- ผู้ใช้ upload ไฟล์ส่วนตัว (PDF, TXT, MD, DOCX) → AI จัดระเบียบให้อัตโนมัติ
- สร้าง Knowledge Graph เชื่อมโยงข้อมูลระหว่างไฟล์
- มีระบบ subscription (Stripe) แบ่งเป็น plans ต่างๆ
- เชื่อมต่อ MCP เพื่อให้ Claude/AI เข้าถึงข้อมูลผู้ใช้ได้

## ฟีเจอร์หลักที่มีอยู่แล้ว
1. **My Data** — Upload + browse ไฟล์
2. **AI Organizer** — จัดกลุ่ม + สรุป + สร้าง relations
3. **Knowledge View** — แสดงภาพรวม collections + graph
4. **MCP Integration** — 30 tools สำหรับ AI access
5. **Stripe Billing** — Plan limits, upgrade/downgrade, audit log
6. **Auth** — JWT-based authentication
7. **Context Packs** — รวมไฟล์เป็น pack ส่งให้ AI

## ผู้ใช้เป้าหมาย
- บุคคลที่อยากเก็บ + จัดระเบียบข้อมูลส่วนตัวด้วย AI
- คนที่ใช้ Claude/AI tools และอยากให้ AI เข้าถึงข้อมูลตัวเองได้

## ที่อยู่ของ Source Code
- Repo: d:\PDB\
- Backend: `/backend/` (Python FastAPI)
- Frontend: `/legacy-frontend/` (HTML/CSS/JS — ยังไม่ได้ migrate เป็น framework)
- Tests: ตามไฟล์ `_test_*.py` และตามโฟลเดอร์
- Docs: `/docs/`, `/DESIGN.md`, `/README.md`

## สถานะปัจจุบัน
- ✅ Production live แล้ว
- ✅ Stripe integration ทำงานได้
- ✅ Test suite (13 tests) pass 100%
- 🚧 Frontend ยังเป็น legacy (HTML+JS) ยังไม่ได้ migrate เป็น React/Vue
