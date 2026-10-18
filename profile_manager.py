"""
Autonomous Bot Profile Manager for Jio Gemini Hunter Bot.
Adheres strictly to PRD.md §4.2 and §4.3.
Manages hash-guarded, idempotent updates to bot display name, About bio,
empty-chat description, profile avatar logo, and scoped command menus.
"""
from __future__ import annotations
import hashlib
import logging
import os
from typing import Dict, Any, List
from telegram import Bot, BotCommand, BotCommandScopeDefault, BotCommandScopeChat, InputFile, InputProfilePhotoStatic
from telegram.error import TelegramError

from db_manager import db_manager

logger = logging.getLogger(__name__)

# Default Project Profile Constants from PRD §1
DEFAULT_BOT_NAME = "⚡ Jio Gemini Pro 18M Hunter"
DEFAULT_ABOUT_TEXT = "💎 Automated Jio 18-Month Google Gemini Pro Hunter & Claim Engine with Zero-Loss Balance Protection."
DEFAULT_DESCRIPTION_TEXT = (
    "⚡ 𝐉𝐈𝐎 𝐆𝐄𝐌ＩＮＩ 𝟏𝟖-𝐌𝐎𝐍𝐓𝐇 𝐇𝐔𝐍𝐓𝐄𝐑 ⚡\n\n"
    "Autonomous Google Gemini Pro 18-Month subscription generator partnered with Reliance Jio.\n\n"
    "🛡️ Key Capabilities:\n"
    "• 🛒 Instant Indian Number Hunting & Active Jio Verification\n"
    "• 📩 Automated MyJio 6-Digit OTP Extraction\n"
    "• 🎁 1-Click 18-Month Google Gemini Pro SKU (Z0241) Generation\n"
    "• 🛡️ Zero-Loss Auto-Refund Watcher (Non-Jio numbers 100% refunded)\n\n"
    "👉 Press [START] below to launch your interactive dashboard!"
)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "brand")
DEFAULT_LOGO_JPG = os.path.join(ASSETS_DIR, "logo.jpg")


