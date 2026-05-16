"""
ฟ้าเขียนไฟล์นี้ — Unit tests สำหรับ backend/embeddings.py
Phase 0 Review: v11.0.0 Organize Pipeline Refactor
รัน: python -m pytest backend/_test_embeddings.py -v -k "not TestRealAPI"
"""
import hashlib
import os

import numpy as np
import pytest

from backend import embeddings


# ═══════════════════════════════════════════════════════════════
# Helper — รีเซ็ต module-level state ก่อนแต่ละ test (graceful degrade)
# ═══════════════════════════════════════════════════════════════
def _reset_embeddings_state():
    """Reset cached init state เพื่อ test graceful-degrade path."""
    embeddings._init_attempted = False
    embeddings._HAS_GEMINI = False
    embeddings._genai_client = None


# ═══════════════════════════════════════════════════════════════
# TestModuleStructure — ตรวจว่า module มีทุก function ที่ต้องการ
# ═══════════════════════════════════════════════════════════════
class TestModuleStructure:
    """Verify public API exists and is importable."""

    def test_all_expected_functions_exist(self):
        expected = [
            "_init_genai", "is_available", "encode_vector", "decode_vector",
            "embed_text", "embed_texts_batch", "embed_files",
            "_sha256_text", "smoke_test",
        ]
        for name in expected:
            assert hasattr(embeddings, name), f"Missing function: {name}"

    def test_module_has_docstring(self):
        assert embeddings.__doc__ is not None
        assert "Plan reference" in embeddings.__doc__

    def test_config_constants_exist(self):
        assert hasattr(embeddings, "EMBEDDING_MODEL")
        assert hasattr(embeddings, "EMBEDDING_BATCH_SIZE")
        assert hasattr(embeddings, "EMBEDDING_MAX_TEXT_CHARS")
        assert embeddings.EMBEDDING_BATCH_SIZE == 50  # default
        assert embeddings.EMBEDDING_MAX_TEXT_CHARS == 80000  # default


# ═══════════════════════════════════════════════════════════════
# TestEncodeDecode — vector ↔ bytes serialization
# ═══════════════════════════════════════════════════════════════
class TestEncodeDecode:
    """Test vector ↔ bytes serialization roundtrip."""

    def test_float32_roundtrip(self):
        v = np.array([0.1, -0.5, 0.3, 1.0, -1.0], dtype=np.float32)
        b = embeddings.encode_vector(v)
        v2 = embeddings.decode_vector(b)
        assert np.allclose(v, v2), "Values changed after roundtrip"
        assert v2.dtype == np.float32

    def test_float64_coerced_to_float32(self):
        v64 = np.array([0.5, 0.25], dtype=np.float64)
        b = embeddings.encode_vector(v64)
        v32 = embeddings.decode_vector(b)
        assert v32.dtype == np.float32, "float64 input must be stored as float32"

    def test_768d_serialized_size(self):
        """768-dim float32 vector = 768 × 4 bytes = 3072 bytes (Gemini text-embedding-004 dim)."""
        v = np.zeros(768, dtype=np.float32)
        b = embeddings.encode_vector(v)
        assert len(b) == 768 * 4, f"Expected {768*4} bytes, got {len(b)}"

    def test_empty_vector_roundtrip(self):
        v = np.array([], dtype=np.float32)
        b = embeddings.encode_vector(v)
        v2 = embeddings.decode_vector(b)
        assert len(v2) == 0

    def test_negative_values_preserved(self):
        v = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
        b = embeddings.encode_vector(v)
        v2 = embeddings.decode_vector(b)
        assert np.allclose(v, v2)

    def test_high_dim_values_preserved(self):
        """Test 1536-dim (paid tier dimension) roundtrip."""
        rng = np.random.default_rng(42)
        v = rng.standard_normal(1536).astype(np.float32)
        b = embeddings.encode_vector(v)
        v2 = embeddings.decode_vector(b)
        assert np.allclose(v, v2, atol=1e-6)


# ═══════════════════════════════════════════════════════════════
# TestSha256Helper
# ═══════════════════════════════════════════════════════════════
class TestSha256Helper:
    """Test _sha256_text cache key helper."""

    def test_known_hash(self):
        expected = hashlib.sha256(b"test").hexdigest()
        assert embeddings._sha256_text("test") == expected

    def test_unicode_handled(self):
        # Thai text → safe encoding via errors="replace"
        h = embeddings._sha256_text("ทดสอบภาษาไทย")
        assert len(h) == 64, "SHA-256 hex digest must be 64 chars"
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_string(self):
        h = embeddings._sha256_text("")
        assert len(h) == 64

    def test_different_texts_different_hashes(self):
        h1 = embeddings._sha256_text("file A content")
        h2 = embeddings._sha256_text("file B content")
        assert h1 != h2

    def test_same_text_same_hash(self):
        text = "consistent content for cache"
        assert embeddings._sha256_text(text) == embeddings._sha256_text(text)


