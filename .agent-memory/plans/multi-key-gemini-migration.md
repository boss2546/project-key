# Plan: Multi-Key Gemini Migration (Summary + Embeddings + Multimodal → Direct + Rotation)

**Author:** 🔴 แดง (Daeng) · revised v2 (2026-05-17, after Explore audit)
**Date:** 2026-05-17
**Status:** `draft` — รอ user approve
**Parent:** v11.0.0 organize refactor (เป็น sub-phase 1.5 — เร่งทำหลัง Phase 1 stop checkpoint)
**Target version:** `10.0.22+` (rolling deploy ระหว่างทำ — ยังไม่ bump major)
**Effort:** เขียว ~24-32 ชั่วโมง (3-4 วัน, ↑ from v1 2-3 วัน เพราะ Files API affinity + 9 callers) + ฟ้า ~4 ชั่วโมง
**Risk:** 🔴 HIGH — refactor core LLM layer + 4-key rotation บน prod + DB schema change (Files affinity)

---

## 🎯 Goal

ย้าย Summary + Embeddings + Multimodal pipeline จาก **OpenRouter → Direct Gemini API** พร้อม **4-key rotation** เพื่อ:

1. ✅ Bypass OpenRouter rate limit (free tier ~hundreds/day)
2. ✅ ใช้ 4 Gemini keys × 10 RPM = **40 RPM rotation** (4× headroom)
3. ✅ ตั้ง `SUMMARY_CONCURRENCY=20` ปลอดภัย (เดิม 5)
4. ✅ ลด cost (เลี่ยง OpenRouter 5-15% markup)
5. ✅ Unblock Phase 1 hybrid clustering (need embedding API ที่ใช้ได้)
6. ✅ Smart throttle handling — skip key ที่โดน 429 ชั่วคราว

**Performance target:**
- Summary 100 ไฟล์ — 30 min → **5-10 min** (3-6× faster)
- Free tier เลี้ยง 4 keys = $0/เดือน (vs paid Gemini $5-10 หรือ OpenRouter $10-20)

---

## 📚 Context

### Why this is needed (จาก discovery วันนี้)

**Discovery 1:** `text-embedding-004` model → **404 NOT FOUND** บน Gemini API v1beta
- เก่า: ตั้ง default model = `text-embedding-004` (768-d)
- ใหม่: ต้องใช้ `gemini-embedding-001` (3072-d) ที่ทำงานจริง
- → **Phase 1 hybrid clustering ใช้ไม่ได้** จนกว่าจะแก้

**Discovery 2:** User มี 4 Gemini API keys
- เทสแล้ว: ทั้ง 4 keys auth ผ่าน chat call ได้
- กระจาย load ข้าม 4 keys = 4× free tier capacity

**Discovery 3:** Summary ผ่าน OpenRouter ติด rate limit ของ OpenRouter เอง
- OpenRouter pool Gemini access ของพวกเขา → rate cap ที่ OpenRouter level
- ใช้ keys ของเราตรง → 4× free tier ของแต่ละ key อิสระ

### Architecture decision

**ทำไมไม่ rotate OpenRouter keys?** OpenRouter มี 1 account per user (key เดียว) — rotation ไม่ช่วย
**ทำไมไม่ใช้ paid Gemini ตรง?** Free tier 4 keys (40 RPM) เพียงพอสำหรับ scale ปัจจุบัน + ฟรี
**ทำไมต้อง refactor ทั้ง 3 services?** Centralize key management — รักษา consistency + simplify ops

---

## 🗺️ Discovered Touchpoints — ครอบคลุม Code Map (จาก Explore audit 2026-05-17)

### A. GOOGLE_API_KEY direct touchpoints

| File:Line | Function | Current usage | Migration impact |
|---|---|---|---|
| `backend/ai_ingest.py:20,47` | `_HAS_GEMINI` init | Module-level single-key client | Replace with api_keys pool |
| `backend/ai_ingest.py:53` | Warning log | Graceful degrade | Update to check pool size |
| `backend/ai_ingest.py:80,112,150` | `is_available()`, errors | Multimodal feature gate | Use api_keys.is_available() |
| `backend/embeddings.py:69,71-72` | `_init_genai()` | Lazy single-key init | Replace with pool |
| `backend/embeddings.py:90` | `is_available()` | Feature gate | Pool-aware |
| `backend/clustering.py:96` | Warning message | "GOOGLE_API_KEY missing" | Update to "GOOGLE_API_KEYS" |
| `backend/processors/startup_probe.py:71` | Boot health check | `os.getenv("GOOGLE_API_KEY")` | Check pool count + 1 success call |
| **Test files** | | | |
| `backend/_test_embeddings.py:132-207` | Graceful degrade tests | `monkeypatch.delenv("GOOGLE_API_KEY")` | Update fixture for pool absence |
| `backend/_test_embeddings.py:269` | TestRealAPI skipif | `not os.getenv("GOOGLE_API_KEY")` | Check `GOOGLE_API_KEYS` |
| `backend/_test_clustering.py:353` | Error assertion | `pytest.raises(RuntimeError)` | Update error text |

### B. Gemini SDK client instantiation (สอง modules)

| File:Line | Pattern | Migration |
|---|---|---|
| `backend/ai_ingest.py:46-50` | `from google import genai; genai.Client(api_key=_api_key)` | Replace with `gemini_direct.GeminiClient(key_pool)` |
| `backend/embeddings.py:78-79` | Same pattern | Same replacement |

### C. LLM call chain — **9 callers** ของ llm.py functions

| Caller | File:Line | Calls | JSON parse? |
|---|---|---|---|
| organize | `backend/organizer.py:330,382,474,517` | `call_llm_json()` × multiple | ✅ |
| cluster label | `backend/clustering.py:335` | `call_llm_json()` | ✅ |
| context packs | `backend/context_packs.py:331` | `call_llm_pro()` | ❌ |
| metadata enrich | `backend/metadata.py:60` | `call_llm_pro()` | ⚠️ (prompt asks JSON, raw resp) |
| graph build | `backend/graph_builder.py:177,245` | `call_llm_pro()` | ✅ |
| extraction summary | `backend/extraction.py:587,620,636` | `call_llm_pro()` (map-reduce!) | ❌ |
| chat retriever | `backend/retriever.py:426,464` | `call_llm_json()`, `call_llm()` | ✅ (json variant) |
| relations | `backend/relations.py:179` | `call_llm_pro()` | ⚠️ Likely |
| AI pack builder | `backend/ai_pack_builder.py:290,431` | `call_llm_json()` | ✅ |

**Strategy**: ทั้งหมดเรียก `llm.py` functions — **refactor ที่ llm.py เพียงจุดเดียว** → callers ไม่ต้องเปลี่ยน (transparent routing)

### D. Multimodal / Files API state coupling (🔴 CRITICAL — new gap!)

