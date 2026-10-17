"""
Jio Gemini 18-Month Hunter Telegram Bot.
Interactive bot for renting virtual Indian numbers, verifying Jio active status,
cancellation & refund balance protection, and automated 18-month Gemini claiming.
Integrated with Control Layer, Admin Gatekeeper, Clear-Chat Engine, and Brand Identity.
Adheres strictly to PRD.md and .agents/skills/telegram-bot-builder/SKILL.md.
"""
from __future__ import annotations
import asyncio
import logging
import os
import re
import sys
import time
from typing import Any

# Reconfigure Windows console encoding to UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf8"}:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN,
    GRIZZLY_API_KEY,
    DEFAULT_SERVICE_CODE,
    DEFAULT_MAX_PRICE,
    DEFAULT_COUNTRY_ID,
    OTP_TIMEOUT,
    POLL_INTERVAL,
    AUTO_SCAN_DELAY,
    LINKS_FILE,
    ENV_FILE,
    save_env_variable,
)
from task_manager import task_manager, CancellationToken
from db_manager import db_manager
from grizzly_client import grizzly_client
from jio_service import jio_service
from refund_agent import refund_agent
from auth_manager import auth_manager
from chat_cleaner import chat_cleaner
from profile_manager import profile_manager
from logger import (
    log_banner,
    log_tg,
    log_step,
    log_carrier_check,
    log_claim_success,
    log_refund,
    log_otp,
    log_bot_info,
    log_bot_warn,
    log_bot_err,
    setup_logger_filters,
)

# UI/UX Design System & Presenter
from ui_presenter import (
    render_dashboard_view,
    render_pipeline_step,
    render_rejection_card,
    render_otp_timeout_card,
    render_success_card,
    render_balance_view,
    render_active_numbers_view,
    render_saved_links_view,
    render_help_view,
    render_set_price_view,
    render_set_service_view,
    render_set_api_key_view,
    render_system_stats_view,
    render_admin_hub_view,
    render_users_list_view,
    render_access_denied_card,
    build_main_keyboard,
    build_stop_keyboard,
    build_sub_keyboard,
    build_prompt_cancel_keyboard,
    build_active_numbers_keyboard,
    build_saved_links_keyboard,
    build_success_keyboard,
    build_help_keyboard,
    build_admin_hub_keyboard,
    build_mode_selector_keyboard,
    build_users_list_keyboard,
    build_confirm_wipe_keyboard,
    render_progress_bar,
    mask_phone,
    SPINNER_FRAMES,
    BANNER_JPG_PATH,
)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Global user-configurable runtime state
RUNTIME_CONFIG = {
    "service_code": DEFAULT_SERVICE_CODE,
    "max_price": DEFAULT_MAX_PRICE,
    "country_id": DEFAULT_COUNTRY_ID,
}


def get_dashboard_content(chat_id: int, user_name: str, is_admin: bool = False) -> tuple[str, InlineKeyboardMarkup]:
    """Generate high-end dashboard text & dynamic inline keyboard."""
    success, balance, bal_str = grizzly_client.get_balance()
    balance_display = bal_str if success else "⚠️ API Key Needed"

    stats = db_manager.get_stats()
    ref_stats = db_manager.get_refund_stats()
    is_running = task_manager.is_running(chat_id)

    text = render_dashboard_view(
        user_name=user_name,
        balance_str=balance_display,
        service_code=RUNTIME_CONFIG["service_code"],
        max_price=RUNTIME_CONFIG["max_price"],
        stats=stats,
        ref_stats=ref_stats,
        is_running=is_running,
    )
    keyboard = build_main_keyboard(is_running, is_admin=is_admin)
    return text, keyboard


# ---------------------------------------------------------
# SECURITY GATEKEEPER & ACCESS CONTROL
# ---------------------------------------------------------

