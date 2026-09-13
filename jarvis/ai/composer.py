"""ChatGPT-style free composer: long answers, follow-ups, code, interpreter."""
from __future__ import annotations

import re
from datetime import datetime

from jarvis.coding.languages import detect, scaffold


def handle(brain, message: str) -> str | None:
    raw = (message or "").strip()
    if not raw:
        return None
    low = raw.lower().strip()

    hit = _followup(brain, raw, low)
    if hit:
        return hit
    hit = _interpreter(raw, low)
    if hit:
        return hit
    hit = _code_request(brain, raw, low)
    if hit:
        return hit
    hit = _longform(brain, raw, low)
    if hit:
        return hit
    hit = _explain_like(brain, raw, low)
    if hit:
        return hit
    return _general(brain, raw, low)


def _followup(brain, raw, low):
    last = (getattr(brain, "last_answer", None) or "").strip()
    topic = (getattr(brain, "last_user", None) or "").strip()
    if low in {"continue", "go on", "keep going", "more", "and then", "what else"}:
        if not last and not topic:
            return "Go on from what?"
        extra = _facts(brain, topic or last[:80])
        return f"{last[:400]}\n\nMore:\n{extra}"[:1800]
    if low in {"shorter", "make it shorter", "tl;dr", "tldr", "summarise that", "summarize that"}:
        if not last:
            return "Nothing to shorten yet."
        sents = re.split(r"(?<=[.!?])\s+", last)
        return " ".join(sents[:2]) if sents else last[:280]
    if low in {"longer", "make it longer", "expand", "expand on that", "go deeper"}:
        if not topic and not last:
            return "Expand on what?"
        return _compose_answer(brain, topic or last[:100], depth="long")
    if low in {"eli5", "explain like i'm 5", "simpler", "in simple terms", "dumb it down"}:
        base = last or topic
        if not base:
            return "What should I simplify?"
        return (
            "Simple version:\n"
            + " ".join(re.split(r"(?<=[.!?])\s+", last or _facts(brain, topic))[:3])
        )
    if low in {"in bullets", "as a list", "bullet points", "as bullets"}:
        if not last:
            return "Nothing to list yet."
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", last) if s.strip()]
        return "\n".join(f"- {s}" for s in sents[:8])
    if low in {"as a table", "in a table"}:
        if not last:
            return "Nothing to tabulate."
        lines = [ln.strip(" -•") for ln in last.splitlines() if ln.strip()][:8]
        out = ["| Item | Detail |", "|---|---|"]
        for ln in lines:
            if ":" in ln:
                a, b = ln.split(":", 1)
                out.append(f"| {a.strip()[:40]} | {b.strip()[:60]} |")
            else:
                out.append(f"| {ln[:40]} | |")
        return "\n".join(out)
    if low in {"examples", "give examples", "for example"}:
        q = topic or last[:80]
        facts = _facts(brain, q + " examples")
        return f"Examples related to {q}:\n{facts}"
    if low in {"try again", "regenerate", "redo that", "another version"}:
        if not topic:
            return "Redo what?"
        return _compose_answer(brain, topic, depth="long")
    m = re.match(r"^(?:what about|and|how about|also)\s+(.+)$", raw, re.I)
    if m and topic:
        nxt = m.group(1).strip().strip("?.!")
        return _compose_answer(brain, f"{topic} — {nxt}", depth="explain")
    return None


def _interpreter(raw, low):
    from jarvis.ai.free_brain import try_math

    hit = try_math(raw)
    if hit:
        return f"{hit}"
    m = re.match(r"^(?:calculate|compute)\s+(.+)$", raw, re.I)
    if m:
        hit = try_math(m.group(1))
        if hit:
            return hit
    return None


def _code_request(brain, raw, low):
    if not re.search(r"\b(code|function|class|script|program|snippet)\b", low):
        if not re.search(r"\b(python|javascript|html|sql|rust|java)\b", low):
            return None
        if not re.search(r"\b(write|make|create|generate|show me|how do i)\b", low):
            return None
    if re.match(r"^(open|close|find|search|tidy)\b", low):
        return None
    ext, lang = detect(raw)
    llm = None
    engine = getattr(brain, "engine", None)
    if engine and getattr(engine, "ready", False):
        try:
            llm = engine.chat(
                f"Write only {lang} code. Complete and runnable. No markdown.",
                [],
                raw,
            )
        except Exception:
            llm = None
    if llm and len(llm.strip()) > 40 and "capabilities are limited" not in llm.lower():
        code = llm.strip()
        if code.startswith("```"):
            code = code.split("\n", 1)[-1]
            code = code.rsplit("```", 1)[0]
        path = brain.coding.create_file(_slug(raw, ext), code.strip() + "\n")
        return f"Wrote {path.name}. Say 'run {path.name}' or 'send {path.name}'.\n\n{code[:1200]}"
    code = _smarter_scaffold(ext, lang, raw)
    path = brain.coding.create_file(_slug(raw, ext), code)
    return f"Wrote {path.name}. Say 'run {path.name}' or 'send {path.name}'.\n\n{code[:1200]}"


