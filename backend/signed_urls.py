"""JWT-signed download URLs (v7.6.0).

Universal primitive — used by:
- MCP `get_file_link` tool — share-safely with AI tools (Claude/ChatGPT/Antigravity)
- Future LINE/Telegram/Discord bot — file delivery via download link
- Web sharing — generate share URL for non-PDB users

ออกแบบเป็น stateless JWT (HS256) — ไม่เก็บใน memory/DB ต่างจาก shared_links.py เดิม.
ข้อดี: scale ข้าม instance ได้, restart ไม่หาย, verify ที่ไหนก็ได้.

Token = JWT signed with JWT_SECRET_KEY (เดียวกับ auth tokens — ถ้า rotate secret =
invalidate ทุก token รวมทั้ง download URL ที่ออกไปแล้ว — acceptable เพราะ TTL สั้น).

Scope = "download" — ป้องกัน token reuse ข้าม feature (เช่น login token ห้ามใช้ download).

TTL: default 1800s (30 min), allowed range 60-3600s (1 min - 1 hour).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from .config import JWT_SECRET_KEY, JWT_ALGORITHM


class DownloadTokenError(Exception):
    """Raised on token decode failure. Has `code` for HTTP error mapping."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# Allowed TTL range (seconds) — 1 min to 1 hour
TTL_MIN_SECONDS = 60
TTL_MAX_SECONDS = 3600
TTL_DEFAULT_SECONDS = 1800  # 30 min

# Token scope — prevents reuse across feature boundaries
SCOPE_DOWNLOAD = "download"


def sign_download_token(
    file_id: str,
    user_id: str,
    ttl_seconds: int = TTL_DEFAULT_SECONDS,
) -> str:
    """Sign a download token (JWT HS256).

    Args:
        file_id: ไฟล์ที่จะ download
        user_id: เจ้าของไฟล์ (server เช็คซ้ำกับ file.user_id ตอน verify)
        ttl_seconds: 60-3600 sec (default 1800 = 30 min)

    Raises:
        ValueError: ถ้า ttl_seconds นอก range
    """
    if ttl_seconds < TTL_MIN_SECONDS or ttl_seconds > TTL_MAX_SECONDS:
        raise ValueError(
            f"ttl_seconds must be between {TTL_MIN_SECONDS} and {TTL_MAX_SECONDS}"
        )

    now = datetime.now(timezone.utc)
    payload = {
        "file_id": file_id,
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
        "scope": SCOPE_DOWNLOAD,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_download_token(token: str) -> dict:
    """Decode + verify download token.

    Returns:
        dict payload: {file_id, user_id, iat, exp, scope}

    Raises:
        DownloadTokenError("LINK_EXPIRED") — exp ผ่านแล้ว
        DownloadTokenError("INVALID_TOKEN") — ทุก case อื่นๆ (signature, missing field, wrong scope)
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise DownloadTokenError("LINK_EXPIRED", "ลิงก์ดาวน์โหลดหมดอายุ")
    except JWTError:
        raise DownloadTokenError("INVALID_TOKEN", "ลิงก์ดาวน์โหลดไม่ถูกต้อง")

    # Required fields check (jose ไม่ enforce required ใน decode — manual check)
    required = {"file_id", "user_id", "iat", "exp", "scope"}
    if not required.issubset(payload.keys()):
        raise DownloadTokenError("INVALID_TOKEN", "Token ไม่มี required fields")

    # Scope check — ป้องกัน token จาก feature อื่นมา download
    if payload.get("scope") != SCOPE_DOWNLOAD:
        raise DownloadTokenError("INVALID_TOKEN", "Token scope ไม่ถูกต้อง")

    return payload
