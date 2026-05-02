"""Organization engine — clustering, importance scoring, summary generation via LLM."""
import json
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import File, Cluster, FileClusterMap, FileInsight, FileSummary, gen_id
from .llm import call_llm_json
from .markdown_store import write_summary_md
from . import vector_search

logger = logging.getLogger(__name__)


async def organize_files(db: AsyncSession, user_id: str):
    """Run the full organization pipeline: cluster → score → summarize."""

    # 1. Get all files with extracted text (eagerly load relationships for async)
    result = await db.execute(
        select(File).where(File.user_id == user_id, File.extracted_text != "")
        .options(selectinload(File.insight), selectinload(File.summary), selectinload(File.cluster_maps))
    )
    files = result.scalars().all()

    if not files:
        logger.warning("No files to organize")
        return

    # Update all to processing
    for f in files:
        f.processing_status = "processing"
    await db.commit()

    try:
        # 2. Cluster files
        clusters_data = await _cluster_files(files)

        # 3. Clear old clusters for this user
        old_clusters = await db.execute(select(Cluster).where(Cluster.user_id == user_id))
        for old_c in old_clusters.scalars().all():
            await db.delete(old_c)
        await db.commit()

        # Clear old insights and summaries using SQL delete (avoid lazy loading)
        file_ids = [f.id for f in files]
        await db.execute(delete(FileInsight).where(FileInsight.file_id.in_(file_ids)))
        await db.execute(delete(FileSummary).where(FileSummary.file_id.in_(file_ids)))
        await db.execute(delete(FileClusterMap).where(FileClusterMap.file_id.in_(file_ids)))
        await db.commit()

        # 4. Create new clusters and mappings
        cluster_map = {}  # temp_id -> real Cluster
        for c_data in clusters_data.get("clusters", []):
            cluster = Cluster(
                id=gen_id(),
                user_id=user_id,
                title=c_data.get("title", "Untitled Group"),
                summary=c_data.get("summary", "")
            )
            db.add(cluster)
            cluster_map[c_data.get("temp_id", cluster.id)] = cluster

            # Map files to cluster
            for file_ref in c_data.get("files", []):
                file_id = file_ref.get("file_id", "")
                matching_file = next((f for f in files if f.id == file_id), None)
                if matching_file:
                    fcm = FileClusterMap(
                        file_id=matching_file.id,
                        cluster_id=cluster.id,
                        relevance_score=file_ref.get("relevance", 1.0)
                    )
                    db.add(fcm)

        await db.commit()

        # 5. Create/Update insights (importance scoring)
        for f in files:
            importance = _find_importance(clusters_data, f.id)
            existing_insight = (await db.execute(
                select(FileInsight).where(FileInsight.file_id == f.id)
            )).scalar_one_or_none()

            if existing_insight:
                existing_insight.importance_score = importance.get("score", 50)
                existing_insight.importance_label = importance.get("label", "medium")
                existing_insight.is_primary_candidate = importance.get("is_primary", False)
                existing_insight.why_important = importance.get("why", "")
            else:
                insight = FileInsight(
                    file_id=f.id,
                    importance_score=importance.get("score", 50),
                    importance_label=importance.get("label", "medium"),
                    is_primary_candidate=importance.get("is_primary", False),
                    why_important=importance.get("why", "")
                )
                db.add(insight)

        # Update status to organized
        for f in files:
            f.processing_status = "organized"
        await db.commit()

        # 6. Generate summaries for each file
        for f in files:
            try:
                # Find which cluster this file belongs to
                cluster_title = "Unclustered"
                for c_data in clusters_data.get("clusters", []):
                    for file_ref in c_data.get("files", []):
                        if file_ref.get("file_id") == f.id:
                            cluster_title = c_data.get("title", "Unclustered")
                            break

                importance_data = _find_importance(clusters_data, f.id)
                summary_data = await _generate_summary(f, cluster_title, importance_data)

                # Upsert: update existing summary or create new
                existing_summary = (await db.execute(
                    select(FileSummary).where(FileSummary.file_id == f.id)
                )).scalar_one_or_none()

                if existing_summary:
                    existing_summary.summary_text = summary_data.get("summary", "")
                    existing_summary.key_topics = json.dumps(summary_data.get("key_topics", []), ensure_ascii=False)
                    existing_summary.key_facts = json.dumps(summary_data.get("key_facts", []), ensure_ascii=False)
                    existing_summary.why_important = summary_data.get("why_important", "")
                    existing_summary.suggested_usage = summary_data.get("suggested_usage", "")
                    file_summary = existing_summary
                else:
                    file_summary = FileSummary(
                        file_id=f.id,
                        summary_text=summary_data.get("summary", ""),
                        key_topics=json.dumps(summary_data.get("key_topics", []), ensure_ascii=False),
                        key_facts=json.dumps(summary_data.get("key_facts", []), ensure_ascii=False),
                        why_important=summary_data.get("why_important", ""),
                        suggested_usage=summary_data.get("suggested_usage", "")
                    )
                    db.add(file_summary)

                # memsearch: Write .md summary file to disk
                md_path = write_summary_md(
                    file_id=f.id,
                    filename=f.filename,
                    filetype=f.filetype,
                    cluster_title=cluster_title,
                    importance_score=importance_data.get("score", 50),
                    importance_label=importance_data.get("label", "medium"),
                    is_primary=importance_data.get("is_primary", False),
                    summary_text=summary_data.get("summary", ""),
                    key_topics=summary_data.get("key_topics", []),
                    key_facts=summary_data.get("key_facts", []),
                    why_important=summary_data.get("why_important", ""),
                    suggested_usage=summary_data.get("suggested_usage", ""),
                    uploaded_at=f.uploaded_at.isoformat() + "Z" if f.uploaded_at else ""
                )
                file_summary.md_path = md_path

                # RAGFlow: Index file text into vector store
                vector_search.index_file(
                    file_id=f.id,
                    filename=f.filename,
                    text=f.extracted_text or "",
                    cluster_title=cluster_title,
                    user_id=user_id,  # v5.1 — per-user index
                )

                # v7.0 BYOS: push summary to Drive (best-effort, no-op for managed)
                try:
                    from .storage_router import push_summary_to_drive_if_byos
                    await push_summary_to_drive_if_byos(
                        user_id, db, f.id, summary_data.get("summary", "")
                    )
                except Exception as drive_e:
                    logger.debug("BYOS summary push skipped: %s", drive_e)

                f.processing_status = "ready"
            except Exception as e:
                logger.error(f"Summary generation failed for {f.filename}: {e}")
                f.processing_status = "error"

        await db.commit()
        logger.info(f"Organization complete for user {user_id}: {len(files)} files, {len(cluster_map)} clusters")

    except Exception as e:
        logger.error(f"Organization failed: {e}")
        for f in files:
            f.processing_status = "error"
        await db.commit()
        raise


