# Ignite 2026 Stage 2 — roster board & card set

Editable rosters for the EU + NA teams in Marvel Rivals Ignite 2026 Stage 2,
plus a transparent-background card set built from them.

Built for ranking teams on camera before the stage starts, when rosters are
still moving.

## Use it

```bash
python3 src/build_all.py                   # refresh from Liquipedia + Weverboard
python3 src/build_all.py --from-workbook    # rebuild cards from your xlsx edits
python3 src/build_all.py --no-fetch         # rebuild from cached raw/
```

Outputs land in `out/`:

| File | What it is |
|---|---|
| `ignite-rosters.xlsx` | the editable source of truth |
| `cards/` | four card sets, each in `ondark/` and `onlight/` |
| `ignite-cards.zip` | everything above, ready to send |

The loop that matters: **edit a name in the workbook → `--from-workbook` →
cards redraw.** Writing the workbook and reading it back is lossless.

## Where the names come from

Liquipedia has published the Stage 2 *team list* but not the Stage 2 *rosters* —
the player slots are still empty templates. So rosters are assembled:

```
team list        Stage 2 (EMEA + Americas)          who is competing
roster baseline  Stage 1                            last published rosters
corrections      Player Transfers 2026 Q3           applied in date order
overlay          x.com/AkamaruRivals                marked LEAKED, never merged silently
```

Tournament pages are edited per-event and lag reality; the transfer list is
maintained continuously. Where they disagree, the transfer list wins. Every
person carries an `origin`, so an unconfirmed slot is visible rather than implied.

Roughly half the field is short at least one starter. That is the real state of
the field, not a gap in the data.

Teams can be dropped from the field entirely via `exclude_teams` in
`data/overrides.json`.

## The live board (`docs/`)

A drag-to-rank tier list with editable rosters, built to run on stream. Static
files only, so it deploys to GitHub Pages as-is.

```bash
python3 src/build_site.py          # regenerate docs/data.json from current rosters
cd docs && python3 -m http.server  # preview at localhost:8000
```

- Three separate rankings: **EMEA**, **Americas** and **Global**. Rank the regions
  first, then hit **Seed from EU + NA** in Global to start from them interleaved
  rather than an empty list.
- Drag a team from the pool into the list to place it, and drag rows to reorder.
  Positions renumber as you go.
- **Order by player rating** sorts the list by each roster's average, which gives
  a data-backed starting order to argue with rather than a blank page.
- Click a team to open its roster; click any name to change it.
- A name typed into an empty slot is marked **leaked** automatically, so
  anything picked up mid-stream is visually distinct from a confirmed roster.
- Rate players S to F; each team shows the placement its roster implies. When a
  team sits at #7 but its players average A, that gap is the thing worth talking
  about on camera.
- The six dots on each team are its 2-2-2 spine: solid confirmed, hollow open,
  amber leaked. You can see which teams nobody has locked in while you rank them.
- Every change is timestamped in the change log, with the old name struck through.
- State autosaves to localStorage and survives a refresh. Export/Import moves a
  session between machines.

## Corrections the wiki does not have yet

Liquipedia lags real roster moves, and you will often know first. Add a row to
`data/overrides.json` and re-run — overrides are applied last, so they always win:

```json
{"date":"2026-08-23","player":"Melio","from":"FlyQuest","to":"","source":"who told you"}
```

Leave `to` empty for a departure or retirement. To move someone between teams,
set both `from` and `to`.

## Layout

```
src/
  common.py          HTTP + rate limiting (Liquipedia requires >=2s between calls)
  fetch_sources.py   Stage 1 pages + Weverboard directory
  fetch_stage2.py    Stage 2 pages + transfer list
  parse_rosters.py   wikitext -> rosters
  transfers.py       Player Transfers parser
  build_current.py   baseline + transfers + overrides + leaks -> current.json
  build_site.py      emits docs/data.json, web logos, fonts
  build_workbook.py  current.json -> xlsx
  read_workbook.py   xlsx -> current.json   (the round trip)
  design.py          type scale, colour, logo normalisation
  cards.py           the four renderers
  svgtext.py         glyphs -> SVG paths, so exports carry no font dependency
  build_cards.py     renders every set
  package.py         zips it
docs/              the live tier-list board (published by GitHub Pages) (index.html, app.js, style.css)
data/leaks.json    paste new AkamaruRivals posts here
data/overrides.json corrections Liquipedia has not recorded yet
```

## Design notes

**Logos are normalised by optical area, not bounding box.** Source logos range
from 4945x1496 to 298x305. Fitting each to a box makes wide marks read as tiny
next to square ones; matching alpha-weighted area makes a row of mixed logos
look like a set.

**Type is solved once per set, not per card.** Autofitting each name
independently renders "SENTINELS" huge beside a shrunken "TEAM LIQUID CITADEL".
Every set is solved to the largest size its longest member can carry.

**Two ink variants, no backgrounds.** A transparent card has no surface to carry
contrast, and 8 of these logos are pure white. Panels and shadows would halo
against an unknown backdrop, so each card ships as `ondark` and `onlight`
instead, using Liquipedia's own lightmode/darkmode logo files where they exist.

**Roster cards are built on the 2-2-2 spine** — two Duelists, two Vanguards, two
Strategists — using the game's own role icons. That is the structure the sport
is actually played on, and the thing a power ranking turns on.

## Known gaps

- No logo exists on any source for **The Chosen Ones** and **JollyJesters**.
  Their cards use a lettered monogram.
- **CrownFall** and **Vengeful** each resolve to three Supports: the source
  spells a departure differently from the arrival (`Sleepai` vs `Shleepai`).
  Flagged as contested rather than guessed.
- 43 of 164 people have no headshot upstream; those cards fall back to initials.
