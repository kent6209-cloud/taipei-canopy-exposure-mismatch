# -*- coding: utf-8 -*-
"""Render the A1 (594 x 841 mm, 300 dpi) computer-map competition poster for
Taipei City: canopy height (CHMv2) x street trees (Taipei tree inventory).

Layout
------
header
row 1 : canopy-height map | street-tree map
row 2 : overlay map       | locator + legend + scale + north arrow + statistics
footer: data sources and method

Statistics are read from taipei_poster_stats.json (native CHMv2; areas converted
from Web Mercator to true ground area, ~1.08 m at Taipei's latitude).
"""
import csv
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely.geometry as sgeom
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pyproj import Transformer

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
CHM = str(ROOT / "county" / "臺北市.tif")
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
TREE_CSV = Path(r"E:\SCI\TPC\tree\TaipeiTree.csv")
STATS = ROOT / "taipei_poster_stats.json"
BOUNDARY = str(ROOT / "taiwan_boundary_3857.shp")
OUT = ROOT / "taipei_canopy_poster_A1.png"
PREVIEW = ROOT / "taipei_canopy_poster_A1_preview.png"

FONT_REG = r"C:\Windows\Fonts\msjh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msjhbd.ttc"

DPI = 300
PX_MM = DPI / 25.4
W = round(594 * PX_MM)
H = round(841 * PX_MM)

MARGIN = 300
GAP = 130
HEADER_H = 790
FOOTER_H = 560
CAPTION_H = 96
ROW_GAP = 60
FOOTER_FONT = 52
FOOTER_LEAD = 78
PAD_M = 489.0
RES = 7.5
NODATA = 255
VMAX = 50
TREE_HEIGHT_CAP = 60.0

INK = (28, 32, 30)
SUB = (96, 104, 100)
ACCENT = (24, 106, 62)
ACCENT_D = (16, 74, 44)
BORDER = (204, 211, 205)
PANEL_BG = (247, 249, 246)
CITY_FILL = (236, 240, 235)

PALETTE = [
    "0 224 222 210", "2 84 140 88", "5 74 152 82", "10 116 180 94",
    "15 156 202 96", "20 198 208 88", "25 216 190 74", "30 196 148 60",
    "35 164 108 50", "40 132 80 42", "50 104 62 38",
]
TREE_CLASS_EDGES = [0.0, 5.0, 10.0, 15.0, 20.0, 1e9]
TREE_CLASS_LABELS = ["< 5", "5–10", "10–15", "15–20", "20 以上"]
TREE_COLORS = [
    (44, 123, 182, 240), (77, 175, 74, 240), (254, 196, 79, 240),
    (240, 59, 32, 240), (117, 42, 131, 240),
]
CANOPY_MIDS = [1, 3, 7, 12, 17, 22, 27, 32, 40]

TO_WM = Transformer.from_crs("EPSG:3826", "EPSG:3857", always_xy=True)
TO_LL = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

_FONTS = {}


