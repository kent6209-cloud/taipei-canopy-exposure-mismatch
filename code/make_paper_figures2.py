# -*- coding: utf-8 -*-
"""Render remaining paper figures (PIL; matplotlib is broken on this host).

  fig1  research framework (schematic)
  fig2  study area (Taipei outline + districts)
  fig3  elevation & canopy (two panels)
  fig6  population x SAI (scatter + trend)
  fig10 NMGCI four-component framework (schematic)

Outputs PNGs to Paper/figures/.
"""
import sys
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RAST = ROOT / "wp2_rasters"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
NODATA = -9999.0


def font(p, s):
    return ImageFont.truetype(p, s)


def read(path):
    ds = gdal.Open(str(path))
    a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    return np.where(a == NODATA, np.nan, a), tuple(x for x in [ds.GetGeoTransform()[0],
                  ds.GetGeoTransform()[1], 0, ds.GetGeoTransform()[3], 0,
                  ds.GetGeoTransform()[5]])


def green_map(arr, vmin, vmax):
    v = np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    stops = [(0.0, (247, 252, 245)), (0.35, (199, 233, 192)), (0.7, (65, 171, 93)),
             (1.0, (0, 68, 27))]
    r = np.zeros_like(v); g = np.zeros_like(v); b = np.zeros_like(v)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        m = (v >= p0) & (v <= p1) & np.isfinite(arr)
        t = np.where(p1 > p0, (v - p0) / (p1 - p0), 0)
        for o, x0, x1 in ((r, c0[0], c1[0]), (g, c0[1], c1[1]), (b, c0[2], c1[2])):
            o[m] = x0 + t[m] * (x1 - x0)
    img = np.full((*arr.shape, 3), 255, np.uint8)
    img[np.isfinite(arr)] = np.dstack([r, g, b])[np.isfinite(arr)].astype(np.uint8)
    return img


def box(d, xy, text, fill, fg=(20, 20, 20), fs=30, fb=FB):
    d.rounded_rectangle(xy, radius=14, fill=fill, outline=(120, 130, 120), width=2)
    d.multiline_text(((xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2), text,
                     font=font(fb, fs), fill=fg, anchor="mm", align="center")


def arrow(d, x0, y0, x1, y1, col=(90, 100, 90)):
    d.line([(x0, y0), (x1, y1)], fill=col, width=4)
    import math
    a = math.atan2(y1 - y0, x1 - x0)
    for da in (2.6, -2.6):
        d.line([(x1, y1), (x1 + 16 * math.cos(a + da), y1 + 16 * math.sin(a + da))],
               fill=col, width=4)


def fig1():
    W, H = 1660, 560
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 30), "", font=font(FB, 44), fill=(20, 20, 20), anchor="ma")
    steps = ["資料取得\nCHMv2／DEM\n行道樹／人口", "資料品管\nEvidence\nFreeze",
             "供給側\nΣH／MGCI\n高程帶", "需求側\nSAI 500 m\n人口加權",
             "空間錯置\nP1／LISA\nMoran's I", "企業／案例\nOpen Green\n企業專案",
             "多效益配置\n情境模擬\n四層帳本", "治理模型\nNMGCI\n政策工具"]
    n = len(steps); bw, bh, gap = 178, 160, 22
    x0 = 34
    for i, s in enumerate(steps):
        x = x0 + i * (bw + gap)
        box(d, [x, 150, x + bw, 150 + bh], s, (233, 242, 232), fs=19)
        if i < n - 1:
            arrow(d, x + bw + 2, 230, x + bw + gap - 2, 230)
    c.save(FIG / "fig1_framework.png"); print("fig1 done")


def fig10():
    W, H = 1200, 700
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 30), "", font=font(FB, 44), fill=(20, 20, 20), anchor="ma")
    comp = {"Source\n生態供給\n近山樹冠／碳代理": (420, 130), "Demand\n日常需求\n平地綠意可達性": (760, 130),
            "Capital\n資本配置\n企業投入類型": (420, 420), "Coupling\n制度耦合\n資料／社群／制度": (760, 420)}
    for txt, (x, y) in comp.items():
        box(d, [x - 150, y, x + 150, y + 160], txt, (233, 242, 232), fs=26)
    arrow(d, 570, 210, 610, 210); arrow(d, 910, 210, 910, 420)
    arrow(d, 610, 500, 570, 500); arrow(d, 420, 420, 420, 290)
    d.text((W / 2, 640), "四層帳本：L1 排放｜L2 碳移除｜L3 自然調適｜L4 社會治理（不得合成單一減碳量）",
           font=font(FR, 26), fill=(80, 80, 80), anchor="ma")
    c.save(FIG / "fig10_nmgci.png"); print("fig10 done")


