"""Relations service — backlinks, outgoing links, and relationship management."""
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import gen_id, GraphNode, GraphEdge, SuggestedRelation

logger = logging.getLogger(__name__)


async def get_backlinks(db: AsyncSession, node_id: str):
    """Get all nodes that link TO this node (incoming edges)."""
    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.target_node_id == node_id)
    )).scalars().all()

    results = []
    for e in edges:
        source = (await db.execute(
            select(GraphNode).where(GraphNode.id == e.source_node_id)
        )).scalar_one_or_none()
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
    """Get all nodes that this node links TO (outgoing edges)."""
    edges = (await db.execute(
        select(GraphEdge).where(GraphEdge.source_node_id == node_id)
    )).scalars().all()

    results = []
    for e in edges:
        target = (await db.execute(
            select(GraphNode).where(GraphNode.id == e.target_node_id)
        )).scalar_one_or_none()
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
    """Get suggested relations awaiting user action."""
    suggestions = (await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == user_id,
            SuggestedRelation.status == status
        )
    )).scalars().all()

    results = []
    for s in suggestions:
        source = (await db.execute(
            select(GraphNode).where(GraphNode.id == s.source_node_id)
        )).scalar_one_or_none()
        target = (await db.execute(
            select(GraphNode).where(GraphNode.id == s.target_node_id)
        )).scalar_one_or_none()

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
    file_nodes = [n for n in nodes if n.object_type == "source_file"]
    tag_map = {}  # node_id → set of connected tag_ids
    for fn in file_nodes:
        tags = set()
        fn_edges = (await db.execute(
            select(GraphEdge).where(
                GraphEdge.source_node_id == fn.id,
                GraphEdge.edge_type == "has_tag"
            )
        )).scalars().all()
        for e in fn_edges:
            tags.add(e.target_node_id)
        tag_map[fn.id] = tags

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
