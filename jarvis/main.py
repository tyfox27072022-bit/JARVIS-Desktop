import sys
from datetime import datetime

from PySide6.QtCore import QThread, Signal
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
from jarvis.vault import VaultLibrary
from jarvis.voice import VoiceEngine
from jarvis.web import WebTools


class Worker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
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
        self.voice = VoiceEngine(self.settings.get("voice", {}))
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
        self.resize(1100, 720)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(self._chat_tab(), "Chat")
        tabs.addTab(self._memory_tab(), "Memory")
        tabs.addTab(self._vault_tab(), "Vault")
        tabs.addTab(self._settings_tab(), "Settings")
        tabs.addTab(self._log_tab(), "Activity Log")

        self.audit.log("JARVIS started")
        self._autoload()

    def _autoload(self):
        def job():
            try:
                return self.brain.ensure_local_model()
            except Exception as e:
                return f"Autoload: {e}"

        self.worker = Worker(job)
        self._workers.append(self.worker)
        self.worker.done.connect(lambda msg: self._on_autoload(msg))
        self.worker.start()

    def _on_autoload(self, msg: str):
        if getattr(self, "status", None):
            self.status.setText(f"{self.assistant} • {self.brain.mode_label}")
        if "Loaded" in (msg or "") or "Already loaded" in (msg or ""):
            self.chat.append(f"{self.assistant}: Model's ready.")

    def _chat_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        mode = self.brain.mode_label
        self.status = QLabel(f"{self.assistant} • {self.brain.mode_label}")
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText(f"Talk to {self.assistant}…")
        send = QPushButton("Send")
        speak_btn = QPushButton("Speak")
        shot = QPushButton("Screenshot")
        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(send)
        row.addWidget(speak_btn)
        row.addWidget(shot)
        layout.addWidget(self.status)
        layout.addWidget(self.chat)
        layout.addLayout(row)
        send.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        speak_btn.clicked.connect(self.listen)
        shot.clicked.connect(self.screenshot)
        self.chat.append(f"{self.assistant}: {greeting(self.user)}")
        return w

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
        return w

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
        return w

    def _settings_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        ai = self.settings.get("ai") or {}
        self.s_user = QLineEdit(self.settings.get("user_name", "Ty"))
        self.s_assistant = QLineEdit(self.settings.get("assistant_name", "JARVIS"))
        self.s_provider = QLineEdit(ai.get("provider", "xai"))
        self.s_model_id = QLineEdit(ai.get("model") or ai.get("local_model_id") or "jarvis")
        self.s_model_path = QLineEdit(ai.get("local_model_path", ""))
        self.s_apikey = QLineEdit(ai.get("api_key", ""))
        self.s_apikey.setEchoMode(QLineEdit.EchoMode.Password)
        self.s_discord = QLineEdit((self.settings.get("discord") or {}).get("bot_token", ""))
        self.s_discord.setEchoMode(QLineEdit.EchoMode.Password)
        self.s_ctx = QLineEdit(str(ai.get("n_ctx", 2048)))
        self.s_temp = QLineEdit(str(ai.get("temperature", 0.5)))
        self.s_maxtok = QLineEdit(str(ai.get("max_tokens", 512)))
        self.s_voice = QCheckBox("Speak replies aloud")
        self.s_voice.setChecked(bool((self.settings.get("voice") or {}).get("enabled")))
        save_btn = QPushButton("Save settings")
        dl_btn = QPushButton("Download local model")
        load_btn = QPushButton("Load local model")
        hw_btn = QPushButton("Detect hardware")
        index_btn = QPushButton("Index a folder on this PC")
        discord_btn = QPushButton("Start Discord (phone DMs)")
        form.addRow("Your name", self.s_user)
        form.addRow("Assistant name", self.s_assistant)
        form.addRow("Provider (xai / local / ollama)", self.s_provider)
        form.addRow("Model (fast / jarvis / sharp)", self.s_model_id)
        form.addRow("xAI API key (fast Grok)", self.s_apikey)
        form.addRow("Discord bot token (phone DMs)", self.s_discord)
        form.addRow("Custom .gguf path (optional)", self.s_model_path)
        form.addRow("Context size", self.s_ctx)
        form.addRow("Temperature", self.s_temp)
        form.addRow("Max tokens", self.s_maxtok)
        form.addRow(self.s_voice)
        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addWidget(dl_btn)
        row.addWidget(load_btn)
        row.addWidget(hw_btn)
        form.addRow(row)
        form.addRow(index_btn)
        form.addRow(discord_btn)
        save_btn.clicked.connect(self.save_settings)
        dl_btn.clicked.connect(self.download_model)
        load_btn.clicked.connect(self.load_model)
        hw_btn.clicked.connect(self.show_hardware)
        index_btn.clicked.connect(self.index_folder)
        discord_btn.clicked.connect(self.start_discord)
        hint = QLabel(
            "This is the Windows desktop app.\n"
            "Fast chat: paste an xAI API key, provider=xai, model=jarvis (or fast / sharp).\n"
            "Offline: Download local model, then Load. Ids: tinyllama-1.1b-q4 | qwen2.5-1.5b-q4 | phi3-mini-q4\n"
            "Phone: create a Discord bot, paste the token, Start Discord, then DM that bot from your phone."
        )
        hint.setWordWrap(True)
        form.addRow(hint)
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
        return w

    def send(self):
        if self.busy:
            return
        msg = self.input.text().strip()
        self.input.clear()
        if not msg:
            return
        self.chat.append(f"<b>{self.user}:</b> {msg}")
        self.busy = True
        self.status.setText(f"{self.assistant} • Thinking…")
        self.worker = Worker(lambda: self.brain.chat(msg))
        self._workers.append(self.worker)
        self.worker.done.connect(lambda a: self._reply(a))
        self.worker.failed.connect(lambda e: self._reply(f"Error: {e}"))
        self.worker.start()

    def _reply(self, answer: str):
        self.busy = False
        self.status.setText(f"{self.assistant} • {self.brain.mode_label}")
        self.chat.append(f"<b>{self.assistant}:</b> {answer}")
        if self.voice.enabled or (self.settings.get("voice") or {}).get("enabled"):
            self.voice.speak(answer)
        self.refresh_memory()
        self.refresh_log()

    def listen(self):
        try:
            text = self.voice.listen()
            self.input.setText(text)
            self.send()
        except Exception as e:
            QMessageBox.warning(self, "Voice", str(e))

    def screenshot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save screenshot", str(WORKSPACE / "screenshot.png"), "PNG (*.png)"
        )
        if not path:
            return
        try:
            self.pc.screenshot(path)
            self.chat.append(f"{self.assistant}: Screenshot saved to {path}")
            self.audit.log(f"Screenshot {path}")
        except Exception as e:
            QMessageBox.warning(self, "Screenshot", str(e))

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
        self.settings["ai"]["provider"] = self.s_provider.text().strip() or "xai"
        self.settings["ai"]["model"] = self.s_model_id.text().strip() or "jarvis"
        self.settings["ai"]["local_model_id"] = self.s_model_id.text().strip() or "tinyllama-1.1b-q4"
        self.settings["ai"]["local_model_path"] = self.s_model_path.text().strip()
        self.settings["ai"]["api_key"] = self.s_apikey.text().strip()
        if self.settings["ai"]["provider"] in ("xai", "grok", ""):
            self.settings["ai"]["api_base"] = "https://api.x.ai/v1"
        self.settings.setdefault("discord", {})
        self.settings["discord"]["bot_token"] = self.s_discord.text().strip()
        try:
            self.settings["ai"]["n_ctx"] = int(self.s_ctx.text().strip() or "2048")
        except ValueError:
            self.settings["ai"]["n_ctx"] = 2048
        try:
            self.settings["ai"]["temperature"] = float(self.s_temp.text().strip() or "0.5")
        except ValueError:
            self.settings["ai"]["temperature"] = 0.5
        try:
            self.settings["ai"]["max_tokens"] = int(self.s_maxtok.text().strip() or "512")
        except ValueError:
            self.settings["ai"]["max_tokens"] = 512
        self.settings.setdefault("voice", {})
        self.settings["voice"]["enabled"] = self.s_voice.isChecked()
        save(self.settings)
        self.user = self.settings["user_name"]
        self.assistant = self.settings["assistant_name"]
        self.voice = VoiceEngine(self.settings.get("voice", {}))
        self.brain.s = self.settings
        self.pc.settings = self.settings.get("pc") or {}
        self.status.setText(f"{self.assistant} • {self.brain.mode_label}")
        self.setWindowTitle(self.assistant)
        QMessageBox.information(self, "Settings", "Saved.")
        self.audit.log("Settings saved")

    def download_model(self):
        self.save_settings()
        self.chat.append(f"{self.assistant}: Downloading model — this can take several minutes…")
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
            self.status.setText(f"{self.assistant} • {self.brain.mode_label}")
            QMessageBox.information(self, "Model", msg)
            self.chat.append(f"{self.assistant}: {msg}")
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
            self.chat.append(f"{self.assistant}: {msg[:800]}")
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
            msg = self._discord_bot.start_background()
            QMessageBox.information(self, "Discord", msg + "\nMessage the bot from your phone in a DM.")
            self.audit.log("Discord bot start requested")
        except Exception as e:
            QMessageBox.warning(self, "Discord", str(e))

    def refresh_log(self):
        self.log_view.setPlainText("\n".join(self.audit.recent(100)) or "(no entries)")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
