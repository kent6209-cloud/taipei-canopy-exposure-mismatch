# -*- coding: utf-8 -*-
"""WP3 coding demonstration: code the 114-year East-district Open Green cases.

Fills the registry schema (investment_type / layer / benefit / verifiability)
for the 11 cases recovered from the 114E report, and attaches an approximate
location at DISTRICT level (from the district polygon centroid) where the exact
address is not available.  Fields inferred from the report's exploration records
are marked coding_confidence = "inferred (待複核)".

Output: opengreen_114E_coded.csv
"""
import csv
import sys
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parent
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT = ROOT / "opengreen_114E_coded.csv"

FIELDS = ["year", "region", "case_name", "district", "village", "site_address",
          "proposing_unit", "investment_type", "layer", "main_benefit",
          "maintenance_years", "verifiability", "lon", "lat", "geo_level",
          "coding_confidence", "source_report"]

# 11 cases from 114E (改造組 + 整備組). "layer" per the four-ledger rule:
# urban greening -> Layer 3 (nature/adaptation) + Layer 4 (social/governance);
# Layer 2 (removal) is NOT assigned (no methodology/additionality evidence).
CASES = [
    ("翠湖農園改造計畫", "內湖區", "大湖里", "台北市內湖區大湖山莊街131號",
     "大湖居安社區發展協會（拜訪紀錄）", "建置;維護", "3;4", "adaptation;social",
     "", "中", "inferred (待複核)"),
    ("脫鞋趣2.0", "", "", "",
     "", "建置", "3;4", "social;nature", "", "低-中", "inferred (待複核)"),
    ("廣慈田田圈—打造社宅綠屋頂生態跳島行動計畫", "信義區", "大仁里",
     "台北市信義區福德街86號R樓（信義區公所頂樓）", "共耕食代企業社（拜訪紀錄）",
     "建置;共同規劃", "3;4", "adaptation;nature;social", "", "中", "inferred (待複核)"),
    ("古風共學共做串燒", "大安區", "古風里", "",
     "臺北市大安區古風社區發展協會（拜訪紀錄）", "勞務;共同規劃", "3;4", "social;nature",
     "", "中", "inferred (待複核)"),
    ("綠活・共生", "", "", "", "", "勞務;共同規劃", "3;4", "social", "", "中",
     "inferred (待複核)"),
    ("里山淨零-店仔綠生活體驗", "南港區", "舊莊里", "",
     "張瑞芳（舊庄店仔復興）", "勞務;共同規劃", "3;4", "nature;social", "", "中",
     "inferred (待複核)"),
    ("松榕農園改造計畫", "信義區", "松隆里", "", "",
     "建置", "3;4", "adaptation;social", "", "低-中", "inferred (待複核)"),
    ("西湖里綠園圃整理計畫", "內湖區", "西湖里", "",
     "黃俊隆（西湖社區發展協會）", "建置;維護", "3;4", "adaptation;social", "", "中",
     "inferred (待複核)"),
    ("行善內湖·食全拾美", "內湖區", "湖元里", "", "杜瑋霖",
     "共同規劃;維護", "3;4", "social;nature", "", "中", "inferred (待複核)"),
    ("建安光影.隨憶而安", "大安區", "建安里", "建安里（捷運忠孝敦化2號出口）",
     "臺北市大安社區大學（拜訪紀錄）", "共同規劃;勞務", "3;4", "social", "", "中",
     "inferred (待複核)"),
    ("象山農場環境整體調查", "信義區", "三犁里", "",
     "臺北市藝術統合教育研究會（象山農場）", "共同規劃", "3;4", "nature;social", "", "中",
     "inferred (待複核)"),
]


def district_centroids():
    g = gpd.read_file(SHP, encoding="utf-8")
    g = g[g["COUNTYNAME"] == "臺北市"].to_crs(4326)
    c = g.geometry.centroid
    return {name: (round(x, 5), round(y, 5)) for name, x, y in
            zip(g["TOWNNAME"], c.x, c.y)}


def main():
    cent = district_centroids()
    rows = []
    for (name, dist, vil, addr, unit, itype, layer, benefit, maint, veri, conf) in CASES:
        lon = lat = ""
        level = ""
        if dist in cent:
            lon, lat = cent[dist]
            level = "district-centroid (approx.)"
        rows.append({"year": 2025, "region": "E", "case_name": name,
                     "district": dist, "village": vil, "site_address": addr,
                     "proposing_unit": unit, "investment_type": itype, "layer": layer,
                     "main_benefit": benefit, "maintenance_years": maint,
                     "verifiability": veri, "lon": lon, "lat": lat,
                     "geo_level": level, "coding_confidence": conf,
                     "source_report": "114E"})
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    print(f"coded {len(rows)} cases -> {OUT.name}")
    for r in rows:
        print(f"  {r['case_name'][:24]:26s} {r['district']}{r['village']:6s} "
              f"{r['layer']} {r['verifiability']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
