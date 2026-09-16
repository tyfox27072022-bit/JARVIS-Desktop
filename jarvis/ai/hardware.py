"""Detect local hardware and recommend a GGUF model size."""
from __future__ import annotations

import platform
import shutil


def probe() -> dict:
    info = {
        "os": platform.system(),
        "arch": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "ram_gb": None,
        "gpu": "unknown",
        "recommended_tier": "tiny",
        "recommended_model_id": "qwen2.5-1.5b-q4",
        "notes": [],
    }
    try:
        import psutil

        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        info["notes"].append("Could not read RAM; assuming low-memory tier.")

    # Very light GPU hint (Windows)
    gpu = "cpu"
    if platform.system() == "Windows":
        try:
            import subprocess

            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
            lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip().lower() != "name"]
            if lines:
                info["gpu"] = lines[0]
                low = lines[0].lower()
                if any(x in low for x in ("nvidia", "rtx", "gtx", "radeon", "amd")):
                    gpu = "gpu"
        except Exception:
            pass
    info["gpu_mode"] = gpu

    ram = info["ram_gb"] or 8
    info["recommended_tier"] = "medium"
    info["recommended_model_id"] = "qwen2.5-1.5b-q4"
    info["notes"].append("Brain: Qwen2.5 1.5B only (~1 GB).")
    if ram < 4:
        info["notes"].append("Low RAM — Qwen may be slow but it's still the model we use.")
    if gpu == "gpu":
        info["notes"].append("Discrete GPU detected — llama-cpp may use it if built with GPU support.")

    return info


def format_report(info: dict | None = None) -> str:
    info = info or probe()
    lines = [
        f"OS: {info['os']} ({info['arch']})",
        f"CPU: {info['cpu']}",
        f"RAM: {info['ram_gb']} GB" if info["ram_gb"] else "RAM: unknown",
        f"GPU: {info.get('gpu')}",
        f"Recommended model: {info['recommended_model_id']} ({info['recommended_tier']})",
    ]
    lines.extend(info.get("notes") or [])
    return "\n".join(lines)
