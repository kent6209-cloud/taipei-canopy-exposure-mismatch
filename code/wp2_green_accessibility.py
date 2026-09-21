# -*- coding: utf-8 -*-
"""WP2: 500 m everyday-green accessibility (SAI) and its spatial relation to canopy carbon.

Builds a common 100 m grid (EPSG:3826) over Taipei City from
  - CHMv2 canopy height (county/臺北市.tif)      -> canopy density  (ΣH proxy per ha)
  - 5 m DEM                                       -> elevation bands
  - taipei_100m_grid_classified.shp grn_ratio     -> mapped green fraction
  - TaipeiTree.csv                                -> street-tree density
and computes, for every cell, a *Sensibility Accessibility Index* (SAI):
the 500 m neighbourhood supply of (mapped green, canopy, street trees).

SAI is then compared with the canopy-carbon proxy (P1 spatial-mismatch test).
Population weighting is NOT applied (no population layer available) - noted in
the output metadata.

Output: wp2_green_accessibility.json
"""
import csv
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from scipy import ndimage as ndi

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
CHM = str(ROOT / "county" / "臺北市.tif")
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
GREEN_SHP = r"E:\SCI\TPC\2025_taipei_100m_grid_classified\taipei_100m_grid_classified.shp"
DIST_SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
TREE_CSV = ROOT / "taipei_trees_authoritative.csv"   # WP1 single source of truth
POP = r"E:\SCI\WP1\auxiliary\population\annual\pop_taipei_2026.tif"
OUT = ROOT / "wp2_green_accessibility.json"

EPSG_METRIC = 3826
GRID_RES = 100.0
CHM_NODATA = 255
DEM_NODATA = -32767.0
WINDOW = 11                      # 11 x 100 m = 500 m radius each side
BANDS = [("都市平地", 0.0, 20.0), ("丘陵近山", 20.0, 100.0),
         ("淺山", 100.0, 300.0), ("山地", 300.0, 600.0),
         ("中高山", 600.0, 1e9)]
SAI_W_GREEN, SAI_W_CANOPY, SAI_W_TREE = 0.4, 0.4, 0.2


def master_grid():
    g = gpd.read_file(GREEN_SHP)
    minx, miny, maxx, maxy = g.total_bounds
    x0, y0 = np.floor(minx / GRID_RES) * GRID_RES, np.floor(miny / GRID_RES) * GRID_RES
    x1, y1 = np.ceil(maxx / GRID_RES) * GRID_RES, np.ceil(maxy / GRID_RES) * GRID_RES
    return (x0, y0, x1, y1)


def warp(src, bounds, resample, dtype, nodata):
    x0, y0, x1, y1 = bounds
    tmp = ROOT / f"_wp2_{Path(src).stem}.tif"
    opts = gdal.WarpOptions(
        format="GTiff", outputBounds=(x0, y0, x1, y1), dstSRS=f"EPSG:{EPSG_METRIC}",
        xRes=GRID_RES, yRes=GRID_RES, resampleAlg=resample, outputType=dtype,
        dstNodata=nodata, multithread=True,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
    gdal.Warp(str(tmp), src, options=opts)
    ds = gdal.Open(str(tmp))
    arr = ds.GetRasterBand(1).ReadAsArray()
    gt = ds.GetGeoTransform()
    ds = None
    tmp.unlink(missing_ok=True)
    return arr.astype(np.float64), gt


def rasterize_green(bounds, gt):
    x0, y0, x1, y1 = bounds
    w = int(round((x1 - x0) / GRID_RES))
    h = int(round((y1 - y0) / GRID_RES))
    drv = gdal.GetDriverByName("GTiff")
    tmp = ROOT / "_wp2_green.tif"
    ds = drv.Create(str(tmp), w, h, 1, gdal.GDT_Float32,
                    options=["TILED=YES", "COMPRESS=DEFLATE"])
    ds.SetGeoTransform((x0, GRID_RES, 0.0, y1, 0.0, -GRID_RES))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG_METRIC)
    ds.SetProjection(srs.ExportToWkt())
    v = gdal.OpenEx(GREEN_SHP, gdal.OF_VECTOR)
    gdal.RasterizeLayer(ds, [1], v.GetLayer(), options=["ATTRIBUTE=grn_ratio", "ALL_TOUCHED=FALSE"])
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    ds = None
    v = None
    tmp.unlink(missing_ok=True)
    return arr


