#!/usr/bin/env python3
"""Generate slate PNGs for the Bags scratch cut."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
W, H = 1920, 1080

BG = (10, 10, 20)              # near-black
PURPLE = (153, 69, 255)        # Solana #9945FF
TEAL = (20, 241, 149)          # Solana #14F195
WHITE = (245, 245, 250)
DIM = (140, 140, 160)

# Font candidates on macOS
FONT_REG = "/System/Library/Fonts/Helvetica.ttc"
FONT_MONO = "/System/Library/Fonts/Menlo.ttc"

def font(path, size):
    return ImageFont.truetype(path, size)

def text_w(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0]

def make_slate(filename, tag, timecode, title, subtitle, footer="[ scratch cut placeholder — drop screen recording here ]"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Border rect
    d.rectangle([60, 60, W - 60, H - 60], outline=PURPLE, width=4)

    # Tag (top-left) and timecode (top-right)
    f_mono = font(FONT_MONO, 28)
    d.text((100, 100), tag, fill=TEAL, font=f_mono)
    tc_w = text_w(d, timecode, f_mono)
    d.text((W - 100 - tc_w, 100), timecode, fill=TEAL, font=f_mono)

    # Title (centered)
    f_title = font(FONT_REG, 84)
    tw = text_w(d, title, f_title)
    d.text(((W - tw) / 2, 420), title, fill=WHITE, font=f_title)

    # Subtitle (centered)
    f_sub = font(FONT_REG, 44)
    sw = text_w(d, subtitle, f_sub)
    d.text(((W - sw) / 2, 560), subtitle, fill=PURPLE, font=f_sub)

    # Footer (centered, bottom)
    f_foot = font(FONT_MONO, 22)
    fw = text_w(d, footer, f_foot)
    d.text(((W - fw) / 2, H - 180), footer, fill=DIM, font=f_foot)

    img.save(OUT / filename, "PNG")
    print(f"wrote {filename}")

def make_outro_overlay():
    """Transparent overlay PNG: 'Monitor × MiroShark' wordmark for outro shot."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    f_mark = font(FONT_REG, 96)
    f_sub = font(FONT_REG, 46)
    f_foot = font(FONT_MONO, 30)

    mark = "Monitor × MiroShark"
    sub = "Zero Human Labs"
    foot = "Bags Hackathon 2026  ·  Solana"

    # Drop a soft dark band behind the text for legibility
    d.rectangle([0, H // 2 - 180, W, H // 2 + 180], fill=(0, 0, 0, 140))

    mw = text_w(d, mark, f_mark)
    d.text(((W - mw) / 2, H // 2 - 130), mark, fill=WHITE, font=f_mark)
    sw = text_w(d, sub, f_sub)
    d.text(((W - sw) / 2, H // 2 + 10), sub, fill=TEAL, font=f_sub)
    fw = text_w(d, foot, f_foot)
    d.text(((W - fw) / 2, H - 160), foot, fill=PURPLE, font=f_foot)

    img.save(OUT / "outro-overlay.png", "PNG")
    print("wrote outro-overlay.png")

if __name__ == "__main__":
    make_slate("slate-02-dashboard.png",
               "SHOT 2 — SCREEN", "0:12 — 0:26",
               "Monitor dashboard",
               "live Bags.fm token feed  ·  composite risk score")
    make_slate("slate-03-risk.png",
               "SHOT 3 — SCREEN", "0:26 — 0:40",
               "Composite risk gauge",
               "pool · fees · price · velocity     →     green / amber / red")
    make_slate("slate-05-quartz-nav.png",
               "SHOT 5 — SCREEN", "1:15 — 1:30",
               "Quartz graph — navigate",
               "click persona  →  belief trajectory across rounds")
    make_slate("slate-06-quartz-react.png",
               "SHOT 6 — SCREEN", "1:30 — 1:45",
               "Quartz cluster + ReACT",
               "consensus card  ·  cluster convergence")
    make_slate("slate-07-x402.png",
               "SHOT 7 — TERMINAL", "1:45 — 2:00",
               "x402 payment flow",
               "curl 402  →  sign USDC on devnet  →  200 JSON")
    make_slate("slate-08-explorer.png",
               "SHOT 8 — SCREEN", "2:00 — 2:15",
               "Solana Explorer",
               "on-chain USDC settlement transaction")
    make_outro_overlay()
