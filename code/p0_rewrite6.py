# -*- coding: utf-8 -*-
"""P0 pass 6: extend the temporal-baseline table (integration rules) and add the
spatial-effective-sample-size table in §4.4.  Dry run unless --apply.
"""
import pathlib
import sys

P = pathlib.Path(r'E:\GeoAI\20260909_taiwan_chmv2\Paper\第四章_研究設計與方法_正式草稿.md')
apply = '--apply' in sys.argv

OLD_TABLE = """| 資料 | 觀測年份 | 說明 |
|---|---|---|
| 官方溫室氣體排放／林業碳匯 | 2023（112 年） | 政策對帳用 |
| CHMv2 樹冠高度 | 產品版次年度（約 2023–2024） | 供給側結構 |
| 臺北市行道樹普查 | 各樹籍 SurveyDate（2022 為主，含更新） | 生物量與密度 |
| WorldPop 人口密度 | 2026 | 需求權重 |
| 100 m 綠地分類圖 | 2025 版 | 綠地比例 |
| Open Green 案例 | 108–114 年（2019–2025） | 需求側治理案例 |
| 企業自然／碳專案 | 目前公告之已媒合案件 | 供給側資本 |
"""

NEW_TABLE = """**表 4-1　資料時間涵蓋與整合規則（Temporal coverage and integration rules）**

| 資料 | 觀測年份 | 原始解析度／單位 | 用途 | 整合規則 |
|---|---|---|---|---|
| 官方溫室氣體排放／林業碳匯 | 2023（112 年） | 全市總量 | 政策對帳 | 僅作量級對照；不作空間分析 |
| CHMv2 樹冠高度 | 產品版次年度（約 2023–2024） | 1.19 m（EPSG:3857） | 供給側結構（ΣH） | 重投影至 EPSG:3826、10 m 網格（NearestNeighbour）；逐列 cos²(lat) 面積校正 |
| 5 m DEM | 單期（2024 版） | 5 m（WGS84） | 高程帶界定、地形底圖 | 雙線性重採樣至 10／100 m 網格 |
| 臺北市行道樹普查 | 各樹籍 `SurveyDate`（2022 為主，含後續更新） | 點（92,626 棵可分析） | 平地結構分解、生物量 | 逐棵配對至 100 m 網格與高程帶；僅採 `analysis_ready` 者 |
| 100 m 綠地分類圖 | 2025 版 | 100 m 多邊形 | SAI 綠地成分（`grn_ratio`） | 與主網格（EPSG:3826、100 m）直接對齊 |
| WorldPop 人口密度 | 2026 | 約 90 m（WGS84） | 需求相對權重（W1） | 平均重採樣至 100 m；僅作相對權重 |
| 民政局里級戶籍人口 | 2024–2026 逐月（最新 2026-08） | 里（456 里） | 需求權重穩健性（W2／W3） | 以里界多邊形面積權重配置至 100 m 網格 |
| Open Green 案例 | 108–114 年（2019–2025） | 案件 | 需求側治理案例（專案層描述） | 行政區質心定位（3 案有門牌）；四象限分類 |
| 企業自然／碳專案 | 2026 年公告之已媒合案件 | 案件（35 件） | 供給側資本（市場外分布） | 縣市層登錄；**0 件位於臺北市** |
"""

OLD_ANCHOR = "- **區分「距離」與「供給密度」**：前者為最近綠源之距離，後者為 500 m 窗內供給量；兩者空間方向可能相反。"
NEW_ANCHOR = OLD_ANCHOR + """

**表 4-2　空間有效推論設定與有效樣本數（Spatial inference and effective sample size）**

| 檢定 | 網格數 | Moran's I | 有效樣本數 *n*_eff | 區塊數（500 m） | 區塊置換 *p* | 區塊 bootstrap 95 % CI |
|---|---:|---:|---:|---:|---:|---|
| 樹冠密度 × 人口 | 23,342 | 0.817 | **1,925** | 1,116 | **0.001** | [−0.564, −0.491]（區塊層 ρ = −0.562） |
| SAI × 人口 | 23,342 | 0.994 | **46** | 1,116 | **0.001** | [−0.635, −0.559]（區塊層 ρ = −0.649） |

> 說明：兩萬餘網格具高度空間自相關（SAI 之 lag-1 自相關 0.996），一般 *p* 值不成立；上表改以 500 m 空間區塊層推論（999 次置換、1,000 次 bootstrap），有效樣本數僅 46–1,925。SAI 之有效樣本數極低，故其推論以區塊層為準（`wp2_spatial_inference.py`）。"""

t = P.read_text(encoding='utf-8')
stats = {'table4-1': t.count(OLD_TABLE), 'anchor4-2': t.count(OLD_ANCHOR)}
if stats['table4-1']:
    t = t.replace(OLD_TABLE, NEW_TABLE)
if stats['anchor4-2']:
    t = t.replace(OLD_ANCHOR, NEW_ANCHOR)
if apply:
    P.write_text(t, encoding='utf-8')
print('{}: {}'.format('APPLIED' if apply else 'DRY-RUN', stats))