def compute_sha256(content: str | bytes) -> str:
    """Compute SHA-256 hex digest for string or file bytes."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


class ProfileManager:
    """Applies Telegram profile settings automatically and idempotently."""

    def __init__(
        self,
        name: str = DEFAULT_BOT_NAME,
        about: str = DEFAULT_ABOUT_TEXT,
        description: str = DEFAULT_DESCRIPTION_TEXT,
        logo_path: str = DEFAULT_LOGO_JPG,
    ):
        self.name = name[:64]
        self.about = about[:120]
        self.description = description[:512]
        self.logo_path = logo_path

    def ensure_logo_jpg(self) -> str | None:
        """
        Verify logo file exists and is in JPG format.
        If given a PNG/SVG, converts onto solid #0F172A brand background.
        """
        if not os.path.exists(self.logo_path):
            # Check if assets generator can create it
            gen_script = os.path.join(ASSETS_DIR, "generate_assets.py")
            if os.path.exists(gen_script):
                try:
                    import subprocess, sys
                    subprocess.run([sys.executable, gen_script], check=True, capture_output=True)
                except Exception as e:
                    logger.warning(f"Could not auto-generate brand assets: {e}")

        if not os.path.exists(self.logo_path):
            return None

        # Verify extension
        if not self.logo_path.lower().endswith((".jpg", ".jpeg")):
            try:
                from PIL import Image
                img = Image.open(self.logo_path).convert("RGBA")
                bg = Image.new("RGBA", img.size, (15, 23, 42, 255))
                composite = Image.alpha_composite(bg, img).convert("RGB")
                target_jpg = os.path.splitext(self.logo_path)[0] + ".jpg"
                composite.save(target_jpg, "JPEG", quality=95)
                self.logo_path = target_jpg
            except Exception as e:
                logger.warning(f"Logo conversion to JPG failed: {e}")
                return None

        return self.logo_path

    async def apply_profile(self, bot: Bot, force: bool = False) -> Dict[str, str]:
        """
        Apply Name, About, Description, and Profile Photo if changed.
        Returns a dictionary of step results: {'name': 'ok|unchanged|failed', ...}
        """
        results: Dict[str, str] = {}

        # 1. Bot Name (setMyName)
        name_hash = compute_sha256(self.name)
        cached_name_hash = db_manager.get_profile_meta("name_hash")
        if force or name_hash != cached_name_hash:
            try:
                await bot.set_my_name(name=self.name)
                db_manager.set_profile_meta("name_hash", name_hash)
                results["name"] = "ok"
                logger.info(f"Updated Bot Name -> {self.name}")
            except Exception as e:
                results["name"] = f"FAILED: {e}"
                logger.warning(f"setMyName failed: {e}")
        else:
            results["name"] = "unchanged"

        # 2. About Bio (setMyShortDescription)
        about_hash = compute_sha256(self.about)
        cached_about_hash = db_manager.get_profile_meta("about_hash")
        if force or about_hash != cached_about_hash:
            try:
                await bot.set_my_short_description(short_description=self.about)
                db_manager.set_profile_meta("about_hash", about_hash)
                results["about"] = "ok"
                logger.info(f"Updated Bot About bio -> {self.about}")
            except Exception as e:
                results["about"] = f"FAILED: {e}"
                logger.warning(f"setMyShortDescription failed: {e}")
        else:
            results["about"] = "unchanged"

        # 3. Description (setMyDescription)
        desc_hash = compute_sha256(self.description)
        cached_desc_hash = db_manager.get_profile_meta("desc_hash")
        if force or desc_hash != cached_desc_hash:
            try:
                await bot.set_my_description(description=self.description)
                db_manager.set_profile_meta("desc_hash", desc_hash)
                results["description"] = "ok"
                logger.info("Updated Bot Description text")
            except Exception as e:
                results["description"] = f"FAILED: {e}"
                logger.warning(f"setMyDescription failed: {e}")
        else:
            results["description"] = "unchanged"

        # 4. Profile Photo (setMyProfilePhoto)
        valid_logo_path = self.ensure_logo_jpg()
        if valid_logo_path and os.path.exists(valid_logo_path):
            with open(valid_logo_path, "rb") as f:
                logo_bytes = f.read()
            logo_hash = compute_sha256(logo_bytes)
            cached_logo_hash = db_manager.get_profile_meta("logo_hash")

            if force or logo_hash != cached_logo_hash:
                try:
                    with open(valid_logo_path, "rb") as f:
                        await bot.set_my_profile_photo(photo=InputProfilePhotoStatic(photo=f))
                    db_manager.set_profile_meta("logo_hash", logo_hash)
                    results["logo"] = "ok"
                    logger.info("Updated Bot Profile Photo (Logo)")
                except Exception as e:
                    results["logo"] = f"FAILED: {e}"
                    logger.warning(f"setMyProfilePhoto failed: {e}")
            else:
                results["logo"] = "unchanged"
        else:
            results["logo"] = "skipped (no logo file)"

        return results

    async def register_scoped_commands(self, bot: Bot, admin_ids: List[int]) -> None:
        """
        Register commands scoped by role:
        1. Public default scope for all users
        2. Admin chat scope for designated administrators
        """
        # User Commands
        user_commands = [
            BotCommand("start", "⚡ Open Main Control Dashboard"),
            BotCommand("menu", "📋 Open Interactive Menu"),
            BotCommand("buy", "🛒 Rent & test 1 number for 18-mo Gemini"),
            BotCommand("autoscan", "⚡ Continuous auto-hunt loop"),
            BotCommand("stop", "🛑 Halt running task & refund balance"),
            BotCommand("balance", "💰 Check Grizzly SMS wallet balance"),
            BotCommand("active_numbers", "📱 List active numbers & cancel"),
            BotCommand("saved_links", "📜 View claimed 18-month Gemini links"),
            BotCommand("help", "📖 Comprehensive user guide & FAQ"),
        ]

        # Admin Commands (User commands + Administrative commands)
        admin_commands = user_commands + [
            BotCommand("admin", "⚙️ Open Administrator Control Hub"),
            BotCommand("users", "👥 List & manage authorized allowlist"),
            BotCommand("invite", "🎟️ Generate 48h single-use deep link"),
            BotCommand("mode", "🛡️ View or toggle access mode"),
            BotCommand("clear", "🧹 Clear messages in this chat"),
            BotCommand("clearall", "💥 Clear messages across all chats"),
            BotCommand("status", "📊 System engine status matrix"),
            BotCommand("setup", "🔄 Force re-sync Telegram profile"),
            BotCommand("set_price", "💵 Set maximum price budget cap"),
            BotCommand("set_service", "🏷️ Set Grizzly service code"),
            BotCommand("set_api_key", "🔑 Configure Grizzly SMS API key"),
        ]

        try:
            # 1. Register Default Scope (Regular Users)
            await bot.set_my_commands(commands=user_commands, scope=BotCommandScopeDefault())

            # 2. Register Admin Scopes (Admin Chats)
            for admin_id in admin_ids:
                try:
                    await bot.set_my_commands(commands=admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
                except Exception as e:
                    logger.debug(f"Could not set admin scope for {admin_id}: {e}")
        except Exception as e:
            logger.warning(f"Command registration encountered error: {e}")


# Global singleton instance
profile_manager = ProfileManager()
