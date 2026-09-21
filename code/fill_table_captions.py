# -*- coding: utf-8 -*-
"""Fill the 23 missing table captions (author-supplied mapping) in the paper sources.

Each target is located by (file, section-heading substring, first-header-row substring);
the caption line is inserted immediately before the matching markdown table.  Two
captions added earlier (表 4-1 / 表 4-2, hyphen style) are renumbered into the new
dot-style sequence, and the three author-numbered tables in §4.8/§4.7 shift by +1 so the
document order stays ascending (4.5 inference → 4.6 CHM → 4.7 resolution → 4.8 reproducibility).

Dry run unless --apply.
"""
import json
import pathlib
import re
import sys

PAPER = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper')
BT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\build_thesis.py')
LOG = pathlib.Path(r'C:\Users\kent6\AppData\Local\Temp\opencode\fill_captions_log.json')

SEP = re.compile(r'^\|[\s:\-|]+\|\s*$')

TARGETS = [
    ('第一章_緒論_正式草稿.md', '1.3', '名詞', '**表 1.2　核心概念與關鍵名詞操作性界定表**'),
    ('第三章_理論框架_正式草稿.md', '3.1', '概念來源', '**表 3.1　NMGCI 分析框架之理論來源與概念構件對照表**'),
    ('第三章_理論框架_正式草稿.md', '3.2', '構件', '**表 3.2　NMGCI 四構件之空間對象、量測指標與治理問題**'),
    ('第三章_理論框架_正式草稿.md', '3.3', '帳本', '**表 3.3　四層帳本（Layer 1–4）之範疇、抵換屬性與資料狀態表**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.1', '階段', '**表 4.1　模組化研究流程（Stage 1–8）之主要工作與產出對照表**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.2', '尺度', '**表 4.2　分析尺度、空間圖資用途與座標系統設定表**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.2', '觀測年份', '**表 4.3　跨年整合空間基線資料集之觀測年份與整合規則**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.2', '分析組件', '**表 4.4　分析方法選擇、替代方案與核心學術理由對照表**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.8', '均勻高度誤差', '**表 4.6　CHMv2 均勻高度誤差對 ΣH 結構代理量之相對敏感性**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.8', '解析度', '**表 4.7　不同重採樣解析度對樹冠面積與 ΣH 之敏感度分析**'),
    ('第四章_研究設計與方法_正式草稿.md', '4.7', '產出', '**表 4.8　核心分析程式、輸出檔與可重現稽核表**'),
    ('第五章_研究結果_正式草稿.md', '5.4', '指標', '**表 5.6　居住網格至最近綠源之路網距離與歐氏距離比較表**'),
    ('第五章_研究結果_正式草稿.md', '5.6', '驗證', '**表 5.8　敏感度與穩健性驗證套件（Validation Suite）總覽表**'),
    ('build_thesis.py', '附錄 A', '原始解析度', '**表 S1　空間資料來源、原始解析度、座標系與授權彙整表**'),
    ('build_thesis.py', '附錄 B', '輸出', '**表 S2　可重現程式碼清單、輸出檔與功能用途彙整表**'),
    ('build_thesis.py', '附錄 F', '中文圖號', '**表 S3　論文圖版索引、類型與中英文圖說對照表**'),
    ('build_thesis.py', '附錄 G　', '植被偵測比例', '**表 S4　臺北市 12 行政區樹冠結構與全臺 368 鄉鎮市區排名對照表**'),
    ('build_thesis.py', '附錄 G-2', '鄉鎮數', '**表 S5　全臺 22 縣市樹冠結構鄉鎮加總與縣市直算交叉檢核表**'),
    ('build_thesis.py', '附錄 H', '該帶中被劃為山坡地之比例', '**表 S6　官方山坡地劃定範圍與高程帶分佈交叉檢核表**'),
    ('build_thesis.py', '附錄 H', '使用分區', '**表 S7　供需赤字網格（低供給·高需求）之主要土地使用分區組成表**'),
    ('build_thesis.py', '附錄 I', '零值比例', '**表 S8　既有年 NPP 通量產品逐年品質與零值比例稽核表**'),
    ('build_thesis.py', '附錄 J', '樹種數', '**表 S9　行道樹樹種組成與胸徑結構之高程帶分解表**'),
    ('build_thesis.py', '附錄 J', '行政區', '**表 S10　臺北市 12 行政區樹冠結構重算與覆蓋率對照表**'),
]

RENAMES = [
    ('**表 4-1　資料時間涵蓋與整合規則（Temporal coverage and integration rules）**',
     '**表 4.3　跨年整合空間基線資料集之觀測年份與整合規則**'),
    ('**表 4-2　空間有效推論設定與有效樣本數（Spatial inference and effective sample size）**',
     '**表 4.5　空間有效推論設定與有效樣本數**'),
]

apply = '--apply' in sys.argv
log = []


def find_table(lines, section_key, header_key):
    """回傳符合 (節次含 section_key, 表頭含 header_key) 之表首索引（0-based）。"""
    hits = []
    section = ''
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('###'):
            section = s
        if s.startswith('|') and i + 1 < len(lines) and SEP.match(lines[i + 1].strip()):
            if section_key in section and header_key in s:
                hits.append(i)
    return hits


buffers = {}
for fname, section_key, header_key, caption in TARGETS:
    path = PAPER / fname if fname != 'build_thesis.py' else BT
    if fname not in buffers:
        buffers[fname] = {'path': path, 'lines': path.read_text(encoding='utf-8').splitlines()}
    lines = buffers[fname]['lines']
    hits = find_table(lines, section_key, header_key)
    if len(hits) != 1:
        log.append({'file': fname, 'section': section_key, 'header': header_key,
                    'status': 'ambiguous' if hits else 'not-found', 'n': len(hits)})
        continue
    i = hits[0]
    prev = next((lines[j].strip() for j in range(i - 1, -1, -1) if lines[j].strip()), '')
    if prev == caption:
        if lines[i - 1].strip():          # 需在圖說與表格之間補空行
            lines.insert(i, '')
            log.append({'file': fname, 'section': section_key, 'caption': caption,
                        'status': 'ok (spacing fixed)'})
        else:
            log.append({'file': fname, 'section': section_key, 'caption': caption,
                        'status': 'ok (already present)'})
        continue
    lines.insert(i, '')                   # 表格前空行（caption 之後）
    lines.insert(i, caption)
    lines.insert(i, '')                   # caption 前空行
    log.append({'file': fname, 'section': section_key, 'caption': caption, 'status': 'ok'})

# renames of the two earlier captions
for fname, holder in buffers.items():
    t = '\n'.join(holder['lines'])
    for a, b in RENAMES:
        if a in t:
            t = t.replace(a, b)
            log.append({'file': fname, 'renamed': a[:30], 'status': 'ok'})
    holder['lines'] = t.splitlines()

if apply:
    for holder in buffers.values():
        holder['path'].write_text('\n'.join(holder['lines']) + '\n', encoding='utf-8')

LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
ok = sum(1 for e in log if e['status'] == 'ok')
bad = [e for e in log if e['status'] != 'ok']
print('{}: {}/{} applied'.format('APPLIED' if apply else 'DRY-RUN', ok, len(TARGETS)))
for e in bad:
    print('  ', e.get('status'), e.get('file'), e.get('section'), e.get('header'), 'n=', e.get('n'))
