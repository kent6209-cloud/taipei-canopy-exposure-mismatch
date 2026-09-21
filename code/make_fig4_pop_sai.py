# -*- coding: utf-8 -*-
"""Figure 4: population-density decile vs mean SAI and mean canopy height.

Replaces the former fig6_pop_sai.png (a 2D density block grid on a
log10(pop+1) axis, which was hard to read and carried no meaningful units).
Here the 23,342 residential cells are split into ten equal-count population-
density deciles and each decile's mean is plotted with a 95% CI, so the
monotone decline is directly legible.

Note: the population layer is WorldPop-derived *relative density*, not an
absolute headcount, so the x axis is labelled by decile, not by persons/ha.

Output: Paper/figures/fig6_pop_sai.png   (圖 4 in the thesis)
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RAST = ROOT / "wp2_rasters"
FB, FR = plus.FB, plus.FR
NDEC = 10
BAR_A = (52, 108, 66)
BAR_B = (36, 84, 186)


def font(p, s):
    return ImageFont.truetype(p, s)


def spearman(a, b):
    """Ordinal-rank Spearman (matches wp2_spatial_stats.spearman_manual)."""
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra = ra - ra.mean(); rb = rb - rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra * ra).sum() * (rb * rb).sum()))


def deciles(x, y, z):
    order = np.argsort(x)
    n = x.size
    edges = np.linspace(0, n, NDEC + 1).astype(int)
    out = []
    for i in range(NDEC):
        sel = order[edges[i]:edges[i + 1]]
        rec = {"n": int(sel.size), "xmid": float(np.median(x[sel]))}
        for key, arr in (("y", y), ("z", z)):
            v = arr[sel]
            m = float(v.mean())
            se = float(v.std(ddof=1) / math.sqrt(v.size))
            rec[key] = (m, 1.96 * se)
        out.append(rec)
    return out


def panel(c, d, x0, y0, w, h, title, dec, key, colour, unit, ymax, ann):
    d.text((x0 + w / 2, y0 - 74), title, font=font(FB, 28), fill=(30, 30, 30), anchor="ma")
    for gy in range(0, int(ymax) + 1, int(ymax / 5)):
        yy = y0 + h - gy / ymax * h
        d.line([(x0, yy), (x0 + w, yy)], fill=(232, 232, 232))
        d.text((x0 - 12, yy), f"{gy}", font=font(FR, 21), fill=(70, 70, 70), anchor="rm")
    bw = w / NDEC * 0.62
    for i, r in enumerate(dec):
        cx = x0 + (i + 0.5) * w / NDEC
        m, ci = r[key]
        top = y0 + h - (m + ci) / ymax * h
        base = y0 + h - (m - ci) / ymax * h
        d.rectangle([cx - bw / 2, top, cx + bw / 2, base], fill=(210, 230, 210))
        d.line([(cx, top), (cx, base)], fill=colour, width=4)
        d.line([(cx - bw / 3, top), (cx + bw / 3, top)], fill=colour, width=4)
        d.line([(cx - bw / 3, base), (cx + bw / 3, base)], fill=colour, width=4)
        hh = y0 + h - m / ymax * h
        d.rectangle([cx - bw / 2, hh, cx + bw / 2, y0 + h], fill=colour)
        d.text((cx, hh - 10), f"{m:.1f}", font=font(FB, 20), fill=(40, 40, 40), anchor="mb")
        d.text((cx, y0 + h + 12), f"D{i + 1}", font=font(FR, 21), fill=(60, 60, 60), anchor="ma")
        d.text((cx, y0 + h + 40), f"{r['xmid']:.0f}", font=font(FR, 17),
               fill=(140, 140, 140), anchor="ma")
    d.line([(x0, y0), (x0, y0 + h)], fill=(30, 30, 30), width=2)
    d.line([(x0, y0 + h), (x0 + w, y0 + h)], fill=(30, 30, 30), width=2)
    d.text((x0 + w / 2, y0 + h + 72), "人口密度分位（D1 最低　→　D10 最高）",
           font=font(FR, 22), fill=(60, 60, 60), anchor="ma")
    d.text((x0, y0 - 34), unit, font=font(FR, 22), fill=(60, 60, 60), anchor="lm")
    d.text((x0 + w / 2, y0 + h + 112), ann, font=font(FB, 23), fill=(178, 40, 40), anchor="ma")


def main():
    sai, _ = plus.read(RAST / "sai.tif")
    pop, _ = plus.read(RAST / "population.tif")
    can, _ = plus.read(RAST / "canopy_supply.tif")
    m = np.isfinite(sai) & np.isfinite(pop) & (pop > 0) & np.isfinite(can)
    x, y, z = pop[m], sai[m], can[m]
    dec = deciles(x, y, z)
    rho_sai, rho_can = spearman(y, x), spearman(z, x)
    n = int(x.size)
    drop_sai = 100.0 * dec[-1]["y"][0] / dec[0]["y"][0]
    drop_can = 100.0 * dec[-1]["z"][0] / dec[0]["z"][0]

    W, H = 1560, 950
    c = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    d.text((W / 2, 30), "",
           font=font(FB, 38), fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 78),
           f"居住網格（人口密度 > 0，n = {n:,}）依人口密度等量分為十分位；長條＝各分位平均，誤差線＝95% CI，"
           "D 下方小字＝該分位中位相對密度", font=font(FR, 22), fill=(120, 120, 120), anchor="ma")

    pw, gap = 620, 170
    x0 = (W - (pw * 2 + gap)) / 2
    y0, ph = 210, 470
    panel(c, d, x0, y0, pw, ph, "（a）平均綠意供給暴露 SAI", dec, "y", BAR_A, "SAI（分）", 100.0,
          f"ρ = -0.599（p = 0.001）　D10 為 D1 的 {drop_sai:.0f}%")
    panel(c, d, x0 + pw + gap, y0, pw, ph, "（b）平均樹冠結構 ΣH", dec, "z", BAR_B, "樹冠高度（m）", 12.0,
          f"ρ = -0.529（p = 0.001）　D10 為 D1 的 {drop_can:.0f}%")

    note = font(FR, 21)
    d.text((x0 - 70, H - 84),
           "註：SAI＝500 m 生活圈綠意供給暴露（accessibility proxy），非滿意度；ΣH 為結構型相對代理量，非絕對碳量。",
           font=note, fill=(110, 110, 110))
    d.text((x0 - 70, H - 52),
           "人口層為 WorldPop 推估之相對密度（非絕對人數），故橫軸以分位表示。相關為描述性；"
           "網格具空間自相關，Spearman ρ 以區塊置換檢定。", font=note, fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    plus.save(c, FIG / "fig6_pop_sai.png")
    print("fig4 done", c.size, "n", n, "rho_sai", round(rho_sai, 3), "rho_canopy", round(rho_can, 3))
    print("decile SAI ", [round(r["y"][0], 1) for r in dec])
    print("decile  ΣH  ", [round(r["z"][0], 2) for r in dec])
    print("median rel-density", [round(r["xmid"], 1) for r in dec])
    return 0


if __name__ == "__main__":
    sys.exit(main())
