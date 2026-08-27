"""
Astra's intelligent brain layer.

The brain produces structured Intents; the tool registry executes
the ToolCalls those intents carry.  An optional AI provider adds
knowledge answers on top of the deterministic planner.
"""

from config.settings import (
    AI_MODEL,
    AI_PROVIDER,
    ASTRA_API_BASE,
    ASTRA_API_KEY,
    ASTRA_OLLAMA_BASE,
    ASTRA_OLLAMA_TIMEOUT,
)

from ai.intent import Intent
from ai.brain import AIBrain
from ai.planner import FallbackPlanner
from ai.provider import AIProvider, AIProviderError, UnavailableProvider
from ai.local_provider import LocalProvider
from ai.ollama_provider import OllamaProvider
from ai.cloud_provider import CloudProvider
from ai.model_agent import ModelAgent


def build_provider():
    """Build the configured AI provider.

    Defaults to UnavailableProvider when nothing is configured, so
    Astra is always fully functional offline.
    """

    name = AI_PROVIDER

    if name == "cloud":

        if ASTRA_API_KEY:
            return CloudProvider(
                api_key=ASTRA_API_KEY,
                base_url=ASTRA_API_BASE,
                model_name=AI_MODEL,
            )

        return UnavailableProvider()

    if name == "local":
        return LocalProvider(AI_MODEL)

    if name == "ollama":
        return OllamaProvider(
            base_url=ASTRA_OLLAMA_BASE,
            model_name=AI_MODEL,
            timeout=ASTRA_OLLAMA_TIMEOUT,
        )

    return UnavailableProvider()


__all__ = [
    "AIBrain",
    "AIProvider",
    "AIProviderError",
    "CloudProvider",
    "ModelAgent",
    "FallbackPlanner",
    "Intent",
    "LocalProvider",
    "OllamaProvider",
    "UnavailableProvider",
    "build_provider",
]
