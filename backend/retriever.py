"""Retrieval logic for AI Chat — selects relevant context before sending to LLM.

RAGFlow-inspired: Uses vector search for first-pass retrieval, then LLM for refinement.
"""
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import File, Cluster, FileClusterMap, FileInsight, FileSummary, ChatQuery, gen_id
from .llm import call_llm, call_llm_json
from . import vector_search

logger = logging.getLogger(__name__)


async def chat_with_retrieval(db: AsyncSession, user_id: str, question: str) -> dict:
    """Process a user question with intelligent retrieval from their data."""

    # 1. Get all user's clusters and files with summaries
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id)
    )
    clusters = clusters_result.scalars().all()

    files_result = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.processing_status == "ready"
        ).options(
            selectinload(File.insight),
            selectinload(File.summary),
            selectinload(File.cluster_maps)
        )
    )
    files = files_result.scalars().all()

    if not files:
        return {
            "answer": "You don't have any organized files yet. Please upload files first and let the system organize them.",
            "cluster": None,
            "files_used": [],
            "retrieval_modes": {},
            "reasoning": "No organized files available to answer from."
        }

    # 2. RAGFlow-style: Vector search for relevant chunks first
    vector_context = ""
    vector_hits = []
    if vector_search.is_available():
        vector_hits = vector_search.search(question, n_results=8)
        if vector_hits:
            vector_context = "\n\nSEMANTIC SEARCH RESULTS (most relevant chunks):\n"
            for hit in vector_hits[:5]:
                vector_context += f"  - [{hit['filename']}] (relevance: {hit['relevance']:.2f}): {hit['text'][:200]}...\n"

    # 3. Build context inventory for LLM retrieval decision
    inventory = _build_inventory(clusters, files)

    # 4. Ask LLM to select relevant context (enhanced with vector search results)
    selection = await _select_context(question, inventory + vector_context)

    # 4. Build the actual context to send to the answering LLM
    context_parts = []
    files_used = []
    retrieval_modes = {}

    for sel_file in selection.get("selected_files", []):
        file_id = sel_file.get("file_id", "")
        mode = sel_file.get("mode", "summary")
        matching_file = next((f for f in files if f.id == file_id), None)
        if not matching_file:
            continue

        files_used.append({
            "id": matching_file.id,
            "filename": matching_file.filename,
            "filetype": matching_file.filetype,
            "importance_label": matching_file.insight.importance_label if matching_file.insight else "medium",
            "is_primary": matching_file.insight.is_primary_candidate if matching_file.insight else False
        })
        retrieval_modes[matching_file.id] = mode

        if mode == "summary" and matching_file.summary:
            context_parts.append(
                f"=== {matching_file.filename} (Summary) ===\n"
                f"{matching_file.summary.summary_text}\n"
                f"Key Topics: {matching_file.summary.key_topics}\n"
                f"Key Facts: {matching_file.summary.key_facts}\n"
            )
        elif mode == "excerpt":
            # Use first 2000 chars of extracted text
            text = matching_file.extracted_text[:2000] if matching_file.extracted_text else ""
            context_parts.append(
                f"=== {matching_file.filename} (Excerpt) ===\n{text}\n"
            )
        elif mode == "raw":
            # Use full extracted text (up to 6000 chars)
            text = matching_file.extracted_text[:6000] if matching_file.extracted_text else ""
            context_parts.append(
                f"=== {matching_file.filename} (Full Text) ===\n{text}\n"
            )

    context_block = "\n\n".join(context_parts)

    # 5. Get the selected cluster info
    selected_cluster = None
    sel_cluster_id = selection.get("selected_cluster_id")
    if sel_cluster_id:
        matching_cluster = next((c for c in clusters if c.id == sel_cluster_id), None)
        if matching_cluster:
            selected_cluster = {
                "id": matching_cluster.id,
                "title": matching_cluster.title,
                "summary": matching_cluster.summary
            }

    reasoning = selection.get("reasoning", "")

    # 6. Generate answer
    answer = await _generate_answer(question, context_block, [f["filename"] for f in files_used])

    # 7. Save to database
    chat_record = ChatQuery(
        id=gen_id(),
        user_id=user_id,
        question=question,
        answer=answer,
        selected_cluster_ids=json.dumps([selected_cluster["id"]] if selected_cluster else []),
        selected_file_ids=json.dumps([f["id"] for f in files_used]),
        retrieval_modes=json.dumps(retrieval_modes),
        reasoning=reasoning
    )
    db.add(chat_record)
    await db.commit()

    return {
        "answer": answer,
        "cluster": selected_cluster,
        "files_used": files_used,
        "retrieval_modes": retrieval_modes,
        "reasoning": reasoning
    }


