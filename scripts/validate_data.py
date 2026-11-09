#!/usr/bin/env python3
"""Validate data/cases.json and data/firms.json before publishing.

The firm list is the legally sensitive half of this project: the plugin and the
page must never present one firm above another for any reason other than a
fixed, stated rule. So the order is enforced here instead of trusted to hand
edits. Rule: sort by firm name with Python's default string order (Latin
letters first, then Hangul in 가나다 order). `--fix` rewrites the file sorted.

Also checks: every firm row has a check date and an official URL or an
explicit null with a reason, every case referenced by firms.json exists in
cases.json, and no row carries referral/tracking parameters.

    validate_data.py          check, exit 1 on problems
    validate_data.py --fix    sort firms in place, then check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "cases.json"
FIRMS = ROOT / "data" / "firms.json"

FIRM_STATUSES = {"open", "open_unconfirmed", "limited", "press_only", "closed"}
CHECK_STATUSES = {"open", "login", "closed", "none", "unknown"}
AUDIENCES = {"customers", "employees", "mixed"}
REQUIRED_FIRM_KEYS = {"firm", "status", "upfront", "success_fee", "if_lost", "intake", "url", "quote", "checked"}
# Anything that could look like we are paid per referral.
TRACKING_PARAMS = re.compile(r"^(utm_|ref$|referral|aff|partner|recommend|invite)", re.I)
# Words the plugin and data must not use about a firm (ranking, endorsement, outcome).
BANNED_WORDS = ["추천", "최저", "최고", "1위", "승소 확률", "승소율", "예상 배상", "연결해 드립니다", "연결해드", "보장",
                "실수령", "승산", "손에 남는", "1인당 10만"]
# Text outside firms.json that users read. Lines that deliberately disclaim
# (「추천이 아니다」, 「추천하지 않는다」) are allowed by ALLOW.
PROSE_FILES = [ROOT / "README.md", ROOT / "FIRMS.md", ROOT / "CASES.md", ROOT / "MAINTAINING.md", ROOT / "plugins/leak-check-kr/skills/leak-check/SKILL.md"]
ALLOW = re.compile(r"추천(이나|이|을|하지| 아님| 없이|,? 순위|하는 것)|권하지 않|순위가 아니|보장되지")
# A line that forbids the words (the SKILL's own rules) may name them.
PROHIBITION = re.compile(r"(말하지|계산하거나|보여 주지|쓰지|넣지) 않는다")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def firm_sort_key(row: dict) -> str:
    return row["firm"]


def check(cases: dict, firms: dict) -> list[str]:
    errs: list[str] = []
    case_ids = set()
    for c in cases["cases"]:
        cid = c.get("id")
        if cid in case_ids:
            errs.append(f"cases: duplicate id {cid}")
        case_ids.add(cid)
        if c.get("audience") not in AUDIENCES:
            errs.append(f"cases/{cid}: audience must be one of {sorted(AUDIENCES)}")
        sc = c.get("self_check") or {}
        if sc.get("status") not in CHECK_STATUSES:
            errs.append(f"cases/{cid}: self_check.status must be one of {sorted(CHECK_STATUSES)}")
        if sc.get("status") == "open" and not sc.get("how"):
            errs.append(f"cases/{cid}: open self_check needs 'how'")
        if not DATE_RE.match(sc.get("checked") or ""):
            errs.append(f"cases/{cid}: self_check.checked must be YYYY-MM-DD")
        if "search" not in c or not isinstance(c["search"].get("mail"), list):
            errs.append(f"cases/{cid}: search.mail list missing")

    seen_cases = set()
    for block in firms["cases"]:
        cid = block["case"]
        if cid not in case_ids:
            errs.append(f"firms: case '{cid}' not in cases.json")
        if cid in seen_cases:
            errs.append(f"firms: case '{cid}' listed twice")
        seen_cases.add(cid)
        names = [r["firm"] for r in block["firms"]]
        if names != sorted(names):
            errs.append(f"firms/{cid}: not in name order: {names} (run --fix)")
        for r in block["firms"]:
            tag = f"firms/{cid}/{r.get('firm')}"
            missing = REQUIRED_FIRM_KEYS - r.keys()
            if missing:
                errs.append(f"{tag}: missing {sorted(missing)}")
            if r.get("status") not in FIRM_STATUSES:
                errs.append(f"{tag}: status must be one of {sorted(FIRM_STATUSES)}")
            if not DATE_RE.match(r.get("checked") or ""):
                errs.append(f"{tag}: checked must be YYYY-MM-DD")
            if r.get("status") == "limited" and not r.get("note"):
                errs.append(f"{tag}: limited rows must say who is accepted in 'note'")
            url = r.get("url")
            if url and not url.startswith("https://"):
                errs.append(f"{tag}: url must be https")
            if url is None and "찾지 못" not in (r.get("intake") or ""):
                errs.append(f"{tag}: url is null without saying why in intake")
            if url:
                q = parse_qs(urlparse(url).query)
                bad = [k for k in q if TRACKING_PARAMS.match(k)]
                if bad:
                    errs.append(f"{tag}: tracking/referral params in url: {bad}")
            blob = json.dumps(r, ensure_ascii=False)
            for w in BANNED_WORDS:
                if w in blob:
                    errs.append(f"{tag}: banned word '{w}'")
    none = set(firms.get("no_recruitment_found", []))
    for cid in none - case_ids:
        errs.append(f"firms.no_recruitment_found: unknown case '{cid}'")
    for cid in none & seen_cases:
        errs.append(f"firms: case '{cid}' is both listed and in no_recruitment_found")
    for cid in case_ids - none - seen_cases:
        errs.append(f"firms: case '{cid}' is neither listed nor in no_recruitment_found")
    sad = firms.get("stale_after_days")
    if not isinstance(sad, int) or sad <= 0:
        errs.append("firms.stale_after_days must be a positive int")
    for c in cases["cases"]:
        blob = json.dumps(c, ensure_ascii=False)
        for w in BANNED_WORDS:
            if w in blob:
                errs.append(f"cases/{c['id']}: banned word '{w}'")
    for f in PROSE_FILES:
        if not f.exists():
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            hit = [w for w in BANNED_WORDS if w in line]
            if hit and not (hit == ["추천"] and ALLOW.search(line)) and not PROHIBITION.search(line):
                errs.append(f"{f.name}:{n}: banned word {hit}")
    for k in ("about", "order"):
        if not firms.get(k):
            errs.append(f"firms: top-level '{k}' missing")
    for w in BANNED_WORDS:
        if w in firms.get("about", "") and w != "추천":
            errs.append(f"firms.about: banned word '{w}'")
    for f, d in (("cases", cases), ("firms", firms)):
        if not DATE_RE.match(d.get("updated", "")):
            errs.append(f"{f}: updated must be YYYY-MM-DD")
        elif date.fromisoformat(d["updated"]) > date.today():
            errs.append(f"{f}: updated is in the future")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="sort firms by name and rewrite firms.json")
    a = ap.parse_args()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    firms = json.loads(FIRMS.read_text(encoding="utf-8"))
    if a.fix:
        for block in firms["cases"]:
            block["firms"].sort(key=firm_sort_key)
        FIRMS.write_text(json.dumps(firms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errs = check(cases, firms)
    for e in errs:
        print("FAIL", e)
    n_cases = len(cases["cases"])
    n_rows = sum(len(b["firms"]) for b in firms["cases"])
    n_open = sum(1 for b in firms["cases"] for r in b["firms"] if r["status"] in ("open", "limited"))
    print(f"{'FAIL' if errs else 'OK'}: {n_cases} cases, {n_rows} firm rows ({n_open} open or limited)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
