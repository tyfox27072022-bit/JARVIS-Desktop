"""Learn Ty's talking style from every message (typed or spoken) and match it."""
from __future__ import annotations

import re
from datetime import datetime

CASUAL = {
    "yeah", "yea", "yep", "nah", "nope", "gonna", "wanna", "gotta", "ain't",
    "innit", "mate", "bro", "bruh", "lol", "lmao", "idk", "tbh", "imo",
    "kinda", "sorta", "dunno", "cheers", "ta", "alright", "ok", "okay",
    "sup", "yo", "hiya", "cheers",
}
CONTRACTIONS = (
    "i'm", "i've", "i'd", "i'll", "don't", "doesn't", "didn't", "can't",
    "won't", "isn't", "aren't", "wasn't", "it's", "that's", "there's",
    "you're", "we're", "they're", "let's", "gonna", "wanna", "gotta",
)
FORMAL = {
    "however", "therefore", "regarding", "furthermore", "please", "kindly",
    "would you", "could you please",
}


def analyze(text: str) -> dict:
    raw = (text or "").strip()
    words = re.findall(r"[A-Za-z']+", raw.lower())
    n = max(len(words), 1)
    lowers = sum(1 for c in raw if c.isalpha() and c.islower())
    uppers = sum(1 for c in raw if c.isalpha() and c.isupper())
    alpha = max(lowers + uppers, 1)
    return {
        "chars": len(raw),
        "words": len(words),
        "avg_word": sum(len(w) for w in words) / n,
        "questions": raw.count("?"),
        "bangs": raw.count("!"),
        "casual": sum(1 for w in words if w in CASUAL),
        "contractions": sum(1 for w in words if w in CONTRACTIONS),
        "formal": sum(1 for w in words if w in FORMAL or " ".join(words).find(w) >= 0 and w in FORMAL),
        "lowercase_ratio": lowers / alpha,
        "has_period": "." in raw,
        "fragments": 1 if not raw.endswith((".", "?", "!")) and len(words) < 8 else 0,
        "sample": raw[:180],
    }


def merge_profile(style: dict, text: str) -> dict:
    stats = analyze(text)
    if not (text or "").strip():
        return style
    acc = style.setdefault("acc", {"n": 0, "chars": 0, "words": 0, "casual": 0, "contractions": 0, "questions": 0, "bangs": 0, "lower": 0.0, "fragments": 0})
    acc["n"] += 1
    acc["chars"] += stats["chars"]
    acc["words"] += stats["words"]
    acc["casual"] += stats["casual"]
    acc["contractions"] += stats["contractions"]
    acc["questions"] += stats["questions"]
    acc["bangs"] += stats["bangs"]
    acc["lower"] += stats["lowercase_ratio"]
    acc["fragments"] += stats["fragments"]
    n = max(acc["n"], 1)
    avg_len = acc["chars"] / n
    detail = "short" if avg_len < 40 else ("detailed" if avg_len > 140 else "medium")
    casual_rate = acc["casual"] / n
    formality = "casual" if casual_rate >= 0.15 or acc["contractions"] / n >= 0.2 else ("formal" if casual_rate == 0 and avg_len > 80 else "relaxed")
    if acc["lower"] / n > 0.85 and acc["fragments"] / n > 0.4:
        formality = "casual"
    examples = style.get("examples") or []
    sample = stats["sample"]
    if sample and sample not in examples:
        examples.append(sample)
    style["examples"] = examples[-16:]
    style["traits"] = {
        "greeting_style": "short" if avg_len < 40 else "normal",
        "detail_level": detail,
        "tone": formality,
        "contractions": acc["contractions"] / n >= 0.12,
        "lowercase": acc["lower"] / n > 0.88,
        "avg_chars": round(avg_len, 1),
        "samples_seen": n,
        "abbreviations": sorted({w for w in re.findall(r"\b[a-z]{2,5}\b", " ".join(examples).lower()) if w in CASUAL})[:12],
    }
    bits = [
        f"Ty talks {formality}, {detail} messages (avg {int(avg_len)} chars).",
    ]
    if style["traits"]["contractions"]:
        bits.append("He uses contractions (I'm, don't, gonna).")
    if style["traits"]["abbreviations"]:
        bits.append("Slang/markers: " + ", ".join(style["traits"]["abbreviations"][:6]) + ".")
    if style["examples"]:
        bits.append("Sound like this: “" + style["examples"][-1][:80] + "”")
    bits.append("Match his length and wording. Don't go stiff or corporate.")
    style["summary"] = " ".join(bits)
    style["updated"] = datetime.now().isoformat(timespec="seconds")
    return style


def prompt_block(style: dict) -> str:
    summary = (style or {}).get("summary") or ""
    traits = (style or {}).get("traits") or {}
    examples = (style or {}).get("examples") or []
    if not summary and not examples:
        return "Match Ty's tone as you learn it — currently unknown."
    lines = ["How Ty talks (match this):"]
    if summary:
        lines.append(summary)
    if examples:
        lines.append("Recent things he said:")
        for e in examples[-4:]:
            lines.append(f"- {e}")
    detail = traits.get("detail_level") or "medium"
    if detail == "short":
        lines.append("Keep replies to 1–2 short sentences unless he asks for more.")
    return "\n".join(lines)


def mirror(reply: str, style: dict) -> str:
    text = (reply or "").strip()
    if not text:
        return text
    traits = (style or {}).get("traits") or {}
    if not traits:
        return text
    # Don't restyle tool/file/search dumps
    if any(s in text for s in ("Here's what I found", "Found ", "Opened ", "CPU ", "• (", "match(es)")):
        return text
    if traits.get("detail_level") == "short":
        parts = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(parts[:2]).strip()
        if len(text) > 220:
            text = text[:217].rsplit(" ", 1)[0] + "."
    swaps = [
        (r"\bI am\b", "I'm"),
        (r"\bdo not\b", "don't"),
        (r"\bcannot\b", "can't"),
        (r"\bit is\b", "it's"),
        (r"\bthat is\b", "that's"),
        (r"\byou are\b", "you're"),
        (r"\bAlright\b", "Alright"),
    ]
    if traits.get("contractions") or traits.get("tone") == "casual":
        for a, b in swaps:
            text = re.sub(a, b, text)
        text = text.replace("Certainly.", "Yep.").replace("Of course.", "Yeah.")
        text = text.replace("I shall ", "I'll ").replace("I will ", "I'll ")
    return text
