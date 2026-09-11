"""
Discord support module — bot-based design only (no user self-bots).

This module encodes Orla Vault ticket rules. Wiring a live bot requires
discord.py + bot_token in config; the core app runs without Discord enabled.
"""


class DiscordSupportLogic:
    def __init__(self, settings: dict):
        self.cfg = settings.get("discord") or {}

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled") and self.cfg.get("bot_token"))

    def has_vault_role(self, member_role_ids: list[str]) -> bool:
        vault = str(self.cfg.get("vault_role_id") or "")
        if not vault:
            return False
        return vault in [str(r) for r in member_role_ids]

    def is_staff(self, member_role_ids: list[str]) -> bool:
        ids = {str(self.cfg.get(k) or "") for k in ("staff_role_id", "dev_role_id", "admin_role_id")}
        ids.discard("")
        return any(r in ids for r in [str(x) for x in member_role_ids])

    def vault_denied_message(self) -> str:
        info = self.cfg.get("purchase_info") or "Vault access is required."
        url = self.cfg.get("purchase_url") or ""
        msg = (
            "I'm sorry, but you don't currently have Vault, so we can't provide support "
            f"for Vault scripts or send those files. {info}"
        )
        if url:
            msg += f"\n{url}"
        return msg

    def opening_message(self) -> str:
        return self.cfg.get("opening_message") or "Hi, how can I help you today?"

    def should_stay_silent(self, minutes_since_staff: float | None) -> bool:
        if minutes_since_staff is None:
            return False
        limit = float(self.cfg.get("staff_inactivity_minutes") or 60)
        return minutes_since_staff < limit

    def may_follow_up(self, minutes_since_customer: float | None) -> bool:
        if minutes_since_customer is None:
            return False
        limit = float(self.cfg.get("customer_followup_minutes") or 10)
        return minutes_since_customer >= limit