| File:Line | Function | Pattern | Migration gotcha |
|---|---|---|---|
| `backend/ai_ingest.py:184-204` | `_ingest_audio()` | Files upload → analyze → auto-delete 48h | 🔴 Key-affinity required |
| `backend/ai_ingest.py:206-256` | `_ingest_video()` | Same | Same |
| `backend/ai_ingest.py:258-298` | `_ingest_image_smart()` | Same | Same |
| `backend/ai_ingest.py:150-268` (entry) | `ingest_via_ai()`, `extract_pdf_via_gemini_sync()` | Multi-step Files API workflow | Same |

**Issue**: Gemini Files API state ผูกกับ key — upload ด้วย key A → analyze ต้องใช้ key A → delete ต้องใช้ key A. ถ้า rotate ภายในไฟล์ → file_id orphaned

**Fix needed**: Per-file key affinity (sticky during 1 file's lifecycle) + optional `File.gemini_api_key_id` column for cleanup tracking

### E. Cost / metrics tracking

| File:Line | Current | Migration |
|---|---|---|
| `backend/llm.py:53-57` | Log `prompt_tokens` จาก OpenRouter | Extract `prompt_token_count` (Gemini SDK format) |
| `backend/admin.py:55+` | No LLM cost tracking | (Optional) add per-key quota dashboard |
| `backend/processors/startup_probe.py:71-75` | Boot probe | Add pool health probe (count + 1 ping) |

### F. SDK behavior differences (gotchas)

| Aspect | OpenRouter | Gemini SDK | Action |
|---|---|---|---|
| **Streaming** | httpx async | Sync only (full response) | ✅ Current code ไม่ใช้ streams |
| **Tool use** | Supported | Different API (`tool_config`) | Code ยังไม่ใช้ — safe |
| **Token usage** | `response.json()["usage"]["prompt_tokens"]` | `response.usage.prompt_token_count` | Field name diff — wrap |
| **Async/sync** | `await client.post()` | `asyncio.to_thread()` wrap | `embeddings.py:149` already does — copy pattern |
| **Model name** | `"google/gemini-3.1-pro-preview"` | `"gemini-2.5-flash"` | ⚠️ Need alias table |
| **Surrogate** | Already strip in `llm.py:59-62` | Same risk | ✅ Keep strip in new code |

---

## 🔴 5 Critical Gaps จาก Explore audit (plan v1 ขาด)

### Gap #1 — Files API Key Affinity (CRITICAL)
**ปัญหา**: ai_ingest.py ทำ 3-step workflow (upload → analyze → cleanup). Gemini Files API state ผูกกับ key ที่ upload. ถ้า rotation switch key มิดทาง → file_id ใช้กับ key ใหม่ไม่ได้ → orphan + can't delete

**Mitigation**:
1. `gemini_direct.py` รองรับ "pin_key" mode — passing key explicit ในทุก call
2. `ai_ingest.py` ดึง key ครั้งเดียวต่อไฟล์ → reuse key throughout file lifecycle
3. (Optional) Schema: เพิ่ม `File.gemini_api_key_suffix` column (last-6-chars) for delete tracking ภายหลัง
4. Test: simulate rotation mid-file → verify pinned key reused

**Impact on plan**: เพิ่ม schema migration (Phase A.3) + per-call key parameter ใน gemini_direct.py

### Gap #2 — Async/Sync Timeout Mismatch
**ปัญหา**: `llm.py:_call_openrouter` ใช้ `httpx.AsyncClient(timeout=180.0)` แต่ Gemini SDK เป็น sync wrap `asyncio.to_thread()` — ไม่มี timeout default

**Mitigation**:
1. `gemini_direct.py` ทุก call wrap `asyncio.wait_for(asyncio.to_thread(...), timeout=180.0)`
2. ถ้า timeout → mark key as throttled + retry next key
3. Test: mock slow call (sleep 200s) → verify timeout + key rotation

**Impact on plan**: เพิ่ม timeout config ใน gemini_direct.py + tests

### Gap #3 — Model Name Translation Layer
**ปัญหา**: OpenRouter ใช้ `"google/gemini-3.1-pro-preview"` แต่ Gemini SDK ใช้ `"gemini-2.5-pro"` หรือ `"gemini-2.0-pro-exp"`. Config.py ตอน v10.0.x ใช้ Flash temp → ต้องมี translation

**Mitigation**:
สร้าง model alias dict ใน `gemini_direct.py`:
```python
OPENROUTER_TO_GEMINI_MODEL = {
    "google/gemini-3-flash-preview": "gemini-2.5-flash",
    "google/gemini-3.1-pro-preview": "gemini-2.5-pro",
    "google/gemini-2.5-flash": "gemini-2.5-flash",
    # ... maintain forward compat
}
```

ถ้า model name ไม่อยู่ใน alias → log warning + ส่งตรง (fallback)

**Impact on plan**: เพิ่ม Step A.2.5 — model translation table

### Gap #4 — Circuit Breaker: All-Keys-Exhausted
**ปัญหา**: ถ้า 4 keys quota เต็มพร้อมกัน → ทุก call fail → no fallback → user error

**Mitigation**:
1. `gemini_direct.py` catch "all keys throttled" → propagate exception
2. `llm.py` wrapper catch direct exception → **fallback to OpenRouter** (if `USE_DIRECT_FOR_X=true` + `OPENROUTER_API_KEY` configured)
3. Admin alert: ถ้า fallback happens → log + (optional) email/LINE notify
4. Daily quota monitor: track per-key request count → alert at 80% (~1200/1500)

**Impact on plan**: เพิ่ม fallback logic in llm.py refactor + admin alert mechanism

### Gap #5 — Test Coverage for Rotation State Machine
**ปัญหา**: Current tests mock `call_llm_json` globally — ไม่ test round-robin fairness, throttle expiry, concurrent rotation. Risk: bug ใน key state mutation ไม่ถูก catch

**Mitigation**:
สร้าง `backend/_test_api_keys.py` ที่ test:
- Round-robin fairness (100 calls × 4 keys → ~25 each ± 1)
- Throttle state machine (mark → skip → expire → resume)
- Concurrent get_key (100 parallel → thread-safe, no double-issue)
- All-throttled fallback (return oldest)
- Single-key compat (pool size 1)
- Diagnostics shape

**Impact on plan**: เพิ่ม 10+ unit tests + per-call assertion ใน existing integration tests

---

## 🏗️ Architecture

### ก่อน (ปัจจุบัน)

```
┌─────────────────────────────────────────────────────┐
│  organizer.py / chat / etc.                         │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
       ┌─────────────────┐
       │  llm.py         │ ← OPENROUTER_API_KEY (single)
       │  call_llm()     │
       │  call_llm_pro() │
       │  call_llm_json()│
       └────────┬────────┘
                │
                ▼
       ┌────────────────────┐
       │  OpenRouter        │
       │  (proxy)           │ ← rate-limited by OpenRouter
       └────────┬───────────┘
                │
                ▼
       ┌────────────────────┐
       │  Gemini API        │ ← Google's pool
       └────────────────────┘

┌─────────────────────────────────────────────────────┐
│  embeddings.py · ai_ingest.py                       │ ← GOOGLE_API_KEY (single)
│  (direct Gemini SDK)                                │
└─────────────────────────────────────────────────────┘
```

### หลัง (target)

```
┌─────────────────────────────────────────────────────┐
│  organizer.py · chat · embeddings · ai_ingest       │
└───────────────┬─────────────────────────────────────┘
                │
                ▼
       ┌──────────────────────┐
       │  api_keys.py         │ ← NEW: central key pool manager
       │  - rotate()          │   - 4 keys round-robin
       │  - mark_throttled()  │   - skip throttled (60s cooldown)
       │  - get_metrics()     │   - per-key stats
       └────────┬─────────────┘
                │
                ▼
       ┌──────────────────────────────────────────┐
       │  gemini_direct.py    │   llm.py         │
       │  - chat()            │   (legacy stays  │
       │  - embed()           │    for fallback) │
       │  - multimodal()      │                  │
       └────────┬─────────────────────┬──────────┘
                │                     │
                ▼                     ▼
       ┌─────────────────┐   ┌──────────────────┐
       │  Gemini API     │   │  OpenRouter      │ ← legacy path
       │  (direct, 4×)   │   │  (fallback only) │
       └─────────────────┘   └──────────────────┘
```

### Routing strategy

```
Feature                    | USE_DIRECT_GEMINI=false | USE_DIRECT_GEMINI=true
─────────────────────────────────────────────────────────────────────────
Embedding (Phase 1)        | OpenRouter (n/a — no embed) | Direct + 4-key rotation
Summary (call_llm_pro)     | OpenRouter (current)        | Direct + 4-key rotation
Cluster label (Phase 1)    | OpenRouter (current)        | Direct + 4-key rotation
Chat (call_llm)            | OpenRouter (current)        | Direct + 4-key rotation
Multimodal (ai_ingest)     | Direct (single key)         | Direct + 4-key rotation
Enrich (metadata)          | OpenRouter (current)        | Direct + 4-key rotation
```

ทุก flow มี **fallback** → ถ้า direct ล้ม (all keys throttled / API down) → fallback OpenRouter

---

## 📁 Files to Create / Modify

### NEW files (3)

#### 1. `backend/api_keys.py` (~150 lines)
Central key pool manager — rotation + throttle + metrics

```python
"""Multi-key Gemini API pool manager.

Features:
- Round-robin key rotation
- Per-key throttle tracking (mark + skip during cooldown)
- Per-key metrics (calls, 429s, errors, last-used)
- Graceful degrade: all throttled → return least-recently-failed
- Thread-safe (asyncio.Lock for state mutations)
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KeyMetrics:
    calls: int = 0
    errors_429: int = 0
    errors_other: int = 0
    last_used_at: float = 0.0
    throttled_until: float = 0.0  # 0 = not throttled
    success_count: int = 0


_keys: list[str] = []
_metrics: dict[str, KeyMetrics] = {}
_lock: asyncio.Lock | None = None
_round_robin_idx: int = 0


def _init():
    """Initialize from env (lazy)."""
    global _keys, _metrics, _lock
    if _keys:
        return  # already init
    
    # Try multi-key env first
    multi = os.getenv("GOOGLE_API_KEYS", "").strip()
    if multi:
        _keys = [k.strip() for k in multi.split(",") if k.strip()]
    else:
        # Fallback to single key
        single = os.getenv("GOOGLE_API_KEY", "").strip()
        if single:
            _keys = [single]
    
    _metrics = {k: KeyMetrics() for k in _keys}
    _lock = asyncio.Lock()
    
    if _keys:
        masked = [k[-6:] for k in _keys]
        logger.info(f"api_keys: pool size {len(_keys)} (last 6 chars: {masked})")
    else:
        logger.warning("api_keys: NO GOOGLE_API_KEY(S) configured")


def is_available() -> bool:
    _init()
    return len(_keys) > 0


def pool_size() -> int:
    _init()
    return len(_keys)


async def get_key() -> Optional[str]:
    """Round-robin + skip throttled. Returns None if no key available.
    
    Strategy:
    1. Try next key (round-robin)
    2. If throttled (cooldown not expired) → skip
    3. After scanning all → return least-recently-throttled (best of bad)
    """
    _init()
    if not _keys:
        return None
    
    global _round_robin_idx
    async with _lock:
        now = time.time()
        # Pass 1: find unthrottled key
        for _ in range(len(_keys)):
            key = _keys[_round_robin_idx]
            _round_robin_idx = (_round_robin_idx + 1) % len(_keys)
            m = _metrics[key]
            if m.throttled_until <= now:
                m.calls += 1
                m.last_used_at = now
                return key
        # Pass 2: all throttled — return one with oldest throttle (likely freshest)
        oldest_key = min(_keys, key=lambda k: _metrics[k].throttled_until)
        m = _metrics[oldest_key]
        m.calls += 1
        m.last_used_at = now
        return oldest_key


async def mark_throttled(key: str, cooldown_sec: int = 60):
    """Mark key as throttled (429) — skip for cooldown_sec."""
    _init()
    async with _lock:
        if key not in _metrics:
            return
        _metrics[key].throttled_until = time.time() + cooldown_sec
        _metrics[key].errors_429 += 1
        logger.warning(f"api_keys: key ...{key[-6:]} throttled for {cooldown_sec}s")


async def mark_success(key: str):
    """Increment success counter."""
    _init()
    async with _lock:
        if key in _metrics:
            _metrics[key].success_count += 1


async def mark_error(key: str):
    """Mark non-429 error."""
    _init()
    async with _lock:
        if key in _metrics:
            _metrics[key].errors_other += 1


def get_diagnostics() -> dict:
    """For admin /api/admin/api-keys/diagnostics endpoint."""
    _init()
    now = time.time()
    return {
        "pool_size": len(_keys),
        "round_robin_idx": _round_robin_idx,
        "keys": [
            {
                "key_suffix": k[-6:],
                "calls": _metrics[k].calls,
                "errors_429": _metrics[k].errors_429,
                "errors_other": _metrics[k].errors_other,
                "success_count": _metrics[k].success_count,
                "throttled_until": _metrics[k].throttled_until,
                "throttled_now": _metrics[k].throttled_until > now,
                "last_used_ago_sec": int(now - _metrics[k].last_used_at) if _metrics[k].last_used_at else None,
            }
            for k in _keys
        ],
    }
```

#### 2. `backend/gemini_direct.py` (~250 lines)
Direct Gemini API client — chat + embedding + multimodal

```python
"""Direct Gemini API client (bypasses OpenRouter).

Replaces OpenRouter routing สำหรับ Gemini-specific calls:
- chat(messages, model) → text completion
- embed(texts, model) → embedding vectors
- multimodal(file_path, prompt) → file analysis

Features:
- Auto key rotation via api_keys module
- Retry on 429 (mark throttled + try next key, max 3 attempts)
- Same response shape as llm.py for drop-in
- Token usage tracking (for admin metrics)

Plan ref: .agent-memory/plans/multi-key-gemini-migration.md
"""
import asyncio
import json
import logging
from typing import Optional

from .api_keys import get_key, mark_throttled, mark_success, mark_error, is_available
from .config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Gemini models for direct path
GEMINI_CHAT_MODEL_FLASH = "gemini-2.5-flash"
GEMINI_CHAT_MODEL_PRO = "gemini-2.5-pro"  # if user has access


async def chat(
    system_prompt: str,
    user_prompt: str,
    model: str = GEMINI_CHAT_MODEL_FLASH,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    max_retries: int = 3,
) -> str:
    """Chat completion via direct Gemini API.
    
    Returns response text (compatible with llm.py call_llm shape).
    Raises Exception if all keys exhausted.
    """
    if not is_available():
        raise RuntimeError("gemini_direct: no GOOGLE_API_KEY(S) configured")
    
    from google import genai
    
    last_err: Exception | None = None
    for attempt in range(max_retries):
        key = await get_key()
        if not key:
            raise RuntimeError("gemini_direct: get_key returned None")
        
        try:
            client = genai.Client(api_key=key)
            # Run in thread (SDK is sync)
            def _call():
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]}
                    ],
                    config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                )
                return response.text
            
            text = await asyncio.to_thread(_call)
            await mark_success(key)
            return text
        
        except Exception as e:
            err_msg = str(e)
            last_err = e
            # 429 detection
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                await mark_throttled(key, cooldown_sec=60)
                logger.warning(f"gemini_direct: key ...{key[-6:]} 429, retry {attempt+1}/{max_retries}")
                await asyncio.sleep(min(2 ** attempt, 8))  # backoff
                continue
            
            # Other errors — mark and propagate
            await mark_error(key)
            logger.error(f"gemini_direct: key ...{key[-6:]} error: {err_msg[:100]}")
            raise
    
    raise RuntimeError(f"gemini_direct: all retries exhausted, last error: {last_err}")


async def chat_json(
    system_prompt: str,
    user_prompt: str,
    model: str = GEMINI_CHAT_MODEL_FLASH,
    temperature: float = 0.2,
) -> dict:
    """Chat returning JSON (parse + retry on parse fail)."""
    raw = await chat(system_prompt, user_prompt, model=model, temperature=temperature)
    return _parse_json_response(raw)


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response (handle ```json fences)."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip markdown fences
        lines = cleaned.split("\n")
        if len(lines) > 2:
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Find JSON object in response
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start:end+1])
        raise


