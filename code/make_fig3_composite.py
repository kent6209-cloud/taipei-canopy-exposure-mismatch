# -*- coding: utf-8 -*-
"""Composite Figure 3: band share | canopy structure (ΣH) | SAI  (one row).

Panel (a) is a bar chart of area-share vs ΣH-share per elevation band (the
quantitative complement to the 圖 2 study-area map).  Panels (b)/(c) are the
ΣH and SAI rasters.  Replaces the former 圖 3 (elevation+canopy), 圖 4 (ΣH)
and 圖 5 (SAI).
Output: Paper/figures/fig3_supply_demand.png
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus
import make_final_figures as ff

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
FB, FR = plus.FB, plus.FR
GREEN = plus.GREEN
font, read, colormap = plus.font, plus.read, plus.colormap
district_lines, district_points = plus.district_lines, plus.district_points
PW = 560          # panel width (px)
GAP = 115
MARGIN = 90

BAND_KEYS = ["都市平地", "丘陵近山", "淺山", "山地", "中高山"]
BAND_LABEL = ["0–20\n平地", "20–100\n近山", "100–300\n淺山", "300–600\n山地", ">600\n中高山"]
BAND_COL = {0: (219, 231, 201), 1: (190, 217, 168), 2: (150, 197, 132),
            3: (99, 160, 99), 4: (52, 108, 66)}
AREA_C = (183, 205, 165)
SIGMA_C = (40, 104, 82)


def panel_rgb(arr, stops, vmin, vmax, valid):
    v = np.zeros_like(arr); v[valid] = (arr[valid] - vmin) / (vmax - vmin)
    rgb = np.full((*arr.shape, 3), 255, np.uint8)
    rgb[valid] = colormap(v, stops)[valid]
    return rgb


def panel_band_bars(size, labels, area_pct, sig_pct):
    """Grouped bars: area share vs ΣH share per elevation band."""
    W, H = size
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 16), "(a) 高程帶：面積占比 vs ΣH 占比", font=font(FB, 22),
           fill=(30, 30, 30), anchor="ma")
    left, right = 78, W - 26
    top, bottom = 118, H - 150
    ymax = 50.0
    for g in range(0, 41, 10):
        y = bottom - (bottom - top) * g / ymax
        d.line([(left, y), (right, y)], fill=(218, 218, 218), width=1)
        d.text((left - 10, y), f"{g}", font=font(FR, 16), fill=(115, 115, 115), anchor="rm")
    d.text((left - 10, top - 18), "%", font=font(FR, 16), fill=(115, 115, 115), anchor="rm")
    n = len(labels)
    slot = (right - left) / n
    bw = slot * 0.30
    for i, (lab, a, s) in enumerate(zip(labels, area_pct, sig_pct)):
        cx = left + slot * (i + 0.5)
        for val, col, off in ((a, AREA_C, -bw * 0.58), (s, SIGMA_C, bw * 0.58)):
            x0, x1 = cx + off - bw / 2, cx + off + bw / 2
            y0 = bottom - (bottom - top) * val / ymax
            d.rectangle([x0, y0, x1, bottom], fill=col)
            d.text(((x0 + x1) / 2, y0 - 7), f"{val:.1f}", font=font(FR, 15),
                   fill=(60, 60, 60), anchor="mb")
        d.multiline_text((cx, bottom + 12), lab, font=font(FR, 16), fill=(50, 50, 50),
                         anchor="ma", align="center", spacing=3)
    d.line([(left, top), (left, bottom)], fill=(120, 120, 120))
    d.line([(left, bottom), (right, bottom)], fill=(120, 120, 120))
    d.rectangle([left + 12, 64, left + 32, 80], fill=AREA_C)
    d.text((left + 40, 72), "面積占比", font=font(FR, 16), fill=(60, 60, 60), anchor="lm")
    d.rectangle([left + 140, 64, left + 160, 80], fill=SIGMA_C)
    d.text((left + 168, 72), "ΣH 占比", font=font(FR, 16), fill=(60, 60, 60), anchor="lm")
    return im


def to_panel(rgb, gt, shape, labels=False):
    im = Image.fromarray(rgb)
    h = int(PW * shape[0] / shape[1])
    return im.resize((PW, h), Image.NEAREST)


def mini_cbar(canvas, d, x, y, w, stops, vmin, vmax, unit, title):
    d.text((x, y - 26), title, font=font(FB, 22), fill=(30, 30, 30))
    bar = colormap(np.linspace(0, 1, w).reshape(1, -1), stops)
    canvas.paste(Image.fromarray(np.repeat(bar, 18, 0)), (x, y))
    d.rectangle([x, y, x + w, y + 18], outline=(120, 120, 120))
    for frac in (0, .5, 1):
        xx = x + frac * w
        d.line([(xx, y + 18), (xx, y + 24)], fill=(60, 60, 60), width=2)
        d.text((xx, y + 27), f"{vmin + frac*(vmax-vmin):g}", font=font(FR, 18),
               fill=(60, 60, 60), anchor="ma")
    d.text((x + w + 10, y + 9), unit, font=font(FR, 18), fill=(60, 60, 60), anchor="lm")


def main():
    scan = json.loads((ROOT / "taipei_elev_carbon_scan.json").read_text(encoding="utf-8"))
    valid_ha = np.array([scan["bands"][k]["valid_ha"] for k in BAND_KEYS])
    sig_pct = np.array([scan["bands"][k]["height_sum_share_pct"] for k in BAND_KEYS])
    area_pct = 100.0 * valid_ha / valid_ha.sum()

    canopy, gt100 = read(ROOT / "wp2_rasters" / "canopy_supply.tif")
    sai, _ = read(ROOT / "wp2_rasters" / "sai.tif")
    vc = np.isfinite(canopy); vs = np.isfinite(sai)
    c_can = panel_rgb(np.nan_to_num(canopy), GREEN, 0, 12, vc)
    c_sai = panel_rgb(np.nan_to_num(sai), GREEN, 0, 100, vs)

    B = to_panel(c_can, gt100, canopy.shape)
    C = to_panel(c_sai, gt100, sai.shape)
    H = B.height
    A = panel_band_bars((PW, H), BAND_LABEL, area_pct, sig_pct)

    W = PW * 3 + GAP * 2
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + MARGIN * 2 + 130), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 22),
           "",
           font=font(FB, 34), fill=(20, 20, 20), anchor="ma")
    top = MARGIN + 30
    for i, im in enumerate((A, B, C)):
        canvas.paste(im, (MARGIN + i * (PW + GAP), top))
    gdf = plus.admin_gdf()
    for i in (1, 2):
        plus.draw_admin(d, gdf, gt100, PW / canopy.shape[1],
                        MARGIN + i * (PW + GAP), top)
    plus.reset_labels()
    for col, row, name in district_points(gt100, sai.shape):
        px = MARGIN + 2 * (PW + GAP) + col * PW / sai.shape[1]
        py = top + row * H / sai.shape[0]
        d.text((px, py), name, font=font(FR, 18), fill=(15, 15, 15), anchor="mm",
               stroke_width=3, stroke_fill=(255, 255, 255))
        plus.record_label("圖 5-1", name, gt100[0] + (col + 0.5) * gt100[1],
                          gt100[3] + (row + 0.5) * gt100[5])
    plus.save_label_log(ROOT / "wp5_district_label_positions.json")
    ly = top + H + 40
    mini_cbar(canvas, d, MARGIN, ly + 26, PW, GREEN, 0, 12, "m", "(b) 樹冠結構 ΣH（相對代理）")
    mini_cbar(canvas, d, MARGIN + (PW + GAP), ly + 26, PW, GREEN, 0, 100, "分", "(c) 綠意供給暴露 SAI")
    d.text((W / 2 + MARGIN, ly + 100),
           "註：(a) 各高程帶面積占比 vs ΣH 占比（平地占 44.1% 面積僅 8.2% ΣH；300 m 以上占 23.5% 面積達 41.7% ΣH）；"
           "(b) ΣH 為結構型相對代理量，非絕對碳量；(c) SAI＝500 m 生活圈綠意供給暴露（accessibility proxy）。",
           font=font(FR, 17), fill=(110, 110, 110), anchor="ma")
    FIG.mkdir(parents=True, exist_ok=True)
    plus.save(canvas, FIG / "fig3_supply_demand.png")
    print("fig3 composite done", canvas.size)
    print("area_pct", [round(float(x), 1) for x in area_pct])
    print("sig_pct", [round(float(x), 1) for x in sig_pct])
    return 0


if __name__ == "__main__":
    sys.exit(main())
