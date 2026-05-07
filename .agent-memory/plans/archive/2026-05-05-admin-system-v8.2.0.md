# Plan: Admin System v8.2.0

**Author:** แดง (Daeng)
**Date:** 2026-05-05
**Status:** draft — pending user approval
**Target version:** v8.1.0 (master HEAD `f8d25e7`) → v8.2.0
**Estimated effort:** เขียว ~2-3 วัน + ฟ้า ~1 วัน
**Pipeline state:** `plan_pending_approval`

---

## 🎯 Goal

เพิ่มหน้าแอดมินแยก (`/admin`) สำหรับเจ้าของระบบใช้จัดการผู้ใช้ ปลด/ลดแพ็กเกจ และดูประวัติการกระทำของระบบ — โดยใช้ของที่มีอยู่ในระบบให้มากที่สุด ไม่เพิ่มความซับซ้อนเกินจำเป็น

**ผู้ใช้ปลายทาง:** Admin (ตอนนี้คือ founder `bossok2546@gmail.com` + แอดมินอื่นที่ promote runtime)

**ทำเสร็จแล้วได้อะไร:**
1. หน้า `/admin` แยกจาก `/app` — เห็น stats, users table, audit log
2. แอดมินเปลี่ยน plan ของ user ได้ (free / starter / admin) ผ่าน UI ทันที (ไม่ต้อง redeploy)
3. แอดมินรีเซ็ตรหัสผ่าน user ได้ (ตั้งรหัสใหม่ + show 1 ครั้ง)
4. แอดมิน deactivate / promote user ได้
5. ทุก action ของแอดมินถูก log ลง `audit_logs` table + ดูย้อนหลังได้ผ่าน UI

---

## 📚 Context

### State ปัจจุบันที่กระทบ scope นี้

