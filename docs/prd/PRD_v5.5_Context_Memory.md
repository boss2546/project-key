# 📄 PRD v5.5 — Context Memory System (Cross-Platform)

> **Product:** Project KEY — Personal Data Bank  
> **Feature:** Context Memory (ระบบจำบริบทข้ามแพลตฟอร์ม)  
> **Version:** v5.5  
> **Author:** Antigravity AI + ทีมพัฒนา  
> **วันที่:** 25 เมษายน 2569  
> **สถานะ:** 📝 Draft — รอ Review

---

## 1. สรุปผู้บริหาร (Executive Summary)

ปัจจุบัน Project KEY รองรับการเชื่อมต่อ AI ผ่าน MCP หลายแพลตฟอร์ม (Claude Desktop, Antigravity, ChatGPT) แต่ทุกครั้งที่ผู้ใช้เปิดแพลตฟอร์มใหม่หรือเริ่มสนทนาใหม่ **AI ไม่รู้ว่าก่อนหน้านี้ผู้ใช้ทำอะไรอยู่** ทำให้ต้องอธิบายซ้ำทุกครั้ง

**Context Memory** จะทำให้ PDB.ME เป็น **"สมองกลาง"** ที่เก็บบริบทการทำงานไว้ เมื่อผู้ใช้เปลี่ยนแพลตฟอร์มหรือเริ่มสนทนาใหม่ AI สามารถดึง context กลับมาใช้ต่อได้ทันที

---

## 2. ปัญหาที่ต้องแก้ (Problem Statement)

### 2.1 ปัญหาปัจจุบัน

| # | ปัญหา | ผลกระทบ |
|---|-------|---------|
| 1 | เปลี่ยนแพลตฟอร์มแล้ว AI ลืมทุกอย่าง | ต้องอธิบายซ้ำ เสียเวลา 5-10 นาทีต่อครั้ง |
| 2 | เปิด conversation ใหม่ต้องเริ่มต้นจากศูนย์ | AI ไม่รู้ว่าโปรเจกต์ทำถึงไหนแล้ว |
| 3 | ไม่มีที่เก็บ "สิ่งที่กำลังทำอยู่" แบบ centralized | ข้อมูลกระจายตามแต่ละ chat session |
| 4 | Context Pack ที่มีอยู่เป็น static (สร้างจากไฟล์) | ไม่ update ตามสถานการณ์จริง |

### 2.2 ความแตกต่างจาก Context Pack ที่มีอยู่

| | Context Pack (v2.0) | **Context Memory (v5.5)** |
|--|---------------------|--------------------------|
| **ที่มา** | สร้างจากไฟล์ในระบบ | สร้างจากการสนทนา/การทำงานจริง |
| **ลักษณะ** | Static — สร้างแล้วไม่เปลี่ยน | Dynamic — อัปเดตได้ตลอด |
| **จุดประสงค์** | ให้ AI รู้จักผู้ใช้ | ให้ AI รู้ว่า **กำลังทำอะไรอยู่** |
| **การใช้** | ผู้ใช้ต้องเลือกเอง | โหลดอัตโนมัติ + แนะนำ |

---

## 3. เป้าหมาย (Goals)

### 3.1 เป้าหมายหลัก
- ผู้ใช้สามารถ **ทำงานต่อข้ามแพลตฟอร์ม** ได้โดยไม่ต้องอธิบายซ้ำ
- AI สามารถ **จำได้ว่าก่อนหน้านี้ทำอะไร** แม้เปิดสนทนาใหม่

### 3.2 เป้าหมายรอง
- ผู้ใช้จัดการ Context ได้ทั้งผ่าน **MCP (สั่ง AI)** และ **Web UI (หน้าเว็บ)**
- ระบบ **แนะนำ Context ที่เกี่ยวข้อง** อัตโนมัติจาก query

### 3.3 พฤติกรรม Default Context (สำคัญ)

> **หลักการ:** ผู้ใช้ไม่ต้องเลือก Context เอง — ระบบจะโหลด Context ล่าสุดให้อัตโนมัติ

