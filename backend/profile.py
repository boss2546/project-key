"""User Profile service — MVP v2.

Manages the user's personal profile that helps AI understand the file owner.
Profile is stored in DB (structured) and can be rendered as profile-context.md.
"""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import UserProfile, gen_id

logger = logging.getLogger(__name__)


async def get_profile(db: AsyncSession, user_id: str) -> dict:
    """Get user profile, return empty defaults if not set."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return {
            "exists": False,
            "identity_summary": "",
            "goals": "",
            "working_style": "",
            "preferred_output_style": "",
            "background_context": "",
            "updated_at": None
        }

    return {
        "exists": True,
        "identity_summary": profile.identity_summary or "",
        "goals": profile.goals or "",
        "working_style": profile.working_style or "",
        "preferred_output_style": profile.preferred_output_style or "",
        "background_context": profile.background_context or "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
    }


async def update_profile(db: AsyncSession, user_id: str, data: dict) -> dict:
    """Create or update user profile."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    # Update only provided fields
    if "identity_summary" in data:
        profile.identity_summary = data["identity_summary"]
    if "goals" in data:
        profile.goals = data["goals"]
    if "working_style" in data:
        profile.working_style = data["working_style"]
    if "preferred_output_style" in data:
        profile.preferred_output_style = data["preferred_output_style"]
    if "background_context" in data:
        profile.background_context = data["background_context"]

    profile.updated_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Profile updated for user {user_id}")
    return await get_profile(db, user_id)


def get_profile_context_text(profile_data: dict) -> str:
    """Convert profile data to a text block for AI context injection."""
    if not profile_data.get("exists"):
        return ""

    parts = []
    if profile_data.get("identity_summary"):
        parts.append(f"ผู้ใช้คนนี้คือ: {profile_data['identity_summary']}")
    if profile_data.get("goals"):
        parts.append(f"เป้าหมาย: {profile_data['goals']}")
    if profile_data.get("working_style"):
        parts.append(f"สไตล์การทำงาน: {profile_data['working_style']}")
    if profile_data.get("preferred_output_style"):
        parts.append(f"ต้องการคำตอบแบบ: {profile_data['preferred_output_style']}")
    if profile_data.get("background_context"):
        parts.append(f"บริบทสำคัญ: {profile_data['background_context']}")

    if not parts:
        return ""

    return "=== USER PROFILE ===\n" + "\n".join(parts) + "\n=== END PROFILE ==="


def is_profile_complete(profile_data: dict) -> bool:
    """Check if profile has meaningful content."""
    if not profile_data.get("exists"):
        return False
    return bool(
        profile_data.get("identity_summary") or
        profile_data.get("goals") or
        profile_data.get("background_context")
    )
