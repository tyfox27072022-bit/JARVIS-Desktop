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
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "outlook": "outlook",
    "teams": "teams",
    "vscode": "vscode",
    "vs code": "vscode",
    "code": "vscode",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "vlc": "vlc",
    "obs": "obs",
    "photos": "photos",
    "zoom": "zoom",
    "slack": "slack",
    "notion": "notion",
    "xbox": "xbox",
    "clock": "clock",
    "camera": "camera",
    "snipping tool": "snipping tool",
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

    def handle(self, message: str, depth: int = 0) -> str | None:
        raw = (message or "").strip()
        if not raw:
            return None
        low = raw.lower().strip("!.?")

        if depth == 0:
            from jarvis.ai.advanced import split_compound

            parts = split_compound(raw)
            if len(parts) > 1:
                bits = []
                for p in parts[:4]:
                    hit = self.handle(p, depth=1)
                    if hit:
                        bits.append(hit)
                if bits:
                    return "\n\n".join(bits)

        talk = self._smalltalk(low)
        if talk:
            return talk

        if low in {"help", "what can you do", "commands"}:
            return (
                "I'm an AI on this PC. I chain jobs, sort files, research, code, search, control apps.\n"
                "Try: tidy downloads then find duplicates · research rust · "
                "look in downloads for rust then open 1 · new project called shop · "
                "files containing TODO in downloads · 50 usd to gbp · remind me to text mum"
            )

        from jarvis.ai.advanced import handle as advanced_handle
        from jarvis.ai.jobs import handle as jobs_handle
        from jarvis.ai.extras import handle as extras_handle

        fb = self._feedback(raw, low)
        if fb:
            return fb

        adv = advanced_handle(self.b, raw)
        if adv:
            return adv

        extra = extras_handle(self.b, raw)
        if extra:
            return extra

        job = jobs_handle(self.b, raw)
        if job:
            return job

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
            try:
                from jarvis.config import save

                save(self.b.s)
            except Exception:
                pass
            return f"Alright {name}."

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
                return "I'll keep that — " + "; ".join(kept).rstrip(".") + "."

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

        used = self._use_pc(raw, low)
        if used:
            return used

        if low in {"wifi", "open wifi"}:
            return self.b.pc.open_wifi()

        if "on my screen" in low or low in {"look at my screen", "what's on screen", "whats on screen"}:
            return self.b.pc.screen_report()
        if low in {"list windows", "what windows are open"}:
            return self.b.pc.list_windows()

        if low in {"system status", "pc status", "system"}:
            s = self.b.pc.system_summary()
            return f"CPU {s['cpu_percent']}% · RAM {s['ram_percent']}% · Disk {s.get('disk_percent')}%"

        if low in {"undo sort", "undo organise", "undo organize", "put files back"}:
            from jarvis.pc.organize import undo_last

            return undo_last(audit=self.b.audit)

        if re.search(r"\b(duplicates?|duplicate files)\b", low):
            from jarvis.pc.organize import find_duplicates

            folder = Path.home() / "Downloads"
            if "desktop" in low:
                folder = Path.home() / "Desktop"
            elif "document" in low:
                folder = Path.home() / "Documents"
            return find_duplicates(folder)

        if re.search(r"\b(big files|large files|biggest files|what's taking space)\b", low):
            from jarvis.pc.organize import find_large

            folder = Path.home() / "Downloads"
            if "desktop" in low:
                folder = Path.home() / "Desktop"
            return find_large(folder)

        if self._wants_organize(low):
            from jarvis.pc.organize import organize_folder

            home = Path.home()
            folder = home / "Downloads"
            if "desktop" in low:
                folder = home / "Desktop"
            elif "document" in low:
                folder = home / "Documents"
            by = "date" if "date" in low or "by date" in low else "type"
            return organize_folder(folder, audit=self.b.audit, by=by)

        coded = self._code(raw, low)
        if coded:
            return coded

        run = re.match(r"^run\s+(.+)$", low)
        if run:
            target = run.group(1).strip()
            try:
                out = self.b.coding.run_file(target)
                return f"Ran {target}:\n{out}"
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
        if low in {"hi", "hey", "hello", "yo", "sup", "hiya", "hi jarvis", "hey jarvis", "hello jarvis"}:
            if hour < 5 or hour >= 22:
                return f"Yeah I'm here, {name}."
            if hour < 12:
                return f"Morning. What's going on?"
            if hour < 18:
                return f"Hey {name}."
            return f"Evening. What do you need?"
        if low in {"how are you", "how're you", "you good", "you alright", "how r u", "whats up", "what's up"}:
            return "Yeah, all good. You?"
        if low in {
            "are you working", "you working", "are you there", "you there",
            "can you hear me", "test", "testing", "you up", "are you up", "still there",
        }:
            return "Yep. Still here."
        if low in {"thanks", "thank you", "cheers"}:
            return "No worries."
        if "joke" in low:
            return "A SQL query walks into a bar, walks up to two tables, and asks if it can join them."
        if low in {"do something", "do anything", "prove it", "work", "do your job"}:
            return "Tell me what. I'll open it, find it, write it, or look it up."
        timed = self._time(low)
        if timed:
            return timed
        if low in {"who are you", "what is your name", "what are you", "are you an ai", "are you ai"}:
            return (
                f"I'm {self.b.s.get('assistant_name', 'JARVIS')} — an AI Ty made. "
                "I learn from what you tell me, how you talk, files I see, and when you correct me. "
                "That sticks even after you close the app."
            )
        if low in {
            "can you learn", "do you learn", "how do you learn",
            "can you remember", "do you remember",
        }:
            return (
                "Yeah. Tell me something and I'll keep it. Talk normally and I'll pick up how you sound. "
                "Index a folder and I learn those files. Say 'too long' or 'don't do that' and I adjust. "
                "Ask 'what do you know about me' anytime."
            )
        if low in {"who am i", "what is my name"}:
            return f"You're {name}."
        return None

    def _feedback(self, raw: str, low: str) -> str | None:
        mem = self.b.memory
        if low in {
            "good", "nice", "perfect", "that's better", "thats better",
            "love that", "good job", "well done", "that's good", "thats good",
            "yes that's it", "better", "nailed it",
        }:
            mem.add_instruction("He liked the last reply. Keep that tone and length.")
            return "Glad that landed."
        if any(p in low for p in ("too long", "keep it short", "shorter", "too much")):
            mem.style.setdefault("traits", {})["detail_level"] = "short"
            mem.save_style()
            mem.add_instruction("Keep replies short.")
            return "Alright — I'll keep it short."
        if any(p in low for p in ("too formal", "more casual", "sound more human", "talk normal", "less robotic")):
            mem.style.setdefault("traits", {})["tone"] = "casual"
            mem.style.setdefault("traits", {})["contractions"] = True
            mem.save_style()
            mem.add_instruction("Talk casual, like a mate. Not a helpdesk.")
            return "I'll talk more like you."
        if any(p in low for p in ("be funnier", "more jokes", "lighten up")):
            mem.add_instruction("Be a bit funnier.")
            return "I'll throw a bit more in."
        if any(p in low for p in ("be serious", "less jokes")):
            mem.add_instruction("Stay more serious.")
            return "I'll keep it straight."
        if low.startswith(("don't ", "dont ", "never ", "stop ")):
            mem.add_instruction(raw.strip())
            return "Alright. I won't."
        if low.startswith("always "):
            mem.add_instruction(raw.strip())
            return "I'll do that from now on."
        return None

    def _use_pc(self, raw: str, low: str) -> str | None:
        pc = self.b.pc
        m = re.match(r"^(?:close|quit|kill|exit)\s+(.+)$", low)
        if m:
            return pc.close_app(m.group(1).strip())
        if low in {"volume up", "turn it up", "louder"}:
            return pc.volume("up")
        if low in {"volume down", "quieter", "turn it down"}:
            return pc.volume("down")
        if low in {"mute", "unmute", "mute volume"}:
            return pc.volume("mute")
        if low in {"lock", "lock pc", "lock my pc", "lock the computer", "lock windows"}:
            return pc.lock()
        if low in {"sleep", "sleep pc", "put pc to sleep", "sleep the computer"}:
            return pc.sleep_pc()
        if low in {"shut down now", "shutdown now", "turn off now"}:
            return pc.shutdown(False)
        if low in {"restart now", "reboot now"}:
            return pc.shutdown(True)
        if low in {"shut down", "shutdown", "shut down my pc", "turn off my pc", "turn off the computer"}:
            return "If you mean it, say: shut down now"
        if low in {"restart", "restart my pc", "reboot"}:
            return "If you mean it, say: restart now"
        if low in {"show desktop", "go to desktop", "minimise all", "minimize all"}:
            return pc.show_desktop() or "Desktop."
        if low in {"switch window", "alt tab", "next window"}:
            return pc.switch_window() or "Switched window."
        if low in {"play", "pause", "play pause", "resume music"}:
            return pc.media("play")
        if low in {"next song", "next track", "skip"}:
            return pc.media("next")
        if low in {"previous song", "previous track", "last song"}:
            return pc.media("prev")
        if low in {"copy", "copy that"}:
            return pc.copy() or "Copied."
        if low in {"paste", "paste that"}:
            return pc.paste() or "Pasted."
        if low in {"select all"}:
            return pc.select_all() or "Selected all."
        if low in {"undo"}:
            return pc.undo() or "Undo."
        if low in {"screenshot", "take a screenshot", "capture screen"}:
            return pc.screenshot_desktop()
        if low in {"scroll down", "page down"}:
            return pc.scroll("down")
        if low in {"scroll up", "page up"}:
            return pc.scroll("up")
        if low in {"click", "left click"}:
            return pc.click()
        if low in {"double click"}:
            if py := getattr(pc, "click", None):
                pc.click()
                return pc.click()
        m = re.match(r"^(?:type|write this)\s+(.+)$", raw, re.I)
        if m and not re.search(r"\b(email|essay|script|program|code)\b", low):
            return pc.type_text(m.group(1).strip())
        m = re.match(r"^press\s+(.+)$", low)
        if m:
            return pc.press(m.group(1).strip())
        m = re.match(r"^click at\s+(\d+)\s*[x,]\s*(\d+)$", low)
        if m:
            return pc.click(int(m.group(1)), int(m.group(2)))
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
        if low in {"find it", "find that", "find them", "open it", "open that", "that one"}:
            if low.startswith("open") or low == "that one":
                return self.b.pc.open_hit(1)
            return self.b.pc.find_named(self.b.pc.last_needle or "it", self.b.pc.last_where)

        m = re.match(r"^open\s+(\d+)$", low)
        if m:
            return self.b.pc.open_hit(int(m.group(1)))

        loc = re.search(
            r"(?:look|find|search|show).{0,30}?\bin\s+(downloads?|desktop|documents?|pictures?|videos?|music|onedrive)\s+(?:for\s+)?(.+)$",
            raw,
            re.I,
        )
        if loc:
            where, what = loc.group(1), loc.group(2).strip()
            return self.b.pc.find_named(what, where)

        loc2 = re.search(
            r"(?:look|find|search|show)\s+(.+?)\s+in\s+(downloads?|desktop|documents?|pictures?|videos?|music)\b",
            raw,
            re.I,
        )
        if loc2:
            return self.b.pc.find_named(loc2.group(1), loc2.group(2))

        if low in {"list desktop", "list my desktop"} or ("on my desktop" in low):
            return self.b.pc.list_folder(str(Path.home() / "Desktop"))
        if low in {"list downloads", "what's in downloads", "whats in downloads"}:
            return self.b.pc.list_folder(str(Path.home() / "Downloads"))
        if low in {"list documents", "what's in documents", "whats in documents"}:
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
            if name.lower() not in {"folder", "file", "directory", "called", "named", "it", "that"}:
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
        if low in {
            "order my files", "sort my files", "organise my files", "organize my files",
            "tidy my files", "tidy downloads", "tidy my downloads", "organise downloads",
            "organize downloads", "clean downloads", "tidy desktop", "organise desktop",
            "organize desktop", "clean desktop", "sort downloads", "sort desktop",
        }:
            return True
        return bool(
            re.search(
                r"(?:order|sort|organise|organize|tidy|clean)\s+(?:my\s+)?(?:files|folder|downloads|desktop|documents)",
                low,
            )
        )

    def _search(self, raw: str, low: str) -> str | None:
        if low in {
            "search the web", "search web", "search the we", "search internet",
            "search online", "web search", "look online", "look it up", "google it",
            "google that", "search that",
        }:
            hist = getattr(self.b, "history", None) or []
            prev = ""
            for turn in reversed(hist):
                if turn.get("role") == "user" and turn.get("content"):
                    prev = turn["content"]
                    break
            if prev:
                try:
                    return self.b.web.answer(prev, open_browser=True)
                except Exception as e:
                    return f"Search didn't come back: {e}"
            return "What should I search for?"
        m = re.match(
            r"^(?:search(?:\s+the)?(?:\s+web|\s+we|\s+internet|\s+online)?(?:\s+for)?|"
            r"look\s*up|lookup|look online for|google|research|browse)\s+(.+)$",
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
            return self.b.web.answer(q, open_browser=True)
        except Exception as e:
            return f"Search didn't come back: {e}"

    def _code(self, raw: str, low: str) -> str | None:
        sent = self._send(raw, low)
        if sent:
            return sent
        wants = bool(
            re.search(r"\b(write|code|generate)\b", low)
            and re.search(
                r"\b(script|program|code|function|class|page|app|html|css|"
                r"python|javascript|typescript|java|rust|golang|\bgo\b|c\+\+|csharp|c#|php|ruby|swift|kotlin|sql|lua)\b",
                low,
            )
        )
        if not wants:
            m = re.match(
                r"^(?:write|make|create)\s+(?:a\s+|an\s+|me\s+)?(?:python\s+)?(?:script|program|file)\s+(?:that\s+|to\s+)?(.+)$",
                raw,
                re.I,
            )
            if not m:
                return None
            job = m.group(1).strip()
        else:
            job = raw
        try:
            engine = getattr(self.b, "engine", None)
            path = self.b.coding.write_program(job, language_hint=raw, engine=engine)
        except Exception as e:
            return f"Couldn't write that: {e}"
        preview = ""
        try:
            preview = path.read_text(encoding="utf-8", errors="replace")[:500]
        except Exception:
            pass
        return (
            f"Wrote {path.name} in the workspace.\n"
            f"Say 'run {path.name}' to execute it, or 'send {path.name}' to drop it on your Desktop.\n\n"
            f"{preview}"
        )

    def _send(self, raw: str, low: str) -> str | None:
        if not re.search(r"\b(send|share|email me|give me the file|drop it on)\b", low):
            return None
        if "search" in low or "web" in low:
            return None
        m = re.search(r"([\w.\-]+\.[a-zA-Z0-9]{1,8})\b", raw)
        name = m.group(1) if m else None
        where = "downloads" if "download" in low else "desktop"
        try:
            msg = self.b.coding.send_file(name, where=where)
        except Exception as e:
            return f"Couldn't send a file: {e}"
        bot = getattr(self.b, "discord_bot", None)
        extra = ""
        if bot and hasattr(bot, "queue_file"):
            try:
                path = self.b.coding.resolve(name)
                extra = " " + (bot.queue_file(path) or "")
            except Exception:
                extra = ""
        return (msg + extra).strip()
