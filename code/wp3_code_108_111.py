# -*- coding: utf-8 -*-
"""WP3 coding: 108-111 Open Green cases (from the text-bearing reports;
109W / 110E / 111E are scanned images and remain pending OCR).

Output: opengreen_108_111_coded.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp3_code_114E import district_centroids

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "opengreen_108_111_coded.csv"
FIELDS = ["year", "region", "case_name", "district", "village", "site_address",
          "proposing_unit", "investment_type", "layer", "main_benefit",
          "maintenance_years", "verifiability", "lon", "lat", "geo_level",
          "coding_confidence", "source_report"]

# (year, region, name, district, proposer, note)
CASES = [
    # 108 東（核定 25 萬元 ×2；其餘多撤案）
    (2019, "E", "打造一條聯繫白屋與小白屋間的友善長廊", "文山區",
     "台北市文山區明興社區協會", "核定 25 萬元"),
    (2019, "E", "茶山Open Green自然教室", "文山區",
     "好孩子自然農場／茶山自然教室", "核定 25 萬元；原初選名「好孩子自然農場體驗營」"),
    # 108 西（認證名單 3 案）
    (2019, "W", "岩山仰德12 魚路古道口小花園", "士林區", "鄭小塔", "認證；士林區"),
    (2019, "W", "點亮太平町-台灣原生林下緣", "大同區", "施瑛雪", "認證；大同區"),
    (2019, "W", "萬華堤內健康休閒空間", "萬華區", "王梧州", "認證；萬華區"),
    # 109 東（後續擴充，與 108 東同案延續）
    (2020, "E", "打造一條聯繫白屋與小白屋間的友善長廊（後續擴充）", "文山區",
     "台北市文山區明興社區協會", "與 108 東同案延續，勿重複計數"),
    (2020, "E", "茶山Open Green自然教室（後續擴充）", "文山區",
     "茶山自然教室", "與 108 東同案延續，勿重複計數"),
    # 110 西（初選入圍 14 案）
    (2021, "W", "岩山湧泉生態步道", "士林區", "", "110 初選入圍；111 改造核定 281,000"),
    (2021, "W", "美崙“山‧城”觀景台改造計畫", "士林區", "", "110 初選入圍"),
    (2021, "W", "湖山香香機", "北投區", "", "110 初選入圍"),
    (2021, "W", "厝邊叨，修揪來坐～", "北投區", "", "110 初選入圍"),
    (2021, "W", "城北心焦點", "中山區", "", "110 初選入圍"),
    (2021, "W", "點亮太平町2-共學食物森林", "大同區", "", "110 初選入圍；111 改造核定 252,700"),
    (2021, "W", "看見柴仔寮-社區認養空間活化計畫", "大同區", "", "110 初選入圍；111 改造核定 156,000"),
    (2021, "W", "逆風文創－社區藝術共響聚落", "大同區", "", "110 初選入圍"),
    (2021, "W", "迪化街都市花器", "大同區", "", "110 初選入圍"),
    (2021, "W", "糖廍社協前綠地改造", "萬華區", "", "110 初選入圍"),
    (2021, "W", "安心老的友善社區", "中正區", "", "110 初選入圍"),
    (2021, "W", "OPEN Park ─ IS 農源", "中正區", "", "110 初選入圍；111 改造核定 250,000"),
    (2021, "W", "「古意」「綠意」~愜意綠家園", "中正區", "", "110 初選入圍"),
    (2021, "W", "南昌中式綠洲計畫", "中正區", "", "110 初選入圍"),
    # 111 西（改造核定 4 案）
    (2022, "W", "岩山湧泉生態步道", "士林區", "岩山生態文史志工團", "核定 281,000；士林區芝玉路一段126號附近"),
    (2022, "W", "點亮太平町2-共學食物森林", "大同區", "", "核定 252,700"),
    (2022, "W", "看見柴仔寮-社區認養空間活化計畫", "大同區", "", "核定 156,000"),
    (2022, "W", "OPEN Park ─ IS 農源", "中正區", "", "核定 250,000；110 年度通過複選共 4 案，總核定 939,700"),
]


def main():
    cent = district_centroids()
    rows = []
    for (yr, reg, name, dist, unit, note) in CASES:
        lon = lat = level = ""
        if dist in cent:
            lon, lat = cent[dist]
            level = "district-centroid (approx.)"
        rows.append({"year": yr, "region": reg, "case_name": name, "district": dist,
                     "village": "", "site_address": "", "proposing_unit": unit,
                     "investment_type": "建置;共同規劃", "layer": "3;4",
                     "main_benefit": "adaptation;nature;social", "maintenance_years": "",
                     "verifiability": "中", "lon": lon, "lat": lat, "geo_level": level,
                     "coding_confidence": f"inferred (待複核); {note}",
                     "source_report": f"{yr - 1911}{reg}"})
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    print(f"coded {len(rows)} cases (108-111) -> {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