def font(path, size):
    key = (path, size)
    if key not in _FONTS:
        try:
            _FONTS[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONTS[key] = ImageFont.truetype(FONT_REG, size)
    return _FONTS[key]


def build_lut():
    stops = [tuple(map(int, line.split())) for line in PALETTE]
    lut = np.zeros((256, 3), np.uint8)
    for i in range(256):
        for j in range(len(stops) - 1):
            v0, r0, g0, b0 = stops[j]
            v1, r1, g1, b1 = stops[j + 1]
            if v0 <= i <= v1:
                t = (i - v0) / max(1, v1 - v0)
                lut[i] = (int(r0 + t * (r1 - r0)), int(g0 + t * (g1 - g0)),
                          int(b0 + t * (b1 - b0)))
                break
    return lut


def load_taipei():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    return gdf[gdf["COUNTYNAME"] == "臺北市"].to_crs(3857).reset_index(drop=True)


def load_trees(city):
    xs, ys, hs, dist = [], [], [], []
    with open(TREE_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                h = float(row["TreeHeight"])
                x = float(row["TWD97X"])
                y = float(row["TWD97Y"])
            except (TypeError, ValueError):
                continue
            if not 0.0 < h <= TREE_HEIGHT_CAP:
                continue
            wx, wy = TO_WM.transform(x, y)
            xs.append(wx)
            ys.append(wy)
            hs.append(h)
            dist.append(row["Dist"].strip())
    pts = gpd.GeoDataFrame({"height": hs, "district": dist},
                           geometry=gpd.points_from_xy(xs, ys), crs=3857)
    return pts[pts.geometry.within(city.buffer(60))].reset_index(drop=True)


def warp_canopy(extent):
    xmin, ymin, xmax, ymax = extent
    tmp = ROOT / "_tpe_disp.tif"
    opts = gdal.WarpOptions(
        format="GTiff", outputBounds=(xmin, ymin, xmax, ymax), dstSRS="EPSG:3857",
        xRes=RES, yRes=RES, resampleAlg=gdal.GRA_Average, outputType=gdal.GDT_Byte,
        dstNodata=NODATA, multithread=True, warpMemoryLimit=1024,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"])
    gdal.Warp(str(tmp), CHM, options=opts)
    ds = gdal.Open(str(tmp))
    gt = ds.GetGeoTransform()
    gw, gh = ds.RasterXSize, ds.RasterYSize
    arr = ds.GetRasterBand(1).ReadAsArray()
    ds = None
    tmp.unlink(missing_ok=True)
    return arr, gt, gw, gh


def _ogr_layer(geoms, rings):
    src = ogr.GetDriverByName("Memory").CreateDataSource("v")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    layer = src.CreateLayer("l", srs=srs,
                            geom_type=ogr.wkbLineString if rings else ogr.wkbMultiPolygon)
    fdef = layer.GetLayerDefn()
    for geom in geoms:
        if rings:
            polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
            for poly in polys:
                for ring in [poly.exterior, *poly.interiors]:
                    feat = ogr.Feature(fdef)
                    feat.SetGeometry(ogr.CreateGeometryFromWkb(ring.wkb))
                    layer.CreateFeature(feat)
        else:
            feat = ogr.Feature(fdef)
            feat.SetGeometry(ogr.CreateGeometryFromWkb(geom.wkb))
            layer.CreateFeature(feat)
    return src, layer


def rasterize(gt, w, h, geoms, rings=False):
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    mem.SetProjection("EPSG:3857")
    mem.GetRasterBand(1).Fill(0)
    src, layer = _ogr_layer(geoms, rings)
    gdal.RasterizeLayer(mem, [1], layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    arr = mem.GetRasterBand(1).ReadAsArray() > 0
    mem = None
    src = None
    return arr


def world_to_px(gt, xs, ys):
    return ((np.asarray(xs) - gt[0]) / gt[1], (gt[3] - np.asarray(ys)) / (-gt[5]))


def scaled_gt(gt, gw, gh, pw, ph):
    return (gt[0], gt[1] * gw / pw, 0.0, gt[3], 0.0, gt[5] * gh / ph)


def disk_offsets(radius):
    r = int(np.ceil(radius))
    return [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx <= radius * radius + 0.5]


def scatter(rgba, px, py, cls, colors, radius):
    h, w = rgba.shape[:2]
    for cid, color in enumerate(colors):
        sel = cls == cid
        if not sel.any():
            continue
        ys = np.round(py[sel]).astype(np.int64)
        xs = np.round(px[sel]).astype(np.int64)
        for dy, dx in disk_offsets(radius):
            yy = ys + dy
            xx = xs + dx
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            rgba[yy[ok], xx[ok]] = color
    return rgba


def overlay_line(img, mask, color, alpha, grow=0):
    if grow:
        mask = np.array(Image.fromarray((mask * 255).astype(np.uint8), "L")
                        .filter(ImageFilter.MaxFilter(grow))) > 0
    layer = np.zeros((*mask.shape, 4), np.uint8)
    layer[mask] = (*color, alpha)
    return Image.alpha_composite(img, Image.fromarray(layer, "RGBA"))


def tree_class_ids(heights):
    ids = np.zeros(len(heights), np.int64)
    for i in range(len(TREE_CLASS_EDGES) - 1):
        lo, hi = TREE_CLASS_EDGES[i], TREE_CLASS_EDGES[i + 1]
        ids[(heights >= lo) & (heights < hi)] = i
    return ids


def canopy_image(arr, lut):
    rgb = np.dstack([lut[arr], np.where(arr == NODATA, 0, 255).astype(np.uint8)])
    base = Image.new("RGBA", (arr.shape[1], arr.shape[0]), (*PANEL_BG, 255))
    return Image.alpha_composite(base, Image.fromarray(rgb, "RGBA"))


def panel_canopy(arr, city_line, dist_line, lut, size):
    img = canopy_image(arr, lut)
    img = overlay_line(img, dist_line, (60, 66, 62), 120)
    img = overlay_line(img, city_line, (25, 29, 27), 235, grow=3)
    return img.convert("RGB").resize(size, Image.LANCZOS)


def panel_trees(city_fill, dist_line, px, py, cls, size, radius):
    gh, gw = city_fill.shape
    img = Image.new("RGBA", (gw, gh), (*PANEL_BG, 255))
    fill = np.zeros((gh, gw, 4), np.uint8)
    fill[city_fill] = (*CITY_FILL, 255)
    img = Image.alpha_composite(img, Image.fromarray(fill, "RGBA"))
    img = overlay_line(img, dist_line, (128, 136, 132), 255)
    pts = np.zeros((gh, gw, 4), np.uint8)
    scatter(pts, px, py, cls, TREE_COLORS, radius)
    img = Image.alpha_composite(img, Image.fromarray(pts, "RGBA"))
    return img.convert("RGB").resize(size, Image.LANCZOS)


def panel_overlay(arr, city_line, dist_line, px, py, lut, size, radius):
    img = canopy_image(arr, lut)
    img = overlay_line(img, dist_line, (40, 46, 42), 110)
    img = overlay_line(img, city_line, (20, 24, 22), 220, grow=3)
    gh, gw = city_line.shape
    flat = np.zeros(len(px), np.int64)
    dots = [((15, 20, 18, 235), radius + 1.2), ((255, 255, 255, 255), radius)]
    for color, r in dots:
        layer = np.zeros((gh, gw, 4), np.uint8)
        scatter(layer, px, py, flat, [color], r)
        img = Image.alpha_composite(img, Image.fromarray(layer, "RGBA"))
    return img.convert("RGB").resize(size, Image.LANCZOS)


def draw_district_labels(img, tpe, gt):
    draw = ImageDraw.Draw(img)
    f = font(FONT_BOLD, 34)
    for _, row in tpe.iterrows():
        p = row.geometry.representative_point()
        px, py = world_to_px(gt, [p.x], [p.y])
        if 0 <= px[0] < img.width and 0 <= py[0] < img.height:
            draw.text((px[0], py[0]), row["TOWNNAME"], font=f, fill=INK, anchor="mm",
                      stroke_width=6, stroke_fill=(255, 255, 255, 235))
    return img


def card(canvas, x, y, w, h, title):
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=20, fill=(255, 255, 255),
                           outline=BORDER, width=3)
    draw.rectangle([x + 34, y + 30, x + 46, y + 76], fill=ACCENT)
    draw.text((x + 62, y + 26), title, font=font(FONT_BOLD, 40), fill=ACCENT_D)
    draw.line([x + 34, y + 96, x + w - 34, y + 96], fill=BORDER, width=2)
    return x + 40, y + 120, w - 80, h - 150


def draw_locator(draw, box, tpe):
    x, y, w, h = box
    tw = gpd.read_file(BOUNDARY)
    if tw.crs is None:
        tw = tw.set_crs(3857)
    tw = tw.to_crs(3857)
    parts = []
    for geom in tw.geometry:
        parts.extend(geom.geoms if geom.geom_type == "MultiPolygon" else [geom])
    parts = [p.simplify(400) for p in parts if p.area > 2e8]
    tb = sgeom.MultiPolygon(parts).bounds
    scale = min(w / (tb[2] - tb[0]), h / (tb[3] - tb[1]))
    ox = x + (w - (tb[2] - tb[0]) * scale) / 2
    oy = y + (h - (tb[3] - tb[1]) * scale) / 2

    def proj(px, py):
        return ox + (px - tb[0]) * scale, oy + (tb[3] - py) * scale

    for p in parts:
        draw.polygon([proj(a, b) for a, b in p.exterior.coords],
                     fill=(228, 234, 226), outline=(150, 160, 152))
    union = tpe.geometry.union_all().simplify(200)
    polys = union.geoms if union.geom_type == "MultiPolygon" else [union]
    for p in polys:
        draw.polygon([proj(a, b) for a, b in p.exterior.coords], fill=(214, 62, 48),
                     outline=(120, 20, 12))
    ccx, ccy = union.centroid.coords[0]
    px, py = proj(ccx, ccy)
    draw.line([(px + 6, py), (x + w - 150, y + 40)], fill=(120, 20, 12), width=3)
    draw.text((x + w - 140, y + 26), "臺北市", font=font(FONT_BOLD, 34),
              fill=(120, 20, 12), anchor="lm")
    draw.text((x + w / 2, y + h + 8), "臺灣", font=font(FONT_REG, 30), fill=SUB,
              anchor="ma")


def draw_scale_north(draw, box, lat):
    x, y, w, h = box
    px_per_km = 1000.0 / (np.cos(np.radians(lat)) * RES)
    draw.text((x, y), "比例尺", font=font(FONT_BOLD, 34), fill=INK)
    bx, by = x, y + 74
    for i in range(5):
        col = (35, 39, 37) if i % 2 == 0 else (255, 255, 255)
        draw.rectangle([bx + i * px_per_km, by, bx + (i + 1) * px_per_km, by + 34],
                       fill=col, outline=(35, 39, 37), width=2)
    for i in range(6):
        px = bx + i * px_per_km
        draw.line([(px, by + 34), (px, by + 46)], fill=(35, 39, 37), width=2)
        draw.text((px, by + 52), str(i), font=font(FONT_REG, 28), fill=SUB, anchor="ma")
    draw.text((bx + 5 * px_per_km + 24, by + 52), "km", font=font(FONT_REG, 30),
              fill=INK, anchor="lm")

    ax = x + w - 200
    ay = y + 6
    draw.polygon([(ax, ay + 150), (ax + 44, ay + 150), (ax + 22, ay + 16)],
                 fill=(35, 39, 37))
    draw.polygon([(ax, ay + 150), (ax + 22, ay + 150), (ax + 22, ay + 16)],
                 fill=(160, 166, 162))
    draw.text((ax + 22, ay + 168), "N", font=font(FONT_BOLD, 42), fill=INK, anchor="ma")


def draw_legend(canvas, draw, box, lut, stats):
    x, y, w, h = box
    draw.text((x, y), "樹冠高度 (m)", font=font(FONT_BOLD, 34), fill=INK)
    ramp_w = w - 40
    ramp = Image.fromarray(lut[:VMAX + 1].astype(np.uint8)[None, :, :], "RGB")
    ramp = ramp.resize((ramp_w, 52), Image.LANCZOS)
    canvas.paste(ramp, (x, y + 52))
    for v in range(0, VMAX + 1, 10):
        px = x + int(ramp_w * v / VMAX)
        draw.line([(px, y + 104), (px, y + 116)], fill=(70, 76, 72), width=3)
        draw.text((px, y + 120), str(v), font=font(FONT_REG, 30), fill=SUB, anchor="ma")

    y2 = y + 196
    draw.text((x, y2), "路樹樹高 (m)", font=font(FONT_BOLD, 34), fill=INK)
    item_w = ramp_w / len(TREE_CLASS_LABELS)
    for i, label in enumerate(TREE_CLASS_LABELS):
        cx = x + 20 + item_w * (i + 0.5)
        draw.ellipse([cx - 14, y2 + 56, cx + 14, y2 + 80], fill=TREE_COLORS[i][:3],
                     outline=(60, 66, 62), width=2)
        draw.text((cx, y2 + 90), label, font=font(FONT_REG, 29), fill=INK, anchor="ma")

    y3 = y2 + 182
    draw.line([(x, y3 + 20), (x + 80, y3 + 20)], fill=(25, 29, 27), width=6)
    draw.text((x + 100, y3 + 20), "行政區界", font=font(FONT_REG, 31), fill=INK,
              anchor="lm")
    draw.line([(x + 330, y3 + 20), (x + 410, y3 + 20)], fill=(20, 24, 22), width=9)
    draw.text((x + 430, y3 + 20), "臺北市界", font=font(FONT_REG, 31), fill=INK,
              anchor="lm")
    draw.ellipse([x + 680, y3 + 6, x + 708, y3 + 34], fill=(255, 255, 255),
                 outline=(30, 34, 32), width=3)
    draw.text((x + 724, y3 + 20), "行道樹（套疊圖）", font=font(FONT_REG, 31),
              fill=INK, anchor="lm")
    draw.rectangle([x + 1130, y3 + 6, x + 1158, y3 + 34], fill=PANEL_BG,
                   outline=(30, 34, 32), width=2)
    draw.text((x + 1174, y3 + 20), "無資料", font=font(FONT_REG, 31), fill=INK,
              anchor="lm")
    draw_summary(draw, (x, y3 + 74, w, h), stats)


def draw_summary(draw, box, stats):
    x, y, w, h = box
    city, trees = stats["city"], stats["trees"]
    rows = [
        ("樹冠高度", f"平均 {city['mean_h']:.1f} m　中位數 {city['median_h']} m　"
                     f"P90 {city['p90_h']} m　最大 {city['max_h']} m"),
        ("樹冠面積", f"{city['canopy_ha']:,.0f} ha　有效範圍 {city['valid_ha']:,.0f} ha"),
        ("行道樹高", f"平均 {trees['mean_h']:.1f} m　中位數 {trees['median_h']:.1f} m　"
                     f"P90 {trees['p90_h']:.1f} m　樹種 {trees['species_total']} 種"),
    ]
    for i, (label, value) in enumerate(rows):
        draw.text((x, y + i * 54), label, font=font(FONT_BOLD, 30), fill=ACCENT_D,
                  anchor="lm")
        draw.text((x + 250, y + i * 54), value, font=font(FONT_REG, 30), fill=INK,
                  anchor="lm")
    top = "、".join(f"{n}（{c:,}）" for n, c in trees["top_species"][:5])
    draw.text((x, y + 3 * 54), "常見樹種", font=font(FONT_BOLD, 30), fill=ACCENT_D,
              anchor="lm")
    draw.text((x + 250, y + 3 * 54), top, font=font(FONT_REG, 27), fill=INK,
              anchor="lm")


def hbar(draw, box, labels, values, colors, fmt, label_w=340):
    x, y, w, h = box
    row_h = h / len(labels)
    maxv = max(values) or 1.0
    bar_x = x + label_w + 24
    bar_w = w - label_w - 200
    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        cy = y + row_h * (i + 0.5)
        draw.text((x + label_w - 12, cy), lab, font=font(FONT_REG, 30), fill=INK,
                  anchor="rm")
        bw = max(3, bar_w * val / maxv)
        draw.rectangle([bar_x, cy - row_h * 0.30, bar_x + bw, cy + row_h * 0.30],
                       fill=col)
        draw.text((bar_x + bw + 16, cy), fmt(val), font=font(FONT_REG, 29),
                  fill=SUB, anchor="lm")


def green_ramp(t):
    lo, hi = np.array([168, 208, 170]), np.array([24, 106, 62])
    return tuple(int(v) for v in lo + (hi - lo) * t)


def draw_height_chart(draw, box, city, lut, labels):
    x, y, w, h = box
    values = [city["zero_ha"]] + city["classes_ha"]
    names = ["無樹冠"] + labels
    colors = [(214, 218, 214)] + [tuple(int(c) for c in lut[m]) for m in CANOPY_MIDS]
    total = sum(values) or 1.0
    hbar(draw, (x, y, w, h), names, [100.0 * v / total for v in values], colors,
         lambda v: f"{v:.1f}%")
    draw.text((x, y + h + 10), "各級面積佔全市有效像元（行政區界內非缺失）之百分比",
              font=font(FONT_REG, 28), fill=SUB)


def draw_district_chart(draw, box, districts):
    x, y, w, h = box
    items = sorted(districts.items(), key=lambda kv: -kv[1]["cover_pct"])
    values = [v["cover_pct"] for _, v in items]
    mx = max(values) or 1.0
    hbar(draw, (x, y, w, h), [k for k, _ in items], values,
         [green_ramp(v / mx) for v in values], lambda v: f"{v:.1f}%", label_w=280)
    draw.text((x, y + h + 10), "樹冠覆蓋率＝樹冠高度 > 0 m 像元 ÷ 行政區界內有效像元",
              font=font(FONT_REG, 28), fill=SUB)


def draw_key_figures(draw, city, trees):
    items = [
        ("樹冠覆蓋率", f"{city['cover_pct']:.1f}", "%"),
        ("平均樹冠高度", f"{city['mean_h']:.1f}", "m"),
        ("行道樹", f"{trees.get('count_mapped', trees['count']):,}", "棵"),
        ("平均路樹樹高", f"{trees['mean_h']:.1f}", "m"),
    ]
    x0 = (W - 1500 * len(items)) / 2
    for i, (lab, val, unit) in enumerate(items):
        x = x0 + i * 1500
        draw.rounded_rectangle([x + 30, 592, x + 1440, 736], radius=16,
                               fill=(255, 255, 255), outline=BORDER, width=3)
        draw.text((x + 74, 664), lab, font=font(FONT_REG, 34), fill=SUB, anchor="lm")
        draw.text((x + 1376, 664), val, font=font(FONT_BOLD, 62), fill=ACCENT_D,
                  anchor="rm")
        draw.text((x + 1396, 676), unit, font=font(FONT_REG, 34), fill=SUB, anchor="lm")


def draw_header(draw, city, trees):
    draw.rectangle([0, 0, W, 16], fill=ACCENT)
    draw.text((W / 2, 250), "臺北市樹冠高度與路樹分布套疊圖",
              font=font(FONT_BOLD, 116), fill=INK, anchor="mm")
    draw.text((W / 2, 392), "整合 Meta／WRI CHMv2 樹冠高度模型與臺北市行道樹普查",
              font=font(FONT_REG, 48), fill=SUB, anchor="mm")
    draw.text((W / 2, 478), "電腦地圖繪製比賽參賽作品　|　A1（594 × 841 mm）　|　"
                            "Web Mercator（EPSG:3857）",
              font=font(FONT_REG, 32), fill=SUB, anchor="mm")
    draw_key_figures(draw, city, trees)
    draw.line([(MARGIN, HEADER_H - 10), (W - MARGIN, HEADER_H - 10)], fill=BORDER,
              width=3)


def footer_lines(n_trees, species):
    return [
        "資料來源　① 樹冠高度：Meta AI & World Resources Institute（WRI）Canopy Height "
        "Model v2（CHMv2），原始像元 1.19 m（Web Mercator；圖幅緯度地面約 1.08 m）；"
        "② 路樹點位：臺北市政府工務局公園路燈"
        f"工程管理處行道樹普查（圖幅內有效 {n_trees:,} 棵，樹種 {species} 種）；"
        "③ 行政區界：內政部國土測繪中心鄉（鎮、市、區）界線（114 年 3 月版）。",
        "統計定義　樹冠覆蓋率＝樹冠高度 > 0 m 之像元數 ÷ 行政區界內有效（非資料缺失）"
        "像元數；平均／中位／P90 樹高僅就樹冠高度 > 0 m 之像元統計；行道樹平均樹高"
        "為普查樹高平均值。",
        "繪製方法　CHMv2 依臺北市行政區界裁切後，以 7.5 m 網格平均重取樣製作圖層；"
        "樹冠高度分級統計與覆蓋率由原始像元直方圖計算，面積並以逐列 cos²(緯度) "
        "自 Web Mercator 還原為真實地面面積（如全市樹冠 13,887 ha）；行道樹點位由 "
        "TWD97／TM2（EPSG:3826）轉換至 Web Mercator（EPSG:3857）後與樹冠圖套疊。",
        "地圖投影與比例尺　Web Mercator（EPSG:3857），比例尺已依圖幅中心緯度（約 25.1°N）"
        "之投影尺度因子校正。製圖工具　GDAL／GeoPandas／Shapely／NumPy／Pillow。",
    ]


CAPTIONS = [
    "",
    "",
    "",
]


def wrap_line(ft, text, max_w):
    """Greedy character wrap of a CJK/Latin string to a pixel width."""
    out, cur = [], ""
    for ch in text:
        if ft.getlength(cur + ch) <= max_w:
            cur += ch
        else:
            out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out


def draw_footer(draw, stats):
    top = H - FOOTER_H
    draw.line([(MARGIN, top), (W - MARGIN, top)], fill=BORDER, width=3)
    ft = font(FONT_REG, FOOTER_FONT)
    max_w = W - 2 * MARGIN
    lines = []
    for logical in footer_lines(stats["trees"].get("count_mapped", stats["trees"]["count"]),
                                stats["trees"]["species_total"]):
        lines.extend(wrap_line(ft, logical, max_w))
    y = top + 40
    for line in lines:
        draw.text((MARGIN, y), line, font=ft, fill=SUB)
        y += FOOTER_LEAD


def compose(canvas, draw, tpe, lut, stats, images, panel_w, panel_h, lat):
    p_canopy, p_trees, p_over = images
    row1 = HEADER_H + 30
    canvas.paste(p_canopy, (MARGIN, row1))
    canvas.paste(p_trees, (MARGIN + panel_w + GAP, row1))
    row2 = row1 + panel_h + CAPTION_H + ROW_GAP
    canvas.paste(p_over, (MARGIN, row2))
    draw_header(draw, stats["city"], stats["trees"])
    for cap, cx in ((CAPTIONS[0], MARGIN + panel_w / 2),
                    (CAPTIONS[1], MARGIN + panel_w * 1.5 + GAP),
                    (CAPTIONS[2], MARGIN + panel_w / 2)):
        cy = row1 + panel_h + 18 if cap != CAPTIONS[2] else row2 + panel_h + 18
        draw.text((cx, cy), cap, font=font(FONT_BOLD, 72), fill=INK, anchor="ma")

    sx = MARGIN + panel_w + GAP
    gap = 22
    base = panel_h - gap * 3
    weights = [620, 806, 1374, 1374]
    scale = base / sum(weights)
    heights = [round(w * scale) for w in weights]
    y = row2
    cx, cy, cw, ch = card(canvas, sx, y, panel_w, heights[0], "位置圖與方位")
    loc_w = int(cw * 0.24)
    draw_locator(draw, (cx, cy - 10, loc_w, ch - 30), tpe)
    draw.line([(cx + loc_w + 50, cy + 10), (cx + loc_w + 50, cy + ch - 60)],
              fill=BORDER, width=2)
    draw_scale_north(draw, (cx + loc_w + 110, cy + 40, cw - loc_w - 140, ch), lat)
    y += heights[0] + gap
    cx, cy, cw, ch = card(canvas, sx, y, panel_w, heights[1], "圖例")
    draw_legend(canvas, draw, (cx, cy, cw, ch), lut, stats)
    y += heights[1] + gap
    cx, cy, cw, ch = card(canvas, sx, y, panel_w, heights[2], "樹冠高度分級統計")
    draw_height_chart(draw, (cx, cy + 6, cw, ch - 76), stats["city"], lut,
                      stats["class_labels"])
    y += heights[2] + gap
    cx, cy, cw, ch = card(canvas, sx, y, panel_w, heights[3], "各行政區樹冠覆蓋率")
    draw_district_chart(draw, (cx, cy + 6, cw, ch - 76), stats["districts"])
    draw_footer(draw, stats)


def main():
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    lut = build_lut()
    tpe = load_taipei()
    city = tpe.geometry.union_all()
    xmin, ymin, xmax, ymax = city.bounds
    lat = TO_LL.transform((xmin + xmax) / 2, (ymin + ymax) / 2)[1]

    arr, gt, gw, gh = warp_canopy((xmin - PAD_M, ymin - PAD_M, xmax + PAD_M,
                                   ymax + PAD_M))
    panel_w = (W - 2 * MARGIN - GAP) // 2
    panel_h = round(panel_w * gh / gw)
    size = (panel_w, panel_h)
    print(f"grid {gw}x{gh} panel {panel_w}x{panel_h} lat {lat:.3f}", flush=True)

    city_fill = rasterize(gt, gw, gh, [city])
    city_line = rasterize(gt, gw, gh, [city], rings=True)
    dist_line = rasterize(gt, gw, gh, list(tpe.geometry), rings=True)

    trees = load_trees(city)
    stats["trees"]["count_mapped"] = int(len(trees))
    px, py = world_to_px(gt, trees.geometry.x.values, trees.geometry.y.values)
    cls = tree_class_ids(trees["height"].values)
    radius = max(1.7, panel_w / gw * 2.1)
    print(f"trees {len(trees):,}", flush=True)

    images = (panel_canopy(arr, city_line, dist_line, lut, size),
              panel_trees(city_fill, dist_line, px, py, cls, size, radius),
              panel_overlay(arr, city_line, dist_line, px, py, lut, size,
                            radius + 0.4))
    gt2 = scaled_gt(gt, gw, gh, *size)
    for img in images:
        draw_district_labels(img, tpe, gt2)

    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    compose(canvas, draw, tpe, lut, stats, images, panel_w, panel_h, lat)

    canvas.save(OUT, optimize=True)
    canvas.resize((W // 4, H // 4), Image.LANCZOS).save(PREVIEW, optimize=True)
    print("saved", OUT, canvas.size, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
