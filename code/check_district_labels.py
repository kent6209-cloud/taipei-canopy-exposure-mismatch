# -*- coding: utf-8 -*-
"""Verify that every district-name label in the map figures lies inside its own
district polygon of the authoritative 臺北市區界圖 (G97_A_CADIST_P.shp).

Reads the label anchors recorded by the figure scripts into
wp5_district_label_positions.json and re-tests containment.

Run: python check_district_labels.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_paper_figures_plus as plus

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "wp5_district_label_positions.json"


def main():
    if not LOG.exists():
        print("no label log; run the figure scripts first")
        return 1
    entries = json.loads(LOG.read_text(encoding="utf-8"))
    g = plus.admin_gdf()
    names = set(g["TOWNNAME"])
    rows = defaultdict(list)
    bad = 0
    for e in entries:
        who = plus.point_in_district(g, e["name"], e["x"], e["y"])
        ok = (who == e["name"])
        if not ok:
            bad += 1
        rows[e["figure"]].append((e["name"], ok, who))

    for fig in sorted(rows):
        print(f"\n=== {fig}  ({len(rows[fig])} labels)")
        for name, ok, who in rows[fig]:
            mark = "OK  " if ok else "FAIL"
            extra = "" if ok else f"  -> actually inside: {who}"
            print(f"  {mark} {name}{extra}")

    total = len(entries)
    print(f"\ntotal {total} labels, {bad} outside their own district")
    print("districts covered:", len({e['name'] for e in entries}), "of", len(names))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
