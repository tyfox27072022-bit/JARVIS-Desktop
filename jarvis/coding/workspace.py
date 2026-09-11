from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys

from jarvis.coding.languages import detect, scaffold
from jarvis.paths import CODING_WS


class CodingWorkspace:
    def __init__(self, root: Path | None = None, audit=None):
        self.root = Path(root or CODING_WS)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self.last_file: Path | None = None

    def create_file(self, name: str, content: str) -> Path:
        safe = Path(name).name
        path = self.root / safe
        if path.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.root / f"{path.stem}_{stamp}{path.suffix}"
        path.write_text(content, encoding="utf-8")
        self.last_file = path
        if self.audit:
            self.audit.log(f"Coding workspace created: {path}")
        return path

    def write_program(self, job: str, language_hint: str | None = None, engine=None) -> Path:
        blob = f"{language_hint or ''} {job}"
        ext, lang = detect(blob)
        name = self._name_from_job(job, ext)
        content = None
        if engine is not None and getattr(engine, "ready", False):
            try:
                prompt = (
                    f"Write a complete, runnable {lang} file for this request:\n{job}\n"
                    "Output ONLY the source code. No markdown fences."
                )
                raw = engine.chat(
                    f"You are a coding assistant. Write clean {lang}.",
                    [],
                    prompt,
                )
                raw = (raw or "").strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1]
                    if raw.endswith("```"):
                        raw = raw[: raw.rfind("```")]
                if len(raw) > 20:
                    content = raw.strip() + "\n"
            except Exception:
                content = None
        if not content:
            content = scaffold(ext, lang, job)
        return self.create_file(name, content)

    def _name_from_job(self, job: str, ext: str) -> str:
        import re

        words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", job or "")
        slug = "_".join(w.lower() for w in words[:4]) or "program"
        return f"{slug[:40]}.{ext}"

    def resolve(self, name: str | None = None) -> Path:
        if name:
            p = Path(name)
            if p.is_file():
                return p
            hit = self.root / Path(name).name
            if hit.is_file():
                return hit
        if self.last_file and self.last_file.is_file():
            return self.last_file
        files = sorted(self.root.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
        files = [f for f in files if f.is_file()]
        if not files:
            raise FileNotFoundError("No workspace file yet.")
        return files[0]

    def send_file(self, name: str | None = None, where: str = "desktop") -> str:
        path = self.resolve(name)
        dest_dir = Path.home() / "Desktop"
        if "download" in (where or "").lower():
            dest_dir = Path.home() / "Downloads"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        shutil.copy2(path, dest)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(dest)])
            else:
                subprocess.Popen(["xdg-open", str(dest_dir)])
        except Exception:
            pass
        if self.audit:
            self.audit.log(f"Sent file to {dest}")
        return f"Sent {path.name} to {dest}"

    def open_file(self, name: str | None = None) -> str:
        path = self.resolve(name)
        if sys.platform == "win32":
            import os

            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return f"Opened {path}"

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
        self.last_file = path
        if self.audit:
            self.audit.log(f"Coding workspace edit: {path}")
        return path

    def list_files(self) -> list[str]:
        return [p.name for p in self.root.iterdir() if p.is_file()]

    def write_named(self, name: str, content: str) -> Path:
        return self.versioned_edit(name, content)

    def run_file(self, name: str | None = None, timeout: int = 20) -> str:
        path = self.resolve(name)
        ext = path.suffix.lower()
        cmd = None
        if ext == ".py":
            cmd = [sys.executable, str(path)]
        elif ext in {".js", ".mjs"}:
            cmd = ["node", str(path)]
        elif ext == ".ps1":
            cmd = ["powershell", "-NoProfile", "-File", str(path)]
        elif ext in {".sh", ".bash"}:
            cmd = ["bash", str(path)]
        elif ext == ".rb":
            cmd = ["ruby", str(path)]
        elif ext == ".php":
            cmd = ["php", str(path)]
        elif ext == ".go":
            cmd = ["go", "run", str(path)]
        if not cmd:
            return f"I wrote it, but I don't auto-run .{ext.lstrip('.')} — say 'send {path.name}' and I'll put it on your Desktop."
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.root),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if self.audit:
            self.audit.log(f"Ran workspace file: {path.name}")
        return out[-4000:] or f"(exit {proc.returncode}, no output)"

    def run_python(self, name: str, timeout: int = 20) -> str:
        return self.run_file(name, timeout=timeout)
