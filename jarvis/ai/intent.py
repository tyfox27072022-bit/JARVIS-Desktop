"""Deterministic intent layer so JARVIS acts even when the small model is weak."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


APPS = {
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "paint": "paint",
    "explorer": "explorer",
    "files": "explorer",
    "file explorer": "explorer",
    "discord": "discord",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "edge",
    "microsoft edge": "edge",
    "firefox": "firefox",
    "spotify": "spotify",
    "steam": "steam",
    "task manager": "taskmgr",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "settings": "ms-settings:",
}

SITES = {
    "google": "https://www.google.com",
    "google.com": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.co.uk",
    "twitch": "https://www.twitch.tv",
    "github": "https://github.com",
    "discord web": "https://discord.com/app",
    "whatsapp": "https://web.whatsapp.com",
    "bing": "https://www.bing.com",
}


class IntentRouter:
    def __init__(self, brain):
        self.b = brain

    def handle(self, message: str) -> str | None:
        raw = (message or "").strip()
        if not raw:
            return None
        low = raw.lower().strip("!.?")

        talk = self._smalltalk(low)
        if talk:
            return talk

        if low in {"help", "what can you do", "commands"}:
            return (
                "Tell me in plain English. Search the web, write code in the workspace, "
                "open apps, find and sort folders, check the screen, remember things."
            )

        opened = self._open(raw, low)
        if opened:
            return opened

        if low in {"wifi", "open wifi"}:
            return self.b.pc.open_wifi()

        if "on my screen" in low or low in {"look at my screen", "what's on screen", "whats on screen"}:
            return self.b.pc.screen_report()
        if low in {"list windows", "what windows are open"}:
            return self.b.pc.list_windows()

        if low in {"system status", "pc status", "system"}:
            s = self.b.pc.system_summary()
            return f"CPU {s['cpu_percent']}% · RAM {s['ram_percent']}% · Disk {s.get('disk_percent')}%"

        if self._wants_organize(low):
            from jarvis.pc.organize import organize_folder

            home = Path.home()
            folder = home / "Downloads"
            if "desktop" in low:
                folder = home / "Desktop"
            elif "document" in low:
                folder = home / "Documents"
            return organize_folder(folder, audit=self.b.audit)

        looked = self._search(raw, low)
        if looked:
            return looked

        coded = self._code(raw, low)
        if coded:
            return coded

        run = re.match(r"^run\s+([\w.\-]+\.py)\s*$", low)
        if run:
            try:
                out = self.b.coding.run_python(run.group(1))
                return f"Ran {run.group(1)}:\n{out}"
            except Exception as e:
                return f"Couldn't run that: {e}"

        if low.startswith("remember "):
            text = raw.split(" ", 1)[1]
            text = re.sub(r"^(that\s+)", "", text, flags=re.I).strip()
            self.b.memory.remember(text, "facts")
            return "Noted."

        if low in {"show memory", "what do you remember"}:
            items = self.b.memory.list_all()
            if not items:
                return "Nothing stored yet."
            return "\n".join(f"- {x.get('text')}" for x in items[-20:])

        find = re.match(
            r"^(?:find|locate)\s+(?:the\s+)?(?:folder|file|directory)?\s*(?:called|named)?\s*(.+)$",
            raw,
            re.I,
        )
        if find:
            name = find.group(1).strip()
            if name.lower() not in {"folder", "file", "directory"}:
                return self.b.pc.find_named(name)

        return None

    def _smalltalk(self, low: str) -> str | None:
        name = self.b.s.get("user_name", "Ty")
        hour = datetime.now().hour
        if low in {
            "hi", "hey", "hello", "yo", "sup", "hiya",
            "hi jarvis", "hey jarvis", "hello jarvis",
            "morning", "good morning", "afternoon", "good afternoon",
            "evening", "good evening",
        }:
            if hour < 5 or hour >= 22:
                return f"Late one, {name}. I'm here."
            if hour < 12:
                return f"Morning {name}. What are we doing?"
            if hour < 18:
                return f"Afternoon {name}. Fire away."
            return f"Evening {name}. What's next?"
        if low in {"how are you", "how're you", "you good", "you alright", "how r u", "whats up", "what's up"}:
            return "I'm good. What do you need?"
        if low in {
            "are you working", "you working", "are you there", "you there",
            "can you hear me", "test", "testing", "hello?", "you up",
            "are you up", "still there",
        }:
            return "Yes. I'm here and working. What do you need?"
        if low in {"thanks", "thank you", "cheers"}:
            return "Anytime."
        if "joke" in low:
            return "A SQL query walks into a bar, walks up to two tables, and asks: “Mind if I join you?”"
        if low in {"do something", "do anything", "prove it", "work", "do your job"}:
            return "Name it. Open an app, find a file, look something up, remember a fact — I'll do that."
            return "Anytime."
        if "what time" in low or "the time" in low or low.endswith("right now") or low in {"time", "date"}:
            return datetime.now().strftime("It's %I:%M %p on %A, %d %B %Y.")
        if low in {"who are you", "what is your name"}:
            return f"I'm {self.b.s.get('assistant_name', 'JARVIS')}."
        if low in {"who am i", "what is my name"}:
            return f"You're {name}."
        return None

    def _open(self, raw: str, low: str) -> str | None:
        m = re.match(r"^(?:open|launch|start|play|go to)\s+(.+)$", low)
        if not m:
            return None
        target = m.group(1).strip().rstrip(".")
        if target.startswith("http"):
            url = raw.split(None, 1)[1] if " " in raw else target
            return self.b.pc.open_url(url)
        if target.startswith("folder "):
            return self.b.pc.open_folder(target[7:].strip())
        for phrase in sorted(APPS, key=len, reverse=True):
            if target == phrase or target.startswith(phrase + " "):
                return self.b.pc.open_app(APPS[phrase])
        for phrase in sorted(SITES, key=len, reverse=True):
            if target == phrase or target.startswith(phrase + " "):
                return self.b.pc.open_url(SITES[phrase])
        if " " not in target and "." in target:
            url = target if target.startswith("http") else "https://" + target
            return self.b.pc.open_url(url)
        return self.b.pc.open_app(target)

    def _wants_organize(self, low: str) -> bool:
        if low in {"order my files", "sort my files", "organise my files", "organize my files", "tidy my files"}:
            return True
        return bool(re.search(r"(?:order|sort|organise|organize|tidy)\s+(?:my\s+)?(?:files|folder|downloads|desktop)", low))

    def _search(self, raw: str, low: str) -> str | None:
        m = re.match(r"^(?:search|look up|lookup|google|research)\s+(.+)$", raw, re.I)
        if not m:
            return None
        q = m.group(1).strip()
        try:
            items = self.b.web.search(q)
        except Exception as e:
            return f"Search didn't come back: {e}"
        if not items:
            return "Nothing useful came back."
        return "Here's what I found:\n" + "\n".join(f"- {i['title']}\n  {i['url']}" for i in items)

    def _code(self, raw: str, low: str) -> str | None:
        m = re.match(r"^(?:write|make|create)\s+(?:a\s+)?(?:python\s+)?(?:script|program|file)\s+(?:that\s+|to\s+)?(.+)$", raw, re.I)
        if not m:
            return None
        job = m.group(1).strip()
        name = "script.py"
        content = (
            f'"""JARVIS workspace script for Ty.\n{job}\n"""\n'
            "def main():\n"
            f"    print({job!r})\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        path = self.b.coding.create_file(name, content)
        return f"Wrote {path.name} in the workspace. Say 'run {path.name}' if you want it executed."
