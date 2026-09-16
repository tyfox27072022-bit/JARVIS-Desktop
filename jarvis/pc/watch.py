"""Keep watching the screen until Ty says stop."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from jarvis.paths import DATA
from jarvis.pc.vision import capture, foreground, ocr, sensitive

PATH = DATA / "activity.json"
STATE = DATA / "watch_state.json"
SKIP_APPS = {"jarvis", "python", "pythonw", "explorer", "dwm", "shellexperiencehost", "searchhost"}


def _load() -> dict:
    if not PATH.exists():
        return {"samples": [], "apps": {}, "habits": [], "screen_notes": []}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"samples": [], "apps": {}, "habits": [], "screen_notes": []}


def _save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_on() -> bool:
    if not STATE.exists():
        return True
    try:
        return bool(json.loads(STATE.read_text(encoding="utf-8")).get("on", True))
    except Exception:
        return True


def set_on(on: bool) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    prev = {}
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    prev["on"] = bool(on)
    prev["since" if on else "stopped"] = datetime.now().isoformat(timespec="seconds")
    STATE.write_text(json.dumps(prev, indent=2), encoding="utf-8")


def tick(pc=None) -> dict | None:
    """Foreground always; screenshot+OCR when the window changes."""
    if not is_on():
        return None
    fg = foreground()
    app = (fg.get("app") or "").strip()
    title = (fg.get("title") or "").strip()
    if not app and not title:
        return None
    low_app = app.lower().replace(".exe", "")
    if any(s in low_app for s in SKIP_APPS):
        return None
    private = sensitive(title)
    if private:
        title = "(private)"
    data = _load()
    samples = data.setdefault("samples", [])
    last = samples[-1] if samples else None
    changed = not last or last.get("app") != app or last.get("title") != title[:120]
    row = {
        "app": app,
        "title": title[:120],
        "t": datetime.now().isoformat(timespec="seconds"),
        "n": 1,
    }
    text = ""
    if changed and pc is not None and not private:
        try:
            shot = capture(pc)
            text = ocr(shot)[:800]
            if text:
                row["text"] = text
                try:
                    (DATA / "last_screen.txt").write_text(
                        f"Foreground: {app} — {title}\n\n{text}",
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                notes = data.setdefault("screen_notes", [])
                notes.append({"t": row["t"], "app": app, "title": title[:80], "text": text[:240]})
                data["screen_notes"] = notes[-80:]
        except Exception:
            pass
        samples.append(row)
    elif last:
        last["t"] = row["t"]
        last["n"] = int(last.get("n") or 1) + 1
    else:
        samples.append(row)
    data["samples"] = samples[-300:]
    apps = data.setdefault("apps", {})
    apps[app] = int(apps.get(app) or 0) + 1
    data["habits"] = _habits(apps)
    _save(data)
    return row


def _habits(apps: dict) -> list[str]:
    if not apps:
        return []
    ranked = sorted(apps.items(), key=lambda kv: kv[1], reverse=True)
    names = [a.replace(".exe", "") for a, n in ranked[:5] if n >= 3]
    if not names:
        return []
    return ["Often uses " + ", ".join(names)]


def report() -> str:
    watching = "Watching your screen. Say 'stop watching' to end it." if is_on() else "Not watching. Say 'watch my screen' to start."
    data = _load()
    samples = data.get("samples") or []
    if not samples:
        return watching + "\nNothing logged yet."
    apps = data.get("apps") or {}
    ranked = sorted(apps.items(), key=lambda kv: kv[1], reverse=True)[:8]
    lines = [watching]
    if data.get("habits"):
        lines.append(data["habits"][0])
    lines.append("Apps:")
    for app, n in ranked:
        lines.append(f"  {app}  ×{n}")
    lines.append("Recent:")
    for s in samples[-8:]:
        extra = f"  “{(s.get('text') or '')[:60]}”" if s.get("text") else ""
        lines.append(f"  {s.get('app','')} — {s.get('title','')}{extra}")
    return "\n".join(lines)


def context_block() -> str:
    bits = ["WATCHING" if is_on() else "not watching"]
    data = _load()
    if data.get("habits"):
        bits.append(data["habits"][0])
    samples = data.get("samples") or []
    if samples:
        last = samples[-1]
        bits.append(f"Just now: {last.get('app')} — {last.get('title')}")
        if last.get("text"):
            bits.append("Screen: " + last["text"][:200])
    return " | ".join(bits)


def distill(memory) -> None:
    data = _load()
    for h in data.get("habits") or []:
        if memory and not memory.already_has(h):
            memory.remember(h, "activity")
    samples = data.get("samples") or []
    titles = [s.get("title") or "" for s in samples[-40:]]
    words = []
    for t in titles:
        for w in t.replace("|", " ").replace("-", " ").split():
            if len(w) > 4 and w[0].isupper():
                words.append(w)
    if not words:
        return
    for w, n in Counter(words).most_common(3):
        if n >= 4:
            fact = f"Often has “{w}” on screen"
            if memory and not memory.already_has(fact):
                memory.remember(fact, "activity")