async def embed_text(text: str, model: str = None) -> list[float]:
    """Embed single text. Returns vector as list[float].
    
    Same shape as embeddings.py:embed_text (np.ndarray → caller converts).
    """
    if not is_available():
        raise RuntimeError("gemini_direct: no GOOGLE_API_KEY(S) configured")
    
    from google import genai
    use_model = model or EMBEDDING_MODEL  # "gemini-embedding-001" (3072-d)
    
    last_err = None
    for attempt in range(3):
        key = await get_key()
        if not key:
            raise RuntimeError("gemini_direct: get_key returned None")
        
        try:
            client = genai.Client(api_key=key)
            def _call():
                r = client.models.embed_content(model=use_model, contents=text)
                return r.embeddings[0].values
            values = await asyncio.to_thread(_call)
            await mark_success(key)
            return values
        except Exception as e:
            err_msg = str(e)
            last_err = e
            if "429" in err_msg or "quota" in err_msg.lower():
                await mark_throttled(key, cooldown_sec=60)
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            await mark_error(key)
            raise
    
    raise RuntimeError(f"gemini_direct.embed_text: all retries exhausted: {last_err}")


async def embed_batch(texts: list[str], model: str = None) -> list[list[float]]:
    """Embed multiple texts in 1 API call (Gemini batch supported)."""
    if not texts:
        return []
    if not is_available():
        raise RuntimeError("gemini_direct: no GOOGLE_API_KEY(S) configured")
    
    from google import genai
    use_model = model or EMBEDDING_MODEL
    
    last_err = None
    for attempt in range(3):
        key = await get_key()
        if not key:
            raise RuntimeError("gemini_direct: get_key returned None")
        
        try:
            client = genai.Client(api_key=key)
            def _call():
                r = client.models.embed_content(model=use_model, contents=texts)
                return [e.values for e in r.embeddings]
            results = await asyncio.to_thread(_call)
            await mark_success(key)
            return results
        except Exception as e:
            err_msg = str(e)
            last_err = e
            if "429" in err_msg or "quota" in err_msg.lower():
                await mark_throttled(key, cooldown_sec=60)
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            await mark_error(key)
            raise
    
    raise RuntimeError(f"gemini_direct.embed_batch: all retries exhausted: {last_err}")


