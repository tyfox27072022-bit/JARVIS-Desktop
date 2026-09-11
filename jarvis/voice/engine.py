import subprocess
import sys


class VoiceEngine:
    def __init__(self, settings: dict):
        self.settings = settings or {}

    @property
    def enabled(self) -> bool:
        return bool(self.settings.get("enabled"))

    def speak(self, text: str) -> None:
        if not text:
            return
        if sys.platform != "win32":
            return
        safe = (
            text.replace('"', "")
            .replace("'", "")
            .replace("\n", " ")
            .replace("\r", " ")[:500]
        )
        rate = int(self.settings.get("rate", 0))
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate={rate}; $s.Speak(\"{safe}\")"
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                shell=False,
            )
        except Exception:
            pass

    def listen(self) -> str:
        try:
            import speech_recognition as sr
        except Exception as e:
            raise RuntimeError(
                f"SpeechRecognition not installed ({e}). Type instead, or install optional voice packages."
            )
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
        return r.recognize_google(audio)
