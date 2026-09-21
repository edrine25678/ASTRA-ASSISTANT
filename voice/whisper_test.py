import os
import wave

import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5

OUTPUT_FILE = "data/whisper_test.wav"


print("================================")
print("       ASTRA WHISPER TEST")
print("================================")
print()

print("Loading Whisper model...")
print("This may take a while the first time.")

model = WhisperModel(
    "tiny.en",
    device="cpu",
    compute_type="int8"
)

print("Whisper model loaded.")
print()

print("Get ready...")
input("Press ENTER, then speak: ")

print()
print("Recording for 5 seconds...")
print("Speak clearly: 'Open Chrome'")

audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="int16"
)

sd.wait()

print("Recording completed.")

os.makedirs("data", exist_ok=True)

with wave.open(OUTPUT_FILE, "wb") as wf:
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio.tobytes())

print("Audio saved.")

print()
print("Transcribing...")

segments, info = model.transcribe(
    OUTPUT_FILE,
    language="en",
    beam_size=5,
    vad_filter=True
)

text = " ".join(segment.text.strip() for segment in segments)

print()
print("================================")
print("Astra heard:")
print(text)
print("================================")