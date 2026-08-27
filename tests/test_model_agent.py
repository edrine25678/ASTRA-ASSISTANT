import unittest

from ai.model_agent import ModelAgent
from tools.base import ToolCall


class FakeProvider:
    def __init__(self, payload):
        self.payload = payload

    def available(self):
        return True

    def generate_json(self, messages):
        return self.payload


class FakeRegistry:
    def discover(self):
        return [{
            "name": "get_time",
            "description": "Get the current time.",
            "parameters": {},
            "requires_confirmation": False,
        }]


class FakeMemory:
    def recall(self, query, limit=3):
        return True, "", [{"content": "The user likes concise answers."}]


class FakeContext:
    def history(self, limit=6):
        return [("user", "hello"), ("assistant", "Hi Edrine.")]


class ModelAgentTests(unittest.TestCase):

    def test_reply_decision(self):
        agent = ModelAgent(
            provider=FakeProvider({"type": "reply", "reply": "Hello."}),
            registry=FakeRegistry(),
        )
        result = agent.decide("hello", FakeContext())
        self.assertEqual(result["type"], "reply")
        self.assertEqual(result["reply"], "Hello.")

    def test_tool_decision_becomes_tool_call(self):
        agent = ModelAgent(
            provider=FakeProvider({
                "type": "tool",
                "tool": "get_time",
                "arguments": {},
            }),
            registry=FakeRegistry(),
        )
        result = agent.decide("what time is it?", FakeContext())
        self.assertEqual(result["type"], "tool")
        self.assertIsInstance(result["call"], ToolCall)
        self.assertEqual(result["call"].name, "get_time")

    def test_invalid_tool_arguments_are_rejected(self):
        agent = ModelAgent(
            provider=FakeProvider({
                "type": "tool",
                "tool": "get_time",
                "arguments": "not-a-dict",
            }),
            registry=FakeRegistry(),
        )
        self.assertIsNone(agent.decide("what time is it?", FakeContext()))


if __name__ == "__main__":
    unittest.main()
