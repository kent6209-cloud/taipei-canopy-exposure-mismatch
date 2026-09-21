# -*- coding: utf-8 -*-
"""Build the canonical thesis deliverables (md + docx).

Single entry point so the Markdown and the Word file never drift apart:

  1. build_thesis.py assembles the chapter drafts into Paper/論文_全文_v1.md
     (the working file used by every figure/number check)
  2. that file is mirrored to the canonical name
     Paper/碳在山、綠感在巷：臺北市近山—都市介面之綠碳供需空間錯置V1.md
  3. pandoc renders the canonical .docx next to it

Edit the chapter drafts under Paper/*_正式草稿.md (or build_thesis.py for the
front matter, references and appendices), then run:

    python build_paper.py

Do NOT hand-edit the .docx: it is regenerated from the Markdown every time.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "Paper"
WORKING_MD = PAPER / "論文_全文_v1.md"
CANON_STEM = "碳在山、綠感在巷：臺北市近山—都市介面之綠碳供需空間錯置V1"
CANON_MD = PAPER / f"{CANON_STEM}.md"
CANON_DOCX = PAPER / f"{CANON_STEM}.docx"


def main():
    sys.path.insert(0, str(ROOT))
    import build_thesis
    import sync_from_docx

    if CANON_DOCX.exists() and "--force" not in sys.argv:
        base = sync_from_docx.load_baseline()
        current = sync_from_docx.md5(CANON_DOCX)
        if base.get("docx_md5") and base["docx_md5"] != current:
            print(
                "REFUSING to overwrite: the Word file was edited since the last build.\n"
                f"  run  python sync_from_docx.py  to fold the docx edits back into the drafts,\n"
                f"  or   python build_paper.py --force  to discard them.",
                file=sys.stderr,
            )
            return 1

    build_thesis.main()
    shutil.copyfile(WORKING_MD, CANON_MD)
    print("wrote", CANON_MD.name, CANON_MD.stat().st_size, "bytes")

    cmd = ["pandoc", str(CANON_MD), "-o", str(CANON_DOCX), "--resource-path", str(PAPER)]
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    print("wrote", CANON_DOCX.name, CANON_DOCX.stat().st_size, "bytes")

    shutil.copyfile(CANON_DOCX, PAPER / "論文_全文_v15.docx")
    sync_from_docx.save_baseline(sync_from_docx.md5(CANON_DOCX), sync_from_docx.md5(CANON_MD))
    print("baseline recorded (docx is now the editing front-end; see sync_from_docx.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
