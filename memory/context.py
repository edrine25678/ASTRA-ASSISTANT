"""Compatibility import for Astra's single conversation-context implementation.

The intelligence layer owns the canonical context object. This module is
kept as a compatibility path for older imports and tests.
"""

from core.intelligence.context import ConversationContext

__all__ = ["ConversationContext"]
