# Publishing the board

The board is live at **https://plivdan.github.io/ignite-rosters/**

GitHub Pages serves the `docs/` folder of `main`. Pages can only publish a
branch from `/` or `/docs`, which is why the board lives in `docs/` rather than
`site/`.

## Updating it

```bash
python3 src/build_all.py --no-fetch     # after editing data/overrides.json
python3 src/build_all.py --from-workbook # after editing the xlsx
git add -A && git commit -m "roster update" && git push
```

Pages redeploys within about a minute of the push.

## Notes

- No build step, no dependencies, no backend. Plain HTML, CSS and JS.
- Fonts are bundled in `docs/fonts/` (Oswald and Barlow Condensed, SIL Open Font
  License), so nothing loads from a CDN and the board works offline.
- Ranking state lives in each viewer's own browser. Publishing the page does not
  publish your ranking, and two people opening the link do not see each other's
  tiers. Use **Export** to save or hand off a session.
- `out/` is gitignored: the card zip is over 100MB and GitHub rejects files that
  large. Rebuild it locally with `python3 src/build_all.py --no-fetch`.
