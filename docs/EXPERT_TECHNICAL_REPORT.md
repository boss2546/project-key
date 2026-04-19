# 📘 Project KEY — Comprehensive Technical & Architectural Report (v4.3)
> **เอกสารฉบับนี้จัดทำขึ้นสำหรับผู้เชี่ยวชาญ (Technical Reviewers / Architects)** เพื่อทำความเข้าใจภาพรวมทั้งหมด กลไกการทำงานเชิงลึก (Core Logic) และสถาปัตยกรรมของ Project KEY — Personal Data Bank

---

## 1. Executive Summary & Vision
**Project KEY** คือ Personal Knowledge Workspace และ Data Bank อัจฉริยะ ที่ออกแบบมาເພື່ອแก้ปัญหา "ข้อมูลกระจัดกระจายและ AI ไม่เข้าใจบริบทส่วนตัว" 
ระบบแปลงไฟล์ดิบ (PDF, TXT, MD, DOCX) ผ่าน AI Pipeline ให้กลายเป็น **Knowledge Graph (ความเชื่อมโยง)** และ **Vectorized Data (การค้นหาความหมาย)** จากนั้นใช้ RAG (Retrieval-Augmented Generation) และ **MCP (Model Context Protocol)** เพื่อให้ AI ภายนอก (เช่น Claude Desktop) ดึงข้อมูลส่วนตัวไปใช้ตอบคำถามได้อย่างมีหลักฐานอ้างอิงชัดเจน

---

## 2. โครงสร้างสถาปัตยกรรม (System Architecture)
ระบบถูกออกแบบเป็น **Monolithic Backend + Vanilla Frontend** เน้นความเร็ว, น้ำหนักเบา, และเหมาะแก่การนำไป Deploy ทันที

### 💡 Tech Stack
- **Frontend:** Vanilla JS, HTML, CSS (Custom Design System, Glassmorphism, Responsive)
- **Data Visualization:** D3.js v7 (แสดงผล Knowledge Graph ทั้ง Global และ Local)
- **Backend:** Python + FastAPI + Uvicorn (Asynchronous)
- **Database:** SQLite (ผ่าน SQLAlchemy + `aiosqlite`) — เน้นเก็บข้อมูลแบบ Local / Single-file database
- **Search Engine:** Custom TF-IDF Index (In-memory) + Keyword Mapping (Hybrid Search)
- **AI/LLM Provider:** OpenRouter API (ใช้ Google Gemini 2.5 Flash เป็นหลักในการวิเคราะห์และจัดโครงสร้างข้อมูล)
- **Deployment:** Docker + Fly.io (Single regional instance + Persistent Volume)

---

## 3. Core Logic & Data Pipeline (กลไกการประมวลผล)

การไหลของข้อมูลจากไฟล์ดิบไปสู่ฐานความรู้ AI มีกระบวนการดังนี้:

### Step 1: Ingestion & Extraction (`extraction.py`)
เมื่อผู้ใช้รันคำสั่ง "Upload"
- **Logic:** ระบบรับไฟล์ (PDF, DOCX, TXT, MD) เข้ามาและแยกร่างข้อความ (Text Extraction) โดยใช้ไลบรารีพื้นฐานอย่าง `PyPDF2` และ `python-docx`
- **Output:** ได้ Plaintext ที่สะอาด เก็บลงตาราง `File` พร้อมระบุ Status = `uploaded`

### Step 2: Organization Pipeline (`organizer.py`)
เมื่อผู้ใช้กด "Organize with AI"
- **Summarization:** ส่ง Text ไปให้ LLM สรุปออกมาเป็น 5 องค์ประกอบ (Summary, Key Topics, Key Facts, Why Important, Suggested Usage)
- **Clustering:** LLM ประเมินเนื้อหาไฟล์และจับเข้ากลุ่ม (Collections / Clusters) อัตโนมัติ หากไม่มีกลุ่มที่ตรงกัน จะสร้างกลุ่มใหม่
- **TF-IDF Indexing:** ข้อความที่แยกมา (Extracted Text) จะถูกแบ่งเป็น Chunks และคำนวณน้ำหนัก (TF-IDF) เก็บไว้ใน RAM (`vector_search.py`) เพื่อทำ Vector Search แบบไม่ต้องพึ่งพา 3rd-party Embeddings API

