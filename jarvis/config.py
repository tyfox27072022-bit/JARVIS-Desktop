import json
from copy import deepcopy
from pathlib import Path

from jarvis.paths import CONFIG_PATH

DEFAULT = {
    "user_name": "Ty",
    "assistant_name": "JARVIS",
    "personality": (
        "Talk like a real person. Intelligent, calm, helpful, a little witty. "
        "British-assistant manner: composed, not stiff. Use contractions."
    ),
    "ai": {
        "provider": "auto",
        "local_model_id": "smollm2-360m-q4",
        "local_model_path": "",
        "n_ctx": 2048,
        "n_threads": 0,
        "temperature": 0.5,
        "max_tokens": 512,
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
    if not CONFIG_PATH.exists():
        save(DEFAULT)
        return deepcopy(DEFAULT)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid")
        return _merge(DEFAULT, data)
    except Exception:
        save(DEFAULT)
        return deepcopy(DEFAULT)


def save(settings: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
