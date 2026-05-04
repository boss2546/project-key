import pytest
from backend.plan_limits import check_upload_allowed, check_pack_create_allowed
from unittest.mock import AsyncMock, patch

class MockUser:
    def __init__(self, plan="free", subscription_status="free", current_period_end=None, is_active=True):
        self.id = "user_123"
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
async def test_starter_upload_50th_file(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 49
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_starter_file_size_20_1mb_rejected(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_active")
    result = await check_upload_allowed(mock_db, user, int(20.1 * 1024 * 1024), "pdf")
    assert result is not None
    assert "20MB" in result["error"]

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
async def test_starter_pack_5(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_active")
    with patch("backend.plan_limits.get_pack_count", new_callable=AsyncMock) as mock_get_pack_count:
        mock_get_pack_count.return_value = 5
        result = await check_pack_create_allowed(mock_db, user)
        assert result is not None
        assert "5" in result["error"]

@pytest.mark.asyncio
async def test_subscription_past_due_grace(mock_db):
    user = MockUser(plan="starter", subscription_status="starter_past_due")
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 49
        with patch("backend.plan_limits.get_storage_used_mb", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = 20
            result = await check_upload_allowed(mock_db, user, 5 * 1024 * 1024, "pdf")
            assert result is None

@pytest.mark.asyncio
async def test_subscription_canceled_before_period_end(mock_db):
    from datetime import datetime, timedelta
    user = MockUser(plan="starter", subscription_status="starter_canceled", current_period_end=datetime.utcnow() + timedelta(days=5))
    with patch("backend.plan_limits.get_file_count", new_callable=AsyncMock) as mock_get_file_count:
        mock_get_file_count.return_value = 49
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
