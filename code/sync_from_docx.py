# -*- coding: utf-8 -*-
"""Reverse sync: the Word deliverable is the editing front-end.

Workflow (decided 2026-09-20):

    user edits  Paper/碳在山…V1.docx  in Word
        -> python sync_from_docx.py            # convert + diff vs the md mirror
        -> the same edits are applied to the chapter drafts (manual step)
        -> python build_paper.py               # regenerate md + docx from the drafts

The comparison is a word-stream diff: the docx is rendered back to Markdown with
pandoc and both sides are normalised for round-trip noise (hard wrapping, smart
quotes, table-rule style, image refs, blockquote markers, emphasis/inline code),
so only real content edits are reported. Read-only unless `--accept` is passed;
`--accept` rewrites the md mirror (image paths relinked by order) but never the
chapter drafts.

    python sync_from_docx.py                 # report only
    python sync_from_docx.py --accept        # overwrite the md mirror (NOT the drafts)
    python sync_from_docx.py --refresh       # re-baseline after an intentional build

Exit code 0 = clean (docx and md agree) or report written; 1 = failure.
"""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "Paper"
CANON_STEM = "碳在山、綠感在巷：臺北市近山—都市介面之綠碳供需空間錯置V1"
CANON_MD = PAPER / f"{CANON_STEM}.md"
CANON_DOCX = PAPER / f"{CANON_STEM}.docx"
WORKING_MD = PAPER / "論文_全文_v1.md"
BASELINE = PAPER / ".docx_baseline.json"
FROM_DOCX = PAPER / "_from_docx_v1.md"
REPORT = PAPER / "_sync_from_docx_report.txt"

QUOTES = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " ",
}
ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>|~$])")
TABLE_RULE = re.compile(r"^\|[\s:\-|]+\|$")
HR = re.compile(r"^[-*_]{3,}$")
BLOCKQUOTE = re.compile(r"^>+\s*")
IMAGE = re.compile(r"^(!\[|<img\b)")
EMPHASIS = re.compile(r"[`*_]")
CONTEXT_WORDS = 14


def norm(text: str) -> str:
    """Collapse pandoc round-trip noise so only real content edits remain.

    Trade-off: pure styling changes (emphasis, inline code, quote markers) count
    as equal, because Word loses that nesting on the way back out. `lint_md`
    flags the one marker case that stays visible in the document.
    """
    out = []
    for line in text.splitlines():
        line = BLOCKQUOTE.sub("", line.strip())
        if HR.match(line):
            continue
        if IMAGE.match(line):
            line = "![img]"
        elif TABLE_RULE.match(line):
            line = "|---|"
        out.append(EMPHASIS.sub("", ESCAPE.sub(r"\1", line)).replace(">", " "))
    s = " ".join(out)
    for src, dst in QUOTES.items():
        s = s.replace(src, dst)
    return re.sub(r"\s+", " ", s).strip()


def lint_md(text: str) -> list:
    """Advisory checks on the md mirror: a `>` line right after a paragraph is
    not a blockquote in CommonMark, so Word shows the marker as literal text."""
    issues, prev_blank = [], True
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith(">") and not prev_blank:
            issues.append((n, line.strip()[:60]))
        prev_blank = not line.strip()
    return issues


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_baseline() -> dict:
    if BASELINE.exists():
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    return {}


