"""Advanced multi-step jobs: research, projects, clipboard, follow-ups."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from jarvis.pc.files_plus import (
    _hint_folder,
    copy_to,
    move_matches,
    rename_in,
    search_content,
)


def split_compound(raw: str) -> list[str]:
    parts = re.split(r"\s+(?:and then|, then|then)\s+", raw.strip(), maxsplit=3, flags=re.I)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else [raw.strip()]


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    if not low:
        return None
    for fn in (
        _again,
        _save_that,
        _research,
        _clipboard,
        _notify,
        _containing,
        _rename,
        _move,
        _copy,
        _read_file,
        _project,
        _zip_it,
    ):
        hit = fn(brain, raw, low)
        if hit:
            return hit
    return None


def _again(brain, raw, low):
    if low not in {"again", "do it again", "once more", "repeat that"}:
        return None
    prev = getattr(brain, "last_user", None)
    if not prev or prev.lower().strip() in {"again", "do it again"}:
        return "Do what again?"
    return brain.intents.handle(prev, depth=1)


def _save_that(brain, raw, low):
    if low not in {
        "save that", "save it", "save that to desktop", "put that on my desktop",
        "save that as a note",
    }:
        return None
    text = getattr(brain, "last_answer", None) or ""
    if not text:
        return "Nothing to save yet."
    dest = Path.home() / "Desktop" / "jarvis_note.txt"
    dest.write_text(text, encoding="utf-8")
    return f"Saved that to {dest}"


def _research(brain, raw, low):
    m = re.match(
        r"^(?:research|look into|dig into|write me notes on|brief me on)\s+(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    topic = m.group(1).strip()
    facts = ""
    try:
        facts = brain.web.answer(topic, open_browser=False) or ""
    except Exception as e:
        facts = str(e)
    body = f"{topic}\n{'=' * min(40, len(topic))}\n\n{facts}\n"
    dest = Path.home() / "Desktop" / (re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40] + "_notes.txt")
    dest.write_text(body, encoding="utf-8")
    try:
        if os.name == "nt":
            os.startfile(str(dest))  # type: ignore[attr-defined]
    except Exception:
        pass
    return f"Researched {topic} and saved notes:\n{dest}\n\n{facts[:900]}"


def _clipboard(brain, raw, low):
    if low in {"what's on my clipboard", "clipboard", "paste clipboard", "read clipboard"}:
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                text=True,
                timeout=8,
            )
            out = (out or "").strip()
            return out[:1500] if out else "Clipboard is empty."
        except Exception as e:
            return f"Couldn't read clipboard: {e}"
    m = re.match(r"^(?:copy this|put on clipboard|clipboard)\s+(.+)$", raw, re.I)
    if m:
        text = m.group(1)
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value {text!r}"],
                timeout=8,
                check=False,
            )
            return "Copied to clipboard."
        except Exception as e:
            return str(e)
    return None


def _notify(brain, raw, low):
    m = re.match(r"^(?:notify me|alert me|toast)\s+(.+)$", raw, re.I)
    if not m:
        return None
    msg = m.group(1).strip().replace("'", "''")
    if sys.platform != "win32":
        return f"Note: {msg}"
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(4000, 'JARVIS', '{msg[:80]}', 'Info')"
    )
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
    except Exception:
        pass
    return f"Pinged you: {msg}"


def _containing(brain, raw, low):
    m = re.search(
        r"(?:files? containing|containing text|grep|search inside files for|look inside files for)\s+(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    where = None
    for w in ("downloads", "desktop", "documents"):
        if w in low:
            where = w
    return search_content(m.group(1).strip().strip("\"'"), where)


def _rename(brain, raw, low):
    m = re.search(r"rename\s+(.+?)\s+to\s+(.+)$", raw, re.I)
    if not m:
        return None
    folder = _hint_folder("desktop" if "desktop" in low else "downloads")
    return rename_in(folder, m.group(1), m.group(2))


def _move(brain, raw, low):
    m = re.search(
        r"move\s+(?:all\s+)?(.+?)\s+(?:from\s+\w+\s+)?(?:to|into)\s+(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    needle, dest_name = m.group(1).strip(), m.group(2).strip()
    src = _hint_folder("desktop" if "desktop" in low else "downloads")
    dest = _hint_folder(dest_name)
    if dest_name.lower() not in {"desktop", "downloads", "documents", "pictures"}:
        dest = src / re.sub(r"[^\w \-]+", "", dest_name)[:40]
    return move_matches(src, needle, dest)


def _copy(brain, raw, low):
    m = re.search(r"copy\s+(.+?)\s+to\s+(desktop|downloads|documents)\b", raw, re.I)
    if not m:
        return None
    name = m.group(1).strip()
    dest = _hint_folder(m.group(2))
    pc = getattr(brain, "pc", None)
    if pc and getattr(pc, "last_hits", None):
        for p in pc.last_hits:
            if name.lower() in p.name.lower():
                return copy_to(p, dest)
    folder = Path.home() / "Downloads"
    hits = [p for p in folder.iterdir() if name.lower() in p.name.lower()] if folder.is_dir() else []
    if not hits:
        return f"Couldn't find {name} to copy."
    return copy_to(hits[0], dest)


def _read_file(brain, raw, low):
    m = re.match(
        r"^(?:read|open and read|what's in|whats in|show me)\s+(?:the file\s+)?(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    name = m.group(1).strip().strip("\"'")
    if any(w in name.lower() for w in ("clipboard", "downloads", "desktop", "my files")):
        return None
    pc = getattr(brain, "pc", None)
    if pc and getattr(pc, "last_hits", None):
        for p in pc.last_hits:
            if name.lower() in p.name.lower() and p.is_file():
                try:
                    return p.read_text(encoding="utf-8", errors="replace")[:2500]
                except Exception as e:
                    return str(e)
    folder = Path.home() / "Downloads"
    hits = [p for p in folder.rglob("*") if p.is_file() and name.lower() in p.name.lower()]
    hits = hits[:1]
    if not hits:
        return None
    try:
        return hits[0].read_text(encoding="utf-8", errors="replace")[:2500]
    except Exception:
        return f"Can't read {hits[0].name} as text."


def _project(brain, raw, low):
    m = re.match(
        r"^(?:new project|create a project|make a project|scaffold)\s+(?:called\s+)?(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    name = re.sub(r"[^\w\-]+", "_", m.group(1).strip())[:32] or "project"
    root = Path.home() / "Desktop" / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# {name}\n\nMade by JARVIS for Ty.\n", encoding="utf-8")
    if "python" in low or "py" in low:
        (root / "main.py").write_text(
            f'"""{name}"""\n\ndef main():\n    print({name!r})\n\nif __name__ == "__main__":\n    main()\n',
            encoding="utf-8",
        )
        (root / "requirements.txt").write_text("", encoding="utf-8")
    else:
        (root / "index.html").write_text(
            f"<!DOCTYPE html><html><head><meta charset=utf-8><title>{name}</title>"
            f"<link rel=stylesheet href=style.css></head><body><h1>{name}</h1>"
            f"<script src=app.js></script></body></html>\n",
            encoding="utf-8",
        )
        (root / "style.css").write_text("body{font-family:sans-serif;margin:2rem}\n", encoding="utf-8")
        (root / "app.js").write_text("console.log('ready');\n", encoding="utf-8")
    return f"Project ready on your Desktop:\n{root}"


def _zip_it(brain, raw, low):
    m = re.match(r"^(?:zip|compress)\s+(.+)$", raw, re.I)
    if not m:
        return None
    name = m.group(1).strip()
    src = Path.home() / "Desktop" / name
    if not src.exists():
        src = Path.home() / "Downloads" / name
    if not src.exists():
        return f"Can't find {name} to zip."
    dest = src.with_suffix(".zip") if src.is_dir() else src.with_name(src.stem + "_pack.zip")
    if src.is_dir():
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p in src.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(src))
    else:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(src, src.name)
    return f"Zipped to {dest}"
