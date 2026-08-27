"""Check Astra's local Ollama connection and configured model."""

from ai import build_provider
from config.settings import AI_MODEL, AI_PROVIDER, ASTRA_OLLAMA_BASE


def main():
    print("Astra Ollama status")
    print("-------------------")
    print(f"Provider : {AI_PROVIDER}")
    print(f"Model    : {AI_MODEL or '(default)'}")
    print(f"Endpoint : {ASTRA_OLLAMA_BASE}")

    if AI_PROVIDER != "ollama":
        print("Status   : NOT CONFIGURED")
        print("Set AI_PROVIDER=ollama in config/.env or the environment.")
        return 1

    provider = build_provider()
    if provider.available():
        print("Status   : READY")
        return 0

    print("Status   : UNAVAILABLE")
    print("Make sure Ollama is running and the configured model is installed.")
    print("Try: ollama list")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
