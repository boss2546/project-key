"""Tests for backend/clustering.py — Phase 1 Hybrid Clustering.

ครอบคลุม:
- _reduce_dimensions: N=3,5,10,31,50 — ไม่ crash + n_comp ถูกต้อง
- _compute_centrality: values in [0,1], noise=0.5, single-member=1.0
- cluster_files_hybrid([]): empty corpus → {"clusters": []}
- cluster_files_hybrid mock: output schema + all files accounted
- _llm_label_cluster mock: output schema + label validation

Run:
    pytest backend/_test_clustering.py -v

Reviewer: ฟ้า (Fah) — 2026-05-17
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.clustering import (
    _compute_centrality,
    _llm_label_cluster,
    _reduce_dimensions,
    cluster_files_hybrid,
)
from backend.config import UMAP_N_COMPONENTS


# ── Helpers ─────────────────────────────────────────────────────────────────

def _run(coro):
    """Run async coroutine synchronously (creates new event loop each call)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _fake_vectors(n: int, dim: int = 768, seed: int = 42) -> np.ndarray:
    """Seeded random float32 vectors for reproducibility."""
    rng = np.random.default_rng(seed)
    return rng.random((n, dim)).astype(np.float32)


def _make_file(
    file_id: str,
    text: str = "content word " * 150,
    filename: str = "doc.pdf",
    source_of_truth: bool = False,
):
    """Mock File ORM object with required attributes."""
    from datetime import datetime, timezone
    f = MagicMock()
    f.id = file_id
    f.filename = filename
    f.extracted_text = text
    f.source_of_truth = source_of_truth
    f.uploaded_at = datetime.now(timezone.utc)
    return f


# ═══════════════════════════════════════════════════════════════════════════
# 1. _reduce_dimensions — UMAP edge-case fix (MSG-V11-UMAP-EDGE-CASE)
# ═══════════════════════════════════════════════════════════════════════════

