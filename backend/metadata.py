"""Metadata enrichment service — extends file/object metadata using LLM analysis."""
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import File, FileSummary
from .llm import call_llm

logger = logging.getLogger(__name__)


async def enrich_file_metadata(db: AsyncSession, file_id: str):
    """Use LLM to enrich a file's metadata: tags, sensitivity, aliases, freshness."""
    file = (await db.execute(
        select(File).where(File.id == file_id)
    )).scalar_one_or_none()
    if not file:
        return None

    summary = (await db.execute(
        select(FileSummary).where(FileSummary.file_id == file_id)
    )).scalar_one_or_none()

    text_for_analysis = ""
    if summary and summary.summary_text:
        text_for_analysis = summary.summary_text[:1500]
    elif file.extracted_text:
        text_for_analysis = file.extracted_text[:1500]

    if not text_for_analysis.strip():
        return None

    prompt = f"""วิเคราะห์เอกสารต่อไปนี้แล้วสร้าง metadata ในรูป JSON:

ชื่อไฟล์: {file.filename}
ประเภท: {file.filetype}
เนื้อหา:
{text_for_analysis}

ตอบเป็น JSON object เท่านั้น:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "aliases": ["ชื่ออื่นที่อ้างถึงเอกสารนี้ได้"],
  "sensitivity": "normal|sensitive|confidential",
  "source_of_truth": true|false,
  "summary_category": "research|study|work|personal|reference|creative"
}}

กฎ:
- tags ไม่เกิน 5 tags ภาษาไทยหรืออังกฤษ
- sensitivity: normal=ทั่วไป, sensitive=ข้อมูลส่วนบุคคล, confidential=ความลับ
- source_of_truth: true ถ้าเป็นเวอร์ชันหลัก/เอกสารอ้างอิงต้นฉบับ
- aliases: ชื่อย่อหรือคำที่คนจะเรียกเอกสารนี้

ตอบ JSON เท่านั้น:"""

    try:
        response = await call_llm(prompt, temperature=0.1)
        result = response.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        metadata = json.loads(result)

        # Update file with enriched metadata
        file.tags = json.dumps(metadata.get("tags", []))
        file.aliases = json.dumps(metadata.get("aliases", []))
        file.sensitivity = metadata.get("sensitivity", "normal")
        file.source_of_truth = metadata.get("source_of_truth", False)

        # Calculate freshness based on upload date
        age_days = (datetime.utcnow() - file.uploaded_at).days
        if age_days <= 7:
            file.freshness = "current"
        elif age_days <= 30:
            file.freshness = "aging"
        else:
            file.freshness = "stale"

        await db.commit()

        logger.info(f"Enriched metadata for file {file.filename}")
        return {
            "file_id": file_id,
            "tags": metadata.get("tags", []),
            "aliases": metadata.get("aliases", []),
            "sensitivity": file.sensitivity,
            "freshness": file.freshness,
            "source_of_truth": file.source_of_truth,
        }

    except Exception as e:
        logger.warning(f"Metadata enrichment failed for {file_id}: {e}")
        return None


async def enrich_all_files(db: AsyncSession, user_id: str):
    """Enrich metadata for all files of a user."""
    files = (await db.execute(
        select(File).where(File.user_id == user_id)
    )).scalars().all()

    enriched = 0
    for f in files:
        result = await enrich_file_metadata(db, f.id)
        if result:
            enriched += 1

    logger.info(f"Enriched metadata for {enriched}/{len(files)} files")
    return {"enriched": enriched, "total": len(files)}


async def get_file_metadata(db: AsyncSession, file_id: str):
    """Get enriched metadata for a file."""
    file = (await db.execute(
        select(File).where(File.id == file_id)
    )).scalar_one_or_none()
    if not file:
        return None

    return {
        "file_id": file.id,
        "filename": file.filename,
        "filetype": file.filetype,
        "tags": json.loads(file.tags or "[]"),
        "aliases": json.loads(file.aliases or "[]"),
        "sensitivity": file.sensitivity,
        "freshness": file.freshness,
        "source_of_truth": file.source_of_truth,
        "version": file.version,
        "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None,
    }


async def update_file_metadata(db: AsyncSession, file_id: str, updates: dict):
    """Manually update file metadata fields."""
    file = (await db.execute(
        select(File).where(File.id == file_id)
    )).scalar_one_or_none()
    if not file:
        return None

    if "tags" in updates:
        file.tags = json.dumps(updates["tags"])
    if "aliases" in updates:
        file.aliases = json.dumps(updates["aliases"])
    if "sensitivity" in updates:
        file.sensitivity = updates["sensitivity"]
    if "source_of_truth" in updates:
        file.source_of_truth = updates["source_of_truth"]
    if "freshness" in updates:
        file.freshness = updates["freshness"]
    if "version" in updates:
        file.version = updates["version"]

    await db.commit()

    return await get_file_metadata(db, file_id)
