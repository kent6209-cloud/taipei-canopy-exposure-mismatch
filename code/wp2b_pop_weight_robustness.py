# -*- coding: utf-8 -*-
"""WP2b：需求側權重穩健性檢核（WorldPop 模型密度 vs 民政局里級戶籍人口）。

背景：WP2 的人口加權僅用 WorldPop 相對密度（`wp2_rasters/population.tif`）。
本腳本改以民政局「各里人口數」（`data_civil/`，2026-08）為權重來源，建三種權重：

  W1 = WorldPop 相對密度（基線）
  W2 = 里級戶籍總量 × WorldPop 之里內配置（權威總量、模型化的里內分布）
  W3 = 里級戶籍總量 × 里內均勻（僅對有效格；不依賴 WorldPop）

對每種權重計算：人口加權 SAI、人口加權樹冠、SAI×權重與樹冠×權重的 Spearman，
以及「落在低供給·高需求赤字格之人口占比」（門檻＝全域平均，同 §5.4 四象限定義）。

輸出：
  wp2b_pop_weight.json
  data_civil/pop_weight_robustness.csv
  Paper/figures/fig12_pop_weight.png（圖 5-5）

限制：戶籍人口 ≠ 常住／日夜間活動人口；里界為 115 年版（456 里，與人口檔 1:1 對齊）。
"""
import json
import pathlib
import sys
from collections import defaultdict

import geopandas as gpd
import numpy as np
from osgeo import gdal, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()

FR = r"C:\Windows\Fonts\msjh.ttc"
FB = r"C:\Windows\Fonts\msjhbd.ttc"

ROOT = pathlib.Path(__file__).resolve().parent
RASTER_DIR = ROOT / "wp2_rasters"
VILLAGE_SHP = r"E:\SCI\TPC\臺北市里界圖_20260623\G97_A_CAVLGE_P.shp"   # 臺北市政府都市發展局（與區界 G97_A_CADIST_P 同系列）
POP_CSV = ROOT / "data_civil" / "taipei_village_pop_monthly.csv"
TMP_GPKG = ROOT / "_wp2b_village.gpkg"
OUT_JSON = ROOT / "wp2b_pop_weight.json"
OUT_CSV = ROOT / "data_civil" / "pop_weight_robustness.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "fig12_pop_weight.png"
EPSG = 3826
NODATA = -9999.0
# 里名異體字：「糖廍里」在人口檔為 U+5ECD（廍）、在里界圖為 U+8500（蔀）
VILLAGE_ALIAS = {("萬華區", "糖蔀里"): ("萬華區", "糖廍里")}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def read_raster(name):
    ds = gdal.Open(str(RASTER_DIR / name))
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform()
    ds = None
    arr[arr == NODATA] = np.nan
    return arr, gt


def latest_village_pop():
    """回傳最新月份 {(區, 里): (人口, 戶數)} 與該月份。"""
    lines = POP_CSV.read_text(encoding="utf-8-sig").splitlines()
    rows = [l.split(",") for l in lines[1:] if l]
    latest = max((int(r[0]), int(r[1])) for r in rows)
    out = {}
    for r in rows:
        if (int(r[0]), int(r[1])) == latest:
            out[(r[2], r[3])] = (int(r[4]), int(r[5]))  # households, pop_total
    return out, latest


