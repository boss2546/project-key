
---

# PRD — Project KEY MVP v0.1

## 1. Overview

### Product Name

Project KEY — MVP v0.1

### Product Definition

แพลตฟอร์มส่วนตัวสำหรับรับไฟล์สำคัญที่กระจัดกระจายเข้ามา จัดให้เป็นระบบ สรุปเป็นไฟล์ Markdown และนำข้อมูลนั้นไปใช้กับ AI ได้อย่างควบคุมได้

### One-line Product Statement

**Store → Organize → Reuse with AI**

### Vision Alignment

MVP นี้ยึด 4 แกนของ Vision:

* เก็บข้อมูลสำคัญไว้อย่างดี
* เป็นส่วนตัว
* เป็นระบบ
* นำไปใช้ได้อย่างไร้รอยต่อ 

Vision ใหญ่ของโปรเจกต์คือทำให้ข้อมูลสำคัญของมนุษย์ถูกเก็บรักษาอย่างดี เป็นส่วนตัว เป็นระบบ และพร้อมถูกนำไปใช้ต่อได้ในทุกบริบทอย่างไร้รอยต่อ 
ในเชิง execution แนวคิดนี้ถูกวางให้เป็นทั้ง data repository, permission layer, retrieval layer และ connector layer สำหรับ AI 

---

## 2. Problem Statement

ผู้ใช้มีข้อมูลสำคัญจำนวนมาก แต่ข้อมูลเหล่านั้น:

* กระจัดกระจาย
* ไม่มีโครงสร้าง
* หาไม่เจอเวลาต้องใช้
* ต้องอัปโหลดซ้ำ
* ต้องอธิบายใหม่ซ้ำๆ ให้ AI

ปัญหาที่แท้จริงไม่ใช่แค่ “ไฟล์รก” แต่คือ **Context Loss, Data Friction และ Personalization Gap** หรือพูดอีกแบบคือผู้ใช้ขาดระบบที่ช่วยให้ AI เข้าใจเขาได้ดีขึ้น 

---

## 3. Goal

### Primary Goal

สร้างระบบส่วนตัวที่ช่วยให้ผู้ใช้:

1. ฝากไฟล์สำคัญเข้าไปในระบบ
2. ให้ระบบจัดข้อมูลให้เป็นกลุ่ม
3. ให้ระบบประเมินความสำคัญ
4. สร้างไฟล์สรุป `.md`
5. ใช้ข้อมูลเหล่านั้นกับ AI ได้โดยไม่ต้องหาไฟล์เองทุกครั้ง

### Success Outcome for Users

ผู้ใช้ควรรู้สึกว่า:

* ไม่ต้องหาไฟล์เองทุกครั้ง
* เห็นว่าไฟล์ไหนอยู่เรื่องเดียวกัน
* รู้ว่าไฟล์ไหนสำคัญ
* ใช้ AI ได้ลื่นขึ้นและตรงขึ้น

Lean เดิมของโปรเจกต์ก็ชี้ชัดว่าคุณค่าที่ต้องเกิดคือ AI เข้าใจผู้ใช้มากขึ้น, ไม่ต้องเริ่มใหม่ทุกครั้ง, ไม่ต้องหาไฟล์ส่งใหม่ซ้ำๆ, และการใช้ AI ลื่นขึ้น 

---

## 4. Scope of MVP v0.1

## In Scope

### A. Private Personal Data Space

ระบบต้องมีพื้นที่ส่วนตัวสำหรับเก็บไฟล์ของผู้ใช้

* ผู้ใช้ 1 คนเห็นเฉพาะข้อมูลของตัวเอง
* ไฟล์ต้นฉบับต้องถูกเก็บไว้
* ข้อมูลทุกชิ้นต้องผูกกับ owner

### B. Multi-file Upload

รองรับไฟล์รอบแรก:

* PDF
* TXT
* MD
* DOCX

### C. Text Extraction

ระบบต้องดึงข้อความจากไฟล์ออกมาเพื่อนำไปจัดระเบียบและสรุปต่อ

### D. Organization Engine

ระบบต้องทำได้ 3 อย่าง:

1. **Grouping** — ไฟล์ไหนอยู่เรื่องเดียวกัน
2. **Importance Scoring** — ไฟล์ไหนสำคัญกว่า
3. **Markdown Summary Generation** — สร้างไฟล์ `.md` ของแต่ละไฟล์

