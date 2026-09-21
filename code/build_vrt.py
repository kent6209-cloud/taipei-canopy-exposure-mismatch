# -*- coding: utf-8 -*-
"""Build a native-1.19 m VRT mosaic of the downloaded Taiwan CHMv2 COG tiles."""
import sys
from pathlib import Path

from osgeo import gdal

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
TILES = ROOT / "tiles"
VRT = ROOT / "taiwan_chmv2_native.vrt"


def main():
    files = sorted(str(p) for p in TILES.glob("*.tif"))
    if not files:
        print("no tiles found")
        return 1
    gdal.BuildVRT(str(VRT), files, srcNodata=None, bandList=[1])
    ds = gdal.Open(str(VRT))
    print("VRT ok:", ds.RasterXSize, "x", ds.RasterYSize)
    print("crs:", ds.GetProjection()[:80])
    ds = None
    return 0


if __name__ == "__main__":
    sys.exit(main())