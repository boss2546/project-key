# 🔁 Restoration Guide — Google Sign-In (login)

> **ลบเมื่อ:** v9.5.0 · 2026-05-14
> **เหตุผลที่ลบ:** ลดความซับซ้อนของ auth flow + race condition ที่ fix ใน v9.4.9 ไม่กลับมา + ลด external dependency
> **อะไรที่ "ไม่" ถูกแตะ:** Google Drive BYOS (drive_oauth.py) ยังคงทำงานเหมือนเดิม — ใช้ env var ตัวเดียวกัน (`GOOGLE_OAUTH_CLIENT_ID`/`SECRET`) แต่คนละ scope

---

## 📌 ก่อน restore — สิ่งที่ต้องเตรียม

1. **Google Cloud Console** — ต้องมี OAuth 2.0 Client ID เดิม (ยังใช้ของ BYOS ได้)
2. **Redirect URI** ต้อง register `https://yourdomain/api/auth/google/callback` ใน Google Console
3. **Env vars** ใน `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID` (เดิม — มีอยู่แล้ว ถ้าใช้ BYOS)
   - `GOOGLE_OAUTH_CLIENT_SECRET` (เดิม)
   - `GOOGLE_LOGIN_REDIRECT_URI=https://yourdomain/api/auth/google/callback` (ใหม่ ถ้าจะ override default)
4. **Existing user data:**
   - `users.google_sub` column **ยังอยู่ใน DB** (ไม่ได้ drop) — restore ทันที = login ได้
   - Google-only users (`password_hash IS NULL`) ที่ login ไม่ได้ตอน v9.5.0 → restore เสร็จจะ login ได้เลย

---

## 🛠️ Restore Steps (5 phases · ~30 นาที)

### Phase 1 — สร้างไฟล์ `backend/google_login.py`

สร้างไฟล์ใหม่ที่ [backend/google_login.py](../../backend/google_login.py) ด้วยเนื้อหานี้:

```python
"""Google Sign-In OAuth 2.0 flow — login-only, separate จาก Drive BYOS."""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import time
from typing import Optional, TypedDict

# Google scope aliases — relax oauthlib check
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from .config import (
    GOOGLE_LOGIN_REDIRECT_URI,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    is_google_login_configured,
)

logger = logging.getLogger(__name__)

LOGIN_SCOPES: list[str] = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class _StateEntry(TypedDict):
    expires: float
    code_verifier: str


_GLOGIN_STATE_CACHE: dict[str, _StateEntry] = {}
_GLOGIN_TTL_SECONDS = 600


def _cleanup_expired_states() -> None:
    now = time.time()
    expired = [s for s, info in _GLOGIN_STATE_CACHE.items() if info["expires"] < now]
    for s in expired:
        _GLOGIN_STATE_CACHE.pop(s, None)


def _build_login_flow():
    from google_auth_oauthlib.flow import Flow

    if not is_google_login_configured():
        raise RuntimeError(
            "Google login ยังไม่ได้ configure — set GOOGLE_OAUTH_CLIENT_ID + "
            "GOOGLE_OAUTH_CLIENT_SECRET ก่อน"
        )

    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_LOGIN_REDIRECT_URI],
            }
        },
        scopes=LOGIN_SCOPES,
        redirect_uri=GOOGLE_LOGIN_REDIRECT_URI,
    )


def init_google_login() -> dict[str, str]:
    _cleanup_expired_states()
    flow = _build_login_flow()
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    _GLOGIN_STATE_CACHE[state] = {
        "expires": time.time() + _GLOGIN_TTL_SECONDS,
        "code_verifier": code_verifier,
    }

    auth_url, _ = flow.authorization_url(
        prompt="select_account",
        include_granted_scopes="true",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return {"auth_url": auth_url}


class _GLoginResult(TypedDict):
    google_sub: str
    email: str
    email_verified: bool
    name: str
    picture: Optional[str]


def _verify_id_token(id_token_jwt: str) -> dict:
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_jwt,
            GoogleRequest(),
            audience=GOOGLE_OAUTH_CLIENT_ID,
            clock_skew_in_seconds=60,
        )
    except ValueError as e:
        logger.error("verify_oauth2_token ValueError: %s", e)
        raise RuntimeError(f"Google ID token verification failed: {e}") from e
    except Exception as e:
        logger.exception("verify_oauth2_token unexpected error: %s", e)
        raise RuntimeError(f"Google ID token verification failed (unexpected): {e}") from e

    iss = idinfo.get("iss")
    if iss not in ("https://accounts.google.com", "accounts.google.com"):
        raise RuntimeError(f"Google ID token has unexpected issuer: {iss}")
    return idinfo


async def handle_google_callback(code: str, state: str) -> _GLoginResult:
    _cleanup_expired_states()
    state_info = _GLOGIN_STATE_CACHE.pop(state, None)
    if not state_info:
        raise ValueError("INVALID_OAUTH_STATE — state ไม่ตรง / ใช้ไปแล้ว / หมดอายุ")

    flow = _build_login_flow()
    try:
        flow.fetch_token(code=code, code_verifier=state_info["code_verifier"])
    except Exception as e:
        raise RuntimeError(f"Google token exchange failed: {e}") from e

    creds = flow.credentials
    id_token_jwt = getattr(creds, "id_token", None)
    if not id_token_jwt:
        raise RuntimeError("Google did not return id_token — check 'openid' scope")

    idinfo = _verify_id_token(id_token_jwt)
    email = idinfo.get("email", "").lower().strip()
    if not email:
        raise RuntimeError("Google ID token missing email claim")
    sub = idinfo.get("sub", "")
    if not sub:
        raise RuntimeError("Google ID token missing sub claim")

    return {
        "google_sub": sub,
        "email": email,
        "email_verified": bool(idinfo.get("email_verified", False)),
        "name": idinfo.get("name", "") or "",
        "picture": idinfo.get("picture"),
    }


def _reset_state_cache_for_testing() -> None:
    _GLOGIN_STATE_CACHE.clear()
```

