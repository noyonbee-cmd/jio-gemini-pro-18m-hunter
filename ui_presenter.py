"""
Master UI Presenter & Aesthetic Design System for Telegram Bot.
Adheres strictly to .claude/skills/telegram-bot-builder/SKILL.md.
Encapsulates typography tokens, micro-animations, progress bars,
interactive inline keyboards, and screen templates.
Preserves all backend scripts completely untouched.
"""
from __future__ import annotations
import math
import os
from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

# ---------------------------------------------------------
# 1. DESIGN TOKENS & TYPOGRAPHY SYSTEM
# ---------------------------------------------------------

# High-tech Unicode Spinner Frames
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Pulse indicators
PULSE_DOTS = ["● ○ ○", "○ ● ○", "○ ○ ●", "○ ● ○"]

# Status Badges
BADGE_ONLINE = "〔 🟢 ᴏɴʟɪɴᴇ 〕"
BADGE_HUNTING = "〔 ⚡ ʜᴜɴᴛɪɴɢ 〕"
BADGE_PROTECTED = "〔 🛡️ ᴢᴇʀᴏ-ʟᴏss 〕"
BADGE_VERIFIED = "〔 💎 ᴠᴇʀɪғɪᴇᴅ 〕"
BADGE_WAITING = "〔 ⏳ ᴡᴀɪᴛɪɴɢ 〕"
BADGE_STOPPED = "〔 🛑 sᴛᴏᴘᴘᴇᴅ 〕"
BADGE_SUCCESS = "〔 🎉 ᴄʟᴀɪᴍᴇᴅ 〕"

# Divider Rails
RAIL_BORDER = "◈ ━━━━━━━━━━━━━━━━━━━━━━━━ ◈"
CARD_TOP = "┌─"
CARD_MID = "│"
CARD_BOT = "└────────────────────────────────────────"


def mask_phone(phone: str) -> str:
    """Mask mobile number for clean visual privacy (e.g. +91 98••• ••210)."""
    clean = "".join(filter(str.isdigit, phone))
    if len(clean) >= 10:
        cc = clean[:-10]
        core = clean[-10:]
        cc_str = f"+{cc} " if cc else "+91 "
        return f"{cc_str}{core[:2]}••• ••{core[-3:]}"
    return f"+{phone}"


def render_progress_bar(percent: int, length: int = 10, spinner_idx: int = 0) -> str:
    """
    Render a high-tech dual progress bar with unicode fill,
    rotating spinner frame, and percentage label.
    """
    percent = max(0, min(100, int(percent)))
    filled = int(round(length * percent / 100))
    bar = "█" * filled + "░" * (length - filled)
    spinner = SPINNER_FRAMES[spinner_idx % len(SPINNER_FRAMES)]
    return f"`{spinner} [{bar}]` **{percent}%**"


# ---------------------------------------------------------
# 2. INLINE KEYBOARDS & NAVIGATION LAYOUTS
# ---------------------------------------------------------

def build_main_keyboard(is_running: bool, is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Build the primary 2-column action matrix with prominent sticky Stop button during runs.
    Follows SKILL.md inline keyboard ergonomic hierarchy. Includes Admin Hub row for admins.
    """
    keyboard = []

    if is_running:
        keyboard.append([
            InlineKeyboardButton("🛑 STOP TASK & AUTO-REFUND", callback_data="stop_current_task")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🛒 Buy 1 Number", callback_data="btn_buy"),
            InlineKeyboardButton("⚡ Auto-Hunt (Loop)", callback_data="btn_autoscan"),
        ])

    keyboard.append([
        InlineKeyboardButton("💰 Wallet Balance", callback_data="btn_balance"),
        InlineKeyboardButton("🔑 Setup API Key", callback_data="btn_set_api_key"),
    ])
    keyboard.append([
        InlineKeyboardButton("💵 Max Price", callback_data="btn_set_price"),
        InlineKeyboardButton("🏷️ Service Code", callback_data="btn_set_service"),
    ])
    keyboard.append([
        InlineKeyboardButton("📱 Active Numbers", callback_data="btn_active_numbers"),
        InlineKeyboardButton("📜 Claimed Links", callback_data="btn_saved_links"),
    ])
    keyboard.append([
        InlineKeyboardButton("📊 System Stats", callback_data="btn_stats"),
        InlineKeyboardButton("📖 User Guide", callback_data="btn_help"),
    ])

    if is_admin:
        keyboard.append([
            InlineKeyboardButton("⚙️ Admin Control Hub", callback_data="btn_admin_hub")
        ])

    return InlineKeyboardMarkup(keyboard)


def build_stop_keyboard() -> InlineKeyboardMarkup:
    """Prominent sticky Stop button displayed while pipeline is executing."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 STOP TASK & REFUND BALANCE", callback_data="stop_current_task")]
    ])