async def _cluster_files(files: list) -> dict:
    """Use LLM to cluster files and score importance."""

    file_descriptions = []
    for f in files:
        text_preview = f.extracted_text[:3000] if f.extracted_text else "[No text]"
        file_descriptions.append(
            f"FILE_ID: {f.id}\n"
            f"FILENAME: {f.filename}\n"
            f"FILETYPE: {f.filetype}\n"
            f"TEXT_PREVIEW:\n{text_preview}\n"
            f"---"
        )

    files_block = "\n\n".join(file_descriptions)

    system_prompt = """You are a document organization AI. Your job is to analyze files, group them into logical clusters, and assess their importance.

You must respond with ONLY valid JSON, no other text. The JSON must follow this exact structure:

{
  "clusters": [
    {
      "temp_id": "c1",
      "title": "Cluster Name",
      "summary": "Brief description of what this cluster is about",
      "files": [
        {
          "file_id": "the actual FILE_ID",
          "relevance": 0.95,
          "importance_score": 85,
          "importance_label": "high",
          "is_primary": true,
          "why_important": "Explanation of why this file matters"
        }
      ]
    }
  ]
}

Rules:
- importance_score: 0-100
- importance_label: "high" (70-100), "medium" (40-69), "low" (0-39)
- is_primary: true for the most important/complete file in each cluster, only ONE per cluster
- Every file must appear in exactly one cluster
- Group files that share topics, themes, or are clearly related
- A cluster can have just 1 file if it doesn't relate to others
- Write cluster titles and summaries in THAI language always, even if the files are in English
- why_important must also be in Thai"""

    user_prompt = f"Analyze and organize these {len(files)} files:\n\n{files_block}"

    return await call_llm_json(system_prompt, user_prompt)