---

### Phase 2 — `backend/config.py` (เพิ่ม config)

หา block comment ที่เขียนว่า `# Google Sign-In removed in v9.5.0` (ประมาณบรรทัด 200) แล้วแทนด้วย:

```python
# ─── Google Sign-In ───
GOOGLE_LOGIN_REDIRECT_URI = os.getenv(
    "GOOGLE_LOGIN_REDIRECT_URI",
    f"{APP_BASE_URL}/api/auth/google/callback",
)


def is_google_login_configured() -> bool:
    """True ถ้า Google Sign-In พร้อม (Client ID + Secret)."""
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
```

---

### Phase 3 — `backend/auth.py` (เพิ่ม `login_or_create_google_user` กลับ)

ที่ท้ายไฟล์ [backend/auth.py](../../backend/auth.py) (หลัง `reset_password` function) เพิ่ม:

```python
# ═══════════════════════════════════════════
# GOOGLE SIGN-IN
# ═══════════════════════════════════════════

async def login_or_create_google_user(
    db: AsyncSession,
    google_sub: str,
    email: str,
    name: str,
) -> dict:
    """Find user by google_sub → fallback email → create if not found. Returns JWT."""
    email_lower = (email or "").lower().strip()
    if not email_lower or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {"code": "INVALID_GOOGLE_PAYLOAD",
                          "message": "Google response missing email or sub"}
            },
        )

    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if user:
        if user.email != email_lower:
            logger.info(f"Google email changed for user {user.id}: {user.email} → {email_lower}")
            user.email = email_lower
            await db.commit()
    else:
        result = await db.execute(select(User).where(User.email == email_lower))
        user = result.scalar_one_or_none()

        if user:
            user.google_sub = google_sub
            await db.commit()
            logger.info(f"Linked Google to existing user: {user.email} ({user.id})")
        else:
            import secrets as _secrets
            from .database import gen_id
            user = User(
                id=gen_id(),
                name=name or "User",
                email=email_lower,
                password_hash=None,
                google_sub=google_sub,
                is_active=True,
                mcp_secret=_secrets.token_urlsafe(32),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"New Google user created: {user.email} ({user.id})")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(user.id, user.email, user.name)
    return {
        "user": {
            "id": user.id, "name": user.name, "email": user.email,
            "mcp_secret": user.mcp_secret,
        },
        "token": token,
    }
```

แล้วใน `login_user` (ประมาณบรรทัด 127) เปลี่ยน:
```python
if not user.password_hash or not verify_password(password, user.password_hash):
```
กลับเป็น:
```python
if not user.password_hash:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "USE_GOOGLE_LOGIN",
                          "message": "บัญชีนี้สมัครด้วย Google — กรุณาคลิก 'Sign in with Google'"}},
    )
if not verify_password(password, user.password_hash):
    raise HTTPException(...)  # เหมือนเดิม
```

