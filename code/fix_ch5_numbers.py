# -*- coding: utf-8 -*-
"""Explicit, collision-free fix of the four Chapter-5 table numbers and their references."""
import json
import pathlib
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
BT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\build_thesis.py')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\fix_ch5_log.json')

RULES = [
    # captions
    ('**表 5.8　居住網格至最近綠源之路網距離與歐氏距離比較表**',
     '**表 5.6　居住網格至最近綠源之路網距離與歐氏距離比較表**'),
    ('**表 5.9TMP　敏感度與穩健性驗證套件（Validation Suite）總覽表**',
     '**表 5.7　敏感度與穩健性驗證套件（Validation Suite）總覽表**'),
    # references to the SAI robustness table inside §5.6 narrative
    ('與權重敏感度計算 SAI（表 5.8）。', '與權重敏感度計算 SAI（表 5.8）。'),
]

apply = '--apply' in sys.argv
log = []
files = [PAPER / '第五章_研究結果_正式草稿.md', PAPER / '第四章_研究設計與方法_正式草稿.md',
         PAPER / '第七章_結論與摘要_正式草稿.md', BT]
for f in files:
    t = f.read_text(encoding='utf-8')
    orig = t
    for a, b in RULES:
        n = t.count(a)
        if n and a != b:
            t = t.replace(a, b)
            log.append({'file': f.name, 'rule': a[:40], 'hits': n, 'status': 'ok'})
    if t != orig and apply:
        f.write_text(t, encoding='utf-8')
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print('{}: {} edits'.format('APPLIED' if apply else 'DRY-RUN', len(log)))
for e in log:
    print('  ', e['file'], e['rule'])
