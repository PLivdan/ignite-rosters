"""Convert strings to SVG path data so exported SVGs carry no font dependency."""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.varLib.instancer import instantiateVariableFont

_cache = {}


def _load(path, wght=None):
    key = (path, wght)
    if key in _cache:
        return _cache[key]
    f = TTFont(path)
    if wght and "fvar" in f:
        f = instantiateVariableFont(f, {"wght": wght}, updateFontNames=False)
    _cache[key] = f
    return f


def text_paths(s, font_path, size, wght=None, tracking=0.0):
    """-> (list of SVG path 'd' strings with x offsets applied, total advance)."""
    f = _load(font_path, wght)
    upem = f["head"].unitsPerEm
    scale = size / upem
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    out, x = [], 0.0
    for ch in s:
        gname = cmap.get(ord(ch))
        if gname is None:
            x += size * 0.3 + tracking
            continue
        pen = SVGPathPen(gs)
        gs[gname].draw(pen)
        d = pen.getCommands()
        if d:
            # font space is Y-up; SVG is Y-down
            out.append((d, x, scale))
        x += hmtx[gname][0] * scale + tracking
    return out, x - (tracking if s else 0)


def paths_to_svg_group(items, fill, baseline_y):
    g = []
    for d, x, scale in items:
        g.append(f'<path d="{d}" fill="{fill}" '
                 f'transform="translate({x:.2f},{baseline_y:.2f}) '
                 f'scale({scale:.5f},{-scale:.5f})"/>')
    return "\n    ".join(g)
