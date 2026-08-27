"""
AI provider interface.

A provider turns a conversation history into a short assistant
reply.  Astra works with providers == "none": every intent is
handled by deterministic tools, so a provider is purely an optional
enhancement.
"""

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised when a provider fails and cannot be used."""


class AIProvider(ABC):

    name = "base"

    @abstractmethod
    def generate(self, messages):
        """Return an assistant reply string for the message history."""

    @abstractmethod
    def generate_json(self, messages):
        """Return a parsed JSON object for model-assisted decisions."""
        raise AIProviderError("This provider does not support structured output.")

    @abstractmethod
    def available(self):
        """True when this provider can be used right now."""

    def close(self):
        """Release resources, if any."""


class UnavailableProvider(AIProvider):
    """Placeholder used when no provider is configured."""

    name = "none"

    def generate(self, messages):
        raise AIProviderError("No AI provider is configured.")

    def generate_json(self, messages):
        """Return a parsed JSON object for model-assisted decisions."""
        raise AIProviderError("This provider does not support structured output.")

    def available(self):
        return False

    def close(self):
        pass
