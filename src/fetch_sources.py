"""Pull the two upstream sources into raw/ so every later step is offline+repeatable."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, LP_PAGES, lp_api, wev_get

os.makedirs(RAW, exist_ok=True)


def fetch_liquipedia():
    for region, title in LP_PAGES.items():
        d = lp_api(action="query", prop="revisions", rvprop="content",
                   rvslots="main", titles=title)
        page = list(d["query"]["pages"].values())[0]
        if "revisions" not in page:
            raise SystemExit(f"Liquipedia page missing: {title}")
        text = page["revisions"][0]["slots"]["main"]["*"]
        path = os.path.join(RAW, f"liquipedia_{region}.wiki")
        with open(path, "w") as f:
            f.write(text)
        print(f"  {region:3} {title:38} {len(text):>7} chars -> {os.path.basename(path)}")


def fetch_weverboard():
    raw = wev_get("directory.php")
    d = json.loads(raw)
    if not d.get("ok"):
        raise SystemExit("Weverboard directory.php returned not-ok")
    path = os.path.join(RAW, "weverboard_directory.json")
    with open(path, "wb") as f:
        f.write(raw)
    print(f"  teams={len(d['teams'])} players={len(d['players'])} "
          f"staff={len(d['staff'])} -> {os.path.basename(path)}")


if __name__ == "__main__":
    print("Liquipedia (rosters, roles, subs, staff):")
    fetch_liquipedia()
    print("Weverboard (logos, headshots, socials, aliases):")
    fetch_weverboard()
    print("done.")
