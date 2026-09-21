# -*- coding: utf-8 -*-
"""Enhanced paper figures (PIL) — adds north arrow, scale bar, district
boundaries + labels, and ticked colour bars to the map figures, and axes to the
scatter.  Overwrites Paper/figures/*.png.

Run: python make_paper_figures_plus.py
"""
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
RAST = ROOT / "wp2_rasters"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
TPE_SHP = r"E:\SCI\TPC\臺北市區界圖_20220915\G97_A_CADIST_P.shp"   # 臺北市區界（權威，圖面用）
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
NODATA = -9999.0
SCALE = 5
MARGIN = 80

GREEN = [(0.0, (247, 252, 245)), (0.35, (199, 233, 192)), (0.7, (65, 171, 93)), (1.0, (0, 68, 27))]
BLUE = [(0.0, (247, 251, 255)), (0.5, (107, 174, 214)), (1.0, (8, 48, 107))]
DIV = [(0.0, (33, 102, 172)), (0.5, (247, 247, 247)), (1.0, (178, 24, 43))]
CLS = [(0.0, (225, 225, 225)), (0.2, (200, 60, 60)), (0.45, (60, 60, 200)),
       (0.7, (90, 170, 230)), (1.0, (230, 160, 40))]



def save(canvas, path):
    try:
        Image.Image.save(canvas, str(path))
    except OSError:
        alt = path.with_name(path.stem + '_new' + path.suffix)
        Image.Image.save(canvas, str(alt))
        print('  (locked) ->', alt.name)

def font(p, s):
    return ImageFont.truetype(p, s)


def read(path):
    ds = gdal.Open(str(path))
    a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    gt = ds.GetGeoTransform()
    return np.where(a == NODATA, np.nan, a), gt


def colormap(v, stops):
    v = np.clip(v, 0, 1)
    r = np.zeros_like(v); g = np.zeros_like(v); b = np.zeros_like(v)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        m = (v >= p0) & (v <= p1)
        t = np.where(p1 > p0, (v - p0) / (p1 - p0), 0)
        for o, x0, x1 in ((r, c0[0], c1[0]), (g, c0[1], c1[1]), (b, c0[2], c1[2])):
            o[m] = x0 + t[m] * (x1 - x0)
    return np.dstack([r, g, b]).astype(np.uint8)


