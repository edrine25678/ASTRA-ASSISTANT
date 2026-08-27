import subprocess
import webbrowser
import os
from datetime import datetime

from core.intents import detect_intent


class AstraCommands:

    # ==========================================
    # APPLICATION REGISTRY
    # ==========================================

    APP_ACTIONS = {
        "chrome": "open_chrome",
        "notepad": "open_notepad",
        "calculator": "open_calculator",
        "file explorer": "open_file_explorer",
        "vs code": "open_vs_code",
        "google": "open_google",
        "youtube": "open_youtube",
        "gmail": "open_gmail",
        "chatgpt": "open_chatgpt",
    }

    APP_RESPONSES = {
        "chrome": "Opening Chrome.",
        "notepad": "Opening Notepad.",
        "calculator": "Opening Calculator.",
        "file explorer": "Opening File Explorer.",
        "vs code": "Opening Visual Studio Code.",
        "google": "Opening Google.",
        "youtube": "Opening YouTube.",
        "gmail": "Opening Gmail.",
        "chatgpt": "Opening ChatGPT.",
    }

    def execute(self, text):

        text = text.lower().strip()

        print(f"Astra command: {text}")

        # ==========================================
        # EXIT ASTRA
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "exit astra",
                "quit astra",
                "shutdown astra",
                "stop listening",
                "goodbye astra"
            ]
        ):
            return "__EXIT__"

        # ==========================================
        # GREETINGS
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "hello astra",
                "hi astra",
                "hey astra",
                "hello",
                "hi"
            ]
        ):
            return "Hello Edrine. How can I help you?"

        # ==========================================
        # HOW ARE YOU
        # ==========================================

        if "how are you" in text:
            return "I'm doing great, Edrine. I'm ready to help."

        # ==========================================
        # WHO ARE YOU
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "who are you",
                "what are you",
                "tell me about yourself"
            ]
        ):
            return "I'm Astra, your personal desktop assistant."

        # ==========================================
        # THANK YOU
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "thank you",
                "thanks"
            ]
        ):
            return "You're welcome, Edrine."

        # ==========================================
        # TIME
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "what time is it",
                "tell me the time",
                "current time",
                "time"
            ]
        ):
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."

        # ==========================================
        # DATE
        # ==========================================

        if any(
            phrase in text
            for phrase in [
                "what is today's date",
                "what's today's date",
                "tell me the date",
                "today's date",
                "current date"
            ]
        ):
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {current_date}."

        # ==========================================
        # OPEN APPLICATION
        #
        # Intent-based detection:
        # normalization -> intent -> action.
        # ==========================================

        intent = detect_intent(text)

        if intent is None:

            return "I don't know how to do that yet."

        method_name = self.APP_ACTIONS.get(intent.target)

        response = self.APP_RESPONSES.get(intent.target)

        if method_name is None or response is None:

            return "I don't know how to do that yet."

        print(
            f"Astra intent: {intent.name} "
            f"-> {intent.target} "
            f"(confidence {intent.confidence:.2f})"
        )

        getattr(self, method_name)()

        return response

    # ==========================================
    # OPEN CHROME
    # ==========================================

    def open_chrome(self):

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",

            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",

            os.path.expandvars(
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
            )
        ]

        for path in chrome_paths:

            if os.path.exists(path):

                subprocess.Popen([path])

                return

        subprocess.Popen(
            "start chrome",
            shell=True
        )

    # ==========================================
    # OPEN NOTEPAD
    # ==========================================

    def open_notepad(self):

        subprocess.Popen(
            "notepad.exe",
            shell=True
        )

    # ==========================================
    # OPEN CALCULATOR
    # ==========================================

    def open_calculator(self):

        subprocess.Popen(
            "calc.exe",
            shell=True
        )

    # ==========================================
    # OPEN FILE EXPLORER
    # ==========================================

    def open_file_explorer(self):

        subprocess.Popen(
            "explorer.exe",
            shell=True
        )

    # ==========================================
    # OPEN VS CODE
    # ==========================================

    def open_vs_code(self):

        try:

            subprocess.Popen(
                "code",
                shell=True
            )

        except Exception:

            return

    # ==========================================
    # OPEN GOOGLE
    # ==========================================

    def open_google(self):

        webbrowser.open("https://www.google.com")

    # ==========================================
    # OPEN YOUTUBE
    # ==========================================

    def open_youtube(self):

        webbrowser.open("https://www.youtube.com")

    # ==========================================
    # OPEN GMAIL
    # ==========================================

    def open_gmail(self):

        webbrowser.open("https://mail.google.com")

    # ==========================================
    # OPEN CHATGPT
    # ==========================================

    def open_chatgpt(self):

        webbrowser.open("https://chatgpt.com")