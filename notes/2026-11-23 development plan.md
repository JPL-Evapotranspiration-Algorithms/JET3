# `JET3` Integrated Development Plan (`v1.0.1` → `v3.3.0`)

- **Date:** November 23, 2026
- **Current Release:** `v3.2.0`
- **Target Release:** `v3.3.0` (resolving the `GEOS5FP` `vapor_gccm`/`ozone_cm` unit regression via `GEOS5FP>=2.27.0`, implementing opt-in GEOS-5 FP residual bias correction for `FLiES-ANN` solar radiation `SWin_Wm2` / `Rg` (`#23`), adding physical unit-range guardrails, and aligning with `ECOv003-L3T-L4T-JET v1.23.0`)
- **Primary Objective:** Consolidate the complete engineering lineage of `JET3` (`v1.0.1`–`v3.2.0`) and finalize the `v3.3.0` release to restore operational ECOSTRESS Collection 3 `L3T_ETAUX` `Rg` parity while preserving strict numerical equivalence with the `ECOv002` Cal-Val baseline (`JET3.verify()`).

---

## 1. Executive Summary & Architectural Context

`JET3` (`JPL-Evapotranspiration-Algorithms/JET3`) is the standalone, mission-independent science engine underlying the ECOSTRESS Collection 3 Level-3/4 Evapotranspiration Product Generating Executable (`ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET`) and the Surface Biology and Geology (`SBG-TIR-L4-JET`) pipeline.

| Layer | Repository | Role & Responsibility |
| :--- | :--- | :--- |
| **Operational PGE Wrapper** | `ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET` | Parses XML RunConfigs, reads `L2T_LSTE` and `L2T_STARS` granules, invokes `JET3`, writes COG/JSON/GeoJPEG bundles (`L3T ETAUX`, `L3T JET`, `L4T ESI`, `L4T WUE`), and runs inside the `eco-level-2-3-4-application` Docker container. |
| **Core Ensemble & Downscaling Engine** | `JPL-Evapotranspiration-Algorithms/JET3` | Orchestrates meteorological/soil-moisture sharpening, bias calibration & uncertainty quantification (UQ), radiative transfer, and the 4-model terrestrial ET ensemble + open-water model; also provides tabular processing (`process_JET_table`) and numerical verification (`verify`). |
| **Radiative Transfer & Net Radiation** | `FLiESANN`, `verma-net-radiation`, `SEBAL-soil-heat-flux` | Computes TOA/surface shortwave radiation (`FLiESANN`), net radiation (`verma-net-radiation`), and soil heat flux (`SEBAL-soil-heat-flux`). |
| **Constituent ET & Water Models** | `PTJPLSM`, `STIC-JPL`, `PM-JPL`, `BESS-JPL`, `AquaSEBS` | Individual surface energy balance, GPP, and open-water evaporation models combined by `JET3`. |

Because `JET3` was extracted as its own package in **February 2026**—roughly three months *after* ECOSTRESS Collection 3 entered operational forward processing (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`, paired with `ECOv003-L3T-L4T-JET` `v1.13.0`–`v1.16.0`)—all development is governed by two core invariants:
1. **Collection 3 Operational & Cal-Val Baseline Consistency:** Default execution (`use_calibration=False`, `generate_UQ=False`, `bias_correct_FLiES_ANN=False`) must match both the frozen `ECOv002-cal-val-JET-outputs.csv` reference baseline (`rtol=1e-4, atol=1e-7` enforced by `JET3.verify()`) and public LP DAAC Collection 3 archive granules (`BuildID 0700`).
2. **Cross-Stack Contract & Unit Integrity (`GEOS5FP >=2.27.0`):** `JET3` must enforce SI method contracts (`wind_speed_mps`, `Td_K`) and physical unit-range guardrails (`vapor_gccm` in $\text{g cm}^{-2}$, `ozone_cm` in $\text{cm}$) so upstream dependency regressions are caught immediately rather than silently shifting radiative transfer or surface energy balance outputs.

---

## 2. Completed Development & Release History (`May 2025 – November 2026`)

### 2.1. Pre-Extraction Lineage Inside `ECOv003-L3T-L4T-JET` (`v1.0.1` – `v1.16.0`, May 2025 – January 2026)

Before `JET3` existed as a separate repository, its ensemble orchestration, spatial downscaling, and verification suite were built and validated inside `ECOv003-L3T-L4T-JET`:

- **`v1.0.1` (2025-05-21) — Initial Collection 3 Port:**
  - Ported `ECOv002-L3T-L4T-JET` to Collection 3 and replaced inline legacy model implementations with standalone `JPL-Evapotranspiration-Algorithms` packages (`BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `STIC-JPL`, `PTJPLSM>=1.2.0`, `FLiESANN`, `FLiESLUT`, `verma-net-radiation`, `NASADEM>=1.2.0`).
  - Consolidated three Collection 2 auxiliary products (`L3T SEB`, `L3T SM`, `L3T MET`) into a unified **`L3T ETAUX`** product (`Ta`, `RH`, `SM`, `Rg`, `Rn`) and added per-model daily ET layers alongside the ensemble daily median (`ETdaily`).
