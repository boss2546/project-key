# 📋 Review Report Template (สำหรับฟ้า)

> ฟ้าใช้ template นี้เขียน review หลังตรวจ code ของเขียว
> Copy template → เพิ่มลงใน inbox/for-User.md หรือ inbox/for-เขียว.md (ถ้า needs changes)

---

## Template

```markdown
### MSG-NNN [PRIORITY] Review: [Feature Name]
**From:** ฟ้า
**Date:** YYYY-MM-DD HH:MM
**Plan:** plans/[feature].md
**Code by:** เขียว
**Verdict:** ✅ APPROVE / ⚠️ NEEDS_CHANGES / ❌ BLOCK
**Status:** 🔴 New

#### Tests Written
- tests/test_xxx.py — X test cases
  - test_happy_path ✓
  - test_validation_missing_field ✓
  - test_auth_no_token ✓
  - [...]
- All passed: X/X

#### Coverage
- Before: X%
- After: Y%

#### Issues Found

##### 🔴 Critical (block release)
- [ ] [BUG-001] [title]
  - File: backend/xxx.py:42
  - Problem: [description]
  - Suggested fix: [hint]

##### 🟠 High (should fix before merge)
- [ ] [BUG-002] ...

##### 🟡 Medium (nice to fix)
- [ ] [BUG-003] ...

##### 🟢 Low / Style
- [ ] [BUG-004] ...

#### Plan Compliance
- ✅ Files modified ตรงตาม plan
- ✅ API contract ตรงตาม spec
- ⚠️ [issue ถ้ามี]

#### Security Check
- ✅ No secrets in code
- ✅ Input validated at boundary
- ✅ SQL parameterized
- ⚠️ [issue ถ้ามี]

#### Convention Check
- ✅ Naming
- ✅ Type hints (Python)
- ✅ Comments
- ⚠️ [issue ถ้ามี]

#### Notes
[สิ่งที่ดี + ข้อเสนอแนะ + ปรับปรุงในอนาคต]

— ฟ้า
```

---

## วิธีใช้

### Verdict = APPROVE → ส่งให้ User
- เขียนใน `inbox/for-User.md` (สร้างถ้ายังไม่มี) หรือรายงานในแชทตรงๆ
- Update pipeline-state.md → state = `review_passed`

### Verdict = NEEDS_CHANGES → ส่งให้เขียว
- เขียนใน `inbox/for-เขียว.md` (section 🔴 New)
- Update pipeline-state.md → state = `review_needs_changes`
- เขียวอ่าน → แก้ → commit ใหม่ → ส่งกลับ ฟ้า re-review

### Verdict = BLOCK → ส่งให้ User + แดง
- เขียนใน `inbox/for-User.md` + อาจส่งให้แดงถ้า plan ผิด
- Update pipeline-state.md → state = `paused`
