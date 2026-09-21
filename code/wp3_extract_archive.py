# -*- coding: utf-8 -*-
"""WP3: parse the historical Open Green "案例檔案" archive entries.

The 105/106-year 成果報告 embed per-case records of the form
  [提案名稱] <year>年度-<name> [權屬] <owner> [地點] <district village address> [申請／執行] <unit>
This tool recovers them from the MarkItDown .md files.

Output: opengreen_archive_cases.csv
"""
import csv
import re
import sys
from pathlib import Path

CACHE = Path(r"C:\Users\kent6\AppData\Local\Temp\opencode")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "opengreen_archive_cases.csv"

NAME = re.compile(r"\[提案名稱\]\s*(.*?)\s*\[權屬\]", re.S)
OWNER = re.compile(r"\[權屬\]\s*(.*?)\s*\[地點\]", re.S)
LOC = re.compile(r"\[地點\]\s*(.*?)\s*\[(?:申請|執行|開放|申請／執行)", re.S)
APPLY = re.compile(r"\[(?:申請／執行|申請|執行)\]\s*(.*?)(?:\[|$)", re.S)


def clean(s):
    return re.sub(r"\s+", "", s).replace("M A P", "").strip()


def parse(text, src):
    rows = []
    for m in NAME.finditer(text):
        raw = clean(m.group(1))
        if not raw:
            continue
        name = re.sub(r"^(\d{4}年度[│\-–、,，；;]*)+", "", raw).strip()
        name = re.split(r"[\[｜|]", name)[0].strip()
        if len(name) < 3:
            continue
        tail = text[m.end():m.end() + 600]
        owner = OWNER.search(m.group(0) + tail)
        loc = LOC.search(m.group(0) + tail)
        apply_ = APPLY.search(m.group(0) + tail)
        rows.append({
            "source_md": src,
            "case_name": name,
            "year_batch": (re.search(r"(\d{4})年度", raw) or [None, ""])[1],
            "owner": clean(owner.group(1))[:40] if owner else "",
            "location": clean(loc.group(1))[:60] if loc else "",
            "applicant": clean(apply_.group(1))[:40] if apply_ else "",
            "quality": "ok" if len(name) <= 30 else "merged(需複核)",
        })
    return rows


def main():
    rows = []
    for src in ["105R.md", "106R.md", "112R.md"]:
        p = CACHE / src
        if not p.exists():
            continue
        rows += parse(p.read_text(encoding="utf-8"), src)
    # dedup by case name
    seen, ded = set(), []
    for r in rows:
        if r["case_name"] in seen:
            continue
        seen.add(r["case_name"])
        ded.append(r)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["source_md", "case_name", "year_batch",
                                            "owner", "location", "applicant", "quality"])
        wr.writeheader()
        wr.writerows(ded)
    print(f"archive cases {len(ded)} (raw {len(rows)}) -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
