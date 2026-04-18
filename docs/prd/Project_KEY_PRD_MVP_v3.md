# PRD — Project KEY MVP v3

## 1. Overview

### Product Name
**Project KEY — MVP v3**

### Product Definition
ระบบพื้นที่ข้อมูลส่วนตัวแบบ **markdown-first, metadata-first, graph-addressable knowledge workspace** ที่ช่วยให้ผู้ใช้เก็บข้อมูลสำคัญ จัดระบบข้อมูล สร้างบริบทพร้อมใช้ และมองเห็นความเชื่อมโยงของข้อมูลเพื่อใช้กับ AI ได้ดีขึ้นอย่างมีหลักฐานอ้างอิง ไม่ใช่แค่ chat กับไฟล์อีกต่อไป

### One-line Product Statement
**Store → Organize → Summarize → Connect → Explore → Reuse with AI**

### Strategic Position
v3 ไม่ใช่ Second Brain เต็มระบบ และยังไม่ใช่ graph app เพื่อความสวยงาม แต่เป็นการยกระดับจาก:
- v1: file-ready for AI
- v2: context-ready for AI

ไปสู่:
- **v3: relationship-aware knowledge workspace for AI**

โดยยังยึดหลัก **Data Bank first, Second Brain later** และให้ graph เป็น **projection / exploration layer** ไม่ใช่ source of truth หลักของระบบ

---

## 2. Vision Alignment

Vision ของ Project KEY ยังคงเดิม:

> ข้อมูลและความทรงจำสำคัญของทุกคนควรถูกเก็บไว้อย่างดี เป็นส่วนตัว และเป็นระบบ และถูกนำไปใช้ได้อย่างไร้รอยต่อ

วิสัยทัศน์นี้ตีความเป็น 4 เสาหลัก:
- **Preservation**
- **Privacy**
- **Structure**
- **Seamless Use**

MVP v3 ถูกออกแบบมาเพื่อดันเสา **Structure** และ **Seamless Use** ให้แข็งขึ้นอย่างมาก ผ่าน:
- metadata ที่ดีขึ้น
- relationship graph
- graph-aware retrieval
- graph-aware AI chat

ในขณะที่ยังคงเคารพแกนของ Personal Data Bank ว่าระบบต้องเป็นพื้นที่ข้อมูลส่วนตัวที่เจ้าของควบคุมได้ และใช้ข้อมูลกับ AI ได้ง่ายที่สุด

---

## 3. Problem Statement

### Core Problem
ผู้ใช้มีข้อมูลอยู่แล้ว แต่ข้อมูล:
- กระจัดกระจาย
- ไม่เป็นระบบ
- ไม่พร้อมใช้กับ AI
- ไม่เห็นความเชื่อมโยงระหว่างข้อมูล
- และเมื่อใช้ AI ก็ยังต้องเริ่มใหม่ อธิบายใหม่ หรือแนบไฟล์ใหม่ซ้ำๆ

### Deeper Interpretation
ปัญหาที่แท้จริงไม่ใช่แค่ AI ไม่ฉลาดพอ แต่คือ:
- **Data Friction**
- **Context Loss**
- **Lack of Relationship Visibility**
- **Personalization Gap**

### Why v3 Exists
v1 แก้เรื่องไฟล์พร้อมใช้  
v2 แก้เรื่องบริบทพร้อมใช้  
v3 ต้องแก้เรื่อง:

> **ข้อมูลถูกมองเห็นเป็นระบบความรู้ที่มีความเชื่อมโยง และ AI ใช้ความเชื่อมโยงนั้นได้จริง**

---

## 4. Goals of MVP v3

### Primary Goal
ยกระดับระบบจาก “Personal Data Space + Context Layer” ไปสู่ “Knowledge Workspace” ที่:

1. จัดข้อมูลด้วย metadata ได้ดีขึ้น  
2. สร้าง typed relationships ระหว่างข้อมูลได้  
3. เปิดให้ผู้ใช้สำรวจข้อมูลผ่าน graph views ได้  
4. ทำให้ AI ใช้ evidence graph ในการตอบได้

