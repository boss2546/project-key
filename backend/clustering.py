"""Hybrid clustering for v11.0.0 — embeddings + UMAP + HDBSCAN + LLM-label.

หน้าที่:
- แทน `_cluster_files()` ใน organizer.py (LLM mega-call) ด้วย math-based clustering
- ดึง embeddings (cached) → reduce dimensions → density-based cluster → LLM ตั้งชื่อกลุ่ม
- Cost O(N) tokens · scale ได้ 1000+ ไฟล์ · deterministic (กดกี่ครั้งก็เหมือนกัน)

ใช้โดย:
- backend/organizer.py — เมื่อ USE_HYBRID_CLUSTERING=true

Reference architecture:
- BERTopic (Grootendorst 2022) — embed + UMAP + HDBSCAN + LLM topic naming
- RAPTOR (arXiv:2401.18059) — recursive clustering for RAG
- Plan: .agent-memory/plans/organize-refactor-v11.md (Step 1.1)

UMAP edge case (MSG-V11-UMAP-EDGE-CASE):
- UMAP มี constraint: n_components < n_samples - 1
- เดิม hard-code 30 → crash เมื่อ 5 ≤ N ≤ 31 ไฟล์
- Fix: dynamic n_components = min(UMAP_N_COMPONENTS, max(2, N - 2))
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Optional

import numpy as np

from .config import (
    HDBSCAN_MIN_CLUSTER_SIZE,
    UMAP_N_COMPONENTS,
)
from .embeddings import embed_files, is_available as embeddings_available
from .importance import heuristic_importance
from .llm import call_llm_json

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════
async def cluster_files_hybrid(
    files: list,
    min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
    progress_callback=None,
) -> dict:
    """Drop-in replacement สำหรับ organizer._cluster_files().

    Returns same shape:
        {
            "clusters": [
                {
                    "temp_id": "c1",
                    "title": "Cluster Name (Thai)",
                    "summary": "Brief description (Thai)",
                    "files": [
                        {
                            "file_id": "...",
                            "relevance": 0.95,
                            "importance_score": 85,
                            "importance_label": "high",
                            "is_primary": true,
                            "why_important": "..."
                        }
                    ]
                }
            ]
        }

    Args:
        files: list of File objects (extracted_text must be populated)
        min_cluster_size: HDBSCAN parameter (default 2 from config)
        progress_callback: optional async callable(phase, step_th, step_en, current, total)
                           เพื่อ update progress_tracker จาก organizer

    Pipeline:
        1. embed_files() → 768-d vectors (cached ใน DB)
        2. UMAP reduce → 30-d (or fewer ถ้า corpus เล็ก)
        3. HDBSCAN cluster → labels (-1 = noise)
        4. _compute_centrality() per file (distance to centroid)
        5. _llm_label_cluster() — parallel, semaphore=3
        6. Output ใน legacy shape
    """
    if not files:
        return {"clusters": []}

    # ─── Pre-check: ต้องมี API key สำหรับ embeddings ──────────────
    if not embeddings_available():
        logger.error(
            "cluster_files_hybrid: Gemini API not available — cannot proceed. "
            "Caller ควร fall back to legacy LLM cluster path."
        )
        raise RuntimeError(
            "Hybrid clustering requires GOOGLE_API_KEY for embeddings. "
            "Set USE_HYBRID_CLUSTERING=false to use legacy path."
        )

    # ─── Step 1: Embeddings ────────────────────────────────────────
    await _safe_progress(
        progress_callback,
        phase="embedding",
        step_th=f"วิเคราะห์ความคล้าย {len(files)} ไฟล์",
        step_en=f"Computing similarity ({len(files)} files)",
    )

    vectors_dict = await embed_files(files)
    # filter out files ที่ embed ไม่สำเร็จ (เช่น text ว่าง)
    valid_files = [f for f in files if f.id in vectors_dict]
    skipped = len(files) - len(valid_files)
    if skipped:
        logger.warning(
            f"cluster_files_hybrid: {skipped}/{len(files)} files ไม่มี embedding (text ว่าง/error). "
            "Skip จาก clustering — caller จัดการ assignment ทีหลังถ้าจำเป็น"
        )
    if not valid_files:
        return {"clusters": []}

    file_ids = [f.id for f in valid_files]
    vectors = np.array([vectors_dict[fid] for fid in file_ids])
    logger.info(
        f"Embeddings ready: {vectors.shape[0]} files × {vectors.shape[1]}-d"
    )

    # ─── Step 2: UMAP reduce (with dynamic n_components fix) ───────
    await _safe_progress(
        progress_callback,
        phase="cluster_math",
        step_th="ลดมิติเวกเตอร์",
        step_en="Reducing dimensions",
    )

    reduced = _reduce_dimensions(vectors, len(valid_files))

    # ─── Step 3: HDBSCAN clustering ────────────────────────────────
    labels = _run_hdbscan(reduced, min_cluster_size)
    cluster_groups = defaultdict(list)
    for f, label in zip(valid_files, labels):
        cluster_groups[int(label)].append(f)

    n_real_clusters = len([k for k in cluster_groups if k != -1])
    n_noise = len(cluster_groups.get(-1, []))
    logger.info(
        f"HDBSCAN: {len(valid_files)} files → {n_real_clusters} clusters + {n_noise} noise"
    )

    # ─── Step 4: Centrality (importance) ───────────────────────────
    centralities = _compute_centrality(reduced, labels)
    file_centrality: dict[str, float] = {
        fid: float(c) for fid, c in zip(file_ids, centralities)
    }

    # ─── Step 5: LLM label each cluster (parallel, semaphore=3) ────
    await _safe_progress(
        progress_callback,
        phase="cluster_label",
        step_th=f"ตั้งชื่อ {n_real_clusters} กลุ่ม",
        step_en=f"Labeling {n_real_clusters} clusters",
        total=n_real_clusters,
    )

    sem = asyncio.Semaphore(3)

    async def _label_one(label_id: int, group_files: list):
        async with sem:
            return label_id, await _llm_label_cluster(group_files, file_centrality)

    label_tasks = [
        _label_one(lbl, grp)
        for lbl, grp in cluster_groups.items()
        if lbl != -1  # skip noise — handle separately ด้านล่าง
    ]
    label_results = await asyncio.gather(*label_tasks) if label_tasks else []

    # ─── Step 6: Assemble output in legacy shape ───────────────────
    cluster_output = []

    # Real clusters (labeled by LLM)
    for label_id, cluster_data in label_results:
        cluster_output.append(cluster_data)

    # Noise files — each as standalone cluster (matches legacy "1-file cluster" behavior)
    for f in cluster_groups.get(-1, []):
        imp = heuristic_importance(f, centrality=0.5)
        cluster_output.append({
            "temp_id": f"c_noise_{f.id[:8]}",
            "title": f.filename,
            "summary": "Standalone file (ไม่เข้าพวกกับกลุ่มอื่น)",
            "files": [{
                "file_id": f.id,
                "relevance": 1.0,
                "importance_score": imp["score"],
                "importance_label": imp["label"],
                "is_primary": True,
                "why_important": "Standalone document",
            }],
        })

    return {"clusters": cluster_output}


# ═══════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════
def _reduce_dimensions(vectors: np.ndarray, n_samples: int) -> np.ndarray:
    """UMAP reduce dimensionality (with dynamic n_components fix).

    UMAP constraint: n_components < n_samples - 1.
    เดิม hard-code 30 → crash เมื่อ 5 ≤ N ≤ 31.
    Fix (MSG-V11-UMAP-EDGE-CASE Option A):
      N < 5:                       skip UMAP (raw vectors)
      5 ≤ N ≤ UMAP_N_COMPONENTS+1: scale n_components = max(2, N-2)
      N > UMAP_N_COMPONENTS+1:     ใช้ UMAP_N_COMPONENTS เต็ม
    """
    if n_samples < 5:
        logger.info(
            f"UMAP skipped (N={n_samples} < 5) — clustering on raw {vectors.shape[1]}-d embeddings"
        )
        return vectors

    # Dynamic n_components — กัน scipy eigsh edge case (k >= N)
    n_comp = min(UMAP_N_COMPONENTS, max(2, n_samples - 2))

    import umap
    reducer = umap.UMAP(
        n_components=n_comp,
        metric="cosine",
        random_state=42,  # determinism
        n_neighbors=min(15, n_samples - 1),
    )
    reduced = reducer.fit_transform(vectors)
    logger.info(
        f"UMAP: {n_samples} files × {vectors.shape[1]}-d → "
        f"{n_comp}-d (target={UMAP_N_COMPONENTS})"
    )
    return reduced


def _run_hdbscan(reduced: np.ndarray, min_cluster_size: int) -> np.ndarray:
    """HDBSCAN density-based clustering.

    Returns: array of cluster labels (int). -1 = noise (outlier).
    """
    import hdbscan
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=max(2, min_cluster_size),  # HDBSCAN min = 2
        metric="euclidean",
        cluster_selection_method="eom",
    )
    return clusterer.fit_predict(reduced)


def _compute_centrality(reduced: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Compute per-file centrality (1 - normalized distance to cluster centroid).

    Returns: array of float in [0, 1]. 1 = at centroid (most central), 0 = at edge.
    Used เป็น "importance" proxy + sample selection ใน _llm_label_cluster.

    Noise points (label=-1) → centrality = 0.5 (neutral, not zero).
    """
    centralities = np.full(len(labels), 0.5, dtype=np.float32)
    for label in set(labels):
        if label == -1:
            continue  # noise stays at neutral 0.5
        mask = labels == label
        members = reduced[mask]
        if len(members) == 1:
            centralities[mask] = 1.0  # only file in cluster = max central
            continue
        centroid = members.mean(axis=0)
        distances = np.linalg.norm(members - centroid, axis=1)
        max_dist = distances.max() or 1.0
        centralities[mask] = 1.0 - (distances / max_dist)
    return centralities


