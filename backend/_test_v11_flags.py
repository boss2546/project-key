"""
ฟ้าเขียนไฟล์นี้ — Unit tests สำหรับ Feature Flags (backend/config.py)
Phase 0 Review: v11.0.0 Organize Pipeline Refactor

ตรวจสอบ:
  1. Phase flags 3 ตัว default OFF (= False)
  2. Safety flags 2 ตัว default ON (= True)
  3. _env_bool truthy parsing: true/True/TRUE/1/yes/YES → True
  4. _env_bool falsy parsing: false/0/no/''/random/on/2 → False
  5. Numeric configs: default values + env override

รัน: python -m pytest backend/_test_v11_flags.py -v
"""
import os

import pytest


# ═══════════════════════════════════════════════════════════════
# Helper — reload config module ให้สะท้อน monkeypatched env
# (config.py อ่าน os.getenv ตอน import → ต้อง reload เพื่อ test)
# ═══════════════════════════════════════════════════════════════

def _reload_config():
    """Force re-execute backend.config เพื่อ pick up env changes.

    ใช้ importlib.reload() แทน del sys.modules[...] เพราะ:
    - del sys.modules["backend.config"] ไม่ลบ attribute ออกจาก backend package object
    - ดังนั้น `from backend import config` ยังคืน stale reference เดิม
    - importlib.reload() re-executes module code in-place → ค่าทุกตัวอัพเดตทันที
    """
    import importlib
    from backend import config as cfg
    importlib.reload(cfg)
    return cfg


# ═══════════════════════════════════════════════════════════════
# TestModuleStructure — ตรวจว่า config มีทุกอย่างที่ต้องการ
# ═══════════════════════════════════════════════════════════════
class TestConfigModuleStructure:
    """Verify config module exposes all expected flags and helpers."""

    def test_env_bool_helper_exists(self):
        from backend import config
        assert hasattr(config, "_env_bool"), "_env_bool helper not found in config"

    def test_all_phase_flags_exist(self):
        from backend import config
        assert hasattr(config, "USE_HYBRID_CLUSTERING")
        assert hasattr(config, "USE_STRUCTURED_SUMMARY")
        assert hasattr(config, "USE_ENTITY_GRAPH")

    def test_safety_flags_exist(self):
        from backend import config
        assert hasattr(config, "USE_SUMMARY_CACHE")
        assert hasattr(config, "USE_ORGANIZE_CHECKPOINT")

    def test_numeric_configs_exist(self):
        from backend import config
        assert hasattr(config, "EMBEDDING_BATCH_SIZE")
        assert hasattr(config, "HDBSCAN_MIN_CLUSTER_SIZE")
        assert hasattr(config, "UMAP_N_COMPONENTS")
        assert hasattr(config, "SUMMARY_CONCURRENCY")

    def test_phase_flags_are_bool_type(self):
        from backend import config
        assert isinstance(config.USE_HYBRID_CLUSTERING, bool)
        assert isinstance(config.USE_STRUCTURED_SUMMARY, bool)
        assert isinstance(config.USE_ENTITY_GRAPH, bool)

    def test_numeric_configs_are_int_type(self):
        from backend import config
        assert isinstance(config.EMBEDDING_BATCH_SIZE, int)
        assert isinstance(config.HDBSCAN_MIN_CLUSTER_SIZE, int)
        assert isinstance(config.UMAP_N_COMPONENTS, int)
        assert isinstance(config.SUMMARY_CONCURRENCY, int)


