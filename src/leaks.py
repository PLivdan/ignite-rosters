"""Resolve reported-but-unconfirmed roster claims against the current rosters."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BUILD, ROOT


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def load(path=None):
    p = path or os.path.join(ROOT, "data", "leaks.json")
    if not os.path.exists(p):
        return {"posts": []}
    return json.load(open(p))


def resolve(rosters, leaks):
    """For each claimed player, report which team (if any) they are on today."""
    where = {}
    for t in rosters["teams"]:
        for p in t["roster"]:
            where.setdefault(norm(p["name"]), []).append(
                {"team": t["name"], "region": t["region"],
                 "role": p["role"], "status": p["status"]})

    field = {norm(t["name"]) for t in rosters["teams"]}
    rows = []
    for post in leaks.get("posts", []):
        if post["kind"] != "roster":
            rows.append({**post, "verdict": "-", "detail": "no roster claim"})
            continue
        if norm(post.get("team", "")) not in field:
            rows.append({**post, "verdict": "team not in field",
                         "landed": 0, "claimed": len(post["players"]),
                         "detail": f"{post['team']} is not in the Stage 2 field, "
                                   f"so this leak no longer applies"})
            continue
        details, landed = [], 0
        for name in post["players"]:
            found = where.get(norm(name), [])
            if not found:
                details.append(f"{name}: not on any Ignite roster")
                continue
            f = found[0]
            on_claimed = norm(f["team"]) == norm(post["team"])
            if on_claimed:
                landed += 1
                details.append(f"{name}: on {f['team']} ({f['status']} {f['role']})")
            else:
                details.append(f"{name}: on {f['team']} instead")
        n = len(post["players"])
        verdict = ("landed" if landed == n else
                   "partial" if landed else "not reflected")
        rows.append({**post, "verdict": verdict, "landed": landed, "claimed": n,
                     "detail": "; ".join(details)})
    return rows


def main():
    # current.json is the live field; rosters.json is the abandoned Stage 1 build
    # and resolving against it reported players on teams no longer competing.
    rosters = json.load(open(os.path.join(BUILD, "current.json")))
    rows = resolve(rosters, load())
    with open(os.path.join(BUILD, "leaks_resolved.json"), "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    for r in rows:
        if r["kind"] != "roster":
            continue
        print(f"  {r['date']}  {r['team']:<22} {r['verdict']:<15} "
              f"({r.get('landed')}/{r.get('claimed')})")
        print(f"      {r['detail']}")


if __name__ == "__main__":
    main()
