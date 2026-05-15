"""Per-user progress tracker for long-running pipelines -- v10.0.3.

Used by /api/organize-new flow so the frontend loading overlay shows live
status instead of "AI กำลังจัดระเบียบ..." stuck spinner. Same UX problem
that we solved for upload tray via upload_worker progress_callback, now
applied to the orchestration layer.

Pattern:
  - In-memory dict keyed by user_id (single-process Uvicorn -- fine).
  - report() called at each natural breakpoint (start_summary, end_summary,
    start_enrich, start_graph, etc.) updates phase + counts.
  - get() returns current state for poll endpoint.
  - clear() called at pipeline end -- frontend stops polling when phase=done.

State shape:
  {
    "phase": "summary" | "enrich" | "graph" | "suggest" | "duplicates" | "done" | None,
    "step_th": "AI กำลังสรุปไฟล์ 3/8",
    "step_en": "Summarizing 3/8",
    "current": 3,
    "total": 8,
    "started_at": ISO8601,
    "elapsed_sec": int,
    "etag": int,  # bumped each update -- frontend uses to detect change
  }
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

# Thread-safe in-memory store. Uvicorn runs single-process so a plain dict
# guarded by a Lock is sufficient. For multi-worker production, swap for
# Redis or DB column.
_LOCK = threading.Lock()
_STATE: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def start(user_id: str, phase: str = "starting", step_th: str = "", step_en: str = "") -> None:
    """Initialize tracking for a user. Resets any previous state.

    v10.0.5 — also seeds the `history` list so the frontend can render the
    complete phase timeline even if polling fires AFTER some phases finished.
    Without history, fast pipelines (<1.5s/phase) appear as a single 'done'
    row because polling races the backend.
    """
    now_mono = time.monotonic()
    initial_phase = {
        "phase": phase,
        "step_th": step_th or "เริ่มประมวลผล...",
        "step_en": step_en or "Starting...",
        "current": 0,
        "total": 0,
        "started_mono": now_mono,
        "completed_mono": None,
        "started_at": _now_iso(),
        "completed_at": None,
    }
    with _LOCK:
        _STATE[user_id] = {
            "phase": phase,
            "step_th": initial_phase["step_th"],
            "step_en": initial_phase["step_en"],
            "current": 0,
            "total": 0,
            "started_at": initial_phase["started_at"],
            "_started_mono": now_mono,
            "elapsed_sec": 0,
            "etag": 1,
            "history": [initial_phase],
        }


def report(
    user_id: str,
    phase: Optional[str] = None,
    step_th: Optional[str] = None,
    step_en: Optional[str] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """Update fields. Anything passed as None keeps existing value.

    v10.0.5 — also maintains history list. New phase name → close previous
    history entry (set completed_mono) + push new entry. Same phase name →
    update last entry's step text/counters in place.
    """
    with _LOCK:
        s = _STATE.get(user_id)
        if s is None:
            # Race -- caller forgot to start(). Auto-init silently.
            start(user_id)
            s = _STATE[user_id]

        now_mono = time.monotonic()
        prev_phase = s.get("phase")
        if phase is not None:
            s["phase"] = phase
        if step_th is not None:
            s["step_th"] = step_th
        if step_en is not None:
            s["step_en"] = step_en
        if current is not None:
            s["current"] = current
        if total is not None:
            s["total"] = total
        started_mono = s.get("_started_mono") or now_mono
        s["elapsed_sec"] = int(now_mono - started_mono)
        s["etag"] = s.get("etag", 0) + 1

        # ── History maintenance ────────────────────────────────────────
        history = s.setdefault("history", [])
        if phase is not None and phase != prev_phase:
            # Close out the previous entry
            if history:
                last = history[-1]
                if last.get("completed_mono") is None:
                    last["completed_mono"] = now_mono
                    last["completed_at"] = _now_iso()
            history.append({
                "phase": phase,
                "step_th": step_th or s.get("step_th", ""),
                "step_en": step_en or s.get("step_en", ""),
                "current": current or 0,
                "total": total or 0,
                "started_mono": now_mono,
                "completed_mono": None,
                "started_at": _now_iso(),
                "completed_at": None,
            })
        elif history:
            # Same phase — refresh latest entry's details
            last = history[-1]
            if step_th is not None:
                last["step_th"] = step_th
            if step_en is not None:
                last["step_en"] = step_en
            if current is not None:
                last["current"] = current
            if total is not None:
                last["total"] = total


def done(user_id: str, step_th: str = "เสร็จสมบูรณ์", step_en: str = "Complete") -> None:
    """Mark pipeline finished. State stays available for ~60s so frontend can fetch the final 'done' marker."""
    with _LOCK:
        s = _STATE.get(user_id)
        if s is None:
            return
        now_mono = time.monotonic()
        prev_phase = s.get("phase")
        s["phase"] = "done"
        s["step_th"] = step_th
        s["step_en"] = step_en
        started_mono = s.get("_started_mono") or now_mono
        s["elapsed_sec"] = int(now_mono - started_mono)
        s["etag"] = s.get("etag", 0) + 1
        s["_done_at"] = now_mono
        # Append done entry into history (close previous phase first)
        history = s.setdefault("history", [])
        if history and history[-1].get("completed_mono") is None:
            history[-1]["completed_mono"] = now_mono
            history[-1]["completed_at"] = _now_iso()
        if prev_phase != "done":
            history.append({
                "phase": "done",
                "step_th": step_th,
                "step_en": step_en,
                "current": 0,
                "total": 0,
                "started_mono": now_mono,
                "completed_mono": now_mono,
                "started_at": _now_iso(),
                "completed_at": _now_iso(),
            })


def error(user_id: str, message: str) -> None:
    """Mark pipeline failed -- frontend can surface the message."""
    with _LOCK:
        s = _STATE.get(user_id)
        if s is None:
            start(user_id)
            s = _STATE[user_id]
        now_mono = time.monotonic()
        s["phase"] = "error"
        s["step_th"] = message[:200]
        s["step_en"] = message[:200]
        started_mono = s.get("_started_mono") or now_mono
        s["elapsed_sec"] = int(now_mono - started_mono)
        s["etag"] = s.get("etag", 0) + 1
        s["_done_at"] = now_mono
        history = s.setdefault("history", [])
        if history and history[-1].get("completed_mono") is None:
            history[-1]["completed_mono"] = now_mono
            history[-1]["completed_at"] = _now_iso()
        history.append({
            "phase": "error",
            "step_th": message[:200],
            "step_en": message[:200],
            "current": 0,
            "total": 0,
            "started_mono": now_mono,
            "completed_mono": now_mono,
            "started_at": _now_iso(),
            "completed_at": _now_iso(),
        })


def clear(user_id: str) -> None:
    """Remove state entry (called on terminal poll or after grace period)."""
    with _LOCK:
        _STATE.pop(user_id, None)


def get(user_id: str) -> Optional[dict]:
    """Return public-facing snapshot + full history. None if no pipeline running.

    v10.0.5 — also returns `history` so frontend can render the complete
    timeline including phases that finished before polling caught up.
    Each history entry has elapsed_sec computed from monotonic timestamps
    (race-free) so the UI can show "✓ phase X — 5.2s" reliably.
    """
    with _LOCK:
        s = _STATE.get(user_id)
        if s is None:
            return None
        now_mono = time.monotonic()
        history_public = []
        for h in s.get("history", []):
            start_m = h.get("started_mono") or 0
            end_m = h.get("completed_mono")
            elapsed = (end_m - start_m) if end_m else (now_mono - start_m)
            history_public.append({
                "phase": h.get("phase"),
                "step_th": h.get("step_th"),
                "step_en": h.get("step_en"),
                "current": h.get("current", 0),
                "total": h.get("total", 0),
                "started_at": h.get("started_at"),
                "completed_at": h.get("completed_at"),
                "is_completed": end_m is not None,
                "elapsed_sec": round(elapsed, 2),
            })
        return {
            "phase": s.get("phase"),
            "step_th": s.get("step_th"),
            "step_en": s.get("step_en"),
            "current": s.get("current", 0),
            "total": s.get("total", 0),
            "started_at": s.get("started_at"),
            "elapsed_sec": s.get("elapsed_sec", 0),
            "etag": s.get("etag", 1),
            "history": history_public,
        }


def gc_stale(max_age_sec: int = 300) -> int:
    """Remove entries older than max_age_sec (default 5 min). Called periodically."""
    cutoff = time.monotonic() - max_age_sec
    removed = 0
    with _LOCK:
        stale = [
            uid for uid, s in _STATE.items()
            if s.get("_done_at") and s["_done_at"] < cutoff
        ]
        for uid in stale:
            _STATE.pop(uid, None)
            removed += 1
    return removed
