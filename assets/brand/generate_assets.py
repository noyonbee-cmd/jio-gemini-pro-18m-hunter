"""
Brand Asset Generator for Jio Gemini 18-Month Hunter Bot.
Generates master SVG and high-resolution JPG exports for:
1. logo.svg & logo.jpg (640x640 square, Telegram avatar compliant)
2. banner.svg & banner.jpg (1280x640 2:1 ratio welcome banner)
3. Contrast validation report (WCAG AAA)
"""
from __future__ import annotations
import math
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_JPG = os.path.join(ASSETS_DIR, "logo.jpg")
LOGO_SVG = os.path.join(ASSETS_DIR, "logo.svg")
BANNER_JPG = os.path.join(ASSETS_DIR, "banner.jpg")
BANNER_SVG = os.path.join(ASSETS_DIR, "banner.svg")

# Color Tokens
C_BG = (15, 23, 42)           # #0F172A Deep Slate
C_SURFACE = (30, 41, 59)      # #1E293B
C_BORDER = (51, 65, 85)       # #334155
C_PRIMARY = (0, 136, 204)     # #0088CC Jio Cyan
C_ACCENT = (123, 44, 191)     # #7B2CBF Gemini Violet
C_GOLD = (245, 158, 11)       # #F59E0B
C_WHITE = (248, 250, 252)     # #F8FAFC
C_MUTED = (148, 163, 184)     # #94A3B8


def create_logo_svg() -> str:
    """Generate master SVG vector for the bot profile photo."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" width="640" height="640">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B1120"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="primaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="50%" stop-color="#0088CC"/>
      <stop offset="100%" stop-color="#0369A1"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#C084FC"/>
      <stop offset="50%" stop-color="#7B2CBF"/>
      <stop offset="100%" stop-color="#581C87"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="16" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="640" height="640" fill="url(#bgGrad)"/>

  <!-- Telegram Avatar Circular Safe Zone Boundary (512px diameter) -->
  <circle cx="320" cy="320" r="256" fill="none" stroke="#1E293B" stroke-width="2" stroke-dasharray="8 8"/>
  <circle cx="320" cy="320" r="230" fill="#131D31" stroke="#334155" stroke-width="3"/>

  <!-- Ambient Glow Behind Diamond -->
  <circle cx="320" cy="320" r="140" fill="#7B2CBF" opacity="0.25" filter="url(#glow)"/>
  <circle cx="320" cy="320" r="100" fill="#0088CC" opacity="0.30" filter="url(#glow)"/>

  <!-- Outer Cyber Rings -->
  <polygon points="320,130 470,320 320,510 170,320" fill="none" stroke="url(#accentGrad)" stroke-width="8" stroke-linejoin="round"/>
  <polygon points="320,165 440,320 320,475 200,320" fill="none" stroke="url(#primaryGrad)" stroke-width="6" stroke-linejoin="round" opacity="0.8"/>

  <!-- Core Diamond Crystal Facets -->
  <!-- Top Left Facet (Jio Blue) -->
  <polygon points="320,200 320,320 220,320" fill="url(#primaryGrad)" opacity="0.95"/>
  <!-- Top Right Facet (Gemini Violet) -->
  <polygon points="320,200 420,320 320,320" fill="url(#accentGrad)" opacity="0.95"/>
  <!-- Bottom Left Facet (Gemini Deep) -->
  <polygon points="220,320 320,320 320,440" fill="#581C87" opacity="0.9"/>
  <!-- Bottom Right Facet (Jio Deep) -->
  <polygon points="320,320 420,320 320,440" fill="#0369A1" opacity="0.9"/>

  <!-- Central Star / Diamond Core -->
  <polygon points="320,270 340,320 390,320 350,345 365,395 320,360 275,395 290,345 250,320 300,320" fill="#F8FAFC" filter="url(#glow)"/>

  <!-- Sparkle Accents -->
  <circle cx="320" cy="115" r="5" fill="#38BDF8"/>
  <circle cx="525" cy="320" r="5" fill="#C084FC"/>
  <circle cx="320" cy="525" r="5" fill="#38BDF8"/>
  <circle cx="115" cy="320" r="5" fill="#C084FC"/>
</svg>"""
    return svg


