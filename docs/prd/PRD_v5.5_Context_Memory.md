# 📄 PRD v5.5 — Context Memory System (Cross-Platform)

> **Product:** Project KEY — Personal Data Bank  
> **Feature:** Context Memory (ระบบจำบริบทข้ามแพลตฟอร์ม)  
> **Version:** v5.5  
> **Author:** Antigravity AI + ทีมพัฒนา  
> **วันที่:** 25 เมษายน 2569  
> **สถานะ:** ✅ Complete — ทดสอบผ่านทั้ง 14/14 test cases (25/04/2569)
> **Design Principle:** 🎯 Zero-Effort Context — ผู้ใช้ไม่ต้องทำอะไรเลย ระบบจัดการให้หมด

---

## 1. สรุปผู้บริหาร (Executive Summary)

ปัจจุบัน Project KEY รองรับการเชื่อมต่อ AI ผ่าน MCP หลายแพลตฟอร์ม (Claude Desktop, Antigravity, ChatGPT) แต่ทุกครั้งที่ผู้ใช้เปิดแพลตฟอร์มใหม่หรือเริ่มสนทนาใหม่ **AI ไม่รู้ว่าก่อนหน้านี้ผู้ใช้ทำอะไรอยู่** ทำให้ต้องอธิบายซ้ำทุกครั้ง

**Context Memory** จะทำให้ PDB.ME เป็น **"สมองกลาง"** ที่เก็บบริบทการทำงานไว้ เมื่อผู้ใช้เปลี่ยนแพลตฟอร์มหรือเริ่มสนทนาใหม่ AI สามารถดึง context กลับมาใช้ต่อได้ทันที

### หลักการออกแบบ: Zero-Effort Context

> **ผู้ใช้ไม่ต้อง "ทำ" อะไรเลย** — ระบบจัดการทุกอย่างให้อัตโนมัติ

| หลักการ | สิ่งที่ระบบทำแทนผู้ใช้ |
|---------|---------------------|
| 🔄 **Auto-Load** | เปิดแพลตฟอร์มใหม่ → context ล่าสุดพร้อมใช้ทันที |
| 💾 **Auto-Suggest Save** | AI แนะนำให้บันทึกก่อนจบสนทนา ผู้ใช้ไม่ต้องจำ |
| 🧹 **Auto-Cleanup** | context เก่าถูก archive อัตโนมัติ ไม่ต้องลบเอง |
| 🔀 **Smart Merge** | ไม่สร้าง context ซ้ำ — อัปเดตตัวเดิมถ้าเรื่องเดียวกัน |
| 📝 **Auto-Summary** | สรุปย่อสร้างอัตโนมัติจาก AI ไม่ต้องเขียนเอง |
| 📌 **Pin สำคัญ** | ผู้ใช้เลือก pin เฉพาะอันสำคัญ (สูงสุด 3 อัน) |

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
| AI จะจบสนทนา | AI **แนะนำ save อัตโนมัติ** → ผู้ใช้แค่ยืนยัน |
| save เรื่องซ้ำกัน (< 2 ชม.) | **Smart Merge** — อัปเดตตัวเดิมแทนสร้างใหม่ |
| context เกิน 20 อัน | **Auto-Archive** — อันเก่าสุดถูก archive อัตโนมัติ |
| pin เกิน 3 อัน | แจ้งเตือนให้ถอด pin อันเก่าก่อน (สูงสุด 3) |

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

**🔑 UX ที่ดีที่สุด — Profile + Context รวมกัน:**

ปัจจุบัน AI เรียก `get_profile` เป็นอันดับแรกเมื่อเริ่มสนทนา → ใน v5.5 จะ **แนบ Context ล่าสุดไปด้วยทันที** ไม่ต้องเรียก 2 รอบ

```
เดิม (v5.4):                    ใหม่ (v5.5):
1. get_profile → ได้โปรไฟล์      1. get_profile → ได้โปรไฟล์ + Context ล่าสุด + Pinned
2. (ไม่มี context)               → AI พร้อมทำงานต่อทันที!
```

