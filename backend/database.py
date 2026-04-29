"""Database models and setup for Project KEY — MVP v3."""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from datetime import datetime
import uuid
import os

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
    mcp_secret = Column(String, nullable=True, unique=True)     # v5.1 — per-user MCP connector secret
    # v5.9.2 — Stripe subscription
    plan = Column(String, default="free")                       # free, starter
    subscription_status = Column(String, default="free")        # free, starter_active, starter_past_due, starter_canceled
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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

    # v5.9.3 — Locked data (downgrade protection)
    is_locked = Column(Boolean, default=False)
    locked_reason = Column(String, nullable=True)   # exceeds_free_plan_limit, subscription_expired

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

    # ─── v6.0 — Personality fields (5 new columns) ───
    # NULL = ผู้ใช้ยังไม่ตั้งค่าระบบนั้น
    mbti_type = Column(String(8), nullable=True)
    # "INTJ" | "INTJ-A" | "INTJ-T" — suffix -A/-T มาจาก NERIS เท่านั้น
    mbti_source = Column(String(20), nullable=True)
    # "official" | "neris" | "self_report"
    enneagram_data = Column(Text, nullable=True)
    # JSON: {"core": 1-9, "wing": 1-9 | null}
    clifton_top5 = Column(Text, nullable=True)
    # JSON array — order matters (rank 1→5), 1-5 items, ห้ามซ้ำ
    via_top5 = Column(Text, nullable=True)
    # JSON array — order matters, 1-5 items, ห้ามซ้ำ

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

    # v5.9.3 — Locked data (downgrade protection)
    is_locked = Column(Boolean, default=False)
    locked_reason = Column(String, nullable=True)   # exceeds_free_plan_limit, subscription_expired


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
# v6.0 — Personality History (append-only snapshot log)
# ═══════════════════════════════════════════

class PersonalityHistory(Base):
    """บันทึกประวัติทุกครั้งที่ผู้ใช้อัปเดต personality (Q3 ของ user 2026-04-30).

    Append-only — ไม่ update/delete row เก่า. Dedup ที่ service layer (profile.py)
    เพื่อไม่ append เมื่อค่าใหม่ == ค่าล่าสุดของระบบนั้น (กัน table บวม)
    """
    __tablename__ = "personality_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    system = Column(String, nullable=False)
    # "mbti" | "enneagram" | "clifton" | "via"
    data_json = Column(Text, nullable=False)
    # JSON snapshot — ถ้า user clear field จะเก็บเป็น {"cleared": true}
    source = Column(String, default="user_update")
    # "user_update" (เว็บไซต์) | "mcp_update" (Claude/Antigravity ผ่าน MCP)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


# ═══════════════════════════════════════════
# v5.5 — Context Memory (Cross-Platform)
# ═══════════════════════════════════════════

class ContextMemory(Base):
    """Persistent context that follows the user across AI platforms.
    
    Enables cross-platform continuity: save context on Claude,
    load it on Antigravity or ChatGPT. Supports smart merge,
    auto-archive, and pinning.
    """
    __tablename__ = "context_memories"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Content
    title = Column(String, nullable=False)
    summary = Column(Text, default="")              # Auto-generated from AI
    content = Column(Text, nullable=False)

    # Classification
    context_type = Column(String, default="conversation")  # conversation, project, task, note
    platform = Column(String, default="unknown")           # claude, antigravity, chatgpt, web, unknown
    tags = Column(Text, default="[]")                      # JSON array

    # State
    is_active = Column(Boolean, default=True)       # False = archived
    is_pinned = Column(Boolean, default=False)      # Max 3 per user

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # Relations
    related_file_ids = Column(Text, default="[]")   # JSON array of file_id
    parent_id = Column(String, nullable=True)       # Chain contexts together


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


