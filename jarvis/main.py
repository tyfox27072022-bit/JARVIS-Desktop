import html
import sys
from datetime import datetime

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from jarvis.ai import Brain
from jarvis.coding import CodingWorkspace
from jarvis.config import load, save
from jarvis.memory import MemoryStore
from jarvis.paths import BASE, WORKSPACE
from jarvis.pc import PCController
from jarvis.security import AuditLog
from jarvis.updates import ImprovementManager
from jarvis.ui import apply_theme
from jarvis.ui.format import chat_html
from jarvis.vault import VaultLibrary
from jarvis.web import WebTools


class Worker(QThread):
    done = Signal(str)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn, with_progress: bool = False):
        super().__init__()
        self.fn = fn
        self.with_progress = with_progress

    def run(self):
        try:
            if self.with_progress:
                self.done.emit(self.fn(self.progress.emit))
            else:
                self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


def greeting(name: str) -> str:
    h = datetime.now().hour
    if h < 12:
        return f"Morning, {name}. What are we doing first?"
    if h < 18:
        return f"Afternoon, {name}. I'm here when you need me."
    return f"Evening, {name}. Fire away whenever you're ready."


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load()
        self.user = self.settings.get("user_name", "Ty")
        self.assistant = self.settings.get("assistant_name", "JARVIS")
        self.audit = AuditLog(self.settings.get("security", {}).get("audit_log", True))
        self.memory = MemoryStore()
        vault_root = BASE / self.settings.get("vault", {}).get("root", "vault/scripts")
        self.vault = VaultLibrary(
            vault_root,
            self.settings.get("vault", {}).get("allowed_extensions"),
            self.audit,
        )
        self.pc = PCController(self.settings, self.audit)
        self.web = WebTools()
        self.coding = CodingWorkspace(audit=self.audit)
        self.improve = ImprovementManager(audit=self.audit)
        self.brain = Brain(
            self.settings,
            self.memory,
            self.vault,
            self.web,
            self.pc,
            self.coding,
            self.improve,
            self.audit,
        )
        self.busy = False
        self.worker = None
        self._workers = []

        self.setWindowTitle(self.assistant)
        self.resize(1120, 740)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(self._chat_tab(), "Chat")
        tabs.addTab(self._memory_tab(), "Memory")
        tabs.addTab(self._vault_tab(), "Vault")
        tabs.addTab(self._settings_tab(), "Settings")
        tabs.addTab(self._log_tab(), "Activity")

        self.audit.log("JARVIS started")
        self._autoload()
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(4000)
        self._watch_timer.timeout.connect(self._watch_tick)
        from jarvis.pc.watch import is_on

        if is_on() and (self.settings.get("pc") or {}).get("allow_watch", True):
            self._watch_timer.start()

    def _autoload(self):
        def job(progress=None):
            try:
                return self.brain.bootstrap(progress_cb=progress)
            except Exception as e:
                return f"Startup: {e}"

        self.worker = Worker(job, with_progress=True)
        self._workers.append(self.worker)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(lambda msg: self._on_autoload(msg))
        self.worker.start()

    def _watch_tick(self):
        from jarvis.pc.watch import distill, is_on, tick

        if not is_on():
            self._watch_timer.stop()
            if getattr(self, "status", None) and not self.busy:
                self.status.setText(self.brain.mode_label.upper())
            return
        try:
            tick(self.pc)
            distill(self.memory)
        except Exception:
            pass
        if getattr(self, "status", None) and not self.busy:
            self.status.setText("WATCHING")

    def _on_progress(self, msg: str):
        if getattr(self, "status", None):
            self.status.setText(msg)

    def _on_autoload(self, msg: str):
        if getattr(self, "status", None):
            self.status.setText(self.brain.mode_label.upper())
        text = msg or ""
        if any(s in text for s in ("Loaded", "Already loaded", "CLI engine ready", "Installed")):
            self._post(self.assistant, "Local brain is online.")
        elif "No local" in text or "skipped" in text or "download" in text.lower():
            pass

    def _chat_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel(self.assistant)
        title.setObjectName("title")
        self.status = QLabel(self.brain.mode_label.upper())
        self.status.setObjectName("status")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(self.status)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText(f"Talk to {self.assistant}…")
        send = QPushButton("Send")
        send.setObjectName("primary")
        send.setDefault(True)
        copy_btn = QPushButton("Copy last")
        shot = QPushButton("Screenshot")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        row.addWidget(copy_btn)
        row.addWidget(shot)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self._chip_bar = QWidget()
        self._chip_bar.setLayout(chips)
        for label, cmd in (
            ("Brief me", "brief me"),
            ("Help", "help"),
            ("Look at my screen", "look at my screen"),
            ("What have I been doing", "what have I been doing"),
        ):
            b = QPushButton(label)
            b.setObjectName("chip")
            b.clicked.connect(lambda _=False, c=cmd: self._chip(c))
            chips.addWidget(b)
        chips.addStretch()
        layout.addLayout(head)
        layout.addWidget(self.chat, 1)
        layout.addWidget(self._chip_bar)
        layout.addLayout(row)
        send.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        copy_btn.clicked.connect(self.copy_last)
        shot.clicked.connect(self.screenshot)
        self._last_reply = ""
        hist = getattr(self.brain, "history", None) or []
        if hist:
            for turn in hist[-40:]:
                role = turn.get("role")
                text = turn.get("content") or ""
                if not text:
                    continue
                who = self.user if role == "user" else self.assistant
                self._post(who, text)
            self._post(self.assistant, "I'm back. Still remember what we talked about.")
        else:
            self._post(
                self.assistant,
                f"{greeting(self.user)} Ask anything. I'll look it up, write, code, or run this PC. Shortcuts are under the chat.",
            )
        return w

    def _post(self, who: str, text: str):
        mine = who == self.user
        if not mine:
            self._last_reply = text or ""
        self.chat.append(chat_html(who, text, mine))

    def _chip(self, cmd: str):
        self.input.setText(cmd)
        self.send()
        if getattr(self, "_chip_bar", None):
            self._chip_bar.hide()

    def copy_last(self):
        text = getattr(self, "_last_reply", "") or ""
        if not text:
            return
        QApplication.clipboard().setText(text)

    def _pad(self, inner: QWidget) -> QWidget:
        inner.layout().setContentsMargins(22, 18, 22, 18)
        inner.layout().setSpacing(12)
        return inner

    def _memory_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.mem_view = QTextEdit()
        self.mem_view.setReadOnly(True)
        refresh = QPushButton("Refresh")
        clear = QPushButton("Clear all memory")
        row = QHBoxLayout()
        row.addWidget(refresh)
        row.addWidget(clear)
        layout.addWidget(self.mem_view)
        layout.addLayout(row)
        refresh.clicked.connect(self.refresh_memory)
        clear.clicked.connect(self.clear_memory)
        self.refresh_memory()
        return self._pad(w)

    def _vault_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.vault_view = QTextEdit()
        self.vault_view.setReadOnly(True)
        refresh = QPushButton("Refresh index")
        import_btn = QPushButton("Import script…")
        row = QHBoxLayout()
        row.addWidget(refresh)
        row.addWidget(import_btn)
        layout.addWidget(self.vault_view)
        layout.addLayout(row)
        refresh.clicked.connect(self.refresh_vault)
        import_btn.clicked.connect(self.import_script)
        self.refresh_vault()
        return self._pad(w)

    def _settings_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        ai = self.settings.get("ai") or {}
        self.s_user = QLineEdit(self.settings.get("user_name", "Ty"))
        self.s_assistant = QLineEdit(self.settings.get("assistant_name", "JARVIS"))
        self.s_provider = QLineEdit("auto")
        self.s_model_id = QLineEdit(ai.get("local_model_id") or "tinyllama-1.1b-q4")
        self.s_model_path = QLineEdit(ai.get("local_model_path", ""))
        self.s_apikey = QLineEdit("")
        self.s_discord = QLineEdit((self.settings.get("discord") or {}).get("bot_token", ""))
        self.s_discord.setEchoMode(QLineEdit.EchoMode.Password)
        self.s_ctx = QLineEdit(str(ai.get("n_ctx", 4096)))
        self.s_temp = QLineEdit(str(ai.get("temperature", 0.5)))
        self.s_maxtok = QLineEdit(str(ai.get("max_tokens", 512)))
        self.s_discord.setEchoMode(QLineEdit.EchoMode.Password)
        save_btn = QPushButton("Save settings")
        save_btn.setObjectName("primary")
        index_btn = QPushButton("Index a folder on this PC")
        discord_btn = QPushButton("Start Discord (phone DMs)")
        form.addRow("Your name", self.s_user)
        form.addRow("Assistant name", self.s_assistant)
        form.addRow("Discord bot token (optional)", self.s_discord)
        self.s_watch = QCheckBox("Watch my screen until I say stop")
        from jarvis.pc.watch import is_on as _watch_on

        self.s_watch.setChecked(_watch_on())
        form.addRow(self.s_watch)
        form.addRow(save_btn)
        form.addRow(index_btn)
        form.addRow(discord_btn)
        save_btn.clicked.connect(self.save_settings)
        index_btn.clicked.connect(self.index_folder)
        discord_btn.clicked.connect(self.start_discord)
        hint = QLabel(
            "JARVIS uses Qwen2.5 only (free, ~1 GB) as its local brain.\n"
            "It can read your screen and learn the apps you use while this window is open.\n"
            "Discord is only for talking from your phone — optional."
        )
        hint.setWordWrap(True)
        credit = QLabel("Made and created by ty_fox07")
        credit.setObjectName("credit")
        form.addRow(hint)
        form.addRow(credit)
        form.setContentsMargins(22, 18, 22, 18)
        form.setSpacing(12)
        return w

    def _log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        refresh = QPushButton("Refresh log")
        layout.addWidget(self.log_view)
        layout.addWidget(refresh)
        refresh.clicked.connect(self.refresh_log)
        self.refresh_log()
        return self._pad(w)

    def send(self):
        if self.busy:
            return
        msg = self.input.text().strip()
        self.input.clear()
        if not msg:
            return
        if msg.lower().strip("!.?") in {"clear chat", "clear conversation", "wipe chat"}:
            self.chat.clear()
            self.brain.history = []
            self._post(self.assistant, "Chat's cleared.")
            return
        self._post(self.user, msg)
        if getattr(self, "_chip_bar", None):
            self._chip_bar.hide()
        self.busy = True
        self.input.setEnabled(False)
        self.status.setText("THINKING")
        self.worker = Worker(lambda: self.brain.chat(msg))
        self._workers.append(self.worker)
        self.worker.done.connect(lambda a: self._reply(a))
        self.worker.failed.connect(lambda e: self._reply(f"Error: {e}"))
        self.worker.start()

    def _reply(self, answer: str):
        self.busy = False
        self.input.setEnabled(True)
        self.input.setFocus()
        try:
            from jarvis.pc.watch import is_on

            if is_on():
                if not self._watch_timer.isActive():
                    self._watch_timer.start()
                self.status.setText("WATCHING")
            else:
                self._watch_timer.stop()
                self.status.setText(self.brain.mode_label.upper())
        except Exception:
            self.status.setText(self.brain.mode_label.upper())
        self._post(self.assistant, answer)
        self.refresh_memory()
        self.refresh_log()

    def screenshot(self):
        self.status.setText("LOOKING")
        self.busy = True

        def job():
            return self.brain.see()

        self.worker = Worker(job)
        self._workers.append(self.worker)
        self.worker.done.connect(lambda a: self._reply(a))
        self.worker.failed.connect(lambda e: self._reply(f"Screen: {e}"))
        self.worker.start()

    def refresh_memory(self):
        items = self.memory.list_all()
        if not items:
            self.mem_view.setPlainText("(empty)")
            return
        lines = [f"[{x.get('id')}] ({x.get('category')}) {x.get('text')}" for x in items]
        self.mem_view.setPlainText("\n".join(lines))

    def clear_memory(self):
        if QMessageBox.question(self, "Confirm", "Clear all memory?") != QMessageBox.StandardButton.Yes:
            return
        self.memory.clear()
        self.refresh_memory()
        self.audit.log("Memory cleared")

    def refresh_vault(self):
        items = self.vault.index()
        if not items:
            self.vault_view.setPlainText("Vault empty — import scripts to index them.")
            return
        lines = [f"[{x['game']}] {x['name']}  ({x['path']})" for x in items]
        self.vault_view.setPlainText("\n".join(lines))

    def import_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import script")
        if not path:
            return
        try:
            dest, game = self.vault.import_script(path)
            QMessageBox.information(self, "Vault", f"Imported as {game}:\n{dest}")
            self.refresh_vault()
        except Exception as e:
            QMessageBox.warning(self, "Import failed", str(e))

    def save_settings(self):
        self.settings["user_name"] = self.s_user.text().strip() or "Ty"
        self.settings["assistant_name"] = self.s_assistant.text().strip() or "JARVIS"
        self.settings.setdefault("ai", {})
        self.settings["ai"]["provider"] = "auto"
        self.settings["ai"]["model"] = "qwen2.5-1.5b-q4"
        self.settings["ai"]["local_model_id"] = "qwen2.5-1.5b-q4"
        self.settings["ai"]["local_model_path"] = self.s_model_path.text().strip()
        self.settings["ai"]["api_key"] = ""
        self.settings.setdefault("discord", {})
        self.settings["discord"]["bot_token"] = self.s_discord.text().strip()
        try:
            self.settings["ai"]["n_ctx"] = int(self.s_ctx.text().strip() or "4096")
        except ValueError:
            self.settings["ai"]["n_ctx"] = 4096
        try:
            self.settings["ai"]["temperature"] = float(self.s_temp.text().strip() or "0.5")
        except ValueError:
            self.settings["ai"]["temperature"] = 0.5
        try:
            self.settings["ai"]["max_tokens"] = int(self.s_maxtok.text().strip() or "512")
        except ValueError:
            self.settings["ai"]["max_tokens"] = 512
        self.settings.setdefault("pc", {})
        self.settings["pc"]["allow_watch"] = bool(self.s_watch.isChecked())
        from jarvis.pc.watch import set_on

        set_on(bool(self.s_watch.isChecked()))
        save(self.settings)
        if self.s_watch.isChecked():
            self._watch_timer.start()
            self.status.setText("WATCHING")
        else:
            self._watch_timer.stop()
        self.user = self.settings["user_name"]
        self.assistant = self.settings["assistant_name"]
        self.brain.s = self.settings
        self.pc.settings = self.settings.get("pc") or {}
        self.status.setText(self.brain.mode_label.upper())
        self.setWindowTitle(self.assistant)
        QMessageBox.information(self, "Settings", "Saved.")
        self.audit.log("Settings saved")

    def download_model(self):
        self.save_settings()
        self._post(self.assistant, "Downloading model — this can take several minutes…")
        self.busy = True

        def job():
            msg = self.brain.download_model()
            try:
                load = self.brain.ensure_local_model()
                return msg + "\n" + load
            except Exception as e:
                return msg + f"\nLoad: {e}"

        self.worker = Worker(job)
        self.worker.done.connect(lambda a: self._reply(a))
        self.worker.failed.connect(lambda e: self._reply(f"Download error: {e}"))
        self.worker.start()

    def load_model(self):
        self.save_settings()
        try:
            msg = self.brain.ensure_local_model()
            self.status.setText(self.brain.mode_label.upper())
            QMessageBox.information(self, "Model", msg)
            self._post(self.assistant, msg)
        except Exception as e:
            QMessageBox.warning(self, "Model", str(e))

    def show_hardware(self):
        from jarvis.ai.hardware import format_report
        QMessageBox.information(self, "Hardware", format_report())

    def index_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Folder for JARVIS to learn")
        if not path:
            return
        try:
            msg = self.pc.index_folder(path)
            QMessageBox.information(self, "Indexed", msg[:1500])
            self._post(self.assistant, msg[:800])
            self.audit.log(f"Indexed folder {path}")
        except Exception as e:
            QMessageBox.warning(self, "Index failed", str(e))

    def start_discord(self):
        self.save_settings()
        token = (self.settings.get("discord") or {}).get("bot_token") or ""
        if not token:
            QMessageBox.warning(self, "Discord", "Paste a bot token in Settings first.")
            return
        try:
            from jarvis.discord.bot import TicketBot

            self.settings["discord"]["enabled"] = True
            save(self.settings)
            if not hasattr(self, "_discord_bot") or self._discord_bot is None:
                self._discord_bot = TicketBot(
                    self.settings, vault=self.vault, brain=self.brain, audit=self.audit
                )
            self.brain.discord_bot = self._discord_bot
            msg = self._discord_bot.start_background()
            QMessageBox.information(self, "Discord", msg + "\nMessage the bot from your phone in a DM.")
            self.audit.log("Discord bot start requested")
        except Exception as e:
            QMessageBox.warning(self, "Discord", str(e))

    def refresh_log(self):
        self.log_view.setPlainText("\n".join(self.audit.recent(100)) or "(no entries)")

    def closeEvent(self, event):
        try:
            self.brain._save_history()
            self.memory.save()
            self.memory.save_style()
            save(self.settings)
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
