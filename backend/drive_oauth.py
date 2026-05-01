"""Google Drive OAuth 2.0 flow + token storage helpers (BYOS feature, v7.0).

หน้าที่:
  - สร้าง auth URL พร้อม CSRF state token (init_oauth)
  - แลก code ↔ refresh_token ตอน callback (handle_callback)
  - สร้าง /Personal Data Bank/ folder ใน Drive ของ user (ถ้ายังไม่มี)
  - encrypt/decrypt refresh_token at rest (Fernet)
  - Build Credentials object สำหรับเรียก Drive API

ทำไมถึง encrypt refresh_token?
  - Refresh token = key ที่ทำให้ server เข้าถึง Drive ของ user ได้ตลอดเวลา
  - ถ้า DB หลุด + token plaintext → attacker เข้าถึง Drive ของ user ทุกคน
  - encrypt with Fernet (AES-128 + HMAC) — key เก็บใน env var (ไม่ใน DB)

State CSRF token:
  - ป้องกัน attacker hook callback URL กับ code ของ attacker เพื่อ link Drive ของ
    attacker เข้า account ของ user เป้าหมาย
  - state = random token + map → user_id + expires (10 min TTL)
  - In-memory dict ใช้ได้สำหรับ single-server. Multi-server ต้องย้ายเป็น Redis
"""
from __future__ import annotations

import logging
import secrets
import time
from typing import TypedDict

from cryptography.fernet import Fernet, InvalidToken

