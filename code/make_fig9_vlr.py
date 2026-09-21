# -*- coding: utf-8 -*-
"""Figure 9: Taipei VLR green-governance policy language (2019-2025).

Replaces the former fig11_vlr_policy_language.png: the note ran off the canvas,
three all-zero series were drawn on top of each other and the y axis had no
label.  Here the zero series are collected into one annotated zero line and the
2025 values are labelled at the line ends.

Output: Paper/figures/fig11_vlr_policy_language.png   (圖 9 in the thesis)
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VLR = Path(r"C:\Users\kent6\AppData\Local\Temp\opencode\vlr")
MD = ROOT / "Paper" / "Sustaianility"
FIG = ROOT / "Paper" / "figures"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
YEARS = ["2019", "2020", "2021", "2023", "2025"]
KEYS = ["淨零", "降溫", "公園", "企業", "碳匯", "樹冠", "都市林", "Open Green"]
ZERO = ["樹冠", "都市林", "Open Green"]
COLORS = {"淨零": (24, 106, 62), "降溫": (200, 60, 60), "公園": (60, 90, 200),
          "企業": (230, 150, 40), "碳匯": (120, 80, 160), "樹冠": (0, 0, 0),
          "都市林": (140, 140, 140), "Open Green": (0, 160, 160)}
W, H, ML, MB, MT, MR = 1600, 820, 170, 130, 96, 330


def font(p, s):
    return ImageFont.truetype(p, s)


def corpus():
    docs = {}
    if VLR.exists():
        for f in sorted(VLR.glob("*.txt")):
            m = re.search(r"(20\d\d)", f.name)
            if m and m.group(1) in YEARS:
                docs.setdefault(m.group(1), "")
                docs[m.group(1)] += f.read_text(encoding="utf-8")
    if not docs and MD.exists():
        for f in sorted(MD.glob("*.md")):
            m = re.search(r"(20\d\d)", f.name)
            if m and m.group(1) in YEARS and "英" not in f.name and "English" not in f.name:
                docs.setdefault(m.group(1), "")
                docs[m.group(1)] += f.read_text(encoding="utf-8")
    return docs


def main():
    docs = corpus()
    counts = {y: {k: re.sub(r"\s+", "", docs.get(y, "")).count(k) for k in KEYS} for y in YEARS}
    (ROOT / "wp11_vlr_counts.json").write_text(
        json.dumps(counts, ensure_ascii=False, indent=1), encoding="utf-8")

    c = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    d.text((W / 2, 24), "",
           font=font(FB, 38), fill=(20, 20, 20), anchor="ma")
    x0, x1, y0, y1 = ML, W - MR, MT, H - MB
    vmax = max(v for y in YEARS for k, v in counts[y].items()) * 1.12

    for gy in range(0, 221, 40):
        yy = y1 - gy / vmax * (y1 - y0)
        d.line([(x0, yy), (x1, yy)], fill=(230, 230, 230))
        d.text((x0 - 12, yy), f"{gy}", font=font(FR, 22), fill=(70, 70, 70), anchor="rm")
    xs = [x0 + i * (x1 - x0) / (len(YEARS) - 1) for i in range(len(YEARS))]
    for xx, y in zip(xs, YEARS):
        d.line([(xx, y0), (xx, y1)], fill=(242, 242, 242))
        d.text((xx, y1 + 16), y, font=font(FR, 24), fill=(60, 60, 60), anchor="ma")
    d.line([(x0, y0), (x0, y1)], fill=(30, 30, 30), width=2)
    d.line([(x0, y1), (x1, y1)], fill=(30, 30, 30), width=2)
    d.text((x0, y0 - 26), "字面計數（次）", font=font(FB, 24), fill=(60, 60, 60), anchor="lm")
    d.text((x0, y1 + 54), "VLR 年度（現有版本，非等距）", font=font(FR, 20),
           fill=(120, 120, 120), anchor="lm")

    for k in KEYS:
        if k in ZERO:
            continue
        pts = [(xx, y1 - counts[y][k] / vmax * (y1 - y0)) for xx, y in zip(xs, YEARS)]
        w = 6 if k in ("淨零", "公園") else 4
        d.line(pts, fill=COLORS[k], width=w)
        for xx, yy in pts:
            d.ellipse([xx - 5, yy - 5, xx + 5, yy + 5], fill=COLORS[k])
        d.text((pts[-1][0] + 14, pts[-1][1]), f"{counts[YEARS[-1]][k]}",
               font=font(FB, 22), fill=COLORS[k], anchor="lm")

    d.line([(x0, y1 - 3), (x1, y1 - 3)], fill=(160, 160, 160), width=4)

    lx, ly = x1 + 90, y0 + 10
    for k in KEYS:
        greyed = k in ZERO
        d.line([(lx, ly + 10), (lx + 34, ly + 10)],
               fill=(190, 190, 190) if greyed else COLORS[k], width=4)
        d.text((lx + 44, ly + 10), k + ("（0）" if greyed else ""),
               font=font(FR, 25), fill=(150, 150, 150) if greyed else (50, 50, 50), anchor="lm")
        ly += 44
    d.text((lx, ly + 16), "灰線：三詞全期 0", font=font(FR, 20), fill=(150, 150, 150), anchor="lm")

    note = font(FR, 21)
    d.text((ML, H - 66),
           "註：數值為 VLR 中文版全文去空白後之字面計數（keyword occurrence），未經詞形還原；"
           "「樹冠」「都市林」「Open Green」全期為 0。", font=note, fill=(110, 110, 110))
    d.text((ML, H - 36),
           "詞頻僅描述政策語言的關注焦點，非政策成效、非預算、亦不代表實際綠化行動。",
           font=note, fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    c.save(FIG / "fig11_vlr_policy_language.png")
    print("fig9 vlr done", c.size, counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
