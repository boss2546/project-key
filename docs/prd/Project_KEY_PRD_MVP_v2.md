# PRD — Project KEY MVP v2

## 1. Overview

### Product Name
Project KEY — MVP v2

### Product Definition
แพลตฟอร์มพื้นที่ข้อมูลส่วนตัวที่ช่วยให้ผู้ใช้เก็บไฟล์สำคัญ จัดให้เป็นระบบ สร้าง AI-ready summaries และใช้ข้อมูลเหล่านั้นกับ AI chat ได้อย่างต่อเนื่องมากขึ้นผ่าน **User Profile**, **Context Packs**, **Hybrid Retrieval**, และ **Automatic Context Injection** โดยยังคงยึดแกน “Data Bank first, Second Brain later” เป็นหลัก

### One-line Product Statement
**Store → Organize → Summarize → Inject Context → Reuse with AI**

### Strategic Position
MVP v2 ไม่ใช่การเปลี่ยน product ไปเป็น Second Brain เต็มรูป แต่เป็นการเพิ่ม **Second Brain layer เฉพาะใน AI Chat** บนฐานของระบบเดิมที่ทำ Store, Organize, Summarize และ AI retrieval ได้แล้ว

---

## 2. Vision Alignment

Vision ของ Project KEY ยังคงเหมือนเดิม: ข้อมูลสำคัญควรถูกเก็บไว้อย่างดี เป็นส่วนตัว เป็นระบบ และถูกนำไปใช้ได้อย่างไร้รอยต่อ

MVP v1 ทำได้ดีในเรื่อง:
- เก็บไฟล์ต้นฉบับ
- จัดระบบอัตโนมัติ
- สร้าง `.md` summaries
- ใช้กับ AI ได้อย่างควบคุม
- แสดง source transparency

MVP v2 จึงมีหน้าที่เติมช่องว่างสำคัญคือ
- ทำให้ AI เริ่ม “เข้าใจผู้ใช้” มากขึ้น
- ทำให้บริบท “ต่อเนื่อง” มากขึ้น
- ลดการที่ผู้ใช้ต้องอธิบายใหม่ทุกครั้ง

---

## 3. Problem Statement

### Core Problem
แม้ผู้ใช้จะมีไฟล์และข้อมูลอยู่แล้ว แต่ AI ยังไม่เข้าใจผู้ใช้และบริบทได้อย่างต่อเนื่อง ทำให้:
- ต้องเริ่มใหม่เมื่อเปิดแชทใหม่
- ต้องหาไฟล์ส่งใหม่ซ้ำๆ
- ต้องอธิบายตัวเองซ้ำ
- คำตอบยัง generic หรือไม่ตรงใจ

### Product Interpretation
ปัญหาที่แท้จริงไม่ใช่แค่ file organization แต่คือ:
- **Context Loss**
- **Data Friction**
- **Personalization Gap**

### Why v2 Exists
MVP v1 แก้ “ไฟล์พร้อมใช้กับ AI” ได้แล้ว  
MVP v2 จะต้องแก้ “AI เริ่มเข้าใจเจ้าของไฟล์และบริบทที่ต่อเนื่องมากขึ้น” ให้ได้

---

## 4. Goals of MVP v2

### Primary Goal
เปลี่ยน AI Chat จาก
- “chat กับไฟล์ที่จัดแล้ว”

ไปเป็น
- “chat กับข้อมูลของฉัน + profile ของฉัน + context packs ของฉัน”

### User Outcome
ผู้ใช้ควรรู้สึกว่า:
- AI รู้จักฉันมากขึ้น
- ไม่ต้องปูพื้นใหม่ทุกครั้ง
- ไม่ต้องเลือกไฟล์เองบ่อยๆ
- คำตอบตรงขึ้นเพราะระบบดึง profile + context + files ที่เกี่ยวให้

### Strategic Goal
ยืนยันว่า Product KEY สามารถขยับจาก **AI-ready Data Layer** ไปสู่ **Context Delivery Layer** ได้จริง

---

## 5. Scope of MVP v2

