"""Graph Builder — auto-builds knowledge graph from existing data.

Scans files, summaries, clusters, and context packs to create
graph nodes and typed edges representing knowledge relationships.
"""
import json
import logging
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    gen_id, File, Cluster, FileClusterMap, FileInsight, FileSummary,
    ContextPack, GraphNode, GraphEdge, NoteObject
)
from .llm import call_llm_pro

logger = logging.getLogger(__name__)


async def build_full_graph(db: AsyncSession, user_id: str):
    """Build the complete knowledge graph from all existing data."""
    logger.info("Building full knowledge graph...")

    # Clear existing graph data
    await db.execute(delete(GraphEdge).where(GraphEdge.user_id == user_id))
    await db.execute(delete(GraphNode).where(GraphNode.user_id == user_id))
    await db.execute(delete(NoteObject).where(NoteObject.user_id == user_id))
    await db.commit()

    # Phase 1: Create nodes from all data sources
    node_map = {}  # object_type:object_id → node_id

    # 1a. Files → nodes
    files = (await db.execute(select(File).where(File.user_id == user_id))).scalars().all()
    for f in files:
        node = GraphNode(
            id=gen_id(), user_id=user_id,
            object_type="source_file", object_id=f.id,
            label=f.filename, node_family="source_file",
            importance_score=0.5, freshness_score=1.0,
            metadata_json=json.dumps({
                "filetype": f.filetype,
                "status": f.processing_status,
                "tags": json.loads(f.tags or "[]"),
            })
        )
        # Update importance from FileInsight if available
        insight = (await db.execute(
            select(FileInsight).where(FileInsight.file_id == f.id)
        )).scalar_one_or_none()
        if insight:
            node.importance_score = insight.importance_score / 100.0

        db.add(node)
        node_map[f"source_file:{f.id}"] = node.id

    # 1b. Clusters → nodes
    clusters = (await db.execute(select(Cluster).where(Cluster.user_id == user_id))).scalars().all()
    for c in clusters:
        node = GraphNode(
            id=gen_id(), user_id=user_id,
            object_type="cluster", object_id=c.id,
            label=c.title, node_family="project",
            importance_score=0.7, freshness_score=1.0,
            metadata_json=json.dumps({"summary_preview": (c.summary or "")[:200]})
        )
        db.add(node)
        node_map[f"cluster:{c.id}"] = node.id

    # 1c. Context Packs → nodes
    packs = (await db.execute(select(ContextPack).where(ContextPack.user_id == user_id))).scalars().all()
    for p in packs:
        node = GraphNode(
            id=gen_id(), user_id=user_id,
            object_type="context_pack", object_id=p.id,
            label=p.title, node_family="context_pack",
            importance_score=0.8, freshness_score=1.0,
            metadata_json=json.dumps({"type": p.type})
        )
        db.add(node)
        node_map[f"context_pack:{p.id}"] = node.id

    await db.commit()

    # Phase 2: Extract tags from summaries — with dedup, filtering, and AI descriptions
    tag_file_map = {}  # tag_label → set of file_ids that use this tag
    entity_nodes = {}  # entity_label → node_id

    # v5.1 — only get summaries for this user's files
    user_file_ids = [f.id for f in files]
    if user_file_ids:
        summaries = (await db.execute(
            select(FileSummary).where(FileSummary.file_id.in_(user_file_ids))
        )).scalars().all()
    else:
        summaries = []
    for s in summaries:
        file_node_key = f"source_file:{s.file_id}"
        if file_node_key not in node_map:
            continue

        # Extract tags from key_topics
        try:
            topics = json.loads(s.key_topics or "[]")
        except (json.JSONDecodeError, TypeError):
            topics = []

        for topic in topics[:5]:  # Limit to 5 tags per file
            topic_clean = topic.strip().lower()
            if not topic_clean or len(topic_clean) < 2:
                continue
            if topic_clean not in tag_file_map:
                tag_file_map[topic_clean] = set()
            tag_file_map[topic_clean].add(s.file_id)

    # Filter: keep only tags used by 2+ files (cross-file discovery value)
    # Exception: keep all if total files <= 3 (small dataset)
    total_files = len(files)
    min_connections = 1 if total_files <= 3 else 2
    useful_tags = {k: v for k, v in tag_file_map.items() if len(v) >= min_connections}

    logger.info(f"Tags: {len(tag_file_map)} total → {len(useful_tags)} useful (min {min_connections} connections)")

    # Generate AI descriptions for all useful tags in one batch call
    tag_descriptions = {}
    if useful_tags:
        tag_list_str = ", ".join(useful_tags.keys())
        try:
            desc_prompt = f"""จาก tag keywords ต่อไปนี้ ให้สร้างคำอธิบายสั้นๆ (1-2 ประโยค) สำหรับแต่ละ tag

Tags: {tag_list_str}

ตอบเป็น JSON object เท่านั้น โดย key = tag name, value = คำอธิบายสั้นๆ ภาษาไทย
ตัวอย่าง: {{"ai": "ปัญญาประดิษฐ์ เทคโนโลยีที่ทำให้เครื่องจักรเรียนรู้และตัดสินใจ", "knowledge graph": "โครงสร้างข้อมูลที่แสดงความสัมพันธ์ระหว่าง entities ต่างๆ"}}

ตอบ JSON เท่านั้น ไม่ต้องอธิบายเพิ่ม:"""

            desc_response = await call_llm_pro("คุณเป็นผู้เชี่ยวชาญด้าน knowledge management ตอบเป็น JSON เท่านั้น", desc_prompt, temperature=0.2)
            desc_json = desc_response.strip()
            if desc_json.startswith("```"):
                desc_json = desc_json.split("\n", 1)[1].rsplit("```", 1)[0]
            tag_descriptions = json.loads(desc_json)
            logger.info(f"Generated descriptions for {len(tag_descriptions)} tags")
        except Exception as e:
            logger.warning(f"Tag description generation failed: {e}")

    # Create tag nodes with dynamic importance and descriptions
    tag_nodes = {}  # tag_label → node_id
    for tag_label, file_ids in useful_tags.items():
        connection_count = len(file_ids)
        # Dynamic importance: more connections = more important (0.3 base → up to 0.9)
        dynamic_importance = min(0.9, 0.3 + (connection_count / max(total_files, 1)) * 0.6)

        description = tag_descriptions.get(tag_label, "")

        tag_node = GraphNode(
            id=gen_id(), user_id=user_id,
            object_type="tag", object_id=tag_label,
            label=tag_label, node_family="tag",
            importance_score=dynamic_importance, freshness_score=1.0,
            metadata_json=json.dumps({
                "description": description,
                "connection_count": connection_count,
                "connected_files": list(file_ids),
            })
        )
        db.add(tag_node)
        tag_nodes[tag_label] = tag_node.id

    await db.commit()

    # Phase 3: Extract entities via LLM
    all_summaries_text = ""
    file_summary_map = {}
    for s in summaries:
        if s.summary_text:
            all_summaries_text += f"\n[{s.file_id}] {s.summary_text[:300]}"
            file_summary_map[s.file_id] = s.summary_text

    if all_summaries_text.strip():
        try:
            entity_prompt = f"""จากข้อมูลสรุปไฟล์ต่อไปนี้ ให้แยก entities สำคัญออกมาในรูปแบบ JSON array

ข้อมูล:
{all_summaries_text[:3000]}

ให้ตอบเป็น JSON array เท่านั้น แต่ละ entity มี:
- "name": ชื่อ entity (ภาษาไทยหรืออังกฤษ)
- "type": ประเภท (person/project/concept/organization/product)
- "mentioned_in": array ของ file_id ที่กล่าวถึง entity นี้

ตัวอย่าง: [{{"name":"NOVA","type":"project","mentioned_in":["abc123","def456"]}}]

ตอบ JSON เท่านั้น ไม่ต้องอธิบาย:"""

            entity_response = await call_llm_pro("คุณเป็นผู้เชี่ยวชาญด้าน entity extraction ตอบเป็น JSON เท่านั้น", entity_prompt, temperature=0.1)
            # Parse JSON from response
            entity_json = entity_response.strip()
            if entity_json.startswith("```"):
                entity_json = entity_json.split("\n", 1)[1].rsplit("```", 1)[0]
            entities = json.loads(entity_json)

            for ent in entities[:20]:  # Limit to 20 entities
                ent_name = ent.get("name", "").strip()
                ent_type = ent.get("type", "entity")
                mentioned_in = ent.get("mentioned_in", [])

                if not ent_name or len(ent_name) < 2:
                    continue

                # Create entity NoteObject
                note_obj = NoteObject(
                    id=gen_id(), user_id=user_id,
                    type=ent_type, title=ent_name,
                    summary=f"Entity ประเภท {ent_type}",
                    aliases=json.dumps([]),
                    metadata_json=json.dumps({"extracted_from": "llm", "source_files": mentioned_in})
                )
                db.add(note_obj)

                # Create entity graph node
                ent_node = GraphNode(
                    id=gen_id(), user_id=user_id,
                    object_type="entity", object_id=note_obj.id,
                    label=ent_name, node_family=ent_type if ent_type in ("person", "project") else "entity",
                    importance_score=0.6, freshness_score=1.0,
                    metadata_json=json.dumps({"entity_type": ent_type})
                )
                db.add(ent_node)
                entity_nodes[ent_name] = ent_node.id

                # Create "mentions" edges to source files
                for fid in mentioned_in:
                    file_key = f"source_file:{fid}"
                    if file_key in node_map:
                        edge = GraphEdge(
                            id=gen_id(), user_id=user_id,
                            source_node_id=node_map[file_key],
                            target_node_id=ent_node.id,
                            edge_type="mentions",
                            weight=0.8, confidence=0.7,
                            provenance="llm",
                            evidence_text=f"ไฟล์กล่าวถึง {ent_name}"
                        )
                        db.add(edge)

            await db.commit()
            logger.info(f"Extracted {len(entities)} entities via LLM")

        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")

    # Phase 4: Create edges

    # 4a. File → Cluster edges (contains) — v5.1: filter by user's files only
    if user_file_ids:
        file_cluster_maps = (await db.execute(
            select(FileClusterMap).where(FileClusterMap.file_id.in_(user_file_ids))
        )).scalars().all()
    else:
        file_cluster_maps = []
    for fcm in file_cluster_maps:
        src = node_map.get(f"source_file:{fcm.file_id}")
        tgt = node_map.get(f"cluster:{fcm.cluster_id}")
        if src and tgt:
            edge = GraphEdge(
                id=gen_id(), user_id=user_id,
                source_node_id=tgt, target_node_id=src,
                edge_type="contains", weight=fcm.relevance_score,
                confidence=1.0, provenance="system",
                evidence_text="ไฟล์อยู่ใน collection นี้"
            )
            db.add(edge)

    # 4b. Context Pack → source file edges (derived_from)
    for p in packs:
        pack_node = node_map.get(f"context_pack:{p.id}")
        if not pack_node:
            continue
        try:
            source_ids = json.loads(p.source_file_ids or "[]")
        except (json.JSONDecodeError, TypeError):
            source_ids = []
        for fid in source_ids:
            file_node = node_map.get(f"source_file:{fid}")
            if file_node:
                edge = GraphEdge(
                    id=gen_id(), user_id=user_id,
                    source_node_id=pack_node, target_node_id=file_node,
                    edge_type="derived_from", weight=0.9,
                    confidence=1.0, provenance="system",
                    evidence_text=f"Context pack สร้างจากไฟล์นี้"
                )
                db.add(edge)

    # 4c. File → Tag edges (has_tag) from key_topics
    for s in summaries:
        file_node_key = f"source_file:{s.file_id}"
        if file_node_key not in node_map:
            continue
        try:
            topics = json.loads(s.key_topics or "[]")
        except (json.JSONDecodeError, TypeError):
            topics = []
        for topic in topics[:5]:
            topic_clean = topic.strip().lower()
            if topic_clean in tag_nodes:
                edge = GraphEdge(
                    id=gen_id(), user_id=user_id,
                    source_node_id=node_map[file_node_key],
                    target_node_id=tag_nodes[topic_clean],
                    edge_type="has_tag", weight=0.6,
                    confidence=0.9, provenance="system",
                    evidence_text=f"ไฟล์มีหัวข้อ '{topic_clean}'"
                )
                db.add(edge)

    # 4d. Files in same cluster → semantically_related edges
    for c in clusters:
        cluster_files = [
            fcm.file_id for fcm in file_cluster_maps
            if fcm.cluster_id == c.id
        ]
        for i, fid1 in enumerate(cluster_files):
            for fid2 in cluster_files[i + 1:]:
                src = node_map.get(f"source_file:{fid1}")
                tgt = node_map.get(f"source_file:{fid2}")
                if src and tgt:
                    edge = GraphEdge(
                        id=gen_id(), user_id=user_id,
                        source_node_id=src, target_node_id=tgt,
                        edge_type="semantically_related", weight=0.7,
                        confidence=0.8, provenance="system",
                        evidence_text=f"อยู่ใน collection '{c.title}' เดียวกัน"
                    )
                    db.add(edge)

    await db.commit()

    # Count results
    node_count = len(node_map) + len(tag_nodes) + len(entity_nodes)
    edge_result = (await db.execute(
        select(GraphEdge).where(GraphEdge.user_id == user_id)
    )).scalars().all()
    edge_count = len(edge_result)

    logger.info(f"Graph built: {node_count} nodes, {edge_count} edges")
    return {"nodes": node_count, "edges": edge_count}