class TestReduceDimensions:
    """Verify UMAP dynamic n_components fix across boundary N values."""

    # ── N < 5: skip UMAP, return raw vectors ────────────────────────────
    def test_n3_skips_umap_returns_raw_shape(self):
        """N=3 < 5: UMAP skipped, output shape == input shape."""
        v = _fake_vectors(3)
        result = _reduce_dimensions(v, 3)
        assert result.shape == (3, 768), f"Got {result.shape}, expected (3, 768)"

    def test_n4_skips_umap_returns_raw_shape(self):
        """N=4 < 5: UMAP skipped, output shape == input shape."""
        v = _fake_vectors(4)
        result = _reduce_dimensions(v, 4)
        assert result.shape == (4, 768)

    def test_n3_no_exception(self):
        """N=3 must not raise any exception."""
        try:
            _reduce_dimensions(_fake_vectors(3), 3)
        except Exception as e:
            pytest.fail(f"N=3 raised unexpectedly: {type(e).__name__}: {e}")

    def test_n4_no_exception(self):
        """N=4 must not raise any exception."""
        try:
            _reduce_dimensions(_fake_vectors(4), 4)
        except Exception as e:
            pytest.fail(f"N=4 raised unexpectedly: {type(e).__name__}: {e}")

    # ── N >= 5: UMAP runs with dynamic n_comp ───────────────────────────
    def test_n5_correct_n_comp(self):
        """N=5: n_comp = min(UMAP_N_COMPONENTS, max(2, 5-2)) = min(30,3) = 3."""
        expected = min(UMAP_N_COMPONENTS, max(2, 5 - 2))  # = 3
        result = _reduce_dimensions(_fake_vectors(5), 5)
        assert result.shape == (5, expected), \
            f"N=5: expected (5,{expected}), got {result.shape}"

    def test_n5_no_exception(self):
        """N=5 boundary — UMAP with 3 components must not crash."""
        try:
            _reduce_dimensions(_fake_vectors(5), 5)
        except Exception as e:
            pytest.fail(f"N=5 raised: {type(e).__name__}: {e}")

    def test_n10_correct_n_comp(self):
        """N=10: n_comp = min(30, max(2, 8)) = 8."""
        expected = min(UMAP_N_COMPONENTS, max(2, 10 - 2))  # = 8
        result = _reduce_dimensions(_fake_vectors(10), 10)
        assert result.shape == (10, expected), \
            f"N=10: expected (10,{expected}), got {result.shape}"

    def test_n31_correct_n_comp(self):
        """N=31: n_comp = min(30, max(2, 29)) = 29 (one below full UMAP_N_COMPONENTS)."""
        expected = min(UMAP_N_COMPONENTS, max(2, 31 - 2))  # = 29
        result = _reduce_dimensions(_fake_vectors(31), 31)
        assert result.shape == (31, expected), \
            f"N=31: expected (31,{expected}), got {result.shape}"

    def test_n50_uses_full_umap_n_components(self):
        """N=50: n_comp = min(30, max(2, 48)) = 30 = UMAP_N_COMPONENTS."""
        expected = min(UMAP_N_COMPONENTS, max(2, 50 - 2))  # = 30
        result = _reduce_dimensions(_fake_vectors(50), 50)
        assert result.shape == (50, expected), \
            f"N=50: expected (50,{expected}), got {result.shape}"

    def test_row_count_preserved_for_all_n(self):
        """Output row count always == input N (no files dropped)."""
        for n in [3, 4, 5, 10, 31, 50]:
            v = _fake_vectors(n)
            result = _reduce_dimensions(v, n)
            assert result.shape[0] == n, \
                f"N={n}: output has {result.shape[0]} rows, expected {n}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. _compute_centrality
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeCentrality:
    """Test centrality scores: range, noise neutrality, single-member, centroid."""

    def test_values_in_0_1(self):
        """All centrality values must be in [0.0, 1.0]."""
        rng = np.random.default_rng(10)
        reduced = rng.random((20, 10)).astype(np.float32)
        labels = np.array([0]*8 + [1]*7 + [-1]*5)
        result = _compute_centrality(reduced, labels)
        assert result.min() >= 0.0, f"min={result.min()} < 0"
        assert result.max() <= 1.0, f"max={result.max()} > 1"

    def test_noise_points_exactly_0_5(self):
        """Noise files (label=-1) must have centrality = 0.5 (neutral)."""
        rng = np.random.default_rng(11)
        reduced = rng.random((10, 8)).astype(np.float32)
        labels = np.array([0]*5 + [-1]*5)
        result = _compute_centrality(reduced, labels)
        noise_vals = result[labels == -1]
        np.testing.assert_array_equal(
            noise_vals,
            np.full(5, 0.5, dtype=np.float32),
            err_msg="All noise points must have centrality exactly 0.5",
        )

    def test_all_noise_stays_0_5(self):
        """All-noise corpus: every value = 0.5."""
        reduced = np.random.default_rng(12).random((6, 4)).astype(np.float32)
        labels = np.array([-1] * 6)
        result = _compute_centrality(reduced, labels)
        np.testing.assert_array_equal(result, np.full(6, 0.5, dtype=np.float32))

    def test_single_member_cluster_is_1(self):
        """A cluster with only 1 member → centrality = 1.0."""
        rng = np.random.default_rng(13)
        reduced = rng.random((5, 8)).astype(np.float32)
        # cluster 0 = index 0 only; cluster 1 = indices 1-3; noise = index 4
        labels = np.array([0, 1, 1, 1, -1])
        result = _compute_centrality(reduced, labels)
        assert result[0] == pytest.approx(1.0, abs=1e-5), \
            f"Single-member cluster should have centrality=1.0, got {result[0]}"

    def test_centroid_has_highest_centrality_in_cluster(self):
        """Point exactly at cluster centroid gets centrality = 1.0."""
        # Three collinear points: [0,0], [2,0], [1,0] → centroid = [1,0]
        reduced = np.array([[0.0, 0.0], [2.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        labels = np.array([0, 0, 0])
        result = _compute_centrality(reduced, labels)
        # Index 2 is at centroid → distance = 0 → centrality = 1.0
        assert result[2] == pytest.approx(1.0, abs=1e-5), \
            f"Centroid point should have centrality=1.0, got {result[2]}"
        # Endpoints are at max distance → centrality = 0.0
        assert result[0] == pytest.approx(0.0, abs=1e-5)
        assert result[1] == pytest.approx(0.0, abs=1e-5)

    def test_output_length_matches_input(self):
        """Output array length == input length."""
        reduced = np.random.default_rng(14).random((15, 10)).astype(np.float32)
        labels = np.array([0]*6 + [1]*5 + [-1]*4)
        result = _compute_centrality(reduced, labels)
        assert len(result) == 15

    def test_two_clusters_no_crash(self):
        """Two real clusters — no exception, values in [0,1]."""
        rng = np.random.default_rng(15)
        reduced = rng.random((12, 6)).astype(np.float32)
        labels = np.array([0]*6 + [1]*6)
        result = _compute_centrality(reduced, labels)
        assert result.shape == (12,)
        assert all(0.0 <= v <= 1.0 for v in result)


# ═══════════════════════════════════════════════════════════════════════════
# 3. cluster_files_hybrid — empty corpus
# ═══════════════════════════════════════════════════════════════════════════

class TestClusterFilesHybridEmpty:
    """Empty file list returns {"clusters": []} immediately."""

    def test_empty_returns_empty_clusters(self):
        """cluster_files_hybrid([]) == {"clusters": []}."""
        result = _run(cluster_files_hybrid([]))
        assert result == {"clusters": []}, f"Expected empty clusters, got {result}"

    def test_empty_has_clusters_key(self):
        """Return value has 'clusters' key as a list."""
        result = _run(cluster_files_hybrid([]))
        assert "clusters" in result
        assert isinstance(result["clusters"], list)
        assert len(result["clusters"]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. cluster_files_hybrid — mocked pipeline (shape + completeness)
# ═══════════════════════════════════════════════════════════════════════════

class TestClusterFilesHybridMocked:
    """Verify output schema and file completeness via mocked dependencies."""

    def _make_files(self, n: int):
        return [_make_file(f"file_{i}", text="word " * 200) for i in range(n)]

    def _fake_embed_dict(self, files):
        return {f.id: _fake_vectors(1, 768, seed=i)[0].tolist()
                for i, f in enumerate(files)}

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    @patch("backend.clustering.call_llm_json")
    def test_output_schema_valid(self, mock_llm, mock_embed, _mock_avail):
        """Each cluster has: temp_id, title, summary, files (list)."""
        files = self._make_files(6)
        mock_embed.return_value = self._fake_embed_dict(files)
        mock_llm.return_value = {"title": "กลุ่มทดสอบ", "summary": "คำอธิบาย"}

        result = _run(cluster_files_hybrid(files))

        assert "clusters" in result
        for cluster in result["clusters"]:
            assert "temp_id" in cluster,    "Missing temp_id"
            assert "title" in cluster,      "Missing title"
            assert "summary" in cluster,    "Missing summary"
            assert "files" in cluster,      "Missing files array"
            assert isinstance(cluster["files"], list)

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    @patch("backend.clustering.call_llm_json")
    def test_file_entries_have_all_fields(self, mock_llm, mock_embed, _mock_avail):
        """Each file entry has all 6 required fields."""
        files = self._make_files(6)
        mock_embed.return_value = self._fake_embed_dict(files)
        mock_llm.return_value = {"title": "กลุ่ม A", "summary": "สรุป A"}

        result = _run(cluster_files_hybrid(files))

        required = {
            "file_id", "relevance", "importance_score",
            "importance_label", "is_primary", "why_important",
        }
        for cluster in result["clusters"]:
            for entry in cluster["files"]:
                missing = required - set(entry.keys())
                assert not missing, f"Missing fields: {missing} in entry {entry}"

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    @patch("backend.clustering.call_llm_json")
    def test_all_files_accounted_no_duplicates(self, mock_llm, mock_embed, _mock_avail):
        """Sum of file_ids across all clusters == input N; no duplicates."""
        n = 8
        files = self._make_files(n)
        mock_embed.return_value = self._fake_embed_dict(files)
        mock_llm.return_value = {"title": "กลุ่ม B", "summary": "สรุป B"}

        result = _run(cluster_files_hybrid(files))

        all_ids = [fe["file_id"] for c in result["clusters"] for fe in c["files"]]
        assert len(all_ids) == n,           f"Expected {n} file entries, got {len(all_ids)}"
        assert len(set(all_ids)) == n,      "Duplicate file_id found across clusters"

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    @patch("backend.clustering.call_llm_json")
    def test_importance_scores_in_range(self, mock_llm, mock_embed, _mock_avail):
        """importance_score for every file must be in [0, 100]."""
        files = self._make_files(6)
        mock_embed.return_value = self._fake_embed_dict(files)
        mock_llm.return_value = {"title": "กลุ่ม C", "summary": "สรุป C"}

        result = _run(cluster_files_hybrid(files))

        for cluster in result["clusters"]:
            for entry in cluster["files"]:
                score = entry["importance_score"]
                assert 0 <= score <= 100, \
                    f"importance_score={score} out of [0,100] for {entry['file_id']}"

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    @patch("backend.clustering.call_llm_json")
    def test_importance_labels_valid(self, mock_llm, mock_embed, _mock_avail):
        """importance_label must be 'high', 'medium', or 'low'."""
        files = self._make_files(6)
        mock_embed.return_value = self._fake_embed_dict(files)
        mock_llm.return_value = {"title": "กลุ่ม D", "summary": "สรุป D"}

        result = _run(cluster_files_hybrid(files))

        valid = {"high", "medium", "low"}
        for cluster in result["clusters"]:
            for entry in cluster["files"]:
                assert entry["importance_label"] in valid, \
                    f"Invalid label: {entry['importance_label']}"

    @patch("backend.clustering.embeddings_available", return_value=False)
    def test_no_api_key_raises_runtime_error(self, _mock_avail):
        """embeddings_available()=False → RuntimeError (caller falls back to legacy)."""
        files = [_make_file("x0")]
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
            _run(cluster_files_hybrid(files))

    @patch("backend.clustering.embeddings_available", return_value=True)
    @patch("backend.clustering.embed_files")
    def test_all_embed_fail_returns_empty_clusters(self, mock_embed, _mock_avail):
        """embed_files returns {} (all fail) → {"clusters": []}."""
        files = [_make_file("y0"), _make_file("y1")]
        mock_embed.return_value = {}  # all embeddings failed
        result = _run(cluster_files_hybrid(files))
        assert result == {"clusters": []}


# ═══════════════════════════════════════════════════════════════════════════
# 5. _llm_label_cluster — output schema + edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestLlmLabelCluster:
    """Test _llm_label_cluster output schema with mocked LLM."""

    @patch("backend.clustering.call_llm_json")
    def test_output_required_keys(self, mock_llm):
        """Output has: temp_id, title, summary, files."""
        mock_llm.return_value = {
            "title": "เอกสารประกันชีวิต",
            "summary": "กลุ่มไฟล์ประกัน",
        }
        files = [_make_file("a0"), _make_file("a1"), _make_file("a2")]
        centralities = {"a0": 0.9, "a1": 0.6, "a2": 0.3}

        result = _run(_llm_label_cluster(files, centralities))

        for key in ("temp_id", "title", "summary", "files"):
            assert key in result, f"Missing key: {key}"
        assert isinstance(result["files"], list)

    @patch("backend.clustering.call_llm_json")
    def test_file_entries_all_fields(self, mock_llm):
        """Each file entry has all 6 required fields."""
        mock_llm.return_value = {"title": "กลุ่ม X", "summary": "สรุป"}
        files = [_make_file("b0"), _make_file("b1")]
        centralities = {"b0": 0.8, "b1": 0.4}

        result = _run(_llm_label_cluster(files, centralities))

        required = {
            "file_id", "relevance", "importance_score",
            "importance_label", "is_primary", "why_important",
        }
        for entry in result["files"]:
            missing = required - set(entry.keys())
            assert not missing, f"Missing: {missing}"

    @patch("backend.clustering.call_llm_json")
    def test_title_from_llm_propagated(self, mock_llm):
        """LLM title appears in result."""
        mock_llm.return_value = {"title": "รายงานการเงิน 2025", "summary": "งบประมาณ"}
        files = [_make_file("c0")]
        result = _run(_llm_label_cluster(files, {"c0": 1.0}))
        assert result["title"] == "รายงานการเงิน 2025"

    @patch("backend.clustering.call_llm_json")
    def test_llm_failure_graceful_fallback(self, mock_llm):
        """LLM exception → fallback title (no crash), schema intact."""
        mock_llm.side_effect = Exception("API timeout")
        files = [_make_file("d0", filename="report.pdf")]
        result = _run(_llm_label_cluster(files, {"d0": 0.9}))
        # Must not crash — schema must still be present
        for key in ("temp_id", "title", "summary", "files"):
            assert key in result, f"Missing key after fallback: {key}"
        assert len(result["files"]) == 1

    @patch("backend.clustering.call_llm_json")
    def test_most_central_file_is_primary(self, mock_llm):
        """File with highest centrality score → is_primary=True."""
        mock_llm.return_value = {"title": "กลุ่มหลัก", "summary": "รายละเอียด"}
        files = [_make_file("e0"), _make_file("e1"), _make_file("e2")]
        # e1 has highest centrality
        centralities = {"e0": 0.3, "e1": 0.95, "e2": 0.6}

        result = _run(_llm_label_cluster(files, centralities))

        primary = next((e for e in result["files"] if e["is_primary"]), None)
        assert primary is not None, "No primary file found"
        assert primary["file_id"] == "e1", \
            f"Expected e1 as primary (centrality=0.95), got {primary['file_id']}"

    @patch("backend.clustering.call_llm_json")
    def test_importance_score_in_range(self, mock_llm):
        """importance_score in [0, 100] for all file entries."""
        mock_llm.return_value = {"title": "กลุ่ม Y", "summary": "ข้อมูล"}
        files = [_make_file(f"f{i}", text="x" * (i * 400)) for i in range(4)]
        centralities = {f"f{i}": i * 0.25 for i in range(4)}

        result = _run(_llm_label_cluster(files, centralities))
        for entry in result["files"]:
            assert 0 <= entry["importance_score"] <= 100, \
                f"importance_score={entry['importance_score']} out of range"

    @patch("backend.clustering.call_llm_json")
    def test_relevance_is_float_in_0_1(self, mock_llm):
        """relevance is a float in [0.0, 1.0]."""
        mock_llm.return_value = {"title": "กลุ่ม Z", "summary": "ข้อมูล Z"}
        files = [_make_file("g0"), _make_file("g1")]
        centralities = {"g0": 0.7, "g1": 0.2}

        result = _run(_llm_label_cluster(files, centralities))
        for entry in result["files"]:
            assert isinstance(entry["relevance"], float), \
                f"relevance should be float, got {type(entry['relevance'])}"
            assert 0.0 <= entry["relevance"] <= 1.0, \
                f"relevance={entry['relevance']} out of [0,1]"

    @patch("backend.clustering.call_llm_json")
    def test_importance_label_valid_values(self, mock_llm):
        """importance_label is 'high', 'medium', or 'low'."""
        mock_llm.return_value = {"title": "กลุ่ม W", "summary": "ข้อมูล W"}
        files = [_make_file(f"h{i}") for i in range(3)]
        centralities = {f"h{i}": 0.5 for i in range(3)}

        result = _run(_llm_label_cluster(files, centralities))
        valid = {"high", "medium", "low"}
        for entry in result["files"]:
            assert entry["importance_label"] in valid, \
                f"Invalid label: {entry['importance_label']}"

    @patch("backend.clustering.call_llm_json")
    def test_all_group_files_in_output(self, mock_llm):
        """All files in group appear in result['files'] (none dropped)."""
        mock_llm.return_value = {"title": "กลุ่ม V", "summary": "ข้อมูล V"}
        n = 5
        files = [_make_file(f"k{i}") for i in range(n)]
        centralities = {f"k{i}": 0.5 for i in range(n)}

        result = _run(_llm_label_cluster(files, centralities))
        result_ids = {e["file_id"] for e in result["files"]}
        input_ids = {f.id for f in files}
        assert result_ids == input_ids, \
            f"Files missing from output: {input_ids - result_ids}"
