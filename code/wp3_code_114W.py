# -*- coding: utf-8 -*-
"""WP3 coding: 114-year West-district Open Green cases.

Source: 114W report tables — 改造組 (4 cases, with 核定經費) and 整備組 (9 cases,
審查意見表).  Layer assignment follows the four-ledger rule (none to Layer 2).

Output: opengreen_114W_coded.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp3_code_114E import district_centroids

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "opengreen_114W_coded.csv"
FIELDS = ["year", "region", "case_name", "district", "village", "site_address",
          "proposing_unit", "investment_type", "layer", "main_benefit",
          "maintenance_years", "verifiability", "lon", "lat", "geo_level",
          "coding_confidence", "source_report"]

# (name, district, village, address, proposer, itype, layer, benefit, verif, note)
CASES = [
    # 改造組
    ("文林社區樸門綠生活2.0", "北投區", "文林里", "",
     "臺北市北投區文林里辦公處、臺北市北投區文林社區發展協會",
     "建置;共同規劃;維護", "3;4", "adaptation;nature;social", "中", "核定經費 250,000"),
    ("城市綠洲計畫-百間厝文化藝術公園", "中正區", "", "",
     "臺北市中正區新營共好社區發展協會",
     "建置;共同規劃", "3;4", "adaptation;social", "中", "核定經費 250,000"),
    ("食農小亭園", "", "騰雲里", "",
     "財團法人海棠文教基金會、騰雲里里辦公室",
     "建置;共同規劃", "3;4", "social;nature", "中", "核定經費 250,000"),
    ("OPEN 北投101", "北投區", "", "",
     "臺北市北投社區大學（財團法人台北市北投文化基金會）",
     "共同規劃;建置", "3;4", "adaptation;social", "中", "經費待確認"),
    # 整備組
    ("朝陽造起來", "", "", "", "朝陽里辦公處、親糸制藝所",
     "共同規劃", "3;4", "social", "中", "整備組"),
    ("我愛石牌社區樸門綠一下－照顧地球、照顧人、分享多餘", "北投區", "石牌里", "",
     "臺北市北投區石牌里辦公處、臺北市北投區我愛石牌社區發展協會",
     "共同規劃", "3;4", "nature;social", "中", "整備組"),
    ("五常綠生活", "", "", "", "五常國中",
     "共同規劃", "3;4", "social;nature", "中", "整備組"),
    ("頂碩里四個小朋友公園", "", "頂碩里", "", "頂碩里辦公處",
     "共同規劃", "3;4", "social", "中", "整備組"),
    ("綠色健康家居由廚餘養耕循環開始", "", "", "", "都市蚓農企業社",
     "共同規劃", "3;4", "nature;social", "中", "整備組"),
    ("有機綠生活-廚餘助益", "", "", "", "蕃薯藤有限公司",
     "共同規劃", "3;4", "nature;social", "中", "整備組"),
    ("建民社區全齡綠化環保行動", "北投區", "建民里", "文林北路130號",
     "建民里辦公處", "共同規劃", "3;4", "adaptation;social", "中", "整備組"),
    ("崁頂探險：尋找社區黃金點", "", "永昌里", "",
     "臺北市中正社區大學、永昌里辦公處、新永昌社區發展協會、荒野保護協會、南海藝工作室",
     "共同規劃", "3;4", "social;nature", "中", "整備組"),
    ("心橋薪橋平樂天橋", "", "", "", "財團法人台北市至善堂",
     "共同規劃", "3;4", "social", "中", "整備組"),
]


def main():
    cent = district_centroids()
    rows = []
    for (name, dist, vil, addr, unit, itype, layer, benefit, veri, note) in CASES:
        lon = lat = level = ""
        if dist in cent:
            lon, lat = cent[dist]
            level = "district-centroid (approx.)"
        rows.append({"year": 2025, "region": "W", "case_name": name, "district": dist,
                     "village": vil, "site_address": addr, "proposing_unit": unit,
                     "investment_type": itype, "layer": layer, "main_benefit": benefit,
                     "maintenance_years": "", "verifiability": veri, "lon": lon, "lat": lat,
                     "geo_level": level, "coding_confidence": f"inferred (待複核); {note}",
                     "source_report": "114W"})
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    l2 = sum(1 for r in rows if "2" in r["layer"].split(";"))
    print(f"coded {len(rows)} cases -> {OUT.name}; Layer2 count = {l2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
