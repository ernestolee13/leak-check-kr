#!/usr/bin/env python3
"""Check that every self-check page and firm intake URL in data/*.json still answers.

Rule: "could not see it" is never written down as "dead". A timeout is a different event from a page that
was taken down, and conflating them is how a watcher goes quiet for a week.

| verdict | meaning |
|---|---|
| ok      | 2xx, or a redirect that stays on the same site (e.g. to its login page) |
| dead    | 4xx (other than 403/429), or a redirect to a different site |
| unknown | timeout, DNS failure, TLS error, 5xx, or a bot wall (403/429 from a CDN) |

Firm sites behind Cloudflare answer 403 to scripts while working fine in a
browser, so 403 and 429 are "unknown", not "dead". Those rows need a browser
check by a person.

    check_links.py          table of every URL
    check_links.py --json   machine output
    check_links.py --source URL_BASE   read data from a published copy instead of the repo
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "leak-check-kr-linkcheck/1.0 (+https://github.com/ernestolee13/leak-check-kr)"
TIMEOUT = 15


def load(source: str | None, name: str) -> dict:
    if source:
        with urllib.request.urlopen(f"{source.rstrip('/')}/data/{name}", timeout=TIMEOUT) as r:
            return json.load(r)
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def targets(cases: dict, firms: dict) -> list[dict]:
    out = []
    for c in cases["cases"]:
        sc = c.get("self_check") or {}
        if sc.get("url") and sc.get("status") in ("open", "login", "none"):
            out.append({"kind": "self_check", "case": c["id"], "label": c["company"], "url": sc["url"]})
    for b in firms["cases"]:
        for r in b["firms"]:
            if r.get("url") and r["status"] != "closed":
                out.append({"kind": "firm", "case": b["case"], "label": r["firm"], "url": r["url"]})
    return out


def site(host: str | None) -> str:
    """Registrable domain, roughly: auth.myrealtrip.com and member.myrealtrip.com are one site.
    Korean second-level zones (co.kr, or.kr, go.kr ...) keep three labels."""
    parts = (host or "").lower().split(".")
    keep = 3 if len(parts) >= 3 and parts[-1] == "kr" and parts[-2] in {"co", "or", "go", "ne", "ac", "re", "pe"} else 2
    return ".".join(parts[-keep:])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def probe(t: dict) -> dict:
    url = t["url"]
    host = urllib.parse.urlparse(url).hostname
    opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    for _ in range(5):  # follow redirects by hand so we can see where they go
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        try:
            with opener.open(req, timeout=TIMEOUT) as r:
                return {**t, "verdict": "ok", "code": r.status, "final": url}
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                nxt = urllib.parse.urljoin(url, e.headers.get("Location", ""))
                if site(urllib.parse.urlparse(nxt).hostname) != site(host):
                    return {**t, "verdict": "dead", "code": e.code, "final": nxt, "why": "redirected off-host"}
                url = nxt
                continue
            if e.code in (403, 429):
                return {**t, "verdict": "unknown", "code": e.code, "final": url, "why": "bot wall, check in a browser"}
            if e.code >= 500:
                return {**t, "verdict": "unknown", "code": e.code, "final": url, "why": "server error, may be transient"}
            return {**t, "verdict": "dead", "code": e.code, "final": url}
        except Exception as e:  # timeout, DNS, TLS
            return {**t, "verdict": "unknown", "code": None, "final": url, "why": type(e).__name__}
    return {**t, "verdict": "unknown", "code": None, "final": url, "why": "too many redirects"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--source", help="base URL that serves data/*.json, e.g. https://raw.githubusercontent.com/ernestolee13/leak-check-kr/main")
    a = ap.parse_args()
    ts = targets(load(a.source, "cases.json"), load(a.source, "firms.json"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(probe, ts))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for r in res:
            print(f"{r['verdict']:8} {str(r['code'] or '-'):4} {r['kind']:10} {r['case']:12} {r['label']}  {r['url']}  {r.get('why', '')}")
    dead = [r for r in res if r["verdict"] == "dead"]
    print(f"{len(res)} urls: {len(res) - len(dead) - sum(r['verdict'] == 'unknown' for r in res)} ok, "
          f"{sum(r['verdict'] == 'unknown' for r in res)} unknown, {len(dead)} dead", file=sys.stderr)
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