# Multimodal — TODO Phase D (เริ่มจาก chat + embed ก่อน)
```

#### 3. `backend/_test_api_keys.py` (~100 lines)
Unit tests สำหรับ key rotation logic (ฟ้าเขียน)

### MODIFY files (5)

#### `backend/config.py`
- เพิ่ม `EMBEDDING_MODEL` default = `"gemini-embedding-001"` (เดิม `text-embedding-004`)
- เพิ่ม `USE_DIRECT_GEMINI` flag (default ON เพราะ embeddings ต้องใช้)
- เพิ่ม `USE_DIRECT_FOR_SUMMARY` flag (default OFF — opt-in)
- เพิ่ม `USE_DIRECT_FOR_CHAT` flag (default OFF — opt-in)
- เพิ่ม `DIRECT_GEMINI_CHAT_MODEL` config (`gemini-2.5-flash` default)
- เพิ่ม `KEY_THROTTLE_COOLDOWN_SEC` config (60 default)

#### `backend/embeddings.py`
- ใช้ `api_keys.get_key()` แทน module-level `_genai_client`
- เปลี่ยน lazy init จาก single key → pool-based
- Default model → `gemini-embedding-001` (จาก config)
- Embedding vector dim เปลี่ยน 768 → 3072 (note: storage 4× larger but OK)

#### `backend/llm.py`
- เพิ่ม fallback routing: ถ้า `USE_DIRECT_FOR_SUMMARY=true` → call `gemini_direct.chat_json()`
- เก็บ OpenRouter path ไว้เป็น fallback (try direct → catch error → fall back)
- Logging: ระบุว่า call ใช้ direct หรือ openrouter

#### `backend/ai_ingest.py`
- เปลี่ยนจาก `os.getenv("GOOGLE_API_KEY")` → ใช้ `api_keys.get_key()` (สำหรับ multimodal rotation)
- Multimodal Files API: ใช้ key เดียวต่อ file upload session (ไม่ rotate ภายในไฟล์ — Gemini Files state ผูกกับ key)

#### `backend/main.py`
- เพิ่ม admin endpoint: `GET /api/admin/api-keys/diagnostics` → return key pool stats
- เพื่อให้ user ดูได้ว่า key ไหนใช้บ่อย key ไหนติด throttle

### MODIFY files — **NEW: more callers found** (Explore audit)

ไฟล์ด้านล่างเรียก llm.py functions — refactor ที่ llm.py เพียงจุดเดียว → **ไม่ต้องแก้ callers** (transparent). แต่ต้อง smoke test ทั้งหมดหลัง migration:

| File:Line | Function | Test scope |
|---|---|---|
| `backend/organizer.py:330,382,474,517` | summary + cluster + map-reduce | Phase C scope |
| `backend/clustering.py:335` | LLM cluster label | Phase C scope |
| `backend/context_packs.py:331` | pack summary | Phase C scope |
| `backend/metadata.py:60` | metadata enrich (tags, sensitivity) | Phase C scope |
| `backend/graph_builder.py:177,245` | entity/relation extract | Phase C scope |
| `backend/extraction.py:587,620,636` | **map-reduce summary** (most LLM calls!) | Phase C+D critical |
| `backend/retriever.py:426,464` | chat context routing | Phase D scope |
| `backend/relations.py:179` | relation extract | Phase C scope |
| `backend/ai_pack_builder.py:290,431` | AI pack selection | Phase C scope |

**Total**: 9 callers · all use `llm.py` central → **0 code changes** ใน callers (เปลี่ยนหลังบ้านอย่างเดียว)

#### `backend/processors/startup_probe.py` (Gap #5)
- Line 71-75: `os.getenv("GOOGLE_API_KEY")` boot probe
- เปลี่ยนเป็น `api_keys.is_available()` + report pool size

### MIGRATIONS — **schema additive** (Gap #1)

ตอน v1 plan บอก "none" แต่ Explore audit เจอว่า Files API affinity ต้องการ tracking:

```python
# backend/database.py — File model
class File(Base):
    # ... existing columns ...
    
    # v11.1.0 (multi-key migration): track which Gemini API key uploaded this file
    # — needed for Files API state coupling (upload + analyze + delete must use SAME key)
    # Stores last 6 chars of key (avoid leaking full key in DB)
    gemini_api_key_suffix = Column(String(8), default="")