def rasterize_villages(gt, shape):
    """以 vill_id 值寫入網格（格里點在多邊形內）。回傳 id 陣列、村里 GeoDataFrame 與對名結果。"""
    log("[1/5] 讀取里界…")
    g = gpd.read_file(VILLAGE_SHP, encoding="utf-8")
    g = g[g["TNAME"].astype(str).str.contains("區")].to_crs(EPSG).reset_index(drop=True)
    pops, latest = latest_village_pop()
    keys = [(VILLAGE_ALIAS.get((t, v), (t, v))) for t, v in zip(g["TNAME"], g["VILNAME"] if "VILNAME" in g else g["VNAME"])]
    g["pop"] = [pops.get(k, (0, 0))[1] for k in keys]
    missing = [k for k in keys if k not in pops]
    g["vill_id"] = np.arange(1, len(g) + 1)
    log("      里數={} 對名成功={} 未匹配={}".format(len(g), len(g) - len(missing), missing))
    log("[2/5] 輸出暫存 GPKG 並向量化…")
    g[["vill_id", "pop", "geometry"]].to_file(TMP_GPKG, driver="GPKG")
    drv = gdal.GetDriverByName("GTiff")
    tmp = ROOT / "_wp2b_village_id.tif"
    ds = drv.Create(str(tmp), shape[1], shape[0], 1, gdal.GDT_Int32,
                    options=["TILED=YES", "COMPRESS=DEFLATE"])
    ds.SetGeoTransform(gt)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).Fill(0)
    v = gdal.OpenEx(str(TMP_GPKG), gdal.OF_VECTOR)
    gdal.RasterizeLayer(ds, [1], v.GetLayer(), options=["ATTRIBUTE=vill_id"])
    ids = ds.GetRasterBand(1).ReadAsArray().astype(np.int32)
    ds, v = None, None
    tmp.unlink(missing_ok=True)
    log("      網格內村里數={}".format(len(set(np.unique(ids)) - {0})))
    return ids, g, missing, latest


def spearman(a, b):
    """ordinal-rank Spearman（閉式；本機禁用 scipy.stats）。"""
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


def weighted_mean(values, weights):
    return float((values * weights).sum() / weights.sum())


def build_weights(ids, g, valid, worldpop):
    """三種權重（總量皆對齊官方戶籍人口；未匹配村里者不計）。"""
    tot = {int(r.vill_id): float(r.pop) for r in g.itertuples()}
    w1 = np.where(valid & (worldpop > 0), worldpop, 0.0)
    w2 = np.zeros_like(w1)
    w3 = np.zeros_like(w1)
    fallback = 0
    for vid, total in tot.items():
        cell = (ids == vid) & valid
        if not cell.any() or total <= 0:
            continue
        inner = cell & (worldpop > 0)
        if inner.any():
            sub = worldpop[inner]
            w2[inner] = total * sub / sub.sum()
        else:
            fallback += 1
            sub = cell.ravel()
            n = int(cell.sum())
            w3[cell] = total / n
            w2[cell] = total / n
        w3[cell] = total / int(cell.sum())
    return {"W1_worldpop": w1, "W2_village_x_worldpop": w2, "W3_village_uniform": w3}, fallback


def quadrants(canopy, pop, valid):
    """§5.4 四象限：門檻＝有效格之平均；赤字＝低供給·高需求。"""
    c_mean, p_mean = np.nanmean(canopy[valid]), np.nanmean(pop[valid])
    deficit = valid & (np.nan_to_num(canopy, nan=np.inf) <= c_mean) & (pop > p_mean)
    return deficit, c_mean, p_mean


