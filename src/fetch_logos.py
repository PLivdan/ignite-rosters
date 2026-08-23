"""Download full-res team logos from Liquipedia, in light-bg and dark-bg variants.

Liquipedia convention: "lightmode" = dark ink, for light backgrounds.
"darkmode" = light ink, for dark backgrounds. "allmode" = safe on both.
Weverboard's copies are thumbnails (some as small as 62px), so Liquipedia
originals are preferred and Weverboard is only the fallback.
"""
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BUILD, ASSETS, lp_api, lp_file, _get, WEV_UA

# Liquipedia file stem per team. Value is the stem shared by the mode variants,
# or an explicit single file when only "allmode" exists.
LOGO_FILES = {
    # EU — Stage 2 field
    "Natus Vincere": "Natus Vincere 2021",
    "Virtus.pro": "Virtus.pro 2019 allmode",
    "RAD Esports": "RAD May 2026 allmode",
    "Team Heretics": "Team Heretics 2024 allmode",
    "Shikigami": "Shikigami allmode",
    "Pulsar Esports": "Pulsar Esports 2025 oct allmode",
    "CrownFall": "Crownfall",
    "Vengeful": "Vengeful allmode",
    "FYR Strays": "FYR Strays allmode",
    # NA — Stage 2 field
    "Team Liquid Citadel": "Team Liquid Citadel",
    "Swamp Gaming": "Swamp Gaming",
    "100 Thieves": "100 Thieves",
    "Yeah We Lost": "Yeah We Lost",
    "FlyQuest": "FlyQuest 2021 allmode",
    "StickDrift": "Stickdrift allmode",
    "Sentinels": "Sentinels 2020 allmode",
    "TSM": "TSM 2019",
    "Spacestation Gaming": "Spacestation Gaming 2021 allmode",
    "NRG Shock": "NRG Shock",
    "Dreamland": "Dreamland allmode",
    # No logo on Liquipedia or Weverboard -> monogram:
    #   The Chosen Ones, Disband, SON MIJO IBN, JollyJesters
}

LOGO_DIR = os.path.join(ASSETS, "logos")


def image_urls(titles):
    """Resolve File: titles to original download URLs."""
    out = {}
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        d = lp_api(action="query", prop="imageinfo", iiprop="url|size",
                   titles="|".join("File:" + t for t in chunk))
        for pg in d["query"]["pages"].values():
            if "imageinfo" in pg:
                ii = pg["imageinfo"][0]
                out[pg["title"][len("File:"):]] = (ii["url"], ii["width"], ii["height"])
    return out


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    data = json.load(open(os.path.join(BUILD, "current.json")))

    wanted = {}
    for team in data["teams"]:
        stem = LOGO_FILES.get(team["name"])
        if not stem:
            continue
        if stem.endswith("allmode"):
            wanted[team["name"]] = {"both": stem + ".png"}
        else:
            wanted[team["name"]] = {"light": f"{stem} lightmode.png",
                                    "dark": f"{stem} darkmode.png"}

    titles = sorted({f for v in wanted.values() for f in v.values()})
    urls = image_urls([t[:-4] + ".png" for t in titles])
    urls = {k + ".png" if not k.endswith(".png") else k: v for k, v in urls.items()}

    manifest = {}
    for team_name, variants in sorted(wanted.items()):
        entry = {}
        for mode, fname in variants.items():
            info = urls.get(fname)
            if not info:
                print(f"  !! no imageinfo for {fname}")
                continue
            url, w, h = info
            dest = os.path.join(LOGO_DIR, f"{team_name.replace('/', '-')}__{mode}.png")
            # A failed fetch can leave a 0-byte file behind; presence alone is not
            # proof of a usable image, so validate before trusting the cache.
            ok = os.path.exists(dest) and os.path.getsize(dest) > 0
            if ok:
                try:
                    Image.open(dest).verify()
                except Exception:
                    ok = False
            if not ok:
                open(dest, "wb").write(lp_file(url))
            entry[mode] = {"file": os.path.basename(dest), "w": w, "h": h}
            print(f"  {team_name:<24} {mode:<6} {w}x{h}")
        manifest[team_name] = entry

    missing = [t["name"] for t in data["teams"] if not manifest.get(t["name"])]
    with open(os.path.join(BUILD, "logo_manifest.json"), "w") as f:
        json.dump({"logos": manifest, "missing": missing}, f, indent=2, ensure_ascii=False)
    print(f"\n{len(manifest)}/{len(data['teams'])} teams have logos")
    if missing:
        print("NO LOGO (monogram will be generated):", missing)


if __name__ == "__main__":
    main()