# ═══════════════════════════════════════════════════════════════
# TestPhoneFlagsDefaultOff — v11 phase flags ต้อง default OFF
# (ป้องกัน production regression หาก env var ไม่ได้ set)
# ═══════════════════════════════════════════════════════════════
class TestPhaseFlagsDefaultOff:
    """Phase flags must be False when env vars are unset."""

    def setup_method(self):
        # ลบ env vars ก่อนแต่ละ test — แต่ config โหลดแล้วตอน import
        # ใช้ _env_bool โดยตรง (ไม่ต้อง reload module ทั้งหมด)
        pass

    def test_hybrid_clustering_default_false(self, monkeypatch):
        monkeypatch.delenv("USE_HYBRID_CLUSTERING", raising=False)
        cfg = _reload_config()
        assert cfg.USE_HYBRID_CLUSTERING == False, (
            "USE_HYBRID_CLUSTERING ต้อง default False — ถ้า True จะ activate clustering "
            "ใน production ก่อน Phase 1 complete"
        )

    def test_structured_summary_default_false(self, monkeypatch):
        monkeypatch.delenv("USE_STRUCTURED_SUMMARY", raising=False)
        cfg = _reload_config()
        assert cfg.USE_STRUCTURED_SUMMARY == False, (
            "USE_STRUCTURED_SUMMARY ต้อง default False"
        )

    def test_entity_graph_default_false(self, monkeypatch):
        monkeypatch.delenv("USE_ENTITY_GRAPH", raising=False)
        cfg = _reload_config()
        assert cfg.USE_ENTITY_GRAPH == False, (
            "USE_ENTITY_GRAPH ต้อง default False"
        )

    def test_all_three_phase_flags_off_simultaneously(self, monkeypatch):
        """ทั้ง 3 flags ต้อง False พร้อมกัน ไม่ใช่แค่ตัวใดตัวหนึ่ง."""
        monkeypatch.delenv("USE_HYBRID_CLUSTERING", raising=False)
        monkeypatch.delenv("USE_STRUCTURED_SUMMARY", raising=False)
        monkeypatch.delenv("USE_ENTITY_GRAPH", raising=False)
        cfg = _reload_config()
        phase_flags = {
            "USE_HYBRID_CLUSTERING": cfg.USE_HYBRID_CLUSTERING,
            "USE_STRUCTURED_SUMMARY": cfg.USE_STRUCTURED_SUMMARY,
            "USE_ENTITY_GRAPH": cfg.USE_ENTITY_GRAPH,
        }
        on_flags = [k for k, v in phase_flags.items() if v]
        assert on_flags == [], f"Phase flags should all be OFF, but these are ON: {on_flags}"


# ═══════════════════════════════════════════════════════════════
# TestSafetyFlagsDefaultOn — safety flags ต้อง default ON
# ═══════════════════════════════════════════════════════════════
class TestSafetyFlagsDefaultOn:
    """Safety flags (USE_SUMMARY_CACHE, USE_ORGANIZE_CHECKPOINT) must default True."""

    def test_summary_cache_default_true(self, monkeypatch):
        monkeypatch.delenv("USE_SUMMARY_CACHE", raising=False)
        cfg = _reload_config()
        assert cfg.USE_SUMMARY_CACHE == True, (
            "USE_SUMMARY_CACHE ต้อง default True — ป้องกัน re-summarize ทุกครั้ง"
        )

    def test_organize_checkpoint_default_true(self, monkeypatch):
        monkeypatch.delenv("USE_ORGANIZE_CHECKPOINT", raising=False)
        cfg = _reload_config()
        assert cfg.USE_ORGANIZE_CHECKPOINT == True, (
            "USE_ORGANIZE_CHECKPOINT ต้อง default True — ป้องกัน organize loop"
        )


# ═══════════════════════════════════════════════════════════════
# TestEnvBoolTruthy — ค่า truthy ต้อง parse เป็น True
# ═══════════════════════════════════════════════════════════════
class TestEnvBoolTruthy:
    """_env_bool must return True for all accepted truthy strings."""

    def _env_bool_with(self, value: str) -> bool:
        """Call _env_bool using os.environ trick (reloads function)."""
        from backend.config import _env_bool
        # ใช้ dummy env var name ที่ไม่ conflict กับ flags จริง
        TEST_KEY = "_TEST_BOOL_FLAG_FA"
        old = os.environ.get(TEST_KEY)
        os.environ[TEST_KEY] = value
        try:
            return _env_bool(TEST_KEY, "false")
        finally:
            if old is None:
                os.environ.pop(TEST_KEY, None)
            else:
                os.environ[TEST_KEY] = old

    def test_truthy_lowercase_true(self):
        assert self._env_bool_with("true") == True

    def test_truthy_titlecase_true(self):
        assert self._env_bool_with("True") == True

    def test_truthy_uppercase_true(self):
        assert self._env_bool_with("TRUE") == True

    def test_truthy_one(self):
        assert self._env_bool_with("1") == True

    def test_truthy_lowercase_yes(self):
        assert self._env_bool_with("yes") == True

    def test_truthy_uppercase_yes(self):
        assert self._env_bool_with("YES") == True

    def test_truthy_mixed_case_yes(self):
        assert self._env_bool_with("Yes") == True


