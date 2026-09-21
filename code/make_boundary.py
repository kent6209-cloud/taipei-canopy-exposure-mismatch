# -*- coding: utf-8 -*-
"""Dissolve the township boundary to a single 3857 multipolygon for cutline clipping."""
import sys
from pathlib import Path

import geopandas as gpd

SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
OUT = r"E:\GeoAI\20260909_taiwan_chmv2\taiwan_boundary_3857.shp"


def main():
    gdf = gpd.read_file(SHP, encoding="utf-8")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:3826")
    merged = gpd.GeoDataFrame({"geometry": [gdf.geometry.union_all()]}, crs=gdf.crs)
    m3857 = merged.to_crs("EPSG:3857")
    m3857.to_file(OUT, encoding="utf-8")
    print("boundary written:", OUT, "geoms:", len(m3857))
    print("bounds 3857:", [round(v, 1) for v in m3857.total_bounds])
    return 0


if __name__ == "__main__":
    sys.exit(main())