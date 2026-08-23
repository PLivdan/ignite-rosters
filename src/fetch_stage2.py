"""Pull the Stage 2 pages and the running transfer list into raw/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, lp_api

PAGES = {
    "stage2_EU": "MR Ignite/2026/Stage 2/EMEA",
    "stage2_NA": "MR Ignite/2026/Stage 2/Americas",
    "transfers_2026Q3": "Player Transfers/2026/3rd Quarter",
}


def main():
    os.makedirs(RAW, exist_ok=True)
    for stem, title in PAGES.items():
        d = lp_api(action="query", prop="revisions", rvprop="content|timestamp",
                   rvslots="main", titles=title)
        pg = list(d["query"]["pages"].values())[0]
        if "revisions" not in pg:
            raise SystemExit(f"missing page: {title}")
        rev = pg["revisions"][0]
        open(os.path.join(RAW, stem + ".wiki"), "w").write(rev["slots"]["main"]["*"])
        print(f"  {title:<42} edited {rev['timestamp'][:10]}  "
              f"{len(rev['slots']['main']['*']):>6} chars")


if __name__ == "__main__":
    main()
