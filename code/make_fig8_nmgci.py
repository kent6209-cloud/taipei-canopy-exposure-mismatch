# -*- coding: utf-8 -*-
"""Figure 8: NMGCI four-component theoretical model (Source x Demand x Capital
x Coupling) on a four-ledger base.

Replaces the former fig10_nmgci.png, where straight centre-to-centre arrows ran
across the component boxes and over their text.  Arrows now run edge-to-edge
along the ring, so no text is crossed.

Output: Paper/figures/fig10_nmgci.png   (圖 8 in the thesis)
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
W, H = 1300, 940
CX, CY = W / 2, 400
RX, RY = 235, 100
GREEN, GREY = (24, 106, 62), (140, 140, 140)


def font(p, s):
    return ImageFont.truetype(p, s)


def box(d, cx, cy, text, solid):
    xy = [cx - RX, cy - RY, cx + RX, cy + RY]
    d.rounded_rectangle(xy, radius=14, fill=(226, 240, 226) if solid else (243, 243, 243),
                        outline=(110, 130, 110) if solid else (165, 165, 165), width=3)
    d.multiline_text((cx, cy), text, font=font(FB, 22), fill=(20, 20, 20),
                     anchor="mm", align="center", spacing=7)


def edge(cx, cy, tx, ty):
    """Point where the ray from a box centre to (tx,ty) leaves the box."""
    dx, dy = tx - cx, ty - cy
    tx_ = RX / abs(dx) if dx else 1e9
    ty_ = RY / abs(dy) if dy else 1e9
    t = min(tx_, ty_)
    return cx + dx * t, cy + dy * t


def ring_arrow(d, p0, p1, solid):
    a = edge(p0[0], p0[1], p1[0], p1[1])
    b = edge(p1[0], p1[1], p0[0], p0[1])
    col = GREEN if solid else GREY
    if solid:
        d.line([a, b], fill=col, width=5)
    else:
        n = max(3, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 16))
        for i in range(n):
            t0, t1 = i / n, min((i + 0.55) / n, 1)
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                    (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)],
                   fill=col, width=5)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (2.6, -2.6):
        d.line([b, (b[0] + 20 * math.cos(ang + da), b[1] + 20 * math.sin(ang + da))],
               fill=col, width=5)


def main():
    c = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    d.text((W / 2, 26), "",
           font=font(FB, 38), fill=(20, 20, 20), anchor="ma")

    comp = [
        ((CX, 190), "SOURCE 生態供給\nCHM／DEM／綠地分類\nΣH（結構型相對代理）\nWhere is supply?", True),
        ((W - 240, CY), "DEMAND 需求\n人口密度／居住網格\n500 m 生活圈\nWhere is need?", True),
        ((CX, 650), "CAPITAL 資本配置\n企業／Open Green 專案\n依帳本配置\nWhere does capital go?", False),
        ((240, CY), "COUPLING 制度耦合\nDigital Twin／社群共作\n維護與持續\nHow are they connected?", False),
    ]
    for (x, y), t, solid in comp:
        box(d, x, y, t, solid)
    for i in range(4):
        ring_arrow(d, comp[i][0], comp[(i + 1) % 4][0], comp[i][2] and comp[(i + 1) % 4][2])

    d.ellipse([CX - 118, CY - 118, CX + 118, CY + 118], outline=GREEN, width=6)
    d.multiline_text((CX, CY), "NMGCI\n近山綠碳\n介面治理", font=font(FB, 30),
                     fill=GREEN, anchor="mm", align="center", spacing=6)

    d.text((W - 240, CY + RY + 26), "SAI＝自需求位置之綠意供給暴露",
           font=font(FR, 21), fill=(90, 90, 90), anchor="ma")

    d.rounded_rectangle([70, 800, W - 70, 888], radius=14, fill=(214, 232, 214),
                        outline=(110, 130, 110), width=3)
    d.text((W / 2, 844),
           "四層帳本（accounting boundary，非加總為單一 CO2e）：\n"
           "L1 排放（Scope 1/2/3）｜L2 碳移除（方法學）｜L3 自然與調適｜L4 社會與治理",
           font=font(FR, 22), fill=(20, 20, 20), anchor="mm", align="center", spacing=6)
    d.text((70, 900),
           "實線＝P1 已有實證；虛線＝P2–P4 待驗證。Digital Twin 為決策介面，非 3D 展示。"
           "等量資本不保證等量效益——位置決定誰受益。",
           font=font(FR, 20), fill=(120, 120, 120))

    FIG.mkdir(parents=True, exist_ok=True)
    c.save(FIG / "fig10_nmgci.png")
    print("fig8 nmgci done", c.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