### E. AI Chat with Controlled Retrieval

ผู้ใช้ถาม AI ได้
ระบบต้องเลือกข้อมูลที่เกี่ยวจากพื้นที่ส่วนตัว แล้วส่งเข้า AI ในรูปแบบที่เหมาะสม:

* `.md summary`
* excerpt
* raw extracted text

### F. Source Visibility

ระบบต้องแสดงให้ผู้ใช้เห็นว่า AI ใช้ข้อมูลอะไรตอบ

---

## Out of Scope

ยังไม่ทำในรอบนี้:

* graph view
* auto move/rename file จริง
* sharing / revoke access
* multi-user collaboration
* image/audio/video parsing
* OCR ขั้นสูงเป็นแกนหลัก
* mobile app
* external connectors
* permission system ซับซ้อนระดับองค์กร
* agent หลายตัว
* long-term memory ข้ามหลายเดือน

---

## 5. Target User

### Primary User

Heavy AI users ที่มีไฟล์/โน้ต/เอกสารเยอะ และใช้ AI ในการเรียนหรือทำงานอยู่แล้ว

### Early Adopter Wedge

ผู้ใช้ที่มี pain ชัดเรื่อง:

* ต้องหาไฟล์บ่อย
* ต้องอธิบาย context ใหม่ให้ AI บ่อย
* ต้องรวมข้อมูลหลายไฟล์ก่อนเริ่มคุยกับ AI

ก่อนหน้านี้แนวคิดเริ่มต้นที่เหมาะสมถูกสรุปไว้ว่าไม่ควรเริ่มจาก platform ใหญ่ทันที แต่ควรเริ่มจาก use case แคบที่ชัดก่อน 

---

## 6. User Stories

### Upload

* ในฐานะผู้ใช้ ฉันต้องการอัปโหลดหลายไฟล์พร้อมกัน เพื่อให้ไม่ต้องจัดไฟล์ทีละชิ้น

### Organize

* ในฐานะผู้ใช้ ฉันต้องการให้ระบบช่วยบอกว่าไฟล์ไหนเกี่ยวกัน เพื่อให้ฉันเห็นภาพรวมเร็วขึ้น

### Prioritize

* ในฐานะผู้ใช้ ฉันต้องการรู้ว่าไฟล์ไหนสำคัญกว่า เพื่อให้หยิบใช้ถูกก่อน

### Summarize

* ในฐานะผู้ใช้ ฉันต้องการไฟล์สรุป `.md` ของแต่ละไฟล์ เพื่อให้ AI ใช้งานต่อได้ง่าย

### Chat with AI

* ในฐานะผู้ใช้ ฉันต้องการถาม AI แล้วให้ระบบเลือกข้อมูลที่เกี่ยวให้ เพื่อไม่ต้องเปิดหาไฟล์เองทุกครั้ง

### Transparency

* ในฐานะผู้ใช้ ฉันต้องการเห็นว่า AI ใช้ไฟล์ไหนบ้าง เพื่อให้ฉันเชื่อถือคำตอบได้

---

## 7. Core User Flow

### Flow 1: Upload

ผู้ใช้อัปโหลดไฟล์หลายไฟล์เข้า “My Data”

### Flow 2: Process

ระบบ:

* เก็บ raw file
* extract text
* เก็บ metadata

### Flow 3: Organize

ระบบ:

* จัดกลุ่มไฟล์
* ให้คะแนนความสำคัญ
* สร้าง `.md summary`

### Flow 4: Browse

ผู้ใช้เข้า Organized View เพื่อดูว่า:

* มี cluster อะไรบ้าง
* ไฟล์ไหนสำคัญ
* สรุปของไฟล์คืออะไร

### Flow 5: Ask AI

ผู้ใช้ถามคำถามใน AI Chat

### Flow 6: Retrieve

ระบบเลือก:

* cluster ที่เกี่ยว
* ไฟล์ที่เกี่ยว
* mode ที่ใช้: summary / excerpt / raw

### Flow 7: Answer

AI ตอบพร้อมแสดง sources ที่ใช้

---

## 8. Screens

## Screen 1: My Data

หน้ารวมไฟล์ทั้งหมดของผู้ใช้

### Must-have Components

* Upload area
* File list
* File type
* Uploaded time
* Processing status

