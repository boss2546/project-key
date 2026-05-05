# Plan: Google Sign-In + Email-or-Google Account Resolution (v8.1.0)

**Author:** เขียว (Khiao) — drafted in single-agent 3-in-1 mode per user authorization 2026-05-04
**Date:** 2026-05-04
**Status:** approved (user said "ดำเนินการตามคุณว่าได้เลย" — confirmed all Q1–Q7 recommended defaults)
**Foundation:** v8.0.7 master HEAD `0f68de8`
**Target version:** 8.1.0
**Estimated:** เขียว ~10–11 ชม. + ฟ้า ~3–4 ชม.

---

## Goal

ผู้ใช้ register / login PDB ด้วย Google account ได้ในคลิกเดียว — แยกเป็น OAuth flow ของตัวเอง ไม่รวมกับ Drive BYOS เพื่อให้ consent screen สั้น (conversion ดี) และ user ที่ไม่อยาก connect Drive ก็ login ได้

**Strategy:** Reuse Google Cloud project + `GOOGLE_OAUTH_CLIENT_ID/SECRET` + PKCE/CSRF pattern จาก [drive_oauth.py](../../backend/drive_oauth.py) — ไม่ duplicate infrastructure

**Out-of-scope (defer):**
- Sign in with LINE standalone (LINE Login channel ตั้งไว้แต่ยังเป็น account-link only)
- 2FA / TOTP, password change endpoint, sessions list, logout-everywhere
- Account settings UI สำหรับ unlink/manage login methods
- Manual account merge ระหว่าง 2 PDB accounts ที่ user สมัครแยก

---

## Files to Create / Modify

### NEW (3)
- `backend/google_login.py` — ~150 lines — Login OAuth flow (parallel with `drive_oauth.py`)
- `tests/test_google_login_v8_1.py` — ~15 cases (สำหรับ ฟ้า เขียน)
- `plans/google-login-v8.1.0.md` — ไฟล์นี้

### MODIFY (8)
- `backend/database.py` — `User.google_sub` column + idempotent migration + unique index
- `backend/config.py` — `GOOGLE_LOGIN_REDIRECT_URI` + `is_google_login_configured()` + APP_VERSION bump 8.0.7→8.1.0
- `backend/auth.py` — `login_or_create_google_user()` + `USE_GOOGLE_LOGIN` error
- `backend/main.py` — `GET /api/auth/google/init` + `GET /api/auth/google/callback`
- `legacy-frontend/landing.html` — Google button + divider บน auth-modal (login + register forms)
- `legacy-frontend/landing.js` — `doGoogleLogin()` + `#token=` fragment handler + `?google_error=` handler + `USE_GOOGLE_LOGIN` toast
- `legacy-frontend/styles.css` — `.btn-google` + `.auth-divider`
- `legacy-frontend/app.js` — i18n strings (TH+EN, 4 keys ใหม่)

### External (5 นาที — User action)
- Google Cloud Console → OAuth Client → เพิ่ม redirect URIs:
  - `https://personaldatabank.fly.dev/api/auth/google/callback`
  - `http://localhost:8000/api/auth/google/callback` (dev)
- ❌ ไม่ต้องเพิ่ม Fly.io secrets — ใช้ `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` ตัวเดียวกับ Drive

---

## API Changes

### `GET /api/auth/google/init` (NEW)
- Auth: none (public)
- Response 200: `{ "auth_url": "https://accounts.google.com/o/oauth2/auth?..." }`
- Response 503: `{ "error": { "code": "GOOGLE_LOGIN_NOT_CONFIGURED", "message": "..." } }`
- Server: เก็บ `state` + `code_verifier` ใน `_GLOGIN_STATE_CACHE` (TTL 10 นาที)
- Frontend: `window.location.assign(auth_url)`

### `GET /api/auth/google/callback?code=...&state=...&error=...` (NEW)
- Auth: none (CSRF state + PKCE คุ้มกัน)
- Behavior: 302 redirect (ไม่คืน JSON)
- Success: `Location: /app#token=<jwt>` (fragment ไม่ใช่ query — กัน Referer leak)
- Failure: `Location: /?google_error=<reason>` (frontend แสดง toast)
- Error reasons: `access_denied`, `invalid_state`, `invalid_id_token`, `email_not_verified`, `google_api_error`, `missing_params`

