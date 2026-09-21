# -*- coding: utf-8 -*-
"""WP2b：里級戶籍人口（需求側權威資料）解析與校驗。

來源：臺北市政府民政局「臺北市每月各里人口數及戶數」（data_civil/pop_11X.ods）。
每檔 12 張工作表（1-12 月），每表為：標題列、表頭、總計列、12 區小計列與各里列。

輸出：
  data_civil/taipei_village_pop_monthly.csv  逐月逐里（year, month, district, village, ...）
  data_civil/wp2_pop_village.json            校驗結果與摘要統計

校驗：每月的「總計」＝各區小計加總＝各里加總（人口數與戶數各驗一次）。
用途：與 WorldPop 相對密度做雙權重穩健性檢核（戶籍 ≠ 常住／日夜間人口）。
"""
import json
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data_civil"
CSV_OUT = DATA / "taipei_village_pop_monthly.csv"
JSON_OUT = DATA / "wp2_pop_village.json"

NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
TITLE = re.compile(r"(\d{3})年\s*(\d{2})月")
COLUMNS = ["行政區", "里別", "村里數_現有門牌", "村里數_戶籍登記", "鄰數_現有門牌",
           "鄰數_戶籍登記", "戶數", "人口數-合計", "人口數-男", "人口數-女"]


def read_sheets(ods_path):
    """回傳 [(sheet_name, [[cell, ...], ...]), ...]；空白工作表一併保留。"""
    with zipfile.ZipFile(ods_path) as z:
        root = ET.fromstring(z.read("content.xml"))
    sheets = []
    for tbl in root.iter("{%s}table" % NS["table"]):
        rows = []
        for row in tbl.findall("table:table-row", NS):
            cells = []
            for c in row.findall("table:table-cell", NS):
                rep = int(c.get("{%s}number-columns-repeated" % NS["table"], "1"))
                txt = "".join(t.text or "" for t in c.iter("{%s}p" % NS["text"]))
                cells.extend([txt] * min(rep, len(COLUMNS) + 2))
            rows.append(cells)
        sheets.append((tbl.get("{%s}name" % NS["table"]), rows))
    return sheets


def to_int(txt):
    txt = (txt or "").strip().replace(",", "")
    return int(txt) if txt.isdigit() else None


def parse_sheet(rows, year, month):
    """切出總計列、區小計列與里列；以 里別 == 行政區 判定小計、== '總計' 判定總計。"""
    total = None
    districts, villages = {}, []
    for cells in rows:
        if len(cells) < len(COLUMNS):
            continue
        district, village = cells[0].strip(), cells[1].strip()
        if not district or district == COLUMNS[0]:
            continue
        rec = {
            "district": district, "village": village,
            "households": to_int(cells[6]), "pop_total": to_int(cells[7]),
            "pop_m": to_int(cells[8]), "pop_f": to_int(cells[9]),
        }
        if rec["pop_total"] is None:
            continue
        if village == "總計":
            total = rec
        elif village == district:
            districts[district] = rec
        else:
            villages.append(rec)
    return total, districts, villages


def main():
    by_month, checks, problems = {}, [], []
    for ods in sorted(DATA.glob("pop_*.ods")):
        for sheet, rows in read_sheets(ods):
            head = " ".join(rows[0]) if rows else ""
            m = TITLE.search(head) or TITLE.search(" ".join(map(str, rows[:2])))
            if not m:
                if head.strip() and "年" in head:
                    problems.append("%s / %s：無法解析年月（%s）" % (ods.name, sheet, head[:40]))
                continue
            year, month = int(m.group(1)) + 1911, int(m.group(2))
            total, districts, villages = parse_sheet(rows, year, month)
            if total is None:
                continue  # 空白模板月（如 115 年 9-12 月）
            key = (year, month)
            by_month[key] = {"total": total, "districts": districts, "villages": villages}
            d_pop = sum(d["pop_total"] for d in districts.values())
            v_pop = sum(v["pop_total"] for v in villages)
            d_hh = sum(d["households"] or 0 for d in districts.values())
            v_hh = sum(v["households"] or 0 for v in villages)
            checks.append({
                "year": year, "month": month,
                "n_districts": len(districts), "n_villages": len(villages),
                "pop_total": total["pop_total"], "pop_sum_districts": d_pop, "pop_sum_villages": v_pop,
                "households_total": total["households"], "households_sum_districts": d_hh,
                "households_sum_villages": v_hh,
                "pop_ok": d_pop == v_pop == total["pop_total"],
                "households_ok": d_hh == v_hh == total["households"],
            })
        print("parsed", ods.name, len(read_sheets(ods)))

    latest = max(by_month)
    lines = ["year,month,district,village,households,pop_total,pop_m,pop_f"]
    for (year, month) in sorted(by_month):
        for v in sorted(by_month[(year, month)]["villages"], key=lambda r: (r["district"], r["village"])):
            lines.append("{},{},{},{},{},{},{},{}".format(
                year, month, v["district"], v["village"], v["households"],
                v["pop_total"], v["pop_m"], v["pop_f"]))
    CSV_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    bad = [c for c in checks if not (c["pop_ok"] and c["households_ok"])]
    summary = {
        "meta": {
            "source": "臺北市政府民政局 臺北市每月各里人口數及戶數",
            "files": sorted(p.name for p in DATA.glob("pop_*.ods")),
            "months_parsed": len(by_month),
            "year_range": [min(by_month)[0], max(by_month)[0]],
            "latest_month": {"year": latest[0], "month": latest[1]},
            "n_villages_latest": len(by_month[latest]["villages"]),
            "n_districts_latest": len(by_month[latest]["districts"]),
            "note": "戶籍人口；戶籍 ≠ 常住／日夜間活動人口。空白月份（115 年 9-12 月）為未發布之模板。",
        },
        "latest": {
            "pop_total": by_month[latest]["total"]["pop_total"],
            "households": by_month[latest]["total"]["households"],
            "by_district": {k: {"pop_total": v["pop_total"], "households": v["households"],
                                "n_villages": sum(1 for x in by_month[latest]["villages"] if x["district"] == k)}
                            for k, v in sorted(by_month[latest]["districts"].items())},
        },
        "validation": {
            "checks": checks, "n_checked": len(checks), "n_failed": len(bad),
            "rule": "總計 = Σ區小計 = Σ里（人口數與戶數各驗一次）",
        },
        "problems": problems,
    }
    JSON_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", CSV_OUT.name, CSV_OUT.stat().st_size, "bytes;", JSON_OUT.name)
    print("months:", len(by_month), "validation failures:", len(bad), "problems:", len(problems))
    print("latest:", summary["meta"]["latest_month"], summary["latest"]["pop_total"])
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
