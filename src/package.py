"""Bundle the cards, the workbook and a short guide into out/ignite-cards.zip."""
import json, os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BUILD, OUT

GUIDE = """MARVEL RIVALS IGNITE 2026 — STAGE 2
Team cards for EU + NA
===================================================================

WHAT IS IN HERE

  01-team-name-cards/   logo with the team name underneath
  02-logos-bare/        the logo on its own, no text
  03-roster-cards/      logo, name, and the full team sheet
  04-players/           one card per player, headshot and name

  Every set comes in two versions. Pick by what you are dropping
  them ONTO, not by what they look like in a file browser:

      ondark/   white text  -> use on dark backgrounds
      onlight/  black text  -> use on light backgrounds

  All PNGs have a transparent background and the text is baked
  into the image, so nothing needs to be typed on top.

  01-team-name-cards/svg/ has the same cards as SVG. The text is
  real vector outlines, so it stays sharp at any size in Figma and
  does not need the font installed.


THE SPREADSHEET

  ignite-rosters.xlsx is where the names come from.

  Rosters sheet          every player, role and status
  Teams sheet            who is short of a full roster
  Power ranking sheet    blank, for ranking the 24 teams
  Roster changes sheet   every signing and departure since 1 July
  Leaks sheet            reported moves and whether they landed

  Pink rows are slots nobody has confirmed yet. Type a name in,
  re-run the build, and the cards redraw with it.


READ THIS BEFORE TRUSTING THE NAMES

  Liquipedia has published the Stage 2 TEAM LIST but not the
  Stage 2 ROSTERS. The names here are the Stage 1 rosters with
  every 2026 Q3 transfer applied on top. That is the best picture
  available today, not an official roster.

  13 of the 24 teams are missing at least one starter. Those gaps
  are real, not an error in the data.


KNOWN GAPS

  No logo exists on any source for four teams, so their cards use
  a lettered monogram instead:
      The Chosen Ones, Disband, SON MIJO IBN, JollyJesters

  CrownFall and Vengeful each show three Supports. The source
  spells a departure differently from the arrival, so the extra
  player cannot be resolved automatically. Delete the wrong one
  in the spreadsheet.


SOURCES

  Rosters, roles, staff   Liquipedia, MR Ignite 2026 Stage 1 and 2
  Roster corrections      Liquipedia, Player Transfers 2026 Q3
  Logos                   Liquipedia, full resolution
  Player headshots        Weverboard (arianwever.com)
  Leaks                   x.com/AkamaruRivals
"""


def main():
    cards = os.path.join(OUT, "cards")
    if not os.path.isdir(cards):
        raise SystemExit("no cards to package — run build_cards.py first")
    guide = os.path.join(OUT, "READ ME FIRST.txt")
    open(guide, "w").write(GUIDE)

    zpath = os.path.join(OUT, "ignite-cards.zip")
    n = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(guide, "READ ME FIRST.txt")
        xl = os.path.join(OUT, "ignite-rosters.xlsx")
        if os.path.exists(xl):
            z.write(xl, "ignite-rosters.xlsx")
        for root, _, files in os.walk(cards):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, OUT))
                n += 1
    mb = os.path.getsize(zpath) / 1e6
    print(f"wrote {zpath}  ({n} images, {mb:.1f} MB)")


if __name__ == "__main__":
    main()
