# -*- coding: utf-8 -*-
"""WP3/RQ2: locate Open Green cases relative to the SAI / supply-demand surface.

Reads the coded case tables (district-centroid coordinates) and samples the
100 m layers (SAI, canopy supply, population) to classify each case into the
supply x demand quadrant used for P1 (deficit = low supply & high demand).

Outputs: wp3_cases_vs_sai.json + Paper/figures/fig8_opengreen_on_sai.png
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp2_green_accessibility as w2

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
OUT = ROOT / "wp3_cases_vs_sai.json"
CSVS = ["opengreen_114E_coded.csv", "opengreen_114W_coded.csv",
        "opengreen_112_113_coded.csv", "opengreen_108_111_coded.csv"]
SCALE = 4
MARGIN = 70


def build():
    bounds = w2.master_grid()
    chm, gt = w2.warp(w2.CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, w2.CHM_NODATA)
    pop, _ = w2.warp(w2.POP, bounds, gdal.GRA_Average, gdal.GDT_Float32, -9999.0)
    green = w2.rasterize_green(bounds, gt)
    trees = w2.tree_density(gt, chm.shape)
    pop = np.where((pop == -9999.0) | ~np.isfinite(pop) | (pop < 0), 0.0, pop)
    valid = np.isfinite(chm) & (chm != w2.CHM_NODATA)
    green = np.where(np.isfinite(green), green, 0.0)
    g5, _ = w2.window_mean(green, valid)
    c5, _ = w2.window_mean(chm, valid)
    t5, _ = w2.window_mean(trees, valid)
    sai = (0.4 * np.clip(g5, 0, 1) + 0.4 * np.clip(c5 / w2.cap95(c5), 0, 1)
           + 0.2 * np.clip(t5 / w2.cap95(t5), 0, 1)) * 100.0
    sai = np.where(valid, sai, np.nan)
    return bounds, gt, valid, chm, sai, pop


def read_cases():
    cases = []
    for name in CSVS:
        p = ROOT / name
        if not p.exists():
            continue
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("lon") and r.get("lat"):
                    cases.append({"case": r["case_name"], "src": name,
                                  "lon": float(r["lon"]), "lat": float(r["lat"]),
                                  "layer": r.get("layer", "")})
    return cases


def main():
    bounds, gt, valid, chm, sai, pop = build()
    to_m = Transformer.from_crs("EPSG:4326", f"EPSG:{w2.EPSG_METRIC}", always_xy=True)
    cases = read_cases()

    cap_mean, pop_mean = float(np.nanmean(chm[valid])), float(np.mean(pop[valid]))
    rows = []
    for c in cases:
        x, y = to_m.transform(c["lon"], c["lat"])
        col = int((x - gt[0]) / gt[1]); row = int((gt[3] - y) / (-gt[5]))
        if not (0 <= col < chm.shape[1] and 0 <= row < chm.shape[0] and valid[row, col]):
            continue
        s_hi = chm[row, col] > cap_mean
        d_hi = pop[row, col] > pop_mean
        quad = ("high_supply_high_demand" if s_hi and d_hi else
                "high_supply_low_demand" if s_hi else
                "low_supply_high_demand" if d_hi else "low_supply_low_demand")
        rows.append({**c, "sai": round(float(sai[row, col]), 2),
                     "canopy_m": round(float(chm[row, col]), 2),
                     "quadrant": quad})

    counts = {}
    for r in rows:
        counts[r["quadrant"]] = counts.get(r["quadrant"], 0) + 1
    deficit = counts.get("low_supply_high_demand", 0)

    payload = {"n_cases_with_coords": len(rows), "quadrant_counts": counts,
               "share_in_deficit_pct": round(100.0 * deficit / len(rows), 1) if rows else 0.0,
               "note": "case coordinates are district centroids (approximate)",
               "cases": rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- figure: SAI map + case points
    v = np.clip(sai / 100.0, 0, 1)
    stops = [(0.0, (247, 252, 245)), (0.35, (199, 233, 192)),
             (0.7, (65, 171, 93)), (1.0, (0, 68, 27))]
    r = np.zeros_like(v); g = np.zeros_like(v); b = np.zeros_like(v)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        m = (v >= p0) & (v <= p1) & valid
        t = np.where(p1 > p0, (v - p0) / (p1 - p0), 0)
        for arr_out, c_0, c_1 in ((r, c0[0], c1[0]), (g, c0[1], c1[1]), (b, c0[2], c1[2])):
            arr_out[m] = c_0 + t[m] * (c_1 - c_0)
    img = np.full((*sai.shape, 3), 255, np.uint8)
    img[valid] = np.dstack([r, g, b])[valid].astype(np.uint8)
    im = Image.fromarray(np.flipud(img)).resize(
        (sai.shape[1] * SCALE, sai.shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 140), (255, 255, 255))
    canvas.paste(im, (MARGIN, MARGIN + 40))
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(r"C:\Windows\Fonts\msjhbd.ttc", 42)
    fr = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 30)
    d.text((W / 2 + MARGIN, 20), "",
           font=f, fill=(20, 20, 20), anchor="ma")
    for c in cases:
        x, y = to_m.transform(c["lon"], c["lat"])
        col = int((x - gt[0]) / gt[1]); row = int((gt[3] - y) / (-gt[5]))
        px = MARGIN + col * SCALE; py = MARGIN + 40 + (sai.shape[0] - 1 - row) * SCALE
        d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=(200, 30, 30), width=3)
    d.text((MARGIN, H + 56), f"紅圈＝Open Green 案例（n={len(rows)}，行政區質心近似）",
           font=fr, fill=(80, 80, 80))
    d.text((MARGIN, H + 96), f"赤字區（低供給·高需求）占 {payload['share_in_deficit_pct']}%",
           font=fr, fill=(80, 80, 80))
    FIG.mkdir(exist_ok=True)
    canvas.save(FIG / "fig8_opengreen_on_sai.png")
    print(f"cases {len(rows)}  quadrants {counts}  deficit {payload['share_in_deficit_pct']}%")
    print("wrote", OUT.name, "and", (FIG / "fig8_opengreen_on_sai.png").name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
