# Zenodo 上架欄位（可直接複製貼上）

## 上架流程（取得 DOI 的標準路徑）

1. **建立 GitHub repo** —— ✅ 已完成（`deposit_zenodo\` 即 repo 根目錄，branch `main`，初始 commit `8295438`，126 檔／12.9 MB）
   - remote：`https://github.com/kent6209-cloud/taipei-canopy-exposure-mismatch.git`（已 push `main` 與 annotated tag `v1.0.0`）
   ```powershell
   cd E:\GeoAI\20260909_taiwan_chmv2\deposit_zenodo
   git remote -v            # 已設定 origin
   git push                 # 後續更新直接 push
   ```
   > repo 根目錄已含 `code/`、`results/`、`README.md`、`LICENSE`、`CITATION.cff`、`.gitignore`、`.gitattributes`。
   > `.gitignore` 已排除原始資料與大檔（`county/`、`townships/`、`tiles/`、`*.tif`、`*.gpkg`、`*.shp`、`data_civil/*.ods`、`*.zip`、`Paper/`）。

2. **連結 Zenodo**：登入 <https://zenodo.org> → Settings → GitHub → 勾選 `taipei-canopy-exposure-mismatch`（授權一次即可）。

3. **發布 Release**（Zenodo 只在建立 Release 時封存並產生 DOI；單純 push tag 不會）：
   - 開 <https://github.com/kent6209-cloud/taipei-canopy-exposure-mismatch/releases/new?tag=v1.0.0>
   - Title：`v1.0.0 — analysis code and results (paper v16 submission)`
   - 貼上下方「Description」段落 → **Publish release**

4. **回填 DOI** —— ✅ 已完成，Zenodo 已發 DOI：
   - **Version DOI（v1.0.0）**：`10.5281/zenodo.22865864` → <https://doi.org/10.5281/zenodo.22865864>
   - **Concept DOI（所有版本）**：`10.5281/zenodo.22865863` → <https://doi.org/10.5281/zenodo.22865863>
   - Zenodo record：<https://zenodo.org/records/22865864>（resource type software、MIT、2026-09-21、封存檔 `kent6209-cloud/taipei-canopy-exposure-mismatch-v1.0.0.zip`）
   - 已回填：`CITATION.cff` 的 `identifiers`、`README.md`、論文的 Data Availability Statement（`build_sustainability_zh.py` 之 BACK_MATTER）

## Zenodo 表單欄位（複製用）

**Resource type**：Software

**Title**
```
Carbon on the Hills, Green in the Alleys: analysis code and results for the spatial mismatch of canopy structure and green exposure across the near-mountain–urban interface of Taipei City
```

**Authors**
```
Wang, Ming-Chih Jason (0000-0000-0000-0000)   ← 待確認 ORCID
Chen, Chien-Min (0000-0000-0000-0000)         ← 待確認 ORCID
```

**Description**
```
Analysis code and reproducible outputs for a study of the spatial mismatch between the
canopy-structure carbon proxy (ΣH, m·ha) and the 500 m green-supply exposure index (SAI,
0–100) across the near-mountain–urban interface of Taipei City.

Contents: (i) data auditing and evidence-freeze scripts for the Taipei street-tree census
(92,777 records → 92,626 analysable trees); (ii) canopy-structure and accessibility indices
at 10 m / 100 m grids; (iii) spatial autocorrelation (Moran's I, LISA, bivariate Moran) and
spatially effective block bootstrap / permutation inference; (iv) sensitivity and robustness
checks (radius × weight, demand-weight source, resolution/resampling, road-network distance);
(v) nationwide township (n = 368) and county (n = 22) comparisons for external validity;
(vi) CHMv2 validation against the street-tree census (n = 92,625 pairs); (vii) all figure
generation scripts (PIL-based).

All input datasets are openly available from the sources listed in README.md and are not
redistributed here.
```

**Keywords**
```
urban green accessibility; canopy height model; spatial mismatch; spatial autocorrelation;
block bootstrap; Taipei City; near-mountain-urban interface; urban canopy structure
```

**License**：MIT（程式碼）；衍生結果建議另註 CC BY 4.0

**Version**：`1.0.0`

**Language**：English（說明）／Chinese（部分程式註解）

**Related identifiers**：待論文上線後填入期刊 DOI（`is supplement to` / `is published in`）

## 取得 DOI 後要改的地方（我可代改並重建）

| 檔案 | 現行文字 | 改為 |
|---|---|---|
| 論文（MDPI 後置聲明） | `Derived spatial layers and analysis scripts are available from the corresponding author on reasonable request.` | `Derived spatial layers and analysis scripts are archived at Zenodo: https://doi.org/10.5281/zenodo.XXXXXXX.` |
| `Paper/new/README_交付說明.md` | 「Repository DOI／URL（現為…）」 | 填入 DOI |
| `deposit_zenodo/CITATION.cff` | 註解中的 `identifiers` | 取消註解並填 DOI |