# ═══════════════════════════════════════════════════════════════
# LLM-label one cluster (small focused call, parallel-safe)
# ═══════════════════════════════════════════════════════════════
async def _llm_label_cluster(
    group_files: list,
    centralities: dict[str, float],
) -> dict:
    """Single LLM call เพื่อ label + score cluster.

    Strategy:
    - ส่งแค่ top-3 most-central files เป็น samples (preview 1500 chars/file)
    - Token budget: ~10K input, ~2K output → fits Gemini Flash 32K easily
    - Compatible กับ output shape ของ _cluster_files() เดิม

    Returns:
        {
            "temp_id": "c_xxx",
            "title": "Thai cluster name",
            "summary": "Thai description",
            "files": [{"file_id", "relevance", "importance_score", ...}]
        }
    """
    # Pick top-3 representatives by centrality (deterministic — same ranks each run)
    sorted_files = sorted(
        group_files,
        key=lambda f: -centralities.get(f.id, 0.0),
    )
    samples = sorted_files[:3]

    file_descriptions = []
    for f in samples:
        preview = (f.extracted_text or "")[:1500]
        file_descriptions.append(
            f"FILE: {f.filename}\n"
            f"PREVIEW:\n{preview}\n---"
        )

    system_prompt = """You are a document organization AI. Given 3 sample files from a cluster of related documents (selected as the most central — closest to cluster center), name the cluster and explain why these files belong together.

Respond with ONLY valid JSON:
{
  "title": "Cluster name (in Thai, 3-8 words)",
  "summary": "Brief description of what unifies these files (in Thai, 1-2 sentences)"
}

Rules:
- Title: descriptive, in Thai (e.g. "ประกันสุขภาพ MTL", "คู่มือฝ่ายขาย Tipco")
- Summary: 1-2 short sentences in Thai
- ถ้าไฟล์ดูไม่เข้าพวก → ตั้งชื่อแบบกว้างๆ ที่ครอบคลุม"""

    user_prompt = (
        f"Cluster contains {len(group_files)} file(s) total. "
        f"Top 3 most-central samples:\n\n"
        + "\n\n".join(file_descriptions)
    )

    try:
        label_data = await call_llm_json(system_prompt, user_prompt)
    except Exception as e:
        logger.error(f"_llm_label_cluster: LLM call failed for cluster of {len(group_files)} files: {e}")
        # Fallback: ใช้ชื่อไฟล์ representative แทน LLM label
        label_data = {
            "title": f"กลุ่มไฟล์ ({samples[0].filename})",
            "summary": f"กลุ่มของ {len(group_files)} ไฟล์ที่คล้ายกันทาง semantic",
        }

    title = label_data.get("title", "Untitled Group")
    summary = label_data.get("summary", "")

    # Build files array — every member ใน cluster ได้ importance + relevance
    files_array = []
    primary_id = sorted_files[0].id  # most central = primary
    for f in group_files:
        centrality = centralities.get(f.id, 0.5)
        imp = heuristic_importance(f, centrality=centrality)
        files_array.append({
            "file_id": f.id,
            "relevance": float(centrality),  # centrality = relevance proxy
            "importance_score": imp["score"],
            "importance_label": imp["label"],
            "is_primary": (f.id == primary_id),
            "why_important": f"Member of cluster '{title}'",
        })

    return {
        "temp_id": f"c_{title[:16].replace(' ', '_')}",
        "title": title,
        "summary": summary,
        "files": files_array,
    }


# ═══════════════════════════════════════════════════════════════
# Progress callback helper
# ═══════════════════════════════════════════════════════════════
async def _safe_progress(
    callback: Optional[callable],
    phase: str,
    step_th: str,
    step_en: str,
    current: int = 0,
    total: int = 0,
) -> None:
    """เรียก progress_callback แบบปลอดภัย (silently swallow error)."""
    if callback is None:
        return
    try:
        # callback signature ตาม progress_tracker.report
        await callback(phase=phase, step_th=step_th, step_en=step_en,
                       current=current, total=total)
    except Exception as e:
        logger.debug(f"progress_callback raised (non-fatal): {e}")
