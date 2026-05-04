"""Google Sign-In OAuth 2.0 flow (v8.1.0) — login-only, separate จาก Drive BYOS.

หน้าที่:
  - สร้าง auth URL พร้อม CSRF state + PKCE S256 (init_google_login)
  - แลก code → ID token → verify signature + audience + email_verified (handle_google_callback)
  - คืน {google_sub, email, email_verified, name, picture} ให้ caller (main.py endpoint) ไป
    upsert User ผ่าน auth.login_or_create_google_user

ทำไมแยก module นี้จาก drive_oauth.py?
  - drive_oauth.py = ขอ scope drive.file + offline access → เก็บ refresh_token (Fernet encrypted)
  - google_login.py = ขอ scope openid+email+profile + ไม่ต้องการ refresh_token → ไม่เก็บ token
  - Login flow user ยังไม่ login → state ไม่ผูกกับ user_id (Drive's state ผูก user_id)
  - แยก _GLOGIN_STATE_CACHE จาก drive_oauth._STATE_CACHE เพื่อชัดเจน + กัน intent confusion

ทำไมต้อง verify ID token เอง (ไม่ใช้ creds.id_token ตรงๆ)?
  - flow.fetch_token() คืน access_token + id_token แต่ google-auth-oauthlib ไม่ verify
    signature ของ id_token ให้ — ต้อง verify เองก่อน trust claims (sub/email/email_verified)
  - ถ้า trust ตรงๆ + attacker ทำ MITM ระหว่าง server↔Google → forge ID token ได้
  - ใช้ google.oauth2.id_token.verify_oauth2_token (verify signature + audience + expiry)
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from typing import Optional, TypedDict

from .config import (
    GOOGLE_LOGIN_REDIRECT_URI,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    is_google_login_configured,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# OAuth scopes (login flow — minimal)
# ═══════════════════════════════════════════════════════════════
# ไม่ขอ drive.file → consent screen สั้นกว่า → conversion ดีกว่า
# ไม่ขอ access_type=offline → ไม่มี refresh_token → ไม่ต้อง encrypt + เก็บ DB
LOGIN_SCOPES: list[str] = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


# ═══════════════════════════════════════════════════════════════
# In-memory CSRF state cache (separate from Drive's cache)
# ═══════════════════════════════════════════════════════════════
class _StateEntry(TypedDict):
    expires: float
    code_verifier: str


_GLOGIN_STATE_CACHE: dict[str, _StateEntry] = {}
_GLOGIN_TTL_SECONDS = 600  # 10 นาที — ผู้ใช้ส่วนใหญ่ consent ภายใน <1 นาที


def _cleanup_expired_states() -> None:
    """ล้าง state หมดอายุ (lazy cleanup ตอน access เพื่อ amortize cost)."""
    now = time.time()
    expired = [s for s, info in _GLOGIN_STATE_CACHE.items() if info["expires"] < now]
    for s in expired:
        _GLOGIN_STATE_CACHE.pop(s, None)


# ═══════════════════════════════════════════════════════════════
# OAuth flow builder
# ═══════════════════════════════════════════════════════════════
def _build_login_flow():
    """Build google_auth_oauthlib Flow — lazy import เพราะเป็น optional dep."""
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
    """สร้าง auth URL + state CSRF token + PKCE code_verifier.

    Returns:
        {"auth_url": "https://accounts.google.com/o/oauth2/auth?..."}

    Frontend redirect → Google รับ consent → redirect กลับมาที่
    /api/auth/google/callback?code=...&state=...
    """
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
        # ไม่ใส่ access_type='offline' → ไม่ต้อง refresh_token (login เพียงครั้งเดียว)
        prompt="select_account",  # ให้ user เลือก account ทุกครั้ง (ดีกว่า silent re-use)
        include_granted_scopes="true",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return {"auth_url": auth_url}


# ═══════════════════════════════════════════════════════════════
# ID token verification + callback handler
# ═══════════════════════════════════════════════════════════════
class _GLoginResult(TypedDict):
    google_sub: str
    email: str
    email_verified: bool
    name: str
    picture: Optional[str]


def _verify_id_token(id_token_jwt: str) -> dict:
    """Verify Google ID token signature + audience + expiry.

    Raises:
        RuntimeError: ถ้า verify ไม่ผ่าน (signature ผิด / audience mismatch / expired)
    """
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest

    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_jwt,
            GoogleRequest(),
            audience=GOOGLE_OAUTH_CLIENT_ID,
            clock_skew_in_seconds=10,  # ช่วยกัน clock drift ระหว่าง server กับ Google
        )
    except ValueError as e:
        # google-auth raise ValueError ทุกกรณี verify fail (signature/audience/expiry)
        raise RuntimeError(f"Google ID token verification failed: {e}") from e

    # ตรวจ issuer ซ้ำ (verify_oauth2_token ตรวจให้แล้ว แต่ defensive)
    iss = idinfo.get("iss")
    if iss not in ("https://accounts.google.com", "accounts.google.com"):
        raise RuntimeError(f"Google ID token has unexpected issuer: {iss}")

    return idinfo


async def handle_google_callback(code: str, state: str) -> _GLoginResult:
    """แลก authorization code → tokens → verify ID token → คืน user info.

    1. Validate state — ตรงกับ cache + ยังไม่หมดอายุ
    2. Exchange code → id_token (PKCE)
    3. Verify id_token signature + audience
    4. Extract sub / email / email_verified / name / picture

    Raises:
        ValueError: state ไม่ valid / หมดอายุ (caller redirect with invalid_state)
        RuntimeError: token exchange fail / id_token verify fail (caller redirect with invalid_id_token)
    """
    _cleanup_expired_states()
    state_info = _GLOGIN_STATE_CACHE.pop(state, None)
    if not state_info:
        raise ValueError("INVALID_OAUTH_STATE — state ไม่ตรง / ใช้ไปแล้ว / หมดอายุ")

    flow = _build_login_flow()
    try:
        flow.fetch_token(code=code, code_verifier=state_info["code_verifier"])
    except Exception as e:
        # google-auth-oauthlib raise OAuthError variants — wrap เป็น RuntimeError
        # เพื่อให้ caller จับด้วย type เดียว (ไม่ต้อง import oauthlib ใน main.py)
        raise RuntimeError(f"Google token exchange failed: {e}") from e

    creds = flow.credentials
    id_token_jwt = getattr(creds, "id_token", None)
    if not id_token_jwt:
        raise RuntimeError("Google did not return id_token — check 'openid' scope")

    idinfo = _verify_id_token(id_token_jwt)

    # email_verified ใน ID token เป็น boolean ตามมาตรฐาน OIDC
    # Google consumer accounts (Gmail) → True เสมอ. Workspace custom domain → อาจ False ได้
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


# ═══════════════════════════════════════════════════════════════
# Test helpers (สำหรับ unit test เท่านั้น)
# ═══════════════════════════════════════════════════════════════
def _reset_state_cache_for_testing() -> None:
    """Clear in-memory CSRF state cache. ใช้เฉพาะใน tests."""
    _GLOGIN_STATE_CACHE.clear()
