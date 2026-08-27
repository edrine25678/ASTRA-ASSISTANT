"""
Unit-style tests for the command normalization and intent layer.

Run from the project root:

    python tests/test_intents.py
    (or: .venv/Scripts/python.exe tests/test_intents.py)

Note: the execute() tests really launch the applications.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.commands import AstraCommands
from core.intents import OPEN_APPLICATION, detect_intent, normalize_text


_PASS = 0
_FAIL = 0


def _check(label, actual, expected):

    global _PASS, _FAIL

    if actual == expected:

        _PASS += 1

        return True

    _FAIL += 1

    print(f"FAIL: {label}")
    print(f"  expected: {expected!r}")
    print(f"  actual:   {actual!r}")

    return False


def _intent_target(text):

    intent = detect_intent(text)

    if intent is None:
        return None

    assert intent.name == OPEN_APPLICATION

    return intent.target


def test_normalization():

    print()
    print("--- NORMALIZATION ---")

    cases = [
        ("  open    chrome  ", "open chrome"),
        ("Open Chrome.", "open chrome"),
        ("Please open the Chrome for me", "open chrome"),
        ("Could you open Chrome?", "open chrome"),
        ("Open the File Explorer", "open file explorer"),
        ("Hey astra open chrome", "open chrome"),
    ]

    for raw, expected in cases:
        _check(f"normalize({raw!r})", normalize_text(raw), expected)


def test_open_app_intents():

    print()
    print("--- OPEN APPLICATION INTENTS ---")

    cases = [
        # Required test inputs
        ("open chrome", "chrome"),
        ("open the chrome", "chrome"),
        ("please open chrome for me", "chrome"),
        ("launch chrome", "chrome"),
        ("open not bad", "notepad"),
        ("open your tube", "youtube"),
        ("open file explorer", "file explorer"),
        ("start calculator", "calculator"),
        ("open vscode", "vs code"),
        # Natural variations
        ("Open Chrome", "chrome"),
        ("Open Chrome.", "chrome"),
        ("could you open chrome", "chrome"),
        ("can you open chrome for me", "chrome"),
        ("run chrome", "chrome"),
        ("start chrome", "chrome"),
        ("open google chrome", "chrome"),
        ("open the chrome for me please", "chrome"),
        ("open chrome app", "chrome"),
        ("open notepad", "notepad"),
        ("open the notepad app", "notepad"),
        ("open notpad", "notepad"),
        ("open youtube", "youtube"),
        ("open you tube", "youtube"),
        ("open your tube for me", "youtube"),
        ("open the file explorer", "file explorer"),
        ("open file the explorer", "file explorer"),
        ("open explorer", "file explorer"),
        ("and file the explorer", "file explorer"),
        ("open calc", "calculator"),
        ("open the calculator app", "calculator"),
        ("open vs code", "vs code"),
        ("open visual studio code", "vs code"),
        ("open code editor", "vs code"),
        ("open google", "google"),
        ("open gmail", "gmail"),
        ("open g mail", "gmail"),
        ("open chat gpt", "chatgpt"),
        ("open chatgpt", "chatgpt"),
        # Known whisper artifacts
        ("on youtube", "youtube"),
        ("and file the explorer", "file explorer"),
        ("and open chrome", "chrome"),
        ("open yourtube", "youtube"),
    ]

    for raw, expected in cases:
        _check(f"intent({raw!r})", _intent_target(raw), expected)


def test_unknown_commands():

    print()
    print("--- UNKNOWN COMMANDS ---")

    cases = [
        "chrome",
        "open fortnite",
        "open not bat",
        "open notepad appx",
        "play music",
        "tell me a joke",
        "open",
        "",
        "open calculator and chrome",
        "what time is it",
        "open google docs",
    ]

    for raw in cases:
        _check(f"unknown({raw!r})", _intent_target(raw), None)


def test_confidence():

    print()
    print("--- CONFIDENCE ---")

    exact = detect_intent("open not bad")
    _check("not bad -> confidence 1.0", round(exact.confidence, 2), 1.0)

    artifact = detect_intent("on youtube")
    _check("on-rule -> confidence 0.9", round(artifact.confidence, 2), 0.9)


def test_execute_pipeline():

    print()
    print("--- EXECUTE PIPELINE (launches real apps) ---")

    commands = AstraCommands()

    cases = [
        ("open chrome", "Opening Chrome."),
        ("open the chrome", "Opening Chrome."),
        ("please open chrome for me", "Opening Chrome."),
        ("launch chrome", "Opening Chrome."),
        ("open not bad", "Opening Notepad."),
        ("open your tube", "Opening YouTube."),
        ("open file explorer", "Opening File Explorer."),
        ("start calculator", "Opening Calculator."),
        ("open vscode", "Opening Visual Studio Code."),
        ("open google", "Opening Google."),
        ("open gmail", "Opening Gmail."),
        ("open chatgpt", "Opening ChatGPT."),
        ("open fortnite", "I don't know how to do that yet."),
        ("hello astra", "Hello Edrine. How can I help you?"),
        ("exit astra", "__EXIT__"),
    ]

    for raw, expected in cases:
        _check(f"execute({raw!r})", commands.execute(raw), expected)

    result = commands.execute("what time is it")
    _check(
        "execute(what time is it)",
        result.startswith("The current time is"),
        True
    )


def main():

    print("================================")
    print("    ASTRA INTENT TESTS")
    print("================================")

    test_normalization()
    test_open_app_intents()
    test_unknown_commands()
    test_confidence()
    test_execute_pipeline()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()