# -*- coding: utf-8 -*-
"""Render one PNG per county from the merged native COGs (county\\*.tif), in the
style of 20260903\\fig_taipei_canopy_height.png: canopy-height colour ramp, township
boundary overlay, colour bar and title.

Counties whose boundary spans far-flung islands (e.g. 高雄市 -> 東沙/太平島) are
displayed on their largest contiguous land cluster so the map stays readable.
"""
import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFilter, ImageFont

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
TOWNSHIPS = ROOT / "townships"
COUNTY_DIR = ROOT / "county"
FIG_DIR = ROOT / "county_fig"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
FONT_PATH = r"C:\Windows\Fonts\msjh.ttc"
RES = 100.0  # display resolution (m)
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


def filter_nearby(geom, dist=40000.0):
    """Keep only parts of the county boundary within `dist` of the largest part,
    dropping far-flung outliers (e.g. 烏坵 from 金門縣, 彭佳嶼/棉花嶼/花瓶嶼 from 基隆市)."""
    parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    if len(parts) <= 1:
        return geom
    parts = sorted(parts, key=lambda p: -p.area)
    main = parts[0]
    rep = main.representative_point()
    keep = [p for p in parts if p.representative_point().distance(rep) <= dist]
    import shapely.ops
    return shapely.ops.unary_union(keep)


def display_geometry(county, dissolved):
    """County-specific display extent (which parts of the county boundary to show)."""
    rule = DISPLAY_OVERRIDES.get(county, "nearby40")
    if rule == "main_only":
        parts = dissolved.geoms if dissolved.geom_type == "MultiPolygon" else [dissolved]
        return max(parts, key=lambda p: p.area)
    return filter_nearby(dissolved, 40000.0)


DISPLAY_OVERRIDES = {
    "金門縣": "main_only",   # 下方（烈嶼/大膽/二膽/東碇等）不列入，僅顯示金門本島
}


def line_overlay(gt, w, h, county_geom):
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
    for geom in county_geom:
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


def render(files, display_geom, county):
    vrt = COUNTY_DIR / f"_{county}.vrt"
    gdal.BuildVRT(str(vrt), [str(f) for f in files], srcNodata=255, bandList=[1])
    cut = COUNTY_DIR / f"_{county}.json"
    gpd.GeoSeries([display_geom], crs="EPSG:3857").to_file(cut, driver="GeoJSON")

    tmp = COUNTY_DIR / f"_{county}_disp.tif"
    opts = gdal.WarpOptions(
        format="GTiff", cutlineDSName=str(cut), cutlineSRS="EPSG:3857",
        cropToCutline=True,
        dstSRS="EPSG:3857", xRes=RES, yRes=RES, resampleAlg=gdal.GRA_Average,
        outputType=gdal.GDT_Byte, dstNodata=255, multithread=True,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"],
    )
    gdal.Warp(str(tmp), str(vrt), options=opts)
    ds = gdal.Open(str(tmp))
    gt = ds.GetGeoTransform()
    hgt = ds.RasterYSize
    arr = ds.GetRasterBand(1).ReadAsArray()
    w = ds.RasterXSize
    ds = None
    tmp.unlink(missing_ok=True)
    vrt.unlink(missing_ok=True)
    cut.unlink(missing_ok=True)

    lut = build_lut()
    rgb = lut[arr]
    a = np.where(arr == 255, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb, a])

    img = Image.fromarray(rgba, "RGBA")

    W = 1400
    scale = W / img.width
    H = int(img.height * scale)
    img = img.resize((W, H), Image.LANCZOS)
    top = 84
    canvas = Image.new("RGBA", (W, H + top + 230), (255, 255, 255, 255))
    canvas.paste(img, (0, top))
    draw = ImageDraw.Draw(canvas)
    draw.text((W // 2, 6), f"{county} CHMv2 樹冠高度圖（Meta/WRI DINOv3，原生約 1.19 m）",
              font=ImageFont.truetype(FONT_PATH, 34), fill=(20, 20, 20), anchor="ma")
    # colorbar
    ramp = lut[:VMAX + 1].astype(np.uint8)[None, :, :]
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
    return canvas.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="render only this county")
    args = ap.parse_args()
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    g3857 = gdf.to_crs("EPSG:3857")
    code2county = {r.TOWNCODE: r.COUNTYNAME for _, r in gdf.iterrows()}
    by_county = {}
    for f in TOWNSHIPS.glob("*.tif"):
        code = f.stem.split("_")[0]
        by_county.setdefault(code2county[code], []).append(f)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for ci, county in enumerate(sorted(by_county), 1):
        if args.only and county != args.only:
            continue
        files = sorted(by_county[county])
        towns = g3857[g3857["COUNTYNAME"] == county]
        dissolved = towns.geometry.union_all()
        display = display_geometry(county, dissolved)
        img = render(files, display, county)
        out = FIG_DIR / f"{county}.png"
        img.save(out)
        print(f"[{ci}/{len(by_county)}] {county} saved {out} ({time.time()-t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())