### User Outcome
ผู้ใช้ควรรู้สึกว่า:
- ข้อมูลของฉันไม่ได้แค่ถูกเก็บ แต่ถูกจัดเป็นระบบความรู้
- ฉันเห็นได้ว่าอะไรเกี่ยวกับอะไร
- ฉันหาเรื่องที่เกี่ยวได้เร็วขึ้น
- AI ไม่ได้ตอบจากไฟล์ลอยๆ แต่ตอบจากโครงสร้างความรู้ของฉัน
- ฉันเริ่ม “เข้าใจข้อมูลตัวเอง” มากขึ้น ไม่ใช่แค่ “หาไฟล์เจอ”

### Strategic Goal
เปลี่ยน Project KEY จาก AI-ready context system ไปเป็น **knowledge operating layer** ที่ปูทางไปสู่ Personal Data Infrastructure ในระยะยาว

---

## 5. Scope of MVP v3

## In Scope

### A. Keep v1 + v2 foundation
ยังคงใช้ของเดิมทั้งหมด:
- private personal data space
- multi-file upload
- text extraction
- collections / grouping
- importance scoring
- markdown summaries
- user profile
- context packs
- hybrid retrieval
- automatic context injection
- AI chat transparency

### B. Metadata Expansion Layer
ยกระดับ metadata ของ objects ทุกประเภท เช่น:
- type
- tags
- aliases
- importance
- sensitivity
- freshness
- provenance
- source-of-truth
- verification status
- use-case tags
- version

### C. Relationship Graph Layer
เพิ่ม graph layer แบบ typed heterogeneous graph ที่เชื่อม:
- files
- notes
- summaries
- context packs
- entities
- tags
- people
- projects
- groups

โดยความสัมพันธ์ต้องมีประเภทและมีหลักฐานรองรับ ไม่ใช่เส้นเชื่อมแบบแบนๆ อย่างเดียว

### D. Graph Views
ต้องมีอย่างน้อย:
- **Global Graph**
- **Local Graph**

และรองรับแนวคิด lenses อย่างน้อย:
- Theme
- Bridge
- Foundation
- Local

เพื่อลดปัญหา hairball และทำให้ graph มีประโยชน์จริงในการสำรวจความรู้

### E. Link Discovery Layer
เพิ่ม workflow แบบ Obsidian-like:
- Backlinks
- Outgoing Links
- Suggested Relations
- Unlinked Mention Candidates

เพื่อช่วยให้ผู้ใช้เห็นทั้งความเชื่อมโยงที่มีแล้ว และความเชื่อมโยงที่ควรมีแต่ยังไม่ได้สร้าง

### F. Graph-aware AI Chat
AI Chat ต้องตอบโดยใช้:
- profile
- context packs
- relevant files
- selected nodes
- typed edges
- local evidence graph

พร้อมแสดงหลักฐานและเส้นทางความสัมพันธ์ที่ถูกใช้ในการตอบ

### G. Canvas-ready Architecture
ยังไม่ต้องทำ canvas เต็มระบบ แต่ต้องออกแบบ data model และ object model ให้พร้อมต่อยอดไปสู่:
- note cards
- file cards
- group cards
- labeled edges
- export/import แนว JSON-canvas-compatible ได้ในอนาคต

---

## Out of Scope
ยังไม่ทำใน v3:
- Daily brief
- Retro / monthly reflection
- Per-session learning loop เต็มรูป
- Multi-agent swarm
- Autonomous research mode
- External tool integrations จำนวนมาก
- Enterprise permission flow เต็มระบบ
- Full multimodal retrieval ทุก modality
- Mobile app
- Collaboration platform

---

## 6. Target User

### Primary User
Heavy AI users และคนที่มีข้อมูลจำนวนมาก เช่น:
- นักศึกษาที่ใช้ AI ช่วยเรียน
- คนทำงานความรู้
- ฟรีแลนซ์
- นักวิจัย
- ครีเอเตอร์
- คนที่มีโน้ต/ไฟล์/เอกสารจำนวนมากและอยากจัดระบบข้อมูลของตัวเอง

