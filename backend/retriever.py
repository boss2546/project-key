"""Retrieval logic for AI Chat — MVP v3 with Graph-aware Context Injection.

Flow:
1. Parse user question
2. Load user profile → inject as system context
3. Retrieve relevant context packs (hybrid search)
4. Retrieve relevant files (hybrid search)
5. Retrieve relevant graph nodes and edges (v3)
6. Assemble graph-aware context block (priority order)
7. Token budget management
8. Generate answer with enriched prompt
9. Log injection details
10. Return answer + full transparency data + evidence graph
"""
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    File, Cluster, FileClusterMap, FileInsight, FileSummary,
    ChatQuery, ContextPack, ContextInjectionLog, GraphNode, GraphEdge, gen_id
)
from .llm import call_llm, call_llm_json
from .profile import get_profile, get_profile_context_text, is_profile_complete
from .context_packs import get_pack_context_text
from . import vector_search

logger = logging.getLogger(__name__)

# Max characters for context to avoid token overflow
MAX_CONTEXT_CHARS = 12000


async def chat_with_retrieval(db: AsyncSession, user_id: str, question: str) -> dict:
    """Process a user question with automatic context injection from all layers."""

    # ═══ LAYER 1: Load User Profile ═══
    profile_data = await get_profile(db, user_id)
    profile_text = get_profile_context_text(profile_data)
    profile_used = is_profile_complete(profile_data)

    # ═══ LAYER 2: Get all context packs ═══
    packs_result = await db.execute(
        select(ContextPack).where(ContextPack.user_id == user_id)
    )
    all_packs = packs_result.scalars().all()
    packs_data = [{
        "id": p.id,
        "type": p.type,
        "title": p.title,
        "summary_text": p.summary_text or ""
    } for p in all_packs]

    # ═══ LAYER 3: Get all clusters ═══
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id)
    )
    clusters = clusters_result.scalars().all()

    # ═══ LAYER 4: Get all ready files ═══
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

    if not files and not packs_data and not profile_used:
        return {
            "answer": "คุณยังไม่มีข้อมูลในระบบ กรุณาอัปโหลดไฟล์ ตั้งค่าโปรไฟล์ หรือสร้าง Context Pack ก่อนเพื่อให้ AI สามารถช่วยตอบคำถามได้",
            "cluster": None,
            "files_used": [],
            "context_packs_used": [],
            "profile_used": False,
            "retrieval_modes": {},
            "reasoning": "ไม่มีข้อมูลในระบบ",
            "injection_summary": "ไม่มีข้อมูล"
        }

    # ═══ HYBRID SEARCH: Find relevant chunks ═══
    vector_context = ""
    vector_hits = []
    if vector_search.is_available():
        vector_hits = vector_search.hybrid_search(question, n_results=8, user_id=user_id)
        if vector_hits:
            vector_context = "\n\nHYBRID SEARCH RESULTS (most relevant chunks):\n"
            for hit in vector_hits[:5]:
                mode_label = hit.get("search_mode", "hybrid")
                vector_context += f"  - [{hit['filename']}] ({mode_label}, relevance: {hit['relevance']:.2f}): {hit['text'][:200]}...\n"

    # ═══ BUILD INVENTORY for LLM selection ═══
    inventory = _build_inventory(clusters, files, packs_data)

    # ═══ LLM CONTEXT SELECTION ═══
    selection = await _select_context(question, inventory + vector_context, profile_used, bool(packs_data))

    # ═══ ASSEMBLE CONTEXT BLOCK (priority order) ═══
    context_parts = []
    context_char_count = 0
    files_used = []
    retrieval_modes = {}
    context_packs_used = []

    # Priority 1: Profile
    if profile_used and profile_text:
        context_parts.append(profile_text)
        context_char_count += len(profile_text)

    # Priority 2: Selected Context Packs
    selected_pack_ids = selection.get("selected_context_pack_ids", [])
    if selected_pack_ids:
        relevant_packs = [p for p in packs_data if p["id"] in selected_pack_ids]
        if relevant_packs:
            pack_text = get_pack_context_text(relevant_packs)
            if context_char_count + len(pack_text) < MAX_CONTEXT_CHARS:
                context_parts.append(pack_text)
                context_char_count += len(pack_text)
            context_packs_used = [{
                "id": p["id"],
                "type": p["type"],
                "title": p["title"]
            } for p in relevant_packs]

    # Priority 3-5: Selected Files (summary/excerpt/raw)
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

        file_context = ""
        if mode == "summary" and matching_file.summary:
            file_context = (
                f"=== {matching_file.filename} (Summary) ===\n"
                f"{matching_file.summary.summary_text}\n"
                f"Key Topics: {matching_file.summary.key_topics}\n"
                f"Key Facts: {matching_file.summary.key_facts}\n"
            )
        elif mode == "excerpt":
            text = matching_file.extracted_text[:2000] if matching_file.extracted_text else ""
            file_context = f"=== {matching_file.filename} (Excerpt) ===\n{text}\n"
        elif mode == "raw":
            text = matching_file.extracted_text[:6000] if matching_file.extracted_text else ""
            file_context = f"=== {matching_file.filename} (Full Text) ===\n{text}\n"

        if file_context and context_char_count + len(file_context) < MAX_CONTEXT_CHARS:
            context_parts.append(file_context)
            context_char_count += len(file_context)

    # ═══ LAYER 5 (v3): Graph Nodes & Edges ═══
    nodes_used = []
    edges_used = []
    graph_context = ""

    # Find relevant graph nodes for files used
    file_ids_used = [f["id"] for f in files_used]
    if file_ids_used:
        for fid in file_ids_used:
            # Find the graph node for this file
            file_node = (await db.execute(
                select(GraphNode).where(
                    GraphNode.user_id == user_id,
                    GraphNode.object_type == "source_file",
                    GraphNode.object_id == fid
                )
            )).scalar_one_or_none()

            if file_node:
                # Get edges from this node
                outgoing = (await db.execute(
                    select(GraphEdge).where(GraphEdge.source_node_id == file_node.id)
                )).scalars().all()
                incoming = (await db.execute(
                    select(GraphEdge).where(GraphEdge.target_node_id == file_node.id)
                )).scalars().all()

                for edge in (outgoing + incoming)[:5]:  # limit per file
                    other_id = edge.target_node_id if edge.source_node_id == file_node.id else edge.source_node_id
                    other_node = (await db.execute(
                        select(GraphNode).where(GraphNode.id == other_id)
                    )).scalar_one_or_none()

                    if other_node:
                        nodes_used.append({
                            "id": other_node.id,
                            "label": other_node.label,
                            "type": other_node.node_family,
                        })
                        edges_used.append({
                            "source": file_node.label,
                            "target": other_node.label,
                            "type": edge.edge_type,
                            "evidence": edge.evidence_text,
                        })

    # Add graph context to prompt
    if nodes_used:
        graph_lines = ["\n=== KNOWLEDGE GRAPH RELATIONSHIPS ==="]
        seen = set()
        for eu in edges_used:
            key = f"{eu['source']}→{eu['target']}"
            if key not in seen:
                seen.add(key)
                graph_lines.append(f"  {eu['source']} --[{eu['type']}]--> {eu['target']}: {eu['evidence']}")
        graph_context = "\n".join(graph_lines)
        if context_char_count + len(graph_context) < MAX_CONTEXT_CHARS:
            context_parts.append(graph_context)
            context_char_count += len(graph_context)

    # Deduplicate nodes_used
    seen_nodes = set()
    unique_nodes = []
    for n in nodes_used:
        if n["id"] not in seen_nodes:
            seen_nodes.add(n["id"])
            unique_nodes.append(n)
    nodes_used = unique_nodes

    context_block = "\n\n".join(context_parts)

    # ═══ SELECTED CLUSTER ═══
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

    # ═══ GENERATE ANSWER ═══
    answer = await _generate_answer(
        question, context_block,
        [f["filename"] for f in files_used],
        profile_data if profile_used else None
    )

    # ═══ BUILD INJECTION SUMMARY ═══
    injection_parts = []
    if profile_used:
        injection_parts.append("โปรไฟล์ผู้ใช้")
    if context_packs_used:
        injection_parts.append(f"{len(context_packs_used)} Context Pack")
    if selected_cluster:
        injection_parts.append(f"คอลเลกชัน: {selected_cluster['title']}")
    if files_used:
        injection_parts.append(f"{len(files_used)} ไฟล์")
    if nodes_used:
        injection_parts.append(f"{len(nodes_used)} graph nodes")
    if edges_used:
        injection_parts.append(f"{len(edges_used)} relations")
    injection_summary = " + ".join(injection_parts) if injection_parts else "ไม่มีบริบทที่เกี่ยวข้อง"

    # ═══ SAVE TO DATABASE ═══
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
    await db.flush()

    # Log injection
    injection_log = ContextInjectionLog(
        id=gen_id(),
        chat_query_id=chat_record.id,
        profile_used=profile_used,
        context_pack_ids=json.dumps([p["id"] for p in context_packs_used]),
        file_ids=json.dumps([f["id"] for f in files_used]),
        cluster_ids=json.dumps([selected_cluster["id"]] if selected_cluster else []),
        injection_summary=injection_summary,
        retrieval_reason=reasoning,
        node_ids_used=json.dumps([n["id"] for n in nodes_used]),
        edge_ids_used=json.dumps([]),  # simplified
    )
    db.add(injection_log)
    await db.commit()

    return {
        "answer": answer,
        "cluster": selected_cluster,
        "files_used": files_used,
        "context_packs_used": context_packs_used,
        "profile_used": profile_used,
        "retrieval_modes": retrieval_modes,
        "reasoning": reasoning,
        "injection_summary": injection_summary,
        # v3 — graph data
        "nodes_used": nodes_used,
        "edges_used": edges_used,
    }


