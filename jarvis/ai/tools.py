"""
Permissioned tool layer. Model requests tools; JARVIS executes with checks.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable


TOOL_PATTERN = re.compile(
    r"\[TOOL:([a-zA-Z0-9_]+)((?:\|[^=\]]+=[^|\]]*)*)\]",
    re.IGNORECASE,
)


def parse_tools(text: str) -> list[tuple[str, dict]]:
    found = []
    for m in TOOL_PATTERN.finditer(text or ""):
        name = m.group(1).strip().lower()
        args = {}
        raw = m.group(2) or ""
        for part in raw.split("|"):
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            args[k.strip().lower()] = v.strip()
        found.append((name, args))
    return found


def strip_tool_tags(text: str) -> str:
    return TOOL_PATTERN.sub("", text or "").strip()


class ToolRouter:
    def __init__(self, brain_refs: dict, pending_confirm: dict | None = None):
        self.r = brain_refs
        self.pending_confirm = pending_confirm if pending_confirm is not None else {}

    def available_descriptions(self) -> str:
        return (
            "Tools (use only when needed):\n"
            "[TOOL:remember|text=...]\n"
            "[TOOL:show_memory]\n"
            "[TOOL:system_status]\n"
            "[TOOL:find_folder|name=...]\n"
            "[TOOL:list_folder|path=...]\n"
            "[TOOL:open_app|name=notepad]\n"
            "[TOOL:open_url|url=https://...]\n"
            "[TOOL:open_folder|path=...]\n"
            "[TOOL:open_wifi]\n"
            "[TOOL:type_text|text=...]\n"
            "[TOOL:press_key|key=enter]\n"
            "[TOOL:screenshot|path=optional]\n"
            "[TOOL:screen_report]\n"
            "[TOOL:list_windows]\n"
            "[TOOL:click|x=100|y=200]\n"
            "[TOOL:double_click|x=100|y=200]\n"
            "[TOOL:hotkey|keys=ctrl s]\n"
            "[TOOL:vault_list]\n"
            "[TOOL:vault_search|query=...]\n"
            "[TOOL:vault_read|path=...]\n"
            "[TOOL:web_search|query=...]\n"
            "[TOOL:web_fetch|url=...]\n"
            "[TOOL:write_file|path=...|content=...]  (may require confirm)\n"
            "[TOOL:list_workspace]\n""[TOOL:code_write|name=file.py|content=...]\n""[TOOL:code_read|name=file.py]\n""[TOOL:code_run|name=file.py]\n"
            "Do not invent tool results."
        )

    def execute(self, name: str, args: dict) -> str:
        name = name.lower()
        handlers: dict[str, Callable[[], str]] = {
            "remember": lambda: self._remember(args.get("text", "")),
            "show_memory": lambda: self.r["memory"].context() or "Memory empty.",
            "system_status": lambda: self._status(),
            "find_folder": lambda: self.r["pc"].find_named(args.get("name", "")),
            "list_folder": lambda: self.r["pc"].list_folder(args.get("path", "")),
            "open_app": lambda: self.r["pc"].open_app(args.get("name", "")),
            "open_url": lambda: self.r["pc"].open_url(args.get("url", "")),
            "open_folder": lambda: self.r["pc"].open_folder(args.get("path", "")),
            "open_wifi": lambda: self.r["pc"].open_wifi(),
            "type_text": lambda: self.r["pc"].type_text(args.get("text", "")),
            "press_key": lambda: self.r["pc"].press(args.get("key", "enter")),
            "screenshot": lambda: self._screenshot(args.get("path", "")),
            "screen_report": lambda: self.r["pc"].screen_report(),
            "list_windows": lambda: self.r["pc"].list_windows(),
            "click": lambda: self.r["pc"].click(args.get("x") and int(args.get("x")), args.get("y") and int(args.get("y"))),
            "double_click": lambda: self.r["pc"].double_click(args.get("x") and int(args.get("x")), args.get("y") and int(args.get("y"))),
            "hotkey": lambda: self.r["pc"].hotkey(args.get("keys", "")),
            "vault_list": lambda: self._vault_list(),
            "vault_search": lambda: self._vault_search(args.get("query", "")),
            "vault_read": lambda: self._vault_read(args.get("path", "")),
            "web_search": lambda: self._web(args.get("query", "")),
            "web_fetch": lambda: self._fetch(args.get("url", "")),
            "write_file": lambda: self._write(
                args.get("path", ""), args.get("content", ""), args.get("confirm", "")
            ),
            "list_workspace": lambda: "\n".join(self.r["coding"].list_files()) or "(empty)",
            "code_write": lambda: str(self.r["coding"].write_named(args.get("name","note.py"), args.get("content",""))),
            "code_read": lambda: self.r["coding"].read(args.get("name","")),
            "code_run": lambda: self.r["coding"].run_python(args.get("name","")),
        }
        fn = handlers.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        try:
            return fn()
        except Exception as e:
            return f"Tool {name} failed: {e}"

    def _remember(self, text: str) -> str:
        if not text.strip():
            return "Nothing to remember."
        self.r["memory"].remember(text.strip(), "facts")
        return "Saved to local memory."

    def _status(self) -> str:
        s = self.r["pc"].system_summary()
        return f"CPU {s['cpu_percent']}% RAM {s['ram_percent']}% Disk {s.get('disk_percent')}%"

    def _vault_list(self) -> str:
        items = self.r["vault"].index()
        if not items:
            return "Vault empty."
        return "\n".join(f"- [{x['game']}] {x['name']}" for x in items[:40])

    def _vault_search(self, q: str) -> str:
        hits = self.r["vault"].search(q)
        if not hits:
            return "No vault matches."
        return "\n".join(f"- [{h['game']}] {h['name']} @ {h['path']}" for h in hits[:20])

    def _vault_read(self, path: str) -> str:
        if not path:
            return "Missing path."
        try:
            return self.r["vault"].read(path, max_chars=8000)
        except Exception as e:
            return str(e)

    def _web(self, q: str) -> str:
        if not q.strip():
            return "Empty query."
        try:
            items = self.r["web"].search(q)
        except Exception as e:
            return f"Web unavailable (offline?): {e}"
        if not items:
            return "No results."
        return "\n".join(f"- {i['title']}: {i['url']}" for i in items)

    def _fetch(self, url: str) -> str:
        try:
            return self.r["web"].fetch(url)[:4000]
        except Exception as e:
            return f"Fetch failed: {e}"

    def _screenshot(self, path: str) -> str:
        from jarvis.paths import WORKSPACE

        dest = Path(path) if path else (WORKSPACE / "screen_shot.png")
        try:
            p = self.r["pc"].screenshot(dest)
            return f"Screenshot saved: {p}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    def _write(self, path: str, content: str, confirm: str) -> str:
        sec = (self.r.get("settings") or {}).get("security") or {}
        if sec.get("require_confirmation_for_delete", True) and Path(path).exists():
            if confirm.lower() not in ("1", "true", "yes", "y"):
                return f"CONFIRMATION REQUIRED to overwrite {path}. Re-call with confirm=yes"
        return self.r["pc"].write_file(path, content, confirm=confirm.lower() in ("1", "true", "yes", "y"))
