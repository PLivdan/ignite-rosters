"""Download player/staff headshots from Weverboard into assets/headshots/."""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BUILD, ASSETS, _get, WEV_UA, slug

HS = os.path.join(ASSETS, "headshots")


def main():
    os.makedirs(HS, exist_ok=True)
    data = json.load(open(os.path.join(BUILD, "current.json")))
    people = {}
    for team in data["teams"]:
        for p in team["roster"]:
            if p.get("icon"):
                people.setdefault(p["name"], p["icon"])

    got, failed, cached = 0, [], 0
    for name, icon in sorted(people.items()):
        # Some icons are relative paths under Graphics/, others are already
        # absolute (api.arianwever.com twitch-avatar endpoints). Prefixing the
        # domain onto an absolute URL 404s, so branch on it.
        if icon.startswith("http"):
            url, ext = icon, ".png"
        else:
            url = "https://arianwever.com/" + urllib.parse.quote(icon)
            ext = os.path.splitext(icon)[1] or ".jpg"
        dest = os.path.join(HS, slug(name) + ext)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            cached += 1
            continue
        try:
            open(dest, "wb").write(_get(url, WEV_UA, referer="https://arianwever.com/players"))
            got += 1
        except Exception as e:
            failed.append((name, str(e)[:40]))
            if os.path.exists(dest):
                os.remove(dest)

    total_people = sum(len(t["roster"]) for t in data["teams"])
    print(f"headshots: {got} downloaded, {cached} cached, {len(failed)} failed")
    print(f"coverage: {len(people)}/{total_people} people have an icon on Weverboard")
    if failed:
        print("failed:", failed[:10])


if __name__ == "__main__":
    main()
