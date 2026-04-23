"""Database models and setup for Project KEY — MVP v3."""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from datetime import datetime
import uuid

from .config import DATABASE_URL

Base = declarative_base()


def gen_id():
    return str(uuid.uuid4())[:12]


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, default="User")
    email = Column(String, unique=True, nullable=True)         # v5.0 — nullable for legacy default-user
    password_hash = Column(String, nullable=True)               # v5.0 — nullable for legacy
    is_active = Column(Boolean, default=True)                   # v5.0
    created_at = Column(DateTime, default=datetime.utcnow)
    files = relationship("File", back_populates="owner")
    profile = relationship("UserProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    raw_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    extracted_text = Column(Text, default="")
    processing_status = Column(String, default="uploaded")  # uploaded, processing, organized, ready, error

    # v3 — Extended metadata
    tags = Column(Text, default="[]")                  # JSON array of tags
    aliases = Column(Text, default="[]")               # JSON array of aliases
    sensitivity = Column(String, default="normal")     # normal, sensitive, confidential
    freshness = Column(String, default="current")      # current, aging, stale
    source_of_truth = Column(Boolean, default=False)   # Is this the authoritative source?
    version = Column(String, default="1.0")

    owner = relationship("User", back_populates="files")
    insight = relationship("FileInsight", uselist=False, back_populates="file", cascade="all, delete-orphan")
    summary = relationship("FileSummary", uselist=False, back_populates="file", cascade="all, delete-orphan")
    cluster_maps = relationship("FileClusterMap", back_populates="file", cascade="all, delete-orphan")


class Cluster(Base):
    __tablename__ = "clusters"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    file_maps = relationship("FileClusterMap", back_populates="cluster", cascade="all, delete-orphan")


class FileClusterMap(Base):
    __tablename__ = "file_cluster_map"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("files.id"), nullable=False)
    cluster_id = Column(String, ForeignKey("clusters.id"), nullable=False)
    relevance_score = Column(Float, default=1.0)

    file = relationship("File", back_populates="cluster_maps")
    cluster = relationship("Cluster", back_populates="file_maps")


class FileInsight(Base):
    __tablename__ = "file_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("files.id"), unique=True, nullable=False)
    importance_score = Column(Integer, default=50)
    importance_label = Column(String, default="medium")  # high, medium, low
    is_primary_candidate = Column(Boolean, default=False)
    why_important = Column(Text, default="")

    file = relationship("File", back_populates="insight")


class FileSummary(Base):
    __tablename__ = "file_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("files.id"), unique=True, nullable=False)
    md_path = Column(String, default="")  # Path to .md summary file on disk
    summary_text = Column(Text, default="")
    key_topics = Column(Text, default="[]")  # JSON array
    key_facts = Column(Text, default="[]")   # JSON array
    why_important = Column(Text, default="")
    suggested_usage = Column(Text, default="")

    file = relationship("File", back_populates="summary")


class ChatQuery(Base):
    __tablename__ = "chat_queries"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, default="")
    selected_cluster_ids = Column(Text, default="[]")  # JSON
    selected_file_ids = Column(Text, default="[]")      # JSON
    retrieval_modes = Column(Text, default="{}")          # JSON
    reasoning = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    injection_log = relationship("ContextInjectionLog", uselist=False, back_populates="chat_query", cascade="all, delete-orphan")


# ═══════════════════════════════════════════
# MVP v2 — Models
# ═══════════════════════════════════════════

class UserProfile(Base):
    """User profile — lets AI understand the file owner."""
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    identity_summary = Column(Text, default="")       # ฉันเป็นใคร
    goals = Column(Text, default="")                   # เป้าหมายของฉัน
    working_style = Column(Text, default="")           # สไตล์การทำงาน/เรียน
    preferred_output_style = Column(Text, default="")  # ต้องการคำตอบแบบไหน
    background_context = Column(Text, default="")      # บริบทสำคัญ
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class ContextPack(Base):
    """High-level context distilled from multiple files/collections."""
    __tablename__ = "context_packs"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)          # profile, study, work, project
    title = Column(String, nullable=False)
    summary_text = Column(Text, default="")
    md_path = Column(String, default="")
    source_file_ids = Column(Text, default="[]")   # JSON array
    source_cluster_ids = Column(Text, default="[]") # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContextInjectionLog(Base):
    """Log of what context was injected for each chat query."""
    __tablename__ = "context_injection_logs"
    id = Column(String, primary_key=True, default=gen_id)
    chat_query_id = Column(String, ForeignKey("chat_queries.id"), nullable=False)
    profile_used = Column(Boolean, default=False)
    context_pack_ids = Column(Text, default="[]")  # JSON
    file_ids = Column(Text, default="[]")           # JSON
    cluster_ids = Column(Text, default="[]")        # JSON
    injection_summary = Column(Text, default="")    # Human-readable summary
    retrieval_reason = Column(Text, default="")
    # v3 — graph injection tracking
    node_ids_used = Column(Text, default="[]")      # JSON — graph nodes used
    edge_ids_used = Column(Text, default="[]")      # JSON — graph edges used
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_query = relationship("ChatQuery", back_populates="injection_log")