### `POST /api/auth/login` (MODIFY)
- เพิ่ม case ใหม่: ถ้า user มี + `password_hash IS NULL` (Google-only) → 401:
  ```json
  { "detail": { "error": { "code": "USE_GOOGLE_LOGIN",
                            "message": "บัญชีนี้สมัครด้วย Google" } } }
  ```
- Other 401 ยังเป็น generic "Invalid email or password" (anti-enumeration)

---

## Data Model Changes

### `users` table — ADD column
```python
google_sub = Column(String, nullable=True, unique=True, index=True)
```
- Stable Google user ID (subject claim) — ตรงข้ามกับ email ที่เปลี่ยนได้
- Lookup priority: `google_sub` → fallback `email` (case-insensitive)
- Unique constraint: 1 Google account = 1 PDB user
- Backward compat: existing users เก็บ NULL ใช้งานปกติ

### Migration (idempotent — pattern ตามตัวอื่นใน [database.py:566+](../../backend/database.py#L566))
```python
if "google_sub" not in user_cols_v8_1:
    await db.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub "
        "ON users(google_sub)"
    )
    migrated = True
    print("  → Added: users.google_sub (Google login)")
```

---

## OAuth Scopes (Login flow)

```python
LOGIN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
```

**ต่างจาก Drive (`drive_oauth.py:46`):**
- ไม่ขอ `drive.file` → consent screen สั้น
- ไม่ขอ `access_type=offline` → ไม่ขอ refresh_token → **ไม่ต้อง encrypt + เก็บ DB**
- ไม่ใช้ `_get_fernet()` (ตัด dependency บน `DRIVE_TOKEN_ENCRYPTION_KEY`)

**Verification (Google Cloud):**
- `openid + email + profile` = non-sensitive → 1–3 วัน ฟรี
- รวมกับ `drive.file` ที่ verify อยู่ = ไม่เพิ่มภาระ

---

## Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Schema migration (~15 นาที)
1. `backend/database.py:19` (User class) — เพิ่ม `google_sub = Column(...)`
2. เพิ่ม migration block ใน `init_db()` หลัง v8.0.0 LineUser block (ราว line 738)
3. ทดสอบ: ลบ projectkey.db local → start server → check column มี

### Step 2: Config helpers (~30 นาที)
4. `backend/config.py` หลัง LINE block:
   ```python
   GOOGLE_LOGIN_REDIRECT_URI = os.getenv(
       "GOOGLE_LOGIN_REDIRECT_URI",
       f"{APP_BASE_URL}/api/auth/google/callback",
   )

   def is_google_login_configured() -> bool:
       return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
   ```
5. `backend/config.py:12` — `APP_VERSION = "8.1.0"`

### Step 3: `backend/google_login.py` (~2 ชม.)
6. Copy boilerplate จาก `drive_oauth.py` แล้วแก้:
   - แยก `_GLOGIN_STATE_CACHE` (ไม่แชร์กับ Drive)
   - `LOGIN_SCOPES` (ดูข้างบน)
   - `_build_login_flow()` — ใช้ `GOOGLE_LOGIN_REDIRECT_URI`
   - `init_google_login() -> dict` — ไม่รับ `user_id` (ผู้ใช้ยังไม่ login)
   - `_verify_id_token(jwt) -> dict`:
     ```python
     from google.oauth2 import id_token
     from google.auth.transport.requests import Request as GoogleRequest
     idinfo = id_token.verify_oauth2_token(
         jwt, GoogleRequest(),
         audience=GOOGLE_OAUTH_CLIENT_ID,
         clock_skew_in_seconds=10,
     )
     return idinfo
     ```
   - `handle_google_callback(code, state) -> _GLoginResult` — fetch_token แล้ว verify ID token เอง
7. ❌ **ห้าม trust ID token** จาก `flow.credentials.id_token` ตรงๆ ต้อง verify signature เอง
8. Result type:
   ```python
   class _GLoginResult(TypedDict):
       google_sub: str        # idinfo["sub"]
       email: str             # idinfo["email"]
       email_verified: bool   # idinfo["email_verified"]
       name: str              # idinfo.get("name", "")
       picture: str | None    # idinfo.get("picture")
   ```