### States

* Empty state
* Uploading state
* Processing state
* Completed state
* Error state

---

## Screen 2: Organized View

หน้าที่แสดงผลการจัดระเบียบ

### Must-have Components

* Cluster cards / list
* Primary file badge
* Importance label
* `.md summary` preview
* Related files

### States

* No clusters yet
* Organized complete
* Re-processing

---

## Screen 3: AI Chat

หน้าคุยกับ AI

### Must-have Components

* Chat input
* Answer area
* Used sources panel
* Selected cluster/files
* Retrieval mode indicator

### States

* No context selected yet
* AI answering
* Answer with sources
* Error state

---

## 9. Functional Requirements

## FR-1 Upload

ระบบต้องให้อัปโหลดหลายไฟล์พร้อมกันได้

## FR-2 Storage

ระบบต้องเก็บไฟล์ต้นฉบับไว้โดยไม่แก้ไข

## FR-3 Extraction

ระบบต้อง extract text จาก PDF, TXT, MD, DOCX ได้

## FR-4 Metadata

ระบบต้องเก็บ metadata ขั้นต่ำ:

* filename
* filetype
* uploaded_at
* owner
* processing_status

## FR-5 Grouping

ระบบต้องจัดไฟล์เป็นกลุ่มตามความเชื่อมโยงได้

## FR-6 Importance Scoring

ระบบต้องให้คะแนนความสำคัญของแต่ละไฟล์ได้

## FR-7 Primary Candidate

ระบบต้องระบุได้ว่าไฟล์ไหนน่าจะเป็นไฟล์หลักของ cluster

## FR-8 Markdown Summary

ระบบต้องสร้างไฟล์ `.md` สรุปสำหรับแต่ละไฟล์

## FR-9 AI Retrieval

ระบบต้องเลือกข้อมูลที่เกี่ยวกับคำถามผู้ใช้ได้ก่อนส่งเข้า AI

## FR-10 Explainability

ระบบต้องแสดง source ที่ใช้ตอบได้

## FR-11 Privacy

ผู้ใช้ต้องเห็นเฉพาะข้อมูลของตัวเอง

---

## 10. Organization Logic

## Grouping Logic

รอบแรกใช้หลัก:

* semantic similarity จาก extracted text
* filename hints
* shared keywords

ผลลัพธ์:

* cluster id
* cluster title
* member files

## Importance Scoring Logic

รอบแรกใช้หลัก:

* ความครบของเนื้อหา
* ความยาวที่มีสาระ
* ความชัดของชื่อไฟล์
* ความใหม่
* ความน่าจะเป็นว่าเป็นไฟล์หลัก/ไฟล์ final

ผลลัพธ์:

* score 0–100
* label: high / medium / low
* primary candidate

## Markdown Summary Logic

ทุกไฟล์ต้องมี `.md summary` 1 ไฟล์

---

## 11. Markdown Summary Spec

```md
---
file_id: <id>
original_filename: <filename>
filetype: <pdf/docx/txt/md>
cluster: <cluster title>
importance_score: <0-100>
importance_label: <high/medium/low>
is_primary_candidate: <true/false>
uploaded_at: <timestamp>
---

# Summary
สรุปเนื้อหาหลักของเอกสารนี้

# Key Topics
- ...
- ...
- ...

# Key Facts
- ...
- ...
- ...

# Why This File Matters
- ...
- ...

# Suggested Usage
- ใช้ตอน...
- ควรใช้เป็น summary / excerpt / raw
```

---

## 12. Retrieval Logic for AI Chat

เมื่อผู้ใช้ถาม:

1. ระบบหา cluster ที่เกี่ยว
2. ระบบเลือกไฟล์ที่เด่นใน cluster
3. ระบบเลือก mode

### Default Rules

* ใช้ `.md summary` เป็นค่าเริ่มต้น
* ใช้ excerpt เมื่อคำถามเจาะเฉพาะบางส่วน
* ใช้ raw extracted text เมื่อจำเป็นต้องละเอียด

แก่นนี้สอดคล้องกับแนวคิดเดิมของโปรเจกต์ที่ต้อง “จัดหมวด จัดลำดับ ค้นหาได้ เรียกใช้ได้ตามบริบท และพร้อมนำไปใช้กับ AI” 

---

## 13. Non-functional Requirements

