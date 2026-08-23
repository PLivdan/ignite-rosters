"""Render sample cards onto light+dark backdrops so the output can be eyeballed."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from common import BUILD, ROOT
import cards

data = json.load(open(os.path.join(BUILD, "rosters.json")))
man = json.load(open(os.path.join(BUILD, "logo_manifest.json")))["logos"]
teams = {t["name"]: t for t in data["teams"]}

BG = {"ondark": (17, 19, 24), "onlight": (244, 245, 247)}


def sheet(images, bg, pad=40, cols=None):
    cols = cols or len(images)
    rows = (len(images) + cols - 1) // cols
    cw = max(i.width for i in images)
    ch = max(i.height for i in images)
    out = Image.new("RGBA", (cols * cw + pad * (cols + 1),
                             rows * ch + pad * (rows + 1)), bg + (255,))
    for n, im in enumerate(images):
        r, c = divmod(n, cols)
        out.alpha_composite(im, (pad + c * (cw + pad) + (cw - im.width) // 2,
                                 pad + r * (ch + pad) + (ch - im.height) // 2))
    return out


picks = ["RAD Esports", "Sentinels", "NRG Shock", "The Chosen Ones",
         "Team Liquid Citadel", "Pulsar Esports"]
for mode in ("ondark", "onlight"):
    ims = [cards.card_team_name(teams[n], mode, man, W=700) for n in picks]
    sheet(ims, BG[mode], cols=6).convert("RGB").save(
        f"{ROOT}/build/preview_01_{mode}.png", quality=92)

    r = cards.card_roster(teams["RAD Esports"], mode, man, W=1100)
    r2 = cards.card_roster(teams["Spacestation Gaming"], mode, man, W=1100)
    sheet([r, r2], BG[mode], cols=2).convert("RGB").save(
        f"{ROOT}/build/preview_03_{mode}.png", quality=92)

t = teams["Sentinels"]
ims = []
for mode in ("ondark",):
    for p in t["roster"][:4] + [q for q in teams["RAD Esports"]["roster"] if q["status"] == "staff"][:1]:
        ims.append(cards.card_player(p, t, mode, W=480))
sheet(ims, BG["ondark"], cols=5).convert("RGB").save(f"{ROOT}/build/preview_04_ondark.png")
print("previews written")