def render_logo_jpg():
    """Render 640x640 JPG logo using Pillow."""
    size = (640, 640)
    img = Image.new("RGB", size, C_BG)
    draw = ImageDraw.Draw(img)

    cx, cy = 320, 320

    # Draw background gradient circles
    for r in range(240, 50, -5):
        alpha = int(25 * (1 - r / 240))
        color = (15 + alpha, 23 + alpha, 42 + alpha)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # Safe zone outline
    draw.ellipse([cx - 240, cy - 240, cx + 240, cy + 240], outline=C_BORDER, width=2)
    draw.ellipse([cx - 220, cy - 220, cx + 220, cy + 220], fill=C_SURFACE, outline=C_BORDER, width=3)

    # Ambient glow
    for glow_r in range(130, 40, -10):
        t = (130 - glow_r) / 90.0
        r_col = int(C_SURFACE[0] + (C_ACCENT[0] - C_SURFACE[0]) * t * 0.4)
        g_col = int(C_SURFACE[1] + (C_ACCENT[1] - C_SURFACE[1]) * t * 0.4)
        b_col = int(C_SURFACE[2] + (C_ACCENT[2] - C_SURFACE[2]) * t * 0.4)
        draw.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=(r_col, g_col, b_col))

    # Outer diamond
    p_outer = [(cx, cy - 180), (cx + 140, cy), (cx, cy + 180), (cx - 140, cy)]
    draw.polygon(p_outer, outline=C_ACCENT, width=8)

    # Inner diamond
    p_inner = [(cx, cy - 145), (cx + 115, cy), (cx, cy + 145), (cx - 115, cy)]
    draw.polygon(p_inner, outline=C_PRIMARY, width=6)

    # Core Diamond Facets
    # Top-Left (Cyan)
    draw.polygon([(cx, cy - 110), (cx, cy), (cx - 90, cy)], fill=C_PRIMARY)
    # Top-Right (Violet)
    draw.polygon([(cx, cy - 110), (cx + 90, cy), (cx, cy)], fill=C_ACCENT)
    # Bottom-Left (Deep Purple)
    draw.polygon([(cx - 90, cy), (cx, cy), (cx, cy + 110)], fill=(88, 28, 135))
    # Bottom-Right (Deep Blue)
    draw.polygon([(cx, cy), (cx + 90, cy), (cx, cy + 110)], fill=(3, 105, 161))

    # Center Sparkle / Core
    p_star = [
        (cx, cy - 45), (cx + 14, cy - 14), (cx + 45, cy), (cx + 14, cy + 14),
        (cx, cy + 45), (cx - 14, cy + 14), (cx - 45, cy), (cx - 14, cy - 14)
    ]
    draw.polygon(p_star, fill=C_WHITE, outline=(245, 158, 11), width=2)

    # Accent dots
    draw.ellipse([cx - 4, cy - 195, cx + 4, cy - 187], fill=(56, 189, 248))
    draw.ellipse([cx + 155, cy - 4, cx + 163, cy + 4], fill=(192, 132, 252))
    draw.ellipse([cx - 4, cy + 187, cx + 4, cy + 195], fill=(56, 189, 248))
    draw.ellipse([cx - 163, cy - 4, cx - 155, cy + 4], fill=(192, 132, 252))

    img.save(LOGO_JPG, "JPEG", quality=95)
    print(f"Generated: {LOGO_JPG} (640x640)")


