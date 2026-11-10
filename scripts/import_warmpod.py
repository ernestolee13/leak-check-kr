#!/usr/bin/env python3
"""Merge warmpod's approved personal-data breach events into data/cases.json.

warmpod collects breach news and a person approves each event there. This
script takes that export and:

- skips events already linked (a case with the same `warmpod_id`),
- links an event to an existing case when the company name matches and the
  dates are within 3 months (sets `warmpod_id` on that case),
- otherwise adds a new case marked `review: "pending"` with self_check
  `unknown` ("확인 방법 미정"). How to check, the notice wording, the audience
  and the case id are filled in by a person afterwards (MAINTAINING.md).

It never writes anything about a law firm. For each new case it only adds a
firms.json `no_recruitment_found` entry saying recruitment is not checked yet.
Dry run by default; `--write` saves. Run validate_data.py and render_docs.py
after writing, then review the diff before pushing.

    import_warmpod.py EXPORT                       dry run (path or https URL)
    import_warmpod.py EXPORT --write               link known cases; queue new ones
    import_warmpod.py EXPORT --write --add ID ...  also add these new incidents
    import_warmpod.py EXPORT --write --link WPID=CASE ...  link by hand (a
        sanction story months after the breach falls outside the date window)

New incidents are not published by default. warmpod also tracks sanctions for
marketing consent, employee data and foreign incidents, which are not cases a
person can check themselves, and dozens of thin pending pages would eat the
site's crawl budget. They go to review/warmpod_queue.json (git-ignored) and a
person picks which ones to add with --add.

Export format: GET https://warmpod.vibestash.app/api/leak-incidents (or the
repo file data/export/leak-incidents.json). A list of incidents, or an object
holding one under "incidents". Fields used: id, companies[{id,name}],
startedAt, publishedAt, headline, url (lead article), sanction{url}|null,
officialUrls[]. The first company name becomes the case company.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "cases.json"
FIRMS = ROOT / "data" / "firms.json"
QUEUE = ROOT / "review" / "warmpod_queue.json"
TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|ref$|referral|aff|partner)", re.I)
CORP = re.compile(r"\(.*?\)|㈜|\(주\)|주식회사|유한회사|\s+")
DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def load_export(src: str) -> dict:
    if src.startswith("https://"):
        with urllib.request.urlopen(src, timeout=20) as r:
            return json.load(r)
    return json.loads(Path(src).read_text(encoding="utf-8"))


# warmpod company names that differ from ours (the operating company vs the service).
ALIASES = {"할리스에프앤비": "할리스", "지마켓": "g마켓", "cjenm": "티빙", "놀유니버스": "인터파크"}


def norm(name: str) -> str:
    n = CORP.sub("", name or "").lower()
    return ALIASES.get(n, n)


def months(d: str) -> int:
    y, m = d[:7].split("-")
    return int(y) * 12 + int(m)


def clean_url(u: str) -> str | None:
    if not u or not u.startswith("https://"):
        return None
    p = urlparse(u)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not TRACKING.match(k)]
    return urlunparse(p._replace(query=urlencode(q), fragment=""))


def new_id(event_id: str, taken: set[str]) -> str:
    base = "wp_" + re.sub(r"[^a-z0-9_]", "_", str(event_id).lower()).strip("_")[:40]
    cid, n = base, 2
    while cid in taken:
        cid, n = f"{base}_{n}", n + 1
    return cid


def wp_ids(c: dict) -> list[str]:
    """`warmpod_id` is one id, or a list when several warmpod incidents are one case."""
    v = c.get("warmpod_id")
    return [v] if isinstance(v, str) else list(v or [])


def add_wp(c: dict, eid: str) -> None:
    ids = wp_ids(c)
    if eid not in ids:
        ids.append(eid)
    c["warmpod_id"] = ids[0] if len(ids) == 1 else ids


def to_event(r: dict) -> dict:
    names = [c.get("name", "").strip() for c in r.get("companies") or [] if c.get("name")]
    # startedAt is when the breach happened or was first reported; publishedAt is the lead
    # article, which can be a later sanction story months after.
    d = (r.get("startedAt") or r.get("publishedAt") or "")[:10]
    official = list(r.get("officialUrls") or [])
    if (r.get("sanction") or {}).get("url"):
        official.insert(0, r["sanction"]["url"])
    return {"id": str(r.get("id") or ""), "company": names[0] if names else "", "date": d,
            "article_url": r.get("url"), "official_urls": list(dict.fromkeys(official))}


def new_case(ev: dict, cid: str, today: str) -> dict:
    disclosed = ev["date"][:7]
    y, m = disclosed.split("-")
    official = [u for u in (clean_url(x) for x in ev.get("official_urls") or []) if u]
    article = clean_url(ev.get("article_url") or "")
    company = re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사", "", ev["company"]).strip()
    case = {
        "id": cid,
        "company": company,
        "disclosed": disclosed,
        "audience": "customers",
        "size": (ev.get("size") or "미확인").strip(),
        "items": [str(i).strip() for i in ev.get("items") or [] if str(i).strip()],
        "self_check": {
            "status": "unknown",
            "url": None,
            "how": "확인 방법 미정. 회사 공지와 조회 페이지를 사람이 확인한 뒤 채운다. 그동안은 메일함과 문자함에서 회사 이름으로 찾아본다.",
            "checked": today,
        },
        "notices": [],
        "search": {"mail": [f"{company} 개인정보 유출"], "sms": [company], "basis": "suggested"},
        "contact": "",
        "limitation_earliest": f"{int(y) + 3}-{m}",
        "sources": official + ([article] if article and article not in official else []),
        "warmpod_id": str(ev["id"]),
        "review": "pending",
    }
    if not official:
        case["confidence"] = "press_only"
    return case


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("export")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--link", nargs="*", default=[], help="WARMPOD_ID=CASE_ID pairs to link by hand")
    ap.add_argument("--add", nargs="*", default=[], help="warmpod ids of new incidents to add as cases")
    a = ap.parse_args()

    exp = load_export(a.export)
    events = exp if isinstance(exp, list) else (exp.get("incidents") or exp.get("items") or [])
    if not isinstance(events, list):
        print("export has no incident list", file=sys.stderr)
        return 1
    data = json.loads(CASES.read_text(encoding="utf-8"))
    cases = data["cases"]
    by_wp = {w: c for c in cases for w in wp_ids(c)}
    taken = {c["id"] for c in cases}
    today = date.today().isoformat()
    ids = {c["id"]: c for c in cases}
    manual = {}
    for pair in a.link:
        wp, _, cid = pair.partition("=")
        if cid not in ids:
            print(f"--link {pair}: no case {cid}", file=sys.stderr)
            return 1
        manual[wp] = ids[cid]
    linked, added, known, skipped, queued = [], [], [], [], []

    for raw in events:
        ev = to_event(raw)
        eid, company, d = ev["id"], ev["company"], ev["date"]
        if not eid or not company or not DATE.match(d[:10]):
            skipped.append(f"{eid or '?'} {company or '?'}: id, company, date(YYYY-MM-DD) required")
            continue
        if eid in by_wp:
            known.append(f"{eid} = {by_wp[eid]['id']}")
            continue
        if eid in manual:
            c = manual[eid]
            add_wp(c, eid)
            by_wp[eid] = c
            linked.append(f"{eid} {company} -> existing {c['id']} (by hand)")
            continue
        hits = [c for c in cases if not wp_ids(c)
                and (norm(company) in norm(c["company"]) or norm(c["company"].split(" (")[0]) == norm(company))
                and abs(months(c["disclosed"]) - months(d)) <= 3]
        if len(hits) == 1:
            add_wp(hits[0], eid)
            by_wp[eid] = hits[0]
            linked.append(f"{eid} {company} -> existing {hits[0]['id']}")
            continue
        if len(hits) > 1:
            skipped.append(f"{eid} {company}: matches {[h['id'] for h in hits]}, link by hand")
            continue
        if eid not in a.add:
            queued.append({"id": eid, "company": company, "date": d[:10], "headline": raw.get("headline"),
                           "kind": raw.get("kind"), "url": raw.get("url"), "official_urls": ev["official_urls"]})
            continue
        cid = new_id(eid, taken)
        taken.add(cid)
        c = new_case(ev, cid, today)
        cases.append(c)
        by_wp[eid] = c
        added.append(f"{eid} {company} {d[:7]} -> new {cid} (review pending)")

    queue_rows = [f"{q['id']} {q['company']} {q['date'][:7]} | {q['headline'] or ''}"[:140] for q in queued]
    for title, rows in (("linked", linked), ("added", added), ("queued for review", queue_rows), ("already linked", known), ("skipped", skipped)):
        print(f"## {title}: {len(rows)}")
        for r in rows:
            print("  " + r)
    if a.write and (linked or added):
        data["updated"] = today
        CASES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        firms = json.loads(FIRMS.read_text(encoding="utf-8"))
        listed = {b["case"] for b in firms["cases"]} | {x["case"] for x in firms["no_recruitment_found"]}
        for c in cases:
            if c.get("review") == "pending" and c["id"] not in listed:
                firms["no_recruitment_found"].append({"case": c["id"], "checked": today, "note": "새로 들어온 사건. 법무법인 모집 여부는 아직 확인하지 않았다."})
        FIRMS.write_text(json.dumps(firms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("wrote", CASES)
    if a.write:
        QUEUE.parent.mkdir(exist_ok=True)
        QUEUE.write_text(json.dumps({"fetched": today, "source": a.export, "incidents": queued}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("queue", QUEUE, len(queued))
    if not a.write:
        print("(dry run, nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
