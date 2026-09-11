"""Pro-level free skills: briefing, downloads, email, hash, git, newest file."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

UA = {"User-Agent": "Mozilla/5.0 JARVIS/2.0"}


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    for fn in (
        _briefing,
        _newest,
        _download,
        _email,
        _hash,
        _git,
        _focus,
        _timer,
        _calc_more,
    ):
        hit = fn(brain, raw, low)
        if hit:
            return hit
    return None


def _briefing(brain, raw, low):
    if low not in {
        "brief me", "catch me up", "what's going on", "whats going on",
        "daily briefing", "good morning jarvis",
    }:
        return None
    bits = [datetime.now().strftime("It's %I:%M %p, %A %d %B.")]
    try:
        r = requests.get("https://wttr.in/London?format=3", headers=UA, timeout=8)
        if r.ok:
            bits.append(r.text.strip())
    except Exception:
        pass
    try:
        from jarvis.ai.extras import REMINDERS
        import json

        if REMINDERS.exists():
            items = json.loads(REMINDERS.read_text(encoding="utf-8"))
            if items:
                bits.append("Reminders: " + "; ".join(i.get("text", "") for i in items[-5:]))
    except Exception:
        pass
    dl = Path.home() / "Downloads"
    if dl.is_dir():
        files = sorted(
            [p for p in dl.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if files:
            bits.append("Latest download: " + files[0].name)
    try:
        s = brain.pc.system_summary()
        bits.append(f"PC: CPU {s['cpu_percent']}% · RAM {s['ram_percent']}%")
    except Exception:
        pass
    return "\n".join(bits)


def _newest(brain, raw, low):
    if low not in {
        "open last download", "open latest download", "what did i just download",
        "newest file", "latest download", "open what i just downloaded",
    }:
        return None
    folder = Path.home() / "Downloads"
    files = [p for p in folder.iterdir() if p.is_file()] if folder.is_dir() else []
    if not files:
        return "Downloads is empty."
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    p = files[0]
    try:
        os.startfile(str(p))  # type: ignore[attr-defined]
    except Exception:
        pass
    return f"Latest in Downloads: {p.name}\nOpened it."


def _download(brain, raw, low):
    m = re.search(r"(?:download|save)\s+(https?://\S+)", raw, re.I)
    if not m:
        return None
    url = m.group(1).rstrip(".,)")
    name = Path(urlparse(url).path).name or "download"
    dest = Path.home() / "Downloads" / name
    try:
        r = requests.get(url, headers=UA, timeout=60, stream=True)
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return f"Saved to {dest}"
    except Exception as e:
        webbrowser.open(url)
        return f"Couldn't pull it here ({e}). Opened the link instead."


def _email(brain, raw, low):
    m = re.match(
        r"^(?:email|mail|send an? email to)\s+(\S+@\S+)\s+(?:about|re|saying)?\s*(.*)$",
        raw,
        re.I,
    )
    if not m:
        return None
    to, topic = m.group(1), (m.group(2) or "").strip()
    subj = topic[:80] or "Hello"
    body = topic or "Hi,"
    webbrowser.open(f"mailto:{to}?subject={quote(subj)}&body={quote(body)}")
    return f"Opened an email to {to}."


def _hash(brain, raw, low):
    m = re.match(r"^(?:hash|checksum|md5|sha256)\s+(.+)$", raw, re.I)
    if not m:
        return None
    name = m.group(1).strip()
    folder = Path.home() / "Downloads"
    hits = [p for p in folder.iterdir() if p.is_file() and name.lower() in p.name.lower()] if folder.is_dir() else []
    if not hits:
        return f"No file matching {name} in Downloads."
    p = hits[0]
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"{p.name}\nSHA256 {h.hexdigest()}"


def _git(brain, raw, low):
    if low not in {"git status", "what's the git status", "repo status"}:
        return None
    for root in (Path.home() / "Desktop", Path.home() / "Documents", Path.cwd()):
        if (root / ".git").exists():
            try:
                out = subprocess.check_output(["git", "-C", str(root), "status", "-sb"], text=True, timeout=8)
                return f"{root.name}:\n{out.strip()}"
            except Exception as e:
                return str(e)
    return "No git repo in Desktop/Documents that I can see."


def _focus(brain, raw, low):
    m = re.match(r"^(?:focus|switch to|bring up|foreground)\s+(.+)$", raw, re.I)
    if not m:
        return None
    return brain.pc.focus_window(m.group(1).strip())


def _timer(brain, raw, low):
    m = re.match(r"^(?:timer|set a timer(?: for)?)\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?)?$", raw, re.I)
    if not m:
        return None
    n = int(m.group(1))
    unit = (m.group(2) or "minutes").lower()
    secs = n
    if unit.startswith("min"):
        secs = n * 60
    elif unit.startswith("hour"):
        secs = n * 3600
    try:
        brain.memory.remember(f"Timer: {n} {unit}", "notes")
    except Exception:
        pass
    return f"Timer noted for {n} {unit} ({secs}s). I can't beep in the background yet — I'll remember it. Say 'notify me {n} {unit} done' after if you want a toast."


def _calc_more(brain, raw, low):
    return None
