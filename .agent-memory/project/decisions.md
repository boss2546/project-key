# 📌 Key Design Decisions

> Decisions สำคัญพร้อมเหตุผล — เพื่อให้ agents ใหม่ไม่ตัดสินใจสวนทางโดยไม่รู้ตัว

---

## DB-001: ใช้ SQLite ไม่ใช่ Postgres
**Why:** เน้น simplicity, deploy ง่ายบน Fly.io ใน volume เดียว
**Implication:** ห้ามแนะนำ migrate ไป Postgres ถ้าไม่มี requirement ใหม่

## DB-002: ใช้ ChromaDB แบบ embedded
**Why:** ไม่ต้องรัน vector DB แยก
**Implication:** อยู่ใน `/chroma_db/` ห้าม commit ลง git

## FE-001: Frontend ยังเป็น Legacy (HTML/JS)
**Why:** ยังไม่มี budget/เวลา migrate, ยังพอใช้งานได้
**Implication:** ไม่แนะนำ migrate ไป React/Vue ในงานเล็กๆ — รอ task เฉพาะ

## AUTH-001: JWT-based auth
**Why:** stateless, เข้ากับ MCP integration ได้ดี
**Implication:** Token signing key อยู่ใน `.jwt_secret`

## MCP-001: MCP เป็น first-class feature
**Why:** จุดขายหลักของโปรเจกต์คือให้ Claude/AI access ข้อมูลได้
**Implication:** API ใหม่ทุกตัวควรพิจารณาว่ามี MCP equivalent ไหม

## BILL-001: Stripe เป็น payment provider เดียว
**Why:** v5.9.3 ลงทุนกับ Stripe integration เยอะแล้ว
**Implication:** ห้ามเสนอเพิ่ม PayPal / อื่นๆ ถ้าไม่มี request ใหม่

## TEST-001: Real DB tests, ไม่ใช่ mocks
**Why:** กันปัญหา mock/prod divergence
**Implication:** Integration tests ใช้ test DB จริง ไม่ใช่ mock

## SEC-001: Locked-data guards (v5.9.3)
**Why:** ป้องกันการแก้ไข share/reprocess/regenerate ที่ทำให้ข้อมูลเสียหาย
**Implication:** ถ้าจะเพิ่ม endpoint ที่แก้ไขไฟล์ → ต้องคิดเรื่อง lock state ด้วย

## DEPLOY-001: Fly.io เป็น production target
**Why:** มี Dockerfile + fly.toml พร้อม
**Implication:** ทุกการเปลี่ยนแปลงต้อง compatible กับ Fly volumes
