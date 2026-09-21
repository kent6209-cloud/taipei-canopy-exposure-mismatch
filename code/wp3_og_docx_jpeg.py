# -*- coding: utf-8 -*-
"""Compact a DOCX by re-encoding embedded images as JPEG (with rels/content-type updates).

Usage: python wp3_og_docx_jpeg.py <docx> [max_px] [quality] [--dry]
"""
import io
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image

MEDIA = 'word/media/'
JPEG_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.emf', '.wmf', '.gif')


def to_jpeg_bytes(data: bytes, max_px: int, quality: int):
    im = Image.open(io.BytesIO(data))
    im.load()
    if max(im.size) > max_px:
        r = max_px / max(im.size)
        im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA') if im.mode == 'P' else im
        bg.paste(im, mask=im.split()[-1] if im.mode == 'RGBA' else None)
        im = bg
    elif im.mode != 'RGB':
        im = im.convert('RGB')
    buf = io.BytesIO()
    im.save(buf, format='JPEG', quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def compact(path: Path, max_px: int = 1400, quality: int = 78, dry: bool = False):
    src_mb = path.stat().st_size / 1e6
    tmp = path.with_suffix('.tmp.docx')
    renamed = {}
    n_img = before = after = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith(MEDIA) and Path(item.filename).suffix.lower() in JPEG_EXT:
                before += len(data)
                try:
                    new = to_jpeg_bytes(data, max_px, quality)
                    if len(new) < len(data):
                        data = new
                        newname = item.filename.rsplit('.', 1)[0] + '.jpeg'
                        renamed[item.filename] = newname
                        item.filename = newname
                        n_img += 1
                except Exception:  # noqa: BLE001
                    pass
                after += len(data)

            if item.filename == '[Content_Types].xml' and not dry:
                txt = data.decode('utf-8')
                if 'Extension="jpeg"' not in txt:
                    txt = txt.replace('<Default Extension="png"',
                                      '<Default Extension="jpeg" ContentType="image/jpeg"/>'
                                      '<Default Extension="png"', 1)
                    data = txt.encode('utf-8')
            if item.filename.endswith('.rels') and not dry:
                txt = data.decode('utf-8')
                for old, new in renamed.items():
                    txt = txt.replace(old.replace('word/', ''), new.replace('word/', ''))
                data = txt.encode('utf-8')
            zout.writestr(item, data)
    if dry:
        tmp.unlink(missing_ok=True)
        return n_img, src_mb, 0.0, before / 1e6, after / 1e6
    tmp.replace(path)
    return n_img, src_mb, path.stat().st_size / 1e6, before / 1e6, after / 1e6


if __name__ == '__main__':
    p = Path(sys.argv[1])
    max_px = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
    q = int(sys.argv[3]) if len(sys.argv) > 3 else 78
    dry = '--dry' in sys.argv
    n, s, e, ib, ia = compact(p, max_px, q, dry)
    print('{}: imgs={} {:.1f} -> {:.1f} MB (media {:.1f} -> {:.1f} MB){}'.format(
        p.name, n, s, e, ib, ia, ' [dry]' if dry else ''))