def _build_inventory(clusters, files, packs_data) -> str:
    """Build a text inventory of all available data for the retrieval selector."""
    parts = []

    # Context Packs inventory
    if packs_data:
        parts.append("=== AVAILABLE CONTEXT PACKS ===")
        for p in packs_data:
            parts.append(
                f"PACK_ID: {p['id']}\n"
                f"TYPE: {p['type']}\n"
                f"TITLE: {p['title']}\n"
                f"PREVIEW: {p['summary_text'][:200]}\n"
                f"---"
            )

    # Files inventory
    cluster_map = {c.id: c for c in clusters}

    parts.append("=== AVAILABLE FILES ===")
    for f in files:
        cluster_titles = []
        cluster_ids = []
        for cm in f.cluster_maps:
            c = cluster_map.get(cm.cluster_id)
            if c:
                cluster_titles.append(c.title)
                cluster_ids.append(c.id)

        summary_preview = f.summary.summary_text[:200] if f.summary else ""
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


async def _select_context(question: str, inventory: str, has_profile: bool, has_packs: bool) -> dict:
    """Use LLM to decide which context sources to use."""

    pack_instruction = ""
    if has_packs:
        pack_instruction = """
  "selected_context_pack_ids": ["pack_id_1", "pack_id_2"],"""

    system_prompt = f"""You are a retrieval selector AI for a personal data space. Based on the user's question and the available data inventory, select the most relevant sources.

The user {"has a profile set up" if has_profile else "has not set up a profile"}.
{"The user has context packs available." if has_packs else "No context packs available."}

Respond with ONLY valid JSON:

{{
  "selected_cluster_id": "cluster_id or null",{pack_instruction}
  "selected_files": [
    {{
      "file_id": "actual file id",
      "mode": "summary|excerpt|raw"
    }}
  ],
  "reasoning": "อธิบายสั้นๆ เป็นภาษาไทยว่าทำไมถึงเลือกแหล่งข้อมูลเหล่านี้ และระบุด้วยว่าใช้ profile / context pack / files อะไรบ้าง"
}}

Mode selection rules:
- "summary": Default. Use for general understanding, overview, or broad topics.
- "excerpt": Use when the question asks about a specific part or detail.
- "raw": Use when precise quotes, exact wording, or very detailed content is needed.

{"Select relevant context packs if they match the question's domain." if has_packs else ""}
Select 1-4 most relevant files. Prefer files with higher importance and primary candidates.
Always write the "reasoning" field in Thai."""

    user_prompt = f"USER QUESTION: {question}\n\nAVAILABLE DATA:\n{inventory}"

    return await call_llm_json(system_prompt, user_prompt)


