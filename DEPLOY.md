# Publishing the board to GitHub Pages

Only the `site/` folder needs to be published. Everything else is the build
pipeline and does not have to be public.

## Option A — publish just the board (simplest)

```bash
cd site
git init -b main
git add .
git commit -m "Ignite 2026 Stage 2 power ranking board"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Then on GitHub: **Settings → Pages → Source: Deploy from a branch → `main` / `root`**.

Live a minute later at `https://<you>.github.io/<repo>/`.

## Option B — publish the whole project, serve `site/`

Push the repo as-is, then set **Settings → Pages → Source: `main` / `/site`**.
Keeps the pipeline and the board versioned together.

## Updating it later

```bash
python3 src/build_all.py --no-fetch   # or --from-workbook after editing the xlsx
cd site && git add . && git commit -m "roster update" && git push
```

## Notes

- No build step, no dependencies, no backend. Plain HTML, CSS and JS.
- Fonts are bundled in `site/fonts/` (Oswald and Barlow Condensed, SIL Open Font
  License), so nothing loads from a CDN and it works offline.
- Ranking state lives in each viewer's browser. Publishing the page does not
  publish your ranking — use **Export** to save or share one.
