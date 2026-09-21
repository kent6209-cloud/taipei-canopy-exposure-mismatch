# -*- coding: utf-8 -*-
"""Figure 7: equal-canopy-investment what-if scenarios (three allocation rules).

Replaces the former fig9_scenarios.png, whose bars overflowed the canvas, whose
labels were clipped and which printed counts in scientific notation.  Three
rows share one rule axis:

  (1) 人口加權 SAI 增益（分）
  (2) 受益人口（相對單位，千人）
  (3) 配置落點之高程帶組成（%）

Output: Paper/figures/fig9_scenarios.png   (圖 7 in the thesis)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "Paper" / "figures"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
RULES = [("A_carbon_first", "A　碳優先\n（高 ΣH 格）", (52, 108, 66)),
         ("B_demand_first", "B　需求優先\n（高人口格）", (36, 84, 186)),
         ("C_balanced", "C　均衡\n（供需並重）", (60, 150, 150))]
BANDS = [("平地 0–20 m", (219, 231, 201)), ("近山 20–300 m", (150, 197, 132)),
         ("山地 >300 m", (52, 108, 66))]
W, H = 1720, 1180
LX, PX0, PX1 = 40, 330, 1440


def font(p, s):
    return ImageFont.truetype(p, s)


def main():
    data = json.loads((ROOT / "wp4_scenario_simulator.json").read_text(encoding="utf-8"))
    sc = data["scenarios"]
    rows = {k: sc[k] for k, _, _ in RULES}

    c = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    d.text((W / 2, 24), "",
           font=font(FB, 40), fill=(20, 20, 20), anchor="ma")
    d.text((W / 2, 74),
           "Model-based what-if（等量增冠假設：每選中格 +3 m；非經驗成效、非因果）",
           font=font(FR, 24), fill=(200, 60, 60), anchor="ma")

    def heading(y, text):
        d.text((LX, y), text, font=font(FB, 27), fill=(24, 106, 62))
        d.line([(LX, y + 40), (PX1, y + 40)], fill=(225, 225, 225), width=2)

    def bar_row(y, values, unit, fmt, vmax):
        w = (PX1 - PX0)
        for i, (key, lab, col) in enumerate(RULES):
            yy = y + i * 62
            d.text((LX, yy + 16), lab, font=font(FR, 21), fill=(50, 50, 50), anchor="lm")
            bw = w * values[key] / vmax if vmax else 0
            d.rectangle([PX0, yy, PX0 + max(bw, 2), yy + 32], fill=col)
            d.text((PX0 + bw + 12, yy + 16), fmt(values[key]) + unit,
                   font=font(FB, 22), fill=(50, 50, 50), anchor="lm")

    heading(130, "（1）人口加權 SAI 增益（分）")
    bar_row(190, {k: rows[k]["pop_weighted_sai_gain"] for k, _, _ in RULES}, "",
            lambda v: f"{v:.3f}", 0.9)

    heading(400, "（2）受益人口（相對單位，千人）")
    bar_row(460, {k: rows[k]["beneficiary_pop_units"] / 1000.0 for k, _, _ in RULES},
            " 千人", lambda v: f"{v:,.1f}", 231.71)

    heading(670, "（3）配置落點之高程帶組成（%）　＋ 平均高程")
    for i, (key, lab, col) in enumerate(RULES):
        yy = 730 + i * 62
        s = rows[key]
        seg = [s["share_flat_pct"], 100.0 - s["share_flat_pct"] - s["share_mountain_pct"],
               s["share_mountain_pct"]]
        cx = PX0
        for (blab, bcol), v in zip(BANDS, seg):
            bw = (PX1 - PX0) * v / 100.0
            d.rectangle([cx, yy, cx + bw, yy + 32], fill=bcol, outline=(255, 255, 255))
            if bw > 90:
                d.text((cx + bw / 2, yy + 16), f"{v:.1f}%", font=font(FB, 20),
                       fill=(20, 20, 20), anchor="mm")
            cx += bw
        d.rectangle([PX0, yy, PX1, yy + 32], outline=(120, 120, 120))
        d.text((PX1 + 14, yy + 16), f"平均高程 {s['mean_elev_m']:.0f} m",
               font=font(FR, 21), fill=(70, 70, 70), anchor="lm")

    ly = 942
    for i, (blab, bcol) in enumerate(BANDS):
        d.rectangle([PX0 + i * 240, ly, PX0 + 26 + i * 240, ly + 20], fill=bcol)
        d.text((PX0 + 36 + i * 240, ly + 10), blab, font=font(FR, 21),
               fill=(60, 60, 60), anchor="lm")

    note = font(FR, 20)
    d.text((LX, 1010),
           "註：三情境皆投入 500 格、增冠 +3 m，故碳代理增益（1,500 m·ha）為模型假設而非發現；"
           "效益差異僅反映配置規則。", font=note, fill=(110, 110, 110))
    d.text((LX, 1042),
           "SAI 增益為全市人口加權平均之變化；受益人口為相對單位（population units），"
           "非實際受惠人數推估。", font=note, fill=(110, 110, 110))
    d.text((LX, 1074),
           "高 ΣH 格（A）多落於 300 m 以上山地，故需求端效益近零；此為位置配置結果，非減碳效率比較。",
           font=note, fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    c.save(FIG / "fig9_scenarios.png")
    print("fig7 scenarios done", c.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
