import os

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1280

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    ".venv",
    "Lib",
    "site-packages",
    "openwakeword",
    "resources",
    "models",
    "alexa_v0.1.onnx"
)

MODEL_PATH = os.path.abspath(MODEL_PATH)


print("Astra Wake-Word Engine Test")
print("===========================")
print()
print(f"Model: {MODEL_PATH}")
print()

if not os.path.exists(MODEL_PATH):
    print("ERROR: Wake-word model not found.")
    raise SystemExit(1)

print("Loading ONNX wake-word model...")

try:
    wake_model = Model(
        wakeword_models=[MODEL_PATH],
        inference_framework="onnx"
    )

    print("Wake-word model loaded successfully.")
    print()
    print("Say 'Alexa' to test the detector.")
    print("Press CTRL+C to stop.")
    print()

except (OSError, RuntimeError) as error:
    print("Model loading failed:")
    print(error)
    raise SystemExit(1)


def audio_callback(indata, frames, time, status):

    if status:
        print(f"Audio status: {status}")

    audio = indata[:, 0]

    audio_int16 = (audio * 32767).astype(np.int16)

    try:
        prediction = wake_model.predict(audio_int16)

        for name, score in prediction.items():

            if score > 0.1:
                print(f"{name}: {score:.3f}")

    except (OSError, RuntimeError) as error:
        print(f"Prediction error: {error}")


try:

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCK_SIZE,
        callback=audio_callback
    ):

        while True:
            sd.sleep(1000)

except KeyboardInterrupt:

    print()
    print("Wake-word test stopped.")

except OSError as error:

    print()
    print("Audio error:")
    print(error)