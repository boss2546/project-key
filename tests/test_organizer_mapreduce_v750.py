"""Unit tests for v7.5.0 organizer map-reduce summary (Phase 4).

Mocks LLM calls (we test the orchestration, not Gemini's output quality).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_PASSWORD", "test1234")

from backend import organizer  # noqa: E402
from backend.config import LARGE_FILE_THRESHOLD  # noqa: E402


# ─── helpers ────────────────────────────────────────────────────────


def _fake_file(text: str, filename: str = "big.txt"):
    """Mutable fake File row — only fields organizer touches."""
    return SimpleNamespace(
        filename=filename,
        filetype="txt",
        extracted_text=text,
        chunk_count=0,
        is_truncated=False,
    )


# ─── routing tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_small_file_uses_simple_path(monkeypatch):
    """≤ LARGE_FILE_THRESHOLD chars → _generate_summary_simple, not map-reduce."""
    calls = {"simple": 0, "mapreduce": 0}

    async def fake_simple(file, ct, imp):
        calls["simple"] += 1
        return {"summary": "ok"}

    async def fake_mr(file, ct, imp):
        calls["mapreduce"] += 1
        return {"summary": "mr"}

    monkeypatch.setattr(organizer, "_generate_summary_simple", fake_simple)
    monkeypatch.setattr(organizer, "_generate_summary_mapreduce", fake_mr)

    f = _fake_file("a" * 1000)
    await organizer._generate_summary(f, "Cluster A", {"label": "high", "score": 80})

    assert calls["simple"] == 1
    assert calls["mapreduce"] == 0


@pytest.mark.asyncio
async def test_big_file_uses_mapreduce(monkeypatch):
    """> LARGE_FILE_THRESHOLD chars → _generate_summary_mapreduce."""
    calls = {"simple": 0, "mapreduce": 0}

    async def fake_simple(file, ct, imp):
        calls["simple"] += 1
        return {"summary": "ok"}

    async def fake_mr(file, ct, imp):
        calls["mapreduce"] += 1
        return {"summary": "mr"}

    monkeypatch.setattr(organizer, "_generate_summary_simple", fake_simple)
    monkeypatch.setattr(organizer, "_generate_summary_mapreduce", fake_mr)

    f = _fake_file("x" * (LARGE_FILE_THRESHOLD + 100))
    await organizer._generate_summary(f, "Cluster B", {"label": "medium", "score": 50})

    assert calls["simple"] == 0
    assert calls["mapreduce"] == 1


# ─── map-reduce orchestration ───────────────────────────────────────


@pytest.mark.asyncio
async def test_mapreduce_calls_llm_n_plus_one(monkeypatch):
    """N chunks → N map calls + 1 reduce call."""
    n_calls = {"summarize_chunk": 0, "merge": 0}

    async def fake_chunk(chunk, fn, n, total):
        n_calls["summarize_chunk"] += 1
        return {"summary": f"mini {n}", "key_topics": [f"t{n}"], "key_facts": [f"f{n}"]}

    async def fake_merge(minis, file, ct, imp):
        n_calls["merge"] += 1
        return {
            "summary": "merged",
            "key_topics": ["all"],
            "key_facts": ["all"],
            "why_important": "x",
            "suggested_usage": "y",
        }

    monkeypatch.setattr(organizer, "_summarize_chunk", fake_chunk)
    monkeypatch.setattr(organizer, "_merge_summaries", fake_merge)

    # Big text → ~5 chunks (CHUNK_SIZE=10K, total 50K)
    f = _fake_file("a " * 25000)  # 50K chars
    result = await organizer._generate_summary_mapreduce(f, "C", {"label": "low", "score": 10})

    assert n_calls["summarize_chunk"] >= 2, "expected multiple chunks"
    assert n_calls["merge"] == 1
    assert n_calls["summarize_chunk"] == f.chunk_count, "chunk_count must match map calls"
    assert result["summary"] == "merged"
    assert f.is_truncated is False


@pytest.mark.asyncio
async def test_mapreduce_partial_failure_sets_is_truncated(monkeypatch):
    """If any chunk fails, is_truncated=True but we still get a (partial) result."""
    chunk_n = {"i": 0}

    async def fake_chunk(chunk, fn, n, total):
        chunk_n["i"] += 1
        if chunk_n["i"] == 2:
            raise RuntimeError("simulated LLM error")
        return {"summary": f"ok{chunk_n['i']}", "key_topics": [], "key_facts": []}

    async def fake_merge(minis, file, ct, imp):
        return {"summary": "merged-with-gap", "key_topics": [], "key_facts": [],
                "why_important": "", "suggested_usage": ""}

    monkeypatch.setattr(organizer, "_summarize_chunk", fake_chunk)
    monkeypatch.setattr(organizer, "_merge_summaries", fake_merge)

    f = _fake_file("a " * 25000)
    result = await organizer._generate_summary_mapreduce(f, "C", {"label": "low", "score": 10})

    assert f.is_truncated is True, "partial failure must flag is_truncated"
    assert result["summary"] == "merged-with-gap"
    assert f.chunk_count > 0


@pytest.mark.asyncio
async def test_mapreduce_chunk_count_set_on_file(monkeypatch):
    """chunk_count attribute is set so caller can commit to DB."""
    async def fake_chunk(chunk, fn, n, total):
        return {"summary": "x", "key_topics": [], "key_facts": []}

    async def fake_merge(minis, file, ct, imp):
        return {"summary": "ok", "key_topics": [], "key_facts": [],
                "why_important": "", "suggested_usage": ""}

    monkeypatch.setattr(organizer, "_summarize_chunk", fake_chunk)
    monkeypatch.setattr(organizer, "_merge_summaries", fake_merge)

    f = _fake_file("a " * 25000)
    initial = f.chunk_count
    assert initial == 0
    await organizer._generate_summary_mapreduce(f, "C", {"label": "low", "score": 10})
    assert f.chunk_count > 0, "chunk_count must be updated"
