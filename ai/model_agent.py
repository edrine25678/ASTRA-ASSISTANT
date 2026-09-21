"""Optional model-assisted reasoning layer for Astra.

The model never receives direct execution privileges. It can only return one
of three structured decisions: reply, clarify, or tool. Tool calls are turned
into Astra ToolCall objects and are still validated by ToolRegistry, safety,
and confirmation before execution.
"""

import json
import re

from ai.provider import AIProviderError
from tools.base import ToolCall


class ModelAgent:

    def __init__(self, provider=None, registry=None, memory=None):
        self.provider = provider
        self.registry = registry
        self.memory = memory

    def available(self):
        return bool(self.provider and self.provider.available())

    def decide(self, user_text, context):
        if not self.available():
            return None

        messages = self._build_messages(user_text, context)

        try:
            raw = self.provider.generate_json(messages)
            decision = self._validate_decision(raw)
            return decision
        except (AIProviderError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _build_messages(self, user_text, context):
        tools = []
        if self.registry is not None:
            tools = self.registry.discover()

        tool_lines = []
        for tool in tools:
            tool_lines.append(json.dumps(tool, ensure_ascii=True))

        history = []
        for role, text in context.history(limit=6):
            history.append({"role": role, "content": text})

        memories = []
        if self.memory is not None:
            try:
                ok, _, items = self.memory.recall(user_text, limit=3)
                if ok:
                    memories = [item["content"] for item in items[:3]]
            except (OSError, KeyError):
                memories = []

        system = (
            "You are Astra, a Windows desktop assistant. "
            "Understand natural language and maintain a calm, concise, human-like tone. "
            "You may answer ordinary conversation directly. When a desktop action is "
            "needed, select exactly one tool from the supplied tool list. Never invent "
            "a tool. Never return shell commands, Python, PowerShell, file paths, or "
            "instructions for bypassing safety. If the request is ambiguous, ask a "
            "short clarification question. If information is unavailable, say so. "
            "Return ONLY valid JSON with one of these shapes: "
            '{"type":"reply","reply":"..."}; '
            '{"type":"clarify","reply":"..."}; '
            '{"type":"tool","tool":"tool_name","arguments":{}}. '
            "For destructive tools, the application will enforce confirmation."
        )

        if tool_lines:
            system += "\nAVAILABLE TOOLS:\n" + "\n".join(tool_lines)

        if memories:
            system += "\nRELEVANT MEMORY (may be ignored if unrelated):\n"
            system += "\n".join(f"- {item}" for item in memories)

        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        return messages

    @staticmethod
    def _validate_decision(raw):
        if isinstance(raw, str):
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
            raw = json.loads(raw)

        if not isinstance(raw, dict):
            raise TypeError("Model response is not an object")

        kind = str(raw.get("type", "")).strip().lower()

        if kind in ("reply", "clarify"):
            reply = str(raw.get("reply", "")).strip()
            if not reply:
                raise ValueError("Empty reply")
            return {"type": kind, "reply": reply}

        if kind == "tool":
            tool = str(raw.get("tool", "")).strip()
            arguments = raw.get("arguments", {})
            if not tool or not isinstance(arguments, dict):
                raise ValueError("Invalid tool decision")
            return {"type": "tool", "call": ToolCall(tool, arguments)}

        raise ValueError("Unknown model decision type")