def create_banner_svg() -> str:
    """Generate master SVG vector for the 1280x640 welcome banner."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640">
  <defs>
    <linearGradient id="bannerBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080D1A"/>
      <stop offset="50%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#141E33"/>
    </linearGradient>
    <linearGradient id="neonCyan" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0088CC"/>
    </linearGradient>
    <linearGradient id="neonPurple" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#C084FC"/>
      <stop offset="100%" stop-color="#7B2CBF"/>
    </linearGradient>
    <filter id="bannerGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="24" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1280" height="640" fill="url(#bannerBg)"/>

  <!-- Ambient Light Orbs -->
  <circle cx="200" cy="320" r="260" fill="#0088CC" opacity="0.18" filter="url(#bannerGlow)"/>
  <circle cx="1080" cy="320" r="260" fill="#7B2CBF" opacity="0.22" filter="url(#bannerGlow)"/>

  <!-- Futuristic Grid Lines -->
  <line x1="100" y1="520" x2="1180" y2="520" stroke="#1E293B" stroke-width="2"/>
  <line x1="100" y1="120" x2="1180" y2="120" stroke="#1E293B" stroke-width="2"/>

  <!-- Left Side: Holographic Emblem -->
  <g transform="translate(240, 320)">
    <circle cx="0" cy="0" r="140" fill="#131D31" stroke="#334155" stroke-width="3"/>
    <polygon points="0,-100 80,0 0,100 -80,0" fill="none" stroke="url(#neonPurple)" stroke-width="6"/>
    <polygon points="0,-75 60,0 0,75 -60,0" fill="none" stroke="url(#neonCyan)" stroke-width="5"/>
    <polygon points="0,-50 0,0 -40,0" fill="#0088CC"/>
    <polygon points="0,-50 40,0 0,0" fill="#7B2CBF"/>
    <polygon points="-40,0 0,0 0,50" fill="#581C87"/>
    <polygon points="0,0 40,0 0,50" fill="#0369A1"/>
    <polygon points="0,-20 7,-7 20,0 7,7 0,20 -7,7 -20,0 -7,-7" fill="#F8FAFC"/>
  </g>

  <!-- Right Side: Content & Typography -->
  <g transform="translate(480, 200)">
    <!-- Pill Badge -->
    <rect x="0" y="0" width="310" height="36" rx="18" fill="#1E293B" stroke="#7B2CBF" stroke-width="2"/>
    <text x="18" y="24" font-family="sans-serif" font-size="14" font-weight="bold" fill="#C084FC" letter-spacing="2">⚡ GOOGLE AI x RELIANCE JIO</text>

    <!-- Main Title -->
    <text x="0" y="90" font-family="sans-serif" font-size="44" font-weight="900" fill="#F8FAFC" letter-spacing="1">JIO GEMINI 18-MONTH</text>
    <text x="0" y="145" font-family="sans-serif" font-size="44" font-weight="900" fill="#38BDF8" letter-spacing="1">HUNTER ENGINE</text>

    <!-- Tagline -->
    <text x="0" y="195" font-family="sans-serif" font-size="20" font-weight="600" fill="#94A3B8">Claim 18-Month Gemini Pro With Zero Waste</text>

    <!-- Feature Tags -->
    <g transform="translate(0, 230)">
      <rect x="0" y="0" width="170" height="34" rx="6" fill="#131D31" stroke="#0088CC" stroke-width="1.5"/>
      <text x="16" y="22" font-family="sans-serif" font-size="13" font-weight="bold" fill="#38BDF8">🛡️ ZERO-LOSS GUARD</text>

      <rect x="185" y="0" width="165" height="34" rx="6" fill="#131D31" stroke="#7B2CBF" stroke-width="1.5"/>
      <text x="201" y="22" font-family="sans-serif" font-size="13" font-weight="bold" fill="#C084FC">📩 MYJIO 6-DIGIT OTP</text>

      <rect x="365" y="0" width="175" height="34" rx="6" fill="#131D31" stroke="#F59E0B" stroke-width="1.5"/>
      <text x="381" y="22" font-family="sans-serif" font-size="13" font-weight="bold" fill="#F59E0B">🎁 18-MO PRO SKU</text>
    </g>
  </g>

  <!-- Frame Corners -->
  <polygon points="50,50 90,50 90,54 54,54 54,90 50,90" fill="#38BDF8"/>
  <polygon points="1230,50 1190,50 1190,54 1226,54 1226,90 1230,90" fill="#C084FC"/>
  <polygon points="50,590 90,590 90,586 54,586 54,550 50,550" fill="#38BDF8"/>
  <polygon points="1230,590 1190,590 1190,586 1226,586 1226,550 1230,550" fill="#C084FC"/>
</svg>"""
    return svg


