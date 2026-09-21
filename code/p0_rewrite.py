# -*- coding: utf-8 -*-
"""P0 rewrite pass 1: work-package labels (WP1–WP5) -> descriptive terms.

Dry run by default; pass --apply to write.  A before/after log is written for review.
"""
import json
import pathlib
import re
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
ROOT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\p0_rewrite_log.json')

# ordered: compound labels first
RULES = [
    (r'WP1／WP2', '資料整備與指標構建'),
    (r'WP2／WP3', '指標構建與案例登錄'),
    (r'WP3–WP5', '案例登錄至治理延伸'),
    (r'WP3～WP5', '案例登錄至治理延伸'),
    (r'WP4／WP5', '情境模擬與治理延伸'),
    (r'WP1–WP5', '整體工作鏈'),
    (r'WP1_\w+\.md', '資料整備章節草稿'),
    (r'WP1\b', '資料整備'),
    (r'WP2\b', '指標構建'),
    (r'WP3\b', '案例登錄'),
    (r'WP4\b', '情境模擬'),
    (r'WP5\b', '治理延伸'),
]

files = sorted(PAPER.glob('第*_正式草稿.md'))
apply = '--apply' in sys.argv
log = []
for f in files:
    t = f.read_text(encoding='utf-8')
    orig = t
    for pat, rep in RULES:
        for m in list(re.finditer(pat, t)):
            log.append({'file': f.name, 'pattern': pat, 'before': t[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')})
        t = re.sub(pat, rep, t)
    if t != orig:
        log.append({'file': f.name, 'changed': True})
        if apply:
            f.write_text(t, encoding='utf-8')
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print('{}: {} changes logged over {} files'.format('APPLIED' if apply else 'DRY-RUN', len(log), len(files)))