async def verify_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Dispatcher-level security gatekeeper.
    Enforces role authorization (admin_only, allowlist, public).
    Fails closed on error.
    """
    user = update.effective_user
    if not user:
        return True

    user_id = user.id
    chat = update.effective_chat

    # Track message ID for cleaner engine if in private chat
    if chat and chat.type == "private" and update.message:
        chat_cleaner.track_incoming(chat.id, update.message.message_id)

    # Allow deep-link invite redemption on /start inv_<code>
    if update.message and update.message.text:
        parts = update.message.text.strip().split()
        if len(parts) > 1 and parts[1].startswith("inv_"):
            return True

    # Check authorization
    if auth_manager.is_authorized(user_id):
        return True

    # Denied: handle callback query
    if update.callback_query:
        await update.callback_query.answer("⛔ Access Denied: Admin privileges or authorized invite required.", show_alert=True)
        return False

    # Denied: handle message with 1-hour rate limit
    if update.message and auth_manager.should_notify_denial(user_id):
        denied_card = render_access_denied_card()
        msg = await update.message.reply_text(denied_card, parse_mode=ParseMode.MARKDOWN)
        if chat:
            chat_cleaner.track_outgoing(chat.id, msg.message_id)

    return False


# ---------------------------------------------------------
# COMMAND HANDLERS
# ---------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start and /menu commands with welcome banner and deep invites."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    first_name = user.first_name if user else "User"
    username = user.username if user else ""
    user_id = user.id if user else 0
    is_admin = auth_manager.is_admin(user_id)

    log_tg("/start", username or str(chat_id), "Opened Main Dashboard")

    # Check deep-link invite parameter: /start inv_<token>
    if context.args and context.args[0].startswith("inv_"):
        token = context.args[0].replace("inv_", "").strip()
        ok, msg = auth_manager.redeem_invite_code(token, user_id, username, first_name)
        if ok:
            await update.effective_message.reply_text(f"🎉 **{msg}**\nWelcome to Jio Gemini Pro Hunter!")
        else:
            await update.effective_message.reply_text(f"⚠️ **Invite Error**: {msg}")

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    text, keyboard = get_dashboard_content(chat_id, first_name, is_admin=is_admin)

    # Attempt to send welcome banner via cached file_id or new upload
    if update.message and os.path.exists(BANNER_JPG_PATH):
        cached_file_id = db_manager.get_profile_meta("welcome_banner_file_id")
        photo_target = cached_file_id if cached_file_id else open(BANNER_JPG_PATH, "rb")
        try:
            sent_msg = await update.message.reply_photo(
                photo=photo_target,
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
            chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)

            # Cache file_id if newly uploaded
            if not cached_file_id and sent_msg.photo:
                new_file_id = sent_msg.photo[-1].file_id
                db_manager.set_profile_meta("welcome_banner_file_id", new_file_id)
            return
        except Exception as e:
            logger.debug(f"Banner photo dispatch failed, falling back to text: {e}")

    # Fallback / Callback in-place text update
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command and sticky stop button."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    is_admin = auth_manager.is_admin(update.effective_user.id)
    log_tg("/stop", user, "Stop requested by user")
    was_running = task_manager.stop_task(chat_id)

    if was_running:
        bar = render_progress_bar(0)
        msg = (
            "🛑 **TASK SAFELY HALTED BY USER**\n\n"
            f"{bar}\n\n"
            "┌─ 🛡️ **Safety Protocol Summary** ─────────────\n"
            "│ • Ongoing hunt pipeline was cleanly stopped.\n"
            "│ • In-flight numbers handed to Background Refund Watcher.\n"
            "│ • Balance protection: 100% refunded.\n"
            "└───────────────────────────────────────────────\n\n"
            "> System is idle and ready for your next command."
        )
    else:
        msg = "ℹ️ No task is currently running. Tap **[ 🛒 Buy 1 Number ]** to start."

    keyboard = build_main_keyboard(False, is_admin=is_admin)
    if update.callback_query:
        await update.callback_query.answer("Task stopped!")
        await update.callback_query.edit_message_text(msg, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(msg, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check Grizzly SMS balance and display financial matrix."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    success, bal, msg = grizzly_client.get_balance()
    log_tg("/balance", user, f"Balance query -> {msg}")
    ref_stats = db_manager.get_refund_stats()

    text = render_balance_view(msg, success, ref_stats)
    keyboard = build_sub_keyboard(refresh_callback="btn_balance")

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def active_numbers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List numbers in progress with manual cancellation buttons."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    numbers = db_manager.get_active_numbers()
    log_tg("/active_numbers", user, f"Active count: {len(numbers)}")

    text = render_active_numbers_view(numbers)
    keyboard = build_active_numbers_keyboard(numbers)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def saved_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    """List or export claimed Gemini 18-Month links with pagination."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)

    offers = db_manager.get_claimed_offers()
    log_tg("/saved_links", user, f"Claimed offers count: {len(offers)} (page {page})")

    text = render_saved_links_view(offers, page=page, per_page=4)
    keyboard = build_saved_links_keyboard(offers, page=page, per_page=4)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
    elif update.message:
        sent_msg = await update.message.reply_text(
            text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display comprehensive bot performance and productivity statistics."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    log_tg("/stats", user, "Queried system performance matrix")

    stats = db_manager.get_stats()
    ref_stats = db_manager.get_refund_stats()
    text = render_system_stats_view(stats, ref_stats, RUNTIME_CONFIG)
    keyboard = build_sub_keyboard(refresh_callback="btn_stats")

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, tab: str = "quickstart") -> None:
    """Display interactive multi-tab user manual."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    text = render_help_view(tab)
    keyboard = build_help_keyboard(tab)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


# ---------------------------------------------------------
# ADMINISTRATIVE COMMAND & CONTROL (PRD §4.4, §4.5, §4.6)
# ---------------------------------------------------------

async def admin_hub_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display administrator control hub."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        if update.callback_query:
            await update.callback_query.answer("⛔ Access Denied: Admin privileges required.", show_alert=True)
        return

    mode = auth_manager.get_access_mode()
    total_users = db_manager.get_authorized_users_count()
    tracked_chats = len(db_manager.get_all_tracked_chats())

    text = render_admin_hub_view(mode, total_users, tracked_chats)
    keyboard = build_admin_hub_keyboard(mode)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(update.effective_chat.id, sent_msg.message_id)


async def users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    """Display paginated allowlist of authorized users."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    per_page = 5
    total = db_manager.get_authorized_users_count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    users = db_manager.get_authorized_users(limit=per_page, offset=page * per_page)

    text = render_users_list_view(users, page, total_pages)
    keyboard = build_users_list_keyboard(users, page, total_pages)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(update.effective_chat.id, sent_msg.message_id)


async def invite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a single-use 48-hour deep-link invite."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    me = await context.bot.get_me()
    link, token = auth_manager.create_invite_link(admin_id=user_id, bot_username=me.username, hours_valid=48)

    text = (
        "🎟️ **NEW 48-HOUR INVITE LINK GENERATED**\n\n"
        f"• **Invite Link**:\n`{link}`\n\n"
        "• **Validity**: 48 Hours\n"
        "• **Usage**: Single-use only (automatically destroyed upon first claim)\n\n"
        "> Share this link with the user you wish to authorize."
    )
    keyboard = build_sub_keyboard(back_callback="btn_admin_hub")

    if update.callback_query:
        await update.callback_query.answer("Invite generated!")
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        sent_msg = await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(update.effective_chat.id, sent_msg.message_id)


