# -*- coding: utf-8 -*-
"""WP3: OCR the three image-only Open Green reports (109W, 110E, 111E) in chunks.

Renders pages [start, end) to PNG (200 dpi) with PyMuPDF and runs Tesseract
(chi_tra, --psm 3).  Appends page-tagged text to the OCR cache so it can be run
in several short calls.

Usage: python wp3_ocr_scanned.py <code> <start> <end>
"""
import subprocess
import sys
import time
from pathlib import Path

import pymupdf

SRC = Path(r"E:\GeoAI\20260909_taiwan_chmv2\Paper\opengreen")
CACHE = Path(r"C:\Users\kent6\AppData\Local\Temp\opencode\opengreen")
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DPI = 200


def find_pdf(code):
    year, region = code[:3], code[3]
    want = "東" if region == "E" else "西"
    for p in SRC.glob(f"*{year}*"):
        if p.suffix.lower() == ".pdf" and want in p.name:
            return p
    raise FileNotFoundError(code)


def main():
    code, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    doc = pymupdf.open(str(find_pdf(code)))
    end = min(end, doc.page_count)
    out = CACHE / f"{code}.ocr.txt"
    t0 = time.time()
    with open(out, "a", encoding="utf-8") as fh:
        for i in range(start, end):
            png = CACHE / f"_{code}_pg.png"
            doc[i].get_pixmap(dpi=DPI).save(str(png))
            r = subprocess.run([TESS, str(png), "stdout", "-l", "chi_tra", "--psm", "3"],
                               capture_output=True, text=True, encoding="utf-8", timeout=120)
            png.unlink(missing_ok=True)
            fh.write(f"\n===PAGE {i+1}===\n{r.stdout}")
    print(f"{code} pages {start}-{end} done in {time.time()-t0:.0f}s "
          f"(total {doc.page_count}) -> {out.name}")
    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
