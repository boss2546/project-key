"""Shared file links — temporary public URLs for AI access."""
import hashlib
import secrets
import time
import os
import logging

logger = logging.getLogger(__name__)

# In-memory store: {token: {file_id, user_id, expires_at, filename}}
_shared_links: dict[str, dict] = {}


def generate_share_token(file_id: str, user_id: str, filename: str, ttl_seconds: int = 1800) -> str:
    """Generate a signed temporary token for file access (default 30 min).
    
    The token is stored in memory and expires after ttl_seconds.
    Returns the token string to be used in /api/shared/{token}.
    """
    # Clean expired tokens
    now = time.time()
    expired = [k for k, v in _shared_links.items() if v["expires_at"] < now]
    for k in expired:
        del _shared_links[k]
    
    token = hashlib.sha256(f"{file_id}{user_id}{now}{secrets.token_hex(8)}".encode()).hexdigest()[:32]
    _shared_links[token] = {
        "file_id": file_id,
        "user_id": user_id,
        "filename": filename,
        "expires_at": now + ttl_seconds,
    }
    logger.info(f"Share link created for {filename} (expires in {ttl_seconds}s)")
    return token


def get_share_link(token: str) -> dict | None:
    """Look up a share token. Returns link data or None if expired/not found."""
    link = _shared_links.get(token)
    if not link:
        return None
    
    if time.time() > link["expires_at"]:
        del _shared_links[token]
        return None
    
    return link


def build_share_url(token: str) -> str:
    """Build a full share URL from a token."""
    base_url = os.getenv("BASE_URL", "https://personaldatabank.fly.dev")
    return f"{base_url}/api/shared/{token}"
