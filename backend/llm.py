"""LLM integration via OpenRouter API."""
import httpx
import json
import logging
from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


async def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 4000) -> str:
    """Call OpenRouter LLM and return the response text."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Project KEY"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OPENROUTER_BASE_URL, headers=headers, json=payload)

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"OpenRouter API error {response.status_code}: {error_text}")
            raise Exception(f"LLM API error {response.status_code}: {error_text}")

        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        else:
            logger.error(f"Unexpected LLM response: {data}")
            raise Exception(f"Unexpected LLM response format")


async def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """Call LLM and parse the response as JSON."""
    raw = await call_llm(system_prompt, user_prompt, temperature, max_tokens=8000)

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
