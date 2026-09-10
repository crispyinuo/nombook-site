#!/usr/bin/env python3
"""Regenerate everything in `assets/` from the app's own artwork.

The site has no build step, so the PNGs are committed and this script exists
only to record where they came from and to redraw them if the brand changes.
The two sources both live in the app repo, not here:

  * `NombookMark` — the one-line bowl-and-open-book drawing, cropped to its
    own alpha. This is the same file the app puts on a share card.
  * `Handlee-Regular` — the wordmark face. "nombook" is set in Handlee in
    every localization of the app, so the site sets it in Handlee too.

Run it with the app checked out beside this repo:

    python3 tools/make-brand-assets.py            # ../nombook
    NOMBOOK_APP=/path/to/nombook python3 tools/make-brand-assets.py

Needs Pillow. Nothing at runtime needs it — the output is plain PNG.
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / "assets"

APP = Path(os.environ.get("NOMBOOK_APP", SITE.parent / "nombook"))
MARK_SRC = APP / "Nombook/Resources/Assets.xcassets/NombookMark.imageset/NombookMark.png"
FONT_SRC = APP / "Nombook/Resources/Fonts/Handlee-Regular.ttf"
FONT_LICENSE = APP / "Nombook/Resources/Fonts/Handlee-OFL.txt"

# The same three tokens the stylesheets use.
PAPER = (245, 238, 225)   # #F5EEE1
INK = (58, 52, 43)        # #3A342B
MUTED = (122, 113, 97)    # #7a7161


def ink_box(draw, text, font):
    """The box the glyphs actually mark, not the font's line box.

    Handlee's caps fill well under half its em, so centering on the nominal
    text size leaves the wordmark visibly high. Every placement below measures
    the drawn pixels instead.
    """
    return draw.textbbox((0, 0), text, font=font)


def lockup(canvas, mark, wordmark_size, center, gap_ratio=0.12):
    """Draw mark + "nombook" as one centered horizontal unit, app-style.

    In the app the pairing is a 76pt logo beside a 40pt wordmark, so the
    wordmark is sized from the mark's height at that same ratio by the caller.
    """
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT_SRC), wordmark_size)
    word = "nombook"
    l, t, r, b = ink_box(draw, word, font)
    word_w, word_h = r - l, b - t

    gap = int(mark.height * gap_ratio)
    total = mark.width + gap + word_w
    cx, cy = center
    x = cx - total // 2

    canvas.alpha_composite(mark, (x, cy - mark.height // 2))
    draw.text((x + mark.width + gap - l, cy - word_h // 2 - t), word, font=font, fill=INK)
    return b - t


def scaled_mark(height):
    mark = Image.open(MARK_SRC).convert("RGBA")
    w = round(mark.width * height / mark.height)
    return mark.resize((w, height), Image.LANCZOS)


def social_card(path, tagline):
    """The 1200x630 og:image — what a shared link unfurls into.

    1200x630 is the size iMessage, WhatsApp, Slack and X all crop cleanly to;
    anything squarer gets letterboxed by one of them.
    """
    card = Image.new("RGBA", (1200, 630), PAPER + (255,))
    mark = scaled_mark(230)

    # The lockup sits above centre to leave the tagline room under it.
    lockup(card, mark, round(230 * 40 / 76), (600, 275))

    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(str(FONT_SRC), 52)
    l, t, r, b = ink_box(draw, tagline, font)
    draw.text((600 - (r - l) // 2 - l, 440 - t), tagline, font=font, fill=MUTED)

    card.convert("RGB").save(path, optimize=True)


def square_icon(path, size, pad=0.14):
    """Opaque, edge-to-edge paper: iOS and Android both mask it themselves,
    and a transparent home-screen icon would come out black."""
    icon = Image.new("RGBA", (size, size), PAPER + (255,))
    mark = scaled_mark(round(size * (1 - 2 * pad)))
    icon.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    icon.convert("RGB").save(path, optimize=True)
    return icon


def main():
    missing = [p for p in (MARK_SRC, FONT_SRC) if not p.exists()]
    if missing:
        sys.exit(
            "Can't find the app's artwork:\n  "
            + "\n  ".join(str(p) for p in missing)
            + f"\nSet NOMBOOK_APP to the app checkout (currently {APP})."
        )

    OUT.mkdir(exist_ok=True)

    # The bare mark, transparent, for use on the pages themselves. It is
    # drawn no larger than ~110px there, so 320 covers a 3x screen and keeps
    # the file small — the art carries a paper grain that does not compress.
    scaled_mark(320).save(OUT / "nombook-mark.png", optimize=True)

    social_card(OUT / "og.png", "your own little cookbook")
    social_card(OUT / "og-recipe.png", "a recipe, shared with you")

    # Nombook is an iPhone app, so there is no web manifest and no Android
    # icon set — just Apple's home-screen size and the favicons.
    square_icon(OUT / "apple-touch-icon.png", 180)

    # Favicons are read at 16px, where the drawing's thin ink line disappears
    # if it is padded as well. Let it run closer to the edge.
    square_icon(OUT / "icon-32.png", 32, pad=0.06)
    square_icon(SITE / "favicon.ico", 48, pad=0.06).convert("RGB").save(
        SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)]
    )

    # Ship the font the wordmark is set in, with its licence beside it.
    (OUT / "handlee-regular.ttf").write_bytes(FONT_SRC.read_bytes())
    (OUT / "handlee-OFL.txt").write_bytes(FONT_LICENSE.read_bytes())

    for f in sorted(OUT.iterdir()):
        print(f"{f.relative_to(SITE)}  {f.stat().st_size:,} bytes")
    print(f"favicon.ico  {(SITE / 'favicon.ico').stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
