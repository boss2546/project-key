"""User Profile service — v6.0 (เพิ่ม personality 4 ระบบ + history).

Manages the user's personal profile that helps AI understand the file owner.
v6.0 — เพิ่มข้อมูลบุคลิกภาพ MBTI / Enneagram / CliftonStrengths / VIA
       + บันทึกประวัติทุกครั้งที่อัปเดต (table personality_history)
       + inject เข้า LLM context ผ่าน get_profile_context_text()
"""
import json
import logging
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import UserProfile, PersonalityHistory
from .personality import (
    format_personality_for_llm, SUPPORTED_SYSTEMS,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 1. GET / READ
# ═══════════════════════════════════════════

async def get_profile(db: AsyncSession, user_id: str) -> dict:
    """Get user profile + personality fields. คืน defaults ถ้ายังไม่ตั้ง."""
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
            "mbti": None,
            "enneagram": None,
            "clifton_top5": None,
            "via_top5": None,
            "updated_at": None,
        }

    # Deserialize personality fields ที่เก็บเป็น JSON / structured
    mbti = None
    if profile.mbti_type:
        mbti = {
            "type": profile.mbti_type,
            "source": profile.mbti_source or "self_report",
        }

    enneagram = _safe_json_loads(profile.enneagram_data)
    clifton_top5 = _safe_json_loads(profile.clifton_top5)
    via_top5 = _safe_json_loads(profile.via_top5)

    return {
        "exists": True,
        "identity_summary": profile.identity_summary or "",
        "goals": profile.goals or "",
        "working_style": profile.working_style or "",
        "preferred_output_style": profile.preferred_output_style or "",
        "background_context": profile.background_context or "",
        "mbti": mbti,
        "enneagram": enneagram,
        "clifton_top5": clifton_top5,
        "via_top5": via_top5,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _safe_json_loads(raw: str | None):
    """Load JSON ที่อาจเป็น None/"" — คืน None ถ้า empty หรือ parse fail."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        # treat empty list/dict as not-set
        if parsed in ([], {}):
            return None
        return parsed
    except (json.JSONDecodeError, TypeError):
        return None


# ═══════════════════════════════════════════
# 2. UPDATE — partial + history snapshot ตามที่ค่าเปลี่ยน
# ═══════════════════════════════════════════

async def update_profile(db: AsyncSession, user_id: str, data: dict) -> dict:
    """Create or update user profile + บันทึก history เมื่อ personality เปลี่ยน.

    `data` keys (ทุกตัว optional, partial update):
        - identity_summary, goals, working_style, preferred_output_style, background_context (str | None)
        - mbti: {"type": str, "source": str} | None  → None = clear
        - enneagram: {"core": int, "wing": int|None} | None
        - clifton_top5: list[str] | None  → [] หรือ None = clear
        - via_top5: list[str] | None
        - _history_source: str (internal — "user_update" | "mcp_update")

    History dedup: ถ้าค่าใหม่ == ค่าล่าสุดของระบบนั้น → ไม่ append row ใหม่
    Clear event: ถ้า user clear field ที่เคยมีค่า → append row ที่ data_json = {"cleared": true}
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        # Need to flush so subsequent queries can see the new row
        await db.flush()

    # ─── ดึง snapshot ก่อนเปลี่ยน เพื่อใช้ compare กับค่าใหม่ใน history dedup ───
    prev_mbti = (
        {"type": profile.mbti_type, "source": profile.mbti_source or "self_report"}
        if profile.mbti_type else None
    )
    prev_enneagram = _safe_json_loads(profile.enneagram_data)
    prev_clifton = _safe_json_loads(profile.clifton_top5)
    prev_via = _safe_json_loads(profile.via_top5)

    # source ของ history (ดึงออกก่อนเพราะไม่ใช่ field ของตาราง)
    history_source = data.pop("_history_source", "user_update") if isinstance(data, dict) else "user_update"

    # ─── 1) Update text fields เดิม ───
    # ⚠️ ใช้ "in data" — ถ้า user ส่ง None มา ก็ overwrite (clear) field
    for key in ("identity_summary", "goals", "working_style",
                "preferred_output_style", "background_context"):
        if key in data:
            setattr(profile, key, data[key] if data[key] is not None else "")

    # ─── 2) Update personality fields ───
    # MBTI — None = clear, dict = set
    if "mbti" in data:
        val = data["mbti"]
        if val is None:
            profile.mbti_type = None
            profile.mbti_source = None
        elif isinstance(val, dict) and val.get("type"):
            profile.mbti_type = val["type"]
            profile.mbti_source = val.get("source") or "self_report"

    # Enneagram — None/{}/missing core = clear, dict with core = set
    if "enneagram" in data:
        val = data["enneagram"]
        if not val or not isinstance(val, dict) or not val.get("core"):
            profile.enneagram_data = None
        else:
            profile.enneagram_data = json.dumps(
                {"core": val["core"], "wing": val.get("wing")},
                ensure_ascii=False,
            )

    # Clifton — None/[] = clear
    if "clifton_top5" in data:
        val = data["clifton_top5"]
        if not val:
            profile.clifton_top5 = None
        else:
            profile.clifton_top5 = json.dumps(val, ensure_ascii=False)

    # VIA — เหมือน Clifton
    if "via_top5" in data:
        val = data["via_top5"]
        if not val:
            profile.via_top5 = None
        else:
            profile.via_top5 = json.dumps(val, ensure_ascii=False)

    profile.updated_at = datetime.utcnow()

    # Flush เพื่อให้ค่าใหม่บน profile object อ่านได้ถูก
    await db.flush()

    # ─── 3) บันทึก history เฉพาะระบบที่ค่าเปลี่ยนจริง (ก่อน commit) ───
    new_mbti = (
        {"type": profile.mbti_type, "source": profile.mbti_source or "self_report"}
        if profile.mbti_type else None
    )
    new_enneagram = _safe_json_loads(profile.enneagram_data)
    new_clifton = _safe_json_loads(profile.clifton_top5)
    new_via = _safe_json_loads(profile.via_top5)

    if "mbti" in data and new_mbti != prev_mbti:
        await record_personality_history(
            db, user_id, "mbti",
            new_mbti if new_mbti is not None else {"cleared": True},
            history_source,
        )
    if "enneagram" in data and new_enneagram != prev_enneagram:
        await record_personality_history(
            db, user_id, "enneagram",
            new_enneagram if new_enneagram is not None else {"cleared": True},
            history_source,
        )
    if "clifton_top5" in data and new_clifton != prev_clifton:
        await record_personality_history(
            db, user_id, "clifton",
            {"top5": new_clifton} if new_clifton is not None else {"cleared": True},
            history_source,
        )
    if "via_top5" in data and new_via != prev_via:
        await record_personality_history(
            db, user_id, "via",
            {"top5": new_via} if new_via is not None else {"cleared": True},
            history_source,
        )

    await db.commit()

    logger.info(f"Profile updated for user {user_id} (source={history_source})")
    result = await get_profile(db, user_id)

    # ─── 4) BYOS projection (best-effort) ───────────────────────
    # ถ้า user เป็น byos mode → push profile.json ลง /Personal Data Bank/personal/ ใน Drive
    # ของ user เพื่อโปร่งใส (user เปิด Drive ดูเองได้). DB เป็น source of truth — Drive failure
    # ไม่ throw + ไม่ rollback DB. Managed users no-op.
    try:
        from .storage_router import push_profile_to_drive_if_byos
        await push_profile_to_drive_if_byos(user_id, db, result)
    except Exception as e:
        # Defensive: storage_router ดักไว้แล้ว แต่ใส่ guard ไว้กันดอด ถ้า import fail
        logger.warning(f"BYOS profile push wrapper failed (non-fatal): {e}")

    return result


# ═══════════════════════════════════════════
# 3. PERSONALITY HISTORY
# ═══════════════════════════════════════════

async def record_personality_history(
    db: AsyncSession,
    user_id: str,
    system: str,
    data: dict,
    source: str = "user_update",
) -> None:
    """Append snapshot ลง personality_history. caller ต้อง dedup เองก่อนเรียก."""
    if system not in SUPPORTED_SYSTEMS:
        logger.warning(f"record_personality_history: invalid system '{system}'")
        return
    entry = PersonalityHistory(
        user_id=user_id,
        system=system,
        data_json=json.dumps(data, ensure_ascii=False),
        source=source,
    )
    db.add(entry)
    # ไม่ commit เอง — caller จัดการ transaction


async def list_personality_history(
    db: AsyncSession,
    user_id: str,
    system: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """คืน history ของผู้ใช้ เรียง recorded_at desc.

    Args:
        system: ถ้าระบุ → filter เฉพาะระบบนั้น (mbti/enneagram/clifton/via)
        limit: max rows (caller validate ขีดบนแล้ว)
    """
    query = select(PersonalityHistory).where(PersonalityHistory.user_id == user_id)
    if system:
        query = query.where(PersonalityHistory.system == system)
    query = query.order_by(desc(PersonalityHistory.recorded_at)).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "system": r.system,
            "data": _safe_json_loads(r.data_json) or {},
            "source": r.source or "user_update",
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]


# ═══════════════════════════════════════════
# 4. LLM CONTEXT INJECTION
# ═══════════════════════════════════════════

def get_profile_context_text(profile_data: dict) -> str:
    """Convert profile + personality เป็น text block สำหรับ inject เข้า LLM context.

    ผูก profile เดิม + personality 4 ระบบเข้าด้วยกัน — caller ใน retriever.py
    เรียกตัวนี้แล้ว inject เป็น Layer 1 priority สูงสุด
    """
    if not profile_data.get("exists"):
        # ผู้ใช้ใหม่ที่ยังไม่ตั้งโปรไฟล์เลย — ก็ยังอาจมี personality ที่ตั้งแยก
        # (ตาม flow ปัจจุบัน mbti/enneagram/etc จะมาพร้อม UserProfile row เดียวกัน
        # แต่กันไว้เผื่ออนาคต)
        personality_text = format_personality_for_llm(profile_data)
        return personality_text or ""

    parts: list[str] = []
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

    base = "=== USER PROFILE ===\n" + "\n".join(parts) + "\n=== END PROFILE ===" if parts else ""
    personality_text = format_personality_for_llm(profile_data)

    if base and personality_text:
        return base + "\n\n" + personality_text
    return base or personality_text or ""


def is_profile_complete(profile_data: dict) -> bool:
    """Profile ถือว่า meaningful ถ้ามีข้อมูลตัวใดตัวหนึ่งใน text fields หรือ personality."""
    if not profile_data.get("exists"):
        return False
    return bool(
        profile_data.get("identity_summary") or
        profile_data.get("goals") or
        profile_data.get("background_context") or
        profile_data.get("mbti") or
        profile_data.get("enneagram") or
        profile_data.get("clifton_top5") or
        profile_data.get("via_top5")
    )
