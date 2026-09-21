# Zenodo 上架欄位（可直接複製貼上）

## 上架流程（取得 DOI 的標準路徑）

1. **建立 GitHub repo**（本專案 `E:\GeoAI` 尚無 commit／remote，需先在 `20260909_taiwan_chmv2\` 內建 repo 或直接上傳 `deposit_zenodo/`）：
   ```powershell
   cd E:\GeoAI\20260909_taiwan_chmv2
   git init
   git add deposit_zenodo
   git commit -m "feat(deposit): analysis code and results for the Taipei canopy-exposure mismatch study"
   git branch -M main
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```
   > 建議把 `deposit_zenodo/` 內容放在 repo 根目錄（即 `code/`、`results/`、`README.md`、`LICENSE`、`CITATION.cff`）。
   > `.gitignore` 至少排除：`Paper/`（含 Word 檔）、`county/`、`townships/`、`tiles/`、`data_civil/*.ods`、`*.zip`（原始資料與大檔）。

2. **連結 Zenodo**：登入 <https://zenodo.org> → Settings → GitHub → 勾選該 repo（授權一次即可）。

3. **發布 Release**：在 GitHub 建 `v1.0.0` Release（Zenodo 會自動封存並**產生 DOI**）。

4. **回填 DOI**：Zenodo 會給兩種 DOI
   - **Version DOI**（例：`10.5281/zenodo.1234567`）→ 用於本論文引用
   - **Concept DOI**（例：`10.5281/zenodo.1234566`）→ 用於「所有版本」
   取得後把 DOI 填入 `CITATION.cff` 的 `identifiers` 與論文的 Data Availability Statement。

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
