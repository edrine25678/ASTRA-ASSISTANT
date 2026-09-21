"""Astra entry point.

Launches the floating-interface voice assistant.  If the Qt
dependency is missing, falls back to the classic console mode.
"""



def main():
    try:
        from ui.app import run_gui
    except ImportError as error:
        print(
            "The Astra interface needs PySide6-Essentials: "
            f"{error}"
        )
        print("Falling back to voice-only console mode.")
        from core.astra import Astra

        Astra().run()
        return 0

    raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