## In Scope

### A. Keep existing v1 foundation
ยังคงใช้ของเดิมทั้งหมด:
- Private personal file space
- Multi-file upload
- Text extraction
- Collections / grouping
- Importance scoring
- `.md` summary generation
- AI chat with controlled retrieval
- Source visibility

### B. Add User Profile Layer
เพิ่ม object หรือ file กลางลักษณะ `me.md` / `profile-context.md` เพื่อเก็บข้อมูลระดับผู้ใช้ เช่น:
- role / identity
- goals
- work or study context
- preferred answer style
- important background
- recurring needs

### C. Add Context Pack Layer
เพิ่มไฟล์สรุประดับสูงกว่าไฟล์เดี่ยว เช่น:
- profile-context.md
- study-context.md
- work-context.md
- project-context.md

หน้าที่ของ context packs คือ distill ไฟล์ดิบหลายไฟล์ให้กลายเป็น “บริบทพร้อมใช้” แบบ reusable

### D. Add Hybrid Retrieval
จากเดิมที่ใช้ TF-IDF + LLM selection ใน v1  
v2 ต้องเพิ่ม retrieval แบบสองทาง:
- semantic retrieval
- keyword retrieval

### E. Add Automatic Context Injection
ก่อนส่ง prompt เข้า AI chat ระบบต้องเลือกและ inject บริบทอัตโนมัติจาก:
- User profile
- Relevant context packs
- Relevant collections
- Relevant file summaries / excerpts / raw

นี่คือหัวใจของ v2

## Out of Scope
ยังไม่ทำใน v2:
- Daily brief
- Monthly retro
- Per-session learning loop เต็มรูป
- Multi-agent teams
- Autonomous research mode
- External tools integrations จำนวนมาก
- Cross-tool orchestration เต็มรูป
- Collaboration
- Enterprise permissions
- Mobile app

---

## 6. Target User

### Primary User
Heavy AI users ที่มีข้อมูลกระจัดกระจายและใช้ AI ซ้ำๆ อยู่แล้ว เช่น:
- นักศึกษาที่ใช้ AI เรียน / สรุป / ติว
- คนทำงานความรู้
- ฟรีแลนซ์
- นักการตลาด
- ครีเอเตอร์

### Why This User
กลุ่มนี้เจอ pain ของ context loss ชัดที่สุด และยิ่งใช้ AI มาก pain ยิ่งแรง เพราะต้องเตรียม context ใหม่บ่อยๆ

---

## 7. Core User Stories

### Profile
- ในฐานะผู้ใช้ ฉันต้องการให้ระบบรู้จักฉันในระดับพื้นฐาน เพื่อให้ AI ไม่ต้องเริ่มจากศูนย์ทุกครั้ง

### Context Pack
- ในฐานะผู้ใช้ ฉันต้องการให้ระบบสรุปบริบทระดับวิชา/งาน/โปรเจกต์ เป็นแพ็กพร้อมใช้ เพื่อให้ไม่ต้องประกอบ context เองทุกครั้ง

### Smarter Retrieval
- ในฐานะผู้ใช้ ฉันต้องการให้ระบบค้นทั้ง “ความหมาย” และ “คำเฉพาะ” เพื่อให้ AI ดึงข้อมูลที่เกี่ยวได้แม่นขึ้น

### Automatic Context Injection
- ในฐานะผู้ใช้ ฉันต้องการให้ AI ดึง profile และ context ที่เกี่ยวให้เองก่อนตอบ เพื่อให้คำตอบต่อเนื่องและตรงขึ้น

### Transparency
- ในฐานะผู้ใช้ ฉันต้องการรู้ว่า AI ใช้ profile, context pack, collection, และไฟล์อะไรบ้าง เพื่อให้เชื่อใจคำตอบได้

---

## 8. Core UX Flow

### Flow 1: User sets up profile
ผู้ใช้สร้างหรือแก้ไข Profile ของตัวเอง

### Flow 2: Files are uploaded and organized
ระบบ v1 ทำงานเหมือนเดิม:
- store raw files
- extract text
- organize into collections
- score importance
- generate `.md` summaries

