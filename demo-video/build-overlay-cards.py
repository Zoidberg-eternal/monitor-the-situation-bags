"""Generate transparent PNG overlay cards for the Bags video.

Usage:
  python3 build-overlay-cards.py                  # rough-cut: 1280x720 + watermark
  python3 build-overlay-cards.py --final          # final: 1920x1080, no watermark
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/tmp/font-arial-bold.ttf"
FONT_REG = "/tmp/font-arial.ttf"

parser = argparse.ArgumentParser()
parser.add_argument("--final", action="store_true", help="emit 1920x1080 final-cut cards (no watermark)")
ARGS = parser.parse_args()

if ARGS.final:
    W, H = 1920, 1080
    SCALE = 1.5  # 1080p / 720p
else:
    W, H = 1280, 720
    SCALE = 1.0


def _sz(px: int) -> int:
    return int(round(px * SCALE))


def caption_card(name: str, text: str, fontsize: int = 30) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bar_h = _sz(70)
    bar_y = H - bar_h - _sz(30)
    draw.rectangle([(0, bar_y), (W, bar_y + bar_h)], fill=(0, 0, 0, 140))
    font = ImageFont.truetype(FONT_BOLD, _sz(fontsize))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2
    y = bar_y + (bar_h - th) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 240))
    img.save(os.path.join(OUT_DIR, name))


def outro_card(name: str) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 110))
    draw = ImageDraw.Draw(img)
    title = "Monitor x MiroShark"
    sub = "Zero Human Labs - Bags Hackathon 2026"
    repo = "github.com/Zoidberg-eternal/monitor-the-situation-stellar"

    fT = ImageFont.truetype(FONT_BOLD, _sz(86))
    fS = ImageFont.truetype(FONT_REG, _sz(32))
    fR = ImageFont.truetype(FONT_REG, _sz(22))

    bb = draw.textbbox((0, 0), title, font=fT)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) // 2, H // 2 - th - _sz(30)), title, font=fT, fill=(255, 255, 255, 255))

    bb = draw.textbbox((0, 0), sub, font=fS)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) // 2, H // 2 + _sz(30)), sub, font=fS, fill=(220, 220, 230, 255))

    bb = draw.textbbox((0, 0), repo, font=fR)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) // 2, H - _sz(70)), repo, font=fR, fill=(180, 180, 200, 220))

    img.save(os.path.join(OUT_DIR, name))


def watermark_card(name: str) -> None:
    """Tiny upper-right ROUGH CUT watermark for full-video overlay."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_BOLD, _sz(18))
    text = "ROUGH CUT v1 - stand-in visuals"
    bb = draw.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = _sz(8)
    x, y = W - tw - _sz(24), _sz(20)
    draw.rectangle(
        [(x - pad, y - pad), (x + tw + pad, y + th + pad)],
        fill=(0, 0, 0, 160),
    )
    draw.text((x, y - bb[1]), text, font=f, fill=(255, 200, 100, 255))
    img.save(os.path.join(OUT_DIR, name))


def main() -> None:
    caption_card("ovl-01-hook.png", "BAGS.FM  //  30s rug cycle  //  humans out of the loop", 28)
    caption_card("ovl-02-monitor.png", "MONITOR  //  4-signal composite risk", 32)
    caption_card("ovl-03-miroshark.png", "MIROSHARK  //  100s of personas  //  5-layer grounding", 26)
    caption_card("ovl-04-quartz.png", "QUARTZ graph  //  every belief traced", 32)
    caption_card("ovl-05-x402.png", "x402  //  USDC on Solana devnet  //  pay-per-call", 28)
    outro_card("ovl-06-outro.png")
    if ARGS.final:
        # No watermark on the final cut.
        wm = os.path.join(OUT_DIR, "ovl-07-watermark.png")
        if os.path.exists(wm):
            os.remove(wm)
    else:
        watermark_card("ovl-07-watermark.png")
    print(f"Cards generated at {W}x{H} ({'final' if ARGS.final else 'rough-cut'}).")


if __name__ == "__main__":
    main()
