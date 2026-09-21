# -*- coding: utf-8 -*-
"""Figure 11: Taipei VLR green-governance policy language (2019-2025).

Counts keywords in the Chinese VLR texts (from the MarkItDown task) and renders a
line chart. Values come from the actual corpus; absent terms are shown as 0.

Output: Paper/figures/fig11_vlr_policy_language.png (+ wp11_vlr_counts.json)
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
VLR = Path(r"C:\Users\kent6\AppData\Local\Temp\opencode\vlr")
# fall back to the converted .md files in Paper/Sustaianility if the temp corpus is gone
MD = ROOT / "Paper" / "Sustaianility"
FIG = ROOT / "Paper" / "figures"
OUT_JSON = ROOT / "wp11_vlr_counts.json"
FB = r"C:\Windows\Fonts\msjhbd.ttc"
FR = r"C:\Windows\Fonts\msjh.ttc"
YEARS = ["2019", "2020", "2021", "2023", "2025"]
KEYS = ["淨零", "降溫", "公園", "企業", "碳匯", "樹冠", "都市林", "Open Green"]
COLORS = {"淨零": (24, 106, 62), "降溫": (200, 60, 60), "公園": (60, 90, 200),
          "企業": (230, 150, 40), "碳匯": (120, 80, 160), "樹冠": (0, 0, 0),
          "都市林": (140, 140, 140), "Open Green": (0, 160, 160)}


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
    counts = {}
    for y in YEARS:
        flat = re.sub(r"\s+", "", docs.get(y, ""))
        counts[y] = {k: flat.count(k) for k in KEYS}
    OUT_JSON.write_text(json.dumps(counts, ensure_ascii=False, indent=1), encoding="utf-8")

    W, H, ML, MB, MT, MR = 1400, 760, 130, 110, 90, 320
    c = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(c)
    d.text((W / 2, 24), "",
           font=ImageFont.truetype(FB, 38), fill=(20, 20, 20), anchor="ma")
    x0, x1, y0, y1 = ML, W - MR, MT, H - MB
    vmax = max(max(counts[y].values()) for y in YEARS) * 1.1
    for gy in range(0, int(vmax) + 1, 40):
        yy = y1 - gy / vmax * (y1 - y0)
        d.line([(x0, yy), (x1, yy)], fill=(228, 228, 228))
        d.text((x0 - 12, yy), f"{gy}", font=ImageFont.truetype(FR, 22), fill=(70, 70, 70), anchor="rm")
    for i, y in enumerate(YEARS):
        xx = x0 + i * (x1 - x0) / (len(YEARS) - 1)
        d.line([(xx, y0), (xx, y1)], fill=(240, 240, 240))
        d.text((xx, y1 + 14), y, font=ImageFont.truetype(FR, 24), fill=(60, 60, 60), anchor="ma")
    d.line([(x0, y0), (x0, y1)], fill=(30, 30, 30), width=2)
    d.line([(x0, y1), (x1, y1)], fill=(30, 30, 30), width=2)
    for k in KEYS:
        pts = []
        for i, y in enumerate(YEARS):
            v = counts[y][k]
            xx = x0 + i * (x1 - x0) / (len(YEARS) - 1)
            yy = y1 - v / vmax * (y1 - y0)
            pts.append((xx, yy, v))
        if max(v for _, _, v in pts) == 0:
            for a, b in zip(pts[:-1], pts[1:]):  # 全期 0 者用底端虛線標記
                for t0, t1 in ((0, 0.5), (0.6, 1.0)):
                    d.line([(a[0] + (b[0] - a[0]) * t0, y1 - 3),
                            (a[0] + (b[0] - a[0]) * t1, y1 - 3)], fill=COLORS[k], width=4)
        else:
            w = 6 if k in ("淨零", "公園") else 4   # 關鍵趨勢線加粗
            d.line([(p[0], p[1]) for p in pts], fill=COLORS[k], width=w)
        for xx, yy, v in pts:
            d.ellipse([xx - 4, yy - 4, xx + 4, yy + 4], fill=COLORS[k])
    # legend
    lx, ly = x1 + 24, y0 + 6
    for k in KEYS:
        d.line([(lx, ly + 10), (lx + 34, ly + 10)], fill=COLORS[k], width=4)
        d.text((lx + 44, ly + 10), k, font=ImageFont.truetype(FR, 26), fill=(50, 50, 50), anchor="lm")
        ly += 42
    d.text((x0, H - 44), "註：數值為 VLR 中文版全文去空白後之字面計數；「樹冠」「都市林」「Open Green」全期為 0。"
                         "詞頻僅描述政策語言，非政策成效。",
           font=ImageFont.truetype(FR, 22), fill=(90, 90, 90))
    FIG.mkdir(parents=True, exist_ok=True)
    c.save(FIG / "fig11_vlr_policy_language.png")
    print("saved fig11_vlr_policy_language.png", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
