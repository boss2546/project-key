"""Plan limits tests — v8.0.2 (Free + Starter ×10 from original baseline)

Limits in effect:
- Free:    50 files / 500 MB / 100 MB max / 10 packs / 50 AI / 100 export
- Starter: 500 files / 10 GB / 200 MB max / 50 packs / 1000 AI / 3000 export
- Admin:   999999 everything (allowlist via ADMIN_EMAILS)
"""
import pytest
from backend.plan_limits import (
    check_upload_allowed,
    check_pack_create_allowed,
    _effective_plan,
    get_limits,
)
from unittest.mock import AsyncMock, patch


class MockUser:
    def __init__(self, plan="free", subscription_status="free", current_period_end=None, is_active=True, email=""):
        self.id = "user_123"
        self.email = email
        self.plan = plan
        self.subscription_status = subscription_status
        self.current_period_end = current_period_end
        self.is_active = is_active


@pytest.fixture
def mock_db():
    return AsyncMock()


# ═══════════════════════════════════════════
# Free plan (×10 from v7.6.0 baseline)
# ═══════════════════════════════════════════

@pytest.mark.asyncio
async def test_free_upload_under_file_limit(mock_db):
    """Free file_limit = 50; 49 files → next upload allowed"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 49
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_free_upload_at_file_limit_rejected(mock_db):
    """Free file_limit = 50; at 50 files → rejected with upgrade prompt"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 50
        result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
        assert result is not None
        assert "50 ไฟล์" in result["error"]
        assert result["upgrade"] is True


@pytest.mark.asyncio
async def test_free_file_size_100mb_allowed(mock_db):
    """Free max_file_size_mb = 100; exact 100 MB allowed"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 0
            result = await check_upload_allowed(mock_db, user, 100 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_free_file_size_over_100mb_rejected(mock_db):
    """Free max_file_size_mb = 100; 100.1 MB rejected"""
    user = MockUser(plan="free")
    result = await check_upload_allowed(mock_db, user, int(100.1 * 1024 * 1024), "pdf")
    assert result is not None
    assert "100MB" in result["error"]
    assert result["upgrade"] is True


@pytest.mark.asyncio
async def test_free_file_type_pdf_allowed(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 0
            result = await check_upload_allowed(mock_db, user, 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_free_file_type_png_rejected(mock_db):
    """Free still doesn't get image types — paid feature"""
    user = MockUser(plan="free")
    result = await check_upload_allowed(mock_db, user, 1024, "png")
    assert result is not None
    assert "ไม่รองรับ" in result["error"]


@pytest.mark.asyncio
async def test_free_storage_under_limit(mock_db):
    """Free storage = 500 MB; 499 + 1 MB = 500 (exact, allowed)"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 499.0
            result = await check_upload_allowed(mock_db, user, 1 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_free_storage_over_limit_rejected(mock_db):
    """Free storage = 500 MB; 500 + 0.1 MB > 500 → rejected"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 500.0
            result = await check_upload_allowed(mock_db, user, int(0.1 * 1024 * 1024), "pdf")
            assert result is not None
            assert "พื้นที่ Free (500MB) เต็มแล้ว" in result["error"]


@pytest.mark.asyncio
async def test_free_pack_at_limit(mock_db):
    """Free context_pack_limit = 10; at 10 → rejected"""
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_pack_count", new_callable=AsyncMock) as mock_get_pack_count:
        mock_get_pack_count.return_value = 10
        result = await check_pack_create_allowed(mock_db, user)
        assert result is not None
        assert "10 Context Pack" in result["error"]


# ═══════════════════════════════════════════
# Starter plan (×10 from v7.6.0 baseline)
# ═══════════════════════════════════════════

@pytest.mark.asyncio
async def test_starter_upload_under_limit(mock_db):
    """Starter file_limit = 500; 499 files → next allowed"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 499
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_starter_file_size_over_limit_rejected(mock_db):
    """Starter max_file_size_mb = 200; 200.1 MB rejected"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    result = await check_upload_allowed(mock_db, user, int(200.1 * 1024 * 1024), "pdf")
    assert result is not None
    assert "200MB" in result["error"]


