# -*- coding: utf-8 -*-
"""Compose the 22 county figures into ONE Taiwan main-island (本島) map.

The main-island mask is the largest connected component of the dissolved township
boundary, so outlying islands (澎湖/金門/馬祖/東沙/太平島/綠島/蘭嶼/小琉球/龜山島/釣魚台…)
are excluded.  Rendered in the same style as fig_taipei_canopy_height.png.
"""
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
VRT = str(ROOT / "taiwan_chmv2_native.vrt")
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT = ROOT / "fig_taiwan_main_island.png"
FONT_PATH = r"C:\Windows\Fonts\msjh.ttc"
RES = 150.0
VMAX = 40

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


def main_island_mask(gdf):
    g3857 = gdf.to_crs("EPSG:3857")
    dissolved = g3857.geometry.union_all()
    parts = sorted(dissolved.geoms, key=lambda p: -p.area)
    main = parts[0]
    print(f"main island part: area={main.area/1e6:.0f} km2, "
          f"parts total={len(parts)}, 2nd largest={(parts[1].area if len(parts)>1 else 0)/1e6:.0f} km2")
    return main


def line_overlay(gt, w, h, geoms):
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Byte)
    mem.SetGeoTransform(gt)
    mem.SetProjection("EPSG:3857")
    mb = mem.GetRasterBand(1)
    mb.Fill(0)
    src = ogr.GetDriverByName("Memory").CreateDataSource("l")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    layer = src.CreateLayer("lines", srs=srs, geom_type=ogr.wkbLineString)
    fdef = layer.GetLayerDefn()
    for geom in geoms:
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in polys:
            for ring in [p.exterior, *p.interiors]:
                f = ogr.Feature(fdef)
                f.SetGeometry(ogr.CreateGeometryFromWkb(ring.wkb))
                layer.CreateFeature(f)
    gdal.RasterizeLayer(mem, [1], layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    arr = mb.ReadAsArray() > 0
    mem = None
    return arr


def main():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    main = main_island_mask(gdf)

    cut = ROOT / "_main_island.json"
    gpd.GeoSeries([main], crs="EPSG:3857").to_file(cut, driver="GeoJSON")
    tmp = ROOT / "_main_island_disp.tif"
    opts = gdal.WarpOptions(
        format="GTiff", cutlineDSName=str(cut), cutlineSRS="EPSG:3857",
        cropToCutline=True, dstSRS="EPSG:3857", xRes=RES, yRes=RES,
        resampleAlg=gdal.GRA_Average, outputType=gdal.GDT_Byte, dstNodata=255,
        multithread=True, creationOptions=["COMPRESS=DEFLATE", "TILED=YES"],
    )
    t0 = time.time()
    gdal.Warp(str(tmp), VRT, options=opts)
    print(f"warp done {time.time()-t0:.0f}s", flush=True)
    ds = gdal.Open(str(tmp))
    gt = ds.GetGeoTransform()
    w, hgt = ds.RasterXSize, ds.RasterYSize
    arr = ds.GetRasterBand(1).ReadAsArray()
    ds = None
    tmp.unlink(missing_ok=True)
    cut.unlink(missing_ok=True)

    lut = build_lut()
    rgba = np.dstack([lut[arr], np.where(arr == 255, 0, 255).astype(np.uint8)])
    img = Image.fromarray(rgba, "RGBA")
    # mainland coastline outline (kept for readability; no township boundaries)
    ml = line_overlay(gt, w, hgt, [main])
    lmx = Image.fromarray((ml * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5))
    lmx = np.array(lmx) > 0
    ov2 = np.zeros((hgt, w, 4), np.uint8)
    ov2[:, :, 3][lmx] = 255
    img = Image.alpha_composite(img, Image.fromarray(ov2, "RGBA"))

    W = 1500
    scale = W / img.width
    H = int(img.height * scale)
    img = img.resize((W, H), Image.LANCZOS)
    top = 84
    canvas = Image.new("RGBA", (W, H + top + 230), (255, 255, 255, 255))
    canvas.paste(img, (0, top))
    draw = ImageDraw.Draw(canvas)
    draw.text((W // 2, 6), "臺灣本島 CHMv2 樹冠高度圖（不含離島及外島）",
              font=ImageFont.truetype(FONT_PATH, 36), fill=(20, 20, 20), anchor="ma")
    ramp = build_lut()[:VMAX + 1].astype(np.uint8)[None, :, :]
    cb = Image.fromarray(ramp, "RGB").resize((int(W * 0.55), 24), Image.LANCZOS)
    cb_y = H + top + 30
    canvas.paste(cb, (int(W * 0.15), cb_y))
    ft = ImageFont.truetype(FONT_PATH, 18)
    for v in range(0, VMAX + 1, 10):
        x = int(W * 0.15) + int(cb.width * v / VMAX)
        draw.line((x, cb_y + 24, x, cb_y + 32), fill=(40, 40, 40), width=2)
        draw.text((x, cb_y + 34), str(v), font=ft, fill=(40, 40, 40), anchor="ma")
    draw.text((int(W * 0.15), cb_y + 60), "樹冠高度 (m)", font=ImageFont.truetype(FONT_PATH, 22),
              fill=(30, 30, 30))
    canvas.convert("RGB").save(OUT)
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())