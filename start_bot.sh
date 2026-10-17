#!/usr/bin/env bash
# Jio Gemini 18-Month Hunter Bot - Linux / RDP Launcher

set -e

echo "================================================================"
echo "       JIO GEMINI 18-MONTH HUNTER BOT - LINUX LAUNCHER"
echo "================================================================"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[X] python3 not found! Please install python3."
    exit 1
fi

# 2. Virtual environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment (venv)..."
    python3 -m venv venv
fi

# 3. Activate venv
source venv/bin/activate

# 4. Install dependencies
echo "[*] Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt

# 5. Check .env
if [ ! -f ".env" ]; then
    echo "[*] Initializing .env configuration..."
    cp .env.example .env
    read -p "Enter Telegram Bot Token from @BotFather: " TG_TOKEN
    read -p "Enter Grizzly SMS API Key (from grizzlysms.com): " GZ_KEY

    cat <<EOF > .env
TELEGRAM_BOT_TOKEN=$TG_TOKEN
GRIZZLY_API_KEY=$GZ_KEY
DEFAULT_SERVICE_CODE=mjo
DEFAULT_COUNTRY_ID=22
DEFAULT_MAX_PRICE=0.60
PROXY=
OTP_TIMEOUT=90
POLL_INTERVAL=3
AUTO_SCAN_DELAY=2
EOF
    echo "[*] Saved .env!"
fi

# 6. Launch
echo "[*] Launching Bot..."
python3 bot.py
