"""
Master Vertical Welcome Banner Generator for Jio Gemini Pro 18M Hunter.
Generates an ultra-premium 3:4 vertical portrait banner (1536 x 2048 pixels)
incorporating the official master logo avatar, futuristic HUD scanner rings,
geometric cyber typography, glassmorphism feature cards, and status footer.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpg")
OUTPUT_VERTICAL_BANNER = os.path.join(ASSETS_DIR, "banner_vertical.jpg")
OUTPUT_BANNER = os.path.join(ASSETS_DIR, "banner.jpg")

# Canvas Dimensions
WIDTH = 1536
HEIGHT = 2048

# Color Palette (PRD §5 / Master Specification)
C_BG_TOP = (7, 17, 31)          # #07111F Deep Midnight Navy
C_BG_BOT = (3, 7, 17)           # #030711 Black-Blue
C_CYAN = (0, 217, 255)          # #00D9FF Electric Cyan
C_COBALT = (36, 107, 253)       # #246BFD Premium Cobalt Blue
C_RED = (229, 57, 69)           # #E53945 Jio Crimson Red
C_SILVER = (200, 211, 224)      # #C8D3E0 Metallic Silver
C_WHITE = (248, 250, 252)       # Clean White
C_SURFACE = (15, 30, 54)        # Glassmorphism Card Surface
C_BORDER = (0, 217, 255, 60)    # Cyan Border (with alpha)

def load_fonts():
    font_path_bahn = r"C:\Windows\Fonts\bahnschrift.ttf"
    font_path_segoe_b = r"C:\Windows\Fonts\segoeuib.ttf"
    font_path_segoe = r"C:\Windows\Fonts\segoeui.ttf"
    
    try:
        f_title = ImageFont.truetype(font_path_bahn, 72)
        f_badge = ImageFont.truetype(font_path_bahn, 60)
        f_subtitle = ImageFont.truetype(font_path_segoe_b, 38)
        f_desc = ImageFont.truetype(font_path_segoe, 28)
        f_card_title = ImageFont.truetype(font_path_bahn, 34)
        f_card_desc = ImageFont.truetype(font_path_segoe, 22)
        f_footer = ImageFont.truetype(font_path_bahn, 24)
    except Exception:
        f_title = ImageFont.load_default()
        f_badge = f_title
        f_subtitle = f_title
        f_desc = f_title
        f_card_title = f_title
        f_card_desc = f_title
        f_footer = f_title

    return {
        "title": f_title,
        "badge": f_badge,
        "subtitle": f_subtitle,
        "desc": f_desc,
        "card_title": f_card_title,
        "card_desc": f_card_desc,
        "footer": f_footer,
    }

def create_vertical_banner():
    # 1. Base Gradient Background
    img = Image.new("RGBA", (WIDTH, HEIGHT), C_BG_TOP)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(C_BG_TOP[0] * (1 - ratio) + C_BG_BOT[0] * ratio)
        g = int(C_BG_TOP[1] * (1 - ratio) + C_BG_BOT[1] * ratio)
        b = int(C_BG_TOP[2] * (1 - ratio) + C_BG_BOT[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # 2. Atmospheric Ambient Glow Layers
    glow_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    
    # Top Logo Cyan/Cobalt Glow
    cx_logo, cy_logo = 768, 410
    glow_draw.ellipse([cx_logo - 360, cy_logo - 360, cx_logo + 360, cy_logo + 360], fill=(0, 217, 255, 38))
    glow_draw.ellipse([cx_logo - 260, cy_logo - 260, cx_logo + 260, cy_logo + 260], fill=(36, 107, 253, 50))
    
    # Bottom Center Glow
    glow_draw.ellipse([768 - 450, 1600 - 300, 768 + 450, 1600 + 300], fill=(36, 107, 253, 20))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(60))
    img = Image.alpha_composite(img, glow_img)
    draw = ImageDraw.Draw(img)

    # 3. Futuristic Circuit Traces & Orbital Scanner Rings in Background
    # Outer Tech Concentric Circles
    for r, width, color in [
        (330, 2, (0, 217, 255, 45)),
        (310, 1, (36, 107, 253, 40)),
        (280, 2, (0, 217, 255, 80)),
        (260, 3, (200, 211, 224, 70)),
    ]:
        draw.ellipse([cx_logo - r, cy_logo - r, cx_logo + r, cy_logo + r], outline=color, width=width)

    # Crosshair Reticle Tick Marks at 12, 3, 6, 9 o'clock
    tick_len = 28
    for angle_deg in [0, 90, 180, 270]:
        rad = math.radians(angle_deg)
        x1 = cx_logo + int(310 * math.cos(rad))
        y1 = cy_logo + int(310 * math.sin(rad))
        x2 = cx_logo + int((310 + tick_len) * math.cos(rad))
        y2 = cy_logo + int((310 + tick_len) * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=C_CYAN + (200,), width=4)
        # Red precision dot at tips
        draw.ellipse([x2 - 3, y2 - 3, x2 + 3, y2 + 3], fill=C_RED + (240,))

    # Corner HUD Tech Brackets
    hud_margin = 48
    hud_bracket_len = 60
    for cx_b, cy_b, dx, dy in [
        (hud_margin, hud_margin, 1, 1),
        (WIDTH - hud_margin, hud_margin, -1, 1),
        (hud_margin, HEIGHT - hud_margin, 1, -1),
        (WIDTH - hud_margin, HEIGHT - hud_margin, -1, -1),
    ]:
        draw.line([(cx_b, cy_b), (cx_b + dx * hud_bracket_len, cy_b)], fill=C_CYAN + (120,), width=3)
        draw.line([(cx_b, cy_b), (cx_b, cy_b + dy * hud_bracket_len)], fill=C_CYAN + (120,), width=3)

    # 4. Composite Master Logo Avatar (Centered Top)
    if os.path.exists(LOGO_PATH):
        with Image.open(LOGO_PATH) as logo_raw:
            logo_rgb = logo_raw.convert("RGBA")
            # Circular mask for logo
            logo_size = 480
            logo_resized = logo_rgb.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", (logo_size, logo_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, logo_size, logo_size], fill=255)
            
            logo_x = cx_logo - (logo_size // 2)
            logo_y = cy_logo - (logo_size // 2)
            img.paste(logo_resized, (logo_x, logo_y), mask)

    # Metallic Rim Ring around Logo
    draw.ellipse([cx_logo - 242, cy_logo - 242, cx_logo + 242, cy_logo + 242], outline=C_CYAN + (220,), width=4)

    # 5. Middle Section — Typography
    fonts = load_fonts()

    # Brand Title: JIO GEMINI PRO
    title_text = "JIO GEMINI PRO"
    bbox = fonts["title"].getbbox(title_text)
    tw = bbox[2] - bbox[0]
    draw.text((768 - (tw // 2), 700), title_text, font=fonts["title"], fill=C_WHITE)

    # 18M HUNTER badge / accent
    sub_title = "18M HUNTER"
    bbox2 = fonts["badge"].getbbox(sub_title)
    tw2 = bbox2[2] - bbox2[0]
    # Draw glowing pill badge behind 18M HUNTER
    pill_w = tw2 + 64
    pill_h = 76
    pill_x = 768 - (pill_w // 2)
    pill_y = 790
    draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=16, fill=(36, 107, 253, 50), outline=C_CYAN + (180,), width=2)
    draw.text((768 - (tw2 // 2), pill_y + 6), sub_title, font=fonts["badge"], fill=C_CYAN)

    # Horizontal Tech Divider
    div_y = 905
    draw.line([(768 - 380, div_y), (768 + 380, div_y)], fill=(36, 107, 253, 80), width=2)
    draw.polygon([(768, div_y - 6), (768 + 8, div_y), (768, div_y + 6), (768 - 8, div_y)], fill=C_CYAN)

    # Welcome Headline: WELCOME TO THE HUNT
    w_text = "WELCOME TO THE HUNT"
    bbox3 = fonts["subtitle"].getbbox(w_text)
    tw3 = bbox3[2] - bbox3[0]
    draw.text((768 - (tw3 // 2), 935), w_text, font=fonts["subtitle"], fill=C_WHITE)

    # Secondary Line: Your AI-Powered Automation Command Center
    desc_text = "Your AI-Powered Automation Command Center"
    bbox4 = fonts["desc"].getbbox(desc_text)
    tw4 = bbox4[2] - bbox4[0]
    draw.text((768 - (tw4 // 2), 990), desc_text, font=fonts["desc"], fill=C_SILVER)

    # 6. Lower Section — 4 Futuristic Interface Feature Modules
    cards = [
        ("JIO MOBILITY SCANNER", "Active Indian (+91) carrier validation & real-time recharge check", "📡"),
        ("SMART VERIFICATION", "Automated 6-digit MyJio Selfcare OTP delivery & authentication", "🔐"),
        ("VOUCHER WORKFLOW", "1-Click Google Gemini Pro 18-Month entitlement redemption (Z0241)", "🎁"),
        ("REFUND STATUS MONITOR", "Zero-Loss 24/7 background agent with 100% credit protection", "🛡️"),
    ]

    card_start_y = 1075
    card_h = 135
    card_w = 1200
    card_gap = 26
    card_x = 768 - (card_w // 2)

    for idx, (c_title, c_desc, c_icon) in enumerate(cards):
        cy_card = card_start_y + (idx * (card_h + card_gap))
        
        # Semi-transparent glassmorphism card background
        card_overlay = Image.new("RGBA", (card_w, card_h), (12, 25, 46, 210))
        c_draw = ImageDraw.Draw(card_overlay)
        
        # Border
        c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=14, outline=(0, 217, 255, 70), width=2)
        
        # Left Accent Neon Strip
        strip_color = C_CYAN if idx % 2 == 0 else C_COBALT
        c_draw.rounded_rectangle([0, 0, 8, card_h], radius=4, fill=strip_color + (255,))
        
        img.paste(card_overlay, (card_x, cy_card), card_overlay)
        
        # Draw Card Text directly onto main canvas
        draw = ImageDraw.Draw(img)
        # Icon / Badge Tag
        badge_tag = f"0{idx+1} // {c_title}"
        draw.text((card_x + 36, cy_card + 28), badge_tag, font=fonts["card_title"], fill=C_CYAN)
        draw.text((card_x + 36, cy_card + 76), c_desc, font=fonts["card_desc"], fill=C_SILVER)
        
        # Right Status Indicator
        status_tag = "ACTIVE" if idx < 3 else "PROTECTED"
        draw.rounded_rectangle([card_x + card_w - 180, cy_card + 46, card_x + card_w - 36, cy_card + 88], radius=8, fill=(0, 217, 255, 30), outline=(0, 217, 255, 120), width=1)
        draw.text((card_x + card_w - 160, cy_card + 54), status_tag, font=fonts["footer"], fill=C_WHITE)

    # 7. Lower Illuminated Rail Divider & Footer
    footer_div_y = 1760
    draw.line([(768 - 480, footer_div_y), (768 + 480, footer_div_y)], fill=(0, 217, 255, 80), width=2)
    # Red accent center notches
    draw.line([(768 - 30, footer_div_y), (768 + 30, footer_div_y)], fill=C_RED, width=3)

    # Footer Text: SYSTEM INTERFACE • READY
    footer_text = "● SYSTEM INTERFACE • READY"
    bbox_f = fonts["footer"].getbbox(footer_text)
    tw_f = bbox_f[2] - bbox_f[0]
    draw.text((768 - (tw_f // 2), 1795), footer_text, font=fonts["footer"], fill=C_CYAN)

    # Sub-footer credit / version
    sub_foot = "JIO GEMINI PRO 18M HUNTER BOT v2.0 • HIGH-SPEED SCANNING ENGINE"
    bbox_sf = fonts["card_desc"].getbbox(sub_foot)
    tw_sf = bbox_sf[2] - bbox_sf[0]
    draw.text((768 - (tw_sf // 2), 1845), sub_foot, font=fonts["card_desc"], fill=(140, 160, 185))

    # Convert to RGB & Save
    final_rgb = img.convert("RGB")
    final_rgb.save(OUTPUT_VERTICAL_BANNER, "JPEG", quality=95)
    print(f"Generated Vertical Banner: {OUTPUT_VERTICAL_BANNER} (1536x2048, 3:4)")

    # Also save as the active banner.jpg for Telegram bot welcome dispatch!
    final_rgb.save(OUTPUT_BANNER, "JPEG", quality=95)
    print(f"Updated Bot Welcome Banner: {OUTPUT_BANNER}")

if __name__ == "__main__":
    create_vertical_banner()