async def _generate_answer(question: str, context: str, filenames: list, profile_data: dict = None) -> str:
    """Generate the final answer using injected context from all layers."""

    profile_instruction = ""
    if profile_data and profile_data.get("exists"):
        style = profile_data.get("preferred_output_style", "")
        if style:
            profile_instruction = f"\nThe user prefers answers in this style: {style}"

    system_prompt = f"""You are an AI assistant that answers questions using the user's personal knowledge workspace.

You have access to the user's:
- Personal profile (if provided)
- Context packs (high-level context documents)
- File collections and summaries
- Raw file content
- Knowledge graph relationships (nodes and typed edges with evidence)

Rules:
- ONLY answer based on the provided context
- If the context doesn't contain enough information, say so honestly
- Reference specific files or context packs by name when relevant
- When knowledge graph relationships are provided, use them to connect ideas and explain connections
- Write in the SAME LANGUAGE as the user's question
- Be detailed and helpful
- Structure your answer with clear formatting (paragraphs, bullet points if needed)
- Acknowledge that you're using the user's personal data when appropriate{profile_instruction}"""

    source_list = ', '.join(filenames) if filenames else 'injected context'
    user_prompt = (
        f"QUESTION: {question}\n\n"
        f"CONTEXT FROM USER'S KNOWLEDGE WORKSPACE ({source_list}):\n\n"
        f"{context}"
    )

    return await call_llm(system_prompt, user_prompt, temperature=0.4, max_tokens=8192)
