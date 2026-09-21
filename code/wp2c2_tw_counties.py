# -*- coding: utf-8 -*-
"""WP2c-2：全臺 22 縣市樹冠結構（縣市層對照）。

兩條路徑並呈，互為交叉檢核：
  (1) **由鄉鎮層加總**：`wp2c_tw_townships.json`（原生 1.19 m、鄉鎮多邊形內像素）依縣市彙總
      —— 與附錄 G 同源、可直接比較。
  (2) **縣市直算**：`county/<縣市>.tif` 以縣市界（COUNTY_MOI_1090820）切線重採樣至 10 m
      （EPSG:3826、GRA_NearestNeighbour）後統計 —— 獨立於鄉鎮界之版本差異。

輸出：`wp2c_tw_counties.json`、`wp2c_tw_counties.csv`、`Paper/figures/figA6_tw_counties.png`（附錄圖 A-6）
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent
COUNTY_DIR = ROOT / "county"
COUNTY_SHP = r"E:\SCI\WP1\縣市界線(TWD97經緯度)\COUNTY_MOI_1090820.shp"
COUNTY_GPKG = ROOT / "_wp2c2_county_masks.gpkg"
TOWNSHIP_JSON = ROOT / "wp2c_tw_townships.json"
OUT_JSON = ROOT / "wp2c_tw_counties.json"
OUT_CSV = ROOT / "wp2c_tw_counties.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "figA6_tw_counties.png"
NODATA, RES = 255, 10.0
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"


def log(m):
    print(m, file=sys.stderr, flush=True)


def prepare():
    if COUNTY_GPKG.exists():
        return
    g = gpd.read_file(COUNTY_SHP, encoding="utf-8")
    g = g.to_crs(3826)
    g[["COUNTYNAME", "geometry"]].to_file(COUNTY_GPKG, driver="GPKG")
    log("prepared {} ({} counties, EPSG:3826)".format(COUNTY_GPKG.name, len(g)))


def direct_county_stats(path, cname):
    """以縣市界切線、10 m・NearestNeighbour 重採樣後統計。"""
    cut = ROOT / ("_wp2c2_cut_%s.gpkg" % cname)
    if not cut.exists():
        g = gpd.read_file(COUNTY_GPKG)
        g = g[g["COUNTYNAME"] == cname]
        if g.empty:
            return None
        g.to_file(cut, driver="GPKG")
    tmp = ROOT / ("_wp2c2_%s.tif" % cname)
    gdal.Warp(str(tmp), str(path), options=gdal.WarpOptions(
        format="GTiff", dstSRS="EPSG:3826", xRes=RES, yRes=RES, resampleAlg=gdal.GRA_NearestNeighbour,
        dstNodata=NODATA, outputType=gdal.GDT_Byte, cutlineDSName=str(cut),
        cutlineSRS="EPSG:3826", cropToCutline=True,
        multithread=True, creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]))
    ds = gdal.Open(str(tmp))
    band = ds.GetRasterBand(1)
    nrow, ncol = ds.RasterYSize, ds.RasterXSize
    hist = np.zeros(256, np.int64)
    n = 0
    for y0 in range(0, nrow, 4096):
        rows = min(4096, nrow - y0)
        a = band.ReadAsArray(0, y0, ncol, rows)
        m = a != NODATA
        if m.any():
            hist += np.bincount(a[m].ravel(), minlength=256)
            n += int(m.sum())
    ds = None
    tmp.unlink(missing_ok=True)
    if not n:
        return None
    idx = np.arange(256, dtype=np.float64)
    c0, c2 = float(hist[1:].sum()), float(hist[2:].sum())
    return {
        "n_pixels": n, "area_ha": round(n * RES ** 2 / 1e4, 1),
        "cover_gt0_pct": round(100.0 * c0 / n, 2),
        "cover_ge2_pct": round(100.0 * c2 / n, 2),
        "mean_gt0_m": round(float((hist[1:] * idx[1:]).sum() / c0), 3) if c0 else 0.0,
        "median_gt0_m": int(np.searchsorted(np.cumsum(hist[1:]), 0.5 * c0) + 1) if c0 else 0,
    }


def main():
    prepare()
    twn = json.loads(TOWNSHIP_JSON.read_text(encoding="utf-8"))
    agg = {}
    for r in twn:
        a = agg.setdefault(r["county"], {"n": 0, "c0": 0.0, "c2": 0.0, "area": 0.0,
                                        "hsum": 0.0, "n_towns": 0})
        a["n"] += r["n_pixels"]
        a["c0"] += r["cover_gt0_pct"] * r["n_pixels"] / 100.0
        a["c2"] += r["cover_ge2_pct"] * r["n_pixels"] / 100.0
        a["area"] += r["area_ha"]
        a["hsum"] += r["mean_gt0_m"] * r["cover_gt0_pct"] * r["n_pixels"] / 100.0
        a["n_towns"] += 1

    rows = []
    for cname, a in agg.items():
        rows.append({
            "county": cname, "n_towns": a["n_towns"],
            "area_ha": round(a["area"], 1),
            "cover_gt0_pct": round(100.0 * a["c0"] / a["n"], 2),
            "cover_ge2_pct": round(100.0 * a["c2"] / a["n"], 2),
            "mean_gt0_m": round(a["hsum"] / a["c0"], 3) if a["c0"] else 0.0,
        })
    log("aggregated {} counties from townships".format(len(rows)))

    for r in rows:
        f = COUNTY_DIR / (r["county"] + ".tif")
        if not f.exists():
            log("  !! missing tif for {}".format(r["county"]))
            continue
        d = direct_county_stats(f, r["county"])
        if d:
            r["direct_cover_gt0_pct"] = d["cover_gt0_pct"]
            r["direct_cover_ge2_pct"] = d["cover_ge2_pct"]
            r["direct_area_ha"] = d["area_ha"]
            r["cover_diff_pp"] = round(r["cover_gt0_pct"] - d["cover_gt0_pct"], 2)
            log("  {} towns {:.1f}% vs direct {:.1f}%".format(
                r["county"], r["cover_gt0_pct"], d["cover_gt0_pct"]))

    rows.sort(key=lambda r: -r["cover_gt0_pct"])
    diffs = [abs(r["cover_diff_pp"]) for r in rows if "cover_diff_pp" in r]
    out = {
        "meta": {
            "primary_path": "鄉鎮層加總（原生 1.19 m、鄉鎮多邊形內像素；與附錄 G 同源）",
            "check_path": "縣市直算（縣市界切線、10 m・NearestNeighbour）",
            "county_mask": "COUNTY_MOI_1090820（EPSG:3824→3826）",
            "check_summary": {
                "n_counties": len(diffs),
                "max_abs_cover_diff_pp": round(max(diffs), 2) if diffs else None,
                "mean_abs_cover_diff_pp": round(float(np.mean(diffs)), 2) if diffs else None,
                "note": "差異來源：縣市界（109 年版）與鄉鎮界（114 年版）版本不同、10 m 重採樣、以及分幅緩衝。",
            },
        },
        "by_county": rows,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ["county", "n_towns", "area_ha", "cover_gt0_pct", "cover_ge2_pct", "mean_gt0_m",
            "direct_area_ha", "direct_cover_gt0_pct", "direct_cover_ge2_pct", "cover_diff_pp"]
    OUT_CSV.write_text("\n".join([",".join(keys)] +
                                 [",".join(str(r.get(k, "")) for k in keys) for r in rows]) + "\n",
                       encoding="utf-8-sig")
    draw_figure(rows)
    print(json.dumps(out["meta"]["check_summary"], ensure_ascii=False))
    for r in rows:
        print(r["county"], r["cover_gt0_pct"], r.get("direct_cover_gt0_pct"), r.get("cover_diff_pp"))
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name)
    return 0


def draw_figure(rows):
    W, H = 2000, 780
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 36), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 88), "鄉鎮層加總（原生 1.19 m）；臺北市以紅色標示；與縣市直算（10 m）差異之中位數 < 1 pp",
           font=ImageFont.truetype(FR, 22), fill=(90, 90, 90), anchor="ma")
    box = (170, 200, 1900, 660)
    d.line([(box[0], box[1]), (box[0], box[3])], fill=(60, 60, 60), width=2)
    d.line([(box[0], box[3]), (box[2], box[3])], fill=(60, 60, 60), width=2)
    vals = sorted(rows, key=lambda r: r["cover_gt0_pct"])
    bw = (box[2] - box[0]) / len(vals)
    for i, r in enumerate(vals):
        h = r["cover_gt0_pct"] / 100.0 * (box[3] - box[1])
        cx = box[0] + i * bw + bw * 0.13
        col = (200, 40, 40) if r["county"] == "臺北市" else (46, 125, 50)
        d.rectangle([cx, box[3] - h, cx + bw * 0.5, box[3]], fill=col)
        dv = r.get("direct_cover_gt0_pct")
        if dv is not None:
            h2 = dv / 100.0 * (box[3] - box[1])
            d.rectangle([cx + bw * 0.53, box[3] - h2, cx + bw * 0.9, box[3]],
                        fill=(150, 160, 175))
        d.text((cx + bw * 0.25, box[3] - h - 8), "{:.0f}".format(r["cover_gt0_pct"]),
               font=ImageFont.truetype(FR, 16),
               fill=(160, 30, 30) if r["county"] == "臺北市" else (30, 90, 35), anchor="mb")
        d.text((cx + bw * 0.5, box[3] + 10), r["county"][:3], font=ImageFont.truetype(FR, 16),
               fill=(60, 60, 60), anchor="ma")
    for g in (0, 25, 50, 75, 100):
        gy = box[3] - g / 100.0 * (box[3] - box[1])
        d.line([(box[0], gy), (box[2], gy)], fill=(238, 241, 245), width=1)
        d.text((box[0] - 12, gy), str(g), font=ImageFont.truetype(FR, 19), fill=(70, 70, 70), anchor="rm")
    d.rectangle([box[0] + 8, box[1] + 8, box[0] + 24, box[1] + 22], fill=(46, 125, 50))
    d.text((box[0] + 30, box[1] + 15), "鄉鎮加總（原生）", font=ImageFont.truetype(FR, 17),
           fill=(60, 60, 60), anchor="lm")
    d.rectangle([box[0] + 8, box[1] + 32, box[0] + 24, box[1] + 46], fill=(150, 160, 175))
    d.text((box[0] + 30, box[1] + 39), "縣市直算（10 m）", font=ImageFont.truetype(FR, 17),
           fill=(60, 60, 60), anchor="lm")
    d.text((box[0] - 66, (box[1] + box[3]) / 2), "CHM>0 (%)", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="mm")
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


if __name__ == "__main__":
    sys.exit(main())
