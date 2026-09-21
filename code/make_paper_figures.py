# -*- coding: utf-8 -*-
"""Render paper figures (PIL; matplotlib is broken on this host).

Maps from wp2_rasters/*.tif with a district-boundary overlay, plus a scenario
comparison chart.  Outputs PNGs to Paper/figures/.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
RAST = ROOT / "wp2_rasters"
OUT = ROOT / "Paper" / "figures"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
FONT_B = r"C:\Windows\Fonts\msjhbd.ttc"
FONT_R = r"C:\Windows\Fonts\msjh.ttc"
SCALE = 4            # pixels per grid cell
MARGIN = 70
NODATA = -9999.0


def font(path, size):
    return ImageFont.truetype(path, size)


def read(path):
    ds = gdal.Open(str(path))
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform()
    return arr, gt


def colormap(vals, stops):
    """vals in [0,1]; stops = list of (pos, (r,g,b))."""
    v = np.clip(vals, 0, 1)
    r = np.zeros_like(v); g = np.zeros_like(v); b = np.zeros_like(v)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        m = (v >= p0) & (v <= p1)
        t = np.zeros_like(v)
        t[m] = (v[m] - p0) / (p1 - p0) if p1 > p0 else 0
        for ch, arr_out, c_0, c_1 in ((0, r, c0[0], c1[0]), (1, g, c0[1], c1[1]), (2, b, c0[2], c1[2])):
            arr_out[m] = c_0 + t[m] * (c_1 - c_0)
    return np.dstack([r, g, b]).astype(np.uint8)


def boundary_mask(arr, gt):
    """Rasterise Taipei district boundaries to the raster grid."""
    h, w = arr.shape
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3826)
    mem.SetProjection(srs.ExportToWkt())
    g = gpd.read_file(SHP, encoding="utf-8")
    g = g[g["COUNTYNAME"] == "臺北市"]
    tmp = ROOT / "_fig_bounds.geojson"
    g.to_crs(3826).to_file(tmp, driver="GeoJSON")
    v = ogr.Open(str(tmp))
    gdal.RasterizeLayer(mem, [1], v.GetLayer(), burn_values=[1],
                        options=["ALL_TOUCHED=TRUE"])
    v = None
    mask = mem.GetRasterBand(1).ReadAsArray() > 0
    mem = None
    tmp.unlink(missing_ok=True)
    return mask


def render_map(arr, gt, path, title, stops, vmin, vmax, boundary=True):
    valid = np.isfinite(arr) & (arr != NODATA)
    v = np.zeros_like(arr)
    v[valid] = (arr[valid] - vmin) / (vmax - vmin)
    rgb = colormap(v, stops)
    img = np.full((*arr.shape, 3), 255, np.uint8)
    img[valid] = rgb[valid]
    if boundary:
        bm = boundary_mask(arr, gt)
        img[bm & ~valid] = (210, 210, 210)
    im = Image.fromarray(np.flipud(img)).resize(
        (arr.shape[1] * SCALE, arr.shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 60), (255, 255, 255))
    canvas.paste(im, (MARGIN, MARGIN + 40))
    d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 20), title, font=font(FONT_B, 46), fill=(20, 20, 20), anchor="ma")
    # colour bar
    cw, ch = W, 26
    bar = colormap(np.linspace(0, 1, cw).reshape(1, -1), stops)
    bar = np.repeat(bar, ch, axis=0)
    canvas.paste(Image.fromarray(bar), (MARGIN, H + 50 + MARGIN))
    d.text((MARGIN, H + 82 + MARGIN), f"{vmin:g}", font=font(FONT_R, 30), fill=(80, 80, 80))
    d.text((W + MARGIN, H + 82 + MARGIN), f"{vmax:g}", font=font(FONT_R, 30),
           fill=(80, 80, 80), anchor="ra")
    canvas.save(path)
    print("saved", path.name, canvas.size)


def render_bars(data, path, title):
    labels = list(data.keys())
    metrics = [("pop_weighted_sai_gain", "人口加權 SAI 增益（分）", (24, 106, 62)),
               ("beneficiary_pop_units", "受益人口（相對單位）", (24, 90, 160))]
    W, H = 1500, 620
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.text((W / 2, 20), title, font=font(FONT_B, 40), fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 70), "Model-based What-if Simulation（內部等量增冠假設；非經驗成效、非因果）",
           font=font(FONT_R, 26), fill=(190, 40, 40), anchor="ma")
    left, top, bw = 320, 130, 280
    for mi, (key, lab, col) in enumerate(metrics):
        vals = [data[l][key] for l in labels]
        mx = max(vals) or 1
        d.text((30, top + mi * 240 + 70), lab, font=font(FONT_R, 28), fill=(60, 60, 60))
        for i, (l, v) in enumerate(zip(labels, vals)):
            x = left + i * (bw + 90)
            bh = int(180 * v / mx)
            d.rectangle([x, top + mi * 240 + 180 - bh, x + bw, top + mi * 240 + 180], fill=col)
            d.text((x + bw / 2, top + mi * 240 + 190), f"{v:,.3g}", font=font(FONT_R, 26),
                   fill=(40, 40, 40), anchor="ma")
            d.text((x + bw / 2, top + mi * 240 + 224), l, font=font(FONT_R, 24),
                   fill=(60, 60, 60), anchor="ma")
    canvas.save(path)
    print("saved", path.name, canvas.size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GRN = [(0.0, (247, 252, 245)), (0.35, (199, 233, 192)), (0.7, (65, 171, 93)), (1.0, (0, 68, 27))]
    BLU = [(0.0, (247, 251, 255)), (0.5, (107, 174, 214)), (1.0, (8, 48, 107))]
    DIV = [(0.0, (33, 102, 172)), (0.5, (247, 247, 247)), (1.0, (178, 24, 43))]
    CLS = [(0.0, (230, 230, 230)), (0.25, (200, 60, 60)), (0.5, (60, 60, 200)),
           (0.75, (90, 170, 230)), (1.0, (230, 160, 40))]

    if (RAST / "canopy_supply.tif").exists():
        a, gt = read(RAST / "canopy_supply.tif")
        arr = np.where(a == NODATA, np.nan, a)
        render_map(arr, gt, OUT / "fig4_sigmaH_canopy.png",
                   "", GRN, 0, 12)
    if (RAST / "sai.tif").exists():
        a, gt = read(RAST / "sai.tif")
        arr = np.where(a == NODATA, np.nan, a)
        render_map(arr, gt, OUT / "fig5_sai.png",
                   "", GRN, 0, 100)
    if (RAST / "mismatch_deficit.tif").exists():
        a, gt = read(RAST / "mismatch_deficit.tif")
        arr = np.where(a == NODATA, np.nan, a)
        m = np.nanmax(np.abs(arr))
        render_map(arr, gt, OUT / "fig7_mismatch.png",
                   "", DIV, -m, m)
    if (RAST / "lisa_cluster.tif").exists():
        a, gt = read(RAST / "lisa_cluster.tif")
        arr = np.where(a == NODATA, np.nan, a)
        render_map(arr, gt, OUT / "fig7b_lisa.png",
                   "", CLS, 0, 4)

    sim = ROOT / "wp4_scenario_simulator.json"
    if sim.exists():
        import json
        data = json.loads(sim.read_text(encoding="utf-8"))["scenarios"]
        render_bars(data, OUT / "fig9_scenarios.png",
                    "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
