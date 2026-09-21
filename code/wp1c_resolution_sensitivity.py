# -*- coding: utf-8 -*-
"""WP1c：CHMv2 解析度／網格化敏感度（A7）。

以同一切線（臺北市 12 區多邊形）將 CHMv2 分別重採樣至 **10 / 30 / 100 m**（EPSG:3826、
GRA_Average，與主分析一致），並另以 **原生解析度（1.19 m、EPSG:3857）** 逐區塊統計，
比較「樹冠面積」與「ΣH」隨解析度的變化：

  樹冠面積：10/30/100 m 採「格內平均高 > 0 即整格計入（格面積）」；原生採「像元高 > 0（像元面積）」。
  ΣH：Σ(樹冠高 × 面積)；原生於 EPSG:3857 需乘 cos²(lat) 校正（lat≈24.9–25.2°N）。

輸出：`wp1c_resolution_sensitivity.json`
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
CHM = ROOT / "county" / "臺北市.tif"
TOWN_SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
CUTLINE = ROOT / "_wp1c_taipei_3826.gpkg"
OUT_JSON = ROOT / "wp1c_resolution_sensitivity.json"
NODATA = 255
RESOLUTIONS = [10.0, 30.0, 100.0]
LAT_MEAN = 25.05          # 臺北市平均緯度（cos² 校正用）


def log(m):
    print(m, file=sys.stderr, flush=True)


def cutline():
    if CUTLINE.exists():
        return
    g = gpd.read_file(TOWN_SHP, encoding="utf-8")
    g = g[g["COUNTYNAME"] == "臺北市"].to_crs(3826)
    g[["TOWNNAME", "geometry"]].to_file(CUTLINE, driver="GPKG")
    log("prepared cutline ({} districts)".format(len(g)))


def warp(res, srs, out, algo=gdal.GRA_Average):
    gdal.Warp(str(out), str(CHM), options=gdal.WarpOptions(
        format="GTiff", dstSRS="EPSG:%d" % srs, xRes=res, yRes=res, resampleAlg=algo,
        dstNodata=NODATA, outputType=gdal.GDT_Byte, cutlineDSName=str(CUTLINE),
        cutlineSRS="EPSG:3826", cropToCutline=False, multithread=True,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))


def block_stats(path, res, cos2=1.0, block_rows=2048):
    ds = gdal.Open(str(path))
    band = ds.GetRasterBand(1)
    nrow, ncol = ds.RasterYSize, ds.RasterXSize
    valid = canopy_n = 0
    hsum = 0.0
    for y in range(0, nrow, block_rows):
        rows = min(block_rows, nrow - y)
        a = band.ReadAsArray(0, y, ncol, rows)
        v = a != NODATA
        c = v & (a > 0)
        valid += int(v.sum())
        canopy_n += int(c.sum())
        if c.any():
            hsum += float(a[c].sum())
    ds = None
    px_ha = (res ** 2) * cos2 / 1e4
    return {
        "resolution_m": res, "n_valid_cells": valid, "n_canopy_cells": canopy_n,
        "valid_ha": round(valid * px_ha, 1), "canopy_ha": round(canopy_n * px_ha, 1),
        "cover_pct": round(100.0 * canopy_n / valid, 2) if valid else 0.0,
        "sigmaH_m_ha": round(hsum * px_ha, 1),
        "cos2_correction": cos2,
    }


def main():
    cutline()
    rows = []
    for res in RESOLUTIONS:
        tmp = ROOT / ("_wp1c_%g.tif" % res)
        warp(res, 3826, tmp)
        st = block_stats(tmp, res, 1.0)
        st["crs"] = "EPSG:3826"
        st["sampling"] = "GRA_Average（格內平均高 > 0 即計入）"
        rows.append(st)
        log("{} m: cover {:.2f}% canopy {:.1f} ha SigmaH {:.1f}".format(
            res, st["cover_pct"], st["canopy_ha"], st["sigmaH_m_ha"]))
        tmp.unlink(missing_ok=True)

    # 主分析所用之重採樣法（nearest）：供與表 5.1 對照
    tmp = ROOT / "_wp1c_10nn.tif"
    warp(10.0, 3826, tmp, gdal.GRA_NearestNeighbour)
    st = block_stats(tmp, 10.0, 1.0)
    st["crs"] = "EPSG:3826"
    st["sampling"] = "GRA_NearestNeighbour（主分析採用，與表 5.1 一致）"
    st["canopy_pct_of_10m"] = round(100.0 * st["canopy_ha"] / rows[0]["canopy_ha"], 1)
    st["sigmaH_pct_of_10m"] = round(100.0 * st["sigmaH_m_ha"] / rows[0]["sigmaH_m_ha"], 1)
    rows.append(st)
    log("10 m nearest: cover {:.2f}% canopy {:.1f} ha SigmaH {:.1f}".format(
        st["cover_pct"], st["canopy_ha"], st["sigmaH_m_ha"]))
    tmp.unlink(missing_ok=True)

    tmp = ROOT / "_wp1c_native.tif"
    warp(1.1943, 3857, tmp)
    cos2 = float(np.cos(np.radians(LAT_MEAN)) ** 2)
    st = block_stats(tmp, 1.1943, cos2)
    st["crs"] = "EPSG:3857（經 cos²(lat) 校正）"
    st["sampling"] = "原生像元高 > 0（像元面積）"
    rows.append(st)
    log("native: cover {:.2f}% canopy {:.1f} ha SigmaH {:.1f}".format(
        st["cover_pct"], st["canopy_ha"], st["sigmaH_m_ha"]))
    tmp.unlink(missing_ok=True)

    ref = rows[0]
    for r in rows[1:]:
        r["canopy_pct_of_10m"] = round(100.0 * r["canopy_ha"] / ref["canopy_ha"], 1)
        r["sigmaH_pct_of_10m"] = round(100.0 * r["sigmaH_m_ha"] / ref["sigmaH_m_ha"], 1)

    # 有效域定義之影響：以 DEM∩CHM（主分析用）重算 10 m
    chm10 = ROOT / "_wp1c_10for_dem.tif"
    warp(10.0, 3826, chm10)
    cds = gdal.Open(str(chm10))
    chm_arr = cds.GetRasterBand(1).ReadAsArray()
    cgt = cds.GetGeoTransform()
    rows_n, cols_n = cds.RasterYSize, cds.RasterXSize
    cds = None
    bounds = (cgt[0], cgt[3] - rows_n * 10.0, cgt[0] + cols_n * 10.0, cgt[3])
    dem = ROOT / "_wp1c_dem.tif"
    gdal.Warp(str(dem), r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif", options=gdal.WarpOptions(
        format="GTiff", outputBounds=bounds, dstSRS="EPSG:3826", xRes=10.0, yRes=10.0,
        resampleAlg=gdal.GRA_Average, dstNodata=-32767.0, outputType=gdal.GDT_Float32,
        cutlineDSName=str(CUTLINE), cutlineSRS="EPSG:3826", multithread=True,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))
    dsd = gdal.Open(str(dem))
    dem_arr = dsd.GetRasterBand(1).ReadAsArray().astype(np.float64)
    dsd = None
    both = np.isfinite(dem_arr) & (dem_arr != -32767.0) & (chm_arr != NODATA)
    can = both & (chm_arr > 0)
    px_ha = (10.0 ** 2) / 1e4
    rows.append({
        "resolution_m": 10.0, "crs": "EPSG:3826",
        "sampling": "GRA_Average（格內平均高 > 0 即計入）",
        "mask": "DEM ∩ CHM（主分析用有效域）",
        "n_valid_cells": int(both.sum()), "n_canopy_cells": int(can.sum()),
        "valid_ha": round(float(both.sum()) * px_ha, 1), "canopy_ha": round(float(can.sum()) * px_ha, 1),
        "cover_pct": round(100.0 * float(can.sum()) / float(both.sum()), 2),
        "sigmaH_m_ha": round(float(chm_arr[can].sum()) * px_ha, 1), "cos2_correction": 1.0,
        "canopy_pct_of_10m": round(100.0 * float(can.sum()) / float(ref["n_canopy_cells"]), 1),
        "sigmaH_pct_of_10m": round(float(chm_arr[can].sum()) / (ref["sigmaH_m_ha"] / px_ha) * 100, 1),
    })
    dem.unlink(missing_ok=True)
    chm10.unlink(missing_ok=True)

    out = {
        "meta": {
            "source": str(CHM) + "（CHMv2 原生 1.19 m、EPSG:3857）",
            "cutline": "臺北市 12 區（TOWN_MOI_1140318）",
            "definition": "樹冠＝CHM > 0；ΣH＝Σ(樹冠高 × 面積)，單位 m·ha",
            "note": ("10/30/100 m 為『格內平均高 > 0 即整格計入』之慣例（與表 5.1 一致）；"
                     "原生解析度則以像元為單位。兩者之差反映**門檻效應**（部分樹冠格之整格計入）"
                     "而非真實樹冠變化。"),
        },
        "by_resolution": rows,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print("wrote", OUT_JSON.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
