# ⚡ Jio Gemini Pro 18M Hunter Bot & Admin Control Layer

An enterprise-grade, fully automated Telegram Bot and high-speed scanner engine that rents Indian (+91) virtual mobile numbers from [Grizzly SMS](https://grizzlysms.com/), tests whether they are authentic **Reliance Jio** subscribers with an **active carrier plan**, automatically cancels and refunds non-eligible numbers to protect your account balance, and seamlessly authenticates into Jio Selfcare via 6-digit SMS OTP to extract and redeem the **18-Month Google Gemini Advanced (Google AI)** subscription (`SKU: Z0241`).

Featuring an **Admin Control Layer**, **1-Command Terminal Setup Wizard**, **Autonomous Bot Profile Sync**, and **Zero-Loss 24/7 Balance Protection**.

---

## 🌟 Key Capabilities

- **🎁 18-Month Google Gemini Pro Vouchers:** Automatically claims authentic 18-month Google Gemini AI benefits partnered with Reliance Jio (`Z0241`).
- **🛡️ Zero-Loss Balance Protection Agent:** Grizzly SMS enforces a strict 60–90 second cancellation cooldown lock after purchase. The bot's background `RefundWatcherAgent` holds non-eligible numbers, tracks the lock timer asynchronously, executes `setStatus(status=8)` the second the lock clears, confirms the balance refund (`ACCESS_CANCEL`), and protects 100% of your funds without blocking the main hunter bot.
- **⚙️ 1-Command Terminal Setup Wizard:** Interactive terminal wizard (`setup.bat` on Windows / `python3 setup.py` on Linux) that verifies Telegram tokens live, captures admin IDs automatically via `/start`, tests Grizzly SMS API keys and balances, and configures `.env` idempotently.
- **🔒 Access Control Layer & Security Gatekeeper:** Role-based access control (`admin`, `user`, `blocked`) with 3 operating modes:
  - `admin_only`: Strictly reserved for designated bot administrators.
  - `allowlist`: Access granted only to approved IDs in SQLite database.
  - `public`: Open to all users while keeping admin tools restricted.
- **🎟️ 48-Hour Deep-Link Invites:** Admins can generate single-use, cryptographically secure 48-hour deep-link invite URLs (`/invite` or `t.me/<bot>?start=inv_<code>`) that auto-enroll users upon click.
- **🧹 Non-Content Message Cleaner:** `/clear [depth]` and `/clearall confirm` delete tracked bot interactions using a recursive bisection algorithm, respecting Telegram's 48-hour deletion limit.
- **🔄 Autonomous Bot Profile Manager:** On startup, the bot automatically syncs display name, About bio, 512-character description, avatar photo, and scoped command menus using SHA-256 hash-guarding (zero wasted Telegram API calls).
- **🎨 Brand Identity Suite & Welcome Banner:** High-tech Electric Cyan (`#00D9FF`) & Cobalt Blue (`#246BFD`) theme with 640x640 circular targeting-reticle avatar (`logo.jpg`) and 1536x2048 3:4 portrait vertical welcome banner (`banner.jpg`). Cached via Telegram `file_id` for instant zero-latency dispatch.
- **📊 Modern Telegram UI & Micro-Animations:** Progress bars (`[██████░░░░] 60%`), rotating spinners (`⠋`, `⠙`, `⠹`), status badges, and responsive inline menus.
- **🥷 Pixel 10 Pro Stealth Emulation:** Reuses Android 16 Google Pixel 10 Pro Chrome Mobile fingerprints and client hints.
- **📊 SQLite Database & Export:** Automatically appends all claimed Gemini activation URLs to SQLite, `gemini_activation_links.txt`, and `gemini_results.csv`.

---

## 🚀 Setup & Installation Guides

### 🖥️ Option 1: Windows (1-Click Local PC or Windows VPS)

1. **Clone the Repository:**
   ```cmd
   git clone https://github.com/noyonbee-cmd/jio-gemini-pro-18m-hunter.git
   cd jio-gemini-pro-18m-hunter
   ```

2. **Run the 1-Click Setup Wizard:**
   Double-click **`setup.bat`** (or open Command Prompt and run):
   ```cmd
   setup.bat
   ```
   The wizard will:
   - Create your Python virtual environment (`venv`).
   - Install all dependencies (`requirements.txt` + `pillow`).
   - Prompt for your **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather)).
   - Auto-capture your **Admin Telegram ID** when you send `/start` to your bot.
   - Validate your **Grizzly SMS API Key** and display your live wallet balance.
   - Automatically configure your bot's profile and logo.

3. **Start the Bot:**
   Double-click **`start_bot.bat`** (or run `.\start_bot.bat`).

---