### Step 3: Graph Building (`graph_builder.py`)
จัดระเบียบข้อมูลเป็น Knowledge Graph อัตโนมัติ (Triple extraction: Subject-Predicate-Object)
- **Node Classification:** LLM ตรวจจับ Entities สำคัญ (เช่น บุคคล, โปรเจกต์, สถานที่, แนวคิด) และกำหนดประเภท (Type: `source_file`, `cluster`, `entity`, `context_pack`, `tag`)
- **Relationship Extraction:** สร้าง `GraphEdge` เชื่อมโยง Node แจกแจง Edge Type เช่น `belongs_to`, `mentions`, `related_to`, `requires`
- **Output:** ฐานข้อมูลกราฟที่นำไปวาดหน้าเว็บด้วย D3.js แบบ Force-directed layout ได้ทันที

### Step 4: Metadata Enrichment (`metadata.py`)
- สแกนเนื้อหาหา Tags ที่เหมาะสม อัพเดตระดับความอ่อนไหวแบบ Automation (`sensitivity`: normal/sensitive) ประเมินความสดใหม่ (`freshness`) และเช็คสถานะอ้างอิงหลัก (`source_of_truth`)

---

## 4. MCP Connector & Claude Integration (การเชื่อมต่อภายนอก)

หัวใจสำคัญใน v4 คือการใช้มาตรฐาน **Model Context Protocol (MCP)** เพื่อเชื่อมต่อกับ Agent ภายนอก (เช่น Claude 3.5 Sonnet desktop app) 

### 📡 สถาปัตยกรรมการเชื่อมต่อ (Streamable HTTP)
- สร้าง SSE (Server-Sent Events) Transport รองรับการส่งข้อความผ่าน `/api/mcp/message` JSON-RPC 2.0
- **Security:** ใช้ Bearer Token + URL Secret (`/mcp/{secret_key}`) เพื่อ Authentication ป้องกันบุคคลภายนอกเรียกใช้งาน

### 🛠️ เครื่องมือ 21 Tools (ออกแบบสำหรับ AI Agent)
ระบบส่ง Tools ทั้ง 21 รายการ (พร้อม Schema แบบ JSON) ให้ AI ใช้งาน แบ่งเป็น 4 หมวดตรรกะคือ:
1. **📖 อ่านและค้นหา (Read & Search - 10 tools):** `get_profile`, `list_files`, `get_file_content` (จำกัด 5k chars เพื่อป้องกัน Context Limit), `get_file_summary`, `search_knowledge` (Hybrid + DB Fallback), `explore_graph`, ฯลฯ
2. **✏️ สร้างและแก้ไข (Create & Edit - 5 tools):** `add_note`, `update_file_tags`, `create_context_pack`, `upload_text`, `update_profile`
3. **🗑️ ลบข้อมูล (Delete - 2 tools):** `delete_file`, `delete_pack`
4. **⚙️ ประมวลผล AI (AI Pipeline - 4 tools):** `run_organize`, `build_graph`, `enrich_metadata`, `admin_login`

### 🔐 Permission Logic & Admin Bypass
- ผู้ใช้สามารถเปิด-ปิด (Toggle) การเข้าถึง Tool ย่อยๆ ได้ ผ่านหน้าจอ UI 
- **Logic Security Bypass:** หากเกิด Use Case ฉุกเฉิน AI สามารถเรียก `admin_login(admin_key="1234")` ก่อน เพื่อปลดล็อก (Authenticate Context Session) ระบบจะอนุญาตให้ข้ามเงื่อนไข Toggle สำหรับ Session นั้นๆ

---

## 5. RAG Retrieval Logic (การดึงข้อมูลเพื่อโต้ตอบ)

หน้าเว็บหลักมีระบบ AI Chat เช่นกัน โดยเมื่อผู้ใช้ถามคำถาม มีการฉีด (Context Injection) ข้อมูลถึง 7 ระดับ แบบไล่ลำดับความสำคัญก่อนส่งไปหา LLM ได้แก่:

1. **User Profile:** (ตัวตน สไตล์ เป้าหมาย) บังคับสไตล์การตอบ
2. **Active Context Packs:** โหลดแพ็กข้อมูลสรุป (หากเปิดโหมด Active)
3. **Conversational History:** โหลดอดีตคำถาม/ตอบ ของ session นั้น
4. **Database Exact Match:** เคาะ DB ด้วยชื่อไฟล์ หรือ Collection ตรงๆ
5. **Hybrid Search:** โยนคำถามหาไฟล์ที่ตรงกับ TF-IDF Text Distance มากที่สุด (เอา Top 3)
6. **Graph Relationships:** เอาไฟล์ Top 3 ไปหา Node เชื่อมรอบๆ (+1 hop) เพื่อดึง "บริบทเสริม" เช่น หากเจอบทความ A จะดึงรายชื่อแท็ก และไฟล์ B ที่ลิงก์กันมาด้วย
7. **Prompt Assembly:** ประกอบทั้งหมดเข้าสู่ `<CONTEXT_LAYER>` ให้ LLM อ่่านพร้อมกัน

