# -*- coding: utf-8 -*-
"""WP3 (enterprise side): registry of corporate climate/nature projects.

Source: 農業部林業及自然保育署「自然碳匯與生物多樣性專案媒合平臺」(ESG 媒合平臺),
as documented in CSR@天下 (2025-11-07 / 2026-04-17).  These are enterprise-funded
forest/nature projects matched to partner communities.

Key spatial fact for RQ2/P2: all listed projects are located OUTSIDE Taipei City
(mountain / rural counties), i.e. on the "carbon-supply" side, while the Open
Green programmes are inside the city.

Layer coding: "2待查" = may qualify for Layer 2 only if a verified methodology /
additionality applies (the platform notes adoption-forestry does NOT directly
yield carbon credits in the first years); "3" nature/adaptation; "4" social/cultural.

Output: enterprise_climate_projects.csv + wp3_enterprise.json
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_CSV = ROOT / "enterprise_climate_projects.csv"
OUT_JSON = ROOT / "wp3_enterprise.json"

FIELDS = ["year", "enterprise", "project_name", "category", "partner_community",
          "county", "layer", "main_benefit", "area_or_scale", "verifiability",
          "source"]

PROJECTS = [
    (2025, "財團法人中華電信股份有限公司", "竹構未來-桃園復興竹林疏伐暨泰雅部落竹業經營",
     "自然碳匯", "友順竹業（泰雅族卡普部落）、桂竹協會", "桃園市復興區",
     "2待查;3;4", "carbon;nature;social", "33.756 公頃（2026 報導）", "中",
     "CSR@天下 2025-11-07；林業署 ESG 媒合平臺"),
    (2025, "根基營造股份有限公司", "嘉義草山臺灣爺蟬棲地復育（國有林地復育造林）",
     "生物多樣性", "草山社區、新美原民部落", "嘉義縣", "3;4", "nature;social", "", "中",
     "CSR@天下 2025-11-07"),
    (2025, "台塑石化股份有限公司", "在風的最前線，守護麥仔寮-強化雲林縣麥寮鄉橋頭段保安林",
     "自然碳匯", "雲林縣麥寮鄉橋頭及新吉等社區發展協會", "雲林縣麥寮鄉", "3;4",
     "nature;social", "", "中", "CSR@天下 2025-11-07"),
    (2025, "信義房屋股份有限公司", "峰峰相連漾綠意-112年臺東縣金峰鄉金山段國有林地復育造林",
     "自然碳匯", "保證責任臺東縣惠美原住民造林勞動合作社", "臺東縣金峰鄉", "2待查;3;4",
     "carbon;nature;social", "", "中", "CSR@天下 2025-11-07"),
    (2025, "冠德建設股份有限公司", "松羅蘭馨 綠林再造-宜蘭事業區79、80林班-再造林計畫",
     "自然碳匯", "松羅社區、宜蘭大學", "宜蘭縣", "2待查;3;4", "carbon;nature;social",
     "3.70 公頃", "中", "CSR@天下 2025-11-07"),
    (2025, "聯詠科技股份有限公司", "偏鄉學童自然環境教育體驗計畫",
     "生物多樣性", "財團法人荒野保護協會新竹分會", "新竹縣", "4", "social", "", "中",
     "CSR@天下 2025-11-07"),
    (2025, "啟坤科技股份有限公司", "蒸情記憶-阿里山林鐵蒸汽機車數位技術傳承",
     "林業文化", "", "嘉義縣阿里山", "4", "social", "", "中", "CSR@天下 2025-11-07"),
    (2025, "東元電機股份有限公司", "智慧山海•手護未來-山海圳國家綠道智能服務及手作步道合作計畫",
     "山林文化", "社團法人台灣千里步道協會", "臺南市", "4", "social", "", "中",
     "CSR@天下 2025-11-07"),
    (2026, "光林智能（LEOTEK）", "馬祖雌光螢保育（友善光環境生態照明）",
     "生物多樣性", "連江縣政府產業發展處、在地社區", "連江縣（馬祖）", "3;4",
     "nature;social", "", "中", "CSR@天下 2026-04-17"),
    (2026, "華碩電腦股份有限公司", "大雪山穿山甲棲地研究（草生栽培對生態影響）",
     "生物多樣性", "大雪山地區", "臺中市和平區", "3;4", "nature;social", "", "中",
     "CSR@天下 2026-04-17"),
]


def main():
    rows = [dict(zip(FIELDS, p)) for p in PROJECTS]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)

    counties = {}
    for r in rows:
        counties[r["county"]] = counties.get(r["county"], 0) + 1
    payload = {
        "source": "農業部林業及自然保育署 自然碳匯與生物多樣性專案媒合平臺（ESG）",
        "source_note": "CSR@天下 2025-11-07 報導列示 113–114 年媒合成功專案（報導稱累計 25 案、"
                       "22 家企業；平台另有完整清單）",
        "n_projects": len(rows),
        "counties": counties,
        "in_taipei": sum(1 for r in rows if "臺北" in r["county"]),
        "key_finding": "本次可得之企業自然／碳專案全數位於臺北市以外（山林／鄉村），"
                       "與市內 Open Green 形成空間分離",
        "projects": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"projects {len(rows)}  in_taipei {payload['in_taipei']}")
    print("counties:", counties)
    print("wrote", OUT_CSV.name, OUT_JSON.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