---

### Phase 4 — `backend/main.py` (เพิ่ม endpoints + import)

ใน import block (บรรทัด 39):
```python
from .auth import register_user, login_user, get_current_user, get_optional_user, request_password_reset, reset_password, login_or_create_google_user, require_admin
```

หลัง `api_reset_password` endpoint (ประมาณบรรทัด 175-180) เพิ่ม:

```python
# ═══════════════════════════════════════════
# Google Sign-In endpoints
# ═══════════════════════════════════════════

@app.get("/api/auth/google/init")
async def api_google_login_init():
    from .config import is_google_login_configured
    if not is_google_login_configured():
        return JSONResponse(
            {"error": {"code": "GOOGLE_LOGIN_NOT_CONFIGURED",
                       "message": "Google login not configured on this server"}},
            status_code=503,
        )
    from . import google_login
    try:
        return google_login.init_google_login()
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "GLOGIN_INIT_FAILED", "message": str(e)}},
        )


@app.get("/api/auth/google/callback")
async def api_google_login_callback(
    code: str = "", state: str = "", error: str = "",
    db: AsyncSession = Depends(get_db),
):
    from . import google_login

    if error:
        return RedirectResponse(f"/?google_error={error}", status_code=302)
    if not code or not state:
        return RedirectResponse("/?google_error=missing_params", status_code=302)

    try:
        result = await google_login.handle_google_callback(code, state)
    except ValueError as e:
        logger.warning("Google callback invalid_state: %s", e)
        return RedirectResponse("/?google_error=invalid_state", status_code=302)
    except RuntimeError as e:
        logger.error("Google callback invalid_id_token: %s", e)
        return RedirectResponse("/?google_error=invalid_id_token", status_code=302)
    except Exception as e:
        logger.exception("Google callback unexpected error: %s", e)
        return RedirectResponse("/?google_error=google_api_error", status_code=302)

    if not result.get("email_verified"):
        return RedirectResponse("/?google_error=email_not_verified", status_code=302)

    try:
        login_result = await login_or_create_google_user(
            db, google_sub=result["google_sub"],
            email=result["email"], name=result["name"] or "User",
        )
    except HTTPException as e:
        logger.warning("Google login user creation rejected: %s", e.detail)
        return RedirectResponse("/?google_error=account_disabled", status_code=302)
    except Exception as e:
        logger.exception("Google upsert unexpected error: %s", e)
        return RedirectResponse("/?google_error=internal_error", status_code=302)

    return RedirectResponse(f"/app#token={login_result['token']}", status_code=302)
```

---

### Phase 5 — Frontend

#### 5a. `legacy-frontend/landing.js`

ก่อน `function doRegister()` เพิ่ม `doGoogleLogin()`:

```javascript
async function doGoogleLogin() {
 try {
 const r = await fetch('/api/auth/google/init', { headers: { 'Accept': 'application/json' } });
 if (r.status === 503) {
  showToast(getLang() === 'th' ? 'Google Sign-In ยังไม่พร้อมใช้งาน' : 'Google Sign-In is not configured', 'error');
  return;
 }
 if (!r.ok) {
  showToast(getLang() === 'th' ? 'เริ่มต้น Google Sign-In ไม่สำเร็จ' : 'Failed to start Google Sign-In', 'error');
  return;
 }
 const data = await r.json();
 if (data.auth_url) window.location.assign(data.auth_url);
 else showToast(getLang() === 'th' ? 'ลิงก์ไม่ถูกต้อง' : 'Invalid auth URL', 'error');
 } catch (e) {
 showToast(getLang() === 'th' ? 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้' : 'Cannot connect to server', 'error');
 }
}
```

ก่อน `function initAuth()` เพิ่ม `_handleGoogleLoginFragment` + `_handleGoogleLoginError`:

