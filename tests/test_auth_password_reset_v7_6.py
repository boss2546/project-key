import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from unittest.mock import patch
import uuid

@pytest.fixture
def test_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
async def test_happy_reset_email_sent(test_client):
    email = f"reset_test_{uuid.uuid4().hex[:8]}@example.com"
    # Need a user first
    register_response = await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "name": "Resetter"}
    )
    assert register_response.status_code == 200
    
    with patch("backend.email_service.send_password_reset_email") as mock_send:
        response = await test_client.post(
            "/api/auth/request-reset",
            json={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" not in data
        assert "message" in data
        assert "email" in data
        
        # Verify email function was called
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert args[0] == email
        assert args[1] == "Resetter"
        assert type(args[2]) == str  # the token

@pytest.mark.asyncio
async def test_unknown_email_anti_enum(test_client):
    response = await test_client.post(
        "/api/auth/request-reset",
        json={"email": f"unknown_{uuid.uuid4().hex[:8]}@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "reset_token" not in data
    assert "message" in data

@pytest.mark.asyncio
async def test_inactive_account_anti_enum(test_client):
    from backend.database import AsyncSessionLocal
    from sqlalchemy import select
    from backend.database import User
    
    email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    # Register a user and deactivate it directly
    await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "name": "Inactive"}
    )
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_active = False
        await db.commit()

    with patch("backend.email_service.send_password_reset_email") as mock_send:
        response = await test_client.post(
            "/api/auth/request-reset",
            json={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" not in data
        assert "message" in data
        mock_send.assert_not_called()

@pytest.mark.asyncio
async def test_email_send_fail_still_success(test_client):
    email = f"fail_{uuid.uuid4().hex[:8]}@example.com"
    await test_client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "name": "Failer"}
    )
    
    with patch("backend.email_service.send_password_reset_email", side_effect=Exception("SMTP Down")):
        response = await test_client.post(
            "/api/auth/request-reset",
            json={"email": email}
        )
        # Should not throw 500, task is sent to background and handled
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" not in data
        assert "message" in data