### 🐧 Option 2: Linux (Ubuntu / Debian / CentOS / India VPS)

1. **Clone the Repository & Install Prerequisites:**
   ```bash
   sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git
   git clone https://github.com/noyonbee-cmd/jio-gemini-pro-18m-hunter.git
   cd jio-gemini-pro-18m-hunter
   ```

2. **Create Virtual Environment & Install Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt pillow
   ```

3. **Run Setup Wizard:**
   ```bash
   python3 setup.py
   ```
   Follow the interactive prompts to link your Bot Token, Admin ID, and Grizzly SMS API Key.

4. **Make Launcher Executable & Start:**
   ```bash
   chmod +x start_bot.sh
   ./start_bot.sh
   ```

---

### 🇮🇳 Option 3: India RDP (Remote Desktop Protocol)

Running on an Indian RDP gives optimal network latency (< 20ms) to Reliance Jio Selfcare mobility endpoints:

1. Connect to your Windows/Linux India RDP.
2. Clone or download the repository.
3. Run `setup.bat` (on Windows RDP) or `./start_bot.sh` (on Linux RDP).
4. Leave `start_bot.bat` running in the background.

---

### 🔄 Option 4: Background Service (24/7 Always-On with PM2 or systemd)

#### Using PM2 (Cross-Platform):
```bash
# Install PM2 globally
npm install -g pm2

# Start bot with PM2
pm2 start bot.py --name "jio-gemini-hunter" --interpreter ./venv/bin/python3

# Enable auto-start on system reboot
pm2 startup
pm2 save
```

#### Using systemd (Linux Server):
Create `/etc/systemd/system/jio-hunter.service`:
```ini
[Unit]
Description=Jio Gemini Pro 18M Hunter Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/jio-gemini-pro-18m-hunter
ExecStart=/home/ubuntu/jio-gemini-pro-18m-hunter/venv/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jio-hunter
sudo systemctl start jio-hunter
```

---

## 📋 Commands Directory

### 👤 User Commands (Public Scope)
| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/start` | `[inv_token]` | Open the interactive dashboard or redeem a 48h invite token. |
| `/menu` | None | Open interactive main control panel. |
| `/buy` | None | Rents 1 number, validates Jio active status, claims 18-month Gemini, or refunds. |
| `/autoscan` | `[N]` | Continuously hunts until a valid Gemini offer is claimed or limit reached. |
| `/stop` | None | Immediately aborts the current operation and refunds any pending number. |
| `/balance` | None | Queries and displays real-time Grizzly SMS balance. |
| `/active_numbers`| None | Lists all pending numbers with 1-click cancel & refund buttons. |
| `/saved_links` | None | View all claimed 18-month Google Gemini activation links (paginated). |
| `/set_price` | `<amount>` | Sets max price limit for number rentals (e.g. `/set_price 0.45`). |
| `/set_service` | `<code>` | Sets target Grizzly service code (e.g. `/set_service jio`). |
| `/set_api_key` | `<key>` | Sets or updates your Grizzly SMS API Key. |
| `/help` | None | Multi-tab interactive user manual and FAQ. |

### 👑 Administrator Commands (Admin Chat Scope Only)
| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/admin` | None | Open Administrator Control Hub with security & user management. |
| `/users` | `[page]` | View and manage authorized user allowlist with 1-tap revocation. |
| `/adduser` | `<user_id>` | Add a numeric Telegram user ID to the allowlist. |
| `/removeuser`| `<user_id>` | Revoke a user's access immediately. |
| `/invite` | None | Generate a single-use 48-hour deep-link invite URL. |
| `/mode` | `[admin_only\|allowlist\|public]` | View or change current bot access policy. |
| `/clear` | `[depth]` | Delete tracked bot messages in current chat (default: 50). |
| `/clearall` | `confirm` | Bulk purge tracked messages across all tracked chats (requires `confirm`). |
| `/setup` | None | Force immediate re-sync of bot profile name, bio, and avatar. |
| `/stats` | None | View live system metrics, restored balance & productivity matrix. |

---

## 📱 Interactive Keyboard Layouts

### Main Dashboard Keyboard
```text
┌─────────────────────────────────┬─────────────────────────────────┐
│     🛒 Buy 1 Number             │      ⚡ Start Auto-Hunt         │
├─────────────────────────────────┴─────────────────────────────────┤
│                  🛑 STOP TASK & REFUND (Sticky)                    │
├─────────────────────────────────┬─────────────────────────────────┤
│     💰 Wallet Balance           │      🔑 Setup API Key           │
├─────────────────────────────────┼─────────────────────────────────┤
│     💵 Max Price                │      🏷️ Service Code            │
├─────────────────────────────────┼─────────────────────────────────┤
│     📱 Active Numbers           │      📜 Claimed Links (1-Tap)   │
├─────────────────────────────────┼─────────────────────────────────┤
│     📊 System Stats             │      📖 User Guide & Help       │
├─────────────────────────────────┴─────────────────────────────────┤
│                     ⚙️ Admin Control Hub (Admins)                  │
└───────────────────────────────────────────────────────────────────┘
```

### Admin Control Hub Keyboard
```text
┌─────────────────────────────────┬─────────────────────────────────┐
│     👥 User Management          │      🎟️ Generate Invite         │
├─────────────────────────────────┼─────────────────────────────────┤
│     🛡️ Mode: ALLOWLIST          │      🔄 Re-Sync Profile         │
├─────────────────────────────────┼─────────────────────────────────┤
│     🧹 Clear This Chat          │      💥 Clear All Chats         │
├─────────────────────────────────┴─────────────────────────────────┤
│                     🔙 Back to Dashboard                          │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Brand Identity Suite

