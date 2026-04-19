# PRD — Project KEY MVP v4

## 1. Overview

### Product Name
**Project KEY — MVP v4**

### Product Definition
ระบบ **Personal Data Bank Connector Layer** ที่ต่อยอดจากพื้นที่ข้อมูลส่วนตัว, context layer, และ knowledge workspace เดิม ให้สามารถ **เชื่อมกับ AI ภายนอกได้จริง** โดยเริ่มจาก **Claude custom connector ผ่าน remote MCP** ก่อน เพื่อให้ผู้ใช้ดึง profile, context packs, summaries, และ knowledge search จาก Project KEY ไปใช้ใน Claude ได้แบบ read-only, เป็นส่วนๆ, และควบคุมได้ในระดับพื้นฐาน

### One-line Product Statement
**Store → Organize → Connect → Share by Slice → Use with External AI**

### Strategic Position
v4 ไม่ใช่การเปลี่ยนทิศของโปรเจกต์  
แต่เป็นการขยับจาก:
- v1: file-ready for AI
- v2: context-ready for AI
- v3: relationship-aware knowledge workspace

ไปสู่:
- **v4: controlled external AI access layer**

หรือพูดอีกแบบ:
> v4 คือชั้นที่ทำให้ Project KEY เริ่มเป็น **PDB ที่ใช้ข้ามเครื่องมือได้จริง** ไม่ใช่แค่ใช้ในแอปเราเอง

---

## 2. Vision Alignment

Vision หลักของโปรเจกต์ยังเหมือนเดิม:

> ข้อมูลและความทรงจำสำคัญของทุกคนควรถูกเก็บไว้อย่างดี เป็นส่วนตัว และเป็นระบบ และถูกนำไปใช้ได้อย่างไร้รอยต่อ

สำหรับ PDB โดยเฉพาะ เรายืนยันภาพใหญ่ว่า:
- เป็นศูนย์กลางข้อมูลส่วนบุคคล
- ดึงใช้ได้ตามบริบท
- ควบคุมสิทธิ์ได้
- เชื่อมกับ AI และบริการต่างๆ ได้ง่ายที่สุด
- เป้าหมายเชิงสั้นคือ **“Upload once, use anywhere, connect with any AI securely.”**

MVP v4 จึงสอดคล้องกับ vision โดยตรง เพราะมันเติม 2 เสาหลักที่ระบบก่อนหน้านี้ยังไม่เด่นพอ:
- **Seamless Use across tools**
- **Consent / Controlled Access**

---

## 3. Problem Statement

### Core Problem
แม้ผู้ใช้จะมีข้อมูลอยู่ใน Project KEY แล้ว แต่ข้อมูลนั้นยังติดอยู่ในระบบเราเป็นหลัก  
เมื่อจะใช้กับ AI ภายนอก เช่น Claude ผู้ใช้ยังต้อง:
- copy/paste เอง
- export เอง
- อธิบายบริบทใหม่
- หรือไม่มีทางให้ AI ภายนอกเข้าถึง data slice ที่เหมาะสมได้เลย

### Deeper Interpretation
ปัญหาของ v4 คือ:

1. **Tool boundary friction**  
   ข้อมูลอยู่ในระบบเรา แต่ AI ที่ผู้ใช้อยากใช้จริงอยู่อีกระบบ

2. **No controlled external access**  
   ยังไม่มีชั้นกลางที่ทำให้ AI ภายนอกเข้าถึงข้อมูลได้แบบ “เฉพาะส่วนที่อนุญาต”

3. **Context portability gap**  
   profile, context packs, summaries, และ knowledge graph ของผู้ใช้ ยังไม่ portable ไปสู่ AI ภายนอกได้ดีพอ

### Why v4 Exists
v1-v3 ทำให้ข้อมูลพร้อมใช้ “ภายใน Project KEY” มากขึ้นเรื่อยๆ  
v4 ต้องทำให้ข้อมูลชุดนั้น **เริ่มออกไปใช้กับ AI ภายนอกได้จริง** อย่างน้อยกับ Claude ก่อน

---

## 4. Goals of MVP v4

### Primary Goal
ทำให้ Claude ผ่าน custom connector / remote MCP สามารถเรียกข้อมูลจาก Project KEY ได้แบบ **read-only** และ **เป็นส่วนๆ** โดยไม่ต้องเปิดทั้งคลังข้อมูล

