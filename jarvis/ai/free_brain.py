"""No-key brain: Wikipedia, weather, maths, web search. Keeps JARVIS useful before a model loads."""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote

import requests

UA = {"User-Agent": "JARVIS/2.0 (personal assistant for Ty)"}


def _get(url: str, timeout: int = 12):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def try_math(message: str) -> str | None:
    raw = message.lower().strip().rstrip("?.!")
    raw = raw.replace("what's", "").replace("whats", "").replace("what is", "")
    raw = raw.replace("calculate", "").replace("compute", "").replace("equals", "")
    raw = raw.replace("x", "*").replace("times", "*").replace("multiplied by", "*")
    raw = raw.replace("divided by", "/").replace("plus", "+").replace("minus", "-")
    expr = re.sub(r"[^0-9+\-*/().%\s]", "", raw).strip()
    if not expr or not re.search(r"\d", expr) or not re.search(r"[+\-*/]", expr):
        return None
    if not re.fullmatch(r"[0-9+\-*/().%\s]+", expr):
        return None
    try:
        val = eval(expr, {"__builtins__": {}}, {})  # noqa: S307 — digits and operators only
    except Exception:
        return None
    if isinstance(val, float) and val == int(val):
        val = int(val)
    return f"{val}."


def try_weather(message: str) -> str | None:
    low = message.lower()
    if "weather" not in low and "forecast" not in low and "temperature" not in low:
        return None
    place = "London"
    m = re.search(r"(?:in|for|at)\s+([a-zA-Z][a-zA-Z\s]{1,40})$", message.strip("?.! "))
    if m:
        place = m.group(1).strip()
    try:
        r = _get(f"https://wttr.in/{quote(place)}?format=3")
        text = (r.text or "").strip()
        if text:
            return f"{text}."
    except Exception:
        return None
    return None


def try_wiki(message: str) -> str | None:
    q = message.strip()
    low = q.lower()
    for prefix in (
        "who is ", "who's ", "who was ",
        "what is ", "what's ", "whats ", "what was ",
        "what's a ", "what is a ",
        "tell me about ", "explain ", "define ", "definition of ",
    ):
        if low.startswith(prefix):
            q = q[len(prefix):].strip(" ?.!")
            break
    else:
        if len(q.split()) > 8:
            return None
    title = q.strip()
    if not title or len(title) < 2:
        return None
    try:
        r = _get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}")
        data = r.json()
        extract = (data.get("extract") or "").strip()
        if extract:
            return extract
    except Exception:
        return None
    return None


def try_search(web, message: str) -> str | None:
    try:
        return web.answer(message)
    except Exception:
        return None


def answer(message: str, web=None) -> str | None:
    for fn in (try_math, try_weather, try_wiki):
        try:
            hit = fn(message)
        except Exception:
            hit = None
        if hit:
            return hit
    if web is not None:
        looks_like_lookup = bool(
            re.search(
                r"\b(who|what|when|where|why|how|search|look up|news|latest|price|meaning)\b",
                message.lower(),
            )
            or message.endswith("?")
        )
        if looks_like_lookup:
            return try_search(web, message)
    return None


def ollama_up(base: str = "http://127.0.0.1:11434") -> bool:
    try:
        r = requests.get(base.rstrip("/") + "/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False
