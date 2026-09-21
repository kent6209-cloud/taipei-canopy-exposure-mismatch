# -*- coding: utf-8 -*-
"""WP2: spatially-valid inference for the P1 correlations.

The naive Spearman p-values assume independent observations, which is invalid for
~23k spatially autocorrelated 100 m cells.  This script replaces them with:

  - a spatial BLOCK bootstrap 95% CI (resample 5x5-cell = 500 m blocks)
  - a spatial BLOCK permutation p-value (shuffle whole blocks)
  - an effective sample size from the lag-1 spatial autocorrelation

Output: wp2_spatial_inference.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp2_green_accessibility as w2

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "wp2_spatial_inference.json"
BLOCK = 5          # 5 x 100 m = 500 m blocks
NBOOT = 1000
NPERM = 999


def _dot(a, b):
    return float((a * b).sum())


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean(); rb -= rb.mean()
    return _dot(ra, rb) / float(np.sqrt(_dot(ra, ra) * _dot(rb, rb)))


def build():
    bounds = w2.master_grid()
    chm, gt = w2.warp(w2.CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, w2.CHM_NODATA)
    pop, _ = w2.warp(w2.POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    green = w2.rasterize_green(bounds, gt)
    trees = w2.tree_density(gt, chm.shape)
    pop = np.where((pop == -9999.0) | ~np.isfinite(pop) | (pop < 0), 0.0, pop)
    valid = np.isfinite(chm) & (chm != w2.CHM_NODATA)
    green = np.where(np.isfinite(green), green, 0.0)
    g5, _ = w2.window_mean(green, valid); c5, _ = w2.window_mean(chm, valid)
    t5, _ = w2.window_mean(trees, valid)
    sai = (0.4 * np.clip(g5, 0, 1) + 0.4 * np.clip(c5 / w2.cap95(c5), 0, 1)
           + 0.2 * np.clip(t5 / w2.cap95(t5), 0, 1)) * 100.0
    return valid, chm, sai, pop


def lag1_autocorr(mat, valid):
    """Mean of E-W and N-S lag-1 autocorrelation over valid cells."""
    vals = []
    for axis in (0, 1):
        a = np.where(valid, mat, np.nan)
        s1 = np.roll(a, -1, axis=axis); s2 = np.roll(a, 1, axis=axis)
        m = valid & np.isfinite(s1)
        mn = valid & np.isfinite(s2)
        v1 = a[m] - np.nanmean(a[m]); w1 = s1[m] - np.nanmean(s1[m])
        v2 = a[mn] - np.nanmean(a[mn]); w2 = s2[mn] - np.nanmean(s2[mn])
        r1 = _dot(v1, w1) / np.sqrt(_dot(v1, v1) * _dot(w1, w1))
        r2 = _dot(v2, w2) / np.sqrt(_dot(v2, v2) * _dot(w2, w2))
        vals.append((r1 + r2) / 2)
    return float(np.mean(vals))


def infer(x, y, block_id, nboot=NBOOT, nperm=NPERM, seed=7):
    rho = spearman(x, y)
    rng = np.random.default_rng(seed)
    # index groups per block (blocks may have unequal sizes at the edge)
    order = np.argsort(block_id)
    bs = np.unique(block_id)
    idx_by_block = [order[block_id[order] == b] for b in bs]
    nb = len(bs)

    # cell-level block bootstrap (resample whole blocks, pool their cells)
    boot = np.empty(nboot)
    for k in range(nboot):
        pick = rng.integers(0, nb, nb)
        idx = np.concatenate([idx_by_block[i] for i in pick])
        boot[k] = spearman(x[idx], y[idx])
    ci = [round(float(np.percentile(boot, 2.5)), 3),
          round(float(np.percentile(boot, 97.5)), 3)]

    # block-level correlation + block permutation (equal-size units by definition)
    cnt = np.bincount(np.searchsorted(bs, block_id), minlength=nb).astype(float)
    mx = np.bincount(np.searchsorted(bs, block_id), weights=x, minlength=nb) / cnt
    my = np.bincount(np.searchsorted(bs, block_id), weights=y, minlength=nb) / cnt
    rho_block = spearman(mx, my)
    perm = np.empty(nperm)
    for k in range(nperm):
        perm[k] = spearman(mx, my[rng.permutation(nb)])
    p = (np.sum(np.abs(perm) >= abs(rho_block)) + 1) / (nperm + 1)

    return {"rho_cell": round(rho, 3), "block_bootstrap_ci95": ci,
            "n_blocks": int(nb), "rho_block": round(rho_block, 3),
            "block_permutation_p": round(float(p), 4),
            "perm_ci95": [round(float(np.percentile(perm, 2.5)), 3),
                          round(float(np.percentile(perm, 97.5)), 3)]}


def main():
    valid, chm, sai, pop = build()
    rows, cols = np.where(valid & (pop > 0))
    canopy = chm[rows, cols]; sai_v = sai[rows, cols]; popv = pop[rows, cols]
    block_id = (rows // BLOCK) * (10000 + cols.max() // BLOCK + 1) + (cols // BLOCK)

    ac_canopy = lag1_autocorr(chm, valid)
    ac_sai = lag1_autocorr(sai, valid)
    n = int(rows.size)

    def n_eff(r):
        r = max(min(r, 0.999), 0.0)
        return int(round(n * (1 - r) / (1 + r)))

    out = {
        "meta": {"n_residential_cells": n, "block_cells": BLOCK, "block_m": BLOCK * 100,
                 "n_boot": NBOOT, "n_perm": NPERM,
                 "note": "block bootstrap/permutation respect spatial dependence; "
                         "use these INSTEAD of naive p-values"},
        "canopy_vs_pop": {**infer(canopy, popv, block_id),
                          "effective_n": n_eff(ac_canopy)},
        "sai_vs_pop": {**infer(sai_v, popv, block_id),
                       "effective_n": n_eff(ac_sai)},
        "lag1_autocorr": {"canopy": round(ac_canopy, 3), "sai": round(ac_sai, 3)},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("wrote", OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
