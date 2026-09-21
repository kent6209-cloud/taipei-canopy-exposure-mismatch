# -*- coding: utf-8 -*-
"""WP4/WP5: multi-benefit climate-capital allocation - scenario prototype.

Allocates an equal capital budget (a fixed number of 1-ha cells) under three
decision rules and reports the resulting multi-ledger outcomes:

  Scenario A  carbon-first   : invest where existing canopy (carbon proxy) is highest
  Scenario B  demand-first   : invest where population is high and SAI is low
  Scenario C  balanced       : normalised blend of A and B

Capital is modelled as adding up to DELTA_M of canopy height to the selected
cells; SAI is then recomputed (500 m window) to measure the population-weighted
accessibility gain.  This is a DECISION-SUPPORT PROTOTYPE, not a calibrated
cost-benefit model - stated explicitly in the output.

Output: wp4_scenario_simulator.json
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
OUT = ROOT / "wp4_scenario_simulator.json"
N_UNITS = 500          # number of 1-ha cells invested (equal budget across scenarios)
DELTA_M = 3.0          # canopy height added per invested cell (m)
CANOPY_CAP_M = 30.0    # planting ceiling (set above observed forest height so no saturation)


def build():
    bounds = w2.master_grid()
    chm, gt = w2.warp(w2.CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, w2.CHM_NODATA)
    dem, _ = w2.warp(w2.DEM, bounds, gdal.GRA_Bilinear, gdal.GDT_Float32, w2.DEM_NODATA)
    pop, _ = w2.warp(w2.POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    green = w2.rasterize_green(bounds, gt)
    trees = w2.tree_density(gt, chm.shape)
    pop = np.where((pop == -9999.0) | ~np.isfinite(pop) | (pop < 0), 0.0, pop)
    valid = np.isfinite(chm) & (chm != w2.CHM_NODATA) & np.isfinite(dem) & (dem != w2.DEM_NODATA)
    green = np.where(np.isfinite(green), green, 0.0)
    return valid, chm, dem, pop, green, trees


def sai(chm, valid, green, trees, cap_c, cap_t, size=11):
    g, _ = w2.window_mean(green, valid, size=size)
    c, _ = w2.window_mean(chm, valid, size=size)
    t, _ = w2.window_mean(trees, valid, size=size)
    return (0.4 * np.clip(g, 0, 1) + 0.4 * np.clip(c / cap_c, 0, 1)
            + 0.2 * np.clip(t / cap_t, 0, 1)) * 100.0


def norm(x):
    lo, hi = np.nanmin(x), np.nanmax(x)
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)


def main():
    valid, chm, dem, pop, green, trees = build()
    c5, _ = w2.window_mean(chm, valid)
    t5, _ = w2.window_mean(trees, valid)
    cap_c, cap_t = w2.cap95(c5), w2.cap95(t5)

    sai0 = np.where(valid, sai(chm, valid, green, trees, cap_c, cap_t), np.nan)

    # priority scores (only inside valid cells)
    A_raw = np.where(valid, chm, np.nan)                                  # carbon-first
    B_raw = np.where(valid, norm(np.where(valid, pop, np.nan))
                     * (1 - norm(np.where(valid, np.nan_to_num(sai0, nan=0.0), np.nan))), np.nan)

    def rank01(x):
        """Percentile rank (0-1) over finite values; NaN -> NaN (BLAS-free)."""
        r = np.full(x.shape, np.nan)
        m = np.isfinite(x)
        v = x[m]
        order = np.argsort(np.argsort(v)).astype(np.float64)
        r[m] = order / max(v.size - 1, 1)
        return r

    A = np.where(valid, norm(A_raw), -np.inf)
    B = np.where(valid, norm(B_raw), -np.inf)
    C = np.where(valid, 0.5 * np.nan_to_num(rank01(A_raw))
                 + 0.5 * np.nan_to_num(rank01(B_raw)), -np.inf)

    scenarios = {"A_carbon_first": A, "B_demand_first": B, "C_balanced": C}
    results = {}
    for name, score in scenarios.items():
        flat = np.where(valid, score, -np.inf).ravel()
        sel = np.argsort(flat)[::-1][:N_UNITS]
        sel = sel[np.isfinite(flat[sel])]
        mask = np.zeros(valid.size, bool)
        mask[sel] = True
        mask = mask.reshape(valid.shape)

        chm_new = chm.copy()
        add = np.minimum(DELTA_M, np.maximum(CANOPY_CAP_M - chm_new, 0.0))
        chm_new[mask] = chm_new[mask] + add[mask]
        sai1 = np.where(valid, sai(chm_new, valid, green, trees, cap_c, cap_t), np.nan)

        z = dem[mask]
        pop_sel = pop[mask]
        carbon_gain = float(add[mask].sum())                   # ΣH-like m·ha (1 ha per cell)
        saiv0 = sai0[valid]; saiv1 = sai1[valid]; popv = pop[valid]
        w0 = float((popv * saiv0).sum() / popv.sum())
        w1 = float((popv * saiv1).sum() / popv.sum())
        results[name] = {
            "cells_invested": int(mask.sum()),
            "carbon_proxy_gain_m_ha": round(carbon_gain, 1),
            "pop_weighted_sai_before": round(w0, 2),
            "pop_weighted_sai_after": round(w1, 2),
            "pop_weighted_sai_gain": round(w1 - w0, 3),
            "beneficiary_pop_units": round(float(pop_sel.sum()), 0),
            "mean_elev_m": round(float(z.mean()), 1) if z.size else None,
            "share_flat_pct": round(100.0 * float((z < 20).mean()), 1) if z.size else None,
            "share_mountain_pct": round(100.0 * float((z >= 100).mean()), 1) if z.size else None,
        }

    payload = {
        "meta": {"grid": "100 m EPSG:3826", "budget_cells_1ha": N_UNITS,
                 "canopy_added_m": DELTA_M, "canopy_cap_m": CANOPY_CAP_M,
                 "type": "decision-support PROTOTYPE / what-if scenario tool "
                         "(NOT a calibrated cost-benefit model)",
                 "note": "carbon gain is a ΣH-like proxy (m·ha), NOT verified carbon credits",
                 "equal_carbon_assumption": "by construction every scenario adds the same "
                 "canopy (+3 m to each selected cell), so the equal carbon gain is a MODEL "
                 "ASSUMPTION, not an empirical finding; differences in accessibility benefit "
                 "reflect the allocation rule, NOT causal effects"},
        "scenarios": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
