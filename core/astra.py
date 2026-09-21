import time

from config.settings import CONVERSATION_TIMEOUT
from core.brain import AstraBrain
from core.intelligence.assistant import AstraAssistant
from core.state import (
    CONVERSATION,
    EXECUTING,
    LISTENING_FOR_COMMAND,
    LISTENING_FOR_WAKE_WORD,
    RESPONDING,
    AstraState,
)
from voice.speaker import AstraSpeaker
from voice.wake_word import AstraWakeWord
from voice.whisper import AstraWhisper


class Astra:

    def __init__(self):
        self.speaker = AstraSpeaker()
        self.wake_word = AstraWakeWord()
        self.whisper = AstraWhisper()
        self.brain = AstraBrain()
        self.assistant = AstraAssistant(brain=self.brain)
        self.state = AstraState()

    def wait_for_wake_word(self):
        """
        Wait until the wake word is detected.
        Returns True when detected.
        """

        detected = False

        def on_wake():
            nonlocal detected
            detected = True

        self.wake_word.listen(on_wake)

        return detected

    def _handle_command(self, command):
        """Process one utterance through the assistant and speak it."""

        self.state.transition(EXECUTING)

        result = self.assistant.process(command)

        self.state.transition(RESPONDING)

        if result is not None and result.response:

            self.speaker.speak(result.response)

        return result

    def _conversation(self):
        """Keep listening after the wake word without repeating it.

        Silence for CONVERSATION_TIMEOUT seconds ends the
        conversation and returns to wake-word listening.
        """

        print()
        print("Conversation open - keep talking.")
        print("Stop speaking to end the conversation.")
        print()

        self.state.transition(CONVERSATION)

        last_heard = time.time()

        while True:

            text = self.whisper.listen()

            if not text:

                if time.time() - last_heard >= CONVERSATION_TIMEOUT:

                    print("Conversation ended.")

                    self.speaker.speak(
                        "I'll be here if you need me."
                    )

                    self.state.transition(LISTENING_FOR_WAKE_WORD)

                    return False

                continue

            last_heard = time.time()

            print()
            print(f"You said: {text}")
            print()

            result = self._handle_command(text)

            if result is not None and result.exit:

                self.state.reset()

                return True

    def run(self):

        print("================================")
        print("           ASTRA")
        print("================================")
        print()

        self.speaker.speak("Astra is starting.")
        self.speaker.speak("Astra is ready.")

        try:

            self.state.transition(LISTENING_FOR_WAKE_WORD)

            while True:

                # ==================================
                # WAIT FOR WAKE WORD
                # ==================================

                print()
                print("Astra is listening...")
                print("Say the wake word.")
                print("Press CTRL+C to stop.")
                print()

                self.wait_for_wake_word()

                print()
                print("Wake word accepted.")

                self.speaker.speak("Hey Edrine.")

                self.state.transition(LISTENING_FOR_COMMAND)

                # ==================================
                # FIRST COMMAND
                # ==================================

                command = self.whisper.listen()

                if not command:

                    self.speaker.speak(
                        "I didn't hear you."
                    )

                    self.state.transition(LISTENING_FOR_WAKE_WORD)

                    continue

                print()
                print(f"You said: {command}")
                print()

                result = self._handle_command(command)

                if result is not None and result.exit:

                    self.state.reset()

                    break

                # ==================================
                # CONVERSATION (no wake word needed)
                # ==================================

                if self._conversation():

                    break

        except KeyboardInterrupt:

            print()
            print("Astra stopped.")


if __name__ == "__main__":
    Astra().run()