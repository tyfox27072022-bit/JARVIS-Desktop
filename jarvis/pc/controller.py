import os
import subprocess
import sys
import webbrowser
from pathlib import Path

import psutil

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None


class PCController:
    def __init__(self, settings: dict, audit=None):
        self.settings = settings.get("pc") or {}
        self.audit = audit
        self.allowed_apps = {
            k.lower(): v for k, v in (self.settings.get("allowed_apps") or {}).items()
        }

    def _log(self, msg: str):
        if self.audit:
            self.audit.log(msg)

    def _perm(self, key: str) -> bool:
        return bool(self.settings.get(key, False))

    def open_app(self, name: str) -> str:
        if not self._perm("allow_apps"):
            return "App launching is disabled in settings."
        key = name.lower().strip()
        builtins = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "discord": "discord:",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "spotify": "spotify:",
            "steam": "steam.exe",
        }
        target = self.allowed_apps.get(key) or builtins.get(key)
        if not target:
            return f"I don't have '{name}' on the allowed list yet."
        try:
            if target.endswith(":"):
                if sys.platform == "win32":
                    os.startfile(target)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(target)
            else:
                subprocess.Popen(
                    [target] if sys.platform != "win32" else target,
                    shell=sys.platform == "win32",
                )
        except Exception as e:
            return f"Couldn't open {key}: {e}"
        self._log(f"Opened application: {key}")
        return f"Opened {key}."

    def open_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return "Only http/https URLs are allowed."
        webbrowser.open(url)
        self._log(f"Opened URL: {url}")
        return f"Opened {url}"

    def open_folder(self, path: str) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled in settings."
        p = Path(path).expanduser()
        if not p.exists():
            alt = Path.home() / path
            if alt.exists():
                p = alt
        p = p.resolve()
        if not p.exists() or not p.is_dir():
            return f"Folder not found: {path}"
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        self._log(f"Opened folder: {p}")
        return f"Opened folder: {p}"

    def open_wifi(self) -> str:
        if sys.platform != "win32":
            return "Wi-Fi settings helper is Windows-only."
        subprocess.Popen(["cmd", "/c", "start", "ms-settings:network-wifi"], shell=False)
        self._log("Opened Wi-Fi settings")
        return "Opened Windows Wi-Fi settings."

    def screenshot(self, path: str | Path) -> Path:
        if not self._perm("allow_screen"):
            raise PermissionError("Screen capture disabled.")
        if pyautogui is None:
            raise RuntimeError("pyautogui not installed — screenshot unavailable.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pyautogui.screenshot().save(str(path))
        self._log(f"Screenshot saved: {path}")
        return path

    def mouse_move(self, x: int, y: int, duration: float = 0.2) -> str:
        if not self._perm("allow_mouse"):
            return "Mouse control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        pyautogui.moveTo(int(x), int(y), duration=duration)
        self._log(f"Mouse move {x},{y}")
        return f"Moved mouse to {x},{y}"

    def click(self, x: int | None = None, y: int | None = None) -> str:
        if not self._perm("allow_mouse"):
            return "Mouse control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        if x is not None and y is not None:
            pyautogui.click(int(x), int(y))
        else:
            pyautogui.click()
        self._log("Mouse click")
        return "Clicked."

    def type_text(self, text: str) -> str:
        if not self._perm("allow_keyboard"):
            return "Keyboard control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        pyautogui.write(text, interval=0.01)
        self._log("Typed text")
        return "Typed text."

    def press(self, key: str) -> str:
        if not self._perm("allow_keyboard"):
            return "Keyboard control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        pyautogui.press(key)
        self._log(f"Pressed key: {key}")
        return f"Pressed {key}."

    def system_summary(self) -> dict:
        disk_path = "C:\\" if sys.platform == "win32" else "/"
        try:
            disk = psutil.disk_usage(disk_path).percent
        except Exception:
            disk = None
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": disk,
        }

    def find_named(self, name: str) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        name = name.strip().strip("\"'")
        if not name:
            return "Which folder or file?"
        needle = name.lower()
        home = Path.home()
        roots = []
        for r in (
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "OneDrive" / "Desktop",
            home / "OneDrive" / "Documents",
            home,
        ):
            if r.exists() and r.is_dir() and r not in roots:
                roots.append(r)
        matches, seen = [], set()
        for root in roots:
            try:
                for child in root.iterdir():
                    if needle in child.name.lower():
                        key = str(child.resolve())
                        if key not in seen:
                            seen.add(key)
                            matches.append(child)
                    if child.is_dir():
                        try:
                            for grand in child.iterdir():
                                if needle in grand.name.lower():
                                    key = str(grand.resolve())
                                    if key not in seen:
                                        seen.add(key)
                                        matches.append(grand)
                        except OSError:
                            pass
            except OSError:
                continue
        if not matches:
            return f"Nothing named '{name}' found under Desktop/Documents/Downloads."
        lines = [f"Found {len(matches)} match(es):"]
        for m in matches[:15]:
            lines.append(f"• ({'folder' if m.is_dir() else 'file'}) {m}")
        if matches[0].is_dir():
            try:
                self.open_folder(str(matches[0]))
                lines.append(f"\nOpened: {matches[0]}")
            except Exception as e:
                lines.append(f"\nCould not open: {e}")
        self._log(f"Find named: {name} -> {len(matches)} hits")
        return "\n".join(lines)

    def list_folder(self, path_or_name: str) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        p = Path(path_or_name).expanduser()
        if not p.exists():
            alt = Path.home() / path_or_name
            if alt.exists():
                p = alt
        if not p.exists() or not p.is_dir():
            return self.find_named(path_or_name)
        try:
            entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError as e:
            return f"Could not read folder: {e}"
        lines = [f"Contents of {p}:"]
        for e in entries[:80]:
            lines.append(f"{'[dir] ' if e.is_dir() else '      '}{e.name}")
        return "\n".join(lines)

    def read_file(self, path: str, max_chars: int = 50000) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        p = Path(path).expanduser()
        if not p.is_file():
            return f"File not found: {path}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            self._log(f"Read file: {p}")
            return text[:max_chars]
        except OSError as e:
            return f"Could not read: {e}"

    def write_file(self, path: str, content: str, confirm: bool = False) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        p = Path(path).expanduser()
        if p.exists() and not confirm:
            return f"File exists. Confirm overwrite for: {p}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self._log(f"Wrote file: {p}")
        return f"Wrote {p}"

    def list_windows(self) -> str:
        try:
            import pygetwindow as gw
        except Exception:
            gw = None
        if gw is None:
            return "Window listing needs pygetwindow (comes with pyautogui on Windows)."
        titles = []
        try:
            for w in gw.getAllWindows():
                title = (w.title or "").strip()
                if title:
                    titles.append(title)
        except Exception as e:
            return f"Could not list windows: {e}"
        if not titles:
            return "No visible window titles."
        return "Open windows:\n" + "\n".join(f"- {t}" for t in titles[:40])

    def screen_report(self) -> str:
        if not self._perm("allow_screen"):
            return "Screen access is disabled in settings."
        lines = []
        if pyautogui is not None:
            try:
                w, h = pyautogui.size()
                x, y = pyautogui.position()
                lines.append(f"Screen {w}x{h}. Mouse at {x},{y}.")
            except Exception as e:
                lines.append(f"Screen size failed: {e}")
        else:
            lines.append("pyautogui not available.")
        lines.append(self.list_windows())
        return "\n".join(lines)

    def double_click(self, x: int | None = None, y: int | None = None) -> str:
        if not self._perm("allow_mouse"):
            return "Mouse control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        if x is not None and y is not None:
            pyautogui.doubleClick(int(x), int(y))
        else:
            pyautogui.doubleClick()
        self._log("Double click")
        return "Double-clicked."

    def hotkey(self, keys: str) -> str:
        if not self._perm("allow_keyboard"):
            return "Keyboard control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        parts = [k.strip() for k in keys.replace("+", " ").split() if k.strip()]
        if not parts:
            return "No keys given."
        pyautogui.hotkey(*parts)
        self._log(f"Hotkey {parts}")
        return f"Pressed {'+'.join(parts)}."

    def index_folder(self, path: str, limit: int = 250) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        root = Path(path).expanduser()
        if not root.exists():
            alt = Path.home() / path
            if alt.exists():
                root = alt
        if not root.exists() or not root.is_dir():
            return f"Folder not found: {path}"
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "AppData"}
        text_ext = {
            ".txt", ".md", ".json", ".py", ".js", ".ts", ".csv", ".log",
            ".html", ".css", ".gpc", ".ini", ".cfg", ".xml", ".yml", ".yaml",
        }
        names = []
        for p in root.rglob("*"):
            if len(names) >= limit:
                break
            if any(part in skip for part in p.parts):
                continue
            if p.is_file() and (p.suffix.lower() in text_ext or p.suffix == ""):
                try:
                    rel = str(p.relative_to(root))
                except ValueError:
                    rel = str(p)
                names.append(rel)
        from jarvis.paths import DATA

        out = DATA / "file_index.txt"
        lines = [str(root / n) for n in names]
        out.write_text("\n".join(lines), encoding="utf-8")
        self._log(f"Indexed {len(names)} files under {root}")
        preview = "\n".join(names[:40])
        return (
            f"Indexed {len(names)} files under {root}.\n"
            f"I can search this list. First names:\n{preview}"
        )
