"""
Local inference via standalone llama.cpp CLI (no C++ compile, works on Python 3.14).

Downloads a Windows binary into data/bin/ and runs GGUF models offline.
"""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

from jarvis.paths import DATA

BIN_DIR = DATA / "bin"

# Official-ish prebuilt CPU zip (update URL if release moves)
# Using llama-cpp b-series Windows binary from ggml releases when possible.
# Fallback: user can place llama-cli.exe manually in data/bin/
LLAMA_WIN_ZIP_CANDIDATES = [
    # These URLs may need updating; ModelManager-style discovery is best-effort.
    "https://github.com/ggerganov/llama.cpp/releases/download/b5217/llama-b5217-bin-win-avx2-x64.zip",
]


class CliEngine:
    def __init__(self):
        self.model_path: Path | None = None
        self.bin_path: Path | None = None
        self.n_ctx = 2048
        self.temperature = 0.5
        self.max_tokens = 512
        self.last_error: str | None = None

    @property
    def ready(self) -> bool:
        return bool(self.model_path and self.model_path.is_file() and self._find_bin())

    def _find_bin(self) -> Path | None:
        if self.bin_path and self.bin_path.is_file():
            return self.bin_path
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("llama-cli.exe", "main.exe", "llama.exe", "llama-cli", "main"):
            p = BIN_DIR / name
            if p.is_file():
                self.bin_path = p
                return p
        # nested extract folders
        for p in BIN_DIR.rglob("llama-cli.exe"):
            self.bin_path = p
            return p
        for p in BIN_DIR.rglob("main.exe"):
            self.bin_path = p
            return p
        return None

    def ensure_binary(self, progress_cb=None) -> Path:
        existing = self._find_bin()
        if existing:
            return existing
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        last_err = None
        for url in LLAMA_WIN_ZIP_CANDIDATES:
            try:
                zpath = BIN_DIR / "llama_cpp_win.zip"
                urlretrieve(url, str(zpath))
                with zipfile.ZipFile(zpath, "r") as zf:
                    zf.extractall(BIN_DIR)
                zpath.unlink(missing_ok=True)
                found = self._find_bin()
                if found:
                    return found
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(
            "Could not download llama.cpp Windows binary automatically.\n"
            "Manual fix:\n"
            "  1. Download a Windows llama.cpp release zip from:\n"
            "     https://github.com/ggerganov/llama.cpp/releases\n"
            "  2. Extract llama-cli.exe into:\n"
            f"     {BIN_DIR}\n"
            f"Last error: {last_err}"
        )

    def load(
        self,
        model_path: str | Path,
        n_ctx: int = 2048,
        temperature: float = 0.5,
        max_tokens: int = 512,
        **kwargs,
    ) -> str:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        self.ensure_binary()
        self.model_path = path
        self.n_ctx = int(n_ctx)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        return f"CLI engine ready: {path.name} via {self._find_bin().name}"

    def chat(self, system: str, history: list[dict], user_message: str) -> str:
        if not self.ready:
            raise RuntimeError("CLI engine not ready (model or binary missing)")

        # Build a simple chat prompt
        parts = [f"System: {system}\n"]
        for h in history[-8:]:
            role = "User" if h.get("role") == "user" else "Assistant"
            parts.append(f"{role}: {h.get('content', '')}\n")
        parts.append(f"User: {user_message}\nAssistant:")
        prompt = "".join(parts)

        bin_path = self._find_bin()
        cmd = [
            str(bin_path),
            "-m",
            str(self.model_path),
            "-p",
            prompt,
            "-n",
            str(self.max_tokens),
            "-c",
            str(self.n_ctx),
            "--temp",
            str(self.temperature),
            "-no-cnv",
        ]
        # Some builds use different flags; try primary then simplified
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(bin_path.parent),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0 and not proc.stdout:
                # retry minimal flags
                cmd2 = [
                    str(bin_path),
                    "-m",
                    str(self.model_path),
                    "-p",
                    prompt,
                    "-n",
                    str(self.max_tokens),
                ]
                proc = subprocess.run(
                    cmd2, capture_output=True, text=True, timeout=300, cwd=str(bin_path.parent)
                )
                out = (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Local model timed out")
        except FileNotFoundError as e:
            raise RuntimeError(f"Binary not executable: {e}") from e

        text = out.strip()
        # Prefer text after last "Assistant:" if present
        if "Assistant:" in text:
            text = text.split("Assistant:")[-1].strip()
        # strip noisy llama logs
        lines = [
            ln
            for ln in text.splitlines()
            if not ln.startswith(("llama_", "main:", "print_info", "load_"))
        ]
        cleaned = "\n".join(lines).strip()
        return cleaned or text[:2000]