def build_sub_keyboard(
    back_callback: str = "btn_dashboard",
    refresh_callback: Optional[str] = None,
    extra_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """
    Standardized submenu navigation bar.
    Enforces 'Zero Dead-Ends' rule from SKILL.md.
    """
    keyboard = []
    if extra_buttons:
        for row in extra_buttons:
            keyboard.append(row)

    nav_row = []
    if refresh_callback:
        nav_row.append(InlineKeyboardButton("🔄 Refresh Data", callback_data=refresh_callback))
    nav_row.append(InlineKeyboardButton("🔙 Back to Dashboard", callback_data=back_callback))
    keyboard.append(nav_row)

    return InlineKeyboardMarkup(keyboard)


def build_prompt_cancel_keyboard(cancel_callback: str = "btn_dashboard") -> InlineKeyboardMarkup:
    """Inline cancellation button for user prompts (e.g. entering price, API key)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel & Return", callback_data=cancel_callback)]
    ])


def build_active_numbers_keyboard(numbers: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build action list with individual cancel buttons and a bulk cancel-all option."""
    buttons = []
    for item in numbers[:8]:
        act_id = item["activation_id"]
        phone = item.get("phone_number", str(act_id))
        masked = mask_phone(phone)
        buttons.append([
            InlineKeyboardButton(f"🛑 Refund {masked}", callback_data=f"cancel_id_{act_id}")
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="btn_active_numbers"),
        InlineKeyboardButton("🔙 Main Menu", callback_data="btn_dashboard"),
    ])
    return InlineKeyboardMarkup(buttons)


def build_saved_links_keyboard(offers: List[Dict[str, Any]], page: int = 0, per_page: int = 4) -> InlineKeyboardMarkup:
    """Paginated inline keyboard displaying direct 1-tap claim buttons."""
    total = len(offers)
    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    page_items = offers[start : start + per_page]

    buttons = []
    for idx, item in enumerate(page_items, start=start + 1):
        url = item.get("claim_url", "")
        phone = item.get("phone_number", "Unknown")
        masked = mask_phone(phone)
        if url:
            buttons.append([
                InlineKeyboardButton(f"🎁 #{idx} Redeem {masked}", url=url)
            ])

    # Pagination navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"saved_page_{page-1}"))
    if total > 0:
        nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"saved_page_{page+1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="btn_saved_links"),
        InlineKeyboardButton("🔙 Main Menu", callback_data="btn_dashboard"),
    ])
    return InlineKeyboardMarkup(buttons)


def build_success_keyboard(claim_url: str) -> InlineKeyboardMarkup:
    """High-conversion victory keyboard on successful 18-month Gemini claim."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 REDEEM 18-MONTH GEMINI PRO OFFER", url=claim_url)],
        [
            InlineKeyboardButton("⚡ Hunt Another", callback_data="btn_buy"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="btn_dashboard"),
        ],
    ])


def build_help_keyboard(current_tab: str = "quickstart") -> InlineKeyboardMarkup:
    """Tabbed help manual navigation."""
    row1 = [
        InlineKeyboardButton(
            "📌 Quick Start" if current_tab != "quickstart" else "• 📌 Quick Start •",
            callback_data="help_tab_quickstart",
        ),
        InlineKeyboardButton(
            "🛡️ Zero-Loss Guard" if current_tab != "refund" else "• 🛡️ Zero-Loss Guard •",
            callback_data="help_tab_refund",
        ),
    ]
    row2 = [
        InlineKeyboardButton(
            "⌨️ Commands" if current_tab != "commands" else "• ⌨️ Commands •",
            callback_data="help_tab_commands",
        ),
        InlineKeyboardButton(
            "❓ FAQs & Tips" if current_tab != "faq" else "• ❓ FAQs & Tips •",
            callback_data="help_tab_faq",
        ),
    ]
    return InlineKeyboardMarkup([
        row1,
        row2,
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="btn_dashboard")],
    ])


def build_admin_hub_keyboard(active_mode: str) -> InlineKeyboardMarkup:
    """Build the administrative management keyboard (PRD §6.7)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 User Management", callback_data="adm_users_page_0"),
            InlineKeyboardButton("🎟️ Generate Invite", callback_data="adm_gen_invite"),
        ],
        [
            InlineKeyboardButton(f"🛡️ Mode: {active_mode.upper()}", callback_data="adm_mode_menu"),
            InlineKeyboardButton("🔄 Re-Sync Profile", callback_data="adm_resync_profile"),
        ],
        [
            InlineKeyboardButton("🧹 Clear This Chat", callback_data="adm_clear_chat"),
            InlineKeyboardButton("💥 Clear All Chats", callback_data="adm_clear_all_prompt"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="btn_dashboard")
        ],
    ])


