"""The four card sets. Every renderer returns a transparent RGBA image."""
import os
from PIL import Image, ImageDraw
from design import (INK, ROLE_LABEL, ROLE_COLOR, LEAK_COLOR, ASSETS, font, trim,
                    fit_logo, tint, canvas, paste_center, draw_tracked, fit_text,
                    text_size, role_icon, solve_uniform, trim_vertical, pad_to_height)

LOGO_DIR = os.path.join(ASSETS, "logos")
HEAD_DIR = os.path.join(ASSETS, "headshots")

# Optical-area target, in square pixels of visible ink, at 1600px canvas scale.
LOGO_AREA_1600 = 430_000


def load_logo(team, mode, manifest):
    """mode: ondark|onlight. Falls back to the 'both' (allmode) file."""
    entry = manifest.get(team["name"]) or {}
    want = "dark" if mode == "ondark" else "light"
    for k in (want, "both"):
        if k in entry:
            p = os.path.join(LOGO_DIR, entry[k]["file"])
            if os.path.exists(p):
                return Image.open(p).convert("RGBA")
    return None


def monogram(team, mode, size=1200):
    """Stand-in mark for a team with no logo anywhere upstream (The Chosen Ones).

    Styled to sit in the set rather than read as a broken asset.
    """
    ink = INK[mode]
    im = canvas(size, size)
    d = ImageDraw.Draw(im)
    pad, stroke = size * 0.06, max(3, size // 190)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size * 0.07,
                        outline=ink["primary"] + (170,), width=stroke)
    tag = (team.get("short") or team["name"][:3]).upper()
    f, tr = fit_text(d, tag, "display", size * 0.62, int(size * 0.40),
                     tracking_ratio=0.04)
    w, _ = text_size(d, tag, f, tr)
    box = d.textbbox((0, 0), tag, font=f)
    draw_tracked(d, (size / 2 - w / 2, size / 2 - (box[3] + box[1]) / 2), tag, f,
                 ink["primary"], tr)
    return im


def team_logo_art(team, mode, manifest, size=1200):
    return load_logo(team, mode, manifest) or monogram(team, mode, size)


# ---------------------------------------------------------------- set 01
def card_team_name(team, mode, manifest, W=1600, name_font=None):
    """Logo above the team name. The tier-list workhorse.

    `name_font` is the (font, tracking) solved across the whole set so every
    card's name renders at the same size.
    """
    ink = INK[mode]
    H = int(W * 1.06)
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    scale = (W / 1600.0) ** 2

    art = team_logo_art(team, mode, manifest)
    art = fit_logo(art, int(W * 0.82), int(H * 0.60), LOGO_AREA_1600 * scale)
    paste_center(im, art, W / 2, H * 0.40)

    name = team["name"].upper()
    f, tr = name_font or fit_text(d, name, "display", W * 0.90, int(W * 0.115),
                                  tracking_ratio=0.05)
    box = d.textbbox((0, 0), name, font=f)
    draw_tracked(d, (W / 2, H * 0.80 - box[1]), name, f, ink["primary"], tr,
                 anchor_center=True)
    return im


# ---------------------------------------------------------------- set 02
def card_bare_logo(team, mode, manifest, longest=2048):
    art = trim(team_logo_art(team, mode, manifest, size=longest))
    s = longest / max(art.size)
    if s < 1:
        art = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    return art


# ---------------------------------------------------------------- set 03
def _name_color(person, ink):
    return LEAK_COLOR if person.get("status_flag") == "leaked" else ink["primary"]


