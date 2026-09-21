# -*- coding: utf-8 -*-
"""WP3 (enterprise): build the full corporate climate/nature project registry from
the 林業及自然保育署「自然碳匯與生物多樣性專案媒合平臺」 listing captured via
Playwright (Paper/paper_esg_projects.json, 35 matched cases).

Codes each project to the four-ledger model by its 專案類型 and extracts county.

Outputs: enterprise_climate_projects_full.csv + wp3_enterprise_full.json
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "Paper" / "paper_esg_projects.json"
OUT_CSV = ROOT / "enterprise_climate_projects_full.csv"
OUT_JSON = ROOT / "wp3_enterprise_full.json"
FIELDS = ["id", "project_name", "category", "county", "location", "period",
          "company", "layer", "main_benefit", "source_url"]


def code_layer(cat):
    if cat in ("造林", "加強森林經營", "竹林經營", "自然碳匯-其他", "土地媒合"):
        return "2待查;3;4", "carbon;nature;social"      # Layer 2 only if a methodology applies
    if cat == "環境友善產業發展":
        return "3;4", "nature;social"
    if cat in ("棲地營造", "野生物保育", "生物多樣性-其他"):
        return "3;4", "nature;social"
    return "4", "social"                                 # 林業文化 / 山林文化 / 山林開放


def county_of(loc):
    m = re.match(r"([臺台]?[^市縣]*(?:市|縣))", loc.strip())
    return m.group(1) if m else ("無特定所在位置" if "無限定" in loc else "")


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    cases = data["cases"]
    rows = []
    for c in cases:
        layer, benefit = code_layer(c["category"])
        rows.append({
            "id": c["id"], "project_name": c["name"], "category": c["category"],
            "county": county_of(c["location"]), "location": c["location"],
            "period": c["period"], "company": c["company"], "layer": layer,
            "main_benefit": benefit,
            "source_url": f"https://esg.forest.gov.tw/ForestESG/Report/Showcase?NobjID={c['id']}",
        })
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)

    counties = Counter(r["county"] for r in rows)
    cats = Counter(r["category"] for r in rows)
    in_taipei = sum(1 for r in rows if r["county"] == "臺北市")
    layer2 = sum(1 for r in rows if "2" in r["layer"].split(";")[0])
    payload = {
        "source": "林業及自然保育署 自然碳匯與生物多樣性專案媒合平臺（ESG）",
        "captured_via": "Playwright 列表頁 /ForestESG/Achievement/Object/Index",
        "n_projects": len(rows), "in_taipei": in_taipei,
        "counties": dict(counties.most_common()),
        "categories": dict(cats.most_common()),
        "key_finding": f"{len(rows)} 件企業專案中 {in_taipei} 件位於臺北市；"
                       f"其餘分布於各山林／鄉村縣市",
        "projects": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"projects {len(rows)}  in_taipei {in_taipei}  counties {len(counties)}")
    print("categories:", dict(cats))
    print("wrote", OUT_CSV.name, OUT_JSON.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
