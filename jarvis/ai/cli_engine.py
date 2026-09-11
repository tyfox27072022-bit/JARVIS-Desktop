"""
Local inference via standalone llama.cpp CLI (no C++ compile, works on Python 3.14).

Downloads a Windows binary into data/bin/ and runs GGUF models offline.
"""
from __future__ import annotations

import ssl
import subprocess
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from jarvis.paths import DATA

BIN_DIR = DATA / "bin"
UA = "Mozilla/5.0 JARVIS/2.0"

LLAMA_WIN_ZIP_CANDIDATES = [
    "https://github.com/ggml-org/llama.cpp/releases/download/b6316/llama-b6316-bin-win-cpu-x64.zip",
    "https://github.com/ggml-org/llama.cpp/releases/download/b5095/llama-b5095-bin-win-avx2-x64.zip",
    "https://github.com/ggerganov/llama.cpp/releases/download/b5217/llama-b5217-bin-win-avx2-x64.zip",
]


def _download(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urlopen(req, context=ctx, timeout=120) as src, open(dest, "wb") as out:
        while True:
            chunk = src.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)


class CliEngine:
    def __init__(self):
        self.model_path: Path | None = None
        self.bin_path: Path | None = None
        self.n_ctx = 2048
        self.temperature = 0.6
        self.max_tokens = 256
        self.last_error: str | None = None

    @property
    def ready(self) -> bool:
        return bool(self.model_path and self.model_path.is_file() and self._find_bin())

    def _find_bin(self) -> Path | None:
        if self.bin_path and self.bin_path.is_file():
            return self.bin_path
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        names = ("llama-cli.exe", "llama-completion.exe", "main.exe", "llama.exe", "llama-cli", "main")
        for name in names:
            p = BIN_DIR / name
            if p.is_file():
                self.bin_path = p
                return p
        for name in names:
            for p in BIN_DIR.rglob(name):
                if p.is_file():
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
                if progress_cb:
                    progress_cb("Installing local engine…")
                zpath = BIN_DIR / "llama_cpp_win.zip"
                _download(url, zpath)
                with zipfile.ZipFile(zpath, "r") as zf:
                    zf.extractall(BIN_DIR)
                zpath.unlink(missing_ok=True)
                found = self._find_bin()
                if found:
                    return found
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"Could not install llama.cpp automatically: {last_err}")

    def load(
        self,
        model_path: str | Path,
        n_ctx: int = 2048,
        temperature: float = 0.6,
        max_tokens: int = 256,
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

        parts = [f"<|im_start|>system\n{system}<|im_end|>\n"]
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "assistant"
            parts.append(f"<|im_start|>{role}\n{h.get('content', '')}<|im_end|>\n")
        parts.append(f"<|im_start|>user\n{user_message}<|im_end|>\n<|im_start|>assistant\n")
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
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(bin_path.parent),
            )
            out = (proc.stdout or "")
            if proc.returncode != 0 and not proc.stdout:
                proc = subprocess.run(
                    [str(bin_path), "-m", str(self.model_path), "-p", prompt, "-n", str(self.max_tokens)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(bin_path.parent),
                )
                out = proc.stdout or ""
        except subprocess.TimeoutExpired:
            raise RuntimeError("Local model timed out")
        text = (out or "").strip()
        if "<|im_start|>assistant" in text:
            text = text.split("<|im_start|>assistant")[-1]
        text = text.replace("<|im_end|>", "").strip()
        if "Assistant:" in text:
            text = text.split("Assistant:")[-1].strip()
        lines = [
            ln
            for ln in text.splitlines()
            if not ln.startswith(("llama_", "main:", "print_info", "load_", "ggml_"))
        ]
        cleaned = "\n".join(lines).strip()
        return cleaned or text[:2000]
