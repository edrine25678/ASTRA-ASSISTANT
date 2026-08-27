import subprocess
import webbrowser
import os
from datetime import datetime


class AstraCommands:

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
        # OPEN CHROME
        # ==========================================

        if "chrome" in text and self.is_open_command(text):
            self.open_chrome()
            return "Opening Chrome."

        # ==========================================
        # OPEN NOTEPAD
        # ==========================================

        if "notepad" in text and self.is_open_command(text):
            self.open_notepad()
            return "Opening Notepad."

        # ==========================================
        # OPEN CALCULATOR
        # ==========================================

        if (
            "calculator" in text
            or "calc" in text
        ) and self.is_open_command(text):

            self.open_calculator()
            return "Opening Calculator."

        # ==========================================
        # OPEN FILE EXPLORER
        # ==========================================

        if (
            "file explorer" in text
            or "file manager" in text
            or "explorer" in text
        ) and self.is_open_command(text):

            self.open_file_explorer()
            return "Opening File Explorer."

        # ==========================================
        # OPEN VS CODE
        # ==========================================

        if (
            "vs code" in text
            or "visual studio code" in text
            or "code editor" in text
        ) and self.is_open_command(text):

            self.open_vs_code()
            return "Opening Visual Studio Code."

        # ==========================================
        # OPEN GOOGLE
        # ==========================================

        if "google" in text and self.is_open_command(text):
            webbrowser.open("https://www.google.com")
            return "Opening Google."

        # ==========================================
        # OPEN YOUTUBE
        # ==========================================

        if "youtube" in text and self.is_open_command(text):
            webbrowser.open("https://www.youtube.com")
            return "Opening YouTube."

        # ==========================================
        # OPEN GMAIL
        # ==========================================

        if "gmail" in text and self.is_open_command(text):
            webbrowser.open("https://mail.google.com")
            return "Opening Gmail."

        # ==========================================
        # OPEN CHATGPT
        # ==========================================

        if "chatgpt" in text and self.is_open_command(text):
            webbrowser.open("https://chatgpt.com")
            return "Opening ChatGPT."

        # ==========================================
        # UNKNOWN COMMAND
        # ==========================================

        return "I don't know how to do that yet."

    # ==========================================
    # COMMAND DETECTION
    # ==========================================

    def is_open_command(self, text):

        return any(
            word in text
            for word in [
                "open",
                "launch",
                "start",
                "run"
            ]
        )

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