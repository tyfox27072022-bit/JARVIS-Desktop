from datetime import datetime
from pathlib import Path

from jarvis.paths import IMPROVEMENTS


class ImprovementManager:
    def __init__(self, root: Path | None = None, audit=None):
        self.root = Path(root or IMPROVEMENTS)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit = audit

    def propose(self, title: str, description: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in title).strip() or "proposal"
        folder = self.root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe.replace(' ', '_')}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "proposal.txt").write_text(description, encoding="utf-8")
        (folder / "status.txt").write_text("WAITING FOR TY\n", encoding="utf-8")
        if self.audit:
            self.audit.log(f"Improvement proposal: {folder.name}")
        return folder

    def list_proposals(self) -> list[str]:
        return sorted(d.name for d in self.root.iterdir() if d.is_dir())
