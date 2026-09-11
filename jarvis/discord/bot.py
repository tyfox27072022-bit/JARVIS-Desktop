"""
Official Discord bot for the Orla Vault server.

Rules:
- Only speak in ticket channels (category ID or name contains 'ticket').
- New ticket: greet. If member lacks Vault role, explain they need to buy Vault.
- May READ other channels / local GPC for knowledge.
- Must NOT attach or paste protected script files unless the member has Vault.
- Stay quiet if staff/dev/admin recently handled the ticket.
- Never grant roles. Bot is not an admin.
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

from jarvis.discord.support import DiscordSupportLogic


PROTECTED_EXT = {".gpc", ".zip", ".rar", ".7z"}


def _channel_is_ticket(channel, cfg: dict) -> bool:
    cat_id = str(cfg.get("ticket_category_id") or "")
    parent = getattr(channel, "category", None)
    if cat_id and parent and str(parent.id) == cat_id:
        return True
    name = (getattr(channel, "name", "") or "").lower()
    parent_name = (getattr(parent, "name", "") or "").lower() if parent else ""
    return "ticket" in name or "ticket" in parent_name


class TicketBot:
    def __init__(self, settings: dict, vault=None, brain=None, audit=None):
        self.settings = settings
        self.cfg = settings.get("discord") or {}
        self.logic = DiscordSupportLogic(settings)
        self.vault = vault
        self.brain = brain
        self.audit = audit
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._pending_files: list = []
        self.last_dm = None

    def queue_file(self, path) -> str:
        from pathlib import Path

        p = Path(path)
        if not p.is_file():
            return ""
        self._pending_files.append(p)
        return "Queued for Discord DM as well."

    def start_background(self) -> str:
        if not self.logic.enabled:
            return "Discord is off. Set discord.enabled=true and bot_token in config."
        if self._thread and self._thread.is_alive():
            return "Discord bot already running."
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="jarvis-discord", daemon=True)
        self._thread.start()
        return "Discord ticket bot starting…"

    def _run(self):
        try:
            asyncio.run(self._async_main())
        except Exception as e:
            if self.audit:
                self.audit.log(f"Discord bot stopped: {e}")

    async def _async_main(self):
        try:
            import discord
        except ImportError as e:
            raise RuntimeError("Install discord.py: pip install discord.py") from e

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        client = discord.Client(intents=intents)
        last_staff: dict[int, datetime] = {}

        @client.event
        async def on_ready():
            if self.audit:
                self.audit.log(f"Discord connected as {client.user}")

        @client.event
        async def on_guild_channel_create(channel):
            if not _channel_is_ticket(channel, self.cfg):
                return
            server_id = str(self.cfg.get("server_id") or "")
            if server_id and str(channel.guild.id) != server_id:
                return
            await channel.send(self.logic.opening_message())

        @client.event
        async def on_message(message):
            if message.author.bot:
                return
            text = (message.content or "").strip()
            if not text:
                return

            # Private messages — this is the phone path
            if message.guild is None:
                reply = "I'm here."
                if self.brain:
                    try:
                        reply = self.brain.chat(text)
                    except Exception as e:
                        reply = f"Give me a moment — I hit a snag: {e}"
                await message.channel.send((reply or "I'm here.")[:1900])
                for pending in list(self._pending_files):
                    try:
                        await message.channel.send(file=discord.File(str(pending)))
                    except Exception:
                        await message.channel.send(f"Couldn't attach {pending.name}.")
                    try:
                        self._pending_files.remove(pending)
                    except ValueError:
                        pass
                self.last_dm = message.channel.id
                if self.audit:
                    self.audit.log("Discord DM answered")
                return

            guild = message.guild
            server_id = str(self.cfg.get("server_id") or "")
            if server_id and str(guild.id) != server_id:
                return
            if not _channel_is_ticket(message.channel, self.cfg):
                return

            role_ids = [str(r.id) for r in getattr(message.author, "roles", [])]
            staff = self.logic.is_staff(role_ids)
            if staff:
                last_staff[message.channel.id] = datetime.now(timezone.utc)
                return

            last = last_staff.get(message.channel.id)
            if last:
                mins = (datetime.now(timezone.utc) - last).total_seconds() / 60
                if self.logic.should_stay_silent(mins):
                    return

            has_vault = self.logic.has_vault_role(role_ids)
            text = (message.content or "").strip()
            wants_script = any(
                w in text.lower()
                for w in ("script", "gpc", ".gpc", "send me", "give me", "vault file")
            )

            if wants_script and not has_vault:
                await message.channel.send(self.logic.vault_denied_message())
                if self.audit:
                    self.audit.log("Discord: vault denied (no role)")
                return

            if wants_script and has_vault:
                # Describe / search locally — do not attach files unless explicitly allowed
                q = text
                if self.vault:
                    hits = self.vault.search(q)
                    if hits:
                        names = "\n".join(f"- {h['game']}: {h['name']}" for h in hits[:8])
                        await message.channel.send(
                            "I found these in the Vault library (names only — "
                            "I won't attach the files here unless Ty's process says to):\n"
                            + names
                        )
                        return
                await message.channel.send(
                    "You've got Vault, so I can help with scripts. Tell me the game and what you need."
                )
                return

            # New / generic help
            if not has_vault and len(text) < 8:
                await message.channel.send(self.logic.opening_message())
                await message.channel.send(self.logic.vault_denied_message())
                return

            reply = None
            if self.brain:
                try:
                    reply = self.brain.chat(text)
                except Exception as e:
                    reply = f"Give me a moment — I hit a snag: {e}"
            await message.channel.send(reply or self.logic.opening_message())

        token = self.cfg.get("bot_token")
        await client.start(token)
