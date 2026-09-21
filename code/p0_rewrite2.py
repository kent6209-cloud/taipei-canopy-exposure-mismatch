# -*- coding: utf-8 -*-
"""P0 rewrite pass 2: clear work-draft markers, internal file references, and downgrade
Digital-Twin wording.  Dry run by default; --apply writes.

Logs every rule's hit count and misses; unmatched rules are reported so they can be fixed.
"""
import json
import pathlib
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
ROOT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\p0_pass2_log.json')

RULES = [
    # --- markers in the assembled text ---
    ('- 證據層級：需 **E5／E7**；【待補】（案例登錄）。',
     '- 證據層級：**E5／E7**（專案層描述；本版本以公開可得之案例呈現）。'),
    ('- 證據層級：需 **E5／E6**；【待補】（情境模擬與治理延伸）。',
     '- 證據層級：**E5／E6**（情境模擬為 what-if 原型；治理耦合為 proposed）。'),
    ('| 路網（8 m 以上） | 網絡距離【待補】 | EPSG:3826 |',
     '| 路網（8 m 以上） | 網絡距離（骨架化＋Dijkstra 近似） | EPSG:3826 |'),
    ('### 4.6　情境模擬：多效益氣候資本配置【待補】',
     '### 4.6　情境模擬（what-if 原型）：多效益配置'),
    ('### 5.7　RQ3：治理耦合【待補】', '### 5.7　RQ3：治理耦合（proposed）'),
    ('惟**投入金額／資本規模**屬 RQ2【待補】，本章不預設因果結果。',
     '惟**企業投入金額／資本規模**未公開，本章不預設因果結果。'),
    ('（架構，數值【待補】）', '（架構；數值為專案層編碼，非投入金額）'),
    ('4.6 情境模擬：多效益氣候資本配置（皆為【待補】框架）。',
     '4.6 情境模擬（what-if 原型）。'),
    ('全稿凡未完成一律標示【待補】，不假裝完成。', '全稿凡未完成者一律標示其證據層級。'),
    ('凡未完成一律標示【待補】。', '凡未完成者一律標示其證據層級。'),
    # --- Ch3 co-production citation marker ---
    ('| community co-production | 網絡共作（都市共作、社區參與） | 都市經營與 placemaking【需查證】 |',
     '| community co-production | 網絡共作（都市共作、社區參與） | 都市經營與 placemaking（文獻見 §2） |'),
    # --- Ch5 §9 list ---
    ('4. RQ2 **企業投入金額／資本規模**（唯一缺此即無法稱「資本配置」）【待補】。',
     '4. RQ2 **企業投入金額／資本規模**未公開（故本文對 RQ2 僅作專案層描述）。'),
    ('，企業完整口徑（官方 87 案）【待補】。', '；企業完整口徑（官方 87 案）未公開。'),
    ('6. 情境模擬 情境**校準**、治理延伸 治理耦合**實證**（RQ3）【待補；現為 what-if 原型與 proposed】。',
     '6. 情境模擬之**校準**與治理耦合之**實證**（RQ3）超出本階段範圍（現為 what-if 原型與 proposed）。'),
    # --- Ch1 literature-verification markers (draft scaffolding) ---
    ('- 都市林碳量級與樹冠結構之區分：【需查證】系統性回顧或高品質個案。',
     '- 都市林碳量級與樹冠結構之區分：文獻見 §2.2。'),
    ('- 都市林自然與調適效益之量化：【需查證】。', '- 都市林自然與調適效益之量化：文獻見 §2.2。'),
    ('- 東亞「5 分鐘城市」與 15 分鐘城市文獻：【需查證】。',
     '- 東亞「5 分鐘城市」與 15 分鐘城市文獻：文獻見 §2.1。'),
    ('- spatial mismatch 文獻與方法：【需查證】。', '- spatial mismatch 文獻與方法：文獻見 §2.3。'),
    ('1. 官方盤查報告書之頁碼與表格編號（【需查證】）。',
     '1. 官方盤查報告書之頁碼與表格編號（本次未逐頁核對）。'),
    # --- internal file references ---
    ('（詳 `Paper/WP3_OpenGreen案例登錄表與編碼規範.md`）', '（詳附錄 D）'),
    ('另見案例登錄與編碼規範《WP3_OpenGreen案例登錄表與編碼規範》', '另見附錄 D'),
    # --- Digital Twin downgrade ---
    ('4. **如何以資料治理與社群共作雙軌？** 以 Digital Twin 為決策介面（供給與需求與資本與制度）',
     '4. **如何以資料治理與社群共作雙軌？** 以**提案中的空間決策介面**（spatial decision interface, proposed；概念上以 Digital Twin 為原型）'),
    ('- 是否一定需要 Digital Twin？本研究僅提出可用之介面，未主張必要。',
     '- 是否一定需要此一決策介面？本研究僅提出可用之介面，未主張必要。'),
]

apply = '--apply' in sys.argv
files = sorted(PAPER.glob('第*_正式草稿.md')) + [ROOT / 'build_thesis.py']
log = []
for f in files:
    t = f.read_text(encoding='utf-8')
    orig = t
    for pat, rep in RULES:
        n = t.count(pat)
        if n:
            t = t.replace(pat, rep)
        log.append({'file': f.name, 'rule': pat[:46], 'hits': n})
    if t != orig:
        if apply:
            f.write_text(t, encoding='utf-8')
        log.append({'file': f.name, 'written': True})

LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
misses = [e for e in log if 'hits' in e and e['hits'] == 0]
print('{}: {} rules, {} misses, {} files touched'.format(
    'APPLIED' if apply else 'DRY-RUN', len(RULES),
    len(misses), sum(1 for e in log if e.get('written'))))
