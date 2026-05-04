import pytest
from unittest.mock import patch, MagicMock
from backend.email_service import (
    send_password_reset_email,
    _render_password_reset_html,
    _render_password_reset_text,
    _send_sync
)
from backend import config

@pytest.fixture
def mock_configured():
    with patch("backend.email_service.is_email_configured", return_value=True):
        yield

@pytest.fixture
def mock_not_configured():
    with patch("backend.email_service.is_email_configured", return_value=False):
        yield

@pytest.mark.asyncio
async def test_resend_api_key_missing(mock_not_configured):
    with patch("backend.email_service.logger.warning") as mock_warn:
        result = await send_password_reset_email("test@example.com", "Tester", "abc123token")
        assert result is False
        mock_warn.assert_called_once()

@pytest.mark.asyncio
async def test_happy_path_send(mock_configured):
    with patch("backend.email_service._send_sync") as mock_send:
        mock_send.return_value = {"id": "eml_abc"}
        with patch("backend.email_service.logger.info") as mock_info:
            result = await send_password_reset_email("test@example.com", "Tester", "token123")
            assert result is True
            mock_send.assert_called_once()
            mock_info.assert_called_once()
            assert "resend_id=eml_abc" in mock_info.call_args[0][0]

@pytest.mark.asyncio
async def test_resend_sdk_exception(mock_configured):
    with patch("backend.email_service._send_sync", side_effect=Exception("API Error")):
        with patch("backend.email_service.logger.error") as mock_error:
            result = await send_password_reset_email("test@example.com", "Tester", "token123")
            assert result is False
            mock_error.assert_called_once()
            assert "API Error" in mock_error.call_args[0][0]

def test_html_template_renders():
    html = _render_password_reset_html("TestUser", "https://example.com/reset")
    assert "TestUser" in html
    assert "https://example.com/reset" in html
    assert "รีเซ็ตรหัสผ่าน" in html

def test_plain_text_template():
    text = _render_password_reset_text("TestUser", "https://example.com/reset")
    assert "TestUser" in text
    assert "https://example.com/reset" in text
    assert "รีเซ็ตรหัสผ่าน" in text
    assert "Hello TestUser" in text

def test_xss_user_name_escape():
    html = _render_password_reset_html("<script>alert(1)</script>", "url")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html

@pytest.mark.asyncio
async def test_reset_url_format(mock_configured):
    with patch("backend.email_service.APP_BASE_URL", "https://pdb.fly.dev"):
        with patch("backend.email_service._send_sync") as mock_send:
            mock_send.return_value = {"id": "1"}
            await send_password_reset_email("test@example.com", "Tester", "abc")
            
            params = mock_send.call_args[0][0]
            assert "https://pdb.fly.dev/reset-password?token=abc" in params["html"]

def test_bilingual_content():
    html = _render_password_reset_html("Tester", "url")
    assert "สวัสดีคุณ" in html
    assert "Hello Tester" in html

@pytest.mark.asyncio
async def test_subject_line_thai(mock_configured):
    with patch("backend.email_service._send_sync") as mock_send:
        mock_send.return_value = {"id": "1"}
        await send_password_reset_email("test@example.com", "Tester", "abc")
        
        params = mock_send.call_args[0][0]
        assert params["subject"] == "รีเซ็ตรหัสผ่าน Personal Data Bank"

@pytest.mark.asyncio
async def test_from_address_format(mock_configured):
    with patch("backend.email_service.EMAIL_FROM_NAME", "Test App"):
        with patch("backend.email_service.EMAIL_FROM_ADDRESS", "no-reply@test.com"):
            with patch("backend.email_service._send_sync") as mock_send:
                mock_send.return_value = {"id": "1"}
                await send_password_reset_email("test@example.com", "Tester", "abc")
                
                params = mock_send.call_args[0][0]
                assert params["from"] == "Test App <no-reply@test.com>"
