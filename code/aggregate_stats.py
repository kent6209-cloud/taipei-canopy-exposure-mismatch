# -*- coding: utf-8 -*-
"""Build taiwan_canopy_stats.json from the mask-respecting per-township histograms.

Definitions (valid pixels = source-mask-valid AND inside township polygon):
  - 像元數: valid pixels (cover denominator)
  - 無資料像元: in-polygon pixels masked as no-data (poly_total - 像元數)
  - 平均/中位數/P90/最大樹高: computed over canopy pixels (height>0)
  - 樹冠覆蓋率: canopy pixels / 像元數 * 100
"""
import json
import pickle
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
PKL = ROOT / "_township_hists.pkl"
OUT = ROOT / "taiwan_canopy_stats.json"


def main():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    code2meta = {r.TOWNCODE: (r.COUNTYNAME, r.TOWNNAME) for _, r in gdf.iterrows()}
    res = pickle.loads(PKL.read_bytes())

    rows = []
    for code, (count, hist, poly_total) in res.items():
        county, town = code2meta[code]
        tot = int(count)
        canopy = int(hist[1:].sum())
        cover = 100.0 * canopy / tot if tot else 0.0
        base = {"縣市": county, "鄉鎮": town, "像元數": tot,
                "無資料像元": int(max(0, poly_total - tot))}
        if canopy == 0:
            rows.append({**base, "平均樹高": None, "中位數樹高": None, "p90": None,
                         "最大樹高": None, "樹冠覆蓋率": 0.0})
            continue
        vals = np.repeat(np.arange(1, 256), hist[1:])
        rows.append({**base, "平均樹高": round(float(vals.mean()), 4),
                     "中位數樹高": int(np.median(vals)),
                     "p90": int(np.percentile(vals, 90)),
                     "最大樹高": int(vals.max()),
                     "樹冠覆蓋率": round(cover, 4)})
    rows.sort(key=lambda r: (r["縣市"], r["鄉鎮"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} townships)")
    return 0


if __name__ == "__main__":
    sys.exit(main())