| สถานการณ์ | พฤติกรรม |
|-----------|----------|
| เปิดแพลตฟอร์มใหม่ (Claude/Antigravity/ChatGPT) | AI เรียก `load_context()` → **ได้ context ล่าสุด + pinned ทันที** |
| มี context ล่าสุด + pinned หลายอัน | ส่ง **context ล่าสุด 1 อัน + pinned ทั้งหมด** รวมกัน |
| ไม่มี context เลย | ตอบ `{"contexts": [], "count": 0}` → AI เริ่มต้นใหม่ปกติ |
| ผู้ใช้ระบุ `context_id` | ดึง context ที่ระบุเท่านั้น (ไม่ auto) |
| ผู้ใช้ save context ใหม่ | context ใหม่จะกลายเป็น "ล่าสุด" ทันที |

**ลำดับการโหลด Default Context:**
```
1. Pinned contexts (is_pinned=true) → โหลดทั้งหมด เรียงตาม updated_at DESC
2. Latest context (ล่าสุด 1 อัน) → โหลดอัตโนมัติถ้าไม่ซ้ำกับ pinned
3. รวมส่งให้ AI เป็น array → AI ได้ข้อมูลครบโดยไม่ต้องถามผู้ใช้
```

**Flow ตัวอย่าง:**
```
ผู้ใช้คุย Claude → save_context("งาน v5.4") → เปิด Antigravity
→ AI เรียก load_context() อัตโนมัติ
→ ได้ "งาน v5.4" ทันที ไม่ต้องถามว่าจะโหลดอะไร
→ AI: "เมื่อกี้คุณทำ v5.4 ค้างไว้ ต่อเลยไหม?"
```

### 3.4 ไม่อยู่ในขอบเขต (Out of Scope)
- Real-time sync ระหว่าง platforms (ไม่ทำ WebSocket)
- Auto-capture ทุก conversation โดยไม่ถาม (privacy concern)
- Shared context ข้ามผู้ใช้ (ยังไม่ทำ collaboration)

---

## 4. User Stories

| # | ในฐานะ | ฉันต้องการ | เพื่อที่จะ |
|---|--------|-----------|----------|
| US-1 | ผู้ใช้ | บันทึก context สรุปการทำงานปัจจุบัน | กลับมาทำต่อได้ทีหลัง |
| US-2 | ผู้ใช้ | ดึง context ล่าสุดเมื่อเปิดแพลตฟอร์มใหม่ | ไม่ต้องอธิบายซ้ำ |
| US-3 | ผู้ใช้ | ปักหมุด (pin) context สำคัญ | ให้ AI โหลดอัตโนมัติทุกครั้ง |
| US-4 | ผู้ใช้ | ดู/แก้ไข/ลบ context ผ่านหน้าเว็บ | จัดการได้สะดวกไม่ต้องสั่ง AI |
| US-5 | ผู้ใช้ | ให้ AI แนะนำ context ที่เกี่ยวข้อง | ไม่ต้องจำว่าเก็บอะไรไว้บ้าง |
| US-6 | ผู้ใช้ | เชื่อม context กับไฟล์ในระบบ | ดึงข้อมูลประกอบได้ทันที |
| US-7 | ผู้ใช้ | แก้ไข context ที่มีอยู่ได้ | อัปเดตให้ตรงกับสถานะปัจจุบัน |
| US-8 | ผู้ใช้ | สั่ง AI ให้บันทึก context ก่อนจบสนทนา | ไม่ลืมสิ่งที่ทำไปแล้ว |

---

## 5. Functional Requirements

### 5.1 MCP Tools (6 ตัวใหม่)

| FR# | ชื่อ Tool | ประเภท | ต้องยืนยัน | คำอธิบาย |
|-----|----------|--------|-----------|---------|
| FR-1 | `save_context` | Write | ⚠️ ใช่ | บันทึก context ใหม่ (title, content, type, tags) |
| FR-2 | `load_context` | Read | ❌ ไม่ | ดึง context ตาม ID หรือดึงล่าสุด + pinned |
| FR-3 | `list_contexts` | Read | ❌ ไม่ | แสดงรายการ contexts ทั้งหมด (filter ได้) |
| FR-4 | `update_context` | Write | ⚠️ ใช่ | แก้ไข title/content/tags/pin ของ context |
| FR-5 | `delete_context` | Delete | ⛔ ใช่ | ลบ context ถาวร |
| FR-6 | `auto_context` | Read | ❌ ไม่ | ค้นหาและแนะนำ context ที่เกี่ยวข้อง |

