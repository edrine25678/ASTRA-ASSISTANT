# Astra — Project Report

**Version 0.11.0** · Review report · Generated from the full test run of 14 August 2026

Astra is a local-first, voice-controlled desktop assistant for Windows. Everything from wake-word detection to spoken output runs on the user's own machine (an i5-7300U, 8 GB laptop). The project is written in Python 3.12; the new reasoning layer uses only the standard library for provider HTTP calls and structured model responses, and is verified by 14 test suites with **721 checks, 0 failures**.

---

## 1. Executive Summary

- **93 Python files, ~13,000 lines of code** (excluding `.venv` and caches).
- **14 test suites, 721 checks, 0 failures.**
- **Boot verified:** `python -u -m core.astra` starts cleanly, registers 14 tools, waits for the wake word.
- **GUI boot verified:** `python main.py` starts hidden with a system-tray icon and a wake-word listener.
- **Live smoke verified:** system specifications, RAM, drives, Wi-Fi, installed/running applications, folder navigation, "close it" confirmation flow — all working without any cloud model (deterministic fallback).
- **Safety-first design:** no raw AI-generated shell commands anywhere; every destructive action goes through a confirmation gate; filesystem access is restricted to an allow-list.

---

## 2. Purpose and Scope

Astra listens for a wake word ("Alexa"), converts speech to text (Whisper), understands the request (deterministic planner first, then a semantic NLU layer), acts through a validated tool registry, and answers with a local TTS voice. A conversation mode keeps the mic open after the wake word so follow-ups like "and tomorrow?" or "close it" work naturally.

Phase history:

| Phase | Theme | Outcome |
|---|---|---|
| 1 | Wake word | `alexa_v0.1.onnx` wake-word detection |
| 2 | Voice pipeline | Whisper STT, TTS, WebRTC VAD, conversation mode |
| 3 | Tool brain | Intent parser, tool registry, safety policy, confirmation gate, tasks, memory |
| 4 | Model providers | Cloud / Local / Unavailable provider abstraction, AstraBrain orchestrator |
| 5 | Skill library | Browser, files, applications, system info, task engine, observer |
| 6 | Intelligence layer | NLU, router, capability layer, conversational context, AstraAssistant |
| 7 | Windows awareness | PC status (CPU/RAM/storage/battery/network), app search, controlled closing, folder awareness |
| 8 | Model-assisted intelligence | Optional provider-backed conversation and safe model-selected tools; deterministic path remains the default |
| 9 | Memory-grounded conversation | Bounded context plus relevant-memory retrieval is supplied to the optional reasoning layer; memory writes remain explicit |
| 10 | Architecture hardening | Single shared context, configurable model/wake-word settings, dependency manifest, safer packaging and diagnostics tests |

---

## 3. Architecture

```
                ┌────────────────────────────────────────────┐
                │                 core/astra.py               │
                │      state machine · main voice loop        │
                └──────┬──────────────────────────────────────┘
                       │ voice
        ┌──────────────┴───────────────┐
        │ voice/ wake word · VAD · STT │          voice/ TTS (spoken answers)
        │ (alexa.onnx, Whisper)        │
        └──────────────┬───────────────┘
                       │ text
        ┌──────────────▼───────────────┐
        │      core/intelligence/       │  AstraAssistant (Phase 6 orchestrator)
        │  precheck → brain → semantic  │
        │  → router → capabilities      │
        └──────┬───────────────┬────────┘
               │ brain (first) │ fallback
        ┌──────▼──────────┐   ┌──▼───────────────────────────┐
        │  core/brain.py  │   │ core/capabilities/ +         │
        │  AstraBrain     │   │ core/capabilities/windows/   │
        │  planner first  │   │ (Phase 6 + 7 families)       │
        └──────┬──────────┘   └──┬───────────────────────────┘
               └──────────┬──────┘
        ┌──────────────▼───────────────┐
        │       tools/ (registry)      │  ToolRegistry → ToolSafety → Confirmation
        │  open · browser · file ·     │  → execution (stdlib / Win32 ctypes only)
        │  system · process            │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼───────────────┐
        │ core/ confirmation · memory ·│  task_engine · observer · state
        │ task_engine · observer       │
        └──────────────────────────────┘
```

