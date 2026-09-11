"""Download / locate GGUF weights under data/models (replaceable)."""
from __future__ import annotations

import urllib.request
from pathlib import Path

from jarvis.ai.model_catalog import MODELS, get_model
from jarvis.paths import DATA

MODELS_DIR = DATA / "models"


class ModelManager:
    def __init__(self, models_dir: Path | None = None):
        self.dir = Path(models_dir or MODELS_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, model_id: str) -> Path | None:
        meta = get_model(model_id)
        if not meta:
            return None
        p = self.dir / meta["filename"]
        return p if p.is_file() else None

    def resolve(self, model_id: str | None, custom_path: str | None = None) -> Path | None:
        if custom_path:
            p = Path(custom_path).expanduser()
            if p.is_file():
                return p
        if model_id:
            hit = self.path_for(model_id)
            if hit:
                return hit
        found = sorted(self.dir.glob("*.gguf"))
        return found[0] if found else None

    def is_installed(self, model_id: str) -> bool:
        return self.path_for(model_id) is not None

    def list_installed(self) -> list[str]:
        return [p.name for p in sorted(self.dir.glob("*.gguf"))]

    def download(self, model_id: str, progress_cb=None) -> Path:
        meta = get_model(model_id)
        if not meta:
            raise ValueError(f"Unknown model id: {model_id}")
        dest = self.dir / meta["filename"]
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            return dest
        url = meta["url"]
        tmp = dest.with_suffix(dest.suffix + ".part")

        def _report(block_num, block_size, total):
            if progress_cb and total > 0:
                progress_cb(min(100, int(block_num * block_size * 100 / total)))

        urllib.request.urlretrieve(url, str(tmp), reporthook=_report if progress_cb else None)
        tmp.replace(dest)
        return dest

    def status_text(self, model_id: str) -> str:
        meta = get_model(model_id) or {}
        path = self.path_for(model_id)
        if path:
            gb = path.stat().st_size / (1024**3)
            return f"Installed: {path.name} ({gb:.2f} GB)"
        return (
            f"Not installed: {meta.get('name', model_id)} "
            f"(~{meta.get('approx_gb', '?')} GB). Use Settings → Download model."
        )
