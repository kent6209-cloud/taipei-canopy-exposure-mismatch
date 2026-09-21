# -*- coding: utf-8 -*-
"""WP2 robustness: SAI sensitivity (radius x weights) and bootstrap confidence intervals.

- Recomputes SAI on the 100 m grid for search radii 300 / 500 / 800 m and for
  several weight sets, and reports the key P1 statistics for each combination.
- Bootstraps the residential Spearman correlations (canopy x pop, SAI x pop) and
  the area- vs population-weighted SAI gap.

Avoids BLAS/LAPACK (broken on this host) by using manual dot products.

Output: wp2_sai_sensitivity.json
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
OUT = ROOT / "wp2_sai_sensitivity.json"
RADII_M = [300, 500, 800]
WEIGHTS = {
    "baseline": (0.4, 0.4, 0.2),
    "equal": (1 / 3, 1 / 3, 1 / 3),
    "canopy_heavy": (0.2, 0.6, 0.2),
    "green_heavy": (0.6, 0.2, 0.2),
    "tree_heavy": (0.2, 0.2, 0.6),
}
NBOOT = 1000


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
    return valid, chm, green, trees, pop


def sai_for(radius_m, weights, valid, chm, green, trees, cap_c, cap_t):
    size = int(round(radius_m / w2.GRID_RES)) * 2 + 1
    g5, _ = w2.window_mean(green, valid, size=size)
    c5, _ = w2.window_mean(chm, valid, size=size)
    t5, _ = w2.window_mean(trees, valid, size=size)
    a_g = np.clip(g5, 0, 1)
    a_c = np.clip(c5 / cap_c, 0, 1)
    a_t = np.clip(t5 / cap_t, 0, 1)
    wg, wc, wt = weights
    s = (wg * a_g + wc * a_c + wt * a_t) * 100.0
    return np.where(valid & np.isfinite(s), s, np.nan)


def main():
    valid, chm, green, trees, pop = build()
    # caps fixed on the 500 m window (reference)
    g5, _ = w2.window_mean(green, valid)
    c5, _ = w2.window_mean(chm, valid)
    t5, _ = w2.window_mean(trees, valid)
    cap_c, cap_t = w2.cap95(c5), w2.cap95(t5)

    rows, cols = np.where(valid)
    canopy = chm[rows, cols]
    popv = pop[rows, cols]
    res = popv > 0

    out = {"meta": {"grid_res_m": w2.GRID_RES, "radii_m": RADII_M,
                    "weight_sets": {k: list(v) for k, v in WEIGHTS.items()},
                    "n_boot": NBOOT, "cap_canopy_m": round(cap_c, 3),
                    "cap_tree_per_ha": round(cap_t, 1)},
           "sensitivity": {}, "bootstrap_ci": {}}

    for radius in RADII_M:
        for name, wts in WEIGHTS.items():
            s = sai_for(radius, wts, valid, chm, green, trees, cap_c, cap_t)
            sv = s[rows, cols]
            ok = np.isfinite(sv)
            # compare like-for-like: area- and population-weighted both on
            # residential cells (pop > 0), matching wp2_green_accessibility.py
            resi = res & ok
            pw = float((popv[resi] * sv[resi]).sum() / popv[resi].sum())
            aw = float(sv[resi].mean())
            rho_sai_pop = spearman(sv[res & ok], popv[res & ok])
            out["sensitivity"][f"r{radius}_{name}"] = {
                "sai_area_weighted": round(aw, 2),
                "sai_pop_weighted": round(pw, 2),
                "gap": round(aw - pw, 2),
                "spearman_sai_vs_pop": round(rho_sai_pop, 3),
            }

    # bootstrap CI at the reference configuration (radius 500, baseline)
    s500 = sai_for(500, WEIGHTS["baseline"], valid, chm, green, trees, cap_c, cap_t)
    sv = s500[rows, cols]
    ok = res & np.isfinite(sv)
    cv, pv, svv = canopy[ok], popv[ok], sv[ok]
    rng = np.random.default_rng(42)
    n = cv.size
    boot_cp = np.empty(NBOOT); boot_sp = np.empty(NBOOT)
    boot_gap = np.empty(NBOOT)
    for k in range(NBOOT):
        idx = rng.integers(0, n, n)
        boot_cp[k] = spearman(cv[idx], pv[idx])
        boot_sp[k] = spearman(svv[idx], pv[idx])
        w = pv[idx]
        boot_gap[k] = float(svv[idx].mean() - (w * svv[idx]).sum() / w.sum())

    def ci(a):
        return [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)]

    out["bootstrap_ci"] = {
        "canopy_vs_pop_residential": {"rho": round(spearman(cv, pv), 3), "ci95": ci(boot_cp)},
        "sai_vs_pop_residential": {"rho": round(spearman(svv, pv), 3), "ci95": ci(boot_sp)},
        "area_minus_pop_weighted_sai": {"gap": round(float(svv.mean() - (pv * svv).sum() / pv.sum()), 2),
                                        "ci95": ci(boot_gap)},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("sensitivity (radius_weights: area/pop/gap/spearman):")
    for k, v in out["sensitivity"].items():
        print(f"  {k:20s} {v['sai_area_weighted']:6.2f} {v['sai_pop_weighted']:6.2f} "
              f"{v['gap']:6.2f} {v['spearman_sai_vs_pop']:+.3f}")
    print("bootstrap CI:", json.dumps(out["bootstrap_ci"], ensure_ascii=False))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