Key rule: **brain first, semantic fallback only.** The deterministic planner (Phase 3) is the first pass because it is proven; the NLU semantic layer (Phase 6–7) refines only what the planner could not resolve. Both paths converge on the same tool registry, safety policy, and confirmation gate.

---

## 4. Feature Inventory

### 4.1 Voice pipeline (Phases 1–2)
- **Wake word:** ONNX model (`alexa_v0.1.onnx`) with configurable threshold.
- **STT:** Whisper (`base.en`, int8 quantized, CPU) — model loads lazily on the first command.
- **VAD:** WebRTC voice-activity detection to segment speech.
- **TTS:** Local speaker with adjustable rate (175 wpm default).
- **Conversation mode:** after the wake word, the mic stays open for `CONVERSATION_TIMEOUT` (10 s) with bounded context (8 messages / 400 tokens).

### 4.2 Understanding (Phases 3, 6, 7)
- **Planner** (`ai/planner.py`): intent phrases → validated `ToolCall`s; multi-step plans ("open chrome and search for python tutorials"), follow-ups, date/time, system queries (time, date, OS, RAM, CPU, battery, disk, processes).
- **NLU** (`core/intelligence/nlu.py`, ~1,255 lines): signal-group semantics with confidence scoring — open/close apps, websites, web search, time/date, file operations, and all Phase 7 intents (CPU, memory, storage, battery, network, computer status, installed/running apps, process info, file search, folder navigation). Entity extraction: applications (via discovery cache), websites, search queries, file types (category → extensions), locations, drive letters, date ranges ("yesterday", "this week").
- **Prechecks** before the brain: pronoun opens ("open it"), pronoun file actions ("delete that folder"), date ellipses ("and tomorrow?"), bare search ("search the web"), folder navigation ("go to downloads"), "close it" (resolves via conversation topic), "close astra" (exit).
- **Router** (`router.py`): confidence thresholds — ≥0.85 act, 0.60–0.85 act unless an entity is missing, <0.60 clarify.

### 4.3 Acting (Phases 3, 5, 6, 7)
- **Tool registry** (`tools/`): 13 default tools + `close_application` (assistant-only):
  `open_application`, `open_url`, `search_web`, `get_time`, `get_date`, `system_info`, `file_search`, `file_list_directory`, `file_open_file`, `file_open_folder`, `file_read_text`, `file_create_text`, `file_delete`, `close_application`.
- **Capability layer:** each intent family is one self-contained capability class (applications, browser, search, system, files + 7 Windows-aware capabilities). Execution always flows through the registry, so safety and confirmation apply uniformly.
- **Tasks** (`core/task_engine.py`): multi-step goals, per-step retries, user confirmation at dangerous steps, replanning, cancel/status control, follow-up resolution ("open the first one").
- **Memory** (`memory/`): SQLite persistence (`memory/astra.db`), save/recall with categories, sensitive-data rejection, pruning, summarization.
- **Observer** (`core/observer.py`): success/failure/denial observation used for honest follow-ups.

### 4.4 Windows awareness (Phase 7)
- **System specifications:** computer name, OS, processor (`ProcessorNameString` from registry — reports "Intel(R) Core(TM) i5-7300U CPU @ 2.60GHz"), logical processors, GPU (display-class registry key), RAM, free disk.
- **Live status:** CPU busy % (two-sample `GetSystemTimes`), RAM usage (`GlobalMemoryStatusEx`), battery/charging (`GetSystemPowerStatus`), drives (`GetLogicalDrives`/`GetDriveTypeW`/`GetDiskFreeSpaceExW`), computer health summary.
- **Network:** internet connectivity (HTTPS probe), Wi-Fi SSID (fixed read-only `netsh wlan show interfaces`), local IP (UDP socket, zero traffic).
- **Applications:** discovery from Start Menu + uninstall registry keys, cached for 7 days (`data/apps_cache.json`, 184 apps on the test machine); "is chrome installed", "do I have vs code", full list.
- **Processes:** running apps, "is chrome running" (Toolhelp snapshot), top memory consumer (`GetProcessMemoryInfo`), controlled closing with confirmation (`OpenProcess`/`TerminateProcess` — never a shell command).
- **Files & folders:** search inside allowed folders only, with type/location/date filters and bounded depth; open/list approved folders; "here" tracking (`context.current_location`) after a folder open.