def build_mode_selector_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """Interactive toggle for access mode."""
    modes = [
        ("admin_only", "🔒 Admin Only"),
        ("allowlist", "📋 Allowlist"),
        ("public", "🌐 Public"),
    ]
    buttons = []
    for mode_key, mode_label in modes:
        label = f"• {mode_label} •" if mode_key == current_mode else mode_label
        buttons.append([InlineKeyboardButton(label, callback_data=f"set_mode_{mode_key}")])

    buttons.append([InlineKeyboardButton("🔙 Back to Admin Hub", callback_data="btn_admin_hub")])
    return InlineKeyboardMarkup(buttons)


def build_users_list_keyboard(users: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Paginated user list keyboard with remove actions and pagination."""
    buttons = []
    for user in users[:5]:
        uid = user.get("user_id")
        u_name = user.get("username") or user.get("first_name") or str(uid)
        buttons.append([
            InlineKeyboardButton(f"🚫 Revoke {u_name}", callback_data=f"adm_revoke_{uid}")
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"adm_users_page_{page-1}"))
    if total_pages > 0:
        nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"adm_users_page_{page+1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("🎟️ New Invite", callback_data="adm_gen_invite"),
        InlineKeyboardButton("🔙 Admin Hub", callback_data="btn_admin_hub"),
    ])
    return InlineKeyboardMarkup(buttons)


def build_confirm_wipe_keyboard() -> InlineKeyboardMarkup:
    """Confirmation prompt for global chat clear."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💥 CONFIRM WIPE ALL CHATS", callback_data="adm_clear_all_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="btn_admin_hub"),
        ]
    ])


# ---------------------------------------------------------
# 3. SCREEN PRESENTERS & VIEW TEMPLATES
# ---------------------------------------------------------

def render_dashboard_view(
    user_name: str,
    balance_str: str,
    service_code: str,
    max_price: float,
    stats: Dict[str, Any],
    ref_stats: Dict[str, Any],
    is_running: bool,
) -> str:
    """Generate the executive main dashboard with status matrix and user greeting."""
    status_badge = BADGE_HUNTING if is_running else BADGE_ONLINE
    claimed_count = stats.get("total_claimed", 0)
    pending_count = stats.get("total_pending", 0)
    refunded_count = ref_stats.get("refunded_count", 0)
    refunded_amt = ref_stats.get("refunded_amount", 0.0)
    ref_queue_count = ref_stats.get("pending_count", 0)

    text = (
        "╔══════════════════════════════════════════════╗\n"
        "║   ⚡ **𝐉𝐈𝐎 𝐆𝐄𝐌ＩＮＩ 𝟏𝟖-𝐌𝐎𝐍𝐓𝐇 𝐇𝐔𝐍𝐓𝐄𝐑** ⚡   ║\n"
        "╚══════════════════════════════════════════════╝\n"
        f"👋 Welcome, **{user_name}**!\n"
        f"System: {status_badge}  •  Guard: {BADGE_PROTECTED}\n\n"
        "┌─ 📊 **Live Control Matrix** ──────────────────────\n"
        f"│ • 💰 **Grizzly Balance** : `{balance_str}`\n"
        f"│ • 🏷️ **Service Tag**     : `{service_code}` (MyJio 6-Digit OTP)\n"
        f"│ • 💵 **Price Budget Cap**: `${max_price:.2f} USD` per number\n"
        f"│ • 📱 **Active Orders**   : `{pending_count} Pending`\n"
        f"│ • 💎 **Claimed 18-Mo**   : `{claimed_count} Generated` 🎁\n"
        f"│ • 🛡️ **Restored Balance**: `${refunded_amt:.2f} USD` ({refunded_count} auto-refunds)\n"
        f"│ • ⏳ **Refund Queue**    : `{ref_queue_count} in cooldown watcher`\n"
        "└───────────────────────────────────────────────\n\n"
        "> 💡 **Zero-Loss Guarantee:** Non-Jio or inactive numbers are\n"
        "> automatically queued and 100% refunded in the background."
    )
    return text


