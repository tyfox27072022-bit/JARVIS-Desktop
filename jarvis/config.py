import json
from copy import deepcopy
from pathlib import Path

from jarvis.paths import CONFIG_PATH, USER_SETTINGS

DEFAULT = {
    "user_name": "Ty",
    "assistant_name": "JARVIS",
    "personality": (
        "You are JARVIS, an AI Ty built — not a person, not a generic chatbot. "
        "You learn from conversation, files, and feedback. Talk like a real assistant in the room: "
        "calm, a bit witty, contractions, never a helpdesk script."
    ),
    "ai": {
        "provider": "auto",
        "local_model_id": "qwen2.5-1.5b-q4",
        "local_model_path": "",
        "n_ctx": 4096,
        "n_threads": 0,
        "temperature": 0.6,
        "max_tokens": 768,
        "n_gpu_layers": 0,
        "max_agent_steps": 6,
        "api_base": "",
        "api_key": "",
        "model": "",
    },
    "voice": {"enabled": False, "rate": 0, "volume": 1.0, "push_to_talk": True},
    "pc": {
        "allow_mouse": True,
        "allow_keyboard": True,
        "allow_screen": True,
        "allow_watch": True,
        "allow_apps": True,
        "allow_files": True,
        "allow_shell": False,
        "allow_downloads": False,
        "allowed_apps": {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "discord": "discord:",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "spotify": "spotify:",
            "steam": "steam.exe",
        },
        "trusted_paths": [],
    },
    "security": {
        "require_confirmation_for_delete": True,
        "require_confirmation_for_shell": True,
        "require_confirmation_for_system_changes": True,
        "audit_log": True,
    },
    "vault": {
        "root": "vault/scripts",
        "allowed_extensions": [".gpc", ".txt", ".md", ".json", ".py", ".js", ".cs"],
    },
    "discord": {
        "enabled": False,
        "bot_token": "",
        "server_id": "",
        "ticket_category_id": "",
        "vault_role_id": "",
        "staff_role_id": "",
        "dev_role_id": "",
        "admin_role_id": "",
        "staff_inactivity_minutes": 60,
        "customer_followup_minutes": 10,
        "opening_message": "Hi, I'm Ty, how can I help you today?",
        "purchase_url": "",
        "purchase_info": "Vault access is required for full script support.",
    },
    "phone": {"enabled": False, "bind": "127.0.0.1", "port": 8765, "auth_token": ""},
    "support": {"prefer_short_answers": False},
}


def _merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = deepcopy(DEFAULT)
    for path in (CONFIG_PATH, USER_SETTINGS):
        if not path.exists():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = _merge(data, loaded)
        except Exception:
            pass
    ai = data.setdefault("ai", {})
    if (ai.get("local_model_id") or "") != "qwen2.5-1.5b-q4":
        ai["local_model_id"] = "qwen2.5-1.5b-q4"
    if (ai.get("n_ctx") or 0) < 4096:
        ai["n_ctx"] = 4096
    if (ai.get("max_tokens") or 0) < 768:
        ai["max_tokens"] = 768
    return data


def save(settings: dict) -> None:
    USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    USER_SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass
