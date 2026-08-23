"""One command to rebuild everything.

  python3 src/build_all.py                  refresh from Liquipedia + Weverboard
  python3 src/build_all.py --from-workbook   rebuild cards from your xlsx edits
  python3 src/build_all.py --no-fetch        rebuild from cached raw/ data
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(mod, label):
    print(f"\n=== {label} ===")
    r = subprocess.run([sys.executable, os.path.join(HERE, mod)])
    if r.returncode:
        raise SystemExit(f"{mod} failed")


def main():
    args = set(sys.argv[1:])
    from_workbook = "--from-workbook" in args
    fetch = not from_workbook and "--no-fetch" not in args

    if fetch:
        run("fetch_sources.py", "fetch sources")
        run("fetch_stage2.py", "fetch stage 2 + transfers")
    if from_workbook:
        run("read_workbook.py", "read your workbook edits")
    else:
        run("build_current.py", "resolve current rosters")
        if fetch:
            run("fetch_logos.py", "fetch logos")
            run("fetch_headshots.py", "fetch headshots")
        run("build_workbook.py", "write workbook")
    run("build_cards.py", "render cards")
    run("package.py", "package zip")
    print("\ndone.")


if __name__ == "__main__":
    main()
