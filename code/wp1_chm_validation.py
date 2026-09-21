# -*- coding: utf-8 -*-
"""WP1：CHMv2 樹冠高度對行道樹普查之獨立驗證（本專案可重現）。

把臺北市行道樹普查（`taipei_trees_authoritative.csv` 之樹高）與 CHMv2 原生解析度
（`county/臺北市.tif`，1.19 m／EPSG:3857）逐棵配對，計算 MAE、RMSE、r、bias，
並比較三種校正：全域加性偏移、行政區加性偏移、全域線性（閉式 OLS）。

輸出：
  wp1_chm_validation.json
  Paper/figures/figA_chm_validation.png（附錄圖 A）

限制：行道樹樹高為目視／人工普查值，CHMv2 為光達／影像融合產品；兩者配對為
「同一座標」而非「同一株樹」之嚴格時空對齊，故僅作為**量級與偏差**之檢核，
不作為 CHM 精度之絕對結論。PSI/P95 等單株誤差未納入。
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions()

ROOT = Path(__file__).resolve().parent
TREE_CSV = ROOT / "taipei_trees_authoritative.csv"
CHM = ROOT / "county" / "臺北市.tif"
OUT_JSON = ROOT / "wp1_chm_validation.json"
OUT_PNG = ROOT / "Paper" / "figures" / "figA_chm_validation.png"
REFPATH = Path(r"E:\GeoAI\20260903\tree_chm_compare.json")   # 前次工作階段之輸出（僅作對照）
CHM_NODATA = 255
WIN = 1                     # 取 3x3 窗（WIN=1）
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"


def log(m):
    print(m, file=sys.stderr, flush=True)


def load_points():
    """回傳 (x, y, height_m, district) —— 僅取可分析且有樹高者。"""
    out = []
    with open(TREE_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("analysis_ready") != "1" or row.get("height_valid") != "1":
                continue
            try:
                h = float(row["TreeHeight_m"])
                x = float(row["TWD97X"])
                y = float(row["TWD97Y"])
            except (TypeError, ValueError):
                continue
            if h > 0:
                out.append((x, y, h, row.get("Dist", "")))
    return out


def to_3857(points):
    src = osr.SpatialReference()
    src.ImportFromEPSG(3826)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(3857)
    tr = osr.CoordinateTransformation(src, dst)
    xy = np.array([tr.TransformPoint(x, y)[:2] for x, y, _, _ in points])
    h = np.array([p[2] for p in points])
    dist = np.array([p[3] for p in points])
    return xy, h, dist


def sample(ds, xy):
    """回傳 (中心像元值, 3x3 最大值)；nodata 以 nan 表示。"""
    gt = ds.GetGeoTransform()
    band = ds.GetRasterBand(1)
    res_x, res_y = gt[1], gt[5]
    ncol, nrow = ds.RasterXSize, ds.RasterYSize
    centre = np.full(len(xy), np.nan)
    window_max = np.full(len(xy), np.nan)
    for i, (x, y) in enumerate(xy):
        col = int((x - gt[0]) / res_x)
        row = int((y - gt[3]) / res_y)
        if not (0 <= col < ncol and 0 <= row < nrow):
            continue
        c0, r0 = max(col - WIN, 0), max(row - WIN, 0)
        w = min(2 * WIN + 1, ncol - c0)
        hh = min(2 * WIN + 1, nrow - r0)
        arr = band.ReadAsArray(c0, r0, w, hh).astype(np.float64)
        arr[arr == CHM_NODATA] = np.nan
        cc, rr = col - c0, row - r0
        centre[i] = arr[rr, cc]
        if np.isfinite(arr).any():
            window_max[i] = np.nanmax(arr)
    return centre, window_max


def metrics(obs, pred):
    m = np.isfinite(obs) & np.isfinite(pred)
    o, p = obs[m], pred[m]
    d = p - o
    oc, pc = o - o.mean(), p - p.mean()
    r = float((oc * pc).sum() / np.sqrt((oc * oc).sum() * (pc * pc).sum())) if oc.any() else float("nan")
    return {
        "n": int(m.sum()),
        "mae": round(float(np.abs(d).mean()), 3),
        "rmse": round(float(np.sqrt((d * d).mean())), 3),
        "r": round(r, 3),
        "bias_mean_pred_minus_obs": round(float(d.mean()), 3),
        "obs_mean": round(float(o.mean()), 3),
        "pred_mean": round(float(p.mean()), 3),
    }


def linear_fit(x, y):
    """閉式最小平方（單變數；避免 BLAS/LAPACK）。"""
    xc, yc = x - x.mean(), y - y.mean()
    slope = float((xc * yc).sum() / (xc * xc).sum())
    return slope, float(y.mean() - slope * x.mean())


def main():
    log("[1/4] 讀取行道樹與 CHM…")
    pts = load_points()
    xy, obs, dist = to_3857(pts)
    ds = gdal.Open(str(CHM))
    centre, wmax = sample(ds, xy)
    ds = None
    res = {"meta": {
        "chm": str(CHM), "chm_res_m": 1.1943, "chm_crs": "EPSG:3857", "chm_nodata": CHM_NODATA,
        "tree_source": TREE_CSV.name, "window": "3x3 (%.1f m)" % (3 * 1.1943),
        "n_candidates": len(pts),
        "note": "配對為同一座標而非同一株樹之嚴格對齊；僅作量級與偏差檢核。",
    }}
    log("[2/4] 計算兩種取樣之指標…")
    res["centre_pixel"] = metrics(obs, centre)
    res["window_max"] = metrics(obs, wmax)
    det = np.isfinite(obs) & np.isfinite(centre) & (centre > 0)
    res["detected_only"] = metrics(obs[det], centre[det])
    res["detection"] = {
        "n_census": int(np.isfinite(obs).sum()),
        "n_chm_positive": int(det.sum()),
        "detection_rate_pct": round(100.0 * float(det.sum()) / float(np.isfinite(obs).sum()), 2),
        "note": "行道樹座標處 CHM>0 之比例；未偵測者計入全樣本誤差。",
    }

    log("[3/4] 校正方案（中心像元）…")
    m = np.isfinite(obs) & np.isfinite(centre)
    o, p, dd = obs[m], centre[m], dist[m]
    bias = float((p - o).mean())
    det_sel = p > 0
    res["calibration_detected_only"] = {
        "raw": metrics(o[det_sel], p[det_sel]),
    }
    b_det = float((p[det_sel] - o[det_sel]).mean())
    res["calibration_detected_only"]["global_offset"] = metrics(o[det_sel], p[det_sel] - b_det)
    res["calibration_detected_only"]["global_offset_value_m"] = round(-b_det, 3)
    sl2, ic2 = linear_fit(p[det_sel], o[det_sel])
    res["calibration_detected_only"]["global_linear"] = metrics(o[det_sel], sl2 * p[det_sel] + ic2)
    res["calibration_detected_only"]["global_linear_coef"] = {
        "slope": round(sl2, 4), "intercept": round(ic2, 3),
        "form": "census_height = %.3f x CHM + %.3f" % (sl2, ic2)}
    res["calibration"] = {
        "raw": metrics(o, p),
        "global_offset": metrics(o, p - bias),
        "global_offset_value_m": round(-bias, 3),
    }
    off = {}
    pred_d = p.copy()
    for d in np.unique(dd):
        sel = dd == d
        b = float((p[sel] - o[sel]).mean())
        off[str(d)] = round(-b, 3)
        pred_d[sel] = p[sel] - b
    res["calibration"]["district_offset"] = metrics(o, pred_d)
    res["calibration"]["district_offset_value_m"] = off
    slope, intercept = linear_fit(p, o)
    res["calibration"]["global_linear"] = metrics(o, slope * p + intercept)
    res["calibration"]["global_linear_coef"] = {
        "slope": round(slope, 4), "intercept": round(intercept, 3),
        "form": "census_height ≈ %.3f × CHM + %.3f" % (slope, intercept),
    }
    if REFPATH.exists():
        res["reference_previous_session"] = json.loads(REFPATH.read_text(encoding="utf-8"))
    res["by_district_bias"] = {
        str(d): {"n": int((dd == d).sum()), "mean_bias_m": round(float((p[dd == d] - o[dd == d]).mean()), 3),
                 "rmse": round(float(np.sqrt(((p[dd == d] - o[dd == d]) ** 2).mean())), 3)}
        for d in np.unique(dd)}

    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    log("[4/4] 繪圖…")
    draw_figure(o, p, res)
    for key in ("centre_pixel", "window_max", "detected_only", "detection"):
        print(key, json.dumps(res[key]))
    for key, val in res["calibration"].items():
        print("calib." + key, json.dumps(val))
    print("wrote", OUT_JSON.name, OUT_PNG.name)
    return 0


def draw_figure(o, p, res):
    W, H = 1900, 760
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 40), "", font=ImageFont.truetype(FB, 40),
           fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 92), "逐棵配對（n = {}）；灰線為 1:1，紅線為閉式線性校正".format(len(o)),
           font=ImageFont.truetype(FR, 24), fill=(90, 90, 90), anchor="ma")

    box = (230, 200, 930, 640)
    d.rectangle(box, outline=(60, 60, 60), width=2)
    xmax = 40.0
    for g in range(0, 41, 10):
        gx = box[0] + g / xmax * (box[2] - box[0])
        gy = box[3] - g / xmax * (box[3] - box[1])
        d.line([(gx, box[1]), (gx, box[3])], fill=(235, 238, 242), width=1)
        d.line([(box[0], gy), (box[2], gy)], fill=(235, 238, 242), width=1)
        d.text((gx, box[3] + 8), str(g), font=ImageFont.truetype(FR, 19), fill=(70, 70, 70), anchor="ma")
        d.text((box[0] - 10, gy), str(g), font=ImageFont.truetype(FR, 19), fill=(70, 70, 70), anchor="rm")
    d.line([(box[0], box[3]), (box[0] + (40 / xmax) * (box[2] - box[0]), box[3] - (40 / xmax) * (box[3] - box[1]))],
           fill=(160, 160, 160), width=2)
    step = max(1, len(o) // 12000)
    for i in range(0, len(o), step):
        gx = box[0] + min(o[i], xmax) / xmax * (box[2] - box[0])
        gy = box[3] - min(p[i], xmax) / xmax * (box[3] - box[1])
        d.point((gx, gy), fill=(70, 90, 120))
    co = res["calibration"]["global_linear_coef"]
    x1, x2 = 0.0, xmax
    y1, y2 = co["slope"] * x1 + co["intercept"], co["slope"] * x2 + co["intercept"]
    d.line([(box[0] + x1 / xmax * (box[2] - box[0]), box[3] - y1 / xmax * (box[3] - box[1])),
            (box[0] + x2 / xmax * (box[2] - box[0]), box[3] - y2 / xmax * (box[3] - box[1]))],
           fill=(200, 40, 40), width=3)
    d.text(((box[0] + box[2]) / 2, box[3] + 40), "普查樹高 (m)", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="ma")
    d.text((box[0] - 95, (box[1] + box[3]) / 2), "CHMv2 (m)", font=ImageFont.truetype(FR, 21),
           fill=(40, 40, 40), anchor="mm")
    raw = res["calibration"]["raw"]
    d.text(((box[0] + box[2]) / 2, box[1] - 34),
           "MAE {mae:.2f} m ／ RMSE {rmse:.2f} m ／ r {r:.2f} ／ bias {bias_mean_pred_minus_obs:.2f} m".format(**raw),
           font=ImageFont.truetype(FB, 23), fill=(40, 40, 40), anchor="ma")

    box2 = (1120, 220, 1840, 620)
    d.line([(box2[0], box2[1]), (box2[0], box2[3])], fill=(60, 60, 60), width=2)
    d.line([(box2[0], box2[3]), (box2[2], box2[3])], fill=(60, 60, 60), width=2)
    byd = res["by_district_bias"]
    keys = sorted(byd, key=lambda k: byd[k]["mean_bias_m"])
    vmax = max(abs(v["mean_bias_m"]) for v in byd.values()) * 1.2
    zer = (box2[1] + box2[3]) / 2
    d.line([(box2[0], zer), (box2[2], zer)], fill=(120, 120, 120), width=2)
    bw = (box2[2] - box2[0]) / max(len(keys), 1)
    for i, k in enumerate(keys):
        v = byd[k]["mean_bias_m"]
        y = zer - v / vmax * ((box2[3] - box2[1]) / 2)
        cx = box2[0] + i * bw + bw * 0.2
        d.rectangle([cx, min(y, zer), cx + bw * 0.6, max(y, zer)],
                    fill=(43, 108, 176) if v < 0 else (183, 121, 31))
        d.text((cx + bw * 0.3, box2[3] + 8), k[:3], font=ImageFont.truetype(FR, 18), fill=(60, 60, 60), anchor="ma")
        d.text((cx + bw * 0.3, y - 6 if v < 0 else y + 6), "{:.1f}".format(v),
               font=ImageFont.truetype(FR, 17), fill=(60, 60, 60), anchor="md" if v < 0 else "ma")
    for gv in (-6, -3, 3, 6):
        gy = zer - gv / vmax * ((box2[3] - box2[1]) / 2)
        d.line([(box2[0], gy), (box2[2], gy)], fill=(238, 241, 245), width=1)
        d.text((box2[0] - 10, gy), str(gv), font=ImageFont.truetype(FR, 18), fill=(90, 90, 90), anchor="rm")
    d.text((box2[0] - 10, zer), "0", font=ImageFont.truetype(FR, 18), fill=(90, 90, 90), anchor="rm")
    d.text(((box2[0] + box2[2]) / 2, box2[1] - 40), "各區平均偏差（CHM - 普查，m）",
           font=ImageFont.truetype(FB, 23), fill=(40, 40, 40), anchor="ma")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PNG)


if __name__ == "__main__":
    sys.exit(main())
