"""Turn a high-level ask into several real steps."""
from __future__ import annotations

import re


GOALS = [
    (
        r"(get|put|sort|tidy|clean).{0,20}(downloads|files).{0,20}(under control|sorted|organised|organized|tidy)",
        ["tidy downloads", "find duplicates in downloads", "big files in downloads"],
        "Downloads: sorted, dupes, big files.",
    ),
    (
        r"(clean|tidy|organise|organize).{0,12}desktop",
        ["organise desktop", "find duplicates in desktop"],
        "Desktop sorted.",
    ),
    (
        r"(set up|make|build).{0,20}(shop|store|landing).{0,20}(site|page|website)",
        ["new project called shop"],
        "Shop project on Desktop.",
    ),
    (
        r"(catch me up|what's going on|whats going on|brief me|start of (the )?day)",
        ["brief me"],
        "Briefing.",
    ),
    (
        r"(open|show).{0,12}(last|latest|newest).{0,12}download",
        ["open last download"],
        "Latest download.",
    ),
]


def handle(brain, raw: str) -> str | None:
    low = (raw or "").lower().strip()
    if not low or len(low.split()) < 3:
        return None
    for pat, steps, _label in GOALS:
        if re.search(pat, low):
            bits = []
            for step in steps:
                try:
                    hit = brain.intents.handle(step, depth=1)
                except Exception as e:
                    hit = str(e)
                if hit:
                    bits.append(hit)
            if bits:
                return "\n\n".join(bits)
    # "do everything for X folder"
    m = re.match(r"^(?:take care of|handle|deal with)\s+(?:my\s+)?(downloads|desktop|documents)$", low)
    if m:
        place = m.group(1)
        bits = []
        for step in (f"tidy {place}", f"find duplicates in {place}", f"big files in {place}"):
            try:
                hit = brain.intents.handle(step, depth=1)
            except Exception as e:
                hit = str(e)
            if hit:
                bits.append(hit)
        return "\n\n".join(bits) if bits else None
    return None
