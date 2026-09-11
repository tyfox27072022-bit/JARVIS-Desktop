"""Download / locate GGUF weights under data/models."""
from __future__ import annotations

import ssl
import urllib.request
from pathlib import Path

from jarvis.ai.model_catalog import DEFAULT_ID, DEFAULT_ORDER, MODELS, get_model
from jarvis.paths import DATA

MODELS_DIR = DATA / "models"
UA = "Mozilla/5.0 JARVIS/2.0 (local assistant)"


class ModelManager:
    def __init__(self, models_dir: Path | None = None):
        self.dir = Path(models_dir or MODELS_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, model_id: str) -> Path | None:
        meta = get_model(model_id)
        if not meta:
            return None
        p = self.dir / meta["filename"]
        return p if p.is_file() and p.stat().st_size > 1_000_000 else None

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
        found = [p for p in found if p.stat().st_size > 1_000_000]
        return found[0] if found else None

    def is_installed(self, model_id: str) -> bool:
        return self.path_for(model_id) is not None

    def list_installed(self) -> list[str]:
        return [p.name for p in sorted(self.dir.glob("*.gguf")) if p.stat().st_size > 1_000_000]

    def _retrieve(self, url: str, dest: Path, progress_cb=None) -> None:
        tmp = dest.with_suffix(dest.suffix + ".part")
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": UA})

        def _report(block_num, block_size, total):
            if progress_cb and total > 0:
                pct = min(100, int(block_num * block_size * 100 / total))
                progress_cb(f"Downloading brain {pct}%")

        with urllib.request.urlopen(req, context=ctx, timeout=120) as src, open(tmp, "wb") as out:
            total = int(src.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = src.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                got += len(chunk)
                if progress_cb and total > 0:
                    progress_cb(f"Downloading brain {min(100, int(got * 100 / total))}%")
        tmp.replace(dest)

    def download(self, model_id: str, progress_cb=None) -> Path:
        meta = get_model(model_id)
        if not meta:
            raise ValueError(f"Unknown model id: {model_id}")
        dest = self.dir / meta["filename"]
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            return dest
        if progress_cb:
            progress_cb(f"Fetching {meta['name']} (~{meta['approx_gb']} GB)")
        self._retrieve(meta["url"], dest, progress_cb=progress_cb)
        if not dest.is_file() or dest.stat().st_size < 1_000_000:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"Download incomplete for {model_id}")
        return dest

    def download_any(self, progress_cb=None) -> tuple[str, Path]:
        existing = self.resolve(DEFAULT_ID)
        if existing:
            for mid, meta in MODELS.items():
                if meta["filename"] == existing.name:
                    return mid, existing
            return DEFAULT_ID, existing
        last = None
        for mid in DEFAULT_ORDER:
            try:
                path = self.download(mid, progress_cb=progress_cb)
                return mid, path
            except Exception as e:
                last = e
                if progress_cb:
                    progress_cb(f"{mid} failed, trying next…")
                continue
        raise RuntimeError(f"Could not download a free local model: {last}")

    def status_text(self, model_id: str) -> str:
        meta = get_model(model_id) or {}
        path = self.path_for(model_id)
        if path:
            gb = path.stat().st_size / (1024**3)
            return f"Installed: {path.name} ({gb:.2f} GB)"
        return f"Not installed: {meta.get('name', model_id)}"
