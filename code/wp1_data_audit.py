# -*- coding: utf-8 -*-
"""WP1: evidence freeze and audit of the Taipei street-tree inventory.

Reconciles the tree counts that circulate in the project (92,777 / 92,707 /
92,677 / 92,662 / 92,626) into ONE authoritative dataset with explicit
per-record validity flags AND per-tree elevation band, so every downstream
analysis applies its own filter instead of hard-coding a number.

Outputs
-------
taipei_trees_authoritative.csv : cleaned records + flags + elev_m + elev_band
wp1_data_audit.json            : waterfall, checks, variable dictionary
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from osgeo import gdal
from pyproj import Transformer

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
TREE_CSV = Path(r"E:\SCI\TPC\tree\TaipeiTree.csv")
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT_CSV = ROOT / "taipei_trees_authoritative.csv"
OUT_JSON = ROOT / "wp1_data_audit.json"

HEIGHT_MIN, HEIGHT_MAX = 0.0, 60.0
DIAMETER_MIN, DIAMETER_MAX = 0.0, 500.0
DEM_NODATA = -32767.0
EPSG_TWD97 = 3826
BANDS = [("都市平地", 0.0, 20.0), ("丘陵近山", 20.0, 100.0),
         ("淺山", 100.0, 300.0), ("山地", 300.0, 600.0),
         ("中高山", 600.0, 1e9)]

VARIABLES = [
    ("TreeID", "str", "行道樹普查樹籍編號（唯一鍵）"),
    ("Dist", "str", "行政區"),
    ("Region", "str", "路段／綠地別"),
    ("RegionRemark", "str", "路段備註"),
    ("TreeType", "str", "樹種"),
    ("Diameter_cm", "float", "胸徑（公分）"),
    ("TreeHeight_m", "float", "樹高（公尺）"),
    ("SurveyDate", "str", "普查日期"),
    ("TWD97X", "float", "X 座標（EPSG:3826）"),
    ("TWD97Y", "float", "Y 座標（EPSG:3826）"),
    ("elev_m", "float", "DEM 取樣高程（公尺）"),
    ("elev_band", "str", "高程分區"),
    ("height_valid", "bool", f"{HEIGHT_MIN} < 樹高 ≤ {HEIGHT_MAX} m"),
    ("diameter_valid", "bool", f"{DIAMETER_MIN} < 胸徑 ≤ {DIAMETER_MAX} cm"),
    ("within_taipei", "bool", "座標落在臺北市行政區界內（EPSG:3826）"),
    ("analysis_ready", "bool", "上述三項皆為真，可用於空間分析"),
]


def band_of(z):
    for name, lo, hi in BANDS:
        if lo <= z < hi:
            return name
    return ""


def taipei_union():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs(EPSG_TWD97)
    tpe = gdf[gdf["COUNTYNAME"] == "臺北市"]
    return tpe.to_crs(EPSG_TWD97).geometry.union_all()


def main():
    union = taipei_union()
    ds = gdal.Open(DEM)
    dem = ds.GetRasterBand(1).ReadAsArray()
    dgt = ds.GetGeoTransform()
    dh, dw = dem.shape
    to_wgs = Transformer.from_crs(f"EPSG:{EPSG_TWD97}", "EPSG:4326", always_xy=True)

    with open(TREE_CSV, encoding="utf-8-sig", newline="") as fh:
        raw = list(csv.DictReader(fh))
    n = len(raw)

    cols = {k: [] for k in ("tid", "dist", "region", "remark", "species", "d",
                            "h", "sdate", "x", "y")}
    h_ok = np.zeros(n, bool)
    d_ok = np.zeros(n, bool)
    parse_ok = np.zeros(n, bool)
    for i, r in enumerate(raw):
        for k, v in (("tid", "TreeID"), ("dist", "Dist"), ("region", "Region"),
                     ("remark", "RegionRemark"), ("species", "TreeType"),
                     ("d", "Diameter"), ("h", "TreeHeight"),
                     ("sdate", "SurveyDate"), ("x", "TWD97X"), ("y", "TWD97Y")):
            cols[k].append((r.get(v) or "").strip())
        try:
            dv, hv = float(r["Diameter"]), float(r["TreeHeight"])
            float(r["TWD97X"]); float(r["TWD97Y"])
            parse_ok[i] = True
            h_ok[i] = HEIGHT_MIN < hv <= HEIGHT_MAX
            d_ok[i] = DIAMETER_MIN < dv <= DIAMETER_MAX
        except (TypeError, ValueError):
            pass

    xs = np.array([float(v) if v else np.nan for v in cols["x"]])
    ys = np.array([float(v) if v else np.nan for v in cols["y"]])
    in_city = np.zeros(n, bool)
    good = parse_ok & np.isfinite(xs) & np.isfinite(ys)
    in_city[good] = shapely.contains_xy(union, xs[good], ys[good])

    elev = np.full(n, np.nan)
    band = np.array([""] * n, dtype=object)
    glon, glat = to_wgs.transform(xs[good], ys[good])
    gc = ((glon - dgt[0]) / dgt[1]).astype(int)
    gr = ((dgt[3] - glat) / (-dgt[5])).astype(int)
    inside = (gc >= 0) & (gc < dw) & (gr >= 0) & (gr < dh)
    idx = np.where(good)[0][inside]
    vals = dem[gr[inside], gc[inside]].astype(float)
    vals[vals == DEM_NODATA] = np.nan
    elev[idx] = vals
    for i in idx:
        band[i] = band_of(elev[i])
    within_dem = np.zeros(n, bool)
    within_dem[idx] = True

    ready = h_ok & d_ok & in_city

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["TreeID", "Dist", "Region", "RegionRemark", "TreeType",
                     "Diameter_cm", "TreeHeight_m", "SurveyDate", "TWD97X", "TWD97Y",
                     "elev_m", "elev_band", "height_valid", "diameter_valid",
                     "within_taipei", "analysis_ready"])
        for i in range(n):
            ev = "" if np.isnan(elev[i]) else round(float(elev[i]), 1)
            wr.writerow([cols["tid"][i], cols["dist"][i], cols["region"][i],
                         cols["remark"][i], cols["species"][i], cols["d"][i],
                         cols["h"][i], cols["sdate"][i], cols["x"][i], cols["y"][i],
                         ev, band[i], int(h_ok[i]), int(d_ok[i]),
                         int(in_city[i]), int(ready[i])])

    ids = Counter(t for t in cols["tid"] if t)
    dups = sum(1 for v in ids.values() if v > 1)
    sp = Counter(s for s in cols["species"] if s)

    band_ready = Counter(band[i] for i in range(n) if ready[i])
    flat = band_ready.get("都市平地", 0)
    flat_pct = round(100.0 * flat / int(ready.sum()), 2) if ready.sum() else 0.0
    band_ready_scan = Counter(band[i] for i in range(n)
                              if h_ok[i] and within_dem[i])
    scan_total = sum(band_ready_scan.values())
    scan_flat = band_ready_scan.get("都市平地", 0)

    payload = {
        "source": str(TREE_CSV),
        "boundary": SHP,
        "dem": DEM,
        "freeze_note": "evidence freeze 2026-09-19; single authoritative table",
        "waterfall": {
            "raw_rows": n,
            "minus_height_invalid": n - int(h_ok.sum()),
            "height_valid": int(h_ok.sum()),
            "minus_diameter_invalid": int(h_ok.sum()) - int((h_ok & d_ok).sum()),
            "height_and_diameter_valid": int((h_ok & d_ok).sum()),
            "minus_outside_taipei": int((h_ok & d_ok).sum()) - int(ready.sum()),
            "analysis_ready": int(ready.sum()),
        },
        "reconciliation_of_known_counts": {
            "92,777": "原始 CSV 列數（未過濾）",
            "92,707": "0 < 樹高 ≤ 60 m",
            "92,677": "0 < 樹高 ≤ 60 m 且 0 < 胸徑 ≤ 500 cm",
            "92,662": "高程帶掃描規則：0 < 樹高 ≤ 60 m 且落在臺北 DEM 網格範圍（未篩胸徑）",
            "92,626": "本表分析用 analysis_ready：樹高、胸徑有效且落在臺北市界內",
        },
        "checks": {
            "height_min_max": [HEIGHT_MIN, HEIGHT_MAX],
            "diameter_min_max": [DIAMETER_MIN, DIAMETER_MAX],
            "duplicate_tree_ids": dups,
            "species_total": len(sp),
            "species_blank_rows": int(sum(1 for s in cols["species"] if not s)),
            "flat_share_analysis_ready_pct": flat_pct,
            "flat_share_elevscan_rule_pct": round(100.0 * scan_flat / scan_total, 2)
            if scan_total else 0.0,
        },
        "district_counts_raw": dict(sorted(Counter(cols["dist"]).items())),
        "district_counts_analysis_ready": dict(sorted(Counter(
            cols["dist"][i] for i in range(n) if ready[i]).items())),
        "elevation_band_counts_analysis_ready": dict(sorted(band_ready.items())),
        "variables": [{"name": a, "type": b, "definition": c} for a, b, c in VARIABLES],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    w = payload["waterfall"]
    print(f"raw {w['raw_rows']:,} -> -H {w['minus_height_invalid']} -> {w['height_valid']:,}"
          f" -> -D {w['minus_diameter_invalid']} -> {w['height_and_diameter_valid']:,}"
          f" -> -city {w['minus_outside_taipei']} -> ready {w['analysis_ready']:,}")
    print("dup", dups, "species", len(sp), "flat_share_ready",
          flat_pct, "flat_share_scan", payload["checks"]["flat_share_elevscan_rule_pct"])
    print("ready bands:", dict(band_ready))
    print("wrote", OUT_CSV.name, OUT_JSON.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
