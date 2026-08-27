"""
Cloud AI provider (optional, OpenAI-compatible).

Only active when ASTRA_API_KEY is set and AI_PROVIDER=cloud.
Uses the standard library only; requires no SDK.  Offline by
default.
"""

import json
import urllib.error
import urllib.request

from ai.provider import AIProvider, AIProviderError


class CloudProvider(AIProvider):

    name = "cloud"

    def __init__(self, api_key, base_url, model_name="gpt-4o-mini"):

        if not api_key:
            raise AIProviderError(
                "Cloud provider requires an API key (ASTRA_API_KEY)."
            )

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name or "gpt-4o-mini"

    def generate(self, messages, max_tokens=120):

        if not self.api_key:
            raise AIProviderError("Cloud provider is not configured.")

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(request, timeout=20) as response:

                body = json.loads(
                    response.read().decode("utf-8")
                )

            return (
                body["choices"][0]["message"]["content"].strip()
            )

        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as error:

            raise AIProviderError(
                f"Cloud provider request failed: {error}"
            ) from error


    def generate_json(self, messages):
        """Generate and parse a JSON decision using the same endpoint.

        The prompt requests JSON-only output. Parsing happens locally so a
        malformed model response is rejected rather than executed.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 300,
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))

            content = body["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.replace("```json", "", 1).replace("```", "", 1).strip()

            return json.loads(content)

        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as error:
            raise AIProviderError(
                f"Cloud provider structured request failed: {error}"
            ) from error

    def available(self):
        return bool(self.api_key)

    def close(self):
        pass