async def _generate_summary(file: File, cluster_title: str, importance: dict) -> dict:
    """Generate a rich markdown summary for a single file.

    v7.5.0: routes to map-reduce for big files (extracted_text > LARGE_FILE_THRESHOLD).
    Sets file.chunk_count + file.is_truncated for caller to commit.
    """
    from .config import LARGE_FILE_THRESHOLD
    text = file.extracted_text or ""
    if len(text) > LARGE_FILE_THRESHOLD:
        return await _generate_summary_mapreduce(file, cluster_title, importance)
    return await _generate_summary_simple(file, cluster_title, importance)


async def _generate_summary_simple(file: File, cluster_title: str, importance: dict) -> dict:
    """Original single-LLM-call path for files ≤ LARGE_FILE_THRESHOLD chars."""
    text_preview = file.extracted_text[:6000] if file.extracted_text else "[No text]"

    system_prompt = """You are a document summarization AI. Create a structured summary of the given file.

You must respond with ONLY valid JSON, no other text:

{
  "summary": "A comprehensive summary of this document's content (2-4 paragraphs)",
  "key_topics": ["Topic 1", "Topic 2", "Topic 3"],
  "key_facts": ["Specific fact 1", "Specific fact 2", "Specific fact 3"],
  "why_important": "Explanation of why this file matters and when to use it",
  "suggested_usage": "Recommend how AI should use this file: as summary, excerpt, or raw text. And when."
}

Rules:
- Write ALL output in THAI language, even if the document is in English
- key_topics: 3-6 items (in Thai)
- key_facts: 3-8 specific, factual items — numbers, dates, names, decisions (in Thai)
- Be specific and useful, not generic"""

    user_prompt = (
        f"FILENAME: {file.filename}\n"
        f"FILETYPE: {file.filetype}\n"
        f"CLUSTER: {cluster_title}\n"
        f"IMPORTANCE: {importance.get('label', 'medium')} ({importance.get('score', 50)}/100)\n\n"
        f"FULL TEXT:\n{text_preview}"
    )

    return await call_llm_json(system_prompt, user_prompt)


async def _generate_summary_mapreduce(file: File, cluster_title: str, importance: dict) -> dict:
    """Big-file summary via map-reduce: chunk → mini-summary per chunk → merge.

    Why map-reduce vs single-call truncation:
      - Old behavior truncated at 6K chars → 96% loss for a 150K-char document
      - LLM context bloat (Gemini Flash 32K) means single-call can't fit big files
      - Per-chunk → final merge captures content from beginning, middle, AND end

    Cost model (Q-F decision):
      - 10 chunks = 10 map calls + 1 reduce call = 11 LLM calls
      - Logged as 1 AI summary quota (not 10) — fairness, user uploads 1 file = 1 count
      - Reduce step receives 10 mini-summaries (~200 chars each = ~2K total — fits easily)

    Sets:
      file.chunk_count = N (so file card UI shows "📚 N ส่วน")
      file.is_truncated = True if any chunk failed (partial result)
    """
    from .text_chunker import chunk_text
    chunks = chunk_text(file.extracted_text or "")
    file.chunk_count = len(chunks)
    file.is_truncated = False  # may flip to True if a map call fails

    logger.info(
        f"Big file map-reduce: {file.filename} ({len(file.extracted_text)} chars → {len(chunks)} chunks)"
    )

    # ─── Map: per-chunk mini-summary ──────────────────────────────────
    mini_summaries: list[dict] = []
    for i, chunk in enumerate(chunks):
        try:
            mini = await _summarize_chunk(chunk, file.filename, i + 1, len(chunks))
            mini_summaries.append(mini)
        except Exception as e:
            logger.error(f"Chunk {i+1}/{len(chunks)} of {file.filename} failed: {e}")
            file.is_truncated = True
            mini_summaries.append({
                "summary": f"[ส่วนที่ {i+1} อ่านไม่ได้: {type(e).__name__}]",
                "key_topics": [],
                "key_facts": [],
            })

    # ─── Reduce: merge mini-summaries into final ──────────────────────
    return await _merge_summaries(
        mini_summaries, file, cluster_title, importance,
    )