def main():
    log("[0/5] 讀取 WP2 網格（SAI／樹冠／WorldPop）…")
    sai, gt = read_raster("sai.tif")
    canopy, _ = read_raster("canopy_supply.tif")
    worldpop, _ = read_raster("population.tif")
    valid = np.isfinite(sai) & np.isfinite(canopy)
    log("      網格 {0[0]}x{0[1]}，有效格 {1}".format(sai.shape, int(valid.sum())))

    ids, g, missing, latest = rasterize_villages(gt, sai.shape)
    matched = float(np.sum(g["pop"]))
    in_grid = set(np.unique(ids)) - {0}
    log("[3/5] 建立三種權重…")
    weights, fallback = build_weights(ids, g, valid, worldpop)
    deficit, c_mean, p_mean = quadrants(canopy, worldpop, valid)

    resid = valid & (worldpop > 0)
    res = {
        "meta": {
            "grid": "100 m EPSG:3826 (same grid as wp2_rasters)",
            "n_valid_cells": int(valid.sum()),
            "n_residential_cells_worldpop": int(resid.sum()),
            "village_month": {"year": latest[0], "month": latest[1]},
            "n_villages": int(len(g)), "n_villages_in_grid": len(in_grid),
            "villages_missing_pop": missing, "villages_unmatched_names": len(missing),
            "official_pop_total": matched,
            "weight_sources": {
                "W1_worldpop": "WorldPop-derived relative density (baseline, wp2)",
                "W2_village_x_worldpop": "official village totals x WorldPop intra-village pattern",
                "W3_village_uniform": "official village totals spread uniformly over valid cells",
            },
            "caveat": "戶籍人口 ≠ 常住/日夜間活動人口；村里界為 115 年版。",
            "deficit_rule": "supply=canopy<=mean 且 demand=pop>mean（同 §5.4 四象限）",
        },
        "baseline_reproduction": {
            "sai_area_weighted": round(float(np.nanmean(sai[resid])), 2),
            "sai_pop_weighted": round(weighted_mean(sai[resid], worldpop[resid]), 2),
            "canopy_area_weighted_m": round(float(np.nanmean(canopy[resid])), 2),
            "canopy_pop_weighted_m": round(weighted_mean(canopy[resid], worldpop[resid]), 2),
            "spearman_sai_vs_pop": round(spearman(sai[resid], worldpop[resid]), 3),
            "spearman_canopy_vs_pop": round(spearman(canopy[resid], worldpop[resid]), 3),
        },
        "by_weight": {},
        "fallback_villages": fallback,
    }

    rows = [["weight", "pop_total_in_cells", "area_weighted_SAI", "pop_weighted_SAI",
             "pop_weighted_canopy_m", "spearman_SAI_vs_pop", "spearman_canopy_vs_pop",
             "pop_share_in_deficit_pct"]]
    for name, w in weights.items():
        m = w > 0
        if not m.any():
            continue
        sai_a = float(np.nanmean(sai[m]))
        sai_p = weighted_mean(sai[m], w[m])
        can_p = weighted_mean(canopy[m], w[m])
        rho_s = spearman(sai[m], w[m])
        rho_c = spearman(canopy[m], w[m])
        def_share = float(w[deficit].sum() / w.sum() * 100.0)
        res["by_weight"][name] = {
            "n_cells": int(m.sum()), "pop_total": round(float(w.sum()), 1),
            "area_weighted_SAI": round(sai_a, 2), "pop_weighted_SAI": round(sai_p, 2),
            "gap_area_minus_pop": round(sai_a - sai_p, 2),
            "pop_weighted_canopy_m": round(can_p, 3),
            "spearman_SAI_vs_pop": round(rho_s, 3),
            "spearman_canopy_vs_pop": round(rho_c, 3),
            "pop_share_in_deficit_pct": round(def_share, 2),
        }
        rows.append([name, round(float(w.sum()), 1), round(sai_a, 2), round(sai_p, 2),
                     round(can_p, 3), round(rho_s, 3), round(rho_c, 3), round(def_share, 2)])

    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_CSV.write_text("\n".join(",".join(map(str, r)) for r in rows) + "\n", encoding="utf-8-sig")
    log("[4/5] 繪圖…")
    make_figure(res, g, ids, worldpop, weights, latest)
    log("[5/5] 完成")
    print(json.dumps(res["by_weight"], ensure_ascii=False, indent=1))
    print("baseline:", json.dumps(res["baseline_reproduction"], ensure_ascii=False))
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name)
    return 0


