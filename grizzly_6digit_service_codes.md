# 📱 Grizzly SMS 6-Digit OTP Service Codes Reference (India / Global)

A complete reference guide of all verified service codes on **Grizzly SMS** that strictly return **6-digit verification codes** (matching Reliance Jio, Google, WhatsApp, Amazon, etc.).

---

## ⚡ 1. Jio Telecom Routes (For MyJio & Carrier Validation)

| Service Code | Platform Name | OTP Length | Typical Price (USD) | Availability (Numbers) | Notes |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `jio` | Reliance Jio / MyJio | 6 Digits | $0.10 | ~479,000+ | Primary official route for Jio Selfcare OTP |
| `jii` | Jio Secondary Carrier | 6 Digits | $0.10 | ~163,000+ | High-volume secondary pool for Jio |
| `mjo` | MyJio Alternative Route | 6 Digits | $0.15 | ~3,340+ | Alternative route for MyJio 6-digit OTP |

---

## 🌐 2. Major Tech & Cloud Services (6 Digits)

| Service Code | Platform Name | OTP Length | Typical Price (USD) | Availability (Numbers) | Example OTP Format |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `go` | Google / Gmail / YouTube | 6 Digits | $0.115 | ~189,000+ | `G-123456` or `123456` |
| `ms` | Microsoft / Outlook / Azure | 6 Digits | $0.065 | High | `123456` |
| `ds` | Discord | 6 Digits | $0.070 | ~70,600+ | `123456` |
| `nf` | Netflix | 6 Digits | $0.075 | ~15,300+ | `123456` |
| `ap` | Apple ID / iCloud | 6 Digits | $0.150 | Normal | `123 456` |
| `ya` | Yandex | 6 Digits | $0.050 | High | `123456` |

---

## 💬 3. Social Media & Messaging (6 Digits)

| Service Code | Platform Name | OTP Length | Typical Price (USD) | Availability (Numbers) | Example OTP Format |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `wa` | WhatsApp | 6 Digits | $0.850 | ~67,100+ | `123-456` |
| `fb` | Facebook / Meta | 6 Digits | $0.075 | ~268,000+ | `123456` |
| `ig` | Instagram | 6 Digits | $0.063 | ~158,000+ | `123 456` |
| `tw` | Twitter / X | 6 Digits | $0.040 | ~19,900+ | `123456` |
| `sn` | Snapchat | 6 Digits | $0.040 | ~800+ | `123456` |
| `tg` | Telegram | 5 or 6 Digits | $0.354 | ~1,980,000+ | Usually 5 or 6 digits |

---

## 🛒 4. Indian E-Commerce, Food & Payments (6 Digits)

| Service Code | Platform Name | OTP Length | Typical Price (USD) | Availability (Numbers) | Notes |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `am` | Amazon India | 6 Digits | $0.090 | ~73,700+ | Amazon Shopping & Prime |
| `me` | Meesho | 6 Digits | $0.090 | ~224,000+ | Indian Social Commerce |
| `fl` | Flipkart | 6 Digits | $0.090 | ~200+ | E-commerce shopping |
| `sw` | Swiggy | 6 Digits | $0.176 | ~520+ | Food Delivery & Instamart |
| `zm` | Zomato | 6 Digits | $0.150 | Normal | Food Delivery & Blinkit |
| `ptm` | Paytm | 6 Digits | $0.120 | Normal | Wallet & Payments |

---

## ❌ 5. Services that DO NOT Give 6 Digits (Do NOT Use)

| Service Code | Platform Name | Actual OTP Length | Why Avoid |
| :---: | :--- | :---: | :--- |
| `air` | Airtel India | **4 Digits** | Airtel Thanks app sends 4-digit codes |
| `vi` | Vodafone Idea (Vi) | **4 Digits** | Vi Selfcare sends 4-digit codes |
| `ub` | Uber | **4 Digits** | Ride verification uses 4-digit codes |

---

## ⌨️ How to Use in Jio Gemini Hunter Bot

### 1. Set Global Default Service:
Send in bot chat:
```text
/set_service <service_code>
```
*Example:* `/set_service mjo` or `/set_service jii`

### 2. Single Purchase with Custom Code:
```text
/buy <service_code>
```
*Example:* `/buy jii`

### 3. Auto-Hunt Loop with Custom Code:
```text
/hunt <attempts> <service_code>
```
*Example:* `/hunt 10 mjo`
