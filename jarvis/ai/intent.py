"""Deterministic intent layer so JARVIS acts even when the small model is weak."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


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
                "I can open apps, find and open files on this PC, list Desktop/Downloads/Documents, "
                "search the web, remember things, tell the time anywhere, and chat. "
                "Try: search the web for … · find file card v · list my desktop · open spotify"
            )

        if low in {
            "how do i talk", "what's my style", "whats my style",
            "how do i sound", "learn how i talk",
        }:
            return self.b.memory.style_report()
        if low in {
            "what do you know about me", "what have you learned",
            "what do you remember about me", "what do you know",
        }:
            return self.b.memory.about_user()

        named = re.match(r"^(?:my name is|call me)\s+([a-zA-Z][\w\-']{1,30})$", raw, re.I)
        if named:
            name = named.group(1).strip().title()
            self.b.s["user_name"] = name
            self.b.memory.remember(f"Name is {name}", "facts")
            return f"Alright, {name}. I'll remember."

        from jarvis.ai.learn import extract, skip_message

        if not skip_message(raw):
            hits = extract(raw)
            explicit = [h for h in hits if h[0] != "notes"]
            if explicit:
                kept = []
                for cat, text in explicit:
                    if not self.b.memory.already_has(text):
                        self.b.memory.remember(text, cat)
                    kept.append(text)
                return "Got it — I'll remember that. " + "; ".join(kept)

        if not any(w in low for w in ("web", "google", "internet", "online", "search the we")):
            files = self._files(raw, low)
            if files:
                return files

        looked = self._search(raw, low)
        if looked:
            return looked

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
        timed = self._time(low)
        if timed:
            return timed
        if low in {"who are you", "what is your name"}:
            return f"I'm {self.b.s.get('assistant_name', 'JARVIS')}."
        if low in {"who am i", "what is my name"}:
            return f"You're {name}."
        return None

    def _time(self, low: str) -> str | None:
        if not (
            "time" in low or low in {"date", "what's the date", "whats the date"}
        ):
            return None
        zones = {
            "new york": "America/New_York",
            "nyc": "America/New_York",
            "usa": "America/New_York",
            "us": "America/New_York",
            "america": "America/New_York",
            "eastern": "America/New_York",
            "la": "America/Los_Angeles",
            "los angeles": "America/Los_Angeles",
            "pacific": "America/Los_Angeles",
            "chicago": "America/Chicago",
            "central": "America/Chicago",
            "denver": "America/Denver",
            "london": "Europe/London",
            "uk": "Europe/London",
            "tokyo": "Asia/Tokyo",
        }
        for name, zid in zones.items():
            if re.search(rf"\b{re.escape(name)}\b", low):
                now = datetime.now(ZoneInfo(zid))
                return now.strftime(f"It's %I:%M %p on %A, %d %B %Y in {name.title()} ({zid}).")
        if "what time" in low or "the time" in low or low.endswith("right now") or low in {"time", "date"}:
            return datetime.now().strftime("It's %I:%M %p on %A, %d %B %Y.")
        return None

    def _files(self, raw: str, low: str) -> str | None:
        if low in {"clear chat", "clear conversation", "wipe chat"}:
            return "__CLEAR_CHAT__"
        if low in {
            "scan my files", "index my files", "see my files", "see all my files",
            "look at my files", "show my files", "list my files", "search my files",
            "what files do i have", "see the files on my pc", "files on my pc",
        }:
            try:
                self.b.pc.index_home()
            except Exception:
                pass
            return self.b.pc.overview()
        if "desktop" in low and any(w in low for w in ("list", "show", "what's", "whats", "on my")):
            return self.b.pc.list_folder(str(Path.home() / "Desktop"))
        if "download" in low and any(w in low for w in ("list", "show", "what's", "whats", "in")):
            return self.b.pc.list_folder(str(Path.home() / "Downloads"))
        if "document" in low and any(w in low for w in ("list", "show", "what's", "whats", "in")):
            return self.b.pc.list_folder(str(Path.home() / "Documents"))

        m = re.search(r"(?:called|named|for one called)\s+(.+)$", raw, re.I)
        if m and any(
            w in low for w in ("file", "folder", "tile", "title", "look", "find", "search", "open", "get")
        ):
            name = m.group(1).strip().strip("\"'/?.!")
            if name and name.lower() not in {"file", "folder", "it"}:
                return self.b.pc.find_named(name)

        m = re.match(
            r"^(?:find|locate)\s+(?:the\s+)?(?:folder|file|directory)?\s*(?:called|named)?\s*(.+)$",
            raw,
            re.I,
        )
        if m:
            name = m.group(1).strip().strip("\"'/?.!")
            if name.lower() not in {"folder", "file", "directory", "called", "named"}:
                return self.b.pc.find_named(name)
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
        if low in {
            "search the web", "search web", "search the we", "search internet",
            "search online", "web search",
        }:
            return "What should I search for?"
        m = re.match(
            r"^(?:search(?:\s+the)?(?:\s+web|\s+we|\s+internet|\s+online)?(?:\s+for)?|"
            r"look\s*up|lookup|google|research|browse)\s+(.+)$",
            raw,
            re.I,
        )
        if not m:
            m = re.search(
                r"search(?:\s+the)?(?:\s+web|\s+we|\s+internet)?(?:\s+for)\s+(.+)$",
                raw,
                re.I,
            )
        if not m:
            return None
        q = m.group(1).strip().strip("\"'")
        if not q or q.lower() in {"the web", "web", "the we", "internet", "online"}:
            return "What should I search for?"
        if q.lower().startswith("my file"):
            return None
        try:
            return self.b.web.answer(q)
        except Exception as e:
            return f"Search didn't come back: {e}"

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
