"""Tests for llm.py — Gemini direct + 2-key failover (v10.0.23).

Mock-based unit tests covering:
- _key_suffix() never leaks full key
- thinking-tokens edge case (content=None)
- failover: primary 429/5xx → backup
- failover: non-retryable 4xx → raise immediately (no backup attempt)
- failover: no backup configured → raise primary error
- failover: backup also fails → raise "both keys failed"
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend import llm


def _make_http_error(status: int, body: str = "rate limited") -> httpx.HTTPStatusError:
    """Build an httpx.HTTPStatusError with the given status code."""
    req = httpx.Request("POST", "https://example.com")
    resp = httpx.Response(status_code=status, request=req, text=body)
    return httpx.HTTPStatusError(f"HTTP {status}", request=req, response=resp)


class TestKeySuffix:
    def test_returns_last_4_chars(self):
        assert llm._key_suffix("AIzaSyAAAAABBBB") == "BBBB"

    def test_short_key_returns_placeholder(self):
        assert llm._key_suffix("abc") == "????"

    def test_empty_key_returns_placeholder(self):
        assert llm._key_suffix("") == "????"

    def test_never_logs_full_key(self):
        """Suffix length must be at most 4 — no full-key leak via logs."""
        key = "AIzaSyVeryLongSecretKeyABCDEFG"
        suffix = llm._key_suffix(key)
        assert len(suffix) <= 4
        assert key not in suffix


class TestFailoverPrimarySucceeds:
    @pytest.mark.asyncio
    async def test_no_failover_when_primary_ok(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(return_value="OK response")
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        result = await llm._call_gemini_with_failover(
            "gemini-2.5-flash", "sys", "user", 0.3, 100
        )

        assert result == "OK response"
        # primary only — backup not touched
        assert once_mock.call_count == 1
        assert once_mock.call_args.args[0] == "primary-key-AAAA"


class TestFailoverPrimary429:
    @pytest.mark.asyncio
    async def test_failover_to_backup_on_429(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=[_make_http_error(429), "OK from backup"])
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        result = await llm._call_gemini_with_failover(
            "gemini-2.5-flash", "sys", "user", 0.3, 100
        )

        assert result == "OK from backup"
        assert once_mock.call_count == 2
        # call 2 used backup key
        assert once_mock.call_args_list[1].args[0] == "backup-key-BBBB"

    @pytest.mark.asyncio
    async def test_failover_to_backup_on_500(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=[_make_http_error(500), "OK from backup"])
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        result = await llm._call_gemini_with_failover(
            "gemini-2.5-flash", "sys", "user", 0.3, 100
        )

        assert result == "OK from backup"
        assert once_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_failover_to_backup_on_503(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=[_make_http_error(503), "OK from backup"])
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        result = await llm._call_gemini_with_failover(
            "gemini-2.5-flash", "sys", "user", 0.3, 100
        )
        assert result == "OK from backup"


class TestFailoverNonRetryable:
    @pytest.mark.asyncio
    async def test_401_raises_immediately_no_backup_attempt(self, monkeypatch):
        """Auth failures should not retry — bad key won't get better with backup."""
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=_make_http_error(401, "unauthorized"))
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        with pytest.raises(Exception, match="LLM API error 401"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )

        # Backup not attempted
        assert once_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_400_raises_immediately(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=_make_http_error(400, "bad request"))
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        with pytest.raises(Exception, match="LLM API error 400"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )

        assert once_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_404_raises_immediately(self, monkeypatch):
        """Model-not-found also non-retryable."""
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(side_effect=_make_http_error(404, "model not found"))
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        with pytest.raises(Exception, match="LLM API error 404"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )

        assert once_mock.call_count == 1


class TestFailoverNoBackup:
    @pytest.mark.asyncio
    async def test_429_raises_when_backup_not_configured(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "")  # not configured

        once_mock = AsyncMock(side_effect=_make_http_error(429))
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        with pytest.raises(Exception, match="LLM API error 429"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )

        # Only primary attempted (no backup to fail over to)
        assert once_mock.call_count == 1


class TestFailoverBothFail:
    @pytest.mark.asyncio
    async def test_both_keys_fail_raises(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "primary-key-AAAA")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        once_mock = AsyncMock(
            side_effect=[_make_http_error(429), _make_http_error(503)]
        )
        monkeypatch.setattr(llm, "_call_gemini_once", once_mock)

        with pytest.raises(Exception, match="both keys failed"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )

        assert once_mock.call_count == 2


class TestPrimaryKeyMissing:
    @pytest.mark.asyncio
    async def test_no_primary_key_raises(self, monkeypatch):
        monkeypatch.setattr(llm, "GEMINI_API_KEY", "")
        monkeypatch.setattr(llm, "GEMINI_API_KEY_BACKUP", "backup-key-BBBB")

        with pytest.raises(Exception, match="GEMINI_API_KEY not configured"):
            await llm._call_gemini_with_failover(
                "gemini-2.5-flash", "sys", "user", 0.3, 100
            )


class TestThinkingTokensEdgeCase:
    """Gemini 2.5+ thinking-tokens consume budget; content can come back None."""

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty_string(self, monkeypatch):
        """When finish_reason='length' + content=None, return '' instead of throwing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"role": "assistant"},  # no content key
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 0, "total_tokens": 13},
        }

        async def mock_post(*_args, **_kwargs):
            return mock_response

        async_client_mock = MagicMock()
        async_client_mock.__aenter__ = AsyncMock(return_value=async_client_mock)
        async_client_mock.__aexit__ = AsyncMock(return_value=None)
        async_client_mock.post = mock_post

        with patch("backend.llm.httpx.AsyncClient", return_value=async_client_mock):
            result = await llm._call_gemini_once(
                "test-key", "gemini-2.5-flash", "sys", "user", 0.0, 10
            )

        assert result == ""
