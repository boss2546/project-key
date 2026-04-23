"""LLM integration via OpenRouter API — optimized for Gemini 3 Flash."""
import httpx
import json
import logging
from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


async def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 8192) -> str:
    """Call OpenRouter LLM and return the response text.
    
    Optimized for google/gemini-3-flash-preview:
    - 1M context window — can process massive documents
    - 65K max completion — supports detailed analysis
    - Internal reasoning — better structured output
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://project-key.fly.dev",
        "X-Title": "Project KEY"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Gemini 3 — leverage provider-specific optimizations
        "provider": {
            "order": ["Google"],
            "allow_fallbacks": True
        }
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(OPENROUTER_BASE_URL, headers=headers, json=payload)

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenRouter API error {response.status_code}: {error_text}")
            raise Exception(f"LLM API error {response.status_code}: {error_text}")

        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            # Log token usage for monitoring
            usage = data.get("usage", {})
            if usage:
                logger.info(f"LLM tokens — prompt: {usage.get('prompt_tokens', '?')}, "
                          f"completion: {usage.get('completion_tokens', '?')}, "
                          f"total: {usage.get('total_tokens', '?')}")
            return content
        else:
            logger.error(f"Unexpected LLM response: {data}")
            raise Exception(f"Unexpected LLM response format")


async def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """Call LLM and parse the response as JSON.
    
    Uses 16K max_tokens for structured data extraction — Gemini 3 Flash
    excels at producing clean JSON with its internal reasoning.
    """
    raw = await call_llm(system_prompt, user_prompt, temperature, max_tokens=16384)

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