async def adduser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add user ID to allowlist manually: /adduser <id> [notes]."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: `/adduser <numeric_telegram_id> [optional_notes]`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = int(context.args[0])
    notes = " ".join(context.args[1:]) if len(context.args) > 1 else "Manual add by admin"

    db_manager.add_authorized_user(user_id=target_id, added_by=user_id, notes=notes)
    db_manager.log_admin_action(user_id, "ADD_USER", target_id=str(target_id), details=notes)
    await update.message.reply_text(f"✅ User `{target_id}` added to authorized allowlist.", parse_mode=ParseMode.MARKDOWN)


async def removeuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove user from allowlist: /removeuser <id>."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: `/removeuser <numeric_telegram_id>`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = int(context.args[0])
    removed = db_manager.remove_authorized_user(target_id)
    if removed:
        db_manager.log_admin_action(user_id, "REMOVE_USER", target_id=str(target_id))
        await update.message.reply_text(f"✅ User `{target_id}` removed from allowlist.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"ℹ️ User `{target_id}` was not found in allowlist.", parse_mode=ParseMode.MARKDOWN)


async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display or toggle access mode: /mode [admin_only|allowlist|public]."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    if not context.args:
        cur_mode = auth_manager.get_access_mode()
        await update.message.reply_text(
            f"🛡️ Current Access Mode: `{cur_mode}`\n\nTo change, use `/mode <admin_only|allowlist|public>`.",
            reply_markup=build_mode_selector_keyboard(cur_mode),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target_mode = context.args[0].lower().strip()
    if auth_manager.set_access_mode(target_mode, admin_id=user_id):
        await update.message.reply_text(f"✅ Access Mode successfully updated to: `{target_mode}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Invalid mode. Choose from: `admin_only`, `allowlist`, `public`", parse_mode=ParseMode.MARKDOWN)


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute private chat message clean for admin: /clear [depth]."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    depth = 300
    if context.args and context.args[0].isdigit():
        depth = min(1500, int(context.args[0]))

    chat_id = update.effective_chat.id
    progress_msg = await update.message.reply_text("🧹 Sweeping messages within 48-hour window...")
    report = await chat_cleaner.clear_chat(context.bot, chat_id, sweep_depth=depth)
    await progress_msg.edit_text(report, parse_mode=ParseMode.MARKDOWN)


async def clearall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute global chat clean across all tracked private chats: /clearall confirm."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    if not context.args or context.args[0].lower() != "confirm":
        await update.message.reply_text(
            "⚠️ **GLOBAL CHAT WIPE CONFIRMATION REQUIRED**\n\n"
            "This operation will delete all tracked messages younger than 48 hours across ALL private user chats.\n\n"
            "To proceed, send: `/clearall confirm`",
            reply_markup=build_confirm_wipe_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    progress_msg = await update.message.reply_text("💥 Executing global chat clean across all tracked chats...")
    report = await chat_cleaner.clear_all_chats(context.bot, limit_chats=25)
    db_manager.log_admin_action(user_id, "CLEAR_ALL_CHATS", details="Cleaned tracked private chats")
    await progress_msg.edit_text(report, parse_mode=ParseMode.MARKDOWN)


async def setup_cmd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force re-sync bot profile on Telegram: /setup [force]."""
    user_id = update.effective_user.id
    if not auth_manager.is_admin(user_id):
        return

    force = bool(context.args and context.args[0].lower() == "force")
    status_msg = await update.message.reply_text("🔄 Synchronizing Telegram Bot Profile...")
    res = await profile_manager.apply_profile(context.bot, force=force)

    report = "🎨 **PROFILE SYNCHRONIZATION REPORT**\n\n"
    for k, v in res.items():
        report += f"• **{k.capitalize()}**: `{v}`\n"
    await status_msg.edit_text(report, parse_mode=ParseMode.MARKDOWN)


async def safe_edit_text(message, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    """Safely edit message text with graceful fallback if markdown entity parsing fails."""
    try:
        return await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "Can't parse entities" in str(e) or "entity" in str(e).lower():
            clean_text = text.replace("**", "").replace("`", "")
            try:
                return await message.edit_text(clean_text, reply_markup=reply_markup, parse_mode=None)
            except Exception:
                pass
        raise


async def execute_single_hunt(chat_id: int, context: ContextTypes.DEFAULT_TYPE, token: CancellationToken, message) -> bool:
    """
    Executes single acquisition, active Jio check, 6-digit OTP polling, and Gemini claim.
    Returns True if an 18-month Gemini link was claimed, False otherwise.
    Strictly preserves backend engine while upgrading all visual presentations.
    """
    stop_keyboard = build_stop_keyboard()

    # ------------------ STEP 1: RENT NUMBER (15%) ------------------
    log_step(1, 5, "Rent Virtual Number via Grizzly SMS", f"Service={RUNTIME_CONFIG['service_code']} | MaxPrice=${RUNTIME_CONFIG['max_price']:.2f}")
    
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    text_step1 = render_pipeline_step(
        step_num=1,
        total_steps=5,
        title="Rent Indian Virtual Number",
        subtitle=f"Querying Grizzly SMS for `{RUNTIME_CONFIG['service_code']}`...",
        percent=15,
        spinner_idx=1,
    )
    await safe_edit_text(message, text_step1, reply_markup=stop_keyboard, parse_mode=ParseMode.MARKDOWN)

    if token.is_cancelled:
        return False

    success, order, err_msg = grizzly_client.get_number(
        service=RUNTIME_CONFIG["service_code"],
        country=RUNTIME_CONFIG["country_id"],
        max_price=RUNTIME_CONFIG["max_price"],
    )

    if not success:
        log_bot_warn(f"Rental failed: {err_msg}")
        bar = render_progress_bar(0)
        await safe_edit_text(
            message,
            f"❌ **NUMBER ACQUISITION PAUSED**\n\n"
            f"{bar}\n\n"
            f"• **Notice**: `{err_msg}`\n"
            f"• **Tip**: Try raising price cap via `/set_price <amount>` or retrying in a moment.",
            reply_markup=build_main_keyboard(False),
            parse_mode=ParseMode.MARKDOWN,
        )
        return False

    act_id = order["activation_id"]
    phone = order["phone_number"]
    cost = order["cost"]
    p_epoch = order.get("purchased_epoch", time.time())

    token.register_cleanup(
        lambda: refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason="User stopped task",
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
    )
    db_manager.add_number(act_id, phone, service_code=RUNTIME_CONFIG["service_code"], cost=cost)

    # ------------------ STEP 2: JIO CARRIER & ACTIVE STATUS CHECK (35%) ------------------
    log_step(2, 5, "Validate Reliance Jio Carrier & Active Plan", f"Mobile=+{phone} | Cost=${cost:.2f} | ActID=#{act_id}")
    
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    text_step2 = render_pipeline_step(
        step_num=2,
        total_steps=5,
        title="Verify Reliance Jio Carrier & Plan",
        subtitle="Verifying mobility subscriber & active plan...",
        percent=35,
        phone=phone,
        cost=cost,
        spinner_idx=2,
    )
    await safe_edit_text(message, text_step2, reply_markup=stop_keyboard, parse_mode=ParseMode.MARKDOWN)

    if token.is_cancelled:
        return False

    is_jio, is_active, details, reason = jio_service.check_carrier_and_plan(phone)

    if not is_jio or not is_active:
        refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason=reason,
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
        card = render_rejection_card(phone, reason, cost, cooldown_seconds=75)
        await safe_edit_text(message, card, reply_markup=build_main_keyboard(False), parse_mode=ParseMode.MARKDOWN)
        return False

    db_manager.update_status(act_id, status="VERIFIED", carrier_valid=True, plan_active=True)

    # ------------------ STEP 3: DISPATCH JIO OTP (50%) ------------------
    log_step(3, 5, "Dispatch Official Jio Login OTP", f"Mobile=+{phone} | Plan={reason}")
    
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    text_step3 = render_pipeline_step(
        step_num=3,
        total_steps=5,
        title="Dispatch MyJio 6-Digit OTP",
        subtitle="Requesting official login verification code from Jio...",
        percent=50,
        phone=phone,
        cost=cost,
        spinner_idx=3,
    )
    await safe_edit_text(message, text_step3, reply_markup=stop_keyboard, parse_mode=ParseMode.MARKDOWN)

    if token.is_cancelled:
        return False

    otp_sent, send_msg = jio_service.send_otp(phone)
    if not otp_sent:
        log_bot_warn(f"Jio OTP dispatch failed for +{phone}: {send_msg}")
        refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason="OTP dispatch error: " + send_msg,
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
        bar = render_progress_bar(0)
        await safe_edit_text(
            message,
            f"⚠️ **JIO OTP DISPATCH FAILED**\n\n"
            f"{bar}\n\n"
            f"• **Target**: `+{phone}`\n"
            f"• **Details**: {send_msg}\n"
            f"• **Auto-Refund Guard**: Number queued for 100% balance refund.",
            reply_markup=build_main_keyboard(False),
            parse_mode=ParseMode.MARKDOWN,
        )
        return False

    grizzly_client.notify_sms_sent(act_id)
    db_manager.update_status(act_id, status="OTP_PENDING")

    # ------------------ STEP 4: POLL FOR 6-DIGIT OTP (60% -> 88%) ------------------
    log_step(4, 5, "Poll 6-Digit MyJio OTP on Grizzly SMS", f"ActID=#{act_id} | Mobile=+{phone} | Timeout={OTP_TIMEOUT}s")
    last_update_time = 0

    def on_poll_progress(elapsed: int, total: int):
        nonlocal last_update_time
        if elapsed - last_update_time >= 3:
            last_update_time = elapsed
            pct = 60 + int((elapsed / max(1, total)) * 28)
            pct = min(88, pct)
            spinner_idx = int(elapsed) % len(SPINNER_FRAMES)
            text_step4 = render_pipeline_step(
                step_num=4,
                total_steps=5,
                title="Listen for 6-Digit MyJio SMS",
                subtitle="Monitoring Grizzly SMS panel...",
                percent=pct,
                phone=phone,
                cost=cost,
                elapsed=elapsed,
                total_timeout=total,
                spinner_idx=spinner_idx,
            )
            asyncio.run_coroutine_threadsafe(
                message.edit_text(text_step4, reply_markup=stop_keyboard, parse_mode=ParseMode.MARKDOWN),
                asyncio.get_event_loop(),
            )

    loop = asyncio.get_event_loop()
    otp_ok, otp_code, poll_msg = await loop.run_in_executor(
        None,
        lambda: grizzly_client.poll_otp(
            activation_id=act_id,
            timeout=OTP_TIMEOUT,
            poll_interval=POLL_INTERVAL,
            cancellation_token=token,
            progress_callback=on_poll_progress,
        ),
    )

    if not otp_ok:
        log_bot_warn(f"OTP polling failed or expired for +{phone}: {poll_msg}")
        refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason=f"OTP wait timed out ({OTP_TIMEOUT}s)",
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
        card = render_otp_timeout_card(phone, cost, OTP_TIMEOUT)
        await safe_edit_text(message, card, reply_markup=build_main_keyboard(False), parse_mode=ParseMode.MARKDOWN)
        return False

    # ------------------ STEP 5: VALIDATE OTP & CLAIM GEMINI 18-MONTH (92%) ------------------
    log_step(5, 5, "Validate OTP & Redeem 18-Month Google Gemini Pro (Z0241)", f"Mobile=+{phone} | OTP={otp_code}")
    
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    text_step5 = render_pipeline_step(
        step_num=5,
        total_steps=5,
        title="Redeem Google Gemini Pro (18 Months)",
        subtitle=f"OTP `{otp_code}` verified! Redeeming SKU Z0241...",
        percent=92,
        phone=phone,
        cost=cost,
        spinner_idx=5,
    )
    await safe_edit_text(message, text_step5, reply_markup=stop_keyboard, parse_mode=ParseMode.MARKDOWN)

    db_manager.update_status(act_id, status="OTP_RECEIVED", otp_code=otp_code)

    verify_ok, verify_msg = jio_service.verify_otp(phone, otp_code)
    if not verify_ok:
        log_bot_err(f"Jio OTP validation failed: {verify_msg}")
        refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason="OTP verification failed: " + verify_msg,
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
        bar = render_progress_bar(0)
        await safe_edit_text(
            message,
            f"❌ **OTP VERIFICATION FAILED**\n\n"
            f"{bar}\n\n"
            f"• **Target**: `+{phone}`\n"
            f"• **Details**: {verify_msg}\n"
            f"• **Auto-Refund Guard**: Number queued for 100% balance refund.",
            reply_markup=build_main_keyboard(False),
            parse_mode=ParseMode.MARKDOWN,
        )
        return False

    claim_ok, claim_url, claim_msg = jio_service.claim_gemini_18mo()
    if not claim_ok:
        log_bot_warn(f"Gemini claim response: {claim_msg}")
        refund_agent.queue_refund(
            activation_id=act_id,
            phone_number=phone,
            cost=cost,
            reason="Gemini claim: " + claim_msg,
            purchased_epoch=p_epoch,
            cooldown_seconds=75,
        )
        bar = render_progress_bar(0)
        await safe_edit_text(
            message,
            f"⚠️ **OFFER REDEMPTION NOTICE**\n\n"
            f"{bar}\n\n"
            f"• **Target**: `+{phone}`\n"
            f"• **Details**: {claim_msg}\n"
            f"• **Auto-Refund Guard**: Balance queued for 100% refund.",
            reply_markup=build_main_keyboard(False),
            parse_mode=ParseMode.MARKDOWN,
        )
        return False

    # Successfully claimed! Finalize order on Grizzly
    grizzly_client.complete_order(act_id)
    db_manager.save_claimed_offer(act_id, phone, claim_url, cost=cost)
    log_claim_success(phone, claim_url, cost)

    success_card = render_success_card(phone, cost, claim_url)
    success_keyboard = build_success_keyboard(claim_url)

    await safe_edit_text(message, success_card, reply_markup=success_keyboard, parse_mode=ParseMode.MARKDOWN)
    return True


async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate a single purchase, validation, and claim run."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    log_tg("/buy", user, "Initiating single Jio acquisition pipeline")

    if task_manager.is_running(chat_id):
        log_bot_warn(f"User @{user} attempted to start task while one is already running.")
        await update.effective_message.reply_text("⚠️ A task is already running! Tap **[ 🛑 STOP TASK ]** to abort.")
        return

    msg = await update.effective_message.reply_text("🚀 Initializing Jio Gemini acquisition pipeline...")
    chat_cleaner.track_outgoing(chat_id, msg.message_id)
    token = task_manager.start_task(chat_id, "buy_single")

    async def _runner():
        try:
            await execute_single_hunt(chat_id, context, token, msg)
        except Exception as e:
            logger.exception("Error during buy run")
            log_bot_err(f"Exception during buy: {e}")
            await msg.edit_text(f"❌ Error occurred: {e}", reply_markup=build_main_keyboard(False))
        finally:
            task_manager.cleanup(chat_id)

    async_task = asyncio.create_task(_runner())
    task_manager.attach_async_task(chat_id, async_task)


async def autoscan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loop numbers until an 18-month Gemini offer is claimed or limit reached."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)

    if task_manager.is_running(chat_id):
        log_bot_warn(f"User @{user} attempted /autoscan while task is active.")
        await update.effective_message.reply_text("⚠️ A task is already running! Use /stop or click Stop to cancel.")
        return

    limit = 10
    if context.args and context.args[0].isdigit():
        limit = min(50, int(context.args[0]))

    log_tg("/autoscan", user, f"Initiating loop scan (limit={limit})")
    msg = await update.effective_message.reply_text(f"⚡ Starting Auto-Hunt loop (Max attempts: {limit})...")
    chat_cleaner.track_outgoing(chat_id, msg.message_id)
    token = task_manager.start_task(chat_id, "autoscan")

    async def _autoscan_runner():
        claimed_count = 0
        try:
            for attempt in range(1, limit + 1):
                if token.is_cancelled:
                    log_bot_info("Auto-hunt aborted due to cancellation token.")
                    break

                pct = int(((attempt - 1) / limit) * 100)
                bar = render_progress_bar(pct)
                log_bot_info(f"Auto-Hunt Attempt [{attempt}/{limit}] in progress...")
                await msg.edit_text(
                    f"⚡ **AUTO-HUNT IN PROGRESS** [Round {attempt}/{limit}]\n\n"
                    f"{bar}\n\n"
                    f"• Searching for eligible Jio number...\n"
                    f"• Refund Watcher active (non-Jio numbers refunded automatically).",
                    reply_markup=build_stop_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )

                claimed = await execute_single_hunt(chat_id, context, token, msg)
                if claimed:
                    claimed_count += 1
                    break

                await asyncio.sleep(AUTO_SCAN_DELAY)

            if not claimed_count and not token.is_cancelled:
                bar = render_progress_bar(100)
                await msg.edit_text(
                    f"🏁 **Auto-Hunt Cycle Complete** [{limit}/{limit}]\n\n"
                    f"{bar}\n\n"
                    f"• Reached {limit} attempts without new activation.\n"
                    f"• Any non-Jio numbers were queued for auto-refund in background.\n"
                    f"• Zero credit waste guaranteed.",
                    reply_markup=build_main_keyboard(False),
                    parse_mode=ParseMode.MARKDOWN,
                )
        except Exception as e:
            logger.exception("Error during autoscan")
            log_bot_err(f"Exception during autoscan: {e}")
            bar = render_progress_bar(0)
            await msg.edit_text(f"❌ Auto-hunt error: {e}", reply_markup=build_main_keyboard(False))
        finally:
            task_manager.cleanup(chat_id)

    async_task = asyncio.create_task(_autoscan_runner())
    task_manager.attach_async_task(chat_id, async_task)


# ---------------------------------------------------------
# INTERACTIVE SETTINGS & PROMPT HANDLERS
# ---------------------------------------------------------

async def cancel_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle manual cancel & refund button for specific activation ID."""
    query = update.callback_query
    await query.answer("Queueing refund...")
    match = re.match(r"^cancel_id_(\d+)$", query.data)
    if not match:
        return

    act_id = int(match.group(1))
    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    log_tg("MANUAL_REFUND", user, f"ActID=#{act_id}")

    num_data = db_manager.get_number(act_id)
    phone = num_data["phone_number"] if num_data else ""
    cost = num_data["cost"] if num_data else 0.10

    refund_agent.queue_refund(
        activation_id=act_id,
        phone_number=phone,
        cost=cost,
        reason="Manual user refund",
        purchased_epoch=time.time() - 90,
        cooldown_seconds=75,
    )
    bar = render_progress_bar(100)
    await query.edit_message_text(
        f"🛑 **Order #{act_id} Queued for Refund**\n\n"
        f"{bar}\n\n"
        "• Background Refund Watcher is monitoring the cooldown window.\n"
        "• Balance will be restored automatically upon panel confirmation.",
        reply_markup=build_main_keyboard(False),
        parse_mode=ParseMode.MARKDOWN,
    )


async def set_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set custom max price for number rental."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    if not context.args:
        log_tg("/set_price", user, "Prompted for price input")
        context.user_data["awaiting_max_price"] = True
        text = render_set_price_view(RUNTIME_CONFIG["max_price"])
        keyboard = build_prompt_cancel_keyboard()
    else:
        try:
            new_price = float(context.args[0])
            RUNTIME_CONFIG["max_price"] = new_price
            save_env_variable("DEFAULT_MAX_PRICE", f"{new_price:.2f}")
            log_tg("/set_price", user, f"Updated max price to ${new_price:.2f}")
            text = f"✅ **Max Price Budget Updated & Saved:** `${new_price:.2f} USD`"
        except ValueError:
            text = "❌ Invalid amount. Example: `/set_price 0.50`"
        keyboard = build_main_keyboard(False)

    sent_msg = await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def set_service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set custom service code on Grizzly SMS."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    if not context.args:
        log_tg("/set_service", user, "Prompted for service code input")
        context.user_data["awaiting_service_code"] = True
        text = render_set_service_view(RUNTIME_CONFIG["service_code"])
        keyboard = build_prompt_cancel_keyboard()
    else:
        raw_code = context.args[0].strip()
        clean_code = grizzly_client.normalize_service_code(raw_code)
        RUNTIME_CONFIG["service_code"] = clean_code
        save_env_variable("DEFAULT_SERVICE_CODE", clean_code)
        log_tg("/set_service", user, f"Updated service code to '{clean_code}' (from '{raw_code}')")
        text = f"✅ **Service Code Updated & Saved:** `{clean_code}`"
        if clean_code != raw_code.lower():
            text += f" *(Mapped to official code `{clean_code}`)*"
        keyboard = build_main_keyboard(False)

    sent_msg = await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)


async def process_api_key_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, candidate_key: str) -> None:
    """Test candidate API key live, fetch balance, and persist to .env if valid."""
    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    log_tg("SETUP_API_KEY", user, f"Testing key: {candidate_key[:6]}...")
    progress_msg = await update.effective_message.reply_text("🔄 Testing API key with Grizzly SMS...")
    chat_cleaner.track_outgoing(chat_id, progress_msg.message_id)

    loop = asyncio.get_event_loop()
    is_valid, balance, msg = await loop.run_in_executor(
        None, lambda: grizzly_client.test_and_save_api_key(candidate_key)
    )

    if is_valid:
        log_bot_info(f"API Key successfully verified for @{user}. Balance: ${balance:.2f} USD")
        text = (
            "🎉 **GRIZZLY SMS API KEY CONNECTED SUCCESSFULLY!**\n\n"
            f"• **Status**: Active & Ready ✅\n"
            f"• **Wallet Balance**: `${balance:.2f} USD` 💰\n"
            "• **Storage**: Persisted permanently to `.env`\n\n"
            "👉 Tap **[ 🛒 Buy 1 Number ]** or **[ ⚡ Auto-Hunt ]** to begin claiming 18-month Gemini offers!"
        )
    else:
        log_bot_warn(f"API Key validation failed for @{user}: {msg}")
        text = (
            "❌ **API Key Validation Failed!**\n\n"
            f"• **Server Response**: `{msg}`\n\n"
            "Please check that you copied the complete API key from https://grizzlysms.com/ and try again."
        )

    keyboard = build_main_keyboard(False)
    await progress_msg.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


async def set_api_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set and validate Grizzly SMS API key."""
    if not await verify_access(update, context):
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)
    if not context.args:
        log_tg("/set_api_key", user, "Prompted for API key input")
        context.user_data["awaiting_api_key"] = True
        text = render_set_api_key_view()
        keyboard = build_prompt_cancel_keyboard()
        sent_msg = await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)
        return

    new_key = context.args[0].strip()
    await process_api_key_submission(update, context, new_key)


async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text replies when user is prompted for API key, price, or service code."""
    if not update.message or not update.message.text:
        return

    if not await verify_access(update, context):
        return

    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    user = update.effective_user.username or str(chat_id)

    # 1. API key prompt
    if context.user_data.pop("awaiting_api_key", False):
        await process_api_key_submission(update, context, text)
        return

    # 2. Max price prompt
    if context.user_data.pop("awaiting_max_price", False):
        log_tg("SET_PRICE_TEXT", user, f"Input: {text}")
        try:
            new_price = float(text)
            RUNTIME_CONFIG["max_price"] = new_price
            save_env_variable("DEFAULT_MAX_PRICE", f"{new_price:.2f}")
            log_bot_info(f"Updated Max Price to ${new_price:.2f}")
            reply = f"✅ **Max Price Budget Updated & Saved:** `${new_price:.2f} USD`"
        except ValueError:
            reply = "❌ Invalid number. Please enter a valid number like `0.50`."
        sent_msg = await update.message.reply_text(reply, reply_markup=build_main_keyboard(False), parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)
        return

    # 3. Service code prompt
    if context.user_data.pop("awaiting_service_code", False):
        clean_code = grizzly_client.normalize_service_code(text)
        RUNTIME_CONFIG["service_code"] = clean_code
        save_env_variable("DEFAULT_SERVICE_CODE", clean_code)
        log_bot_info(f"Updated Service Code to '{clean_code}'")
        reply = f"✅ **Service Code Updated & Saved:** `{clean_code}`"
        if clean_code != text.strip().lower():
            reply += f"\n*(Mapped to official code `{clean_code}`)*"
        sent_msg = await update.message.reply_text(reply, reply_markup=build_main_keyboard(False), parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)
        return


# ---------------------------------------------------------
# GENERIC CALLBACK QUERY DISPATCHER
# ---------------------------------------------------------

async def generic_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route inline keyboard clicks with instant acknowledgement and tap-time auth."""
    if not await verify_access(update, context):
        return

    query = update.callback_query
    data = query.data
    user = update.effective_user.first_name or update.effective_user.username or str(update.effective_chat.id)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    is_admin = auth_manager.is_admin(user_id)

    log_tg(f"[BUTTON] {data}", user)

    # Clean pending prompt states on navigation
    if data in ("btn_dashboard", "stop_current_task", "btn_admin_hub"):
        context.user_data.pop("awaiting_api_key", None)
        context.user_data.pop("awaiting_max_price", None)
        context.user_data.pop("awaiting_service_code", None)

    # 1. Main Dashboard
    if data == "btn_dashboard":
        await query.answer()
        text, keyboard = get_dashboard_content(chat_id, user, is_admin=is_admin)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # 2. Hero Actions
    elif data == "btn_buy":
        await query.answer("Initiating single number hunt...")
        await buy_handler(update, context)
    elif data == "btn_autoscan":
        await query.answer("Starting auto-hunt loop...")
        await autoscan_handler(update, context)
    elif data == "stop_current_task":
        await stop_handler(update, context)

    # 3. Balance & Financial
    elif data == "btn_balance":
        await balance_handler(update, context)

    # 4. Management & History
    elif data == "btn_active_numbers":
        await active_numbers_handler(update, context)
    elif data == "btn_saved_links":
        await saved_links_handler(update, context, page=0)
    elif data.startswith("saved_page_"):
        page_num = int(data.split("_")[-1])
        await saved_links_handler(update, context, page=page_num)

    # 5. Settings & Config
    elif data == "btn_stats":
        await stats_handler(update, context)
    elif data == "btn_help":
        await help_handler(update, context, tab="quickstart")
    elif data.startswith("help_tab_"):
        tab_name = data.replace("help_tab_", "")
        await help_handler(update, context, tab=tab_name)
    elif data == "btn_set_api_key":
        await query.answer()
        context.user_data["awaiting_api_key"] = True
        await query.edit_message_text(
            render_set_api_key_view(),
            reply_markup=build_prompt_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "btn_set_price":
        await query.answer()
        context.user_data["awaiting_max_price"] = True
        await query.edit_message_text(
            render_set_price_view(RUNTIME_CONFIG["max_price"]),
            reply_markup=build_prompt_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "btn_set_service":
        await query.answer()
        context.user_data["awaiting_service_code"] = True
        await query.edit_message_text(
            render_set_service_view(RUNTIME_CONFIG["service_code"]),
            reply_markup=build_prompt_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

    # 6. Admin Control Hub Callbacks
    elif data == "btn_admin_hub":
        await admin_hub_handler(update, context)
    elif data.startswith("adm_users_page_"):
        page_num = int(data.split("_")[-1])
        await users_handler(update, context, page=page_num)
    elif data == "adm_gen_invite":
        await invite_handler(update, context)
    elif data == "adm_mode_menu":
        await query.answer()
        cur_mode = auth_manager.get_access_mode()
        await query.edit_message_text(
            f"🛡️ **Configure Bot Access Mode**\n\n• Current Policy: `{cur_mode.upper()}`\n\nSelect a policy below:",
            reply_markup=build_mode_selector_keyboard(cur_mode),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data.startswith("set_mode_"):
        target_mode = data.replace("set_mode_", "")
        if auth_manager.set_access_mode(target_mode, admin_id=user_id):
            await query.answer(f"Mode set to {target_mode}!")
            await admin_hub_handler(update, context)
    elif data == "adm_clear_chat":
        await query.answer("Cleaning chat...")
        report = await chat_cleaner.clear_chat(context.bot, chat_id)
        sent_msg = await context.bot.send_message(chat_id, report, parse_mode=ParseMode.MARKDOWN)
        chat_cleaner.track_outgoing(chat_id, sent_msg.message_id)
    elif data == "adm_clear_all_prompt":
        await query.answer()
        await query.edit_message_text(
            "⚠️ **CONFIRM GLOBAL CHAT WIPE**\n\n"
            "This will delete tracked messages < 48h across all user chats.\nProceed?",
            reply_markup=build_confirm_wipe_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data == "adm_clear_all_confirm":
        await query.answer("Wiping chats...")
        report = await chat_cleaner.clear_all_chats(context.bot)
        await query.edit_message_text(report, reply_markup=build_sub_keyboard(back_callback="btn_admin_hub"), parse_mode=ParseMode.MARKDOWN)
    elif data == "adm_resync_profile":
        await query.answer("Re-syncing...")
        res = await profile_manager.apply_profile(context.bot, force=True)
        report = "🎨 **PROFILE RE-SYNC COMPLETE**\n\n"
        for k, v in res.items():
            report += f"• **{k.capitalize()}**: `{v}`\n"
        await query.edit_message_text(report, reply_markup=build_sub_keyboard(back_callback="btn_admin_hub"), parse_mode=ParseMode.MARKDOWN)
    elif data.startswith("adm_revoke_"):
        target_uid = int(data.replace("adm_revoke_", ""))
        db_manager.remove_authorized_user(target_uid)
        db_manager.log_admin_action(user_id, "REVOKE_USER", target_id=str(target_uid))
        await query.answer(f"User {target_uid} revoked!")
        await users_handler(update, context, page=0)
    elif data == "noop":
        await query.answer()


# ---------------------------------------------------------
# APPLICATION ENTRYPOINT & LIFECYCLE
# ---------------------------------------------------------

def main() -> None:
    """Launch the Telegram Bot application."""
    setup_logger_filters()
    log_banner()

    clean_token = (TELEGRAM_BOT_TOKEN or "").strip()
    if not clean_token or clean_token == "your_telegram_bot_token_here":
        print("\n" + "=" * 60)
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing!")
        print("Please configure your bot token in .env or run setup.py / setup.bat.")
        print("=" * 60)
        token_input = input("Enter Telegram Bot Token from @BotFather: ").strip()
        if not token_input:
            sys.exit(1)
        save_env_variable("TELEGRAM_BOT_TOKEN", token_input)
        bot_token = token_input
    else:
        bot_token = clean_token

    async def on_startup(application: Application) -> None:
        refund_agent.start()
        # Autonomous Profile Setup (Name, About, Description, Logo, Scoped Commands)
        try:
            await profile_manager.apply_profile(application.bot)
            admin_ids = list(auth_manager.get_admin_ids())
            await profile_manager.register_scoped_commands(application.bot, admin_ids)
        except Exception as e:
            logger.warning(f"Startup profile deployment notice: {e}")

    async def on_shutdown(application: Application) -> None:
        refund_agent.stop()

    app = (
        Application.builder()
        .token(bot_token)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    # Core User Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", start_handler))
    app.add_handler(CommandHandler("buy", buy_handler))
    app.add_handler(CommandHandler("autoscan", autoscan_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("active_numbers", active_numbers_handler))
    app.add_handler(CommandHandler("saved_links", saved_links_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("set_price", set_price_handler))
    app.add_handler(CommandHandler("set_service", set_service_handler))
    app.add_handler(CommandHandler("set_api_key", set_api_key_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Administrative Commands (PRD §4.4, §4.5, §4.6)
    app.add_handler(CommandHandler("admin", admin_hub_handler))
    app.add_handler(CommandHandler("users", users_handler))
    app.add_handler(CommandHandler("adduser", adduser_handler))
    app.add_handler(CommandHandler("removeuser", removeuser_handler))
    app.add_handler(CommandHandler("invite", invite_handler))
    app.add_handler(CommandHandler("mode", mode_handler))
    app.add_handler(CommandHandler("clear", clear_handler))
    app.add_handler(CommandHandler("clearall", clearall_handler))
    app.add_handler(CommandHandler("setup", setup_cmd_handler))

    # Callbacks
    app.add_handler(CallbackQueryHandler(cancel_id_callback, pattern=r"^cancel_id_\d+$"))
    app.add_handler(CallbackQueryHandler(generic_callback_router))

    # Text replies for interactive prompts (API key, price, service code)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))

    log_bot_info("Connecting to Telegram Bot API with Control Layer & Brand Identity...")
    log_bot_info(f"Telegram Bot Token: {bot_token[:10]}...{bot_token[-4:]}")
    log_bot_info(f"Access Policy: [{auth_manager.get_access_mode().upper()}]")
    log_bot_info(f"Grizzly Service Code: {RUNTIME_CONFIG['service_code']} (MyJio 6-Digit OTP)")
    log_bot_info(f"Target Country ID: {RUNTIME_CONFIG['country_id']} (India)")
    log_bot_info(f"Max Price Budget: ${RUNTIME_CONFIG['max_price']:.2f} USD")
    log_bot_info("Live Terminal Logs Active: All incoming API requests, responses, and user commands stream live.")
    log_bot_info("Press Ctrl+C in terminal to stop.")

    app.run_polling()


if __name__ == "__main__":
    main()
