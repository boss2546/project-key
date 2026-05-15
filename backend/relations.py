"""Relations service — backlinks, outgoing links, and relationship management."""
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import gen_id, GraphNode, GraphEdge, SuggestedRelation

logger = logging.getLogger(__name__)


async def get_backlinks(db: AsyncSession, node_id: str):
    """Get all nodes that link TO this node (incoming edges).

    v10.0.0: fixed N+1 -- was 1 query per edge for the source node;
    now a single bulk IN-query then in-memory join.
    """
    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.target_node_id == node_id)
    )).scalars().all()
    if not edges:
        return []

    source_ids = {e.source_node_id for e in edges}
    source_rows = (await db.execute(
        select(GraphNode).where(GraphNode.id.in_(source_ids))
    )).scalars().all()
    source_by_id = {n.id: n for n in source_rows}

    results = []
    for e in edges:
        source = source_by_id.get(e.source_node_id)
        if source:
            results.append({
                "edge_id": e.id,
                "node_id": source.id,
                "label": source.label,
                "object_type": source.object_type,
                "node_family": source.node_family,
                "edge_type": e.edge_type,
                "weight": e.weight,
                "confidence": e.confidence,
                "evidence": e.evidence_text,
            })
    return results


async def get_outgoing(db: AsyncSession, node_id: str):
    """Get all nodes that this node links TO (outgoing edges).

    v10.0.0: fixed N+1 (same pattern as get_backlinks).
    """
    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.source_node_id == node_id)
    )).scalars().all()
    if not edges:
        return []

    target_ids = {e.target_node_id for e in edges}
    target_rows = (await db.execute(
        select(GraphNode).where(GraphNode.id.in_(target_ids))
    )).scalars().all()
    target_by_id = {n.id: n for n in target_rows}

    results = []
    for e in edges:
        target = target_by_id.get(e.target_node_id)
        if target:
            results.append({
                "edge_id": e.id,
                "node_id": target.id,
                "label": target.label,
                "object_type": target.object_type,
                "node_family": target.node_family,
                "edge_type": e.edge_type,
                "weight": e.weight,
                "confidence": e.confidence,
                "evidence": e.evidence_text,
            })
    return results


async def get_suggestions(db: AsyncSession, user_id: str, status: str = "pending"):
    """Get suggested relations awaiting user action.

    v10.0.0: fixed 2N+1 -- was 2 queries per suggestion (source + target node);
    now a single IN-query covering both ids.
    """
    suggestions = (await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            SuggestedRelation.status == status
        )
    )).scalars().all()
    if not suggestions:
        return []

    node_ids = set()
    for s in suggestions:
        node_ids.add(s.source_node_id)
        node_ids.add(s.target_node_id)
    nodes = (await db.execute(
        select(GraphNode).where(GraphNode.id.in_(node_ids))
    )).scalars().all()
    by_id = {n.id: n for n in nodes}

    results = []
    for s in suggestions:
        source = by_id.get(s.source_node_id)
        target = by_id.get(s.target_node_id)
        if source and target:
            results.append({
                "id": s.id,
                "source_id": s.source_node_id,
                "source_label": source.label,
                "source_type": source.object_type,
                "target_id": s.target_node_id,
                "target_label": target.label,
                "target_type": target.object_type,
                "relation_type": s.relation_type,
                "reason": s.suggestion_reason,
                "confidence": s.confidence,
                "status": s.status,
            })
    return results


async def accept_suggestion(db: AsyncSession, suggestion_id: str, user_id: str):
    """Accept a suggested relation — create a real edge from it."""
    suggestion = (await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.id == suggestion_id,
            SuggestedRelation.user_id == user_id
        )
    )).scalar_one_or_none()

    if not suggestion:
        return None

    # Create real edge
    edge = GraphEdge(
        id=gen_id(), user_id=user_id,
        source_node_id=suggestion.source_node_id,
        target_node_id=suggestion.target_node_id,
        edge_type=suggestion.relation_type,
        weight=0.8, confidence=suggestion.confidence,
        provenance="user_accepted",
        evidence_text=suggestion.suggestion_reason,
    )
    db.add(edge)

    # Update suggestion status
    suggestion.status = "accepted"
    await db.commit()

    return {"edge_id": edge.id, "status": "accepted"}


