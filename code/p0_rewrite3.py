# -*- coding: utf-8 -*-
"""P0 pass 3 (line-level): clear all remaining work-draft markers in the paper sources.

Each edit is addressed by (file, line number, required substring); the line is replaced
only if the requirement matches, and every item is logged with ok/skip status.
Dry run by default; --apply writes.
"""
import json
import pathlib
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
BT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\build_thesis.py')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\p0_pass3_log.json')

EDITS = [
    ('第一章_緒論_正式草稿.md', 132, '【需查證】',
     '- 都市林碳量級與碳帳本之區分：文獻見 §2.2。'),
    ('第一章_緒論_正式草稿.md', 133, '【需查證】',
     '- 都市綠基盤之熱舒適／逕流／健康效益：文獻見 §2.2。'),
    ('第一章_緒論_正式草稿.md', 134, '【需查證】',
     '- 首爾「5 分鐘庭園城市」與 15 分鐘城市文獻：文獻見 §2.1。'),
    ('第一章_緒論_正式草稿.md', 135, '【需查證】',
     '- spatial mismatch 之原始與延伸文獻：文獻見 §2.3。'),
    ('第一章_緒論_正式草稿.md', 151, '【需查證】',
     '1. 官方盤查報告書之頁碼與表格編號（本次未逐頁核對）。'),
    ('第三章_理論框架_正式草稿.md', 35, '【需查證】',
     '| community co-production | 耦合鏈二（社群共作、維護持續） | 社群園圃與 placemaking（文獻見 §2） |'),
    ('第三章_理論框架_正式草稿.md', 98, '【待補】',
     '- 證據層級：**E5／E7**（專案層描述；本版本以公開可得之案例呈現）。'),
    ('第三章_理論框架_正式草稿.md', 110, '【待補】',
     '- 證據層級：**E5／E6**（情境模擬為 what-if 原型；治理耦合為 proposed）。'),
    ('第三章_理論框架_正式草稿.md', 126, '【需查證】',
     '沿用第二章文獻 [1]–[17]；3.1 之社群共作概念沿用既有文獻。'),
    ('第三章_理論框架_正式草稿.md', 140, '【待補】',
     '2. P2／P3／P4 之 案例登錄至治理延伸 實證（P2 已達**專案層描述**：Open Green 70 案／企業 35 案；P3／P4 仍為 proposed）。'),
    ('第五章_研究結果_正式草稿.md', 3, '【待補】',
     '> 依《論文正式寫作步驟及大綱提示詞》Phase 6。僅呈現**已完成且可驗證**之結果。資料整備與指標構建 為完整實證；案例登錄 為**專案層描述**（Open Green 70 案、企業 35 案，投入金額未公開）；情境模擬 為**what-if 原型**（非校準模型）；治理延伸 為 **proposed**。凡未完成者一律標示其證據層級。'),
    ('第五章_研究結果_正式草稿.md', 225, '【待補】',
     '### 5.7　RQ3：治理耦合（proposed）'),
    ('第五章_研究結果_正式草稿.md', 256, '【待補】',
     '4. RQ2 **企業投入金額／資本規模**未公開（故本文對 RQ2 僅作專案層描述）。'),
    ('第五章_研究結果_正式草稿.md', 257, '【待補】',
     '5. **Open Green 108–111 掃描報告人工登打**：3 份區報告（109 西 217 頁、110 東 197 頁、111 東 146 頁）已完成 OCR（tesseract chi_tra）並產出頁次摘要與候選案件清單，但**案件名稱與地址之辨識率不足**（欄位標籤可辨識次數為 0），故案例層級登錄仍待人工校對；另企業完整口徑（官方 87 案）未公開。'),
    ('第六章_討論_正式草稿.md', 53, '【待補】',
     '對應矩陣（投入—效益—帳本—空間）之**專案層**填答已具（Open Green 70 案、企業 35 案）；惟**企業投入金額／資本規模**未公開，本章不預設因果結果。'),
    ('第六章_討論_正式草稿.md', 98, '【待補】',
     '- 表 6.1　投入—效益—帳本—空間矩陣（架構；數值為專案層編碼，非投入金額）。'),
    ('第四章_研究設計與方法_正式草稿.md', 9, '【待補】',
     '第四章全文：4.1 研究架構、4.2 研究區與尺度、4.3 資料整備 碳代理量與行道樹生物量、4.4 指標構建 SAI 與人口加權、4.5 案例登錄 企業／案例、4.6 情境模擬 多效益配置（what-if 原型）。'),
    ('第四章_研究設計與方法_正式草稿.md', 59, '【待補】',
     '| 路網（8 m 以上） | 網絡距離（骨架化＋Dijkstra 近似） | EPSG:3826 |'),
    ('第四章_研究設計與方法_正式草稿.md', 148, '【待補】',
     '### 4.6　情境模擬（what-if 原型）：多效益配置'),
    ('第四章_研究設計與方法_正式草稿.md', 257, '【待補】',
     '> 本章交代了 P1 的操作化與可重現流程，並界定後續架構：案例登錄 為專案層登錄（完整度見 §4.5）、情境模擬 為 what-if 原型（§4.6）、治理延伸 為 proposed 治理架構（尚未驗證）。第五章僅呈現目前已可驗證之結果，未完成者一律標示其證據層級。'),
]

