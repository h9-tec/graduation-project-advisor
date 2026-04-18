from __future__ import annotations

from typing import Any, Literal

from core.llm import azure, ollama
from core.settings import get_settings

Tier = Literal["fast", "smart"]


async def chat_json(
    *,
    tier: Tier,
    system: str,
    user: str,
    max_tokens: int = 1200,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Provider-neutral JSON chat. Routes on settings.llm_provider.

    ``tier`` lets callers request either the fast (cheap) or smart
    (quality) model without knowing the provider. Azure maps to its
    two deployments; Ollama maps to two configured model tags.
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        model = (
            settings.ollama_model_smart if tier == "smart" else settings.ollama_model_fast
        )
        return await ollama.chat_json(
            model=model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # default: azure
    deployment = (
        settings.azure_openai_deployment_smart
        if tier == "smart"
        else settings.azure_openai_deployment_fast
    )
    return await azure.chat_json(
        deployment=deployment,
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
