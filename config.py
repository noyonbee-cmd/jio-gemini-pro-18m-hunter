"""
Configuration module for Jio Gemini 18-Month & Grizzly SMS Hunter Bot.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

def save_env_variable(key: str, value: str) -> None:
    """Save or update a key=value pair in the .env file permanently."""
    lines = []
    found = False
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        lines = new_lines
    if not found:
        lines.append(f"{key}={value}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


# Grizzly SMS API Settings
GRIZZLY_API_KEY = os.getenv("GRIZZLY_API_KEY", "").strip()
GRIZZLY_BASE_URL = "https://api.grizzlysms.com/stubs/handler_api.php"
DEFAULT_SERVICE_CODE = os.getenv("DEFAULT_SERVICE_CODE", "jio").strip()  # jio = MyJio on Grizzly SMS
DEFAULT_COUNTRY_ID = int(os.getenv("DEFAULT_COUNTRY_ID", "22"))         # 22 = India
DEFAULT_MAX_PRICE = float(os.getenv("DEFAULT_MAX_PRICE", "0.60"))       # Max purchase price cap

# Proxy Setting
PROXY = os.getenv("PROXY", "").strip()

# Polling and Execution Timers
OTP_TIMEOUT = int(os.getenv("OTP_TIMEOUT", "90"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))
AUTO_SCAN_DELAY = int(os.getenv("AUTO_SCAN_DELAY", "2"))

# Output Files
LINKS_FILE = BASE_DIR / "gemini_activation_links.txt"
RESULTS_FILE = BASE_DIR / "gemini_results.csv"
DB_FILE = BASE_DIR / "jio_bot.db"

# ==================== RELIANCE JIO API ENDPOINTS ====================
JIO_CHECK_NUMBER_URL = "https://www.jio.com/api/jio-recharge-service/recharge/mobility/number/{mobile}"
JIO_SEND_OTP_URL = "https://www.jio.com/api/jio-login-service/login/sendOtp"
JIO_VERIFY_OTP_URL = "https://www.jio.com/api/jio-login-service/login/validateOtp"
JIO_AUTH_URL = "https://www.jio.com/api/jio-authenticate-service/authenticate/authJsonData"
JIO_NAVIGATE_URL = "https://www.jio.com/api/jio-ott-service/ott/subscription/navigate/Z0241"
JIO_ACTIVATE_URL = "https://www.jio.com/api/jio-ott-service/ott/subscription/activate/Z0241?source=JIO"
JIO_GOOGLE_URL = "https://www.jio.com/api/jio-ott-service/ott/subscription/google-ai"
JIO_SUBMIT_URL = "https://www.jio.com/api/jio-ott-service/ott/submission/submit"
JIO_GOOGLE_PAGE = "https://www.jio.com/selfcare/googleai/?header=no&type=Z0241&source=JIO"

# ==================== STEALTH USER-AGENT & CLIENT HINTS ====================
# Android 16 Google Pixel 10 Pro mobile signature (ported from pixel-gemini)
PIXEL_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
)

PIXEL_CLIENT_HINTS = {
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?1",
    "Sec-CH-UA-Platform": '"Android"',
    "Sec-CH-UA-Platform-Version": '"16.0.0"',
    "Sec-CH-UA-Model": '"Pixel 10 Pro"',
}

COMMON_JIO_HEADERS = {
    "User-Agent": PIXEL_USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.jio.com",
    **PIXEL_CLIENT_HINTS,
}
