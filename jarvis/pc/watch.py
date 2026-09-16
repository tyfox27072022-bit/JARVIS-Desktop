"""Learn from what Ty does: apps, windows, habits."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from jarvis.paths import DATA
from jarvis.pc.vision import foreground, sensitive

PATH = DATA / "activity.json"
SKIP_APPS = {"jarvis", "python", "pythonw", "explorer", "dwm", "shellexperiencehost", "searchhost"}


def _load() -> dict:
    if not PATH.exists():
        return {"samples": [], "apps": {}, "habits": []}
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"samples": [], "apps": {}, "habits": []}


def _save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sample() -> dict | None:
    fg = foreground()
    app = (fg.get("app") or "").strip()
    title = (fg.get("title") or "").strip()
    if not app and not title:
        return None
    low_app = app.lower().replace(".exe", "")
    if any(s in low_app for s in SKIP_APPS):
        return None
    if sensitive(title):
        title = "(private)"
    data = _load()
    row = {
        "app": app,
        "title": title[:120],
        "t": datetime.now().isoformat(timespec="seconds"),
    }
    samples = data.setdefault("samples", [])
    last = samples[-1] if samples else None
    if last and last.get("app") == app and last.get("title") == row["title"]:
        last["t"] = row["t"]
        last["n"] = int(last.get("n") or 1) + 1
    else:
        samples.append(row)
    data["samples"] = samples[-200:]
    apps = data.setdefault("apps", {})
    apps[app] = int(apps.get(app) or 0) + 1
    data["habits"] = _habits(apps)
    _save(data)
    return row


def _habits(apps: dict) -> list[str]:
    if not apps:
        return []
    ranked = sorted(apps.items(), key=lambda kv: kv[1], reverse=True)
    names = []
    for app, n in ranked[:5]:
        if n < 3:
            continue
        names.append(app.replace(".exe", ""))
    if not names:
        return []
    return ["Often uses " + ", ".join(names)]


def report() -> str:
    data = _load()
    samples = data.get("samples") or []
    if not samples:
        return "I haven't watched you yet. Leave me open and I'll pick up what you do."
    apps = data.get("apps") or {}
    ranked = sorted(apps.items(), key=lambda kv: kv[1], reverse=True)[:8]
    lines = ["What you've been doing (while JARVIS is open):"]
    if data.get("habits"):
        lines.append(data["habits"][0])
    lines.append("Apps:")
    for app, n in ranked:
        lines.append(f"  {app}  ×{n}")
    lines.append("Recent windows:")
    for s in samples[-8:]:
        lines.append(f"  {s.get('app','')} — {s.get('title','')}")
    return "\n".join(lines)


def context_block() -> str:
    data = _load()
    habits = data.get("habits") or []
    samples = data.get("samples") or []
    bits = []
    if habits:
        bits.append(habits[0])
    if samples:
        last = samples[-1]
        bits.append(f"Just now: {last.get('app')} — {last.get('title')}")
    return " | ".join(bits)


def distill(memory) -> None:
    data = _load()
    for h in data.get("habits") or []:
        if memory and not memory.already_has(h):
            memory.remember(h, "activity")
    samples = data.get("samples") or []
    titles = [s.get("title") or "" for s in samples[-30:]]
    words = []
    for t in titles:
        for w in t.replace("|", " ").replace("-", " ").split():
            if len(w) > 4 and w[0].isupper():
                words.append(w)
    if not words:
        return
    common = Counter(words).most_common(3)
    for w, n in common:
        if n >= 4:
            fact = f"Often has “{w}” on screen"
            if memory and not memory.already_has(fact):
                memory.remember(fact, "activity")
