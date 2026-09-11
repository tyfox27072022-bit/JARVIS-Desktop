"""ChatGPT-style jobs, free: write, translate, summarise, explain, plan, images."""
from __future__ import annotations

import os
import re
import webbrowser
from pathlib import Path
from urllib.parse import quote

import requests

UA = {"User-Agent": "Mozilla/5.0 JARVIS/2.0"}

LANGS = {
    "spanish": "es", "es": "es", "french": "fr", "fr": "fr", "german": "de", "de": "de",
    "italian": "it", "it": "it", "portuguese": "pt", "pt": "pt", "dutch": "nl",
    "polish": "pl", "russian": "ru", "japanese": "ja", "jp": "ja", "chinese": "zh",
    "korean": "ko", "arabic": "ar", "hindi": "hi", "turkish": "tr", "swedish": "sv",
    "norwegian": "no", "danish": "da", "finnish": "fi", "greek": "el", "czech": "cs",
    "romanian": "ro", "hungarian": "hu", "thai": "th", "vietnamese": "vi",
    "english": "en", "en": "en", "welsh": "cy", "irish": "ga", "ukrainian": "uk",
}


def _llm(brain, system: str, user: str) -> str | None:
    engine = getattr(brain, "engine", None)
    if not engine or not getattr(engine, "ready", False):
        return None
    try:
        out = engine.chat(system, [], user)
        out = (out or "").strip()
        if len(out) > 40 and "capabilities are limited" not in out.lower():
            return out
    except Exception:
        return None
    return None


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    if not low:
        return None
    for fn in (
        _image,
        _translate,
        _summarize,
        _rewrite,
        _write,
        _plan,
        _brainstorm,
        _compare,
        _explain,
        _define,
        _make,
    ):
        hit = fn(brain, raw, low)
        if hit:
            return hit
    return None


def _image(brain, raw, low):
    m = re.match(
        r"^(?:draw|generate|make|create|paint)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|art|illustration)\s+(?:of\s+|for\s+)?(.+)$",
        raw,
        re.I,
    )
    if not m:
        m = re.match(r"^(?:imagine|picture of)\s+(.+)$", raw, re.I)
    if not m:
        return None
    prompt = m.group(1).strip()
    url = "https://image.pollinations.ai/prompt/" + quote(prompt) + "?nologo=true"
    dest = Path.home() / "Desktop" / ("jarvis_" + re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:40] + ".jpg")
    try:
        r = requests.get(url, headers=UA, timeout=90)
        if r.ok and r.content and len(r.content) > 2000:
            dest.write_bytes(r.content)
            if os.name == "nt":
                os.startfile(str(dest))  # type: ignore[attr-defined]
            return f"Image saved to {dest}"
    except Exception:
        pass
    try:
        webbrowser.open(url)
    except Exception:
        pass
    return f"Opened a free image generator for: {prompt}"


def _translate(brain, raw, low):
    m = re.search(
        r"translate\s+(?:this\s+)?(?:to|into)\s+([a-zA-Z]+)\s*[:\-]?\s*(.+)$",
        raw,
        re.I,
    )
    if not m:
        m = re.search(r"translate\s+(.+?)\s+to\s+([a-zA-Z]+)\s*$", raw, re.I)
        if m:
            text, lang = m.group(1), m.group(2)
        else:
            return None
    else:
        lang, text = m.group(1), m.group(2)
    code = LANGS.get(lang.lower())
    if not code:
        return f"I don't have a code for {lang}. Try Spanish, French, German, Japanese…"
    llm = _llm(brain, f"Translate to {lang}. Only the translation.", text)
    if llm:
        return llm
    for url, params in (
        (
            "https://api.mymemory.translated.net/get",
            {"q": text, "langpair": f"en|{code}"},
        ),
        (
            "https://translate.googleapis.com/translate_a/single",
            {"client": "gtx", "sl": "auto", "tl": code, "dt": "t", "q": text},
        ),
    ):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=15)
            if not r.ok:
                continue
            data = r.json()
            if isinstance(data, dict):
                t = (data.get("responseData") or {}).get("translatedText") or ""
                if t and "MYMEMORY WARNING" not in t:
                    return t
            elif isinstance(data, list) and data and data[0]:
                bits = [row[0] for row in data[0] if row and row[0]]
                if bits:
                    return "".join(bits)
        except Exception:
            continue
    webbrowser.open(
        "https://translate.google.com/?sl=auto&tl=" + code + "&text=" + quote(text) + "&op=translate"
    )
    return f"Opened Google Translate to {lang}."