def render_pipeline_step(
    step_num: int,
    total_steps: int,
    title: str,
    subtitle: str,
    percent: int,
    phone: str = "",
    cost: float = 0.0,
    elapsed: int = 0,
    total_timeout: int = 0,
    spinner_idx: int = 0,
) -> str:
    """Render a dynamic, high-tech animated execution card during pipeline execution."""
    bar = render_progress_bar(percent, length=10, spinner_idx=spinner_idx)
    masked = mask_phone(phone) if phone else "Assigning..."

    text = (
        "⚡ **𝐉𝐈𝐎 𝐆𝐄𝐌ＩＮＩ 𝟏𝟖-𝐌𝐎𝐍𝐓𝐇 𝐏Ｉ𝐏𝐄𝐋ＩＮ𝐄** ⚡\n"
        f"{RAIL_BORDER}\n"
        f"**Step [{step_num}/{total_steps}]:** {title}\n"
        f"{bar}\n\n"
        "┌─ 📱 **Operational Context** ──────────────────────\n"
        f"│ • 📡 **Status** : {subtitle}\n"
        f"│ • 📱 **Target** : `{masked}`\n"
    )
    if cost > 0:
        text += f"│ • 💵 **Price**  : `${cost:.2f} USD`\n"
    if total_timeout > 0:
        text += f"│ • ⏱️ **Timer**  : `{elapsed}s` / `{total_timeout}s` (Timeout)\n"

    text += (
        "└───────────────────────────────────────────────\n\n"
        "> 🛡️ *Live task guard is active. Tap Stop to abort & auto-refund.*"
    )
    return text


def render_rejection_card(phone: str, reason: str, cost: float, cooldown_seconds: int = 75) -> str:
    """Render clean, friendly rejection card explaining auto-refund status."""
    masked = mask_phone(phone)
    safe_reason = str(reason).replace("`", "").replace("_", " ")
    text = (
        "⚠️ **NUMERIC VALIDATION FAILED: NO CHARGE**\n"
        f"{RAIL_BORDER}\n"
        "`[░░░░░░░░░░]` **AUTO-REFUND ENGAGED** 🛡️\n\n"
        "┌─ 🔍 **Rejection Analysis** ───────────────────────\n"
        f"│ • 📱 **Target Number** : `{masked}`\n"
        f"│ • ❌ **Detected Cause** : `{safe_reason}`\n"
        f"│ • 💰 **Cost To Refund** : `${cost:.2f} USD`\n"
        f"│ • ⏳ **Cooldown Lock**  : ~`{cooldown_seconds}s` (Grizzly window)\n"
        f"│ • 🤖 **Refund Agent**   : `Active in Background`\n"
        "└───────────────────────────────────────────────\n\n"
        "> 🛡️ **Zero Balance Waste:** The background watcher will cancel\n"
        "> the number the second the lock clears, restoring your funds."
    )
    return text


def render_otp_timeout_card(phone: str, cost: float, timeout_sec: int) -> str:
    """Render card when OTP wait expires."""
    masked = mask_phone(phone)
    text = (
        "⏰ **SMS TIMEOUT: BALANCE PROTECTED**\n"
        f"{RAIL_BORDER}\n"
        "`[░░░░░░░░░░]` **ORDER CANCELLED & REFUNDED** 🛡️\n\n"
        "┌─ 📱 **Timeout Summary** ──────────────────────────\n"
        f"│ • 📱 **Number**   : `{masked}`\n"
        f"│ • ⏱️ **Wait Time**: `{timeout_sec}s` without MyJio SMS\n"
        f"│ • 💵 **Restored** : `${cost:.2f} USD` (100% Refunded)\n"
        "└───────────────────────────────────────────────\n\n"
        "> 💡 Try another number or raise your price cap to access\n"
        "> fresher provider routes."
    )
    return text