@pytest.mark.asyncio
async def test_starter_png_allowed(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 0
            result = await check_upload_allowed(mock_db, user, 1024, "png")
            assert result is None


@pytest.mark.asyncio
async def test_starter_xlsx_allowed(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 0
            result = await check_upload_allowed(mock_db, user, 1024, "xlsx")
            assert result is None


@pytest.mark.asyncio
async def test_starter_pack_at_limit(mock_db):
    """Starter context_pack_limit = 50; at 50 → rejected"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_pack_count", new_callable=AsyncMock) as mock_get_pack_count:
        mock_get_pack_count.return_value = 50
        result = await check_pack_create_allowed(mock_db, user)
        assert result is not None
        assert "50" in result["error"]


# ═══════════════════════════════════════════
# Subscription state transitions
# ═══════════════════════════════════════════

@pytest.mark.asyncio
async def test_subscription_past_due_grace(mock_db):
    """past_due treated as starter (grace period)"""
    user = MockUser(plan="starter", subscription_status="starter_past_due")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 499
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_subscription_canceled_before_period_end(mock_db):
    """canceled but period not yet ended → still starter"""
    from datetime import datetime, timedelta
    user = MockUser(
        plan="starter",
        subscription_status="starter_canceled",
        current_period_end=datetime.utcnow() + timedelta(days=5),
    )
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 499
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None


@pytest.mark.asyncio
async def test_subscription_canceled_after_period_end(mock_db):
    """canceled past period end → falls back to free (50 file limit)"""
    from datetime import datetime, timedelta
    user = MockUser(
        plan="starter",
        subscription_status="starter_canceled",
        current_period_end=datetime.utcnow() - timedelta(days=5),
    )
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 50  # over free limit (was 5; now 50)
        result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
        assert result is not None
        assert "50 ไฟล์" in result["error"]


# ═══════════════════════════════════════════
# v8.0.1 — Admin allowlist tests
# ═══════════════════════════════════════════

def test_admin_email_resolves_to_admin_plan():
    """Email in ADMIN_EMAILS → effective plan is 'admin'"""
    user = MockUser(email="bossok2546@gmail.com", subscription_status="free")
    assert _effective_plan(user) == "admin"


def test_admin_email_case_insensitive():
    """Admin lookup ignores case"""
    user = MockUser(email="BossOk2546@Gmail.COM", subscription_status="free")
    assert _effective_plan(user) == "admin"


def test_admin_limits_are_999999():
    """Admin plan limits are effectively unlimited"""
    user = MockUser(email="bossok2546@gmail.com", subscription_status="free")
    limits = get_limits(user)
    assert limits["file_limit"] == 999999
    assert limits["storage_limit_mb"] == 999999
    assert limits["max_file_size_mb"] == 999999
    assert limits["context_pack_limit"] == 999999
    assert limits["semantic_search_enabled"] is True


def test_non_admin_email_uses_normal_plan():
    """Non-admin emails follow subscription_status normally"""
    user = MockUser(email="random@example.com", subscription_status="free")
    assert _effective_plan(user) == "free"


@pytest.mark.asyncio
async def test_admin_can_upload_huge_file(mock_db):
    """Admin can upload 500 MB file (would be rejected on Free/Starter)"""
    user = MockUser(email="bossok2546@gmail.com", subscription_status="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 1000  # over free + starter limit
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 1000  # 1 GB used
            result = await check_upload_allowed(mock_db, user, 500 * 1024 * 1024, "xlsx")
            assert result is None  # admin bypasses


# ═══════════════════════════════════════════
# v8.0.2 — ×10 baseline sanity check
# ═══════════════════════════════════════════

def test_v8_0_2_starter_baseline_x10():
    """Confirm Starter limits are ×10 from v7.6.0 baseline"""
    user = MockUser(subscription_status="starter_active")
    limits = get_limits(user)
    # Original baseline → ×10
    assert limits["file_limit"] == 500           # 50 → 500
    assert limits["storage_limit_mb"] == 10240   # 1024 → 10240
    assert limits["max_file_size_mb"] == 200     # 20 → 200
    assert limits["context_pack_limit"] == 50    # 5 → 50
    assert limits["ai_summary_limit_monthly"] == 1000   # 100 → 1000
    assert limits["export_limit_monthly"] == 3000       # 300 → 3000
    assert limits["refresh_limit_monthly"] == 100       # 10 → 100
    assert limits["version_history_days"] == 70         # 7 → 70


def test_v8_0_2_free_baseline_x10():
    """Confirm Free limits are ×10 from v7.6.0 baseline (where applicable)"""
    user = MockUser(subscription_status="free")
    limits = get_limits(user)
    assert limits["file_limit"] == 50            # 5 → 50
    assert limits["storage_limit_mb"] == 500     # 50 → 500
    assert limits["max_file_size_mb"] == 100     # 10 → 100
    assert limits["context_pack_limit"] == 10    # 1 → 10
    assert limits["ai_summary_limit_monthly"] == 50   # 5 → 50
    assert limits["export_limit_monthly"] == 100      # 10 → 100
    # Gated features stay 0 / False to preserve upgrade incentive
    assert limits["refresh_limit_monthly"] == 0
    assert limits["semantic_search_enabled"] is False
    assert limits["version_history_days"] == 0