- **`v1.1.0` – `v1.9.0` (2025-06-24 to 2025-09-12) — Downscaling Modularization & Auxiliary Data Wiring:**
  - Extracted `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` (`v1.1.0`) and adopted `ECOv003-exit-codes`.
  - Wired `GEDI` canopy height, `MODISCI` clumping index, and `SoilGrids` field capacity/wilting point directories into `BESS-JPL` and `PTJPLSM` (`v1.4.0`–`v1.6.6`).
  - Wrapped spatial downscaling calls in `try/except` fallback blocks (`v1.7.0`), standardized on tilde (`~=`) dependency pins, and masked sharpened meteorology rasters to valid ECOSTRESS LST swath pixels (`v1.7.1`–`v1.9.0`).
- **`v1.10.0` – `v1.11.0` (2025-10-01 to 2025-11-12) — Open-Water Evaporation & SI/Daylight Standardization:**
  - Integrated **`AquaSEBS`** for open-water evaporation over SRTM/NASADEM water masks and added dual `ECOv002`/`ECOv003` granule support (`v1.10.0`).
  - Standardized internal variable names to explicit SI unit suffixes (`SZA_deg`, `elevation_m`, `SWin_Wm2`, `LE_*_Wm2`, `Rn_Wm2`), switched to raw `FLiESANN~=2.1.0` solar radiation without `GEOS5FP.SWin` bias correction (`91478687`), enabled `upscale_to_daylight=True` across all four ET models, aligned `ETdaily` and `ETuncertainty` to $\text{mm day}^{-1}$, and added canopy/soil/interception partitioning layers (`v1.11.0`).