### Step 4: `auth.py` upsert logic (~1.5 ชม.)
9. เพิ่ม `login_or_create_google_user(db, google_sub, email, name) -> dict`:
   - Lookup by `google_sub` → if found: update email if changed → return JWT
   - else lookup by `email` (lower) → if found: link (set google_sub) → return JWT
   - else: INSERT (password_hash=NULL, mcp_secret generated, google_sub set)
   - Return shape เดียวกับ `login_user()`: `{"user": {...}, "token": jwt}`
10. แก้ `login_user()` ก่อนเรียก `verify_password`:
    ```python
    if user and not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail={"error": {
                "code": "USE_GOOGLE_LOGIN",
                "message": "บัญชีนี้สมัครด้วย Google — กรุณาคลิก 'Sign in with Google'",
            }},
        )
    ```

### Step 5: `main.py` endpoints (~1.5 ชม.)
11. เพิ่ม `GET /api/auth/google/init` หลัง `/api/auth/reset-password` (line ~159):
    - 503 ถ้า `is_google_login_configured()` false
    - `try: return google_login.init_google_login()` / except `RuntimeError`
12. เพิ่ม `GET /api/auth/google/callback`:
    - Read query: code, state, error
    - error → `RedirectResponse(f"/?google_error={error}")`
    - missing code/state → redirect with `missing_params`
    - try `handle_google_callback`:
      - ValueError → `invalid_state`
      - RuntimeError → `invalid_id_token`
      - other → `google_api_error`
    - `email_verified=false` → `email_not_verified`
    - call `login_or_create_google_user()`
    - return `RedirectResponse(f"/app#token={jwt}", status_code=302)`

### Step 6: Frontend UI (~3 ชม.)
13. `landing.html` — เพิ่มในต้น `#login-form` และ `#register-form`:
    - ปุ่ม `<button class="btn btn-google btn-block" id="btn-google-login-X">` (X=login/register, ID ต่างกัน)
    - SVG: official Google G logo (4 colors — ใส่ inline)
    - Divider `<div class="auth-divider"><span>หรือ</span></div>` ระหว่าง social + email
14. `landing.js`:
    - `doGoogleLogin()` — fetch `/api/auth/google/init` → check 503 → `window.location.assign(auth_url)`
    - Wire ปุ่มใน `initAuth()` (2 IDs: btn-google-login-login + btn-google-login-register)
    - `#token=` fragment handler ที่หัว `initAuth()`:
      - parse hash → decode JWT payload (atob middle segment)
      - localStorage save token + user
      - `history.replaceState({}, document.title, '/app')`
      - `_isInitVerified = true; if (showApp()) initAppData(); showToast('เข้าสู่ระบบสำเร็จ!')`
    - `?google_error=` handler — toast translated message
    - `doLogin()` error: ถ้า `errCode === 'USE_GOOGLE_LOGIN'` → แสดง hint + ลิงก์ปุ่ม
