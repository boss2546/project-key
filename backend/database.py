"""Database models and setup for Project KEY."""
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
    name = Column(String, default="Personal Workspace")
    created_at = Column(DateTime, default=datetime.utcnow)
    files = relationship("File", back_populates="owner")


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