def render_success_card(phone: str, cost: float, claim_url: str) -> str:
    """Render celebratory victory card upon successful claim."""
    masked = mask_phone(phone)
    text = (
        "🎉 💎 **𝐆𝐎𝐎𝐆𝐋𝐄 𝐆𝐄𝐌ＩＮＩ 𝟏𝟖-𝐌𝐎𝐍𝐓𝐇 𝐂𝐋𝐀Ｉ𝐌Ｅ𝐃!** 💎 🎉\n"
        f"{RAIL_BORDER}\n"
        "`[██████████]` **100% SUCCESS** ✅\n\n"
        "┌─ 🎁 **Activation Voucher** ───────────────────────\n"
        f"│ • 📱 **Mobile Identity** : `{masked}`\n"
        f"│ • 💵 **Total Cost Spent** : `${cost:.2f} USD`\n"
        "│ • 💎 **Included Benefit** : `Google Gemini Pro (18 Months)`\n"
        "│ • 📦 **SKU Plan Tag**     : `Reliance Jio Z0241`\n"
        "└───────────────────────────────────────────────\n\n"
        "🔗 **Direct Google Activation URL:**\n"
        f"`{claim_url}`\n\n"
        "👉 **Tap the button below to link 18 months of Google Gemini Pro to your Google Account!**"
    )
    return text


def render_balance_view(balance_str: str, is_valid: bool, ref_stats: Dict[str, Any]) -> str:
    """Render live balance view with refund metrics."""
    refunded_count = ref_stats.get("refunded_count", 0)
    refunded_amt = ref_stats.get("refunded_amount", 0.0)
    pending_ref = ref_stats.get("pending_count", 0)

    status_icon = "✅ Connected & Valid" if is_valid else "⚠️ API Key Required / Invalid"
    text = (
        "💰 **GRIZZLY SMS WALLET & BALANCE GUARD**\n"
        f"{RAIL_BORDER}\n\n"
        "┌─ 💵 **Account Finances** ─────────────────────────\n"
        f"│ • 💳 **Available Balance**: `{balance_str}`\n"
        f"│ • 🔑 **API Key Status**   : `{status_icon}`\n"
        f"│ • 🛡️ **Total Refunded**   : `${refunded_amt:.2f} USD` ({refunded_count} orders)\n"
        f"│ • ⏳ **Pending in Queue** : `{pending_ref} orders`\n"
        "└───────────────────────────────────────────────\n\n"
        "> 💡 To top up your balance, visit your account dashboard at\n"
        "> [grizzlysms.com](https://grizzlysms.com/)."
    )
    return text


def render_active_numbers_view(numbers: List[Dict[str, Any]]) -> str:
    """Render list of pending active orders."""
    if not numbers:
        return (
            "📱 **ACTIVE NUMBERS IN PROGRESS**\n"
            f"{RAIL_BORDER}\n\n"
            "✨ **All clear! No numbers are currently active or pending.**\n\n"
            "> Tap **[ 🛒 Buy 1 Number ]** or **[ ⚡ Auto-Hunt ]** to begin."
        )

    text = (
        f"📱 **ACTIVE NUMBERS IN PROGRESS ({len(numbers)})**\n"
        f"{RAIL_BORDER}\n\n"
    )
    for idx, item in enumerate(numbers[:8], 1):
        act_id = item["activation_id"]
        phone = item.get("phone_number", str(act_id))
        st = item.get("status", "PENDING")
        cost = item.get("cost", 0.10)
        masked = mask_phone(phone)
        text += (
            f"**{idx}.** `{masked}`  (Order `#{act_id}`)\n"
            f"   • Status: `{st}` | Cost: `${cost:.2f}`\n\n"
        )

    text += "> 🛑 Tap an individual refund button below to cancel that number immediately."
    return text


