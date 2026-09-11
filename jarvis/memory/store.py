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

    def remember(self, text: str, category: str = "notes") -> dict:
        if category not in self.data:
            category = "notes"
        return self._add(category, text)

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
