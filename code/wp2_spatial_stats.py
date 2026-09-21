# -*- coding: utf-8 -*-
"""WP2-E3: spatial statistics for the P1 mismatch test (Moran's I, LISA, quadrants).

Reuses the 100 m grid of wp2_green_accessibility.py and adds:
  - Global Moran's I (queen contiguity, row-standardised) with 999-permutation p
  - Bivariate Moran's I (supply = canopy vs demand = population)
  - Local Moran's I (LISA) cluster types (HH/LL/HL/LH) at p < 0.05
  - Supply x demand quadrant classification
  - Spearman correlations with p-values
  - GeoTIFF rasters (SAI, canopy, population, mismatch, LISA cluster)

Outputs: wp2_spatial_stats.json + wp2_rasters/*.tif
"""
import json
import sys
from pathlib import Path

import numpy as np
import scipy.stats as st
from osgeo import gdal
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp2_green_accessibility as w2

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "wp2_spatial_stats.json"
RASTER_DIR = ROOT / "wp2_rasters"
NPERM = 999
ALPHA = 0.05


def build_layers():
    bounds = w2.master_grid()
    chm, gt = w2.warp(w2.CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, w2.CHM_NODATA)
    pop, _ = w2.warp(w2.POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    green = w2.rasterize_green(bounds, gt)
    trees = w2.tree_density(gt, chm.shape)
    pop = np.where((pop == -9999.0) | ~np.isfinite(pop) | (pop < 0), 0.0, pop)
    valid = np.isfinite(chm) & (chm != w2.CHM_NODATA)
    green = np.where(np.isfinite(green), green, 0.0)

    green500, _ = w2.window_mean(green, valid)
    canopy500, _ = w2.window_mean(chm, valid)
    tree500, _ = w2.window_mean(trees, valid)
    a_g = np.clip(green500, 0, 1)
    a_c = np.clip(canopy500 / w2.cap95(canopy500), 0, 1)
    a_t = np.clip(tree500 / w2.cap95(tree500), 0, 1)
    sai = (0.4 * a_g + 0.4 * a_c + 0.2 * a_t) * 100.0
    sai = np.where(valid & np.isfinite(sai), sai, np.nan)
    pop_c = np.where(valid, pop, np.nan)
    return bounds, gt, valid, chm, sai, pop_c


def queen_weights(mask):
    """Sparse row-standardised queen contiguity on a 2-D validity mask."""
    h, w = mask.shape
    idx = np.full(mask.shape, -1, np.int64)
    idx[mask] = np.arange(int(mask.sum()))
    rows, cols = [], []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            a = idx[max(0, dr):h + min(0, dr), max(0, dc):w + min(0, dc)]
            b = idx[max(0, -dr):h + min(0, -dr), max(0, -dc):w + min(0, -dc)]
            ok = (a >= 0) & (b >= 0)
            rows.append(a[ok]); cols.append(b[ok])
    rows = np.concatenate(rows); cols = np.concatenate(cols)
    n = int(mask.sum())
    W = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    deg = np.asarray(W.sum(axis=1)).ravel()
    deg[deg == 0] = 1.0
    return sparse.diags(1.0 / deg) @ W, n


def _dot(a, b):
    """Element-wise dot that avoids BLAS (broken LAPACK on this host)."""
    return float((a * b).sum())


def moran(z, W, nperm=NPERM, seed=0):
    n = z.size
    zz = z - z.mean()
    lag = W @ zz
    S0 = float(W.sum())
    denom = _dot(zz, zz)
    I = (n / S0) * _dot(zz, lag) / denom
    rng = np.random.default_rng(seed)
    perm = np.empty(nperm)
    for k in range(nperm):
        zp = rng.permutation(zz)
        perm[k] = (n / S0) * _dot(zp, W @ zp) / denom
    p = (np.sum(np.abs(perm) >= abs(I)) + 1) / (nperm + 1)
    return I, float(p), perm


def lisa(z, W, nperm=NPERM, seed=1):
    n = z.size
    zz = z - z.mean()
    lag = W @ zz
    Ii = zz * lag
    rng = np.random.default_rng(seed)
    ge = np.zeros(n, np.int64)
    for _ in range(nperm):
        zp = rng.permutation(zz)
        ge += (np.abs(zz * (W @ zp)) >= np.abs(Ii)).astype(np.int64)
    p = (ge + 1) / (nperm + 1)
    return Ii, p, zz, lag


def spearman_manual(a, b):
    """Spearman rho with two-sided p (t approximation); avoids scipy/BLAS."""
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean(); rb -= rb.mean()
    rho = _dot(ra, rb) / float(np.sqrt(_dot(ra, ra) * _dot(rb, rb)))
    n = a.size
    if abs(rho) >= 1.0:
        return rho, 0.0, n
    t = rho * np.sqrt((n - 2) / (1 - rho * rho))
    p = 2.0 * st.t.sf(abs(t), n - 2)
    return rho, float(p), n


def bivariate_moran(zx, zy, W, nperm=NPERM, seed=2):
    n = zx.size
    x = (zx - zx.mean()) / zx.std()   # standardise both -> I_B in ~[-1, 1]
    y = (zy - zy.mean()) / zy.std()
    lag = W @ y
    S0 = float(W.sum())
    denom = _dot(x, x)
    I = (n / S0) * _dot(x, lag) / denom
    rng = np.random.default_rng(seed)
    perm = np.empty(nperm)
    for k in range(nperm):
        yp = rng.permutation(y)
        perm[k] = (n / S0) * _dot(x, W @ yp) / denom
    p = (np.sum(np.abs(perm) >= abs(I)) + 1) / (nperm + 1)
    return I, float(p)


def write_raster(arr, gt, path, dtype=gdal.GDT_Float32, nodata=-9999.0):
    a = arr.astype(np.float64).copy()
    a[~np.isfinite(a)] = nodata
    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(str(path), a.shape[1], a.shape[0], 1, dtype,
                    options=["TILED=YES", "COMPRESS=DEFLATE"])
    ds.SetGeoTransform(gt)
    ds.SetProjection(f"EPSG:{w2.EPSG_METRIC}")
    b = ds.GetRasterBand(1)
    b.SetNoDataValue(nodata)
    b.WriteArray(a)
    ds = None


def main():
    bounds, gt, valid, chm, sai, pop = build_layers()
    W, n = queen_weights(valid)
    print(f"valid cells {n:,}  W nnz {W.nnz:,}", flush=True)

    rows, cols = np.where(valid)
    canopy_v = chm[rows, cols]
    sai_v = sai[rows, cols]
    pop_v = pop[rows, cols]

    # --- global Moran's I
    mc = moran(canopy_v, W)
    ms = moran(sai_v, W)
    mismatch = (pop_v - pop_v.mean()) / pop_v.std() - (canopy_v - canopy_v.mean()) / canopy_v.std()
    mm = moran(mismatch, W)
    biv = bivariate_moran(canopy_v, pop_v, W)

    # --- LISA on the mismatch (deficit hotspots)
    Ii, p_i, zz, lag = lisa(mismatch, W)
    sig = p_i < ALPHA
    cluster = np.full(n, 0, np.int8)  # 0 ns, 1 HH, 2 LL, 3 LH, 4 HL
    cluster[sig & (zz > 0) & (lag > 0)] = 1
    cluster[sig & (zz < 0) & (lag < 0)] = 2
    cluster[sig & (zz < 0) & (lag > 0)] = 3
    cluster[sig & (zz > 0) & (lag < 0)] = 4

    # --- quadrants (supply=canopy, demand=population), means as thresholds
    s_hi = canopy_v > canopy_v.mean()
    d_hi = pop_v > pop_v.mean()
    quad = np.zeros(n, np.int8)
    quad[s_hi & d_hi] = 1     # high supply-high demand
    quad[s_hi & ~d_hi] = 2    # high supply-low demand
    quad[~s_hi & d_hi] = 3    # low supply-high demand  <= deficit
    quad[~s_hi & ~d_hi] = 4

    # --- correlations with p-values (residential cells)
    res = pop_v > 0
    r_canopy_pop = spearman_manual(canopy_v[res], pop_v[res])
    r_sai_pop = spearman_manual(sai_v[res], pop_v[res])
    r_canopy_sai = spearman_manual(canopy_v, sai_v)

    payload = {
        "meta": {"grid_res_m": w2.GRID_RES, "n_cells": n, "nperm": NPERM,
                 "weights": "queen contiguity, row-standardised",
                 "alpha": ALPHA},
        "global_moran": {
            "canopy_supply": {"I": round(mc[0], 4), "p": round(mc[1], 4)},
            "sai": {"I": round(ms[0], 4), "p": round(ms[1], 4)},
            "mismatch_deficit": {"I": round(mm[0], 4), "p": round(mm[1], 4)},
            "bivariate_canopy_vs_pop": {"I": round(biv[0], 4), "p": round(biv[1], 4)},
        },
        "lisa_mismatch": {
            "HH": int((cluster == 1).sum()), "LL": int((cluster == 2).sum()),
            "LH": int((cluster == 3).sum()), "HL": int((cluster == 4).sum()),
            "not_significant": int((cluster == 0).sum()),
        },
        "quadrants": {
            "high_supply_high_demand": int((quad == 1).sum()),
            "high_supply_low_demand": int((quad == 2).sum()),
            "low_supply_high_demand": int((quad == 3).sum()),
            "low_supply_low_demand": int((quad == 4).sum()),
        },
        "correlations": {
            "canopy_vs_pop_residential": {"rho": round(r_canopy_pop[0], 4),
                                          "p": r_canopy_pop[1], "n": r_canopy_pop[2]},
            "sai_vs_pop_residential": {"rho": round(r_sai_pop[0], 4),
                                       "p": r_sai_pop[1], "n": r_sai_pop[2]},
            "canopy_vs_sai_all": {"rho": round(r_canopy_sai[0], 4),
                                  "p": r_canopy_sai[1], "n": r_canopy_sai[2]},
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    RASTER_DIR.mkdir(exist_ok=True)
    def full(mat):
        out = np.full(valid.shape, np.nan)
        out[rows, cols] = mat
        return out
    write_raster(full(canopy_v), gt, RASTER_DIR / "canopy_supply.tif")
    write_raster(full(sai_v), gt, RASTER_DIR / "sai.tif")
    write_raster(full(pop_v), gt, RASTER_DIR / "population.tif")
    write_raster(full(mismatch), gt, RASTER_DIR / "mismatch_deficit.tif")
    write_raster(full(cluster.astype(float)), gt, RASTER_DIR / "lisa_cluster.tif")

    print(json.dumps(payload["global_moran"], ensure_ascii=False, indent=1))
    print("LISA", payload["lisa_mismatch"])
    print("quadrants", payload["quadrants"])
    print("corr", {k: (v["rho"], round(v["p"], 4)) for k, v in payload["correlations"].items()})
    print("wrote", OUT, "and", RASTER_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
