"""Render every card set from build/current.json into out/cards/."""
import base64, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from common import BUILD, OUT, ASSETS, slug
from design import solve_uniform, INK, FONTS
import cards as C
import svgtext

CARDS = os.path.join(OUT, "cards")
MODES = ("ondark", "onlight")
# Headshots are only 315px at source, so a 1024px player card upscales them
# for no detail and 4x the bytes. 640 sits close to native.
W01, W03, W04 = 1600, 2048, 640


def outdir(*parts):
    p = os.path.join(CARDS, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def svg_team_card(team, mode, manifest, name_size, tracking, W=W01):
    """Vector text + embedded logo bitmap. No font dependency on the far end."""
    H = int(W * 1.06)
    ink = "#FFFFFF" if mode == "ondark" else "#0E1116"
    art = C.team_logo_art(team, mode, manifest)
    from design import fit_logo
    art = fit_logo(art, int(W * 0.82), int(H * 0.60), C.LOGO_AREA_1600 * (W / 1600.0) ** 2)
    tmp = os.path.join(BUILD, "_tmp_logo.png")
    art.save(tmp)
    b64 = base64.b64encode(open(tmp, "rb").read()).decode()
    lx, ly = W / 2 - art.width / 2, H * 0.40 - art.height / 2

    name = team["name"].upper()
    items, adv = svgtext.text_paths(name, os.path.join(FONTS, "Oswald[wght].ttf"),
                                    name_size, wght=700, tracking=tracking)
    baseline = H * 0.80 + name_size * 0.74
    group = svgtext.paths_to_svg_group(items, ink, 0)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <image x="{lx:.1f}" y="{ly:.1f}" width="{art.width}" height="{art.height}"
         href="data:image/png;base64,{b64}"/>
  <g transform="translate({W/2 - adv/2:.2f},{baseline:.2f})">
    {group}
  </g>
</svg>
'''


def main():
    data = json.load(open(os.path.join(BUILD, "current.json")))
    manifest = json.load(open(os.path.join(BUILD, "logo_manifest.json")))["logos"]
    teams = data["teams"]
    if os.path.isdir(CARDS):
        shutil.rmtree(CARDS)

    # ---- one type size per set, solved across every member ----
    tn_font, tn_tr = solve_uniform([t["name"].upper() for t in teams], "display",
                                   W01 * 0.90, int(W01 * 0.115), tracking_ratio=0.05)
    rn_font, rn_tr = solve_uniform([t["name"].upper() for t in teams], "display",
                                   W03 * 0.85, int(W03 * 0.085), tracking_ratio=0.045)
    all_players = [p["name"] for t in teams for p in t["roster"] if p["status"] == "main"]
    pl_font, pl_tr = solve_uniform(all_players, "displaymed", W03 * 0.30, int(W03 * 0.042))
    everyone = [p["name"] for t in teams for p in t["roster"]]
    pc_font, pc_tr = solve_uniform(everyone, "display", W04 * 0.90, int(W04 * 0.145),
                                   tracking_ratio=0.03)
    print(f"uniform type: team-name {tn_font.size}px | roster-name {rn_font.size}px | "
          f"roster-player {pl_font.size}px | player-card {pc_font.size}px")

    counts = {}

    # ---- 01 team + name (PNG and SVG) ----
    for mode in MODES:
        for t in teams:
            d = outdir("01-team-name-cards", mode, t["region"])
            im = C.card_team_name(t, mode, manifest, W=W01, name_font=(tn_font, tn_tr))
            im.save(os.path.join(d, f"{slug(t['name'])}.png"), optimize=True)
            sd = outdir("01-team-name-cards", "svg", t["region"])
            with open(os.path.join(sd, f"{slug(t['name'])}__{mode}.svg"), "w") as f:
                f.write(svg_team_card(t, mode, manifest, tn_font.size, tn_tr))
            counts["01"] = counts.get("01", 0) + 1

    # ---- 02 bare logos ----
    for mode in MODES:
        for t in teams:
            d = outdir("02-logos-bare", mode, t["region"])
            C.card_bare_logo(t, mode, manifest).save(
                os.path.join(d, f"{slug(t['name'])}.png"), optimize=True)
            counts["02"] = counts.get("02", 0) + 1

    # ---- 03 roster cards (uniform height per mode) ----
    for mode in MODES:
        rendered = [(t, C.card_roster(t, mode, manifest, W=W03,
                                      name_font=(rn_font, rn_tr),
                                      player_font=(pl_font, pl_tr))) for t in teams]
        tallest = max(im.height for _, im in rendered)
        from design import pad_to_height
        for t, im in rendered:
            d = outdir("03-roster-cards", mode, t["region"])
            pad_to_height(im, tallest).save(
                os.path.join(d, f"{slug(t['name'])}.png"), optimize=True)
            counts["03"] = counts.get("03", 0) + 1

    # ---- 04 player cards ----
    for mode in MODES:
        for t in teams:
            for p in t["roster"]:
                d = outdir("04-players", mode, t["region"], slug(t["name"]))
                C.card_player(p, t, mode, W=W04, name_font=(pc_font, pc_tr)).save(
                    os.path.join(d, f"{slug(p['name'])}.png"), optimize=True)
                counts["04"] = counts.get("04", 0) + 1

    tmp = os.path.join(BUILD, "_tmp_logo.png")
    if os.path.exists(tmp):
        os.remove(tmp)
    total = sum(counts.values())
    for k in sorted(counts):
        print(f"  set {k}: {counts[k]} images")
    print(f"total {total} images (+{len(teams)*2} SVG) in {CARDS}")


if __name__ == "__main__":
    main()
