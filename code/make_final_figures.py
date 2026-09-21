# -*- coding: utf-8 -*-
"""Figure 4-2 (study area hillshade) — retained from the earlier enhancement pass.

Run: python make_final_figures.py

Superseded helpers are kept for provenance but NOT called:
  fig4_quantile()   -> 圖 5-1 (make_fig3_composite.py)
  fig6_density()    -> 圖 5-2 (make_fig4_pop_sai.py)
  fig7_combined()   -> 圖 5-3 (make_fig5_mismatch.py)
  fig8_quadrant()   -> 圖 5-4 (make_fig6_opengreen.py)

Output: Paper/figures/fig2_study_area.png
"""
import csv
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RAST = ROOT / "wp2_rasters"
DEM = r"E:\SCI\TPC\TPCityDem\TPCityDem5m.tif"
DEM_NODATA = -32767.0
FB, FR = plus.FB, plus.FR
GREEN, DIV, CLS = plus.GREEN, plus.DIV, plus.CLS
SCALE, MARGIN = plus.SCALE, plus.MARGIN
font, read, colormap = plus.font, plus.read, plus.colormap
district_lines, district_points = plus.district_lines, plus.district_points
north, scalebar, colorbar, save = plus.north, plus.scalebar, plus.colorbar, plus.save


def warp_res(src, bounds, res, resample, dtype, nodata):
    x0, y0, x1, y1 = bounds
    tmp = ROOT / "_ff_tmp.tif"
    gdal.Warp(str(tmp), src, options=gdal.WarpOptions(
        format="GTiff", outputBounds=(x0, y0, x1, y1), dstSRS="EPSG:3826",
        xRes=res, yRes=res, resampleAlg=resample, outputType=dtype, dstNodata=nodata,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))
    ds = gdal.Open(str(tmp)); arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform(); ds = None; tmp.unlink(missing_ok=True)
    return arr, gt


def map_image(arr, gt, stops, vmin, vmax, districts=True, labels=False):
    valid = np.isfinite(arr)
    v = np.zeros_like(arr); v[valid] = (arr[valid] - vmin) / (vmax - vmin)
    img = np.full((*arr.shape, 3), 255, np.uint8)
    img[valid] = colormap(v, stops)[valid]
    if districts:
        line, _ = district_lines(gt, arr.shape); img[line] = (70, 70, 70)
    im = Image.fromarray(img).resize((arr.shape[1] * SCALE, arr.shape[0] * SCALE), Image.NEAREST)
    return im


def admin_gdf():
    return plus.admin_gdf()


def draw_admin(d, g, gt, scale, ox, oy):
    return plus.draw_admin(d, g, gt, scale, ox, oy)


