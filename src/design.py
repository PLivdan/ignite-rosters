"""Design tokens + drawing primitives for the Ignite card set.

Everything renders onto a transparent canvas, so there is no surface to carry
contrast. Each card is therefore emitted twice: `ondark` (light ink) and
`onlight` (dark ink). Backgrounds, panels and shadows are deliberately absent —
they would halo against whatever the card is dropped onto.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONTS = os.path.join(ASSETS, "fonts")

INK = {
    "ondark":  {"primary": (255, 255, 255), "secondary": (174, 182, 194),
                "muted": (122, 132, 148), "rule": (255, 255, 255, 46)},
    "onlight": {"primary": (14, 17, 22), "secondary": (90, 100, 114),
                "muted": (140, 149, 162), "rule": (14, 17, 22, 40)},
}

# Marvel Rivals' own role vocabulary; DPS/Tank/Support is Overwatch's.
ROLE_LABEL = {"DPS": "Duelist", "Tank": "Vanguard", "Support": "Strategist",
              "Flex": "Flex"}
ROLE_COLOR = {"DPS": (226, 82, 58), "Tank": (74, 144, 217),
              "Support": (63, 185, 132), "Flex": (155, 123, 212)}
LEAK_COLOR = (240, 169, 59)

_font_cache = {}


def font(kind, size):
    """kind: display | displaymed | body | bodysemi | bodybold"""
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    files = {
        "display":    ("Oswald[wght].ttf", 700),
        "displaymed": ("Oswald[wght].ttf", 500),
        "body":       ("BarlowCondensed-Medium.ttf", None),
        "bodysemi":   ("BarlowCondensed-SemiBold.ttf", None),
        "bodybold":   ("BarlowCondensed-Bold.ttf", None),
    }
    name, wght = files[kind]
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass  # static build or no variable-font support; regular weight is fine
    _font_cache[key] = f
    return f


def trim(im):
    """Crop to the alpha bounding box."""
    im = im.convert("RGBA")
    bbox = im.split()[-1].getbbox()
    return im.crop(bbox) if bbox else im


def ink_area(im):
    """Alpha-weighted visible area — the perceptual 'size' of a logo."""
    a = im.convert("RGBA").split()[-1]
    return sum(a.getdata()) / 255.0


def fit_logo(im, box_w, box_h, target_area=None):
    """Scale a logo to equal *optical* weight, not equal height.

    Fitting each logo to a bounding box makes wide marks (RAD is 4945x1496)
    read as tiny next to square ones (Sentinels 1000x1000). Matching
    alpha-weighted area instead makes a row of mixed logos look like a set.
    The box is still a hard clamp so nothing overflows its slot.
    """
    im = trim(im)
    w, h = im.size
    scale = min(box_w / w, box_h / h)
    if target_area:
        area = ink_area(im)
        if area > 0:
            scale = min(scale, (target_area / area) ** 0.5)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    return im.resize((nw, nh), Image.LANCZOS)


def tint(im, rgb):
    """Recolor a monochrome glyph by reusing its alpha as a mask."""
    im = im.convert("RGBA")
    solid = Image.new("RGBA", im.size, rgb + (255,))
    solid.putalpha(im.split()[-1])
    return solid


def text_size(draw, s, f, tracking=0):
    if not s:
        return (0, 0)
    box = draw.textbbox((0, 0), s, font=f)
    w = box[2] - box[0] + tracking * max(0, len(s) - 1)
    return (w, box[3] - box[1])


def draw_tracked(draw, xy, s, f, fill, tracking=0, anchor_center=False):
    """Letter-spaced text. PIL has no tracking, so glyphs are placed manually."""
    if not s:
        return 0
    x, y = xy
    if tracking == 0:
        if anchor_center:
            w = draw.textbbox((0, 0), s, font=f)[2] - draw.textbbox((0, 0), s, font=f)[0]
            x -= w / 2
        draw.text((x, y), s, font=f, fill=fill)
        return draw.textbbox((0, 0), s, font=f)[2]
    total = text_size(draw, s, f, tracking)[0]
    if anchor_center:
        x -= total / 2
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill)
        adv = draw.textbbox((0, 0), ch, font=f)[2] - draw.textbbox((0, 0), ch, font=f)[0]
        if ch == " ":
            adv = f.size * 0.26
        x += adv + tracking
    return total


def fit_text(draw, s, kind, max_w, start, min_size=10, tracking_ratio=0.0):
    """Largest font size at which `s` fits `max_w`."""
    size = start
    while size > min_size:
        f = font(kind, size)
        if text_size(draw, s, f, tracking_ratio * size)[0] <= max_w:
            return f, tracking_ratio * size
        size -= max(1, size // 28)
    f = font(kind, min_size)
    return f, tracking_ratio * min_size


def canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def paste_center(base, im, cx, cy):
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def role_icon(role, rgb, size):
    p = os.path.join(ASSETS, "roles", ROLE_LABEL.get(role, "") + ".png")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    s = size / im.height
    im = im.resize((max(1, round(im.width * s)), size), Image.LANCZOS)
    return tint(im, rgb)


def solve_uniform(strings, kind, max_w, start, min_size=10, tracking_ratio=0.0):
    """One type size that fits EVERY string in a set.

    Per-card autofit sizes each name independently, so "SENTINELS" renders huge
    next to a shrunken "TEAM LIQUID CITADEL". Dragged side by side that reads as
    sloppy, so the whole set is solved to the largest size the longest member
    can carry, and everything uses it.
    """
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    size = start
    while size > min_size:
        f = font(kind, size)
        tr = tracking_ratio * size
        if all(text_size(d, s, f, tr)[0] <= max_w for s in strings if s):
            return f, tr
        size -= 1
    return font(kind, min_size), tracking_ratio * min_size


def trim_vertical(im, pad_top, pad_bottom):
    """Drop dead vertical space but keep the canvas width (and so the x-alignment)."""
    bbox = im.convert("RGBA").split()[-1].getbbox()
    if not bbox:
        return im
    top = max(0, bbox[1] - pad_top)
    bot = min(im.height, bbox[3] + pad_bottom)
    return im.crop((0, top, im.width, bot))


def pad_to_height(im, height):
    """Top-align content on a fixed-height canvas so headers line up across a set."""
    if im.height >= height:
        return im
    out = Image.new("RGBA", (im.width, height), (0, 0, 0, 0))
    out.alpha_composite(im, (0, 0))
    return out
