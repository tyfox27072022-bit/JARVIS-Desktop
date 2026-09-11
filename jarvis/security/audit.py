from datetime import datetime
from pathlib import Path

from jarvis.paths import LOGS


class AuditLog:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.path = LOGS / "audit.log"
        LOGS.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        if not self.enabled:
            return
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

    def recent(self, n: int = 50) -> list[str]:
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
            return lines[-n:]
        except OSError:
            return []
