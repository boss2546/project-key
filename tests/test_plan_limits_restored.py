import pytest
from backend.plan_limits import check_upload_allowed, check_pack_create_allowed, _effective_plan, get_limits
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

@pytest.mark.asyncio
async def test_free_upload_5th_file(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 4
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_free_upload_6th_file_rejected(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 5
        result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
        assert result is not None
        assert "5 ไฟล์" in result["error"]
        assert result["upgrade"] is True

@pytest.mark.asyncio
async def test_free_file_size_10mb_allowed(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 0
            result = await check_upload_allowed(mock_db, user, 10 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_free_file_size_10_1mb_rejected(mock_db):
    user = MockUser(plan="free")
    result = await check_upload_allowed(mock_db, user, int(10.1 * 1024 * 1024), "pdf")
    assert result is not None
    assert "10MB" in result["error"]
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
    user = MockUser(plan="free")
    result = await check_upload_allowed(mock_db, user, 1024, "png")
    assert result is not None
    assert "ไม่รองรับ" in result["error"]

@pytest.mark.asyncio
async def test_free_storage_50mb_exact(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 49.0
            result = await check_upload_allowed(mock_db, user, 1 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_free_storage_50_1mb_rejected(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 0
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 50.0
            result = await check_upload_allowed(mock_db, user, int(0.1 * 1024 * 1024), "pdf")
            assert result is not None
            assert "พื้นที่ Free (50MB) เต็มแล้ว" in result["error"]

@pytest.mark.asyncio
async def test_free_pack_limit_1(mock_db):
    user = MockUser(plan="free")
    with patch("backend.plan_limits.get_pack_count", new_callable=AsyncMock) as mock_get_pack_count:
        mock_get_pack_count.return_value = 1
        result = await check_pack_create_allowed(mock_db, user)
        assert result is not None
        assert "1 Context Pack" in result["error"]

@pytest.mark.asyncio
async def test_starter_upload_under_limit(mock_db):
    """v8.0.1: Starter file_limit bumped 50 → 250 (×5)"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 249
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_starter_file_size_over_limit_rejected(mock_db):
    """v8.0.1: Starter max_file_size_mb bumped 20 → 100 (×5)"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    result = await check_upload_allowed(mock_db, user, int(100.1 * 1024 * 1024), "pdf")
    assert result is not None
    assert "100MB" in result["error"]

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
    """v8.0.1: Starter context_pack_limit bumped 5 → 25 (×5)"""
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_pack_count", new_callable=AsyncMock) as mock_get_pack_count:
        mock_get_pack_count.return_value = 25
        result = await check_pack_create_allowed(mock_db, user)
        assert result is not None
        assert "25" in result["error"]

@pytest.mark.asyncio
async def test_subscription_past_due_grace(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_past_due")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 249
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_subscription_canceled_before_period_end(mock_db):
    from datetime import datetime, timedelta
    user = MockUser(plan="starter", subscription_status="starter_canceled", current_period_end=datetime.utcnow() + timedelta(days=5))
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 249
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_subscription_canceled_after_period_end(mock_db):
    from datetime import datetime, timedelta
    user = MockUser(plan="starter", subscription_status="starter_canceled", current_period_end=datetime.utcnow() - timedelta(days=5))
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 49 # over free limit
        result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
        assert result is not None
        assert "5 ไฟล์" in result["error"]


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
    """Admin can upload 500MB file (would be rejected on Free/Starter)"""
    user = MockUser(email="bossok2546@gmail.com", subscription_status="free")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_count:
        mock_count.return_value = 1000  # over free + starter limit
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 1000  # 1GB used
            result = await check_upload_allowed(mock_db, user, 500 * 1024 * 1024, "xlsx")
            assert result is None  # admin bypasses