### Why This User
กลุ่มนี้มี pain ชัดทั้งสองแบบ:
1. ข้อมูลกระจัดกระจาย หาไม่เจอ ใช้ยาก
2. AI ยังไม่เข้าใจเขาและบริบทอย่างต่อเนื่อง

---

## 7. Core User Stories

### Metadata
- ในฐานะผู้ใช้ ฉันต้องการให้ข้อมูลแต่ละชิ้นมี metadata ชัดเจน เพื่อให้ค้นหา จัดลำดับ และเรียกใช้ได้แม่นขึ้น

### Relationship Discovery
- ในฐานะผู้ใช้ ฉันต้องการเห็นว่าข้อมูลต่างๆ เชื่อมโยงกันยังไง เพื่อให้เข้าใจโครงสร้างความรู้ของตัวเอง

### Graph Exploration
- ในฐานะผู้ใช้ ฉันต้องการมุมมอง global และ local graph เพื่อสำรวจทั้งภาพใหญ่และบริบทเฉพาะจุด

### Suggested Linking
- ในฐานะผู้ใช้ ฉันต้องการให้ระบบแนะนำความเชื่อมโยงที่ยังไม่ถูกสร้าง เพื่อให้ knowledge graph ของฉันสมบูรณ์ขึ้น

### Graph-aware AI
- ในฐานะผู้ใช้ ฉันต้องการให้ AI ใช้ความสัมพันธ์ระหว่างข้อมูล ไม่ใช่แค่ chunk หรือไฟล์แยกๆ เพื่อให้คำตอบ grounded และฉลาดขึ้น

### Evidence Transparency
- ในฐานะผู้ใช้ ฉันต้องการเห็นว่า AI ใช้ node, edge, file, และ context อะไรบ้าง เพื่อให้เชื่อถือคำตอบได้

---

## 8. Core UX Flow

### Flow 1: Upload and Organize
ผู้ใช้อัปโหลดไฟล์  
ระบบ v1/v2 ทำงาน:
- store raw files
- extract text
- organize
- score importance
- generate summaries
- generate profile/context packs

### Flow 2: Enrich Metadata
ระบบเพิ่ม metadata และ classification ให้ objects

### Flow 3: Build Relationships
ระบบสร้าง graph relations จาก:
- explicit links
- metadata matches
- mentions
- aliases
- derived_from
- semantic relatedness
- used_together patterns

### Flow 4: Explore Knowledge
ผู้ใช้เปิด:
- Knowledge View
- Global Graph
- Local Graph

เพื่อสำรวจความสัมพันธ์ของข้อมูล

### Flow 5: Ask AI
ผู้ใช้ถามคำถามใน AI Chat

### Flow 6: Graph-aware Retrieval
ระบบเลือก:
- profile
- context packs
- relevant files
- relevant nodes
- relevant typed edges
- local evidence graph

### Flow 7: Answer with Evidence
AI ตอบพร้อมแสดง:
- sources
- relationships used
- why nodes were selected
- local graph of evidence

---

## 9. Screens / Views

## Screen 1: My Data
ยังเป็นพื้นที่ข้อมูลส่วนตัวเหมือนเดิม

### New in v3
- metadata inspector
- source-of-truth signals
- freshness indicators
- sensitivity badges

---

## Screen 2: Knowledge View
แทน Collections เดิมในเชิง product language

### Must-have
- collections
- notes
- summaries
- context packs
- table/list/cards base view
- metadata filters
- relation previews

---

## Screen 3: Global Graph
มุมมองกราฟทั้ง vault แบบ search-first

### Must-have
- graph canvas
- filters
- groups
- search
- detail panel
- saved lenses
- node/edge type filters

---

## Screen 4: Local Graph
มุมมองกราฟรอบ item ปัจจุบัน

### Must-have
- depth slider
- inbound/outbound toggles
- relation type filters
- local evidence neighborhood
- open in note / open in AI / open in graph

---

## Screen 5: AI Chat
หน้าแชทแบบ graph-aware

### Must-have
- profile indicator
- injected context panel
- files used
- context packs used
- nodes used
- edges used
- reasoning panel
- mini evidence graph

---

## Screen 6: Canvas View (Beta / limited)
ยังไม่ใช่ canvas เต็มระบบ แต่เริ่มมี view แบบ intentional workspace

