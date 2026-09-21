# -*- coding: utf-8 -*-
"""WP3: extract an Open Green case registry from the annual summary reports.

Source: 臺北市都市更新處「Open Green 打開綠生活」專案成果
        (https://uro.gov.taipei/News_Content.aspx?n=FA7FC23C73028362&sms=5FD6DE9E4911B7AA)

Local PDFs are used when present (Paper/opengreen/*.pdf); otherwise the report
is downloaded.  Text is extracted with pypdf and case names recovered in two
ways: (a) table-of-contents entries and (b) headings that immediately precede a
"(一) 基地背景介紹 / 計畫概述" subsection (the actual case blocks).

Outputs: opengreen_cases.csv + wp3_opengreen.json
"""
import base64
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "Paper" / "opengreen"
CACHE = Path(r"C:\Users\kent6\AppData\Local\Temp\opencode\opengreen")
OUT_CSV = ROOT / "opengreen_cases.csv"
OUT_JSON = ROOT / "wp3_opengreen.json"
YEARS = ["108", "109", "110", "111", "112", "113", "114"]

REPORTS = {
    "108": {"E": "19f46c43-004e-49bc-91d2-58cb4ad8f463", "W": "6b9cdd96-db38-43f2-bc82-6a18f7185507"},
    "109": {"E": "30858197-99c8-44b9-9ade-cdfc50c08c33", "W": "43dced2e-ba75-482f-bae7-5d85525dda96"},
    "110": {"E": "69fa6bab-909d-476f-a9bf-143a195184f1", "W": "81cd8c84-52aa-40b6-ab09-4a6ab6dcabca"},
    "111": {"E": "e82343d8-a1c7-4204-911c-0fc1250fe05a", "W": "00cd524d-1ccc-49c6-8ff5-7a5676aed52d"},
    "112": {"E": "6638df28-ccd9-4bfb-a1f1-d98937f2237c", "W": "01cf6ada-7ef3-4fcc-885f-1ae928f9790b"},
    "113": {"E": "81b3b1c3-e0ee-41fa-849f-c27a95d5b111", "W": "0a9d3d1f-f8f7-4ef1-baf4-ba09dd57cbf4"},
    "114": {"E": "2a8a856f-3dac-4f35-a4bc-8606318ab0f4", "W": "82c7f0e3-9ab2-4603-a4a8-53075d75141a"},
}
PATH_PREFIX = "/001/Upload/459/relfile/22631/8995478/"
N_PARAM = {
    ("108", "E"): "MTA45bm0LU9wZW5HcmVlbi3mnbHljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("108", "W"): "MTA45bm0LU9wZW5HcmVlbi3opb%2fljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("109", "E"): "MTA55bm0LU9wZW5HcmVlbi3mnbHljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("109", "W"): "MTA55bm0LU9wZW5HcmVlbi3opb%2fljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("110", "E"): "MTEw5bm0LU9wZW5HcmVlbi3mnbHljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("110", "W"): "MTEw5bm0LU9wZW5HcmVlbi3opb%2fljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("111", "E"): "MTEx5bm0LU9wZW5HcmVlbi3mnbHljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("111", "W"): "MTEx5bm0LU9wZW5HcmVlbi3opb%2fljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("112", "E"): "MTEy5bm0LU9wZW4gR3JlZW4t5p2x5Y2A57i957WQ5aCx5ZGK5pu4LnBkZg%3d%3d",
    ("112", "W"): "MTEy5bm0LU9wZW4gR3JlZW4t6KW%2f5Y2A57i957WQ5aCx5ZGK5pu4LnBkZg%3d%3d",
    ("113", "E"): "MTEz5bm0LU9wZW4gR3JlZW4t5p2x5Y2A57i957WQ5aCx5ZGK5pu4LnBkZg%3d%3d",
    ("113", "W"): "MTEz5bm0LU9wZW4gR3JlZW4t6KW%2f5Y2A57i957WQ5aCx5ZGK5pu4LnBkZg%3d%3d",
    ("114", "E"): "MTE05bm0LU9QRy3mnbHljYDnuL3ntZDloLHlkYrmm7gucGRm",
    ("114", "W"): "MTE05bm0LU9QRy3opb%2fljYDnuL3ntZDloLHlkYrmm7gucGRm",
}

TOC_CASE = re.compile(r"^\s*[一二三四五六七八九十]+、\s*([^.\n]{2,60}?)\s*\.{3,}", re.M)
BODY_HEAD = re.compile(r"^[一二三四五六七八九十]+、\s*(.+?)\s*$", re.M)
BODY_ANCHOR = re.compile(r"^[（(]一[）)]\s*(?:基地背景介紹|計畫概述|計畫理念及行動動機|改造點|改造構想)",
                         re.M)
