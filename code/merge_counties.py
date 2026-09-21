# -*- coding: utf-8 -*-
"""Merge the 368 per-township native CHMv2 COGs into 22 county COGs (E:\\GeoAI\\20260909_taiwan_chmv2\\county).

All township COGs share the same source-aligned Web-Mercator grid; per county a VRT
is built and translated to a native-resolution COG (nearest, nodata 255 = ocean/gap).
"""
import sys
import time
from pathlib import Path

import geopandas as gpd
from osgeo import gdal

gdal.UseExceptions()

ROOT = Path(r"E:\GeoAI\20260909_taiwan_chmv2")
TOWNSHIPS = ROOT / "townships"
COUNTY_DIR = ROOT / "county"
SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"

COG_OPTS = ["COMPRESS=DEFLATE", "BLOCKSIZE=512",
            "OVERVIEW_RESAMPLING=NEAREST", "NUM_THREADS=ALL_CPUS"]


def main():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    code2county = {r.TOWNCODE: r.COUNTYNAME for _, r in gdf.iterrows()}
    counties = sorted({r.COUNTYNAME for _, r in gdf.iterrows()})
    print(f"{len(counties)} counties")

    # group township tifs by county (split townships share the TOWNCODE prefix)
    by_county = {c: [] for c in counties}
    for f in sorted(TOWNSHIPS.glob("*.tif")):
        code = f.stem.split("_")[0]
        by_county[code2county[code]].append(str(f))

    COUNTY_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for ci, county in enumerate(counties, 1):
        files = by_county[county]
        dest = COUNTY_DIR / f"{county}.tif"
        tmp_vrt = COUNTY_DIR / f"_{county}.vrt"
        gdal.BuildVRT(str(tmp_vrt), files, srcNodata=255, bandList=[1])
        gdal.Translate(str(dest), str(tmp_vrt), format="COG",
                       creationOptions=COG_OPTS)
        tmp_vrt.unlink(missing_ok=True)
        ds = gdal.Open(str(dest))
        size = ds.RasterXSize * ds.RasterYSize
        ov = ds.GetRasterBand(1).GetOverviewCount()
        ds = None
        mb = dest.stat().st_size / 1e6
        print(f"[{ci}/{len(counties)}] {county}: {len(files)} townships, "
              f"COG {mb:.0f} MB, overviews {ov} ({time.time()-t0:.0f}s)", flush=True)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())