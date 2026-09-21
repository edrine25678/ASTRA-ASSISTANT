from collections import deque

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

from config.settings import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL


class AstraWhisper:

    def __init__(self):

        self.model = None

        print("Whisper model will load on the first command.")

        self.sample_rate = 16000

        # ==========================================
        # AUDIO FRAME SETTINGS
        # ==========================================

        self.frame_duration = 30

        self.frame_size = int(
            self.sample_rate *
            self.frame_duration /
            1000
        )

        # ==========================================
        # VOICE ACTIVITY DETECTION
        # ==========================================

        # 0 = least aggressive
        # 3 = most aggressive
        self.vad = webrtcvad.Vad(2)

        # ==========================================
        # COMMAND SETTINGS
        # ==========================================

        self.max_duration = 8

        self.min_speech_duration = 0.45

        self.silence_duration = 0.7

        # Require several speech frames before
        # deciding that the user actually spoke.
        self.speech_confirmation_frames = 4

        # ==========================================
        # AUDIO ENERGY THRESHOLD
        # ==========================================

        # Helps reject quiet background sounds.
        self.energy_threshold = 450

    # ==============================================
    # MODEL
    # ==============================================

    def _load_model(self):

        if self.model is not None:
            return

        print("Loading Whisper model...")

        self.model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )

        print("Whisper model loaded successfully.")

    # ==============================================
    # LISTEN
    # ==============================================

    def listen(self):

        print()
        print("Astra is listening for speech...")
        print("Speak now.")

        self._load_model()

        frames = []

        speech_started = False

        speech_time = 0

        silence_time = 0

        consecutive_speech = 0

        max_frames = int(
            self.max_duration *
            1000 /
            self.frame_duration
        )

        int(
            self.silence_duration *
            1000 /
            self.frame_duration
        )

        # Keep a small amount of audio before speech.
        pre_buffer_size = 5

        pre_buffer = deque(
            maxlen=pre_buffer_size
        )

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_size
        )

        stream.start()

        try:

            for _ in range(max_frames):

                audio, overflowed = stream.read(
                    self.frame_size
                )

                if overflowed:

                    print(
                        "Warning: audio buffer overflow."
                    )

                frame = audio[:, 0].copy()

                # ==================================
                # AUDIO ENERGY
                # ==================================

                energy = np.sqrt(
                    np.mean(
                        frame.astype(np.float32) ** 2
                    )
                )

                # ==================================
                # WEBRTC VAD
                # ==================================

                vad_speech = self.vad.is_speech(
                    frame.tobytes(),
                    self.sample_rate
                )

                # Require BOTH:
                #
                # 1. VAD says speech
                # 2. Audio has enough energy

                is_speech = (
                    vad_speech
                    and
                    energy >= self.energy_threshold
                )

                # ==================================
                # BEFORE SPEECH
                # ==================================

                if not speech_started:

                    pre_buffer.append(frame)

                    if is_speech:

                        consecutive_speech += 1

                    else:

                        consecutive_speech = 0

                    # Require several consecutive
                    # speech frames.
                    if (
                        consecutive_speech >=
                        self.speech_confirmation_frames
                    ):

                        speech_started = True

                        # Include a little audio from
                        # immediately before speech.
                        frames.extend(
                            list(pre_buffer)
                        )

                        speech_time += (
                            len(pre_buffer) *
                            self.frame_duration
                        )

                        pre_buffer.clear()

                    continue

                # ==================================
                # AFTER SPEECH STARTED
                # ==================================

                if is_speech:

                    frames.append(frame)

                    speech_time += (
                        self.frame_duration
                    )

                    silence_time = 0

                else:

                    # Keep a little silence after the
                    # user's command.
                    frames.append(frame)

                    silence_time += (
                        self.frame_duration
                    )

                    if (
                        silence_time >=
                        self.silence_duration * 1000
                    ):

                        break

        finally:

            stream.stop()
            stream.close()

        # ==========================================
        # NOTHING DETECTED
        # ==========================================

        if not speech_started:

            print(
                "Astra did not detect clear speech."
            )

            return ""

        # ==========================================
        # SPEECH TOO SHORT
        # ==========================================

        if (
            speech_time <
            self.min_speech_duration * 1000
        ):

            print(
                "Astra did not hear enough speech."
            )

            return ""

        # ==========================================
        # CONVERT AUDIO
        # ==========================================

        audio = np.concatenate(frames)

        audio = (
            audio.astype(np.float32)
            / 32768.0
        )

        print("Speech ended.")
        print("Transcribing...")

        # ==========================================
        # WHISPER
        # ==========================================

        segments, _info = self.model.transcribe(

            audio,

            language="en",

            beam_size=5,

            best_of=3,

            vad_filter=True,

            condition_on_previous_text=False,

            no_speech_threshold=0.7,

            log_prob_threshold=-0.8,

            compression_ratio_threshold=2.0,

            repetition_penalty=1.15
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        # ==========================================
        # CLEAN REPETITION
        # ==========================================

        text = self.remove_repetition(text)

        # ==========================================
        # FINAL RESULT
        # ==========================================

        if text:

            print(
                f"Astra heard: {text}"
            )

            return text

        print(
            "Astra did not understand the speech."
        )

        return ""

    # ==============================================
    # REPETITION FILTER
    # ==============================================

    @staticmethod
    def remove_repetition(text):

        words = text.split()

        if len(words) < 4:

            return text

        cleaned = []

        for word in words:

            if len(cleaned) >= 3 and (
                cleaned[-1].lower()
                == word.lower()

                and

                cleaned[-2].lower()
                == word.lower()

                and

                cleaned[-3].lower()
                == word.lower()
            ):

                continue

            cleaned.append(word)

        return " ".join(cleaned)


# ==============================================
# STANDALONE TEST
# ==============================================

if __name__ == "__main__":

    whisper = AstraWhisper()

    while True:

        try:

            text = whisper.listen()

            print()
            print("RESULT:", text)
            print()

        except KeyboardInterrupt:

            print()
            print("Whisper test stopped.")

            break