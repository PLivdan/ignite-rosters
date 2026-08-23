"""Emit the static tier-list board: docs/data.json, web-sized logos, fonts."""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from common import BUILD, ASSETS, ROOT, slug
from design import trim
import cards as C

# GitHub Pages only serves a branch from / or /docs, so the published
# board lives in docs/ rather than site/.
SITE = os.path.join(ROOT, "docs")
LOGO_PX = 320


def main():
    data = json.load(open(os.path.join(BUILD, "current.json")))
    manifest = json.load(open(os.path.join(BUILD, "logo_manifest.json")))["logos"]
    logos = os.path.join(SITE, "logos")
    os.makedirs(logos, exist_ok=True)

    teams = []
    for t in data["teams"]:
        art = trim(C.team_logo_art(t, "ondark", manifest, size=LOGO_PX))
        s = LOGO_PX / max(art.size)
        if s < 1:
            art = art.resize((max(1, round(art.width * s)),
                              max(1, round(art.height * s))), Image.LANCZOS)
        fn = slug(t["name"]) + ".png"
        art.save(os.path.join(logos, fn), optimize=True)

        teams.append({
            "id": slug(t["name"]),
            "name": t["name"],
            "short": t["short"],
            "region": t["region"],
            "logo": "logos/" + fn,
            "roster": [{"name": p["name"], "role": p["role"], "status": p["status"],
                        "origin": p["origin"], "since": p.get("since", "")}
                       for p in t["roster"]],
            "needs": t["needs"],
            "contested": t["contested"],
        })

    fonts = os.path.join(SITE, "fonts")
    os.makedirs(fonts, exist_ok=True)
    for f in ("Oswald[wght].ttf", "BarlowCondensed-Medium.ttf",
              "BarlowCondensed-SemiBold.ttf", "BarlowCondensed-Bold.ttf"):
        shutil.copy(os.path.join(ASSETS, "fonts", f), os.path.join(fonts, f))

    roles = os.path.join(SITE, "roles")
    os.makedirs(roles, exist_ok=True)
    for r in ("Duelist", "Vanguard", "Strategist"):
        shutil.copy(os.path.join(ASSETS, "roles", r + ".png"),
                    os.path.join(roles, r + ".png"))

    payload = {
        "event": data["event"],
        "generated": data["generated"],
        "basis": data["basis"],
        "teams": teams,
        "changes": sorted(data["transfer_effects"], reverse=True)[:60],
    }
    with open(os.path.join(SITE, "data.json"), "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(os.path.join(SITE, "data.json")) / 1024
    print(f"docs/data.json  {len(teams)} teams, {kb:.0f} KB")
    print(f"docs/logos/     {len(os.listdir(logos))} files")


if __name__ == "__main__":
    main()
