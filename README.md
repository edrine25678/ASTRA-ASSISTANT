# Astra

A local-first, voice-controlled desktop assistant for Windows.

Astra runs entirely on your machine — from wake-word detection to speech recognition to spoken responses. No cloud dependency required.

## Features

- **Voice Control** — Wake word detection, Whisper speech-to-text, local TTS
- **Windows Awareness** — System specs, CPU/RAM/battery status, Wi-Fi info, drive space
- **Application Management** — Open, close, and search installed apps
- **File Operations** — Search, list, read, create, and delete files
- **Web Integration** — Open URLs, web search
- **Smart Assistant** — Multi-step task execution, conversation memory, context tracking
- **Safety First** — Confirmation gates for destructive actions, filesystem allow-lists, no shell commands
- **Floating UI** — Glass-effect overlay with animated orb, system tray integration

## Quick Start

```powershell
# Clone the repo
git clone https://github.com/edrine25678/ASTRA-ASSISTANT.git
cd ASTRA-ASSISTANT

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run (GUI mode)
python main.py

# Or run (console mode)
python -u -m core.astra
```

## Requirements

- Windows 10/11
- Python 3.12+
- Microphone (for voice input)

### Dependencies

| Package | Purpose |
|---------|---------|
| faster-whisper | Speech-to-text |
| openwakeword | Wake word detection |
| webrtcvad-wheels | Voice activity detection |
| sounddevice | Audio input |
| pyttsx3 | Text-to-speech |
| PySide6-Essentials | GUI overlay |

## Configuration

Edit `config/settings.py` or create `config/.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `AI_PROVIDER` | `none` | `cloud`, `local`, or `none` |
| `WHISPER_MODEL` | `base.en` | Whisper model size |
| `WAKE_WORD_THRESHOLD` | `0.7` | Wake word sensitivity |
| `VOICE_RATE` | `175` | TTS speed (words per minute) |
| `CONVERSATION_TIMEOUT` | `10` | Seconds to keep mic open |

## Project Structure

```
Astra/
├── main.py              # Entry point
├── config/              # Settings and secrets
├── ai/                  # Model providers (cloud/local/Ollama)
├── core/
│   ├── astra.py         # Main voice loop
│   ├── brain.py         # Task orchestrator
│   ├── capabilities/    # Feature modules
│   └── intelligence/    # NLU, routing, context
├── tools/               # Tool registry and safety
├── voice/               # Wake word, STT, TTS
├── memory/              # SQLite persistence
├── ui/                  # Floating overlay GUI
└── tests/               # 14 test suites (721 checks)
```

## Ollama (Optional Local AI)

For local AI without cloud access:

```powershell
# Install Ollama, then:
.\setup_ollama.ps1

# Set in config/.env
AI_PROVIDER=ollama
```

## Testing

```powershell
# Run all tests
python -m pytest tests/

# Run specific suite
python -u -m tests.test_ui
python -u -m tests.test_windows
```

## License

See [LICENSE](LICENSE) for details.