### Secondary Goals
1. พิสูจน์ว่า Project KEY สามารถทำหน้าที่เป็น **connector layer for AI** ได้จริง
2. ทำให้ user ที่มีความรู้เทคนิคระดับหนึ่งสามารถเชื่อม Claude กับ Project KEY ได้
3. วาง foundation สำหรับการต่อไปยัง ChatGPT / Gemini ในอนาคต โดยเริ่มจาก **PDB core API first, vendor adapter second**

### User Outcome
ผู้ใช้ควรรู้สึกว่า:
- ฉันไม่ต้อง copy ข้อมูลเองทุกครั้ง
- Claude สามารถใช้ข้อมูลของฉันจาก Project KEY ได้
- ข้อมูลที่ Claude เห็นถูกคัดมาแล้ว ไม่ใช่ทั้งคลัง
- ฉันเริ่มใช้ PDB ของฉัน “ข้ามเครื่องมือ” ได้จริง

---

## 5. Product Strategy for v4

### Strategic Wedge
v4 ไม่ได้เริ่มจาก “connect every AI”
แต่เริ่มจาก:

> **Claude MCP-only, read-only, basic security, single-user-first**

เพราะ practical ที่สุด และสอดคล้องกับสิ่งที่เราคุยกันว่า
- คนทั่วไปยังไม่ควรเป็นคนตั้ง integration เองจากศูนย์
- แต่คนที่มีความรู้เทคนิคระดับหนึ่งสามารถต่อ Claude connector ได้ ถ้าเรามี MCP server URL, token, และคู่มือให้พร้อม

### Why Claude First
Claude เหมาะเป็น wedge แรก เพราะ use case ของผู้ใช้เราตรงกับการอ่าน:
- markdown
- summaries
- context packs
- structured personal context
- knowledge search

และ v4 นี้ต้องการพิสูจน์เรื่อง “external AI access” ไม่ใช่ multi-vendor breadth ตั้งแต่แรก

---

## 6. Scope of MVP v4

## In Scope

### A. Keep v1-v3 foundation
ยังคงใช้ของเดิมทั้งหมด:
- private personal data space
- file upload / extraction
- summaries
- profile
- context packs
- knowledge view
- graph / evidence layer
- AI chat ภายในระบบ

### B. PDB Core API Layer
ต้องมี API กลางของ Project KEY ที่อ่านข้อมูลจากระบบเราได้อย่างเป็นระเบียบ และพร้อมให้ adapter ใช้ต่อ เช่น:
- profile
- context packs
- file summaries
- knowledge search
- scenario exports

### C. Claude MCP Server (Remote MCP)
ต้องมี service ใหม่สำหรับ expose tool ให้ Claude เรียกผ่าน custom connector ได้

### D. Read-only Tool Set
v4 จะเปิดเฉพาะ tool แบบอ่านอย่างเดียวก่อน

### E. Basic Token-based Access
ต้องมี token พื้นฐานสำหรับเรียก MCP tools

### F. MCP Setup UI
ใน Project KEY ต้องมีหน้า/section สำหรับ:
- MCP Server URL
- Generate token
- Copy instructions
- Test connection

### G. Basic Usage Logs
บันทึกขั้นต่ำว่า:
- token ไหนเรียกอะไร
- เมื่อไร
- สำเร็จ/ล้มเหลวหรือไม่

---

## Out of Scope
ยังไม่ทำใน v4:
- OAuth เต็มระบบ
- write actions จาก Claude กลับเข้า Project KEY
- fine-grained field-level permissions
- revoke ระดับละเอียดแบบ enterprise
- ChatGPT connector
- Gemini connector
- multi-user workspace
- public share links เต็มระบบ
- full audit/compliance system

---

## 7. Target User

### Primary User
ผู้ใช้ที่:
- มีข้อมูลอยู่ใน Project KEY แล้ว
- ใช้ Claude อยู่แล้ว
- มีความรู้เทคนิคระดับหนึ่ง
- อยากให้ Claude ใช้ข้อมูลส่วนตัว/ข้อมูลโปรเจกต์ของตัวเองได้โดยไม่ต้อง copy context ทุกครั้ง

