from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI

from core.settings import get_settings


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    """Ollama exposes an OpenAI-compatible API at ``/v1``.

    We reuse the OpenAI SDK with a local base_url. The api_key is a
    placeholder required by the SDK but ignored by Ollama.
    """
    settings = get_settings()
    return AsyncOpenAI(
        base_url=f"{settings.ollama_url.rstrip('/')}/v1",
        api_key="ollama-local",
    )


async def chat_json(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1200,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Call Ollama via its OpenAI-compat endpoint and parse JSON.

    Older Ollama builds do not implement response_format strictly, so we
    reinforce the JSON contract in the system message and fall back to
    bracket-extraction if the model wraps the payload in prose.
    """
    client = get_client()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system
                + "\n\nYou MUST return a single JSON object and nothing else. "
                + "No markdown fences, no prose before or after.",
            },
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = resp.choices[0].message.content
    if not content:
        raise ValueError("Ollama returned empty content")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback: try extracting the outermost JSON object.
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise
