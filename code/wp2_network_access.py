# -*- coding: utf-8 -*-
"""WP2 robustness: street-network accessibility as an alternative to Euclidean 500 m.

The available Road.shp is a POLYGON road-area coverage (not a topological line
network), so centrelines are derived by rasterising the polygons (20 m grid) and
skeletonising them, then a graph shortest-path (scipy csgraph, 8-neighbour) is
run from green-source road pixels.  Residential 100 m cells are snapped to the
nearest network pixel.  This is an APPROXIMATION of network distance and is
labelled as such.

Output: wp2_network_access.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr
from scipy import sparse
from scipy.sparse import csgraph
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp2_green_accessibility as w2

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
ROAD_SHP = r"E:\GeoAI\8mroadup\Road.shp"
OUT = ROOT / "wp2_network_access.json"
NET_RES = 20.0
GREEN_THRESHOLD = 0.5      # a 20 m cell is a green source if grn_ratio >= 0.5
ACCESS_M = 500.0


def rasterize_layer(bounds, res, shp, attribute=None):
    x0, y0, x1, y1 = bounds
    w = int(round((x1 - x0) / res))
    h = int(round((y1 - y0) / res))
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Float32)
    mem.SetGeoTransform((x0, res, 0.0, y1, 0.0, -res))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(w2.EPSG_METRIC)
    mem.SetProjection(srs.ExportToWkt())
    v = gdal.OpenEx(shp, gdal.OF_VECTOR)
    opts = ["ALL_TOUCHED=TRUE"] + ([f"ATTRIBUTE={attribute}"] if attribute else [])
    if attribute:
        gdal.RasterizeLayer(mem, [1], v.GetLayer(), options=opts)
    else:
        gdal.RasterizeLayer(mem, [1], v.GetLayer(), burn_values=[1], options=opts)
    arr = mem.GetRasterBand(1).ReadAsArray().astype(np.float64)
    mem = None; v = None
    return arr, (x0, res, y1)


def build_graph(sk):
    h, w = sk.shape
    idx = np.full(sk.shape, -1, np.int64)
    idx[sk] = np.arange(int(sk.sum()))
    rows, cols, vals = [], [], []
    for dr, dc, wt in ((-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                       (-1, -1, 1.41421), (-1, 1, 1.41421), (1, -1, 1.41421), (1, 1, 1.41421)):
        a = idx[max(0, dr):h + min(0, dr), max(0, dc):w + min(0, dc)]
        b = idx[max(0, -dr):h + min(0, -dr), max(0, -dc):w + min(0, -dc)]
        ok = (a >= 0) & (b >= 0)
        rows.append(a[ok]); cols.append(b[ok]); vals.append(np.full(int(ok.sum()), wt * NET_RES))
    n = int(sk.sum())
    rows = np.concatenate(rows); cols = np.concatenate(cols); vals = np.concatenate(vals)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n)), idx, n


def main():
    bounds = w2.master_grid()
    roads, (rx0, rres, ry1) = rasterize_layer(bounds, NET_RES, ROAD_SHP)
    green, _ = rasterize_layer(bounds, NET_RES, w2.GREEN_SHP, attribute="grn_ratio")
    road_mask = roads > 0
    sk = skeletonize(road_mask)
    print(f"net grid {road_mask.shape}  road px {int(road_mask.sum()):,}  skeleton px {int(sk.sum()):,}",
          flush=True)

    # residential 100 m cells
    pop, _ = w2.warp(w2.POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    chm, _ = w2.warp(w2.CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, w2.CHM_NODATA)
    pop = np.where((pop == -9999.0) | ~np.isfinite(pop) | (pop < 0), 0.0, pop)
    valid = np.isfinite(chm) & (chm != w2.CHM_NODATA)
    rows, cols = np.where(valid & (pop > 0))
    cx = bounds[0] + w2.GRID_RES * (np.arange(chm.shape[1]) + 0.5)
    cy = bounds[3] - w2.GRID_RES * (np.arange(chm.shape[0]) + 0.5)
    px = cx[cols]; py = cy[rows]
    popv = pop[rows, cols]

    rr, cc = np.where(sk)
    rx = rx0 + (cc + 0.5) * NET_RES
    ry = ry1 - (rr + 0.5) * NET_RES
    # map each 20 m skeleton pixel back to its 100 m analysis cell
    p_col = np.clip(((rx - bounds[0]) / w2.GRID_RES).astype(int), 0, chm.shape[1] - 1)
    p_row = np.clip(((bounds[3] - ry) / w2.GRID_RES).astype(int), 0, chm.shape[0] - 1)

    gr100 = w2.rasterize_green(bounds, (bounds[0], w2.GRID_RES, 0, bounds[3], 0, -w2.GRID_RES))
    gr100 = np.where(np.isfinite(gr100), gr100, 0.0)

    def analyse(cell_mask, label):
        """cell_mask: boolean 100 m grid of source cells."""
        src_cells = cell_mask[p_row, p_col]
        sources = idx[rr[src_cells], cc[src_cells]] if src_cells.any() else np.array([], np.int64)
        dist = csgraph.dijkstra(graph, indices=sources, min_only=True)
        net = snap_d + dist[idx[rr[snap_i], cc[snap_i]]]
        grows, gcols = np.where(cell_mask)
        euc = cKDTree(np.column_stack([cx[gcols], cy[grows]])).query(
            np.column_stack([px, py]), k=1)[0]
        fin = np.isfinite(net)
        net_acc = (net <= ACCESS_M) & fin
        euc_acc = euc <= ACCESS_M
        return {
            "source_cells": int(cell_mask.sum()),
            "network_share_within_500m_pct": round(100.0 * net_acc.mean(), 2),
            "network_median_dist_m": round(float(np.median(net[fin])), 1),
            "euclidean_share_within_500m_pct": round(100.0 * euc_acc.mean(), 2),
            "agreement_rate_pct": round(100.0 * float((net_acc == euc_acc).mean()), 2),
            "spearman_netdist_vs_pop": round(_spearman(net[fin], popv[fin]), 3),
        }

    graph, idx, n = build_graph(sk)
    print(f"graph nodes {n:,}  edges {graph.nnz:,}", flush=True)
    tree = cKDTree(np.column_stack([rx, ry]))
    snap_d, snap_i = tree.query(np.column_stack([px, py]), k=1)

    variants = {
        "any_green_space": analyse(gr100 >= GREEN_THRESHOLD, "green"),
        "canopy_ge_2m": analyse(chm >= 2.0, "canopy"),
    }
    payload = {
        "meta": {"net_res_m": NET_RES, "access_radius_m": ACCESS_M,
                 "green_threshold": GREEN_THRESHOLD, "canopy_source_threshold_m": 2.0,
                 "method": "road-polygon rasterisation -> skeletonisation -> 8-neighbour "
                           "graph Dijkstra from source road pixels (APPROXIMATION)",
                 "n_residential_cells": int(rows.size)},
        "variants": variants,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    print("wrote", OUT)
    return 0


def _spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


if __name__ == "__main__":
    sys.exit(main())