async def dismiss_suggestion(db: AsyncSession, suggestion_id: str, user_id: str):
    """Dismiss a suggested relation."""
    suggestion = (await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.id == suggestion_id,
            SuggestedRelation.user_id == user_id
        )
    )).scalar_one_or_none()

    if not suggestion:
        return None

    suggestion.status = "dismissed"
    await db.commit()

    return {"status": "dismissed"}


async def generate_suggestions(db: AsyncSession, user_id: str):
    """Generate suggested relations using heuristics and LLM analysis."""
    from .llm import call_llm_pro

    # Get all nodes
    nodes = (await db.execute(
        select(GraphNode).where(GraphNode.user_id == user_id)
    )).scalars().all()

    # Get existing edges for deduplication
    existing_edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.user_id == user_id)
    )).scalars().all()
    existing_pairs = set()
    for e in existing_edges:
        existing_pairs.add((e.source_node_id, e.target_node_id))
        existing_pairs.add((e.target_node_id, e.source_node_id))

    # Clear old pending suggestions
    old_suggestions = (await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            SuggestedRelation.status == "pending"
        )
    )).scalars().all()
    for s in old_suggestions:
        await db.delete(s)
    await db.commit()

    # Heuristic 1: Entities with similar labels might be same_entity
    entity_nodes = [n for n in nodes if n.object_type == "entity"]
    for i, n1 in enumerate(entity_nodes):
        for n2 in entity_nodes[i + 1:]:
            if n1.label.lower() == n2.label.lower() and (n1.id, n2.id) not in existing_pairs:
                suggestion = SuggestedRelation(
                    id=gen_id(), user_id=user_id,
                    source_node_id=n1.id, target_node_id=n2.id,
                    relation_type="same_entity",
                    suggestion_reason=f"'{n1.label}' และ '{n2.label}' อาจเป็น entity เดียวกัน",
                    confidence=0.9,
                )
                db.add(suggestion)

    # Heuristic 2: Files sharing many tags might be semantically_related
    # v10.0.0: fixed N+1 -- previous code ran one SELECT per file_node.
    # Now single bulk query then group in Python.
    file_nodes = [n for n in nodes if n.object_type == "source_file"]
    file_node_ids = [fn.id for fn in file_nodes]
    tag_map = {fn.id: set() for fn in file_nodes}
    if file_node_ids:
        all_has_tag_edges = (await db.execute(
            select(GraphEdge).where(
                GraphEdge.source_node_id.in_(file_node_ids),
                GraphEdge.edge_type == "has_tag"
            )
        )).scalars().all()
        for e in all_has_tag_edges:
            tag_map.setdefault(e.source_node_id, set()).add(e.target_node_id)

    for i, fn1 in enumerate(file_nodes):
        for fn2 in file_nodes[i + 1:]:
            shared = tag_map.get(fn1.id, set()) & tag_map.get(fn2.id, set())
            if len(shared) >= 2 and (fn1.id, fn2.id) not in existing_pairs:
                suggestion = SuggestedRelation(
                    id=gen_id(), user_id=user_id,
                    source_node_id=fn1.id, target_node_id=fn2.id,
                    relation_type="semantically_related",
                    suggestion_reason=f"มีหัวข้อร่วมกัน {len(shared)} หัวข้อ",
                    confidence=0.6,
                )
                db.add(suggestion)

    await db.commit()

    # Count new suggestions
    new_count = len((await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            SuggestedRelation.status == "pending"
        )
    )).scalars().all())

    logger.info(f"Generated {new_count} suggestions for user {user_id}")
    return {"suggestions_count": new_count}
