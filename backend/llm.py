"""LLM integration via Gemini direct API (OpenAI-compatible endpoint) — dual model support.

v10.0.23: ย้ายจาก OpenRouter → Gemini direct. เหตุผล: Tier 1 Postpay ให้ 2,000 RPM/key
(เทียบ OpenRouter free ~10 RPM), latency ต่ำลง, ไม่ต้องจ่าย markup.

Models:
- Flash (LLM_MODEL): Fast & cheap — used for chat, lightweight queries
- Pro (LLM_MODEL_PRO): Smart & powerful — used for organize, summarize, text cleanup

Failover: ถ้า primary key เจอ 429/5xx → retry ด้วย backup key อัตโนมัติ.
Backup key ว่าง = no-op failover (เด้ง error เลย).
"""
import httpx
import json
import logging
from .config import (
    GEMINI_API_KEY,
    GEMINI_API_KEY_BACKUP,
    GEMINI_BASE_URL,
    LLM_MODEL,
    LLM_MODEL_PRO,
)
from .extraction import strip_surrogates

logger = logging.getLogger(__name__)


def _key_suffix(key: str) -> str:
    """Last 4 chars of API key for log identification (no full key leak)."""
    return key[-4:] if key and len(key) >= 4 else "????"


async def _call_gemini_once(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Single attempt with one API key. Raises on non-200."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(GEMINI_BASE_URL, headers=headers, json=payload)

        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Gemini API error {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )

        data = response.json()
        if "choices" not in data or len(data["choices"]) == 0:
            logger.error(f"Unexpected Gemini response: {data}")
            raise Exception("Unexpected Gemini response format")

        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content")
        finish_reason = choice.get("finish_reason")
        usage = data.get("usage", {})

        # Gemini 2.5+ ใช้ thinking tokens — ถ้า max_tokens น้อยเกินไป thinking จะ
        # กิน budget หมดก่อนตอบ → content=None, finish_reason="length", completion_tokens=0
        if content is None:
            logger.warning(
                f"Gemini [{model}/key:{_key_suffix(api_key)}] returned empty content "
                f"(finish_reason={finish_reason}, usage={usage}). "
                f"อาจเป็นเพราะ max_tokens={max_tokens} น้อยเกิน — thinking ใช้หมด"
            )
            content = ""
        if usage:
            logger.info(
                f"LLM [{model}/key:{_key_suffix(api_key)}] tokens — "
                f"prompt: {usage.get('prompt_tokens', '?')}, "
                f"completion: {usage.get('completion_tokens', '?')}, "
                f"total: {usage.get('total_tokens', '?')}"
            )
        # strip lone surrogates from LLM output (prevent UnicodeEncodeError downstream)
        return strip_surrogates(content)


async def _call_gemini_with_failover(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> str:
    """Call Gemini with primary key; on 429/5xx fall back to backup key (if set)."""
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not configured")

    logger.info(f"LLM call → {model} (temp={temperature}, max_tokens={max_tokens})")

    try:
        return await _call_gemini_once(
            GEMINI_API_KEY, model, system_prompt, user_prompt, temperature, max_tokens
        )
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        is_retryable = status == 429 or 500 <= status < 600
        has_backup = bool(GEMINI_API_KEY_BACKUP)

        if is_retryable and has_backup:
            logger.warning(
                f"Primary key ({_key_suffix(GEMINI_API_KEY)}) returned {status} — "
                f"failing over to backup key ({_key_suffix(GEMINI_API_KEY_BACKUP)})"
            )
            try:
                return await _call_gemini_once(
                    GEMINI_API_KEY_BACKUP, model, system_prompt, user_prompt,
                    temperature, max_tokens,
                )
            except httpx.HTTPStatusError as e2:
                logger.error(
                    f"Backup key also failed ({e2.response.status_code}): {e2.response.text}"
                )
                raise Exception(f"LLM API error (both keys failed): {e2.response.status_code}")

        # Non-retryable (4xx other than 429) OR no backup configured
        logger.error(f"Gemini API error {status}: {e.response.text}")
        raise Exception(f"LLM API error {status}: {e.response.text}")


async def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 8192) -> str:
    """Call Flash model — fast & cheap. Used for chat, lightweight queries."""
    return await _call_gemini_with_failover(LLM_MODEL, system_prompt, user_prompt, temperature, max_tokens)


async def call_llm_pro(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 8192) -> str:
    """Call Pro model — smart & powerful.
    Used for: organize, summarize, text cleanup, knowledge graph, metadata enrichment.
    """
    return await _call_gemini_with_failover(LLM_MODEL_PRO, system_prompt, user_prompt, temperature, max_tokens)


async def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """Call Pro model and parse the response as JSON.
    
    Uses Gemini 3.1 Pro for structured data extraction — organize, summarize, etc.
    """
    raw = await call_llm_pro(system_prompt, user_prompt, temperature, max_tokens=16384)

    # Try to extract JSON from response
    # LLMs sometimes wrap JSON in ```json ... ```
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove code fences
        lines = cleaned.split("\n")
        start = 0
        end = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("```") and i == 0:
                start = i + 1
                # Skip language identifier line if present
                if lines[i].strip() != "```":
                    start = i + 1
            elif line.strip() == "```" and i > 0:
                end = i
        cleaned = "\n".join(lines[start:end])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw: {raw[:500]}")
        # Try to find JSON object or array in the response
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            idx_start = raw.find(start_char)
            idx_end = raw.rfind(end_char)
            if idx_start != -1 and idx_end != -1 and idx_end > idx_start:
                try:
                    return json.loads(raw[idx_start:idx_end + 1])
                except json.JSONDecodeError:
                    continue
        raise Exception(f"Could not parse LLM response as JSON: {raw[:300]}")

