"""Optional cloud providers. Fast path is xAI Grok when an API key is set."""
from __future__ import annotations

import requests

GROK_MODELS = {
    "fast": "grok-4.3",
    "jarvis": "grok-4.5",
    "sharp": "grok-4.6",
    "grok-4.3": "grok-4.3",
    "grok-4.5": "grok-4.5",
    "grok-4.6": "grok-4.6",
}


def resolve_model(ai: dict) -> str:
    raw = (ai.get("model") or ai.get("local_model_id") or "jarvis").strip()
    return GROK_MODELS.get(raw.lower(), raw or "grok-4.5")


def cloud_chat(settings: dict, system: str, history: list, message: str) -> str:
    ai = settings.get("ai") or {}
    provider = (ai.get("provider") or "").lower()
    base = (ai.get("api_base") or "").rstrip("/")
    key = (ai.get("api_key") or "").strip()
    model = resolve_model(ai)
    msgs = [{"role": "system", "content": system}] + list(history[-12:]) + [
        {"role": "user", "content": message}
    ]
    if provider == "ollama":
        base = base or "http://127.0.0.1:11434"
        r = requests.post(
            base + "/api/chat",
            json={"model": model if model not in GROK_MODELS.values() else "llama3.2", "messages": msgs, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    if provider in ("xai", "grok", "") or "x.ai" in base:
        base = base or "https://api.x.ai/v1"
        model = resolve_model(ai)
    else:
        base = base or "https://api.openai.com/v1"

    if not key:
        raise RuntimeError("API key empty — paste it in Settings.")
    r = requests.post(
        base + "/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": msgs,
            "temperature": float(ai.get("temperature", 0.7)),
            "max_tokens": int(ai.get("max_tokens", 700)),
        },
        timeout=90,
    )
    r.raise_for_status()
    return (r.json()["choices"][0]["message"].get("content") or "").strip()
