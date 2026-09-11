import os
import shutil
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def persist_dir() -> Path:
    """Survives closing the app and unzipping a new copy."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
        p = root / "JARVIS"
    else:
        p = Path.home() / ".jarvis"
    p.mkdir(parents=True, exist_ok=True)
    return p


BASE = app_dir()
PERSIST = persist_dir()
CONFIG_PATH = BASE / "config" / "settings.json"
USER_SETTINGS = PERSIST / "settings.json"
DATA = PERSIST / "data"
MEMORY_DIR = DATA / "memory"
LOGS = DATA / "logs"
IMPROVEMENTS = DATA / "improvements"
STYLE_DIR = DATA / "style"
CONVO_PATH = DATA / "conversation.json"
WORKSPACE = PERSIST / "workspace"
CODING_WS = WORKSPACE / "coding"
VAULT = BASE / "vault" / "scripts"
MODELS = BASE / "models"

for p in (
    CONFIG_PATH.parent,
    USER_SETTINGS.parent,
    MEMORY_DIR,
    LOGS,
    IMPROVEMENTS,
    STYLE_DIR,
    WORKSPACE,
    CODING_WS,
    VAULT,
):
    p.mkdir(parents=True, exist_ok=True)


def migrate_old_data() -> None:
    old = BASE / "data"
    if not old.is_dir():
        return
    mapping = [
        (old / "memory" / "memory.json", MEMORY_DIR / "memory.json"),
        (old / "style" / "style_profile.json", STYLE_DIR / "style_profile.json"),
        (old / "conversation.json", CONVO_PATH),
        (old / "file_index.txt", DATA / "file_index.txt"),
        (old / "models", DATA / "models"),
        (old / "logs", LOGS),
    ]
    for src, dst in mapping:
        try:
            if not src.exists():
                continue
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        except Exception:
            pass


migrate_old_data()
