# -*- coding: utf-8 -*-
"""Figures 1 and 10, redesigned per the academic review.

圖 1  研究設計與 RQ-WP 論證架構（三層；實線=已實證、虛線=待驗證）
圖 10 NMGCI 四構件理論模型（Source x Demand x Capital x Coupling + 四層帳本底座）

Outputs overwrite Paper/figures/fig1_framework.png and fig10_nmgci.png.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"


def font(p, s):
    return ImageFont.truetype(p, s)


def save(canvas, path):
    try:
        Image.Image.save(canvas, str(path))
    except OSError:
        alt = path.with_name(path.stem + "_new" + path.suffix)
        Image.Image.save(canvas, str(alt)); print("  (locked) ->", alt.name)


def box(d, xy, text, fill=(233, 242, 232), fs=22, bold=True):
    d.rounded_rectangle(xy, radius=12, fill=fill, outline=(110, 120, 110), width=2)
    d.multiline_text(((xy[0] + xy[2]) / 2, (xy[1] + xy[3]) / 2), text,
                     font=font(FB if bold else FR, fs), fill=(20, 20, 20),
                     anchor="mm", align="center")


def arrow(d, p0, p1, col=(90, 100, 90), dashed=False, width=4):
    x0, y0 = p0; x1, y1 = p1
    if not dashed:
        d.line([p0, p1], fill=col, width=width)
    else:
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 14))
        for i in range(n):
            t0 = i / n; t1 = min((i + 0.55) / n, 1)
            d.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                    (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=col, width=width)
    a = math.atan2(y1 - y0, x1 - x0)
    for da in (2.6, -2.6):
        d.line([(x1, y1), (x1 + 18 * math.cos(a + da), y1 + 18 * math.sin(a + da))],
               fill=col, width=width)


def fig1():
    W, H = 1720, 980
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 26), "", font=font(FB, 42), fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 74), "實線＝已有實證（RQ1／P1）　虛線＝待驗證（RQ2–RQ3／P2–P4）",
           font=font(FR, 24), fill=(120, 120, 120), anchor="ma")

    # Layer 1: RQ
    d.text((40, 120), "第一層　研究問題", font=font(FB, 26), fill=(24, 106, 62))
    rq = [("RQ1\n空間錯置", True), ("RQ2\n企業氣候資本配置", False), ("RQ3\n治理耦合", False)]
    bw = 420; gap = 40; x0 = (W - (len(rq) * bw + (len(rq) - 1) * gap)) / 2
    for i, (t, solid) in enumerate(rq):
        x = x0 + i * (bw + gap)
        box(d, [x, 158, x + bw, 268], t, fill=(226, 240, 226) if solid else (242, 242, 242), fs=26)

    # Layer 2: data / method / evidence-freeze
    d.text((40, 316), "第二層　資料與方法", font=font(FB, 26), fill=(24, 106, 62))
    data = "CHMv2 樹冠高度\n5 m DEM\n行道樹普查（92,626）\n100 m 綠地分類\nWorldPop 人口密度\nOpen Green 案例\n企業自然／碳專案"
    box(d, [x0, 354, x0 + 520, 560], data, fs=22, bold=False)
    box(d, [x0 + 560, 354, x0 + 940, 560], "資料品質控制\nEvidence Freeze\n單一權威資料庫\n投影／面積校正\n(EPSG:3826, cos²lat)", fs=22)
    box(d, [x0 + 980, 354, x0 + 1500, 560],
        "空間分析與統計\n高程帶 ΣH｜SAI｜人口加權\nMoran's I／LISA／四象限\n空間區塊 bootstrap／置換\n路網距離檢核｜情境模擬", fs=22, bold=False)
    for cx in (x0 + 540, x0 + 960):
        arrow(d, (cx, 457), (cx + 20, 457))
    for i in range(3):
        x = x0 + i * (bw + gap) + bw / 2
        arrow(d, (x, 268), (x, 354), dashed=not rq[i][1])

    # Layer 3: WP outputs
    d.text((40, 604), "第三層　研究產出", font=font(FB, 26), fill=(24, 106, 62))
    wps = [("資料整備\n供給側\nΣH／樹冠結構", True), ("指標構建\n需求側\nSAI／人口加權\n空間錯置", True),
           ("案例登錄\n資本案例\n投入—效益—帳本—空間", False), ("情境模擬\n多效益配置\n情境（what-if）", False),
           ("治理延伸\n治理耦合\nproposed", False)]
    bw2 = 300; g2 = 24
    x2 = (W - (len(wps) * bw2 + (len(wps) - 1) * g2)) / 2
    for i, (t, solid) in enumerate(wps):
        x = x2 + i * (bw2 + g2)
        box(d, [x, 642, x + bw2, 786], t, fill=(226, 240, 226) if solid else (242, 242, 242), fs=20)
        if i:
            arrow(d, (x - g2 + 2, 714), (x - 2, 714), dashed=not solid)
    box(d, [x2, 826, x2 + len(wps) * bw2 + (len(wps) - 1) * g2, 906],
        "NMGCI 中程分析框架　＋　四層帳本（L1 排放｜L2 碳移除｜L3 自然調適｜L4 社會治理）",
        fill=(214, 232, 214), fs=24)
    arrow(d, (W / 2, 786), (W / 2, 826), dashed=True)
    d.text((x2, 926), "註：情境模擬 為決策支援 what-if 情境，非實證成效；治理延伸 為 proposed 治理架構，尚未驗證。",
           font=font(FR, 22), fill=(120, 120, 120))
    FIG.mkdir(parents=True, exist_ok=True)
    save(c, FIG / "fig1_framework.png"); print("fig1 done")


def fig10():
    W, H = 1240, 880
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 24), "",
           font=font(FB, 38), fill=(20, 20, 20), anchor="ma")
    cx, cy = W / 2, 380
    d.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], outline=(24, 106, 62), width=5)
    d.multiline_text((cx, cy), "NMGCI\n近山綠碳\n介面治理", font=font(FB, 28), fill=(24, 106, 62),
                     anchor="mm", align="center")
    comp = {
        "SOURCE 生態供給\nCHM／DEM／綠地\nΣH（結構代理）\nWhere is supply?": (cx, 150, True),
        "DEMAND 需求\n人口密度／居住網格\n500 m 生活圈\nWhere is need?": (W - 210, cy, True),
        "CAPITAL 資本配置\n企業／Open Green 專案\n依帳本配置\nWhere does capital go?": (cx, 640, False),
        "COUPLING 制度耦合\nDigital Twin／社群共作\n維護持續\nHow are they connected?": (210, cy, False),
    }
    positions = {}
    for t, (x, y, solid) in comp.items():
        rx, ry = 210, 92
        box(d, [x - rx, y - ry, x + rx, y + ry], t,
            fill=(226, 240, 226) if solid else (242, 242, 242), fs=20)
        positions[t] = (x, y)
    # SAI note attached to Demand
    d.text((W - 210, cy + 108), "SAI＝自需求位置之綠意供給暴露", font=font(FR, 20),
           fill=(90, 90, 90), anchor="ma")
    # ring arrows (solid for Source/Demand, dashed for Capital/Coupling)
    pts = list(comp.values())
    for i in range(4):
        (x0, y0, s0) = pts[i]; (x1, y1, s1) = pts[(i + 1) % 4]
        arrow(d, (x0, y0), (x1, y1), dashed=not (s0 and s1))
    # four-ledger base
    d.rounded_rectangle([80, 760, W - 80, 846], radius=12, fill=(214, 232, 214), outline=(110, 120, 110), width=2)
    d.text((W / 2, 803),
           "四層帳本（accounting boundary，非加總為單一 CO₂e）：\n"
           "L1 排放（Scope 1/2/3）｜L2 碳移除（方法學）｜L3 自然與調適｜L4 社會與治理",
           font=font(FR, 22), fill=(20, 20, 20), anchor="mm", align="center")
    d.text((80, 858), "實線＝P1 已有實證；虛線＝P2–P4 待驗證。Digital Twin 為決策介面，非 3D 展示。",
           font=font(FR, 20), fill=(120, 120, 120))
    save(c, FIG / "fig10_nmgci.png"); print("fig10 done")


def main():
    # fig10() is superseded by make_fig8_nmgci.py (圖 3-1) and no longer run here.
    fig1()
    return 0


if __name__ == "__main__":
    sys.exit(main())
