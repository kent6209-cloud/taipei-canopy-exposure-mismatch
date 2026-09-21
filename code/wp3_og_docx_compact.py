# -*- coding: utf-8 -*-
"""Shrink pdf2docx output by re-encoding the embedded images (PNG) inside the DOCX.

Usage: python wp3_og_docx_compact.py <docx> [max_px]

The DOCX is a ZIP: every `word/media/*` image is re-saved with PIL at a bounded
long edge and PNG-optimised, then the archive is rewritten in place (temporary
file next to it, atomic replace). Non-image parts are copied byte for byte.
"""
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

MEDIA = 'word/media/'


def compact(path: Path, max_px: int = 1200) -> tuple:
    src_mb = path.stat().st_size / 1e6
    tmp = path.with_suffix('.compact.docx')
    n_img, before, after = 0, 0, 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith(MEDIA) and Path(item.filename).suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.tif'):
                before += len(data)
                try:
                    im = Image.open(io.BytesIO(data))
                    im.load()
                    if max(im.size) > max_px:
                        ratio = max_px / max(im.size)
                        im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))), Image.LANCZOS)
                    buf = io.BytesIO()
                    if im.mode not in ('RGB', 'RGBA', 'L', 'P'):
                        im = im.convert('RGB')
                    im.save(buf, format='PNG', optimize=True, compress_level=9)
                    new = buf.getvalue()
                    if len(new) < len(data):
                        data = new
                    after += len(data)
                    n_img += 1
                except Exception:  # noqa: BLE001
                    after += len(data)
            zout.writestr(item, data)
    tmp.replace(path)
    return n_img, src_mb, path.stat().st_size / 1e6, before / 1e6, after / 1e6


if __name__ == '__main__':
    p = Path(sys.argv[1])
    max_px = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    n, s, e, ib, ia = compact(p, max_px)
    print('{}: images={} {:.1f} MB -> {:.1f} MB (media {:.1f} -> {:.1f} MB)'.format(
        p.name, n, s, e, ib, ia))
