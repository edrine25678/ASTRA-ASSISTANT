import json
import unittest
from unittest.mock import patch

from ai.ollama_provider import OllamaProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OllamaProviderTests(unittest.TestCase):

    def test_generate(self):
        provider = OllamaProvider(model_name="qwen2.5:3b-instruct")
        with patch(
            "ai.ollama_provider.urllib.request.urlopen",
            return_value=FakeResponse({"message": {"content": "Hello Edrine."}}),
        ) as mocked:
            result = provider.generate([
                {"role": "user", "content": "Hello"},
            ])

        self.assertEqual(result, "Hello Edrine.")
        self.assertTrue(mocked.called)

    def test_generate_json(self):
        provider = OllamaProvider(model_name="qwen2.5:3b-instruct")
        payload = {
            "message": {
                "content": '{"type":"reply","reply":"Hello."}'
            }
        }
        with patch(
            "ai.ollama_provider.urllib.request.urlopen",
            return_value=FakeResponse(payload),
        ):
            result = provider.generate_json([])

        self.assertEqual(result["type"], "reply")
        self.assertEqual(result["reply"], "Hello.")

    def test_available_checks_exact_model(self):
        provider = OllamaProvider(model_name="qwen2.5:3b-instruct")
        payload = {
            "models": [
                {"name": "qwen2.5:3b-instruct"},
            ]
        }
        with patch(
            "ai.ollama_provider.urllib.request.urlopen",
            return_value=FakeResponse(payload),
        ):
            self.assertTrue(provider.available())


if __name__ == "__main__":
    unittest.main()