### 5.2 REST API (สำหรับ Frontend)

| FR# | Method | Endpoint | คำอธิบาย |
|-----|--------|----------|---------|
| FR-7 | GET | `/api/contexts` | ดึงรายการ contexts ของผู้ใช้ |
| FR-8 | POST | `/api/contexts` | สร้าง context ใหม่ |
| FR-9 | PUT | `/api/contexts/{id}` | แก้ไข context |
| FR-10 | DELETE | `/api/contexts/{id}` | ลบ context |
| FR-11 | POST | `/api/contexts/{id}/pin` | toggle pin/unpin |

### 5.3 Frontend UI

| FR# | หน้า | คำอธิบาย |
|-----|------|---------|
| FR-12 | Context Memory Page | แสดง/สร้าง/แก้ไข/ลบ/pin contexts |

---

## 6. Data Model

### 6.1 ตาราง `context_memories`

```sql
CREATE TABLE context_memories (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    content         TEXT NOT NULL,
    
    context_type    TEXT DEFAULT 'conversation',
    platform        TEXT DEFAULT 'unknown',
    tags            TEXT DEFAULT '[]',
    
    is_active       BOOLEAN DEFAULT TRUE,
    is_pinned       BOOLEAN DEFAULT FALSE,
    
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at    DATETIME,
    
    related_file_ids TEXT DEFAULT '[]',
    parent_id       TEXT REFERENCES context_memories(id)
);
```

### 6.2 ข้อจำกัดข้อมูล

| Field | ข้อจำกัด |
|-------|---------|
| `title` | 1–200 ตัวอักษร |
| `summary` | 1–500 ตัวอักษร |
| `content` | 1–50,000 ตัวอักษร |
| `context_type` | enum: `conversation`, `project`, `task`, `note` |
| `platform` | enum: `claude`, `antigravity`, `chatgpt`, `web`, `unknown` |
| `tags` | สูงสุด 20 tags |

---

## 7. MCP API Specification

### 7.1 `save_context`

**Input:**
```json
{
  "title": "string (required)",
  "content": "string (required)",
  "summary": "string (optional — auto-generate if empty)",
  "context_type": "string (optional, default: conversation)",
  "platform": "string (optional, default: auto-detect)",
  "tags": "array (optional)",
  "related_file_ids": "array (optional)",
  "is_pinned": "boolean (optional, default: false)"
}
```
**Annotations:** `readOnlyHint: false, destructiveHint: false`

### 7.2 `load_context` (Default = ล่าสุดเสมอ)

**Input:**
```json
{
  "context_id": "string (optional — ถ้าไม่ใส่ = ดึงล่าสุดอัตโนมัติ)",
  "include_pinned": "boolean (optional, default: true)"
}
```

**Logic (สำคัญ):**
- **ไม่ใส่ context_id** → ดึง context ที่ `updated_at` ล่าสุด 1 อัน + pinned ทั้งหมด
- **ใส่ context_id** → ดึง context นั้นตัวเดียว
- ทุกครั้งที่ load → อัปเดต `last_used_at` อัตโนมัติ
- AI client ควรเรียก tool นี้ตอนเริ่มสนทนาใหม่เสมอ

**Annotations:** `readOnlyHint: true`

### 7.3 `list_contexts`

**Input:**
```json
{
  "limit": "integer (optional, default: 10, max: 50)",
  "context_type": "string (optional — filter)",
  "is_pinned": "boolean (optional — filter)",
  "search": "string (optional — keyword search)"
}
```
**Annotations:** `readOnlyHint: true`

### 7.4 `update_context`

**Input:**
```json
{
  "context_id": "string (required)",
  "title": "string (optional)",
  "content": "string (optional)",
  "summary": "string (optional)",
  "tags": "array (optional)",
  "is_pinned": "boolean (optional)",
  "is_active": "boolean (optional)"
}
```
**Annotations:** `readOnlyHint: false`

### 7.5 `delete_context`

**Input:** `{ "context_id": "string (required)" }`  
**Annotations:** `destructiveHint: true`

### 7.6 `auto_context`

**Input:** `{ "query": "string (required)", "limit": "integer (optional, default: 3)" }`  
**Annotations:** `readOnlyHint: true`

---

## 8. Frontend UI Specification