def render_saved_links_view(offers: List[Dict[str, Any]], page: int = 0, per_page: int = 4) -> str:
    """Render claimed 18-month Google Gemini links."""
    total = len(offers)
    if not total:
        return (
            "📜 **CLAIMED GEMINI 18-MONTH LINKS**\n"
            f"{RAIL_BORDER}\n\n"
            "📭 **No claimed offers found in database yet.**\n\n"
            "> Start a scan using **[ 🛒 Buy 1 Number ]** or **[ ⚡ Auto-Hunt ]**."
        )

    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    page_items = offers[start : start + per_page]

    text = (
        f"📜 **CLAIMED GEMINI 18-MONTH OFFERS ({total})**\n"
        f"{RAIL_BORDER}\n"
        f"Showing Page `{page + 1}/{total_pages}`\n\n"
    )

    for idx, item in enumerate(page_items, start=start + 1):
        phone = item.get("phone_number", "Unknown")
        claimed_at = item.get("claimed_at", "")
        url = item.get("claim_url", "")
        masked = mask_phone(phone)
        text += (
            f"💎 **Offer #{idx}** — `{masked}`\n"
            f"   • Claimed: `{claimed_at}`\n"
            f"   • Link: [1-Tap Google Redeem]({url})\n\n"
        )

    text += "> 💡 All links are also saved locally to `gemini_activation_links.txt`."
    return text


def render_help_view(tab: str = "quickstart") -> str:
    """Render comprehensive multi-tab user manual."""
    if tab == "refund":
        return (
            "🛡️ **ZERO-LOSS AUTO-REFUND GUARD**\n"
            f"{RAIL_BORDER}\n\n"
            "Grizzly SMS enforces a 60–90 second lock before allowing a cancellation.\n\n"
            "**How Our Multi-Agent Guard Protects Your Money:**\n"
            "1. **Instant Carrier Check**: If a number is non-Jio or inactive, the hunter bot drops it immediately.\n"
            "2. **Background Watcher**: It hands the order to the `RefundWatcherAgent`.\n"
            "3. **Zero Bottleneck**: The main bot continues hunting without waiting.\n"
            "4. **Guaranteed Refund**: As soon as the cooldown timer expires, the watcher fires `status=8`.\n"
            "5. **100% Restored**: Your Grizzly panel balance is refunded automatically."
        )
    elif tab == "commands":
        return (
            "⌨️ **TELEGRAM COMMANDS DIRECTORY**\n"
            f"{RAIL_BORDER}\n\n"
            "• `/start` / `/menu` — Open Main Interactive Dashboard\n"
            "• `/buy` — Rent 1 number, verify Jio status & claim\n"
            "• `/autoscan [N]` — Auto-hunt continuously up to N times\n"
            "• `/stop` — Stop ongoing task & auto-refund active order\n"
            "• `/balance` — Check live Grizzly SMS wallet balance\n"
            "• `/active_numbers` — View pending numbers with 1-click refund\n"
            "• `/saved_links` — View and browse all claimed Gemini links\n"
            "• `/set_price <val>` — Set maximum budget cap per number\n"
            "• `/set_service <code>` — Switch Grizzly service code (`jio`, `mjo`)\n"
            "• `/set_api_key <key>` — Set & test your Grizzly SMS API key\n"
            "• `/help` — Open this comprehensive guide"
        )
    elif tab == "faq":
        return (
            "❓ **FREQUENTLY ASKED QUESTIONS & PRO TIPS**\n"
            f"{RAIL_BORDER}\n\n"
            "**Q: What is the best service code to use?**\n"
            "• Use `jio` (official MyJio, 450k+ numbers available at ~$0.10 USD) or `mjo`.\n\n"
            "**Q: How do I claim the 18-month Gemini offer?**\n"
            "• Click the `[ 🎁 REDEEM OFFER ]` button on the victory card. Sign in with the Google Account you wish to upgrade!\n\n"
            "**Q: Can I run this in the background?**\n"
            "• Yes! Run `start_bot.bat` or `./start_bot.sh` on your server or RDP."
        )
    else:  # quickstart
        return (
            "📖 **JIO GEMINI 18-MONTH QUICK START**\n"
            f"{RAIL_BORDER}\n\n"
            "**Step 1:** Connect your Grizzly API Key via `/set_api_key` or `[ 🔑 Setup API Key ]`.\n"
            "**Step 2:** Ensure your wallet has at least ~$0.50 USD balance.\n"
            "**Step 3:** Tap **[ 🛒 Buy 1 Number ]** for a single test, or **[ ⚡ Auto-Hunt ]** to scan continuously.\n"
            "**Step 4:** Once an active Jio subscriber is verified, the bot receives the 6-digit OTP and generates your **18-Month Google Gemini Pro** link!\n\n"
            "> 🛡️ **Zero Risk**: Any non-eligible number is cancelled and refunded automatically."
        )