**1. ระบบ admin primitive ที่มีอยู่แล้ว** (กระจาย ยังไม่รวมศูนย์):
- `ADMIN_PASSWORD` env ([config.py:66-74](../../backend/config.py#L66-L74)) — fail-closed, ใช้ override MCP disabled tool
- `ADMIN_EMAILS` env ([config.py:79-83](../../backend/config.py#L79-L83)) — comma-list → ผ่าน `_effective_plan()` → "admin"
- `PLAN_LIMITS["admin"]` ([plan_limits.py:51-62](../../backend/plan_limits.py#L51-L62)) — quota 999999 ทุก field
- `_effective_plan()` ([plan_limits.py:72-102](../../backend/plan_limits.py#L72-L102)) — admin override Stripe status
- `audit_logs` table ([database.py:442-451](../../backend/database.py#L442-L451)) — มี schema, ใช้แล้ว 4 events (`plan_changed`, `data_unlocked`, `subscription_status_changed`, `downgrade_completed`)
- `log_audit()` helper ([plan_limits.py:478-496](../../backend/plan_limits.py#L478-L496))
- `lock_excess_data()` / `unlock_data_for_plan()` ([plan_limits.py:363-471](../../backend/plan_limits.py#L363-L471))

**2. Stripe webhook = source of truth** ([billing.py:210-432](../../backend/billing.py#L210-L432)):
- `checkout.session.completed` → set `plan="starter"` + `subscription_status="starter_active"` + unlock data
- `customer.subscription.deleted` → set `plan="free"` + lock excess data
- `customer.subscription.updated` → sync period dates + status

**3. Password reset ปัจจุบัน** ([auth.py:263-349](../../backend/auth.py#L263-L349)):
- User-driven: `request_password_reset()` → ส่ง email link (Resend) → JWT 15 นาที → `reset_password()` → bcrypt hash + auto-login
- Email template TH/EN ([email_service.py:29-92](../../backend/email_service.py#L29-L92))

### User decisions (จาก scoping discussion 2026-05-05)

| # | ตัวเลือก | คำตอบ | ผลกระทบ |
|---|---|---|---|
| 1 | Admin storage | **B — เก็บใน DB** | เพิ่ม `users.is_admin` column + UI promote/demote runtime |
| 2 | Password reset by admin | **B — admin ตั้งรหัสใหม่ + show 1 ครั้ง** | ไม่ใช้ email reset link, ต้อง endpoint ใหม่ |
| 3 | Plan downgrade ของ user ที่มี Stripe active | **A — ห้าม + warning** | UI block ปุ่ม + แสดงข้อความให้ไป Stripe Portal |
| 4 | Audit log viewer | **เอา** | UI section ใหม่ + endpoint อ่าน `audit_logs` |

### Architectural decisions (baked-in สำหรับ "ง่ายๆ ไม่ซับซ้อน")

- **3 plans เท่านั้น:** `free` / `starter` / `admin` — ไม่เพิ่ม tier ใหม่
- **No multi-admin role:** ทุก admin มีสิทธิ์เท่ากัน (ไม่มี super-admin / read-only / support tier)
- **No 2FA / IP allowlist:** ใช้ JWT + admin role check พอ (เพิ่มภายหลังถ้า public scale)
- **No impersonate / login-as-user:** ไม่ทำ feature ที่ admin login เป็น user คนอื่น
- **No bulk action / CSV export:** action ทีละ user
- **No email notification ถึง user:** เปลี่ยน plan / password / deactivate → ไม่ส่ง email อัตโนมัติ (admin บอก user เอง)
- **JWT revocation = ไม่ทำ:** reset password / deactivate ไม่ kill session ทันที — รอ JWT หมดอายุ 24 ชม. (acceptable trade-off)

---

## 📁 Files to Create / Modify

### Backend (5 files)

- [ ] `backend/database.py` (modify) — เพิ่ม `User.is_admin` + `User.manual_plan_override` columns + idempotent migration + seed bootstrap จาก `ADMIN_EMAILS`
- [ ] `backend/auth.py` (modify) — เพิ่ม `require_admin` FastAPI dependency + `admin_set_user_password()` helper
- [ ] `backend/admin.py` (CREATE — ~250 บรรทัด) — module ใหม่ ฟังก์ชัน:
  - `get_admin_stats()` — dashboard counts
  - `list_users(query, plan_filter, page, page_size)` — paginated user list
  - `get_user_detail(user_id)` — user + usage + Stripe info
  - `change_user_plan(admin_user, target_user_id, new_plan, reason)` — Stripe-aware guard
  - `reset_user_password(admin_user, target_user_id, new_password)` — bcrypt + audit
  - `set_user_active(admin_user, target_user_id, is_active)` — toggle + self-guard
  - `set_user_admin(admin_user, target_user_id, is_admin)` — promote/demote + self-guard
  - `list_audit_logs(filter_event_type, filter_user_id, limit, offset)` — paginated read
- [ ] `backend/main.py` (modify) — register 10 admin endpoints + `/admin` HTML serve route
- [ ] `backend/plan_limits.py` (modify) — update `_effective_plan()` ลำดับใหม่: `user.is_admin` > `ADMIN_EMAILS` > Stripe status

### Frontend (3 files)

- [ ] `legacy-frontend/admin.html` (CREATE — ~400 บรรทัด) — standalone admin shell
  - **โหลด `shared.css` + `styles.css`** (เหมือน app.html — reuse design tokens + universal atoms)
  - Header (logo + admin email + logout)
  - 3 tabs: Dashboard / Users / Audit Log
  - Modals — ใช้ `.modal-overlay` + `.modal` patterns ที่มีอยู่ใน shared.css (Change Plan / Reset Password / Confirm Deactivate / Confirm Promote / Show Password One-Time)
- [ ] `legacy-frontend/admin.js` (CREATE — ~500 บรรทัด) — admin UI logic
  - Auth guard (redirect ไป `/` ถ้าไม่ admin)
  - Fetch wrapper (สั้นกว่า authFetch ของ app.js — admin ไม่ต้อง language toggle / debounce / hideLoadingOverlay)
  - 3 tab renderers (stats / users / audit)
  - Modal handlers (ใช้ class `.hidden` toggle ตาม pattern เดิม)
  - **Toast = reuse `.toast` + `#toast-container`** จาก shared.css (z-index 11000, slideUp anim) — admin.js แค่ inject DOM, ไม่ต้อง redefine CSS
- [ ] `legacy-frontend/styles.css` (modify) — เพิ่ม admin-specific classes (~80 บรรทัด section ใหม่ — สั้นกว่าเดิมเพราะ reuse shared.css)
  - `.admin-shell` / `.admin-header` / `.admin-tabs` / `.admin-tab` / `.admin-tab-content`
  - `.admin-stats-grid` / `.admin-stat-card`
  - `.admin-users-table` / `.admin-user-actions` / `.admin-users-pagination`
  - `.admin-audit-list` / `.admin-audit-row`
  - `.admin-warning-banner` / `.admin-password-display`
  - `.badge-free` / `.badge-starter` / `.badge-admin` (modifier ของ `.badge` ที่มีอยู่ที่ styles.css:359)
  - **ห้าม** redefine `.modal-*` / `.toast` / `.btn-*` / `.form-input` — ใช้ของ shared.css ทั้งหมด

### Tests (1 file สำหรับฟ้า)

- [ ] `tests/test_admin.py` (CREATE — ~30 cases) — endpoint tests + permission gate + Stripe collision

### Frontend integration (modify)

- [ ] `legacy-frontend/landing.js` (modify) — หลัง login สำเร็จ ตรวจ `user.is_admin` → redirect `/admin` หรือ `/app`
- [ ] `legacy-frontend/app.js` (modify, optional) — แสดง "Admin Panel" link ใน sidebar footer ถ้า `is_admin === true`

---

## 📡 API Changes

### Auth check

#### `GET /api/admin/me`
**Auth:** Required (JWT) + Admin role

**Response 200:**
```json
{
  "id": "abc123def456",
  "email": "boss@example.com",
  "name": "Boss",
  "is_admin": true,
  "effective_plan": "admin"
}
```

**Errors:**
- `401 UNAUTHORIZED` — no token / expired
- `403 NOT_ADMIN` — token valid แต่ `is_admin=False` และ email ไม่อยู่ใน ADMIN_EMAILS

---

### Dashboard stats

#### `GET /api/admin/stats`
**Auth:** Admin

**Response 200:**
```json
{
  "users": {
    "total": 42,
    "by_plan": { "free": 30, "starter": 10, "admin": 2 },
    "active": 40,
    "inactive": 2,
    "signups_today": 3,
    "signups_this_week": 12,
    "signups_this_month": 35
  },
  "files": {
    "total": 567,
    "total_storage_mb": 4521.3
  },
  "subscriptions": {
    "starter_active": 8,
    "starter_past_due": 1,
    "starter_canceled": 1
  },
  "line": {
    "feature_available": true,
    "linked_users": 5,
    "push_quota_used": 23,
    "push_quota_limit": 200,
    "push_quota_percent": 11.5
  },
  "system": {
    "app_version": "8.2.0",
    "db_size_mb": 2.4,
    "checked_at": "2026-05-05T14:30:00Z"
  }
}
```

**Errors:** `401`, `403 NOT_ADMIN`

---

### User list + detail

#### `GET /api/admin/users`
**Auth:** Admin

**Query params:**
- `q` (string, optional) — search by email substring (case-insensitive)
- `plan` (enum, optional) — `"free"` | `"starter"` | `"admin"` | `"inactive"` (composite filter)
- `page` (int, default 1, min 1)
- `page_size` (int, default 20, min 1, max 100)

**Response 200:**
```json
{
  "users": [
    {
      "id": "abc123",
      "email": "user@example.com",
      "name": "User One",
      "is_admin": false,
      "is_active": true,
      "plan": "starter",
      "subscription_status": "starter_active",
      "effective_plan": "starter",
      "manual_plan_override": false,
      "stripe_customer_id": "cus_xxx",
      "stripe_subscription_id": "sub_xxx",
      "current_period_end": "2026-06-05T00:00:00Z",
      "created_at": "2026-04-01T10:00:00Z",
      "file_count": 45,
      "storage_mb": 234.5,
      "last_seen_at": null
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Errors:** `401`, `403 NOT_ADMIN`, `400 INVALID_PAGE` (page < 1 or page_size out of range)

---

#### `GET /api/admin/users/{user_id}`
**Auth:** Admin

**Response 200:**
```json
{
  "user": {
    "id": "abc123",
    "email": "user@example.com",
    "name": "User One",
    "is_admin": false,
    "is_active": true,
    "plan": "starter",
    "subscription_status": "starter_active",
    "effective_plan": "starter",
    "manual_plan_override": false,
    "stripe_customer_id": "cus_xxx",
    "stripe_subscription_id": "sub_xxx",
    "current_period_start": "2026-05-05T00:00:00Z",
    "current_period_end": "2026-06-05T00:00:00Z",
    "cancel_at_period_end": false,
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-05-05T14:30:00Z",
    "google_sub": "1234567890",
    "has_password": true,
    "storage_mode": "managed"
  },
  "usage": {
    "context_packs": { "used": 12, "limit": 50 },
    "files": { "used": 45, "limit": 500 },
    "storage_mb": { "used": 234.5, "limit": 10240 },
    "ai_summaries": { "used": 23, "limit": 1000 },
    "exports": { "used": 5, "limit": 3000 },
    "refreshes": { "used": 0, "limit": 100 }
  },
  "stripe_active": true,
  "can_admin_downgrade": false,
  "downgrade_block_reason": "STRIPE_ACTIVE_SUBSCRIPTION"
}
```

**Errors:** `401`, `403 NOT_ADMIN`, `404 USER_NOT_FOUND`

---

### Change plan

#### `PUT /api/admin/users/{user_id}/plan`
**Auth:** Admin

**Request:**
```json
{
  "plan": "starter",
  "reason": "Manual upgrade for beta tester (พ.ค. 2026)"
}
```

**Response 200:**
```json
{
  "status": "ok",
  "user_id": "abc123",
  "old_plan": "free",
  "new_plan": "starter",
  "manual_override": true,
  "unlocked_packs": 0,
  "unlocked_files": 0,
  "audit_log_id": 105
}
```

**Errors:**
- `400 INVALID_PLAN` — plan ≠ "free" / "starter" / "admin"
- `400 EMPTY_REASON` — reason missing or whitespace only
- `401`, `403 NOT_ADMIN`
- `404 USER_NOT_FOUND`
- `409 STRIPE_ACTIVE_SUBSCRIPTION` — user มี `stripe_subscription_id` + `subscription_status` ใน {`starter_active`, `starter_past_due`} และ admin พยายาม downgrade เป็น free
  ```json
  {
    "error": {
      "code": "STRIPE_ACTIVE_SUBSCRIPTION",
      "message": "ผู้ใช้นี้มี Stripe subscription กำลังใช้งาน — ให้ผู้ใช้ไปกดยกเลิกที่ Stripe Customer Portal ของตัวเองก่อน",
      "hint": "After cancellation, Stripe webhook will downgrade this user to free automatically."
    }
  }
  ```
- `409 CANNOT_DEMOTE_SELF` — admin พยายามเปลี่ยน plan ของตัวเองจาก admin → free/starter (ป้องกัน lock-out)

**Behavior หลัง success:**
- ถ้า `new_plan == "starter"` (manual upgrade): set `manual_plan_override = True` → Stripe webhook จะ skip user นี้ (ดู [Risks #1](#risks))
- ถ้า `new_plan == "free"` (manual downgrade ของ user ที่ไม่มี Stripe sub): set `manual_plan_override = False` (กลับไปใช้ Stripe sync)
- ถ้า `new_plan == "admin"`: ตั้ง `is_admin = True` ด้วย (admin = role ≠ plan แต่เพื่อ UX แสดงรวม)
- รัน `unlock_data_for_plan()` ถ้า upgrade
- รัน `lock_excess_data()` ถ้า downgrade (free)
- เขียน `audit_logs` event = `admin_changed_plan` พร้อม old/new + reason + `triggered_by={admin_email}`

---

### Reset password

#### `POST /api/admin/users/{user_id}/reset-password`
**Auth:** Admin

**Request:**
```json
{
  "new_password": "TempPass!2026",
  "reason": "User โทรมาแจ้งลืมรหัส (LINE @somchai)"
}
```

**Response 200:**
```json
{
  "status": "ok",
  "user_id": "abc123",
  "user_email": "user@example.com",
  "new_password_shown_once": "TempPass!2026",
  "warning": "รหัสนี้แสดงครั้งเดียว — ส่งให้ user ทันที. ไม่บันทึกลงระบบ.",
  "audit_log_id": 106
}
```

**Errors:**
- `400 PASSWORD_TOO_SHORT` — `< 6 chars` (match validation เดิม)
- `400 EMPTY_REASON`
- `401`, `403 NOT_ADMIN`
- `404 USER_NOT_FOUND`
- `409 GOOGLE_ONLY_USER` — `user.password_hash IS NULL` + `user.google_sub IS NOT NULL` (สมัครผ่าน Google เท่านั้น)
  ```json
  {
    "error": {
      "code": "GOOGLE_ONLY_USER",
      "message": "ผู้ใช้นี้สมัครด้วย Google เท่านั้น — ไม่มีรหัสผ่านในระบบ ให้ผู้ใช้ login ผ่านปุ่ม Sign in with Google",
      "hint": "Set a password for this Google user first via /api/admin/users/{id}/set-password (not implemented in v8.2.0 — defer)"
    }
  }
  ```

**Behavior:**
- bcrypt hash ใหม่ + ทับ `password_hash`
- `audit_logs` event = `admin_reset_password` + `triggered_by={admin_email}` + `new_value=user_email` + `old_value=reason`
- **ไม่** เก็บรหัสใหม่ในระบบ (return ครั้งเดียว, ไม่ log raw password)
- **ไม่** revoke JWT ของ user เดิม (acceptable — JWT 24 ชม. หมดอายุเองตามปกติ; ถ้าจะ kill session ต้องทำ revocation list = scope ภายหลัง)
- **ไม่** ส่ง email แจ้ง user (admin บอกเอง)

---

### Toggle active

#### `PUT /api/admin/users/{user_id}/active`
**Auth:** Admin

**Request:**
```json
{
  "is_active": false,
  "reason": "TOS violation — uploaded copyrighted material"
}
```

**Response 200:**
```json
{
  "status": "ok",
  "user_id": "abc123",
  "is_active": false,
  "audit_log_id": 107
}
```

**Errors:**
- `400 EMPTY_REASON`
- `401`, `403 NOT_ADMIN`
- `404 USER_NOT_FOUND`
- `409 CANNOT_DEACTIVATE_SELF` — admin deactivate ตัวเอง

**Behavior:**
- `audit_logs` event = `admin_deactivated_user` หรือ `admin_reactivated_user`
- User ที่ถูก deactivate → login ครั้งถัดไป `get_current_user()` จะ raise 401 "User not found or deactivated" ([auth.py:198-202](../../backend/auth.py#L198-L202))
- JWT เดิมยังใช้ได้จนหมดอายุ ([same trade-off เหมือน reset password](#))

---

### Promote / Demote admin

#### `PUT /api/admin/users/{user_id}/admin`
**Auth:** Admin

**Request:**
```json
{
  "is_admin": true,
  "reason": "Hire new support staff @somchai"
}
```

**Response 200:**
```json
{
  "status": "ok",
  "user_id": "abc123",
  "is_admin": true,
  "audit_log_id": 108
}
```

**Errors:**
- `400 EMPTY_REASON`
- `401`, `403 NOT_ADMIN`
- `404 USER_NOT_FOUND`
- `409 CANNOT_DEMOTE_SELF` — admin demote ตัวเอง
- `409 LAST_ADMIN_GUARD` — ถ้า demote คนนี้แล้วระบบจะไม่มี admin เหลือเลย (ทั้ง DB + ADMIN_EMAILS env)

**Behavior:**
- `audit_logs` event = `admin_promoted` หรือ `admin_demoted`
- หลัง promote: user คนนั้น login ครั้งหน้า `_effective_plan()` return "admin" → quota 999999

---

### Audit log viewer

#### `GET /api/admin/audit-logs`
**Auth:** Admin

**Query params:**
- `event_type` (string, optional) — filter เช่น `admin_changed_plan`, `plan_changed`
- `user_id` (string, optional) — filter เฉพาะ user คนนี้
- `triggered_by` (string, optional) — filter `system` / `stripe_webhook` / `{admin_email}`
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)

**Response 200:**
```json
{
  "logs": [
    {
      "id": 105,
      "user_id": "abc123",
      "user_email": "user@example.com",
      "event_type": "admin_changed_plan",
      "old_value": "free",
      "new_value": "starter",
      "triggered_by": "boss@example.com",
      "created_at": "2026-05-05T14:30:00Z"
    },
    {
      "id": 104,
      "user_id": "def456",
      "user_email": "u2@example.com",
      "event_type": "plan_changed",
      "old_value": "free",
      "new_value": "starter",
      "triggered_by": "stripe_webhook",
      "created_at": "2026-05-05T13:00:00Z"
    }
  ],
  "total": 230,
  "limit": 50,
  "offset": 0
}
```

**Errors:** `401`, `403 NOT_ADMIN`, `400 INVALID_LIMIT`

**Note:** `user_email` ต้อง JOIN `audit_logs.user_id` → `users.email` (ถ้า user ถูกลบไป → return `null`)

---

### HTML page route

#### `GET /admin`
**Auth:** None ที่ server (frontend JS guard เช็คเอง — ถ้าไม่ admin redirect `/`)

**Response:** `admin.html` (no-cache headers — match pattern จาก `_serve_html()` [main.py:2868-2875](../../backend/main.py#L2868-L2875))

---

## 💾 Data Model Changes

### Schema additions ใน `users` table

```sql
-- v8.2.0 Migration — Admin role + manual plan override
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN manual_plan_override BOOLEAN DEFAULT 0;
```

**Default = 0/False:** user ทุกคน (ทั้งเดิมและใหม่) ไม่ใช่ admin + ไม่มี override จนกว่าจะถูกตั้ง

### Idempotent migration block ใน `init_db()` ([database.py:741-755](../../backend/database.py#L741-L755))

วาง block ใหม่ต่อจาก v8.1.0 google_sub migration:

```python
# v8.2.0 Migration — Admin system: is_admin + manual_plan_override
cursor = await db.execute("PRAGMA table_info(users)")
user_cols_v8_2 = [row[1] for row in await cursor.fetchall()]
if "is_admin" not in user_cols_v8_2:
    await db.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    migrated = True
    print("  → Added: users.is_admin (v8.2.0 — Admin system)")
if "manual_plan_override" not in user_cols_v8_2:
    await db.execute("ALTER TABLE users ADD COLUMN manual_plan_override BOOLEAN DEFAULT 0")
    migrated = True
    print("  → Added: users.manual_plan_override (v8.2.0)")

# v8.2.0 Bootstrap — seed is_admin from ADMIN_EMAILS env (one-shot, safe to re-run)
# Why: คนแรกใช้งานต้องเป็น admin ได้จาก env (ไม่งั้นจะไม่มีใคร login เข้าหน้า /admin ได้)
# หลังจากนี้ admin ใหม่ถูก promote ผ่าน UI — ADMIN_EMAILS ยังใช้เป็น fallback
try:
    from .config import ADMIN_EMAILS
    if ADMIN_EMAILS:
        for email in ADMIN_EMAILS:
            await db.execute(
                "UPDATE users SET is_admin = 1 WHERE LOWER(email) = ? AND is_admin = 0",
                (email.lower(),),
            )
        print(f"  → Seeded is_admin=1 for {len(ADMIN_EMAILS)} ADMIN_EMAILS entries")
except Exception as e:
    print(f"  ⚠️ ADMIN_EMAILS bootstrap skipped: {e}")
```

### SQLAlchemy model update ใน `User` class

```python
# v8.2.0 — Admin system
is_admin = Column(Boolean, default=False)
# True = admin (ผ่าน UI promote หรือ ADMIN_EMAILS bootstrap). Lookup ลำดับใน _effective_plan:
# user.is_admin (DB) > email in ADMIN_EMAILS (env, legacy fallback) > Stripe status
manual_plan_override = Column(Boolean, default=False)
# True = admin ตั้ง plan ตรงๆ (manual upgrade เช่น beta tester) → Stripe webhook ต้อง SKIP user นี้
# False (default) = Stripe webhook overwrite ตามปกติ
```

### Audit log event types ใหม่

ไม่ต้องเปลี่ยน schema (column `event_type` เป็น free-form string) — แค่เพิ่ม convention:

| Event type | ผู้บันทึก | old_value | new_value | triggered_by |
|---|---|---|---|---|
| `admin_changed_plan` | admin via UI | old plan | new plan | admin_email |
| `admin_reset_password` | admin via UI | reason | user_email | admin_email |
| `admin_deactivated_user` | admin via UI | reason | user_email | admin_email |
| `admin_reactivated_user` | admin via UI | reason | user_email | admin_email |
| `admin_promoted` | admin via UI | reason | user_email | admin_email |
| `admin_demoted` | admin via UI | reason | user_email | admin_email |

(เดิมมีแล้ว: `plan_changed`, `data_unlocked`, `subscription_status_changed`, `downgrade_completed`, `file_locked`, `usage_limit_reached` — admin ใช้ event_type ใหม่เพื่อแยกจาก system/stripe events)

### Stripe webhook update — skip ถ้า manual override

ใน `_handle_subscription_created()` / `_handle_subscription_updated()` / `_handle_payment_succeeded()` ([billing.py:268-432](../../backend/billing.py#L268-L432)):

```python
# v8.2.0 — respect manual plan override by admin
if getattr(user, "manual_plan_override", False):
    logger.info(f"Stripe webhook skipped for user {user.id} (manual_plan_override=True)")
    return  # หรือ continue ไม่ทำอะไรกับ plan/status — แต่ยัง log + update period dates ปกติ
```

**Decision:** webhook handlers ที่จะแก้ `user.plan` / `user.subscription_status` ต้องเช็ค flag นี้ก่อน. ใน `_handle_subscription_deleted()` ก็เช่นกัน (ถ้า admin upgrade manual แล้ว Stripe ส่ง deletion event มาเพราะ user ไม่ได้ใช้ Stripe → ต้อง skip).

**ข้อยกเว้น:** `_handle_checkout_completed()` — ถ้า user จ่ายเงินจริง webhook นี้ควร override `manual_plan_override` เป็น False (Stripe = source of truth ทันทีที่ user จ่าย).

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — Backend Foundation (วันที่ 1, ~4 ชม.)

#### Step 1.1: DB schema + migration

แก้ `backend/database.py`:
1. ใน class `User`: เพิ่ม 2 columns ตามที่ระบุใน [Data Model](#data-model-changes) (วางต่อจาก `google_sub`)
2. ใน `init_db()`: วาง migration block ตามที่ระบุ (ต่อจาก v8.1.0 block ที่ line ~744)
3. เทสต์ local: ลบ `projectkey.db` → start app → ดู log "Added: users.is_admin (v8.2.0)"
4. เทสต์ idempotency: restart app → ต้องเห็น "Schema up to date — no migration needed"

#### Step 1.2: Update `_effective_plan()`

แก้ `backend/plan_limits.py:72-102`:
1. เปลี่ยนลำดับการ check:
   ```python
   def _effective_plan(user) -> str:
       # v8.2.0 — Admin from DB column (highest priority)
       if getattr(user, "is_admin", False):
           return "admin"

       # Legacy fallback — ADMIN_EMAILS env (kept for ops/break-glass)
       email = (getattr(user, "email", "") or "").lower()
       if email:
           try:
               from .config import ADMIN_EMAILS
               if email in ADMIN_EMAILS:
                   return "admin"
           except ImportError:
               pass

       # Stripe-driven status
       status = getattr(user, "subscription_status", "free") or "free"
       # ... (ของเดิม ไม่เปลี่ยน)
   ```
2. ตรวจให้แน่ใจว่า `user.plan` field (column ปัจจุบัน) ไม่ขัดแย้ง — มันคือ "Stripe-derived plan" ไม่ใช่ effective plan, OK

#### Step 1.3: `require_admin` dependency

แก้ `backend/auth.py` — เพิ่มฟังก์ชันต่อจาก `get_optional_user()`:

```python
async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency — ตรวจว่า user เป็น admin จริง.

    ผ่านเฉพาะถ้า:
      1. JWT valid (จาก get_current_user) + is_active=True
      2. user.is_admin == True (DB) OR email ใน ADMIN_EMAILS env

    Use as: current_admin: User = Depends(require_admin)
    """
    is_admin_db = bool(getattr(current_user, "is_admin", False))
    email = (current_user.email or "").lower()
    is_admin_env = False
    try:
        from .config import ADMIN_EMAILS
        is_admin_env = email in ADMIN_EMAILS
    except ImportError:
        pass

    if not (is_admin_db or is_admin_env):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "NOT_ADMIN", "message": "Admin access required"}},
        )
    return current_user
```

#### Step 1.4: Stripe webhook respect `manual_plan_override`

แก้ `backend/billing.py`:
1. `_handle_subscription_created()` — เพิ่มตอนต้น (ก่อน `user.stripe_subscription_id = ...`):
   ```python
   if getattr(user, "manual_plan_override", False):
       logger.info(f"Stripe webhook subscription.created skipped (manual_plan_override) user={user.id}")
       return
   ```
2. `_handle_subscription_updated()` — เพิ่ม guard เดียวกัน
3. `_handle_subscription_deleted()` — เพิ่ม guard เดียวกัน
4. `_handle_payment_succeeded()` — เพิ่ม guard เดียวกัน
5. `_handle_payment_failed()` — เพิ่ม guard เดียวกัน
6. `_handle_checkout_completed()` — **ไม่ต้อง guard** (user จ่ายเงินจริง = ต้อง upgrade) แต่เพิ่ม `user.manual_plan_override = False` (ล้าง override ถ้ามี เพราะ Stripe เป็น truth แล้ว)

#### Step 1.5: Pydantic models ใน `main.py`

เพิ่มต่อจาก existing models (ก่อน `# ═══ FILE APIs ═══`):

```python
# ═══════════════════════════════════════════
# v8.2.0 — Admin Request Models
# ═══════════════════════════════════════════

class AdminChangePlanRequest(BaseModel):
    plan: str  # validated ใน endpoint
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


class AdminResetPasswordRequest(BaseModel):
    new_password: str
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()


class AdminToggleRequest(BaseModel):
    """ใช้กับ /active และ /admin endpoints (boolean flag + reason)."""
    value: bool  # is_active หรือ is_admin
    reason: str

    @field_validator("reason")
    @classmethod
    def _check_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("EMPTY_REASON")
        return v.strip()
```

---

### Phase 2 — Backend Admin Module (วันที่ 1-2, ~5 ชม.)

#### Step 2.1: Create `backend/admin.py`

ไฟล์ใหม่ ~250 บรรทัด มีโครงสร้างนี้:

```python
"""Admin module for Personal Data Bank (PDB) — v8.2.0.

จัดการ user, plan, password, audit log สำหรับเจ้าของระบบ + ทีม.
ทุกฟังก์ชันใน module นี้ต้องผ่าน require_admin dependency แล้ว — ไม่เช็ค role ซ้ำ.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    User, File, ContextPack, AuditLog, UsageLog,
)
from .plan_limits import (
    _effective_plan, get_limits, lock_excess_data, unlock_data_for_plan,
    log_audit, get_file_count, get_storage_used_mb, get_pack_count,
    get_monthly_summary_count, get_monthly_export_count, get_monthly_refresh_count,
)
from .auth import hash_password

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 1. Stats / Dashboard
# ═══════════════════════════════════════════

async def get_admin_stats(db: AsyncSession) -> dict:
    """Aggregate dashboard counts for /admin home page."""
    # Total users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # By plan (effective — ต้อง compute เพราะ admin ผ่าน is_admin หรือ ADMIN_EMAILS)
    all_users = (await db.execute(select(User))).scalars().all()
    by_plan = {"free": 0, "starter": 0, "admin": 0}
    active_count = 0
    for u in all_users:
        if u.is_active:
            active_count += 1
        eff = _effective_plan(u)
        if eff in by_plan:
            by_plan[eff] += 1

    # Signups (UTC)
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())  # Monday
    month_start = today_start.replace(day=1)

    signups_today = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )).scalar() or 0
    signups_week = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )).scalar() or 0
    signups_month = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )).scalar() or 0

    # Files + storage
    total_files = (await db.execute(select(func.count(File.id)))).scalar() or 0
    # Storage = sum file sizes from disk (best-effort — large user count อาจช้า)
    storage_total_mb = 0.0
    file_paths = (await db.execute(select(File.raw_path))).fetchall()
    import os as _os
    for (path,) in file_paths:
        try:
            if path and _os.path.exists(path):
                storage_total_mb += _os.path.getsize(path) / (1024 * 1024)
        except OSError:
            pass

    # Subscription breakdown
    sub_active = sum(1 for u in all_users if u.subscription_status == "starter_active")
    sub_past_due = sum(1 for u in all_users if u.subscription_status == "starter_past_due")
    sub_canceled = sum(1 for u in all_users if u.subscription_status == "starter_canceled")

    # LINE
    from .config import is_line_configured
    line_stats = {"feature_available": is_line_configured(), "linked_users": 0,
                  "push_quota_used": 0, "push_quota_limit": 200, "push_quota_percent": 0}
    if is_line_configured():
        from .database import LineUser
        from . import line_quota
        linked = (await db.execute(
            select(func.count(LineUser.id)).where(LineUser.line_user_id.isnot(None))
        )).scalar() or 0
        usage = line_quota.get_current_usage()
        line_stats = {
            "feature_available": True,
            "linked_users": linked,
            "push_quota_used": usage.get("pushes_used", 0),
            "push_quota_limit": usage.get("limit", 200),
            "push_quota_percent": usage.get("percent", 0),
        }

    # System
    from .config import APP_VERSION, DATA_DIR
    db_size_mb = 0.0
    db_path = _os.path.join(DATA_DIR, "projectkey.db")
    try:
        if _os.path.exists(db_path):
            db_size_mb = round(_os.path.getsize(db_path) / (1024 * 1024), 2)
    except OSError:
        pass

    return {
        "users": {
            "total": total_users,
            "by_plan": by_plan,
            "active": active_count,
            "inactive": total_users - active_count,
            "signups_today": signups_today,
            "signups_this_week": signups_week,
            "signups_this_month": signups_month,
        },
        "files": {
            "total": total_files,
            "total_storage_mb": round(storage_total_mb, 2),
        },
        "subscriptions": {
            "starter_active": sub_active,
            "starter_past_due": sub_past_due,
            "starter_canceled": sub_canceled,
        },
        "line": line_stats,
        "system": {
            "app_version": APP_VERSION,
            "db_size_mb": db_size_mb,
            "checked_at": now.isoformat() + "Z",
        },
    }


# ═══════════════════════════════════════════
# 2. User List + Detail
# ═══════════════════════════════════════════

async def list_users(
    db: AsyncSession,
    q: Optional[str] = None,
    plan_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Paginated user list with optional search + filter."""
    if page < 1:
        raise HTTPException(400, detail={"error": {"code": "INVALID_PAGE", "message": "page >= 1"}})
    if page_size < 1 or page_size > 100:
        raise HTTPException(400, detail={"error": {"code": "INVALID_PAGE", "message": "page_size 1-100"}})

    query = select(User)

    if q:
        query = query.where(User.email.ilike(f"%{q}%"))

    if plan_filter == "inactive":
        query = query.where(User.is_active == False)  # noqa: E712
    # Note: filter by "free"/"starter"/"admin" ทำที่ post-process เพราะ effective plan
    # ต้อง compute (ไม่ใช่แค่ user.plan column).

    # Count total (before plan filter post-process — slight overcount if plan filter set)
    total_query = query.with_only_columns(func.count(User.id)).order_by(None)
    total = (await db.execute(total_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    users = (await db.execute(query)).scalars().all()

    # Post-filter by effective plan if plan_filter in {free, starter, admin}
    if plan_filter in {"free", "starter", "admin"}:
        users = [u for u in users if _effective_plan(u) == plan_filter]
        # Note: total อาจไม่แม่นในกรณีนี้ — เพิ่ม note ใน response

    # Build dicts
    result = []
    for u in users:
        f_count = (await db.execute(
            select(func.count(File.id)).where(File.user_id == u.id)
        )).scalar() or 0
        # Storage — skip per-user disk scan ใน list (เพราะช้า), แสดงแค่ใน detail
        result.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_admin": bool(u.is_admin),
            "is_active": bool(u.is_active),
            "plan": u.plan or "free",
            "subscription_status": u.subscription_status or "free",
            "effective_plan": _effective_plan(u),
            "manual_plan_override": bool(getattr(u, "manual_plan_override", False)),
            "stripe_customer_id": u.stripe_customer_id,
            "stripe_subscription_id": u.stripe_subscription_id,
            "current_period_end": u.current_period_end.isoformat() + "Z" if u.current_period_end else None,
            "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
            "file_count": f_count,
            "storage_mb": None,  # not computed in list — see detail
            "last_seen_at": None,  # ไม่มี column นี้ใน users — defer
        })

    return {
        "users": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_user_detail(db: AsyncSession, user_id: str) -> dict:
    """User + usage + Stripe + downgrade-block info."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})

    # Usage (reuse plan_limits helpers)
    from .plan_limits import _month_start_for_user
    period_start = _month_start_for_user(user)
    limits = get_limits(user)

    file_count = await get_file_count(db, user.id)
    storage_mb = await get_storage_used_mb(db, user.id)
    pack_count = await get_pack_count(db, user.id)
    summaries = await get_monthly_summary_count(db, user.id, period_start)
    exports = await get_monthly_export_count(db, user.id, period_start)
    refreshes = await get_monthly_refresh_count(db, user.id, period_start)

    # Stripe active check
    stripe_active = bool(
        user.stripe_subscription_id and
        user.subscription_status in ("starter_active", "starter_past_due")
    )
    can_admin_downgrade = not stripe_active
    block_reason = "STRIPE_ACTIVE_SUBSCRIPTION" if stripe_active else None

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": bool(user.is_admin),
            "is_active": bool(user.is_active),
            "plan": user.plan or "free",
            "subscription_status": user.subscription_status or "free",
            "effective_plan": _effective_plan(user),
            "manual_plan_override": bool(getattr(user, "manual_plan_override", False)),
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "current_period_start": user.current_period_start.isoformat() + "Z" if user.current_period_start else None,
            "current_period_end": user.current_period_end.isoformat() + "Z" if user.current_period_end else None,
            "cancel_at_period_end": bool(user.cancel_at_period_end),
            "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
            "updated_at": user.updated_at.isoformat() + "Z" if user.updated_at else None,
            "google_sub": user.google_sub,
            "has_password": bool(user.password_hash),
            "storage_mode": user.storage_mode or "managed",
        },
        "usage": {
            "context_packs": {"used": pack_count, "limit": limits["context_pack_limit"]},
            "files": {"used": file_count, "limit": limits["file_limit"]},
            "storage_mb": {"used": storage_mb, "limit": limits["storage_limit_mb"]},
            "ai_summaries": {"used": summaries, "limit": limits["ai_summary_limit_monthly"]},
            "exports": {"used": exports, "limit": limits["export_limit_monthly"]},
            "refreshes": {"used": refreshes, "limit": limits["refresh_limit_monthly"]},
        },
        "stripe_active": stripe_active,
        "can_admin_downgrade": can_admin_downgrade,
        "downgrade_block_reason": block_reason,
    }


# ═══════════════════════════════════════════
# 3. Mutations (change plan / reset / toggle)
# ═══════════════════════════════════════════

VALID_PLANS = {"free", "starter", "admin"}


async def change_user_plan(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    new_plan: str,
    reason: str,
) -> dict:
    """Change plan with Stripe-aware downgrade guard + audit log."""
    if new_plan not in VALID_PLANS:
        raise HTTPException(400, detail={"error": {"code": "INVALID_PLAN", "message": f"plan must be one of {VALID_PLANS}"}})

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})

    # Self-demote guard (admin → non-admin ตัวเอง)
    if target.id == admin_user.id and new_plan != "admin":
        raise HTTPException(409, detail={"error": {
            "code": "CANNOT_DEMOTE_SELF",
            "message": "เปลี่ยน plan ของตัวเองออกจาก admin ไม่ได้ — ให้แอดมินอื่นเป็นคนทำ",
        }})

    # Stripe collision guard (downgrade ของ user ที่มี Stripe active)
    stripe_active = bool(
        target.stripe_subscription_id and
        target.subscription_status in ("starter_active", "starter_past_due")
    )
    is_downgrade = (
        (target.plan == "starter" or _effective_plan(target) == "starter")
        and new_plan == "free"
    )
    if stripe_active and is_downgrade:
        raise HTTPException(409, detail={"error": {
            "code": "STRIPE_ACTIVE_SUBSCRIPTION",
            "message": "ผู้ใช้นี้มี Stripe subscription กำลังใช้งาน — ให้ผู้ใช้ไปกดยกเลิกที่ Stripe Customer Portal ของตัวเองก่อน",
            "hint": "After cancellation, Stripe webhook will downgrade this user to free automatically.",
        }})

    old_plan_effective = _effective_plan(target)

    # Apply changes
    if new_plan == "admin":
        target.is_admin = True
        # ยังคง user.plan เดิมไว้ (free/starter) — admin = role over plan
        target.manual_plan_override = False
    elif new_plan == "starter":
        target.is_admin = False  # ถ้าเดิมเป็น admin ลดลง
        target.plan = "starter"
        target.subscription_status = "starter_active"
        target.manual_plan_override = True  # admin manual upgrade — Stripe webhook ต้อง skip
    else:  # free
        target.is_admin = False
        target.plan = "free"
        target.subscription_status = "free"
        target.manual_plan_override = False

    # Lock/unlock data
    unlocked = {"unlocked_packs": 0, "unlocked_files": 0}
    locked = {"locked_packs": 0, "locked_files": 0}
    if new_plan == "starter" or new_plan == "admin":
        unlocked = await unlock_data_for_plan(db, target.id, "starter" if new_plan == "starter" else "admin")
    elif new_plan == "free":
        locked = await lock_excess_data(db, target.id, "free")

    target.updated_at = datetime.utcnow()
    db.add(target)

    # Audit
    await log_audit(
        db, target.id, "admin_changed_plan",
        old_value=old_plan_effective,
        new_value=f"{new_plan} (reason: {reason})",
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    # Get audit log id for response
    last_log = (await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == target.id,
            AuditLog.event_type == "admin_changed_plan",
        ).order_by(desc(AuditLog.created_at)).limit(1)
    )).scalar_one_or_none()

    logger.info(
        f"Admin {admin_user.email} changed plan of {target.email}: "
        f"{old_plan_effective} → {new_plan} (reason: {reason[:50]})"
    )

    return {
        "status": "ok",
        "user_id": target.id,
        "old_plan": old_plan_effective,
        "new_plan": new_plan,
        "manual_override": bool(target.manual_plan_override),
        "unlocked_packs": unlocked["unlocked_packs"],
        "unlocked_files": unlocked["unlocked_files"],
        "locked_packs": locked["locked_packs"],
        "locked_files": locked["locked_files"],
        "audit_log_id": last_log.id if last_log else None,
    }


async def reset_user_password(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    new_password: str,
    reason: str,
) -> dict:
    """Set new password for user — show once, no email."""
    if len(new_password) < 6:
        raise HTTPException(400, detail={"error": {
            "code": "PASSWORD_TOO_SHORT", "message": "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"
        }})

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})

    # Google-only user guard
    if not target.password_hash and target.google_sub:
        raise HTTPException(409, detail={"error": {
            "code": "GOOGLE_ONLY_USER",
            "message": "ผู้ใช้นี้สมัครด้วย Google เท่านั้น — ไม่มีรหัสผ่านในระบบ ให้ผู้ใช้ login ผ่านปุ่ม Sign in with Google",
            "hint": "Set a password for this Google user first via /api/admin/users/{id}/set-password (not implemented in v8.2.0 — defer)",
        }})

    target.password_hash = hash_password(new_password)
    target.updated_at = datetime.utcnow()
    db.add(target)

    await log_audit(
        db, target.id, "admin_reset_password",
        old_value=reason,  # เก็บ reason ไว้ใน old_value (ไม่มี column dedicated)
        new_value=target.email,
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    last_log = (await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == target.id,
            AuditLog.event_type == "admin_reset_password",
        ).order_by(desc(AuditLog.created_at)).limit(1)
    )).scalar_one_or_none()

    logger.info(f"Admin {admin_user.email} reset password for {target.email} (reason: {reason[:50]})")

    return {
        "status": "ok",
        "user_id": target.id,
        "user_email": target.email,
        "new_password_shown_once": new_password,  # show ครั้งเดียว — ไม่ persist
        "warning": "รหัสนี้แสดงครั้งเดียว — ส่งให้ user ทันที. ไม่บันทึกลงระบบ.",
        "audit_log_id": last_log.id if last_log else None,
    }


async def set_user_active(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    is_active: bool,
    reason: str,
) -> dict:
    if target_user_id == admin_user.id and not is_active:
        raise HTTPException(409, detail={"error": {
            "code": "CANNOT_DEACTIVATE_SELF",
            "message": "ห้าม deactivate ตัวเอง",
        }})

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})

    target.is_active = is_active
    target.updated_at = datetime.utcnow()
    db.add(target)

    event = "admin_reactivated_user" if is_active else "admin_deactivated_user"
    await log_audit(
        db, target.id, event,
        old_value=reason,
        new_value=target.email,
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    last_log = (await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == target.id, AuditLog.event_type == event,
        ).order_by(desc(AuditLog.created_at)).limit(1)
    )).scalar_one_or_none()

    return {
        "status": "ok", "user_id": target.id,
        "is_active": bool(target.is_active),
        "audit_log_id": last_log.id if last_log else None,
    }


async def set_user_admin(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    is_admin: bool,
    reason: str,
) -> dict:
    if target_user_id == admin_user.id and not is_admin:
        raise HTTPException(409, detail={"error": {
            "code": "CANNOT_DEMOTE_SELF",
            "message": "ห้าม demote ตัวเอง — ให้แอดมินอื่นทำ",
        }})

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}})

    # Last-admin guard (ก่อน demote)
    if not is_admin:
        # นับ admin คนอื่นที่ active
        from .config import ADMIN_EMAILS as _AE
        other_db_admins = (await db.execute(
            select(func.count(User.id)).where(
                User.is_admin == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.id != target_user_id,
            )
        )).scalar() or 0
        env_admins_active = 0
        if _AE:
            for e in _AE:
                u = (await db.execute(
                    select(User).where(User.email == e.lower(), User.is_active == True)  # noqa: E712
                )).scalar_one_or_none()
                if u and u.id != target_user_id:
                    env_admins_active += 1

        if other_db_admins + env_admins_active == 0:
            raise HTTPException(409, detail={"error": {
                "code": "LAST_ADMIN_GUARD",
                "message": "ไม่สามารถ demote — จะไม่มี admin ที่ active เหลือเลย ตั้งคนใหม่ก่อน",
            }})

    target.is_admin = is_admin
    target.updated_at = datetime.utcnow()
    db.add(target)

    event = "admin_promoted" if is_admin else "admin_demoted"
    await log_audit(
        db, target.id, event,
        old_value=reason,
        new_value=target.email,
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    last_log = (await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == target.id, AuditLog.event_type == event,
        ).order_by(desc(AuditLog.created_at)).limit(1)
    )).scalar_one_or_none()

    return {
        "status": "ok", "user_id": target.id,
        "is_admin": bool(target.is_admin),
        "audit_log_id": last_log.id if last_log else None,
    }