# ═══════════════════════════════════════════
# MVP v3 — Knowledge Graph Models
# ═══════════════════════════════════════════

class NoteObject(Base):
    """A knowledge object — notes, entities, concepts extracted from files."""
    __tablename__ = "note_objects"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)        # note, entity, concept, person, project, tag
    title = Column(String, nullable=False)
    md_path = Column(String, default="")
    summary = Column(Text, default="")
    aliases = Column(Text, default="[]")          # JSON array — alternative names
    metadata_json = Column(Text, default="{}")    # JSON — flexible metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphNode(Base):
    """A node in the knowledge graph — projection of any object."""
    __tablename__ = "graph_nodes"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    object_type = Column(String, nullable=False)   # source_file, note, entity, tag, context_pack, project, person, cluster
    object_id = Column(String, nullable=False)      # FK to the source object
    label = Column(String, nullable=False)           # Display label
    node_family = Column(String, default="note")     # Visual grouping
    importance_score = Column(Float, default=0.5)    # 0-1
    freshness_score = Column(Float, default=1.0)     # 0-1 (1=fresh, 0=stale)
    pinned = Column(Boolean, default=False)
    metadata_json = Column(Text, default="{}")       # Flexible metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class GraphEdge(Base):
    """A typed, weighted relationship between two graph nodes."""
    __tablename__ = "graph_edges"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    source_node_id = Column(String, ForeignKey("graph_nodes.id"), nullable=False)
    target_node_id = Column(String, ForeignKey("graph_nodes.id"), nullable=False)
    edge_type = Column(String, nullable=False)        # explicit_link, has_tag, mentions, derived_from, semantically_related, same_entity, used_together, contains
    weight = Column(Float, default=1.0)                # Edge strength 0-1
    confidence = Column(Float, default=1.0)            # How confident is this relation 0-1
    provenance = Column(String, default="system")      # system, user, llm
    evidence_text = Column(Text, default="")           # Why this relation exists
    created_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.utcnow)

    source_node = relationship("GraphNode", foreign_keys=[source_node_id])
    target_node = relationship("GraphNode", foreign_keys=[target_node_id])


class SuggestedRelation(Base):
    """AI-suggested relations that await user confirmation."""
    __tablename__ = "suggested_relations"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    source_node_id = Column(String, ForeignKey("graph_nodes.id"), nullable=False)
    target_node_id = Column(String, ForeignKey("graph_nodes.id"), nullable=False)
    relation_type = Column(String, nullable=False)
    suggestion_reason = Column(Text, default="")      # Why is this suggested
    confidence = Column(Float, default=0.5)            # 0-1
    status = Column(String, default="pending")         # pending, accepted, dismissed
    created_at = Column(DateTime, default=datetime.utcnow)

    source_node = relationship("GraphNode", foreign_keys=[source_node_id])
    target_node = relationship("GraphNode", foreign_keys=[target_node_id])


class GraphLens(Base):
    """Saved graph view configurations / filters."""
    __tablename__ = "graph_lenses"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="custom")            # theme, bridge, foundation, local, custom
    filter_json = Column(Text, default="{}")           # JSON — node/edge filters
    layout_json = Column(Text, default="{}")           # JSON — layout preferences
    created_at = Column(DateTime, default=datetime.utcnow)


class CanvasObject(Base):
    """Canvas workspace — future-ready for v3.1."""
    __tablename__ = "canvas_objects"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="Untitled Canvas")
    json_payload = Column(Text, default="{}")          # JSON — full canvas state
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════
# MVP v4 — PDB Connector Layer Models
# ═══════════════════════════════════════════

class MCPToken(Base):
    """Bearer token for MCP connector access."""
    __tablename__ = "mcp_tokens"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)  # SHA-256 hash
    label = Column(String, default="Default Token")
    scope = Column(String, default="read-only")               # read-only only in v4
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class MCPUsageLog(Base):
    """Log of MCP tool calls for traceability."""
    __tablename__ = "mcp_usage_logs"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_id = Column(String, ForeignKey("mcp_tokens.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    request_summary = Column(Text, default="")
    status = Column(String, default="success")          # success, error
    latency_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# Async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