* ต้องเป็น private by default
* UI ต้องเรียบ เข้าใจง่าย เหมาะกับการขึ้นบน Antigravity
* flow ต้องเป็น linear: Upload → Process → Organize → Chat
* ระบบต้องอธิบายได้ว่าใช้ source ไหน
* ต้องพร้อมต่อยอดไปสู่ platform ที่ใหญ่กว่าในอนาคต

Vision เดิมก็บอกไว้ชัดว่าข้อมูลไม่ควรถูกขังในระบบเดียว แต่ควรถูกใช้ได้ในหลายบริบทอย่างไร้รอยต่อ 

---

## 14. Tech Direction

### Product Direction

สร้าง **web app ของเราเอง**
ไม่ยึด note app หรือ graph app ตัวอื่นเป็นฐานหลัก

### Recommended Build Direction

* Frontend: Next.js
* Backend: FastAPI
* Parsing: Docling
* Metadata DB: Postgres
* File Storage: object storage
* Similarity Search: vector search แบบเบา
* LLM layer: สำหรับ summarize / cluster title / answer generation

---

## 15. Open-source Usage Strategy

เราใช้โอเพ่นซอร์สเป็น “ส่วนประกอบ” ไม่ใช่เป็น product foundation ทั้งก้อน

### Use as Core Components

* Doc parsing
* Similarity / retrieval
* LLM orchestration บางส่วน

### Do Not Use as Main Product Base

* ไม่ผูก UX หลักกับ note app
* ไม่ผูก product model กับ graph editor
* ไม่เริ่มจาก plugin ecosystem

---

## 16. Success Metrics

### Product Metrics

* จำนวนไฟล์ที่อัปโหลดสำเร็จ
* สัดส่วนไฟล์ที่ parse สำเร็จ
* จำนวน cluster ที่สร้างได้

### UX Metrics

* ผู้ใช้รู้สึกว่าหาไฟล์เองน้อยลง
* ผู้ใช้เห็นว่าไฟล์ไหนสำคัญขึ้น
* ผู้ใช้เข้าใจว่า AI ใช้ source อะไร

### Outcome Metrics

* จำนวนเคสที่ผู้ใช้บอกว่า AI ใช้ง่ายขึ้น
* จำนวนเคสที่บอกว่าอธิบายใหม่น้อยลง
* จำนวนเคสที่ยินดีใช้ต่อหรือแนะนำต่อ

Lean เดิมก็ใช้ metric แนวเดียวกัน เช่น AI ใช้ง่ายขึ้น, หาไฟล์/อธิบายใหม่น้อยลง, และ willingness to continue/refer 

---

## 17. Release Plan

## Sprint 1

* Upload
* Raw file storage
* Text extraction
* Metadata storage

## Sprint 2

* Grouping
* Importance scoring
* `.md summary` generation
* Organized View

## Sprint 3

* AI Chat
* Retrieval logic
* Source visibility

---

## 18. Risks

### Risk 1

Grouping ไม่แม่นพอ
**Mitigation:** ให้ user override ได้ใน phase ถัดไป

### Risk 2

Importance scoring ไม่ตรงความคาดหวัง
**Mitigation:** แสดงเหตุผล why_important

### Risk 3

AI ใช้ context ผิด
**Mitigation:** แสดง source และ retrieval mode ให้ผู้ใช้เห็น

### Risk 4

Scope บวม
**Mitigation:** ยึด 3 screens และ 3 core capabilities เท่านั้น

---

## 19. Final Scope Lock

MVP v0.1 ล็อกไว้ที่:

* Private personal file space
* Multi-file upload
* Text extraction
* Grouping
* Importance scoring
* `.md` summary generation
* AI chat with controlled retrieval
* Source transparency

ทุกอย่างนอกเหนือจากนี้ถือว่า **out of scope**

---

## 20. Final Summary

นี่ไม่ใช่แค่ “chat with files”
แต่คือ **ชั้นแรกของ Personal Data Bank** ที่เริ่มจากสิ่งเล็กที่สุดซึ่งยังตรงกับ Vision:
ทำให้ข้อมูลสำคัญถูกเก็บไว้อย่างดี เป็นส่วนตัว ถูกจัดเป็นระบบ และถูกนำไปใช้กับ AI ได้อย่างไร้รอยต่อ 