def save_baseline(docx_md5: str, md_md5: str) -> None:
    BASELINE.write_text(
        json.dumps(
            {
                "docx_md5": docx_md5,
                "md_md5": md_md5,
                "synced_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def docx_to_markdown(docx: Path, out: Path) -> None:
    cmd = ["pandoc", str(docx), "-t", "gfm", "--wrap=none", "-o", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc failed:\n{proc.stdout}\n{proc.stderr}")


def relink_images(md_text: str, converted_text: str) -> str:
    """Word replaces image paths with media/rIdNN; restore them by order."""
    good = [ln for ln in md_text.splitlines() if IMAGE.match(ln.strip()) and ln.strip().startswith("![")]
    out, i = [], 0
    for line in converted_text.splitlines():
        if IMAGE.match(line.strip()) and good:
            out.append(good[min(i, len(good) - 1)])
            i += 1
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def diff_words(old: str, new: str):
    """Word-stream diff: immune to wrapping and block-grouping differences."""
    a, b = norm(old).split(), norm(new).split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return a, b, [op for op in sm.get_opcodes() if op[0] != "equal"]


def main() -> int:
    ap = argparse.ArgumentParser(description="sync the md mirror from the Word deliverable")
    ap.add_argument("--accept", action="store_true", help="overwrite the md mirror with the docx content")
    ap.add_argument("--refresh", action="store_true", help="re-baseline without diffing (after an intentional build)")
    args = ap.parse_args()

    if not CANON_DOCX.exists():
        print(f"missing {CANON_DOCX}", file=sys.stderr)
        return 1

    docx_md5 = md5(CANON_DOCX)
    md_md5 = md5(CANON_MD) if CANON_MD.exists() else ""

    if args.refresh:
        save_baseline(docx_md5, md_md5)
        print(f"re-baselined at {docx_md5[:12]}")
        return 0

    base = load_baseline()
    if base.get("docx_md5") == docx_md5:
        print(f"clean: {CANON_DOCX.name} unchanged since last build ({docx_md5[:12]}); md mirror in sync")
        return 0

    print(f"docx changed since last build: {base.get('docx_md5', 'n/a')[:12]} -> {docx_md5[:12]}")
    docx_to_markdown(CANON_DOCX, FROM_DOCX)

    md_text = CANON_MD.read_text(encoding="utf-8")
    lint = lint_md(md_text)
    a, b, ops = diff_words(md_text, FROM_DOCX.read_text(encoding="utf-8"))

    lines = ["# docx -> md sync report", f"generated: {datetime.now().isoformat(timespec='seconds')}", ""]
    lines.append(f"md lint: {len(lint)} blockquote line(s) not preceded by a blank line (renders a literal '>' in Word)")
    for n, txt in lint:
        lines.append(f"  - line {n}: {txt}")
    lines.append("")
    lines.append(f"content diff: {len(ops)} changed region(s); md {len(a)} words vs docx {len(b)} words")
    lines.append("")

    for k, (tag, i1, i2, j1, j2) in enumerate(ops, 1):
        before = " ".join(a[max(0, i1 - CONTEXT_WORDS):i1])
        after = " ".join(a[i2:i2 + CONTEXT_WORDS])
        lines.append(f"## change {k}  [{tag}]  at md word {i1}")
        lines.append(f"context : …{before}  ⟦ ⟧  {after}…")
        if tag in ("delete", "replace"):
            lines.append("- removed: " + " ".join(a[i1:i2]))
        if tag in ("insert", "replace"):
            lines.append("+ added  : " + " ".join(b[j1:j2]))
        lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"report: {REPORT.name}  ({len(ops)} changed region(s))")
    if lint:
        print(f"md lint: {len(lint)} blockquote line(s) render as literal '>' in Word - see report")

    if not ops:
        save_baseline(docx_md5, md_md5)
        print("clean after conversion: docx content equals the md mirror (round-trip noise only)")
        return 0

    if args.accept:
        merged = relink_images(md_text, FROM_DOCX.read_text(encoding="utf-8"))
        CANON_MD.write_text(merged, encoding="utf-8")
        WORKING_MD.write_text(merged, encoding="utf-8")
        save_baseline(docx_md5, md5(CANON_MD))
        print("accepted: md mirror updated from docx (image paths relinked by order);")
        print("now apply the same edits to the chapter drafts, then run build_paper.py")
    else:
        print("dry run: review the report, then re-run with --accept (chapter drafts still need the same edits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