def _smarter_scaffold(ext, lang, job):
    j = job.lower()
    if ext == "py":
        if any(w in j for w in ("add", "sum", "calculator", "plus")):
            return (
                '"""Simple calculator."""\n\n'
                "def add(a, b):\n    return a + b\n\n"
                "def main():\n    a = float(input('a: '))\n    b = float(input('b: '))\n"
                "    print('sum', add(a, b))\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
        if "guess" in j:
            return (
                "import random\n\n"
                "n = random.randint(1, 10)\n"
                "g = int(input('Guess 1-10: '))\n"
                "print('Yes' if g == n else f'No, it was {n}')\n"
            )
        if any(w in j for w in ("flask", "api", "server")):
            return (
                "from flask import Flask, jsonify\napp = Flask(__name__)\n\n"
                "@app.get('/')\ndef home():\n    return jsonify(ok=True)\n\n"
                "if __name__ == '__main__':\n    app.run(debug=True)\n"
            )
    if ext == "html" or "page" in j or "website" in j:
        title = re.sub(r"[^a-zA-Z0-9 ]+", "", job)[:40] or "Page"
        return (
            "<!DOCTYPE html><html><head><meta charset=utf-8>"
            f"<title>{title}</title>"
            "<style>body{font-family:system-ui;margin:2rem auto;max-width:40rem}"
            "button{padding:.5rem 1rem}</style></head><body>"
            f"<h1>{title}</h1><p>Built by JARVIS.</p>"
            "<button onclick=\"alert('hi')\">Click</button>"
            "</body></html>\n"
        )
    return scaffold(ext, lang, job)


def _slug(job, ext):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+", job or "")
    slug = "_".join(w.lower() for w in words[:4]) or "snippet"
    return f"{slug[:40]}.{ext}"


def _longform(brain, raw, low):
    m = re.match(
        r"^(?:write|draft|compose|create)\s+(?:me\s+)?(?:an?\s+)?"
        r"(essay|article|story|poem|letter|email|bio|speech|script|blog|report|cover letter)"
        r"\s+(?:about|on|to|for)?\s*(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    kind, topic = m.group(1).lower(), m.group(2).strip()
    facts = _facts(brain, topic)
    name = (brain.s or {}).get("user_name", "Ty")
    if kind == "email":
        return (
            f"Subject: {topic[:70]}\n\n"
            f"Hey,\n\nQuick one about {topic}.\n\n{facts[:500]}\n\n"
            f"Yell if you want it changed.\n\nCheers,\n{name}"
        )
    if kind == "poem":
        return f"{topic.title()}\n\nQuiet work, late light,\n{topic.lower()} on the mind,\nstill going."
    if kind == "story":
        return (
            f"{topic.title()}\n\n"
            f"It started small. {facts[:280] or topic.capitalize() + '.'} "
            f"He didn't have a plan, just the next step. By the end of the day "
            f"it looked like something you could stand in."
        )
    paras = _paragraphs(topic, facts)
    return f"{kind.title()}: {topic}\n\n" + "\n\n".join(paras)


def _explain_like(brain, raw, low):
    m = re.match(
        r"^(?:explain|how does|how do|why (?:is|does|do)|what causes)\s+(.+)$",
        raw,
        re.I,
    )
    if not m:
        return None
    topic = m.group(1).strip().strip("?.!")
    return _compose_answer(brain, topic, depth="explain")


def _general(brain, raw, low):
    # Skip pure commands
    if re.match(r"^(open|close|find|tidy|lock|volume|run |send )\b", low):
        return None
    if len(raw.split()) < 3 and not raw.endswith("?"):
        return None
    return _compose_answer(brain, raw, depth="normal")


def _compose_answer(brain, topic: str, depth: str = "normal") -> str:
    facts = _facts(brain, topic)
    if not facts:
        facts = (
            f"I don't have a live page on “{topic}” right now. "
            "Say 'search the web for …' and I'll look again."
        )
    paras = _paragraphs(topic, facts, depth=depth)
    title = topic.rstrip("?.!").strip()
    if depth == "explain":
        return f"**{title}**\n\n" + "\n\n".join(paras)
    if depth == "long":
        return f"**{title}**\n\n" + "\n\n".join(paras) + "\n\nWant this as bullets, a table, or code?"
    return "\n\n".join(paras)


def _paragraphs(topic, facts, depth="normal"):
    clean = re.sub(r"\s+", " ", facts or "").strip()
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    if not sents:
        sents = [f"Here's a take on {topic}."]
    n = 8 if depth == "long" else 5 if depth == "explain" else 4
    chunks = []
    buf = []
    for s in sents[: n * 2]:
        buf.append(s)
        if len(buf) >= 2:
            chunks.append(" ".join(buf))
            buf = []
        if len(chunks) >= n:
            break
    if buf and len(chunks) < n:
        chunks.append(" ".join(buf))
    if depth in {"long", "explain"} and len(chunks) < 3:
        chunks.append(
            f"If you want, I can turn this into a list, a short script, or notes on your Desktop — say the word."
        )
    return chunks or sents[:3]


def _facts(brain, topic: str) -> str:
    topic = (topic or "").strip()
    if not topic:
        return ""
    bits = []
    try:
        from jarvis.ai.free_brain import try_wiki, try_weather, try_math

        for fn in (try_math, try_weather, try_wiki):
            hit = fn(topic)
            if _clean_fact(hit):
                bits.append(_clean_fact(hit))
                break
    except Exception:
        pass
    try:
        web = getattr(brain, "web", None)
        if web:
            hit = web.answer(topic, open_browser=False)
            c = _clean_fact(hit)
            if c:
                bits.append(c)
    except Exception:
        pass
    # de-dupe
    seen, out = set(), []
    for b in bits:
        k = b[:80]
        if k not in seen:
            seen.add(k)
            out.append(b)
    return "\n".join(out)[:2500]


def _clean_fact(hit) -> str:
    t = (hit or "").strip()
    if not t:
        return ""
    if t.startswith("<") or t.lower().startswith("<!doctype"):
        return ""
    return t
