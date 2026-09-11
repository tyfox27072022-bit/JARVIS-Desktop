"""Sort folders into buckets. Never deletes. Undo is stored."""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.paths import DATA

BUCKETS = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".heic", ".tif", ".tiff"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
    "Installers": {".exe", ".msi", ".msix", ".apk"},
    "Scripts": {".py", ".js", ".ts", ".gpc", ".ps1", ".bat", ".cmd", ".cs", ".lua", ".sh"},
    "Code": {".html", ".css", ".json", ".xml", ".yml", ".yaml", ".java", ".cpp", ".h", ".rs", ".go"},
    "eBooks": {".epub", ".mobi", ".azw3"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
    "3D": {".obj", ".fbx", ".stl", ".blend", ".glb"},
}

UNDO = DATA / "last_organize.json"


def _folder_from_hint(hint: str | None) -> Path:
    home = Path.home()
    h = (hint or "downloads").lower()
    if "desktop" in h:
        return home / "Desktop"
    if "document" in h:
        return home / "Documents"
    if "picture" in h:
        return home / "Pictures"
    if "video" in h:
        return home / "Videos"
    return home / "Downloads"


def organize_folder(path: Path, audit=None, by: str = "type") -> str:
    path = Path(path).expanduser()
    if not path.is_dir():
        return f"I can't see a folder at {path}."
    moved = []
    journal = []
    skipped = 0
    now = datetime.now()
    for item in list(path.iterdir()):
        if not item.is_file() or item.name.startswith("."):
            continue
        if item.suffix.lower() in {".lnk", ".url"}:
            continue
        if by == "date":
            try:
                age = now - datetime.fromtimestamp(item.stat().st_mtime)
            except OSError:
                age = timedelta(0)
            if age.days < 7:
                dest_name = "This week"
            elif age.days < 31:
                dest_name = "This month"
            else:
                dest_name = "Older"
        else:
            dest_name = "Other"
            ext = item.suffix.lower()
            for bucket, exts in BUCKETS.items():
                if ext in exts:
                    dest_name = bucket
                    break
        dest_dir = path / dest_name
        dest_dir.mkdir(exist_ok=True)
        target = dest_dir / item.name
        if target.exists():
            skipped += 1
            continue
        shutil.move(str(item), str(target))
        moved.append(f"{item.name} → {dest_name}/")
        journal.append({"from": str(item), "to": str(target)})
        if audit:
            audit.log(f"Organized {item} -> {target}")
    try:
        UNDO.parent.mkdir(parents=True, exist_ok=True)
        UNDO.write_text(json.dumps(journal, indent=2), encoding="utf-8")
    except Exception:
        pass
    if not moved:
        return f"Nothing new to sort in {path.name}."
    preview = "\n".join(moved[:20])
    extra = f"\n…and {len(moved) - 20} more." if len(moved) > 20 else ""
    skip = f"\nSkipped {skipped} names that already existed." if skipped else ""
    return (
        f"Sorted {len(moved)} file(s) in {path.name} by {by}:\n{preview}{extra}{skip}\n"
        "Say 'undo sort' if you want them back."
    )


def undo_last(audit=None) -> str:
    if not UNDO.exists():
        return "Nothing to undo."
    try:
        journal = json.loads(UNDO.read_text(encoding="utf-8"))
    except Exception:
        return "Couldn't read the last sort."
    back = 0
    for row in reversed(journal):
        src, dst = Path(row.get("to") or ""), Path(row.get("from") or "")
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            back += 1
            if audit:
                audit.log(f"Undo organize {src} -> {dst}")
    try:
        UNDO.unlink()
    except Exception:
        pass
    return f"Moved {back} file(s) back."


def find_duplicates(path: Path) -> str:
    path = Path(path).expanduser()
    if not path.is_dir():
        return f"No folder at {path}."
    by_name = defaultdict(list)
    for p in path.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            by_name[p.name.lower()].append(p)
    dups = {k: v for k, v in by_name.items() if len(v) > 1}
    if not dups:
        return f"No duplicate names in {path.name}."
    lines = [f"Duplicate names in {path.name}:"]
    n = 0
    for name, files in list(dups.items())[:15]:
        lines.append(name)
        for f in files[:4]:
            lines.append(f"  {f}")
        n += 1
    extra = f"\n…and {len(dups) - 15} more names." if len(dups) > 15 else ""
    return "\n".join(lines) + extra


def find_large(path: Path, n: int = 10) -> str:
    path = Path(path).expanduser()
    if not path.is_dir():
        return f"No folder at {path}."
    files = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        try:
            files.append((p.stat().st_size, p))
        except OSError:
            continue
        if len(files) > 5000:
            break
    files.sort(reverse=True)
    if not files:
        return f"Empty: {path.name}"
    lines = [f"Biggest files in {path.name}:"]
    for size, p in files[:n]:
        mb = size / (1024 * 1024)
        lines.append(f"  {mb:.1f} MB  {p.name}")
    return "\n".join(lines)


def unzip_file(path: Path) -> str:
    import zipfile

    path = Path(path).expanduser()
    if not path.is_file() or path.suffix.lower() != ".zip":
        return f"That's not a zip: {path}"
    dest = path.with_suffix("")
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, "r") as z:
        z.extractall(dest)
    return f"Unzipped into {dest}"
