# -*- coding: utf-8 -*-
"""WP2d：土地利用的制度脈絡檢核（A3 官方山坡地 × 高程帶；A4 使用分區 × 供需象限）。

A3：以內政部《山坡地範圍》（115.05.12 版）交叉檢驗本文「近山＝高程 ≥ 20 m」之界定：
    各高程帶中被劃為山坡地之比例、以及山坡地落在各高程帶之比例。
A4：以臺北市《主要計畫圖》（115.04.09 版，使用分區）對照 WP2 之供需四象限：
    低供給·高需求（赤字）格主要落在何種使用分區，作為治理延伸（RQ3）之空間依據。

輸出：`wp2d_land_context.json`、`wp2d_land_context.csv`、`Paper/figures/figA3_land_context.png`（附錄圖 A-3）

限制：Open Green 案例僅有行政區質心座標（3 案有門牌），故**不做案例落點與分區之精細對照**；
      主要計畫圖未涵蓋非都市計畫區（如保護區以外之山坡地），無分區之格以「未納入計畫」表示。
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
GREEN_SHP = r"E:\SCI\TPC\2025_taipei_100m_grid_classified\taipei_100m_grid_classified.shp"
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
SLOPE = r"E:\SCI\TPC\山坡地範圍修正1150512_1150526\山坡地範圍修正1150512_1150526.shp"
ZONE = r"E:\SCI\TPC\1150409主要計畫圖\主計圖-面.shp"
ZONE_GPKG = ROOT / "_wp2d_zone_3826.gpkg"
RAST = ROOT / "wp2_rasters"
OUT_JSON = ROOT / "wp2d_land_context.json"
OUT_CSV = ROOT / "wp2d_land_context.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "figA3_land_context.png"
EPSG = 3826
GRID_RES = 100.0
DEM_NODATA = -32767.0
BANDS = [("都市平地 0–20 m", 0.0, 20.0), ("丘陵近山 20–100 m", 20.0, 100.0),
         ("淺山 100–300 m", 100.0, 300.0), ("山地 300–600 m", 300.0, 600.0),
         ("中高山 > 600 m", 600.0, 1e9)]
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"


def log(m):
    print(m, file=sys.stderr, flush=True)


def master_grid():
    g = gpd.read_file(GREEN_SHP)
    minx, miny, maxx, maxy = g.total_bounds
    return (np.floor(minx / GRID_RES) * GRID_RES, np.floor(miny / GRID_RES) * GRID_RES,
            np.ceil(maxx / GRID_RES) * GRID_RES, np.ceil(maxy / GRID_RES) * GRID_RES)


def new_raster(bounds, dtype):
    x0, y0, x1, y1 = bounds
    w, h = int(round((x1 - x0) / GRID_RES)), int(round((y1 - y0) / GRID_RES))
    ds = gdal.GetDriverByName("MEM").Create("", w, h, 1, dtype)
    ds.SetGeoTransform((x0, GRID_RES, 0.0, y1, 0.0, -GRID_RES))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).Fill(0)
    return ds


def dem_grid(bounds):
    tmp = ROOT / "_wp2d_dem.tif"
    opts = gdal.WarpOptions(format="GTiff", outputBounds=bounds, dstSRS="EPSG:%d" % EPSG,
                            xRes=GRID_RES, yRes=GRID_RES, resampleAlg=gdal.GRA_Average,
                            outputType=gdal.GDT_Float32, dstNodata=DEM_NODATA,
                            creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
    gdal.Warp(str(tmp), DEM, options=opts)
    ds = gdal.Open(str(tmp))
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform()
    ds = None
    tmp.unlink(missing_ok=True)
    arr[arr == DEM_NODATA] = np.nan
    return arr, gt


def rasterize_vector(bounds, shp, attribute=None, burn=1, enc=None, epsg_in=None, filt=None):
    ds = new_raster(bounds, gdal.GDT_Int32)
    src = gdal.OpenEx(shp, gdal.OF_VECTOR, open_options=["ENCODING=%s" % enc] if enc else [])
    layer = src.GetLayer()
    if epsg_in and src.GetLayer().GetSpatialRef() is None:
        pass
    if filt:
        layer.SetAttributeFilter(filt)
    opts = ["ATTRIBUTE=%s" % attribute] if attribute else []
    gdal.RasterizeLayer(ds, [1], layer, burn_values=[burn], options=opts)
    arr = ds.GetRasterBand(1).ReadAsArray()
    ds, src = None, None
    return arr


def prepare_zone_gpkg():
    if ZONE_GPKG.exists():
        return
    g = gpd.read_file(ZONE, encoding="cp950")
    g = g.set_crs(epsg=EPSG) if g.crs is None else g.to_crs(EPSG)
    g["zid"] = np.arange(1, len(g) + 1)
    g = g.rename(columns={"使用分區": "zone"})
    g[["zid", "zone", "geometry"]].to_file(ZONE_GPKG, driver="GPKG")
    log("prepared {} ({} zoning polygons)".format(ZONE_GPKG.name, len(g)))


def main():
    if "--figure-only" in sys.argv:
        d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        draw_figure(d["A3_slope_validation"], d["A4_zoning"])
        print("figure regenerated from", OUT_JSON.name)
        return 0
    bounds = master_grid()
    dem, gt = dem_grid(bounds)
    valid = np.isfinite(dem)
    log("grid {}x{}, valid cells {}".format(dem.shape[0], dem.shape[1], int(valid.sum())))

    log("[A3] 官方山坡地範圍…")
    sg = gpd.read_file(SLOPE, encoding="utf-8")
    tmp_slope = ROOT / "_wp2d_slope.gpkg"
    sg.to_crs(EPSG)[["geometry"]].to_file(tmp_slope, driver="GPKG")
    slope = rasterize_vector(bounds, str(tmp_slope)) > 0
    sg_area_ha = float(sg.to_crs(EPSG).geometry.area.sum() / 1e4)

    band = np.full(dem.shape, "", dtype=object)
    for name, lo, hi in BANDS:
        band[(dem >= lo) & (dem < hi)] = name
    rows = []
    total_slope = int((slope & valid).sum())
    for name, lo, hi in BANDS:
        m = valid & (band == name)
        n = int(m.sum())
        ns = int((m & slope).sum())
        rows.append({
            "band": name, "n_cells": n, "area_ha": round(n * 0.01, 1),
            "slope_cells": ns, "slope_pct_of_band": round(100.0 * ns / n, 1) if n else 0.0,
            "share_of_all_slope_pct": round(100.0 * ns / total_slope, 1) if total_slope else 0.0,
        })
    a3 = {
        "slope_source": "內政部《山坡地範圍》115.05.12 版（原始 EPSG:3824，點陣化至 100 m 網格）",
        "slope_area_ha_vector": round(sg_area_ha, 1),
        "slope_cells_grid": total_slope,
        "slope_area_ha_grid": round(total_slope * 0.01, 1),
        "by_band": rows,
        "pct_slope_at_or_above_20m": round(
            100.0 * sum(r["slope_cells"] for r in rows if "0–20" not in r["band"]) / total_slope, 1),
        "pct_flat_band_that_is_slope": next(r["slope_pct_of_band"] for r in rows if "0–20" in r["band"]),
        "note": "驗證「近山＝高程 ≥20 m」之界定；平地帶若含少量山坡地，屬地形過渡帶。",
    }

    log("[A4] 使用分區…")
    prepare_zone_gpkg()
    zone = rasterize_vector(bounds, str(ZONE_GPKG), attribute="zid")
    zmap = {}
    for r in gpd.read_file(ZONE_GPKG).itertuples():
        nm = r.zone if isinstance(r.zone, str) and r.zone.strip() else "(未標註使用分區)"
        zmap[int(r.zid)] = nm
    sai, _ = read_raster(RAST / "sai.tif")
    canopy, _ = read_raster(RAST / "canopy_supply.tif")
    pop, _ = read_raster(RAST / "population.tif")
    ok = valid & np.isfinite(sai) & np.isfinite(canopy)
    c_mean, p_mean = np.nanmean(canopy[ok]), np.nanmean(pop[ok])
    deficit = ok & (canopy <= c_mean) & (pop > p_mean)
    resid = ok & (pop > 0)

    names = np.full(len(zmap) + 1, "", dtype=object)
    for zid, nm in zmap.items():
        names[zid] = nm
    zname = names[zone]

    zrows = []
    for nm in sorted(set(zname[ok])):
        m = ok & (zname == nm)
        n = int(m.sum())
        if n == 0:
            continue
        zrows.append({
            "zone": nm, "n_cells": n,
            "mean_sai": round(float(np.nanmean(sai[m])), 1),
            "mean_canopy_m": round(float(np.nanmean(canopy[m])), 2),
            "mean_pop_density": round(float(np.nanmean(pop[m])), 1),
            "deficit_cells": int((m & deficit).sum()),
            "deficit_pct_of_zone": round(100.0 * float((m & deficit).sum()) / n, 1),
            "pct_of_all_deficit": round(100.0 * float((m & deficit).sum()) / float(deficit.sum()), 1),
        })
    zrows.sort(key=lambda r: -r["deficit_cells"])
    no_zone = int((ok & (zname == "")).sum())
    a4 = {
        "zone_source": "臺北市《主要計畫圖》115.04.09 版（使用分區；原始檔無 .prj，依 TM2 座標判定為 EPSG:3826）",
        "quadrant_rule": "supply=canopy<=mean 且 demand=pop>mean（同 §5.4）",
        "n_valid_cells": int(ok.sum()), "n_deficit_cells": int(deficit.sum()),
        "cells_without_zoning": no_zone,
        "top_deficit_zones": zrows[:12],
        "note": ("使用分區依多邊形名稱彙總（同一名稱可能有多個多邊形）。"
                 "Open Green 案例僅有行政區質心座標，故不做案例落點×分區之精細對照。"),
    }

    OUT_JSON.write_text(json.dumps({"A3_slope_validation": a3, "A4_zoning": a4}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    OUT_CSV.write_text("\n".join([",".join(["zone", "n_cells", "mean_sai", "mean_canopy_m",
                                            "mean_pop_density", "deficit_cells", "deficit_pct_of_zone",
                                            "pct_of_all_deficit"])] +
                                 [",".join(str(r[k]) for k in r) for r in zrows]) + "\n",
                        encoding="utf-8-sig")
    draw_figure(a3, a4)
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name)
    return 0


def read_raster(path):
    ds = gdal.Open(str(path))
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    ds = None
    arr[arr == -9999.0] = np.nan
    return arr, None


def draw_figure(a3, a4):
    W, H = 2000, 780
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 36), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 88), "左：各高程帶被劃為山坡地之比例（A3）；右：低供給·高需求赤字格之使用分區組成（A4）",
           font=ImageFont.truetype(FR, 23), fill=(90, 90, 90), anchor="ma")

    box = (140, 210, 900, 650)
    d.line([(box[0], box[1]), (box[0], box[3])], fill=(60, 60, 60), width=2)
    d.line([(box[0], box[3]), (box[2], box[3])], fill=(60, 60, 60), width=2)
    rows = a3["by_band"]
    bw = (box[2] - box[0]) / len(rows)
    for i, r in enumerate(rows):
        h = r["slope_pct_of_band"] / 100.0 * (box[3] - box[1])
        cx = box[0] + i * bw + bw * 0.18
        d.rectangle([cx, box[3] - h, cx + bw * 0.64, box[3]], fill=(46, 125, 50))
        d.text((cx + bw * 0.32, box[3] - h - 8), "{:.0f}%".format(r["slope_pct_of_band"]),
               font=ImageFont.truetype(FB, 20), fill=(30, 90, 35), anchor="mb")
        nm = r["band"].replace(" m", "").replace("–", "-")
        d.text((cx + bw * 0.32, box[3] + 10), nm.split(" ")[0], font=ImageFont.truetype(FR, 18),
               fill=(60, 60, 60), anchor="ma")
        rng = nm.split(" ")[1] if " " in nm else ""
        rng = ">600" if rng == ">" else rng
        d.text((cx + bw * 0.32, box[3] + 34), rng,
               font=ImageFont.truetype(FR, 16), fill=(110, 110, 110), anchor="ma")
    d.text((box[0], box[1] - 34), "(a) 各高程帶中官方山坡地之比例", font=ImageFont.truetype(FB, 24),
           fill=(20, 20, 20), anchor="lm")
    d.text((box[0] - 60, (box[1] + box[3]) / 2), "比例 (%)", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="mm")

    box2 = (1120, 210, 1880, 650)
    d.line([(box2[0], box2[1]), (box2[0], box2[3])], fill=(60, 60, 60), width=2)
    d.line([(box2[0], box2[3]), (box2[2], box2[3])], fill=(60, 60, 60), width=2)
    top = [r for r in a4["top_deficit_zones"] if r["deficit_cells"] > 0][:8]
    bh = (box2[3] - box2[1]) / max(len(top), 1)
    vmax = max(r["pct_of_all_deficit"] for r in top) if top else 1.0
    for i, r in enumerate(top):
        w = r["pct_of_all_deficit"] / vmax * (box2[2] - box2[0] - 180)
        y = box2[1] + i * bh + bh * 0.18
        d.rectangle([box2[0] + 180, y, box2[0] + 180 + w, y + bh * 0.62], fill=(183, 121, 31))
        d.text((box2[0] + 172, y + bh * 0.31), r["zone"], font=ImageFont.truetype(FR, 19),
               fill=(60, 60, 60), anchor="rm")
        d.text((box2[0] + 180 + w + 8, y + bh * 0.31), "{:.1f}%".format(r["pct_of_all_deficit"]),
               font=ImageFont.truetype(FB, 19), fill=(120, 75, 10), anchor="lm")
    d.text((box2[0], box2[1] - 34), "(b) 赤字格（低供給·高需求）之使用分區占比", font=ImageFont.truetype(FB, 24),
           fill=(20, 20, 20), anchor="lm")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


if __name__ == "__main__":
    sys.exit(main())