class WebhookLog(Base):
    """v5.9.2 — Stripe webhook event log for idempotency."""
    __tablename__ = "webhook_logs"
    id = Column(String, primary_key=True, default=gen_id)
    event_id = Column(String, unique=True, nullable=False)      # Stripe event ID (evt_xxx)
    event_type = Column(String, nullable=False)                  # e.g. checkout.session.completed
    stripe_object_id = Column(String, nullable=True)             # e.g. sub_xxx or cs_xxx
    status = Column(String, default="processed")                 # processed, error
    error_message = Column(Text, default="")
    processed_at = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    """v5.9.3 — Track monthly usage for quota enforcement."""
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)       # ai_summary, export, refresh
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """v5.9.3 — Audit log for tracking important system events."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    event_type = Column(String, nullable=False)      # plan_changed, usage_limit_reached, file_locked, etc.
    old_value = Column(Text, default="")
    new_value = Column(Text, default="")
    triggered_by = Column(String, default="system")   # user, stripe_webhook, system, admin
    created_at = Column(DateTime, default=datetime.utcnow)


# Async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables + run safe migrations.
    
    SAFETY RULES for future migrations:
    1. NEVER drop tables or columns — always ADD, never remove
    2. NEVER rename columns — add new + copy data if needed
    3. Auto-backup runs before every migration
    4. All migrations are idempotent (safe to re-run)
    5. Test locally before deploying to production
    """
    # Step 1: Create any missing tables (checkfirst=True is SQLAlchemy default — safe)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Step 2: Run safe column migrations
    import aiosqlite
    import shutil
    from datetime import datetime as dt
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    if not os.path.exists(db_path):
        print("✅ DB: Fresh database — no migration needed")
        return

    # Auto-backup before any migration
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"projectkey_{dt.utcnow().strftime('%Y%m%d_%H%M%S')}.db")
    try:
        shutil.copy2(db_path, backup_path)
        # Keep only last 5 backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        for old in backups[:-5]:
            os.remove(os.path.join(backup_dir, old))
        print(f"✅ DB Backup: {backup_path}")
    except Exception as e:
        print(f"⚠️ DB Backup failed (non-fatal): {e}")

    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            migrated = False

            # v5.0 Migration — Auth columns
            if "email" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN email TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
                migrated = True
                print("  → Added: email, password_hash, is_active")

            # v5.1 Migration — Per-user MCP secret
            if "mcp_secret" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN mcp_secret TEXT")
                migrated = True
                print("  → Added: mcp_secret")
                # Generate secrets for existing users
                import secrets as _secrets
                cursor2 = await db.execute("SELECT id FROM users")
                for row in await cursor2.fetchall():
                    secret = _secrets.token_urlsafe(32)
                    await db.execute("UPDATE users SET mcp_secret = ? WHERE id = ?", (secret, row[0]))
                print("  → Generated MCP secrets for existing users")

            # v5.9.2 Migration — Stripe subscription fields
            if "plan" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
                await db.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'free'")
                await db.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN stripe_price_id TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN current_period_start TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN current_period_end TEXT")
                await db.execute("ALTER TABLE users ADD COLUMN cancel_at_period_end BOOLEAN DEFAULT 0")
                await db.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
                migrated = True
                print("  → Added: plan, subscription_status, stripe_*, period dates, cancel_at_period_end, updated_at")

            # v5.9.3 — Locked data columns for files
            cursor = await db.execute("PRAGMA table_info(files)")
            file_columns = [row[1] for row in await cursor.fetchall()]
            if "is_locked" not in file_columns:
                await db.execute("ALTER TABLE files ADD COLUMN is_locked BOOLEAN DEFAULT 0")
                await db.execute("ALTER TABLE files ADD COLUMN locked_reason TEXT")
                migrated = True
                print("  → Added: files.is_locked, files.locked_reason")

            # v5.9.3 — Locked data columns for context_packs
            cursor = await db.execute("PRAGMA table_info(context_packs)")
            pack_columns = [row[1] for row in await cursor.fetchall()]
            if "is_locked" not in pack_columns:
                await db.execute("ALTER TABLE context_packs ADD COLUMN is_locked BOOLEAN DEFAULT 0")
                await db.execute("ALTER TABLE context_packs ADD COLUMN locked_reason TEXT")
                migrated = True
                print("  → Added: context_packs.is_locked, context_packs.locked_reason")

            # v6.0 — Personality fields ใน user_profiles (PRD: 4 ระบบ + history)
            # ⚠️ ดู table user_profiles ไม่ใช่ users — เคยมี migration error เพราะดูผิด table
            cursor = await db.execute("PRAGMA table_info(user_profiles)")
            profile_columns = [row[1] for row in await cursor.fetchall()]
            if "mbti_type" not in profile_columns:
                await db.execute("ALTER TABLE user_profiles ADD COLUMN mbti_type TEXT")
                await db.execute("ALTER TABLE user_profiles ADD COLUMN mbti_source TEXT")
                await db.execute("ALTER TABLE user_profiles ADD COLUMN enneagram_data TEXT")
                await db.execute("ALTER TABLE user_profiles ADD COLUMN clifton_top5 TEXT")
                await db.execute("ALTER TABLE user_profiles ADD COLUMN via_top5 TEXT")
                migrated = True
                print("  → Added: user_profiles.mbti_type, mbti_source, enneagram_data, clifton_top5, via_top5")

            # v6.0 — composite index บน personality_history (table ถูกสร้างโดย create_all แล้ว)
            # CREATE INDEX IF NOT EXISTS = idempotent + safe re-run
            try:
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_personality_history_user_system "
                    "ON personality_history(user_id, system, recorded_at DESC)"
                )
            except Exception as e:
                print(f"  ⚠️ personality_history index creation warning: {e}")

            if migrated:
                await db.commit()
                print("✅ DB Migration: completed successfully")
            else:
                print("✅ DB: Schema up to date — no migration needed")
    except Exception as e:
        print(f"❌ DB Migration error: {e}")


async def get_db():
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