### Flow 3: System builds context packs
ระบบรวบหลายไฟล์หรือหลาย collection เป็นบริบทระดับสูง เช่น project context หรือ study context

### Flow 4: User asks AI
ผู้ใช้ถามในหน้า AI Chat

### Flow 5: Automatic context selection
ระบบเลือก:
- user profile
- relevant context packs
- relevant collections
- relevant files
- retrieval mode ที่เหมาะ

### Flow 6: AI answers with context transparency
AI ตอบพร้อมแสดงว่าใช้:
- profile หรือไม่
- context pack ไหน
- collection ไหน
- file ไหน
- retrieval mode ใด

---

## 9. Screens

## Screen 1: My Data
ใช้เหมือน v1 เป็นหลัก  
อาจเพิ่ม card หรือ summary เล็กๆ ว่า profile และ context packs พร้อมหรือยัง

### New Elements
- Profile setup status
- Context pack generation status

## Screen 2: Collections
ยังคงเป็นหน้าจัดระบบไฟล์  
แต่เพิ่มมุมมองเชื่อมไปยัง context packs

### New Elements
- Context pack suggestions
- Derived from these collections/files

## Screen 3: AI Chat
เป็นหน้าที่เปลี่ยนมากที่สุดใน v2

### Must-have New Components
- “My Profile” indicator
- “Injected Context” panel
- “Context Packs Used” section
- “Why this context was selected” section
- clearer separation between:
  - profile
  - context pack
  - collection
  - file

---

## 10. Functional Requirements

### FR-1 User Profile
ระบบต้องให้ผู้ใช้สร้างและแก้ไข profile context ได้

### FR-2 Profile Storage
ระบบต้องเก็บ profile เป็น structured object หรือ markdown file ที่ AI ใช้ได้

### FR-3 Context Pack Generation
ระบบต้องสร้าง context packs จากหลายไฟล์หรือหลาย collections ได้

### FR-4 Context Pack Types
ระบบต้องรองรับอย่างน้อย:
- profile
- study
- work
- project

### FR-5 Hybrid Retrieval
ระบบต้องค้นข้อมูลด้วยทั้ง semantic retrieval และ keyword retrieval

### FR-6 Automatic Context Injection
ระบบต้อง inject profile + context packs + relevant file context ก่อน AI ตอบ

### FR-7 Context Transparency
ระบบต้องแสดงว่ามีการ inject context อะไรบ้าง

### FR-8 Existing v1 Functions Remain
ระบบต้องรักษา:
- grouping
- importance scoring
- primary file detection
- `.md` summaries
- source visibility จาก v1 ไว้ทั้งหมด

---

## 11. Data Model Additions

ของเดิมจาก v1 ยังอยู่ครบ เช่น `files`, `clusters`, `file_summaries`, `chat_queries`  
v2 เพิ่มดังนี้

## Entity: UserProfile
- user_id
- identity_summary
- goals
- working_style
- preferred_output_style
- background_context
- updated_at

## Entity: ContextPack
- id
- user_id
- type
- title
- summary_text
- md_path
- source_file_ids
- source_cluster_ids
- updated_at

## Entity: ContextInjectionLog
- id
- chat_query_id
- profile_used
- context_pack_ids
- file_ids
- retrieval_reason
- created_at

---

## 12. AI Chat Logic in v2

### Current v1 logic
v1 ทำ:
- vector search
- LLM context selection
- answer generation

### New v2 logic
v2 ต้องทำแบบนี้:

1. Parse user question  
2. Retrieve profile context  
3. Retrieve relevant context packs  
4. Retrieve relevant collections/files using hybrid retrieval  
5. Assemble injected context block  
6. Send enriched prompt to answer model  
7. Return answer + context usage explanation

### Context Priority
ระบบควรมีลำดับหยิบ context แบบนี้:
1. User profile
2. Relevant context packs
3. Relevant collection summaries
4. Relevant file summaries
5. Excerpts / raw text เมื่อจำเป็น