def district_lines(gt, shape):
    tmp = ROOT / "_dline.geojson"
    g = gpd.read_file(SHP, encoding="utf-8")
    g = g[g["COUNTYNAME"] == "臺北市"].to_crs(3826)
    g.to_file(tmp, driver="GeoJSON")
    mem = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3826)
    mem.SetProjection(srs.ExportToWkt())
    v = ogr.Open(str(tmp))
    gdal.RasterizeLayer(mem, [1], v.GetLayer(), burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    mask = mem.GetRasterBand(1).ReadAsArray() > 0
    v = None; mem = None; tmp.unlink(missing_ok=True)
    line = np.zeros(shape, bool)
    line[1:] |= mask[1:] != mask[:-1]
    line[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    return line, mask


def district_points(gt, shape):
    g = admin_gdf()
    pts = []
    for _, r in g.iterrows():
        c = r.geometry.representative_point()
        col = int((c.x - gt[0]) / gt[1]); row = int((gt[3] - c.y) / (-gt[5]))
        if 0 <= col < shape[1] and 0 <= row < shape[0]:
            pts.append((col, row, r["TOWNNAME"]))
    return pts


LABEL_LOG = []


def reset_labels():
    LABEL_LOG.clear()


def record_label(fig, name, x, y):
    LABEL_LOG.append({"figure": fig, "name": name, "x": float(x), "y": float(y)})


def save_label_log(path):
    """Merge this run's labels into the shared label-position log."""
    import json
    prev = []
    if Path(path).exists():
        try:
            prev = json.loads(Path(path).read_text(encoding="utf-8"))
        except ValueError:
            prev = []
    figs = {e["figure"] for e in LABEL_LOG}
    out = [e for e in prev if e.get("figure") not in figs] + list(LABEL_LOG)
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(out)


def admin_gdf():
    """臺北市 12 區界（權威圖層，EPSG:3826）；欄位 TOWNNAME 供標註使用。"""
    g = gpd.read_file(TPE_SHP)
    if g.crs is None:
        g = g.set_crs(3826)
    g = g.to_crs(3826)
    if "TOWNNAME" not in g.columns:
        g = g.rename(columns={"TNAME": "TOWNNAME"})
    if "COUNTYNAME" not in g.columns:
        g["COUNTYNAME"] = "臺北市"
    return g


def point_in_district(g, name, x, y):
    """Return the district name containing (x, y) in EPSG:3826, else None."""
    from shapely.geometry import Point
    pt = Point(x, y)
    for _, r in g.iterrows():
        if r.geometry.contains(pt):
            return r["TOWNNAME"]
    return None


def admin_gdf():
    """Taipei City district polygons in EPSG:3826."""
    g = gpd.read_file(SHP, encoding="utf-8")
    return g[g["COUNTYNAME"] == "臺北市"].to_crs(3826)


def draw_admin(d, g, gt, scale, ox, oy):
    """Vector admin lines over a pasted raster map.

    市界 = black with a white halo; 區界 = grey with a white halo.
    """
    def to_px(coords):
        return [((x - gt[0]) / gt[1] * scale + ox, (gt[3] - y) / (-gt[5]) * scale + oy)
                for x, y in coords]

    for geom in g.geometry:
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            pts = to_px(poly.exterior.coords)
            d.line(pts, fill=(255, 255, 255), width=5, joint="curve")
            d.line(pts, fill=(105, 105, 105), width=2, joint="curve")
    outer = g.geometry.union_all().boundary
    rings = list(outer.geoms) if outer.geom_type == "MultiLineString" else [outer]
    for ring in rings:
        pts = to_px(ring.coords)
        d.line(pts, fill=(255, 255, 255), width=10, joint="curve")
        d.line(pts, fill=(10, 10, 10), width=5, joint="curve")


def north(d, x, y, s=46):
    d.polygon([(x, y), (x - s * 0.42, y + s), (x, y + s * 0.78), (x + s * 0.42, y + s)],
              fill=(40, 40, 40))
    d.text((x, y - 2), "N", font=font(FB, 30), fill=(20, 20, 20), anchor="ms")


def scalebar(d, x, y, gt, km=2):
    px = int(km * 1000 / abs(gt[1]) * SCALE)
    seg = px // km if km else px
    d.rectangle([x, y, x + px, y + 10], fill=(255, 255, 255), outline=(30, 30, 30))
    for i in range(km):
        for j in range(2):
            if (i + j) % 2 == 0:
                d.rectangle([x + (i * seg) + j * (seg // 2), y,
                             x + (i + 1) * seg + j * (seg // 2), y + 10], fill=(30, 30, 30))
    for i in range(km + 1):
        d.line([(x + i * seg, y + 10), (x + i * seg, y + 18)], fill=(30, 30, 30), width=2)
        d.text((x + i * seg, y + 22), f"{i}", font=font(FR, 22), fill=(40, 40, 40), anchor="ma")
    d.text((x + px / 2, y + 52), "km", font=font(FR, 22), fill=(40, 40, 40), anchor="ma")


def colorbar(canvas, d, x, y, w, stops, vmin, vmax, unit, h=26, markers=None):
    bar = colormap(np.linspace(0, 1, w).reshape(1, -1), stops)
    canvas.paste(Image.fromarray(np.repeat(bar, h, 0)), (x, y))
    d.rectangle([x, y, x + w, y + h], outline=(120, 120, 120))
    for frac in (0, .25, .5, .75, 1):
        xx = x + frac * w
        d.line([(xx, y + h), (xx, y + h + 6)], fill=(60, 60, 60), width=2)
        v = vmin + frac * (vmax - vmin)
        d.text((xx, y + h + 10), f"{v:g}", font=font(FR, 22), fill=(40, 40, 40), anchor="ma")
    for frac, label, col in (markers or []):
        xx = x + (frac - vmin) / (vmax - vmin) * w
        d.line([(xx, y - 12), (xx, y + h + 12)], fill=col, width=4)
        d.text((xx, y - 16), label, font=font(FR, 20), fill=col, anchor="ms")
    d.text((x + w + 16, y + h / 2), unit, font=font(FR, 24), fill=(40, 40, 40), anchor="lm")


def render_map(path, title, arr, gt, stops, vmin, vmax, unit,
               districts=True, labels=True, cb=True, markers=None):
    valid = np.isfinite(arr)
    v = np.zeros_like(arr)
    v[valid] = (arr[valid] - vmin) / (vmax - vmin)
    img = np.full((*arr.shape, 3), 255, np.uint8)
    img[valid] = colormap(v, stops)[valid]
    if districts:
        line, _ = district_lines(gt, arr.shape)
        img[line] = (70, 70, 70)
    im = Image.fromarray(img).resize(
        (arr.shape[1] * SCALE, arr.shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    top = 70 if cb else 40
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 120), (255, 255, 255))
    canvas.paste(im, (MARGIN, MARGIN + top))
    d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 18), title, font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    if labels:
        for col, row, name in district_points(gt, arr.shape):
            px = MARGIN + col * SCALE; py = MARGIN + top + row * SCALE
            d.text((px, py), name, font=font(FR, 22), fill=(25, 25, 25), anchor="mm",
                   stroke_width=3, stroke_fill=(255, 255, 255))
    north(d, MARGIN + W - 60, MARGIN + top + 20)
    scalebar(d, MARGIN + 30, MARGIN + top + H - 90, gt)
    if cb:
        colorbar(canvas, d, MARGIN, MARGIN + top + H + 26, W, stops, vmin, vmax, unit,
                 markers=markers)
    save(canvas, path)
    print("saved", path.name, canvas.size)


def fig2(gt, shape):
    line, mask = district_lines(gt, shape)
    img = np.full((*shape, 3), 255, np.uint8)
    img[mask] = (224, 234, 224); img[line] = (0, 90, 45)
    im = Image.fromarray(img).resize((shape[1] * SCALE, shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 60), (255, 255, 255))
    canvas.paste(im, (MARGIN, MARGIN + 40)); d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 18), "", font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    for col, row, name in district_points(gt, shape):
        px = MARGIN + col * SCALE; py = MARGIN + 40 + row * SCALE
        d.text((px, py), name, font=font(FR, 24), fill=(25, 25, 25), anchor="mm",
               stroke_width=3, stroke_fill=(255, 255, 255))
    north(d, MARGIN + W - 60, MARGIN + 60)
    scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    save(canvas, FIG / "fig2_study_area.png"); print("saved fig2_study_area.png")


def fig6():
    a, _ = read(RAST / "sai.tif"); p, _ = read(RAST / "population.tif")
    m = np.isfinite(a) & np.isfinite(p) & (p > 0)
    x = np.log10(p[m] + 1); y = a[m]
    rng = np.random.default_rng(0)
    idx = rng.choice(x.size, min(8000, x.size), replace=False); x, y = x[idx], y[idx]
    W, H, ML, MB, MT, MR = 1300, 800, 130, 110, 90, 60
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 26), "", font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    x0, x1 = ML, W - MR; y0, y1 = MT, H - MB
    for gy in range(0, 101, 20):
        yy = y1 - gy / 100 * (y1 - y0)
        d.line([(x0, yy), (x1, yy)], fill=(225, 225, 225))
        d.text((x0 - 12, yy), f"{gy}", font=font(FR, 22), fill=(60, 60, 60), anchor="rm")
    for gx in np.arange(math.floor(x.min()), x.max() + 0.5, 0.5):
        xx = x0 + (gx - x.min()) / (x.max() - x.min()) * (x1 - x0)
        d.line([(xx, y0), (xx, y1)], fill=(238, 238, 238))
        d.text((xx, y1 + 12), f"{gx:g}", font=font(FR, 22), fill=(60, 60, 60), anchor="ma")
    d.line([(x0, y0), (x0, y1)], fill=(30, 30, 30), width=2)
    d.line([(x0, y1), (x1, y1)], fill=(30, 30, 30), width=2)
    for xi, yi in zip(x, y):
        px = x0 + (xi - x.min()) / (x.max() - x.min()) * (x1 - x0)
        py = y1 - yi / 100 * (y1 - y0)
        d.ellipse([px, py, px + 2, py + 2], fill=(30, 120, 70))
    b = ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum()
    a0 = y.mean() - b * x.mean()
    xs = np.array([x.min(), x.max()]); ys = a0 + b * xs
    d.line([(x0, y1 - ys[0] / 100 * (y1 - y0)), (x1, y1 - ys[1] / 100 * (y1 - y0))],
           fill=(200, 40, 40), width=5)
    d.text((x0 + (x1 - x0) / 2, H - 60), "log10(人口密度 + 1)", font=font(FR, 26), fill=(60, 60, 60), anchor="ma")
    d.text((40, (y0 + y1) / 2), "SAI", font=font(FR, 26), fill=(60, 60, 60), anchor="mm")
    d.text((x1, y0 + 4), f"斜率 {b:.1f}/log10(人口)　n={x.size}", font=font(FR, 24),
           fill=(120, 120, 120), anchor="ra")
    c.save(FIG / "fig6_pop_sai.png"); print("saved fig6_pop_sai.png", round(float(b), 2))


def fig3():
    from wp2_green_accessibility import master_grid, warp, DEM, CHM, CHM_NODATA, DEM_NODATA
    bounds = master_grid()
    dem, gt = warp(DEM, bounds, gdal.GRA_Bilinear, gdal.GDT_Float32, DEM_NODATA)
    chm, _ = warp(CHM, bounds, gdal.GRA_Average, gdal.GDT_Float32, CHM_NODATA)
    dem = np.where((dem == DEM_NODATA) | ~np.isfinite(dem), np.nan, dem)
    chm = np.where((chm == CHM_NODATA) | ~np.isfinite(chm), np.nan, chm)
    entries = [(dem, 0, 600, "m", "(a) 高程"), (chm, 0, 12, "m", "(b) 樹冠高度")]
    panels = []
    for arr, vmin, vmax, unit, lab in entries:
        valid = np.isfinite(arr); v = np.zeros_like(arr); v[valid] = (arr[valid] - vmin) / (vmax - vmin)
        img = np.full((*arr.shape, 3), 255, np.uint8); img[valid] = colormap(v, GREEN)[valid]
        line, _ = district_lines(gt, arr.shape); img[line] = (70, 70, 70)
        im = Image.fromarray(img).resize((arr.shape[1] * SCALE, arr.shape[0] * SCALE), Image.NEAREST)
        panels.append((im, unit, lab, vmin, vmax))
    W = panels[0][0].width; H = panels[0][0].height
    canvas = Image.new("RGB", (W * 2 + 3 * MARGIN, H + 2 * MARGIN + 150), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.text((canvas.width / 2, 18), "", font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    for i, (im, unit, lab, vmin, vmax) in enumerate(panels):
        x = MARGIN + i * (W + MARGIN); y = MARGIN + 40
        canvas.paste(im, (x, y))
        d.text((x + W / 2, y - 6), lab, font=font(FB, 28), fill=(30, 30, 30), anchor="ma")
        colorbar(canvas, d, x, y + H + 20, W, GREEN, vmin, vmax, unit)
    north(d, MARGIN + W - 60, MARGIN + 60)
    scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    save(canvas, FIG / "fig3_elevation_canopy.png"); print("saved fig3_elevation_canopy.png")


def main():
    sai, gt = read(RAST / "sai.tif")
    canopy, _ = read(RAST / "canopy_supply.tif")
    mis, _ = read(RAST / "mismatch_deficit.tif")
    clu, _ = read(RAST / "lisa_cluster.tif")
    fig2(gt, sai.shape)
    fig3()
    render_map(FIG / "fig4_sigmaH_canopy.png", "",
               canopy, gt, GREEN, 0, 12, "m")
    # 圖 5：SAI，並於色尺標示面積加權 43.06 與人口加權 29.49
    render_map(FIG / "fig5_sai.png", "",
               sai, gt, GREEN, 0, 100, "分",
               markers=[(43.06, "面積加權 43.06", (200, 40, 40)),
                        (29.49, "人口加權 29.49", (40, 60, 200))])
    mmax = float(np.nanmax(np.abs(mis)))
    render_map(FIG / "fig7_mismatch.png", "",
               mis, gt, DIV, -mmax, mmax, "z")
    render_map(FIG / "fig7b_lisa.png", "",
               clu, gt, CLS, 0, 4, "1=HH 2=LL 3=LH 4=HL", labels=False)
    fig6()
    # fig8: SAI + case points
    from pyproj import Transformer
    import csv
    to_m = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    valid = np.isfinite(sai)
    v = np.clip(sai / 100, 0, 1)
    img = np.full((*sai.shape, 3), 255, np.uint8); img[valid] = colormap(v, GREEN)[valid]
    line, _ = district_lines(gt, sai.shape); img[line] = (70, 70, 70)
    im = Image.fromarray(img).resize((sai.shape[1] * SCALE, sai.shape[0] * SCALE), Image.NEAREST)
    W, H = im.size
    canvas = Image.new("RGB", (W + 2 * MARGIN, H + 2 * MARGIN + 120), (255, 255, 255))
    canvas.paste(im, (MARGIN, MARGIN + 40)); d = ImageDraw.Draw(canvas)
    d.text((W / 2 + MARGIN, 18), "", font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    n = 0
    for name in ["opengreen_114E_coded.csv", "opengreen_114W_coded.csv",
                 "opengreen_112_113_coded.csv", "opengreen_108_111_coded.csv"]:
        fp = ROOT / name
        if not fp.exists():
            continue
        for r in csv.DictReader(open(fp, encoding="utf-8-sig")):
            if not (r.get("lon") and r.get("lat")):
                continue
            x, y = to_m.transform(float(r["lon"]), float(r["lat"]))
            col = int((x - gt[0]) / gt[1]); row = int((gt[3] - y) / (-gt[5]))
            if not (0 <= col < sai.shape[1] and 0 <= row < sai.shape[0]):
                continue
            n += 1
            px = MARGIN + col * SCALE; py = MARGIN + 40 + row * SCALE
            d.ellipse([px - 8, py - 8, px + 8, py + 8], outline=(200, 30, 30), width=4)
    north(d, MARGIN + W - 60, MARGIN + 60)
    scalebar(d, MARGIN + 30, MARGIN + 40 + H - 90, gt)
    colorbar(canvas, d, MARGIN, MARGIN + 40 + H + 26, W, GREEN, 0, 100, "分")
    d.text((MARGIN, 40 + H + 100 + MARGIN - 60), f"紅圈＝Open Green 案例（n={n}，行政區質心近似）",
           font=font(FR, 24), fill=(80, 80, 80))
    save(canvas, FIG / "fig8_opengreen_on_sai.png"); print("saved fig8_opengreen_on_sai.png", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
