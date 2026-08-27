# Astra + Ollama Local AI

Astra now has a local AI route through Ollama. The Python integration talks to Ollama over its local HTTP API; no Ollama Python package is required.

## Recommended model for this laptop

The default is:

`qwen2.5:3b-instruct`

It is a roughly 1.9 GB Q4 model in Ollama's library. Astra's 8 GB RAM / i5-7300U hardware is not a good target for large 7B+ models, so start with the 3B model and measure response time before experimenting with anything larger.

## One-time Windows setup

1. Install Ollama for Windows from the official Ollama site.
2. Restart PowerShell so the `ollama` command is available.
3. Open the Astra project folder.
4. Activate Astra's virtual environment.
5. Run:

```powershell
.\setup_ollama.ps1
```

The script pulls the configured model and writes these values into `config/.env`:

```text
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:3b-instruct
ASTRA_OLLAMA_BASE=http://127.0.0.1:11434
ASTRA_OLLAMA_TIMEOUT=30
```

## Verify Ollama before starting Astra

```powershell
python tools\ollama_status.py
```

You want:

```text
Status   : READY
```

You can also check the model directly:

```powershell
ollama list
```

## Start Astra

```powershell
python -m core.astra
```

When the deterministic layer cannot resolve a request, Astra can ask the local model to either:

- answer naturally,
- ask for clarification, or
- select one registered Astra tool.

The model never receives direct shell/Python execution privileges. Tool requests still go through Astra's registry, validation, safety and confirmation layers.

## If Ollama is unavailable

Astra does not stop working. The local deterministic capabilities remain available and the model-assisted path simply falls back.

To disable the model route completely, set:

```text
AI_PROVIDER=none
```

in `config/.env`.
