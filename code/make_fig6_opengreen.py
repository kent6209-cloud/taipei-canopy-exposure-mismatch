# -*- coding: utf-8 -*-
"""Figure 6 (new numbering): Open Green cases on the SAI surface.

The 52 coded cases carry *district-centroid* coordinates, so they collapse onto
12 distinct points.  Plotting one pin per case is therefore misleading.  This
figure instead aggregates cases per centroid and encodes

    bubble area  ∝ number of cases at that centroid
    bubble fill  = supply-demand quadrant (threshold = city-wide mean)
    label        = case count

plus a stacked bar of the quadrant composition and an explicit limitation note.

Output: Paper/figures/fig8_opengreen_on_sai.png   (圖 6 in the thesis)
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RJ = ROOT / "wp3_cases_vs_sai.json"
SAI_TIF = ROOT / "wp2_rasters" / "sai.tif"

GREEN = plus.GREEN
ORDER = ["low_supply_high_demand", "low_supply_low_demand",
         "high_supply_low_demand", "high_supply_high_demand"]
QCOL = {
    "low_supply_high_demand": (198, 32, 45),
    "low_supply_low_demand": (130, 130, 130),
    "high_supply_low_demand": (36, 84, 186),
    "high_supply_high_demand": (138, 78, 176),
}
QNAME = {
    "low_supply_high_demand": "低供給·高需求（赤字）",
    "low_supply_low_demand": "低供給·低需求",
    "high_supply_low_demand": "高供給·低需求",
    "high_supply_high_demand": "高供給·高需求",
}
MARGIN = 80
BUBBLE_X = 3.0      # bubble-size multiplier (circle areas scale with BUBBLE_X**2)


def aggregate(cases):
    """Group the cases by their (shared) centroid coordinate."""
    groups = defaultdict(list)
    for c in cases:
        groups[(round(c["lon"], 5), round(c["lat"], 5))].append(c)
    out = []
    for (lon, lat), items in groups.items():
        quad = max(set(i["quadrant"] for i in items),
                   key=lambda q: sum(1 for i in items if i["quadrant"] == q))
        out.append({"lon": lon, "lat": lat, "n": len(items), "quadrant": quad})
    return out


def draw_bubbles(d, items):
    for it in items:
        px, py, r = it["px"], it["py"], it["r"]
        d.ellipse([px - r, py - r, px + r, py + r],
                  fill=QCOL[it["quadrant"]], outline=(255, 255, 255), width=4)
        fs = int(max(20, min(38, r * 0.62)))
        d.text((px, py), str(it["n"]), font=plus.font(plus.FB, fs),
               fill=(255, 255, 255), anchor="mm")


DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0), (-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)]


def draw_district_labels(d, gt, shape, left, top, scale, items, W, H, gdf):
    """Place each district name outside the bubbles, inside its own district."""
    fnt = plus.font(plus.FR, 24)
    from shapely.geometry import Point
    polys = {r["TOWNNAME"]: r.geometry for _, r in gdf.iterrows()}
    placed = []
    pts = []
    for col, row, name in plus.district_points(gt, shape):
        if not (0 <= col < shape[1] and 0 <= row < shape[0]):
            continue
        dx, dy = left + col * scale, top + row * scale
        near = min(items, key=lambda it: (it["px"] - dx) ** 2 + (it["py"] - dy) ** 2)
        pts.append((near, name))
    pts.sort(key=lambda t: -t[0]["r"])
    for near, name in pts:
        w, h = d.textbbox((0, 0), name, font=fnt)[2:]
        poly = polys.get(name)
        best = None
        for ux, uy in DIRS:
            gap = near["r"] + max(w, h) / 2 + 8
            cx = near["px"] + ux * gap
            cy = near["py"] + uy * gap
            rect = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
            pen = 0.0
            if rect[0] < left or rect[2] > left + W or rect[1] < top or rect[3] > top + H:
                pen += 1e6
            if poly is not None:                      # 區名必須落在本區界內
                wcx = (cx - left) / scale
                wcy = (cy - top) / scale
                if not poly.contains(Point(gt[0] + (wcx + 0.5) * gt[1],
                                           gt[3] + (wcy + 0.5) * gt[5])):
                    pen += 5e5
            for it in items:
                if math.hypot(cx - it["px"], cy - it["py"]) < it["r"] + max(w, h) / 2 + 4:
                    pen += 1e4
            for r2 in placed:
                ox = max(0, min(rect[2], r2[2]) - max(rect[0], r2[0]))
                oy = max(0, min(rect[3], r2[3]) - max(rect[1], r2[1]))
                pen += ox * oy
            if best is None or pen < best[0]:
                best = (pen, cx, cy, rect)
        if poly is not None and best[0] >= 5e5:        # 退回到本區代表點
            rp = poly.representative_point()
            cx = left + (rp.x - gt[0]) / gt[1] * scale
            cy = top + (gt[3] - rp.y) / (-gt[5]) * scale
            best = (5e5, cx, cy, [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])
        _, cx, cy, rect = best
        d.text((cx, cy), name, font=fnt, fill=(20, 20, 20), anchor="mm",
               stroke_width=4, stroke_fill=(255, 255, 255))
        placed.append(rect)
        plus.record_label("圖 5-4", name, gt[0] + ((cx - left) / scale + 0.5) * gt[1],
                          gt[3] + ((cy - top) / scale + 0.5) * gt[5])


def draw_composition(canvas, d, x0, x1, y, counts, total):
    h = 56
    cx = x0
    for q in ORDER:
        n = counts.get(q, 0)
        w = (x1 - x0) * n / total
        d.rectangle([cx, y, cx + w, y + h], fill=QCOL[q], outline=(255, 255, 255), width=2)
        pct = 100.0 * n / total
        lab = f"{n}（{pct:.1f}%）" if w > 120 else str(n)
        d.text((cx + w / 2, y + h / 2), lab, font=plus.font(plus.FB, 21),
               fill=(255, 255, 255), anchor="mm")
        cx += w
    d.rectangle([x0, y, x1, y + h], outline=(90, 90, 90), width=2)
    rows = [(ORDER[0], ORDER[1]), (ORDER[2], ORDER[3])]
    for i, pair in enumerate(rows):
        lx = x0
        ly = y + h + 30 + i * 34
        for q in pair:
            d.rectangle([lx, ly - 11, lx + 22, ly + 11], fill=QCOL[q])
            txt = f"{QNAME[q]} {counts.get(q, 0)} 案"
            d.text((lx + 30, ly), txt, font=plus.font(plus.FR, 21),
                   fill=(55, 55, 55), anchor="lm")
            lx += 60 + d.textlength(txt, font=plus.font(plus.FR, 21)) + 70


def main():
    payload = json.loads(RJ.read_text(encoding="utf-8"))
    cases = payload["cases"]
    counts = payload["quadrant_counts"]
    total = payload["n_cases_with_coords"]
    groups = aggregate(cases)

    arr, gt = plus.read(SAI_TIF)
    shape = arr.shape
    valid = np.isfinite(arr)
    v = np.zeros_like(arr); v[valid] = np.clip(arr[valid] / 100.0, 0, 1)
    img = np.full((*shape, 3), 255, np.uint8)
    img[valid] = plus.colormap(v, GREEN)[valid]

    scale = max(3, int(round(1240 / shape[1])))
    im = Image.fromarray(img).resize((shape[1] * scale, shape[0] * scale), Image.NEAREST)
    W, H = im.size
    TOP_TITLE, TOP_MAP, BOT = 60, 40, 360
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + TOP_TITLE + TOP_MAP + BOT), (255, 255, 255))
    canvas.paste(im, (MARGIN, TOP_TITLE + TOP_MAP))
    d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 20),
           "",
           font=plus.font(plus.FB, 40), fill=(20, 20, 20), anchor="ma")

    left, top = MARGIN, TOP_TITLE + TOP_MAP
    plus.draw_admin(d, plus.admin_gdf(), gt, scale, left, top)
    from pyproj import Transformer
    to_m = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    items = []
    for g in groups:
        x, y = to_m.transform(g["lon"], g["lat"])
        col = int((x - gt[0]) / gt[1])
        row = int((gt[3] - y) / (-gt[5]))
        if not (0 <= col < shape[1] and 0 <= row < shape[0]):
            continue
        items.append({**g, "px": left + col * scale, "py": top + row * scale,
                      "r": BUBBLE_X * (9.0 + 3.4 * float(np.sqrt(g["n"])))})

    draw_bubbles(d, items)
    gdf = plus.admin_gdf()
    plus.reset_labels()
    draw_district_labels(d, gt, shape, left, top, scale, items, W, H, gdf)

    plus.north(d, left + W - 60, top + 20)
    plus.scalebar(d, left + 30, top + H - 90, gt)

    cb_y = top + H + 30
    plus.colorbar(canvas, d, MARGIN, cb_y, W, GREEN, 0, 100, "分")

    y0 = cb_y + 92
    draw_composition(canvas, d, MARGIN, MARGIN + W, y0, counts, total)
    note = plus.font(plus.FR, 20)
    d.text((MARGIN, y0 + 152),
           f"註：52 案座標為行政區質心近似（投影後落於 {len(groups)} 個質心點）；圓面積 ∝ 該質心案件數、填色＝供給—需求象限。",
           font=note, fill=(110, 110, 110))
    d.text((MARGIN, y0 + 182),
           "象限門檻為全市均值（供給＝樹冠、需求＝人口）；低供給·高需求＝政策赤字區。",
           font=note, fill=(110, 110, 110))
    d.text((MARGIN, y0 + 212),
           "SAI 為 500 m 生活圈綠意供給暴露（accessibility proxy），非滿意度或使用量。"
           "底圖黑粗線＝市界、灰白線＝區界。",
           font=note, fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    plus.save(canvas, FIG / "fig8_opengreen_on_sai.png")
    plus.save_label_log(ROOT / "wp5_district_label_positions.json")
    print("fig6 done", canvas.size, "groups", len(groups), "counts", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