```javascript
function _handleGoogleLoginFragment() {
 const hash = window.location.hash || '';
 if (!hash.startsWith('#token=')) return false;
 const jwt = hash.slice('#token='.length);
 if (!jwt || jwt.split('.').length !== 3) return false;
 try {
  const payloadB64 = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
  const padded = payloadB64 + '='.repeat((4 - payloadB64.length % 4) % 4);
  const payload = JSON.parse(atob(padded));
  state.authToken = jwt;
  state.currentUser = { id: payload.sub, email: payload.email, name: payload.name };
  localStorage.setItem('pdb_token', jwt);
  localStorage.setItem('pdb_user', JSON.stringify(state.currentUser));
  window.history.replaceState({}, document.title, '/app');
  if (_redirectToPendingLineLink()) return true;
  _isInitVerified = true;
  showToast(getLang() === 'th' ? 'เข้าสู่ระบบสำเร็จ! กำลังโหลด...' : 'Signed in! Loading...', 'success');
  fetch('/api/admin/me', { headers: { 'Authorization': 'Bearer ' + jwt } })
   .then(res => {
    try {
     sessionStorage.setItem('pdb_admin_probe', res.ok ? '1' : '0');
     sessionStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
    } catch (_) {}
    if (res.ok) window.location.href = '/admin';
    else if (showApp()) initAppData();
   })
   .catch(() => { if (showApp()) initAppData(); });
  return true;
 } catch (e) { return false; }
}

function _handleGoogleLoginError() {
 const params = new URLSearchParams(window.location.search);
 const gErr = params.get('google_error');
 if (!gErr) return;
 const isTH = getLang() === 'th';
 const messages = {
  access_denied: isTH ? 'คุณยกเลิกการเข้าสู่ระบบ Google' : 'You canceled Google sign-in',
  invalid_state: isTH ? 'ลิงก์หมดอายุ กรุณาลองใหม่' : 'Login link expired',
  invalid_id_token: isTH ? 'Google ID token ไม่ถูกต้อง' : 'Invalid Google ID token',
  email_not_verified: isTH ? 'อีเมล Google ยังไม่ verified' : 'Google email is not verified',
  google_api_error: isTH ? 'Google API ขัดข้อง' : 'Google API error',
  missing_params: isTH ? 'ลิงก์ callback ไม่สมบูรณ์' : 'Incomplete callback URL',
  account_disabled: isTH ? 'บัญชีนี้ถูกปิดใช้งาน' : 'This account is deactivated',
  internal_error: isTH ? 'เกิดข้อผิดพลาดในระบบ' : 'Internal server error',
 };
 showToast(messages[gErr] || (isTH ? 'เกิดข้อผิดพลาด' : 'An error occurred'), 'error');
 const url = new URL(window.location.href);
 url.searchParams.delete('google_error');
 window.history.replaceState({}, document.title, url.pathname + (url.search || '') + url.hash);
}
```

ใน `initAuth()` บรรทัดแรกของ function (ก่อน "v9.3.0 — ถ้า user logged in อยู่แล้ว..."):

```javascript
function initAuth() {
 // ⚠️ ต้อง run ก่อน check authToken — Google callback ส่งกลับ /app#token=...
 if (_handleGoogleLoginFragment()) return;
 _handleGoogleLoginError();

 // v9.3.0 — ถ้า user logged in อยู่แล้ว ... (เดิม)
 ...
```

ในส่วน event listener (ใน initAuth หลัง `btn-register`):

```javascript
 document.getElementById('btn-google-login-login')?.addEventListener('click', doGoogleLogin);
 document.getElementById('switch-to-login-google')?.addEventListener('click', (e) => {
  e.preventDefault();
  showAuthModal('login');
  setTimeout(() => document.getElementById('btn-google-login-login')?.focus(), 100);
 });
```

ใน `doLogin()` หลัง `if (!res.ok) {` เพิ่ม USE_GOOGLE_LOGIN handling:

```javascript
 const errCode = data?.detail?.error?.code;
 if (errCode === 'USE_GOOGLE_LOGIN') {
  errorEl.innerHTML = 'บัญชีนี้สมัครด้วย Google — ' +
    '<a href="#" id="login-error-google-link">คลิกเพื่อ Sign in with Google</a>';
  errorEl.classList.remove('hidden');
  document.getElementById('login-error-google-link')?.addEventListener('click', (e) => {
   e.preventDefault();
   doGoogleLogin();
  });
  return;
 }
```

#### 5b. `legacy-frontend/landing.html` + `app.html`

ใน login form ทั้ง 2 ไฟล์ — หลัง `<button class="btn btn-primary btn-block" id="btn-login">เข้าสู่ระบบ</button>` เพิ่ม:

