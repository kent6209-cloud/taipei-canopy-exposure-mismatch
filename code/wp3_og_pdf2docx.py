# -*- coding: utf-8 -*-
"""Convert Open Green PDFs to DOCX with pdf2docx (layout-preserving).

Usage:
    python wp3_og_pdf2docx.py                 # all top-level Paper/opengreen/*.pdf
    python wp3_og_pdf2docx.py --include-sub     # also Paper/opengreen/新增資料夾/*.pdf
    python wp3_og_pdf2docx.py --only 112 --include-sub false

Skips a file when the target .docx is newer than the .pdf. Logs to
Paper/opengreen/_pdf2docx_log.txt (UTF-8).
"""
import argparse
import sys
import time
from pathlib import Path

import pymupdf as fitz
from pdf2docx import Converter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp3_og_docx_jpeg import compact

ROOT = Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\opengreen')
SUB = ROOT / '新增資料夾'
LOG = ROOT / '_pdf2docx_log.txt'
MAX_PX, QUALITY = 1400, 78
SINGLE = False


def convert(pdf: Path, force: bool = False) -> str:
    docx = pdf.with_suffix('.docx')
    if not force and docx.exists() and docx.stat().st_mtime > pdf.stat().st_mtime:
        return 'skip (docx newer)'
    with fitz.open(pdf) as d:
        pages = d.page_count
    t0 = time.time()
    cv = Converter(str(pdf))
    kw = {"multi_processing": not SINGLE, "ignore_page_error": True}
    try:
        cv.convert(str(docx), **kw)
    finally:
        cv.close()
    n_img, raw_mb, comp_mb, med_before, med_after = compact(docx, MAX_PX, QUALITY)
    dt = time.time() - t0
    return ('ok {} pages in {:.0f}s -> {:.1f} MB (raw {:.1f} MB; media {:.1f}->{:.1f} MB, {} imgs)'
            .format(pages, dt, comp_mb, pdf.stat().st_size / 1e6, med_before, med_after, n_img))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--include-sub', action='store_true', help='also convert 新增資料夾/*.pdf')
    ap.add_argument('--only', default=None, help='substring filter on file name')
    ap.add_argument('--force', action='store_true', help='re-convert even if the docx exists')
    ap.add_argument('--single', action='store_true', help='disable multiprocessing')
    args = ap.parse_args()
    global SINGLE
    SINGLE = '--single' in sys.argv

    targets = sorted(ROOT.glob('*.pdf'))
    if args.include_sub and SUB.exists():
        targets += sorted(SUB.glob('*.pdf'))
    if args.only:
        targets = [p for p in targets if args.only in p.name]

    print('targets: {}'.format(len(targets)), file=sys.stderr, flush=True)
    with LOG.open('a', encoding='utf-8') as fh:
        fh.write('\n=== run {} ===\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        for i, pdf in enumerate(targets, 1):
            t0 = time.time()
            try:
                msg = convert(pdf, args.force)
            except Exception as e:  # noqa: BLE001
                msg = 'FAILED: {}'.format(str(e)[:200])
            line = '[{}/{}] {:<44} {}'.format(i, len(targets), pdf.name[:44], msg)
            print(line, file=sys.stderr, flush=True)
            fh.write(line + '\n')
            fh.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
