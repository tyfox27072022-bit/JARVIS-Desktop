import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE = app_dir()
CONFIG_PATH = BASE / "config" / "settings.json"
DATA = BASE / "data"
MEMORY_DIR = DATA / "memory"
LOGS = DATA / "logs"
IMPROVEMENTS = DATA / "improvements"
STYLE_DIR = DATA / "style"
WORKSPACE = BASE / "workspace"
CODING_WS = WORKSPACE / "coding"
VAULT = BASE / "vault" / "scripts"

for p in (
    CONFIG_PATH.parent,
    MEMORY_DIR,
    LOGS,
    IMPROVEMENTS,
    STYLE_DIR,
    WORKSPACE,
    CODING_WS,
    VAULT,
):
    p.mkdir(parents=True, exist_ok=True)