```

Migration block (pattern v7.5.0):
```python
try:
    cursor = await db.execute("PRAGMA table_info(files)")
    file_cols_v111 = {row[1] for row in await cursor.fetchall()}
    if "gemini_api_key_suffix" not in file_cols_v111:
        await db.execute("ALTER TABLE files ADD COLUMN gemini_api_key_suffix TEXT DEFAULT ''")
        migrated = True
        print("  → Added: files.gemini_api_key_suffix (v11.1.0 — Files API key affinity)")
except Exception as e:
    print(f"  ⚠️ v11.1.0 files migration warning: {e}")
```

**Backward compat**: empty string = legacy file (uploaded ก่อน rotation) → ai_ingest.py:cleanup ใช้ key แรก (best-effort)

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### 📦 Phase A — Infrastructure (4-6 ชั่วโมง)

#### Step A.1 — Create `backend/api_keys.py`
- Implement KeyMetrics dataclass
- Implement get_key/mark_throttled/mark_success/mark_error/get_diagnostics
- Thread-safe ด้วย asyncio.Lock
- Init lazy จาก `GOOGLE_API_KEYS` env (comma-separated)
- Fallback ไป `GOOGLE_API_KEY` single (backward compat)

**🔬 Verify gate:**
- [ ] Unit test: 4 keys → round-robin → ทุก key ได้ใช้
- [ ] Throttle test: mark key → skip 60s → กลับมาใช้ได้
- [ ] All throttled: return least-recently-throttled (best of bad)
- [ ] Empty pool: return None gracefully
- [ ] Diagnostics endpoint: shape ถูก

#### Step A.2 — Create `backend/gemini_direct.py`
- Implement chat() with retry + key rotation
- Implement chat_json() with JSON parsing
- Implement embed_text() / embed_batch()
- (Skip multimodal สำหรับ Phase A — ทำ Phase D ภายหลัง)

**🔬 Verify gate:**
- [ ] Chat 1 call ผ่าน (auth + response)
- [ ] Chat 20 concurrent calls — กระจาย 4 keys
- [ ] Embed single — 3072-d vector returned
- [ ] Embed batch (5 texts) — 5 vectors returned
- [ ] 429 retry: simulate throttle → retry with different key

#### Step A.3 — Add config flags
แก้ `backend/config.py`:
```python
USE_DIRECT_GEMINI: bool = _env_bool("USE_DIRECT_GEMINI", "true")  # default ON เพราะ embed ต้อง
USE_DIRECT_FOR_SUMMARY: bool = _env_bool("USE_DIRECT_FOR_SUMMARY", "false")
USE_DIRECT_FOR_CHAT: bool = _env_bool("USE_DIRECT_FOR_CHAT", "false")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")  # ⚠️ CHANGE
KEY_THROTTLE_COOLDOWN_SEC: int = int(os.getenv("KEY_THROTTLE_COOLDOWN_SEC", "60"))
```

**🔬 Verify gate:**
- [ ] Default flags: USE_DIRECT_GEMINI=true, summary=false, chat=false
- [ ] EMBEDDING_MODEL default = "gemini-embedding-001"

---

### 🔵 Phase B — Embeddings migration (2 ชั่วโมง)

#### Step B.1 — Update `backend/embeddings.py`
แทน module-level `_genai_client`:
```python
# OLD
_genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# NEW
from . import gemini_direct  # uses api_keys pool internally
```

`embed_text()`:
```python
# OLD
def _call():
    return _genai_client.models.embed_content(...)
values = await asyncio.to_thread(_call)

