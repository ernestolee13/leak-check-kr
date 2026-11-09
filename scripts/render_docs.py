#!/usr/bin/env python3
"""Generate the human-readable guide from data/*.json and sync the skill snapshot.

data/cases.json and data/firms.json are the only hand-edited sources. This
writes:
  FIRMS.md   firms taking plaintiffs, per case, in the order firms.json gives
             (validate_data.py enforces name order)
  CASES.md   per case: how to find the notice, search words, self-check page
  README.md  the block between <!-- summary:start --> and <!-- summary:end -->
  plugins/leak-check-kr/skills/leak-check/references/  data snapshot the skill
             falls back to when it cannot fetch the live files

    render_docs.py          write everything
    render_docs.py --check  exit 1 if anything is out of date
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REFS = ROOT / "plugins" / "leak-check-kr" / "skills" / "leak-check" / "references"
STATUS = {
    "open": "접수 중",
    "limited": "일부만 접수",
    "open_unconfirmed": "마감 공지 없음, 접수 전 확인",
    "press_only": "보도로만 확인",
    "closed": "마감",
}
CHECK = {"open": "열림", "login": "로그인 후 조회", "closed": "닫힘", "none": "조회 창구 없음", "unknown": "확인 못 함"}
AUDIENCE = {"customers": "이용자", "employees": "임직원, 협력사", "mixed": "이용자와 임직원"}
NOTICE_BASIS = {"company_notice": "회사 공지", "user_post": "이용자가 올린 전사", "press": "보도", "notice": "개별 통지 (발신과 제목)"}


def cell(v) -> str:
    return str(v if v not in (None, "") else "미기재").replace("|", "\\|").replace("\n", " ")


def firms_md(cases: dict, firms: dict) -> str:
    names = {c["id"]: c["company"] for c in cases["cases"]}
    out = [
        "# 지금 원고를 받는 법무법인",
        "",
        f"마지막 확인 {firms['updated']}. {firms['order']} 추천이나 순위가 아니고, 각 법무법인 페이지에 적힌 내용을 옮긴 것이다. "
        "이 목록을 만든 사람은 변호사가 아니며 어느 법무법인에서도 대가를 받지 않는다. 신청 전에 각 페이지에서 조건을 다시 확인한다.",
        "",
        "성공보수는 이겼을 때 받은 돈에서 법무법인이 가져가는 비율이다. 한 사건에 두 곳에 신청하면 문제가 될 수 있으니, 이미 신청한 곳이 있으면 그 법무법인에 먼저 확인한다.",
        "",
    ]
    for b in firms["cases"]:
        out += [f"## {names.get(b['case'], b['case'])}", ""]
        live = [r for r in b["firms"] if r["status"] != "closed"]
        closed = [r for r in b["firms"] if r["status"] == "closed"]
        if live:
            out += ["| 법무법인 | 상태 | 착수금, 참가비 | 성공보수 | 패소 시 | 마감 | 접수 | 확인일 |", "|---|---|---|---|---|---|---|---|"]
            for r in live:
                firm = f"[{cell(r['firm'])}]({r['url']})" if r.get("url") else cell(r["firm"])
                status = STATUS[r["status"]] + (f" ({cell(r['round'])})" if r.get("round") else "")
                if r.get("note"):
                    status += f". {cell(r['note'])}"
                deadline = r.get("deadline") or "적혀 있지 않음"
                out.append(f"| {firm} | {status} | {cell(r['upfront'])} | {cell(r['success_fee'])} | {cell(r['if_lost'])} | {cell(deadline)} | {cell(r['intake'])} | {r['checked']} |")
            out.append("")
        if closed:
            out.append("마감: " + ", ".join(f"{r['firm']}" + (f" ({r['deadline']})" if r.get("deadline") else "") for r in closed))
            out.append("")
    out += ["## 아직 원고를 받는 곳이 없는 사건", "",
            "법무법인 사이트, 모집 플랫폼, 「원고 모집」 보도를 찾아봤지만 지금 접수하는 곳을 찾지 못한 사건이다. 통지 문자와 메일을 지우지 말고 보관해 둔다.", "",
            "| 사건 | 마지막 확인 | 메모 |", "|---|---|---|"]
    for n in firms.get("no_recruitment_found", []):
        out.append(f"| {cell(names.get(n['case'], n['case']))} | {n['checked']} | {(n.get('note') or '').replace('|', '/')} |")
    out.append("")
    return "\n".join(out)


def cases_md(cases: dict) -> str:
    out = [
        "# 사건별 유출 확인하는 법",
        "",
        f"마지막 갱신 {cases['updated']}. {cases['how_to_use']}",
        "",
        f"어느 회사인지 모를 때: [{cases['fallback']['kisa']['name']}]({cases['fallback']['kisa']['url']}). {cases['fallback']['kisa']['note']} 신고와 상담은 {cases['fallback']['report']}.",
        "",
    ]
    for c in cases["cases"]:
        sc = c["self_check"]
        out += [f"## {c['company']}", ""]
        out.append(f"- 알려진 때 {c['disclosed']}, 대상 {AUDIENCE[c['audience']]}, 규모 {c['size']}")
        if c.get("confidence") == "press_only":
            out.append("- 회사 공지를 직접 확인하지 못했고 보도로만 확인했다")
        if c.get("scope_note"):
            out.append(f"- {c['scope_note']}")
        out.append(f"- 유출 항목: {', '.join(c['items'])}")
        link = f" [{sc['url']}]({sc['url']})" if sc.get("url") else ""
        out.append(f"- 회사 조회: {CHECK[sc['status']]}.{link} {sc['how']} (확인 {sc['checked']})")
        for n in c.get("notices", []):
            out.append(f"- 통지 예시 ({n['channel']}, {n['sender']}, {n['date']}, 출처 {NOTICE_BASIS[n['basis']]}): 「{n['opening']}」")
        q = c["search"]
        if q.get("mail") or q.get("sms"):
            basis = "실제 통지 문구 기반" if q["basis"] == "notice_text" else "추정 검색어라 놓칠 수 있음"
            mail = ", ".join(f"`{x}`" for x in q.get("mail", [])) or "없음"
            sms = ", ".join(f"`{x}`" for x in q.get("sms", [])) or "없음"
            out.append(f"- 메일 검색어 {mail}, 문자 검색어 {sms} ({basis})")
        if c.get("contact"):
            out.append(f"- 문의: {c['contact']}")
        if c.get("fraud_warning"):
            out.append(f"- 사칭 주의: {c['fraud_warning']}")
        if c.get("note"):
            out.append(f"- 참고: {c['note']}")
        out.append(f"- 가장 이른 시효 만료 예상 {c['limitation_earliest']} (알려진 달에 3년을 더한 값, 법률 판단 아님)")
        if c.get("sources"):
            out.append("- 출처: " + ", ".join(c["sources"]))
        out.append("")
    return "\n".join(out)


def summary_block(cases: dict, firms: dict) -> str:
    names = {c["id"]: c["company"] for c in cases["cases"]}
    lines = ["<!-- summary:start -->", f"**{firms['updated']} 기준.** 사건 {len(cases['cases'])}건, 법무법인 조건 {sum(len(b['firms']) for b in firms['cases'])}행.", ""]
    for b in firms["cases"]:
        live = [r for r in b["firms"] if r["status"] != "closed"]
        if live:
            lines.append(f"- {names[b['case']]}: " + ", ".join(f"{r['firm']} ({STATUS[r['status']]})" for r in live))
    none = firms.get("no_recruitment_found", [])
    if none:
        lines += ["", f"- 아직 원고를 받는 곳이 없음 ({len(none)}건): " + ", ".join(names[n["case"]] for n in none)]
    lines += ["", "법무법인 이름 순이며 추천이 아니다. 조건과 공식 링크는 [FIRMS.md](FIRMS.md), 사건별 확인법은 [CASES.md](CASES.md).", "<!-- summary:end -->"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cases = json.loads((DATA / "cases.json").read_text(encoding="utf-8"))
    firms = json.loads((DATA / "firms.json").read_text(encoding="utf-8"))
    want = {ROOT / "FIRMS.md": firms_md(cases, firms) , ROOT / "CASES.md": cases_md(cases)}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    want[ROOT / "README.md"] = re.sub(r"<!-- summary:start -->.*?<!-- summary:end -->", lambda _: summary_block(cases, firms), readme, flags=re.S)
    for name in ("cases.json", "firms.json", "schema.md"):
        want[REFS / name] = (DATA / name).read_text(encoding="utf-8")
    stale = [p for p, text in want.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        print("OK: generated files match data" if not stale else "run scripts/render_docs.py")
        return 1 if stale else 0
    REFS.mkdir(parents=True, exist_ok=True)
    for p in stale:
        p.write_text(want[p], encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
