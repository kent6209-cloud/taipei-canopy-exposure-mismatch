# -*- coding: utf-8 -*-
"""P0 pass 5: citation marker + Digital-Twin downgrade wording.  Dry run unless --apply."""
import json
import pathlib
import sys

EDITS = {
    '第一章_緒論_正式草稿.md': [
        ('此一判斷與既有都市林碳量級研究的方向一致【需查證具體文獻】。',
         '此一判斷與既有都市林碳量級研究的方向一致（Nowak & Crane 2002；Nowak et al. 2013；見 §2.2）。'),
        ('- **RQ3（治理機制耦合；proposed）**：如何透過數位孿生（Digital Twin）決策介面與社群共作機制之**雙軌耦合**',
         '- **RQ3（治理機制耦合；proposed）**：如何透過**提案中的空間決策介面**（spatial decision interface；概念原型為數位孿生）與社群共作機制之**雙軌耦合**'),
        ('| Digital Twin | 供給、需求、資本與制度資訊整合於同一空間決策介面之資料基礎設施 |',
         '| 空間決策介面（spatial decision interface, proposed） | 供給、需求、資本與制度資訊整合於同一介面之**提案**性資料基礎設施（概念原型為數位孿生）；本研究未進行系統開發與驗證 |'),
    ],
    '第五章_研究結果_正式草稿.md': [
        ('> 待 情境模擬與治理延伸 完成後，分析 Digital Twin 是否提供決策介面、企業是否能看到需求熱點、社群是否參與需求辨識與維護、制度是否允許不同效益進入不同帳本。',
         '> 此屬後續研究：分析**提案中的空間決策介面**是否有助於辨識需求熱點、企業是否據以調整投入、社群是否參與需求辨識與維護、制度是否允許不同效益進入不同帳本。'),
    ],
    '第六章_討論_正式草稿.md': [
        ('4. **如何把資料治理與社群共作接起來？** 以 Digital Twin 為決策介面（供給／需求／資本同框）、以社群共作為維護與需求辨識機制（Coupling）。',
         '4. **如何把資料治理與社群共作接起來？** 以**提案中的空間決策介面**（供給／需求／資本同框；概念原型為數位孿生）搭配社群共作（維護與需求辨識），構成 Coupling 的構件。'),
    ],
    '第七章_結論與摘要_正式草稿.md': [
        ('**RQ3（治理延伸：機制設計）**：本研究提出以 Digital Twin（**決策介面**）與社群共作（**需求辨識與維護**）構成之耦合設計',
         '**RQ3（治理延伸：機制設計）**：本研究提出以**提案中的空間決策介面**（概念原型為數位孿生）與社群共作（**需求辨識與維護**）構成之耦合設計'),
        ('- **Digital Twin**：定位為資料整合與情境比較的決策介面，而非單純三維展示。',
         '- **空間決策介面（proposed）**：定位為資料整合與情境比較之介面，非單純三維展示；本研究未進行系統開發與成效驗證。'),
        ('**關鍵詞**：近山—都市介面、綠意可達性、空間錯置、企業氣候資本、四層帳本、數位孿生、空間治理',
         '**關鍵詞**：近山—都市介面、綠意可達性、空間錯置、企業氣候資本、四層帳本、空間決策介面（proposed）、空間治理'),
    ],
}

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\p0_pass5_log.json')
apply = '--apply' in sys.argv
log = []
for name, pairs in EDITS.items():
    f = PAPER / name
    t = f.read_text(encoding='utf-8')
    orig = t
    for a, b in pairs:
        n = t.count(a)
        log.append({'file': name, 'rule': a[:40], 'hits': n})
        if n:
            t = t.replace(a, b)
    if t != orig:
        if apply:
            f.write_text(t, encoding='utf-8')
        log.append({'file': name, 'written': True})
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print('{}: {} hits, {} misses'.format('APPLIED' if apply else 'DRY-RUN',
                                      sum(e.get('hits', 0) for e in log),
                                      sum(1 for e in log if e.get('hits') == 0)))
for e in log:
    if e.get('hits') == 0:
        print('  MISS:', e['file'], e['rule'])