**แก้ไข `get_profile` response:**
```json
{
  "identity_summary": "...",
  "goals": "...",
  "working_style": "...",
  "preferred_output_style": "...",
  "background_context": "...",
  
  "active_contexts": [
    {
      "context_id": "ctx_abc123",
      "title": "สรุปงาน v5.4",
      "summary": "ทำ export_file_to_chat + MCP annotations",
      "is_pinned": true,
      "updated_at": "2026-04-25T10:00:00"
    }
  ],
  "active_contexts_count": 1,
  "tip": "Active contexts are included. Use load_context(id) to get full content."
}
```

> **หมายเหตุ:** `active_contexts` ส่งแค่ title + summary (ไม่ส่ง content เต็ม) เพื่อประหยัด token  
> ถ้า AI ต้องการ content เต็ม → เรียก `load_context(context_id)` ต่อ

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
| FR-1 | `save_context` | Write | ✅ ไม่ต้อง | บันทึก context ใหม่ (สรุปอัตโนมัติ + Smart Merge) — AI แนะนำ save ก่อนจบสนทนา |
| FR-2 | `load_context` | Read | ❌ ไม่ | ดึง context ตาม ID หรือดึงล่าสุด + pinned |
| FR-3 | `list_contexts` | Read | ❌ ไม่ | แสดงรายการ contexts ทั้งหมด (filter ได้) |
| FR-4 | `update_context` | Write | ⚠️ ใช่ | แก้ไข title/content/tags/pin (เฉพาะแก้ข้อมูลเดิม) |
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
| `summary` | auto-generated จาก AI (ไม่ต้องเขียนเอง) — สูงสุด 500 chars |
| `content` | 1–50,000 ตัวอักษร |
| `context_type` | enum: `conversation`, `project`, `task`, `note` |
| `platform` | enum: `claude`, `antigravity`, `chatgpt`, `web`, `unknown` |
| `tags` | สูงสุด 20 tags |
| `is_pinned` | สูงสุด **3** contexts ต่อ user |
| `max_active` | สูงสุด **20** active contexts ต่อ user (เกิน → auto-archive) |

---

## 7. MCP API Specification

### 7.1 `save_context`

**Input:**
```json
{
  "title": "string (required)",
  "content": "string (required)",
  "summary": "string (optional — auto-generate จาก AI ถ้าไม่ใส่)",
  "context_type": "string (optional, default: conversation)",
  "platform": "string (optional, default: auto-detect)",
  "tags": "array (optional)",
  "related_file_ids": "array (optional)",
  "is_pinned": "boolean (optional, default: false)"
}
```

**Smart Merge Logic:**
- ถ้ามี context ที่ title คล้ายกัน + `updated_at` < 2 ชั่วโมง → **อัปเดตตัวเดิม** แทนสร้างใหม่
- ถ้าไม่มี หรือ title ต่างกัน → สร้าง context ใหม่ตามปกติ
- ถ้า active contexts เกิน 20 → auto-archive อันเก่าสุด (`is_active=false`)

**AI Behavior Instruction (ใส่ใน tool description):**
```
AI SHOULD proactively suggest saving context when:
1. The conversation is about to end
2. Significant work has been completed
3. The user switches topics
The user only needs to confirm — AI handles the rest.
```

**Annotations:** `readOnlyHint: false, destructiveHint: false, idempotentHint: false`

> ✅ `save_context` ไม่ต้องยืนยันแบบเข้มงวด เพราะเป็นการ "save" ไม่ใช่ "delete" — ลด friction ให้ AI ทำงานได้ลื่น

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
| `save_context` | ✅ ทำได้เลย | readOnly: false, destructive: false |
| `update_context` | ⚠️ ต้องยืนยัน | readOnly: false |
| `delete_context` | ⛔ ยืนยันเข้มงวด | destructive: true |

---

## 10. Test Cases

