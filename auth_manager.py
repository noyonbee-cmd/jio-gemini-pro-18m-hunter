"""
Access Control Layer & Security Gatekeeper for Jio Gemini Hunter Bot.
Adheres strictly to PRD.md §4.4 and §4.5.
Provides role resolution, mode gating, callback tap-time verification,
deep-link invite generation, and audit logging.
"""
from __future__ import annotations
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Set
from telegram import Update
from telegram.ext import ContextTypes

from config import ENV_FILE, save_env_variable
from db_manager import db_manager


class AuthManager:
    """Manages bot access roles, modes, gatekeeper hooks, and invites."""

    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ROLE_BLOCKED = "blocked"

    MODE_ADMIN_ONLY = "admin_only"
    MODE_ALLOWLIST = "allowlist"
    MODE_PUBLIC = "public"

    def __init__(self):
        # In-memory denial rate-limit tracking: {user_id: last_denial_timestamp}
        self._denial_history: dict[int, float] = {}

    def get_admin_ids(self) -> Set[int]:
        """Parse numeric admin IDs from environment."""
        raw = os.getenv("ADMIN_IDS", "").strip()
        ids: Set[int] = set()
        if raw:
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.add(int(part))
        return ids

    def is_admin(self, user_id: int) -> bool:
        """Check if user is a designated administrator."""
        return user_id in self.get_admin_ids()

    def get_access_mode(self) -> str:
        """Get currently configured access mode (default: admin_only)."""
        mode = db_manager.get_setting("access_mode", "").lower().strip()
        if mode in (self.MODE_ADMIN_ONLY, self.MODE_ALLOWLIST, self.MODE_PUBLIC):
            return mode
        env_mode = os.getenv("ACCESS_MODE", "").lower().strip()
        if env_mode in (self.MODE_ADMIN_ONLY, self.MODE_ALLOWLIST, self.MODE_PUBLIC):
            return env_mode
        return self.MODE_ADMIN_ONLY

    def set_access_mode(self, mode: str, admin_id: int = 0) -> bool:
        """Set active access mode and log admin action."""
        mode = mode.lower().strip()
        if mode not in (self.MODE_ADMIN_ONLY, self.MODE_ALLOWLIST, self.MODE_PUBLIC):
            return False
        db_manager.set_setting("access_mode", mode)
        save_env_variable("ACCESS_MODE", mode)
        db_manager.log_admin_action(admin_id, "CHANGE_ACCESS_MODE", details=f"Mode set to {mode}")
        return True

    def get_user_role(self, user_id: int) -> str:
        """Resolve role for user based on admin list, allowlist, and active mode."""
        if self.is_admin(user_id):
            return self.ROLE_ADMIN

        mode = self.get_access_mode()
        if mode == self.MODE_ADMIN_ONLY:
            return self.ROLE_BLOCKED

        if mode == self.MODE_ALLOWLIST:
            if db_manager.is_user_authorized(user_id):
                return self.ROLE_USER
            return self.ROLE_BLOCKED

        # MODE_PUBLIC
        return self.ROLE_USER

    def is_authorized(self, user_id: int) -> bool:
        """Return True if user has admin or user permission."""
        role = self.get_user_role(user_id)
        return role in (self.ROLE_ADMIN, self.ROLE_USER)

    def is_user_authorized(self, user_id: int) -> bool:
        """Alias for is_authorized."""
        return self.is_authorized(user_id)

    def should_notify_denial(self, user_id: int, cooldown_seconds: int = 3600) -> bool:
        """
        Rate-limit denial notices to at most once per hour (3600s).
        Returns True if a denial notification should be sent, False if dropped silently.
        """
        now = time.time()
        last = self._denial_history.get(user_id, 0.0)
        if now - last >= cooldown_seconds:
            self._denial_history[user_id] = now
            return True
        return False

    def create_invite_link(self, admin_id: int, bot_username: str, hours_valid: int = 48) -> tuple[str, str]:
        """
        Generate a single-use 48-hour deep-link invite code.
        Returns: (deep_link_url, raw_token)
        """
        token = secrets.token_hex(8)  # 16 characters
        expires_at = datetime.now(timezone.utc) + timedelta(hours=hours_valid)
        expires_iso = expires_at.isoformat()
        db_manager.create_invite_token(token, created_by=admin_id, expires_at_iso=expires_iso)
        db_manager.log_admin_action(admin_id, "GENERATE_INVITE", target_id=token, details=f"Expires {expires_iso}")
        link = f"https://t.me/{bot_username.lstrip('@')}?start=inv_{token}"
        return link, token

    def redeem_invite_code(self, token: str, user_id: int, username: str = "", first_name: str = "") -> tuple[bool, str]:
        """
        Attempt to atomically redeem an invite token.
        """
        token_data = db_manager.get_invite_token(token)
        if not token_data:
            return False, "Invalid or unrecognized invite link."

        if token_data.get("used_by"):
            return False, "This invite link has already been used."

        expires_str = token_data.get("expires_at", "")
        if expires_str:
            try:
                exp_dt = datetime.fromisoformat(expires_str)
                if datetime.now(timezone.utc) > exp_dt:
                    return False, "This invite link has expired (48-hour limit)."
            except Exception:
                pass

        # Atomic redemption in DB
        redeemed = db_manager.redeem_invite_token(token, user_id)
        if not redeemed:
            return False, "Failed to redeem invite token. It may have already been claimed."

        # Add to authorized allowlist
        db_manager.add_authorized_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            added_by=token_data.get("created_by", 0),
            notes=f"Redeemed invite token inv_{token}",
        )
        db_manager.log_admin_action(
            admin_id=token_data.get("created_by", 0),
            action="REDEEM_INVITE",
            target_id=str(user_id),
            details=f"Token inv_{token} redeemed by @{username} ({first_name})",
        )
        return True, "Invite verified! You have been granted access."


# Global singleton instance
auth_manager = AuthManager()
