"""
The AI brain: converts ordinary text into a structured decision.

The brain is deliberately independent from the microphone, Whisper
and speaker implementations.  It only receives text and produces an
Intent; the planner can be swapped for a model-based implementation
later behind the same plan() interface.
"""

from ai.intent import Intent
from ai.planner import FallbackPlanner


class AIBrain:

    def __init__(self, planner=None):
        self.planner = planner if planner is not None else FallbackPlanner()

    def process(self, text):
        """Turn raw text into a structured Intent."""

        intent = self.planner.plan(text)

        print(f"Astra intent: {intent}")

        return intent

    def set_planner(self, planner):
        """Replace the planning strategy (e.g. with a model)."""

        self.planner = planner
