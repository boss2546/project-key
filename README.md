# 🔑 Project KEY — Personal Data Bank

> พื้นที่ข้อมูลส่วนตัวที่ใช้ AI จัดระเบียบ วิเคราะห์ และเชื่อมโยงข้อมูลของคุณ  
> **v5.3** — Multi-Platform MCP + Bug Fixes + Dual AI (Gemini 3.1 Pro/Flash)

[![Production](https://img.shields.io/badge/Production-project--key.fly.dev-blue)](https://project-key.fly.dev/)
[![Version](https://img.shields.io/badge/version-5.3-green)]()
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-23-purple)]()

---

## 📖 สารบัญ

- [เริ่มต้นใช้งาน](#-เริ่มต้นใช้งาน)
- [คู่มือการใช้งาน](#-คู่มือการใช้งาน)
- [ฟีเจอร์ทั้งหมด](#-ฟีเจอร์ทั้งหมด)
- [เชื่อมต่อ MCP](#-เชื่อมต่อ-mcp)
- [โครงสร้างโปรเจกต์](#-โครงสร้างโปรเจกต์)
- [เทคโนโลยี](#-เทคโนโลยี)
- [Deploy ขึ้น Production](#-deploy-ขึ้น-production)
- [ประวัติเวอร์ชัน](#-ประวัติเวอร์ชัน)

---

## 🚀 เริ่มต้นใช้งาน

### ติดตั้งบนเครื่อง (Local)

```bash
# 1. ติดตั้ง dependencies
pip install -r requirements.txt

# 2. ตั้งค่า API key (ใช้ OpenRouter)
echo OPENROUTER_API_KEY=your_api_key_here > .env

# 3. รันเซิร์ฟเวอร์
python -m uvicorn backend.main:app --port 8000
```

เปิดเบราว์เซอร์ไปที่ [http://localhost:8000](http://localhost:8000)

### สมัคร API Key

1. ไปที่ [openrouter.ai](https://openrouter.ai/) → สมัครสมาชิก
2. ไปที่ **Keys** → สร้าง key ใหม่
3. คัดลอก key มาใส่ในไฟล์ `.env`

---

## 📘 คู่มือการใช้งาน

### 1. 📁 ข้อมูลของฉัน (My Data)

หน้าหลักสำหรับจัดการไฟล์ทั้งหมด

**อัปโหลดไฟล์:**
- กดปุ่ม **"อัปโหลด"** หรือลากไฟล์วางในพื้นที่
- รองรับ: PDF, TXT, MD, DOCX
- ขนาดสูงสุด: 10 MB ต่อไฟล์

**ดูรายละเอียดไฟล์:**
- คลิกที่ชื่อไฟล์ → แผงด้านขวาจะแสดง:
  - สรุปเนื้อหา (AI สร้างให้อัตโนมัติ)
  - แท็ก (tag) ที่เกี่ยวข้อง
  - ความเชื่อมโยงกับไฟล์อื่น
  - เมตาดาต้า (ขนาด, วันที่, ประเภท)

**จัดระเบียบด้วย AI:**
- กดปุ่ม **"จัดระเบียบด้วย AI"**
- AI จะทำงาน 4 ขั้นตอน:
  1. จัดกลุ่มไฟล์เป็นคอลเลกชันอัตโนมัติ
  2. สร้างสรุปเนื้อหาทุกไฟล์
  3. สร้าง Knowledge Graph
  4. วิเคราะห์ความเชื่อมโยงระหว่างไฟล์

### 2. 🔍 มุมมองความรู้ (Knowledge View)

แสดงภาพรวมข้อมูลทั้งหมดที่จัดกลุ่มเรียบร้อย

- ดูคอลเลกชัน (กลุ่มไฟล์ที่เนื้อหาคล้ายกัน)
- คลิกคอลเลกชันเพื่อดูไฟล์ในกลุ่ม
- AI ตั้งชื่อกลุ่มให้อัตโนมัติ

### 3. 🕸️ กราฟ (Knowledge Graph)

แสดงความเชื่อมโยงระหว่างข้อมูลทั้งหมดเป็นภาพ

- **โหนด (จุดกลม)** = ไฟล์, หัวข้อ, แนวคิดสำคัญ
- **เส้นเชื่อม** = ความสัมพันธ์ระหว่างข้อมูล
- **วิธีใช้:**
  - ลากเพื่อเลื่อนดู
  - เลื่อนล้อเมาส์เพื่อซูม
  - คลิกโหนดเพื่อดูรายละเอียด
  - เลือก **Lens** ด้านบนเพื่อเปลี่ยนมุมมอง

**สร้างกราฟ:**
- กดปุ่ม **"สร้างกราฟ"** (ต้องจัดระเบียบข้อมูลก่อน)
- AI จะวิเคราะห์และสร้างโหนด + ความสัมพันธ์อัตโนมัติ

### 4. 💬 AI แชท (AI Chat)

ถามคำถามเกี่ยวกับข้อมูลของคุณ — AI จะตอบโดยอ้างอิงจากข้อมูลจริง

**วิธีใช้:**
- พิมพ์คำถามแล้วกด Enter หรือกดปุ่มส่ง
- AI จะค้นหาข้อมูลที่เกี่ยวข้องจาก:
  - โปรไฟล์ส่วนตัว
  - ไฟล์ทั้งหมด
  - Knowledge Graph
  - Context Packs
- ด้านขวาจะแสดง **"หลักฐานที่ใช้"** ว่า AI อ้างอิงจากไฟล์ไหนบ้าง

**ตัวอย่างคำถาม:**
- *"สรุปข้อมูลทั้งหมดของฉันให้หน่อย"*
- *"Project KEY เกี่ยวข้องกับอะไรบ้าง"*
- *"หาความเชื่อมโยงระหว่าง [หัวข้อ A] กับ [หัวข้อ B]"*

### 5. 👤 โปรไฟล์ (Profile)

ตั้งค่าข้อมูลส่วนตัวเพื่อให้ AI ตอบตรงตามเป้าหมาย

- ชื่อ, อาชีพ, เป้าหมาย, รูปแบบการทำงาน
- เมื่อตั้งค่าแล้ว AI จะปรับคำตอบให้เหมาะกับคุณ
- ตั้งค่าได้ที่ **AI แชท → Profile** หรือผ่าน Onboarding Quiz ตอนเริ่มใช้งาน

### 6. 📦 Context Packs

แพ็คความรู้ที่สกัดจากหลายไฟล์รวมกัน — เหมาะสำหรับส่งให้ AI อื่นใช้

- สร้างได้ที่ **AI แชท → Packs**
- ระบุหัวข้อ → AI สรุปข้อมูลจากทุกไฟล์ที่เกี่ยวข้องเป็น Pack เดียว

### 7. 🌐 สลับภาษา

- กดปุ่ม **TH | EN** ที่มุมซ้ายล่าง
- ระบบมีคำแปล 170+ รายการ
- ค่าเริ่มต้นเป็นภาษาไทย

---

## ✨ ฟีเจอร์ทั้งหมด

| ฟีเจอร์ | รายละเอียด |
|---------|-----------|
| 📁 ข้อมูลของฉัน | อัปโหลด จัดการ ดูรายละเอียดไฟล์ (PDF, TXT, MD, DOCX) |
| 🧠 จัดระเบียบด้วย AI | จัดกลุ่มอัตโนมัติ สร้างสรุป เพิ่ม metadata |
| 🔗 Knowledge Graph | แสดงกราฟความสัมพันธ์ด้วย D3.js |
| 💬 AI แชท | ถาม-ตอบอ้างอิงข้อมูลจริง 7 ชั้น (Graph-Aware RAG) |
| 👤 โปรไฟล์ | ปรับ AI ให้ตรงตามเป้าหมายส่วนตัว |
| 📦 Context Packs | สกัดความรู้จากหลายไฟล์เป็น Pack |
| 🔌 MCP Connector | เชื่อมต่อ Claude / Antigravity ด้วย 23 เครื่องมือ + File Sharing |
| 🔐 ระบบสิทธิ์ | เปิด/ปิดเครื่องมือ MCP + รหัสผ่าน Admin |
| 👥 Multi-User | สมัคร/ล็อกอิน + ข้อมูลแยกรายบุคคล |
| 🔄 LLM Text Cleanup | แก้ข้อความ PDF ที่เพี้ยนด้วย AI อัตโนมัติ |
| 🌐 สองภาษา | ไทย/อังกฤษ สลับได้ทันที |

---

## 🔌 เชื่อมต่อ MCP

ใช้ MCP (Model Context Protocol) ให้ AI Client เข้าถึงข้อมูลของคุณ:

### ขั้นตอนการเชื่อมต่อ

1. ไปที่หน้า **ตั้งค่า MCP** ในแอป
2. คัดลอก Connector URL

### สำหรับ Claude Desktop

```json
{
  "mcpServers": {
    "project-key": {
      "url": "https://project-key.fly.dev/mcp/{YOUR_SECRET_KEY}"
    }
  }
}
```

### สำหรับ Antigravity (ใช้ mcp-remote bridge)

```json
{
  "mcpServers": {
    "project-key": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://project-key.fly.dev/mcp/{YOUR_SECRET_KEY}"]
    }
  }
}
```

> 💡 Antigravity ไม่รองรับ remote MCP โดยตรง — ใช้ `mcp-remote` package เป็น stdio ↔ HTTP bridge

### เครื่องมือ MCP ทั้ง 23 ตัว

| หมวด | เครื่องมือ |
|------|-----------|
| 📖 **อ่านและค้นหา** (11) | ดูโปรไฟล์, รายการไฟล์, เนื้อหาไฟล์, **ลิงก์ดาวน์โหลดไฟล์**, สรุปไฟล์, รายการคอลเลกชัน, รายการ Context Pack, ดู Context Pack, ค้นหาความรู้, สำรวจกราฟ, ดูภาพรวม |
| ✏️ **สร้างและแก้ไข** (5) | สร้าง Context Pack, เพิ่มโน้ต, แก้แท็ก, อัปโหลดข้อความ, แก้โปรไฟล์ |
| 🗑️ **ลบ** (2) | ลบไฟล์, ลบ Pack |
| ⚙️ **AI Pipeline** (5) | จัดระเบียบ, สร้างกราฟ, เพิ่ม metadata, **แก้ไขการแปลงไฟล์ (reprocess)**, เข้าสู่ระบบ Admin |

### ตัวอย่างการใช้ใน Claude

> *"ค้นหาข้อมูลเกี่ยวกับ Knowledge Graph จากไฟล์ของฉัน"*

Claude จะเรียก `search_knowledge` → ได้ข้อมูลจากไฟล์ที่เกี่ยวข้อง → ตอบพร้อมอ้างอิง

---

## 📂 โครงสร้างโปรเจกต์

```
Project KEY/
├── legacy-frontend/          # ฝั่ง Frontend
│   ├── index.html            # หน้าเว็บ (1,025 บรรทัด — 7 หน้า + i18n)
│   ├── app.js                # โค้ดฝั่ง Frontend (2,720 บรรทัด)
│   └── styles.css            # ธีมสีเข้ม + ระบบดีไซน์ (3,263 บรรทัด)
│
├── backend/                  # FastAPI backend (19 โมดูล)
│   ├── main.py               # 40+ API endpoints (1,362 บรรทัด)
│   ├── mcp_tools.py          # 23 เครื่องมือ MCP + ระบบสิทธิ์ + File Sharing (1,176 บรรทัด)
│   ├── graph_builder.py      # สร้าง Knowledge Graph
│   ├── retriever.py          # ระบบ RAG 7 ชั้น
│   ├── vector_search.py      # ค้นหาแบบ TF-IDF
│   ├── database.py           # ฐานข้อมูล 18 ตาราง
│   ├── organizer.py          # AI จัดกลุ่ม + ให้คะแนน
│   ├── relations.py          # ความเชื่อมโยง + แนะนำ
│   ├── llm.py                # Dual model: Gemini 3.1 Pro + Flash
│   ├── shared_links.py       # ลิงก์ดาวน์โหลดชั่วคราว (30 นาที)
│   ├── auth.py               # สมัคร/ล็อกอิน/รีเซ็ตรหัสผ่าน (JWT)
│   ├── mcp_tokens.py         # จัดการ Token สำหรับ MCP
│   ├── extraction.py         # แปลงไฟล์เป็นข้อความ + LLM cleanup
│   ├── metadata.py           # AI เพิ่ม metadata (tags, sensitivity)
│   ├── context_packs.py      # จัดการ Context Pack
│   ├── profile.py            # จัดการโปรไฟล์ผู้ใช้
│   ├── markdown_store.py     # จัดการ markdown files
│   └── config.py             # ตั้งค่าระบบ
│
├── mcp-proxy.js              # MCP stdio → HTTP proxy (สำรอง)
├── Dockerfile                # สำหรับ build Docker image
├── fly.toml                  # ตั้งค่า Fly.io
├── .env                      # API key (ไม่รวมใน git)
│
├── docs/                     # เอกสาร
│   ├── PROJECT_REPORT.md     # รายงานฉบับเต็ม (v0.1 → v4.3)
│   └── prd/                  # เอกสาร PRD v1-v4
│
└── tests/                    # ชุดทดสอบ
    ├── e2e/                  # ทดสอบ End-to-End + MCP
    └── testsprite/           # ทดสอบอัตโนมัติ
```

---

## 🛠️ เทคโนโลยี

| ส่วน | เทคโนโลยี |
|------|-----------|
| Frontend | HTML + Vanilla JS + CSS + D3.js v7 |
| Backend | Python FastAPI + Uvicorn |
| ฐานข้อมูล | SQLite (18 ตาราง, async ผ่าน aiosqlite) |
| ค้นหา | TF-IDF hybrid (สร้างใหม่อัตโนมัติตอนเริ่มระบบ) |
| AI/LLM | OpenRouter → Gemini 3.1 Pro (จัดการข้อมูล) + Gemini 3 Flash (แชท) |
| Auth | JWT + bcrypt (Multi-User) |
| Deploy | Docker + Fly.io (ภูมิภาค Singapore) |
| AI Integration | MCP Streamable HTTP (23 เครื่องมือ) — รองรับ Claude Desktop + Antigravity |

---

## 🚀 Deploy ขึ้น Production

### Fly.io

```bash
# ติดตั้ง flyctl (ครั้งแรก)
# ดูวิธีที่: https://fly.io/docs/flyctl/install/

# ตั้งค่า API key บน Fly
flyctl secrets set OPENROUTER_API_KEY=your_api_key_here

# Deploy
flyctl deploy

# เว็บไซต์: https://project-key.fly.dev/
```

### ข้อควรรู้
- ข้อมูลเก็บใน **Persistent Volume** (`/app/data`) ไม่หายเมื่อ deploy ใหม่
- เซิร์ฟเวอร์อยู่ที่ **Singapore** (ใกล้ไทย, latency ต่ำ)
- ระบบ **auto-stop** เมื่อไม่มีคนใช้ → ประหยัดค่าใช้จ่าย
- เข้าใช้งานครั้งแรกอาจใช้เวลา 3-5 วินาทีในการ startup

---

## 📋 ประวัติเวอร์ชัน

| เวอร์ชัน | สิ่งที่เพิ่ม |
|----------|------------|
| v0.1 | อัปโหลด, จัดระเบียบ, AI แชท |
| v2.0 | โปรไฟล์, Context Packs, ค้นหาแบบ Hybrid |
| v3.0 | Knowledge Graph, สองภาษา, ปรับโครงสร้างโปรเจกต์ |
| v4.0 | Deploy Fly.io, MCP 5 เครื่องมือ |
| v4.1 | MCP 21 เครื่องมือ, ปรับปรุง UX จัดการข้อมูล |
| v4.2 | ระบบสิทธิ์, แบ่ง 4 หมวด, แปลไทยครบ |
| v4.3 | แก้บัคค้นหา, แก้บัคเพิ่มโน้ต, สร้าง index ตอน startup |
| v5.0 | Multi-User Auth (สมัคร/ล็อกอิน/JWT), ข้อมูลแยกรายบุคคล |
| v5.1 | รีเซ็ตรหัสผ่าน, Token ส่วนตัว, URL แยกผู้ใช้ |
| v5.2 | Dual AI (Gemini 3.1 Pro/Flash), LLM Text Cleanup, File Sharing Link, MCP 22 เครื่องมือ |
| **v5.3** | **แก้บัค `import os`, เพิ่ม Antigravity MCP tab (mcp-remote bridge), MCP 23 เครื่องมือ, Multi-Platform MCP Setup** |

---

## ❓ แก้ปัญหาที่พบบ่อย

### แชท AI ไม่ตอบ
- ตรวจสอบ API key ในไฟล์ `.env` ว่ายังใช้ได้
- ไปที่ [openrouter.ai](https://openrouter.ai/) → ดูว่า key ยังใช้งานได้

### หน้าเว็บโหลดช้าตอน deploy
- ครั้งแรกอาจใช้เวลา 3-5 วินาที (auto-start)
- หลังจากนั้นจะเร็วปกติ

### กราฟไม่แสดง
- ต้อง **จัดระเบียบด้วย AI** ก่อน (กดปุ่มที่หน้าข้อมูลของฉัน)
- แล้วกด **สร้างกราฟ** ที่หน้ากราฟ

### อัปโหลดไฟล์ไม่ได้
- ตรวจสอบขนาดไฟล์ (สูงสุด 10 MB)
- รองรับเฉพาะ: `.pdf`, `.txt`, `.md`, `.docx`

### เชื่อมต่อ MCP ไม่ได้ (Antigravity)
- ต้องใช้ `mcp-remote` bridge — ดูตัวอย่างในหน้า MCP Settings
- กด Reload Window หลังแก้ `mcp_config.json`

---

*สร้างด้วย ❤️ โดยทีม Project KEY*