### 4.5 Personality
- Variant response pools (open/close/search) that rotate and avoid repeating the last response; clarification questions; honest fallbacks ("I don't know how to do that yet.") with local tools still available when the cloud provider is unreachable.

---

## 5. Safety and Security Design

1. **No raw AI-generated shell commands.** The AI can only request `ToolCall`s; every tool validates its arguments; execution is bounded by `ToolSafety.ALLOWED_TOOLS`. The only subprocess call in the codebase is the fixed `netsh wlan show interfaces` read-only query with no user input interpolated.
2. **Confirmation gate.** Tools set `requires_confirmation = True` (file_delete, close_application); `ConfirmationManager` assigns risk levels (unknown tools default HIGH); the assistant always asks yes/no before destructive actions and honors "no"/"never mind".
3. **Filesystem allow-list.** Operations are confined to Desktop/Documents/Downloads/Pictures/Videos/Music/home + the Astra project. Writes to the Astra source tree are refused. Search depth is bounded (5 levels), results capped.
4. **System-process blacklist.** Astra will never terminate svchost, explorer, lsass, etc., and never terminates its own process.
5. **No autonomous control.** No screenshots, no keylogging, no webcam, no scripting, no arbitrary file deletion, no credential handling. Secrets live only in `config/.env`.
6. **Bounded everything.** Conversation history, memory DB, app cache, search results — all capped.
7. **Graceful degradation.** Every capability returns an honest "unavailable" message rather than fabricated data (e.g., per-process CPU ranking is declined with overall CPU usage instead).

---

## 6. Configuration (`config/settings.py`)

| Setting | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `none` | cloud / local / none provider selection |
| `WHISPER_MODEL` / `DEVICE` / `COMPUTE_TYPE` | base.en / cpu / int8 | STT |
| `WAKE_WORD_THRESHOLD` | 0.9 | wake-word sensitivity |
| `VOICE_RATE` | 175 | TTS speaking rate |
| `CONVERSATION_TIMEOUT` | 10 s | conversation-mode mic hold |
| `MAX_CONTEXT_MESSAGES` / `TOKENS` | 8 / 400 | bounded conversation memory |
| `MEMORY_ENABLED` / `MEMORY_DB_PATH` | true / `memory/astra.db` | long-term memory |
| `APP_CACHE_PATH` / `APP_CACHE_MAX_AGE_DAYS` | `data/apps_cache.json` / 7 | application discovery cache |
| `ASTRA_VERSION` | 0.7.0 | reported in system specs |
| `ALLOWED_DIRECTORIES` | Desktop, Documents, Downloads, Pictures, Videos, Music, home, astra | filesystem allow-list |
| `SEARCH_RESULT_LIMIT` / `MAX_FILE_SEARCH_DEPTH` | 5 / 5 | file-search bounds |
| `LOG_LEVEL` / `LOG_DIR` | INFO / `logs/astra.log` | logging |

---

## 7. Verification

### 7.1 Test suites (721 checks, 0 failures)