async def get_graph_data(db: AsyncSession, user_id: str):
    """Get all nodes and edges for rendering the full graph."""
    nodes = (await db.execute(
        select(GraphNode).where(GraphNode.user_id == user_id)
    )).scalars().all()

    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.user_id == user_id)
    )).scalars().all()

    return {
        "nodes": [
            {
                "id": n.id,
                "object_type": n.object_type,
                "object_id": n.object_id,
                "label": n.label,
                "node_family": n.node_family,
                "importance": n.importance_score,
                "freshness": n.freshness_score,
                "pinned": n.pinned,
                "metadata": json.loads(n.metadata_json or "{}"),
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "edge_type": e.edge_type,
                "weight": e.weight,
                "confidence": e.confidence,
                "provenance": e.provenance,
                "evidence": e.evidence_text,
            }
            for e in edges
        ],
    }


async def get_node_detail(db: AsyncSession, node_id: str):
    """Get detailed info about a single node including summary and relations."""
    node = (await db.execute(
        select(GraphNode).where(GraphNode.id == node_id)
    )).scalar_one_or_none()
    if not node:
        return None

    # Get summary based on object type
    summary = ""
    metadata = json.loads(node.metadata_json or "{}")

    if node.object_type == "source_file":
        file_summary = (await db.execute(
            select(FileSummary).where(FileSummary.file_id == node.object_id)
        )).scalar_one_or_none()
        if file_summary:
            summary = file_summary.summary_text

    elif node.object_type == "context_pack":
        pack = (await db.execute(
            select(ContextPack).where(ContextPack.id == node.object_id)
        )).scalar_one_or_none()
        if pack:
            summary = pack.summary_text

    elif node.object_type == "cluster":
        cluster = (await db.execute(
            select(Cluster).where(Cluster.id == node.object_id)
        )).scalar_one_or_none()
        if cluster:
            summary = cluster.summary

    elif node.object_type == "entity":
        note = (await db.execute(
            select(NoteObject).where(NoteObject.id == node.object_id)
        )).scalar_one_or_none()
        if note:
            summary = note.summary

    elif node.object_type == "tag":
        # Tag description from metadata
        desc = metadata.get("description", "")
        conn_count = metadata.get("connection_count", 0)
        if desc:
            summary = f"{desc} (เชื่อมกับ {conn_count} ไฟล์)"
        else:
            summary = f"Tag ที่ปรากฏใน {conn_count} ไฟล์"

    # Get connected edges
    outgoing = (await db.execute(
        select(GraphEdge).where(GraphEdge.source_node_id == node_id)
    )).scalars().all()

    incoming = (await db.execute(
        select(GraphEdge).where(GraphEdge.target_node_id == node_id)
    )).scalars().all()

    # Resolve labels for connected nodes
    connected_ids = set()
    for e in outgoing:
        connected_ids.add(e.target_node_id)
    for e in incoming:
        connected_ids.add(e.source_node_id)

    connected_nodes = {}
    if connected_ids:
        for cid in connected_ids:
            cn = (await db.execute(
                select(GraphNode).where(GraphNode.id == cid)
            )).scalar_one_or_none()
            if cn:
                connected_nodes[cn.id] = {"label": cn.label, "type": cn.object_type, "family": cn.node_family}

    return {
        "id": node.id,
        "object_type": node.object_type,
        "object_id": node.object_id,
        "label": node.label,
        "node_family": node.node_family,
        "importance": node.importance_score,
        "freshness": node.freshness_score,
        "summary": summary,
        "metadata": metadata,
        "outgoing": [
            {
                "edge_id": e.id,
                "target_id": e.target_node_id,
                "target_label": connected_nodes.get(e.target_node_id, {}).get("label", "?"),
                "target_type": connected_nodes.get(e.target_node_id, {}).get("type", "?"),
                "edge_type": e.edge_type,
                "weight": e.weight,
                "evidence": e.evidence_text,
            }
            for e in outgoing
        ],
        "incoming": [
            {
                "edge_id": e.id,
                "source_id": e.source_node_id,
                "source_label": connected_nodes.get(e.source_node_id, {}).get("label", "?"),
                "source_type": connected_nodes.get(e.source_node_id, {}).get("type", "?"),
                "edge_type": e.edge_type,
                "weight": e.weight,
                "evidence": e.evidence_text,
            }
            for e in incoming
        ],
    }


