# -*- coding: utf-8 -*-
"""WP2: direct Source-Demand mismatch layer (reviewer request, v17 item 2).

Adds an explicit mismatch indicator that pairs the supply side (canopy-height carbon proxy,
Sigma-H) directly with the demand side (population), instead of inferring mismatch from
parallel band statistics:

    M_i  = z(Pop_i) - z(SigmaH_i)      (Sigma-H based supply)
    M_i' = z(Pop_i) - z(Canopy_i)      (mean canopy-height based supply, v16 definition)

Sigma-H per 100 m cell is obtained by warping the native CHM with GRA_Sum (sum of canopy
heights over valid sub-pixels), which is proportional to the carbon proxy and, unlike a cell
mean, is weighted by the valid canopy area of the cell.  Global Moran's I (queen contiguity),
bivariate Moran (supply x population) and the agreement between M and M' are reported.

Output: wp2_direct_mismatch.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp2_green_accessibility as w2
import wp2_spatial_stats as ws

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "wp2_direct_mismatch.json"
NPERM = ws.NPERM


def main():
    bounds, gt, valid, chm, sai, pop = ws.build_layers()
    # Sigma-H proxy: sum of canopy heights per cell (proportional to Sigma(h_i * a_i))
    sig_h, _ = w2.warp(w2.CHM, bounds, gdal.GRA_Sum, gdal.GDT_Float32, w2.CHM_NODATA)
    sig_h = np.where(np.isfinite(sig_h) & (sig_h > 0), sig_h, 0.0)

    W, n = ws.queen_weights(valid)
    rows, cols = np.where(valid)
    canopy = chm[rows, cols]
    sh = sig_h[rows, cols]
    popv = pop[rows, cols]

    def z(v):
        return (v - v.mean()) / v.std()

    m_sigh = z(popv) - z(sh)
    m_canopy = z(popv) - z(canopy)

    i_sigh = ws.moran(m_sigh, W)
    i_canopy = ws.moran(m_canopy, W)
    biv_sigh = ws.bivariate_moran(sh, popv, W)
    biv_canopy = ws.bivariate_moran(canopy, popv, W)

    res = popv > 0
    r_agree, _, _ = ws.spearman_manual(m_sigh[res], m_canopy[res])
    rho_sh_pop, _, _ = ws.spearman_manual(sh[res], popv[res])
    rho_canopy_pop, _, _ = ws.spearman_manual(canopy[res], popv[res])

    out = {
        "meta": {"grid_res_m": w2.GRID_RES, "n_cells": int(n), "nperm": NPERM,
                 "weights": "queen contiguity, row-standardised",
                 "sigma_h": "per-cell sum of canopy heights (GRA_Sum of native CHM), "
                            "proportional to Sigma(h_i * a_i)",
                 "note": "M = z(Pop) - z(Supply); M > 0 means demand overload / supply deficit"},
        "mismatch_sigma_h": {"moran_I": round(i_sigh[0], 4), "p": round(i_sigh[1], 4)},
        "mismatch_canopy": {"moran_I": round(i_canopy[0], 4), "p": round(i_canopy[1], 4)},
        "bivariate_sigma_h_vs_pop": {"moran_I": round(biv_sigh[0], 4), "p": round(biv_sigh[1], 4)},
        "bivariate_canopy_vs_pop": {"moran_I": round(biv_canopy[0], 4), "p": round(biv_canopy[1], 4)},
        "residential": {
            "n": int(res.sum()),
            "rho_sigma_h_vs_pop": round(rho_sh_pop, 3),
            "rho_canopy_vs_pop": round(rho_canopy_pop, 3),
            "spearman_between_M_and_Mprime": round(r_agree, 4),
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("wrote", OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
