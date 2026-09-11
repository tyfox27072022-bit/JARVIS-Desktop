"""Teachable workflows — Ty invents commands, JARVIS replays them."""
from __future__ import annotations

import json
import re
from pathlib import Path

from jarvis.paths import DATA

PATH = DATA / "macros.json"


def _load() -> dict:
    if not PATH.exists():
        return {}
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    m = re.match(
        r"^(?:when i say|if i say|remember (?:this )?workflow|save (?:this )?macro)\s+"
        r"[\"']?(.+?)[\"']?\s*(?:,|:| do | then | → |->)\s*(.+)$",
        raw,
        re.I,
    )
    if m:
        name = m.group(1).strip().strip("\"'").lower()
        body = m.group(2).strip()
        if body.lower().startswith("do "):
            body = body[3:].strip()
        steps = [s.strip() for s in re.split(r"\s+then\s+", body, flags=re.I) if s.strip()]
        if not name or not steps:
            return "Need a name and at least one step."
        data = _load()
        data[name] = steps
        _save(data)
        return f"Saved “{name}” → " + " then ".join(steps)

    if low in {"my workflows", "macros", "saved commands", "what workflows do i have"}:
        data = _load()
        if not data:
            return "None yet. Say: when I say night, do volume down then lock my pc"
        lines = ["Workflows:"]
        for k, steps in data.items():
            lines.append(f"- {k}: " + " then ".join(steps))
        return "\n".join(lines)

    m = re.match(r"^(?:forget workflow|delete macro)\s+(.+)$", raw, re.I)
    if m:
        name = m.group(1).strip().lower()
        data = _load()
        if name in data:
            del data[name]
            _save(data)
            return f"Forgot {name}."
        return f"No workflow called {name}."

    data = _load()
    key = re.sub(r"^(run|do)\s+", "", low).strip()
    if key in data:
        bits = []
        for step in data[key][:6]:
            try:
                hit = brain.intents.handle(step, depth=1)
            except Exception as e:
                hit = str(e)
            if hit:
                bits.append(hit)
        return "\n\n".join(bits) if bits else f"Ran {key}."
    return None
