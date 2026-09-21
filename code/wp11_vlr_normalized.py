# -*- coding: utf-8 -*-
"""Figure 1: Taipei VLR green-governance policy language (2019-2025), raw counts + per-10,000.

Corpus: Chinese-language VLR reports only (Paper/Sustaianility/*.md, English editions excluded).
NOTE: the earlier figure used a temp folder that also contained an English edition and a
derived 'snippets' file, which double-counted the 2025 values (e.g. 淨零 199 instead of 100).
This script uses the Chinese full reports only and reports normalised frequency per 10,000 CJK
characters so that year-to-year length differences cannot drive the trend.

Outputs:
  wp11_vlr_normalized.json                       (counts, CJK char counts, per-10k)
  Paper/figures/fig11_vlr_policy_language.png    (two panels: counts | per 10,000 chars)
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MD = ROOT / 'Paper' / 'Sustaianility'
FIG = ROOT / 'Paper' / 'figures'
JSON_OUT = ROOT / 'wp11_vlr_normalized.json'
FB = r'C:\Windows\Fonts\msjhbd.ttc'
FR = r'C:\Windows\Fonts\msjh.ttc'
YEARS = ['2019', '2020', '2021', '2023', '2025']
KEYS = ['淨零', '降溫', '公園', '企業', '碳匯', '樹冠', '都市林', 'Open Green']
ZERO = ['樹冠', '都市林', 'Open Green']
COLORS = {'淨零': (24, 106, 62), '降溫': (200, 60, 60), '公園': (60, 90, 200),
          '企業': (230, 150, 40), '碳匯': (120, 80, 160), '樹冠': (0, 0, 0),
          '都市林': (140, 140, 140), 'Open Green': (0, 160, 160)}
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
W, H = 1800, 860
PANEL = [(110, 560), (980, 1400)]
MT, MB = 150, 190


def font(p, s):
    return ImageFont.truetype(p, s)


def corpus():
    docs = {}
    for f in sorted(MD.glob('*.md')):
        m = re.search(r'(20\d\d)', f.name)
        if not m or m.group(1) not in YEARS:
            continue
        if '英' in f.name or 'English' in f.name:
            continue
        docs.setdefault(m.group(1), '')
        docs[m.group(1)] += f.read_text(encoding='utf-8')
    return docs


def panel(d, x0, x1, y0, y1, series, title, ylab, ymax, label_ends=True):
    for gy in range(0, int(ymax) + 1, max(1, int(ymax // 5))):
        yy = y1 - gy / ymax * (y1 - y0)
        d.line([(x0, yy), (x1, yy)], fill=(230, 230, 230))
        d.text((x0 - 12, yy), str(gy), font=font(FR, 22), fill=(70, 70, 70), anchor='rm')
    xs = [x0 + i * (x1 - x0) / (len(YEARS) - 1) for i in range(len(YEARS))]
    for xx, y in zip(xs, YEARS):
        d.line([(xx, y0), (xx, y1)], fill=(242, 242, 242))
        d.text((xx, y1 + 16), y, font=font(FR, 24), fill=(60, 60, 60), anchor='ma')
    d.line([(x0, y0), (x0, y1)], fill=(30, 30, 30), width=2)
    d.line([(x0, y1), (x1, y1)], fill=(30, 30, 30), width=2)
    d.text((x0, y0 - 30), title, font=font(FB, 26), fill=(40, 40, 40), anchor='lm')
    d.text((x0, y1 + 54), ylab, font=font(FR, 21), fill=(110, 110, 110), anchor='lm')
    for k in KEYS:
        if k in ZERO:
            continue
        pts = [(xx, y1 - series[y][k] / ymax * (y1 - y0)) for xx, y in zip(xs, YEARS)]
        d.line(pts, fill=COLORS[k], width=6 if k in ('淨零', '公園') else 4)
        for xx, yy in pts:
            d.ellipse([xx - 5, yy - 5, xx + 5, yy + 5], fill=COLORS[k])
        if label_ends:
            d.text((pts[-1][0] + 14, pts[-1][1]), '{:g}'.format(series[YEARS[-1]][k]),
                   font=font(FB, 22), fill=COLORS[k], anchor='lm')
    d.line([(x0, y1 - 3), (x1, y1 - 3)], fill=(160, 160, 160), width=4)


def main():
    docs = corpus()
    data = {}
    counts, per10k = {}, {}
    for y in YEARS:
        txt = re.sub(r'\s+', '', docs.get(y, ''))
        n_cjk = len(CJK.findall(txt))
        c = {k: txt.count(k) for k in KEYS}
        p = {k: round(c[k] / n_cjk * 10000, 1) for k in KEYS}
        data[y] = {'n_cjk_chars': n_cjk, 'counts': c, 'per10k': p}
        counts[y], per10k[y] = c, p
    JSON_OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')

    c = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(c)
    d.text((W / 2, 26), '', font=font(FB, 38), fill=(20, 20, 20), anchor='ma')
    y0, y1 = MT, H - MB
    cmax = max(v for y in YEARS for k, v in counts[y].items()) * 1.15
    pmax = max(v for y in YEARS for k, v in per10k[y].items()) * 1.15
    panel(d, PANEL[0][0], PANEL[0][1], y0, y1, counts, '(a) 字面計數（次）',
          'VLR 年度（現有版本，非等距）', cmax)
    panel(d, PANEL[1][0], PANEL[1][1], y0, y1, per10k, '(b) 標準化詞頻（每萬中文字次）',
          'VLR 年度（現有版本，非等距）', pmax)

    lx, ly = PANEL[1][1] + 80, y0 + 10
    for k in KEYS:
        greyed = k in ZERO
        d.line([(lx, ly + 10), (lx + 34, ly + 10)],
               fill=(190, 190, 190) if greyed else COLORS[k], width=4)
        d.text((lx + 44, ly + 10), k + ('（0）' if greyed else ''),
               font=font(FR, 25), fill=(150, 150, 150) if greyed else (50, 50, 50), anchor='lm')
        ly += 44
    d.text((lx, ly + 16), '灰線：三詞全期 0', font=font(FR, 20), fill=(150, 150, 150), anchor='lm')

    note = font(FR, 21)
    d.text((110, H - 70),
           '註：語料為 VLR 中文版全文（英譯版排除）；(b) 為每萬中文字之標準化頻率，用以排除各年度篇幅差異。',
           font=note, fill=(110, 110, 110))
    d.text((110, H - 40),
           '詞頻僅描述政策語言的關注焦點，非政策成效、非預算，亦不代表實際綠化行動。',
           font=note, fill=(110, 110, 110))

    FIG.mkdir(parents=True, exist_ok=True)
    c.save(FIG / 'fig11_vlr_policy_language.png')
    print('wrote', JSON_OUT.name, 'and', (FIG / 'fig11_vlr_policy_language.png').name)
    for y in YEARS:
        print(y, 'CJK={:,}'.format(data[y]['n_cjk_chars']), data[y]['per10k'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
