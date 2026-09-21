import json
import os
import queue

import sounddevice as sd
from vosk import KaldiRecognizer, Model


class AstraSpeech:
    def __init__(self):
        self.model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "models",
            "vosk",
            "vosk-model-small-en-us-0.15"
        )

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Vosk model not found:\n{self.model_path}"
            )

        print("Loading Astra speech model...")
        self.model = Model(self.model_path)

        self.sample_rate = 16000
        self.audio_queue = queue.Queue()

        print("Astra speech model loaded.")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")

        self.audio_queue.put(bytes(indata))

    def listen(self):
        recognizer = KaldiRecognizer(
            self.model,
            self.sample_rate
        )

        print("\nAstra is listening for speech...")
        print("Speak now. Press CTRL+C to stop.\n")

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._audio_callback
        ):
            while True:
                data = self.audio_queue.get()

                if recognizer.AcceptWaveform(data):
                    result = json.loads(
                        recognizer.Result()
                    )

                    text = result.get("text", "").strip()

                    if text:
                        return text


if __name__ == "__main__":
    print("==============================")
    print("      ASTRA SPEECH TEST")
    print("==============================")

    try:
        speech = AstraSpeech()

        while True:
            text = speech.listen()

            print(f"Astra heard: {text}")

    except KeyboardInterrupt:
        print("\nSpeech test stopped.")

    except OSError as e:
        print(f"\nSpeech error: {e}")