### Secondary User
ทีม product / founder / power user ที่อยากทดลองว่า PDB ของตัวเองจะกลายเป็น external AI context layer ได้จริงไหม

---

## 8. Core User Stories

### External AI Use
- ในฐานะผู้ใช้ ฉันต้องการให้ Claude เข้าถึงข้อมูลที่จัดไว้ใน Project KEY ได้ เพื่อไม่ต้องคัดลอกข้อมูลเองทุกครั้ง

### Controlled Access
- ในฐานะผู้ใช้ ฉันต้องการให้ Claude เห็นเฉพาะข้อมูลที่ Project KEY อนุญาต ไม่ใช่ทั้งคลังทั้งหมด

### Context Portability
- ในฐานะผู้ใช้ ฉันต้องการใช้ profile, context packs, และ summaries ที่มีอยู่แล้วใน Project KEY กับ Claude ได้โดยตรง

### Setup Simplicity
- ในฐานะผู้ใช้ ฉันต้องการได้ MCP URL และ token พร้อมคู่มือสั้นๆ เพื่อเชื่อม Claude ได้ง่าย

### Traceability
- ในฐานะผู้ใช้ ฉันต้องการรู้ว่า connector ถูกใช้เมื่อไร และเรียก tool อะไรไปบ้าง

---

## 9. Core UX Flow

### Flow 1: User prepares data
ผู้ใช้มีข้อมูลอยู่ใน Project KEY แล้ว:
- files
- summaries
- profile
- context packs
- knowledge graph

### Flow 2: User opens MCP Setup
ผู้ใช้เปิดหน้า MCP Setup ใน Project KEY

### Flow 3: Generate access token
ระบบสร้าง read-only token สำหรับ connector

### Flow 4: Add connector in Claude
ผู้ใช้ไปที่ Claude > Settings > Connectors > Add custom connector  
แล้วใส่:
- Name
- Remote MCP server URL
- auth/token ตามที่ระบบให้

### Flow 5: Claude connects to Project KEY
Claude เรียก MCP tools ของ Project KEY ผ่าน remote MCP

### Flow 6: User asks Claude
ผู้ใช้ถาม Claude เช่น:
- “ช่วยสรุปโปรเจกต์นี้จาก context pack ของฉัน”
- “ช่วยดึงข้อมูลจาก profile และ context ที่เกี่ยว”

### Flow 7: MCP tools are called
Claude เรียก tool เช่น:
- get_profile
- list_context_packs
- get_context_pack
- search_knowledge
- get_file_summary

### Flow 8: Claude answers
Claude ตอบโดยมีบริบทจาก Project KEY

---

## 10. Functional Requirements

### FR-1 PDB Core API
ระบบต้องมี API กลางที่ดึงข้อมูลหลักจาก Project KEY ได้ในรูปแบบที่เป็นระเบียบ

### FR-2 MCP Adapter Service
ระบบต้องมี remote MCP server ที่ map tool calls ไปยัง PDB Core API ได้

### FR-3 Read-only Access
tool ทั้งหมดใน v4 ต้องเป็นแบบ read-only

### FR-4 Token Authentication
ระบบต้องใช้ token พื้นฐานในการเรียก MCP tools

### FR-5 User-bound Token
token ต้องผูกกับ user เดียว

### FR-6 MCP Setup Screen
ระบบต้องมีหน้า/section สำหรับแสดง MCP URL, generate token, copy setup instructions

### FR-7 Basic Connection Test
ระบบต้องมีวิธีให้ user ทดสอบว่า connector ใช้งานได้

### FR-8 Basic Usage Logs
ระบบต้องบันทึกว่า token ไหนเรียก tool อะไร เมื่อไร และสำเร็จหรือไม่

### FR-9 Tool Exposure Control
ระบบต้องเปิดเฉพาะ MCP tools ที่อนุญาต ไม่ expose API ภายในทั้งหมด

### FR-10 Existing v1-v3 Functions Remain
ระบบต้องรักษาฟีเจอร์ v1-v3 ไว้ครบถ้วนโดยไม่ breaking changes

---

## 11. MCP Tool Set v1

### Tool 1: `get_profile`
#### Purpose
ให้ Claude ดึง profile ของผู้ใช้ไปใช้เป็นบริบท

#### Returns
- identity_summary
- goals
- working_style
- preferred_output_style
- background_context

