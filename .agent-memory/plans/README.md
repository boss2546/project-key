# 📝 Plans Folder

> Plans สำหรับ feature แต่ละตัว — เขียนโดย แดง (นักวางแผน), อ่านโดย เขียว (นักพัฒนา) และ ฟ้า (นักตรวจสอบ)

---

## 📋 Naming Convention

```
plans/
├── README.md                       ← ไฟล์นี้
├── [feature-name].md               ← Plan ปัจจุบัน
└── archive/                        ← Plans เก่าที่ done แล้ว
    ├── 2026-04-29-export-json.md
    └── 2026-04-30-user-profile.md
```

ใช้ `kebab-case` ใน filename เช่น:
- `export-json.md`
- `password-reset.md`
- `mcp-tool-newchat.md`

---

## 📐 Template (แดงใช้)

```markdown
# Plan: [Feature Name]

**Author:** แดง (Daeng)
**Date:** YYYY-MM-DD
**Status:** draft / approved / in-progress / done

---

## 🎯 Goal
[อะไรคือเป้าหมาย, ใครคือผู้ใช้, ทำเสร็จแล้วได้อะไร]

## 📚 Context
[ทำไมต้องทำ, เกี่ยวข้องกับอะไรเดิม, decisions ก่อนหน้า]

## 📁 Files to Create / Modify

### Backend
- [ ] `backend/xxx.py` (modify) — เพิ่มฟังก์ชัน A, B
- [ ] `backend/yyy.py` (create) — module ใหม่สำหรับ Z

### Frontend
- [ ] `legacy-frontend/index.html` (modify) — เพิ่ม element X
- [ ] `legacy-frontend/app.js` (modify) — handler

### Tests (สำหรับฟ้า)
- [ ] `_test_xxx.py` (create) — test cases

## 📡 API Changes

### POST /api/xxx
**Auth:** Required (JWT)

**Request:**
```json
{
  "field1": "string",
  "field2": "number"
}
```

**Response 200:**
```json
{
  "result": "..."
}
```

**Errors:**
- 400 `VALIDATION_ERROR` — field1 missing
- 401 `UNAUTHORIZED` — no token
- 500 `INTERNAL_ERROR` — server fail

## 💾 Data Model Changes
[ถ้ามี — schema additions, migrations needed]

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Backend
1. แก้ `backend/xxx.py`:
   - เพิ่ม function `do_thing(arg1, arg2) -> Result`
   - Validate input ด้วย ...
   - Call existing `helper_func()` to get ...
   - Return ...
2. ลงทะเบียน route ใน `main.py`

### Step 2: Frontend
1. แก้ `legacy-frontend/app.js`:
   - เพิ่ม async function `handleX()`
   - Call API ด้วย fetch
   - Update DOM เมื่อ response กลับ

### Step 3: Verify
- เปิด browser → ลอง flow
- เช็คว่า response ถูก format

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. User login → call POST /api/xxx with valid input → expect 200 + correct result

### Validation Errors
- field1 missing → 400 VALIDATION_ERROR
- field2 not number → 400 VALIDATION_ERROR

### Auth Errors
- No token → 401
- Expired token → 401

### Edge Cases
- field1 = empty string
- field1 = very long string (>1000 chars)
- field2 = 0, negative number, very large number

## ✅ Done Criteria
- [ ] โค้ดทำงานได้ตาม goal
- [ ] Tests ผ่านทั้งหมด (≥ 80% coverage)
- [ ] api-spec.md updated
- [ ] data-models.md updated (ถ้าเปลี่ยน schema)
- [ ] No security issues
- [ ] Convention ถูกต้อง

## ⚠️ Risks / Open Questions
- [risk + mitigation]
- [คำถามให้ user ตัดสินใจ]

## 📌 Notes for นักพัฒนา
[hints, gotchas, สิ่งที่ต้องระวัง]
```

---

## 🔄 Lifecycle ของ Plan

```
แดงเขียน plan (status: draft)
    ↓
User approve (status: approved)
    ↓
เขียว build (status: in-progress)
    ↓
ฟ้า review (still: in-progress)
    ↓
User merge (status: done)
    ↓
ย้ายไป archive/
```

---

## 📂 Archiving

เมื่อ feature done แล้ว:
1. เปลี่ยน status → `done`
2. ย้ายไฟล์ไป `plans/archive/[YYYY-MM-DD]-[name].md`
3. Update `pipeline-state.md` → state = `idle`