async def _summarize_chunk(chunk: str, filename: str, chunk_n: int, total: int) -> dict:
    """Map step: summarize one chunk into structured mini-summary."""
    system_prompt = """You are a document summarization AI processing one chunk of a larger file.

Respond with ONLY valid JSON:
{
  "summary": "Concise 1-2 sentence summary of THIS chunk only (Thai)",
  "key_topics": ["topic1", "topic2"],
  "key_facts": ["fact1", "fact2"]
}

Rules:
- Write in THAI
- Stay focused on what's in THIS chunk (don't speculate about the whole document)
- Keep summary brief (will be merged with other chunks later)
- key_topics: 1-4 items per chunk
- key_facts: 1-5 specific items per chunk"""

    user_prompt = (
        f"FILENAME: {filename}\n"
        f"CHUNK: {chunk_n} of {total}\n\n"
        f"CONTENT:\n{chunk}"
    )
    return await call_llm_json(system_prompt, user_prompt)


async def _merge_summaries(mini_summaries: list[dict], file: File, cluster_title: str, importance: dict) -> dict:
    """Reduce step: merge per-chunk summaries into one comprehensive summary.

    Inputs are small (each ~200 chars × 10 chunks = ~2K) so single LLM call works fine.
    Output schema matches _generate_summary_simple for downstream compatibility.
    """
    # Format mini-summaries as a structured input for the reducer
    chunks_text = "\n\n".join(
        f"=== ส่วนที่ {i+1} ===\nสรุป: {m.get('summary', '')}\n"
        f"หัวข้อ: {', '.join(m.get('key_topics', []))}\n"
        f"ข้อเท็จจริง: {'; '.join(m.get('key_facts', []))}"
        for i, m in enumerate(mini_summaries)
    )

    system_prompt = """You are a document summarization AI merging chunk summaries from a large document.

Respond with ONLY valid JSON:
{
  "summary": "Comprehensive 3-5 paragraph summary covering content from ALL chunks (Thai)",
  "key_topics": ["Topic 1", "Topic 2", "Topic 3"],
  "key_facts": ["Specific fact 1", "Specific fact 2", "Specific fact 3"],
  "why_important": "Why this file matters and when to use it (Thai)",
  "suggested_usage": "How AI should use this file (Thai)"
}

Rules:
- Write in THAI
- summary should reflect the WHOLE document — pull highlights from beginning, middle, AND end
- key_topics: 4-8 items, deduplicated across chunks
- key_facts: 5-10 specific items — prefer concrete (numbers, dates, names) over vague
- If a chunk says "[ส่วนที่ N อ่านไม่ได้]" → mention that gap in summary"""

    user_prompt = (
        f"FILENAME: {file.filename}\n"
        f"FILETYPE: {file.filetype}\n"
        f"CLUSTER: {cluster_title}\n"
        f"IMPORTANCE: {importance.get('label', 'medium')} ({importance.get('score', 50)}/100)\n"
        f"TOTAL CHUNKS: {len(mini_summaries)}\n\n"
        f"CHUNK SUMMARIES TO MERGE:\n{chunks_text}"
    )
    return await call_llm_json(system_prompt, user_prompt)


def _find_importance(clusters_data: dict, file_id: str) -> dict:
    """Find importance data for a file from the clustering result."""
    for c in clusters_data.get("clusters", []):
        for f in c.get("files", []):
            if f.get("file_id") == file_id:
                return {
                    "score": f.get("importance_score", 50),
                    "label": f.get("importance_label", "medium"),
                    "is_primary": f.get("is_primary", False),
                    "why": f.get("why_important", "")
                }
    return {"score": 50, "label": "medium", "is_primary": False, "why": ""}