---

### Tool 2: `list_context_packs`
#### Purpose
ให้ Claude เห็นว่าผู้ใช้มี context packs อะไรบ้าง

#### Returns
- pack_id
- title
- type
- short_summary
- updated_at

---

### Tool 3: `get_context_pack`
#### Purpose
ให้ Claude ดึง context pack ที่ต้องการแบบเต็ม

#### Input
- `pack_id`

#### Returns
- title
- type
- summary_text
- source_file_ids
- source_cluster_ids
- updated_at

---

### Tool 4: `search_knowledge`
#### Purpose
ให้ Claude ค้นในฐานความรู้ของผู้ใช้

#### Input
- `query`
- optional `type_filter`
- optional `limit`

#### Returns
- matched files
- summaries
- packs
- short relevance note

---

### Tool 5: `get_file_summary`
#### Purpose
ให้ Claude ดึง summary ของไฟล์เดียวแบบเร็ว

#### Input
- `file_id`

#### Returns
- filename
- summary
- key_topics
- importance_label
- source_of_truth
- freshness

---

## 12. API Design Direction

## PDB Core API (internal / app-side)
ตัวอย่าง endpoint ภายในที่ MCP adapter ใช้ต่อ:
- `GET /api/profile`
- `GET /api/context-packs`
- `GET /api/context-packs/{id}`
- `GET /api/files/{id}/summary`
- `POST /api/search`
- `POST /api/mcp/tokens`
- `GET /api/mcp/logs`

## MCP Layer
ทำหน้าที่:
- รับคำขอจาก Claude
- validate token
- map tool calls
- เรียก Core API
- คืนผลลัพธ์ในรูปแบบที่ Claude ใช้ได้

### Important Principle
**Project KEY Core API first, MCP adapter second**  
เพื่อให้อนาคตต่อ ChatGPT/Gemini ได้ง่าย ไม่ผูกกับ vendor เดียวตั้งแต่แรก

---

## 13. Security Model (Basic)

v4 ไม่เน้น security หนัก  
แต่ต้องมี minimum viable safety

### Required Basic Controls
1. **Bearer token**
2. **Token per user**
3. **Read-only only**
4. **Endpoint allowlist**
5. **Basic HTTPS deployment**
6. **Basic request logging**

### Explicitly Not in v4
- OAuth full flow
- granular consent per field
- role-based access control
- enterprise audit model
- secret rotation automation

---

## 14. Screens / Views

## Screen 1: MCP Setup
หน้าหลักใหม่ของ v4

### Must-have
- MCP Server URL
- Current connector status
- Generate token button
- Copy token button
- Copy setup instructions
- Revoke current token button
- Test connection button

### UX Goal
ทำให้ user ที่พอมีความรู้เทคนิคสามารถเชื่อม Claude ได้ภายในไม่กี่ขั้น

---

## Screen 2: Token Management
### Must-have
- active token list
- created_at
- last_used_at
- status
- revoke button

---

## Screen 3: MCP Logs
### Must-have
- timestamp
- tool_name
- token_id
- result status
- latency
- optional error message

---

## Screen 4: Existing v1-v3 product
- My Data
- Knowledge View
- Graph
- AI Chat  
ยังคงอยู่เหมือนเดิม

---

## 15. Data Model Additions

### Entity: MCPToken
- id
- user_id
- token_hash
- label
- scope
- is_active
- created_at
- last_used_at
- revoked_at

### Entity: MCPUsageLog
- id
- user_id
- token_id
- tool_name
- request_summary
- status
- latency_ms
- created_at
- error_message

### Entity: ExternalAccessGrant (optional lightweight)
- id
- user_id
- provider_name
- access_type
- scope_json
- created_at
- revoked_at

---

## 16. Technical Direction

### Architecture
แนะนำให้แยกเป็น 2 services

#### Service A: `project-key-app`
- web app หลัก
- backend หลัก
- core API
- token management UI
- existing v1-v3 system

#### Service B: `project-key-mcp`
- remote MCP adapter server
- public HTTPS endpoint
- token validation
- map tools to core API

### Why Separate
- isolate connector concerns
- debug ง่าย
- ไม่ผูก app หลักกับ MCP spec โดยตรง
- รองรับ adapter อื่นในอนาคตได้ง่ายขึ้น