# ═══════════════════════════════════════════
# 4. Audit log viewer
# ═══════════════════════════════════════════

async def list_audit_logs(
    db: AsyncSession,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    if limit < 1 or limit > 200:
        raise HTTPException(400, detail={"error": {"code": "INVALID_LIMIT", "message": "limit 1-200"}})

    query = select(AuditLog)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if triggered_by:
        query = query.where(AuditLog.triggered_by == triggered_by)

    total_query = query.with_only_columns(func.count(AuditLog.id)).order_by(None)
    total = (await db.execute(total_query)).scalar() or 0

    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()

    # JOIN email (best-effort — user อาจถูกลบ)
    email_cache = {}
    result = []
    for r in rows:
        if r.user_id not in email_cache:
            u = (await db.execute(select(User.email).where(User.id == r.user_id))).scalar_one_or_none()
            email_cache[r.user_id] = u
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_email": email_cache.get(r.user_id),
            "event_type": r.event_type,
            "old_value": r.old_value or "",
            "new_value": r.new_value or "",
            "triggered_by": r.triggered_by,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        })

    return {"logs": result, "total": total, "limit": limit, "offset": offset}
```

#### Step 2.2: Register endpoints ใน `main.py`

วางหลังจาก existing admin block (ใกล้ `/api/line/admin/quota` line ~1113):

```python
# ═══════════════════════════════════════════
# v8.2.0 — Admin System endpoints
# ═══════════════════════════════════════════
from .auth import require_admin
from . import admin as _admin_mod


