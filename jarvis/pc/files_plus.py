"""Move, copy, rename, content search — never deletes."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

TEXT_EXT = {
    ".txt", ".md", ".py", ".js", ".json", ".csv", ".log", ".ini", ".cfg",
    ".html", ".css", ".xml", ".yml", ".yaml", ".gpc", ".bat", ".ps1",
}


def _hint_folder(hint: str | None) -> Path:
    home = Path.home()
    h = (hint or "").lower()
    if "desktop" in h:
        return home / "Desktop"
    if "document" in h:
        return home / "Documents"
    if "picture" in h:
        return home / "Pictures"
    return home / "Downloads"


def search_content(needle: str, where: str | None = None, limit: int = 12) -> str:
    folder = _hint_folder(where)
    if not folder.is_dir():
        return f"No folder {folder}"
    needle_l = (needle or "").lower().strip()
    if len(needle_l) < 2:
        return "What text should I look for?"
    hits = []
    scanned = 0
    for p in folder.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        scanned += 1
        if scanned > 800:
            break
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if needle_l in text.lower():
            line = next((ln.strip() for ln in text.splitlines() if needle_l in ln.lower()), "")
            hits.append((p, line[:120]))
        if len(hits) >= limit:
            break
    if not hits:
        return f"No files in {folder.name} containing “{needle}”."
    lines = [f"Text “{needle}” shows up in {folder.name}:"]
    for i, (p, snippet) in enumerate(hits, 1):
        lines.append(f"{i}. {p.name}")
        if snippet:
            lines.append(f"   … {snippet}")
    lines.append("Say open 1 if you want the first one.")
    return "\n".join(lines)


def rename_in(folder: Path, old: str, new: str) -> str:
    folder = Path(folder)
    old, new = old.strip(), new.strip()
    if not old or not new:
        return "Need an old name and a new name."
    hits = [p for p in folder.iterdir() if old.lower() in p.name.lower()]
    if not hits:
        return f"Nothing matching {old} in {folder.name}."
    p = hits[0]
    dest = p.with_name(new if "." in new else new + p.suffix)
    if dest.exists():
        return f"{dest.name} already exists."
    p.rename(dest)
    return f"Renamed {p.name} → {dest.name}"


def move_matches(folder: Path, needle: str, dest: Path) -> str:
    folder, dest = Path(folder), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    needle = needle.lower().strip()
    moved = []
    for p in list(folder.iterdir()):
        if not p.is_file():
            continue
        if needle in p.name.lower() or (needle.startswith(".") and p.suffix.lower() == needle):
            target = dest / p.name
            if target.exists():
                continue
            shutil.move(str(p), str(target))
            moved.append(p.name)
    if not moved:
        return f"Nothing matching {needle} in {folder.name}."
    return f"Moved {len(moved)} to {dest}:\n" + "\n".join(f"  {n}" for n in moved[:20])


def copy_to(src: Path, dest_dir: Path) -> str:
    src, dest_dir = Path(src), Path(dest_dir)
    if not src.exists():
        return f"Can't find {src}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest)
    return f"Copied {src.name} to {dest_dir}"
