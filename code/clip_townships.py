# -*- coding: utf-8 -*-
"""Clip the native CHMv2 COG tiles to each of the 368 townships -> native COGs.

Mask-respecting: the source CHMv2 COGs carry an internal validity mask (0 = no-data).
Pixels are kept only where (a) the township polygon covers the pixel center AND
(b) the source mask is valid.  No-data (masked or outside polygon) = nodata 255.
Values are copied without resampling (source grid, center-of-pixel rasterize).
Per-township histograms (valid pixels only) are saved for the stats aggregation.
"""
import argparse
import json
import math
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from shapely.geometry import box

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
TILES = ROOT / "tiles"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT = ROOT / "townships"
HIST_OUT = ROOT / "_township_hists.pkl"
WORKERS = 4
HALF = 20037508.342789244
RES = 1.1943285669558463


def bbox_window(gt, xmin, ymin, xmax, ymax, w, h):
    col0 = max(0, int(math.floor((xmin - gt[0]) / gt[1])))
    row0 = max(0, int(math.floor((gt[3] - ymax) / (-gt[5]))))
    col1 = min(w, int(math.ceil((xmax - gt[0]) / gt[1])))
    row1 = min(h, int(math.ceil((gt[3] - ymin) / (-gt[5]))))
    if col1 <= col0 or row1 <= row0:
        return None
    return col0, row0, col1 - col0, row1 - row0


def clip_one(args):
    code, cname, tname, wkb, tile_files, suffix = args
    dest = OUT / f"{code}_{cname}_{tname}{suffix}.tif"
    done = False
    if dest.exists():
        done = True
    g = ogr.CreateGeometryFromWkb(wkb)
    minx, maxx, miny, maxy = g.GetEnvelope()
    col0 = int(round((minx + HALF) / RES))
    col1 = int(round((maxx + HALF) / RES))
    row0 = int(round((HALF - maxy) / RES))
    row1 = int(round((HALF - miny) / RES))
    w, h = col1 - col0, row1 - row0
    if w <= 0 or h <= 0:
        return code, "fail:empty window", None

    frame = np.full((h, w), 255, dtype=np.uint8)
    hist = np.zeros(256, dtype=np.int64)
    count = 0
    poly_total = 0
    proj = None
    poly = box(minx, miny, maxx, maxy)
    for tpath in tile_files:
        ds = gdal.Open(str(tpath))
        gt = ds.GetGeoTransform()
        tw, th = ds.RasterXSize, ds.RasterYSize
        tbx = (gt[0], gt[3] + th * gt[5], gt[0] + tw * gt[1], gt[3])
        if not poly.intersects(box(*tbx)):
            ds = None
            continue
        if proj is None:
            proj = ds.GetProjection()
        xs = poly.bounds
        l = max(xs[0], tbx[0]); r = min(xs[2], tbx[2])
        bt = max(xs[1], tbx[1]); tp = min(xs[3], tbx[3])
        win = bbox_window(gt, l, bt, r, tp, tw, th)
        if win is None:
            ds = None
            continue
        c0, r0, ww, hh = win
        band = ds.GetRasterBand(1)
        mband = band.GetMaskBand() if band.GetMaskFlags() & (
            gdal.GMF_PER_DATASET | gdal.GMF_ALPHA | gdal.GMF_NODATA) else None
        gcol0 = int(round((gt[0] + HALF) / RES)) + c0
        grow0 = int(round((HALF - gt[3]) / RES)) + r0
        fc0 = gcol0 - col0
        fr0 = grow0 - row0

        mem = gdal.GetDriverByName("MEM").Create("", ww, 1, 1, gdal.GDT_Byte)
        mem.SetProjection(proj)
        mb = mem.GetRasterBand(1)
        src = ogr.GetDriverByName("Memory").CreateDataSource("t")
        srs = osr.SpatialReference()
        srs.ImportFromWkt(proj)
        layer = src.CreateLayer("t", srs=srs, geom_type=ogr.wkbMultiPolygon)
        fdef = layer.GetLayerDefn()
        f = ogr.Feature(fdef)
        f.SetGeometry(g)
        layer.CreateFeature(f)

        CHUNK = 2048
        for y0 in range(0, hh, CHUNK):
            ch = min(CHUNK, hh - y0)
            vals = band.ReadAsArray(c0, r0 + y0, ww, ch)
            if mband is not None:
                mwin = mband.ReadAsArray(c0, r0 + y0, ww, ch)
                valid = mwin == 255
            else:
                valid = np.ones((ch, ww), dtype=bool)
            mem.SetGeoTransform((gt[0] + c0 * gt[1], gt[1], 0.0,
                                 gt[3] + (r0 + y0) * gt[5], 0.0, gt[5]))
            mb.Fill(0)
            gdal.RasterizeLayer(mem, [1], layer, burn_values=[1])
            pmask = mb.ReadAsArray() > 0
            poly_total += int(pmask.sum())
            ok = valid & pmask
            if not ok.any():
                continue
            # place into frame (bounds-guarded slice)
            r0c = max(0, fr0 + y0)
            r1c = min(h, fr0 + y0 + ch)
            c0c = max(0, fc0)
            c1c = min(w, fc0 + ww)
            if r1c <= r0c or c1c <= c0c:
                continue
            sub = ok[r0c - (fr0 + y0):r1c - (fr0 + y0), c0c - fc0:c1c - fc0]
            vals_sub = vals[r0c - (fr0 + y0):r1c - (fr0 + y0), c0c - fc0:c1c - fc0]
            if sub.any():
                frame[r0c:r1c, c0c:c1c][sub] = vals_sub[sub]
            hist += np.bincount(vals[ok], minlength=256)
            count += int(ok.sum())
        mem = None
        src = None

    if not done:
        tmp = dest.with_suffix(".tmp.tif")
        x0 = -HALF + col0 * RES
        ytop = HALF - row0 * RES
        drv = gdal.GetDriverByName("GTiff")
        tds = drv.Create(str(tmp), w, h, 1, gdal.GDT_Byte,
                         options=["TILED=YES", "COMPRESS=DEFLATE",
                                  "BLOCKXSIZE=512", "BLOCKYSIZE=512"])
        tds.SetGeoTransform((x0, RES, 0.0, ytop, 0.0, -RES))
        tds.SetProjection(proj)
        tb = tds.GetRasterBand(1)
        tb.SetNoDataValue(255)
        tb.WriteArray(frame)
        tds = None
        try:
            gdal.Translate(str(dest), str(tmp), format="COG", creationOptions=[
                "COMPRESS=DEFLATE", "BLOCKSIZE=512",
                "OVERVIEW_RESAMPLING=NEAREST", "NUM_THREADS=ALL_CPUS"])
        finally:
            tmp.unlink(missing_ok=True)
    return code, "ok", (count, hist, poly_total)