- **`v1.13.0` – `v1.16.0` (2025-11-18 to 2026-01-30) — Pipeline Modularization, `verify.py`, & C3 Deployment:**
  - Decomposed the PGE into `JET.py`, `process_JET_table.py`, and `verify.py` (bundled with `ECOv002-cal-val-JET-inputs.csv` and `ECOv002-cal-val-JET-outputs.csv`), entering operational forward processing on November 20, 2025 (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`) paired with `ECOv003-L2T-STARS>=1.11.0` ingesting Suomi NPP VIIRS (`VNP43NRT`).
  - Locked the Collection 3 validation baseline in `v1.16.0` (`AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0`, `verma-net-radiation~=1.11.0`) and extracted the core science engine into standalone `JET3`.

---

### 2.2. Standalone `JET3` Release History (`v3.0.0` – `v3.2.0`, February – November 2026)

- **`v3.0.0` & `v3.0.1` (2026-02-18) — Initial Standalone Repository & Verification Suite:**
  - Created `JET3` (`ed6a1ef0`) containing `JET.py`, `process_JET_table.py`, `constants.py`, `exceptions.py`, `Ta_C_error_OLS.py`, `ECOv002_calval_JET_inputs.py`, `ECOv002_calval_JET_outputs.py`, and `verify.py` + `tests/test_verify.py`, establishing the frozen `ECOv002-cal-val-JET-outputs.csv` verification check (`rtol=1e-4, atol=1e-7`) across 22 output variables.
- **Empirical Bias Calibration & Uncertainty Quantification (`2026-02-25` – `2026-02-27`):**
  - Added `statsmodels` dependency and implemented empirical OLS error-correction functions (`calibrate_Ta_C.py`, `calibrate_RH.py`, `calibrate_SM.py`) and $\pm 1\sigma$ UQ generators (`generate_*_uncalibrated_UQ.py`, `generate_*_calibrated_UQ.py`) wired via opt-in `use_calibration: bool = False` and `generate_UQ: bool = False` flags.
- **Spatial Downscaling Migration & `v3.1.0` Release (`2026-03-27` – `2026-04-28`):**
  - Added `scikit-learn` dependency and migrated `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` into `JET3`, gated to execute only when both `Ta_C is None` and `RH is None`.
- **Sensitivity Analysis & Notebook Tooling (`2026-07-15` – `2026-11-19`):**
  - Added `ECOv002-calval-tables>=1.13.0`, `SALib`, and `notebooks/render_notebooks.py` for Sobol sensitivity, Shapley attribution, Cal-Val benchmarking, and headless WebPDF rendering.
- **`v3.2.0` (2026-11-20) — `GEOS5FP >=2.24.0` Alignment & Resolution of Issues `#14`–`#21`:**
  - Following the November 2, 2026 decommissioning of Suomi NPP VIIRS (`VNP43NRT`) and the JPSS (`VCD43NRT`) stack rebuild, resolved all eight tracked bugs and contract mismatches (`#14`–`#21`) and added `tests/test_regressions.py`:
    - **#14:** Gated `ET_daylight_AquaSEBS_kg` overlay on `water_mask is not None` (`water_mask & ~np.isnan(...)`).
    - **#15:** Added conditional column extraction in `process_JET_table.py` supporting the `'Ta'` alias and missing optional/online columns (`Tmin_C`, `RH`, `SM`).
    - **#16:** Fixed the duplicate `BlankOutput` check in `JET.py` to inspect `ET_daylight_PTJPLSM_kg`.
    - **#17:** Updated stale `ECOv003_L3T_L4T_JET` package resource and metadata references in `JET3/Ta_C_error_OLS.py` and `pyproject.toml` to `JET3`.
    - **#18:** Removed duplicate definitions of `SHARPEN_METEOROLOGY` and `GEOS_IN_SENTINEL_COARSE_CELL_SIZE` in `JET3/constants.py`.
    - **#19:** Replaced deprecated `GEOS5FP_connection.wind_speed()` with `wind_speed_mps()` in `JET3/JET.py`.
    - **#20:** Replaced deprecated `GEOS5FP_connection.Td_C()` with `Td_K() - 273.15` in `JET3/sharpen_meteorology_data.py`.
    - **#21:** Replaced nonexistent `GEOS5FP_connection.elevation()` with `hasattr` checks and `NASADEM` fallback (`NASADEM>=2.2.1`) in `JET3/JET.py`.

---

### 2.3. Milestone Summary Table (`v1.0.1` – `v3.3.0`)

| Date | `JET3` Version | `ECOv003-L3T-L4T-JET` | Key Constituent Model / Infra Versions | Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **2025-05-21** | *(inline in PGE)* | `v1.0.1` | `BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `PTJPLSM>=1.2.0`, `STIC-JPL`, `FLiESANN`, `verma-net-radiation` | Initial Collection 3 port; unified `L3T ETAUX` product. |
| **2025-06-24** | *(inline in PGE)* | `v1.1.0` | `ECOv003-exit-codes` | Extracted `sharpen_meteorology_data` & `sharpen_soil_moisture_data`. |
| **2025-07-28** | *(inline in PGE)* | `v1.6.0` | `BESS-JPL>=1.15.0`, `PTJPLSM>=1.3.0`, `FLiESLUT>=1.0.3` | Wired `GEDI`, `MODISCI`, and `SoilGrids` auxiliary data directories. |
| **2025-10-01** | *(inline in PGE)* | `v1.10.0` | `AquaSEBS`, `ECOv002-granules~=1.2.1`, `ECOv003-granules~=1.10.0` | Integrated `AquaSEBS` open-water evaporation & dual-collection input. |
| **2025-11-12** | *(inline in PGE)* | `v1.11.0` | `AquaSEBS~=1.1.0`, `BESS-JPL~=1.20.0`, `FLiESANN~=2.1.0`, `PM-JPL~=1.7.0`, `PTJPLSM~=1.9.0`, `STIC-JPL~=1.4.0` | SI unit naming (`_Wm2`, `_deg`, `_m`), raw `FLiES-ANN` `Rg`, daylight upscaling. |
| **2025-11-18** | *(inline in PGE)* | `v1.13.0` | Container `v1.7.0` / `v1.7.1`, `L2T-STARS>=1.11.0` | Modularized `JET.py` & `process_JET_table.py`; introduced `verify.py`; entered C3 production. |
| **2026-01-30** | *(extracted)* | `v1.16.0` | `AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0` | Extracted `JET3` package; locked 11-month C3 reference baseline. |
| **2026-02-18** | `v3.0.0` / `v3.0.1` | `v1.16.0` | `verma-net-radiation~=1.11.0`, `SEBAL-soil-heat-flux` | Initial standalone `JET3` commit (`ed6a1ef0`) & release with `verify()`. |
| **2026-04-28** | `v3.1.0` | `v1.16.0` | `scikit-learn`, `statsmodels` | Added OLS calibration/UQ & migrated sharpening procedures into `JET3`. |
| **2026-11-02** | `v3.1.0` | `v1.18.0` | — | Suomi NPP VIIRS (`VNP43NRT`) decommissioned; JPSS transition begins. |
| **2026-11-19** | `v3.1.0` | `v1.22.0` | `GEOS5FP~=2.24.0`, `numpy~=2.5.4`, `pandas~=3.1.1`, `rasterio~=1.5.2` | Multi-stage Docker runtime, `argparse` CLI, and smoke tests. |
| **2026-11-20** | `v3.2.0` | `v1.22.1` | `GEOS5FP>=2.24.0`, `NASADEM>=2.2.1`, `gedi-canopy-height` | Resolved `JET3` issues `#14`–`#21` (`wind_speed_mps`, `Td_K`, `elevation_m`, `water_mask` gating, table aliases, package metadata). |
| **2026-11-23** | `v3.3.0` *(target)* | `v1.23.0` *(target)* | `GEOS5FP>=2.27.0` | Resolve `#23`: keep `BIAS_CORRECT_FLIES_ANN = False` default, add opt-in `bias_correct_FLiES_ANN`, pin `GEOS5FP>=2.27.0`, and add `vapor_gccm`/`ozone_cm` unit guards. |

---

## 3. Target Scope for `JET3 v3.3.0`: Solar Radiation Parity, Unit Guardrails, & Opt-In Bias Correction (`#23`)

### 3.1. Root-Cause Diagnosis (`orbit=44841`, `scene=001`, `tile=11SPS`, `2026-06-02T18:00:12Z`)

During end-to-end validation against public LP DAAC Collection 3 granules (`ECOv003_L3T_ETAUX_44841_001_11SPS_20260602T180012_0700_02.zip`), meteorological downscaling layers (`Ta`, `RH`, `SM`) matched the public granules (`r = 1.00000`), while incoming shortwave radiation (`Rg` / `SWin_Wm2`) exhibited a **`+74.35 W/m²` positive bias** (`1064.17 W/m²` local vs. `989.83 W/m²` public, $r = 0.38894$). Systematic hypothesis testing established:
1. **Enabling `bias_correct_FLiES_ANN=True` (`GEOS5FP.SWin` residual correction):** Shifted `Rg` from `1064.17 W/m²` to `752.58 W/m²` (`Bias = -237.25 W/m²`, $r = 0.0894$), confirming `BIAS_CORRECT_FLIES_ANN` must remain **`False`** by default in both `JET3` and `ECOv003-L3T-L4T-JET`.
2. **Disabling `ZERO_COT_CORRECTION`:** Produced identical results on this clear-sky tile (`COT = 0.0000`).
3. **Fixing `GEOS5FP` `vapor_gccm` (`TQV / 10.0` $\rightarrow \text{g cm}^{-2}$) & `ozone_cm` (`TO3 / 1000.0` $\rightarrow \text{cm}$) in `GEOS5FP v2.27.0`:**

| Metric (`L3T_ETAUX` `Rg`) | Broken `GEOS5FP v2.26.0` Units | Fixed `GEOS5FP v2.27.0` Units | Public Reference (`_02`) |
| :--- | ---: | ---: | ---: |
| **Min `Rg` ($\text{W m}^{-2}$)** | 1033.04 | **964.09** | 964.50 |
| **Mean `Rg` ($\text{W m}^{-2}$)** | 1064.17 | **989.80** | 989.83 |
| **Max `Rg` ($\text{W m}^{-2}$)** | 1078.78 | **1031.98** | 1032.79 |
| **Bias ($\text{W m}^{-2}$)** | +74.34881 | **-0.02331** | — |
| **RMSE ($\text{W m}^{-2}$)** | 74.75685 | **0.52714** | — |
| **Pearson $r$** | 0.38894 | **0.99859** | — |

---

### 3.2. `JET3 v3.3.0` Technical Deliverables

1. **Default Configuration (`JET3/constants.py`):**
   - Set `BIAS_CORRECT_FLIES_ANN = False` as the default so standalone `JET3` users, `JET3.verify()`, and `ECOv003-L3T-L4T-JET` retain exact parity with the Collection 3 baseline (`BuildID 0700`) and `ECOv002-cal-val-JET-outputs.csv` (`rtol=1e-4, atol=1e-7`).
2. **Opt-In Coarse-Scale Residual Bias Correction (`JET3/JET.py`, Issue `#23`):**
   - Expose `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` on `JET()`.
   - When `bias_correct_FLiES_ANN and processing_as_raster and not offline_mode` holds, retrieve coarse `GEOS5FP_connection.SWin()` on `coarse_geometry` ($13{,}720\text{ m}$), compute the coarse residual $E_c = SWin_{c,\mathrm{FLiES}} - SWin_{c,\mathrm{GEOS5FP}}$, interpolate $E_f$ to the fine grid (filling border `NaN`s outside coarse cell centers with `float(np.nanmean(SWin_bias_coarse))`), and apply $SWin_{f,\mathrm{corrected}} = \max(0, SWin_{f,\mathrm{raw}} - E_f)$.
3. **Physical Unit-Range Guardrails (`JET3/JET.py`):**
   - Emit `logger.warning` alerts immediately before `FLiESANN(...)` if `np.nanmean(vapor_gccm) > 15.0` (unscaled $\text{kg m}^{-2}$) or `np.nanmean(ozone_cm) > 5.0` (unscaled Dobson Units), preventing silent $10\times$ / $1000\times$ upstream unit regressions.
4. **Dependency Pinning & Documentation (`pyproject.toml`, `README.md`, `makefile`):**
   - Bump `version = "3.3.0"` and require `"GEOS5FP>=2.27.0"` in `pyproject.toml`.
   - Align `makefile` targets and formatting with `BESS-JPL` and document the `v3.3.0` release in `README.md`.
5. **Regression & Verification Suite (`tests/test_regressions.py`, `tests/test_verify.py`):**
   - `test_issue_23_bias_correct_flies_ann` verifies both `bias_correct_FLiES_ANN=False` (default, no `SWin` query) and `bias_correct_FLiES_ANN=True` (interpolated coarse bias subtracted and border pixels gap-filled).
   - `test_unscaled_vapor_and_ozone_unit_warnings` verifies warning logs when unscaled `vapor_gccm` or `ozone_cm` is supplied.
   - `make test` (`28 passed`) and `make verify` (`JET3.verify()`) pass with exit code `0`.

---

## 4. Release & Downstream Integration Checklist (`v3.3.0`)

- [x] **Step 1 — Patch `JET3` (`v3.3.0`):** Set `BIAS_CORRECT_FLIES_ANN = False` in `JET3/constants.py`, wire `bias_correct_FLiES_ANN` residual bias correction and `vapor_gccm`/`ozone_cm` unit warnings into `JET3/JET.py`, and pin `"GEOS5FP>=2.27.0"` in `pyproject.toml`.
- [x] **Step 2 — Validate Tests & Cal-Val Baseline:** Run `make test` (`28 passed`) and `make verify` (`JET3.verify()`).
- [ ] **Step 3 — Commit, Merge, Tag & Publish `JET3 v3.3.0`:**
  - Commit on `solar_radiation_bias_correction_option` (`Closes #23`), merge to `main`, tag `v3.3.0`, and push (`git push origin main --tags`) to publish `JET3==3.3.0` to PyPI.
- [ ] **Step 4 — Downstream Alignment (`ECOv003-L3T-L4T-JET v1.23.0` & Container Build):**
  - Confirm `BIAS_CORRECT_FLIES_ANN = False` and `ZERO_COT_CORRECTION = True` in `ECOv003_L3T_L4T_JET/constants.py`.
  - Pin `"GEOS5FP>=2.27.0"` and `"JET3~=3.3.0"` in `ECOv003-L3T-L4T-JET/pyproject.toml`.
  - Assert `BIAS_CORRECT_FLIES_ANN is False` and `GEOS5FPConnection` physical unit-range contracts (`vapor_gccm < 10.0`, `ozone_cm < 1.0`) in `smoke_test.py` and `tests/test_docker_smoke.py`.
  - Re-run `examples/example_L3T_L4T_JET_run_with_download.py` on `orbit=44841, scene=1, tile=11SPS` (`2026-06-02`) to confirm end-to-end `MATCH` across `L3T_ETAUX` (`Ta`, `RH`, `SM`, `Rg`, `Rn`), `L3T_JET`, `L4T_ESI`, and `L4T_WUE`, then rebuild `ecostress-level-2-3-4` and run `make docker-smoke-test`.
```[cite: 17, 18, 19, 20]