def _summarize(brain, raw, low):
    if not re.search(r"\b(summarise|summarize|tldr|tl;dr|sum up)\b", low):
        return None
    url_m = re.search(r"https?://\S+", raw)
    text = ""
    if url_m:
        try:
            text = brain.web.fetch(url_m.group(0), max_chars=4000)
        except Exception as e:
            return f"Couldn't fetch that page: {e}"
    else:
        text = re.sub(r"^(?:please\s+)?(?:summarise|summarize|tldr|sum up)\s+(?:this\s+)?", "", raw, flags=re.I).strip()
        if len(text) < 40:
            # maybe a file name
            try:
                hits = brain.pc.find_named(text)
                return "Point me at a URL or paste the text. I can also find files:\n" + hits
            except Exception:
                return "Paste the text or a link and I'll summarise it."
    llm = _llm(brain, "Summarise clearly in 5 short bullets. No fluff.", text[:3500])
    if llm:
        return llm
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pick = sentences[:6]
    return "Summary:\n- " + "\n- ".join(s.strip() for s in pick if s.strip())[:1500]


def _rewrite(brain, raw, low):
    m = re.match(
        r"^(?:rewrite|rephrase|improve|fix grammar|make (?:this )?(?:better|shorter|longer|formal|casual))\s*[:\-]?\s*(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    text = m.group(1).strip()
    how = "clearer"
    if "short" in low:
        how = "shorter"
    elif "formal" in low:
        how = "more formal"
    elif "casual" in low:
        how = "more casual"
    llm = _llm(brain, f"Rewrite {how}. Keep the meaning. Output only the rewrite.", text)
    if llm:
        return llm
    return text  # fallback: at least echo cleaned


def _write(brain, raw, low):
    m = re.match(
        r"^(?:write|draft|compose)\s+(?:me\s+)?(?:an?\s+)?(email|essay|story|poem|letter|bio|speech|caption|review|list|paragraph|intro|cover letter|script)\s+(?:about\s+|on\s+|to\s+|for\s+)?(.+)$",
        raw,
        re.I,
    )
    if not m:
        m = re.match(r"^(?:write|draft|compose)\s+(?:me\s+)?(.+)$", raw, re.I)
        if not m:
            return None
        kind, topic = "piece", m.group(1).strip()
        if re.search(r"\b(code|program|function|html|python|javascript)\b", kind + topic.lower()):
            return None  # coding handles it
    else:
        kind, topic = m.group(1).lower(), m.group(2).strip()
        if re.search(r"\b(code|program|function|html|python|javascript)\b", (kind + " " + topic).lower()):
            return None
    llm = _llm(
        brain,
        f"You write like a helpful assistant for Ty. Produce a complete {kind} about: {topic}. "
        "No preamble. Match a natural spoken English tone.",
        f"Write a {kind} about {topic}.",
    )
    if llm:
        return llm
    facts = ""
    try:
        facts = brain.web.answer(topic, open_browser=False)
    except Exception:
        facts = ""
    name = (brain.s or {}).get("user_name", "Ty")
    if kind == "email":
        return (
            f"Subject: {topic[:70]}\n\n"
            f"Hey,\n\nQuick one about {topic}. "
            f"Yell if you want it changed.\n\nCheers,\n{name}"
        )
    if kind == "list":
        return "Here's a starter list:\n- " + "\n- ".join(
            [s.strip(" -•") for s in (facts or topic).split("\n") if s.strip()][:8] or [topic]
        )
    if kind == "poem":
        return f"{topic.title()}\n\nQuiet work, late light,\n{topic.lower()} on the mind,\nstill going."
    body = facts or f"Here's a draft on {topic}."
    return f"{kind.title()} — {topic}\n\n{body[:1200]}"


def _plan(brain, raw, low):
    m = re.match(
        r"^(?:plan|how do i|how to|steps to|help me)\s+(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    if low.startswith("how are"):
        return None
    job = m.group(1).strip()
    llm = _llm(brain, "Give a clear numbered plan. 6-10 steps. Practical.", f"Plan: {job}")
    if llm:
        return llm
    try:
        facts = brain.web.answer("how to " + job, open_browser=False)
    except Exception:
        facts = ""
    return f"Plan: {job}\n1. Get clear on the outcome.\n2. Gather what you need.\n3. Do the first small version.\n4. Check it.\n5. Repeat until it's right.\n\n{facts[:800]}"


def _brainstorm(brain, raw, low):
    m = re.match(r"^(?:brainstorm|ideas? for|give me ideas(?:\s+for)?|suggest)\s+(.+)$", raw, re.I)
    if not m:
        return None
    topic = m.group(1).strip()
    llm = _llm(brain, "Brainstorm 8 short, useful ideas. Numbered.", topic)
    if llm:
        return llm
    try:
        facts = brain.web.answer(topic + " ideas", open_browser=False)
    except Exception:
        facts = topic
    return f"Ideas for {topic}:\n{facts[:1200]}"


def _compare(brain, raw, low):
    m = re.search(r"compare\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+)$", raw, re.I)
    if not m:
        if "pros and cons" in low:
            topic = re.sub(r".*pros and cons (?:of\s+)?", "", raw, flags=re.I)
            llm = _llm(brain, "Pros and cons. Two short lists.", topic)
            if llm:
                return llm
            return f"Pros and cons of {topic}:\nPros:\n- \nCons:\n- "
        return None
    a, b = m.group(1).strip(), m.group(2).strip()
    llm = _llm(brain, "Compare fairly in a short table-like list.", f"{a} vs {b}")
    if llm:
        return llm
    return f"{a} vs {b}\n- {a}: look up current details\n- {b}: look up current details\nSay 'search the web for {a} vs {b}' for sources."


def _explain(brain, raw, low):
    m = re.match(r"^(?:explain|what does .+ mean|eli5|in simple terms)\s*(.+)$", raw, re.I)
    if not m and not low.startswith("explain"):
        return None
    topic = m.group(1).strip() if m else raw
    topic = re.sub(r"^(explain|eli5|in simple terms)\s+", "", topic, flags=re.I)
    llm = _llm(brain, "Explain simply, like to a smart friend. Short paragraphs.", topic)
    if llm:
        return llm
    try:
        return brain.web.answer(topic, open_browser=False)
    except Exception:
        return None


def _define(brain, raw, low):
    m = re.match(r"^(?:define|definition of|what is(?: a| an)?|what's a)\s+(.+)$", raw, re.I)
    if not m:
        return None
    topic = m.group(1).strip().strip("?.!")
    if len(topic.split()) > 12:
        return None
    llm = _llm(brain, "One-paragraph definition, then why it matters.", topic)
    if llm:
        return llm
    try:
        return brain.web.answer("what is " + topic, open_browser=False)
    except Exception:
        return None


def _desktop_write(name: str, content: str) -> Path:
    dest = Path.home() / "Desktop"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / name
    path.write_text(content, encoding="utf-8")
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass
    return path


def _make(brain, raw, low):
    m = re.match(r"^(?:make|create|build|put together)\s+(?:me\s+)?(?:an?\s+)?(.+)$", raw, re.I)
    if not m:
        return None
    what = m.group(1).strip()
    wlow = what.lower()
    if re.search(r"\b(image|picture|photo|art|illustration)\b", wlow):
        return None
    if re.search(r"\b(script|program|function|python|javascript|html page|code)\b", wlow):
        return None
    if wlow.startswith("folder"):
        name = re.sub(r"^folder\s*(?:called|named)?\s*", "", what, flags=re.I).strip() or "JARVIS"
        name = re.sub(r"[^\w \-]+", "", name)[:40] or "JARVIS"
        p = Path.home() / "Desktop" / name
        p.mkdir(parents=True, exist_ok=True)
        return f"Made the folder {p}"
    facts = ""
    topic = re.sub(r"^(?:a |an |the )", "", what, flags=re.I)
    try:
        facts = brain.web.answer(topic, open_browser=False) or ""
    except Exception:
        facts = ""
    llm = _llm(brain, "Make the thing they asked for. Complete, usable, no preamble.", what)
    body = llm or facts or what
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:32] or "jarvis"
    if "list" in wlow:
        path = _desktop_write(f"{slug}.txt", body if body.startswith("•") or "\n-" in body else "• " + "\n• ".join(
            [ln.strip(" -•") for ln in body.split("\n") if ln.strip()][:20] or [topic]
        ))
        return f"Made the list and put it on your Desktop:\n{path}\n\n{body[:800]}"
    if any(k in wlow for k in ("website", "web page", "webpage", "landing")):
        html = (
            "<!DOCTYPE html><html><head><meta charset=utf-8>"
            f"<title>{topic}</title>"
            "<style>body{font-family:sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem}</style>"
            f"</head><body><h1>{topic}</h1><p>{body[:800]}</p></body></html>"
        )
        path = _desktop_write(f"{slug}.html", html)
        return f"Made a page and opened it:\n{path}"
    path = _desktop_write(f"{slug}.txt", f"{topic}\n\n{body[:4000]}")
    return f"Made it and saved it on your Desktop:\n{path}"

