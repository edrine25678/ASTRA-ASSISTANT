import threading

import pyttsx3


def speak():
    print("Starting TTS thread...")

    engine = pyttsx3.init()
    engine.setProperty("volume", 1.0)

    engine.say("This is a worker thread speaker test.")
    engine.runAndWait()

    print("THREAD TTS FINISHED")


thread = threading.Thread(target=speak)
thread.start()
thread.join()

print("Test complete.")