# -*- coding: utf-8 -*-
"""Compute the citation order of first appearance and renumber references to MDPI order.

MDPI requires references numbered in order of appearance.  This script:
  1. scans the assembled manuscript (body only, reference list excluded),
  2. builds old -> new numbering,
  3. rewrites [..] tokens in the chapter drafts,
  4. reorders/renumbers the reference list in build_thesis.py.
Run with --dry-run to only print the mapping.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2')
PAPER = ROOT / 'Paper'
MD = PAPER / '論文_全文_v1.md'
BT = ROOT / 'build_thesis.py'
TOKEN = re.compile(r'\[(\d+(?:\s*[,\u2013-]\s*\d+)*)\]')


def expand(tok):
    out = []
    for part in re.split(r'[,\u2013-]', tok):
        part = part.strip()
        if part:
            out.append(int(part))
    return out


def collapse(nums):
    nums = sorted(set(nums))
    runs, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        runs.append((nums[i], nums[j]))
        i = j + 1
    parts = [str(a) if a == b else '{}\u2013{}'.format(a, b) for a, b in runs]
    return '[' + ','.join(parts) + ']'


def main():
    dry = '--dry-run' in sys.argv
    text = MD.read_text(encoding='utf-8')
    body = text[:text.index('## 參考文獻')]
    order = []
    for m in TOKEN.finditer(body):
        for n in expand(m.group(1)):
            if n not in order:
                order.append(n)
    mapping = {old: i + 1 for i, old in enumerate(order)}
    print('first-appearance order (old):', order)
    print('mapping old -> new:', {k: mapping[k] for k in sorted(mapping)})
    block_refs = BT.read_text(encoding='utf-8')
    block_refs = block_refs[block_refs.index('    refs = """## 參考文獻'):
                          block_refs.index('## 附錄')]
    items_all = re.findall(r'^(\d+)\.\s', block_refs, flags=re.M)
    unmapped = sorted(set(int(i) for i in items_all) - set(mapping))
    print('never cited:', unmapped)
    if dry:
        return 0

    # --- rewrite citation tokens in the chapter drafts -----------------------
    def sub_token(m):
        nums = expand(m.group(1))
        if any(n not in mapping for n in nums):
            return m.group(0)
        return collapse(mapping[n] for n in nums)

    for f in sorted(PAPER.glob('第*_*正式草稿.md')):
        t = f.read_text(encoding='utf-8')
        lines = t.splitlines(keepends=True)
        inside, changed = False, 0
        for i, ln in enumerate(lines):
            if ln.startswith('## 4'):
                inside = True
            elif ln.startswith('## 5'):
                inside = False
            if inside and '[' in ln:
                new_ln = TOKEN.sub(sub_token, ln)
                if new_ln != ln:
                    lines[i] = new_ln
                    changed += 1
        if changed:
            f.write_text(''.join(lines), encoding='utf-8')
        print('{:<40} lines rewritten: {}'.format(f.name, changed))

    # --- reorder the reference list -----------------------------------------
    t = BT.read_text(encoding='utf-8')
    a = t.index('    refs = """## 參考文獻')
    b = t.index('## 附錄')
    head, tail = t[:a], t[b:]
    block = t[a:b]
    items = re.findall(r'^\d+\.\s.*$', block, flags=re.M)
    assert len(items) >= 27, 'expected >=27 references, found {}'.format(len(items))
    bodies = [re.sub(r'^\d+\.\s*', '', s) for s in items]
    new_items = []
    for old, new in sorted(mapping.items(), key=lambda kv: kv[1]):
        new_items.append('{}. {}'.format(new, bodies[old - 1]))
    for n in unmapped:
        new_items.append('{}. {}'.format(mapping.get(n, n), bodies[n - 1]))
    block_new = '    refs = """## 參考文獻\n\n' + '\n'.join(new_items) + '\n\n---\n\n'
    BT.write_text(head + block_new + tail, encoding='utf-8')
    print('reference list reordered ({} items)'.format(len(new_items)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
