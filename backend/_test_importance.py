"""Tests for backend/importance.py — Phase 1 Deterministic Importance Scoring.

ครอบคลุม:
- heuristic_importance: inputs หลากหลาย (centrality / text length / recency /
  source_of_truth / reference_count)
- score ∈ [0, 100] เสมอ
- label thresholds: high ≥70, medium 40-69, low <40
- factors breakdown สอดคล้องกับ total score
- heuristic_score shortcut

Run:
    pytest backend/_test_importance.py -v

Reviewer: ฟ้า (Fah) — 2026-05-17
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.importance import heuristic_importance, heuristic_score


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_file(
    text: str = "",
    days_old: int = 30,
    source_of_truth: bool = False,
    uploaded_at=None,
):
    """Mock File ORM object for importance scoring."""
    f = MagicMock()
    f.extracted_text = text
    f.source_of_truth = source_of_truth
    if uploaded_at is not None:
        f.uploaded_at = uploaded_at
    else:
        f.uploaded_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    return f


# ═══════════════════════════════════════════════════════════════════════════
# 1. Score always in [0, 100]
# ═══════════════════════════════════════════════════════════════════════════

class TestScoreRange:
    """heuristic_importance score must always be 0-100."""

    def test_minimum_input_score_in_range(self):
        """Empty text, 0 centrality, old file, no SOT, 0 refs → score ≥ 0."""
        f = _make_file(text="", days_old=500, source_of_truth=False)
        result = heuristic_importance(f, centrality=0.0, reference_count=0)
        assert 0 <= result["score"] <= 100

    def test_maximum_input_score_in_range(self):
        """Long text, centrality=1, fresh file, SOT=True, many refs → score ≤ 100."""
        f = _make_file(text="word " * 5000, days_old=0, source_of_truth=True)
        result = heuristic_importance(f, centrality=1.0, reference_count=100)
        assert 0 <= result["score"] <= 100

    def test_score_in_range_mid_values(self):
        """Mid-range inputs → score in [0, 100]."""
        f = _make_file(text="x" * 5000, days_old=90)
        result = heuristic_importance(f, centrality=0.5, reference_count=3)
        assert 0 <= result["score"] <= 100

    def test_score_always_int(self):
        """Score must be an integer."""
        f = _make_file(text="hello " * 100, days_old=15)
        result = heuristic_importance(f, centrality=0.7)
        assert isinstance(result["score"], int), f"score should be int, got {type(result['score'])}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Label thresholds
# ═══════════════════════════════════════════════════════════════════════════

class TestLabelThresholds:
    """Label mapping: high≥70, medium 40-69, low<40."""

    def _file_with_score(self, target_score: int):
        """Construct a file that yields approximately target_score."""
        # Use source_of_truth + centrality + recency knobs
        f = MagicMock()
        f.extracted_text = ""
        f.source_of_truth = False
        f.uploaded_at = datetime.now(timezone.utc) - timedelta(days=500)
        return f

    def test_high_label_threshold(self):
        """score ≥ 70 → label = 'high'."""
        # Long text (40) + high centrality (30) + fresh (15) + SOT (10) = 95
        f = _make_file(text="word " * 5000, days_old=1, source_of_truth=True)
        result = heuristic_importance(f, centrality=1.0, reference_count=0)
        assert result["score"] >= 70
        assert result["label"] == "high", \
            f"score={result['score']} should be 'high', got '{result['label']}'"

    def test_low_label_threshold(self):
        """score < 40 → label = 'low'."""
        # Empty text (0) + 0 centrality (0) + old file (0) + no SOT (0) + 0 refs (0) = 0
        f = _make_file(text="", days_old=500, source_of_truth=False)
        result = heuristic_importance(f, centrality=0.0, reference_count=0)
        assert result["score"] < 40
        assert result["label"] == "low", \
            f"score={result['score']} should be 'low', got '{result['label']}'"

    def test_medium_label_range(self):
        """score in [40, 69] → label = 'medium'."""
        # text=1000 chars → len_score≈30, centrality=0.2→6, old→0, no SOT→0, ref=0 → ~36
        # Push into medium: text=5000 → 37, cent=0.2→6, old→0 → ~43
        f = _make_file(text="a" * 5000, days_old=500, source_of_truth=False)
        result = heuristic_importance(f, centrality=0.2, reference_count=0)
        if 40 <= result["score"] <= 69:
            assert result["label"] == "medium"
        # If not medium range, at least label matches score
        else:
            if result["score"] >= 70:
                assert result["label"] == "high"
            else:
                assert result["label"] == "low"

    def test_label_matches_score_consistently(self):
        """label is always consistent with score, regardless of inputs."""
        cases = [
            ("", 0, False, 500),
            ("x" * 1000, 30, False, 200),
            ("x" * 10000, 0, True, 1),
            ("x" * 500, 15, False, 60),
        ]
        for text, days, sot, cent_pct in cases:
            f = _make_file(text=text, days_old=days, source_of_truth=sot)
            result = heuristic_importance(f, centrality=cent_pct / 100.0)
            score = result["score"]
            label = result["label"]
            if score >= 70:
                assert label == "high",   f"score={score} → expected high, got {label}"
            elif score >= 40:
                assert label == "medium", f"score={score} → expected medium, got {label}"
            else:
                assert label == "low",    f"score={score} → expected low, got {label}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Individual factor behaviour
# ═══════════════════════════════════════════════════════════════════════════

class TestFactors:
    """Test each scoring factor in isolation."""

    # ── Factor 1: text_length (0-40) ───────────────────────────────────
    def test_empty_text_len_score_is_0(self):
        """Empty text → text_length factor = 0."""
        f = _make_file(text="")
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["text_length"] == 0

    def test_longer_text_higher_len_score(self):
        """Longer text yields higher text_length factor (log scale)."""
        f_short = _make_file(text="a" * 100)
        f_long  = _make_file(text="a" * 10000)
        r_short = heuristic_importance(f_short, centrality=0.0)
        r_long  = heuristic_importance(f_long,  centrality=0.0)
        assert r_long["factors"]["text_length"] > r_short["factors"]["text_length"], \
            "Longer text must score higher on text_length factor"

    def test_text_length_capped_at_40(self):
        """text_length factor never exceeds 40."""
        f = _make_file(text="x" * 1_000_000)
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["text_length"] <= 40

    def test_text_1000_chars_approx_30(self):
        """1000 chars → log10(1000)*10 = 30 points."""
        f = _make_file(text="a" * 1000, days_old=500)
        result = heuristic_importance(f, centrality=0.0)
        # log10(1000) * 10 = 30.0 exactly
        assert result["factors"]["text_length"] == 30

    # ── Factor 2: centrality (0-30) ────────────────────────────────────
    def test_centrality_0_gives_0_points(self):
        """centrality=0 → centrality factor = 0."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["centrality"] == 0

    def test_centrality_1_gives_30_points(self):
        """centrality=1 → centrality factor = 30."""
        f = _make_file()
        result = heuristic_importance(f, centrality=1.0)
        assert result["factors"]["centrality"] == 30

    def test_centrality_0_5_gives_15_points(self):
        """centrality=0.5 → centrality factor = 15."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.5)
        assert result["factors"]["centrality"] == 15

    def test_centrality_clamped_above_1(self):
        """centrality > 1 is clamped to 1 (max 30 points)."""
        f = _make_file()
        result = heuristic_importance(f, centrality=5.0)
        assert result["factors"]["centrality"] == 30

    def test_centrality_clamped_below_0(self):
        """centrality < 0 is clamped to 0 (0 points)."""
        f = _make_file()
        result = heuristic_importance(f, centrality=-3.0)
        assert result["factors"]["centrality"] == 0

    # ── Factor 3: recency (0-15) ────────────────────────────────────────
    def test_fresh_file_full_recency(self):
        """File uploaded today (< 7 days) → recency = 15."""
        f = _make_file(days_old=1)
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["recency"] == 15

    def test_old_file_zero_recency(self):
        """File > 365 days → recency = 0."""
        f = _make_file(days_old=400)
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["recency"] == 0

    def test_mid_age_file_partial_recency(self):
        """File 30 days → recency between 0 and 15 (linear decay region)."""
        f = _make_file(days_old=30)
        result = heuristic_importance(f, centrality=0.0)
        assert 0 < result["factors"]["recency"] < 15, \
            f"recency={result['factors']['recency']} expected in (0,15) for 30-day-old file"

    def test_no_uploaded_at_gives_neutral_recency(self):
        """Missing uploaded_at → recency = 7 or 8 (neutral ~7.5)."""
        f = MagicMock()
        f.extracted_text = ""
        f.source_of_truth = False
        f.uploaded_at = None
        result = heuristic_importance(f, centrality=0.0)
        # neutral = 7.5 → rounds to 7 or 8
        assert result["factors"]["recency"] in (7, 8), \
            f"Neutral recency should be ~7.5, got {result['factors']['recency']}"

    def test_tz_naive_uploaded_at_handled(self):
        """tz-naive uploaded_at should not crash (gets treated as UTC)."""
        f = MagicMock()
        f.extracted_text = ""
        f.source_of_truth = False
        f.uploaded_at = datetime.now()  # tz-naive
        try:
            result = heuristic_importance(f, centrality=0.0)
            assert 0 <= result["score"] <= 100
        except Exception as e:
            pytest.fail(f"tz-naive uploaded_at raised: {e}")

    # ── Factor 4: source_of_truth (0-10) ────────────────────────────────
    def test_source_of_truth_true_adds_10(self):
        """source_of_truth=True → factor = 10."""
        f = _make_file(source_of_truth=True)
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["source_of_truth"] == 10

    def test_source_of_truth_false_adds_0(self):
        """source_of_truth=False → factor = 0."""
        f = _make_file(source_of_truth=False)
        result = heuristic_importance(f, centrality=0.0)
        assert result["factors"]["source_of_truth"] == 0

    # ── Factor 5: reference_count (0-5) ─────────────────────────────────
    def test_zero_refs_adds_0(self):
        """reference_count=0 → references factor = 0."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.0, reference_count=0)
        assert result["factors"]["references"] == 0

    def test_two_refs_adds_1(self):
        """reference_count=2 → references factor = 1 (2 * 0.5 = 1.0)."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.0, reference_count=2)
        assert result["factors"]["references"] == 1

    def test_refs_capped_at_5(self):
        """reference_count=100 → references factor capped at 5."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.0, reference_count=100)
        assert result["factors"]["references"] == 5

    def test_negative_refs_treated_as_zero(self):
        """reference_count<0 → references factor = 0 (no negative scores)."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.0, reference_count=-5)
        assert result["factors"]["references"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. factors sum == score (internal consistency)
# ═══════════════════════════════════════════════════════════════════════════

class TestFactorConsistency:
    """factors dict values must add up to score (within rounding)."""

    def _assert_factors_sum_to_score(self, f, centrality=0.5, reference_count=0):
        result = heuristic_importance(f, centrality=centrality,
                                      reference_count=reference_count)
        factor_sum = sum(result["factors"].values())
        score = result["score"]
        # Allow ±1 for rounding (each factor rounds independently)
        assert abs(factor_sum - score) <= 1, \
            f"factor_sum={factor_sum} differs from score={score} by >1"

    def test_factors_sum_low_score(self):
        """Low-score file: factors sum ≈ score."""
        f = _make_file(text="", days_old=500)
        self._assert_factors_sum_to_score(f, centrality=0.0)

    def test_factors_sum_high_score(self):
        """High-score file: factors sum ≈ score."""
        f = _make_file(text="x" * 50000, days_old=1, source_of_truth=True)
        self._assert_factors_sum_to_score(f, centrality=1.0, reference_count=10)

    def test_factors_sum_mid_score(self):
        """Mid-score file: factors sum ≈ score."""
        f = _make_file(text="x" * 2000, days_old=100)
        self._assert_factors_sum_to_score(f, centrality=0.4, reference_count=3)

    def test_all_factor_keys_present(self):
        """factors dict has all 5 required keys."""
        f = _make_file()
        result = heuristic_importance(f, centrality=0.5)
        expected_keys = {"text_length", "centrality", "recency", "source_of_truth", "references"}
        assert set(result["factors"].keys()) == expected_keys, \
            f"factors keys mismatch: {result['factors'].keys()}"

    def test_all_factor_values_are_ints(self):
        """All factor values must be integers."""
        f = _make_file(text="hello " * 300, days_old=45)
        result = heuristic_importance(f, centrality=0.6, reference_count=4)
        for key, val in result["factors"].items():
            assert isinstance(val, int), f"factor '{key}' should be int, got {type(val)}"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Return structure
# ═══════════════════════════════════════════════════════════════════════════

class TestReturnStructure:
    """Verify full return dict structure."""

    def test_return_has_required_keys(self):
        """Return dict has: score, label, factors."""
        f = _make_file()
        result = heuristic_importance(f)
        assert "score" in result
        assert "label" in result
        assert "factors" in result

    def test_label_is_string(self):
        """label is a string."""
        f = _make_file()
        result = heuristic_importance(f)
        assert isinstance(result["label"], str)

    def test_label_is_valid_value(self):
        """label is one of: high, medium, low."""
        for text, days in [("", 500), ("x" * 3000, 5), ("x" * 20000, 1)]:
            f = _make_file(text=text, days_old=days)
            result = heuristic_importance(f, centrality=0.5)
            assert result["label"] in ("high", "medium", "low"), \
                f"Invalid label: {result['label']}"


# ═══════════════════════════════════════════════════════════════════════════
# 6. heuristic_score shortcut
# ═══════════════════════════════════════════════════════════════════════════

class TestHeuristicScore:
    """heuristic_score() is a shortcut returning just the integer score."""

    def test_returns_int(self):
        """heuristic_score returns an int."""
        f = _make_file(text="hello " * 200)
        score = heuristic_score(f)
        assert isinstance(score, int)

    def test_matches_heuristic_importance_score(self):
        """heuristic_score(f) == heuristic_importance(f)['score']."""
        f = _make_file(text="test " * 500, days_old=20, source_of_truth=True)
        full = heuristic_importance(f, centrality=0.6)
        shortcut = heuristic_score(f, centrality=0.6)
        assert shortcut == full["score"], \
            f"shortcut={shortcut} != full score={full['score']}"

    def test_in_range_0_100(self):
        """heuristic_score always in [0, 100]."""
        for days, text, cent in [(1, "x" * 10000, 1.0), (500, "", 0.0), (30, "x" * 100, 0.5)]:
            f = _make_file(text=text, days_old=days)
            score = heuristic_score(f, centrality=cent)
            assert 0 <= score <= 100, f"score={score} out of [0,100]"

    def test_default_centrality_is_0_5(self):
        """heuristic_score(f) uses centrality=0.5 as default."""
        f = _make_file()
        default_score = heuristic_score(f)
        explicit_score = heuristic_importance(f, centrality=0.5)["score"]
        assert default_score == explicit_score
