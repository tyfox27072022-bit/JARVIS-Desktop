"""Free open-weight GGUF models JARVIS installs itself. No API keys."""

MODELS = {
    "qwen2.5-1.5b-q4": {
        "name": "Qwen2.5 1.5B Instruct Q4_K_M",
        "filename": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "url": (
            "https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/"
            "resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
        ),
        "approx_gb": 1.0,
        "context_default": 4096,
        "tier": "medium",
        "notes": "Default brain. Free Qwen chat model, ~1 GB.",
        "template": "chatml",
    },
    "smollm2-360m-q4": {
        "name": "SmolLM2 360M Instruct",
        "filename": "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        "url": (
            "https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/"
            "resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf"
        ),
        "approx_gb": 0.27,
        "context_default": 2048,
        "tier": "tiny",
        "notes": "Fallback if Qwen cannot download.",
        "template": "chatml",
    },
    "tinyllama-1.1b-q4": {
        "name": "TinyLlama 1.1B Chat Q4_K_M",
        "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "url": (
            "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/"
            "resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        ),
        "approx_gb": 0.67,
        "context_default": 2048,
        "tier": "small",
        "notes": "Last-resort fallback.",
        "template": "tinyllama",
    },
}

DEFAULT_ORDER = ["qwen2.5-1.5b-q4", "smollm2-360m-q4", "tinyllama-1.1b-q4"]
DEFAULT_ID = "qwen2.5-1.5b-q4"


def list_models() -> list[dict]:
    return [{"id": k, **v} for k, v in MODELS.items()]


def get_model(model_id: str) -> dict | None:
    m = MODELS.get(model_id)
    if not m:
        return None
    return {"id": model_id, **m}
