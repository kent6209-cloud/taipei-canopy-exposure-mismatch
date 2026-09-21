# -*- coding: utf-8 -*-
"""P0 pass 4: final WP-label clean-up (internal file references + appendix titles)."""
import json
import pathlib
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
BT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\build_thesis.py')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\p0_pass4_log.json')

RULES = [
    ('（詳 `Paper/WP3_OpenGreen案例登錄表與編碼規範.md`）', '（詳附錄 D 案例編碼協定）'),
    ('見《WP3_OpenGreen案例登錄表與編碼規範》', '見附錄 D 案例編碼協定'),
    ('WP3_OpenGreen 案例登錄表與編碼規範', '附錄 D 案例編碼協定'),
    ('| WP1 資料稽核（92,777→92,626） |', '| 資料稽核（92,777→92,626） |'),
    ('### 附錄 I　年 NPP 通量產品之可用性檢核（WP3 延伸之資料障礙）',
     '### 附錄 I　年 NPP 通量產品之可用性檢核（通量延伸之資料障礙）'),
    ('是否足以支持 WP3 之時序／空間通量分析', '是否足以支持時序／空間通量分析'),
]

apply = '--apply' in sys.argv
log = []
for f in sorted(PAPER.glob('第*_正式草稿.md')) + [BT]:
    t = f.read_text(encoding='utf-8')
    orig = t
    for pat, rep in RULES:
        n = t.count(pat)
        if n:
            t = t.replace(pat, rep)
        log.append({'file': f.name, 'rule': pat[:40], 'hits': n})
    if t != orig:
        if apply:
            f.write_text(t, encoding='utf-8')
        log.append({'file': f.name, 'written': True})

LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
miss = [e for e in log if e.get('hits') == 0]
print('{}: {} hits, {} misses, files written: {}'.format(
    'APPLIED' if apply else 'DRY-RUN', sum(e.get('hits', 0) for e in log), len(miss),
    sum(1 for e in log if e.get('written'))))
