"""
AstraTaskEngine: multi-step task management.

A task is a goal plus an ordered list of steps.  The engine plans
the task, executes steps one by one through the tool registry,
observes each result, asks the user when a step needs approval,
and stops safely when the user cancels.

Everything runs synchronously in the calling thread: no background
workers, no extra processes.  That keeps the footprint small on a
2-core / 8 GB machine.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import get_logger

from tools.base import ToolCall

logger = get_logger("core.task_engine")


class TaskState:

    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_TOOL = "waiting_for_tool"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:

    id: int = 0
    description: str = ""
    kind: str = "tool"          # tool | follow_up | note
    tool: str = ""              # tool name for tool steps
    arguments: dict = field(default_factory=dict)
    status: str = TaskState.PENDING
    observation: str = ""
    result: object = None
    retries: int = 0

    def to_dict(self):

        return {
            "id": self.id,
            "description": self.description,
            "kind": self.kind,
            "tool": self.tool,
            "status": self.status,
            "observation": self.observation,
        }


@dataclass
class Task:

    goal: str = ""
    status: str = TaskState.PLANNING
    steps: list = field(default_factory=list)
    created_at: str = ""
    current_step_index: int = 0
    captured_results: list = field(default_factory=list)
    pending_question: str = ""
    pending_kind: str = ""      # confirm | ask
    pending_call: object = None
    pending_options: list = field(default_factory=list)

    def current_step(self):

        for step in self.steps:

            if step.status == TaskState.PENDING:
                return step

        return None

    def description(self):

        step = self.current_step()

        if self.status == TaskState.WAITING_FOR_USER:
            return self.pending_question

        if step is not None:
            return step.description

        return ""


class AstraTaskEngine:

    MAX_RETRIES = 2

    TRANSIENT_MARKERS = ("timeout", "timed out", "connection", "temporarily")

    def __init__(self, registry, planner=None, observer=None,
                 confirmation=None, memory=None, context=None):

        from core.observer import AstraObserver
        from core.confirmation import ConfirmationManager

        self.registry = registry
        self.planner = planner
        self.observer = observer if observer is not None else AstraObserver()
        self.confirmation = (
            confirmation if confirmation is not None else ConfirmationManager()
        )
        self.memory = memory
        self.context = context

        self.current_task = None
        self._step_counter = 0

    # ==============================================
    # TASK LIFECYCLE
    # ==============================================

    def create_task(self, goal):
        """Create and return a new task, replacing any active one."""

        if (
            self.current_task is not None
            and self.current_task.status
            in (TaskState.PLANNING, TaskState.RUNNING,
                TaskState.WAITING_FOR_USER, TaskState.PAUSED)
        ):
            logger.info("Replacing active task: %s", self.current_task.goal)

        task = Task(
            goal=goal.strip(),
            status=TaskState.PLANNING,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

        self.current_task = task

        logger.info("Task created")
        logger.info("Goal: %s", task.goal)

        return task

    def plan_task(self, task, steps):
        """Assign a plan and move the task to RUNNING."""

        if not steps:

            task.status = TaskState.FAILED

            logger.info("Task failed to plan: %s", task.goal)

            return False

        for index, step in enumerate(steps, start=1):
            step.id = self._next_step_id()
            step.status = TaskState.PENDING

        task.steps = list(steps)
        task.current_step_index = 0
        task.status = TaskState.RUNNING

        logger.info("Plan created: %s steps", len(steps))

        return True

    def start_new(self, goal, planner=None):
        """Plan and run a task.  Returns the spoken response."""

        task = self.create_task(goal)

        planner = planner or self.planner

        if planner is None:
            task.status = TaskState.FAILED
            return "I couldn't plan that task."

        steps = planner.plan(goal)

        if not self.plan_task(task, steps):

            return (
                "I couldn't plan that task. "
                "Try describing it step by step."
            )

        return self._run_loop(task)

    def pause(self):
        """Pause the active task."""

        if (
            self.current_task is None
            or self.current_task.status == TaskState.COMPLETED
        ):
            return "There's no active task to pause."

        if self.current_task.status == TaskState.RUNNING:
            self.current_task.status = TaskState.PAUSED
            logger.info("Task paused: %s", self.current_task.goal)

        return f"Task paused. {self.status_description()}"

    def resume(self):
        """Resume a paused task."""

        task = self.current_task

        if task is None or task.status != TaskState.PAUSED:
            return "There's no paused task to resume."

        task.status = TaskState.RUNNING

        logger.info("Task resumed: %s", task.goal)

        return self._run_loop(task)

    def cancel(self):
        """Cancel the active task safely."""

        task = self.current_task

        if task is None or task.status in (
            TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED
        ):
            return "There's no active task to stop."

        task.status = TaskState.CANCELLED
        task.pending_question = ""
        task.pending_call = None

        self._record_task(task)

        logger.info("Task cancelled: %s", task.goal)

        return "Okay, I stopped the task."

    def status_description(self):
        """Describe what Astra is doing right now."""

        task = self.current_task

        if task is None:
            return "I'm not working on anything right now."

        if task.status == TaskState.RUNNING:

            step = task.current_step()

            if step is not None:
                return (
                    f"I'm working on: {task.goal}. "
                    f"Next: {step.description}."
                )

            return f"I'm working on: {task.goal}."

        if task.status == TaskState.WAITING_FOR_USER:
            return task.pending_question

        if task.status == TaskState.PAUSED:
            return f"Task paused: {task.goal}."

        if task.status == TaskState.COMPLETED:
            return f"The last task is finished: {task.goal}."

        if task.status == TaskState.FAILED:
            return f"The last task didn't finish: {task.goal}."

        if task.status == TaskState.CANCELLED:
            return f"The last task was cancelled: {task.goal}."

        return "I'm not working on anything right now."

    def continue_with_input(self, text):
        """Feed a user reply into a task that is waiting for input."""

        task = self.current_task

        if (
            task is None
            or task.status != TaskState.WAITING_FOR_USER
        ):
            return None

        raw = (text or "").strip().lower()

        if task.pending_kind == "confirm":
            return self._continue_confirmation(task, raw)

        if task.pending_kind == "ask":
            return self._continue_ask(task, raw)

        task.status = TaskState.FAILED

        return "I lost track of what I was asking. Task stopped."

    def resolve_follow_up(self, index):
        """Resolve "the first one" against captured results."""

        task = self.current_task

        if task is None or not task.captured_results:
            return None

        return self._pick_candidate(task.captured_results, index)

    # ==============================================
    # EXECUTION LOOP
    # ==============================================

    def _run_loop(self, task):

        while task.status == TaskState.RUNNING:

            step = task.current_step()

            if step is None:

                task.status = TaskState.COMPLETED

                self._record_task(task)

                logger.info("Task completed: %s", task.goal)

                return self._completion_response(task)

            outcome = self._execute_step(task, step)

            if outcome == "waiting":
                return task.pending_question

            if outcome == "finished":
                task.status = TaskState.COMPLETED

                self._record_task(task)

                logger.info("Task completed: %s", task.goal)

                return self._completion_response(task)

        if task.status == TaskState.FAILED:

            self._record_task(task)

            logger.info("Task failed: %s", task.goal)

            observation = ""

            for step in task.steps:

                if step.status == TaskState.FAILED and step.observation:
                    observation = step.observation
                    break

            if observation:
                return f"I couldn't finish that task. {observation}"

            return f"I couldn't finish that task. {task.goal}"

        if task.status == TaskState.CANCELLED:
            return "Okay, I stopped the task."

        if task.status == TaskState.WAITING_FOR_USER:
            return task.pending_question

        return self.status_description()

    def _execute_step(self, task, step):

        if step.kind == "note":

            task.status = TaskState.FAILED

            step.status = TaskState.FAILED
            step.observation = (
                f"I couldn't understand the step: '{step.description}'."
            )

            return "failed"

        if step.kind == "follow_up":
            return self._execute_follow_up(task, step)

        logger.info("Executing step %s", step.id)
        logger.info("Tool: %s", step.tool or step.kind)

        self._adjust_step(task, step)

        call = ToolCall(step.tool or "", step.arguments)

        # ----- risk-based confirmation -----

        if self.confirmation.needs_confirmation(call) and not call.confirmed:

            task.status = TaskState.WAITING_FOR_USER
            task.pending_kind = "confirm"
            task.pending_call = call
            task.pending_question = (
                f"Are you sure you want me to {step.description.lower()}?"
            )

            logger.info("User confirmation requested: %s", step.description)

            return "waiting"

        # ----- execute -----

        result = self.registry.execute(call)

        observation = self.observer.interpret(result, step.tool or "")

        step.observation = observation
        step.result = result

        if result.needs_confirmation:

            task.status = TaskState.WAITING_FOR_USER
            task.pending_kind = "confirm"
            task.pending_call = call
            task.pending_question = result.response

            logger.info("User confirmation requested: %s", step.description)

            return "waiting"

        if result.denied:

            step.status = TaskState.FAILED
            task.status = TaskState.FAILED

            logger.info("Step %s denied by safety policy", step.id)

            return "failed"

        if result.success:

            step.status = TaskState.COMPLETED

            self._capture_results(task, result)

            logger.info("Step %s completed", step.id)

            return "continue"

        # ----- failure -----

        return self._handle_failure(task, step, result)

    def _handle_failure(self, task, step, result):

        error = result.error or ""

        transient = any(
            marker in error.lower() for marker in self.TRANSIENT_MARKERS
        )

        if transient and step.retries < self.MAX_RETRIES:

            step.retries += 1

            logger.info(
                "Step %s transient failure, retry %s/%s",
                step.id,
                step.retries,
                self.MAX_RETRIES,
            )

            return "continue"

        step.status = TaskState.FAILED

        # Attempt replanning once.
        if self.planner is not None:

            replacement = self.planner.replan(
                task, step, step.observation
            )

            if replacement:

                logger.info("Task replanned: %s", task.goal)

                remaining = [
                    s for s in task.steps
                    if s.status == TaskState.PENDING
                ]

                for index, new_step in enumerate(replacement, start=1):
                    new_step.id = self._next_step_id()
                    new_step.status = TaskState.PENDING

                task.steps = remaining + list(replacement)

                return "continue"

        task.status = TaskState.FAILED

        logger.info(
            "Step %s failed: %s", step.id, step.observation
        )

        return "failed"

    def _execute_follow_up(self, task, step):

        # "open the first one" resolves against captured results.
        index = step.arguments.get("index")

        if not task.captured_results:

            step.status = TaskState.FAILED
            task.status = TaskState.FAILED
            step.observation = (
                f"I can't do that yet: '{step.description}'. "
                "I don't have any results from the previous step."
            )

            logger.info("Follow-up failed: no captured results")

            return "failed"

        picked = self._pick_candidate(task.captured_results, index)

        if picked is None:

            task.status = TaskState.WAITING_FOR_USER
            task.pending_kind = "ask"
            task.pending_options = [
                item["path"] for item in task.captured_results
            ]
            task.pending_question = (
                "Which one should I use? "
                "Say the first one, the second one, and so on."
            )

            logger.info("User selection requested")

            return "waiting"

        step.kind = "tool"
        step.tool = "file_open_file"
        step.arguments = {"path": picked}

        logger.info("Follow-up resolved to: %s", picked)

        return self._execute_step(task, step)

    def _pick_candidate(self, results, index):

        def _path(item):

            return item["path"] if isinstance(item, dict) else item

        if index is None:
            return None

        if index == "last":
            return _path(results[-1]) if results else None

        if isinstance(index, int) and 0 <= index < len(results):
            return _path(results[index])

        return None

    # ==============================================
    # USER INPUT
    # ==============================================

    def _continue_confirmation(self, task, raw):

        question = task.pending_question

        yes = any(word in raw.split() for word in
                  ("yes", "yeah", "yep", "sure", "ok", "okay", "go"))
        no = any(word in raw.split() for word in
                 ("no", "nope", "cancel", "stop", "never"))

        if no and not yes:

            task.pending_question = ""
            task.pending_call = None

            step = task.current_step()
            step.status = "skipped"

            task.status = TaskState.RUNNING

            logger.info("Step skipped by user")

            return self._run_loop(task)

        if yes:

            call = task.pending_call
            call.confirmed = True

            task.pending_question = ""
            task.pending_call = None
            task.status = TaskState.RUNNING

            step = task.current_step()
            step.retries += 1

            logger.info("User confirmed: %s", step.description)

            result = self.registry.execute(call)

            observation = self.observer.interpret(
                result, step.tool or ""
            )

            step.observation = observation
            step.result = result

            if result.success:

                step.status = TaskState.COMPLETED

                self._capture_results(task, result)

                logger.info("Step %s completed after confirmation", step.id)

                return self._run_loop(task)

            if result.denied:

                step.status = TaskState.FAILED
                task.status = TaskState.FAILED

                return f"I couldn't do that. {observation}"

            task.status = TaskState.FAILED
            step.status = TaskState.FAILED

            logger.info("Step %s failed after confirmation", step.id)

            return f"I couldn't do that. {observation}"

        # Unclear reply: keep waiting for a clear answer.
        task.pending_question = question
        task.pending_kind = "confirm"
        task.status = TaskState.WAITING_FOR_USER

        return question

    def _continue_ask(self, task, raw):

        index = self._parse_ordinal(raw)

        picked = self._pick_candidate(task.pending_options, index)

        if picked is None:

            return (
                "I didn't catch which one. "
                "Say the first one, the second one, and so on."
            )

        task.status = TaskState.RUNNING
        task.pending_kind = ""
        task.pending_question = ""
        task.pending_options = []

        step = task.current_step()

        step.kind = "tool"
        step.tool = "file_open_file"
        step.arguments = {"path": picked}

        logger.info("User selected: %s", picked)

        return self._run_loop(task)

    @staticmethod
    def _parse_ordinal(text):

        raw = (text or "").lower()

        if "last" in raw:
            return "last"

        for index, name in enumerate(("first", "second", "third", "fourth")):

            if name in raw:
                return index

        match = re.search(r"\b([1-4])(?:st|nd|rd|th)?\b", raw)

        if match:
            return int(match.group(1)) - 1

        if "one" in raw:
            return 0

        if "two" in raw:
            return 1

        return None

    # ==============================================
    # HELPERS
    # ==============================================

    def _next_step_id(self):

        self._step_counter += 1

        return self._step_counter

    def _capture_results(self, task, result):

        files = result.data.get("files") or []

        for path in files:
            task.captured_results.append({"path": path, "kind": "file"})

        if self.context is not None and result.tool == "open_url":

            target = (result.data.get("url") or "").lower()

            for name in ("youtube", "google", "gmail", "chatgpt", "github"):

                if name in target:
                    self.context.set_last_site(name)
                    return

    def _adjust_step(self, task, step):
        """Apply conversation context to a step before it runs."""

        if self.context is None:
            return

        if (
            step.tool == "search_web"
            and step.arguments.get("engine") == "google"
            and self.context.last_site == "youtube"
        ):
            step.arguments["engine"] = "youtube"

    def _completion_response(self, task):

        observations = [
            step.observation
            for step in task.steps
            if step.status == TaskState.COMPLETED and step.observation
        ]

        skipped = sum(
            1 for step in task.steps if step.status == "skipped"
        )

        if not observations:
            response = "Done."
        else:
            response = "Done. " + " ".join(observations)

        if skipped:
            response += f" I skipped {skipped} step(s)."

        return response

    def _record_task(self, task):

        if self.memory is None:
            return

        try:

            detail = task.description() or ""

            self.memory.store_task_record(
                task.goal, task.status, detail=detail
            )

        except Exception as error:

            logger.warning("Could not store task record: %s", error)