### 8.1 ตำแหน่ง: Tab ใหม่ "🧠 Context Memory" ใน sidebar

### 8.2 Layout หน้า Context Memory

```
┌───────────────────────────────────────────┐
│ 🧠 Context Memory              [+ สร้างใหม่] │
│                                             │
│ 📌 Pinned                                   │
│ ┌─────────────────────────────────────┐     │
│ │ 📌 สรุปงาน Project KEY v5.4        │     │
│ │ ทำ export_file_to_chat + annotations│     │
│ │ 🏷️ project-key | antigravity       │     │
│ │ [แก้ไข] [ถอดหมุด]                  │     │
│ └─────────────────────────────────────┘     │
│                                             │
│ 📋 Recent                                   │
│ ┌─────────────────────────────────────┐     │
│ │ 💬 แก้บัค login page               │     │
│ │ แก้ JWT token expired...           │     │
│ │ 🏷️ bugfix | claude                │     │
│ │ [แก้ไข] [📌] [🗑️]                 │     │
│ └─────────────────────────────────────┘     │
└───────────────────────────────────────────┘
```

### 8.3 Context Type Icons

| Type | Icon |
|------|------|
| `conversation` | 💬 |
| `project` | 🎯 |
| `task` | ✅ |
| `note` | 📝 |

---

## 9. Security & Permission

| Action | Permission | Annotations |
|--------|-----------|-------------|
| `load_context` | ✅ ทำได้เลย | readOnly: true |
| `list_contexts` | ✅ ทำได้เลย | readOnly: true |
| `auto_context` | ✅ ทำได้เลย | readOnly: true |
| `save_context` | ⚠️ ต้องยืนยัน | readOnly: false |
| `update_context` | ⚠️ ต้องยืนยัน | readOnly: false |
| `delete_context` | ⛔ ยืนยันเข้มงวด | destructive: true |

---

## 10. Test Cases

| TC# | กรณีทดสอบ | Expected |
|-----|----------|----------|
| TC-1 | save_context ปกติ | สร้างสำเร็จ + return context_id |
| TC-2 | load_context() ไม่ใส่ ID | ได้ context ล่าสุด + pinned |
| TC-3 | load_context(id) | ได้ context นั้น + อัปเดต last_used_at |
| TC-4 | load_context("invalid") | error: context_not_found |
| TC-5 | list_contexts + filter | ได้เฉพาะ type ที่ระบุ |
| TC-6 | update_context | แก้ไขสำเร็จ + updated_at เปลี่ยน |
| TC-7 | pin context | is_pinned = true |
| TC-8 | delete_context | ลบสำเร็จ |
| TC-9 | auto_context("MCP") | แนะนำ context ที่ match |
| TC-10 | สร้างผ่าน Web UI | context ปรากฏในรายการ |

---

## 11. Acceptance Criteria

- [ ] save/load/list/update/delete/auto_context ทำงานผ่าน MCP
- [ ] Web UI สร้าง/แก้/ลบ/pin ได้
- [ ] Annotations ถูกต้อง (read=auto, write=confirm, delete=destructive)
- [ ] ข้อมูลแยก user_id ไม่ข้ามผู้ใช้
- [ ] ทดสอบผ่าน Antigravity MCP จริง
- [ ] Deploy production สำเร็จ
- [ ] 10/10 test cases ผ่าน

---

## 12. Timeline

| Phase | งาน | ระยะเวลา |
|-------|-----|---------|
| Phase 1 | Backend: DB + context_memory.py + MCP tools | 1-2 ชม. |
| Phase 2 | Frontend: UI page | 1-2 ชม. |
| Phase 3 | Test + Deploy + Docs | 30 นาที |
| **รวม** | | **~3-4 ชั่วโมง** |

---

## 13. สถิติหลังทำเสร็จ

| รายการ | v5.4 | **v5.5** |
|--------|------|----------|
| MCP Tools | 24 | **30** (+6) |
| DB Tables | 18 | **19** (+1) |
| Backend Modules | 19 | **20** (+1) |
| ระบบจำบริบท | ❌ | ✅ Context Memory |
| ข้ามแพลตฟอร์ม | ❌ ลืมทุกครั้ง | ✅ จำได้ต่อเนื่อง |

---

*PRD จัดทำโดย Antigravity AI · Project KEY v5.5 · 25 เมษายน 2569*
