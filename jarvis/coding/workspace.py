from datetime import datetime
from pathlib import Path

from jarvis.paths import CODING_WS


class CodingWorkspace:
    def __init__(self, root: Path | None = None, audit=None):
        self.root = Path(root or CODING_WS)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit = audit

    def create_file(self, name: str, content: str) -> Path:
        safe = Path(name).name
        path = self.root / safe
        if path.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.root / f"{path.stem}_{stamp}{path.suffix}"
        path.write_text(content, encoding="utf-8")
        if self.audit:
            self.audit.log(f"Coding workspace created: {path}")
        return path

    def read(self, name: str) -> str:
        path = self.root / Path(name).name
        if not path.exists():
            raise FileNotFoundError(name)
        return path.read_text(encoding="utf-8", errors="replace")

    def versioned_edit(self, name: str, new_content: str) -> Path:
        path = self.root / Path(name).name
        if path.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = path.with_name(f"{path.stem}_backup_{stamp}{path.suffix}")
            backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        path.write_text(new_content, encoding="utf-8")
        if self.audit:
            self.audit.log(f"Coding workspace edit: {path}")
        return path

    def list_files(self) -> list[str]:
        return [p.name for p in self.root.iterdir() if p.is_file()]

    def write_named(self, name: str, content: str) -> Path:
        return self.versioned_edit(name, content)

    def run_python(self, name: str, timeout: int = 20) -> str:
        import subprocess, sys
        path = self.root / Path(name).name
        if not path.is_file():
            raise FileNotFoundError(name)
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.root),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if self.audit:
            self.audit.log(f"Ran workspace file: {path.name}")
        return out[-4000:] or f"(exit {proc.returncode}, no output)"
