# -*- coding: utf-8 -*-
"""WP1: elevation-stratified canopy-carbon proxy and street-tree allometric biometrics.

Two independent products:

1.  Landscape canopy structure by elevation band (ΣH proxy), read from the
    10 m EPSG:3826 scan produced by taipei_elev_carbon_scan.py.  ΣH is a
    *relative* biomass-structure proxy - absolute forest carbon needs
    allometric calibration and is deliberately NOT reported here.

2.  Street-tree biomass/carbon stock from TaipeiTree.csv, using the
    pantropical allometric equation of Chave et al. (2014):
        AGB_kg = 0.0673 * (rho * D^2 * H)^0.976      (rho g/cm3, D cm, H m)
    with a per-species wood-density lookup, IPCC carbon fraction and a
    below-ground root:shoot expansion.  This is the Layer-2/3 boundary
    evidence for the NMGCI four-ledger model.

Output: wp1_carbon_bands.json
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
AUTH_CSV = ROOT / "taipei_trees_authoritative.csv"   # produced by wp1_data_audit.py
TREE_CSV = Path(r"E:\SCI\TPC\tree\TaipeiTree.csv")   # fallback if audit not run
CANOPY_JSON = ROOT / "taipei_elev_carbon_scan.json"
OUT = ROOT / "wp1_carbon_bands.json"

BANDS = [
    ("都市平地", 0.0, 20.0),
    ("丘陵近山", 20.0, 100.0),
    ("淺山", 100.0, 300.0),
    ("山地", 300.0, 600.0),
    ("中高山", 600.0, 1e9),
]
TREE_HEIGHT_MAX = 60.0
DEM_NODATA = -32767.0

# Chave et al. (2014) coefficients
CHAVE_A = 0.0673
CHAVE_B = 0.976
CARBON_FRACTION = 0.4561          # IPCC default
ROOT_SHOOT_RATIO = 0.26           # below-ground / above-ground
CO2_PER_C = 44.0 / 12.0

# Wood density (g/cm3) - literature values for the dominant Taipei street species.
WOOD_DENSITY = {
    "榕樹": 0.55, "茄苳": 0.60, "樟樹": 0.52, "楓香": 0.55, "臺灣欒樹": 0.60,
    "白千層": 0.68, "黑板樹": 0.42, "小葉欖仁": 0.58, "大花紫薇": 0.62,
    "水黃皮": 0.55, "正榕": 0.55, "印度橡膠樹": 0.50, "木棉": 0.45,
    "阿勃勒": 0.65, "鳳凰木": 0.50, "苦楝": 0.55, "欖仁樹": 0.55,
    "蒲葵": 0.35, "大王椰子": 0.35, "蘇鐵": 0.45,
}
DEFAULT_WOOD_DENSITY = 0.55
MIN_SPECIES_N = 30


def band_of(z):
    for name, lo, hi in BANDS:
        if lo <= z < hi:
            return name
    return None


def agb_kg(diameter_cm, height_m, species):
    rho = WOOD_DENSITY.get(species, DEFAULT_WOOD_DENSITY)
    return CHAVE_A * (rho * diameter_cm ** 2 * height_m) ** CHAVE_B


def read_trees():
    """Read the authoritative table (WP1) and keep analysis_ready records."""
    rows = []
    with open(AUTH_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("analysis_ready") != "1":
                continue
            d = float(r["Diameter_cm"])
            h = float(r["TreeHeight_m"])
            sp = (r["TreeType"] or "").strip()
            rows.append({
                "district": (r["Dist"] or "").strip(), "species": sp,
                "d": d, "h": h, "agb": agb_kg(d, h, sp),
                "band": (r["elev_band"] or None),
            })
    return rows


def fit_power_law(h, agb):
    """OLS of ln(AGB)=ln(a)+b·ln(H) (closed form - avoids LAPACK).

    Returns a, b, r2.
    """
    lx, ly = np.log(h), np.log(agb)
    lx_m, ly_m = lx.mean(), ly.mean()
    sxx = float(((lx - lx_m) ** 2).sum())
    sxy = float(((lx - lx_m) * (ly - ly_m)).sum())
    b = sxy / sxx
    ln_a = ly_m - b * lx_m
    pred = ln_a + b * lx
    ss_res = float(((ly - pred) ** 2).sum())
    ss_tot = float(((ly - ly_m) ** 2).sum())
    return float(np.exp(ln_a)), float(b), (1 - ss_res / ss_tot if ss_tot else 0.0)


def summarise(rows, key):
    agg = defaultdict(lambda: {"n": 0, "agb": 0.0})
    for r in rows:
        k = r[key]
        if k is None:
            continue
        agg[k]["n"] += 1
        agg[k]["agb"] += r["agb"]
    out = {}
    for k, v in agg.items():
        c = v["agb"] * CARBON_FRACTION * (1 + ROOT_SHOOT_RATIO)
        out[k] = {
            "n": v["n"],
            "agb_t": round(v["agb"] / 1000.0, 1),
            "carbon_t": round(c / 1000.0, 1),
            "co2e_t": round(c * CO2_PER_C / 1000.0, 1),
        }
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["co2e_t"]))


def main():
    rows = read_trees()
    if not rows:
        print("no valid trees", file=sys.stderr)
        return 1
    agb = np.array([r["agb"] for r in rows])
    h = np.array([r["h"] for r in rows])
    tot_c = float(agb.sum()) * CARBON_FRACTION * (1 + ROOT_SHOOT_RATIO)

    species_counts = defaultdict(int)
    for r in rows:
        species_counts[r["species"]] += 1
    power_laws = {}
    for sp, n in sorted(species_counts.items(), key=lambda kv: -kv[1])[:10]:
        if n < MIN_SPECIES_N or not sp:
            continue
        sel = np.array([r["species"] == sp for r in rows])
        a, b, r2 = fit_power_law(h[sel], agb[sel])
        power_laws[sp] = {"n": n, "a": round(a, 5), "b": round(b, 3), "r2": round(r2, 3)}
    a_all, b_all, r2_all = fit_power_law(h, agb)

    landscape = {}
    if CANOPY_JSON.exists():
        scan = json.loads(CANOPY_JSON.read_text(encoding="utf-8"))
        landscape = {
            b: {"cover_pct": v["cover_pct"], "canopy_ha": v["canopy_ha"],
                "height_sum_m_ha": v["height_sum_m_ha"],
                "height_sum_share_pct": v["height_sum_share_pct"]}
            for b, v in scan["bands"].items()
        }

    payload = {
        "meta": {
            "n_trees": len(rows),
            "equation": "AGB_kg = 0.0673 * (rho*D^2*H)^0.976  [Chave et al. 2014]",
            "carbon_fraction": CARBON_FRACTION,
            "root_shoot_ratio": ROOT_SHOOT_RATIO,
            "default_wood_density_g_cm3": DEFAULT_WOOD_DENSITY,
            "note": "Forest canopy ΣH is a relative proxy; absolute forest carbon "
                    "requires allometric calibration and is not reported here.",
        },
        "street_trees": {
            "total": {
                "n": len(rows),
                "agb_t": round(agb.sum() / 1000.0, 1),
                "carbon_t": round(tot_c / 1000.0, 1),
                "co2e_t": round(tot_c * CO2_PER_C / 1000.0, 1),
                "mean_agb_kg": round(float(agb.mean()), 1),
            },
            "by_district": summarise(rows, "district"),
            "by_elevation_band": summarise(rows, "band"),
            "by_species_top": summarise(rows, "species"),
            "height_to_biomass_fit": {
                "pooled": {"a": round(a_all, 5), "b": round(b_all, 3), "r2": round(r2_all, 3)},
                "by_species": power_laws,
            },
        },
        "landscape_canopy_by_band": landscape,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    t = payload["street_trees"]["total"]
    print(f"trees={t['n']:,}  AGB={t['agb_t']:,} t  C={t['carbon_t']:,} t  "
          f"CO2e={t['co2e_t']:,} t")
    print(f"pooled AGB=a*H^b -> a={a_all:.4f} b={b_all:.3f} r2={r2_all:.3f}")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