# ═══════════════════════════════════════════════════════════════
# TestEnvBoolFalsy — ค่า falsy ต้อง parse เป็น False
# ═══════════════════════════════════════════════════════════════
class TestEnvBoolFalsy:
    """_env_bool must return False for all non-truthy strings (strict whitelist)."""

    def _env_bool_with(self, value: str) -> bool:
        from backend.config import _env_bool
        TEST_KEY = "_TEST_BOOL_FLAG_FA"
        old = os.environ.get(TEST_KEY)
        os.environ[TEST_KEY] = value
        try:
            return _env_bool(TEST_KEY, "false")
        finally:
            if old is None:
                os.environ.pop(TEST_KEY, None)
            else:
                os.environ[TEST_KEY] = old

    def test_falsy_false(self):
        assert self._env_bool_with("false") == False

    def test_falsy_uppercase_false(self):
        assert self._env_bool_with("FALSE") == False

    def test_falsy_zero(self):
        assert self._env_bool_with("0") == False

    def test_falsy_no(self):
        assert self._env_bool_with("no") == False

    def test_falsy_empty_string(self):
        assert self._env_bool_with("") == False

    def test_falsy_on(self):
        """'on' ไม่อยู่ใน whitelist → ต้อง False (ไม่ใช่ truthy)."""
        assert self._env_bool_with("on") == False

    def test_falsy_two(self):
        """'2' ไม่อยู่ใน whitelist → ต้อง False."""
        assert self._env_bool_with("2") == False

    def test_falsy_random_string(self):
        """ค่าสุ่มอื่นๆ → ต้อง False."""
        assert self._env_bool_with("enabled") == False

    def test_falsy_space(self):
        """Space → ต้อง False."""
        assert self._env_bool_with(" ") == False


# ═══════════════════════════════════════════════════════════════
# TestEnvBoolDefault — ค่า default parameter ทำงานถูก
# ═══════════════════════════════════════════════════════════════
class TestEnvBoolDefault:
    """_env_bool respects the default parameter when env var is absent."""

    def test_default_false_when_unset(self, monkeypatch):
        from backend.config import _env_bool
        monkeypatch.delenv("_NONEXISTENT_FLAG_FA", raising=False)
        result = _env_bool("_NONEXISTENT_FLAG_FA", "false")
        assert result == False

    def test_default_true_when_unset(self, monkeypatch):
        from backend.config import _env_bool
        monkeypatch.delenv("_NONEXISTENT_FLAG_FA", raising=False)
        result = _env_bool("_NONEXISTENT_FLAG_FA", "true")
        assert result == True

    def test_env_overrides_default(self, monkeypatch):
        """Env var ที่ set ต้อง override default value."""
        from backend.config import _env_bool
        monkeypatch.setenv("_NONEXISTENT_FLAG_FA", "true")
        result = _env_bool("_NONEXISTENT_FLAG_FA", "false")
        assert result == True


