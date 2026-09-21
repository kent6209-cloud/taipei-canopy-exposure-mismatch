# -*- coding: utf-8 -*-
"""WP3b：碳通量（NPP）資料可用性檢核（附錄 I）。

目的：評估既有的「年 NPP」產品是否足以支持本論文 WP3 之時序／空間通量分析。
來源：`E:\\SCI\\20260704\\dynamic_ndvi_harmonized\\NPP_harm_YYYY_<sensor>_<date>.tif`
      （100 m、EPSG:3826，與本專案主網格相同，27,239 有效格）、
      `E:\\SCI\\new\\output\\modis_spatial_downscale\\modis_npp_YYYY_100m.tif`（MODIS 降尺度）。

檢核項目與結論：
  1. 逐年零值比例與正值平均 → **4 個年度實質無效**（2003／2008／2015／2025）。
  2. 感測器世代之不連續：Landsat（1998–2014）零值約 1–20 %、Sentinel-2（2016–2024）**45–52 %**
     → 表面上的「通量下降」為零值膨脹（覆蓋／遮罩）所致，非真實生產力變化。
  3. 高程帶分布中 > 600 m 帶 NPP 占比為 0 %（大面積遮罩）→ 與樹冠結構分布不符。
  4. MODIS 降尺度產品為**常數柵格**（std ≈ 0）→ 不可用。
  **判定**：現有 NPP 產品不足以支持可辯護的時序或空間通量分析；WP3 之通量延伸維持【待補】，
          本文續以 ΣH（結構）作為供給代理，並嚴格區分 stock 與 flux。

輸出：`wp3b_carbon_flux.json`、`wp3b_carbon_flux.csv`、`Paper/figures/figA4_carbon_flux.png`（附錄圖 A-4）
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
NPP_DIR = Path(r"E:\SCI\20260704\dynamic_ndvi_harmonized")
MODIS_DIR = Path(r"E:\SCI\new\output\modis_spatial_downscale")
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
RAST = ROOT / "wp2_rasters"
OUT_JSON = ROOT / "wp3b_carbon_flux.json"
OUT_CSV = ROOT / "wp3b_carbon_flux.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "figA4_carbon_flux.png"
EPSG, RES, DEM_NODATA, NODATA = 3826, 100.0, -32767.0, -9999.0
BANDS = [("都市平地 0–20 m", 0.0, 20.0), ("丘陵近山 20–100 m", 20.0, 100.0),
         ("淺山 100–300 m", 100.0, 300.0), ("山地 300–600 m", 300.0, 600.0),
         ("中高山 > 600 m", 600.0, 1e9)]
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
SENSOR = re.compile(r"NPP_harm_(\d{4})_(\w+?)_")
UNUSABLE = {2003, 2008, 2015, 2025}


def log(m):
    print(m, file=sys.stderr, flush=True)


def read(path, nodata=NODATA):
    ds = gdal.Open(str(path))
    a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform()
    ds = None
    a[a == nodata] = np.nan
    return a, gt


def dem_bands(gt, shape):
    tmp = ROOT / "_wp3b_dem.tif"
    x0 = gt[0]
    y1 = gt[3]
    opts = gdal.WarpOptions(format="GTiff", outputBounds=(x0, y1 - shape[0] * RES, x0 + shape[1] * RES, y1),
                            dstSRS="EPSG:%d" % EPSG, xRes=RES, yRes=RES, resampleAlg=gdal.GRA_Average,
                            outputType=gdal.GDT_Float32, dstNodata=DEM_NODATA,
                            creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
    gdal.Warp(str(tmp), DEM, options=opts)
    arr, _ = read(tmp, DEM_NODATA)
    tmp.unlink(missing_ok=True)
    band = np.full(arr.shape, "", dtype=object)
    for name, lo, hi in BANDS:
        band[(arr >= lo) & (arr < hi)] = name
    return arr, band


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


def ols_slope(x, y):
    xc, yc = x - x.mean(), y - y.mean()
    return float((xc * yc).sum() / (xc * xc).sum())


def modis_check():
    """MODIS 降尺度產品是否具空間變異。"""
    out = []
    for f in sorted(MODIS_DIR.glob("modis_npp_*_100m.tif")):
        ds = gdal.Open(str(f))
        a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
        ds = None
        a[a == NODATA] = np.nan
        v = a[np.isfinite(a)]
        year = int(f.name.split("_")[2])
        out.append({"year": year, "std": round(float(np.nanstd(v)), 6),
                    "min": round(float(np.nanmin(v)), 3), "max": round(float(np.nanmax(v)), 3)})
    return out


def main():
    sai, gt = read(RAST / "sai.tif")
    canopy, _ = read(RAST / "canopy_supply.tif")
    pop, _ = read(RAST / "population.tif")
    valid = np.isfinite(sai) & np.isfinite(canopy)
    elev, band = dem_bands(gt, sai.shape)
    c_mean, p_mean = np.nanmean(canopy[valid]), np.nanmean(pop[valid])
    deficit = valid & (canopy <= c_mean) & (pop > p_mean)

    rows, stack = [], {}
    for f in sorted(NPP_DIR.glob("NPP_harm_*.tif")):
        m = SENSOR.search(f.name)
        if not m:
            continue
        year, sensor = int(m.group(1)), m.group(2)
        arr, _ = read(f)
        mm = valid & np.isfinite(arr)
        v = arr[mm]
        pos = v[v > 0]
        rows.append({
            "year": year, "sensor": sensor, "era": "Landsat (1998–2014)" if year <= 2014 else "Sentinel-2 (2015–2025)",
            "n_cells": int(mm.sum()),
            "zero_share_pct": round(100.0 * float((v == 0).mean()), 1),
            "mean_positive": round(float(pos.mean()), 0) if pos.size else 0.0,
            "mean_all": round(float(v.mean()), 0),
            "mean_positive_deficit": round(float(arr[mm & deficit][arr[mm & deficit] > 0].mean()), 0)
            if (mm & deficit).any() else 0.0,
            "mean_positive_other": round(float(arr[mm & ~deficit][arr[mm & ~deficit] > 0].mean()), 0)
            if (mm & ~deficit).any() else 0.0,
            "usable": year not in UNUSABLE,
        })
        stack[year] = arr
        log("  {} {} zero%={} mean+={}".format(year, sensor, rows[-1]["zero_share_pct"], rows[-1]["mean_positive"]))
    rows.sort(key=lambda r: r["year"])

    def era_trend(lo, hi):
        sel = [r for r in rows if lo <= r["year"] <= hi and r["usable"] and r["mean_positive"] > 0]
        if len(sel) < 4:
            return None
        x = np.array([r["year"] for r in sel], dtype=np.float64)
        y = np.array([r["mean_positive"] for r in sel], dtype=np.float64)
        s = ols_slope(x, y)
        return {"years": [int(x.min()), int(x.max())], "n_years": len(sel),
                "slope_per_year": round(s, 1), "mean": round(float(y.mean()), 0),
                "pct_of_mean_per_decade": round(100.0 * s * 10 / float(y.mean()), 1)}

    ref_year = 2019
    ref = stack[ref_year]
    mm = valid & np.isfinite(ref)
    refp = mm & (ref > 0)
    by_band, results = [], []
    for name, lo, hi in BANDS:
        sel_p = refp & (band == name)
        sel_a = mm & (band == name)
        n = int(sel_a.sum())
        if n == 0:
            continue
        tot_pos = float(np.nansum(ref[refp]))
        by_band.append({
            "band": name, "n_cells": n,
            "zero_share_pct": round(100.0 * float((ref[sel_a] == 0).mean()), 1),
            "n_positive": int(sel_p.sum()),
            "mean_positive": round(float(np.nanmean(ref[sel_p])), 0) if sel_p.any() else 0.0,
            "share_of_npp_positive_pct": round(100.0 * float(np.nansum(ref[sel_p])) / tot_pos, 1),
            "share_of_canopy_pct": round(100.0 * float(np.nansum(canopy[sel_a & valid])) /
                                         float(np.nansum(canopy[valid])), 1),
            "mean_canopy_m": round(float(np.nanmean(canopy[sel_a & valid])), 2),
        })
    modis = modis_check()

    out = {
        "meta": {
            "npp_source": "CASA × 調和 NDVI 之年 NPP（gC/m²/yr）；來源專案 E:\\SCI\\20260704",
            "grid": "100 m EPSG:3826（與 wp2_rasters 相同）",
            "n_years": len(rows), "years": [rows[0]["year"], rows[-1]["year"]],
            "unusable_years": sorted(UNUSABLE),
            "verdict": ("現有 NPP 產品**不足以**支持可辯護之時序或空間通量分析："
                        "4 個年度實質無效、感測器世代零值比例不連續（Landsat 1–20 % vs Sentinel-2 45–52 %）、"
                        "山地帶大面積遮罩；MODIS 降尺度產品為常數柵格。"
                        "WP3 之通量延伸維持【待補】；本文續以 ΣH（結構）為供給代理，並嚴格區分 stock 與 flux。"),
            "caveats": [
                "NPP 為通量、ΣH 為冠層結構存量代理，兩者不可互換或相加，亦不得換算為碳權。",
                "本檢核不做趨勢之外的推論；趨勢僅在同一感測器世代內計算。",
            ],
        },
        "annual_quality": rows,
        "era_trends": {"landsat": era_trend(1998, 2014), "sentinel2": era_trend(2015, 2025)},
        "modis_downscale_check": {
            "constant_raster": all(m["std"] < 1e-3 for m in modis),
            "detail": modis[:3], "n_files": len(modis),
        },
        "reference_year_2019": {
            "zero_share_pct": round(100.0 * float((ref[mm] == 0).mean()), 1),
            "spearman_npp_vs_canopy": round(spearman(ref[refp], canopy[refp]), 3),
            "spearman_npp_vs_sai": round(spearman(ref[refp], sai[refp]), 3),
            "spearman_npp_vs_pop": round(spearman(ref[refp], pop[refp]), 3),
            "mean_positive_deficit_cells": round(float(np.nanmean(ref[refp & deficit])), 0) if (refp & deficit).any() else 0.0,
            "mean_positive_other_cells": round(float(np.nanmean(ref[refp & ~deficit])), 0) if (refp & ~deficit).any() else 0.0,
        },
        "by_elevation_band_2019": by_band,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ["year", "sensor", "era", "n_cells", "zero_share_pct", "mean_positive", "mean_all",
            "mean_positive_deficit", "mean_positive_other", "usable"]
    OUT_CSV.write_text("\n".join([",".join(keys)] + [",".join(str(r[k]) for k in keys) for r in rows]) + "\n",
                       encoding="utf-8-sig")
    draw_figure(rows, by_band, out)
    print("verdict:", out["meta"]["verdict"][:60])
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name)
    return 0


def draw_figure(rows, by_band, out):
    W, H = 2100, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 36), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 88), "零值膨脹與感測器世代不連續使既有通量產品不足以支持時序或空間分析",
           font=ImageFont.truetype(FR, 24), fill=(90, 90, 90), anchor="ma")

    # (a) zero share by year + mean on positive cells
    box = (180, 220, 1230, 640)
    d.line([(box[0], box[1]), (box[0], box[3])], fill=(60, 60, 60), width=2)
    d.line([(box[0], box[3]), (box[2], box[3])], fill=(60, 60, 60), width=2)
    yrs = [r["year"] for r in rows]
    px = lambda y: box[0] + (y - min(yrs)) / (max(yrs) - min(yrs)) * (box[2] - box[0])
    bw = (box[2] - box[0]) / len(yrs) * 0.7
    for r in rows:
        h = r["zero_share_pct"] / 100.0 * (box[3] - box[1])
        col = (200, 40, 40) if not r["usable"] else ((150, 150, 150) if r["year"] <= 2014 else (183, 121, 31))
        d.rectangle([px(r["year"]) - bw / 2, box[3] - h, px(r["year"]) + bw / 2, box[3]], fill=col)
    for yy in range(min(yrs), max(yrs) + 1, 5):
        d.text((px(yy), box[3] + 10), str(yy), font=ImageFont.truetype(FR, 18), fill=(70, 70, 70), anchor="ma")
    for g in (0, 25, 50, 75, 100):
        gy = box[3] - g / 100.0 * (box[3] - box[1])
        d.text((box[0] - 10, gy), str(g), font=ImageFont.truetype(FR, 18), fill=(70, 70, 70), anchor="rm")
    d.text((box[0] - 72, (box[1] + box[3]) / 2), "零值比例 (%)", font=ImageFont.truetype(FR, 20),
           fill=(40, 40, 40), anchor="mm")
    d.text((box[0], box[1] - 34), "(a) 逐年零值比例（灰＝Landsat 世代、褐＝Sentinel-2、紅＝實質無效年）",
           font=ImageFont.truetype(FB, 23), fill=(20, 20, 20), anchor="lm")

    # (b) reference-year band comparison
    box2 = (1520, 220, 2000, 640)
    d.line([(box2[0], box2[1]), (box2[0], box2[3])], fill=(60, 60, 60), width=2)
    d.line([(box2[0], box2[3]), (box2[2], box2[3])], fill=(60, 60, 60), width=2)
    bw2 = (box2[2] - box2[0]) / len(by_band)
    vmax = 100.0
    for i, r in enumerate(by_band):
        cx = box2[0] + i * bw2
        h1 = r["share_of_npp_positive_pct"] / vmax * (box2[3] - box2[1])
        h2 = r["share_of_canopy_pct"] / vmax * (box2[3] - box2[1])
        d.rectangle([cx + bw2 * 0.10, box2[3] - h1, cx + bw2 * 0.42, box2[3]], fill=(46, 125, 50))
        d.rectangle([cx + bw2 * 0.52, box2[3] - h2, cx + bw2 * 0.84, box2[3]], fill=(43, 108, 176))
        d.text((cx + bw2 * 0.26, box2[3] - h1 - 6), "{:.0f}".format(r["share_of_npp_positive_pct"]),
               font=ImageFont.truetype(FR, 16), fill=(30, 90, 35), anchor="mb")
        d.text((cx + bw2 * 0.68, box2[3] - h2 - 6), "{:.0f}".format(r["share_of_canopy_pct"]),
               font=ImageFont.truetype(FR, 16), fill=(30, 60, 110), anchor="mb")
        d.text((cx + bw2 * 0.47, box2[3] + 10), r["band"].split(" ")[0][:4], font=ImageFont.truetype(FR, 16),
               fill=(60, 60, 60), anchor="ma")
        d.text((cx + bw2 * 0.47, box2[3] + 30), "零 {:.0f}%".format(r["zero_share_pct"]),
               font=ImageFont.truetype(FR, 14), fill=(170, 60, 60), anchor="ma")
    d.rectangle([box2[0] + 6, box2[1] + 6, box2[0] + 20, box2[1] + 20], fill=(46, 125, 50))
    d.text((box2[0] + 26, box2[1] + 13), "NPP 占比（僅正值格）%", font=ImageFont.truetype(FR, 17),
           fill=(60, 60, 60), anchor="lm")
    d.rectangle([box2[0] + 6, box2[1] + 30, box2[0] + 20, box2[1] + 44], fill=(43, 108, 176))
    d.text((box2[0] + 26, box2[1] + 37), "ΣH 占比 %", font=ImageFont.truetype(FR, 17),
           fill=(60, 60, 60), anchor="lm")
    d.text((box2[0], box2[1] - 34), "(b) 2019：各高程帶 NPP 與 ΣH 占比", font=ImageFont.truetype(FB, 23),
           fill=(20, 20, 20), anchor="lm")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


if __name__ == "__main__":
    sys.exit(main())
