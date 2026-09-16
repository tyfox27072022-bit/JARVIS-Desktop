"""JARVIS runs one local brain: Qwen2.5 1.5B. Free, no API keys."""

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
        "notes": "The only local brain. Free Qwen chat model, ~1 GB.",
        "template": "chatml",
    },
}

DEFAULT_ORDER = ["qwen2.5-1.5b-q4"]
DEFAULT_ID = "qwen2.5-1.5b-q4"


def list_models() -> list[dict]:
    return [{"id": k, **v} for k, v in MODELS.items()]


def get_model(model_id: str) -> dict | None:
    m = MODELS.get(model_id)
    if not m:
        return None
    return {"id": model_id, **m}