---

## 17. Deployment Direction

### Deployment Goal
v4 ต้อง **publicly reachable** เพื่อให้ Claude custom connector เรียกได้

### Initial Deployment Target
- FastAPI / ASGI based services
- public HTTPS endpoint
- one region
- low complexity setup

### Practical Hosting Direction
- deploy-ready สำหรับ MCP prototype
- persistent data layer ต้องวางแผนให้ดี
- ถ้ายังใช้ SQLite/local files ต้องมี persistent storage strategy

### Important Note
เป้าหมายของ v4 คือ **deployable MCP prototype**  
ยังไม่ใช่ production-grade infra เต็มระบบ

---

## 18. Success Metrics

### Product Metrics
- จำนวน user ที่ generate MCP token สำเร็จ
- จำนวน user ที่เชื่อม Claude connector สำเร็จ
- จำนวน MCP tool calls ต่อวัน
- จำนวน successful MCP requests

### UX Metrics
- เวลาที่ใช้จาก “เริ่ม setup” ถึง “Claude ใช้งานได้”
- จำนวนครั้งที่ user ต้อง export/copy context เองลดลงหรือไม่
- ผู้ใช้รู้สึกว่า Claude ใช้งานข้อมูลจาก Project KEY ได้ลื่นขึ้นหรือไม่

### Outcome Metrics
- จำนวนคำถามที่ Claude ตอบได้โดยเรียกข้อมูลจาก Project KEY
- จำนวน user ที่บอกว่าไม่ต้อง re-explain/re-upload บ่อยเหมือนเดิม
- willingness to continue using connector

---

## 19. Risks

### Risk 1
Claude connector setup ยังซับซ้อนเกินไป  
**Mitigation:** MCP Setup screen + copy instructions + test connection

### Risk 2
Token หลุดหรือถูกใช้ผิด  
**Mitigation:** read-only only, revoke token ได้, expose เฉพาะ tool ที่จำเป็น

### Risk 3
Core API กับ MCP layer ผูกกันแน่นเกิน  
**Mitigation:** แยก adapter layer ชัดเจน

### Risk 4
User คาดหวังว่า connector จะทำได้ทุกอย่าง  
**Mitigation:** สื่อชัดว่า v4 เป็น read-only prototype

### Risk 5
Deployment ใช้ได้แต่ persistent data ไม่เสถียร  
**Mitigation:** วาง data storage strategy ตั้งแต่ต้น

---

## 20. Release Plan

### Phase 0 — Prep
- finalize tool set v1
- define token model
- define MCP/core API boundary

### Phase 1 — Core API Cleanup
- profile API
- packs API
- summary API
- search API
- internal consistency

### Phase 2 — Token & Logs
- generate token
- revoke token
- usage logs
- setup UI

### Phase 3 — MCP Adapter
- implement remote MCP server
- map 5 tools
- validate token
- test locally

### Phase 4 — Public Deploy
- deploy MCP service publicly
- verify HTTPS reachability
- connect with Claude custom connector

### Phase 5 — Real Usage Testing
- run real prompts
- inspect logs
- refine tool output
- improve docs/setup

---

## 21. Final Scope Lock

MVP v4 ล็อกไว้ที่:

- Claude custom connector only
- remote MCP only
- read-only tools only
- basic token auth
- core PDB API layer
- setup UI
- basic usage logs
- public deployable MCP prototype

ทุกอย่างนอกเหนือจากนี้ถือว่า phase ถัดไป

---

## 22. Final Summary

Project KEY MVP v4 คือการต่อยอดจาก Personal Data Space, Context Layer, และ Knowledge Workspace ไปสู่ **PDB Connector Layer** ที่ทำให้ Claude สามารถเข้าถึงข้อมูลที่ถูกจัดไว้ใน Project KEY ได้จริงผ่าน remote MCP โดยยังคงควบคุมขอบเขตการเข้าถึงในระดับพื้นฐาน และพิสูจน์ให้เห็นว่า Project KEY สามารถทำหน้าที่เป็น **external AI context layer** ได้จริง ซึ่งเป็นก้าวสำคัญในการไปสู่ภาพใหญ่ของ Personal Data Bank ที่ “อัปโหลดครั้งเดียว ใช้ได้ทุกที่ และเชื่อมกับ AI ได้”
