# -*- coding: utf-8 -*-
"""Assemble the full thesis from the chapter drafts into one document.

Extracts the formal body (section 4 "本節正式正文") from each chapter file,
adds front matter (title / abstract / keywords / contents), a reference list and
appendices, and writes Paper/論文_全文_v1.md.

Run: python build_thesis.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "Paper"
OUT = P / "論文_全文_v1.md"

CH_FILES = [
    "第一章_緒論_正式草稿.md",
    "第二章_文獻回顧_正式草稿.md",
    "第三章_理論框架_正式草稿.md",
    "第四章_研究設計與方法_正式草稿.md",
    "第五章_研究結果_正式草稿.md",
    "第六章_討論_正式草稿.md",
    "第七章_結論與摘要_正式草稿.md",
]


def body_of(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    i0 = next((i for i, l in enumerate(lines) if l.startswith("## 4")), 0)
    i1 = next((i for i, l in enumerate(lines) if l.startswith("## 5")), len(lines))
    return "\n".join(lines[i0 + 1:i1]).strip()


def abstract_of(text):
    m = re.search(r"# 摘要（全文完成後撰寫）(.*)$", text, re.S)
    if not m:
        return ""
    body = "\n".join(l for l in m.group(1).strip().splitlines()
                     if not l.strip().startswith("**關鍵詞**"))
    return body.strip()


def main():
    ch1 = (P / CH_FILES[0]).read_text(encoding="utf-8")
    ch7 = (P / CH_FILES[6]).read_text(encoding="utf-8")

    fm = f"""# 碳在山、綠感在巷：臺北市近山—都市介面之冠層結構與日常綠意供給空間錯置

**Carbon on the Hills, Green in the Alleys: Spatial Mismatch between Canopy-Carbon Proxies and Everyday Green Exposure across the Near-Mountain–Urban Interface in Taipei**

博士學位論文（草稿；路徑 B 縮題版）

> 副題：企業綠色資本與資料—制度耦合之治理延伸（治理應用，非核心實證）

---

## 摘要

{abstract_of(ch7)}

**關鍵詞**：近山—都市介面、冠層結構碳代理、綠意供給暴露、空間錯置、人口加權暴露、空間有效推論、四層帳本、治理延伸

---

## Abstract