| Suite | Checks | Covers |
|---|---|---|
| `test_brain` | 104 | Phase 3–4 planner/orchestrator behavior |
| `test_windows` | 101 | **Phase 7** NLU routing, entities, close flow, guards, degradation |
| `test_intelligence` | 80 | Phase 6 prechecks, semantic fallback, confirmation, topic tracking |
| `test_intents` | 77 | intent phrase mapping |
| `test_tools` | 63 | registry, safety policy, denial |
| `test_task_engine` | 51 | multi-step tasks, retries, replan, follow-ups |
| `test_astra_brain` | 40 | orchestrator integration |
| `test_memory` | 38 | persistence, categories, pruning, sensitive rejection |
| `test_file_tool` | 29 | search/list/read/create/delete, project-root protection |
| `test_planner` | 26 | single/multi-step plans |
| `test_state` | 15 | conversation state machine |
| `test_confirmation` | 14 | risk levels, confirmation gate |
| `test_observer` | 9 | observation of tool outcomes |
| `test_ui` | 74 | **Phase 11B** GUI: state machine, orb, overlay fade/expand/auto-hide, voice worker session, pause/resume, exit, tray guard, real-assistant round trip |
| **Total** | **721** | |

Run individually: `python -m tests.<name>` (e.g. `python -u -m tests.test_windows`).

### 7.2 Boot test
`python -u -m core.astra` — "Astra is starting.", all 14 tools registered, Whisper loads lazily, process waits on the wake word. Verified on the i5-7300U / 8 GB machine.

### 7.3 Live smoke (deterministic, no cloud)
- `what are my computer specifications` → *"This is a computer 'EDRYNE', running Windows-11-10.0.22631-SP0, with an Intel(R) Core(TM) i5-7300U CPU @ 2.60GHz, 4 logical processors, Intel(R) HD Graphics 620, 7.8 GB RAM, about 15.5 GB free on C:."*
- `how much ram do i have` → *"Your computer has 7.8 GB of RAM, with about 0.6 GB available."*
- `what is using the most memory` → *"Opencode is using the most memory right now, about 451.9 MB."*
- `how is my computer doing` → *"Your computer looks under load. your CPU is about 49% busy, 92.4% of your RAM is used (7.3 of 7.8 GB), you're on battery with 80% left, about 15.5 GB free on C:."*
- `what wifi am i connected to` → *"You are connected to Wi-Fi network 'GENTEX'."*
- `is chrome installed` / `do i have vs code` → yes / yes.
- `show me my drives` → *"Your drives: C: 15.5 free of 175.3 GB, E: 19.3 free of 63.1 GB."*
- `is chrome running` → *"Yes, chrome is running with 27 window(s)."* → `close it` → *"Are you sure you want me to do that?"* → `yes` → closed (confirmation gate proven live).
- `show me my downloads` → opens folder; then `what files are here` lists Downloads (42 items) — "here" tracking works.

---

## 8. Project Tree

```
Astra/
├── main.py                    # entry point
├── config.py / config/        # settings, .env (secrets), __init__
├── ai/                        # planner, intent map, providers (cloud/local/unavailable)
├── core/
│   ├── astra.py               # main voice loop + state machine
│   ├── brain.py               # AstraBrain orchestrator
│   ├── commands.py / commands_backup.py
│   ├── intents.py             # 141 app aliases
│   ├── planner.py             # phase-3 planner wrapper
│   ├── task_engine.py         # multi-step goals, retries, replan
│   ├── confirmation.py        # risk levels, confirmation gate
│   ├── observer.py            # tool-outcome observation
│   ├── state.py               # conversation state machine
│   ├── logger.py
│   ├── capabilities/          # Phase 6 families
│   │   └── windows/           # Phase 7: system, storage, network, processes,
│   │                          #   applications, files, folders, locations
│   └── intelligence/          # Phase 6: intent, nlu, router, response,
│                              #   context, assistant
├── tools/                     # registry, safety, base, and tool modules
│   ├── application_tools.py   # open_application
│   ├── browser_tools.py       # open_url, search_web
│   ├── system_tools.py        # time, date, system_info (13 topics)
│   ├── file_tool.py           # search/list/open/read/create/delete
│   └── process_tools.py       # close_application (Win32 ctypes)
├── voice/                     # wake_word, microphone, whisper, speaker, VAD
├── memory/                    # SQLite persistence
├── ui/                        # Phase 11B GUI package (theme, state, signals, orb, overlay, tray, workers, app)
├── tests/                     # 14 suites + performance_probe
├── data/                      # whisper test audio, apps_cache.json
└── logs/                      # astra.log
```

