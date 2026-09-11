import os
import re
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
        key = name.lower().strip().strip("\"'")
        builtins = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "discord": "discord:",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "edge": "msedge.exe",
            "firefox": "firefox.exe",
            "spotify": "spotify:",
            "steam": "steam.exe",
            "taskmgr": "taskmgr.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "ms-settings:": "ms-settings:",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "outlook": "outlook.exe",
            "teams": "ms-teams.exe",
            "vscode": "code",
            "code": "code",
            "visual studio": "devenv.exe",
            "whatsapp": "whatsapp:",
            "telegram": "telegram.exe",
            "vlc": "vlc.exe",
            "obs": "obs64.exe",
            "photos": "ms-photos:",
            "store": "ms-windows-store:",
            "clock": "ms-clock:",
            "camera": "microsoft.windows.camera:",
            "snip": "ms-screenclip:",
            "snipping tool": "ms-screenclip:",
            "zoom": "Zoom.exe",
            "slack": "slack.exe",
            "notion": "notion.exe",
            "epic": "EpicGamesLauncher.exe",
            "xbox": "xbox:",
        }
        target = self.allowed_apps.get(key) or builtins.get(key)
        err = None
        if target:
            try:
                self._launch(target)
                self._log(f"Opened application: {key}")
                return f"{name} is open."
            except Exception as e:
                err = e
        # Start Menu shortcut
        lnk = self._find_start_shortcut(key)
        if lnk:
            try:
                os.startfile(str(lnk))  # type: ignore[attr-defined]
                self._log(f"Opened shortcut: {lnk}")
                return f"{name} is open."
            except Exception as e:
                err = e
        if sys.platform == "win32":
            try:
                subprocess.Popen(f'start "" "{name}"', shell=True)
                self._log(f"start {name}")
                return f"{name} is open."
            except Exception as e:
                err = e
        return f"Couldn't open {name}" + (f": {err}" if err else ".")

    def _launch(self, target: str) -> None:
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
            return
        if target.endswith(":") or target.startswith("ms-"):
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            else:
                webbrowser.open(target)
            return
        if sys.platform == "win32":
            subprocess.Popen(target, shell=True)
        else:
            subprocess.Popen([target])

    def _find_start_shortcut(self, name: str) -> Path | None:
        if sys.platform != "win32":
            return None
        needle = name.lower()
        roots = [
            Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        ]
        hits = []
        for root in roots:
            if not root.is_dir():
                continue
            try:
                for p in root.rglob("*.lnk"):
                    if needle in p.stem.lower():
                        hits.append(p)
                        if len(hits) >= 8:
                            break
            except OSError:
                continue
        if not hits:
            return None
        hits.sort(key=lambda p: (len(p.stem), p.stem.lower()))
        return hits[0]

    def close_app(self, name: str) -> str:
        if not self._perm("allow_apps"):
            return "App control is disabled."
        key = name.lower().strip()
        exe = {
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "firefox": "firefox.exe",
            "notepad": "notepad.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "code": "Code.exe",
            "vscode": "Code.exe",
        }.get(key, key if key.endswith(".exe") else f"{key}.exe")
        if sys.platform != "win32":
            return "Close-app helper is Windows-only."
        proc = subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, text=True)
        if proc.returncode == 0:
            self._log(f"Closed {exe}")
            return f"Closed {name}."
        return f"Couldn't close {name} — is it running?"

    def volume(self, action: str) -> str:
        if pyautogui is None:
            return "Need pyautogui for volume keys."
        action = (action or "").lower()
        key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(action)
        if not key:
            return "Say volume up, volume down, or mute."
        for _ in range(4 if action != "mute" else 1):
            pyautogui.press(key)
        self._log(f"Volume {action}")
        return f"Volume {action}."

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
        keys = [k.strip() for k in re.split(r"[+\s]+", key.lower()) if k.strip()]
        if len(keys) > 1:
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        self._log(f"Pressed key: {key}")
        return f"Pressed {key}."

    def hotkey(self, *keys: str) -> str:
        if not self._perm("allow_keyboard"):
            return "Keyboard control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        pyautogui.hotkey(*keys)
        self._log("Hotkey " + "+".join(keys))
        return "Done."

    def lock(self) -> str:
        if sys.platform != "win32":
            return "Lock is Windows-only."
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        self._log("Locked PC")
        return "Locking the PC."

    def sleep_pc(self) -> str:
        if sys.platform != "win32":
            return "Sleep is Windows-only."
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend',$false,$false)"],
        )
        self._log("Sleep PC")
        return "Putting the PC to sleep."

    def shutdown(self, restart: bool = False) -> str:
        if sys.platform != "win32":
            return "Power control is Windows-only."
        args = ["shutdown", "/r" if restart else "/s", "/t", "5"]
        subprocess.Popen(args)
        self._log("Restart" if restart else "Shutdown")
        return "Restarting in 5 seconds." if restart else "Shutting down in 5 seconds. Open cmd and run shutdown /a if you didn't mean it."

    def show_desktop(self) -> str:
        return self.hotkey("win", "d")

    def switch_window(self) -> str:
        return self.hotkey("alt", "tab")

    def media(self, action: str) -> str:
        if pyautogui is None:
            return "Need pyautogui for media keys."
        key = {
            "play": "playpause",
            "pause": "playpause",
            "next": "nexttrack",
            "previous": "prevtrack",
            "prev": "prevtrack",
            "stop": "stop",
        }.get((action or "").lower())
        if not key:
            return "Say play, pause, next, or previous."
        pyautogui.press(key)
        self._log(f"Media {action}")
        return f"Media {action}."

    def copy(self) -> str:
        return self.hotkey("ctrl", "c")

    def paste(self) -> str:
        return self.hotkey("ctrl", "v")

    def select_all(self) -> str:
        return self.hotkey("ctrl", "a")

    def undo(self) -> str:
        return self.hotkey("ctrl", "z")

    def screenshot_desktop(self) -> str:
        dest = Path.home() / "Desktop" / "jarvis_screenshot.png"
        try:
            self.screenshot(dest)
        except Exception as e:
            if sys.platform == "win32":
                return self.hotkey("win", "shift", "s")
            return str(e)
        return f"Screenshot saved to {dest}"

    def scroll(self, direction: str = "down") -> str:
        if not self._perm("allow_mouse"):
            return "Mouse control disabled."
        if pyautogui is None:
            return "pyautogui not installed."
        amt = -400 if direction == "down" else 400
        pyautogui.scroll(amt)
        return f"Scrolled {direction}."

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

    def _home_roots(self) -> list[Path]:
        home = Path.home()
        roots = []
        for r in (
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "Pictures",
            home / "Videos",
            home / "Music",
            home / "OneDrive" / "Desktop",
            home / "OneDrive" / "Documents",
            home / "OneDrive" / "Downloads",
        ):
            if r.exists() and r.is_dir() and r not in roots:
                roots.append(r)
        return roots or [home]

    def find_named(self, name: str) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        name = name.strip().strip("\"'/")
        if not name:
            return "Which folder or file?"
        needle = name.lower()
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "AppData", "Windows"}
        matches, seen = [], set()

        def consider(p: Path):
            if needle not in p.name.lower():
                return
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            if key not in seen:
                seen.add(key)
                matches.append(p)

        for root in self._home_roots():
            try:
                for p in root.rglob("*"):
                    if any(part in skip for part in p.parts):
                        continue
                    consider(p)
                    if len(matches) >= 25:
                        break
            except OSError:
                continue
            if len(matches) >= 25:
                break

        try:
            from jarvis.paths import DATA

            idx = DATA / "file_index.txt"
            if idx.exists():
                for line in idx.read_text(encoding="utf-8", errors="replace").splitlines():
                    p = Path(line.strip())
                    if p.name and needle in p.name.lower():
                        consider(p)
        except Exception:
            pass

        if not matches:
            return (
                f"Nothing named '{name}' on Desktop, Documents, Downloads, Pictures, Videos or Music. "
                "Say 'scan my files' to index more, or tell me the folder."
            )
        lines = [f"Found {len(matches)} match(es) for '{name}':"]
        for m in matches[:15]:
            kind = "folder" if m.is_dir() else "file"
            lines.append(f"• ({kind}) {m}")
        first = matches[0]
        try:
            if first.is_dir():
                self.open_folder(str(first))
                lines.append(f"\nOpened folder: {first}")
            else:
                if sys.platform == "win32":
                    os.startfile(str(first))  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", str(first)])
                lines.append(f"\nOpened: {first}")
        except Exception as e:
            lines.append(f"\nFound it but couldn't open: {e}")
        self._log(f"Find named: {name} -> {len(matches)} hits")
        return "\n".join(lines)

    def overview(self) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        blocks = []
        for root in self._home_roots():
            try:
                entries = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except OSError:
                continue
            lines = [f"{root.name} — {root}"]
            for e in entries[:30]:
                mark = "/" if e.is_dir() else ""
                lines.append(f"  {e.name}{mark}")
            if len(entries) > 30:
                lines.append(f"  … {len(entries) - 30} more")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks) or "Couldn't read your user folders."

    def index_home(self, limit_each: int = 200) -> str:
        if not self._perm("allow_files"):
            return "File access is disabled."
        from jarvis.paths import DATA

        all_lines = []
        notes = []
        for root in self._home_roots():
            msg = self.index_folder(str(root), limit=limit_each)
            notes.append(msg.split("\n")[0])
            idx = DATA / "file_index.txt"
            if idx.exists():
                all_lines.extend(idx.read_text(encoding="utf-8", errors="replace").splitlines())
        uniq = []
        seen = set()
        for line in all_lines:
            if line and line not in seen:
                seen.add(line)
                uniq.append(line)
        (DATA / "file_index.txt").write_text("\n".join(uniq), encoding="utf-8")
        self._log(f"Indexed home folders: {len(uniq)} files")
        return f"I can see {len(uniq)} files across your user folders.\n" + "\n".join(notes)

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
