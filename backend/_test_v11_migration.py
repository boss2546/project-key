"""
ฟ้าเขียนไฟล์นี้ — Unit tests สำหรับ v11.0.0 Schema Migration (database.py)
Phase 0 Review: v11.0.0 Organize Pipeline Refactor

Strategy: สร้าง legacy SQLite DB ด้วย aiosqlite โดยตรง (ไม่ผ่าน init_db)
→ ทดสอบว่า v11 migration SQL เพิ่ม column ได้ครบ, idempotent, ค่า default ถูกต้อง

รัน: python -m pytest backend/_test_v11_migration.py -v
"""
import os
import tempfile
import asyncio
import aiosqlite
import pytest
import pytest_asyncio


# ═══════════════════════════════════════════════════════════════
# LEGACY SCHEMA DDL — สถานะก่อน v11.0.0 (v10.0.14-equivalent)
# เอาเฉพาะ 4 ตารางที่ v11 migration แตะ
# ═══════════════════════════════════════════════════════════════

LEGACY_TABLES_DDL = """
CREATE TABLE IF NOT EXISTS files (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    filename      TEXT NOT NULL,
    filetype      TEXT NOT NULL,
    raw_path      TEXT NOT NULL,
    extracted_text TEXT DEFAULT '',
    content_hash  TEXT,
    processing_status TEXT DEFAULT 'uploaded'
);

CREATE TABLE IF NOT EXISTS file_summaries (
    id         TEXT PRIMARY KEY,
    file_id    TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    summary    TEXT DEFAULT '',
    tags       TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS clusters (
    id      TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    label   TEXT DEFAULT '',
    summary TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS graph_nodes (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id   TEXT NOT NULL,
    label       TEXT DEFAULT ''
);
"""

# v11.0.0 migration SQL — คัดมาจาก database.py init_db() block
# (เพื่อ test แบบ white-box ว่า SQL ทำงานถูกต้อง independent จาก app startup)
V11_MIGRATION_COLS = {
    "files": [
        ("embedding_vector", "ALTER TABLE files ADD COLUMN embedding_vector BLOB"),
        ("embedding_model",  "ALTER TABLE files ADD COLUMN embedding_model TEXT DEFAULT ''"),
        ("embedding_hash",   "ALTER TABLE files ADD COLUMN embedding_hash TEXT DEFAULT ''"),
    ],
    "file_summaries": [
        ("entities",        "ALTER TABLE file_summaries ADD COLUMN entities TEXT DEFAULT ''"),
        ("relationships",   "ALTER TABLE file_summaries ADD COLUMN relationships TEXT DEFAULT ''"),
        ("schema_version",  "ALTER TABLE file_summaries ADD COLUMN schema_version INTEGER DEFAULT 1"),
    ],
    "clusters": [
        ("method",        "ALTER TABLE clusters ADD COLUMN method TEXT DEFAULT 'llm'"),
        ("centroid",      "ALTER TABLE clusters ADD COLUMN centroid BLOB"),
        ("member_count",  "ALTER TABLE clusters ADD COLUMN member_count INTEGER DEFAULT 0"),
    ],
    "graph_nodes": [
        ("community_id",           "ALTER TABLE graph_nodes ADD COLUMN community_id TEXT DEFAULT ''"),
        ("embedding_centrality",   "ALTER TABLE graph_nodes ADD COLUMN embedding_centrality REAL DEFAULT 0.0"),
    ],
}

V11_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_files_embedding_hash "
    "ON files(embedding_hash)"
)


async def _get_columns(db: aiosqlite.Connection, table: str) -> set[str]:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()
    return {row[1] for row in rows}


async def _run_v11_migration(db: aiosqlite.Connection) -> list[str]:
    """Run v11 ALTER ADD + index. คืน list of 'Added:' messages (เหมือน print ใน production)."""
    added = []
    for table, col_list in V11_MIGRATION_COLS.items():
        existing = await _get_columns(db, table)
        for col_name, sql in col_list:
            if col_name not in existing:
                await db.execute(sql)
                added.append(f"Added: {table}.{col_name}")
    await db.execute(V11_INDEX_SQL)
    await db.commit()
    return added


