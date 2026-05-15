"""Safety primitives for the extraction pipeline -- v10.0.0.

Three building blocks:
  1. PARSE_LOCK       -- threading.Lock for lxml-backed parsers (python-docx, python-pptx)
                         that share a module-level oxml_parser instance. Concurrent
                         calls without the lock cause random XMLSyntaxError.
                         See HANDOFF Lesson 2.
  2. retry_with_backoff -- decorator that retries on transient errors
                         (rate limit / timeout / 5xx / connection). Stops on
                         deterministic errors (400 / 401 / 404).
  3. get_extract_semaphore -- lazy-init asyncio.Semaphore to cap concurrent
                         heavy extractions. Lazy because Python 3.9
                         binds asyncio primitives to the event loop at
                         construction (HANDOFF Lesson 3).

Import this from extraction.py / processors / upload_worker so all heavy
parsing flows share the same guards.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import os
import random
import threading
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)


# ============================================================
# 1) Threading lock for lxml-backed parsers
# ============================================================
# python-docx and python-pptx share lxml's module-level oxml_parser.
# Concurrent .docx / .pptx parsing without serialization triggers
# XMLSyntaxError randomly under load (stress-tested in PDB Ingestion Lab,
# 100-file concurrent run produced ~3 failures).
#
# This single lock is acquired inside the *_extract_docx_basic*,
# *_extract_pptx* synchronous helpers in extraction.py before any
# python-docx / python-pptx call. openpyxl does NOT need the lock
# (it does not use lxml the same way).
PARSE_LOCK = threading.Lock()


# ============================================================
# 2) Retry with exponential backoff (transient errors only)
# ============================================================
_RETRYABLE_HINTS = (
    "rate limit", "429", "503", "504", "502", "500",
    "timeout", "timed out", "connection",
    "ConnectionError", "ReadError", "RemoteProtocolError",
    "ServerDisconnected",
)


def _is_retryable_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(hint.lower() in msg for hint in _RETRYABLE_HINTS)


T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    jitter: float = 0.5,
):
    """Decorator -- retry sync or async function on transient errors only.

    Args:
        max_attempts: total tries including the first (so 3 = 2 retries)
        base_delay:   seconds for first backoff (2 * 2^attempt)
        max_delay:    cap on a single backoff sleep
        jitter:       random fraction added (0..jitter) to break sync storms

    Non-retryable errors (4xx that aren't 429) raise immediately.
    """

    def decorator(fn):
        is_coro = asyncio.iscoroutinefunction(fn)

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            last_exc: Optional[BaseException] = None
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if not _is_retryable_error(e) or attempt + 1 >= max_attempts:
                        raise
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    delay += random.random() * jitter
                    logger.warning(
                        "retry_with_backoff: %s attempt %d/%d failed (%s) -- "
                        "sleeping %.1fs",
                        fn.__name__, attempt + 1, max_attempts, e, delay,
                    )
                    await asyncio.sleep(delay)
            assert last_exc is not None
            raise last_exc

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            import time
            last_exc: Optional[BaseException] = None
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if not _is_retryable_error(e) or attempt + 1 >= max_attempts:
                        raise
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    delay += random.random() * jitter
                    logger.warning(
                        "retry_with_backoff: %s attempt %d/%d failed (%s) -- "
                        "sleeping %.1fs",
                        fn.__name__, attempt + 1, max_attempts, e, delay,
                    )
                    time.sleep(delay)
            assert last_exc is not None
            raise last_exc

        return async_wrapper if is_coro else sync_wrapper

    return decorator


# ============================================================
# 3) Lazy-init concurrency semaphore for heavy extractions
# ============================================================
# Python 3.9 binds asyncio.Semaphore() to the running event loop at
# *construction* time. A module-level Semaphore would attach to whatever
# loop happens to be active during first import (often a one-shot loop in
# tests / startup probing) and then throw "Future attached to a different
# loop" when the real worker loop tries to acquire it.
#
# Lazy init defers construction until the first acquire() call, by which
# time the worker's loop is running.
_EXTRACT_SEMAPHORE: Optional[asyncio.Semaphore] = None
_EXTRACT_CONCURRENCY = int(os.getenv("LOCAL_EXTRACT_CONCURRENCY", "4"))


def get_extract_semaphore() -> asyncio.Semaphore:
    """Return the (lazy-initialized) extract concurrency semaphore."""
    global _EXTRACT_SEMAPHORE
    if _EXTRACT_SEMAPHORE is None:
        _EXTRACT_SEMAPHORE = asyncio.Semaphore(_EXTRACT_CONCURRENCY)
    return _EXTRACT_SEMAPHORE


# Reset hook -- used by tests to force re-binding to a fresh loop.
def _reset_semaphore_for_testing() -> None:
    global _EXTRACT_SEMAPHORE
    _EXTRACT_SEMAPHORE = None