| TC# | กรณีทดสอบ | Expected |
|-----|----------|----------|
| TC-1 | save_context ปกติ | สร้างสำเร็จ + auto-generate summary |
| TC-2 | load_context() ไม่ใส่ ID | ได้ context ล่าสุด + pinned |
| TC-3 | load_context(id) | ได้ context นั้น + อัปเดต last_used_at |
| TC-4 | load_context("invalid") | error: context_not_found |
| TC-5 | list_contexts + filter | ได้เฉพาะ type ที่ระบุ |
| TC-6 | update_context | แก้ไขสำเร็จ + updated_at เปลี่ยน |
| TC-7 | pin context (อันที่ 4) | แจ้งเตือน: "สูงสุด 3 กรุณาถอด pin อันเก่าก่อน" |
| TC-8 | delete_context | ลบสำเร็จ |
| TC-9 | auto_context("MCP") | แนะนำ context ที่ match |
| TC-10 | สร้างผ่าน Web UI | context ปรากฏในรายการ |
| TC-11 | **Smart Merge** — save ซ้ำ title เดิม < 2 ชม. | อัปเดตตัวเดิม ไม่สร้างใหม่ |
| TC-12 | **Auto-Archive** — active เกิน 20 | อันเก่าสุด archive อัตโนมัติ |
| TC-13 | **Auto-Summary** — save โดยไม่ใส่ summary | ได้ summary อัตโนมัติจาก AI |
| TC-14 | **get_profile + context** | get_profile ส่ง active_contexts มาด้วย |

---

## 11. Acceptance Criteria

- [x] save/load/list/update/delete/auto_context ทำงานผ่าน MCP
- [x] **save_context ไม่ต้องยืนยัน** (auto-approve) — ลด friction
- [x] **Smart Merge** — ไม่สร้าง context ซ้ำซ้อน ✅ ทดสอบ 25/04/2569
- [x] **Auto-Summary** — สรุปสร้างจาก AI อัตโนมัติ (OpenClaw-inspired)
- [x] **Auto-Archive** — เกิน 20 → archive เอง ✅ ทดสอบ 25/04/2569
- [x] **Max 3 Pin** — จำกัด pin
- [x] **get_profile แนบ context** — Profile + Context รวมกัน 1 call
- [x] Web UI สร้าง/แก้/ลบ/pin ได้
- [x] Annotations ถูกต้อง (save=auto, update=confirm, delete=destructive)
- [x] ข้อมูลแยก user_id ไม่ข้ามผู้ใช้
- [x] ทดสอบผ่าน Antigravity MCP จริง
- [x] Deploy production สำเร็จ
- [x] **14/14 test cases ผ่าน**

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

---

## 14. คู่มือการใช้งาน Context Memory System (User & AI Guide)

ระบบ Context Memory ถูกออกแบบมาด้วยแนวคิด **"Zero-Effort Context"** หมายความว่า **AI จะเป็นฝ่ายจัดการบริบทให้ผู้ใช้เองโดยที่ผู้ใช้แทบไม่ต้องทำอะไรเลย** เพียงแค่พูดคุยและทำงานตามปกติ ระบบจะคอยบันทึก จดจำ และดึงข้อมูลกลับมาให้อัตโนมัติเมื่อเริ่มการสนทนาใหม่ ไม่ว่าจะย้ายไปคุยผ่านแพลตฟอร์มใดก็ตาม (Claude, Antigravity, ChatGPT)

### 🧠 สำหรับ AI (AI Agent Guide)
AI ที่เชื่อมต่อผ่าน MCP จะต้องปฏิบัติตาม Guideline เหล่านี้เพื่อให้เกิด UX ที่ดีที่สุด:

1. **ดึง Profile พร้อม Context อัตโนมัติ (Start of Session)**
   - เมื่อเริ่มการสนทนาใหม่และ AI ทำการเรียกใช้เครื่องมือ `get_profile` ระบบจะแนบ **Active Contexts** ล่าสุดที่ผู้ใช้ทำค้างไว้ (รวมถึง Pinned Contexts) มาใน response ด้วยทันที
   - **ไม่ต้องใช้ `load_context` เพื่อค้นหาว่ามี context อะไรบ้าง** ให้ดูจากผลลัพธ์ของ `get_profile` ได้เลย
   - หากเห็น `active_contexts` ให้ AI **สานต่องานนั้นได้ทันที** หรือสรุปความคืบหน้าให้ผู้ใช้ฟังสั้นๆ ว่า "กำลังสานต่องาน [Context Title]..."