---

## 13. Context Pack Specification

ตัวอย่างประเภทที่ควรมีใน v2

### profile-context.md
- user role
- goals
- answer preferences
- recurring context

### study-context.md
- current subjects
- exam priorities
- preferred study style
- key materials

### work-context.md
- current work themes
- stakeholders
- recurring tasks
- important references

### project-context.md
- project purpose
- active documents
- current status
- important files
- known decisions

---

## 14. Technical Direction

### Foundation
ใช้ระบบ v1 ต่อไปก่อน:
- FastAPI
- SQLite/local dev
- existing organization engine
- existing markdown summary layer
- existing AI chat flow

### Changes in v2
- add UserProfile module
- add ContextPack generation module
- add hybrid retrieval module
- add context injection assembly step
- extend chat UI

### Important Principle
ไม่ยกเครื่องทั้งระบบ  
แต่เติม **Second Brain Chat Layer** บนฐานที่มีอยู่

---

## 15. Success Metrics

### Product Metrics
- จำนวนผู้ใช้ที่ตั้งค่า profile เสร็จ
- จำนวน context packs ที่ถูกสร้าง
- สัดส่วน chat queries ที่ใช้ context injection

### UX Metrics
- ผู้ใช้รู้สึกว่า AI เข้าใจมากขึ้นหรือไม่
- ผู้ใช้รู้สึกว่าเริ่มใหม่บ่อยน้อยลงหรือไม่
- จำนวนครั้งที่ผู้ใช้ต้องเลือกไฟล์เองลดลงหรือไม่

### Outcome Metrics
- จำนวนเคสที่ผู้ใช้บอกว่า AI ตรงขึ้น
- จำนวนเคสที่ผู้ใช้บอกว่าใช้ AI ลื่นขึ้น
- willingness to continue / willingness to pay

---

## 16. Risks

### Risk 1
Profile ไม่ดีพอจน AI เข้าใจ user ผิด  
**Mitigation:** ให้ user edit profile ได้ง่าย

### Risk 2
Context pack คุณภาพต่ำ  
**Mitigation:** ให้ preview / regenerate ได้

### Risk 3
Injection มากเกินจน prompt bloated  
**Mitigation:** จำกัด context priority และ token budget

### Risk 4
Hybrid retrieval ซับซ้อนเกินไปเร็วเกิน  
**Mitigation:** เริ่มแบบ lightweight ก่อน ไม่ต้อง over-engineer

### Risk 5
หลุดจาก Data Bank ไปเป็น second brain ใหญ่เกิน  
**Mitigation:** ยึดหลักว่า v2 เติมเฉพาะ AI chat layer ไม่เปิด scope ไป daily brief / agent systems

---

## 17. Release Plan

### Sprint 1
- UserProfile model + UI
- profile setup / edit flow
- AI chat reads profile

### Sprint 2
- ContextPack model
- generate profile/work/study/project packs
- collections to context-pack mapping

### Sprint 3
- Hybrid retrieval
- keyword + semantic combination
- improved file/context ranking

### Sprint 4
- Automatic context injection
- UI transparency for injected context
- tuning and evaluation

---

## 18. Final Scope Lock

MVP v2 ล็อกที่:

- v1 foundation ทั้งหมด
- User Profile layer
- Context Pack layer
- Hybrid Retrieval
- Automatic Context Injection
- AI Chat transparency ที่ละเอียดขึ้น

ทุกอย่างนอกเหนือจากนี้ถือว่า later-stage second brain features

---

## 19. Final Summary

MVP v2 คือการต่อยอดจากระบบเดิมที่ช่วยให้ไฟล์พร้อมใช้กับ AI ไปสู่ระบบที่ช่วยให้ **AI เริ่มเข้าใจผู้ใช้และบริบทของเขาได้ต่อเนื่องมากขึ้น** โดยใช้แนวคิดจาก second brain เฉพาะในชั้นแชท ไม่ใช่เปลี่ยน product ทั้งตัวให้กลายเป็น second brain ตั้งแต่ตอนนี้