async def _create_legacy_db(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        for stmt in LEGACY_TABLES_DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()


# ═══════════════════════════════════════════════════════════════
# TestV11MigrationSchema — column presence + defaults
# ═══════════════════════════════════════════════════════════════
class TestV11MigrationSchema:
    """Verify v11 migration adds all 11 columns and index."""

    @pytest.mark.asyncio
    async def test_alter_adds_all_v11_cols_files(self):
        """files: ต้องได้ embedding_vector, embedding_model, embedding_hash."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                added = await _run_v11_migration(db)
                cols = await _get_columns(db, "files")
            assert "embedding_vector" in cols, "files.embedding_vector missing"
            assert "embedding_model" in cols, "files.embedding_model missing"
            assert "embedding_hash" in cols, "files.embedding_hash missing"
            # All 3 should appear in added list
            assert any("embedding_vector" in a for a in added)
            assert any("embedding_model" in a for a in added)
            assert any("embedding_hash" in a for a in added)
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_alter_adds_all_v11_cols_file_summaries(self):
        """file_summaries: ต้องได้ entities, relationships, schema_version."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                cols = await _get_columns(db, "file_summaries")
            assert "entities" in cols, "file_summaries.entities missing"
            assert "relationships" in cols, "file_summaries.relationships missing"
            assert "schema_version" in cols, "file_summaries.schema_version missing"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_alter_adds_all_v11_cols_clusters(self):
        """clusters: ต้องได้ method, centroid, member_count."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                cols = await _get_columns(db, "clusters")
            assert "method" in cols, "clusters.method missing"
            assert "centroid" in cols, "clusters.centroid missing"
            assert "member_count" in cols, "clusters.member_count missing"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_alter_adds_all_v11_cols_graph_nodes(self):
        """graph_nodes: ต้องได้ community_id, embedding_centrality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                cols = await _get_columns(db, "graph_nodes")
            assert "community_id" in cols, "graph_nodes.community_id missing"
            assert "embedding_centrality" in cols, "graph_nodes.embedding_centrality missing"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_total_added_count_is_11(self):
        """Migration ต้อง add ครบ 11 columns ใน 1 run แรก."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                added = await _run_v11_migration(db)
            assert len(added) == 11, f"Expected 11 columns added, got {len(added)}: {added}"
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# TestV11MigrationIdempotency — run 2 ครั้งต้องปลอดภัย
# ═══════════════════════════════════════════════════════════════
class TestV11MigrationIdempotency:
    """Verify migration is safe to re-run (idempotent)."""

    @pytest.mark.asyncio
    async def test_idempotent_rerun_adds_nothing(self):
        """รัน migration 2 ครั้ง → ครั้งที่ 2 ต้องไม่มี 'Added:' messages."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                first_run = await _run_v11_migration(db)
                second_run = await _run_v11_migration(db)
            assert len(first_run) == 11, f"First run should add 11, got {len(first_run)}"
            assert second_run == [], (
                f"Second run must add 0 columns (idempotent), but added: {second_run}"
            )
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_idempotent_columns_still_present_after_rerun(self):
        """หลังรัน 2 ครั้ง ทุก column ยังคงอยู่ครบ."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await _run_v11_migration(db)
                for table, col_list in V11_MIGRATION_COLS.items():
                    cols = await _get_columns(db, table)
                    for col_name, _ in col_list:
                        assert col_name in cols, (
                            f"{table}.{col_name} disappeared after idempotent rerun"
                        )
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# TestV11MigrationDefaults — ค่า default ถูกต้อง
# ═══════════════════════════════════════════════════════════════
class TestV11MigrationDefaults:
    """Verify column default values are correct after migration."""

    @pytest.mark.asyncio
    async def test_embedding_model_default_empty_string(self):
        """files.embedding_model DEFAULT '' → INSERT ไม่ระบุ → ได้ ''."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO files (id, user_id, filename, filetype, raw_path) "
                    "VALUES ('f1', 'u1', 'test.txt', 'txt', '/tmp/test.txt')"
                )
                await db.commit()
                cursor = await db.execute("SELECT embedding_model FROM files WHERE id='f1'")
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == '', f"Expected '' got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_embedding_hash_default_empty_string(self):
        """files.embedding_hash DEFAULT '' → INSERT ไม่ระบุ → ได้ ''."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO files (id, user_id, filename, filetype, raw_path) "
                    "VALUES ('f2', 'u1', 'test2.txt', 'txt', '/tmp/test2.txt')"
                )
                await db.commit()
                cursor = await db.execute("SELECT embedding_hash FROM files WHERE id='f2'")
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == '', f"Expected '' got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_embedding_vector_default_null(self):
        """files.embedding_vector BLOB (no DEFAULT) → INSERT ไม่ระบุ → ได้ NULL."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO files (id, user_id, filename, filetype, raw_path) "
                    "VALUES ('f3', 'u1', 'test3.txt', 'txt', '/tmp/test3.txt')"
                )
                await db.commit()
                cursor = await db.execute("SELECT embedding_vector FROM files WHERE id='f3'")
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] is None, f"Expected NULL BLOB, got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_schema_version_default_1(self):
        """file_summaries.schema_version DEFAULT 1 → INSERT ไม่ระบุ → ได้ 1."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO file_summaries (id, file_id, user_id) "
                    "VALUES ('s1', 'f1', 'u1')"
                )
                await db.commit()
                cursor = await db.execute(
                    "SELECT schema_version FROM file_summaries WHERE id='s1'"
                )
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 1, f"Expected schema_version=1 got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_clusters_method_default_llm(self):
        """clusters.method DEFAULT 'llm' → INSERT ไม่ระบุ → ได้ 'llm'."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO clusters (id, user_id) VALUES ('c1', 'u1')"
                )
                await db.commit()
                cursor = await db.execute("SELECT method FROM clusters WHERE id='c1'")
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 'llm', f"Expected 'llm' got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_clusters_member_count_default_0(self):
        """clusters.member_count DEFAULT 0 → INSERT ไม่ระบุ → ได้ 0."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO clusters (id, user_id) VALUES ('c2', 'u1')"
                )
                await db.commit()
                cursor = await db.execute("SELECT member_count FROM clusters WHERE id='c2'")
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 0, f"Expected 0 got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_embedding_centrality_default_0_0(self):
        """graph_nodes.embedding_centrality DEFAULT 0.0 → INSERT ไม่ระบุ → ได้ 0.0."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO graph_nodes (id, user_id, object_type, object_id) "
                    "VALUES ('g1', 'u1', 'file', 'f1')"
                )
                await db.commit()
                cursor = await db.execute(
                    "SELECT embedding_centrality FROM graph_nodes WHERE id='g1'"
                )
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 0.0, f"Expected 0.0 got {row[0]!r}"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_community_id_default_empty_string(self):
        """graph_nodes.community_id DEFAULT '' → INSERT ไม่ระบุ → ได้ ''."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                await db.execute(
                    "INSERT INTO graph_nodes (id, user_id, object_type, object_id) "
                    "VALUES ('g2', 'u1', 'file', 'f2')"
                )
                await db.commit()
                cursor = await db.execute(
                    "SELECT community_id FROM graph_nodes WHERE id='g2'"
                )
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == '', f"Expected '' got {row[0]!r}"
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# TestV11MigrationLegacyData — legacy rows ต้องไม่หาย
# ═══════════════════════════════════════════════════════════════
class TestV11MigrationLegacyData:
    """Verify existing rows are preserved after migration."""

    @pytest.mark.asyncio
    async def test_legacy_file_row_preserved(self):
        """Row ที่มีก่อน migration ต้องยังอยู่ครบ หลัง ALTER ADD columns."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                # Insert legacy row ก่อน migration
                await db.execute(
                    "INSERT INTO files (id, user_id, filename, filetype, raw_path, extracted_text) "
                    "VALUES ('legacy-1', 'user-abc', 'report.pdf', 'pdf', '/data/report.pdf', "
                    "'Q4 revenue increased 12%')"
                )
                await db.commit()
                # Run migration
                await _run_v11_migration(db)
                # Verify row still exists + original columns intact
                cursor = await db.execute(
                    "SELECT id, user_id, filename, filetype, extracted_text "
                    "FROM files WHERE id='legacy-1'"
                )
                row = await cursor.fetchone()
            assert row is not None, "Legacy row disappeared after migration"
            assert row[0] == 'legacy-1'
            assert row[1] == 'user-abc'
            assert row[2] == 'report.pdf'
            assert row[3] == 'pdf'
            assert row[4] == 'Q4 revenue increased 12%'
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_legacy_row_v11_cols_are_null_or_default(self):
        """Legacy row ก่อน migration → v11 columns ต้องเป็น NULL/default (ไม่ error)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await db.execute(
                    "INSERT INTO files (id, user_id, filename, filetype, raw_path) "
                    "VALUES ('legacy-2', 'user-xyz', 'notes.txt', 'txt', '/data/notes.txt')"
                )
                await db.commit()
                await _run_v11_migration(db)
                cursor = await db.execute(
                    "SELECT embedding_vector, embedding_model, embedding_hash "
                    "FROM files WHERE id='legacy-2'"
                )
                row = await cursor.fetchone()
            assert row is not None
            # embedding_vector is BLOB with no default → NULL for legacy row
            assert row[0] is None, f"Legacy embedding_vector should be NULL, got {row[0]!r}"
            # embedding_model has DEFAULT '' but legacy row got NULL (SQLite ALTER behavior)
            # Both NULL and '' are acceptable legacy states — key check: no crash
            assert row[2] is None or row[2] == '', (
                f"embedding_hash should be NULL or '' for legacy row, got {row[2]!r}"
            )
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_multiple_legacy_rows_all_preserved(self):
        """หลาย rows ต้องทั้งหมดรอดหลัง migration."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                for i in range(5):
                    await db.execute(
                        "INSERT INTO files (id, user_id, filename, filetype, raw_path) "
                        "VALUES (?, ?, ?, 'txt', ?)",
                        (f"file-{i}", "u1", f"file{i}.txt", f"/data/file{i}.txt"),
                    )
                await db.commit()
                await _run_v11_migration(db)
                cursor = await db.execute("SELECT COUNT(*) FROM files")
                row = await cursor.fetchone()
            assert row[0] == 5, f"Expected 5 rows, got {row[0]}"
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# TestV11MigrationIndex — index สร้างได้ + idempotent
# ═══════════════════════════════════════════════════════════════
class TestV11MigrationIndex:
    """Verify idx_files_embedding_hash is created correctly."""

    @pytest.mark.asyncio
    async def test_embedding_hash_index_created(self):
        """idx_files_embedding_hash ต้องมีอยู่หลัง migration."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name='idx_files_embedding_hash'"
                )
                row = await cursor.fetchone()
            assert row is not None, "idx_files_embedding_hash index not found after migration"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_embedding_hash_index_idempotent(self):
        """CREATE INDEX IF NOT EXISTS → ไม่ error เมื่อรัน 2 ครั้ง."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            await _create_legacy_db(path)
            async with aiosqlite.connect(path) as db:
                await _run_v11_migration(db)
                # ต้องไม่ throw exception
                await _run_v11_migration(db)
        finally:
            os.unlink(path)