Urban greening policies are frequently justified by carbon mitigation, yet the
spatial distribution of carbon and of residents' everyday green access need not
coincide. Using Taipei City as the study area, this study proposes the
Near-Mountain Green-Carbon Interface (NMGCI) analytical framework and integrates
the CHMv2 canopy-height model, a 5 m DEM, the Taipei street-tree census (92,626
authoritative records) and population density at 10 m / 100 m analysis grids.
Results show that the zone above 20 m elevation holds 55.9% of the area but
86.7% of canopy and 91.8% of the canopy-carbon proxy (ΣH); in residential grid
cells (n = 23,342) both canopy density and the 500 m green-supply-exposure index
(SAI) fall as population rises (Spearman rho = -0.529 and -0.599). A direct
Source-Demand mismatch layer, M = z(population) - z(ΣH), confirms strong spatial
clustering (Global Moran's I = 0.888, p = 0.001), and the bivariate Moran's I
between ΣH and population is -0.433 (p = 0.001). Because of spatial
autocorrelation these are re-tested with spatial block permutation (p = 0.001,
CIs excluding zero, stable for 250-1000 m blocks). The population-weighted SAI
(29.49) lies well below the area-weighted SAI (43.06). Network-distance audit
shows that the proportion of residential cells within 500 m of green space is
significantly higher when measured by Euclidean distance than by network
distance (97.5% vs. 62.5%), indicating that proximity differs from neighbourhood
green-supply density. As a governance extension (project-level, not full capital
accounting), 61.5% (32/52) of the geocoded Open Green cases fall in the
low-supply/high-demand quadrant, whereas all 35 corporate nature/carbon projects
matched on the Forestry Agency platform lie outside Taipei City. The study
proposes a four-ledger accounting frame (emissions / removal /
adaptation-and-nature / social-and-governance) so that urban greening is not
equated with a single carbon-offset figure.

**Keywords**: near-mountain-urban interface, green supply exposure, spatial
mismatch, population-weighted exposure, spatially effective inference,
four-ledger accounting, governance extension

---

## 目錄

- 第一章　緒論
- 第二章　文獻回顧
- 第三章　理論框架：近山綠碳介面治理（NMGCI）
- 第四章　研究設計與方法
- 第五章　研究結果
- 第六章　討論
- 第七章　結論、限制與後續研究
- 參考文獻
- 附錄

---

"""

    parts = [fm]
    for f in CH_FILES:
        parts.append(body_of(P / f))
        parts.append("\n\n---\n\n")
    body = "\n".join(parts)

    refs = """## 參考文獻

1. 臺北市政府環境保護局. 《臺北市第二期溫室氣體減量執行方案 113 年成果報告》；臺北市政府：臺北，臺灣，2025.
2. Nowak, D.J.; Crane, D.E. Carbon Storage and Sequestration by Urban Trees in the USA. *Environmental Pollution* **2002**, *116*, 381–389.
3. Nowak, D.J.; Greenfield, E.J.; Hoehn, R.E.; Lapoint, E. Carbon Storage and Sequestration by Trees in Urban and Community Areas of the United States. *Environmental Pollution* **2013**, *178*, 229–236.
4. Schendl, M.; James, P. Beyond Proximity: Greenspace Accessibility in the x-Minute City. *People and Nature* **2025**, *7*, e70081.
5. Song, X.-P.; Lai, K.Y.; Tan, P.Y.; Tan, H.T.W. Contrasting Inequality in Human Exposure to Greenspace between Cities of Global North and Global South. *Nature Communications* **2022**, *13*, 4453.
6. Song, X.-P.; Tan, P.Y.; Edwards, P.; Richards, D. Global Inequities in Population Exposure to Urban Greenspaces Increased over the Last Two Decades. *Communications Earth & Environment* **2023**, *4*, 435.
7. Zhao, Y.; Song, X.-P.; Chen, B. Greening Dominates Greenspace Exposure Inequality in Chinese Cities. *npj Urban Sustainability* **2025**, *5*, 12.
8. McPherson, E.G.; Xiao, Q.; Aguaron, E. A New Approach to Quantify and Map Carbon Stored, Sequestered and Emissions Avoided by Urban Forests. *Landscape and Urban Planning* **2013**, *120*, 70–84.
9. Winbourne, J.B.; Jones, T.S.; McNellis, R.E.; Garner, J.H.; Smith, I.A.; Hutyra, L.R. Quantification of Urban Forest and Grassland Carbon Fluxes Using Continuous Automated Chambers. *JGR Biogeosciences* **2022**, *127*, e2021JG006568.
10. Congressional Research Service. *U.S. Forest Carbon Data: In Brief* (R46313); CRS: Washington, DC, USA, 2023.
11. Taskforce on Nature-related Financial Disclosures. *Recommendations of the Taskforce on Nature-related Financial Disclosures*; TNFD: London, UK, 2023.
12. Integrity Council for the Voluntary Carbon Market. *Core Carbon Principles, Assessment Framework and Assessment Procedure*; ICVCM: London, UK, 2024.
13. Liu, Q.; Wang, Y.; Zhang, Z. Spatial Gradients of Supply and Demand of Ecosystem Services within Cities. *Ecological Indicators* **2023**, *157*, 111263.
14. Herreros-Cantis, P.; McPhearson, T. Mapping Supply of and Demand for Ecosystem Services to Assess Environmental Justice in New York City. *Ecological Applications* **2021**, *31*, e02390.
15. Zhong, Z.; Li, Y.; Chen, X. Linear and Non-Linear Dynamics of Ecosystem Services Supply, Demand, and Mismatches. *Ecological Indicators* **2024**, *159*, 111614.
16. Supianto, A.A.; Nasar, W.; Aspen, D.M.; Hasan, A.; Karlsen, A.S.T.; Torres, R.D.S. An Urban Digital Twin Framework for Reference and Planning. *IEEE Access* **2024**, *12*, 152444–152465.
17. 臺北市政府. 《臺北市自願檢視報告》（Voluntary Local Review）；臺北市政府：臺北，臺灣，2019–2025.
18. 臺北市政府. 《臺北市淨零排放管理自治條例》；臺北市政府：臺北，臺灣，2025.
19. 內政部國土測繪中心. 《鄉（鎮、市、區）界線（114 年 3 月版）》；內政部：臺北，臺灣，2025.
20. Meta AI; World Resources Institute. *Canopy Height Model v2 (CHMv2)*; Meta AI & WRI: Washington, DC, USA, 2024.
21. 臺北市政府工務局公園路燈工程管理處. 《臺北市行道樹普查資料》；臺北市政府工務局：臺北，臺灣，2024.
22. WorldPop. *Taiwan 100 m Population Density Grid 2026*; WorldPop, University of Southampton: Southampton, UK, 2026.
23. 臺北市政府民政局. 《臺北市每月各里人口數及戶數（113–115 年逐月）》；臺北市政府：臺北，臺灣，2026.
24. Chave, J.; Réjou-Méchain, M.; Búrquez, A.; Chidumayo, E.; Colgan, M.S.; Delitti, W.B.; Duque, A.; Tiemoko, D. Improved Allometric Models to Estimate the Aboveground Biomass of Tropical Trees. *Global Change Biology* **2014**, *20*, 3177–3190.
25. 臺北市政府都市發展局. 《臺北市里界圖（115 年 6 月 23 日版）》；臺北市政府：臺北，臺灣，2026.
26. 臺北市都市更新處. 《Open Green 打開綠生活》年度總結報告（108–114 年）；臺北市都市更新處：臺北，臺灣，2025.
27. 農業部林業及自然保育署. 《自然碳匯與生物多樣性專案媒合平臺》. https://esg.forest.gov.tw（存取於 2026 年 8 月）.

---

## 附錄

### 附錄 A　空間資料來源、格式與授權

**表 S1　空間資料來源、原始解析度、座標系與授權彙整表**

| 資料 | 原始解析度 | 座標 | 授權／來源 |
|---|---|---|---|
| CHMv2 樹冠高度 | Web Mercator 像元 1.19 m（地面 ≈1.08 m） | EPSG:3857 | Meta AI／WRI（開源） |
| 5 m DEM | 5 m | WGS84 | 政府開放／專案 |
| 臺北市行道樹普查 | 點（原始 92,777 筆；權威 92,626） | EPSG:3826 | 臺北市公園路燈工程管理處（開放資料） |
| 100 m 綠地分類 | 100 m | EPSG:3826 | 專案（grn_ratio） |
| WorldPop 人口密度 | 約 90 m | WGS84 | WorldPop（開源） |
| 里級戶籍人口／戶數 | 里（456 里，逐月 113–115 年） | — | 臺北市政府民政局（公開） |
| 村里界 | 向量（456 里） | EPSG:3826 | 臺北市政府都市發展局《臺北市里界圖》（115.06.23） |
| 行政區界 | 向量 | EPSG:3826 | 內政部國土測繪中心（114.03） |
| Open Green 年度報告 | PDF | — | 臺北市都市更新處（公開） |
| VLR 自願檢視報告 | PDF | — | 臺北市政府（公開） |
| 企業自然／碳專案 | 網頁 | — | 農業部林業及自然保育署 ESG 媒合平臺（公開） |

### 附錄 B　可重現程式與執行稽核（Reproducible Code Base）

本附錄列出全部分析程式、輸出檔與功能用途（見表 S2）；程式與衍生結果已典藏於 Zenodo（見「Data Availability Statement」）。

**表 S2　可重現程式碼清單、輸出檔與功能用途彙整表**

| 程式 | 輸出 | 用途 |
|---|---|---|
| `wp1_data_audit.py` | `taipei_trees_authoritative.csv`, `wp1_data_audit.json` | 資料稽核（92,777→92,626） |
| `taipei_elev_carbon_scan.py` | `taipei_elev_carbon_scan.json` | 高程帶 ΣH |
| `wp1_carbon_bands.py` | `wp1_carbon_bands.json` | 行道樹異速生長生物量 |
| `wp1_chm_validation.py` | `wp1_chm_validation.json`, `figA_chm_validation.png` | CHMv2 對行道樹普查之獨立驗證 |
| `wp2_green_accessibility.py` | `wp2_green_accessibility.json` | SAI 與人口加權 |
| `wp2_spatial_stats.py` | `wp2_spatial_stats.json`, `wp2_rasters/` | Moran's I／LISA／四象限 |
| **`wp2_spatial_inference.py`** | `wp2_spatial_inference.json` | **空間區塊 bootstrap／置換** |
| `wp2_sai_sensitivity.py` | `wp2_sai_sensitivity.json` | 半徑×權重敏感度 |
| `wp2b_pop_village.py` | `data_civil/taipei_village_pop_monthly.csv`, `wp2_pop_village.json` | 里級戶籍人口解析與校驗（32 個月、0 失敗） |
| `wp2b_pop_weight_robustness.py` | `wp2b_pop_weight.json`, `fig12_pop_weight.png` | 需求權重來源穩健性（W1–W3） |
| `wp2c_tw_townships.py` | `wp2c_tw_townships.json/.csv`, `figA2_tw_townships.png` | 全臺 368 鄉鎮市區樹冠結構（外部效度對照） |
| `wp2d_land_context.py` | `wp2d_land_context.json/.csv`, `figA3_land_context.png` | 官方山坡地 × 高程帶檢核；使用分區 × 供需象限 |
| `wp3b_carbon_flux.py` | `wp3b_carbon_flux.json/.csv`, `figA4_carbon_flux.png` | 年 NPP 產品之可用性檢核（附錄 I） |
| `wp1b_tree_structure.py` | `wp1b_tree_structure.json/.csv`, `figA5_tree_structure.png` | 行道樹樹種×高程帶分解；區級樹冠結構 |
| `wp1c_resolution_sensitivity.py` | `wp1c_resolution_sensitivity.json` | CHMv2 解析度／重採樣敏感度 |
| `wp2c2_tw_counties.py` | `wp2c_tw_counties.json/.csv`, `figA6_tw_counties.png` | 全臺 22 縣市樹冠結構（縣市層對照與交叉檢核） |
| `wp2_network_access.py` | `wp2_network_access.json` | 路網近似距離 |
| `wp3_opengreen_extract.py`, `wp3_code_*.py`, `wp3_extract_md_tables.py` | `opengreen_*.csv/.json` | Open Green 案例（70 案） |
| `wp3_enterprise_full.py` | `enterprise_climate_projects_full.csv` | 企業專案（35 案） |
| `wp3_case_vs_sai.py` | `wp3_cases_vs_sai.json`, `fig8` | 案例×SAI |
| `wp4_scenario_simulator.py` | `wp4_scenario_simulator.json` | 多效益情境模擬（what-if） |
| `make_fig3_composite.py`, `make_fig4_pop_sai.py`, `make_fig5_mismatch.py`, `make_fig6_opengreen.py`, `make_fig7_scenarios.py`, `make_fig8_nmgci.py`, `make_fig9_vlr.py`, `make_fig1_fig10.py`, `make_final_figures.py` | `Paper/figures/*.png` | 圖 2-1～5-4 |

> 所有面積於 EPSG:3826 計算；CHMv2 面積經逐列 cos²(lat) 校正。輸出 JSON 即時序產物，可依程式重跑複核。

### 附錄 C　空間統計診斷與參數敏感度
- 全域 Moran's I：樹冠 0.817、錯置赤字 0.893、SAI 0.994、雙變量（樹冠×人口）−0.443（皆 p=0.001）。
- LISA（赤字）：H-H 6,274、L-L 7,349、L-H 8、H-L 11；供需四象限赤字區 7,911 格。
- 空間區塊推論：樹冠×人口 ρ=−0.562、SAI×人口 ρ=−0.649（1,116 區塊、999 置換，p=0.001）；有效樣本數 1,925／46。
- 敏感度矩陣（3 半徑 × 5 權重）：見表 5.8（ρ 介於 −0.517～−0.615，`tree_heavy` 反轉）。
- 需求權重來源（WorldPop 相對密度 vs 民政局里級戶籍人口）：見表 5.9（人口加權 SAI 27.71–29.49、面積加權 43.06–46.74；ρ −0.525～−0.707；兩權重來源於里層 ρ=0.61，n=456）。

### 附錄 D　案例編碼協定（Coding Protocols）
- Open Green：70 案（108–114）＋歷史案例檔案 67 筆；欄位 `investment_type／layer／main_benefit／verifiability`；官方累計 87 案。
- 企業專案：林業署媒合平臺 35 案；類別對應 Layer 2（造林＝「2待查」）、Layer 3、Layer 4。
- Layer 分派規則：都市綠化／社區園圃**原則上不列 Layer 2**；須符合方法學、外加性與查證方可計入。
- 限制：3 份掃描報告（109 西、110 東、111 東）與 107 年無法自動取得；編碼多為單人推得，**編碼者間信度尚未建立**。
- **掃描報告 OCR 稽核**（3 份、560 頁；PyMuPDF 200 dpi＋Tesseract `chi_tra`）：OCR 文字以徵件辦法與案例敘事為主，**欄位標籤（基地位置／設計單位／施工單位）可辨識次數為 0**，案例層級登錄仍須人工校對；已產出人工核對用工作檔 `Paper/opengreen/掃描檔_頁次摘要.md` 與 `掃描檔_候選案件（OCR）.md`（候選上界 109W 22／110E 14／111E 14）。

### 附錄 E　不確定性傳播公式與誤差估計
- **CHMv2 → ΣH（線性傳播）**：`ΔΣH/ΣH ≈ Δ × A_c / ΣH`；以 ΣH=127,779 m·ha、A_c=13,805 ha 得 ±1/2/3 m 對應 ±10.8%／±21.6%／±32.4%，實測偏差 −3.69 m 對應 **−39.9%**（僅影響**絕對量級**，不改變相對空間分布）。
- **CHMv2 獨立驗證**（`wp1_chm_validation.py`；臺北市行道樹普查逐棵配對，n=92,625）：中心像元 MAE 5.94 m／RMSE 7.00 m／r 0.40／bias −5.38 m；僅 CHM>0（n=55,753、偵測率 60.2%）MAE 4.62／RMSE 5.65／r 0.35／bias −3.69 m；3×3 窗最大值 RMSE 6.41／bias −4.56 m。校正後 RMSE：全域加性 4.49／行政區加性 4.40／全域線性（`普查樹高 ≈ 0.348 × CHM + 7.95`）3.48 m（附錄圖 A-1）。偏差方向為**低估**，故 ΣH 為保守量級。
- **WorldPop**：採相對權重 `pop_i/Σpop`，均勻倍率誤差自動抵銷；檢定為秩相關，對單調扭曲穩健。另以民政局里級戶籍人口（2026-08，456 里）重做權重（表 5.9、圖 5-5），結論方向與量級不變；惟戶籍人口 ≠ 常住／日夜間活動人口。
- **SAI 權重**：15 組組合之 ρ 全距約 0.10（≈±0.05）；`tree_heavy` 反轉已揭露。
- **解析度／重採樣敏感度**（`wp1c_resolution_sensitivity.py`）：ΣH 於 1.19–100 m 與 NearestNeighbour／Average 下之全距為 **−0.1 %～+1.9 %**；樹冠面積則為 −11 %～+32 %。主分析（10 m・NearestNeighbour）可重現表 5.1（樹冠 13,811 vs 13,805 ha、ΣH 127,840 vs 127,779 m·ha）。
- **需求權重來源**：人口加權 SAI 27.71（W2 里總量×模型配置）／29.20（W3 里總量×里內均勻）vs 29.49（W1 WorldPop）；面積—人口落差 13.6～17.5 分，方向一致。
- **投影面積**：cos²(lat) 校正消除 ≈1.22× 膨脹；殘餘（網格化／海岸 no-data）為 −0.19%。

![](figures/figA_chm_validation.png)

**附錄圖 A-1　CHMv2 樹冠高度對行道樹普查之驗證（逐棵配對，n = 92,625）**

*Appendix Figure A-1. CHMv2 canopy height validated against the Taipei street-tree census (per-tree pairing, n = 92,625). Left: CHMv2 versus census tree height with the 1:1 line and the closed-form linear calibration; right: mean bias (CHM − census) by district.*

### 附錄 F　圖版索引（實證 vs 概念／模型標註）

> 圖版已置於各章對應段落並附中英圖說（圖 2-1 於 §2.6、圖 3-1 於 §3.2、圖 4-1 於 §4.1、圖 4-2 於 §4.2、圖 4-3 於 §4.6、圖 5-1 於 §5.1、圖 5-2 於 §5.2、圖 5-3 於 §5.3、圖 5-4 於 §5.5、圖 5-5 於 §5.6）。下表（表 S3）同時列出各圖版於投稿版之編號：主文為 Figure 1–10（連續），補充材料為 Figure S1–S6（連續），並對應補充材料區段 S5、S7–S11。


**表 S3　論文圖版索引、類型與中英文圖說對照表**

| 圖號 | 位置 | 類型 | 英文圖說（投稿版） |
|---|---|---|---|
| 圖 2-1 | §2.6 | 政策文本描述 | Trend of green-governance keywords in the Taipei Voluntary Local Reviews (2019–2025). |
| 圖 3-1 | §3.2 | 理論模型（非流程圖） | The Near-Mountain Green-Carbon Interface (NMGCI) analytical framework. |
| 圖 4-1 | §4.1 | 概念（實線＝已實證） | Research design and RQ–WP argumentation structure. |
| 圖 4-2 | §4.2 | 實證底圖 | Study area, near-mountain–urban interface and elevation zoning in Taipei City. |
| 圖 4-3 | §4.6 | 模型 what-if（非成效） | What-if simulation of equal canopy-increment capital allocation under three spatial rules. |
| 圖 5-1 | §5.1 | 實證 | Supply-side spatial structure: elevation-band shares, ΣH and SAI. |
| 圖 5-2 | §5.2 | 實證 | Mean SAI and canopy structure (ΣH) across population-density deciles (n = 23,342). |
| 圖 5-3 | §5.3 | 實證 | Spatial mismatch deficit and LISA clusters. |
| 圖 5-4 | §5.5 | 實證（專案層描述） | Open Green cases overlaid on the SAI supply–demand quadrants. |
| 圖 5-5 | §5.6 | 穩健性檢核 | Robustness of the demand-side weighting: WorldPop density versus official village population (n = 456 villages). |
| 附錄圖 A-1 | 附錄 E（Supplementary S5） | 驗證 | CHMv2 canopy height validated against the Taipei street-tree census (per-tree pairing, n = 92,625). |
| 附錄圖 A-2 | 附錄 G（Supplementary S7） | 外部效度 | Vegetation-detection share of all 368 Taiwanese townships, with the 12 Taipei districts highlighted. |
| 附錄圖 A-6 | 附錄 G-2（Supplementary S8） | 外部效度 | Vegetation-detection share of the 22 counties/cities, with a township-vs-county consistency check. |
| 附錄圖 A-3 | 附錄 H（Supplementary S9） | 制度／土地 | Official slope-land share by elevation band, and land-use zoning composition of the supply–demand deficit cells. |
| 附錄圖 A-4 | 附錄 I（Supplementary S10） | 資料品質 | Usability audit of the annual NPP product (zero-inflation and sensor-era discontinuity). |
| 附錄圖 A-5 | 附錄 J（Supplementary S11） | 結構分解 | Street-tree species and DBH by elevation band, and district-level canopy cover recomputed from CHMv2. |

### 附錄 G　全臺鄉鎮市區樹冠結構對照（外部效度檢核）

**方法**：以 CHMv2 原生解析度（1.19 m、EPSG:3857）逐鄉鎮裁切檔，僅取**落在該鄉鎮多邊形內**且非 nodata 之像元，累積高度直方圖後依鄉鎮代碼合併（部分鄉鎮分散於多個分幅檔），計算植被偵測比例（CHM > 0）、樹冠比例（CHM ≥ 2 m）、樹冠像元之平均與 P90 高度；面積以 cos²(lat) 校正。輸出：`wp2c_tw_townships.json`、`wp2c_tw_townships.csv`（368 鄉鎮市區）。

**全臺分布（n = 368）**：植被偵測比例最低 1.8 %、P25 12.1 %、**中位數 34.3 %**、P75 68.1 %、最高 97.2 %（平均 40.1 %）；樹冠像元平均高度之中位數 6.70 m。

**臺北市 12 區之位置**（見表 S4）：


**表 S4　臺北市 12 行政區樹冠結構與全臺 368 鄉鎮市區排名對照表**

| 區 | 植被偵測比例 | 樹冠像元平均高 (m) | 全臺排名／368 | 百分位 |
|---|---:|---:|---:|---:|
| 松山區 | 10.1 % | 5.83 | 75 | 20.4 |
| 大同區 | 10.7 % | 5.75 | 82 | 22.3 |
| 萬華區 | 12.9 % | 5.49 | 100 | 27.2 |
| 中正區 | 20.0 % | 6.68 | 138 | 37.5 |
| 中山區 | 24.6 % | 7.14 | 156 | 42.4 |
| 大安區 | 27.5 % | 8.14 | 162 | 44.0 |
| 信義區 | 43.8 % | 10.01 | 213 | 57.9 |
| 北投區 | 56.5 % | 9.47 | 247 | 67.1 |
| 內湖區 | 58.0 % | 9.04 | 252 | 68.5 |
| 文山區 | 59.3 % | 8.97 | 255 | 69.3 |
| 南港區 | 61.8 % | 9.14 | 262 | 71.2 |
| 士林區 | 64.0 % | 9.84 | 266 | 72.3 |

**三點觀察**：

1. **核心區位於全國後段**：松山、大同、萬華三區之植被偵測比例僅 10–13 %，落在全臺 368 鄉鎮市區的**第 20–27 百分位**；即「高度都市化、綠意偏低」並非臺北獨有，但臺北核心區位於該分布的低端。
2. **近山區接近全國中位數**：士林至北投等含大面積山地之區為 56–64 %（第 67–72 百分位），僅略高於全臺中位數——**行政區本身即為異質單元**。
3. **市內落差 > 市際落差**：臺北市 12 區之植被偵測比例相差 **6.4 倍**（10.1 %–64.0 %），大於六都彼此之區中位數差異（臺北市 35.7 %、臺中市 15.8 %、臺南市 14.4 %、高雄市 19.9 %、桃園市 21.2 %、新北市 66.6 %）。此與 §6.4 之 MAUP 邊界條件一致：**以行政區或全市平均呈現綠意，會系統性掩蓋近山—都市介面的內部落差**——正是本文主張以 100 m 網格處理錯置的理由之一。

> **性質界定**：本附錄為**描述性外部對照**，非多城市機制檢驗。植被偵測比例（CHM > 0）與本文 §5.1 之樹冠覆蓋率（10 m 網格、CHM > 0）**定義不同、不可直接互比**；本附錄僅用於**同一指標下**之跨鄉鎮排序與臺北市內部落差之呈現。全臺各鄉鎮之人口密度、高程與制度條件未納入，故不構成 RQ1 之外部複製。

![](figures/figA2_tw_townships.png)

**附錄圖 A-2　全臺鄉鎮市區植被偵測比例與臺北市之位置**

*Appendix Figure A-2. Vegetation-detection share (CHM > 0) of all 368 Taiwanese townships computed from the native-resolution CHMv2 within township polygons. (a) Townships ranked by share, with the 12 Taipei districts highlighted; (b) the 12 Taipei districts, showing a 6.4-fold within-city contrast. Descriptively this shows that municipal averages mask the near-mountain–urban interface contrast; it is not a multi-city test of the mechanism.*

### 附錄 G-2　縣市層對照與交叉檢核

以 `county/<縣市>.tif`（22 檔）依縣市界（`COUNTY_MOI_1090820`）計算同一指標，並與鄉鎮層加總互驗（見表 S5）。


**表 S5　全臺 22 縣市樹冠結構鄉鎮加總與縣市直算交叉檢核表**

| 縣市 | 鄉鎮數 | 面積 (ha) | 植被偵測比例 | 樹冠比例 (≥2 m) | 樹冠平均高 (m) | 縣市直算 | 差異 (pp) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 花蓮縣 | 13 | 459,999 | 82.6 % | 81.3 % | 13.81 | 82.7 % | −0.01 |
| 南投縣 | 13 | 411,527 | 81.1 % | 79.1 % | 13.80 | 81.1 % | ±0.00 |
| 臺東縣 | 16 | 356,643 | 81.1 % | 79.5 % | 13.11 | 81.1 % | −0.01 |
| 新北市 | 29 | 204,093 | 77.8 % | 76.2 % | 11.58 | 77.9 % | −0.04 |
| 新竹縣 | 13 | 141,410 | 77.0 % | 75.1 % | 12.96 | 77.1 % | −0.04 |
| 宜蘭縣 | 12 | 216,695 | 75.2 % | 74.0 % | 13.12 | 75.3 % | −0.05 |
| 苗栗縣 | 18 | 183,463 | 72.0 % | 70.4 % | 12.63 | 72.1 % | −0.03 |
| 基隆市 | 7 | 13,779 | 70.5 % | 68.6 % | 7.89 | 70.5 % | −0.03 |
| 高雄市 | 38 | 293,530 | 63.5 % | 61.0 % | 11.48 | 63.4 % | +0.07 |
| 屏東縣 | 33 | 281,197 | 61.9 % | 58.1 % | 7.82 | 61.9 % | −0.03 |
| 臺中市 | 29 | 224,921 | 56.5 % | 54.5 % | 12.49 | 56.5 % | ±0.00 |
| 嘉義縣 | 18 | 196,010 | 53.9 % | 51.6 % | 11.67 | 53.9 % | −0.02 |
| **臺北市** | 12 | 27,095 | **51.3 %** | 48.9 % | 9.26 | 51.3 % | −0.01 |
| 桃園市 | 13 | 119,751 | 46.0 % | 44.1 % | 11.34 | 46.0 % | −0.05 |
| 連江縣 | 4 | 2,923 | 45.2 % | 41.0 % | 6.41 | 45.8 % | −0.53 |
| 臺南市 | 37 | 226,817 | 37.1 % | 34.4 % | 7.86 | 37.1 % | −0.01 |
| 金門縣 | 6 | 18,545 | 31.9 % | 28.6 % | 4.70 | 31.9 % | −0.06 |
| 嘉義市 | 2 | 6,000 | 31.8 % | 27.4 % | 7.59 | 31.8 % | ±0.00 |
| 新竹市 | 3 | 12,500 | 30.7 % | 28.5 % | 8.79 | 30.7 % | +0.01 |
| 澎湖縣 | 6 | 12,678 | 20.3 % | 15.8 % | 3.14 | 20.5 % | −0.17 |
| 雲林縣 | 20 | 140,390 | 15.9 % | 14.3 % | 7.88 | 15.9 % | ±0.00 |
| 彰化縣 | 26 | 124,752 | 13.5 % | 11.8 % | 6.22 | 13.5 % | +0.01 |

**交叉檢核**：22 個縣市之「鄉鎮層加總」與「縣市直算（10 m・NearestNeighbour）」於植被偵測比例之平均絕對差 **0.05 pp**、最大差 **0.53 pp**（連江縣；面積小、島嶼邊界效應）。臺北市為 51.26 %／51.27 %（差 −0.01 pp）。此一致性支持附錄 G 以鄉鎮層呈現之結果。

**觀察**：臺北市 51.3 % 於六都中排名第 4（低於新北 77.8 %、高雄 63.5 %、臺中 56.5 %；高於桃園 46.0 %、臺南 37.1 %），於全臺 22 縣市中排名第 13。**縣市層看不出其特殊性**——這正是重要之處：臺北市的「近山—都市」張力**不在縣市平均值**，而在**市內**（12 區由 10.0 % 至 64.1 %，見附錄 J(2)）；以縣市或行政區為單元均無法呈現介面落差（縣市層空間分布見附錄圖 A-6）。

![](figures/figA6_tw_counties.png)

**附錄圖 A-6　全臺 22 縣市植被偵測比例（縣市層）**

*Appendix Figure A-6. Vegetation-detection share (CHM > 0) of the 22 Taiwanese counties/cities, computed by aggregating the native-resolution township results (green) and independently by direct county-level computation at 10 m (grey); Taipei City is highlighted in red. The two paths agree within 0.05 pp on average (maximum 0.53 pp), and Taipei City (51.3 %) ranks only 13th of 22 — the near-mountain–urban tension lies within, not between, municipalities.*

### 附錄 H　官方山坡地與使用分區之交叉檢核（制度脈絡）

**（1）官方山坡地 × 高程帶（近山界定之外部檢核）**

方法：將內政部《山坡地範圍》（115.05.12 版，原始 EPSG:3824）投影並點陣化至與主分析相同之 100 m 網格，再與 5 m DEM 之平均高程交叉列表。向量面積 14,914 ha，網格計數 14,917 格（≈14,917 ha），一致性良好（見表 S6）。


**表 S6　官方山坡地劃定範圍與高程帶分佈交叉檢核表**

| 高程帶 | 網格數 | 該帶中被劃為山坡地之比例 | 占全部山坡地之比例 |
|---|---:|---:|---:|
| 都市平地 0–20 m | 20,510 | **1.4 %** | 2.0 % |
| 丘陵近山 20–100 m | 9,413 | 41.1 % | 25.9 % |
| 淺山 100–300 m | 14,391 | 31.0 % | 29.9 % |
| 山地 300–600 m | 10,089 | 39.3 % | 26.6 % |
| 中高山 > 600 m | 4,533 | 51.3 % | 15.6 % |
| **合計** | 58,936 | — | 100 % |

官方山坡地有 **98.0 %** 落於高程 ≥ 20 m；平地帶僅 1.4 % 被劃為山坡地。各帶比例並非單調遞增，係因山坡地之法定劃定同時考量**平均坡度**與區位（山坡地保育利用條例），非純以高程判定。**結論**：以「高程 ≥ 20 m」界定近山—都市介面，與官方山坡地高度一致，且不會把平地誤納入近山。

**（2）使用分區 × 供需象限（制度性錯位）**

方法：將臺北市《主要計畫圖》（115.04.09 版）使用分區點陣化至同一 100 m 網格，對照 §5.4 之四象限（供給＝樹冠 ≤ 平均；需求＝人口 > 平均）。全市 27,652 有效格中 7,911 格為赤字格（與表 5.5 一致）；各分區之赤字組成見表 S7。


**表 S7　供需赤字網格（低供給·高需求）之主要土地使用分區組成表**

| 使用分區 | 網格數 | 平均 SAI | 平均樹冠 (m) | 平均人口密度 | 赤字格數 | 占該分區 | 占全部赤字格 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **住宅區** | 4,510 | 30.6 | 1.63 | 178.7 | **3,304** | 73.3 % | **41.8 %** |
| （計畫圖未標註分區） | 2,248 | 34.1 | 2.54 | 108.2 | 1,045 | 46.5 % | 13.2 % |
| 商業區 | 981 | 24.2 | 0.44 | 189.8 | 752 | 76.7 % | 9.5 % |
| 特定專用區 | 444 | 24.1 | 1.00 | 246.9 | 418 | 94.1 % | 5.3 % |
| 工業區 | 444 | 22.1 | 0.51 | 145.8 | 340 | 76.6 % | 4.3 % |
| 機關用地 | 533 | 49.3 | 3.52 | 94.2 | 219 | 41.1 % | 2.8 % |
| 國小用地 | 269 | 28.4 | 1.48 | 167.2 | 204 | 75.8 % | 2.6 % |
| 道路用地 | 1,660 | 17.1 | 0.43 | 27.5 | 201 | 12.1 % | 2.5 % |
| 公園用地 | 1,014 | 38.1 | 4.43 | 55.4 | 188 | 18.5 % | 2.4 % |
| **保護區** | **6,993** | **63.5** | **8.18** | 11.1 | 122 | **1.7 %** | 1.5 % |

**解讀**：赤字格以**住宅區（41.8 %）**與**商業區（9.5 %）**為主，即**私有、高密度、可開發**之土地；供給側則集中於**保護區**（6,993 格、近全市四分之一；平均 SAI 63.5、樹冠 8.18 m、僅 1.7 % 為赤字）。此「**供給在不可開發地、需求在私有密集地**」的制度性錯位，說明總量導向之植樹或單一碳帳本無法解決錯置，必須透過帳本邊界與跨區配置機制（見 §6.3）。

> **限制**：使用分區為 115 年版主要計畫圖；部分格（2,248 格，占赤字 13.2 %）在該圖層中未標註分區（多屬非都市計畫或圖層未覆蓋範圍），故上述比例為**在已標註分區範圍內**之分布，且不作因果推論。Open Green 案例僅有行政區質心座標（3 案有門牌），故**未**進行案例落點×分區之精細對照。

![](figures/figA3_land_context.png)

**附錄圖 A-3　官方山坡地與使用分區之交叉檢核**

*Appendix Figure A-3. (a) Share of each elevation band designated as official slope land (Council of Agriculture slope-land boundary, 2026 version); (b) land-use zoning composition of the low-supply/high-demand deficit cells. Deficit cells concentrate on privately developable residential (41.8 %) and commercial (9.5 %) land, whereas protected-zone land accounts for about a quarter of the city but only 1.7 % of its cells are deficit.*

### 附錄 I　年 NPP 通量產品之可用性檢核（通量延伸之資料障礙）

**目的與來源**：評估既有「年 NPP」產品（CASA × 調和 NDVI，100 m、EPSG:3826，與主網格相同；來源專案 `E:\SCI\20260704`）是否足以支持時序／空間通量分析。另檢核 MODIS 降尺度產品（`modis_npp_YYYY_100m.tif`）。

**逐年品質**（`wp3b_carbon_flux.csv` 為完整表；表 S8 列關鍵年度）：


**表 S8　既有年 NPP 通量產品逐年品質與零值比例稽核表**

| 年度 | 感測器 | 零值比例 | 正值格平均 NPP | 可用 |
|---:|---|---:|---:|:--:|
| 1998 | Landsat 5 | 5.8 % | 1,141 | ✓ |
| 2002 | Landsat 7 | 2.3 % | 1,908 | ✓ |
| **2003** | Landsat 7 | **98.7 %** | 35 | ✗ |
| **2008** | Landsat 7 | **84.4 %** | 315 | ✗ |
| 2012 | Landsat 7 | 3.3 % | 2,016 | ✓ |
| 2014 | Landsat 8 | 12.7 % | 1,526 | ✓ |
| **2015** | Sentinel-2 | **96.7 %** | 452 | ✗ |
| 2019 | Sentinel-2 | 45.4 % | 1,240 | ✓ |
| 2024 | Sentinel-2 | 51.3 % | 1,109 | ✓ |
| **2025** | Sentinel-2 | **100 %** | 0 | ✗ |

**四項發現**

1. **4 個年度實質無效**（2003、2008、2015、2025；零值比例 ≥ 84 %），檔案亦明顯偏小。
2. **感測器世代之不連續**：Landsat 期（1998–2014）零值多為 1–20 %，Sentinel-2 期（2015–2025）穩定為 **45–52 %**。若不做分世代處理，全期趨勢（−34 gC/m²/yr）實為**零值膨脹**與世代差異之合成，非生產力變化。分世代之閉式趨勢見 `wp3b_carbon_flux.json`（`era_trends`）。
3. **空間分布不合理**：2019 年各高程帶之零值比例由都市平地 18 % 遞增至中高山 **100 %**；> 600 m 帶 NPP 占比為 0 %（與 ΔΣH 占比 13.2 % 不符），顯示山地帶大面積被遮罩。
4. **MODIS 降尺度產品不可用**：`modis_npp_*_100m.tif`（2001–2024）為**常數柵格**（各年 std ≈ 0、min = max = 3.2766），無空間資訊。

**判定**：既有 NPP 產品**不足以支持可辯護的時序或空間通量分析**。本階段未納入通量分析；本文續以 **ΣH（冠層結構）** 作為供給側代理，並依鐵則**嚴格區分 stock 與 flux**——本附錄即為「不以不可靠通量資料替代結構指標」之依據。後續若需通量證據，應改採：(i) 地面通量塔或林業署年通量統計；(ii) MODIS/Terra GPP-NPP 官方產品（非降尺度再造）；(iii) 林業碳匯官方盤查之年通量，並先完成感測器一致性校正與 no-data 判定。

![](figures/figA4_carbon_flux.png)

**附錄圖 A-4　年 NPP 產品之可用性檢核**

*Appendix Figure A-4. Usability audit of the annual NPP product. (a) Share of zero-valued cells per year (grey = Landsat era, brown = Sentinel-2 era, red = effectively unusable years); (b) band-wise share of NPP (positive cells only) versus ΣH in 2019, annotated with the zero share of each band. The zero-inflation and sensor-era discontinuity make the existing flux product unsuitable for temporal or spatial flux analysis.*

### 附錄 J　行道樹結構分解與區級樹冠結構

**（1）行道樹樹種與胸徑之高程帶分解**（`wp1b_tree_structure.py`；92,626 棵，284 種；見表 S9）


**表 S9　行道樹樹種組成與胸徑結構之高程帶分解表**

| 高程帶 | 棵數 | 樹種數 | 主要樹種（前 8 種占比 %） | 胸徑中位數 (cm) | IQR (cm) |
|---|---:|---:|---|---:|---|
| 都市平地 0–20 m | 87,647 | **275** | 榕樹 12／茄苳 11／樟樹 10／楓香 8／臺灣欒樹 7／黑板樹 8／白千層 7 | 24.0 | 12.3–35.3 |
| 丘陵近山 20–100 m | 3,971 | 139 | 黑板樹 10／臺灣欒樹 9／榕樹 8／楓香 7／白千層 7／樟樹 6 | 20.0 | 6.9–34.0 |
| 淺山 100–300 m | 715 | 40 | **楓香 45**／榕樹 15／白千層 7／臺灣欒樹 6 | 27.8 | 17.2–37.6 |
| 山地 300–600 m | 293 | **11** | **榕樹 50／楓香 43**（兩者合計 93 %） | **53.0** | 41.5–64.0 |
| 中高山 > 600 m | 0 | — | — | — | — |

兩項結構訊息：**(i) 樹種多樣性隨高程急遽收斂**（275 → 11 種），平地帶承載全市綠意的**物種多樣性核心**；**(ii) 山區僅存的少數行道樹為大型個體**（胸徑中位數 53 cm、約平地之 2.2 倍），且集中為榕樹與楓香兩種。此解釋了第五、六章之關鍵對比：**平地以「數量多、樹種雜、個體小」的行道樹承擔日常綠意；山區則以少數大樹與連片森林貢獻 ΣH 結構**——兩者不可用同一指標衡量，亦支持 §6.2「量體 ≠ 暴露」之論證。

**（2）區級樹冠結構**（本專案 CHMv2 管線重算：10 m・NearestNeighbour・DEM∩CHM 有效域；見表 S10）


**表 S10　臺北市 12 行政區樹冠結構重算與覆蓋率對照表**

| 行政區 | 有效面積 (ha) | 樹冠面積 (ha) | 覆蓋率 | 樹冠高 mean (m) | median (m) | P90 (m) | ΣH (m·ha) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 士林區 | 6,192.0 | 3,966.3 | 64.1 % | 9.83 | 10 | 17 | 39,003 |
| 南港區 | 2,190.1 | 1,355.9 | 61.9 % | 9.14 | 9 | 16 | 12,397 |
| 內湖區 | 3,191.6 | 1,894.2 | 59.4 % | 8.96 | 9 | 14 | 16,982 |
| 文山區 | 3,116.9 | 1,809.7 | 58.1 % | 9.05 | 9 | 16 | 16,383 |
| 北投區 | 5,756.2 | 3,252.7 | 56.5 % | 9.47 | 9 | 17 | 30,811 |
| 信義區 | 1,123.7 | 491.4 | 43.7 % | 10.01 | 10 | 17 | 4,917 |
| 大安區 | 1,132.0 | 310.6 | 27.4 % | 8.14 | 8 | 15 | 2,529 |
| 中山區 | 1,403.6 | 346.4 | 24.7 % | 7.16 | 7 | 12 | 2,480 |
| 中正區 | 741.9 | 148.5 | 20.0 % | 6.69 | 6 | 12 | 993 |
| 萬華區 | 744.2 | 95.2 | 12.8 % | 5.46 | 5 | 11 | 520 |
| 大同區 | 477.6 | 50.6 | 10.6 % | 5.74 | 5 | 11 | 291 |
| 松山區 | 865.3 | 86.7 | 10.0 % | 5.85 | 5 | 11 | 508 |
| **合計** | **26,935.1** | **13,808.2** | **51.3 %** | — | — | — | **127,812** |

12 區之樹冠面積 13,808.2 ha 與 ΣH 127,812 m·ha，分別與表 5.1 之 13,805.4 ha／127,779.3 m·ha 差異 **+0.02 %／+0.03 %**；區級覆蓋率亦與附錄 G（原生解析度）一致（松山 10.0 % vs 10.1 %；士林 64.1 % vs 64.0 %），顯示各管線之可重現性。區級排序同時呼應圖 5-4 之案例分布與附錄 H 之使用分區結構（圖版見附錄圖 A-5）。

![](figures/figA5_tree_structure.png)

**附錄圖 A-5　行道樹結構分解與區級樹冠結構**

*Appendix Figure A-5. (a) Species composition of the Taipei street-tree census by elevation band (top eight species, % of trees per band); (b) median and interquartile range of trunk diameter (DBH) by band; (c) canopy cover of the 12 districts recomputed with the project's own CHMv2 pipeline (10 m, nearest neighbour). Species richness collapses from 275 (flat) to 11 (mountain), while median DBH rises from 24 to 53 cm.*
"""
    OUT.write_text(body.rstrip() + "\n\n---\n\n" + refs + "\n", encoding="utf-8")
    print("wrote", OUT, len(OUT.read_text(encoding='utf-8')), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