def _build_inventory(clusters, files) -> str:
    """Build a text inventory of all available data for the retrieval selector."""
    parts = []
    cluster_map = {}
    for c in clusters:
        cluster_map[c.id] = c

    for f in files:
        cluster_titles = []
        cluster_ids = []
        for cm in f.cluster_maps:
            c = cluster_map.get(cm.cluster_id)
            if c:
                cluster_titles.append(c.title)
                cluster_ids.append(c.id)

        summary_preview = ""
        if f.summary:
            summary_preview = f.summary.summary_text[:200]

        importance = f.insight.importance_label if f.insight else "unknown"
        is_primary = f.insight.is_primary_candidate if f.insight else False

        parts.append(
            f"FILE_ID: {f.id}\n"
            f"FILENAME: {f.filename}\n"
            f"CLUSTER: {', '.join(cluster_titles)} (IDs: {', '.join(cluster_ids)})\n"
            f"IMPORTANCE: {importance} | PRIMARY: {is_primary}\n"
            f"SUMMARY_PREVIEW: {summary_preview}\n"
            f"TEXT_LENGTH: {len(f.extracted_text or '')} chars\n"
            f"---"
        )

    return "\n".join(parts)


async def _select_context(question: str, inventory: str) -> dict:
    """Use LLM to decide which files and retrieval mode to use."""

    system_prompt = """You are a retrieval selector AI. Based on the user's question and the available file inventory, select which files are most relevant and how they should be used.

Respond with ONLY valid JSON:

{
  "selected_cluster_id": "cluster_id or null",
  "selected_files": [
    {
      "file_id": "actual file id",
      "mode": "summary|excerpt|raw"
    }
  ],
  "reasoning": "อธิบายสั้นๆ เป็นภาษาไทยว่าทำไมถึงเลือกไฟล์เหล่านี้ และเลือกโหมดการดึงข้อมูลอะไร"
}

Mode selection rules:
- "summary": Default. Use when the question is about general understanding, overview, or broad topics.
- "excerpt": Use when the question asks about a specific part, detail, or section.
- "raw": Use when the question needs precise quotes, exact wording, or very detailed content.

Select 1-4 most relevant files. Prefer files with higher importance and primary candidates.
Always write the "reasoning" field in Thai."""

    user_prompt = f"USER QUESTION: {question}\n\nAVAILABLE FILES:\n{inventory}"

    return await call_llm_json(system_prompt, user_prompt)


async def _generate_answer(question: str, context: str, filenames: list) -> str:
    """Generate the final answer using retrieved context."""

    system_prompt = """You are an AI assistant that answers questions using the user's personal document collection. 

Rules:
- ONLY answer based on the provided context
- If the context doesn't contain enough information, say so honestly
- Reference specific files by name when relevant
- Write in the SAME LANGUAGE as the user's question
- Be detailed and helpful
- Structure your answer with clear formatting (paragraphs, bullet points if needed)"""

    user_prompt = (
        f"QUESTION: {question}\n\n"
        f"CONTEXT FROM USER'S FILES ({', '.join(filenames)}):\n\n"
        f"{context}"
    )

    return await call_llm(system_prompt, user_prompt, temperature=0.4, max_tokens=4000)
