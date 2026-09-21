# -*- coding: utf-8 -*-
"""WP3 coding: 112- and 113-year Open Green cases (改造組 with 核定經費, and the
113E 整備組 cases readable from the review tables).

Layer assignment follows the four-ledger rule; no case is assigned to Layer 2.
Fields not reliably present are left blank (no guessing).

Output: opengreen_112_113_coded.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp3_code_114E import district_centroids

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "opengreen_112_113_coded.csv"
FIELDS = ["year", "region", "case_name", "district", "village", "site_address",
          "proposing_unit", "investment_type", "layer", "main_benefit",
          "maintenance_years", "verifiability", "lon", "lat", "geo_level",
          "coding_confidence", "source_report"]

# (year, region, name, district, village, proposer, itype, benefit, verif, note)
CASES = [
    # 112 東（改造組；已排除未通過之「台北Green 通用 Green」）
    (2023, "E", "茶山自然教室之點線面的串連與再進化", "文山區", "", "茶山自然教室（張錦祥）",
     "建置;共同規劃", "adaptation;nature;social", "中", "核定 225,900 元；平均 86.5 分"),
    (2023, "E", "OPG 舊庄店仔口農園", "南港區", "舊莊里", "張瑞芳",
     "建置;共同規劃", "adaptation;nature;social", "中", "核定 300,000 元；平均 84.125 分"),
    # 112 東（自 MarkItDown .md 表個擷取；PDF 文字層先前無法取得）
    (2023, "E", "白石湖社區綠環境空間盤點計畫", "內湖區", "", "臺北市內湖區白石湖社區發展協會",
     "共同規劃", "nature;social", "中", "112 東（md 表）"),
    (2023, "E", "112年大湖社區親河親山環境串連計畫", "內湖區", "大湖里",
     "臺北市內湖區大湖社區發展協會", "共同規劃;建置", "adaptation;nature;social", "中",
     "112 東（md 表）"),
    (2023, "E", "親近【內湖第一棵大樹】", "內湖區", "", "王郁蘭",
     "共同規劃", "social;nature", "中", "112 東（md 表）"),
    (2023, "E", "Open Corner, Open Power -共享綠空間奇蹟", "南港區", "",
     "臺北市南港區久如社區發展協會", "共同規劃;建置", "adaptation;social", "中",
     "112 東（md 表）"),
    (2023, "E", "聯成社區巷弄香草園", "南港區", "", "臺北市南港區聯成社區發展協會",
     "共同規劃", "nature;social", "中", "112 東（md 表）"),
    # 112 西（改造組）
    (2023, "W", "Open Yard 打開大我的院子", "", "", "岩山社區文史志工團",
     "建置;共同規劃", "adaptation;social", "中", "核定 30 萬元"),
    (2023, "W", "萬華糖廍 ESG 可食地景", "萬華區", "", "萬華社區小學",
     "建置;共同規劃", "nature;social", "中", "核定 14 萬元"),
    (2023, "W", "點亮寶村-共生聚落農園新生計畫", "中正區", "", "台北市寶藏巖文化村協會",
     "建置;共同規劃", "adaptation;social", "中", "核定 10 萬元"),
    # 113 東（改造組）
    (2024, "E", "113年大湖社區親河親山環境串連計畫", "內湖區", "大湖里",
     "大湖居安社區發展協會", "建置;共同規劃", "adaptation;nature;social", "中",
     "核定 250,000 元"),
    (2024, "E", "再造華夏-荒蕪空地的華麗轉身", "", "古莊里", "",
     "建置;共同規劃", "adaptation;social", "中", "核定 250,000 元"),
    (2024, "E", "古亭市場", "", "", "",
     "建置;共同規劃", "social", "中", "核定 250,000 元"),
    (2024, "E", "119 地號田園城市", "", "景聯里", "",
     "建置;共同規劃", "adaptation;social", "中", "核定 250,000 元（三興段一小段 119 地號）"),
    # 113 東（整備組；可讀取者）
    (2024, "E", "共耕食代綠色生活圈—共生聚落發展計畫", "", "", "共耕食代企業社",
     "共同規劃", "social;nature", "中", "整備組"),
    (2024, "E", "打造新世代共學生活村", "", "", "社團法人台灣展賦協會",
     "共同規劃", "social", "中", "整備組"),
    (2024, "E", "脫鞋趣", "", "", "向日有機農場",
     "共同規劃", "nature;social", "中", "整備組"),
    # 113 西（改造組）
    (2024, "W", "大屯共饗空間", "北投區", "", "張天恩",
     "建置;共同規劃", "adaptation;social", "中", "核定 270,000 元；已營運有成"),
    (2024, "W", "善.美的生態x永續x美學基地-延平201", "大同區", "", "財團法人台北市至善堂",
     "建置;共同規劃", "adaptation;social", "中", "核定 300,000 元"),
    (2024, "W", "攜家帶眷，做伙來OPH", "", "", "財團法人台北市客家文化基金會",
     "建置;共同規劃", "nature;social", "中", "核定 150,000 元（客家農場）"),
    (2024, "W", "「中山有點草」城市生態野化計畫", "中山區", "", "雜草稍慢",
     "共同規劃;維護", "nature;social", "中", "核定 280,000 元"),
]


def main():
    cent = district_centroids()
    rows = []
    for (yr, reg, name, dist, vil, unit, itype, benefit, veri, note) in CASES:
        lon = lat = level = ""
        if dist in cent:
            lon, lat = cent[dist]
            level = "district-centroid (approx.)"
        rows.append({"year": yr, "region": reg, "case_name": name, "district": dist,
                     "village": vil, "site_address": "", "proposing_unit": unit,
                     "investment_type": itype, "layer": "3;4", "main_benefit": benefit,
                     "maintenance_years": "", "verifiability": veri, "lon": lon, "lat": lat,
                     "geo_level": level, "coding_confidence": f"inferred (待複核); {note}",
                     "source_report": f"{yr - 1911}{reg}"})
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    print(f"coded {len(rows)} cases (112-113) -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