async def organize_new_files(db: AsyncSession, user_id: str) -> dict:
    """Organize only NEW files that don't have summaries yet. Much faster than full organize."""

    # Find files without summaries
    from sqlalchemy import not_, exists
    result = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.extracted_text != "",
            ~exists(select(FileSummary.file_id).where(FileSummary.file_id == File.id))
        ).options(selectinload(File.insight), selectinload(File.summary), selectinload(File.cluster_maps))
    )
    new_files = result.scalars().all()

    if not new_files:
        logger.info(f"No new unprocessed files for user {user_id}")
        return {"skipped": True, "count": 0}

    logger.info(f"Processing {len(new_files)} new files for user {user_id}")

    # Mark as processing
    for f in new_files:
        f.processing_status = "processing"
    await db.commit()

    try:
        # 1. Cluster just the new files
        clusters_data = await _cluster_files(new_files)

        # 2. Create new clusters for the new files (don't delete existing clusters)
        for c_data in clusters_data.get("clusters", []):
            cluster = Cluster(
                id=gen_id(),
                user_id=user_id,
                title=c_data.get("title", "Untitled Group"),
                summary=c_data.get("summary", "")
            )
            db.add(cluster)

            for file_ref in c_data.get("files", []):
                file_id = file_ref.get("file_id", "")
                matching_file = next((f for f in new_files if f.id == file_id), None)
                if matching_file:
                    fcm = FileClusterMap(
                        file_id=matching_file.id,
                        cluster_id=cluster.id,
                        relevance_score=file_ref.get("relevance", 1.0)
                    )
                    db.add(fcm)

        await db.commit()

        # 3. Create insights for new files
        for f in new_files:
            importance = _find_importance(clusters_data, f.id)
            insight = FileInsight(
                file_id=f.id,
                importance_score=importance.get("score", 50),
                importance_label=importance.get("label", "medium"),
                is_primary_candidate=importance.get("is_primary", False),
                why_important=importance.get("why", "")
            )
            db.add(insight)

        for f in new_files:
            f.processing_status = "organized"
        await db.commit()

        # 4. Generate summaries for new files
        for f in new_files:
            try:
                cluster_title = "Unclustered"
                for c_data in clusters_data.get("clusters", []):
                    for file_ref in c_data.get("files", []):
                        if file_ref.get("file_id") == f.id:
                            cluster_title = c_data.get("title", "Unclustered")
                            break

                importance_data = _find_importance(clusters_data, f.id)
                summary_data = await _generate_summary(f, cluster_title, importance_data)

                file_summary = FileSummary(
                    file_id=f.id,
                    summary_text=summary_data.get("summary", ""),
                    key_topics=json.dumps(summary_data.get("key_topics", []), ensure_ascii=False),
                    key_facts=json.dumps(summary_data.get("key_facts", []), ensure_ascii=False),
                    why_important=summary_data.get("why_important", ""),
                    suggested_usage=summary_data.get("suggested_usage", "")
                )
                db.add(file_summary)

                md_path = write_summary_md(
                    file_id=f.id,
                    filename=f.filename,
                    filetype=f.filetype,
                    cluster_title=cluster_title,
                    importance_score=importance_data.get("score", 50),
                    importance_label=importance_data.get("label", "medium"),
                    is_primary=importance_data.get("is_primary", False),
                    summary_text=summary_data.get("summary", ""),
                    key_topics=summary_data.get("key_topics", []),
                    key_facts=summary_data.get("key_facts", []),
                    why_important=summary_data.get("why_important", ""),
                    suggested_usage=summary_data.get("suggested_usage", ""),
                    uploaded_at=f.uploaded_at.isoformat() + "Z" if f.uploaded_at else ""
                )
                file_summary.md_path = md_path

                vector_search.index_file(
                    file_id=f.id,
                    filename=f.filename,
                    text=f.extracted_text or "",
                    cluster_title=cluster_title,
                    user_id=user_id,
                )

                # v7.0 BYOS: push summary to Drive (best-effort, no-op for managed)
                try:
                    from .storage_router import push_summary_to_drive_if_byos
                    await push_summary_to_drive_if_byos(
                        user_id, db, f.id, summary_data.get("summary", "")
                    )
                except Exception as drive_e:
                    logger.debug("BYOS summary push skipped: %s", drive_e)

                f.processing_status = "ready"
            except Exception as e:
                logger.error(f"Summary generation failed for {f.filename}: {e}")
                f.processing_status = "error"

        await db.commit()
        logger.info(f"New files organized: {len(new_files)} files for user {user_id}")
        # v7.1 — return file_ids เพื่อให้ caller รัน duplicate detection ต่อ
        # (ตอนนี้ทุกไฟล์ใหม่ index เข้า vector_search แล้ว → semantic detection ใช้งานได้เต็ม)
        return {
            "skipped": False,
            "count": len(new_files),
            "file_ids": [f.id for f in new_files],
        }

    except Exception as e:
        logger.error(f"Organize new files failed: {e}")
        for f in new_files:
            f.processing_status = "error"
        await db.commit()
        raise