async def get_neighborhood(db: AsyncSession, node_id: str, depth: int = 1, user_id: str = None):
    """Get N-hop neighborhood around a node for local graph view."""
    visited_nodes = set()
    visited_edges = set()
    frontier = {node_id}

    for _ in range(depth):
        new_frontier = set()
        for nid in frontier:
            if nid in visited_nodes:
                continue
            visited_nodes.add(nid)

            # Get outgoing edges
            outgoing = (await db.execute(
                select(GraphEdge).where(GraphEdge.source_node_id == nid)
            )).scalars().all()
            for e in outgoing:
                visited_edges.add(e.id)
                new_frontier.add(e.target_node_id)

            # Get incoming edges
            incoming = (await db.execute(
                select(GraphEdge).where(GraphEdge.target_node_id == nid)
            )).scalars().all()
            for e in incoming:
                visited_edges.add(e.id)
                new_frontier.add(e.source_node_id)

        frontier = new_frontier - visited_nodes

    # Also include the last frontier nodes (they're neighbors we haven't expanded)
    visited_nodes.update(frontier)

    # Fetch node data
    nodes = []
    for nid in visited_nodes:
        n = (await db.execute(
            select(GraphNode).where(GraphNode.id == nid)
        )).scalar_one_or_none()
        if n:
            nodes.append({
                "id": n.id,
                "object_type": n.object_type,
                "object_id": n.object_id,
                "label": n.label,
                "node_family": n.node_family,
                "importance": n.importance_score,
                "freshness": n.freshness_score,
                "metadata": json.loads(n.metadata_json or "{}"),
            })

    # Fetch edge data (only edges between visited nodes)
    edges = []
    for eid in visited_edges:
        e = (await db.execute(
            select(GraphEdge).where(GraphEdge.id == eid)
        )).scalar_one_or_none()
        if e and e.source_node_id in visited_nodes and e.target_node_id in visited_nodes:
            edges.append({
                "id": e.id,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "edge_type": e.edge_type,
                "weight": e.weight,
                "confidence": e.confidence,
                "evidence": e.evidence_text,
            })

    return {
        "center_node_id": node_id,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
    }