```html
<div class="auth-divider"><span>หรือ</span></div>
<button type="button" class="btn btn-google btn-block" id="btn-google-login-login">
 <svg class="btn-google-icon" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
  <path fill="#4285F4" d="M17.64 9.2a10.34 10.34 0 0 0-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92a8.78 8.78 0 0 0 2.68-6.62z"/>
  <path fill="#34A853" d="M9 18a8.6 8.6 0 0 0 5.96-2.18l-2.92-2.26a5.4 5.4 0 0 1-8.06-2.84H.96v2.32A9 9 0 0 0 9 18z"/>
  <path fill="#FBBC05" d="M3.96 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.28-1.72V4.96H.96A9 9 0 0 0 0 9c0 1.45.34 2.83.96 4.04l3-2.32z"/>
  <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.46 3.44 1.36l2.58-2.58A8.6 8.6 0 0 0 9 0 9 9 0 0 0 .96 4.96l3 2.32A5.4 5.4 0 0 1 9 3.58z"/>
 </svg>
 <span>Continue with Google</span>
</button>
<p class="auth-switch auth-switch-muted">ใช้ Google ครั้งแรก = สมัครอัตโนมัติ · ครั้งถัดไป = login</p>
```

ใน register form หลัง `<a href="#" id="switch-to-login">เข้าสู่ระบบ</a></p>` เพิ่ม:
```html
<p class="auth-switch auth-switch-muted">หรือ <a href="#" id="switch-to-login-google">ใช้ Google เข้าระบบ →</a> (สมัครให้อัตโนมัติถ้ายังไม่มีบัญชี)</p>
```

---

### Phase 6 — `backend/admin.py` (เพิ่ม guard กลับ)

ใน `reset_user_password` function ก่อน `target.password_hash = hash_password(new_password)` เพิ่ม:

```python
if not target.password_hash and target.google_sub:
    raise HTTPException(
        status_code=409,
        detail={"error": {
            "code": "GOOGLE_ONLY_USER",
            "message": "ผู้ใช้นี้สมัครด้วย Google เท่านั้น — ไม่มีรหัสผ่านในระบบ",
        }},
    )
```

---

## ✅ Smoke test หลัง restore

```bash
# 1. Import smoke test
python -c "from backend.main import app; print(len([r for r in app.routes if hasattr(r, 'path')]))"
# Expected: 124 routes (v9.5.0 = 122, restore + 2 google endpoints = 124)

# 2. Boot dev server
python -m uvicorn backend.main:app --reload --port 8000

# 3. Test endpoints
curl http://localhost:8000/api/auth/google/init     # → 200 with auth_url OR 503 if not configured
```

## 🧪 Manual UI test

1. เปิด `http://localhost:8000/` (landing page)
2. คลิก "เข้าสู่ระบบ" → modal ต้องแสดงปุ่ม "Continue with Google"
3. คลิก Google button → redirect ไป accounts.google.com
4. Consent → redirect กลับ `/app#token=<jwt>` → fragment handler save token → app loads

## 📊 Files changed in this restoration

| File | Action |
|---|---|
| `backend/google_login.py` | **CREATE** (Phase 1) |
| `backend/config.py` | Edit — add `GOOGLE_LOGIN_REDIRECT_URI` + `is_google_login_configured` |
| `backend/auth.py` | Edit — add `login_or_create_google_user` + restore USE_GOOGLE_LOGIN in `login_user` |
| `backend/main.py` | Edit — add import + 2 endpoints |
| `backend/admin.py` | Edit — restore GOOGLE_ONLY_USER guard in `reset_user_password` |
| `legacy-frontend/landing.js` | Edit — add 3 functions + event listeners + login error handler |
| `legacy-frontend/landing.html` | Edit — add Google button to login form + "หรือใช้ Google" link in register form |
| `legacy-frontend/app.html` | Edit — same as landing.html |

---

## 💡 Notes

- **ไม่ต้อง drop `users.google_sub` column** — มันอยู่ใน DB อยู่แล้ว ไม่ต้อง migrate
- **Existing Google-only users** (ที่ register ก่อน v9.5.0): หลัง restore = login ได้ทันที (`google_sub` ยังเก็บอยู่)
- **Drive BYOS ไม่กระทบ** ทั้งก่อนและหลัง restore — คนละ flow, คนละ scope, ใช้ env vars เดียวกัน
- ถ้าจะลด complexity ต่อ → ลอง `google_sub` lookup ใน `auth.py` ออก แล้วใช้ email-only matching ก็ได้ (เสี่ยงเรื่อง user เปลี่ยน Google email แต่ลด code ลง 1 query)

---

**Source code snapshot:** ดู git history ของ commit ก่อน v9.5.0 (master HEAD = `406387a` v9.4.9) — มี `backend/google_login.py` พร้อม comments เต็มรูปแบบ
