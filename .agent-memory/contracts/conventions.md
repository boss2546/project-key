# 📐 Code Conventions

> มาตรฐานที่ทุก agent ต้องยึดถือ — ป้องกัน code drift

---

## Python (Backend)

### Style
- ใช้ **type hints** ทุก function
- ใช้ **f-strings** ไม่ใช้ `.format()` หรือ `%`
- Import ตามลำดับ: stdlib → third-party → local
- Function/variable: `snake_case`
- Class: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

### Comments / Docstrings
- **Comment + docstring เป็นภาษาไทย** (สำหรับ business logic)
- ตัวแปร / ชื่อฟังก์ชัน เป็นภาษาอังกฤษเสมอ
- Comment เฉพาะที่ "WHY" ไม่ใช่ "WHAT"

```python
# ❌ ไม่ดี — อธิบาย what
# วน loop ผ่าน files
for f in files:
    ...

# ✅ ดี — อธิบาย why
# เรียงจากใหญ่ไปเล็กเพราะ Stripe จะ rate-limit ถ้า batch ใหญ่ส่งหลังเล็ก
files.sort(key=lambda f: -f.size)
```

### Error Handling
- Validate input ที่ boundary (API endpoints) เสมอ
- Internal functions ไม่ต้อง defensive ถ้า caller validate แล้ว
- Error response format: `{ "error": { "code": "ERROR_CODE", "message": "..." } }`
- Error codes ใช้ `UPPER_SNAKE_CASE` เช่น `INVALID_TOKEN`, `FILE_NOT_FOUND`

### API Routes (FastAPI)
- Path: `/api/<resource>` หรือ `/api/<resource>/<action>`
- Method: REST conventions (GET / POST / PUT / DELETE)
- Auth: ใช้ dependency injection จาก `auth.py`
- Response models: ใช้ Pydantic models

---

## Frontend (Legacy HTML/JS)

### JavaScript
- ใช้ **ES6+** (const/let, arrow functions, async/await)
- ห้ามใช้ `var`
- ใช้ `fetch()` สำหรับ API calls
- Function: `camelCase`
- DOM IDs: `kebab-case`

### CSS
- ใช้ class-based selectors เป็นหลัก
- ห้ามใช้ `!important` ถ้าไม่จำเป็น
- ใช้ CSS variables สำหรับ theme colors

### HTML
- Semantic HTML5 tags (`<header>`, `<nav>`, `<main>`)
- Forms ต้องมี `<label>` เชื่อมกับ input
- Accessibility: aria-labels บนปุ่ม icon-only

---

## Git Commits

### รูปแบบ
```
<type>(<scope>): <description>

[optional body]

Author-Agent: <agent-name>
```

### Types
- `feat` — feature ใหม่
- `fix` — แก้ bug
- `refactor` — refactor (ไม่เปลี่ยน behavior)
- `test` — เพิ่ม/แก้ tests
- `docs` — เปลี่ยน docs/memory
- `chore` — งานทั่วไป

### Scopes ที่ใช้บ่อย
- `auth`, `billing`, `mcp`, `frontend`, `backend`, `db`, `tests`, `memory`

### ตัวอย่าง
```
feat(auth): add password reset endpoint

เพิ่ม POST /api/auth/reset-password
ส่ง email link ผ่าน Resend API
Token หมดอายุใน 1 ชั่วโมง

Author-Agent: แดง (Daeng)
```

---

## File / Folder Naming
- Python files: `snake_case.py`
- HTML/CSS/JS: `kebab-case.html`, `kebab-case.css`
- Markdown docs: `kebab-case.md` หรือ `UPPER_SNAKE_CASE.md` สำหรับ root docs
- Test files: `_test_<module>.py` หรือ `test_<module>.py`

---

## ภาษาในงาน

| ที่ไหน | ภาษา |
|--------|------|
| Code (vars, functions, classes) | English |
| Comments / Docstrings (business logic) | Thai |
| Comments (technical/algo) | English ก็ได้ |
| Error messages → user | Thai |
| Error codes (constants) | English UPPER_SNAKE_CASE |
| Git commit messages | Thai หรือ English (consistent ในแต่ละ commit) |
| Memory files | Thai เป็นหลัก |
| Communication ระหว่าง agents | Thai |

---

## Security
- **ห้าม commit:** `.env`, `.jwt_secret`, `.mcp_secret`, `*.db`, API keys
- **ห้าม log:** passwords, tokens, full credit card numbers
- **Validate:** ทุก user input ที่เข้า DB หรือ shell
- **SQL:** ใช้ parameterized queries (database.py ทำให้แล้ว — อย่า bypass)