def render_set_price_view(current_price: float) -> str:
    """Prompt view for setting max price cap."""
    return (
        "💵 **CONFIGURE MAXIMUM PRICE CAP**\n"
        f"{RAIL_BORDER}\n\n"
        f"• **Current Cap**: `${current_price:.2f} USD` per number\n\n"
        "Please send your desired max price (e.g. `0.20`, `0.50`, `0.75`), "
        "or use `/set_price <amount>`.\n\n"
        "> 💡 Recommended: `$0.40 - $0.60 USD` for maximum availability."
    )


def render_set_service_view(current_service: str) -> str:
    """Prompt view for setting service code."""
    return (
        "🏷️ **CONFIGURE GRIZZLY SERVICE CODE**\n"
        f"{RAIL_BORDER}\n\n"
        f"• **Active Service Tag**: `{current_service}`\n\n"
        "Popular Service Codes on Grizzly SMS:\n"
        "• `jio` — Official MyJio (~470,000+ numbers, ~$0.10)\n"
        "• `mjo` — MyJio Alternative (~3,300 numbers, ~$0.15)\n"
        "• `jii` — Jio Secondary Line (~163,000 numbers, ~$0.10)\n"
        "• `vi`  — Vi / Vodafone Idea (~62,000 numbers, ~$0.05)\n"
        "• `air` — Airtel India Route\n"
        "• `go`  — Google / Gmail Route\n\n"
        "👉 **Tap a button below** to select instantly, or reply with **ANY custom service code**."
    )


def build_service_selector_keyboard(current_service: str = "jio") -> InlineKeyboardMarkup:
    """Inline keyboard for rapid service selection or typing custom."""
    def mark(code: str, label: str) -> str:
        return f"• {label} •" if current_service.lower() == code.lower() else label

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(mark("jio", "⚡ jio ($0.10)"), callback_data="svc_select_jio"),
            InlineKeyboardButton(mark("mjo", "📱 mjo ($0.15)"), callback_data="svc_select_mjo"),
        ],
        [
            InlineKeyboardButton(mark("jii", "🔄 jii ($0.10)"), callback_data="svc_select_jii"),
            InlineKeyboardButton(mark("vi", "🌐 vi ($0.05)"), callback_data="svc_select_vi"),
        ],
        [
            InlineKeyboardButton("⌨️ Type Custom Code", callback_data="svc_type_custom"),
            InlineKeyboardButton("🔙 Dashboard", callback_data="btn_dashboard"),
        ],
    ])


def render_set_api_key_view() -> str:
    """Prompt view for setting API key."""
    return (
        "🔑 **CONNECT GRIZZLY SMS API KEY**\n"
        f"{RAIL_BORDER}\n\n"
        "Please reply with your API Key copied from your profile:\n"
        "🔗 [grizzlysms.com/profile/settings](https://grizzlysms.com/profile/settings)\n\n"
        "• The bot tests the key live before saving.\n"
        "• Once confirmed, it persists permanently to `.env`.\n\n"
        "*(Or send directly: `/set_api_key <your_key>`)*"
    )


def render_system_stats_view(
    stats: Dict[str, Any], ref_stats: Dict[str, Any], runtime_config: Dict[str, Any]
) -> str:
    """Render comprehensive system performance matrix."""
    claimed = stats.get("total_claimed", 0)
    pending = stats.get("total_pending", 0)
    ref_count = ref_stats.get("refunded_count", 0)
    ref_amount = ref_stats.get("refunded_amount", 0.0)
    pending_ref = ref_stats.get("pending_count", 0)

    return (
        "📊 **SYSTEM ENGINE & PERFORMANCE MATRIX**\n"
        f"{RAIL_BORDER}\n\n"
        "┌─ 💎 **Productivity Metrics** ─────────────────────\n"
        f"│ • 🎁 **18-Mo Offers Claimed** : `{claimed}` 💎\n"
        f"│ • 📱 **Active Pipeline Tasks** : `{pending}`\n"
        f"│ • 🛡️ **Numbers Auto-Refunded** : `{ref_count}`\n"
        f"│ • 💵 **Total Money Restored**  : `${ref_amount:.2f} USD`\n"
        f"│ • ⏳ **Pending Refund Queue**  : `{pending_ref} orders`\n"
        "├─ ⚙️ **Active Configuration** ────────────────────\n"
        f"│ • 🏷️ **Service Code**          : `{runtime_config.get('service_code', 'jio')}`\n"
        f"│ • 💵 **Price Cap**             : `${runtime_config.get('max_price', 0.50):.2f} USD`\n"
        f"│ • 🇮🇳 **Target Country**        : `India (ID: 22)`\n"
        "└───────────────────────────────────────────────\n\n"
        "> 🛡️ Balance Guard active 24/7."
    )


