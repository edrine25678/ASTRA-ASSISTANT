"""Optional local Ollama provider.

Uses Ollama's localhost HTTP API through the standard library, so Astra does
not need an SDK. The provider is opt-in and remains unavailable until a local
Ollama server is reachable and the configured model exists.
"""

import json
import urllib.error
import urllib.request

from ai.provider import AIProvider, AIProviderError


class OllamaProvider(AIProvider):

    name = "ollama"

    def __init__(self, base_url="http://127.0.0.1:11434", model_name="", timeout=30):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name or "qwen2.5:3b-instruct"
        self.timeout = float(timeout)

    def _post(self, messages, temperature=0.2, json_mode=False):
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if json_mode:
            payload["format"] = "json"

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise AIProviderError(
                f"Local Ollama request failed: {error}"
            ) from error

    def generate(self, messages):
        body = self._post(messages, temperature=0.5)
        try:
            return body["message"]["content"].strip()
        except (KeyError, AttributeError) as error:
            raise AIProviderError("Invalid Ollama response") from error

    def generate_json(self, messages):
        body = self._post(messages, temperature=0.1, json_mode=True)
        try:
            content = body["message"]["content"].strip()
            if content.startswith("```"):
                content = content.replace("```json", "", 1).replace("```", "", 1).strip()
            return json.loads(content)
        except (KeyError, AttributeError, json.JSONDecodeError) as error:
            raise AIProviderError("Ollama returned invalid structured output") from error

    def available(self):
        try:
            request = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=min(self.timeout, 3)) as response:
                body = json.loads(response.read().decode("utf-8"))
            models = {item.get("name") for item in body.get("models", [])}
            return self.model_name in models
        except Exception:
            return False

    def close(self):
        pass
