# -*- coding: utf-8 -*-
"""List the tables lacking a caption in 論文_全文_v15.docx, with context, to fill titles.

Output: Paper/表題待補清單.md
"""
import pathlib
import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

SRC = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\論文_全文_v15.docx')
OUT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\表題待補清單.md')
CAP = re.compile(r'^\**表\s*\d')

d = Document(str(SRC))
rows = []
section = ''
prev = ''
idx = 0
for child in d.element.body.iterchildren():
    if child.tag == qn('w:p'):
        p = Paragraph(child, d)
        t = p.text.strip()
        if p.style.name == 'Heading 3' and t:
            section = t
        if t:
            prev = t
    elif child.tag == qn('w:tbl'):
        idx += 1
        tb = Table(child, d)
        header = ' | '.join(c.text.strip()[:16] for c in tb.rows[0].cells)
        rows.append({
            'no': idx, 'section': section, 'prev': prev,
            'header': header, 'n_rows': len(tb.rows), 'has_caption': bool(CAP.match(prev)),
        })

lines = ['# 表題待補清單（Sustainability 中文版）', '',
         '> 來源：`Paper/論文_全文_v15.docx` 之 31 個表格；下表列出**缺表題**者及其所屬節次、',
         '> 前一語句與首列表頭，供填寫表號與表題後重跑 `build_sustainability_zh.py`。', '']
missing = [r for r in rows if not r['has_caption']]
lines.append('共 {} 表；其中 **{} 表已有表題**、**{} 表待補**。'.format(len(rows), len(rows) - len(missing), len(missing)))
lines.append('')
lines.append('| # | 所屬節次 | 前一語句（節錄） | 首列表頭 | 列數 |')
lines.append('|---:|---|---|---|---:|')
for r in missing:
    lines.append('| {} | {} | {} | {} | {} |'.format(
        r['no'], r['section'][:26], r['prev'][:60].replace('|', '／'), r['header'][:50].replace('|', '／'), r['n_rows']))
OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('wrote', OUT.name, '| tables', len(rows), '| missing', len(missing))