# ═══════════════════════════════════════════════════════════════
# TestGracefulDegrade — ไม่มี API key → ไม่ crash, คืน None/False
# ═══════════════════════════════════════════════════════════════
class TestGracefulDegrade:
    """Test graceful degrade when no GOOGLE_API_KEY is set."""

    def setup_method(self):
        _reset_embeddings_state()

    def test_no_api_key_is_available_returns_false(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        assert embeddings.is_available() == False

    @pytest.mark.asyncio
    async def test_embed_text_returns_none_no_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        result = await embeddings.embed_text("hello world")
        assert result is None, "Should return None, not crash"

    @pytest.mark.asyncio
    async def test_embed_texts_batch_returns_list_of_nones(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        texts = ["a", "b", "c"]
        result = await embeddings.embed_texts_batch(texts)
        assert result == [None, None, None]

    @pytest.mark.asyncio
    async def test_embed_texts_batch_empty_list(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        result = await embeddings.embed_texts_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_files_empty_list_no_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        result = await embeddings.embed_files([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_embed_files_with_files_no_key_returns_empty(self, monkeypatch):
        """embed_files ต้อง return {} (ไม่ crash) ถ้าไม่มี key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()

        # สร้าง mock file object
        class FakeFile:
            id = "fake-id"
            extracted_text = "some content"
            content_hash = "abc123"
            embedding_vector = None
            embedding_hash = ""
            embedding_model = ""

        result = await embeddings.embed_files([FakeFile()])
        assert result == {}

    @pytest.mark.asyncio
    async def test_smoke_test_no_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()
        info = await embeddings.smoke_test()
        assert info["available"] == False
        assert "error" in info


# ═══════════════════════════════════════════════════════════════
# TestEmbedFilesCacheLogic — cache hit/miss logic (no API needed)
# ═══════════════════════════════════════════════════════════════
class TestEmbedFilesCacheLogic:
    """Test cache hit detection in embed_files (ไม่ต้องใช้ API)."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_decoded_vector(self, monkeypatch):
        """File ที่ embed แล้ว (embedding_vector + hash + model match) → decode จาก BLOB."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()

        v = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        cached_bytes = embeddings.encode_vector(v)
        current_model = embeddings.EMBEDDING_MODEL

        class FakeFile:
            id = "cached-file"
            extracted_text = "some content"
            content_hash = "hash-abc"
            embedding_vector = cached_bytes
            embedding_hash = "hash-abc"
            embedding_model = current_model

        # No API key but has cached vector → should return cached
        result = await embeddings.embed_files([FakeFile()])
        assert "cached-file" in result
        assert np.allclose(result["cached-file"], v)

    @pytest.mark.asyncio
    async def test_cache_miss_on_model_mismatch(self, monkeypatch):
        """Model เปลี่ยน → cache miss → ต้อง re-embed (ไม่มี API = ไม่ return)."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()

        v = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        cached_bytes = embeddings.encode_vector(v)

        class FakeFile:
            id = "model-mismatch"
            extracted_text = "some content"
            content_hash = "hash-xyz"
            embedding_vector = cached_bytes
            embedding_hash = "hash-xyz"
            embedding_model = "old-model-v1"  # ≠ current EMBEDDING_MODEL

        result = await embeddings.embed_files([FakeFile()])
        # Cache miss → needs API → no API → returns {}
        assert "model-mismatch" not in result

    @pytest.mark.asyncio
    async def test_empty_extracted_text_skipped(self, monkeypatch):
        """File ที่ extracted_text ว่าง → ข้ามทั้งหมด ไม่ embed."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        _reset_embeddings_state()

        class EmptyFile:
            id = "empty-file"
            extracted_text = ""
            content_hash = None
            embedding_vector = None
            embedding_hash = ""
            embedding_model = ""

        result = await embeddings.embed_files([EmptyFile()])
        assert result == {}


# ═══════════════════════════════════════════════════════════════
# TestRealAPI — ต้องมี GOOGLE_API_KEY (skip ถ้าไม่มี)
# ═══════════════════════════════════════════════════════════════
@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="needs real GOOGLE_API_KEY")
class TestRealAPI:
    """Integration tests — รันได้เฉพาะตอนมี GOOGLE_API_KEY set."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_float32_768d(self):
        v = await embeddings.embed_text("Hello world — test embedding")
        assert v is not None
        assert v.dtype == np.float32
        assert v.shape == (768,), f"Expected (768,), got {v.shape}"

    @pytest.mark.asyncio
    async def test_embed_text_thai_content(self):
        v = await embeddings.embed_text("สวัสดีโลก ทดสอบภาษาไทย")
        assert v is not None
        assert v.shape == (768,)

    @pytest.mark.asyncio
    async def test_smoke_test_passes(self):
        info = await embeddings.smoke_test()
        assert info["available"] == True
        assert info["sample_dim"] == 768
        # Gemini normalizes vectors → L2 norm ≈ 1.0
        assert 0.95 < info["sample_norm"] < 1.05, f"Norm {info['sample_norm']} unexpected"

    @pytest.mark.asyncio
    async def test_embed_texts_batch_multi(self):
        texts = ["document one", "document two", "document three"]
        results = await embeddings.embed_texts_batch(texts)
        assert len(results) == 3
        for r in results:
            assert r is not None
            assert r.shape == (768,)

    @pytest.mark.asyncio
    async def test_different_texts_different_vectors(self):
        v1 = await embeddings.embed_text("cats and dogs")
        v2 = await embeddings.embed_text("financial quarterly report")
        assert not np.allclose(v1, v2), "Different texts should produce different vectors"
