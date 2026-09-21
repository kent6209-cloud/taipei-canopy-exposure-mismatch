# -*- coding: utf-8 -*-
"""WP3: recover case tables from the MarkItDown .md files of the Open Green reports.

Parses markdown tables whose header contains 提案名稱／計畫名稱／提案主題 together
with 提案單位／團隊名稱 and/or 核定經費／核定金額, and emits one row per case.

Output: opengreen_cases_md.csv
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Paper" / "opengreen"
OUT = ROOT / "opengreen_cases_md.csv"


def tables(lines):
    """Yield (header_cells, [data_rows]) for each markdown table."""
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) \
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


def col(cells, *keys):
    for k in keys:
        for idx, c in enumerate(cells):
            if k in c:
                return idx
    return None


AMT = re.compile(r"(\d[\d,]{3,}|\d+\s*萬|[\d.]+\s*元)")


def main():
    out_rows = []
    for md in sorted(SRC.glob("*.md")):
        if md.stat().st_size == 0:
            continue
        lines = md.read_text(encoding="utf-8").splitlines()
        stem = md.stem
        for header, rows in tables(lines):
            h = "".join(header)
            if not (("名稱" in h or "主題" in h) and
                    ("核定" in h or "團隊" in h or "單位" in h)):
                continue
            iname = col(header, "提案名稱", "計畫名稱", "提案主題", "名稱")
            iorg = col(header, "團隊名稱", "提案單位", "團隊")
            iamt = col(header, "核定經費", "核定金額", "金額", "經費")
            for r in rows:
                if not r or not any(r):
                    continue
                name = r[iname] if iname is not None and iname < len(r) else ""
                org = r[iorg] if iorg is not None and iorg < len(r) else ""
                amt = r[iamt] if iamt is not None and iamt < len(r) else ""
                name = name.strip()
                if len(name) < 3 or name.replace(" ", "").isdigit():
                    continue
                out_rows.append({"source_md": stem, "case_name": name,
                                 "proposing_unit": org.strip(),
                                 "budget": amt.strip()})
    # de-dup
    seen, dedup = set(), []
    for r in out_rows:
        k = (r["case_name"], r["proposing_unit"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["source_md", "case_name",
                                            "proposing_unit", "budget"])
        wr.writeheader()
        wr.writerows(dedup)
    print(f"rows {len(dedup)} -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
