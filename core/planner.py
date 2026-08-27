"""
AstraPlanner: goal -> plan.

Converts a user goal (raw text) into an ordered list of TaskSteps.
The planner never executes anything itself; the task engine runs
the plan through the tool registry.
"""

import re

from ai.planner import FallbackPlanner

from core.logger import get_logger

from core.task_engine import TaskStep

logger = get_logger("core.planner")


class AstraPlanner:

    SEPARATOR = re.compile(
        r"\s*(?:,|\band\b|\bthen\b|\band\s+then\b|;|\bafter that\b)\s*"
    )

    VERB_GROUP = re.compile(r"^(?:open|launch|start|run|opening)\s+(.+)$")

    def __init__(self, brain=None):
        self.brain = brain if brain is not None else FallbackPlanner()

    def plan(self, goal):
        """Return a list of TaskSteps for the goal.

        The first step carries the goal in its arguments so the
        engine knows what the whole task is about.
        """

        raw = (goal or "").strip()

        if not raw:
            return []

        # "open chrome and youtube" / "open notepad and calculator":
        # one verb applied to several targets.
        match = self.VERB_GROUP.match(raw.lower())

        if match:

            targets = [
                target.strip()
                for target in re.split(r"\s*(?:,|and)\s*", match.group(1))
                if target.strip()
            ]

            if len(targets) >= 2:

                resolved = []

                for target in targets:

                    step = self._plan_clause(target)

                    if step is None:

                        step = self._plan_clause(f"open {target}")

                    if step is None:
                        resolved = []
                        break

                    resolved.append(step)

                if resolved:
                    return resolved

        parts = [
            part.strip()
            for part in self.SEPARATOR.split(raw.lower())
            if part.strip()
        ]

        steps = [self._plan_clause(part) for part in parts]

        steps = [step for step in steps if step is not None]

        # A single clause that is itself a full command.
        if not steps:
            step = self._plan_clause(raw.lower())

            if step is not None:
                steps = [step]

        return steps

    def _plan_clause(self, clause):
        """Plan one clause into a step, or None when unusable."""

        intent = self.brain.plan(clause)

        step = TaskStep(
            description=clause.capitalize(),
            kind="tool",
        )

        if intent.tool_call is not None:

            step.tool = intent.tool_call.name
            step.arguments = dict(intent.tool_call.arguments)

            logger.info(
                "Planned step: %s (%s)", clause, intent.tool_call.name
            )

            return step

        if intent.type == "follow_up":

            step.kind = "follow_up"
            step.arguments = dict(intent.parameters)

            logger.info("Planned follow-up step: %s", clause)

            return step

        if intent.type == "knowledge":

            step.kind = "tool"
            step.tool = "knowledge"
            step.arguments = dict(intent.parameters)

            return step

        logger.info("Could not plan clause: %s", clause)

        return None

    def replan(self, task, failed_step, observation):
        """Attempt recovery after a step failure.

        Returns a list of replacement steps, or None when no safe
        alternative exists.  Phase 5 has no automatic recovery
        alternatives, so this returns None unless a clause can be
        re-interpreted.
        """

        logger.info(
            "Replan requested for step %s (%s)",
            failed_step.id,
            observation,
        )

        return None