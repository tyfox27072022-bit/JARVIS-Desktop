"""Pull lasting facts out of what Ty says so JARVIS actually learns."""
from __future__ import annotations

import re

SKIP = {
    "hi", "hey", "hello", "yo", "sup", "hiya", "thanks", "thank you", "cheers",
    "ok", "okay", "yes", "no", "yep", "nope", "clear chat", "help",
}

# (regex, category, template with groups)
PATTERNS = [
    (r"\bmy name is ([a-zA-Z][\w\-']{1,30})\b", "facts", "Name is {0}"),
    (r"\bcall me ([a-zA-Z][\w\-']{1,30})\b", "facts", "Prefers to be called {0}"),
    (r"\bi(?:'m| am) (\d{1,3}) years old\b", "facts", "Age: {0}"),
    (r"\bi live in ([^.,!?]{2,60})", "facts", "Lives in {0}"),
    (r"\bi work (?:at|for|as) ([^.,!?]{2,60})", "facts", "Works {0}"),
    (r"\bi(?:'m| am) (?:a |an )?([^.,!?]{2,50}) (?:developer|engineer|student|gamer|designer)\b", "facts", "Is a {0}"),
    (r"\bi (?:like|love|enjoy) ([^.,!?]{2,80})", "preferences", "Likes {0}"),
    (r"\bi (?:hate|don't like|dont like|can't stand) ([^.,!?]{2,80})", "preferences", "Dislikes {0}"),
    (r"\bi prefer ([^.,!?]{2,80})", "preferences", "Prefers {0}"),
    (r"\bplease always ([^.,!?]{2,80})", "instructions", "Always {0}"),
    (r"\balways ([^.,!?]{2,80}) when (?:i|you) ([^.,!?]{2,40})", "instructions", "Always {0} when {1}"),
    (r"\bnever ([^.,!?]{2,80})", "instructions", "Never {0}"),
    (r"\bmy (dog|cat|brother|sister|mum|mom|dad|girlfriend|boyfriend|wife|husband|son|daughter|car|job|school|birthday|email) is ([^.,!?]{1,80})", "facts", "Their {0} is {1}"),
]


def skip_message(text: str) -> bool:
    low = (text or "").strip().lower().strip("!.?")
    if not low or low in SKIP:
        return True
    if low.startswith(("open ", "find ", "search ", "google ", "list ", "scan ", "run ")):
        return True
    return False


def extract(message: str) -> list[tuple[str, str]]:
    raw = (message or "").strip()
    if skip_message(raw):
        return []
    found: list[tuple[str, str]] = []
    for pat, cat, tmpl in PATTERNS:
        m = re.search(pat, raw, re.I)
        if not m:
            continue
        groups = [g.strip().rstrip(".") for g in m.groups() if g and g.strip()]
        if not groups:
            continue
        try:
            text = tmpl.format(*groups)
        except Exception:
            continue
        if len(text) > 160:
            continue
        found.append((cat, text))
    # Generic notes are stored in learn_from_turn, not as a spoken confirmation.
    return found
