"""
JARVIS AI Core — local-first, crash-safe chat path.
"""
from __future__ import annotations

import os
import re
import traceback

from jarvis.ai.agent import AgentLoop
from jarvis.ai.hardware import format_report, probe
from jarvis.ai.intent import IntentRouter
from jarvis.ai.local_engine import LocalEngine
from jarvis.ai.model_manager import ModelManager
from jarvis.ai.tools import ToolRouter, parse_tools, strip_tool_tags

GREETINGS = {
    "hi",
    "hey",
    "hello",
    "yo",
    "sup",
    "hiya",
    "hi jarvis",
    "hey jarvis",
    "hello jarvis",
    "morning",
    "afternoon",
    "evening",
    "good morning",
    "good afternoon",
    "good evening",
}


class Brain:
    def __init__(self, settings, memory, vault, web, pc, coding, improve, audit=None):
        self.s = settings
        self.memory = memory
        self.vault = vault
        self.web = web
        self.pc = pc
        self.coding = coding
        self.improve = improve
        self.audit = audit
        self.history: list[dict] = []
        self.engine = LocalEngine()
        self.models = ModelManager()
        self.tools = ToolRouter(
            {
                "memory": memory,
                "vault": vault,
                "web": web,
                "pc": pc,
                "coding": coding,
                "settings": settings,
            }
        )
        self._autoload_attempted = False
        self.intents = IntentRouter(self)

    @property
    def mode_label(self) -> str:
        try:
            if self.engine.ready:
                name = self.engine.model_path.name if self.engine.model_path else "local"
                return f"Local AI ({name})"
            provider = ((self.s.get("ai") or {}).get("provider") or "xai").lower()
            key = ((self.s.get("ai") or {}).get("api_key") or "").strip()
            if key and provider in ("xai", "grok", "openai", "auto", ""):
                mid = (self.s.get("ai") or {}).get("model") or "jarvis"
                return f"Grok ({mid})"
            if provider in ("openai", "xai", "ollama"):
                if provider == "ollama":
                    return "Ollama"
            found = self.models.list_installed()
            if found:
                return f"Model on disk ({found[0]}) — loading"
            return "Independent"
        except Exception:
            return "JARVIS"

    def ensure_local_model(self) -> str:
        if self.engine.ready and self.engine.model_path:
            return f"Already loaded: {self.engine.model_path.name}"
        GROK_IDS = {
            "fast", "jarvis", "sharp", "grok", "grok-4.3", "grok-4.5", "grok-4.6",
        }
        from jarvis.ai.model_catalog import DEFAULT_ID

        ai = self.s.get("ai") or {}
        model_id = ai.get("local_model_id") or DEFAULT_ID
        if (model_id or "").lower() in GROK_IDS:
            model_id = DEFAULT_ID
        custom = (ai.get("local_model_path") or "").strip()
        path = self.models.resolve(model_id, custom or None)
        if not path:
            installed = self.models.list_installed()
            return (
                "No local model file found yet — first-run install will fetch one."
            )
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            try:
                from jarvis.ai.cli_engine import CliEngine

                CliEngine().ensure_binary()
            except Exception as e:
                if self.audit:
                    self.audit.log(f"CLI binary setup: {e}")
        n_ctx = int(ai.get("n_ctx") or 2048)
        temp = float(ai.get("temperature") or 0.6)
        max_tok = int(ai.get("max_tokens") or 256)
        threads = ai.get("n_threads")
        gpu_layers = int(ai.get("n_gpu_layers") or 0)
        msg = self.engine.load(
            path,
            n_ctx=min(n_ctx, 2048),
            n_threads=int(threads) if threads else None,
            temperature=temp,
            max_tokens=max_tok,
            n_gpu_layers=gpu_layers,
        )
        if self.audit:
            self.audit.log(msg)
        return msg

    def bootstrap(self, progress_cb=None) -> str:
        """Install JARVIS's own free local model and load it. No keys."""
        if self.engine.ready:
            return f"Already loaded: {self.engine.model_path.name}"
        if progress_cb:
            progress_cb("Looking for a local brain…")
        msg = self.ensure_local_model()
        if self.engine.ready:
            return msg
        try:
            from jarvis.ai.cli_engine import CliEngine

            if progress_cb:
                progress_cb("Installing local engine…")
            try:
                CliEngine().ensure_binary(progress_cb=progress_cb)
            except Exception as e:
                if self.audit:
                    self.audit.log(f"engine bin: {e}")
            mid, path = self.models.download_any(progress_cb=progress_cb)
            self.s.setdefault("ai", {})["local_model_id"] = mid
            load = self.ensure_local_model()
            return f"Installed {path.name}. {load}"
        except Exception as e:
            if self.audit:
                self.audit.log(f"bootstrap: {e}")
            return (
                "Couldn't fetch the local brain yet — I'll still open apps, find files, "
                f"and look things up. ({e})"
            )

    def download_model(self, model_id: str | None = None, progress_cb=None) -> str:
        ai = self.s.get("ai") or {}
        mid = model_id or ai.get("local_model_id") or probe()["recommended_model_id"]
        grok_ids = {"fast", "jarvis", "sharp", "grok", "grok-4.3", "grok-4.5", "grok-4.6"}
        if (mid or "").lower() in grok_ids:
            from jarvis.ai.model_catalog import DEFAULT_ID

            mid = DEFAULT_ID
        path = self.models.download(mid, progress_cb=progress_cb)
        ai["local_model_id"] = mid
        self.s["ai"] = ai
        return f"Downloaded {path.name}. Loading…"

    def system_prompt(self) -> str:
        name = self.s.get("assistant_name", "JARVIS")
        user = self.s.get("user_name", "Ty")
        personality = self.s.get("personality", "helpful")
        try:
            mem = self.memory.context()
        except Exception:
            mem = ""
        index = ""
        try:
            from jarvis.paths import DATA

            ip = DATA / "file_index.txt"
            if ip.exists():
                index = ip.read_text(encoding="utf-8", errors="replace")[:4000]
        except Exception:
            index = ""
        return (
            f"You are {name}, personal assistant for {user}. "
            f"{personality} "
            "Talk like a person. Short, warm, slightly witty. Contractions. "
            "Do not invent PC actions — use tools or the known index.\n"
            f"Memory:\n{mem or '(none)'}\n"
            f"Indexed PC files:\n{index or '(none yet — ask them to Index a folder in Settings)'}"
        )

    def chat(self, message: str) -> str:
        try:
            return self._chat_inner(message)
        except Exception as e:
            if self.audit:
                self.audit.log(f"chat crash: {e}")
            return (
                "Caught that — had a wobble on my side. "
                f"({e}) Try saying that again."
            )

    def _chat_inner(self, message: str) -> str:
        message = (message or "").strip()
        if not message:
            return "Sorry Ty — I missed that. Say it once more?"

        try:
            hit = self.intents.handle(message)
            if hit is not None:
                self._push(message, hit)
                return hit
        except Exception as e:
            if self.audit:
                self.audit.log(f"intent: {e}")

        local = self._local_commands(message)
        if local is not None:
            self._push(message, local)
            return local

        low = message.lower().strip().strip("!.?")
        if low in GREETINGS:
            reply = self._greeting_reply()
            self._push(message, reply)
            return reply
        if low in ("how are you", "how're you", "you good", "you alright", "how r u"):
            reply = "I'm good, Ty. What do you need?"
            self._push(message, reply)
            return reply

        env_key = (os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or "").strip()
        if env_key:
            self.s.setdefault("ai", {})
            self.s["ai"]["api_key"] = self.s["ai"].get("api_key") or env_key
            self.s["ai"].setdefault("api_base", "https://api.x.ai/v1")
            self.s["ai"].setdefault("model", "grok-4.5")

        provider = ((self.s.get("ai") or {}).get("provider") or "auto").lower()
        key = ((self.s.get("ai") or {}).get("api_key") or "").strip()

        if key and provider in ("xai", "grok", "openai", "auto", ""):
            try:
                from jarvis.ai.cloud_optional import cloud_chat

                if not (self.s.get("ai") or {}).get("api_base"):
                    self.s.setdefault("ai", {})["api_base"] = "https://api.x.ai/v1"
                reply = cloud_chat(self.s, self.system_prompt(), self.history, message)
                reply = (reply or "").strip() or "I'm here. Say that another way?"
                self._push(message, reply)
                return reply
            except Exception as e:
                if self.audit:
                    self.audit.log(f"Grok chat: {e}")

        try:
            from jarvis.ai.free_brain import ollama_up
            from jarvis.ai.cloud_optional import cloud_chat

            if ollama_up() and provider in ("ollama", "auto", "local", ""):
                self.s.setdefault("ai", {})
                self.s["ai"]["provider"] = self.s["ai"].get("provider") or "ollama"
                reply = cloud_chat(self.s, self.system_prompt(), self.history, message)
                if reply:
                    self._push(message, reply)
                    return reply
        except Exception as e:
            if self.audit:
                self.audit.log(f"Ollama: {e}")

        if not self.engine.ready and not self._autoload_attempted:
            self._autoload_attempted = True
            try:
                self.ensure_local_model()
            except Exception as e:
                if self.audit:
                    self.audit.log(f"Autoload failed: {e}")

        if self.engine.ready:
            try:
                looks = False
                try:
                    looks = self._looks_like_task(message)
                except Exception:
                    looks = False
                if looks:
                    agent = AgentLoop(
                        self.engine,
                        self.tools,
                        self.system_prompt,
                        max_steps=int((self.s.get("ai") or {}).get("max_agent_steps") or 4),
                        audit=self.audit,
                    )
                    reply = agent.run(message, self.history)
                else:
                    reply = self.engine.chat(self.system_prompt(), self.history, message)
                    reply = self._run_tools_in_reply(reply or "")
                reply = (reply or "").strip() or "I'm here. Say that another way?"
                if self._junk_reply(reply):
                    reply = self._sensible_fallback(message)
                self._push(message, reply)
                return reply
            except Exception as e:
                fallback = (
                    f"I'm here, Ty. The local model hiccuped ({e}). "
                    "Commands still work: help, search …, find folder …"
                )
                self._push(message, fallback)
                return fallback

        try:
            from jarvis.ai.free_brain import answer

            hit = answer(message, self.web)
            if hit:
                self._push(message, hit)
                return hit
        except Exception as e:
            if self.audit:
                self.audit.log(f"free brain: {e}")

        reply = (
            "I'm here and I can do it — open apps, find files, look things up, remember stuff. "
            f"On “{message[:80]}”: say it as an action (open …, find …, search …) "
            "or ask a question and I'll look it up."
        )
        self._push(message, reply)
        return reply

    def _greeting_reply(self) -> str:
        name = self.s.get("user_name", "Ty")
        return f"Hey {name}. What's on the cards?"

    def _junk_reply(self, text: str) -> bool:
        low = (text or "").lower()
        bad = (
            "to jarvis",
            "welcome to the team",
            "ty's calm",
            "i greet you",
            "<|system|>",
            "<|user|>",
            "british assistant, i",
        )
        if any(b in low for b in bad):
            return True
        if text.lower().startswith("to jarvis"):
            return True
        return False

    def _sensible_fallback(self, message: str) -> str:
        low = message.lower()
        if "file" in low or "folder" in low or "order" in low or "organise" in low or "organize" in low:
            return "Which folder should I tidy — Desktop, Downloads, or something named?"
        if "spotify" in low:
            return self.pc.open_app("spotify")
        if any(w in low for w in ("time", "am", "pm", "clock")):
            from datetime import datetime

            return datetime.now().strftime("It's %I:%M %p on %A.")
        return "Got you. Tell me the next step in plain words and I'll do that."

    def _looks_like_task(self, message: str) -> bool:
        low = (message or "").lower()
        keys = (
            "open ",
            "find ",
            "search ",
            "list ",
            "click ",
            "type ",
            "write ",
            "create ",
            "screenshot",
            "vault",
            "and then",
            "folder",
            "notepad",
        )
        hits = sum(1 for k in keys if k in low)
        return hits >= 1 and len(message.split()) >= 3

    def _run_tools_in_reply(self, reply: str) -> str:
        try:
            calls = parse_tools(reply)
            if not calls:
                return reply
            results = []
            for name, args in calls:
                results.append(f"{name}: {self.tools.execute(name, args)}")
            clean = strip_tool_tags(reply)
            block = "\n".join(results)
            return f"{clean}\n\n{block}".strip() if clean else block
        except Exception as e:
            return reply or str(e)

    def _push(self, user: str, assistant: str):
        try:
            self.history.append({"role": "user", "content": user})
            self.history.append({"role": "assistant", "content": assistant})
            self.history = self.history[-16:]
        except Exception:
            self.history = []

    def _local_commands(self, message: str) -> str | None:
        low = message.lower().strip()
        m = message.strip()

        if low in ("hardware", "system info", "recommend model"):
            return format_report()

        if low.startswith("load model"):
            try:
                return self.ensure_local_model()
            except Exception as e:
                return f"Load failed: {e}"

        if low.startswith("download model"):
            parts = m.split(None, 2)
            mid = parts[2].strip() if len(parts) >= 3 else None
            try:
                msg = self.download_model(mid)
                load = self.ensure_local_model()
                return f"{msg}\n{load}"
            except Exception as e:
                return f"Download failed: {e}"

        if low.startswith("remember that ") or low.startswith("remember "):
            text = m.split(" ", 1)[1] if " " in m else ""
            text = re.sub(r"^(that\s+)", "", text, flags=re.I).strip()
            if not text:
                return "Happy to remember it — what should I keep?"
            if any(w in text.lower() for w in ("prefer", "always", "never", "don't", "do not")):
                self.memory.add_instruction(text)
                if "short" in text.lower():
                    self.s.setdefault("support", {})["prefer_short_answers"] = True
                return "Got it. I'll keep that in mind."
            self.memory.remember(text, "facts")
            return "Noted. I've put that in memory."

        if low in ("show memory", "list memory", "what do you remember", "view memory"):
            items = self.memory.list_all()
            if not items:
                return "Blank slate at the moment. Tell me what to remember."
            return "Memory:\n" + "\n".join(
                f"[{x.get('id')}] ({x.get('category')}) {x.get('text')}" for x in items[-40:]
            )

        if low.startswith("delete memory "):
            mid = m.split(" ", 2)[-1].strip()
            return f"Deleted {mid}." if self.memory.delete(mid) else f"No id {mid}."

        if low in ("clear memory", "clear all memory"):
            self.memory.clear()
            return "Done. Memory's cleared."

        if low.startswith("learn my writing style"):
            samples = [h["content"] for h in self.history if h.get("role") == "user"][-15:]
            if ":" in m:
                extra = m.split(":", 1)[1].strip()
                if extra:
                    samples.append(extra)
            return self.memory.learn_style_from_messages(samples)

        if "what time" in low or low.endswith("right now") or low in ("time", "what's the time", "whats the time"):
            from datetime import datetime

            return datetime.now().strftime("It's %I:%M %p on %A.")

        if low in ("help", "what can you do", "commands"):
            return (
                f"I'm {self.s.get('assistant_name', 'JARVIS')} · {self.mode_label}.\n"
                "Search the web, write code in the workspace, open apps, find folders, "
                "look at the screen, remember things. Just tell me what you want."
            )

        if "what is my name" in low or "who am i" in low:
            return f"You're {self.s.get('user_name', 'Ty')} — I do know that one."
        if "who are you" in low or "what is your name" in low:
            return f"I'm {self.s.get('assistant_name', 'JARVIS')}. Yours."

        if low in ("system status", "pc status", "system"):
            s = self.pc.system_summary()
            return f"CPU {s['cpu_percent']}% · RAM {s['ram_percent']}% · Disk {s.get('disk_percent')}%"

        if low in (
            "what's on my screen",
            "what is on my screen",
            "whats on my screen",
            "look at my screen",
        ):
            return self.pc.screen_report()
        if low in ("list windows", "what windows are open"):
            return self.pc.list_windows()

        if low in ("wifi", "open wifi", "connect to wifi", "connect to the wifi"):
            return self.pc.open_wifi()

        if low in ("list vault", "list scripts"):
            items = self.vault.index()
            return "\n".join(f"- [{x['game']}] {x['name']}" for x in items[:60]) or "Vault is empty."

        if low.startswith("search vault "):
            hits = self.vault.search(m[13:].strip())
            return (
                "\n".join(f"- [{h['game']}] {h['name']}" for h in hits[:30]) or "No vault matches."
            )

        if low.startswith("search "):
            q = m[7:].strip()
            try:
                items = self.web.search(q)
            except Exception as e:
                return f"Search didn't come back: {e}"
            return "\n".join(f"- {i['title']}\n  {i['url']}" for i in items) or "No results."

        if low == "list workspace":
            files = self.coding.list_files()
            return "Workspace:\n" + ("\n".join(files) if files else "(empty)")

        if low.startswith("improve yourself"):
            idea = m.split(":", 1)[1].strip() if ":" in m else "General improvements"
            p = self.improve.propose(idea[:40], idea)
            return f"Sandbox proposal: {p.name}\nStatus: WAITING FOR TY"

        app = re.match(
            r"^(?:open|launch|start)\s+(notepad|calculator|calc|paint|explorer|discord|chrome|edge|spotify|steam)\s*$",
            low,
        )
        if app:
            return self.pc.open_app(app.group(1))

        url = re.match(r"^(?:open|launch)\s+(?:url\s+)?(https?://\S+)\s*$", m, re.I)
        if url:
            return self.pc.open_url(url.group(1))

        folder = re.match(r"^(?:open|launch)\s+folder\s+(.+)$", m, re.I)
        if folder:
            return self.pc.open_folder(folder.group(1).strip())

        find = re.match(
            r"^(?:find|search|locate)\s+(?:the\s+)?(?:folder|file|directory)\s+(?:called\s+|named\s+)?(.+)$",
            m,
            re.I,
        )
        if find:
            return self.pc.find_named(find.group(1).strip())

        see = re.search(
            r"(?:see|find|open|show)\s+(?:the\s+)?(?:file|folder)?\s*(?:called|named)\s+(.+)$",
            m,
            re.I,
        )
        if see:
            return self.pc.find_named(see.group(1).strip().strip("?.!"))

        listf = re.match(r"^(?:list|show)\s+(?:folder\s+|directory\s+)?(.+)$", m, re.I)
        if listf and listf.group(1).strip().lower() not in (
            "vault",
            "scripts",
            "memory",
            "workspace",
        ):
            return self.pc.list_folder(listf.group(1).strip())

        return None