def render_admin_hub_view(active_mode: str, total_users: int, tracked_chats: int) -> str:
    """Render administrator control hub (PRD §6.7)."""
    return (
        "⚙️ **𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐍𝐓𝐑𝐎𝐋 𝐇𝐔𝐁**\n"
        f"{RAIL_BORDER}\n"
        f"Access Policy: `[{active_mode.upper()}]` • Allowed Users: `{total_users}`\n\n"
        "┌─ 🛠️ **System Administration** ───────────────────\n"
        f"│ • 🛡️ **Access Mode**     : `{active_mode}`\n"
        f"│ • 👥 **Allowed Users**   : `{total_users} Authorized`\n"
        f"│ • 💬 **Tracked Chats**   : `{tracked_chats} Private Chats`\n"
        "│ • 🔄 **Profile State**   : `Hash-Guarded & Synchronized` ✅\n"
        "│ • 🤖 **Refund Watcher**  : `Running (24/7 Background)`\n"
        "└───────────────────────────────────────────────\n\n"
        "Choose an administrative action below:"
    )


def render_users_list_view(users: List[Dict[str, Any]], page: int, total_pages: int) -> str:
    """Render paginated user management list."""
    if not users:
        return (
            "👥 **AUTHORIZED USER ALLOWLIST**\n"
            f"{RAIL_BORDER}\n\n"
            "📭 **No authorized users in allowlist yet.**\n\n"
            "> Tap **[ 🎟️ New Invite ]** or send `/invite` to create an access link."
        )

    text = (
        f"👥 **AUTHORIZED USERS (Page {page + 1}/{total_pages})**\n"
        f"{RAIL_BORDER}\n\n"
    )
    for idx, u in enumerate(users, start=(page * 5) + 1):
        uid = u.get("user_id")
        uname = f"@{u['username']}" if u.get("username") else (u.get("first_name") or "User")
        added = u.get("created_at", "")
        text += f"**{idx}.** {uname} (`{uid}`) — Added: `{added}`\n"

    text += "\n> Tap **[ 🚫 Revoke ]** below to remove access for a user immediately."
    return text


def render_access_denied_card() -> str:
    """Render sleek access restriction card for blocked users."""
    return (
        "⛔ **ACCESS RESTRICTED: ADMIN PRIVILEGES REQUIRED**\n"
        f"{RAIL_BORDER}\n\n"
        "This bot is currently operating in restricted mode.\n\n"
        "• To gain access, ask the bot owner for an authorized invite link.\n"
        "• If you have an invite code, send: `/start inv_<code>`.\n\n"
        "> 🛡️ Access attempt logged."
    )


BANNER_JPG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "brand", "banner.jpg")



# ---------------------------------------------------------
# 4. BOT COMMANDS REGISTRATION (SKILL.md)
# ---------------------------------------------------------

async def register_bot_commands(application) -> None:
    """
    Register native Telegram bot commands so users get an
    instant autocomplete menu with icons when typing '/'.
    """
    commands = [
        BotCommand("start", "⚡ Open Main Control Dashboard"),
        BotCommand("menu", "📋 Open Interactive Menu"),
        BotCommand("buy", "🛒 Rent & test 1 number for 18-mo Gemini"),
        BotCommand("autoscan", "⚡ Continuous auto-hunt loop"),
        BotCommand("stop", "🛑 Halt running task & refund balance"),
        BotCommand("balance", "💰 Check Grizzly SMS wallet balance"),
        BotCommand("active_numbers", "📱 List active numbers & cancel"),
        BotCommand("saved_links", "📜 View claimed 18-month Gemini links"),
        BotCommand("set_price", "💵 Set maximum price budget cap"),
        BotCommand("set_service", "🏷️ Set Grizzly service code"),
        BotCommand("set_api_key", "🔑 Configure Grizzly SMS API key"),
        BotCommand("help", "📖 Comprehensive user guide & FAQ"),
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        pass