# ═══════════════════════════════════════════════════════════════
# TestNumericConfigDefaults — numeric defaults
# ═══════════════════════════════════════════════════════════════
class TestNumericConfigDefaults:
    """Numeric config defaults must match approved Q1-Q7 decisions."""

    def test_embedding_batch_size_default_50(self, monkeypatch):
        monkeypatch.delenv("EMBEDDING_BATCH_SIZE", raising=False)
        cfg = _reload_config()
        assert cfg.EMBEDDING_BATCH_SIZE == 50, (
            f"EMBEDDING_BATCH_SIZE default should be 50, got {cfg.EMBEDDING_BATCH_SIZE}"
        )

    def test_hdbscan_min_cluster_size_default_2(self, monkeypatch):
        """Approved Q2: min_cluster_size = 2."""
        monkeypatch.delenv("HDBSCAN_MIN_CLUSTER_SIZE", raising=False)
        cfg = _reload_config()
        assert cfg.HDBSCAN_MIN_CLUSTER_SIZE == 2, (
            f"HDBSCAN_MIN_CLUSTER_SIZE default should be 2 (approved Q2), "
            f"got {cfg.HDBSCAN_MIN_CLUSTER_SIZE}"
        )

    def test_umap_n_components_default_30(self, monkeypatch):
        monkeypatch.delenv("UMAP_N_COMPONENTS", raising=False)
        cfg = _reload_config()
        assert cfg.UMAP_N_COMPONENTS == 30, (
            f"UMAP_N_COMPONENTS default should be 30, got {cfg.UMAP_N_COMPONENTS}"
        )

    def test_summary_concurrency_default_5(self, monkeypatch):
        monkeypatch.delenv("SUMMARY_CONCURRENCY", raising=False)
        cfg = _reload_config()
        assert cfg.SUMMARY_CONCURRENCY == 5, (
            f"SUMMARY_CONCURRENCY default should be 5, got {cfg.SUMMARY_CONCURRENCY}"
        )

    def test_embedding_batch_size_env_override(self, monkeypatch):
        """EMBEDDING_BATCH_SIZE ต้อง override ได้ผ่าน env."""
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "10")
        cfg = _reload_config()
        assert cfg.EMBEDDING_BATCH_SIZE == 10, (
            f"Expected 10 from env override, got {cfg.EMBEDDING_BATCH_SIZE}"
        )

    def test_hdbscan_env_override(self, monkeypatch):
        """HDBSCAN_MIN_CLUSTER_SIZE ต้อง override ได้."""
        monkeypatch.setenv("HDBSCAN_MIN_CLUSTER_SIZE", "5")
        cfg = _reload_config()
        assert cfg.HDBSCAN_MIN_CLUSTER_SIZE == 5


# ═══════════════════════════════════════════════════════════════
# TestFlagEnvOverride — flags ต้อง activate ได้เมื่อ env set = true
# ═══════════════════════════════════════════════════════════════
class TestFlagEnvOverride:
    """Flags must activate correctly when env vars are explicitly set."""

    def test_hybrid_clustering_activates_with_env_true(self, monkeypatch):
        monkeypatch.setenv("USE_HYBRID_CLUSTERING", "true")
        cfg = _reload_config()
        assert cfg.USE_HYBRID_CLUSTERING == True

    def test_structured_summary_activates_with_env_1(self, monkeypatch):
        monkeypatch.setenv("USE_STRUCTURED_SUMMARY", "1")
        cfg = _reload_config()
        assert cfg.USE_STRUCTURED_SUMMARY == True

    def test_entity_graph_activates_with_env_yes(self, monkeypatch):
        monkeypatch.setenv("USE_ENTITY_GRAPH", "yes")
        cfg = _reload_config()
        assert cfg.USE_ENTITY_GRAPH == True

    def test_summary_cache_deactivates_with_env_false(self, monkeypatch):
        """Safety flag สามารถ opt-out ได้เมื่อ set false."""
        monkeypatch.setenv("USE_SUMMARY_CACHE", "false")
        cfg = _reload_config()
        assert cfg.USE_SUMMARY_CACHE == False

    def test_organize_checkpoint_deactivates_with_env_0(self, monkeypatch):
        monkeypatch.setenv("USE_ORGANIZE_CHECKPOINT", "0")
        cfg = _reload_config()
        assert cfg.USE_ORGANIZE_CHECKPOINT == False
