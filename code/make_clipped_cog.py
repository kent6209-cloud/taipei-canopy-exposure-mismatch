# -*- coding: utf-8 -*-
"""Clip the native CHMv2 VRT to the Taiwan boundary and emit a compressed COG.

Because the dissolved Taiwan boundary spans ~1.9 M m N-S (incl. outer islands),
a single native-1.19 m GeoTIFF over that bbox would be ~1.5 T cells, so this
script emits a cutline-clipped COG at a target resolution (default 30 m) with
255 as nodata (source is uint8 0-254).
"""
import argparse
import sys
from pathlib import Path

from osgeo import gdal

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
VRT = str(ROOT / "taiwan_chmv2_native.vrt")
CUTLINE = str(ROOT / "taiwan_boundary_3857.shp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=30.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or str(ROOT / f"taiwan_chmv2_clipped_{int(args.res)}m.tif")
    opts = gdal.WarpOptions(
        format="GTiff",
        cutlineDSName=CUTLINE,
        cropToCutline=True,
        xRes=args.res,
        yRes=args.res,
        resampleAlg=gdal.GRA_Average,
        outputType=gdal.GDT_Byte,
        dstNodata=255,
        multithread=True,
        warpMemoryLimit=2048,
        creationOptions=[
            "COMPRESS=DEFLATE", "TILED=YES", "BIGTIFF=IF_SAFER",
            "BLOCKXSIZE=512", "BLOCKYSIZE=512", "NUM_THREADS=8",
        ],
    )
    ds = gdal.Warp(out, VRT, options=opts)
    print("warp done:", out, ds.RasterXSize, "x", ds.RasterYSize)
    stats = ds.GetRasterBand(1).ComputeStatistics(False)
    print("min/max/mean/std:", stats)
    ds = None
    return 0


if __name__ == "__main__":
    sys.exit(main())