# -*- coding: utf-8 -*-
"""Final numbering fixes: remove the duplicated 表 4.3 caption and renumber Ch5 tables
in strict document order (路網 5.6 → 驗證套件 5.7 → SAI 穩健性 5.8 → 需求側權重 5.9).

Dry run unless --apply.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2')
PAPER = ROOT / 'Paper'
CH4 = PAPER / '第四章_研究設計與方法_正式草稿.md'
CH5 = PAPER / '第五章_研究結果_正式草稿.md'
CH7 = PAPER / '第七章_結論與摘要_正式草稿.md'
BT = ROOT / 'build_thesis.py'
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\final_fix_log.json')

CAP43 = '**表 4.3　跨年整合空間基線資料集之觀測年份與整合規則**'
apply = '--apply' in sys.argv
log = []

# ---- A: 刪除重複的表 4.3 caption（保留與表格相鄰者） ----
lines = CH4.read_text(encoding='utf-8').splitlines()
idx = [i for i, l in enumerate(lines) if l.strip() == CAP43]
if len(idx) == 2:
    # 保留後面那一個（與表格之間已有空行），刪除前面那一個與其後的空行
    drop = idx[0]
    if drop + 1 < len(lines) and not lines[drop + 1].strip():
        del lines[drop:drop + 2]
    else:
        del lines[drop]
    log.append({'file': CH4.name, 'action': 'removed duplicate 表 4.3', 'status': 'ok'})
else:
    log.append({'file': CH4.name, 'action': 'duplicate 表 4.3', 'n': len(idx), 'status': 'skip'})

# ---- B: Ch5 重新編號（以臨時 token 避免衝突） ----
RENUM = [('表 5.8', '表 5.7TMP'), ('表 5.6', '表 5.8'), ('表 5.7', '表 5.9'), ('表 5.7TMP', '表 5.7')]
for f in [CH5, CH4, CH7, BT]:
    is_ch4 = f == CH4
    holder = {'lines': lines if is_ch4 else f.read_text(encoding='utf-8').splitlines()}
    t = '\n'.join(holder['lines'])
    for a, b in RENUM:
        n = t.count(a)
        if n:
            t = t.replace(a, b)
            log.append({'file': f.name, 'rule': '{} -> {}'.format(a, b), 'hits': n, 'status': 'ok'})
    holder['lines'] = t.splitlines()
    if is_ch4:
        lines = holder['lines']
    else:
        holder['path'] = f
        if apply:
            f.write_text('\n'.join(holder['lines']) + '\n', encoding='utf-8')

# ---- C: §5 圖表清單之舊參照（腳手架，不進正文）對齊新編號 ----
t = '\n'.join(lines).replace('- 表 4.3　作業程序與資料品質（92,777→92,626）。',
                             '- 表 4.8　核心分析程式、輸出檔與可重現稽核。')
lines = t.splitlines()
if apply:
    CH4.write_text('\n'.join(lines) + '\n', encoding='utf-8')

LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print('{}: {} actions'.format('APPLIED' if apply else 'DRY-RUN', len(log)))
for e in log:
    print('  ', e.get('status'), e.get('file'), e.get('action') or e.get('rule'), e.get('hits', ''), e.get('n', ''))
