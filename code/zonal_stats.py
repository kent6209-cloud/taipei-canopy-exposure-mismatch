# -*- coding: utf-8 -*-
"""Per-township canopy-height stats from native-1.19 m CHMv2 COG tiles (GDAL-only).

Each tile's intersecting township polygons are rasterized (field=row id) into
the tile's native grid window; per-township histograms (256 bins) are
accumulated so mean/median/p90/max and canopy-cover are exact at native res.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
TILES = ROOT / "tiles"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT = ROOT / "taiwan_canopy_stats.json"


def bbox_window(gt, xmin, ymin, xmax, ymax, w, h):
    col0 = max(0, int(math.floor((xmin - gt[0]) / gt[1])))
    row0 = max(0, int(math.floor((gt[3] - ymax) / (-gt[5]))))
    col1 = min(w, int(math.ceil((xmax - gt[0]) / gt[1])))
    row1 = min(h, int(math.ceil((gt[3] - ymin) / (-gt[5]))))
    if col1 <= col0 or row1 <= row0:
        return None
    return col0, row0, col1 - col0, row1 - row0


def window_gt(gt, col0, row0):
    return (gt[0] + col0 * gt[1], gt[1], 0.0, gt[3] + row0 * gt[5], 0.0, gt[5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="test mode: process only first N tiles")
    args = ap.parse_args()

    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    gdf = gdf.to_crs("EPSG:3857").reset_index(drop=True)
    n = len(gdf)
    counts = np.zeros(n, dtype=np.int64)
    hist = np.zeros((n, 256), dtype=np.int64)
    tree = gdf.sindex
    CKPT = ROOT / "_zonal_ckpt.npz"
    start_k = 0
    if CKPT.exists():
        z = np.load(CKPT)
        counts = z["counts"].astype(np.int64)
        hist = z["hist"].astype(np.int64)
        start_k = int(z["k"])

    manifest = json.loads((ROOT / "tile_manifest.json").read_text(encoding="utf-8"))
    tile_files = [TILES / f"{m['quadkey']}.tif" for m in manifest if m["status"] == 200]
    if args.limit:
        tile_files = tile_files[: args.limit]

    mem_drv = gdal.GetDriverByName("MEM")
    vec_drv = ogr.GetDriverByName("Memory")
    t0 = time.time()
    for k, path in enumerate(tile_files, 1):
        if k <= start_k:
            continue
        ds = gdal.Open(str(path))
        gt = ds.GetGeoTransform()
        w, h = ds.RasterXSize, ds.RasterYSize
        xmin = gt[0]
        xmax = gt[0] + w * gt[1]
        ymax = gt[3]
        ymin = gt[3] + h * gt[5]
        cand = list(tree.intersection((xmin, ymin, xmax, ymax)))
        if not cand:
            ds = None
            continue
        xs = gdf.geometry.iloc[cand].total_bounds
        l = max(xs[0], xmin); r = min(xs[2], xmax)
        bt = max(xs[1], ymin); tp = min(xs[3], ymax)
        win = bbox_window(gt, l, bt, r, tp, w, h)
        if win is None:
            ds = None
            continue
        col0, row0, ww, hh = win
        chm = ds.GetRasterBand(1).ReadAsArray(col0, row0, ww, hh)

        mem = mem_drv.Create("", ww, hh, 1, gdal.GDT_UInt16)
        mem.SetGeoTransform(window_gt(gt, col0, row0))
        mem.SetProjection(ds.GetProjection())
        mb = mem.GetRasterBand(1)
        mb.Fill(0)
        src = vec_drv.CreateDataSource("tmp")
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjection())
        layer = src.CreateLayer("t", srs=srs, geom_type=ogr.wkbMultiPolygon)
        fdef = layer.GetLayerDefn()
        fid = ogr.FieldDefn("id", ogr.OFTInteger)
        layer.CreateField(fid)
        for i in cand:
            geom = gdf.geometry.iloc[i]
            ogr_geom = ogr.CreateGeometryFromWkb(geom.wkb)
            f = ogr.Feature(fdef)
            f.SetField("id", int(i) + 1)  # 1..n ; 0 = background (ocean)
            f.SetGeometry(ogr_geom)
            layer.CreateFeature(f)
            f = None
        gdal.RasterizeLayer(mem, [1], layer, options=["ATTRIBUTE=id"])
        ids = mb.ReadAsArray()
        src = None
        mem = None
        ds = None

        valid = ids > 0
        if not valid.any():
            continue
        key = (ids.astype(np.int32) * 256 + chm.astype(np.int32)).ravel()
        flat = np.bincount(key, minlength=(n + 1) * 256)
        for idx in range(1, n + 1):  # id 1..n = townships; id 0 = ocean
            seg = flat[idx * 256:(idx + 1) * 256]
            tot = int(seg.sum())
            if tot:
                counts[idx - 1] += tot
                hist[idx - 1] += seg
        if k % 10 == 0 or k == len(tile_files):
            np.savez(CKPT, counts=counts, hist=hist, k=k)
            print(f"[{k}/{len(tile_files)}] elapsed { (time.time()-t0)/60:.1f} min", flush=True)

    out_rows = []
    for idx in range(n):
        tot = int(counts[idx])
        canopy = int(hist[idx, 1:].sum())
        cover = 100.0 * canopy / tot if tot else 0.0
        base = {"縣市": gdf["COUNTYNAME"].iloc[idx], "鄉鎮": gdf["TOWNNAME"].iloc[idx]}
        if canopy == 0:
            out_rows.append({**base, "平均樹高": None, "中位數樹高": None, "p90": None,
                             "最大樹高": None, "樹冠覆蓋率": 0.0, "像元數": 0})
            continue
        vals = np.repeat(np.arange(1, 256), hist[idx, 1:])
        out_rows.append({**base, "平均樹高": round(float(vals.mean()), 4),
                         "中位數樹高": int(np.median(vals)), "p90": int(np.percentile(vals, 90)),
                         "最大樹高": int(vals.max()), "樹冠覆蓋率": round(cover, 4),
                         "像元數": tot})
    out_rows.sort(key=lambda r: (r["縣市"], r["鄉鎮"]))
    OUT.write_text(json.dumps(out_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if CKPT.exists():
        CKPT.unlink()
    print(f"wrote {OUT} ({len(out_rows)} townships) in {time.time()-t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())