Located in `assets/brand/`:
- **`tokens.json`**: Official color palette and design tokens:
  - Electric Cyan: `#00D9FF`
  - Cobalt Blue: `#246BFD`
  - Jio Red: `#E53945`
  - Metallic Silver: `#C8D3E0`
  - Deep Midnight Navy: `#07111F`
- **`BRAND_BRIEF.md`**: Brand personality, visual guidelines, and typography.
- **`FONTS.md`**: Unicode typography mappings (Mathematical Bold Serif, Monospace, Small Caps).
- **`logo.jpg`**: 640x640 circular profile avatar with cybernetic targeting reticle and diamond AI spark.
- **`banner.jpg` & `banner_vertical.jpg`**: 1536x2048 (3:4 portrait vertical) welcome hero banner sent with `/start`.

---

## 🛠️ Configuration Template (`.env.example`)

Copy `.env.example` to `.env` or use `setup.bat`:

```ini
# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Numeric Admin IDs (comma-separated, e.g. 123456789)
ADMIN_IDS=

# Access Control Policy: admin_only | allowlist | public
ACCESS_MODE=admin_only

# Grizzly SMS API Key (from https://grizzlysms.com/profile/settings)
GRIZZLY_API_KEY=your_grizzly_api_key_here

# Default Service code for MyJio 6-digit OTP delivery (jio or mjo)
DEFAULT_SERVICE_CODE=jio

# Country ID for India on Grizzly SMS (22 = India)
DEFAULT_COUNTRY_ID=22

# Maximum price per number in USD (e.g. 0.40, 0.45)
DEFAULT_MAX_PRICE=0.45

# Optional proxy (HTTP or SOCKS5)
PROXY=

# Polling and timeout settings (seconds)
OTP_TIMEOUT=90
POLL_INTERVAL=3
AUTO_SCAN_DELAY=2
```

---

## 🛡️ Zero-Loss Balance Architecture

```
Rented Virtual Number: +91XXXXXXXXXX
           │
           ▼
[ Jio Mobility API Check ] ──> /recharge/mobility/number/{mobile}
           │
    ┌──────┴─────────────────────────────────┐
    ▼                                        ▼
[ Non-Jio OR Inactive Plan ]        [ Valid Active Jio Number ]
    │                                        │
    ▼                                        ▼
[ Hand to RefundWatcherAgent ]       [ Dispatch Jio OTP ]
    │                                        │
    ▼                                        ▼
[ Wait 60-90s Lock Expiry ]          [ Poll 6-Digit OTP ]
    │                                        │
    ▼                                        ▼
[ Grizzly setStatus(id, 8) ]        [ Extract Gemini Link (Z0241) ]
    │                                        │
    ▼                                        ▼
💰 100% Refunded (ACCESS_CANCEL)    🎁 18-Month Gemini Pro Claimed!
```

---

## 🔒 Security & Privacy Guarantees

1. **Fail-Closed Gatekeeper**: If a user role cannot be positively verified, access is denied by default.
2. **Zero Plaintext Token Logging**: Bot tokens and API keys are automatically redacted in all terminal logs and error dumps.
3. **No Message Content Storing**: The message tracker only records `chat_id`, `message_id`, and `created_epoch`. User chat text is never persisted.
4. **Honest 48-Hour Telegram Limits**: Telegram Bot API strictly forbids deleting messages older than 48 hours. The bot transparently reports any messages that could not be deleted due to this Telegram restriction.
5. **Tamper-Evident Audit Logging**: Every administrative action (mode changes, user additions/removals, invite generation) is logged with timestamp in SQLite table `admin_audit_log`.

---

## 📄 License
MIT License. Created for legitimate automation and promotional entitlement redemption.
