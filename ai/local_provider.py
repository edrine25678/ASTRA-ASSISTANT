"""
Local AI provider (offline).

A real local model is intentionally not bundled or downloaded: the
machine is a 2-core i5 with ~8 GB of RAM, so a local LLM would make
Astra unusable.  This provider exists so the architecture has a
home for a future offline model and reports cleanly when it is
unavailable.
"""

from ai.provider import AIProvider, AIProviderError


class LocalProvider(AIProvider):

    name = "local"

    def __init__(self, model_name=""):
        self.model_name = model_name or "unset"

    def generate(self, messages):
        raise AIProviderError(
            "No local AI model is available yet."
        )

    def available(self):
        return False

    def close(self):
        pass
