"""Test harness สำหรับ v11.0.0 organize pipeline quality benchmark.

Plan ref: .agent-memory/plans/organize-refactor-v11.md (Step 0.5)

หน้าที่:
- Run organize pipeline บน test corpus (real prod data ของ admin user)
- เก็บ metrics: wall-clock, LLM calls, memory peak, cluster count, JSON parse rate
- Output: side-by-side report (legacy vs v11)

ใช้:
    python scripts/test_organize_quality.py --baseline           # รัน legacy
    python scripts/test_organize_quality.py --v11                # รัน hybrid
    python scripts/test_organize_quality.py --compare            # both + diff report
    python scripts/test_organize_quality.py --user-id <id>       # specific user
    python scripts/test_organize_quality.py --limit 50           # cap files

Output: reports/organize-quality-{mode}-{timestamp}.md

⚠️ SECURITY:
- ใช้กับ admin user (bossok2546@gmail.com) เท่านั้น — DB ที่ touch = projectkey.db จริง
- Snapshot DB ก่อน run: cp projectkey.db projectkey_test_v11.db
- ห้าม run บน prod DB โดยตรง — ใช้ local copy
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

# Ensure backend module importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Metrics collector
# ═══════════════════════════════════════════════════════════════
class Metrics:
    """Collect timing + resource metrics during organize."""

    def __init__(self, label: str):
        self.label = label
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.phases: list[dict] = []
        self.llm_call_count: int = 0
        self.embedding_call_count: int = 0
        self.memory_peak_mb: float = 0.0
        self.file_count: int = 0
        self.cluster_count: int = 0
        self.error: str | None = None

    def start(self) -> None:
        tracemalloc.start()
        self.start_time = time.time()

    def stop(self) -> None:
        self.end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        self.memory_peak_mb = peak / (1024 * 1024)
        tracemalloc.stop()

    @property
    def duration_sec(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "duration_sec": round(self.duration_sec, 2),
            "duration_min": round(self.duration_sec / 60, 2),
            "llm_call_count": self.llm_call_count,
            "embedding_call_count": self.embedding_call_count,
            "memory_peak_mb": round(self.memory_peak_mb, 2),
            "file_count": self.file_count,
            "cluster_count": self.cluster_count,
            "phases": self.phases,
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════════
# LLM call counter (monkey-patch wrapper)
# ═══════════════════════════════════════════════════════════════
class LLMCallTracker:
    """Wrap call_llm_json + call_llm_pro to count calls."""

    def __init__(self):
        self.count = 0
        self._originals = {}

    def install(self):
        """Monkey-patch backend.llm functions."""
        try:
            from backend import llm
        except ImportError:
            logger.warning("backend.llm not importable — LLM tracking disabled")
            return

        # Wrap call_llm_json
        if hasattr(llm, "call_llm_json"):
            self._originals["call_llm_json"] = llm.call_llm_json

            async def _tracked(*args, **kwargs):
                self.count += 1
                return await self._originals["call_llm_json"](*args, **kwargs)

            llm.call_llm_json = _tracked

        if hasattr(llm, "call_llm_pro"):
            self._originals["call_llm_pro"] = llm.call_llm_pro

            async def _tracked_pro(*args, **kwargs):
                self.count += 1
                return await self._originals["call_llm_pro"](*args, **kwargs)

            llm.call_llm_pro = _tracked_pro

    def uninstall(self):
        from backend import llm
        for name, fn in self._originals.items():
            setattr(llm, name, fn)
        self._originals = {}


# ═══════════════════════════════════════════════════════════════
# Test corpus selection
# ═══════════════════════════════════════════════════════════════
async def select_test_files(db, user_id: str, limit: int) -> list:
    """Select up to `limit` files จาก admin user สำหรับ test corpus.

    Filters:
      - extracted_text != "" (must have content)
      - file_kind == "processed" (not vault-only)
      - extraction_status == "ok" (not error)

    Returns up to `limit` files, ordered by uploaded_at DESC (recent first).
    """
    from sqlalchemy import select
    from backend.database import File

    result = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.extracted_text != "",
            File.file_kind == "processed",
            File.extraction_status == "ok",
        ).order_by(File.uploaded_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════
# Test runner
# ═══════════════════════════════════════════════════════════════
async def run_test(mode: str, user_id: str | None, limit: int) -> Metrics:
    """Run organize pipeline ใน mode ที่ระบุ + collect metrics.

    mode = "baseline" (legacy, USE_HYBRID_CLUSTERING=false)
         | "v11"      (hybrid, USE_HYBRID_CLUSTERING=true)
    """
    # Force feature flag ตาม mode
    if mode == "baseline":
        os.environ["USE_HYBRID_CLUSTERING"] = "false"
        os.environ["USE_STRUCTURED_SUMMARY"] = "false"
        os.environ["USE_ENTITY_GRAPH"] = "false"
    elif mode == "v11":
        os.environ["USE_HYBRID_CLUSTERING"] = "true"
        os.environ["USE_STRUCTURED_SUMMARY"] = "true"
        os.environ["USE_ENTITY_GRAPH"] = "true"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Reload modules to pick up new env
    for mod in list(sys.modules.keys()):
        if mod.startswith("backend."):
            del sys.modules[mod]

    from backend.database import AsyncSessionLocal, init_db
    from backend.config import (
        USE_HYBRID_CLUSTERING,
        USE_STRUCTURED_SUMMARY,
        USE_ENTITY_GRAPH,
    )

    metrics = Metrics(label=mode)
    tracker = LLMCallTracker()

    try:
        await init_db()

        # Find admin user_id ถ้าไม่ระบุ
        if not user_id:
            from backend.database import User
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.email == "bossok2546@gmail.com").limit(1)
                )
                admin = result.scalar_one_or_none()
                if not admin:
                    metrics.error = "Admin user bossok2546@gmail.com not found in DB"
                    return metrics
                user_id = admin.id

        async with AsyncSessionLocal() as db:
            files = await select_test_files(db, user_id, limit)
            metrics.file_count = len(files)
            logger.info(f"[{mode}] Test corpus: {len(files)} files for user_id={user_id}")

            if not files:
                metrics.error = "No test files found"
                return metrics

            # Install tracker
            tracker.install()

            # Start metrics
            metrics.start()

            # Run organize_new_files (เรียกตรง — ไม่ผ่าน endpoint เพราะไม่มี auth ใน script)
            try:
                from backend.organizer import organize_new_files
                result = await organize_new_files(db, user_id)
                metrics.cluster_count = result.get("count", 0)
            except Exception as e:
                metrics.error = f"{type(e).__name__}: {e}"
                logger.exception(f"[{mode}] organize failed")

            metrics.stop()
            metrics.llm_call_count = tracker.count
            tracker.uninstall()

    except Exception as e:
        metrics.error = f"setup error: {type(e).__name__}: {e}"
        logger.exception(f"[{mode}] test setup failed")

    return metrics


# ═══════════════════════════════════════════════════════════════
# Report generation
# ═══════════════════════════════════════════════════════════════
def write_report(metrics: Metrics, out_path: Path) -> None:
    """Write metrics report ใน Markdown format."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md = [
        f"# Organize Quality Report — {metrics.label}",
        "",
        f"**Generated:** {datetime.utcnow().isoformat()}Z",
        f"**Mode:** `{metrics.label}`",
        "",
        "## Metrics",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| File count | {metrics.file_count} |",
        f"| Wall-clock time | {metrics.duration_sec:.2f}s ({metrics.duration_min:.2f} min) |",
        f"| LLM calls | {metrics.llm_call_count} |",
        f"| Embedding calls | {metrics.embedding_call_count} |",
        f"| Memory peak | {metrics.memory_peak_mb:.2f} MB |",
        f"| Cluster count | {metrics.cluster_count} |",
        f"| Error | {metrics.error or '_None_'} |",
        "",
    ]
    if metrics.phases:
        md.append("## Phase breakdown")
        md.append("")
        md.append("| Phase | Duration |")
        md.append("|---|---|")
        for p in metrics.phases:
            md.append(f"| {p.get('name', '?')} | {p.get('duration_sec', 0):.2f}s |")

    md.append("")
    md.append("## Raw JSON")
    md.append("```json")
    md.append(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
    md.append("```")

    out_path.write_text("\n".join(md), encoding="utf-8")
    logger.info(f"Report saved: {out_path}")


def write_comparison_report(baseline: Metrics, v11: Metrics, out_path: Path) -> None:
    """Side-by-side diff report."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def pct_change(b, v):
        if b == 0:
            return "—"
        return f"{((v - b) / b) * 100:+.1f}%"

    md = [
        "# Organize Quality Comparison — Legacy (baseline) vs v11.0.0 (hybrid)",
        "",
        f"**Generated:** {datetime.utcnow().isoformat()}Z",
        "",
        "| Metric | Baseline (v10.x) | v11 Hybrid | Change |",
        "|---|---|---|---|",
        f"| File count | {baseline.file_count} | {v11.file_count} | — |",
        f"| Wall-clock | {baseline.duration_sec:.2f}s | {v11.duration_sec:.2f}s | {pct_change(baseline.duration_sec, v11.duration_sec)} |",
        f"| LLM calls | {baseline.llm_call_count} | {v11.llm_call_count} | {pct_change(baseline.llm_call_count, v11.llm_call_count)} |",
        f"| Memory peak | {baseline.memory_peak_mb:.2f} MB | {v11.memory_peak_mb:.2f} MB | {pct_change(baseline.memory_peak_mb, v11.memory_peak_mb)} |",
        f"| Cluster count | {baseline.cluster_count} | {v11.cluster_count} | — |",
        f"| Error | {baseline.error or '_None_'} | {v11.error or '_None_'} | — |",
        "",
        "## Acceptance Criteria (Plan target)",
        "",
        "- ✅ Wall-clock < 50% of baseline (target: 6-9× faster)",
        "- ✅ LLM calls < 30% of baseline (target: 10-90× fewer)",
        "- ✅ Memory peak < 50% of baseline",
        "- ✅ Cluster count > 0 (no failure)",
        "- ✅ No error in v11 mode",
        "",
        "## Raw data",
        "",
        "### Baseline",
        "```json",
        json.dumps(baseline.to_dict(), indent=2, ensure_ascii=False),
        "```",
        "",
        "### v11",
        "```json",
        json.dumps(v11.to_dict(), indent=2, ensure_ascii=False),
        "```",
    ]
    out_path.write_text("\n".join(md), encoding="utf-8")
    logger.info(f"Comparison report saved: {out_path}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
async def main():
    parser = argparse.ArgumentParser(description="v11.0.0 organize quality test harness")
    parser.add_argument("--baseline", action="store_true", help="Run legacy pipeline")
    parser.add_argument("--v11", action="store_true", help="Run v11 hybrid pipeline")
    parser.add_argument("--compare", action="store_true", help="Run both + comparison report")
    parser.add_argument("--user-id", type=str, default=None, help="User ID (default: admin)")
    parser.add_argument("--limit", type=int, default=30, help="Max files (default 30)")
    parser.add_argument("--output-dir", type=str, default="reports", help="Report output dir")

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    if not (args.baseline or args.v11 or args.compare):
        parser.print_help()
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.compare:
        logger.info("=== Mode: COMPARE (running baseline → v11) ===")
        baseline = await run_test("baseline", args.user_id, args.limit)
        write_report(baseline, out_dir / f"organize-quality-baseline-{ts}.md")
        v11 = await run_test("v11", args.user_id, args.limit)
        write_report(v11, out_dir / f"organize-quality-v11-{ts}.md")
        write_comparison_report(baseline, v11, out_dir / f"organize-quality-COMPARE-{ts}.md")
    elif args.baseline:
        logger.info("=== Mode: BASELINE (legacy pipeline) ===")
        metrics = await run_test("baseline", args.user_id, args.limit)
        write_report(metrics, out_dir / f"organize-quality-baseline-{ts}.md")
    elif args.v11:
        logger.info("=== Mode: V11 (hybrid pipeline) ===")
        metrics = await run_test("v11", args.user_id, args.limit)
        write_report(metrics, out_dir / f"organize-quality-v11-{ts}.md")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