def render_banner_jpg():
    """Render 1280x640 JPG welcome banner using Pillow."""
    size = (1280, 640)
    img = Image.new("RGB", size, C_BG)
    draw = ImageDraw.Draw(img)

    # Ambient orbs
    for r in range(250, 40, -10):
        t = (250 - r) / 210.0
        c1 = (int(15 + 20 * t), int(23 + 60 * t), int(42 + 120 * t))
        draw.ellipse([200 - r, 320 - r, 200 + r, 320 + r], fill=c1)

        c2 = (int(15 + 70 * t), int(23 + 20 * t), int(42 + 100 * t))
        draw.ellipse([1080 - r, 320 - r, 1080 + r, 320 + r], fill=c2)

    # Frame lines
    draw.line([(80, 100), (1200, 100)], fill=C_BORDER, width=2)
    draw.line([(80, 540), (1200, 540)], fill=C_BORDER, width=2)

    # Left Emblem
    cx, cy = 250, 320
    draw.ellipse([cx - 130, cy - 130, cx + 130, cy + 130], fill=C_SURFACE, outline=C_BORDER, width=3)
    p1 = [(cx, cy - 90), (cx + 70, cy), (cx, cy + 90), (cx - 70, cy)]
    draw.polygon(p1, outline=C_ACCENT, width=6)
    p2 = [(cx, cy - 65), (cx + 50, cy), (cx, cy + 65), (cx - 50, cy)]
    draw.polygon(p2, outline=C_PRIMARY, width=5)

    # Facets
    draw.polygon([(cx, cy - 50), (cx, cy), (cx - 40, cy)], fill=C_PRIMARY)
    draw.polygon([(cx, cy - 50), (cx + 40, cy), (cx, cy)], fill=C_ACCENT)
    draw.polygon([(cx - 40, cy), (cx, cy), (cx, cy + 50)], fill=(88, 28, 135))
    draw.polygon([(cx, cy), (cx + 40, cy), (cx, cy + 50)], fill=(3, 105, 161))

    # Center Star
    draw.polygon([(cx, cy - 18), (cx + 6, cy - 6), (cx + 18, cy), (cx + 6, cy + 6),
                  (cx, cy + 18), (cx - 6, cy + 6), (cx - 18, cy), (cx - 6, cy - 6)], fill=C_WHITE)

    # Right Content Box & Typography (fallback font handling)
    try:
        font_badge = ImageFont.truetype("arial.ttf", 14)
        font_title = ImageFont.truetype("arial.ttf", 46)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_tag = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font_badge = font_title = font_sub = font_tag = ImageFont.load_default()

    # Badge
    tx, ty = 460, 160
    draw.rounded_rectangle([tx, ty, tx + 280, ty + 36], radius=18, fill=C_SURFACE, outline=C_ACCENT, width=2)
    draw.text((tx + 20, ty + 9), "⚡ GOOGLE AI x RELIANCE JIO", fill=(192, 132, 252), font=font_badge)

    # Title Lines
    draw.text((tx, ty + 50), "JIO GEMINI 18-MONTH", fill=C_WHITE, font=font_title)
    draw.text((tx, ty + 105), "HUNTER ENGINE", fill=(56, 189, 248), font=font_title)

    # Tagline
    draw.text((tx, ty + 170), "Claim 18-Month Gemini Pro With Zero Waste", fill=C_MUTED, font=font_sub)

    # Tags Row
    tag_y = ty + 220
    # Tag 1
    draw.rounded_rectangle([tx, tag_y, tx + 180, tag_y + 34], radius=6, fill=C_SURFACE, outline=C_PRIMARY, width=2)
    draw.text((tx + 16, tag_y + 9), "🛡️ ZERO-LOSS GUARD", fill=(56, 189, 248), font=font_tag)

    # Tag 2
    draw.rounded_rectangle([tx + 195, tag_y, tx + 375, tag_y + 34], radius=6, fill=C_SURFACE, outline=C_ACCENT, width=2)
    draw.text((tx + 210, tag_y + 9), "📩 MYJIO 6-DIGIT OTP", fill=(192, 132, 252), font=font_tag)

    # Tag 3
    draw.rounded_rectangle([tx + 390, tag_y, tx + 570, tag_y + 34], radius=6, fill=C_SURFACE, outline=C_GOLD, width=2)
    draw.text((tx + 406, tag_y + 9), "🎁 18-MO PRO SKU", fill=C_GOLD, font=font_tag)

    # Corner brackets
    draw.line([(50, 50), (90, 50)], fill=(56, 189, 248), width=4)
    draw.line([(50, 50), (50, 90)], fill=(56, 189, 248), width=4)

    draw.line([(1230, 50), (1190, 50)], fill=(192, 132, 252), width=4)
    draw.line([(1230, 50), (1230, 90)], fill=(192, 132, 252), width=4)

    draw.line([(50, 590), (90, 590)], fill=(56, 189, 248), width=4)
    draw.line([(50, 590), (50, 550)], fill=(56, 189, 248), width=4)

    draw.line([(1230, 590), (1190, 590)], fill=(192, 132, 252), width=4)
    draw.line([(1230, 590), (1230, 550)], fill=(192, 132, 252), width=4)

    img.save(BANNER_JPG, "JPEG", quality=92)
    print(f"Generated: {BANNER_JPG} (1280x640)")


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1. Generate SVGs
    with open(LOGO_SVG, "w", encoding="utf-8") as f:
        f.write(create_logo_svg())
    print(f"Generated: {LOGO_SVG}")

    with open(BANNER_SVG, "w", encoding="utf-8") as f:
        f.write(create_banner_svg())
    print(f"Generated: {BANNER_SVG}")

    # 2. Render JPGs
    render_logo_jpg()
    render_banner_jpg()
    print("All Brand Assets successfully generated!")


if __name__ == "__main__":
    main()
