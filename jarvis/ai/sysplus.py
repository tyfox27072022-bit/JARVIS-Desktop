"""Processes, IP, ping — extra PC intel."""
from __future__ import annotations

import re
import socket
import subprocess
import sys

try:
    import psutil
except Exception:
    psutil = None


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    if low in {"my ip", "what's my ip", "whats my ip", "ip address"}:
        return _ip()
    if low in {"top processes", "what's running", "whats running", "process list", "task list"}:
        return _procs()
    m = re.match(r"^ping\s+(\S+)$", low)
    if m:
        return _ping(m.group(1))
    m = re.match(r"^kill process\s+(.+)$", raw, re.I)
    if m:
        return _kill(m.group(1).strip())
    return None


def _ip() -> str:
    bits = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        bits.append("Local " + s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        import requests

        r = requests.get("https://api.ipify.org", timeout=8)
        if r.ok:
            bits.append("Public " + r.text.strip())
    except Exception:
        pass
    return " · ".join(bits) or "Couldn't get an IP."


def _procs() -> str:
    if psutil is None:
        return "Need psutil for process list."
    rows = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            mem = (info.get("memory_info").rss / 1_000_000) if info.get("memory_info") else 0
            rows.append((info.get("cpu_percent") or 0, mem, info.get("name") or "?"))
        except Exception:
            continue
    rows.sort(reverse=True)
    lines = ["Top processes:"]
    for cpu, mem, name in rows[:12]:
        lines.append(f"  {name}  cpu {cpu:.0f}%  ram {mem:.0f} MB")
    return "\n".join(lines)


def _ping(host: str) -> str:
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    n = "-n" if sys.platform == "win32" else "-c"
    try:
        out = subprocess.check_output(["ping", n, "2", host], text=True, timeout=10, stderr=subprocess.STDOUT)
        return "\n".join(out.splitlines()[-6:])
    except Exception as e:
        return f"Ping failed: {e}"


def _kill(name: str) -> str:
    if psutil is None:
        return f"Say 'close {name}' and I'll taskkill it."
    needle = name.lower().replace(".exe", "")
    killed = []
    for p in psutil.process_iter(["name", "pid"]):
        try:
            n = (p.info.get("name") or "").lower()
            if needle in n:
                p.terminate()
                killed.append(p.info.get("name"))
        except Exception:
            continue
    if killed:
        return "Stopped: " + ", ".join(sorted(set(killed))[:8])
    return f"No process matching {name}."
