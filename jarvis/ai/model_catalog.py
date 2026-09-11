"""Replaceable open-weight GGUF catalog. Swap entries without rewriting JARVIS."""

# ids are stable keys used in settings.json
MODELS = {
    "tinyllama-1.1b-q4": {
        "name": "TinyLlama 1.1B Chat Q4_K_M",
        "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "url": (
            "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/"
            "resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        ),
        "approx_gb": 0.67,
        "context_default": 2048,
        "tier": "tiny",
        "notes": "Fastest; good for weak PCs. Offline after download.",
    },
    "qwen2.5-1.5b-q4": {
        "name": "Qwen2.5 1.5B Instruct Q4_K_M",
        "filename": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "url": (
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/"
            "resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
        ),
        "approx_gb": 1.1,
        "context_default": 4096,
        "tier": "small",
        "notes": "Strong small model for chat and light reasoning.",
    },
    "phi3-mini-q4": {
        "name": "Phi-3 Mini 4K Instruct Q4",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "url": (
            "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/"
            "resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        ),
        "approx_gb": 2.3,
        "context_default": 4096,
        "tier": "medium",
        "notes": "Higher quality; needs more RAM.",
    },
}


def list_models() -> list[dict]:
    return [{"id": k, **v} for k, v in MODELS.items()]


def get_model(model_id: str) -> dict | None:
    m = MODELS.get(model_id)
    if not m:
        return None
    return {"id": model_id, **m}
