"""Deterministic importance scoring สำหรับ v11.0.0 Hybrid Clustering.

หน้าที่:
- คำนวณ "ความสำคัญ" ของไฟล์ 0-100 จาก factors ที่อธิบายได้
- แทน LLM-based importance ของ legacy (subjective, non-deterministic)

Factors (weight-based, 0-100 total):
- text_length (0-40):       longer = ข้อมูลเยอะกว่า (log scale)
- embedding_centrality (0-30): close to cluster centroid = "core" doc
- recency (0-15):           uploaded recently = อาจ relevant กว่า
- source_of_truth (0-10):   user flag → boost
- reference_count (0-5):    ใน graph มีไฟล์อื่นอ้างถึง = สำคัญ

Returns dict ที่ explainable — user เห็น breakdown ได้ทำไมไฟล์นี้ได้คะแนนนี้

ใช้โดย:
- backend/clustering.py — score แต่ละไฟล์หลัง HDBSCAN cluster
- (อนาคต) backend/organizer.py — fallback importance ตอน LLM unavailable

Plan ref: .agent-memory/plans/organize-refactor-v11.md (Step 1.2)
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


def heuristic_importance(
    file,
    centrality: float = 0.5,
    reference_count: int = 0,
) -> dict:
    """Compute deterministic importance score 0-100.

    Args:
        file: File ORM object (ต้องมี extracted_text, uploaded_at, source_of_truth)
        centrality: 0-1 = position within cluster (1 = centroid, 0 = edge).
                    คำนวณใน clustering._compute_centrality()
        reference_count: optional — จำนวนไฟล์อื่นที่ "อ้างถึง" ไฟล์นี้ ใน graph
                         (default 0 ถ้ายังไม่มี graph ตอน clustering)

    Returns:
        {
            "score": int 0-100,
            "label": "high" | "medium" | "low",
            "factors": {
                "text_length": int 0-40,
                "centrality": int 0-30,
                "recency": int 0-15,
                "source_of_truth": int 0-10,
                "references": int 0-5,
            }
        }

    Score interpretation:
        - 0-39:   low (peripheral, draft, old)
        - 40-69:  medium (relevant but not core)
        - 70-100: high (core document, recent + central + flagged)
    """
    # ─── Factor 1: text_length (log scale, 0-40 points) ──────────
    # WHY log scale: 1K char → 30, 10K → 40, 100K → diminishing
    # ไฟล์สั้นๆ ไม่ค่อยมีข้อมูลเชิงลึก แต่ไฟล์ยาวๆ ก็ไม่จำเป็นต้องสำคัญแบบ linear
    text_len = len(getattr(file, "extracted_text", "") or "")
    if text_len == 0:
        len_score = 0.0
    else:
        # log10(1) = 0 (ไฟล์ 1 char → 0 points)
        # log10(1000) = 3 → 30 points
        # log10(10000) = 4 → 40 points (capped)
        len_score = min(40.0, math.log10(max(text_len, 1)) * 10)

    # ─── Factor 2: centrality (0-30 points) ──────────────────────
    # 0 = at cluster edge, 1 = at centroid
    cent_score = max(0.0, min(1.0, centrality)) * 30

    # ─── Factor 3: recency (0-15 points) ─────────────────────────
    # < 7 days: full 15 points
    # 7-365 days: linear decay
    # > 365 days: 0 points
    uploaded_at = getattr(file, "uploaded_at", None)
    if uploaded_at is None:
        rec_score = 7.5  # neutral when unknown
    else:
        # Ensure timezone-aware
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - uploaded_at).days
        if age_days <= 7:
            rec_score = 15.0
        elif age_days >= 365:
            rec_score = 0.0
        else:
            # Linear decay จาก 15 → 0 ระหว่าง day 7 → day 365
            rec_score = 15.0 * (1.0 - (age_days - 7) / (365 - 7))

    # ─── Factor 4: source_of_truth flag (0-10 points) ────────────
    sot_score = 10.0 if getattr(file, "source_of_truth", False) else 0.0

    # ─── Factor 5: reference_count (0-5 points) ──────────────────
    # Diminishing returns: 0 ref = 0, 1 ref = 0.5, ..., 10+ ref = 5 (capped)
    ref_score = min(5.0, max(0, reference_count) * 0.5)

    # ─── Total + label ───────────────────────────────────────────
    total = len_score + cent_score + rec_score + sot_score + ref_score
    total_int = max(0, min(100, int(round(total))))

    label = _score_to_label(total_int)

    return {
        "score": total_int,
        "label": label,
        "factors": {
            "text_length": int(round(len_score)),
            "centrality": int(round(cent_score)),
            "recency": int(round(rec_score)),
            "source_of_truth": int(round(sot_score)),
            "references": int(round(ref_score)),
        },
    }


def _score_to_label(score: int) -> str:
    """Map numeric score → label string.

    Same thresholds as legacy importance (organizer.py).
    """
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


# ═══════════════════════════════════════════════════════════════
# Convenience helper (for callers ที่ไม่อยากเรียก dict subscript)
# ═══════════════════════════════════════════════════════════════
def heuristic_score(file, centrality: float = 0.5) -> int:
    """Shortcut: return just the integer score (0-100)."""
    return heuristic_importance(file, centrality)["score"]
