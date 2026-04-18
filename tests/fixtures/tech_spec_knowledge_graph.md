# Technical Specification: Knowledge Graph Engine

## 1. Architecture Overview
ระบบ Knowledge Graph Engine เป็นส่วนหนึ่งของโปรเจกต์ NOVA
ทำหน้าที่สร้างและจัดการ knowledge graph จากข้อมูลผู้ใช้

## 2. Data Model

### 2.1 Graph Nodes
- File Node: แทนไฟล์ที่อัปโหลด
- Entity Node: แทน entities ที่ extract ได้ (คน, โปรเจกต์, องค์กร)
- Tag Node: แทน keywords/topics
- Pack Node: แทน context packs

### 2.2 Graph Edges
- contains: ไฟล์อยู่ใน collection
- mentions: ไฟล์กล่าวถึง entity
- has_tag: ไฟล์มี tag
- semantically_related: ไฟล์เกี่ยวข้องกัน
- derived_from: context pack สร้างจากไฟล์

## 3. Algorithms
- Entity Extraction: ใช้ LLM (GPT-4/Claude)
- Semantic Similarity: TF-IDF + Cosine Similarity
- Graph Layout: Force-directed (D3.js)
- Link Suggestion: Co-occurrence + Shared Tags

## 4. API Endpoints
- POST /api/graph/build - สร้างกราฟ
- GET /api/graph/global - ดูกราฟทั้งหมด
- GET /api/graph/neighborhood/{id} - ดูกราฟรอบ node

## 5. Performance Requirements
- Graph build: < 30 seconds สำหรับ 100 files
- Graph render: < 2 seconds สำหรับ 500 nodes
- Node detail: < 500ms response time

## 6. Dependencies
- D3.js v7 สำหรับ visualization
- SQLite สำหรับ persistence
- FastAPI สำหรับ API layer