def cluster_parts(geom, dist=50000.0):
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    polys = [p for p in polys if p.area > 1e-5 * 1e6]  # > ~0.01 km2
    clusters = []
    for p in polys:
        cp = p.centroid
        hit = [i for i, cl in enumerate(clusters)
               if any(cl[j].centroid.distance(cp) < dist for j in range(len(cl)))]
        if hit:
            base = hit[0]
            for i in hit[1:]:
                clusters[base] += clusters[i]
            clusters[base].append(p)
            clusters = [c for i, c in enumerate(clusters) if i not in hit[1:]]
        else:
            clusters.append([p])
    return [__import__("shapely").ops.unary_union(c) for c in clusters]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=int, default=0, help="only first N townships")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    g3857 = gdf.to_crs("EPSG:3857").reset_index(drop=True)

    manifest = json.loads((ROOT / "tile_manifest.json").read_text(encoding="utf-8"))
    all_tiles = sorted(str(TILES / f"{m['quadkey']}.tif") for m in manifest if m["status"] == 200)

    # precompute per-tile quadkey paths for fast intersect filtering per township
    jobs = []
    for i, r in gdf.iterrows():
        geom = g3857.geometry.iloc[i]
        minx, miny, maxx, maxy = geom.bounds
        if (maxx - minx) > 250000 or (maxy - miny) > 250000:
            clusters = cluster_parts(geom)
            for k, cl in enumerate(clusters):
                jobs.append((r.TOWNCODE, r.COUNTYNAME, r.TOWNNAME, cl.wkb,
                             all_tiles, f"_{k}"))
        else:
            jobs.append((r.TOWNCODE, r.COUNTYNAME, r.TOWNNAME, geom.wkb,
                         all_tiles, ""))
    if args.test:
        jobs = jobs[: args.test]

    results = {}
    t0 = time.time()
    done = 0
    fails = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for code, status, payload in ex.map(clip_one, jobs):
            done += 1
            if status != "ok":
                fails.append((code, status))
                print(f"FAIL {code}: {status}", flush=True)
            else:
                if code in results:
                    r0_, h0_, p0_ = results[code]
                    r1_, h1_, p1_ = payload
                    results[code] = (r0_ + r1_, h0_ + h1_, p0_ + p1_)
                else:
                    results[code] = payload
            if done % 20 == 0 or done == len(jobs):
                print(f"[{done}/{len(jobs)}] {time.time()-t0:.0f}s", flush=True)
    HIST_OUT.write_bytes(pickle.dumps(results))
    print(f"done {len(jobs)} clips, fails={fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())