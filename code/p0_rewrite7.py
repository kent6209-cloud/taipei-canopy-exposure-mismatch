# -*- coding: utf-8 -*-
"""P0-6: restructure Chapter 6 to 6.1–6.5 (merge 6.5 NMGCI significance + 6.6 boundaries
into a single 6.5 on significance, proposed decision interface and theory boundaries).

Dry run unless --apply.
"""
import pathlib
import sys

P = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\第六章_討論_正式草稿.md')
apply = '--apply' in sys.argv

RULES = [
    # 6.5 heading -> merged significance + proposed interface + boundaries
    ('### 6.5　NMGCI 的理論意義',
     '### 6.5　NMGCI 的理論意義、提案中的空間決策介面與理論邊界'),
    # 6.6 heading -> demoted to a sub-block inside 6.5
    ('### 6.6　理論邊界（主動揭露）', '**理論邊界（主動揭露）**'),
    # section-level map line in the chapter's outline
    ('第六章全文：6.1 空間解耦、6.2 量體 vs 暴露、6.3 四層帳本、6.4 方法邊界、6.5 NMGCI 理論意義、6.6 理論邊界。',
     '第六章全文：6.1 空間解耦與總量導向綠化的限制、6.2 量體 vs 暴露（人口加權）、6.3 四層帳本治理框架、6.4 方法邊界與敏感度、6.5 NMGCI 理論意義、提案中的空間決策介面與理論邊界。'),
]
# generic: any explicit outline line mentioning 6.6
GENERIC = [
    ('、6.5 NMGCI 理論意義、6.6 理論邊界', '與 6.5 NMGCI 理論意義、提案中的空間決策介面與理論邊界'),
    ('6.5 NMGCI 理論意義、6.6 理論邊界', '6.5 NMGCI 理論意義、提案中的空間決策介面與理論邊界'),
]

t = P.read_text(encoding='utf-8')
stats = []
for a, b in RULES + GENERIC:
    n = t.count(a)
    stats.append((a[:36], n))
    if n:
        t = t.replace(a, b)
if apply:
    P.write_text(t, encoding='utf-8')
print('{}: {}'.format('APPLIED' if apply else 'DRY-RUN', stats))
