import sounddevice as sd
import numpy as np


SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1280


def audio_callback(indata, frames, time, status):
    if status:
        print(f"Audio status: {status}")

    audio = indata[:, 0].copy()

    # Convert floating-point audio to 16-bit PCM.
    audio_int16 = (audio * 32767).astype(np.int16)

    print(
        f"Audio received: "
        f"{len(audio_int16)} samples | "
        f"Peak: {np.max(np.abs(audio_int16))}"
    )


print("Astra microphone stream")
print("=======================")
print()
print("Speak into the microphone.")
print("Press CTRL+C to stop.")
print()

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
    print("Astra microphone stream stopped.")

except Exception as error:
    print()
    print("Microphone error:")
    print(error)