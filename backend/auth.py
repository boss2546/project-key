"""Authentication module for Personal Data Bank (PDB) — v5.0 Multi-User.

Provides JWT-based authentication with bcrypt password hashing.
"""
import os
import logging
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from jose import JWTError, jwt

from .database import User, get_db
from .config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

# Bearer token extractor
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(user_id: str, email: str, name: str) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def register_user(db: AsyncSession, email: str, password: str, name: str) -> dict:
    """Register a new user. Returns user info + JWT token."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Validate
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )

    # Create user
    from .database import gen_id
    import secrets as _secrets
    user = User(
        id=gen_id(),
        name=name or "User",
        email=email.lower().strip(),
        password_hash=hash_password(password),
        is_active=True,
        mcp_secret=_secrets.token_urlsafe(32),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate token
    token = create_access_token(user.id, user.email, user.name)

    logger.info(f"New user registered: {user.email} ({user.id})")
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mcp_secret": user.mcp_secret,
        },
        "token": token,
    }


async def login_user(db: AsyncSession, email: str, password: str) -> dict:
    """Login a user. Returns user info + JWT token."""
    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate token
    token = create_access_token(user.id, user.email, user.name)

    logger.info(f"User logged in: {user.email} ({user.id})")
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mcp_secret": user.mcp_secret,  # v5.1 — per-user MCP URL
        },
        "token": token,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — extract current user from JWT token.
    
    Use as: current_user: User = Depends(get_current_user)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """FastAPI dependency — returns user if authenticated, None if not.
    
    Use for endpoints that work both with and without auth (e.g. landing page data).
    """
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    return user


# ═══════════════════════════════════════════
# PASSWORD RESET — v5.1
# ═══════════════════════════════════════════

def create_reset_token(user_id: str, email: str) -> str:
    """Create a short-lived JWT token for password reset (15 min)."""
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "reset",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_reset_token(token: str) -> dict | None:
    """Decode and validate a password reset token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload
    except JWTError:
        return None


async def request_password_reset(db: AsyncSession, email: str) -> dict:
    """Request a password reset.

    SECURITY (Phase 1.3): Anti-enumeration — never reveals whether the email
    exists. Always returns a uniform success-shaped response so attackers can't
    map registered emails by probing this endpoint.

    NOTE: still returns `reset_token` directly because there is no email
    sending pipeline yet. TODO (Phase 2): wire SMTP/SendGrid, drop
    `reset_token` from response, and email a one-shot signed link instead.
    """
    email = email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Generic success — same shape whether the email exists or not.
    # Only emit a token when a real, active account is found.
    response = {
        "message": "ถ้าอีเมลนี้มีบัญชีอยู่ ระบบจะส่งลิงก์รีเซ็ตให้",
        "email": email,
    }

    if not user:
        logger.info(f"Password reset requested for unknown email: {email}")
        return response

    if not user.is_active:
        logger.info(f"Password reset requested for inactive account: {email}")
        return response

    token = create_reset_token(user.id, user.email)
    logger.info(f"Password reset requested for: {user.email}")
    
    # Send email (v7.6.0) - fail gracefully inside send_password_reset_email
    from .email_service import send_password_reset_email
    import asyncio
    asyncio.create_task(send_password_reset_email(user.email, user.name, token))
    
    return response


async def reset_password(db: AsyncSession, token: str, new_password: str) -> dict:
    """Reset password using a valid reset token."""
    # Validate token
    payload = decode_reset_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ลิงก์รีเซ็ตหมดอายุหรือไม่ถูกต้อง"
        )

    # Validate new password
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"
        )

    # Find user
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบบัญชีผู้ใช้"
        )

    # Update password
    user.password_hash = hash_password(new_password)
    await db.commit()

    logger.info(f"Password reset completed for: {user.email}")

    # Auto-login after reset
    access_token = create_access_token(user.id, user.email, user.name)
    return {
        "message": "เปลี่ยนรหัสผ่านสำเร็จ",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mcp_secret": user.mcp_secret,
        },
        "token": access_token,
    }