---

## 9. Known Limitations

- **Per-process CPU ranking** is not implemented; "what is using the most cpu" reports overall CPU usage instead.
- **Model-assisted conversation and model-selected tool calls** require a configured provider and API key; without one, Astra remains deterministic and fully local. The model is never allowed to execute arbitrary shell/Python commands. A local Ollama provider is also available for laptop-only operation when a small local model is installed.
- **Wake-word end-to-end** (mic) verification requires the physical microphone. The current bundled model is still `alexa_v0.1.onnx`; the model filename is configurable so a genuine "Hey Astra" model can be substituted later.
- **Wi-Fi/network probing** depends on the machine state (offline → honest "not connected"); the HTTPS probe can be slow in constrained networks (3 s timeout).
- **Application discovery** is a snapshot at cache time (refreshed every 7 days or when the cache is missing).
- The project is not a git repository. `requirements.txt` now records the external runtime dependencies used by the voice stack.

---

## 10. How to Run

```powershell
# from the project root
.\.venv\Scripts\python.exe main.py                 # GUI mode: system tray + floating overlay (default)
.\.venv\Scripts\python.exe -u -m core.astra        # console voice assistant (wake word: "Alexa")
.\.venv\Scripts\python.exe -u -m tests.test_ui     # any suite, e.g. Phase 11B GUI
```

**Report end.** All data in sections 7 comes from the verified 14 August 2026 run.

## Architecture Stabilization Update (August 2026)

The project was reviewed after Phase 7 and stabilized before the next intelligence phase.

### Corrections applied

- Configuration now loads `config/.env` in addition to a root `.env`, while environment variables still take precedence.
- Wake-word model resolution no longer depends on the `.venv` directory layout. The model filename is configurable through `WAKE_WORD_MODEL`.
- Wake-word sensitivity is configurable and now defaults to `0.7` to reduce accidental activations in noisy environments.
- `core.intelligence.context.ConversationContext` is now the canonical conversation-context implementation.
- `memory.context.ConversationContext` remains as a compatibility import so existing modules and tests do not need an immediate rewrite.
- `AstraAssistant` now shares the same context instance owned by `AstraBrain` by default. This prevents Phase 5 and Phase 6 from maintaining separate histories, pending confirmations, and browser-topic state.
- `requirements.txt` now lists the direct runtime dependencies needed to recreate the Python environment.
- Obsolete backup/test runtime artifacts were removed from the distributable source archive: `core/commands_backup.py`, generated Whisper test audio, the duplicate Vosk model archive, the SQLite runtime database, and the runtime log.
- The virtual environment is excluded from the updated archive. It must be recreated from `requirements.txt` on a target Windows installation.

### Deliberately not changed

- The current OpenWakeWord model remains `alexa_v0.1.onnx` because the uploaded project does not contain a trained `Hey Astra` model. The model is now configurable, so replacing it later does not require a source-code change.
- The deterministic planner remains the reliable local fallback. The cloud/local AI provider architecture remains available for the future conversational reasoning phase.
- Windows-specific code remains Windows-specific; full runtime tests must be executed on the target Windows machine.


## 11. Phase 11B — Floating Voice Assistant Interface

This phase adds a compact, frameless, floating overlay that appears only when Astra is activated and disappears after a short inactivity timeout. The GUI is intentionally a frontend on top of the existing voice runtime, not a replacement for the wake-word, Whisper, memory, tool, or safety architecture.

### Design

- Default runtime state is quiet and background-only.
- The overlay is a lightweight Qt surface with a dark translucent glass look, rounded corners, and a compact bottom-center placement on the primary monitor.
- It is always-on-top while active, but it does not steal focus from the user's Windows application.
- The design keeps the assistant feeling like a native desktop voice agent rather than a conventional app window.

### Architecture

Astra's GUI remains a thin UI layer connected to the existing runtime:

