"""
Local GGUF inference.

1) Prefer llama-cpp-python if installed (fast in-process).
2) Else use standalone llama.cpp CLI binary (works on Python 3.14, no compile).
"""
from __future__ import annotations

from pathlib import Path


class LocalEngine:
    def __init__(self):
        self._llm = None
        self._cli = None
        self.backend = None  # "python" | "cli"
        self.model_path: Path | None = None
        self.last_error: str | None = None
        self.n_ctx = 2048
        self.temperature = 0.5
        self.max_tokens = 512
        self.n_gpu_layers = 0

    @property
    def ready(self) -> bool:
        if self.backend == "python":
            return self._llm is not None
        if self.backend == "cli":
            return bool(self._cli and self._cli.ready)
        return False

    def unload(self):
        self._llm = None
        self._cli = None
        self.backend = None
        self.model_path = None

    def load(
        self,
        model_path: str | Path,
        n_ctx: int = 2048,
        n_threads: int | None = None,
        temperature: float = 0.5,
        max_tokens: int = 512,
        n_gpu_layers: int | None = None,
    ) -> str:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(f"Model file not found: {path}")

        self.n_ctx = int(n_ctx)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.n_gpu_layers = int(n_gpu_layers or 0)

        # --- try python binding ---
        try:
            from llama_cpp import Llama

            kwargs = {
                "model_path": str(path),
                "n_ctx": self.n_ctx,
                "verbose": False,
                "n_gpu_layers": self.n_gpu_layers,
            }
            if n_threads:
                kwargs["n_threads"] = int(n_threads)
            try:
                self._llm = Llama(**kwargs)
            except Exception:
                kwargs["n_gpu_layers"] = 0
                self.n_gpu_layers = 0
                self._llm = Llama(**kwargs)
            self.backend = "python"
            self.model_path = path
            self.last_error = None
            mode = f"GPU layers={self.n_gpu_layers}" if self.n_gpu_layers else "CPU"
            return f"Loaded local model (python): {path.name} (ctx={self.n_ctx}, {mode})"
        except ImportError:
            pass
        except Exception as e:
            self.last_error = str(e)

        # --- CLI fallback (Python 3.14 friendly) ---
        from jarvis.ai.cli_engine import CliEngine

        self._cli = CliEngine()
        msg = self._cli.load(
            path,
            n_ctx=self.n_ctx,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        self.backend = "cli"
        self.model_path = path
        self.last_error = None
        return msg + " (CLI backend — no llama-cpp-python required)"

    def chat(self, system: str, history: list[dict], user_message: str) -> str:
        if self.backend == "python" and self._llm is not None:
            return self._chat_python(system, history, user_message)
        if self.backend == "cli" and self._cli is not None:
            return self._cli.chat(system, history, user_message)
        raise RuntimeError("Local model not loaded yet — first-run install still going.")

    def _chat_python(self, system: str, history: list[dict], user_message: str) -> str:
        prompt = self._format_prompt(system, history, user_message)
        out = self._llm(
            prompt,
            max_tokens=min(int(self.max_tokens or 256), 320),
            temperature=0.7,
            stop=["<|im_end|>", "<|im_start|>", "</s>", "<|user|>", "<|system|>", "\nUser:", "\nTy:"],
        )
        text = (out["choices"][0].get("text") or "").strip()
        text = text.replace("<|assistant|>", "").replace("<|im_end|>", "").strip()
        return text

    def _format_prompt(self, system: str, history: list[dict], user_message: str) -> str:
        parts = [f"<|im_start|>system\n{system}<|im_end|>\n"]
        for h in history[-6:]:
            content = (h.get("content") or "").strip()
            if not content:
                continue
            role = "user" if h.get("role") == "user" else "assistant"
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
        parts.append(f"<|im_start|>user\n{user_message}<|im_end|>\n<|im_start|>assistant\n")
        return "".join(parts)