เมื่อ AI ตอบ หน้าตางแชตจะโยง Reference File ขึ้นมาให้อัตโนมัติ พร้อม UI ดู Evidence Graph แหล่งที่มาของข้อมูล (mini Graph) ชัดเจน

---

## 6. สรุป Database Schema หลัก (18 Tables)
- **User / UserProfile:** จุดเริ่มระบบ (ปัจจุบันเป็น `DEFAULT_USER_ID`) รองรับ Multi-user อนาคต
- **File / FileSummary / FileInsight:** แหล่งเก็บเอกสารและผลลัพธ์จากการสกัดข้อมูลของ AI
- **Cluster / FileClusterMap:** การจัดหมวดหมู่อัตโนมัติ (Many-to-Many)
- **GraphNode / GraphEdge:** สถาปัตยกรรมกราฟสำหรับระบุ Entity ความสัมพันธ์ แผนผังของ Second Brain
- **ContextPack / ContextPackContent:** โมดูลจำเพาะรวบรวมไฟล์/หัวข้อความรู้ (Pack/Bundle) สำหรับเรียกใช้งานเฉพาะงาน
- **MCPToken / MCPUsageLog:** จัดการสิทธิ์การเชื่อมต่อกับ 3rd-party
- **NoteObject / SuggestedRelation:** รองรับฟีเจอร์โน้ตเชื่อมโยงและคำแนะนำพฤติกรรมข้อมูล

---

## 7. คู่มือการใช้งานและทดสอบ (Testing & Usage)

1. **Deployment Testing:**
   - โฮสต์ไว้ที่: `https://project-key.fly.dev/`
   - แหล่งข้อมูลจะถูกเซฟด้วย Persistent Volumes ทำให้ข้อมูลไม่หายเมื่อเครื่องรีบสตาร์ต
   - **(v4.3 Fix):** เซิร์ฟเวอร์ที่ Restart จะโหลด Search Index เข้า RAM ใหม่ อัตโนมัติ (Auto-rebuild) จาก Backup DB ทำให้ AI สามารถ Search ข้อมูลได้ทันที

2. **UI Workflow Testing:**
   - แพลตฟอร์มมีโครงสร้าง 2 ฝั่ง: ฝั่งบริหารจัดข้อมูล และฝั่งแชต/กราฟวิเคราะห์ 
   - รองรับ **อัปโหลดไฟล์ -> Organize With AI -> Explore Graph / Chat**
   - UI รองรับการเปลี่ยนภาษา (Localization TH/EN) ได้ด้วยการคลิกเดียว อัปเดต DOM Real-time แบบไม่รีเฟรช และเปลี่ยนทั้งระบบอย่างสมบูรณ์ครอบคลุม 170 Keys

3. **External AI Testing (Claude MCP Testing):**
   - อัพเดตลิงก์ผ่านไฟล์ `claude_desktop_config.json` จากแพลตฟอร์ม (พร้อมใส่ Secret Key ที่หน้า Dashboard ออกให้)
   - รีสตาร์ท Claude แล้ว ทดสอบ Prompt: *"จงสแกนฐานความรู้ของฉันผ่าน Project KEY และสรุปข้อมูลโปรเจกต์ทั้งหมดที่มี"* 
   - ระบบพร้อมส่งข้อมูลเชิงลึกในพริบตา และอัปทูเดตที่สุด!

---

> **ข้อแนะนำเชิงเทคนิคสำหรับ Next Steps (สำหรับ Expert Review) :**
> - หากสเกลข้อมูลมีขนาดใหญ่ในระดับ Production องค์กร (> 50,000 ชิ้น) ควรพิจารณาย้าย In-Memory TF-IDF เป็น **ChromaDB** หรือ **pgvector** ตามแบบสถาปัตยกรรม Microservices
> - ควรรวม Authentication ด้วย JWT สำหรับ Multi-User Workspace เต็มรูปแบบ (Scale out)
> - เปลี่ยน Hardcoded Admin password ออกให้รับจาก Environment Variable ของ OS เพื่่อความปลอดภัยสูงสุดบน Production

*สร้างและเรียบเรียงโดย Project KEY Architect Team / Antigravity AI* 