15. `styles.css`:
    - `.btn-google` (white bg, 1px #dadce0 border, hover #f8f9fa)
    - `.auth-divider` (flex + ::before/::after lines)
16. `app.js` I18N dict — เพิ่ม 4 keys:
    - `auth.signInWithGoogle`, `auth.or`, `auth.useGoogleHint`, `auth.emailNotVerified`

### Step 7: Self-test 10 scenarios (~1.5 ชม.)
17. Local manual test (ห้าม fly deploy):
    1. ปุ่ม Google login → consent → กลับมา → login (new user) สำเร็จ + check users.google_sub ใน DB
    2. Re-login same Google account → user เดิม ไม่ duplicate
    3. Register email/password → logout → Google sign in ด้วย email เดียวกัน → google_sub ถูก set, user.id เดิม
    4. Login email/password ของ Google-only user → toast "บัญชีนี้สมัครด้วย Google"
    5. Cancel ที่ Google consent → toast "ยกเลิก"
    6. unset env vars → 503 + toast
    7. State expired (mock) → toast "invalid_state"
    8. Existing flow regression — login email/password ของ user มี password ปกติ ทำงานเหมือนเดิม
    9. localStorage `pdb_token` set ถูก + `/api/auth/me` ตอบ 200 หลัง Google login
    10. `/reset-password?token=...` ยังทำงานปกติ (no regress)

### Step 8: Test scenarios (สำหรับ ฟ้า — ห้ามเขียวเขียน)
- Happy paths (5): init OK / callback create user / re-login / link existing email user / email change in Google sync
- Security (5): invalid state / expired state / tampered ID token / wrong audience / email_verified=false
- Errors (3): access_denied / 503 unset / missing params
- Edge (2): concurrent inits / `USE_GOOGLE_LOGIN` 401 from /login
- **Total ~15 cases** + mock pattern follows `tests/test_auth_password_reset_v7_6.py:14`

---

## Done Criteria
- [ ] Code compile + import ไม่ error
- [ ] Migration idempotent (รัน 2 ครั้ง safe)
- [ ] Self-test 10 scenarios pass on local (manual)
- [ ] Existing tests pass (LINE bot 274 + auth + regression)
- [ ] No secrets in code, no debug print
- [ ] APP_VERSION 8.0.7 → 8.1.0 (config.py + package.json sync)
- [ ] Memory updated (pipeline-state, last-session, active-tasks, session log)
- [ ] Commits separate logical (5 commits — ดู Pipeline)

---

## Risks (decided — accepted)

**R1 — Auto-link by email = takeover risk if Google account compromised** ✅ accept (industry standard, Google verifies email_verified=true ให้)
**R2 — Verification testing mode (max 100)** ✅ accept (build now, submit verify before public launch — 1–3 วัน turnaround)
**R3 — Race: 2 callbacks concurrent** ✅ handle (UNIQUE constraint + retry on IntegrityError)

---

## Open Questions — Resolved (user approved all defaults)

| # | Question | Decision |
|---|---|---|
| Q1 | Token delivery: fragment vs query | ✅ Fragment (`#token=`) — กัน Referer leak |
| Q2 | Google-only user wrong password → ตอบอะไร | ✅ Toast hint (option A) — UX > strict anti-enumeration |
| Q3 | Block password reset สำหรับ Google-only | ✅ Allow (option A) — flexibility |
| Q4 | i18n location | ✅ I18N dict ใน `app.js` (consistent pattern) |
| Q5 | Verification timing | ✅ Build first, submit before public launch |
| Q6 | Bundle กับ auth-hardening Level 1 | ✅ Standalone — ship Google login เร็ว, security plan แยก |
| Q7 | Test mocking strategy | ✅ Patch `google.oauth2.id_token.verify_oauth2_token` (ฟ้าทำ) |

---

## Pipeline / Author convention

- **Author-Agent:** เขียว (Khiao) ทุก commit (3-in-1 mode authorized)
- **State updates:**
  - Pre-build: `pipeline-state.md` → `building`
  - Post-build + tests pass: → `built_pending_review`
  - 3-in-1 self-review: → `done`
- **Branch:** master (ตาม pattern v8.0.x — ทุก commit อยู่บน master)
- **Commit hashes (planned):**
  1. `feat(db): add users.google_sub column + migration`
  2. `feat(auth): google_login module + login_or_create_google_user`
  3. `feat(api): /api/auth/google/init + /callback endpoints`
  4. `feat(frontend): Sign in with Google button + token fragment handler`
  5. `chore: bump APP_VERSION 8.1.0 + memory + plan archive`

---

## Time Budget

| Phase | Time | Owner |
|---|---|---|
| Step 1 — Schema | 15 นาที | เขียว |
| Step 2 — Config + APP_VERSION | 30 นาที | เขียว |
| Step 3 — `google_login.py` | 2 ชม. | เขียว |
| Step 4 — `auth.py` upsert | 1.5 ชม. | เขียว |
| Step 5 — `main.py` endpoints | 1.5 ชม. | เขียว |
| Step 6 — Frontend UI | 3 ชม. | เขียว |
| Step 7 — Self-test 10 scenarios | 1.5 ชม. | เขียว |
| Step 8 — ฟ้า tests | 3–4 ชม. | ฟ้า |
| External setup | 30 นาที | User |
| **Total Build** | **~10–11 ชม.** | |
| **Total + Review** | **~14–15 ชม.** | |

= **1.5–2 working days**
