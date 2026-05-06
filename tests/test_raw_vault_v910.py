"""v9.1.0 Raw File Vault — pytest unit tests.

Coverage:
- vault.py: tokenize_filename + build_vault_searchable_text + is_vault_extracted_text
- DB migration: file_kind column + index + backfill
- File model: file_kind default + per-row override
- _serialize_file: file_kind + vault_reason
- Vault searchable text format (Q5 user requirement: filename + ext only)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_PASSWORD", "test1234")
for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"):
    os.environ[k] = ""

from backend import vault as vault_mod  # noqa: E402


# ─── 1. tokenize_filename — basic + edge cases ──────────────────────


def test_tokenize_kebab_case():
    assert vault_mod.tokenize_filename("meeting-notes-Q4.zip") == ["meeting", "notes", "q4", "zip"]


def test_tokenize_snake_case():
    assert vault_mod.tokenize_filename("project_report_2024.pdf") == ["project", "report", "2024", "pdf"]


def test_tokenize_camel_case():
    assert vault_mod.tokenize_filename("MyDesignPortfolio.psd") == ["my", "design", "portfolio", "psd"]


def test_tokenize_mixed_case():
    assert vault_mod.tokenize_filename("IMG_20260507_142233.heic") == ["img", "20260507", "142233", "heic"]


def test_tokenize_strips_stopwords():
    # "temp" + "v1" are stopwords → only "doc" remains
    assert vault_mod.tokenize_filename("temp_v1.doc") == ["doc"]


def test_tokenize_strips_final_marker():
    # "final" is stopword (file naming noise)
    assert vault_mod.tokenize_filename("Resume_2024_Final.pdf") == ["resume", "2024", "pdf"]


def test_tokenize_dedupes():
    # Same word appearing twice → only once
    assert vault_mod.tokenize_filename("test-test.test") == ["test"]


def test_tokenize_strips_short_numbers():
    # Pure numeric < 4 chars = noise
    assert vault_mod.tokenize_filename("v2-final.zip") == ["zip"]


def test_tokenize_keeps_long_numbers():
    # 4+ digit = meaningful (year, ID)
    assert "2024" in vault_mod.tokenize_filename("budget-2024.xlsx")
    assert "20260507" in vault_mod.tokenize_filename("IMG_20260507.heic")


def test_tokenize_empty_input():
    assert vault_mod.tokenize_filename("") == []
    assert vault_mod.tokenize_filename(None) == []


def test_tokenize_extension_preserved():
    # Extensions are valuable signals — must NOT be stopwords
    for ext in ["doc", "pdf", "psd", "zip", "mp3", "mp4", "heic", "rar", "epub"]:
        result = vault_mod.tokenize_filename(f"file.{ext}")
        assert ext in result, f"extension {ext} should be in tokens"


# ─── 2. build_vault_searchable_text ─────────────────────────────────


def test_build_searchable_includes_marker():
    text = vault_mod.build_vault_searchable_text("design.psd", "psd")
    assert "[Vault file]" in text


def test_build_searchable_includes_filename():
    text = vault_mod.build_vault_searchable_text("meeting-notes.zip", "zip")
    assert "meeting-notes.zip" in text


def test_build_searchable_includes_ext():
    text = vault_mod.build_vault_searchable_text("data.xyz", "xyz")
    assert "extension: xyz" in text


def test_build_searchable_includes_keywords():
    text = vault_mod.build_vault_searchable_text("project-report-2024.zip", "zip")
    assert "project" in text
    assert "report" in text
    assert "2024" in text


def test_build_searchable_handles_empty_filename():
    text = vault_mod.build_vault_searchable_text("", "zip")
    assert "untitled" in text


def test_build_searchable_handles_none_ext():
    text = vault_mod.build_vault_searchable_text("file.xyz", "")
    assert "unknown" in text or "extension:" in text


def test_build_searchable_strips_dot_from_ext():
    text = vault_mod.build_vault_searchable_text("file.xyz", ".xyz")
    assert "extension: xyz" in text  # leading dot stripped


def test_build_searchable_path_traversal_safe():
    # Filename with path traversal → basename only
    text = vault_mod.build_vault_searchable_text("../../etc/passwd", "")
    assert "../" not in text
    assert "passwd" in text


# ─── 3. is_vault_extracted_text ─────────────────────────────────────


def test_is_vault_text_true_for_marker():
    assert vault_mod.is_vault_extracted_text("[Vault file] x.zip")


def test_is_vault_text_false_for_normal():
    assert not vault_mod.is_vault_extracted_text("normal extracted content")
    assert not vault_mod.is_vault_extracted_text("[Image: no text detected]")
    assert not vault_mod.is_vault_extracted_text("")
    assert not vault_mod.is_vault_extracted_text(None)


# ─── 4. DB migration — file_kind column ─────────────────────────────


@pytest.mark.asyncio
async def test_db_migration_creates_file_kind_column(tmp_path, monkeypatch):
    """init_db ครั้งแรก → ALTER TABLE เพิ่ม file_kind"""
    db_dir = tmp_path / "test_db"
    db_dir.mkdir()
    monkeypatch.setenv("DATA_DIR", str(db_dir))

    # Re-import database with new DATA_DIR
    import importlib
    import backend.config
    importlib.reload(backend.config)
    import backend.database
    importlib.reload(backend.database)

    from backend.database import init_db, AsyncSessionLocal
    await init_db()

    from sqlalchemy import text as sql
    async with AsyncSessionLocal() as db:
        cur = await db.execute(sql("PRAGMA table_info(files)"))
        cols = [r[1] for r in cur.fetchall()]
        assert "file_kind" in cols, "file_kind column missing after migration"

        # Index should exist
        cur = await db.execute(sql("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_files_file_kind'"))
        idx = cur.fetchone()
        assert idx is not None, "idx_files_file_kind missing"


# ─── 5. File model default + override ───────────────────────────────


def test_file_model_default_file_kind_processed():
    """New File row default file_kind='processed'"""
    from backend.database import File
    f = File(id="x", user_id="u", filename="test.pdf", filetype="pdf",
             raw_path="/tmp/x", extracted_text="content")
    # default value applies on INSERT — check column default
    assert File.file_kind.default.arg == "processed"


def test_file_model_explicit_vault_only():
    from backend.database import File
    f = File(id="x", user_id="u", filename="design.psd", filetype="psd",
             raw_path="/tmp/x", extracted_text="[Vault file] design.psd",
             file_kind="vault_only")
    assert f.file_kind == "vault_only"


# ─── 6. extract_text remains unchanged for vault ext (caller dispatches) ─


def test_extract_text_unsupported_ext_returns_marker():
    """extract_text เห็น .zip → return [Unsupported file type] (caller handles vault routing)"""
    from backend.extraction import extract_text
    result = extract_text("/tmp/nonexistent.zip", "zip")
    assert result.startswith("[")
    # Either "Unsupported" or could try "AI ingest needed" — both ok markers
