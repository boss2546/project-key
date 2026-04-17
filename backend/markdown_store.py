"""
Markdown-first summary layer (inspired by memsearch).
Summaries are stored as .md files on disk — human-readable and editable.
The DB stores metadata, but the .md file is the source of truth.

Reference: memsearch by Zilliz
- Markdown as source of truth
- YAML frontmatter + structured markdown body
- Human-editable, version-controllable
"""
import os
import json
import yaml
import logging
from datetime import datetime

from .config import BASE_DIR

logger = logging.getLogger(__name__)

SUMMARIES_DIR = os.path.join(BASE_DIR, "summaries")
os.makedirs(SUMMARIES_DIR, exist_ok=True)


def write_summary_md(
    file_id: str,
    filename: str,
    filetype: str,
    cluster_title: str,
    importance_score: int,
    importance_label: str,
    is_primary: bool,
    summary_text: str,
    key_topics: list,
    key_facts: list,
    why_important: str,
    suggested_usage: str,
    uploaded_at: str = ""
) -> str:
    """
    Write a structured .md summary file to disk.
    Returns the path to the created file.
    """
    # Build YAML frontmatter
    frontmatter = {
        "file_id": file_id,
        "original_filename": filename,
        "filetype": filetype,
        "cluster": cluster_title,
        "importance_score": importance_score,
        "importance_label": importance_label,
        "is_primary_candidate": is_primary,
        "uploaded_at": uploaded_at or datetime.utcnow().isoformat() + "Z"
    }

    # Build markdown body
    body_parts = []

    body_parts.append(f"# Summary\n\n{summary_text}\n")

    if key_topics:
        body_parts.append("# Key Topics\n")
        for topic in key_topics:
            body_parts.append(f"- {topic}")
        body_parts.append("")

    if key_facts:
        body_parts.append("# Key Facts\n")
        for fact in key_facts:
            body_parts.append(f"- {fact}")
        body_parts.append("")

    if why_important:
        body_parts.append(f"# Why This File Matters\n\n{why_important}\n")

    if suggested_usage:
        body_parts.append(f"# Suggested Usage\n\n{suggested_usage}\n")

    # Combine frontmatter + body
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    md_content = f"---\n{yaml_str}---\n\n" + "\n".join(body_parts)

    # Write to file
    safe_name = _safe_filename(filename)
    md_path = os.path.join(SUMMARIES_DIR, f"{safe_name}.summary.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    logger.info(f"Written summary: {md_path}")
    return md_path


def read_summary_md(filename: str) -> dict | None:
    """Read a summary .md file and parse frontmatter + body."""
    safe_name = _safe_filename(filename)
    md_path = os.path.join(SUMMARIES_DIR, f"{safe_name}.summary.md")

    if not os.path.exists(md_path):
        return None

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "path": md_path}
            except yaml.YAMLError:
                pass

    return {"frontmatter": {}, "body": content, "path": md_path}


def list_all_summaries() -> list:
    """List all summary .md files."""
    summaries = []
    if os.path.exists(SUMMARIES_DIR):
        for f in os.listdir(SUMMARIES_DIR):
            if f.endswith('.summary.md'):
                path = os.path.join(SUMMARIES_DIR, f)
                data = read_summary_md(f.replace('.summary.md', ''))
                if data:
                    summaries.append(data)
    return summaries


def _safe_filename(name: str) -> str:
    """Make a filename safe for filesystem use."""
    # Remove extension and dangerous chars
    base = os.path.splitext(name)[0]
    return "".join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in base)