### Must-have
- note cards
- file cards
- grouping area
- labeled connection preview
- convert from local graph

---

## 10. Functional Requirements

### FR-1 Metadata Expansion
ระบบต้องเก็บ metadata เพิ่มสำหรับ objects หลักทุกประเภท

### FR-2 Source-of-Truth Marking
ระบบต้องระบุได้ว่าไฟล์/โน้ต/pack ใดเป็น source-of-truth

### FR-3 Freshness Tracking
ระบบต้องมี freshness / staleness indicators

### FR-4 Typed Relations
ระบบต้องสร้างและเก็บความสัมพันธ์แบบมีประเภทระหว่าง objects

### FR-5 Global Graph
ระบบต้องมีมุมมอง global graph สำหรับสำรวจทั้งฐานข้อมูล

### FR-6 Local Graph
ระบบต้องมี local graph สำหรับ item ที่ active อยู่

### FR-7 Link Discovery
ระบบต้องแสดง backlinks, outgoing links และ suggested relations

### FR-8 Detail Panel
เมื่อเลือก node ต้องแสดง summary, metadata, related items, relation evidence, และ actions

### FR-9 Graph-aware Retrieval
AI retrieval ต้องคำนึงถึง nodes, edges, metadata, packs และ files ร่วมกัน

### FR-10 Evidence Graph in Chat
AI chat ต้องแสดง evidence graph หรืออย่างน้อย evidence relationships ที่ใช้ตอบ

### FR-11 Lenses / Saved Views
ระบบต้องรองรับ graph lenses อย่างน้อย theme / bridge / foundation / local

### FR-12 Existing v1-v2 Functions Remain
ระบบต้องรักษา file upload, summaries, profile, packs, hybrid retrieval และ source transparency จาก v1-v2 ทั้งหมด

---

## 11. Data Model Additions

ของเดิมจาก v1-v2 ยังอยู่ครบ และ v3 เพิ่มดังนี้

## Entity: NoteObject
- id
- user_id
- type
- title
- md_path
- summary
- aliases
- metadata_json
- created_at
- updated_at

## Entity: GraphNode
- id
- user_id
- object_type
- object_id
- label
- node_family
- importance_score
- pinned
- freshness_score

## Entity: GraphEdge
- id
- user_id
- source_node_id
- target_node_id
- edge_type
- weight
- confidence
- provenance
- evidence_text
- created_at
- last_verified_at

## Entity: SuggestedRelation
- id
- user_id
- source_node_id
- target_node_id
- relation_type
- suggestion_reason
- confidence
- status

## Entity: GraphLens
- id
- user_id
- name
- type
- filter_json
- layout_json
- created_at

## Entity: CanvasObject (future-compatible)
- id
- user_id
- title
- json_payload
- created_at
- updated_at

---

## 12. Graph Model

### Node Families
อย่างน้อยต้องมี:
- note
- source_file
- page_or_block
- entity
- tag
- project
- person
- context_pack
- canvas
- group

### Edge Families
อย่างน้อยต้องมี:
- explicit_link
- has_tag
- mentions
- alias_match
- backlink
- unlinked_mention_candidate
- derived_from
- contains
- same_entity
- semantically_related
- used_together_in_answer
- pinned_by_user

### Important Principle
ทุก relation ต้องพยายามมี:
- type
- evidence
- confidence
- provenance

---

## 13. AI Logic in v3

### Current v2 logic
v2 ทำ:
- profile
- context packs
- hybrid retrieval
- auto context injection

### New v3 logic
v3 ต้องทำแบบนี้:

1. Parse user query  
2. Retrieve relevant profile + context packs  
3. Retrieve relevant files + summaries  
4. Retrieve relevant nodes and edges  
5. Expand through graph neighborhood  
6. Select best evidence set  
7. Assemble graph-aware context block  
8. Generate answer  
9. Return answer + evidence graph summary

### Context Priority
1. User profile  
2. Context packs  
3. Source-of-truth notes/files  
4. Relevant nodes  
5. Typed edges  
6. Excerpts / raw evidence

---

## 14. Technical Direction