@app.get("/api/admin/me")
async def api_admin_me(current_admin: User = Depends(require_admin)):
    """Verify admin role + return identity."""
    from .plan_limits import _effective_plan
    return {
        "id": current_admin.id,
        "email": current_admin.email,
        "name": current_admin.name,
        "is_admin": bool(current_admin.is_admin),
        "effective_plan": _effective_plan(current_admin),
    }


@app.get("/api/admin/stats")
async def api_admin_stats(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.get_admin_stats(db)


@app.get("/api/admin/users")
async def api_admin_list_users(
    q: str | None = Query(None),
    plan: str | None = Query(None, regex="^(free|starter|admin|inactive)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.list_users(db, q, plan, page, page_size)


@app.get("/api/admin/users/{user_id}")
async def api_admin_user_detail(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.get_user_detail(db, user_id)


@app.put("/api/admin/users/{user_id}/plan")
async def api_admin_change_plan(
    user_id: str,
    body: AdminChangePlanRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.change_user_plan(db, current_admin, user_id, body.plan, body.reason)


@app.post("/api/admin/users/{user_id}/reset-password")
async def api_admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.reset_user_password(db, current_admin, user_id, body.new_password, body.reason)


@app.put("/api/admin/users/{user_id}/active")
async def api_admin_toggle_active(
    user_id: str,
    body: AdminToggleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.set_user_active(db, current_admin, user_id, body.value, body.reason)


@app.put("/api/admin/users/{user_id}/admin")
async def api_admin_toggle_admin(
    user_id: str,
    body: AdminToggleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.set_user_admin(db, current_admin, user_id, body.value, body.reason)


@app.get("/api/admin/audit-logs")
async def api_admin_audit_logs(
    event_type: str | None = Query(None),
    user_id: str | None = Query(None),
    triggered_by: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_mod.list_audit_logs(db, event_type, user_id, triggered_by, limit, offset)


@app.get("/admin")
async def serve_admin():
    """Serve admin.html — JS guard handles role check (server returns 403 on API calls)."""
    return _serve_html("admin.html")
```

#### Step 2.3: Bump APP_VERSION

แก้ `backend/config.py:12`:
```python
APP_VERSION = "8.2.0"
```

---

### Phase 3 — Frontend (วันที่ 2-3, ~6 ชม.)

#### Step 3.1: `legacy-frontend/admin.html`

โครงสร้างเลียนแบบ `app.html` แต่ minimal:

```html
<!DOCTYPE html>
<html lang="th">
<head>
 <meta charset="UTF-8">
 <meta name="viewport" content="width=device-width, initial-scale=1.0">
 <title>PDB Admin Panel</title>
 <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
 <link rel="stylesheet" href="/legacy/shared.css?v=8.2.0">
 <link rel="stylesheet" href="/legacy/styles.css?v=8.2.0">
</head>
<body class="show-landing">
 <!-- 'show-landing' = override body { overflow: hidden } ของ shared.css เพื่อให้ admin scroll ได้ -->

 <!-- Loading guard -->
 <div id="admin-loading" class="admin-loading">
   <p>กำลังตรวจสอบสิทธิ์...</p>
 </div>

 <!-- Main shell (hidden until auth verified) -->
 <div id="admin-shell" class="admin-shell hidden">
   <header class="admin-header">
     <div class="admin-logo">
       <svg>...</svg>
       <span>PDB Admin <span class="admin-badge">v8.2.0</span></span>
     </div>
     <div class="admin-user-info">
       <span id="admin-email">—</span>
       <button id="btn-back-to-app" class="btn btn-ghost btn-sm">← กลับไป /app</button>
       <button id="btn-admin-logout" class="btn btn-outline btn-sm">ออกจากระบบ</button>
     </div>
   </header>

   <nav class="admin-tabs">
     <button class="admin-tab active" data-tab="dashboard">Dashboard</button>
     <button class="admin-tab" data-tab="users">Users</button>
     <button class="admin-tab" data-tab="audit">Audit Log</button>
   </nav>

   <main class="admin-main">

     <!-- Tab 1: Dashboard -->
     <section id="admin-tab-dashboard" class="admin-tab-content active">
       <h2>ภาพรวมระบบ</h2>
       <div class="admin-stats-grid" id="admin-stats-grid">
         <div class="admin-stat-card">
           <div class="stat-label">ผู้ใช้ทั้งหมด</div>
           <div class="stat-value" id="stat-total-users">—</div>
           <div class="stat-detail" id="stat-users-breakdown">—</div>
         </div>
         <div class="admin-stat-card">
           <div class="stat-label">ผู้ใช้ Active</div>
           <div class="stat-value" id="stat-active-users">—</div>
         </div>
         <div class="admin-stat-card">
           <div class="stat-label">สมัครวันนี้ / สัปดาห์นี้</div>
           <div class="stat-value"><span id="stat-signups-today">—</span> / <span id="stat-signups-week">—</span></div>
         </div>
         <div class="admin-stat-card">
           <div class="stat-label">ไฟล์ทั้งหมด</div>
           <div class="stat-value" id="stat-total-files">—</div>
           <div class="stat-detail"><span id="stat-storage">—</span> MB</div>
         </div>
         <div class="admin-stat-card">
           <div class="stat-label">Stripe Active Subs</div>
           <div class="stat-value" id="stat-stripe-active">—</div>
           <div class="stat-detail">past due: <span id="stat-stripe-pastdue">0</span></div>
         </div>
         <div class="admin-stat-card">
           <div class="stat-label">LINE Quota</div>
           <div class="stat-value"><span id="stat-line-used">—</span>/<span id="stat-line-limit">—</span></div>
           <div class="stat-detail"><span id="stat-line-percent">0</span>% ใช้แล้ว · <span id="stat-line-linked">0</span> linked</div>
         </div>
       </div>
       <p class="admin-checked-at">อัปเดตล่าสุด: <span id="admin-checked-at">—</span></p>
     </section>

     <!-- Tab 2: Users -->
     <section id="admin-tab-users" class="admin-tab-content">
       <h2>จัดการผู้ใช้</h2>
       <div class="admin-users-controls">
         <input type="text" id="admin-users-search" placeholder="ค้นหา email..." class="form-input">
         <select id="admin-users-filter" class="form-input">
           <option value="">ทั้งหมด</option>
           <option value="free">Free</option>
           <option value="starter">Starter</option>
           <option value="admin">Admin</option>
           <option value="inactive">Inactive</option>
         </select>
         <button id="admin-users-refresh" class="btn btn-outline">รีเฟรช</button>
       </div>
       <div class="admin-users-table-wrapper">
         <table class="admin-users-table">
           <thead>
             <tr>
               <th>Email</th>
               <th>ชื่อ</th>
               <th>Plan</th>
               <th>Stripe</th>
               <th>ไฟล์</th>
               <th>สมัครเมื่อ</th>
               <th>สถานะ</th>
               <th>Actions</th>
             </tr>
           </thead>
           <tbody id="admin-users-tbody">
             <tr><td colspan="8" class="text-muted">กำลังโหลด...</td></tr>
           </tbody>
         </table>
       </div>
       <div class="admin-users-pagination">
         <button id="admin-users-prev" class="btn btn-sm btn-outline">← ก่อนหน้า</button>
         <span id="admin-users-page-info">หน้า 1/1</span>
         <button id="admin-users-next" class="btn btn-sm btn-outline">ถัดไป →</button>
       </div>
     </section>

     <!-- Tab 3: Audit Log -->
     <section id="admin-tab-audit" class="admin-tab-content">
       <h2>กล้องวงจรปิด — ประวัติการกระทำ</h2>
       <div class="admin-audit-controls">
         <select id="admin-audit-filter" class="form-input">
           <option value="">ทั้งหมด</option>
           <option value="admin_changed_plan">เปลี่ยน Plan (admin)</option>
           <option value="admin_reset_password">รีเซ็ตรหัสผ่าน (admin)</option>
           <option value="admin_deactivated_user">Deactivate (admin)</option>
           <option value="admin_reactivated_user">Reactivate (admin)</option>
           <option value="admin_promoted">Promote admin</option>
           <option value="admin_demoted">Demote admin</option>
           <option value="plan_changed">Plan changed (auto)</option>
           <option value="downgrade_completed">Downgrade (Stripe)</option>
         </select>
         <button id="admin-audit-refresh" class="btn btn-outline">รีเฟรช</button>
       </div>
       <div class="admin-audit-list" id="admin-audit-list">
         <p class="text-muted">กำลังโหลด...</p>
       </div>
     </section>

   </main>

 </div>

 <!-- Modal: Change Plan -->
 <div class="modal-overlay hidden" id="modal-change-plan">
   <div class="modal">
     <div class="modal-header">
       <h2>เปลี่ยน Plan</h2>
       <button class="btn-close" id="modal-change-plan-close"></button>
     </div>
     <div class="modal-body">
       <p>ผู้ใช้: <strong id="modal-change-plan-email">—</strong></p>
       <p>Plan ปัจจุบัน: <strong id="modal-change-plan-current">—</strong></p>
       <div id="modal-change-plan-warning" class="admin-warning-banner hidden"></div>
       <div class="form-group">
         <label>Plan ใหม่</label>
         <select id="modal-change-plan-select" class="form-input">
           <option value="free">Free</option>
           <option value="starter">Starter (manual override — ไม่ผ่าน Stripe)</option>
           <option value="admin">Admin (full access)</option>
         </select>
       </div>
       <div class="form-group">
         <label>เหตุผล (บันทึกใน audit log)</label>
         <textarea id="modal-change-plan-reason" class="form-input" rows="2" placeholder="เช่น Beta tester, แลกของรางวัล, etc."></textarea>
       </div>
     </div>
     <div class="modal-footer">
       <button class="btn btn-outline" id="modal-change-plan-cancel">ยกเลิก</button>
       <button class="btn btn-primary" id="modal-change-plan-confirm">บันทึก</button>
     </div>
   </div>
 </div>

 <!-- Modal: Reset Password -->
 <div class="modal-overlay hidden" id="modal-reset-password">
   <div class="modal">
     <div class="modal-header">
       <h2>รีเซ็ตรหัสผ่าน</h2>
       <button class="btn-close" id="modal-reset-password-close"></button>
     </div>
     <div class="modal-body">
       <p>ผู้ใช้: <strong id="modal-reset-password-email">—</strong></p>
       <div class="admin-warning-banner">⚠️ ระบบจะแสดงรหัสครั้งเดียวเท่านั้น — เตรียมส่งให้ user ทันที</div>
       <div class="form-group">
         <label>รหัสผ่านใหม่ (อย่างน้อย 6 ตัว)</label>
         <input type="text" id="modal-reset-password-input" class="form-input" placeholder="กรอกรหัสใหม่">
         <button type="button" class="btn btn-outline btn-sm" id="modal-reset-password-generate">สร้างรหัสสุ่ม 12 ตัว</button>
       </div>
       <div class="form-group">
         <label>เหตุผล</label>
         <textarea id="modal-reset-password-reason" class="form-input" rows="2" placeholder="เช่น user ลืมรหัส โทรมาแจ้ง"></textarea>
       </div>
     </div>
     <div class="modal-footer">
       <button class="btn btn-outline" id="modal-reset-password-cancel">ยกเลิก</button>
       <button class="btn btn-primary" id="modal-reset-password-confirm">เปลี่ยนรหัส</button>
     </div>
   </div>
 </div>

 <!-- Modal: Show new password (one-time) -->
 <div class="modal-overlay hidden" id="modal-password-shown">
   <div class="modal">
     <div class="modal-header">
       <h2>รหัสผ่านใหม่ — แสดงครั้งเดียว</h2>
     </div>
     <div class="modal-body">
       <div class="admin-warning-banner">⚠️ คัดลอกตอนนี้ — ปิดแล้วจะไม่สามารถดูได้อีก</div>
       <div class="admin-password-display" id="admin-password-display">—</div>
       <button class="btn btn-outline" id="modal-password-copy">คัดลอก</button>
     </div>
     <div class="modal-footer">
       <button class="btn btn-primary" id="modal-password-shown-close">ปิด (ยืนยันว่าเก็บแล้ว)</button>
     </div>
   </div>
 </div>

 <!-- Modal: Confirm Deactivate / Promote -->
 <div class="modal-overlay hidden" id="modal-confirm-action">
   <div class="modal">
     <div class="modal-header">
       <h2 id="modal-confirm-title">ยืนยัน</h2>
     </div>
     <div class="modal-body">
       <p id="modal-confirm-message">—</p>
       <div class="form-group">
         <label>เหตุผล (บันทึกใน audit log)</label>
         <textarea id="modal-confirm-reason" class="form-input" rows="2"></textarea>
       </div>
     </div>
     <div class="modal-footer">
       <button class="btn btn-outline" id="modal-confirm-cancel">ยกเลิก</button>
       <button class="btn btn-primary" id="modal-confirm-ok">ยืนยัน</button>
     </div>
   </div>
 </div>

 <!-- Toast container — reuse #toast-container + .toast classes จาก shared.css -->
 <div id="toast-container"></div>

 <script src="/legacy/admin.js?v=8.2.0"></script>
</body>
</html>
```

**Verified shared.css patterns ที่ admin.html ใช้:**
- `.modal-overlay` + `.modal` + `.modal-header` + `.modal-body` + `.modal-footer` (shared.css:217-376) — มี mobile responsive 92vw + animation fadeIn พร้อม
- `.btn` + `.btn-primary` + `.btn-outline` + `.btn-ghost` + `.btn-sm` + `.btn-block` + `.btn-close` (shared.css:101-215) — มี mobile 44px touch target พร้อม
- `.form-group` + `.form-input` + textarea (shared.css:378-421) — รองรับ `:focus`, `.is-invalid`
- `#toast-container` + `.toast` + `.toast.success/.error/.info` + `.toast-msg` + `.toast-close` (shared.css:436-485) — z-index 11000, slideUp animation
- `.hidden` (shared.css:488)
- `body.show-landing` (shared.css:81-84) — override `overflow: hidden` เพื่อ scroll ได้

#### Step 3.2: `legacy-frontend/admin.js`

โครงร่าง 4 sections (~600 lines):

```javascript
/**
 * PDB Admin Panel — v8.2.0
 *
 * Sections:
 *  §A  Auth guard + state
 *  §B  Tab routing + nav
 *  §C  Dashboard tab
 *  §D  Users tab + modals (change plan / reset password / toggle active / toggle admin)
 *  §E  Audit log tab
 *  §F  Toast / confirm helpers (lite — match admin scope only)
 */

// ═══════════════════════════════════════════
// §A — Auth guard + state
// ═══════════════════════════════════════════
const ADMIN = {
  token: localStorage.getItem('pdb_token'),
  me: null,  // { id, email, name, is_admin, effective_plan }
  users: { page: 1, pageSize: 20, total: 0, query: '', filter: '' },
  audit: { eventType: '', limit: 50, offset: 0 },
};

async function adminFetch(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  if (ADMIN.token) opts.headers['Authorization'] = `Bearer ${ADMIN.token}`;
  const res = await fetch(url, opts);
  if (res.status === 401) {
    localStorage.removeItem('pdb_token');
    localStorage.removeItem('pdb_user');
    window.location.href = '/';
    throw new Error('Unauthorized');
  }
  if (res.status === 403) {
    // Not admin
    document.getElementById('admin-loading').innerHTML =
      '<p>คุณไม่ใช่ admin — กำลังพากลับ <a href="/app">/app</a></p>';
    setTimeout(() => { window.location.href = '/app'; }, 2000);
    throw new Error('Not admin');
  }
  return res;
}

async function init() {
  if (!ADMIN.token) {
    window.location.href = '/';
    return;
  }
  try {
    const res = await adminFetch('/api/admin/me');
    if (!res.ok) throw new Error('Auth failed');
    ADMIN.me = await res.json();
    document.getElementById('admin-email').textContent = ADMIN.me.email;
    document.getElementById('admin-loading').classList.add('hidden');
    document.getElementById('admin-shell').classList.remove('hidden');
    setupNav();
    loadDashboard();
  } catch (e) {
    console.error(e);
  }
}

// ═══════════════════════════════════════════
// §B — Tab routing
// ═══════════════════════════════════════════
function setupNav() {
  document.querySelectorAll('.admin-tab').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.admin-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab;
      document.querySelectorAll('.admin-tab-content').forEach(s => s.classList.remove('active'));
      document.getElementById(`admin-tab-${tab}`).classList.add('active');
      if (tab === 'dashboard') loadDashboard();
      if (tab === 'users') loadUsers();
      if (tab === 'audit') loadAuditLogs();
    };
  });
  document.getElementById('btn-back-to-app').onclick = () => { window.location.href = '/app'; };
  document.getElementById('btn-admin-logout').onclick = () => {
    localStorage.removeItem('pdb_token'); localStorage.removeItem('pdb_user');
    window.location.href = '/';
  };
}

// ═══════════════════════════════════════════
// §C — Dashboard
// ═══════════════════════════════════════════
async function loadDashboard() {
  const res = await adminFetch('/api/admin/stats');
  const data = await res.json();
  document.getElementById('stat-total-users').textContent = data.users.total;
  document.getElementById('stat-users-breakdown').textContent =
    `Free ${data.users.by_plan.free} · Starter ${data.users.by_plan.starter} · Admin ${data.users.by_plan.admin}`;
  document.getElementById('stat-active-users').textContent = data.users.active;
  document.getElementById('stat-signups-today').textContent = data.users.signups_today;
  document.getElementById('stat-signups-week').textContent = data.users.signups_this_week;
  document.getElementById('stat-total-files').textContent = data.files.total;
  document.getElementById('stat-storage').textContent = data.files.total_storage_mb;
  document.getElementById('stat-stripe-active').textContent = data.subscriptions.starter_active;
  document.getElementById('stat-stripe-pastdue').textContent = data.subscriptions.starter_past_due;
  document.getElementById('stat-line-used').textContent = data.line.push_quota_used;
  document.getElementById('stat-line-limit').textContent = data.line.push_quota_limit;
  document.getElementById('stat-line-percent').textContent = data.line.push_quota_percent;
  document.getElementById('stat-line-linked').textContent = data.line.linked_users;
  document.getElementById('admin-checked-at').textContent = new Date(data.system.checked_at).toLocaleString('th-TH');
}

// ═══════════════════════════════════════════
// §D — Users
// ═══════════════════════════════════════════
async function loadUsers() {
  const params = new URLSearchParams({
    page: ADMIN.users.page, page_size: ADMIN.users.pageSize,
  });
  if (ADMIN.users.query) params.set('q', ADMIN.users.query);
  if (ADMIN.users.filter) params.set('plan', ADMIN.users.filter);
  const res = await adminFetch(`/api/admin/users?${params}`);
  const data = await res.json();
  ADMIN.users.total = data.total;

  const tbody = document.getElementById('admin-users-tbody');
  if (data.users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-muted">ไม่มีผู้ใช้</td></tr>';
  } else {
    tbody.innerHTML = data.users.map(u => `
      <tr data-user-id="${u.id}">
        <td>${escapeHtml(u.email || '—')}</td>
        <td>${escapeHtml(u.name || '—')}</td>
        <td>${planBadge(u.effective_plan)}</td>
        <td>${u.stripe_subscription_id ? `<span class="badge-stripe">${u.subscription_status}</span>` : '—'}</td>
        <td>${u.file_count || 0}</td>
        <td>${u.created_at ? new Date(u.created_at).toLocaleDateString('th-TH') : '—'}</td>
        <td>${u.is_active ? '<span class="badge-active">Active</span>' : '<span class="badge-inactive">Inactive</span>'}</td>
        <td class="admin-user-actions">
          <button class="btn btn-sm btn-outline" onclick="openChangePlan('${u.id}')">Plan</button>
          <button class="btn btn-sm btn-outline" onclick="openResetPassword('${u.id}')">รหัสผ่าน</button>
          <button class="btn btn-sm btn-outline" onclick="toggleActive('${u.id}', ${!u.is_active})">${u.is_active ? 'Deactivate' : 'Reactivate'}</button>
          <button class="btn btn-sm btn-outline" onclick="toggleAdmin('${u.id}', ${!u.is_admin})">${u.is_admin ? 'Demote' : 'Promote'}</button>
        </td>
      </tr>
    `).join('');
  }
  document.getElementById('admin-users-page-info').textContent = `หน้า ${data.page}/${data.total_pages || 1}`;
  document.getElementById('admin-users-prev').disabled = data.page <= 1;
  document.getElementById('admin-users-next').disabled = data.page >= data.total_pages;
}

function planBadge(plan) {
  const colors = { free: 'badge-free', starter: 'badge-starter', admin: 'badge-admin' };
  return `<span class="badge ${colors[plan] || ''}">${plan}</span>`;
}

// Modal: Change plan
async function openChangePlan(userId) {
  const res = await adminFetch(`/api/admin/users/${userId}`);
  const data = await res.json();
  const modal = document.getElementById('modal-change-plan');
  modal.dataset.userId = userId;
  document.getElementById('modal-change-plan-email').textContent = data.user.email;
  document.getElementById('modal-change-plan-current').textContent = data.user.effective_plan;
  document.getElementById('modal-change-plan-select').value = data.user.effective_plan;
  document.getElementById('modal-change-plan-reason').value = '';
  const warning = document.getElementById('modal-change-plan-warning');
  if (data.stripe_active) {
    warning.classList.remove('hidden');
    warning.textContent = '⚠️ User คนนี้มี Stripe subscription กำลังใช้งาน — downgrade เป็น free จะถูกบล็อก';
  } else {
    warning.classList.add('hidden');
  }
  modal.classList.remove('hidden');
}

document.getElementById('modal-change-plan-confirm').onclick = async () => {
  const modal = document.getElementById('modal-change-plan');
  const userId = modal.dataset.userId;
  const plan = document.getElementById('modal-change-plan-select').value;
  const reason = document.getElementById('modal-change-plan-reason').value.trim();
  if (!reason) { showToast('กรอกเหตุผลก่อน', 'error'); return; }
  try {
    const res = await adminFetch(`/api/admin/users/${userId}/plan`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan, reason }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.error?.message || `HTTP ${res.status}`);
    }
    const data = await res.json();
    showToast(`เปลี่ยน plan เรียบร้อย: ${data.old_plan} → ${data.new_plan}`, 'success');
    modal.classList.add('hidden');
    loadUsers();
  } catch (e) {
    showToast(e.message, 'error');
  }
};

// (… handler ของ reset password / toggle active / toggle admin ตามลำดับเดียวกัน …)

// ═══════════════════════════════════════════
// §E — Audit log
// ═══════════════════════════════════════════
async function loadAuditLogs() {
  const params = new URLSearchParams({ limit: ADMIN.audit.limit, offset: ADMIN.audit.offset });
  if (ADMIN.audit.eventType) params.set('event_type', ADMIN.audit.eventType);
  const res = await adminFetch(`/api/admin/audit-logs?${params}`);
  const data = await res.json();
  const list = document.getElementById('admin-audit-list');
  if (data.logs.length === 0) {
    list.innerHTML = '<p class="text-muted">ยังไม่มีรายการ</p>';
    return;
  }
  list.innerHTML = data.logs.map(log => `
    <div class="admin-audit-row">
      <div class="audit-time">${new Date(log.created_at).toLocaleString('th-TH')}</div>
      <div class="audit-event"><strong>${escapeHtml(log.event_type)}</strong></div>
      <div class="audit-user">${escapeHtml(log.user_email || log.user_id)}</div>
      <div class="audit-detail">
        ${log.old_value ? `<span class="audit-old">${escapeHtml(log.old_value)}</span> → ` : ''}
        <span class="audit-new">${escapeHtml(log.new_value)}</span>
      </div>
      <div class="audit-by">โดย: ${escapeHtml(log.triggered_by)}</div>
    </div>
  `).join('');
}

// ═══════════════════════════════════════════
// §F — Toast + utils (REUSE shared.css .toast pattern)
// ═══════════════════════════════════════════
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, s =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
}

// Toast — ใช้ class จาก shared.css ตรงๆ (.toast + .success/.error/.info + .toast-msg + .toast-close)
// อย่า redefine CSS ใหม่ — shared.css:436-485 มีครบแล้ว
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;  // matches .toast.success / .toast.error / .toast.info
  t.innerHTML = `
    <div class="toast-msg">${escapeHtml(msg)}</div>
    <button class="toast-close" aria-label="ปิด">&times;</button>
  `;
  t.querySelector('.toast-close').onclick = () => t.remove();
  document.getElementById('toast-container').appendChild(t);
  // Auto-dismiss after 4s for success/info; error stays until user closes (match v7.2.0 UX)
  if (type !== 'error') {
    setTimeout(() => { t.remove(); }, 4000);
  }
}

// Bootstrap
init();
```

**ทำไม reuse shared.css เต็มที่:**
- ลด code duplication (`.toast` 50 บรรทัด CSS — admin ไม่ต้องเขียนเอง)
- Visual consistency กับ /app (user เห็น toast แบบเดียวกัน)
- Mobile responsive ติดมาเลย (44px touch target ของ button จาก shared.css:317-348)
- อนาคต ถ้า /app เปลี่ยน toast style → /admin update ตามอัตโนมัติ

#### Step 3.3: `legacy-frontend/styles.css` additions

วาง section ใหม่ท้ายไฟล์ (~80 lines) — **ใช้เฉพาะ design tokens ที่มีจริงใน shared.css**:

**✅ Design tokens ที่ใช้ได้ (verified):**
- Background: `--bg-primary` `--bg-secondary` `--bg-card` `--bg-hover` `--bg-active`
- Surface: `--surface-1` `--surface-2` `--surface-3`
- Border: `--border` `--border-hover`
- Text: `--text-primary` `--text-secondary` `--text-muted`
- Accent: `--accent` `--accent-hover` `--accent-glow`
- Status: `--success` `--warning` `--error`

**❌ ห้ามใช้ (ไม่มีจริง):** `--bg-base`, `--border-subtle`, `--accent-primary`, `--accent-tag`

```css
/* ═══════════════════════════════════════════
   ADMIN PANEL — v8.2.0
   reuse: shared.css ทั้ง modal-overlay/.modal/.toast/.btn-*/.form-input
   ═══════════════════════════════════════════ */
.admin-loading {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-primary); color: var(--text-muted);
}

.admin-shell {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex; flex-direction: column;
  overflow-y: auto;  /* override body overflow:hidden ของ shared.css */
}

.admin-header {
  padding: 16px 32px;
  border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-secondary);
}
.admin-logo { display: flex; align-items: center; gap: 12px; font-weight: 600; color: var(--text-primary); }
.admin-logo-pill {  /* badge เล็กข้างชื่อ — reuse style ของ logo-version */
  background: var(--surface-2);
  color: var(--text-secondary);
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
}
.admin-user-info { display: flex; gap: 12px; align-items: center; font-size: 14px; color: var(--text-secondary); }

.admin-tabs {
  display: flex; gap: 4px;
  padding: 0 32px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}
.admin-tab {
  padding: 12px 20px;
  background: transparent; border: none; cursor: pointer;
  color: var(--text-muted); border-bottom: 2px solid transparent;
  font-family: inherit; font-size: 13px;
}
.admin-tab:hover { color: var(--text-secondary); }
.admin-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); font-weight: 600; }
.admin-tab-content { display: none; padding: 32px; }
.admin-tab-content.active { display: block; animation: fadeIn 0.2s ease; }
.admin-main { flex: 1; max-width: 1400px; margin: 0 auto; width: 100%; }

.admin-stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.admin-stat-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
}
.admin-stat-card .stat-label { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.admin-stat-card .stat-value { font-size: 28px; font-weight: 700; color: var(--text-primary); }
.admin-stat-card .stat-detail { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.admin-checked-at { color: var(--text-muted); font-size: 12px; margin-top: 24px; }

.admin-users-controls { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.admin-users-controls .form-input { flex: 1; max-width: 400px; }
.admin-users-table-wrapper { overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; }
.admin-users-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.admin-users-table th {
  text-align: left; padding: 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted); font-weight: 600;
  background: var(--bg-card);
}
.admin-users-table td { padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
.admin-users-table tr:last-child td { border-bottom: none; }
.admin-user-actions { display: flex; gap: 4px; flex-wrap: wrap; }
.admin-users-pagination {
  display: flex; gap: 12px; align-items: center; justify-content: center;
  margin-top: 24px; color: var(--text-secondary); font-size: 13px;
}

/* ─── Badge modifiers (extend .badge from styles.css:359) ─── */
.badge-free   { background: var(--surface-2); color: var(--text-secondary); }
.badge-starter{ background: var(--accent-glow); color: var(--accent-hover); border: 1px solid var(--accent); }
.badge-admin  { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid var(--warning); }
.badge-stripe { background: rgba(167, 139, 250, 0.15); color: #c4b5fd; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-active { color: var(--success); }
.badge-inactive { color: var(--error); }

/* ─── Audit log ─── */
.admin-audit-list { display: flex; flex-direction: column; gap: 8px; }
.admin-audit-row {
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: grid; grid-template-columns: 160px 180px 1fr 1fr 180px;
  gap: 12px; font-size: 13px; align-items: center;
}
.admin-audit-row .audit-time { color: var(--text-muted); }
.admin-audit-row .audit-old { color: var(--text-muted); text-decoration: line-through; }
.admin-audit-row .audit-new { color: var(--text-primary); font-weight: 600; }
.admin-audit-row .audit-by { color: var(--text-muted); font-size: 12px; }

/* ─── Warnings + password display ─── */
.admin-warning-banner {
  padding: 12px 16px;
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
  border-left: 3px solid var(--warning);
  border-radius: 4px;
  font-size: 14px; margin: 16px 0;
}
.admin-password-display {
  font-family: 'Menlo', 'Monaco', monospace;
  font-size: 18px;
  padding: 16px;
  background: var(--surface-1);
  border: 2px dashed var(--accent);
  border-radius: 8px;
  text-align: center;
  user-select: all;  /* allow easy triple-click copy */
  margin: 16px 0;
  color: var(--text-primary);
}

/* ─── Mobile responsive ─── */
@media (max-width: 768px) {
  .admin-header, .admin-tabs { padding-left: 16px; padding-right: 16px; }
  .admin-tab-content { padding: 16px; }
  .admin-audit-row { grid-template-columns: 1fr; gap: 4px; }
  .admin-users-table { font-size: 12px; }
  .admin-users-table th, .admin-users-table td { padding: 8px; }
  .admin-stats-grid { grid-template-columns: 1fr 1fr; }
}
```

**Key changes จาก draft แรก:**
- ❌ ลบ `.admin-toast*` ออก — ใช้ `.toast` + `#toast-container` ของ shared.css ทั้งหมด
- ❌ ลบ `--bg-base`, `--border-subtle`, `--accent-primary`, `--accent-tag` — ใช้ token ที่มีจริง
- ✅ ใช้ `animation: fadeIn` ที่ define ใน shared.css อยู่แล้ว
- ✅ Override `body { overflow: hidden }` ของ shared.css ด้วย `.admin-shell { overflow-y: auto }` (admin page ต้องการ scroll)

#### Step 3.4: `landing.js` redirect logic — **single point ใน `showApp()`**

**Verified location:** `landing.js` มี `showApp()` ที่ line 41-44:
```javascript
function showApp() {
  // ... (logic เดิม)
  window.location.href = '/app';
}
```

**ที่เรียก `showApp()`:**
- Line 126 — `doLogin()` success
- Line 199 — register flow success
- Line 304 — reset password auto-login success
- Line 339 — handler อื่น
- Line 430 — initAuth verify

**Decision: แก้ที่จุดเดียว** — ใน `showApp()` เปลี่ยน hardcoded `/app` เป็น check is_admin ก่อน:

```javascript
async function showApp() {
  // ... (existing logic เดิม — return false ถ้าไม่มี token)
  if (!state.authToken) {
    window.location.href = '/';
    return false;
  }

  // v8.2.0 — Admin redirect: ถ้า user เป็น admin ส่งไป /admin แทน /app
  // ใช้ /api/admin/me เพื่อรองรับทั้ง is_admin (DB) และ ADMIN_EMAILS (env fallback)
  // Best-effort: ถ้า 403/error → fallback ไป /app ตามปกติ
  try {
    const res = await fetch('/api/admin/me', {
      headers: { Authorization: `Bearer ${state.authToken}` },
    });
    if (res.ok) {
      window.location.href = '/admin';
      return true;
    }
  } catch (_) { /* network error → fallback */ }

  window.location.href = '/app';
  return true;
}
```

**ผลกระทบ:** `doLogin()`, register, reset password, Google login fragment, initAuth — **ทุก path** ที่เรียก `showApp()` จะได้ admin redirect "ฟรี" ไม่ต้องแก้ที่ละจุด

**⚠️ Caller-side awareness:**
- `_handleGoogleLoginFragment()` (line 314) ทำ `state.authToken = jwt; localStorage.setItem; showApp()` → ได้ admin redirect ฟรี ✅
- `doLogin()` (line 86) `if (showApp()) initAppData()` — ถ้า redirect ไป /admin, `initAppData()` ที่อยู่หลัง `if` จะรันก่อน redirect ไม่ครบ → **ไม่มีปัญหา** เพราะ `window.location.href` cancel any in-flight JS หลัง assignment

**Side note:** `showApp()` เปลี่ยนเป็น `async` — caller ที่ใช้ `if (showApp())` ต้องรู้ว่า return Promise. แต่ truthy เพราะ Promise object → behavior เหมือนเดิม (initAppData รันก่อน redirect — แต่ redirect ยกเลิกการ render). ถ้าอยาก clean → caller ใช้ `await showApp()` (ไม่ critical สำหรับ scope นี้)

---

### Phase 4 — Tests + Verification (วันที่ 3, ~3 ชม.)

#### Step 4.1: `tests/test_admin.py`

ครอบคลุม ~30 cases — ดู [Test Scenarios](#test-scenarios) ด้านล่าง

#### Step 4.2: Manual smoke test (UI)

1. Start app local — login ด้วย `bossok2546@gmail.com` (ADMIN_EMAILS)
2. ตรวจ redirect ไป `/admin` อัตโนมัติ
3. Dashboard load ครบทุก stat
4. Users tab — search ด้วย email + paginate
5. ลองเปลี่ยน plan ของ user ทดสอบ free → starter → check Audit log
6. ลอง reset password user ทดสอบ → จด password ที่ show → logout login ด้วย user นั้น → confirm ใช้ได้
7. ลอง deactivate user → user login ไม่ได้ (401)
8. ลอง promote user ทดสอบ → user คนนั้น login → ตรวจ /admin เข้าได้
9. ลอง demote ตัวเอง → expect 409 CANNOT_DEMOTE_SELF
10. ลอง downgrade user ที่มี Stripe sub active → expect 409 STRIPE_ACTIVE_SUBSCRIPTION

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path (10 cases)

1. **Admin login** — ADMIN_EMAILS user login → JWT contains email → `/api/admin/me` 200
2. **Stats** — 3 users (1 free, 1 starter, 1 admin) → `/api/admin/stats` returns correct breakdown
3. **List users** — pagination page=1 page_size=2 → returns 2 + total_pages correct
4. **Search by email** — `?q=bossok` → returns matching only
5. **Filter by plan** — `?plan=starter` → returns only starter users
6. **User detail** — returns user + usage + stripe_active flag
7. **Change plan free → starter** — user without Stripe → success + manual_override=true + unlock=0 (no locked data)
8. **Change plan starter → free** — user without Stripe → success + lock excess
9. **Reset password** — set 12-char password → returns it once + verify login works
10. **Audit log list** — after 3 admin actions → returns 3 + most recent first

### Validation Errors (8 cases)

11. **Invalid plan** — PUT `/plan` with `plan="enterprise"` → 400 INVALID_PLAN
12. **Empty reason — change plan** → 400 EMPTY_REASON (Pydantic validator)
13. **Empty reason — reset password** → 400 EMPTY_REASON
14. **Empty reason — toggle active** → 400 EMPTY_REASON
15. **Password too short** — 5 chars → 400 PASSWORD_TOO_SHORT
16. **Page out of range** — page=0 or page_size=200 → 400 INVALID_PAGE
17. **Audit limit out of range** — limit=300 → 400 INVALID_LIMIT
18. **Search query injection** — `q="' OR 1=1 --"` → safe (SQLAlchemy parameterized)

### Auth Errors (5 cases)

19. **No JWT** — any /api/admin/* → 401
20. **Expired JWT** → 401
21. **Valid JWT but not admin** — `/api/admin/me` from regular user → 403 NOT_ADMIN
22. **Deactivated admin** — `is_active=False` → 401 (caught by `get_current_user`)
23. **JWT signed with different secret** → 401

### Edge Cases (10 cases)

24. **Stripe collision** — admin downgrade user with `subscription_status=starter_active` → 409 STRIPE_ACTIVE_SUBSCRIPTION
25. **Stripe past_due collision** — same as above with `starter_past_due` → 409 (same code)
26. **Stripe canceled (period not ended)** — `subscription_status=starter_canceled` + period_end > now → 409 (same code) **IF** still has subscription_id
27. **Self-demote** — admin PUT `/admin` with own user_id + value=false → 409 CANNOT_DEMOTE_SELF
28. **Self-deactivate** — same → 409 CANNOT_DEACTIVATE_SELF
29. **Self plan change away from admin** — admin PUT `/plan` with own id + new_plan=free → 409 CANNOT_DEMOTE_SELF (because is_admin would flip)
30. **Last admin guard** — only 1 admin in system, demote → 409 LAST_ADMIN_GUARD
31. **Reset password for Google-only user** — user with `password_hash=NULL` + `google_sub=set` → 409 GOOGLE_ONLY_USER
32. **Audit log for deleted user** — log.user_id points to deleted user → user_email=null in response (no crash)
33. **Manual override survives Stripe webhook** — admin set free→starter+manual_override → simulate Stripe `subscription.updated` event → user.plan unchanged + log "skipped"

### Migration test (1 case)

34. **Bootstrap from ADMIN_EMAILS** — fresh DB + ADMIN_EMAILS=`a@x.com` + create user with that email → init_db runs → user.is_admin=True

### Stripe collision regression (1 case)

35. **Checkout completed wipes manual override** — admin set user manual_override=true + simulate `checkout.session.completed` → user.manual_plan_override=False (Stripe takes over)

---

## ✅ Done Criteria

### Code
- [ ] All 10 endpoints implemented + registered in main.py
- [ ] `users.is_admin` + `users.manual_plan_override` columns added (idempotent migration)
- [ ] Bootstrap seeds ADMIN_EMAILS into is_admin column
- [ ] `_effective_plan()` updated to check is_admin first
- [ ] All 5 Stripe webhook handlers respect `manual_plan_override`
- [ ] `require_admin` dependency works (403 NOT_ADMIN for non-admins)
- [ ] admin.html + admin.js + styles additions complete
- [ ] landing.js redirects admin to `/admin` post-login

### Tests
- [ ] tests/test_admin.py — 35 cases all pass
- [ ] Regression: existing 274/274 tests still pass (LINE bot + auth + Stripe + BYOS)

### Memory
- [ ] APP_VERSION = "8.2.0" ใน config.py
- [ ] pipeline-state.md updated → state="done" หลัง user merge
- [ ] last-session.md updated
- [ ] Session log written
- [ ] Plan moved to archive/

### Manual UX
- [ ] หน้า /admin โหลด + auth guard ทำงาน (non-admin redirect to /app)
- [ ] เปลี่ยน plan ของ user ทดสอบ ผ่าน UI ได้
- [ ] Reset password show ครั้งเดียว + login ด้วยรหัสใหม่ได้
- [ ] Audit log แสดงทุก action ที่ทำ + filter ทำงาน
- [ ] Stripe block warning แสดงเมื่อจะ downgrade user ที่มี active sub

### Security
- [ ] No raw password ใน logs (verify with grep)
- [ ] No JWT bypass — `require_admin` ครอบทุก /api/admin/* endpoint
- [ ] No SQL injection — all queries parameterized
- [ ] No XSS — `escapeHtml()` ใช้ทุก user-supplied string ใน UI

---

## ⚠️ Risks / Open Questions

### Risks

**R1 — Stripe webhook bypass via manual_plan_override**
- **What:** Manual upgrade ผ่าน admin → user ใช้ Starter ฟรี โดย Stripe ไม่ตัดเงิน. Webhook `subscription.created` จะถูก skip
- **Mitigation:** `_handle_checkout_completed()` ล้าง `manual_plan_override = False` เสมอ — ถ้า user จ่ายเงินจริง Stripe takes over (ไม่ตัดเงินคนละครั้ง)
- **Edge case:** ถ้า admin upgrade manual + later user ไป checkout ที่ Stripe จริง → checkout.completed จะ wipe override → ถูกต้อง (Stripe = truth ตั้งแต่ตอนนั้น)

**R2 — JWT ไม่ถูก revoke หลัง deactivate / reset password**
- **What:** User ที่ถูก deactivate / reset password ยังใช้ JWT เดิมได้จนหมดอายุ (24 ชม.)
- **Mitigation:** `get_current_user()` เช็ค `is_active` ทุก request → deactivated user 401 ทันที. แต่ reset password ไม่ kill session = trade-off acceptable
- **Defer:** ถ้าต้อง kill session ทันที → ต้องเพิ่ม `password_changed_at` column + JWT issued_at check (out of scope v8.2.0)

**R3 — Self-lockout via API**
- **What:** Admin DELETE บัญชีตัวเอง / demote ตัวเองเป็น free → ไม่มีใครเข้า /admin ได้
- **Mitigation:** Self-guards (CANNOT_DEMOTE_SELF / CANNOT_DEACTIVATE_SELF / LAST_ADMIN_GUARD)
- **Backup:** ADMIN_EMAILS env ยังเป็น break-glass — ถ้าทุก admin DB ถูกล้างหมด founder email ใน env ยังเข้าได้

**R4 — Listing performance**
- **What:** `get_admin_stats()` loop ผ่าน `os.path.getsize` ทุก file → slow ถ้า users >1000
- **Mitigation:** Acceptable ในสเกล <1000 users (ปัจจุบัน <50). ถ้าโต → cache stats หรือ aggregate column
- **Defer:** เพิ่ม `users.last_seen_at` + `users.cached_storage_mb` ใน v8.3.0 ถ้าจำเป็น

**R5 — Plan filter accuracy**
- **What:** `list_users(plan_filter)` ใช้ `_effective_plan()` post-process → total count ไม่ตรงกับจำนวน returned ถ้า filter
- **Mitigation:** comment ใน response field; UI แสดง warning ถ้าจำเป็น
- **Acceptable:** scope "ง่ายๆ"

### Open Questions (ให้ user ตัดสินใจก่อน build)

**Q1 — UI ใน /app (sidebar) แสดง "Admin Panel" link สำหรับ admin user ไหม?**
- 🟢 ทำ — UX ดี, admin ไม่ต้องจำ URL `/admin`
- 🟡 ไม่ทำ — keep /app clean, admin พิมพ์ URL เอง
- **Default:** 🟢 ทำ (เพิ่ม link เล็กๆ ใน sidebar footer สำหรับ `is_admin === true`)

**Q2 — ADMIN_EMAILS env ยังคงเป็น fallback ตลอดไป หรือ deprecate?**
- 🟢 คงไว้ — เป็น break-glass สำหรับกู้ระบบ
- 🟡 Deprecate — เก็บ logic แค่ migration, หลังจาก seed ครั้งแรกห้ามใช้
- **Default:** 🟢 คงไว้ (ปลอดภัยกว่า, มี runtime cost ต่ำ)

**Q3 — แสดงรหัสผ่าน reset ใน clipboard auto-copy ไหม?**
- 🟢 ทำ — ปุ่ม "คัดลอก" ใน modal show password
- 🟡 ห้าม clipboard — บังคับให้ admin พิมพ์เอง (ปลอดภัยกว่า)
- **Default:** 🟢 มีปุ่ม "คัดลอก" (ตามที่ผมร่าง)

**Q4 — Email notification ถึง user เมื่อ admin เปลี่ยน plan / deactivate?**
- 🟢 ส่ง — UX ดี, user รู้ทันที
- 🟡 ไม่ส่ง — admin บอกเอง (ตามที่ user เลือกใน 2B)
- **Default:** 🟡 ไม่ส่ง (consistent กับ password reset 2B)

**Q5 — i18n สำหรับ /admin?**
- 🟢 ทำ TH+EN เต็ม (เหมือน /app)
- 🟡 TH only — admin คือ founder ไทย, EN ทีหลัง
- **Default:** 🟡 TH only ใน v8.2.0 (ลด scope; ของ /app TH+EN ยังคงเดิม)

ถ้า user ไม่ตอบ → ใช้ default ทุกข้อ

---

## 📌 Notes for นักพัฒนา

### Gotchas

0. **CSS design tokens — verified list (อย่าใช้ที่ไม่มี!)**
   - ✅ ใช้ได้: `--bg-primary` `--bg-secondary` `--bg-card` `--bg-hover` `--bg-active` `--surface-1/2/3` `--border` `--border-hover` `--text-primary` `--text-secondary` `--text-muted` `--accent` `--accent-hover` `--accent-glow` `--success` `--warning` `--error`
   - ❌ ห้ามใช้ (ไม่มีใน shared.css): `--bg-base` `--border-subtle` `--accent-primary` `--accent-tag` `--text-soft` `--accent-blue`
   - **Reusable components จาก shared.css** (อย่า redefine!):
     - `.modal-overlay` + `.modal` + `.modal-header` + `.modal-body` + `.modal-footer`
     - `.btn` + `.btn-primary` + `.btn-outline` + `.btn-ghost` + `.btn-sm` + `.btn-block` + `.btn-close` + `.btn-danger` + `.btn-glow`
     - `.form-group` + `.form-input` + textarea
     - `#toast-container` + `.toast` + `.toast.success/.error/.info`
     - `.hidden`
     - `.is-invalid`
     - `.kebab-btn` + `.kebab-menu` + `.kebab-menu-item`
   - **Verified ของจริง**: ดูที่ [shared.css:16-68](../../legacy-frontend/shared.css#L16-L68) (design tokens) + [shared.css:101-485](../../legacy-frontend/shared.css#L101-L485) (universal atoms)

1. **`pricing.html` กับ `/admin` คนละ stack** — pricing.html มี own JS, อย่า require shared.css/styles.css ตามใจ. admin.html ใช้ pattern เหมือน app.html (load shared.css + styles.css + own admin.js)

2. **Stripe webhook idempotency** — `WebhookLog.event_id` UNIQUE → re-deliver ไม่ทำงานซ้ำ. `manual_plan_override` skip ก็ยัง insert log row (status=processed) — กัน Stripe retry storm

3. **`User.is_admin` กับ `_effective_plan == "admin"`** — สอง concepts:
   - `is_admin` = role flag (DB column boolean)
   - `_effective_plan` = quota plan ("admin" plan = 999999)
   - Admin ที่ DB → ผ่าน `_effective_plan()` ก็ได้ "admin" → quota unlimited
   - ดู logic ใน admin.py `change_user_plan()` ที่ set ทั้ง 2 fields ให้สอดคล้อง

4. **ADMIN_EMAILS env case sensitivity** — เก็บใน config.py:80 เป็น `e.strip().lower()`. ตอน compare ต้อง lower ทุกที่

5. **Pydantic v2 validator** — `@field_validator` ต้องใส่ `@classmethod` ใต้ decorator. ดู pattern ใน main.py:267-281

6. **`Depends(require_admin)` ดึง User object** — ส่ง user เข้าไปใน admin module functions ตรงๆ. อย่าเรียก `get_current_user()` ซ้ำ

7. **DB transaction** — admin.py functions ทำ commit เอง. main.py route handler ไม่ต้อง commit ซ้ำ

8. **Frontend XSS** — ทุก user-supplied string (email, name, reason) ผ่าน `escapeHtml()` ก่อนใส่ DOM. innerHTML = ห้ามใช้กับ raw input

9. **Admin.js auth guard ก่อน render** — `init()` ต้อง await /api/admin/me สำเร็จก่อนจะ remove `.hidden` จาก `#admin-shell`. ถ้า fail = redirect

10. **APP_VERSION sync** — bump 8.1.0 → 8.2.0 ใน:
    - `backend/config.py:12`
    - `legacy-frontend/admin.html` cache-bust query string
    - `legacy-frontend/app.html` `<span class="logo-version">v8.2.0</span>` (line ~165)

### Hidden Constraints

- **SQLite ALTER TABLE limitations** — เพิ่ม column ได้ แต่ DROP/RENAME ไม่ได้ (ทำใน v8.2.0 OK)
- **No async lock บน user row** — race condition ถ้า admin คนละคนเปลี่ยน plan ของ user เดียวกันพร้อมกัน → last write wins. Acceptable (admin team เล็ก)
- **Audit log ใน v8.2.0 อ่านอย่างเดียว** — ไม่มี delete / archive logic. ถ้าใหญ่ → defer cleanup ไป v8.3+
- **Storage stats ไม่ cache** — refresh dashboard = scan disk ทุกครั้ง. Acceptable <1000 files
- **`_handle_checkout_completed()` reset manual_override** — ใน billing.py ต้องเพิ่ม `user.manual_plan_override = False` ใกล้ line 236 (หลัง `user.plan = "starter"`). อย่าลืม

### Reuse Existing Patterns

- **JWT auth** — `Depends(get_current_user)` → ใช้ `require_admin` ครอบทับ
- **Pydantic models** — `class XxxRequest(BaseModel)` + `field_validator` (match google_login pattern)
- **DB migrations** — idempotent ALTER TABLE block ใน `init_db()` (v5.0 → v8.1.0 chain)
- **Audit log** — `await log_audit(db, user_id, event_type, ...)` (มีอยู่แล้ว)
- **Lock/unlock** — `await lock_excess_data() / unlock_data_for_plan()` (มีอยู่แล้ว)
- **Frontend escapeHtml** — copy from app.js
- **Frontend toast** — minimal version ใน admin.js (ไม่ใช้ของ app.js)
- **Frontend authFetch** — copy + simplify (ไม่ต้อง language toggle / debounce)

### Files NOT to touch

- `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`
- `backend/llm.py` — ไม่เกี่ยว LLM pipeline
- `backend/retriever.py` — ไม่เกี่ยว
- `backend/mcp_tools.py` — admin ใน MCP defer (ไม่ทำในรอบนี้)
- `backend/line_bot.py` — admin command ใน LINE defer

---

## 🔄 Pipeline Handoff

หลัง user approve plan นี้:

1. **เขียว** เริ่ม Phase 1 → 2 → 3 → self-test
2. เขียว update `pipeline-state.md` → `building`
3. เขียวเสร็จ → commit แยก 5 commits (DB / Stripe guard / admin module / endpoints / frontend) → update state `built_pending_review`
4. เขียวเขียนใน `inbox/for-ฟ้า.md` แจ้งฟ้า + commit hashes
5. **ฟ้า** review + เขียน tests/test_admin.py (35 cases) → state `reviewing`
6. ฟ้า APPROVE → user merge → state `done` → archive plan

---

## 📊 Summary Card

| Item | Value |
|---|---|
| New endpoints | 10 |
| New backend modules | 1 (`admin.py`) |
| New frontend files | 2 (`admin.html` + `admin.js`) |
| Modified backend files | 4 (database, auth, plan_limits, billing, main, config) |
| Modified frontend files | 2 (styles.css, landing.js) |
| New DB columns | 2 (`users.is_admin`, `users.manual_plan_override`) |
| New audit event types | 6 |
| New tests | 35 |
| Estimated effort | เขียว ~2-3 วัน + ฟ้า ~1 วัน |
| APP_VERSION bump | 8.1.0 → 8.2.0 |
| Risk level | 🟡 Medium (Stripe collision is the main risk, mitigated) |
| User-facing change | Yes (new /admin page) |
| Breaking change | No (backward compat — existing /app unchanged) |
