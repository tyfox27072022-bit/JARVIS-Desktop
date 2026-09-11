import json
import uuid
from datetime import datetime
from pathlib import Path

from jarvis.paths import MEMORY_DIR, STYLE_DIR


class MemoryStore:
    """Persistent personal memory, instructions, conversation snapshots, style profile."""

    def __init__(self, path: Path | None = None):
        self.path = path or (MEMORY_DIR / "memory.json")
        self.data = {
            "facts": [],
            "instructions": [],
            "preferences": [],
            "projects": [],
            "notes": [],
            "conversation_snippets": [],
        }
        self.load()
        self.style_path = STYLE_DIR / "style_profile.json"
        self.style = {
            "summary": "",
            "examples": [],
            "traits": {
                "greeting_style": "",
                "detail_level": "medium",
                "tone": "",
                "abbreviations": [],
            },
            "updated": None,
        }
        self.load_style()

    def load(self):
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for k in self.data:
                        loaded.setdefault(k, [])
                    self.data = loaded
            except Exception:
                pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_style(self):
        if self.style_path.exists():
            try:
                self.style = json.loads(self.style_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def save_style(self):
        self.style_path.parent.mkdir(parents=True, exist_ok=True)
        self.style["updated"] = datetime.now().isoformat(timespec="seconds")
        self.style_path.write_text(
            json.dumps(self.style, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _add(self, category: str, text: str) -> dict:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "text": text.strip(),
            "created": datetime.now().isoformat(timespec="seconds"),
        }
        self.data.setdefault(category, []).append(entry)
        self.save()
        return entry

    def already_has(self, text: str) -> bool:
        needle = (text or "").strip().lower()
        if not needle:
            return True
        for items in self.data.values():
            for item in items:
                if isinstance(item, dict) and (item.get("text") or "").strip().lower() == needle:
                    return True
        return False

    def learn_from_turn(self, user_text: str, assistant_text: str = "") -> list[str]:
        from jarvis.ai.learn import extract, skip_message
        from jarvis.ai.style import merge_profile

        learned = []
        if (user_text or "").strip():
            try:
                self.style = merge_profile(self.style, user_text)
                self.save_style()
            except Exception:
                pass
        if not skip_message(user_text):
            hits = extract(user_text)
            if not hits and len((user_text or "").strip()) > 24 and not user_text.strip().endswith("?"):
                hits = [("notes", user_text.strip()[:200])]
            for cat, text in hits:
                if self.already_has(text):
                    continue
                self.remember(text, cat)
                learned.append(text)
            snippets = self.data.setdefault("conversation_snippets", [])
            snippets.append(
                {
                    "id": str(uuid.uuid4())[:8],
                    "text": user_text.strip()[:400],
                    "reply": (assistant_text or "")[:400],
                    "created": datetime.now().isoformat(timespec="seconds"),
                }
            )
            self.data["conversation_snippets"] = snippets[-80:]
            self.save()
        return learned

    def style_prompt(self) -> str:
        from jarvis.ai.style import prompt_block

        return prompt_block(self.style)

    def mirror_reply(self, text: str) -> str:
        from jarvis.ai.style import mirror

        return mirror(text, self.style)

    def style_report(self) -> str:
        t = self.style.get("traits") or {}
        summary = self.style.get("summary") or "Not enough chat yet — keep talking."
        examples = self.style.get("examples") or []
        lines = [summary]
        if t:
            lines.append(
                f"Tone: {t.get('tone')} · length: {t.get('detail_level')} · "
                f"contractions: {'yes' if t.get('contractions') else 'not really'} · "
                f"from {t.get('samples_seen', 0)} messages."
            )
        if examples:
            lines.append("Things you've said that I'm matching:")
            lines.extend(f"  “{e}”" for e in examples[-5:])
        return "\n".join(lines)

    def about_user(self) -> str:
        items = []
        for cat in ("facts", "preferences", "instructions", "notes"):
            for item in self.data.get(cat, [])[-20:]:
                if isinstance(item, dict) and item.get("text"):
                    items.append(f"- ({cat}) {item['text']}")
        if not items:
            return "I haven't stored anything about you yet. Tell me things — I'll keep them."
        return "Here's what I've learned:\n" + "\n".join(items)

    def add_instruction(self, text: str) -> dict:
        return self._add("instructions", text)

    def add_preference(self, text: str) -> dict:
        return self._add("preferences", text)

    def list_all(self) -> list[dict]:
        out = []
        for cat, items in self.data.items():
            for item in items:
                if isinstance(item, dict):
                    out.append({**item, "category": cat})
        return out

    def delete(self, entry_id: str) -> bool:
        for cat, items in self.data.items():
            for i, item in enumerate(list(items)):
                if isinstance(item, dict) and item.get("id") == entry_id:
                    items.pop(i)
                    self.save()
                    return True
        return False

    def clear(self, category: str | None = None):
        if category:
            self.data[category] = []
        else:
            for k in self.data:
                self.data[k] = []
        self.save()

    def context(self, max_items: int = 40) -> str:
        chunks = []
        for cat in ("instructions", "preferences", "facts", "projects", "notes"):
            for item in self.data.get(cat, [])[-max_items:]:
                if isinstance(item, dict) and item.get("text"):
                    chunks.append(f"{cat}: {item['text']}")
        style = (self.style.get("summary") or "").strip()
        if style:
            chunks.append(f"writing_style: {style}")
        return "\n".join(chunks)

    def learn_style_from_messages(self, messages: list[str]) -> str:
        samples = [m.strip() for m in messages if m and m.strip()][:30]
        if not samples:
            return "No messages provided."
        self.style["examples"] = samples[-20:]
        joined = "\n".join(samples)
        # Lightweight heuristic profile (full NLP via AI when online)
        avg_len = sum(len(s) for s in samples) / max(len(samples), 1)
        detail = "short" if avg_len < 80 else ("detailed" if avg_len > 200 else "medium")
        self.style["traits"]["detail_level"] = detail
        self.style["summary"] = (
            f"Ty tends toward {detail} messages. Sample phrasing learned from "
            f"{len(samples)} message(s). Prefer matching his brevity and wording."
        )
        self.save_style()
        return self.style["summary"]