from .config import (
    DRIVE_TOKEN_ENCRYPTION_KEY,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REDIRECT_URI,
    is_byos_configured,
)
from .drive_layout import DRIVE_ROOT_FOLDER_NAME, MIME_FOLDER

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# OAuth scopes
# ═══════════════════════════════════════════════════════════════
# drive.file = เฉพาะไฟล์ที่ app สร้าง / user pick ผ่าน Picker
# (ห้าม list Drive ทั้งหมด — verification ฟรี ~2-4 weeks vs `drive` เต็ม $25K-85K + 6 เดือน)
SCOPES: list[str] = [
    "https://www.googleapis.com/auth/drive.file",
    # openid + email — ใช้เพื่อรู้ว่า Drive นี้เป็นของ Google account ไหน
    # (เก็บใน drive_connections.drive_email สำหรับ display)
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


# ═══════════════════════════════════════════════════════════════
# In-memory CSRF state cache (single-server dev)
# ═══════════════════════════════════════════════════════════════
class _StateEntry(TypedDict):
    user_id: str
    expires: float
    code_verifier: str


# Module-level cache — TTL 10 นาที, cleanup lazy ตอน get
_STATE_CACHE: dict[str, _StateEntry] = {}
_STATE_TTL_SECONDS = 600


def _cleanup_expired_states() -> None:
    """ล้าง state ที่หมดอายุออกจาก cache (เรียกตอน access เพื่อ amortize cost)."""
    now = time.time()
    expired = [s for s, info in _STATE_CACHE.items() if info["expires"] < now]
    for s in expired:
        _STATE_CACHE.pop(s, None)


# ═══════════════════════════════════════════════════════════════
# Token encryption (Fernet)
# ═══════════════════════════════════════════════════════════════
def _get_fernet() -> Fernet:
    """Build Fernet cipher จาก env var DRIVE_TOKEN_ENCRYPTION_KEY.

    Raises RuntimeError ถ้า env var ว่าง หรือ format ไม่ถูก —
    endpoint level ควร short-circuit ก่อน (is_byos_configured) เพื่อให้ user
    ได้ error message ที่ดีกว่า cryptography error.
    """
    if not DRIVE_TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("DRIVE_TOKEN_ENCRYPTION_KEY env var ไม่ได้ set")
    try:
        return Fernet(DRIVE_TOKEN_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError) as e:
        # Fernet key ต้องเป็น 32 url-safe base64-encoded bytes
        raise RuntimeError(
            "DRIVE_TOKEN_ENCRYPTION_KEY format ผิด — generate ด้วย "
            "Fernet.generate_key().decode() ก่อนนำมา set"
        ) from e


def encrypt_refresh_token(plaintext: str) -> str:
    """Encrypt refresh_token ก่อนเก็บลง DB."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_refresh_token(ciphertext: str) -> str:
    """Decrypt refresh_token ตอนเรียก Drive API.

    Raises RuntimeError ถ้า key เปลี่ยนหลังจาก encrypt — user ต้อง re-connect
    เพราะ token เก่าใช้ไม่ได้แล้ว (token rotation policy).
    """
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise RuntimeError(
            "Decrypt refresh_token ไม่สำเร็จ — encryption key อาจถูกเปลี่ยน "
            "user ต้อง re-connect Drive"
        ) from e


# ═══════════════════════════════════════════════════════════════
# OAuth flow
# ═══════════════════════════════════════════════════════════════
def _build_flow():
    """Build google_auth_oauthlib Flow สำหรับ web-app OAuth.

    Lazy import เพราะ google_auth_oauthlib เป็น optional dep (BYOS feature) —
    ถ้า env vars ไม่ครบ + ไม่เคยเรียก endpoint นี้ → ไม่ต้องโหลด lib.
    """
    from google_auth_oauthlib.flow import Flow

    if not is_byos_configured():
        raise RuntimeError(
            "BYOS ยังไม่ได้ configure — set GOOGLE_OAUTH_CLIENT_ID, "
            "GOOGLE_OAUTH_CLIENT_SECRET, DRIVE_TOKEN_ENCRYPTION_KEY ก่อน"
        )

    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
    )


def init_oauth(user_id: str) -> dict[str, str]:
    """สร้าง auth URL + state CSRF token สำหรับ user.

    Returns:
        {"auth_url": "https://accounts.google.com/o/oauth2/auth?...&state=..."}

    Frontend redirect ไป auth_url → Google รับ consent → redirect กลับมาที่
    /api/drive/oauth/callback?code=...&state=...
    """
    _cleanup_expired_states()

    flow = _build_flow()
    state = secrets.token_urlsafe(32)
    # PKCE: generate code_verifier (Google mandates since 2025)
    import hashlib, base64
    code_verifier = secrets.token_urlsafe(64)  # 86 chars, URL-safe
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    _STATE_CACHE[state] = {
        "user_id": user_id,
        "expires": time.time() + _STATE_TTL_SECONDS,
        "code_verifier": code_verifier,
    }

    auth_url, _ = flow.authorization_url(
        access_type="offline",   # request refresh_token (ต้องมีเพื่อ refresh access_token)
        prompt="consent",         # บังคับ consent screen — ทำให้ refresh_token ออกมาแน่นอน
        include_granted_scopes="true",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return {"auth_url": auth_url}


class _CallbackResult(TypedDict):
    user_id: str
    drive_email: str
    refresh_token: str
    drive_root_folder_id: str


async def handle_callback(code: str, state: str) -> _CallbackResult:
    """แลก authorization code → tokens + สร้าง root folder ใน Drive.

    1. Validate state — ตรงกับ user ที่ initiate flow + ยังไม่หมดอายุ
    2. Exchange code → access_token + refresh_token
    3. Get user's Drive email (สำหรับ display)
    4. Create /Personal Data Bank/ folder ใน Drive root (ถ้ายังไม่มี)
    5. Return — caller (main.py endpoint) เก็บลง DriveConnection table

    Raises ValueError ถ้า state ไม่ valid / หมดอายุ —
    main.py แปลงเป็น HTTPException 400 ด้วย code INVALID_OAUTH_STATE
    """
    _cleanup_expired_states()
    state_info = _STATE_CACHE.pop(state, None)
    if not state_info:
        raise ValueError("INVALID_OAUTH_STATE — state ไม่ตรง / ใช้ไปแล้ว / หมดอายุ")

    flow = _build_flow()
    # PKCE: pass code_verifier ที่ generate ตอน init
    flow.fetch_token(code=code, code_verifier=state_info["code_verifier"])
    creds = flow.credentials
    if not creds.refresh_token:
        # ปกติ refresh_token จะออกมาเพราะเรา force prompt='consent' แต่ถ้าไม่มี = bug
        raise RuntimeError("Google ไม่ได้ส่ง refresh_token กลับมา — ตรวจ prompt='consent'")

    # Build authed Drive service (lazy import)
    from googleapiclient.discovery import build

    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # Get user's Drive email จาก about resource
    about = drive_service.about().get(fields="user(emailAddress)").execute()
    drive_email = about["user"]["emailAddress"]

    # หา root folder เดิม (drive.file scope จะเห็นเฉพาะ folder ที่ app เคยสร้าง)
    existing = drive_service.files().list(
        q=(
            f"name='{DRIVE_ROOT_FOLDER_NAME}' "
            f"and mimeType='{MIME_FOLDER}' "
            f"and trashed=false"
        ),
        fields="files(id, name)",
        spaces="drive",
        pageSize=1,
    ).execute()

    if existing.get("files"):
        root_id = existing["files"][0]["id"]
        logger.info(
            "BYOS: reused existing /%s/ folder (id=%s) for user_id=%s",
            DRIVE_ROOT_FOLDER_NAME, root_id, state_info["user_id"],
        )
    else:
        created = drive_service.files().create(
            body={"name": DRIVE_ROOT_FOLDER_NAME, "mimeType": MIME_FOLDER},
            fields="id",
        ).execute()
        root_id = created["id"]
        logger.info(
            "BYOS: created /%s/ folder (id=%s) for user_id=%s",
            DRIVE_ROOT_FOLDER_NAME, root_id, state_info["user_id"],
        )

    return {
        "user_id": state_info["user_id"],
        "drive_email": drive_email,
        "refresh_token": creds.refresh_token,
        "drive_root_folder_id": root_id,
    }


# ═══════════════════════════════════════════════════════════════
# Build Credentials สำหรับเรียก Drive API ครั้งอื่น
# ═══════════════════════════════════════════════════════════════
def build_credentials_from_refresh_token(refresh_token_plaintext: str):
    """Build google.oauth2.credentials.Credentials จาก refresh_token.

    Drive API client จะ auto-refresh access_token เมื่อ expired (1 ชม.) ผ่าน
    refresh_token ที่ส่งให้ — caller ไม่ต้องเรียก refresh เอง.
    """
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,  # ไม่มี access_token เริ่มต้น — จะ refresh ตอนเรียก API ครั้งแรก
        refresh_token=refresh_token_plaintext,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=SCOPES,
    )


# ═══════════════════════════════════════════════════════════════
# Revoke (สำหรับ disconnect endpoint)
# ═══════════════════════════════════════════════════════════════
def revoke_refresh_token(refresh_token_plaintext: str) -> bool:
    """แจ้ง Google ให้ revoke refresh_token (เรียกตอน user disconnect).

    Returns True ถ้า revoke สำเร็จ. False ถ้า Google reject (เช่น token ถูก revoke
    ไปแล้ว) — ในกรณีนี้ caller ก็ลบ DB row ได้เลย (idempotent disconnect).

    Note: ไม่ raise ถ้า revoke fail — disconnect ฝั่ง app ยังทำงานต่อได้
    เพราะเรา drop refresh_token ทิ้งฝั่งเราเองอยู่แล้ว.
    """
    import httpx

    try:
        r = httpx.post(
            "https://oauth2.googleapis.com/revoke",
            data={"token": refresh_token_plaintext},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        return r.status_code == 200
    except httpx.HTTPError as e:
        logger.warning("BYOS: revoke_refresh_token http error (non-fatal): %s", e)
        return False


# ═══════════════════════════════════════════════════════════════
# Test helpers (สำหรับ unit test — ไม่ใช้ใน production code)
# ═══════════════════════════════════════════════════════════════
def _reset_state_cache_for_testing() -> None:
    """Clear in-memory CSRF state cache. ใช้เฉพาะใน tests."""
    _STATE_CACHE.clear()
