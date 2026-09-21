import logging

import pyttsx3

from config.settings import VOICE_RATE

logger = logging.getLogger(__name__)


class AstraSpeaker:

    def __init__(self):

        print("[TTS] Initializing Windows SAPI5...")

        self.engine = pyttsx3.init("sapi5")

        self.engine.setProperty(
            "rate",
            VOICE_RATE
        )

        self.engine.setProperty(
            "volume",
            1.0
        )

        voices = self.engine.getProperty("voices")

        if voices:
            self.engine.setProperty(
                "voice",
                voices[0].id
            )

            print(
                f"[TTS] Voice: {voices[0].id}"
            )

        print("[TTS] Windows SAPI5 initialized.")

    def speak(self, text):

        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        print(f"Astra: {text}")

        try:

            self.engine.say(text)

            self.engine.runAndWait()

            print("[TTS] Speech completed.")

        except (OSError, RuntimeError) as error:

            logger.exception("TTS speech error")
            print(
                f"[TTS] Speech error: {error}"
            )

    def stop(self):

        try:
            self.engine.stop()

        except (OSError, RuntimeError):
            logger.debug("TTS engine stop failed", exc_info=True)


if __name__ == "__main__":

    print()
    print("================================")
    print("       ASTRA SPEAKER TEST")
    print("================================")
    print()

    speaker = AstraSpeaker()

    speaker.speak(
        "Hey Edrine. This is Astra. "
        "If you can hear me, the speaker is working."
    )

    print()
    print("Speaker test complete.")