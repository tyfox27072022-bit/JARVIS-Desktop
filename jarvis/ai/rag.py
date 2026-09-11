"""Answer from files on this PC (Downloads/Documents/Desktop)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

TEXT_EXT = {
    ".txt", ".md", ".py", ".js", ".json", ".log", ".ini", ".csv",
    ".html", ".css", ".xml", ".yml", ".yaml", ".gpc", ".bat",
}


def _roots():
    home = Path.home()
    for n in ("Documents", "Desktop", "Downloads", "OneDrive"):
        p = home / n
        if p.is_dir():
            yield p


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower()
    m = re.match(
        r"^(?:according to my files|what do my files say about|"
        r"search my (?:docs|documents|files) for|from my files)\s+(.+)$",
        raw,
        re.I,
    )
    if m:
        return search_answer(m.group(1).strip())
    m = re.match(r"^(?:summarise|summarize|peek(?: at)?)\s+(.+\.csv)\s*$", raw, re.I)
    if m:
        return summarise_csv(m.group(1).strip())
    if "according to my files" in low or "what do my files say" in low:
        q = re.sub(r".*(?:about|for)\s+", "", raw, flags=re.I).strip()
        if q:
            return search_answer(q)
    return None


def search_answer(query: str, limit: int = 8) -> str:
    q = (query or "").lower().strip()
    if len(q) < 2:
        return "What should I look for in your files?"
    words = [w for w in re.findall(r"[a-z0-9]{3,}", q)]
    hits = []
    scanned = 0
    for root in _roots():
        try:
            for p in root.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
                    continue
                if any(x in p.parts for x in ("node_modules", ".git", "AppData")):
                    continue
                scanned += 1
                if scanned > 1200:
                    break
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                low = text.lower()
                if q in low or (words and all(w in low for w in words[:3])):
                    line = next((ln.strip() for ln in text.splitlines() if q in ln.lower() or (words and words[0] in ln.lower())), "")
                    hits.append((p, line[:160]))
                if len(hits) >= limit:
                    break
        except OSError:
            continue
        if len(hits) >= limit or scanned > 1200:
            break
    if not hits:
        return f"Nothing in your Documents/Desktop/Downloads about “{query}”."
    lines = [f"From your files, on “{query}”:"]
    for p, snippet in hits:
        lines.append(f"- {p.name} ({p.parent.name})")
        if snippet:
            lines.append(f"    {snippet}")
    return "\n".join(lines)


def summarise_csv(name: str) -> str:
    needle = Path(name).name.lower()
    found = None
    for root in _roots():
        for p in root.glob("*.csv"):
            if needle in p.name.lower() or p.name.lower() == needle:
                found = p
                break
        if found:
            break
    if not found:
        return f"No CSV named {name}."
    try:
        with found.open(encoding="utf-8", errors="replace", newline="") as f:
            rows = list(csv.reader(f))
    except Exception as e:
        return str(e)
    if not rows:
        return f"{found.name} is empty."
    header, body = rows[0], rows[1:]
    return (
        f"{found.name}: {len(body)} rows, {len(header)} columns.\n"
        f"Columns: {', '.join(header[:20])}\n"
        + "\n".join(", ".join(r[:8]) for r in body[:5])
    )