def fig2_hillshade():
    from wp2_green_accessibility import master_grid
    bounds = master_grid()
    dem, gt = warp_res(DEM, bounds, 40.0, gdal.GRA_Bilinear, gdal.GDT_Float32, DEM_NODATA)
    dem = np.where((dem == DEM_NODATA) | ~np.isfinite(dem), np.nan, dem)
    # hillshade (azimuth 315, altitude 45)
    filled = np.where(np.isfinite(dem), dem, np.nanmean(dem))
    gy, gx = np.gradient(filled, 40.0)
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, zen = math.radians(360 - 315 + 90), math.radians(90 - 45)
    hs = (np.sin(zen) * np.sin(slope) + np.cos(zen) * np.cos(slope) *
          np.cos(az - aspect))
    hs = np.clip((hs + 1) / 2, 0, 1)
    # 分層設色（hypsometric tint）＋地形陰影
    edges = (0, 20, 100, 300, 600, float("inf"))
    bandcol = {0: (219, 231, 201), 1: (190, 217, 168), 2: (150, 197, 132),
               3: (99, 160, 99), 4: (52, 108, 66)}
    band = np.full(dem.shape, -1, np.int8)
    valid = np.isfinite(dem)
    for k in range(5):
        band[valid & (dem >= edges[k]) & (dem < edges[k + 1])] = k
    shade = (0.58 + 0.42 * hs)[..., None]        # 保留地形起伏
    base = np.full((*dem.shape, 3), 255, np.uint8)
    for k, c in bandcol.items():
        m = band == k
        base[m] = (np.array(c) * shade[m]).astype(np.uint8)
    edge = np.zeros(dem.shape, bool)
    edge[1:] |= band[1:] != band[:-1]; edge[:, 1:] |= band[:, 1:] != band[:, :-1]
    base[edge & valid] = (60, 60, 60)            # 分帶界線
    im = Image.fromarray(base).resize((dem.shape[1] * 2, dem.shape[0] * 2), Image.NEAREST)
    W, H = im.size
    c = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 130), (255, 255, 255))
    c.paste(im, (MARGIN, MARGIN + 40)); d = ImageDraw.Draw(c)
    d.text((W / 2 + MARGIN, 18), "",
           font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    draw_admin(d, admin_gdf(), gt, 2, MARGIN, MARGIN + 40)
    plus.reset_labels()
    for col, row, name in district_points(gt, dem.shape):
        px = MARGIN + col * 2; py = MARGIN + 40 + row * 2
        d.text((px, py), name, font=font(FR, 22), fill=(20, 20, 20), anchor="mm",
               stroke_width=3, stroke_fill=(255, 255, 255))
        plus.record_label("圖 4-2", name, gt[0] + (col + 0.5) * gt[1],
                          gt[3] + (row + 0.5) * gt[5])
    plus.save_label_log(ROOT / "wp5_district_label_positions.json")
    north(d, MARGIN + W - 60, MARGIN + 60); scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    # elevation legend
    ly = MARGIN + 40 + H + 24
    for k, lab in [(0, "0–20 m 平地"), (1, "20–100 m 近山"), (2, "100–300 m 淺山"),
                   (3, "300–600 m 山地"), (4, ">600 m 中高山")]:
        d.rectangle([MARGIN + k * 235, ly, MARGIN + 32 + k * 235, ly + 20], fill=bandcol[k])
        d.text((MARGIN + 42 + k * 235, ly + 10), lab, font=font(FR, 20),
               fill=(60, 60, 60), anchor="lm")
    d.text((MARGIN, ly + 40), "分層設色（hypsometric tint）× 5 m DEM hillshade"
                              "（azimuth 315°, altitude 45°）；圖幅範圍為臺北市。",
           font=font(FR, 20), fill=(110, 110, 110))
    d.text((MARGIN, ly + 68), "黑粗線＝臺北市界（外框）；灰白線＝區界（12 區）；"
                              "深灰細線＝高程帶界線（20/100/300/600 m）。",
           font=font(FR, 20), fill=(110, 110, 110))
    save(c, FIG / "fig2_study_area.png"); print("fig2 hillshade done")


def fig4_quantile():
    canopy, gt = read(RAST / "canopy_supply.tif")
    valid = np.isfinite(canopy)
    pos = canopy[valid & (canopy > 0)]
    ranks = np.full(canopy.shape, np.nan)
    q = np.zeros_like(canopy); q[valid & (canopy > 0)] = (
        np.searchsorted(np.sort(pos), canopy[valid & (canopy > 0)]) / pos.size)
    q[valid & (canopy <= 0)] = -0.02
    img = np.full((*canopy.shape, 3), 255, np.uint8)
    v = np.clip(q, 0, 1)
    img[valid] = colormap(v, GREEN)[valid]
    line, _ = district_lines(gt, canopy.shape); img[line] = (60, 60, 60)
    im = Image.fromarray(img).resize((canopy.shape[1] * SCALE, canopy.shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    c = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 120), (255, 255, 255))
    c.paste(im, (MARGIN, MARGIN + 40)); d = ImageDraw.Draw(c)
    d.text((W / 2 + MARGIN, 18), "",
           font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    # annotation box
    box = "86.7% 樹冠位於高程 ≥20 m\n平地（0–20 m）覆蓋率僅 15.5%"
    d.rounded_rectangle([MARGIN + 20, MARGIN + 60, MARGIN + 560, MARGIN + 160],
                        radius=12, fill=(255, 255, 255), outline=(150, 150, 150), width=2)
    d.multiline_text((MARGIN + 40, MARGIN + 80), box, font=font(FB, 24), fill=(30, 30, 30))
    north(d, MARGIN + W - 60, MARGIN + 60); scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    # quantile colourbar with value ticks
    ly = MARGIN + 40 + H + 26
    bar = colormap(np.linspace(0, 1, W).reshape(1, -1), GREEN)
    c.paste(Image.fromarray(np.repeat(bar, 26, 0)), (MARGIN, ly))
    d.rectangle([MARGIN, ly, MARGIN + W, ly + 26], outline=(120, 120, 120))
    for frac in (0, .25, .5, .75, 1):
        xx = MARGIN + frac * W
        val = np.percentile(pos, frac * 100)
        d.line([(xx, ly + 26), (xx, ly + 32)], fill=(60, 60, 60), width=2)
        d.text((xx, ly + 36), f"{val:.1f}", font=font(FR, 22), fill=(40, 40, 40), anchor="ma")
    d.text((MARGIN + W + 14, ly + 13), "m", font=font(FR, 24), fill=(40, 40, 40), anchor="lm")
    d.text((MARGIN, ly + 70), "色階＝樹冠像素之分位數（quantile）；數值＝對應樹冠高度（m）。"
                              "ΣH 為相對結構代理量，非絕對碳量。", font=font(FR, 20), fill=(110, 110, 110))
    save(c, FIG / "fig4_sigmaH_canopy.png"); print("fig4 quantile done")


def fig6_density():
    a, _ = read(RAST / "sai.tif"); p, _ = read(RAST / "population.tif")
    m = np.isfinite(a) & np.isfinite(p) & (p > 0)
    x = np.log10(p[m] + 1); y = a[m]
    W, H, ML, MB, MT, MR = 1300, 820, 140, 120, 100, 60
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 22), "", font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    x0, x1, y0, y1 = ML, W - MR, MT, H - MB
    xmin, xmax = float(x.min()), float(x.max())
    Hh, xe, ye = np.histogram2d(x, y, bins=[70, 60], range=[[xmin, xmax], [0, 100]])
    Hh = np.log1p(Hh); mx = Hh.max() or 1
    for i in range(Hh.shape[0]):
        for j in range(Hh.shape[1]):
            if Hh[i, j] <= 0:
                continue
            px0 = x0 + (xe[i] - xmin) / (xmax - xmin) * (x1 - x0)
            px1 = x0 + (xe[i + 1] - xmin) / (xmax - xmin) * (x1 - x0)
            py0 = y1 - ye[j + 1] / 100 * (y1 - y0); py1 = y1 - ye[j] / 100 * (y1 - y0)
            t = Hh[i, j] / mx
            col = (int(247 - 210 * t), int(252 - 150 * t), int(245 - 190 * t))
            d.rectangle([px0, py0, px1, py1], fill=col)
    for gy in range(0, 101, 20):
        yy = y1 - gy / 100 * (y1 - y0); d.line([(x0, yy), (x1, yy)], fill=(235, 235, 235))
        d.text((x0 - 12, yy), f"{gy}", font=font(FR, 22), fill=(70, 70, 70), anchor="rm")
    for gx in np.arange(math.floor(xmin), xmax + 0.5, 0.5):
        xx = x0 + (gx - xmin) / (xmax - xmin) * (x1 - x0)
        d.text((xx, y1 + 12), f"{gx:g}", font=font(FR, 22), fill=(70, 70, 70), anchor="ma")
    d.line([(x0, y0), (x0, y1)], fill=(30, 30, 30), width=2); d.line([(x0, y1), (x1, y1)], fill=(30, 30, 30), width=2)
    b = ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum()
    a0 = y.mean() - b * x.mean()
    xs = np.array([xmin, xmax]); ys = a0 + b * xs
    # OLS 95% CI band (approximate)
    n = x.size; resid = y - (a0 + b * x); se = resid.std() / math.sqrt(n)
    for sign in (1, -1):
        pts = [(x0 + (xi - xmin) / (xmax - xmin) * (x1 - x0),
                y1 - np.clip(yi + sign * 1.96 * se, 0, 100) / 100 * (y1 - y0)) for xi, yi in zip(xs, ys)]
        d.line(pts, fill=(120, 170, 120), width=2)
    d.line([(x0, y1 - ys[0] / 100 * (y1 - y0)), (x1, y1 - ys[1] / 100 * (y1 - y0))],
           fill=(200, 40, 40), width=5)
    d.text((x0 + 20, y0 + 16), "Spearman ρ = −0.599　區塊置換 p = 0.001　n = 23,342 居住網格",
           font=font(FB, 24), fill=(180, 40, 40))
    d.text((x0 + (x1 - x0) / 2, H - 56), "log10(人口密度 + 1)", font=font(FR, 26), fill=(60, 60, 60), anchor="ma")
    d.text((44, (y0 + y1) / 2), "SAI", font=font(FR, 26), fill=(60, 60, 60), anchor="mm")
    save(c, FIG / "fig6_pop_sai.png"); print("fig6 density done", round(float(b), 2))


def fig7_combined():
    mis, gt = read(RAST / "mismatch_deficit.tif"); clu, _ = read(RAST / "lisa_cluster.tif")
    mm = float(np.nanmax(np.abs(mis)))
    A = map_image(mis, gt, DIV, -mm, mm, districts=True)
    B = map_image(clu, gt, CLS, 0, 4, districts=True)
    W, H = A.size
    c = Image.new("RGB", (W * 2 + 3 * MARGIN, H + 2 * MARGIN + 110), (255, 255, 255))
    d = ImageDraw.Draw(c)
    c.paste(A, (MARGIN, MARGIN + 40)); c.paste(B, (W + 2 * MARGIN, MARGIN + 40))
    d.text((W + 1.5 * MARGIN, 18), "",
           font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    d.text((MARGIN + W / 2, MARGIN + 30), "(a) 錯置赤字 z(pop) - z(canopy)", font=font(FB, 26), fill=(30, 30, 30), anchor="ma")
    d.text((W + 2 * MARGIN + W / 2, MARGIN + 30), "(b) LISA 分群", font=font(FB, 26), fill=(30, 30, 30), anchor="ma")
    north(d, MARGIN + W - 60, MARGIN + 60); scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    ly = MARGIN + 40 + H + 20
    # LISA legend
    labels = [("HH 6,274", CLS[1][1]), ("LL 7,349", CLS[2][1]), ("LH 8", CLS[3][1]),
              ("HL 11", CLS[4][1]), ("不顯著 14,010", CLS[0][1])]
    for i, (lab, col) in enumerate(labels):
        xx = W + 2 * MARGIN + i * 210
        d.rectangle([xx, ly, xx + 26, ly + 20], fill=col, outline=(90, 90, 90))
        d.text((xx + 34, ly + 10), lab, font=font(FR, 20), fill=(60, 60, 60), anchor="lm")
    d.text((MARGIN, ly + 34), "雙變量 Moran's I = −0.443（p=0.001）；赤字區 7,911 格。"
                              "HH＝高赤字被高赤字包圍，非個別居民推論。", font=font(FR, 20), fill=(110, 110, 110))
    save(c, FIG / "fig7_mismatch.png"); print("fig7 combined done")


def fig8_quadrant():
    sai, gt = read(RAST / "sai.tif")
    base = map_image(sai, gt, GREEN, 0, 100, districts=True)
    W, H = base.size
    panel = 320
    c = Image.new("RGB", (W + panel + 3 * MARGIN, H + 2 * MARGIN + 90), (255, 255, 255))
    c.paste(base, (MARGIN, MARGIN + 40)); d = ImageDraw.Draw(c)
    d.text((W / 2 + MARGIN + panel / 2, 18), "",
           font=font(FB, 38), fill=(20, 20, 20), anchor="ma")
    data = json.loads((ROOT / "wp3_cases_vs_sai.json").read_text(encoding="utf-8"))
    to_m = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    qcol = {"low_supply_high_demand": (220, 30, 30), "high_supply_low_demand": (30, 70, 200),
            "high_supply_high_demand": (240, 170, 30), "low_supply_low_demand": (120, 120, 120)}
    quad = {}
    cases = []
    for f in ["opengreen_114E_coded.csv", "opengreen_114W_coded.csv",
              "opengreen_112_113_coded.csv", "opengreen_108_111_coded.csv"]:
        fp = ROOT / f
        if not fp.exists():
            continue
        for r in csv.DictReader(open(fp, encoding="utf-8-sig")):
            if r.get("lon") and r.get("lat"):
                cases.append((float(r["lon"]), float(r["lat"])))
    for r in data["cases"]:
        q = r["quadrant"]; quad[q] = quad.get(q, 0) + 1
        x, y = to_m.transform(r["lon"], r["lat"])
        col = int((x - gt[0]) / gt[1]); row = int((gt[3] - y) / (-gt[5]))
        if not (0 <= col < sai.shape[1] and 0 <= row < sai.shape[0]):
            continue
        px = MARGIN + col * SCALE; py = MARGIN + 40 + row * SCALE
        cc = qcol.get(q, (80, 80, 80))
        d.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(0, 0, 0))
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 255, 255))
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=cc)
    # stacked bar panel
    tot = sum(quad.values()) or 1
    bx = W + 2 * MARGIN; by = MARGIN + 70; bw = 200; bh = 520
    order = ["low_supply_high_demand", "low_supply_low_demand",
             "high_supply_high_demand", "high_supply_low_demand"]
    ycur = by
    for q in order:
        n = quad.get(q, 0)
        hgt = int(bh * n / tot)
        d.rectangle([bx, ycur, bx + bw, ycur + hgt], fill=qcol[q], outline=(255, 255, 255))
        if n:
            d.text((bx + bw / 2, ycur + hgt / 2), f"{n}（{100*n/tot:.1f}%）",
                   font=font(FB, 22), fill=(255, 255, 255) if q != "low_supply_low_demand" else (20, 20, 20),
                   anchor="mm")
        ycur += hgt
    d.text((bx + bw / 2, by - 30), "案例象限分布", font=font(FB, 24), fill=(30, 30, 30), anchor="ma")
    d.text((bx, by + bh + 24), "低供給·高需求", font=font(FR, 20), fill=(220, 30, 30))
    d.text((bx, by + bh + 50), "61.5% 落於赤字區；", font=font(FR, 20), fill=(90, 90, 90))
    d.text((bx, by + bh + 74), "座標為行政區質心近似", font=font(FR, 20), fill=(90, 90, 90))
    north(d, MARGIN + W - 60, MARGIN + 60); scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    colorbar(c, d, MARGIN, MARGIN + 40 + H + 26, W, GREEN, 0, 100, "分")
    save(c, FIG / "fig8_opengreen_on_sai.png"); print("fig8 pins+bar done", quad)


def main():
    # fig2_hillshade -> 圖 4-2 (研究區底圖)；其餘圖號已改由專用腳本產製：
    #   圖 2-1 -> make_fig9_vlr.py        圖 3-1 -> make_fig8_nmgci.py
    #   圖 4-1 -> make_fig1_fig10.py      圖 4-3 -> make_fig7_scenarios.py
    #   圖 5-1 -> make_fig3_composite.py  圖 5-2 -> make_fig4_pop_sai.py
    #   圖 5-3 -> make_fig5_mismatch.py   圖 5-4 -> make_fig6_opengreen.py
    fig2_hillshade()
    return 0


if __name__ == "__main__":
    sys.exit(main())
