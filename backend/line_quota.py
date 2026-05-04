"""LINE push API quota tracking (v8.0.0 Phase H).

LINE Communication plan = 200 push messages/month free.
Reply API = ฟรีไม่จำกัด (ไม่นับ quota).

ตรงนี้ track เฉพาะ push เพื่อ:
- เตือน admin ก่อน quota เต็ม (>= 80%)
- Optimize: หลีกเลี่ยง push ที่ไม่จำเป็น
- Stats: ดูว่าใช้ feature ไหนกิน quota เยอะ

Storage = in-memory counter รีเซ็ตทุกเดือน. Persistent storage = future
optimization (ใช้ DB table หรือ Redis). For MVP — in-memory พอ:
- Server restart = counter รีเซ็ต (acceptable, ไม่ critical)
- Multi-instance = แต่ละ instance นับเอง (Fly.io ใช้ instance เดียวอยู่แล้ว)
"""
from __future__ import annotations
import logging
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


# Free tier limit
FREE_TIER_PUSH_LIMIT = 200

# In-memory counter — keyed by (year, month)
_counter: dict[tuple[int, int], int] = {}
_lock = Lock()

# Alerted flag — เพื่อไม่ alert ซ้ำใน month เดียวกัน
_alerted: dict[tuple[int, int], bool] = {}


def _current_month_key() -> tuple[int, int]:
    now = datetime.utcnow()
    return (now.year, now.month)


def record_push() -> int:
    """Record a successful push. Returns new total for current month.

    Logs warning at 80% / 95% / 100% thresholds (once per threshold per month).
    """
    key = _current_month_key()
    with _lock:
        _counter[key] = _counter.get(key, 0) + 1
        total = _counter[key]
        threshold_pct = (total / FREE_TIER_PUSH_LIMIT) * 100

        # Alert at 80% (warn) and 100% (critical) — once per month
        if total == int(FREE_TIER_PUSH_LIMIT * 0.8) and not _alerted.get((key, 80)):
            logger.warning(
                "LINE push quota at 80%% (%d/%d) for %d-%02d — consider upgrading to Light plan",
                total, FREE_TIER_PUSH_LIMIT, key[0], key[1],
            )
            _alerted[(key, 80)] = True
        if total >= FREE_TIER_PUSH_LIMIT and not _alerted.get((key, 100)):
            logger.error(
                "LINE push quota EXCEEDED (%d/%d) for %d-%02d — push API will return 429",
                total, FREE_TIER_PUSH_LIMIT, key[0], key[1],
            )
            _alerted[(key, 100)] = True

    return total


def get_current_usage() -> dict:
    """Return current month's push usage stats."""
    key = _current_month_key()
    with _lock:
        used = _counter.get(key, 0)
    pct = (used / FREE_TIER_PUSH_LIMIT) * 100 if FREE_TIER_PUSH_LIMIT else 0
    return {
        "year": key[0],
        "month": key[1],
        "pushes_used": used,
        "limit": FREE_TIER_PUSH_LIMIT,
        "percent": round(pct, 1),
        "remaining": max(0, FREE_TIER_PUSH_LIMIT - used),
        "exceeded": used >= FREE_TIER_PUSH_LIMIT,
    }


def reset() -> None:
    """Reset counter (test helper / manual admin action)."""
    with _lock:
        _counter.clear()
        _alerted.clear()
