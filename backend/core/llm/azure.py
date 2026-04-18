from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from openai import AsyncAzureOpenAI

from core.settings import get_settings


@lru_cache(maxsize=1)
def get_client() -> AsyncAzureOpenAI:
    settings = get_settings()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


async def chat_json(
    *,
    deployment: str,
    system: str,
    user: str,
    max_tokens: int = 1200,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Call Azure OpenAI and parse the response as JSON.

    Uses response_format={"type": "json_object"} so the model returns
    strict JSON. Raises ValueError if parsing fails or no content.
    """
    client = get_client()
    resp = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = resp.choices[0].message.content
    if not content:
        raise ValueError("LLM returned empty content")
    return json.loads(content)