def _axes(d, box, yticks, fmt="{:.0f}", ylabel=""):
    """畫出座標軸、水平格線與 y 刻度。"""
    x0, y0, x1, y1 = box
    f = ImageFont.truetype(FR, 20)
    for v in yticks:
        yy = y1 - (v - yticks[0]) / (yticks[-1] - yticks[0]) * (y1 - y0)
        d.line([(x0, yy), (x1, yy)], fill=(226, 232, 240), width=1)
        d.text((x0 - 10, yy), fmt.format(v), font=f, fill=(70, 70, 70), anchor="rm")
    d.line([(x0, y0), (x0, y1)], fill=(60, 60, 60), width=2)
    d.line([(x0, y1), (x1, y1)], fill=(60, 60, 60), width=2)
    if ylabel:
        d.text((x0 - 62, (y0 + y1) / 2), ylabel, font=ImageFont.truetype(FR, 21),
               fill=(40, 40, 40), anchor="mm")


def _vpos(v, box, vmin, vmax):
    x0, y0, x1, y1 = box
    return y1 - (v - vmin) / (vmax - vmin) * (y1 - y0)


def make_figure(res, g, ids, worldpop, weights, latest):
    names = [n for n in res["by_weight"]]
    short = {"W1_worldpop": "W1\nWorldPop\n(基線)",
             "W2_village_x_worldpop": "W2\n里總量\n×WorldPop 配置",
             "W3_village_uniform": "W3\n里總量\n×里內均勻"}
    W, H = 2280, 780
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    gap, pad_l, pad_r = 70, 110, 60
    pw = (W - pad_l - pad_r - 2 * gap) // 3
    ytop, ybot = 205, H - 140
    title = "".format(
        latest[0], latest[1], len(g))
    d.text((W / 2, 44), title, font=ImageFont.truetype(FB, 40), fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 96), "同一 SAI 網格、同一里級總量，僅抽換需求側權重來源；方向與量級皆不變",
           font=ImageFont.truetype(FR, 24), fill=(90, 90, 90), anchor="ma")

    # (a) area- vs population-weighted SAI
    box = (pad_l, ytop, pad_l + pw, ybot)
    _axes(d, box, [0, 10, 20, 30, 40, 50])
    d.text((box[0] + 8, box[1] + 16), "SAI（0–100）", font=ImageFont.truetype(FR, 21), fill=(120, 120, 120), anchor="la")
    area = res["by_weight"][names[0]]["area_weighted_SAI"]
    d.rectangle([box[0] + 30, _vpos(area, box, 0, 50), box[0] + 30 + 70, box[3]],
                fill=(201, 214, 227))
    d.text((box[0] + 65, (box[3] + _vpos(area, box, 0, 50)) / 2), "面積\n加權", font=ImageFont.truetype(FR, 20),
           fill=(60, 60, 60), anchor="mm")
    f20, f22 = ImageFont.truetype(FR, 20), ImageFont.truetype(FB, 22)
    for i, n in enumerate(names):
        cx = box[0] + 150 + i * 150
        val = res["by_weight"][n]["pop_weighted_SAI"]
        top = _vpos(val, box, 0, 50)
        d.rectangle([cx, top, cx + 90, box[3]], fill=(43, 108, 176))
        d.text((cx + 45, top - 16), "{:.1f}".format(val), font=f22, fill=(30, 60, 110), anchor="mb")
        d.text((cx + 45, box[3] + 12), short[n], font=f20, fill=(60, 60, 60), anchor="ma")
    _panel_label(d, box, "(a) 面積加權 vs 人口加權 SAI")

    # (b) population share in deficit cells
    x0 = pad_l + pw + gap
    box = (x0, ytop, x0 + pw, ybot)
    _axes(d, box, [0, 20, 40, 60, 80, 100])
    d.text((box[0] + 8, box[1] - 14), "人口占比（%）", font=ImageFont.truetype(FR, 21), fill=(120, 120, 120), anchor="la")
    for i, n in enumerate(names):
        v = res["by_weight"][n]["pop_share_in_deficit_pct"]
        cx = box[0] + 60 + i * 190
        d.rectangle([cx, _vpos(v, box, 0, 100), cx + 110, box[3]], fill=(183, 121, 31))
        d.text((cx + 55, _vpos(v, box, 0, 100) - 16), "{:.1f}%".format(v), font=f22,
               fill=(120, 75, 10), anchor="mb")
        d.text((cx + 55, box[3] + 12), short[n], font=f20, fill=(60, 60, 60), anchor="ma")
    _panel_label(d, box, "(b) 落在低供給·高需求赤字格之人口占比")

    # (c) village-level agreement of the two weight sources
    x0 = pad_l + 2 * (pw + gap)
    box = (x0 + 70, ytop, x0 + pw, ybot)
    dens, wp = [], []
    for rid in np.unique(ids):
        if rid == 0:
            continue
        cell = ids == rid
        area_km2 = float(cell.sum()) * 0.01
        w = worldpop[cell]
        wp_sum = float(np.nansum(w[w > 0]))
        off = float(g.loc[g["vill_id"] == rid, "pop"].iloc[0])
        if area_km2 <= 0 or wp_sum <= 0 or off <= 0:
            continue
        dens.append(off / area_km2)
        wp.append(wp_sum / area_km2)
    dens, wp = np.array(dens), np.array(wp)
    rho = spearman(wp, dens)
    lo = float(min(dens.min(), wp.min()))
    hi = float(max(dens.max(), wp.max()))
    l0, l1 = np.log10(lo) - 0.1, np.log10(hi) + 0.1

    def px(v):
        return box[0] + (np.log10(v) - l0) / (l1 - l0) * (box[2] - box[0])

    def py(v):
        return box[3] - (np.log10(v) - l0) / (l1 - l0) * (box[3] - box[1])

    for t in range(int(np.ceil(l0)), int(np.floor(l1)) + 1):
        d.line([(box[0], py(10 ** t)), (box[2], py(10 ** t))], fill=(226, 232, 240), width=1)
        d.text((box[0] - 10, py(10 ** t)), "{:,}".format(10 ** t), font=ImageFont.truetype(FR, 19),
               fill=(70, 70, 70), anchor="rm")
        d.line([(px(10 ** t), box[1]), (px(10 ** t), box[3])], fill=(240, 244, 248), width=1)
        d.text((px(10 ** t), box[3] + 8), "{:,}".format(10 ** t), font=ImageFont.truetype(FR, 19),
               fill=(70, 70, 70), anchor="ma")
    d.line([(box[0], box[1]), (box[0], box[3])], fill=(60, 60, 60), width=2)
    d.line([(box[0], box[3]), (box[2], box[3])], fill=(60, 60, 60), width=2)
    d.line([(px(lo), py(lo)), (px(hi), py(hi))], fill=(229, 62, 62), width=3)
    for a, b in zip(wp, dens):
        x, y = px(a), py(b)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(74, 85, 104))
    d.text(((box[0] + box[2]) / 2, box[3] + 42), "WorldPop 相對密度（人/km²）",
           font=ImageFont.truetype(FR, 21), fill=(40, 40, 40), anchor="ma")
    d.text((box[0] - 92, (box[1] + box[3]) / 2), "戶籍人口密度（人/km²）",
           font=ImageFont.truetype(FR, 21), fill=(40, 40, 40), anchor="mm")
    d.text((box[2] - 8, box[1] + 16), "1:1", font=ImageFont.truetype(FB, 21), fill=(200, 40, 40), anchor="ra")
    _panel_label(d, box, "(c) 里級兩權重來源之一致性（ρ = {:.2f}, n = {}）".format(rho, len(dens)))

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)
    return rho


def _panel_label(d, box, text):
    d.text((box[0], box[1] - 40), text, font=ImageFont.truetype(FB, 24), fill=(20, 20, 20), anchor="lm")


if __name__ == "__main__":
    sys.exit(main())
