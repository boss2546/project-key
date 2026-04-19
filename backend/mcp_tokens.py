"""MCP Token management service — MVP v4.

Handles generation, validation, listing, and revocation of
Bearer tokens for the PDB Connector Layer.
"""
import secrets
import hashlib
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import MCPToken, gen_id

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "pk_"


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash a raw token for secure storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def generate_token(db: AsyncSession, user_id: str, label: str = "Default Token") -> dict:
    """Generate a new MCP token. Returns the raw token ONCE (never stored)."""
    raw_token = TOKEN_PREFIX + secrets.token_hex(24)
    token_hash = _hash_token(raw_token)

    token = MCPToken(
        id=gen_id(),
        user_id=user_id,
        token_hash=token_hash,
        label=label,
        scope="read-only",
        is_active=True,
    )
    db.add(token)
    await db.commit()

    logger.info(f"Generated MCP token '{label}' for user {user_id}")
    return {
        "id": token.id,
        "raw_token": raw_token,  # Only returned once!
        "label": token.label,
        "scope": token.scope,
        "created_at": token.created_at.isoformat(),
    }


async def validate_token(db: AsyncSession, raw_token: str) -> dict | None:
    """Validate a raw token. Returns token info if valid, None if invalid."""
    if not raw_token or not raw_token.startswith(TOKEN_PREFIX):
        return None

    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(MCPToken).where(
            MCPToken.token_hash == token_hash,
            MCPToken.is_active == True,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return None

    # Update last_used_at
    token.last_used_at = datetime.utcnow()
    await db.commit()

    return {
        "token_id": token.id,
        "user_id": token.user_id,
        "label": token.label,
        "scope": token.scope,
    }


async def list_tokens(db: AsyncSession, user_id: str) -> list[dict]:
    """List all tokens for a user."""
    result = await db.execute(
        select(MCPToken)
        .where(MCPToken.user_id == user_id)
        .order_by(MCPToken.created_at.desc())
    )
    tokens = result.scalars().all()

    return [
        {
            "id": t.id,
            "label": t.label,
            "scope": t.scope,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
            "revoked_at": t.revoked_at.isoformat() if t.revoked_at else None,
        }
        for t in tokens
    ]


async def revoke_token(db: AsyncSession, token_id: str, user_id: str) -> bool:
    """Revoke a token. Returns True if found and revoked."""
    result = await db.execute(
        select(MCPToken).where(
            MCPToken.id == token_id,
            MCPToken.user_id == user_id,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return False

    token.is_active = False
    token.revoked_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Revoked MCP token '{token.label}' ({token_id})")
    return True


async def get_active_token_count(db: AsyncSession, user_id: str) -> int:
    """Count active tokens for a user."""
    result = await db.execute(
        select(MCPToken).where(
            MCPToken.user_id == user_id,
            MCPToken.is_active == True,
        )
    )
    return len(result.scalars().all())
