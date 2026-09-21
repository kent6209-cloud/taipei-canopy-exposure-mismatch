# -*- coding: utf-8 -*-
"""Repair DOCX files whose image references still point at renamed media.

The JPEG compaction renames `word/media/imageN.png` -> `imageN.jpeg`; any part that
references the old name (document/header/footer `.rels`, [Content_Types].xml) must be
updated.  This script scans every `.rels` part of each DOCX, rewrites references that
point at a missing media file but whose `.jpeg` twin exists, and ensures the JPEG
content-type default is declared.

Usage: python wp3_og_docx_fix_rels.py [folder]
"""
import re
import sys
import zipfile
from pathlib import Path

REF = re.compile(r'(media/[A-Za-z0-9_\-\.]+)\.(png|jpg|bmp|tif|tiff|gif|emf|wmf)')


def repair(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        media = {n for n in names if n.startswith('word/media/')}
        parts = {}
        for n in names:
            if n.endswith('.rels') or n == '[Content_Types].xml':
                parts[n] = z.read(n).decode('utf-8', 'replace')
        others = [(n, z.read(n)) for n in names if n not in parts]

    changed = 0
    for n, txt in list(parts.items()):
        new = txt

        def sub(m):
            base, ext = m.group(1), m.group(2)
            if ('word/' + base) in media:
                return m.group(0)
            alt = 'word/' + base + '.jpeg'
            return base + '.jpeg' if alt in media else m.group(0)

        new = REF.sub(sub, new)
        if n == '[Content_Types].xml' and 'Extension="jpeg"' not in new:
            new = new.replace('<Default Extension="png"',
                              '<Default Extension="jpeg" ContentType="image/jpeg"/>'
                              '<Default Extension="png"', 1)
        if new != txt:
            parts[n] = new
            changed += 1

    if not changed:
        return 'ok (no change)'
    tmp = path.with_suffix('.fix.docx')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in others:
            zout.writestr(n, data)
        for n, txt in parts.items():
            zout.writestr(n, txt.encode('utf-8'))
    tmp.replace(path)
    return 'repaired {} part(s)'.format(changed)


if __name__ == '__main__':
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r'E:\GeoAI\20260909_taiwan_chmv2\Paper\opengreen')
    for f in sorted(folder.glob('*.docx')):
        print('{:<44} {}'.format(f.name[:44], repair(f)))