2. **บันทึก Context เชิงรุก (Proactive Save)**
   - ไม่ต้องรอให้ผู้ใช้สั่งบันทึก! AI ควรเรียกใช้เครื่องมือ `save_context` **อัตโนมัติ**ในกรณีต่อไปนี้:
     - 📌 จบการทำงานสำคัญๆ หรือทำงานเสร็จ 1 หัวข้อย่อย
     - 📌 ผู้ใช้ต้องการเปลี่ยนไปทำงานหัวข้ออื่น
     - 📌 ดูเหมือนการสนทนากำลังจะจบลง (เช่น มีการกล่าวสรุปหรือขอบคุณ)
   - หากเนื้อหายังคงอยู่ในเรื่องเดิม การใช้ `save_context` ซ้ำภายใน 2 ชั่วโมงด้วยชื่อ (title) เดิม ระบบจะทำการ **Smart Merge** (อัปเดตข้อมูล) ให้อัตโนมัติ ไม่เปลืองโควต้า

3. **ไม่ต้องสร้าง Summary (Auto-Summary)**
   - ตอนใช้คำสั่ง `save_context` ไม่จำเป็นต้องส่งพารามิเตอร์ `summary` มาก็ได้ ระบบ backend จะทำการสร้างสรุปให้เองจาก `content` (แต่ถ้ามีสรุปที่ชัดเจนอยู่แล้วก็ส่งมาได้เลย)

4. **การแนะนำ Context (Auto Context)**
   - หากผู้ใช้ถามถึงงานเก่าๆ ที่ไม่ได้อยู่ใน Active Contexts ล่าสุด ให้ AI ใช้ `auto_context` โดยใส่ keyword ของเรื่องที่คุย เพื่อหารายการงานเก่าๆ มาให้ผู้ใช้เลือกอย่างรวดเร็ว

### 👤 สำหรับผู้ใช้งาน (User Guide)

ในฝั่งของผู้ใช้นั้น **แทบไม่ต้องเรียนรู้อะไรใหม่เลย** เพียงแค่:

1. **ทำงานตามปกติ:** เมื่อคุณทำงานค้างไว้ในระบบหนึ่ง (เช่น Claude) แล้วจำเป็นต้องสลับไปใช้คอมพิวเตอร์อีกเครื่องที่มี Antigravity หรือไปคุยบน ChatGPT พอคุณเปิดแชทใหม่ AI จะรู้ทันทีว่าคุณทำอะไรค้างไว้จากข้อมูลที่ผูกมากับ Profile 
2. **ไม่โดนขัดจังหวะ:** การให้ AI บันทึกบริบท (`save_context`) เป็นแบบ **Auto-Approve** (ไม่ต้องกดยืนยัน) AI จึงสามารถแอบเก็บบันทึกงานของคุณไว้เบื้องหลังได้ตลอดเวลาโดยไม่ขัดจังหวะการทำงาน
3. **Pin งานสำคัญ:** หากมีบางเรื่องที่คุณทำค้างอยู่และสำคัญมาก คุณสามารถสั่งให้ AI "Pin บริบทนี้ให้หน่อย" (จำกัดสูงสุด 3 อัน) งานนั้นจะติดตัวคุณไปทุกแพลตฟอร์มเสมอจนกว่าคุณจะสั่ง Unpin
4. **ลืมเรื่องรกรุงรังไปได้เลย:** ระบบมี **Auto-Archive** หากคุณสร้างบริบทเปิดใช้งานเกิน 20 อัน ระบบจะนำอันที่เก่าที่สุดเก็บเข้ากรุให้เองโดยอัตโนมัติ ไม่ต้องคอยตามลบ

---
