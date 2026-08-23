"""Parse Liquipedia's Player Transfers list.

Tournament pages are edited per-event and lag reality; the transfer list is
maintained continuously. Convention, verified against sensha's player page:
team1 = the team being left, team2 = the team being joined.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW

# Roles that sit on a team sheet. Manager / Content Creator / Owner do not.
STAFF_ROLES = {"coach", "head coach", "assistant coach", "analyst",
               "assistant analyst", "performance coach"}
SUB_ROLES = {"substitute", "sub"}
POS_CANON = {"dps": "DPS", "tank": "Tank", "sup": "Support", "support": "Support",
             "flex": "Flex"}


def _split_params(row):
    """Split on | that are not inside a nested {{...}} (the ref template)."""
    parts, depth, cur = [], 0, ""
    i = 0
    while i < len(row):
        if row.startswith("{{", i):
            depth += 1
            cur += "{{"
            i += 2
            continue
        if row.startswith("}}", i):
            depth -= 1
            cur += "}}"
            i += 2
            continue
        if row[i] == "|" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += row[i]
        i += 1
    parts.append(cur)
    return parts


def parse(path=None):
    p = path or os.path.join(RAW, "transfers_2026Q3.wiki")
    c = open(p).read()
    moves = []
    for m in re.finditer(r"\{\{Transfer Row\|(.*?)\}\}\s*\n", c, re.S):
        body = m.group(1)
        d = {}
        for part in _split_params(body):
            if "=" in part:
                k, _, v = part.partition("=")
                d[k.strip()] = v.strip()
        date = d.get("date", "")
        t1, t2 = d.get("team1", "").strip(), d.get("team2", "").strip()
        r1, r2 = d.get("role1", "").strip(), d.get("role2", "").strip()
        # Up to five people share one row; each carries its own pos.
        for i in range(1, 6):
            nk = "name" if i == 1 else f"name{i}"
            pk = "pos" if i == 1 else f"pos{i}"
            name = d.get(nk, "").strip()
            if not name:
                continue
            moves.append({
                "date": date, "name": name,
                "pos": POS_CANON.get(d.get(pk, "").strip().lower(), ""),
                "from_team": t1, "to_team": t2,
                "from_role": r1, "to_role": r2,
                "ref": (re.search(r"url=([^}|]+)", d.get("ref", "")) or [None, ""])[1]
                       if "url=" in d.get("ref", "") else "",
            })
    moves.sort(key=lambda m: m["date"])
    return moves


def classify(move):
    """What the destination slot is: main | sub | staff | gone | ignore."""
    role = (move["to_role"] or "").strip().lower()
    if not move["to_team"]:
        return "gone"
    if role in SUB_ROLES:
        return "sub"
    if role in STAFF_ROLES:
        return "staff"
    if role in {"retired", "inactive"}:
        return "gone"
    if role and role not in SUB_ROLES and role not in STAFF_ROLES:
        return "ignore"      # manager, content creator, owner, streamer
    return "main"


def role_of(move):
    if move["to_role"] and move["to_role"].strip().lower() in STAFF_ROLES:
        return move["to_role"].strip().title()
    return move["pos"] or ""


if __name__ == "__main__":
    ms = parse()
    print(f"{len(ms)} person-moves parsed, {ms[0]['date']} .. {ms[-1]['date']}")
    import collections
    print("destination kinds:", collections.Counter(classify(m) for m in ms))