def card_roster(team, mode, manifest, W=2048, include_subs=True, include_staff=True,
                name_font=None, player_font=None, fixed_height=None):
    """Full team sheet, built on the 2-2-2 role spine the game is actually played on."""
    ink = INK[mode]
    H = int(W * 1.34)  # generous; trimmed to content at the end
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    M = W * 0.075

    art = team_logo_art(team, mode, manifest)
    art = fit_logo(art, int(W * 0.62), int(H * 0.20), 300_000 * (W / 2048.0) ** 2)
    paste_center(im, art, W / 2, H * 0.125)

    y = H * 0.245
    name = team["name"].upper()
    f, tr = name_font or fit_text(d, name, "display", W - 2 * M, int(W * 0.085),
                                  tracking_ratio=0.045)
    box = d.textbbox((0, 0), name, font=f)
    draw_tracked(d, (W / 2, y - box[1]), name, f, ink["primary"], tr, anchor_center=True)
    y += box[3] - box[1] + W * 0.022

    sub = f"{'EMEA' if team['region'] == 'EU' else 'AMERICAS'}     IGNITE 2026 STAGE 2"
    fs = font("bodysemi", int(W * 0.025))
    draw_tracked(d, (W / 2, y), sub, fs, ink["muted"], W * 0.0045, anchor_center=True)
    y += W * 0.055

    mains = [p for p in team["roster"] if p["status"] == "main"]
    groups = [(r, [p for p in mains if p["role"] == r]) for r in ("DPS", "Tank", "Support")]
    leftover = [p for p in mains if p["role"] not in ("DPS", "Tank", "Support")]
    if leftover:
        groups.append(("Flex", leftover))

    row_h = W * 0.108
    label_x = M + W * 0.075
    col_x = (M + W * 0.30, M + W * 0.63)
    for role, people in groups:
        if not people:
            continue
        d.line([(M, y), (W - M, y)], fill=ink["rule"], width=max(1, int(W * 0.0011)))
        cy = y + row_h / 2
        rc = ROLE_COLOR.get(role, ink["secondary"])
        icon = role_icon(role, rc, int(W * 0.036))
        if icon:
            paste_center(im, icon, M + W * 0.030, cy)
        fl = font("bodybold", int(W * 0.0245))
        lb = ROLE_LABEL.get(role, role).upper()
        bb = d.textbbox((0, 0), lb, font=fl)
        draw_tracked(d, (label_x, cy - (bb[3] + bb[1]) / 2), lb, fl, rc, W * 0.0035)
        for i, p in enumerate(people[:2]):
            fn, tn = player_font or fit_text(d, p["name"], "displaymed",
                                             W * 0.30, int(W * 0.042))
            nb = d.textbbox((0, 0), p["name"], font=fn)
            draw_tracked(d, (col_x[i], cy - (nb[3] + nb[1]) / 2), p["name"], fn,
                         _name_color(p, ink), tn)
        y += row_h
    d.line([(M, y), (W - M, y)], fill=ink["rule"], width=max(1, int(W * 0.0011)))
    y += W * 0.035

    def block(title, people, fmt):
        nonlocal y
        if not people:
            return
        ft = font("bodybold", int(W * 0.0225))
        draw_tracked(d, (M, y), title, ft, ink["muted"], W * 0.004)
        fv = font("body", int(W * 0.030))
        x, ly = M + W * 0.175, y - W * 0.004
        for p in people:
            s = fmt(p)
            wpx = d.textbbox((0, 0), s, font=fv)[2]
            if x + wpx > W - M:
                x, ly = M + W * 0.175, ly + W * 0.042
            d.text((x, ly), s, font=fv, fill=_name_color(p, ink)
                   if p.get("status_flag") == "leaked" else ink["secondary"])
            x += wpx + W * 0.030
        y = ly + W * 0.062

    if include_subs:
        block("SUBS", [p for p in team["roster"] if p["status"] == "sub"],
              lambda p: p["name"])
    if include_staff:
        block("STAFF", [p for p in team["roster"] if p["status"] == "staff"],
              lambda p: f"{p['name']} ({p['role']})")

    im = trim_vertical(im, int(W * 0.055), int(W * 0.055))
    if fixed_height:
        im = pad_to_height(im, fixed_height)
    return im


# ---------------------------------------------------------------- set 04
def card_player(person, team, mode, W=1024, name_font=None):
    """Headshot, name, role. Ring colour carries the role."""
    ink = INK[mode]
    H = int(W * 1.36)
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    rc = ROLE_COLOR.get(person["role"], ink["secondary"])
    dia = int(W * 0.74)
    cx, cy = W / 2, H * 0.38

    src = None
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        p = os.path.join(HEAD_DIR, _slug(person["name"]) + ext)
        if os.path.exists(p):
            src = p
            break

    ring = max(4, int(W * 0.012))
    if src:
        ph = Image.open(src).convert("RGBA")
        s = dia / min(ph.size)
        ph = ph.resize((round(ph.width * s), round(ph.height * s)), Image.LANCZOS)
        ph = ph.crop(((ph.width - dia) // 2, (ph.height - dia) // 2,
                      (ph.width - dia) // 2 + dia, (ph.height - dia) // 2 + dia))
        mask = Image.new("L", (dia * 4, dia * 4), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, dia * 4, dia * 4], fill=255)
        ph.putalpha(mask.resize((dia, dia), Image.LANCZOS))
        im.alpha_composite(ph, (int(cx - dia / 2), int(cy - dia / 2)))
    else:
        # No headshot upstream: initials in the role colour, same silhouette.
        ini = "".join(c for c in person["name"] if c.isalnum())[:2].upper()
        fi, _ = fit_text(d, ini, "display", dia * 0.55, int(dia * 0.42))
        b = d.textbbox((0, 0), ini, font=fi)
        d.text((cx - (b[2] + b[0]) / 2, cy - (b[3] + b[1]) / 2), ini, font=fi,
               fill=ink["secondary"])
    d.ellipse([cx - dia / 2, cy - dia / 2, cx + dia / 2, cy + dia / 2],
              outline=rc + (255,), width=ring)

    y = H * 0.80
    nm = person["name"]
    f, tr = name_font or fit_text(d, nm, "display", W * 0.90, int(W * 0.145),
                                  tracking_ratio=0.03)
    b = d.textbbox((0, 0), nm, font=f)
    draw_tracked(d, (cx, y - b[1]), nm, f, _name_color(person, ink), tr,
                 anchor_center=True)
    y = H * 0.80 + f.size * 1.02  # fixed, so the meta line never drifts

    meta = ROLE_LABEL.get(person["role"], person["role"]).upper()
    if person["status"] == "sub":
        meta += "   SUB"
    if person["status"] == "staff":
        meta = person["role"].upper()
    meta += f"     {(team.get('short') or team['name']).upper()}"
    fm = font("bodybold", int(W * 0.040))
    draw_tracked(d, (cx, y), meta, fm, ink["muted"], W * 0.006, anchor_center=True)
    return im


def _slug(s):
    keep = "".join(c if (c.isalnum() or c in " -_.") else "_" for c in str(s))
    return " ".join(keep.split()).strip().replace(" ", "_") or "unnamed"
