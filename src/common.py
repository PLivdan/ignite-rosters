"""Shared config + HTTP helpers for the Ignite roster pipeline."""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
BUILD = os.path.join(ROOT, "build")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "out")

# Liquipedia's API terms require a descriptive UA and rate limiting (>=2s between
# parse/query calls). Scraping faster gets the IP banned, so every call goes
# through lp_api() which sleeps.
# Liquipedia's API terms require a descriptive UA with a contact address.
# Kept out of the source so a public repo does not publish an email: set
# LIQUIPEDIA_CONTACT in your environment before running the fetch scripts.
_contact = os.environ.get("LIQUIPEDIA_CONTACT", "set LIQUIPEDIA_CONTACT env var")
LP_UA = f"IgniteRosterTool/1.0 ({_contact}) python-urllib"
WEV_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

LP_PAGES = {
    "EU": "MR Ignite/2026/Stage 1/EMEA",
    "NA": "MR Ignite/2026/Stage 1/Americas",
}

_last_lp_call = [0.0]


def _get(url, ua, timeout=45, referer=None):
    # Referer must be per-host: sending the Weverboard referer to Liquipedia
    # trips its hotlink protection and returns 403 on every image.
    headers = {"User-Agent": ua, "Accept-Encoding": "gzip"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            data = gzip.decompress(data)
        return data


def lp_api(**params):
    """Rate-limited Liquipedia API call (JSON)."""
    wait = 2.0 - (time.time() - _last_lp_call[0])
    if wait > 0:
        time.sleep(wait)
    params.setdefault("format", "json")
    url = "https://liquipedia.net/marvelrivals/api.php?" + urllib.parse.urlencode(params)
    raw = _get(url, LP_UA)
    _last_lp_call[0] = time.time()
    return json.loads(raw)


def lp_file(url):
    """Fetch a Liquipedia-hosted image; same rate limit applies."""
    wait = 2.0 - (time.time() - _last_lp_call[0])
    if wait > 0:
        time.sleep(wait)
    raw = _get(url, LP_UA, referer="https://liquipedia.net/marvelrivals/")
    _last_lp_call[0] = time.time()
    return raw


def wev_get(path):
    return _get("https://api.arianwever.com/" + path, WEV_UA,
                referer="https://arianwever.com/teams")


def slug(s):
    """Filesystem-safe name that still reads like the original."""
    keep = "".join(c if (c.isalnum() or c in " -_.") else "_" for c in str(s))
    return " ".join(keep.split()).strip().replace(" ", "_") or "unnamed"
