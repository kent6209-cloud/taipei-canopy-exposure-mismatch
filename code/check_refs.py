# -*- coding: utf-8 -*-
"""Cross-reference audit for the v16 journal files.

For each file: caption numbers defined (MDPI caption styles) vs numbers cited in body text.
Reports: cited-but-undefined, defined-but-never-cited, duplicate captions, and remaining
placeholder markers (【待補】/【需查證】/WP1-WP5/TODO/XXX).
"""
import pathlib
import re

from docx import Document

NEW = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\new')
SUFFIX = 'v17' if '--v16' not in __import__('sys').argv else 'v16'
FILES = ['論文_全文_{}_Sustainability中文版.docx'.format(SUFFIX),
         '論文_全文_{}_Sustainability中文版_主文.docx'.format(SUFFIX),
         '論文_全文_{}_Sustainability中文版_附錄（補充材料）.docx'.format(SUFFIX)]

FIG = re.compile(r'(?<![A-Za-z0-9])Figure\s+(S?)(\d+)')
TAB = re.compile(r'(?<![A-Za-z0-9])Table\s+(S?)(\d+)')
CAP_FIG = re.compile(r'^\**Figure\s+(S?)(\d+)')
CAP_TAB = re.compile(r'^\**Table\s+(S?)(\d+)')

for name in FILES:
    d = Document(str(NEW / name))
    body = []
    cap_fig, cap_tab = {}, {}
    for q in d.paragraphs:
        sn = q.style.name
        txt = q.text.strip()
        if not txt:
            continue
        if sn == 'MDPI_5.1_figure_caption':
            m = CAP_FIG.match(txt)
            if m:
                key = m.group(1) + m.group(2)
                cap_fig.setdefault(key, []).append(txt[:60])
            continue
        if sn == 'MDPI_4.1_table_caption':
            m = CAP_TAB.match(txt)
            if m:
                key = m.group(1) + m.group(2)
                cap_tab.setdefault(key, []).append(txt[:60])
            continue
        body.append(txt)
    text = '\n'.join(body)
    cite_fig = {m.group(1) + m.group(2) for m in FIG.finditer(text)}
    cite_tab = {m.group(1) + m.group(2) for m in TAB.finditer(text)}

    print('=' * 78)
    print(name)
    print('  captions: Figure {}  Table {}'.format(len(cap_fig), len(cap_tab)))
    print('  cited   : Figure {}  Table {}'.format(len(cite_fig), len(cite_tab)))
    print('  cited but no caption : Figure {}  Table {}'.format(
        sorted(cite_fig - set(cap_fig)), sorted(cite_tab - set(cap_tab))))
    print('  caption but never cited: Figure {}  Table {}'.format(
        sorted(set(cap_fig) - cite_fig), sorted(set(cap_tab) - cite_tab)))
    dup = {k: v for k, v in list(cap_fig.items()) + list(cap_tab.items()) if len(v) > 1}
    print('  duplicate captions   : {}'.format(list(dup) or 'none'))
    ph = {k: text.count(k) for k in ('【待補】', '【需查證】', 'WP1', 'WP2', 'WP3', 'WP4', 'WP5', 'TODO', 'XXX')}
    print('  placeholders         : {}'.format({k: v for k, v in ph.items() if v} or 'none'))
