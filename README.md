# 典藏說明（Zenodo / GitHub）

**標題**：Carbon on the Hills, Green in the Alleys: Spatial Mismatch of Canopy Structure and
Green Exposure across the Near-Mountain–Urban Interface of Taipei City
（碳在山、綠感在巷：臺北市近山—都市介面之綠碳供需空間錯置）

本典藏包含論文（v16）之**分析程式**與**程式輸出**，用以重現正文與補充材料中之全部數值、
表格與圖版。原始資料皆為公開資料，未一併轉載（見「資料來源」）。

## 內容

| 目錄 | 內容 | 檔案數 |
|---|---|---:|
| `code/` | 分析、統計、製圖與文件組裝程式（Python 3.10；GDAL／geopandas／numpy／PIL） | 72 |
| `results/` | 程式輸出：JSON（數值）、CSV（表格）、PKL（直方圖） | 46 |
| `_manifest_sha256.csv` | 全部檔案之大小與 SHA-256（完整性檢核） | 1 |

## 資料來源（原始資料，公開）

| 資料 | 來源 | 授權 |
|---|---|---|
| CHMv2 樹冠高度（1.19 m，EPSG:3857） | Meta AI & World Resources Institute（DINOv3 Global CHM v2） | 開源 |
| 5 m DEM | 臺北市政府（政府資料開放） | 政府資料開放授權條款第 1 版 |
| 臺北市行道樹普查（92,626 棵可分析） | 臺北市工務局公園路燈工程管理處 | 同上 |
| WorldPop 人口密度（2026，約 90 m） | WorldPop | CC BY 4.0 |
| 里級戶籍人口與戶數（2024–2026 逐月） | 臺北市政府民政局 | 政府資料開放授權條款第 1 版 |
| 村里界、區界 | 臺北市政府都市發展局；內政部國土測繪中心 | 同上 |
| 鄉鎮市區界（1140318）、縣市界（1090820） | 內政部國土測繪中心 | 同上 |
| 山坡地範圍（1150512）、主要計畫圖（1150409） | 內政部／臺北市政府都市發展局 | 同上 |
| Open Green 年度報告（108–114） | 臺北市都市更新處 | 政府公開資訊 |
| 企業自然／碳專案（35 件） | 農業部林業及自然保育署 ESG 媒合平臺 | 政府公開資訊 |
| 年 NPP 產品（1998–2025，100 m） | 專案既有產品（CASA × 調和 NDVI） | 依原授權 |

## 重現步驟

```bash
# 環境：Python 3.10、GDAL 3.12、geopandas、numpy、Pillow
# 1) 取得公開資料後置於專案根目錄（CHM 裁切檔置 county/、鄉鎮裁切檔置 townships/）
# 2) 依序執行
python wp1_data_audit.py            # 行道樹稽核（92,777 → 92,626）
python taipei_elev_carbon_scan.py   # 高程帶 ΣH（表 5.1）
python wp2_green_accessibility.py   # SAI 與人口加權（表 5.2）
python wp2_spatial_stats.py         # Moran's I／LISA／四象限（表 5.4、5.5）
python wp2_spatial_inference.py     # 空間區塊 bootstrap／置換（表 4.5）
python wp2_sai_sensitivity.py       # 半徑×權重敏感度（表 5.7）
python wp2_network_access.py        # 路網近似距離（表 5.6）
python wp2b_pop_village.py          # 里級戶籍人口解析與校驗
python wp2b_pop_weight_robustness.py# 需求權重穩健性（表 5.9、Figure 10）
python wp1_chm_validation.py        # CHMv2 驗證（Figure S1）
python wp1b_tree_structure.py       # 行道樹結構分解（Table S9、S10）
python wp2c_tw_townships.py         # 全臺 368 鄉鎮（Table S4、Figure S2）
python wp2c2_tw_counties.py         # 全臺 22 縣市（Table S5、Figure S3）
python wp2d_land_context.py         # 山坡地／使用分區（Table S6、S7）
python wp3b_carbon_flux.py          # NPP 產品可用性（Table S8）
python build_paper.py               # 組裝全文與 Word 檔
```

> 註：本機環境之 BLAS/LAPACK 與 matplotlib 不相容，故所有圖版以 PIL 繪製；統計以閉式解計算
> （未使用 `scipy.stats`），此設計不影響結果數值。

## 授權

- **程式碼**：MIT（見 `LICENSE`）
- **衍生結果**（`results/`）：CC BY 4.0
- **原始資料**：依上表各來源授權，使用時請引用原資料提供者

## 引用

- **DOI（v1.0.0）**：<https://doi.org/10.5281/zenodo.22865864>（Concept DOI：<https://doi.org/10.5281/zenodo.22865863>）
- **GitHub repo**：<https://github.com/kent6209-cloud/taipei-canopy-exposure-mismatch>
- 引用格式見 `CITATION.cff`；建議同時引用典藏與論文。
