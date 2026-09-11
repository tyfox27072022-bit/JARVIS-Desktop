"""Sort a folder into simple type buckets. Never deletes."""
from __future__ import annotations

import shutil
from pathlib import Path

BUCKETS = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Scripts": {".py", ".js", ".gpc", ".ps1", ".bat", ".cmd", ".cs"},
}


def organize_folder(path: Path, audit=None) -> str:
    path = Path(path).expanduser()
    if not path.is_dir():
        return f"I can't see a folder at {path}."
    moved = []
    skipped = 0
    for item in list(path.iterdir()):
        if not item.is_file():
            continue
        if item.name.startswith("."):
            continue
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
        if audit:
            audit.log(f"Organized {item} -> {target}")
    if not moved:
        return f"Nothing new to sort in {path}."
    preview = "\n".join(moved[:25])
    extra = f"\n…and {len(moved) - 25} more." if len(moved) > 25 else ""
    skip = f"\nSkipped {skipped} that already existed." if skipped else ""
    return f"Sorted {len(moved)} file(s) in {path}:\n{preview}{extra}{skip}"