def tree_density(gt, shape):
    gt_x0, gt_res, _, gt_y0 = gt[0], gt[1], gt[2], gt[3]
    counts = np.zeros(shape, np.float64)
    with open(TREE_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("analysis_ready") != "1":
                continue
            try:
                x = float(row["TWD97X"])
                y = float(row["TWD97Y"])
            except (TypeError, ValueError):
                continue
            col = int((x - gt_x0) / gt_res)
            row_i = int((gt_y0 - y) / gt_res)
            if 0 <= col < shape[1] and 0 <= row_i < shape[0]:
                counts[row_i, col] += 1
    return counts


def window_mean(arr, valid, size=WINDOW):
    a = np.where(valid, arr, 0.0)
    k = float(size * size)
    s = ndi.uniform_filter(a, size=size, mode="constant", cval=0.0) * k
    c = ndi.uniform_filter(valid.astype(np.float64), size=size, mode="constant", cval=0.0) * k
    return np.where(c > 0, s / np.maximum(c, 1e-9), np.nan), c


def cap95(v):
    pos = v[np.isfinite(v) & (v > 0)]
    return float(np.percentile(pos, 95)) if pos.size else 1.0


def pearson(a, b):
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return pearson(ra, rb)


def district_lookup(centroids_xy):
    dist = gpd.read_file(DIST_SHP, encoding="utf-8")
    dist = dist[dist["COUNTYNAME"] == "臺北市"].to_crs(EPSG_METRIC)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(*centroids_xy), crs=EPSG_METRIC)
    joined = gpd.sjoin(pts, dist[["TOWNNAME", "geometry"]], how="left", predicate="within")
    return joined["TOWNNAME"].fillna("未匹配").astype(str).to_numpy()


