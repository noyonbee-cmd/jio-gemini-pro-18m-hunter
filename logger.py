"""
Live Colored Terminal Logger for Jio Gemini 18-Month Hunter Bot.
Prints clean, high-visibility real-time logs for all API requests, responses,
Telegram user interactions, carrier validations, and refund events.
"""
from __future__ import annotations
import sys
import logging
from datetime import datetime

# Windows Console UTF-8 & ANSI color activation
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
MAGENTA = "\033[1;35m"
CYAN = "\033[1;36m"
WHITE = "\033[1;37m"
BG_BLUE = "\033[44;1;37m"
BG_GREEN = "\033[42;1;30m"
BG_RED = "\033[41;1;37m"


def timestamp() -> str:
    """Format current local time."""
    return datetime.now().strftime("%H:%M:%S")


def log_banner() -> None:
    """Print startup banner."""
    print(f"\n{CYAN}{BOLD}{'=' * 70}{RESET}")
    print(f"{CYAN}{BOLD}  * JIO GEMINI 18-MONTH HUNTER BOT - LIVE CONSOLE LOGS ACTIVE *{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 70}{RESET}\n")


def log_tg(action: str, user: str, details: str = "") -> None:
    """Log Telegram user commands or button clicks."""
    ts = timestamp()
    user_part = f"{YELLOW}@{user}{RESET}" if user else f"{YELLOW}User{RESET}"
    det_part = f" -> {WHITE}{details}{RESET}" if details else ""
    print(f"{DIM}[{ts}]{RESET} {MAGENTA}[TELEGRAM]{RESET} {user_part} {BOLD}{action}{RESET}{det_part}")


def log_api_req(service: str, method: str, endpoint: str, details: str = "") -> None:
    """Log outgoing HTTP API request."""
    ts = timestamp()
    svc_color = CYAN if "GRIZZLY" in service.upper() else BLUE
    tag = f"{svc_color}[{service.upper()} REQ]{RESET}"
    method_str = f"{BOLD}{method.upper()}{RESET}"
    det = f" | {DIM}{details}{RESET}" if details else ""
    print(f"{DIM}[{ts}]{RESET} {tag} --> {method_str} {endpoint}{det}")


def log_api_res(service: str, status_code: int, elapsed_ms: float, summary: str = "") -> None:
    """Log incoming HTTP API response."""
    ts = timestamp()
    svc_color = CYAN if "GRIZZLY" in service.upper() else BLUE
    tag = f"{svc_color}[{service.upper()} RES]{RESET}"
    
    if 200 <= status_code < 300:
        st_color = GREEN
    elif 300 <= status_code < 400:
        st_color = YELLOW
    else:
        st_color = RED

    status_str = f"{st_color}{status_code}{RESET}"
    time_str = f"{DIM}({elapsed_ms:.0f}ms){RESET}"
    print(f"{DIM}[{ts}]{RESET} {tag} <-- {status_str} {time_str} {summary}")


def log_step(step_num: int, total_steps: int, title: str, detail: str = "") -> None:
    """Log pipeline step progression."""
    ts = timestamp()
    step_tag = f"{YELLOW}[STEP {step_num}/{total_steps}]{RESET}"
    det_part = f"\n       +- {DIM}{detail}{RESET}" if detail else ""
    print(f"{DIM}[{ts}]{RESET} {step_tag} {BOLD}{WHITE}{title}{RESET}{det_part}")


def log_carrier_check(phone: str, is_jio: bool, is_active: bool, detail: str) -> None:
    """Log carrier and active plan validation outcome."""
    ts = timestamp()
    if is_jio and is_active:
        icon = f"{GREEN}[+] ACTIVE JIO{RESET}"
    elif is_jio and not is_active:
        icon = f"{YELLOW}[!] INACTIVE JIO{RESET}"
    else:
        icon = f"{RED}[x] NON-JIO CARRIER{RESET}"

    print(f"{DIM}[{ts}]{RESET} {BLUE}[JIO CARRIER]{RESET} +{phone} -> {icon} ({detail})")


def log_refund(activation_id: int, phone: str, reason: str) -> None:
    """Log balance protection refund trigger."""
    ts = timestamp()
    print(
        f"{DIM}[{ts}]{RESET} {BG_RED} REFUND TRIGGERED {RESET} "
        f"ID: #{activation_id} (+{phone}) | Reason: {YELLOW}{reason}{RESET} | Balance refunded!"
    )


def log_otp(phone: str, otp: str) -> None:
    """Log OTP received event."""
    ts = timestamp()
    print(
        f"{DIM}[{ts}]{RESET} {BG_GREEN} 6-DIGIT OTP RECEIVED {RESET} "
        f"Number: +{phone} | Code: {BOLD}{YELLOW}{otp}{RESET}"
    )


def log_claim_success(phone: str, activation_url: str, cost: float) -> None:
    """Log successful 18-month Gemini offer generation."""
    ts = timestamp()
    print(f"\n{GREEN}{'=' * 70}{RESET}")
    print(f"{DIM}[{ts}]{RESET} {BG_BLUE} >> 18-MONTH GEMINI PRO LINK GENERATED! {RESET}")
    print(f"       * Mobile: +{phone} (Cost: ${cost:.2f})")
    print(f"       * Link  : {BOLD}{GREEN}{activation_url}{RESET}")
    print(f"{GREEN}{'=' * 70}{RESET}\n")


def log_bot_info(msg: str) -> None:
    """Log general bot information."""
    ts = timestamp()
    print(f"{DIM}[{ts}]{RESET} {CYAN}[INFO]{RESET} {msg}")


def log_bot_warn(msg: str) -> None:
    """Log bot warning."""
    ts = timestamp()
    print(f"{DIM}[{ts}]{RESET} {YELLOW}[WARN]{RESET} {msg}")


def log_bot_err(msg: str) -> None:
    """Log bot error."""
    ts = timestamp()
    print(f"{DIM}[{ts}]{RESET} {RED}[ERROR]{RESET} {msg}")


def setup_logger_filters() -> None:
    """Silence noisy third-party libraries (httpx getUpdates polling)."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