- [ui/app.py](ui/app.py) boots the Qt app, wires the overlay to the signal hub, and owns clean shutdown.
- [ui/overlay.py](ui/overlay.py) implements the floating glass panel, fade-in/fade-out, auto-hide, expanded mode, and transcript area.
- [ui/orb.py](ui/orb.py) renders the animated orb and applies the listening/thinking/speaking/error states.
- [ui/state.py](ui/state.py) centralizes the GUI finite-state machine.
- [ui/signals.py](ui/signals.py) provides the single thread-boundary signal hub.
- [ui/theme.py](ui/theme.py) keeps the visual design and sizing centralized.
- [ui/tray.py](ui/tray.py) keeps Astra alive in the Windows tray with Open / Pause / Resume / Settings / About / Exit controls.
- [ui/workers.py](ui/workers.py) owns the background voice loop, wake-word wait, speech processing, conversation flow, and provider-status reporting.

### State machine

The GUI machine is intentionally centralized and validated:

- `IDLE` -> `LISTENING` when the wake word is detected.
- `LISTENING` -> `THINKING` while the request is processed.
- `THINKING` -> `SPEAKING` when the spoken response is ready.
- `SPEAKING` -> `IDLE` after the TTS step completes.
- Any state -> `ERROR` if a runtime failure occurs.
- `ERROR` -> `IDLE` after recovery or a reset.

This machine ensures the UI never has scattered visual state logic across unrelated modules.

### Wake-word integration

- The authoritative system remains [voice/wake_word.py](voice/wake_word.py), not a separate GUI wake detector.
- The current default model remains configurable via `WAKE_WORD_MODEL` in [config/settings.py](config/settings.py).
- The overlay is shown on the wake signal, then it switches to `LISTENING` while the underlying Whisper pipeline handles user speech.
- The UI does not claim a specific "Hey Astra" model unless the project is configured with one; the label remains generic when the active model is only a generic OpenWakeWord model.

### Whisper and conversation flow

- After the wake word, the interface transitions to `LISTENING` and displays the live status.
- The existing Whisper pipeline continues to be the single speech-to-text implementation.
- Recognized text is mirrored into the transcript area and the overlay remains visible while the assistant processes the request and then replies.
- Follow-up conversation continues without a second wake word until the inactivity timeout expires.

### Ollama and provider status

- The UI reports the actual provider status via `provider_status` and displays the available label in the header chip.
- It uses the configured provider and model rather than a hard-coded default model string.
- If Ollama is inaccessible, the interface still stays alive and falls back to Astra's deterministic local path without crashing.

### Threading strategy

- The main GUI thread only handles Qt rendering and signal-driven UI updates.
- The voice loop runs on a separate worker thread.
- Wake-word listening, Whisper recognition, tool execution, and TTS remain outside the GUI thread.
- This keeps the overlay responsive even while audio or LLM work is happening.

### System tray and shutdown

- [ui/tray.py](ui/tray.py) adds the standard Astra tray experience: Open, Pause Listening, Resume Listening, Settings, About, and Exit.
- Exit is routed through the existing worker shutdown and overlay cleanup flow so the wake listener, GUI, and background processes stop cleanly.

### Performance considerations

- The orb animation runs on a modest timer frame rate with no expensive repeated FFTs.
- The overlay uses OpacityEffect and simple animation instead of a full heavy UI stack.
- The design remains suitable for the target machine class: Intel Core i5-7300U, 8 GB RAM, Intel HD Graphics 620.

### Verification status (verified 14 August 2026)

All Phase 11B behavior is verified, not just compile-checked:

