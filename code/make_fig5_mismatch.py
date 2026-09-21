# -*- coding: utf-8 -*-
"""Figure 5: supply-demand mismatch deficit + LISA cluster (two panels).

Replaces the former 圖 5 (fig7_mismatch) and 圖 5b (fig7b_lisa); the standalone
LISA figure duplicated panel (b) and carried a misleading 0-4 gradient bar.

  (a) 錯置赤字 z(pop) − z(canopy)   diverging, own colour bar
  (b) LISA 分群                      categorical + swatch legend with counts

Output: Paper/figures/fig7_mismatch.png   (圖 5 in the thesis)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RAST = ROOT / "wp2_rasters"
DIV, CLS = plus.DIV, plus.CLS
SCALE, MARGIN = plus.SCALE, plus.MARGIN
LISA = [("HH 6,274", CLS[1][1], (198, 32, 45)), ("LL 7,349", CLS[2][1], (36, 84, 186)),
        ("LH 8", CLS[3][1], (110, 180, 235)), ("HL 11", CLS[4][1], (235, 165, 40))]
BAND_C = [(0, "0–20 m"), (1, "20–100 m"), (2, "100–300 m"), (3, "300–600 m"), (4, ">600 m")]


def map_image(arr, gt, stops, vmin, vmax):
    valid = np.isfinite(arr)
    v = np.zeros_like(arr); v[valid] = (arr[valid] - vmin) / (vmax - vmin)
    img = np.full((*arr.shape, 3), 255, np.uint8)
    img[valid] = plus.colormap(v, stops)[valid]
    return Image.fromarray(img).resize((arr.shape[1] * SCALE, arr.shape[0] * SCALE),
                                       Image.NEAREST)


def diverging_bar(c, d, x, y, w, stops, vmin, vmax, unit):
    bar = plus.colormap(np.linspace(0, 1, w).reshape(1, -1), stops)
    c.paste(Image.fromarray(np.repeat(bar, 22, 0)), (x, y))
    d.rectangle([x, y, x + w, y + 22], outline=(120, 120, 120))
    for frac in (0.0, 0.5, 1.0):
        xx = x + frac * w
        d.line([(xx, y + 22), (xx, y + 28)], fill=(60, 60, 60), width=2)
        val = vmin + frac * (vmax - vmin)
        d.text((xx, y + 32), "0.00" if frac == 0.5 else f"{val:+.2f}",
               font=plus.font(plus.FR, 19), fill=(60, 60, 60), anchor="ma")
    d.text((x + w + 12, y + 11), unit, font=plus.font(plus.FR, 19),
           fill=(60, 60, 60), anchor="lm")


def main():
    mis, gt = plus.read(RAST / "mismatch_deficit.tif")
    clu, _ = plus.read(RAST / "lisa_cluster.tif")
    plus.reset_labels()
    mm = float(np.nanpercentile(np.abs(mis[np.isfinite(mis)]), 98))
    A = map_image(mis, gt, DIV, -mm, mm)
    B = map_image(clu, gt, CLS, 0, 4)
    W, H = A.size
    c = Image.new("RGB", (W * 2 + 3 * MARGIN, H + 2 * MARGIN + 150), (255, 255, 255))
    d = ImageDraw.Draw(c)
    left, right, top = MARGIN, W + 2 * MARGIN, MARGIN + 44
    c.paste(A, (left, top)); c.paste(B, (right, top))
    d.text((W + 1.5 * MARGIN, 18), "",
           font=plus.font(plus.FB, 40), fill=(20, 20, 20), anchor="ma")
    d.text((left + W / 2, MARGIN + 6), "(a) 錯置赤字 z(人口) - z(樹冠)",
           font=plus.font(plus.FB, 26), fill=(30, 30, 30), anchor="ma")
    d.text((right + W / 2, MARGIN + 6), "(b) LISA 空間聚集分群",
           font=plus.font(plus.FB, 26), fill=(30, 30, 30), anchor="ma")

    gdf = plus.admin_gdf()
    for ox in (left, right):
        plus.draw_admin(d, gdf, gt, SCALE, ox, top)

    for col, row, name in plus.district_points(gt, mis.shape):
        if 0 <= col < mis.shape[1] and 0 <= row < mis.shape[0]:
            d.text((left + col * SCALE, top + row * SCALE), name,
                   font=plus.font(plus.FR, 20), fill=(25, 25, 25), anchor="mm",
                   stroke_width=4, stroke_fill=(255, 255, 255))
            plus.record_label("圖 5-3", name, gt[0] + (col + 0.5) * gt[1],
                              gt[3] + (row + 0.5) * gt[5])

    plus.north(d, left + W - 60, top + 20)
    plus.scalebar(d, left + 30, top + H - 90, gt)

    ly = top + H + 26
    diverging_bar(c, d, left, ly, W, DIV, -mm, mm, "z 分數")
    d.text((left, ly + 62), "紅＝需求赤字（人口高、樹冠低）　藍＝供給盈餘",
           font=plus.font(plus.FR, 20), fill=(90, 90, 90))

    lx = right
    for lab, col, _ in LISA:
        d.rectangle([lx, ly, lx + 26, ly + 20], fill=col, outline=(90, 90, 90))
        d.text((lx + 34, ly + 10), lab, font=plus.font(plus.FR, 20), fill=(60, 60, 60), anchor="lm")
        lx += 200
    d.rectangle([lx, ly, lx + 26, ly + 20], fill=CLS[0][1], outline=(90, 90, 90))
    d.text((lx + 34, ly + 10), "不顯著 14,010", font=plus.font(plus.FR, 20),
           fill=(60, 60, 60), anchor="lm")
    d.text((right, ly + 62),
           "雙變量 Moran's I = -0.443（p=0.001）；赤字區 7,911 格。HH＝高赤字被高赤字包圍，非個別居民推論。",
           font=plus.font(plus.FR, 20), fill=(110, 110, 110))
    d.text((left, ly + 96),
           "註：z 為全市標準化；赤字＝z(人口) > z(樹冠)。色階裁切至 ±p98 以保留對比。"
           "LISA 為 Local Moran's I 顯著（p<0.05）網格之分群。",
           font=plus.font(plus.FR, 20), fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    plus.save(c, FIG / "fig7_mismatch.png")
    plus.save_label_log(ROOT / "wp5_district_label_positions.json")
    print("fig5 mismatch done", c.size, "range", round(-mm, 2), round(mm, 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