# NEW
values = await gemini_direct.embed_text(text)
```

#### Step B.2 — Update `embed_files()` cache logic
- Cache invalidation: เพิ่ม model name comparison (เปลี่ยน 768-d → 3072-d → embeddings เก่าไม่ valid)
- ถ้า `file.embedding_model != EMBEDDING_MODEL` → re-embed

**🔬 Verify gate:**
- [ ] Local: embed 5 files → ดู key rotation log
- [ ] Cache: re-run → cache HIT (เพราะ model name match)
- [ ] Model change: ตั้ง EMBEDDING_MODEL=`models/gemini-embedding-001` → re-embed all
- [ ] Storage: vector_dim เปลี่ยน 768 → 3072, BLOB ขยายตาม

---

### 🟢 Phase C — Summary migration (4-6 ชั่วโมง)

#### Step C.1 — Add direct route in `backend/llm.py`

```python
async def call_llm_pro(system_prompt, user_prompt, temperature=0.3, max_tokens=8192):
    from .config import USE_DIRECT_FOR_SUMMARY
    if USE_DIRECT_FOR_SUMMARY:
        try:
            from .gemini_direct import chat
            return await chat(system_prompt, user_prompt,
                              model=DIRECT_GEMINI_CHAT_MODEL,
                              temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            logger.warning(f"call_llm_pro: direct failed ({e}), falling back to OpenRouter")
            # fall through to OpenRouter
    return await _call_openrouter(LLM_MODEL_PRO, system_prompt, user_prompt, temperature, max_tokens)
```

#### Step C.2 — Same for `call_llm_json` (JSON variant)

#### Step C.3 — Test summary path

**🔬 Verify gate:**
- [ ] Smoke test: USE_DIRECT_FOR_SUMMARY=true → summary call works
- [ ] Concurrency 20: 20 parallel summary calls succeed (4 keys × 5 each)
- [ ] Fallback: invalidate keys → fallback ไป OpenRouter ทันที
- [ ] Cost log: per-key call count + tokens

---

### 🟣 Phase D — Chat + Multimodal (4-6 ชั่วโมง)

#### Step D.1 — Chat (call_llm)
Same pattern as call_llm_pro แต่ใช้ Flash model

#### Step D.2 — Multimodal (ai_ingest)
- Gemini Files API state ผูกกับ key ที่ upload
- Strategy: per-file ใช้ key เดียวตลอด workflow (upload + analyze + delete)
- รักษา rotation ที่ระดับ file (1 file = 1 key throughout)

**🔬 Verify gate:**
- [ ] Chat: 10 messages with USE_DIRECT_FOR_CHAT=true → ทำงาน
- [ ] Multimodal: upload audio → transcribe → cleanup (1 key)
- [ ] PDF Gemini fallback: 50-page PDF → works

---

### 🟡 Phase E — Polish + Deploy (2-4 ชั่วโมง)

#### Step E.1 — Admin diagnostics
แก้ `backend/main.py`:
```python
@app.get("/api/admin/api-keys/diagnostics")
async def api_keys_diagnostics(admin: User = Depends(require_admin)):
    from .api_keys import get_diagnostics
    return get_diagnostics()
```

#### Step E.2 — Fly secrets setup
```bash
# Set 4 keys (comma-separated)
flyctl secrets set GOOGLE_API_KEYS="key1,key2,key3,key4"

# Enable direct routes incrementally
flyctl secrets set USE_DIRECT_GEMINI=true       # Embeddings (auto-needed)
flyctl secrets set USE_DIRECT_FOR_SUMMARY=true  # Summary
flyctl secrets set USE_DIRECT_FOR_CHAT=true     # Chat (optional)

# Increase concurrency
flyctl secrets set SUMMARY_CONCURRENCY=20
```

#### Step E.3 — Update memory + docs
- `pipeline-state.md` → state = built_pending_review
- `inbox/for-ฟ้า.md` → MSG-V11-MULTIKEY-REVIEW-REQUEST
- README — add section: "Multi-key Gemini setup"

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Unit tests (ฟ้าเขียน)

#### `backend/_test_api_keys.py` (~10 tests)
- `test_round_robin_4_keys` — ยิง 8 ครั้ง → key 1234,1234
- `test_skip_throttled_key` — mark key 2 throttled → ครั้งถัดไปข้าม
- `test_throttle_expires` — รอ 61s → key กลับมาใช้
- `test_all_throttled_returns_oldest` — throttle ทั้ง 4 → ได้ตัวที่ throttle นานที่สุด
- `test_empty_pool` — no GOOGLE_API_KEYS → get_key() = None
- `test_single_key_fallback` — `GOOGLE_API_KEY=x` (no plural) → pool size 1
- `test_diagnostics_shape` — return dict มี keys[] + per-key metrics
- `test_concurrent_access` — 100 parallel get_key() → thread-safe (no race)
- `test_mark_success_increments` — call mark_success × 5 → counter = 5

#### `backend/_test_gemini_direct.py` (~10 tests)
- `test_chat_returns_text` — mock genai → return string
- `test_chat_429_retries_different_key` — 1st key 429 → 2nd key works
- `test_chat_all_keys_429_raises` — 3 retries exhausted → raise
- `test_chat_json_parses` — mock returns "{...}" → dict
- `test_chat_json_handles_fences` — ```json {} ``` → parses correctly
- `test_embed_text_returns_3072` — mock returns 3072-d → list[float]
- `test_embed_batch_5_texts` — 5 texts → 5 vectors

### Integration tests (ฟ้ารัน manual)

#### Scenario A: Smoke (USE_DIRECT_GEMINI=true)
```
local backend start
embed 5 files via embeddings.embed_files()
→ ดู log: "api_keys: key ...XXXXXX used"
→ ทุก key ได้ใช้
```

#### Scenario B: Summary concurrency 20
```
USE_DIRECT_FOR_SUMMARY=true
SUMMARY_CONCURRENCY=20
organize 30 files
→ ดู: 4 keys ใช้ ~7-8 calls each
→ ไม่มี 429 (หรือ ≤ 1-2 ตัว retry ทัน)
```

#### Scenario C: Throttle simulation
```
Manually force throttle:
  from backend.api_keys import mark_throttled
  await mark_throttled("key1", 60)
  await mark_throttled("key2", 60)
→ Subsequent calls ใช้ key3 + key4
→ หลัง 60s → key1, key2 กลับมา
```

#### Scenario D: Fallback verify
```
USE_DIRECT_FOR_SUMMARY=true
+ ทำให้ทุก key ใช้ไม่ได้ (เปลี่ยน env ชั่วคราวเป็น invalid)
→ summary call → catch Exception → fallback OpenRouter
→ Verify log "direct failed, falling back"
```

#### Scenario E: Admin diagnostics
```
GET /api/admin/api-keys/diagnostics → admin auth → return shape:
{
  "pool_size": 4,
  "round_robin_idx": 12,
  "keys": [
    {"key_suffix": "XkVrXA", "calls": 23, "errors_429": 1, ...},
    ...
  ]
}
```

### Browser test
- Login → organize ไฟล์ 20 ตัว
- ดู Fly logs สำหรับ "api_keys: key ...XXX used" — distributed across 4
- เทียบกับเดิม (USE_DIRECT_FOR_SUMMARY=false) — ดูความเร็ว

---

## ⚠️ Risks / Open Questions

### Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Google detect 4 keys จาก IP เดียว → revoke all | M | H | ใช้คนละ Google account; rotate ผ่าน Fly secret + monitor |
| R2 | Gemini API response shape ไม่ตรงกับ OpenRouter → break parsing | M | H | Adapter layer + extensive test |
| R3 | gemini-embedding-001 dim 3072 vs 768 → existing embedding cache invalid | H | M | Auto re-embed when model mismatch; existing rows have model='' → re-embed |
| R4 | Multimodal Files API ผูก state กับ key → rotation ล้ม | M | M | Per-file pin key; ไม่ rotate ภายในไฟล์ |
| R5 | Throttle cascading: 4 keys 429 พร้อมกัน → all queue stuck | L | H | Fallback to OpenRouter + alert admin |
| R6 | Storage: 3072-d × 4 bytes × 1000 files = 12 MB extra | L | L | Acceptable |
| R7 | Cost migration: OpenRouter → Gemini direct ราคาต่าง | L | M | Track per-call cost ใน diagnostics |
| R8 | Free tier daily limit (1500 req/day per key) → 6000 total | L | M | Monitor + alert at 80% |

### Open Questions (รอ user ตัดสิน)

#### Q1 — Default flag rollout
- (A) USE_DIRECT_GEMINI=true (default) — embeddings ต้องใช้
- (B) USE_DIRECT_FOR_SUMMARY=false (default OFF) — opt-in
- (C) USE_DIRECT_FOR_CHAT=false (default OFF) — opt-in
- **ผมแนะนำ A=on, B=off (test ก่อน), C=off**

#### Q2 — Multi-key safety
- ใช้ 4 keys นี้ทันที (เร็ว แต่เสี่ยง revoke)?
- หรือ revoke + generate ใหม่ทั้งหมด แล้วค่อย deploy?
- **แนะนำ: revoke 4 keys นี้ + สร้างใหม่ (ปลอดภัยกว่า — เปิดเผยใน chat แล้ว)**

#### Q3 — Existing embedding cache
- ไฟล์เก่าที่ embed ด้วย text-embedding-004 (ถ้ามี) → ต้อง re-embed all?
- Or: keep old cache + only new files use new model?
- **แนะนำ: re-embed all บน first organize call (one-time cost ~$0.05 total)**

#### Q4 — Multimodal scope
- ทำ Phase D ทันที (เร็วขึ้น)?
- หรือทำ A-C ก่อน + Phase D หลัง validate (ปลอดภัย)?
- **แนะนำ: A-C ก่อน, D หลัง 1 สัปดาห์ stable**

#### Q5 — Fallback strategy
- Direct fail → OpenRouter (current proposal)
- หรือ Direct fail → error → user retry?
- **แนะนำ: OpenRouter fallback — graceful degradation**

#### Q6 — Per-user vs global keys
- ใช้ 4 keys ของ admin ให้ทุก user (global pool)?
- หรือ user ให้ keys ของตัวเอง (BYOK)?
- **แนะนำ: Global pool — simpler, admin จ่ายค่า, user free**

---

## 📌 Notes for เขียว

### Critical reminders

1. **🔐 SECURITY ก่อน implement**: revoke 4 keys ที่ user แชร์ในแชท + generate ใหม่ที่ AI Studio + set ผ่าน flyctl
2. **กรอง keys ใน log** — `logger.info(f"key {key[-6:]}")` ห้าม log full key
3. **Test แต่ละ phase ก่อนทำ phase ถัดไป** — ฟ้า review per phase
4. **Feature flag default OFF ทุก phase ใหม่** (ยกเว้น USE_DIRECT_GEMINI=true เพราะ embedding ต้องใช้)
5. **Rollback ง่าย**: flip flag → restart machine → 30 วินาที

### Gotchas

- `google.genai` SDK เป็น sync — wrap with `asyncio.to_thread()`
- Gemini `embed_content` รับ list[str] สำหรับ batch (ไม่ใช่ string เดียว)
- Response object: `r.embeddings[0].values` (not `r.embedding`)
- Error message ไม่ตรงตาม OpenAI format — parse จาก str(e)
- 429 detection: ค้นหา "429" หรือ "RESOURCE_EXHAUSTED" หรือ "quota" ใน error message
- Files API state ผูก key — ห้าม upload ด้วย key A แล้ว get ด้วย key B

### Performance baselines

| Metric | OpenRouter (current) | Direct + 4 keys (target) |
|---|---|---|
| Summary 30 files | 5-10 นาที | 1.5-3 นาที |
| Embed 30 files | N/A (broken) | 30 วินาที |
| Concurrent summary | 5 | 20 |
| Free tier req/day | OpenRouter ~few hundred | 4 × 1500 = 6000 |

### Timeline

```
Day 1: Phase A (infrastructure)
  Morning: api_keys.py + tests
  Afternoon: gemini_direct.py + tests
  Evening: config flags + integration

Day 2: Phase B + C (embeddings + summary)
  Morning: Embeddings migration + verify
  Afternoon: Summary direct route + smoke test
  Evening: Deploy Phase B + C (USE_DIRECT_GEMINI=true, USE_DIRECT_FOR_SUMMARY=true)

Day 3: Phase D + E (chat + multimodal + polish)
  Morning: Chat direct route
  Afternoon: Multimodal + admin diagnostics
  Evening: Final deploy + ฟ้า handoff
```

Total: ~3 วัน เขียว + 0.5 วัน ฟ้า

---

## 📋 Done Criteria (Overall)

### Functional
- [ ] api_keys.py pool — 4 keys round-robin works
- [ ] gemini_direct.py — chat + embed work with rotation
- [ ] embeddings.py — uses gemini_direct (no module-level client)
- [ ] llm.py — call_llm_pro routes to direct ถ้า flag ON
- [ ] Fallback to OpenRouter works (graceful degrade)
- [ ] Admin /api/admin/api-keys/diagnostics — return stats
- [ ] Feature flags rollout: A=ON, B=OFF→ON sequential, C=OFF→ON

### Performance
- [ ] Summary 30 files: < 3 นาที (was: 5-10)
- [ ] SUMMARY_CONCURRENCY=20 stable: no 429 cascades
- [ ] 4 keys distributed evenly (per-key calls ratio 1:1 ± 20%)
- [ ] Throttle recovery: key throttled → cooldown → resume in 60s

### Quality
- [ ] Unit tests 20+ tests pass (api_keys + gemini_direct)
- [ ] No regression: USE_DIRECT_FOR_SUMMARY=false → OpenRouter path unchanged
- [ ] Response shape compatible (organizer.py ไม่ต้องเปลี่ยน)
- [ ] Logs ปลอดภัย (keys masked)

### Production
- [ ] All 4 keys configured via flyctl secrets
- [ ] Old keys (ที่แชร์ในแชท) revoked
- [ ] New keys (generated หลังจาก) replaced
- [ ] Production version bumped (v10.0.22 → v10.0.23?)

---

## 🔖 Memory Updates ที่ต้องทำตอนเสร็จ Plan

1. `pipeline-state.md` → state = "plan_pending_approval · multi-key migration"
2. `active-tasks.md` → add task "Multi-key Gemini migration"
3. Notify เขียว ผ่าน `inbox/for-เขียว.md` หลัง user approve

---

## 🧪 Master Test Matrix — Per-Milestone Verify Gates (Section ใหม่ v2)

> **ทุก step มี Verify gate** — เขียวห้าม commit ขั้นถัดไปถ้า "Verify" ไม่ผ่าน. ฟ้าใช้ matrix นี้ใน review.

### Phase A — Infrastructure (Day 1)

| Step | Milestone | Verify gate | Effort |
|---|---|---|---|
| **A.1** | `backend/api_keys.py` (key pool manager) | Unit tests `_test_api_keys.py` 10 cases · round-robin fairness · throttle state machine | 2 hr |
| **A.2** | `backend/gemini_direct.py` (SDK wrapper) | Unit tests `_test_gemini_direct.py` 10 cases · chat works · embed works · 429 retry works | 2 hr |
| **A.2.5** | Model name alias table | Unit test: `"google/gemini-3-flash-preview"` → `"gemini-2.5-flash"` · unknown model → pass-through with warning | 30 min |
| **A.3** | Schema: `File.gemini_api_key_suffix` column (Gap #1) | Migration `init_db()` 3-scenarios pass (fresh/ALTER/rerun) · idempotent | 30 min |
| **A.4** | Config flags (5 new) | Test_config 6 cases · defaults correct · env override works | 30 min |

**🔬 Phase A Verify**:
- [ ] 30+ unit tests PASS (api_keys + gemini_direct + alias + schema)
- [ ] No code path active yet (flags OFF) — production unchanged

### Phase B — Embeddings (Day 2 morning)

| Step | Milestone | Verify gate | Effort |
|---|---|---|---|
| **B.1** | `embeddings.py` use gemini_direct | Manual: embed 5 files local · ดู log key rotation · cache HIT on rerun | 1 hr |
| **B.2** | Cache invalidation by model | Manual: change `EMBEDDING_MODEL` → all files re-embed once | 30 min |
| **B.3** | Migration script: re-embed legacy files | Run `scripts/migrate_to_v11.py` · verify all File.embedding_vector populated with new model | 1 hr |

**🔬 Phase B Verify**:
- [ ] Local: 20 files embedded → 4 keys used (~5 each) — log evidence
- [ ] Re-run: cache HIT 20/20 (no API calls)
- [ ] Model change: cache MISS 20/20 → all re-embed
- [ ] All 161 Phase 0/1 tests still PASS

### Phase C — Summary Migration (Day 2 afternoon)

| Step | Milestone | Verify gate | Effort |
|---|---|---|---|
| **C.1** | `llm.py:call_llm_pro` route to direct | Smoke test: USE_DIRECT_FOR_SUMMARY=true · 1 organize call works | 2 hr |
| **C.2** | `llm.py:call_llm_json` route to direct (with JSON parse) | Smoke: organize 5 files · structured output ok | 1 hr |
| **C.3** | Fallback verify | Disable all keys (invalid env) · summary call → fallback OpenRouter | 30 min |
| **C.4** | Concurrency raise | `SUMMARY_CONCURRENCY=20` · 30 files no 429 cascade | 1 hr |

**🔬 Phase C Verify**:
- [ ] Smoke: organize 30 files with flag ON → no error
- [ ] All 4 keys used (call distribution check via diagnostics)
- [ ] Fallback path tested (manually invalid keys → OpenRouter used)
- [ ] Token usage log includes per-key suffix

### Phase D — Chat + Multimodal (Day 3 morning)

| Step | Milestone | Verify gate | Effort |
|---|---|---|---|
| **D.1** | `llm.py:call_llm` (chat) route to direct | Chat 10 turns works · response sensible | 2 hr |
| **D.2** | Multimodal Files API key affinity (Gap #1) | Upload audio → analyze → delete · all 3 use SAME key (verify via log) | 2 hr |
| **D.3** | PDF Gemini fallback | 50-page PDF process · works end-to-end | 1 hr |

**🔬 Phase D Verify**:
- [ ] Chat round-trip: USE_DIRECT_FOR_CHAT=true → reply makes sense
- [ ] Multimodal key affinity: log shows same key for upload + analyze + delete (1 file)
- [ ] PDF (audio/video too if available) ingest works

### Phase E — Polish + Deploy (Day 3 afternoon)

| Step | Milestone | Verify gate | Effort |
|---|---|---|---|
| **E.1** | Admin endpoint `/api/admin/api-keys/diagnostics` | curl returns pool stats · admin auth required | 30 min |
| **E.2** | Logging: mask keys (only last 6 chars) | grep code · no full keys in any log statement | 15 min |
| **E.3** | Fly deploy + smoke prod | curl /health · 4 keys set · diagnostics endpoint OK | 1 hr |
| **E.4** | E2E browser regression | All v10.x flows ทำงาน · no console errors · no 5xx | 1 hr |

**🔬 Phase E Verify** (final sign-off by ฟ้า):
- [ ] Production deploys cleanly · `/health` v10.0.22+ live
- [ ] Diagnostics endpoint returns 4 keys metrics
- [ ] Log audit: no plaintext keys exposed
- [ ] Performance benchmark: organize 30 files < 3 min (target)
- [ ] Cost benchmark: token usage tracked per key
- [ ] All previous tests (161 v11 + new Phase A-E tests) PASS

---

### 📋 Continuous Regression Checklist (รันทุก phase deploy)

#### v10.x features ที่ห้าม regression:
- [ ] Login (email/pass + LINE + rate-limit 5→429)
- [ ] Upload file (small + big + multimodal)
- [ ] Organize 5 files works (legacy or hybrid)
- [ ] Chat with citation
- [ ] Drive OAuth (BYOS) + sync
- [ ] Admin panel + LINE webhook
- [ ] Unified error response (detail + error.code)
- [ ] Retry chunk fail (v10.0.14 — still works in new path)
- [ ] No "บางส่วนถูกตัด" badge (v10.0.13)

#### New v11 + Multi-key features ที่ต้องเช็ค:
- [ ] embed_files() cache HIT/MISS correct
- [ ] cluster_files_hybrid works with new embeddings (gemini-embedding-001)
- [ ] 4-key rotation balanced
- [ ] Throttle expiry works
- [ ] Fallback to OpenRouter on all-throttled

---

### 🎯 Test Data Tiers (สำหรับ benchmark per phase)

| Tier | Size | Use case |
|---|---|---|
| Tier 1 (smoke) | 5 ไฟล์ | Per-step gate ก่อน commit |
| Tier 2 (regression) | 30 ไฟล์ | End-of-phase verify |
| Tier 3 (concurrency) | 100 ไฟล์ | Phase C stress test |
| Tier 4 (stress) | 500 ไฟล์ | Phase E final verify |

---

### 🚦 Per-Phase Stop Criteria (ฟ้า ตัดสิน)

แต่ละ phase ฟ้า มี veto:
- 🟢 **APPROVE** → flip next flag · ไป phase ถัดไป
- 🟡 **NEEDS_CHANGES** → list bugs · เขียวแก้ · re-review
- 🔴 **BLOCK** → revert flag · investigate ก่อน proceed

**Stop-the-line conditions** (Phase D หรือ E):
- 🚨 Files API affinity bug → orphan file_ids ใน Gemini account
- 🚨 Token logging leak (full key in log)
- 🚨 All-throttle cascade → fallback ไม่ทำงาน
- 🚨 Cost spike > 5× baseline

---

## ✅ Approval Checklist

ก่อน approve:
- [ ] เห็นด้วยกับ scope (3 phases A-E, 2-3 วัน)?
- [ ] เห็นด้วยกับ rollout: USE_DIRECT_GEMINI=ON, SUMMARY=OFF→ON, CHAT=OFF→ON?
- [ ] ตอบ Q1-Q6 (default flags, key revoke, cache, multimodal, fallback, key sharing)?
- [ ] OK กับ revoke 4 keys ปัจจุบัน + generate ใหม่?
- [ ] OK ทำ Phase 1 รอ pending → ทำ multi-key migration ก่อน?

---

**Plan Author:** 🔴 แดง (Daeng)
**Plan Date:** 2026-05-17
**Plan Status:** `draft` — รอ user approve
**Dependency:** Phase 1 hybrid clustering ต้องการ embedding ที่ทำงาน → ทำ migration นี้ก่อน