HEAD_STOP = re.compile(r"^(?:壹|貳|參|肆|伍|陸|柒|捌|玖|壹拾|拾)[、]")
ADDR = re.compile(r"(?:基地地址|基地位置|地址)[:：]\s*([^\n]+)")
DIST = re.compile(r"行政區\s*([^\n]+)")
SKIP = ("計畫緣起", "計畫目標", "計畫理念", "計畫架構", "徵件", "宣傳", "審查", "成果展示",
        "附錄", "經費", "結論", "建議", "前言", "摘要", "目錄", "執行架構", "工作流程",
        "評選委員會", "輔導緣起", "輔導策略", "執行規劃", "製作成果", "協助辦理", "社群經營",
        "主視覺", "工作會議", "關係網絡")


def report_url(year, region):
    path = f"{PATH_PREFIX}{REPORTS[year][region]}.pdf"
    u = base64.b64encode(path.encode()).decode()
    return (f"https://www-ws.gov.taipei/Download.ashx?u={urllib.parse.quote(u, safe='')}"
            f"&n={N_PARAM[(year, region)]}&icon=..pdf")


def local_pdf(year, region):
    if not SOURCE_DIR.exists():
        return None
    want = "東" if region == "E" else "西"
    for f in SOURCE_DIR.glob(f"*{year}*"):
        if f.suffix.lower() == ".pdf" and want in f.name:
            return f
    return None


def get_text(year, region):
    txt = CACHE / f"{year}{region}.txt"
    if txt.exists():
        return txt
    CACHE.mkdir(parents=True, exist_ok=True)
    pdf = local_pdf(year, region)
    if pdf is None:
        pdf = CACHE / f"{year}{region}.pdf"
        if not pdf.exists():
            urllib.request.urlretrieve(report_url(year, region), pdf)
            print("downloaded", pdf.name, flush=True)
    import pymupdf
    doc = pymupdf.open(str(pdf))
    txt.write_text("".join(page.get_text() for page in doc), encoding="utf-8")
    doc.close()
    return txt


def parse(txt_path, year, region):
    text = txt_path.read_text(encoding="utf-8")

    toc = []
    for m in TOC_CASE.finditer(text):
        n = m.group(1).strip()
        if len(n) >= 3 and not n.startswith(("基地背景", "改造工項")) \
                and not any(k in n for k in SKIP):
            toc.append(n)

    heads = [(m.start(), m.group(1).strip()) for m in BODY_HEAD.finditer(text)
             if not HEAD_STOP.match(m.group(0))]
    body = []
    for m in BODY_ANCHOR.finditer(text):
        prev = [h for h in heads if h[0] < m.start()]
        if prev:
            body.append(prev[-1][1])

    def dedup(seq):
        out, seen = [], set()
        for n in seq:
            n = re.sub(r"\s*\.{3,}\s*\d+\s*$", "", n.strip()).strip()
            if len(n) >= 3 and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    return {"year": year, "region": region, "source_pdf": f"{year}{region}",
            "case_names": dedup(body) or dedup(toc),
            "toc_names": dedup(toc), "body_names": dedup(body),
            "addresses": [a.strip() for a in ADDR.findall(text)],
            "districts": [d.strip() for d in DIST.findall(text)]}


def main():
    years = sys.argv[1:] or YEARS
    reports = [parse(get_text(y, r), y, r) for y in years for r in ("E", "W")]

    rows = []
    for rep in reports:
        addrs = rep["addresses"]
        for i, name in enumerate(rep["case_names"]):
            rows.append({
                "year": int(rep["year"]) + 1911, "region": rep["region"],
                "case_name": name, "site_address": addrs[i] if i < len(addrs) else "",
                "district_village": "", "proposing_unit": "", "investment_type": "",
                "layer": "", "main_benefit": "", "maintenance_years": "",
                "public_evidence": rep["source_pdf"], "verifiability": "",
            })

    fields = ["year", "region", "case_name", "site_address", "district_village",
              "proposing_unit", "investment_type", "layer", "main_benefit",
              "maintenance_years", "public_evidence", "verifiability"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)

    payload = {"source": "臺北市都市更新處 Open Green 打開綠生活 專案成果",
               "reports": reports, "n_cases": len(rows),
               "schema_note": "investment_type/layer/main_benefit/maintenance_years/"
                              "verifiability 需人工編碼（見 WP3 登錄表）"}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"reports {len(reports)}  cases {len(rows)}")
    for rep in reports:
        print(f"  {rep['year']}{rep['region']}: body={len(rep['body_names'])} "
              f"toc={len(rep['toc_names'])} used={len(rep['case_names'])} "
              f"addr={len(rep['addresses'])}")
    print("wrote", OUT_CSV.name, OUT_JSON.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
