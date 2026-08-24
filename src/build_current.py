"""Best-available CURRENT rosters for the teams actually playing Ignite Stage 2.

Stage 2 is the event being ranked, but Liquipedia has only published its team
list — the player slots are still empty templates. So:

  team list        Stage 2 (who is competing)
  roster baseline  Stage 1 (last published rosters)
  corrections      Player Transfers 2026 Q3, applied in date order
  overlay          reported-but-unconfirmed leaks

Every person carries where they came from, so an unconfirmed slot is visible
rather than implied.
"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, BUILD, LP_PAGES
import transfers as tx
import leaks as leaks_mod
from parse_rosters import parse_region, norm, NAME_OVERRIDES, ROLE_ORDER

STAGE2 = {"EU": "raw/stage2_EU.wiki", "NA": "raw/stage2_NA.wiki"}

# Short tags for orgs Weverboard does not track (new to Stage 2).
EXTRA_SHORT = {"Vengeful": "VNG", "Disband": "DSB", "SON MIJO IBN": "SMI",
               "Dreamland": "DL", "JollyJesters": "JJ", "The Chosen Ones": "TCO"}

# Canonical display names for orgs that appear under several spellings.
CANON = {
    "rad": "RAD Esports", "liquidcitadel": "Team Liquid Citadel",
    "teamliquidcitadel": "Team Liquid Citadel", "navi": "Natus Vincere",
    "natusvincere": "Natus Vincere", "equinoxgaming": "ExG", "exg": "ExG",
    "stickdrift": "StickDrift", "spacestationgaming": "Spacestation Gaming",
    "sonmijoibn": "SON MIJO IBN", "jollyjesters": "JollyJesters",
}


def canon(name):
    return CANON.get(norm(name), name)


def stage2_teams():
    out = []
    for region, path in STAGE2.items():
        c = open(os.path.join(os.path.dirname(RAW), path)).read()
        marks = [m.start() for m in re.finditer(r"\{\{Opponent\|", c)]
        for i, s in enumerate(marks):
            b = c[s:(marks[i + 1] if i + 1 < len(marks) else len(c))]
            nm = b[len("{{Opponent|"):].split("\n", 1)[0].strip()
            if nm and "|players=" in b:
                out.append({"region": region, "name": canon(nm), "lp_name": nm})
    return out


def main():
    ov_path = os.path.join(os.path.dirname(RAW), "data", "overrides.json")
    overrides = json.load(open(ov_path)) if os.path.exists(ov_path) else {}
    dropped = {norm(canon(x)) for x in overrides.get("exclude_teams", [])}

    teams = [t for t in stage2_teams() if norm(canon(t["name"])) not in dropped]
    index = {norm(t["name"]): t["name"] for t in teams}
    for t in teams:
        index.setdefault(norm(t["lp_name"]), t["name"])
    # transfer-list spellings that differ from the Stage 2 page
    for k, v in (("rad", "RAD Esports"), ("liquidcitadel", "Team Liquid Citadel"),
                 ("stickdrift", "StickDrift")):
        index.setdefault(k, v)

    state = {t["name"]: {} for t in teams}
    # An alias must never resolve to a team that was excluded from the field,
    # or every later state[...] lookup for it raises KeyError.
    index = {k: v for k, v in index.items() if v in state}

    # ---- baseline: Stage 1 rosters, minus anyone already marked former ----
    kept, dropped_former = 0, []
    for region in LP_PAGES:
        for team in parse_region(region):
            name = index.get(norm(canon(team["lp_name"])))
            if not name:
                continue
            for p in team["roster"]:
                if p.get("former"):
                    dropped_former.append((name, p["name"]))
                    continue
                state[name][p["name"]] = {
                    "name": p["name"], "role": p["role"], "status": p["status"],
                    "origin": "stage1", "since": "", "ref": "",
                }
                kept += 1

    # ---- corrections: apply every Q3 move in date order ----
    moves = tx.parse()
    applied = []
    for m in moves:
        prev_role = ""
        src = index.get(norm(canon(m["from_team"]))) if m["from_team"] else None
        if src and m["name"] in state[src]:
            prev_role = state[src][m["name"]]["role"]
            del state[src][m["name"]]
            applied.append((m["date"], m["name"], f"left {src}"))
        kind = tx.classify(m)
        dst = index.get(norm(canon(m["to_team"]))) if m["to_team"] else None
        if kind in ("main", "sub", "staff") and dst:
            role = tx.role_of(m) or prev_role
            state[dst][m["name"]] = {
                "name": m["name"], "role": role, "status": kind,
                "origin": "transfer", "since": m["date"], "ref": m.get("ref", ""),
            }
            applied.append((m["date"], m["name"], f"joined {dst} as {role or kind}"))

    # ---- local corrections: things known before Liquipedia records them ----
    for mv in overrides.get("moves", []):
        who = mv["player"]
        src = index.get(norm(canon(mv.get("from", "")))) if mv.get("from") else None
        prev_role = ""
        if src and who in state[src]:
            prev_role = state[src][who]["role"]
            del state[src][who]
            applied.append((mv["date"], who, f"left {src} (override)"))
        dst = index.get(norm(canon(mv.get("to", "")))) if mv.get("to") else None
        if dst:
            state[dst][who] = {
                "name": who, "role": mv.get("role") or prev_role,
                "status": mv.get("status") or "main", "origin": "override",
                "since": mv["date"], "ref": mv.get("source", ""),
                # an expected-but-unconfirmed move renders amber, like a leak
                "status_flag": "" if mv.get("confirmed", True) else "leaked",
            }
            applied.append((mv["date"], who, f"joined {dst} (override)"))

    # role changes: same team, different role (e.g. a starter moving to fill)
    for rc in overrides.get("role_changes", []):
        tgt = index.get(norm(canon(rc.get("team", ""))))
        if not tgt or rc["player"] not in state[tgt]:
            continue
        rec = state[tgt][rc["player"]]
        was = rec["role"]
        rec["role"] = rc["role"]
        rec["origin"] = "override"
        rec["since"] = rc["date"]
        rec["ref"] = rc.get("source", "")
        if not rc.get("confirmed", True):
            rec["status_flag"] = "leaked"
        applied.append((rc["date"], rc["player"], f"{was} to {rc['role']} on {tgt} (override)"))

    # ---- overlay: reported-but-unconfirmed ----
    leak_rows = []
    lk = leaks_mod.load()
    for post in lk.get("posts", []):
        if post["kind"] != "roster":
            continue
        dst = index.get(norm(canon(post.get("team", ""))))
        if not dst:
            continue
        for nm in post["players"]:
            if nm in state[dst]:
                continue
            leak_rows.append((dst, nm, post["date"]))

    # Weverboard supplies short tags, headshots and socials.
    wev = json.load(open(os.path.join(RAW, "weverboard_directory.json")))
    wshort, wlinks = {}, {}
    for w in wev["teams"]:
        for cand in [w["name"], w.get("short") or ""] + (w.get("aliases") or []):
            if cand:
                wshort.setdefault(norm(canon(cand)), w.get("short") or "")
                wlinks.setdefault(norm(canon(cand)), w.get("links") or {})
    icons = {norm(p["name"]): p.get("icon", "")
             for p in wev["players"] + wev["staff"]}

    out = []
    for t in teams:
        roster = list(state[t["name"]].values())
        for p in roster:
            p["icon"] = icons.get(norm(p["name"]), "")
        roster.sort(key=lambda p: ({"main": 0, "sub": 1, "staff": 2}.get(p["status"], 3),
                                   ROLE_ORDER.get(p["role"], 9), p["name"].lower()))
        mains = [p for p in roster if p["status"] == "main"]
        by_role = {}
        for p in mains:
            by_role[p["role"]] = by_role.get(p["role"], 0) + 1
        contested = [f"{n}x {r}" for r, n in by_role.items() if n > 2]
        k = norm(t["name"])
        out.append({**t, "roster": roster,
                    "short": EXTRA_SHORT.get(t["name"]) or wshort.get(k, "") or t["name"][:3].upper(),
                    "socials": wlinks.get(k, {}),
                    "mains": len(mains),
                    "complete": len(mains) == 6 and not contested,
                    "contested": contested,
                    "needs": max(0, 6 - len(mains))})

    payload = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "event": "Marvel Rivals Ignite 2026 — Stage 2",
        "basis": {
            "team_list": "Liquipedia MR Ignite/2026/Stage 2 (EMEA, Americas)",
            "roster_baseline": "Liquipedia MR Ignite/2026/Stage 1",
            "corrections": "Liquipedia Player Transfers/2026/3rd Quarter",
            "leaks": "x.com/AkamaruRivals (pasted by hand)",
        },
        "teams": out,
        "dropped_former": dropped_former,
        "transfer_effects": applied,
    }
    with open(os.path.join(BUILD, "current.json"), "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    if dropped:
        print(f"excluded by data/overrides.json: {overrides.get('exclude_teams')}")
    print(f"Stage 2 field: {len(out)} teams "
          f"({sum(1 for t in out if t['region']=='EU')} EU / "
          f"{sum(1 for t in out if t['region']=='NA')} NA)")
    print(f"baseline kept {kept}, dropped {len(dropped_former)} marked former: {dropped_former}")
    print(f"transfer effects applied: {len(applied)}\n")
    for region in ("EU", "NA"):
        print(f"--- {region} ---")
        for t in [x for x in out if x["region"] == region]:
            c = {s: sum(1 for p in t["roster"] if p["status"] == s)
                 for s in ("main", "sub", "staff")}
            mark = "OK " if t["complete"] else "GAP"
            print(f"  {mark} {t['name']:<24} starters={c['main']} "
                  f"subs={c['sub']} staff={c['staff']}")


if __name__ == "__main__":
    main()