### Foundation
ยังใช้ระบบ v1-v2 ต่อเป็นฐาน:
- markdown-first summaries
- metadata records
- profile/context pack system
- hybrid search
- AI chat

### New in v3
- graph index
- node/edge generation
- graph renderer
- detail panel
- graph-aware retrieval layer
- relation suggestion engine

### Important Technical Principle
**Graph เป็น projection layer ไม่ใช่ source of truth**  
source of truth ยังคงเป็น markdown notes, metadata, files, packs, และ structured objects

---

## 15. Success Metrics

### Product Metrics
- จำนวน objects ที่มี metadata สมบูรณ์ขึ้น
- จำนวน typed relations ที่สร้างได้
- จำนวน suggested relations ที่ user ยอมรับ
- จำนวน graph views ที่ถูกใช้งาน

### UX Metrics
- ผู้ใช้หาเรื่องที่เกี่ยวได้เร็วขึ้นหรือไม่
- ผู้ใช้รู้สึกว่าเข้าใจโครงสร้างข้อมูลตัวเองมากขึ้นหรือไม่
- ผู้ใช้รู้สึกว่า AI grounded ขึ้นหรือไม่
- ผู้ใช้ต้องหาไฟล์เองน้อยลงหรือไม่

### Outcome Metrics
- จำนวนเคสที่ผู้ใช้บอกว่า “เห็นความเชื่อมโยงที่ไม่เคยเห็นมาก่อน”
- จำนวนเคสที่ผู้ใช้บอกว่า “AI ตอบดีขึ้นเพราะเข้าใจความสัมพันธ์ของข้อมูล”
- willingness to continue / willingness to pay

---

## 16. Risks

### Risk 1
Graph ใหญ่เกินไปจนกลายเป็น hairball  
**Mitigation:** ใช้ local graph, filters, lenses, search-first graph

### Risk 2
Suggested relations มั่ว  
**Mitigation:** ต้องมี evidence + confidence + user confirm flow

### Risk 3
Graph สวยแต่ไม่ช่วย product จริง  
**Mitigation:** ให้ graph ผูกกับ AI retrieval และ detail panel เสมอ

### Risk 4
Scope บวมจาก multimodal/Canvas เร็วเกินไป  
**Mitigation:** เริ่มจาก graph foundation ก่อน แล้วค่อย multimodal/canvas layer

### Risk 5
หลุดจาก Data Bank ไปเป็น Obsidian clone  
**Mitigation:** ยึด source-of-truth, metadata, and AI-use-first narrative เสมอ

---

## 17. Release Plan

### Wave 1 — Knowledge Graph Foundation
- metadata expansion
- node/edge model
- backlinks / outgoing / suggested relations
- global graph
- local graph
- detail panel

### Wave 2 — Graph-aware AI
- graph-aware retrieval
- evidence graph in chat
- bridge/foundation/theme lenses
- relation-aware answer transparency

### Wave 3 — Multimodal & Canvas-ready Layer
- Docling block/page integration
- figure/table/page nodes
- canvas-compatible object model
- convert local graph to canvas

---

## 18. Final Scope Lock

MVP v3 ล็อกไว้ที่:

- metadata expansion
- relationship graph
- global graph
- local graph
- link discovery
- graph-aware retrieval
- graph-aware AI chat
- canvas-ready architecture

ทุกอย่างนอกเหนือจากนี้ถือเป็น later-stage layer

---

## 19. Final Summary

Project KEY MVP v3 คือการต่อยอดจาก Personal Data Space และ AI-ready Context Layer ไปสู่ **Knowledge Workspace** ที่ผู้ใช้ไม่เพียงเก็บและใช้ข้อมูลกับ AI ได้ แต่ยังมองเห็นความเชื่อมโยงของข้อมูล สำรวจระบบความรู้ของตัวเอง และให้ AI ใช้ความเชื่อมโยงนั้นอย่างมีหลักฐานอ้างอิงในการตอบได้จริง โดยยังคงยึด Personal Data Bank เป็นแกน และใช้ graph เป็น lens สำหรับสำรวจและ reasoning ไม่ใช่ฐานข้อมูลหลักของระบบ
