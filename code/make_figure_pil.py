# -*- coding: utf-8 -*-
"""Render the national Taiwan CHMv2 canopy-height map (PIL-only; matplotlib is broken on this host).

Pipeline: 100 m cutline-clipped height raster -> GDAL color-relief RGBA -> compose main
map + outer-island insets + township boundaries + colorbar + title via PIL.
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pyproj import Transformer

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
VRT = str(ROOT / "taiwan_chmv2_native.vrt")
CUTLINE = str(ROOT / "taiwan_boundary_3857.shp")
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
TMP_HEIGHT = r"C:\Users\kent6\AppData\Local\Temp\opencode\tw_chm_100m.tif"
TMP_RGBA = r"C:\Users\kent6\AppData\Local\Temp\opencode\tw_chm_100m_rgba.tif"
TMP_LINES = r"C:\Users\kent6\AppData\Local\Temp\opencode\tw_lines.tif"
OUT = ROOT / "fig_taiwan_canopy_height.png"

PALETTE = [
    "0 224 222 210",
    "2 84 140 88",
    "5 74 152 82",
    "10 116 180 94",
    "15 156 202 96",
    "20 198 208 88",
    "25 216 190 74",
    "30 196 148 60",
    "35 164 108 50",
    "40 132 80 42",
    "50 104 62 38",
    "nv 0 0 0 0",
]

WM = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# display windows in epsg:3857
def wm_lonlat(lon, lat):
    x, y = WM.transform(lon, lat)
    return x, y

MAIN = (*wm_lonlat(119.15, 21.75), *wm_lonlat(122.20, 25.55))  # xmin,ymin,xmax,ymax
INSETS = [
    ("馬祖", (*wm_lonlat(119.70, 25.95), *wm_lonlat(120.60, 26.45))),
    ("金門", (*wm_lonlat(118.10, 24.35), *wm_lonlat(118.55, 24.60))),
    ("東沙", (*wm_lonlat(116.55, 20.60), *wm_lonlat(116.90, 20.80))),
    ("太平島", (*wm_lonlat(114.25, 10.30), *wm_lonlat(114.50, 10.50))),
]
FONT_PATH = r"C:\Windows\Fonts\msjh.ttc"


def px_window(gt, xmin, ymin, xmax, ymax, W=0, H=0):
    c0 = int((xmin - gt[0]) / gt[1]); c1 = int(np.ceil((xmax - gt[0]) / gt[1]))
    r0 = int((gt[3] - ymax) / (-gt[5])); r1 = int(np.ceil((gt[3] - ymin) / (-gt[5])))
    if W and H:
        c0 = max(0, min(c0, W)); c1 = max(0, min(c1, W))
        r0 = max(0, min(r0, H)); r1 = max(0, min(r1, H))
    return c0, r0, c1, r1


def build_lut():
    stops = []
    for line in PALETTE:
        if line == "nv 0 0 0 0":
            continue
        v, r, g, b = map(int, line.split())
        stops.append((v, (r, g, b)))
    lut = np.zeros((256, 3), np.uint8)
    for i in range(256):
        for j in range(len(stops) - 1):
            v0, c0 = stops[j]; v1, c1 = stops[j + 1]
            if v0 <= i <= v1:
                t = (i - v0) / max(1, v1 - v0)
                lut[i] = tuple(int(c0[k] + t * (c1[k] - c0[k])) for k in range(3))
                break
    return lut


def build_rasters():
    if not Path(TMP_HEIGHT).exists():
        opts = gdal.WarpOptions(
            format="GTiff", cutlineDSName=CUTLINE, cropToCutline=True,
            xRes=100.0, yRes=100.0, resampleAlg=gdal.GRA_Average,
            outputType=gdal.GDT_Byte, dstNodata=255, multithread=True,
            creationOptions=["COMPRESS=DEFLATE", "TILED=YES"],
        )
        gdal.Warp(TMP_HEIGHT, VRT, options=opts)


def build_line_overlay(gt, w, h):
    gdf = gpd.read_file(SHP, encoding="utf-8").to_crs("EPSG:3857")
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    mem.SetProjection(gdal.Open(TMP_HEIGHT).GetProjection())
    mem.GetRasterBand(1).Fill(0)
    src = ogr.GetDriverByName("Memory").CreateDataSource("l")
    srs = osr.SpatialReference()
    srs.ImportFromWkt(gdal.Open(TMP_HEIGHT).GetProjection())
    layer = src.CreateLayer("lines", srs=srs, geom_type=ogr.wkbLineString)
    fdef = layer.GetLayerDefn()
    for geom in gdf.geometry:
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in polys:
            for ring in [p.exterior, *p.interiors]:
                f = ogr.Feature(fdef)
                f.SetGeometry(ogr.CreateGeometryFromWkb(ring.wkb))
                layer.CreateFeature(f)
    gdal.RasterizeLayer(mem, [1], layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    arr = mem.GetRasterBand(1).ReadAsArray()
    mem = None
    return (arr > 0)


def canvas_panel(arr, lines, gt, window, inset=False):
    c0, r0, c1, r1 = window
    crop = arr[r0:r1, c0:c1]
    img = Image.fromarray(crop, "RGBA")
    lm = lines[r0:r1, c0:c1]
    if lm.any():
        lmimg = Image.fromarray((lm * 255).astype(np.uint8), "L")
        lmimg = lmimg.filter(ImageFilter.MaxFilter(3))
        black = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(black)
        lmdata = np.array(lmimg) > 0
        # overlay dark linework via numpy alpha blend
        a = np.zeros(lmdata.shape, dtype=np.uint8)
        a[lmdata] = 190
        rgba = np.dstack([np.full(lmdata.shape, 45, np.uint8),
                          np.full(lmdata.shape, 45, np.uint8),
                          np.full(lmdata.shape, 45, np.uint8), a])
        ov = Image.fromarray(rgba, "RGBA")
        img = Image.alpha_composite(img, ov)
    return img


def colorbar_img():
    lut = build_lut()
    ramp = np.repeat(lut[:41, :][np.newaxis, :, :], 1, axis=0).astype(np.uint8)
    img = Image.fromarray(ramp, "RGB")
    return img.resize((img.width * 8, 26), Image.LANCZOS)


def main():
    build_rasters()
    hds = gdal.Open(TMP_HEIGHT)
    gt = hds.GetGeoTransform()
    RW, RH = hds.RasterXSize, hds.RasterYSize
    h = hds.GetRasterBand(1).ReadAsArray()
    lut = build_lut()
    rgb = lut[h]
    a = np.where(h == 255, 0, 255).astype(np.uint8)
    arr = np.dstack([rgb, a])  # H,W,4
    print("rgba", arr.shape, flush=True)

    lines = build_line_overlay(gt, RW, RH)
    print("lines built", flush=True)

    FONT = ImageFont.truetype(FONT_PATH, 40)
    FONT_S = ImageFont.truetype(FONT_PATH, 26)
    FONT_T = ImageFont.truetype(FONT_PATH, 22)

    main_img = canvas_panel(arr, lines, gt, px_window(gt, *MAIN, RW, RH))
    inset_imgs = []
    for name, win in INSETS:
        im = canvas_panel(arr, lines, gt, px_window(gt, *win, RW, RH))
        if im.width > 0 and im.height > 0:
            inset_imgs.append((name, im))

    W = 1700
    scale = W / main_img.width
    H = int(main_img.height * scale)
    main_img = main_img.resize((W, H), Image.LANCZOS)
    top = 90
    canvas = Image.new("RGBA", (W, H + top + 260), (255, 255, 255, 255))
    canvas.paste(main_img, (0, top))

    draw = ImageDraw.Draw(canvas)
    draw.text((W // 2, 8), "全臺灣 CHMv2 樹冠高度圖（Meta/WRI DINOv3, 原生約 1.19 m）",
              font=FONT, fill=(20, 20, 20), anchor="ma")

    # colorbar
    cb = colorbar_img().resize((int(W * 0.55), 26), Image.LANCZOS)
    cb_y = H + top + 30
    canvas.paste(cb, (int(W * 0.15), cb_y))
    for v in (0, 10, 20, 30, 40):
        x = int(W * 0.15) + int(cb.width * v / 40)
        draw.line((x, cb_y + 26, x, cb_y + 34), fill=(40, 40, 40), width=2)
        draw.text((x, cb_y + 36), str(v), font=FONT_T, fill=(40, 40, 40), anchor="ma")
    draw.text((int(W * 0.15), cb_y + 68), "樹冠高度 (m)", font=FONT_S, fill=(30, 30, 30))

    # insets
    iw = int(W * 0.21)
    gap = 14
    x0 = int(W * 0.03)
    for name, im in inset_imgs:
        ih = int(im.height * iw / im.width)
        im2 = im.resize((iw, ih), Image.LANCZOS)
        canvas.paste(im2, (x0, cb_y + 110))
        draw.text((x0 + iw // 2, cb_y + 110 + ih + 2), name, font=FONT_T, fill=(20, 20, 20), anchor="ma")
        x0 += iw + gap

    canvas.convert("RGB").save(OUT)
    print("saved", OUT, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())