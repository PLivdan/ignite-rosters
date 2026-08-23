"""Parse Liquipedia rosters, reconcile with Weverboard art/metadata -> build/rosters.json."""
import json, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, BUILD, LP_PAGES

# Liquipedia team name -> Weverboard team key. Only the pairs that plain
# normalisation misses; everything else resolves by name/short/alias.
NAME_OVERRIDES = {
    "rad": "rad",
    "liquid citadel": "tlc",
    "equinox gaming": "exg",
    "natus vincere": "navi",
    "spacestation gaming": "ssg",
    "the chosen ones": "chosen_ones",
    "the lions": "the_lions",
    "team heretics": "heretics",
    "virtus.pro": "virtus_pro",
    "pulsar esports": "pulsar",
    "reason gaming": "reason",
    "100 thieves": "hundred_thieves",
    "nrg shock": "nrg_shock",
    "swamp gaming": "swamp",
    "yeah we lost": "ywl",
}

ROLE_CANON = {
    "dps": "DPS", "tank": "Tank", "sup": "Support", "flex": "Flex",
    "coach": "Coach", "head coach": "Head Coach",
    "assistant coach": "Assistant Coach", "analyst": "Analyst",
}
ROLE_ORDER = {"DPS": 0, "Tank": 1, "Support": 2, "Flex": 3,
              "Head Coach": 4, "Coach": 5, "Assistant Coach": 6, "Analyst": 7}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def parse_person(block):
    """{{Person|role=dps|Name|flag=xx|status=sub|type=staff}} -> dict."""
    inner = block[len("{{Person|"):-2]
    parts = [p.strip() for p in inner.split("|")]
    role, name, flag, status, ptype = "", "", "", "", ""
    for p in parts:
        if "=" in p:
            k, _, v = p.partition("=")
            k = k.strip().lower()
            if k == "role":
                role = v.strip()
            elif k == "flag":
                flag = v.strip()
            elif k == "status":
                status = v.strip()
            elif k == "type":
                ptype = v.strip()
        elif p and not name:
            name = p
    if not name:
        return None
    role_c = ROLE_CANON.get(role.strip().lower(), role.strip().title())
    # status=former marks someone who has LEFT. Treating it as active put a
    # departed starter (Alter Esports' TeamCaptain) and a departed analyst
    # (SSG's sensha) on the cards as current members.
    former = status.lower() == "former"
    if ptype.lower() == "staff":
        status_c = "staff"
    elif status.lower() == "sub":
        status_c = "sub"
    else:
        status_c = "main"
    return {"name": name, "role": role_c, "flag": flag.lower(),
            "status": status_c, "former": former, "source": "liquipedia"}


def parse_region(region):
    text = open(os.path.join(RAW, f"liquipedia_{region}.wiki")).read()
    # Slice each team block from its {{Opponent| marker to the NEXT one. Splitting
    # on |qualification silently merged Stickdrift into Equinox, so anchor on the
    # only delimiter that is guaranteed present.
    marks = [m.start() for m in re.finditer(r"\{\{Opponent\|", text)]
    teams = []
    for i, start in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else len(text)
        block = text[start:end]
        head = block[len("{{Opponent|"):].split("\n", 1)[0].strip()
        if not head or "|players=" not in block:
            continue
        roster, seen = [], set()
        for pm in re.finditer(r"\{\{Person\|[^}]*\}\}", block):
            person = parse_person(pm.group(0))
            if not person:
                continue
            key = (person["name"].lower(), person["role"])
            if key in seen:
                continue
            seen.add(key)
            roster.append(person)
        if roster:
            teams.append({"region": region, "lp_name": head, "roster": roster})
    return teams


def main():
    os.makedirs(BUILD, exist_ok=True)
    wev = json.load(open(os.path.join(RAW, "weverboard_directory.json")))

    by_key = {t["key"]: t for t in wev["teams"]}
    lookup = {}
    for t in wev["teams"]:
        for cand in [t["name"], t.get("short") or "", t["key"]] + (t.get("aliases") or []):
            if cand:
                lookup.setdefault(norm(cand), t["key"])

    icons = {norm(p["name"]): p.get("icon") for p in wev["players"] + wev["staff"]}

    out, unmatched = [], []
    for region in LP_PAGES:
        for team in parse_region(region):
            n = norm(team["lp_name"])
            key = NAME_OVERRIDES.get(team["lp_name"].lower()) or lookup.get(n)
            w = by_key.get(key, {})
            if not w:
                unmatched.append(f"{region}:{team['lp_name']}")
            for p in team["roster"]:
                p["icon"] = icons.get(norm(p["name"]), "")
            team["roster"].sort(key=lambda p: (
                {"main": 0, "sub": 1, "staff": 2}[p["status"]],
                ROLE_ORDER.get(p["role"], 9), p["name"].lower()))
            out.append({
                "region": region,
                "name": w.get("name") or team["lp_name"],
                "lp_name": team["lp_name"],
                "short": w.get("short") or "",
                "wev_key": key or "",
                "logo_url": w.get("logo") or "",
                "socials": w.get("links") or {},
                "roster": team["roster"],
            })

    out.sort(key=lambda t: (t["region"], t["name"].lower()))
    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "sources": {
            "liquipedia": {r: t for r, t in LP_PAGES.items()},
            "weverboard": "https://api.arianwever.com/directory.php",
        },
        "teams": out,
        "weverboard_only_teams": [
            {"name": t["name"], "short": t.get("short"), "region": t.get("region"),
             "key": t["key"], "logo_url": t.get("logo") or "",
             "roster": [{"name": p["name"], "icon": p.get("icon", ""),
                         "role": "", "status": "main", "source": "weverboard"}
                        for p in (t.get("players") or [])]}
            for t in wev["teams"]
            if t["key"] not in {o["wev_key"] for o in out}
        ],
    }
    with open(os.path.join(BUILD, "rosters.json"), "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    for region in LP_PAGES:
        ts = [t for t in out if t["region"] == region]
        print(f"{region}: {len(ts)} teams")
        for t in ts:
            c = {s: sum(1 for p in t["roster"] if p["status"] == s)
                 for s in ("main", "sub", "staff")}
            flag = "" if c["main"] == 6 else f"  <-- {c['main']} mains"
            print(f"   {t['name']:<24} {t['short']:<6} "
                  f"main={c['main']} sub={c['sub']} staff={c['staff']}{flag}")
    print(f"\nother regions (art only): {len(payload['weverboard_only_teams'])} teams")
    missing_icon = sum(1 for t in out for p in t["roster"] if not p["icon"])
    total = sum(len(t["roster"]) for t in out)
    print(f"people: {total}, without headshot: {missing_icon}")
    if unmatched:
        print("UNMATCHED to Weverboard:", unmatched)


if __name__ == "__main__":
    main()