BT_EDITS = [
    (369, '【待補】', '> **限制**：使用分區為 115 年版主要計畫圖；部分格（2,248 格，占赤字 13.2 %）在該圖層中未標註分區（多屬非都市計畫或圖層未覆蓋範圍），故上述比例為**在已標註分區範圍內**之分布，且不作因果推論。Open Green 案例僅有行政區質心座標（3 案有門牌），故**未**進行案例落點×分區之精細對照。'),
    (403, '【待補】', '**判定**：既有 NPP 產品**不足以支持可辯護的時序或空間通量分析**。本階段未納入通量分析；本文續以 **ΣH（冠層結構）** 作為供給側代理，並依鐵則**嚴格區分 stock 與 flux**——本附錄即為「不以不可靠通量資料替代結構指標」之依據。後續若需通量證據，應改採：(i) 地面通量塔或林業署年通量統計；(ii) MODIS/Terra GPP-NPP 官方產品（非降尺度再造）；(iii) 林業碳匯官方盤查之年通量，並先完成感測器一致性校正與 no-data 判定。'),
]

apply = '--apply' in sys.argv
log = []


def do_edit(path: pathlib.Path, label, line_no, need, new_line, lines_holder):
    lines = lines_holder['lines']
    if line_no - 1 >= len(lines):
        log.append({'file': label, 'line': line_no, 'status': 'out-of-range'})
        return
    cur = lines[line_no - 1]
    if need not in cur:
        log.append({'file': label, 'line': line_no, 'status': 'skip', 'current': cur[:70]})
        return
    lines[line_no - 1] = new_line
    log.append({'file': label, 'line': line_no, 'status': 'ok'})


buffers = {}
for name, line_no, need, new_line in EDITS:
    f = PAPER / name
    if name not in buffers:
        buffers[name] = {'lines': f.read_text(encoding='utf-8').splitlines(), 'path': f}
    do_edit(f, name, line_no, need, new_line, buffers[name])

bt_lines = BT.read_text(encoding='utf-8').splitlines()
buf = {'lines': bt_lines}
for line_no, need, new_line in BT_EDITS:
    do_edit(BT, BT.name, line_no, need, new_line, buf)
buffers['build_thesis.py'] = {'lines': bt_lines, 'path': BT}

if apply:
    for name, holder in buffers.items():
        holder['path'].write_text('\n'.join(holder['lines']) + '\n', encoding='utf-8')

LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
ok = sum(1 for e in log if e['status'] == 'ok')
skip = [e for e in log if e['status'] != 'ok']
print('{}: {}/{} edits ok'.format('APPLIED' if apply else 'DRY-RUN', ok, len(log)))
for e in skip:
    print('  skip:', e)