- **`tests/test_ui.py` — 74 checks, 0 failures** (headless, `QT_QPA_PLATFORM=offscreen`): UI state machine transitions, orb modes/amplitude clamping/painting, overlay show/fade-in/fade-out/auto-hide/expand/transcript/text input, the full voice-worker session (wake -> greet -> recognize -> process -> speak -> conversation follow-up -> timeout -> farewell), pause/resume of the wake listener, typed commands without the wake word, graceful stop, "close astra" exit, assistant-error survival, tray availability guard, provider labels, and a real `AstraAssistant` round trip (time query, identity query, exit).
- **Full regression: all 14 suites, 721 checks, 0 failures** (existing 647 + 74 new).
- **`python -m compileall .` — clean.**
- **GUI boot test:** `python main.py` starts hidden, registers all 14 tools, process stays alive waiting for the wake word; tray icon available (offscreen tests confirm the no-tray guard).
- **CLI mode intact:** `python -u -m core.astra` still runs the console voice loop; `voice/wake_word.py` gained optional `stop_event`/`break_event` hooks (backwards compatible) so the GUI worker can end a wake wait cleanly.

### Known limitations

- The wake-word model is still `alexa_v0.1.onnx` (configurable via `WAKE_WORD_MODEL`); the UI never claims it is a "Hey Astra" model.
- The overlay text input is a convenience; voice remains primary, and typed commands are processed at the next worker decision point.
- Real-time voice visualization is a simulated amplitude pulse (no duplicate microphone stream), by design.
- "Settings" is a read-only status dialog (provider, model, version); no settings editing UI.
- Full end-to-end mic verification (real wake word on hardware) requires the user's microphone; suites + boot tests stand in as verification.

### How to run

```powershell
.\.venv\Scripts\python.exe main.py          # GUI mode: tray + floating overlay (default)
.\.venv\Scripts\python.exe -u -m core.astra # classic console mode (unchanged)
.\.venv\Scripts\python.exe -u -m tests.test_ui   # headless GUI test suite
```

### Files involved

- [ui/__init__.py](ui/__init__.py)
- [ui/app.py](ui/app.py)
- [ui/orb.py](ui/orb.py)
- [ui/overlay.py](ui/overlay.py)
- [ui/signals.py](ui/signals.py)
- [ui/state.py](ui/state.py)
- [ui/theme.py](ui/theme.py)
- [ui/tray.py](ui/tray.py)
- [ui/workers.py](ui/workers.py)
- [config/settings.py](config/settings.py)
- [main.py](main.py)
- [requirements.txt](requirements.txt)
- [tests/test_ui.py](tests/test_ui.py)

---

## 12. Phase 8+ Model-assisted Intelligence

Astra now has an optional model reasoning layer. The model is only consulted after the deterministic planner and semantic NLU cannot resolve a request. It can return:

1. a conversational reply,
2. a clarification question, or
3. one structured `ToolCall`.

A model-selected tool call is still passed to `ToolRegistry`, `ToolSafety`, validation, and the confirmation gate. The model therefore has no direct shell, Python, process, or filesystem execution channel.

When `AI_PROVIDER=none` (the default), this layer is inactive and Astra remains fully deterministic/local. `AI_PROVIDER=ollama` enables a local model over localhost, while `AI_PROVIDER=cloud` enables an OpenAI-compatible remote provider. In both cases the model can only produce a reply, clarification, or validated `ToolCall`.

## 12. Packaging

The distributable project excludes `.venv`, Python caches, runtime logs, generated databases, and other machine-specific artifacts. Recreate the virtual environment from `requirements.txt` on the target Windows machine.

## Ollama Local AI Route (Added)

Astra now includes an optional local conversational AI route through Ollama. The integration uses Ollama's localhost HTTP API directly, so no Python Ollama SDK is required. The default configured model is `qwen2.5:3b-instruct`. The model is not bundled with Astra; it must be installed separately with Ollama.

The route is isolated behind `ai/ollama_provider.py` and selected through `AI_PROVIDER=ollama`. If Ollama is not running or the configured model is unavailable, Astra's deterministic intelligence continues to operate instead of failing the assistant. Model-generated tool requests are still converted into `ToolCall` objects and pass through Astra's normal registry, validation, safety, and confirmation path.

For Windows setup, run `setup_ollama.ps1` after installing Ollama. Use `python tools\ollama_status.py` to verify that the local service and model are available.
