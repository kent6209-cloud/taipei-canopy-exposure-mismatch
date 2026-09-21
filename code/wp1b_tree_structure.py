# -*- coding: utf-8 -*-
"""WP1b：行道樹結構分解（A6）與區級樹冠結構（A8）。

A6：以臺北市行道樹普查（`taipei_trees_authoritative.csv`）計算
    (a) 主要樹種於各高程帶之組成（前 8 種）
    (b) 胸徑（Diameter_cm）於各高程帶之分佈（中位數、P25、P75）
    (c) 各帶之樹種豐富度
A8：以本專案 CHMv2 管線（10 m・NearestNeighbour＋DEM∩CHM 有效域）重算 12 區之
    樹冠覆蓋率、平均／中位／P90 樹冠高與 ΣH，並附各區行道樹棵數。

輸出：`wp1b_tree_structure.json`、`wp1b_tree_structure.csv`、`Paper/figures/figA5_tree_structure.png`（附錄圖 A-5）

限制：行道樹樹高／胸徑為人工普查值，含目視誤差；`height_valid`／`diameter_valid` 已於 WP1 標記。
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
TREE_CSV = ROOT / "taipei_trees_authoritative.csv"
CHM = ROOT / "county" / "臺北市.tif"
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
TOWN_SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
CUT = ROOT / "_wp1b_taipei_3826.gpkg"
OUT_JSON = ROOT / "wp1b_tree_structure.json"
OUT_CSV = ROOT / "wp1b_tree_structure.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "figA5_tree_structure.png"
BANDS = ["都市平地 0–20 m", "丘陵近山 20–100 m", "淺山 100–300 m", "山地 300–600 m", "中高山 > 600 m"]
BAND_ALIAS = [("都市平地", "都市平地 0–20 m"), ("丘陵近山", "丘陵近山 20–100 m"),
              ("淺山", "淺山 100–300 m"), ("山地", "山地 300–600 m"), ("中高山", "中高山 > 600 m")]


def norm_band(v):
    v = (v or "").strip()
    for k, lab in BAND_ALIAS:
        if v.startswith(k):
            return lab
    return ""
NODATA, DEM_NODATA, RES = 255, -32767.0, 10.0
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
COLORS = [(43, 108, 176), (46, 125, 50), (183, 121, 31), (120, 80, 160), (200, 40, 40),
          (60, 160, 160), (150, 90, 60), (110, 110, 110)]


def log(m):
    print(m, file=sys.stderr, flush=True)


def load_trees():
    rows = []
    with open(TREE_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("analysis_ready") != "1":
                continue
            rows.append(r)
    return rows


def a6(trees):
    species_by_band = defaultdict(Counter)
    dbh_by_band = defaultdict(list)
    for r in trees:
        band = norm_band(r.get("elev_band"))
        sp = (r.get("TreeType") or "").strip() or "(未標示)"
        if band:
            species_by_band[band][sp] += 1
            if r.get("diameter_valid") == "1":
                try:
                    dbh_by_band[band].append(float(r["Diameter_cm"]))
                except (TypeError, ValueError):
                    pass
    total = Counter()
    for c in species_by_band.values():
        total.update(c)
    top8 = [s for s, _ in total.most_common(8)]
    bands = [b for b in BANDS if b in species_by_band]
    table = []
    for b in bands:
        c = species_by_band[b]
        n = sum(c.values())
        row = {"band": b, "n_trees": n, "n_species": len(c),
               "top_species_pct": {s: round(100.0 * c[s] / n, 1) for s in top8}}
        d = np.array(dbh_by_band[b], dtype=np.float64)
        if d.size:
            row.update({"dbh_n": int(d.size), "dbh_median_cm": round(float(np.median(d)), 1),
                        "dbh_p25_cm": round(float(np.percentile(d, 25)), 1),
                        "dbh_p75_cm": round(float(np.percentile(d, 75)), 1),
                        "dbh_mean_cm": round(float(d.mean()), 1)})
        table.append(row)
    return {"top8_species": top8, "by_band": table,
            "overall_species": {s: v for s, v in total.most_common(12)},
            "overall_richness": len(total)}


def a8():
    if not CUT.exists():
        g = gpd.read_file(TOWN_SHP, encoding="utf-8")
        g = g[g["COUNTYNAME"] == "臺北市"].to_crs(3826)
        g[["TOWNNAME", "geometry"]].to_file(CUT, driver="GPKG")
    chm_t = ROOT / "_wp1b_chm10.tif"
    gdal.Warp(str(chm_t), str(CHM), options=gdal.WarpOptions(
        format="GTiff", dstSRS="EPSG:3826", xRes=RES, yRes=RES, resampleAlg=gdal.GRA_NearestNeighbour,
        dstNodata=NODATA, outputType=gdal.GDT_Byte, cutlineDSName=str(CUT), cutlineSRS="EPSG:3826",
        multithread=True, creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))
    ds = gdal.Open(str(chm_t))
    chm = ds.GetRasterBand(1).ReadAsArray()
    gt = ds.GetGeoTransform()
    shape = (ds.RasterYSize, ds.RasterXSize)
    ds = None
    bounds = (gt[0], gt[3] - shape[0] * RES, gt[0] + shape[1] * RES, gt[3])
    dem_t = ROOT / "_wp1b_dem10.tif"
    gdal.Warp(str(dem_t), DEM, options=gdal.WarpOptions(
        format="GTiff", outputBounds=bounds, dstSRS="EPSG:3826", xRes=RES, yRes=RES,
        resampleAlg=gdal.GRA_Average, dstNodata=DEM_NODATA, outputType=gdal.GDT_Float32,
        cutlineDSName=str(CUT), cutlineSRS="EPSG:3826", multithread=True,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))
    ds = gdal.Open(str(dem_t))
    dem = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    ds = None
    valid = (chm != NODATA) & (dem != DEM_NODATA) & np.isfinite(dem)

    out = []
    src = ogr.Open(str(CUT))
    layer = src.GetLayer()
    for feat in layer:
        name = feat.GetField("TOWNNAME")
        mem = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Byte)
        mem.SetGeoTransform(gt)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(3826)
        mem.SetProjection(srs.ExportToWkt())
        mem.GetRasterBand(1).Fill(0)
        drv = ogr.GetDriverByName("MEM").CreateDataSource("m")
        vl = drv.CreateLayer("l", srs)
        vl.CreateFeature(feat.Clone())
        gdal.RasterizeLayer(mem, [1], vl, burn_values=[1], options=["ALL_TOUCHED=FALSE"])
        m = (mem.GetRasterBand(1).ReadAsArray() > 0) & valid
        h = chm[m]
        can = h[h > 0]
        px_ha = (RES ** 2) / 1e4
        out.append({
            "district": name, "n_cells": int(m.sum()), "area_ha": round(float(m.sum()) * px_ha, 1),
            "canopy_ha": round(float(can.size) * px_ha, 1),
            "cover_pct": round(100.0 * can.size / int(m.sum()), 2) if m.any() else 0.0,
            "mean_h_all_m": round(float(h.mean()), 2) if h.size else 0.0,
            "mean_h_canopy_m": round(float(can.mean()), 2) if can.size else 0.0,
            "median_h_canopy_m": round(float(np.median(can)), 1) if can.size else 0.0,
            "p90_h_canopy_m": int(np.percentile(can, 90)) if can.size else 0,
            "sigmaH_m_ha": round(float(can.sum()) * px_ha, 1),
        })
        mem, drv = None, None
    src = None
    chm_t.unlink(missing_ok=True)
    dem_t.unlink(missing_ok=True)
    out.sort(key=lambda r: -r["cover_pct"])
    return out


def draw_figure(a6, a8, trees):
    W, H = 2150, 820
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 36), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 88), "依高程帶之樹種組成（左）、胸徑分佈（中）與 12 區樹冠覆蓋率（右，本專案 CHM 管線重算）",
           font=ImageFont.truetype(FR, 23), fill=(90, 90, 90), anchor="ma")

    # (a) species composition by band
    box = (150, 220, 900, 660)
    d.line([(box[0], box[1]), (box[0], box[3])], fill=(60, 60, 60), width=2)
    d.line([(box[0], box[3]), (box[2], box[3])], fill=(60, 60, 60), width=2)
    bands = a6["by_band"]
    bw = (box[2] - box[0]) / max(len(bands), 1)
    top8 = a6["top8_species"]
    for i, r in enumerate(bands):
        y = box[3]
        for j, sp in enumerate(top8):
            share = r["top_species_pct"].get(sp, 0.0)
            h = share / 100.0 * (box[3] - box[1])
            if h > 0:
                d.rectangle([box[0] + i * bw + bw * 0.18, y - h, box[0] + i * bw + bw * 0.82, y],
                            fill=COLORS[j % len(COLORS)])
                if h > 24:
                    d.text((box[0] + i * bw + bw * 0.5, y - h / 2), "{:.0f}".format(share),
                           font=ImageFont.truetype(FR, 15), fill=(255, 255, 255), anchor="mm")
            y -= h
        d.text((box[0] + i * bw + bw * 0.5, box[3] + 10), r["band"].split(" ")[0][:4],
               font=ImageFont.truetype(FR, 18), fill=(60, 60, 60), anchor="ma")
        d.text((box[0] + i * bw + bw * 0.5, box[3] + 32), "n={:,}".format(r["n_trees"]),
               font=ImageFont.truetype(FR, 15), fill=(110, 110, 110), anchor="ma")
        d.text((box[0] + i * bw + bw * 0.5, box[3] + 52), "{} 種".format(r["n_species"]),
               font=ImageFont.truetype(FR, 15), fill=(110, 110, 110), anchor="ma")
    lx, ly = box[0] + 6, box[1] + 10
    for j, sp in enumerate(top8):
        d.rectangle([lx, ly + j * 24, lx + 18, ly + 16 + j * 24], fill=COLORS[j % len(COLORS)])
        d.text((lx + 26, ly + 8 + j * 24), sp[:6], font=ImageFont.truetype(FR, 16),
               fill=(60, 60, 60), anchor="lm")
    d.text((box[0], box[1] - 34), "(a) 高程帶之樹種組成（前 8 種，%）", font=ImageFont.truetype(FB, 23),
           fill=(20, 20, 20), anchor="lm")

    # (b) DBH median/IQR by band
    box2 = (1020, 220, 1430, 660)
    d.line([(box2[0], box2[1]), (box2[0], box2[3])], fill=(60, 60, 60), width=2)
    d.line([(box2[0], box2[3]), (box2[2], box2[3])], fill=(60, 60, 60), width=2)
    dmax = max([r.get("dbh_p75_cm", 0) for r in bands] + [10]) * 1.15
    for g in range(0, int(dmax) + 1, 20):
        gy = box2[3] - g / dmax * (box2[3] - box2[1])
        d.line([(box2[0], gy), (box2[2], gy)], fill=(238, 241, 245), width=1)
        d.text((box2[0] - 10, gy), str(g), font=ImageFont.truetype(FR, 18), fill=(70, 70, 70), anchor="rm")
    bw2 = (box2[2] - box2[0]) / max(len(bands), 1)
    for i, r in enumerate(bands):
        if "dbh_median_cm" not in r:
            continue
        cx = box2[0] + i * bw2 + bw2 * 0.5
        y25 = box2[3] - r["dbh_p25_cm"] / dmax * (box2[3] - box2[1])
        y75 = box2[3] - r["dbh_p75_cm"] / dmax * (box2[3] - box2[1])
        ym = box2[3] - r["dbh_median_cm"] / dmax * (box2[3] - box2[1])
        d.rectangle([cx - 14, y75, cx + 14, y25], fill=(201, 214, 227), outline=(120, 140, 160))
        d.line([(cx - 18, ym), (cx + 18, ym)], fill=(43, 108, 176), width=4)
        d.text((cx, y75 - 8), "{:.0f}".format(r["dbh_median_cm"]), font=ImageFont.truetype(FB, 17),
               fill=(30, 60, 110), anchor="mb")
        d.text((cx, box2[3] + 10), r["band"].split(" ")[0][:4], font=ImageFont.truetype(FR, 18),
               fill=(60, 60, 60), anchor="ma")
    d.text((box2[0] - 60, (box2[1] + box2[3]) / 2), "胸徑 (cm)", font=ImageFont.truetype(FR, 20),
           fill=(40, 40, 40), anchor="mm")
    d.text((box2[0], box2[1] - 34), "(b) 胸徑中位數與四分位距", font=ImageFont.truetype(FB, 23),
           fill=(20, 20, 20), anchor="lm")

    # (c) district canopy cover
    box3 = (1560, 220, 2060, 660)
    d.line([(box3[0], box3[1]), (box3[0], box3[3])], fill=(60, 60, 60), width=2)
    d.line([(box3[0], box3[3]), (box3[2], box3[3])], fill=(60, 60, 60), width=2)
    rows = sorted(a8, key=lambda r: r["cover_pct"])
    bw3 = (box3[2] - box3[0]) / len(rows)
    for i, r in enumerate(rows):
        h = r["cover_pct"] / 100.0 * (box3[3] - box3[1])
        cx = box3[0] + i * bw3 + bw3 * 0.15
        d.rectangle([cx, box3[3] - h, cx + bw3 * 0.7, box3[3]], fill=(46, 125, 50))
        d.text((cx + bw3 * 0.35, box3[3] - h - 6), "{:.0f}".format(r["cover_pct"]),
               font=ImageFont.truetype(FR, 16), fill=(30, 90, 35), anchor="mb")
        d.text((cx + bw3 * 0.35, box3[3] + 10), r["district"][:2], font=ImageFont.truetype(FR, 17),
               fill=(60, 60, 60), anchor="ma")
    d.text((box3[0], box3[1] - 34), "(c) 12 區樹冠覆蓋率（10 m・NN）", font=ImageFont.truetype(FB, 23),
           fill=(20, 20, 20), anchor="lm")
    d.text((box3[0] - 62, (box3[1] + box3[3]) / 2), "覆蓋率 (%)", font=ImageFont.truetype(FR, 20),
           fill=(40, 40, 40), anchor="mm")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


def main():
    log("[A6] 行道樹結構…")
    trees = load_trees()
    a6res = a6(trees)
    log("  trees {}  species {}".format(len(trees), a6res["overall_richness"]))
    log("[A8] 區級樹冠結構（CHM 10 m NN）…")
    a8res = a8()
    for r in a8res:
        log("  {} cover {:.2f}% mean {:.2f} m SigmaH {:.0f}".format(
            r["district"], r["cover_pct"], r["mean_h_canopy_m"], r["sigmaH_m_ha"]))
    out = {"A6_street_trees": a6res, "A8_district_canopy": a8res,
           "meta": {"tree_source": TREE_CSV.name, "grid": "10 m EPSG:3826・GRA_NearestNeighbour・DEM∩CHM",
                    "note": "行道樹為人工普查值；A8 為本專案 CHM 管線重算（非外部專案數值）。"}}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ["district", "n_cells", "area_ha", "canopy_ha", "cover_pct", "mean_h_all_m",
            "mean_h_canopy_m", "median_h_canopy_m", "p90_h_canopy_m", "sigmaH_m_ha"]
    OUT_CSV.write_text("\n".join([",".join(keys)] + [",".join(str(r[k]) for k in keys) for r in a8res]) + "\n",
                       encoding="utf-8-sig")
    draw_figure(a6res, a8res, trees)
    print("species richness:", a6res["overall_richness"])
    for r in a6res["by_band"]:
        print(r["band"], r["n_trees"], r["n_species"], r.get("dbh_median_cm"))
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
