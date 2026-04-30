# 💬 Messages From ฟ้า (Fah) — นักตรวจสอบ

> ฟ้าใช้ไฟล์นี้เขียน review reports และ bug reports
> Format: ข้อความใหม่อยู่ "บนสุด" (newest first)

---

## 📋 Review Report Template

```markdown
## [REVIEW-001] Feature: [name]
**Date:** YYYY-MM-DD HH:MM
**Plan:** plans/[feature].md
**Code by:** เขียว
**Verdict:** ✅ APPROVE / ⚠️ NEEDS_CHANGES / ❌ BLOCK

### Tests Written
- tests/test_xxx.py — X test cases
  - test_happy_path ✓
  - test_validation_missing_field ✓
  - test_auth_no_token ✓
  - [...]
- All passed: X/X

### Coverage
- Before: X%
- After: Y%

### Issues Found

#### 🔴 Critical (block release)
- [ ] [BUG-001] [title]
  - File: backend/xxx.py:42
  - Problem: [description]
  - Suggested fix: [hint]

#### 🟠 High (should fix before merge)
- [ ] [BUG-002] ...

#### 🟡 Medium (nice to fix)
- [ ] [BUG-003] ...

#### 🟢 Low / Style
- [ ] [BUG-004] ...

### Plan Compliance
- ✅ Files modified ตรงตาม plan
- ✅ API contract ตรงตาม spec
- ⚠️ [issue ถ้ามี]

### Security Check
- ✅ No secrets in code
- ✅ Input validated at boundary
- ✅ SQL parameterized
- ⚠️ [issue ถ้ามี]

### Notes
[สิ่งที่ดี + ข้อเสนอแนะทั่วไป]

— ฟ้า
```

---

## 📨 Reviews / Reports

_ยังไม่มี — รอ feature แรกที่เขียวทำเสร็จ_
