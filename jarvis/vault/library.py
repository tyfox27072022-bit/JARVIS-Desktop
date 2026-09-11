import json
import shutil
from datetime import datetime
from pathlib import Path

HINTS = {
    "Fortnite": ["fortnite", "uefn"],
    "Rust": ["rust", "rust console", "recoil"],
    "Call of Duty": ["call of duty", "warzone", "black ops", "modern warfare", "cod"],
    "GTA": ["gta", "grand theft auto"],
    "EA FC": ["fifa", "ea fc"],
    "Apex Legends": ["apex legends", "apex"],
    "Destiny": ["destiny"],
}


class VaultLibrary:
    def __init__(self, root: Path, allowed_ext: list[str] | None = None, audit=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.allowed_ext = [e.lower() for e in (allowed_ext or [".gpc", ".txt", ".md"])]
        self.audit = audit
        self.index_path = self.root.parent / "index.json"

    def detect_game(self, path: Path) -> str:
        name = path.name.lower()
        try:
            text = path.read_text(errors="ignore")[:150000].lower()
        except Exception:
            text = name
        for game, hints in HINTS.items():
            if any(h in name or h in text for h in hints):
                return game
        return "Unknown Game"

    def index(self) -> list[dict]:
        items = []
        for p in self.root.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                items.append(
                    {
                        "name": p.name,
                        "game": p.parent.name,
                        "path": str(p),
                        "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(
                            timespec="seconds"
                        ),
                        "size": p.stat().st_size,
                    }
                )
        self._save_index(items)
        return items

    def _save_index(self, items: list[dict]):
        try:
            self.index_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        except OSError:
            pass

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [
            x
            for x in self.index()
            if q in x["name"].lower() or q in x["game"].lower() or q in x["path"].lower()
        ]

    def import_script(self, source: str | Path, quarantine: Path | None = None) -> tuple[Path, str]:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        if source.suffix.lower() not in self.allowed_ext and self.allowed_ext:
            if source.suffix.lower() not in {".gpc", ".txt", ".md", ".json", ".py"}:
                raise ValueError(f"Extension not allowed: {source.suffix}")
        # Quarantine first — never execute
        qdir = Path(quarantine) if quarantine else (self.root.parent / "quarantine")
        qdir.mkdir(parents=True, exist_ok=True)
        qpath = qdir / source.name
        if qpath.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            qpath = qdir / f"{source.stem}_{stamp}{source.suffix}"
        shutil.copy2(source, qpath)
        # Validate readable text-ish
        try:
            sample = qpath.read_text(encoding="utf-8", errors="replace")[:5000]
        except Exception as e:
            raise ValueError(f"Validation failed: {e}") from e
        if "\x00" in sample[:200]:
            raise ValueError("File looks binary; refusing import.")
        game = self.detect_game(qpath)
        dest = self.root / game / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = dest.with_name(f"{dest.stem}_{stamp}{dest.suffix}")
        shutil.copy2(qpath, dest)
        if self.audit:
            self.audit.log(f"Vault import: {source} -> quarantine -> {dest} ({game})")
        self.index()
        return dest, game

    def version_copy(self, path: str | Path, suffix: str = "modified") -> Path:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(str(p))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = p.with_name(f"{p.stem}_{suffix}_{stamp}{p.suffix}")
        shutil.copy2(p, out)
        if self.audit:
            self.audit.log(f"Version copy: {out}")
        return out

    def read(self, path: str | Path, max_chars: int = 100000) -> str:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:max_chars]