def fig2(gt, shape):
    tmp = ROOT / "_fig2.geojson"
    mem = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3826)
    mem.SetProjection(srs.ExportToWkt())
    import geopandas as gpd
    g = gpd.read_file(SHP, encoding="utf-8")
    tpe = g[g["COUNTYNAME"] == "臺北市"].to_crs(3826)
    tpe.to_file(tmp, driver="GeoJSON")
    v = ogr.Open(str(tmp))
    gdal.RasterizeLayer(mem, [1], v.GetLayer(), burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    mask = mem.GetRasterBand(1).ReadAsArray() > 0
    mem = None; v = None; tmp.unlink(missing_ok=True)
    line = np.zeros(shape, np.uint8)
    for i in range(1, shape[0] - 1):
        line[i] = np.where(mask[i] != mask[i - 1], 1, line[i])
    img = np.full((*shape, 3), 255, np.uint8)
    img[mask] = (222, 233, 222); img[line.astype(bool) & mask] = (0, 90, 45)
    im = Image.fromarray(np.flipud(img)).resize((shape[1] * 3, shape[0] * 3), Image.NEAREST)
    W, H = im.size
    c = Image.new("RGB", (W + 120, H + 160), (255, 255, 255)); c.paste(im, (60, 90))
    d = ImageDraw.Draw(c)
    d.text((W / 2 + 60, 30), "", font=font(FB, 44), fill=(20, 20, 20), anchor="ma")
    d.text((60, H + 110), "底圖：臺北市行政區界（EPSG:3826），100 m 分析網格範圍",
           font=font(FR, 26), fill=(80, 80, 80))
    c.save(FIG / "fig2_study_area.png"); print("fig2 done")


def fig3():
    from wp2_green_accessibility import master_grid, warp, DEM, CHM, CHM_NODATA, DEM_NODATA
    bounds = master_grid()
    dem, gt = warp(DEM, bounds, gdal.GRA_Bilinear, gdal.GDT_Float32, DEM_NODATA)
    chm, _ = warp(CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, CHM_NODATA)
    dem = np.where((dem == DEM_NODATA) | ~np.isfinite(dem), np.nan, dem)
    chm = np.where((chm == CHM_NODATA) | ~np.isfinite(chm), np.nan, chm)
    imgs = [green_map(np.clip(dem, 0, 600), 0, 600), green_map(chm, 0, 12)]
    titles = ["(a) 高程（m）", "(b) 樹冠高度（m）"]
    panel = [Image.fromarray(np.flipud(x)).resize((x.shape[1] * 3, x.shape[0] * 3), Image.NEAREST)
             for x in imgs]
    W = panel[0].width * 2 + 60; H = panel[0].height
    c = Image.new("RGB", (W + 80, H + 150), (255, 255, 255))
    c.paste(panel[0], (40, 90)); c.paste(panel[1], (panel[0].width + 60, 90))
    d = ImageDraw.Draw(c)
    d.text((W / 2 + 40, 26), "", font=font(FB, 44), fill=(20, 20, 20), anchor="ma")
    d.text((40 + panel[0].width / 2, 80 + H), titles[0], font=font(FR, 30), fill=(60, 60, 60), anchor="ma")
    d.text((60 + panel[0].width + panel[0].width / 2, 80 + H), titles[1],
           font=font(FR, 30), fill=(60, 60, 60), anchor="ma")
    c.save(FIG / "fig3_elevation_canopy.png"); print("fig3 done")


def fig6():
    a, _ = read(RAST / "sai.tif"); p, _ = read(RAST / "population.tif")
    m = np.isfinite(a) & np.isfinite(p) & (p > 0)
    x = np.log10(p[m] + 1); y = a[m]
    rng = np.random.default_rng(0)
    idx = rng.choice(x.size, min(6000, x.size), replace=False)
    x, y = x[idx], y[idx]
    W, H, M = 1200, 800, 110
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 30), "", font=font(FB, 42), fill=(20, 20, 20), anchor="ma")
    for xi, yi in zip(x, y):
        px = M + (xi - x.min()) / (x.max() - x.min()) * (W - 2 * M)
        py = H - M - (yi - 0) / 100 * (H - 2 * M)
        d.ellipse([px, py, px + 2, py + 2], fill=(30, 120, 70))
    # trend (OLS closed form)
    b = ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum()
    a0 = y.mean() - b * x.mean()
    xs = np.array([x.min(), x.max()]); ys = a0 + b * xs
    d.line([(M + (xs[0] - x.min()) / (x.max() - x.min()) * (W - 2 * M),
             H - M - ys[0] / 100 * (H - 2 * M)),
            (M + (xs[1] - x.min()) / (x.max() - x.min()) * (W - 2 * M),
             H - M - ys[1] / 100 * (H - 2 * M))], fill=(200, 40, 40), width=5)
    d.text((W / 2, H - 60), f"斜率 {b:.1f}／log10(人口)　（n 抽樣 {x.size}）",
           font=font(FR, 28), fill=(80, 80, 80), anchor="ma")
    d.text((W / 2, H - 24), "x：log10(人口密度+1)　y：SAI（0–100）",
           font=font(FR, 26), fill=(120, 120, 120), anchor="ma")
    c.save(FIG / "fig6_pop_sai.png"); print("fig6 done", round(float(b), 2))


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig1(); fig10()
    a, gt = read(RAST / "sai.tif") if (RAST / "sai.tif").exists() else (None, None)
    if a is not None:
        fig2(gt, a.shape); fig3(); fig6()
    return 0


if __name__ == "__main__":
    sys.exit(main())
