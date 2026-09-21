import logging
import os

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from config.settings import WAKE_WORD_MODEL, WAKE_WORD_THRESHOLD

logger = logging.getLogger(__name__)


class AstraWakeWord:

    SAMPLE_RATE = 16000
    CHANNELS = 1
    BLOCK_SIZE = 1280

    def __init__(self):

        model_path = self._find_model(WAKE_WORD_MODEL)

        if model_path is None:
            raise FileNotFoundError(
                "Wake-word model not found. Expected "
                f"'{WAKE_WORD_MODEL}' in the OpenWakeWord resources/models "
                "directory or at the path configured by WAKE_WORD_MODEL."
            )

        self.model = Model(
            wakeword_models=[model_path],
            inference_framework="onnx",
        )

        self.threshold = WAKE_WORD_THRESHOLD


    @staticmethod
    def _find_model(model_name):
        """Resolve a wake-word model without depending on the virtualenv path."""

        candidates = []
        requested = os.path.expandvars(os.path.expanduser(model_name))

        if os.path.isabs(requested):
            candidates.append(requested)
        else:
            candidates.append(os.path.abspath(requested))

            try:
                import openwakeword
                package_dir = os.path.dirname(openwakeword.__file__)
                candidates.append(
                    os.path.join(package_dir, "resources", "models", requested)
                )
            except (ImportError, OSError):
                logger.debug("Could not locate openwakeword package dir", exc_info=True)

            candidates.append(
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "data", "models", "wake", requested
                )
            )

        for path in candidates:
            if os.path.isfile(path):
                return os.path.abspath(path)

        return None

    def listen(self, on_wake, stop_event=None, break_event=None):
        """Listen for the wake word until detected.

        on_wake is called from the audio callback when the wake word
        is detected.  Optional threading.Event hooks let a caller end
        the wait cleanly:

          stop_event  - set  -> return False (listener should stop)
          break_event - set  -> return True  (wake flow interrupted,
                                caller decides what happened)
        """

        print("Astra is listening...")
        print("Say the wake word.")
        print("Press CTRL+C to stop.")
        print()

        detected = False

        def callback(indata, frames, time, status):

            nonlocal detected

            if status:
                print(f"Audio status: {status}")

            if detected:
                return

            audio = indata[:, 0]

            audio_int16 = (
                audio * 32767
            ).astype(np.int16)

            predictions = self.model.predict(
                audio_int16
            )

            for name, score in predictions.items():

                if score >= self.threshold:

                    print(
                        f"Wake word detected: "
                        f"{name} ({score:.3f})"
                    )

                    detected = True

                    self.model.reset()

                    on_wake()

                    return

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=self.BLOCK_SIZE,
            callback=callback,
        ):

            while not detected:

                if stop_event is not None and stop_event.is_set():
                    return False

                if break_event is not None and break_event.is_set():
                    return True

                sd.sleep(100)

        return True