def main():
    bounds = master_grid()
    chm, gt = warp(CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, CHM_NODATA)
    dem, _ = warp(DEM, bounds, gdal.GRA_Bilinear, gdal.GDT_Float32, DEM_NODATA)
    pop, _ = warp(POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    green = rasterize_green(bounds, gt)
    trees = tree_density(gt, chm.shape)
    shape = chm.shape

    pop = np.where(pop == -9999.0, 0.0, pop)
    pop = np.where(np.isfinite(pop) & (pop > 0), pop, 0.0)
    valid = np.isfinite(dem) & (dem != DEM_NODATA) & np.isfinite(chm) & (chm != CHM_NODATA)
    green = np.where(np.isfinite(green), green, 0.0)

    green500, _ = window_mean(green, valid)
    canopy500, _ = window_mean(chm, valid)
    tree500, _ = window_mean(trees, valid)

    cap_c = cap95(canopy500)
    cap_t = cap95(tree500)
    a_g = np.clip(green500, 0, 1)
    a_c = np.clip(canopy500 / cap_c, 0, 1)
    a_t = np.clip(tree500 / cap_t, 0, 1)
    sai = (SAI_W_GREEN * a_g + SAI_W_CANOPY * a_c + SAI_W_TREE * a_t) * 100.0
    sai = np.where(np.isfinite(sai), sai, np.nan)
    # canopy-independent green supply (decouples SAI from the carbon proxy)
    sai_gt = (0.6 * a_g + 0.4 * a_t) * 100.0
    sai_gt = np.where(np.isfinite(sai_gt), sai_gt, np.nan)

    # district / band aggregation
    rows, cols = np.where(valid)
    xs = gt[0] + (cols + 0.5) * gt[1]
    ys = gt[3] + (rows + 0.5) * gt[5]
    dist = district_lookup((xs, ys))
    band = np.full(len(rows), "", dtype=object)
    zvals = dem[rows, cols]
    for name, lo, hi in BANDS:
        band[(zvals >= lo) & (zvals < hi)] = name

    def agg(key):
        out = {}
        for k in sorted(set(key)):
            m = key == k
            out[k] = {
                "n_cells": int(m.sum()),
                "sai_mean": round(float(np.nanmean(sai[rows[m], cols[m]])), 2),
                "canopy_h_mean_m": round(float(np.nanmean(chm[rows[m], cols[m]])), 2),
                "green_ratio_mean": round(float(np.nanmean(green[rows[m], cols[m]])), 3),
                "tree_per_ha": round(float(np.nanmean(trees[rows[m], cols[m]])), 1),
            }
        return out

    by_band = agg(band)
    cell = np.column_stack([chm[rows, cols], sai[rows, cols], sai_gt[rows, cols], pop[rows, cols]])
    cell = cell[np.isfinite(cell).all(axis=1)]
    res = cell[cell[:, 3] > 0]        # residential cells (demand side)
    pop_sum = float(res[:, 3].sum())
    summary_p1 = {
        # all cells: canopy is a mechanical component of SAI -> interpret with care
        "all_cells": {
            "n": int(cell.shape[0]),
            "pearson_canopy_vs_sai": round(pearson(cell[:, 0], cell[:, 1]), 3),
            "spearman_canopy_vs_sai": round(spearman(cell[:, 0], cell[:, 1]), 3),
            "pearson_canopy_vs_sai_no_canopy": round(pearson(cell[:, 0], cell[:, 2]), 3),
        },
        # demand-oriented test at residential cells (population>0)
        "residential_cells": {
            "n": int(res.shape[0]),
            "pearson_canopy_vs_pop": round(pearson(res[:, 0], res[:, 3]), 3),
            "spearman_canopy_vs_pop": round(spearman(res[:, 0], res[:, 3]), 3),
            "pearson_sai_vs_pop": round(pearson(res[:, 1], res[:, 3]), 3),
            "spearman_sai_vs_pop": round(spearman(res[:, 1], res[:, 3]), 3),
        },
        "population_weighted": {
            "sai_mean": round(pop_sum and float((res[:, 3] * res[:, 1]).sum() / pop_sum), 2),
            "sai_area_weighted": round(float(res[:, 1].mean()), 2),
            "canopy_m_mean": round(pop_sum and float((res[:, 3] * res[:, 0]).sum() / pop_sum), 2),
            "canopy_area_weighted_m": round(float(res[:, 0].mean()), 2),
        },
    }
    if "都市平地" in by_band and "丘陵近山" in by_band:
        summary_p1["band_contrast"] = {
            "sai_flat": by_band["都市平地"]["sai_mean"],
            "sai_near_mountain": by_band["丘陵近山"]["sai_mean"],
            "canopy_flat_m": by_band["都市平地"]["canopy_h_mean_m"],
            "canopy_near_mountain_m": by_band["丘陵近山"]["canopy_h_mean_m"],
        }

    payload = {
        "meta": {
            "grid_res_m": GRID_RES,
            "window_m": WINDOW * GRID_RES,
            "sai_weights": {"green": SAI_W_GREEN, "canopy": SAI_W_CANOPY, "tree": SAI_W_TREE},
            "cap_canopy_m": round(cap_c, 2), "cap_tree_per_ha": round(cap_t, 1),
            "population_source": "WorldPop-derived pop_taipei_2026.tif (relative density)",
            "population_note": "population used as a relative density weight, not an absolute count",
            "valid_cells": int(valid.sum()),
        },
        "p1_test": summary_p1,
        "by_elevation_band": by_band,
        "by_district": agg(dist),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload["p1_test"], ensure_ascii=False, indent=1))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
