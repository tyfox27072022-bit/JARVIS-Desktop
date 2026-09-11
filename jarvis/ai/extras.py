"""Free extras: currency, passwords, reminders, site check, recent files."""
from __future__ import annotations

import json
import random
import re
import secrets
import string
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

from jarvis.paths import DATA

UA = {"User-Agent": "Mozilla/5.0 JARVIS/2.0"}
REMINDERS = DATA / "reminders.json"


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    for fn in (_currency, _password, _reminder, _site, _recent, _wordcount, _empty_report):
        hit = fn(brain, raw, low)
        if hit:
            return hit
    return None


def _currency(brain, raw, low):
    m = re.search(
        r"(?:convert\s+)?(\d+(?:\.\d+)?)\s*([a-z]{3})\s+(?:to|in)\s+([a-z]{3})",
        low,
    )
    if not m and "how much is" in low:
        m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]{3}).*([a-z]{3})", low)
    if not m:
        return None
    amount, src, dst = float(m.group(1)), m.group(2).upper(), m.group(3).upper()
    try:
        r = requests.get(
            f"https://api.frankfurter.app/latest?amount={amount}&from={src}&to={dst}",
            headers=UA,
            timeout=12,
        )
        data = r.json()
        val = (data.get("rates") or {}).get(dst)
        if val is not None:
            return f"{amount:g} {src} is about {val:g} {dst}."
    except Exception:
        pass
    return f"Couldn't convert {src} to {dst} right now."


def _password(brain, raw, low):
    if not re.search(r"\b(password|passcode)\b", low):
        return None
    if not re.search(r"\b(make|generate|give|new|create|random)\b", low) and low not in {
        "password", "new password",
    }:
        return None
    n = 16
    m = re.search(r"(\d+)\s*(?:char|letter)", low)
    if m:
        n = max(8, min(64, int(m.group(1))))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    pw = "".join(secrets.choice(alphabet) for _ in range(n))
    return f"Here's a new one ({n} chars):\n{pw}\nI haven't stored it."


def _reminder(brain, raw, low):
    m = re.match(r"^(?:remind me(?: to)?|set a reminder(?: to)?)\s+(.+)$", raw, re.I)
    if m:
        text = m.group(1).strip()
        items = []
        if REMINDERS.exists():
            try:
                items = json.loads(REMINDERS.read_text(encoding="utf-8"))
            except Exception:
                items = []
        items.append({"text": text, "created": datetime.now().isoformat(timespec="seconds")})
        REMINDERS.parent.mkdir(parents=True, exist_ok=True)
        REMINDERS.write_text(json.dumps(items, indent=2), encoding="utf-8")
        try:
            brain.memory.remember("Reminder: " + text, "notes")
        except Exception:
            pass
        return f"I'll keep that: {text}"
    if low in {"reminders", "my reminders", "what are my reminders"}:
        if not REMINDERS.exists():
            return "No reminders yet."
        try:
            items = json.loads(REMINDERS.read_text(encoding="utf-8"))
        except Exception:
            return "Couldn't read reminders."
        if not items:
            return "No reminders yet."
        return "Reminders:\n" + "\n".join(f"- {i.get('text')}" for i in items[-20:])
    return None


def _site(brain, raw, low):
    m = re.match(r"^(?:is|check)\s+(\S+)\s+(?:up|down|online)\??$", low)
    if not m:
        return None
    host = m.group(1).strip()
    if not host.startswith("http"):
        host = "https://" + host
    try:
        r = requests.get(host, headers=UA, timeout=8)
        return f"{host} responded {r.status_code}."
    except Exception as e:
        return f"{host} didn't respond ({e.__class__.__name__})."


def _recent(brain, raw, low):
    if low not in {
        "recent downloads", "what's new in downloads", "whats new in downloads",
        "latest downloads", "new files",
    }:
        return None
    folder = Path.home() / "Downloads"
    if not folder.is_dir():
        return "No Downloads folder."
    files = [p for p in folder.iterdir() if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "Downloads is empty."
    lines = ["Latest in Downloads:"]
    for p in files[:12]:
        lines.append(f"  {p.name}")
    return "\n".join(lines)


def _wordcount(brain, raw, low):
    m = re.match(r"^(?:count(?: the)? words|word count)\s*[:\-]?\s*(.+)$", raw, re.I)
    if not m:
        return None
    text = m.group(1)
    words = re.findall(r"\w+", text)
    return f"{len(words)} words, {len(text)} characters."


def _empty_report(brain, raw, low):
    return None
