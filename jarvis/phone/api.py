"""
Phone access foundation.

Production must use TLS, device pairing, short-lived tokens, and explicit
command permissions. This module only documents the surface and stores config.
"""


class PhoneAPI:
    def __init__(self, settings: dict):
        self.cfg = settings.get("phone") or {}

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled"))

    def status(self) -> str:
        if not self.enabled:
            return "Phone API disabled. Enable in settings and pair a device with auth_token."
        return (
            f"Phone API configured on {self.cfg.get('bind')}:{self.cfg.get('port')} "
            "(start a secure listener before exposing beyond localhost)."
        )
