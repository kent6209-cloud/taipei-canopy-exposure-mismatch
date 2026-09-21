# -*- coding: utf-8 -*-
"""WP2c：全臺鄉鎮市區樹冠結構統計（由逐鄉鎮 CHM 裁切檔重算，供外部效度對照）。

來源：`townships/<TOWNCODE>_<縣市>_<鄉鎮>.tif`（CHMv2 原生 1.19 m、EPSG:3857、含緩衝）
      `E:\\GeoAI\\鄉(鎮、市、區)界線1140318\\TOWN_MOI_1140318.shp`（多邊形 mask）

只取**落在該鄉鎮多邊形內**且非 nodata(255) 的像元，逐檔累積高度直方圖後，
依 TOWNCODE 合併（部分鄉鎮面積大、分散於多個分幅檔），再計算：
  cover_gt0_pct   植被偵測比例（CHM > 0）
  cover_ge2_pct   樹冠比例（CHM ≥ 2 m）
  mean_gt0_m / p90_gt0_m / mean_ge2_m
  area_ha         有效面積（cos²(lat) 校正，與主分析一致）

輸出：`wp2c_tw_townships.json`、`wp2c_tw_townships.csv`、`Paper/figures/figA2_tw_townships.png`
       `python wp2c_tw_townships.py --figure-only` 僅由既有 JSON 重繪圖。
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
TOWNS = ROOT / "townships"
TOWN_SHP = r"E:\GeoAI\鄉(鎮、市、區)界線1140318\TOWN_MOI_1140318.shp"
TOWN_GPKG = ROOT / "_wp2c_towns_masks.gpkg"      # 暫存：投影至 EPSG:3857 以便點陣化
OUT_JSON = ROOT / "wp2c_tw_townships.json"
OUT_CSV = ROOT / "wp2c_tw_townships.csv"
OUT_PNG = ROOT / "Paper" / "figures" / "figA2_tw_townships.png"
NODATA = 255
RES_M = 1.1943
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"


def log(m):
    print(m, file=sys.stderr, flush=True)


def prepare_towns():
    """裁切檔為 EPSG:3857，故 mask 需投影至 3857；另存質心緯度供 cos²(lat) 面積校正。"""
    if TOWN_GPKG.exists():
        return
    g = gpd.read_file(TOWN_SHP, encoding="utf-8")
    lat = g.to_crs(4326).geometry.centroid.y
    g = g.to_crs(3857)
    g["lat"] = lat.to_numpy()
    g[["TOWNCODE", "COUNTYNAME", "TOWNNAME", "lat", "geometry"]].to_file(TOWN_GPKG, driver="GPKG")
    log("prepared {} ({} townships, EPSG:3857)".format(TOWN_GPKG.name, len(g)))


def polygon_mask(gt, shape, towncode):
    """把指定鄉鎮多邊形（TOWNCODE）點陣化到與 CHM 相同的網格。"""
    ds = gdal.GetDriverByName("MEM").Create("", shape[1], shape[0], 1, gdal.GDT_Byte)
    ds.SetGeoTransform(gt)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).Fill(0)
    src = ogr.Open(str(TOWN_GPKG))
    layer = src.GetLayer()
    layer.SetAttributeFilter("TOWNCODE = '%s'" % towncode)
    feat = layer.GetNextFeature()
    if feat is None:
        ds, src = None, None
        return None, None, None
    name = (feat.GetField("COUNTYNAME"), feat.GetField("TOWNNAME"))
    lat = float(feat.GetField("lat"))
    mem = ogr.GetDriverByName("MEM").CreateDataSource("m")
    vl = mem.CreateLayer("l", srs)
    vl.CreateFeature(feat.Clone())
    gdal.RasterizeLayer(ds, [1], vl, burn_values=[1], options=["ALL_TOUCHED=FALSE"])
    mask = ds.GetRasterBand(1).ReadAsArray().astype(bool)
    ds, src, mem = None, None, None
    return mask, name, lat


def hist_of(arr, mask):
    """回傳 (有效像元數, 高度直方圖 0-255)；nodata(255) 不計入。"""
    valid = mask & (arr != NODATA)
    n = int(valid.sum())
    if n == 0:
        return 0, None
    h = np.bincount(arr[valid].ravel(), minlength=256).astype(np.int64)
    h[NODATA] = 0
    return n, h


def from_hist(n, hist, lat):
    """由聚合直方圖推回指標（跨分幅檔案合併後仍正確）。"""
    canopy0, canopy2 = int(hist[1:].sum()), int(hist[2:].sum())
    vals0 = np.repeat(np.arange(1, 256), hist[1:]) if canopy0 else np.array([0])
    vals2 = np.repeat(np.arange(2, 256), hist[2:]) if canopy2 else np.array([0])
    return {
        "n_pixels": n,
        "area_ha": round(n * RES_M ** 2 * float(np.cos(np.radians(lat)) ** 2) / 1e4, 2),
        "cover_gt0_pct": round(100.0 * canopy0 / n, 2) if n else 0.0,
        "cover_ge2_pct": round(100.0 * canopy2 / n, 2) if n else 0.0,
        "mean_gt0_m": round(float(vals0.mean()), 3) if canopy0 else 0.0,
        "p90_gt0_m": int(np.percentile(vals0, 90)) if canopy0 else 0,
        "mean_ge2_m": round(float(vals2.mean()), 3) if canopy2 else 0.0,
    }


def extract():
    prepare_towns()
    files = sorted(TOWNS.glob("*.tif"))
    log("files: {}".format(len(files)))
    acc = {}
    for i, f in enumerate(files, 1):
        towncode = f.name.split("_")[0]
        ds = gdal.Open(str(f))
        arr = ds.GetRasterBand(1).ReadAsArray()
        gt = ds.GetGeoTransform()
        ds = None
        mask, name, lat = polygon_mask(gt, arr.shape, towncode)
        if mask is None or not mask.any():
            log("  !! {} no polygon".format(f.name))
            continue
        n, hist = hist_of(arr, mask)
        if hist is None:
            continue
        a = acc.setdefault(towncode, {"county": name[0], "town": name[1], "lat": lat,
                                      "n": 0, "hist": np.zeros(256, np.int64), "n_tiles": 0})
        a["n"] += n
        a["hist"] += hist
        a["n_tiles"] += 1
        if i % 50 == 0:
            log("  {}/{}".format(i, len(files)))

    rows = []
    for code, a in acc.items():
        s = from_hist(a["n"], a["hist"], a["lat"])
        s.update({"towncode": code, "county": a["county"], "town": a["town"], "n_tiles": a["n_tiles"]})
        rows.append(s)
    rows.sort(key=lambda r: (r["county"], r["town"]))
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ["towncode", "county", "town", "n_tiles", "n_pixels", "area_ha", "cover_gt0_pct",
            "cover_ge2_pct", "mean_gt0_m", "p90_gt0_m", "mean_ge2_m"]
    OUT_CSV.write_text("\n".join([",".join(keys)] + [",".join(str(r[k]) for k in keys) for r in rows]) + "\n",
                       encoding="utf-8-sig")
    return rows


def draw_figure(rows):
    """"""
    cov = np.array([r["cover_gt0_pct"] for r in rows])
    ranked = [rows[i] for i in np.argsort(cov)]
    tp = [r for r in rows if r["county"] == "臺北市"]
    med = float(np.median(cov))
    W, H = 2100, 820
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 36), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 88), "CHMv2 原生 1.19 m、鄉鎮多邊形內像素（n = {} 鄉鎮市區）".format(len(rows)),
           font=ImageFont.truetype(FR, 24), fill=(90, 90, 90), anchor="ma")

    box = (190, 210, 1330, 690)
    ymax = 100.0
    d.rectangle(box, outline=(60, 60, 60), width=2)
    for g in range(0, 101, 20):
        gy = box[3] - g / ymax * (box[3] - box[1])
        d.line([(box[0], gy), (box[2], gy)], fill=(235, 238, 242), width=1)
        d.text((box[0] - 12, gy), str(g), font=ImageFont.truetype(FR, 20), fill=(70, 70, 70), anchor="rm")
    step = max(1, len(ranked) // 900)
    for i in range(0, len(ranked), step):
        gx = box[0] + (i / max(len(ranked) - 1, 1)) * (box[2] - box[0])
        gy = box[3] - min(ranked[i]["cover_gt0_pct"], ymax) / ymax * (box[3] - box[1])
        d.line([(gx, box[3]), (gx, gy)], fill=(150, 180, 205), width=2)
    gy = box[3] - med / ymax * (box[3] - box[1])
    d.line([(box[0], gy), (box[2], gy)], fill=(150, 150, 150), width=2)
    d.text((box[2] - 6, gy - 12), "全臺中位數 {:.1f}%".format(med), font=ImageFont.truetype(FR, 20),
           fill=(90, 90, 90), anchor="ra")

    # 臺北市 12 區：僅標紅點、不標區名（區名見面板 (b)），避免與曲線重疊
    pos = {r["towncode"]: i for i, r in enumerate(ranked)}
    for r in tp:
        gx = box[0] + (pos[r["towncode"]] / max(len(ranked) - 1, 1)) * (box[2] - box[0])
        gy = box[3] - r["cover_gt0_pct"] / ymax * (box[3] - box[1])
        d.ellipse([gx - 7, gy - 7, gx + 7, gy + 7], fill=(200, 40, 40))
    d.text(((box[0] + box[2]) / 2, box[3] + 14), "鄉鎮市區（依植被偵測比例排序，低 → 高）",
           font=ImageFont.truetype(FR, 21), fill=(40, 40, 40), anchor="ma")
    d.text((box[0] - 78, (box[1] + box[3]) / 2), "CHM>0 (%)", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="mm")
    d.text((box[0], box[1] - 34), "(a) 全臺 {} 鄉鎮市區排序（紅點＝臺北市 12 區）".format(len(rows)),
           font=ImageFont.truetype(FB, 24), fill=(20, 20, 20), anchor="lm")

    box2 = (1500, 210, 2030, 690)
    d.line([(box2[0], box2[1]), (box2[0], box2[3])], fill=(60, 60, 60), width=2)
    d.line([(box2[0], box2[3]), (box2[2], box2[3])], fill=(60, 60, 60), width=2)
    tp_sorted = sorted(tp, key=lambda r: r["cover_gt0_pct"])
    bw = (box2[2] - box2[0]) / len(tp_sorted)
    for i, r in enumerate(tp_sorted):
        h = r["cover_gt0_pct"] / ymax * (box2[3] - box2[1])
        cx = box2[0] + i * bw + bw * 0.15
        d.rectangle([cx, box2[3] - h, cx + bw * 0.7, box2[3]], fill=(43, 108, 176))
        d.text((cx + bw * 0.35, box2[3] - h - 6), "{:.0f}".format(r["cover_gt0_pct"]),
               font=ImageFont.truetype(FR, 17), fill=(30, 60, 110), anchor="mb")
        d.text((cx + bw * 0.35, box2[3] + 8), r["town"][:2], font=ImageFont.truetype(FR, 17),
               fill=(60, 60, 60), anchor="ma")
    gy = box2[3] - med / ymax * (box2[3] - box2[1])
    d.line([(box2[0], gy), (box2[2], gy)], fill=(150, 150, 150), width=2)
    d.text((box2[0] + 4, gy - 10), "全臺中位數", font=ImageFont.truetype(FR, 19), fill=(90, 90, 90), anchor="la")
    ratio = max(r["cover_gt0_pct"] for r in tp) / min(r["cover_gt0_pct"] for r in tp)
    d.text(((box2[0] + box2[2]) / 2, box2[1] - 34), "(b) 臺北市 12 區（區內落差 {:.1f} 倍）".format(ratio),
           font=ImageFont.truetype(FB, 24), fill=(20, 20, 20), anchor="ma")
    d.text(((box2[0] + box2[2]) / 2, box2[3] + 42), "臺北市各區", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="ma")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


def main():
    if "--figure-only" in sys.argv:
        rows = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        draw_figure(rows)
        print("figure regenerated from", OUT_JSON.name)
        return 0
    rows = extract()
    draw_figure(rows)
    print("wrote", OUT_JSON.name, OUT_CSV.name, OUT_PNG.name, "townships:", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
