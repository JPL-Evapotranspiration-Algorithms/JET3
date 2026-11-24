# `JET3` Integrated Development Plan (`v1.0.1` → `v3.3.0`)

- **Date:** November 23, 2026
- **Current Release:** `v3.2.0`
- **Target Release:** `v3.3.0` (implementing opt-in GEOS-5 FP residual bias correction for `FLiES-ANN` solar radiation `SWin_Wm2` / `Rg` and aligning with `ECOv003-L3T-L4T-JET >=1.23.0`)
- **Primary Objective:** Consolidate the complete engineering lineage of `JET3` across all releases (`v1.0.1`–`v3.2.0`) and define the verified specification for `v3.3.0` to restore operational ECOSTRESS Collection 3 `L3T_ETAUX` `Rg` parity while preserving strict numerical equivalence with the `ECOv002` Cal-Val baseline (`JET3.verify()`).

---

## 1. Executive Summary & Architectural Context

`JET3` (`JPL-Evapotranspiration-Algorithms/JET3`) is the standalone, mission-independent science engine underlying the ECOSTRESS Collection 3 Level-3/4 Evapotranspiration Product Generating Executable (`ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET`) and the Surface Biology and Geology (`SBG-TIR-L4-JET`) pipeline[cite: 7, 9].

| Layer | Repository | Role & Responsibility |
| :--- | :--- | :--- |
| **Operational PGE Wrapper** | `ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET` | Parses XML RunConfigs, reads `L2T_LSTE` and `L2T_STARS` granules, invokes `JET3`, writes COG/JSON/GeoJPEG bundles (`L3T ETAUX`, `L3T JET`, `L4T ESI`, `L4T WUE`), and runs inside the `eco-level-2-3-4-application` Docker container. |
| **Core Ensemble & Downscaling Engine** | `JPL-Evapotranspiration-Algorithms/JET3` | Orchestrates meteorological/soil-moisture sharpening, bias calibration & uncertainty quantification (UQ), radiative transfer, and the 4-model terrestrial ET ensemble + open-water model; also provides tabular processing (`process_JET_table`) and numerical verification (`verify`). |
| **Radiative Transfer & Net Radiation** | `FLiESANN`, `verma-net-radiation`, `SEBAL-soil-heat-flux` | Computes TOA/surface shortwave radiation (`FLiESANN`), net radiation (`verma-net-radiation`), and soil heat flux (`SEBAL-soil-heat-flux`). |
| **Constituent ET & Water Models** | `PTJPLSM`, `STIC-JPL`, `PM-JPL`, `BESS-JPL`, `AquaSEBS` | Individual surface energy balance, GPP, and open-water evaporation models combined by `JET3`.[cite: 9] |

Because `JET3` was extracted as its own package in **February 2026**—roughly three months *after* ECOSTRESS Collection 3 entered operational forward processing (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`, paired with `ECOv003-L3T-L4T-JET` `v1.13.0`–`v1.16.0`)—all development is governed by two core invariants:
1. **Standalone Collection 3 Cal-Val Baseline Consistency:** Default standalone execution (`use_calibration=False`, `generate_UQ=False`, `bias_correct_FLiES_ANN=False`) must produce outputs matching the frozen `ECOv002-cal-val-JET-outputs.csv` reference baseline (`rtol=1e-4, atol=1e-7`) enforced by `JET3.verify()`.
2. **Operational PGE Parity & Cross-Stack Contract Alignment:** `JET3` must maintain full API compatibility with `GEOS5FP >=2.24.0` (`wind_speed_mps`, `Td_K`) and expose opt-in scene-level corrections (`bias_correct_FLiES_ANN`) required by `ECOv003-L3T-L4T-JET` to match public LP DAAC Collection 3 products[cite: 7, 10].

---

## 2. Completed Development & Release History (`May 2025 – November 2026`)

### 2.1. Pre-Extraction Lineage Inside `ECOv003-L3T-L4T-JET` (`v1.0.1` – `v1.16.0`, May 2025 – January 2026)

Before `JET3` existed as a separate repository, its ensemble orchestration, spatial downscaling, and verification suite were built and validated inside `ECOv003-L3T-L4T-JET`[cite: 7, 9]:

- **`v1.0.1` (2025-05-21) — Initial Collection 3 Port:**
  - Ported `ECOv002-L3T-L4T-JET` to Collection 3 and replaced inline legacy model implementations with standalone `JPL-Evapotranspiration-Algorithms` packages (`BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `STIC-JPL`, `PTJPLSM>=1.2.0`, `FLiESANN`, `FLiESLUT`, `verma-net-radiation`, `NASADEM>=1.2.0`).
  - Consolidated three Collection 2 auxiliary products (`L3T SEB`, `L3T SM`, `L3T MET`) into a unified **`L3T ETAUX`** product (`Ta`, `RH`, `SM`, `Rg`, `Rn`) and added per-model daily ET layers alongside the ensemble daily median (`ETdaily`).
- **`v1.1.0` – `v1.9.0` (2025-06-24 to 2025-09-12) — Downscaling Modularization & Auxiliary Data Wiring:**
  - Extracted `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` (`v1.1.0`) and adopted `ECOv003-exit-codes`.
  - Wired `GEDI` canopy height, `MODISCI` clumping index, and `SoilGrids` field capacity/wilting point directories into `BESS-JPL` and `PTJPLSM` (`v1.4.0`–`v1.6.6`).
  - Wrapped spatial downscaling calls in `try/except` fallback blocks (`v1.7.0`), standardized on tilde (`~=`) dependency pins, and masked sharpened meteorology rasters to valid ECOSTRESS LST swath pixels (`v1.7.1`–`v1.9.0`).
- **`v1.10.0` – `v1.11.0` (2025-10-01 to 2025-11-12) — Open-Water Evaporation & SI/Daylight Standardization:**
  - Integrated **`AquaSEBS`** for open-water evaporation over SRTM/NASADEM water masks and added dual `ECOv002`/`ECOv003` granule support (`v1.10.0`).
  - Standardized internal variable names to explicit SI unit suffixes (`SZA_deg`, `elevation_m`, `SWin_Wm2`, `LE_*_Wm2`, `Rn_Wm2`), enabled `upscale_to_daylight=True` across all four ET models, aligned `ETdaily` and `ETuncertainty` to $\text{mm day}^{-1}$, and added canopy/soil/interception partitioning layers (`v1.11.0`).
- **`v1.13.0` – `v1.16.0` (2025-11-18 to 2026-01-30) — Pipeline Modularization, `verify.py`, & C3 Deployment:**
  - Decomposed the PGE into `JET.py`, `process_JET_table.py`, and `verify.py` (bundled with `ECOv002-cal-val-JET-inputs.csv` and `ECOv002-cal-val-JET-outputs.csv`), entering operational forward processing on November 20, 2025 (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`) paired with `ECOv003-L2T-STARS>=1.11.0` ingesting Suomi NPP VIIRS (`VNP43NRT`).
  - Locked the Collection 3 validation baseline in `v1.16.0` (`AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0`, `verma-net-radiation~=1.11.0`) and extracted the core science engine into standalone `JET3`[cite: 9].

---

### 2.2. Standalone `JET3` Release History (`v3.0.0` – `v3.2.0`, February – November 2026)

- **`v3.0.0` & `v3.0.1` (2026-02-18) — Initial Standalone Repository & Verification Suite:**
  - **Root Commit (`ed6a1ef0`, `v3.0.0`):** Created `JET3` containing `JET.py`, `process_JET_table.py`, `constants.py`, `exceptions.py`, `Ta_C_error_OLS.py`, `ECOv002_calval_JET_inputs.py`, `ECOv002_calval_JET_outputs.py`, and `verify.py` + `tests/test_verify.py`.
  - **Patch Release (`v3.0.1`):** Fixed `tests/test_verify.py` imports, exported `verify`, `load_ECOv002_calval_JET_inputs`, `load_ECOv002_calval_JET_outputs`, and `Ta_C_error_OLS` in `JET3/JET3.py`, and established the frozen `ECOv002-cal-val-JET-outputs.csv` verification check (`rtol=1e-4, atol=1e-7`) across 22 output variables.
- **Empirical Bias Calibration & Uncertainty Quantification (`2026-02-25` – `2026-02-27`):**
  - Added `statsmodels` dependency and implemented empirical OLS error-correction functions (`calibrate_Ta_C.py`, `calibrate_RH.py`, `calibrate_SM.py`) and $\pm 1\sigma$ UQ generators (`generate_*_uncalibrated_UQ.py`, `generate_*_calibrated_UQ.py`) supporting scalars, NumPy arrays, and `rasters.Raster` geometries with `NaN` masking.
  - Wired opt-in `use_calibration: bool = False` and `generate_UQ: bool = False` flags into `JET()` and `process_JET_table()`, and refactored `JET()` to build its `results` dictionary incrementally across workflow stages.
- **Spatial Downscaling Migration & `v3.1.0` Release (`2026-03-27` – `2026-04-28`):**
  - Added `scikit-learn` dependency and migrated `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` from `ECOv003-L3T-L4T-JET` into `JET3`, controlled by `sharpen_meteorology: bool = SHARPEN_METEOROLOGY` and `sharpen_soil_moisture: bool = SHARPEN_SOIL_MOISTURE` in `JET()`.
  - Gated meteorology sharpening to execute only when *both* `Ta_C is None` and `RH is None` (falling back to single-variable `GEOS5FP` retrieval when only one is missing) and released **`v3.1.0`**.
- **Sensitivity Analysis & Notebook Tooling (`2026-07-15` – `2026-11-19`):**
  - Added `ECOv002-calval-tables>=1.13.0` (`2026-07-15`) and `SALib` (`2026-08-09`) to support Sobol global sensitivity, Shapley attribution, and Cal/Val benchmarking notebooks.
  - Added `notebooks/render_notebooks.py` (`2026-11-19`) for automated headless notebook execution and WebPDF rendering[cite: 7, 9].
- **`v3.2.0` (2026-11-20) — `GEOS5FP >=2.24.0` Alignment & Resolution of Issues `#14`–`#21`:**
  - Following the November 2, 2026 decommissioning of Suomi NPP VIIRS (`VNP43NRT`) and the coordinated rebuild around Python 3.12+, JPSS (`VCD43NRT`), and `GEOS5FP >=2.24.0`, resolved all eight tracked bugs and contract mismatches (`#14`–`#21`) and added `tests/test_regressions.py`:
    - **#14:** Gated `ET_daylight_AquaSEBS_kg` overlay on `water_mask is not None` (`water_mask & ~np.isnan(...)`) so land pixels and unmasked tables are never overwritten by open-water evaporation.
    - **#15:** Replaced unconditional attribute lookups in `process_JET_table.py` with conditional lookups supporting the `'Ta'` column alias and missing optional/online columns (`Tmin_C`, `RH`, `SM`).
    - **#16:** Fixed the duplicate `BlankOutput` check in `JET.py` to validate `ET_daylight_PTJPLSM_kg` rather than checking `LE_PTJPLSM_Wm2` twice.
    - **#17:** Updated stale `ECOv003_L3T_L4T_JET` package resource and metadata references in `JET3/Ta_C_error_OLS.py` and `pyproject.toml` to `JET3`.
    - **#18:** Removed duplicate definitions of `SHARPEN_METEOROLOGY` and `GEOS_IN_SENTINEL_COARSE_CELL_SIZE` in `JET3/constants.py`.
    - **#19:** Replaced deprecated `GEOS5FP_connection.wind_speed()` with `wind_speed_mps()` in `JET3/JET.py` and pinned `GEOS5FP>=2.24.0` in `pyproject.toml`.
    - **#20:** Replaced deprecated `GEOS5FP_connection.Td_C()` with `Td_K() - 273.15` in `JET3/sharpen_meteorology_data.py`, eliminating silent fallback to coarse GEOS-5 FP meteorology.
    - **#21:** Replaced nonexistent `GEOS5FP_connection.elevation()` with `hasattr` checks and `NASADEM` fallback (`NASADEM>=2.2.1`) in `JET3/JET.py`[cite: 7, 8, 9].

---

### 2.3. Milestone Summary Table (`v1.0.1` – `v3.3.0`)

| Date | `JET3` Version | `ECOv003-L3T-L4T-JET` | Key Constituent Model / Infra Versions | Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **2025-05-21** | *(inline in PGE)* | `v1.0.1` | `BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `PTJPLSM>=1.2.0`, `STIC-JPL`, `FLiESANN`, `verma-net-radiation` | Initial Collection 3 port; unified `L3T ETAUX` product. |
| **2025-06-24** | *(inline in PGE)* | `v1.1.0` | `ECOv003-exit-codes` | Extracted `sharpen_meteorology_data` & `sharpen_soil_moisture_data`. |
| **2025-07-28** | *(inline in PGE)* | `v1.6.0` | `BESS-JPL>=1.15.0`, `PTJPLSM>=1.3.0`, `FLiESLUT>=1.0.3` | Wired `GEDI`, `MODISCI`, and `SoilGrids` auxiliary data directories. |
| **2025-10-01** | *(inline in PGE)* | `v1.10.0` | `AquaSEBS`, `ECOv002-granules~=1.2.1`, `ECOv003-granules~=1.10.0` | Integrated `AquaSEBS` open-water evaporation & dual-collection input. |
| **2025-11-12** | *(inline in PGE)* | `v1.11.0` | `AquaSEBS~=1.1.0`, `BESS-JPL~=1.20.0`, `FLiESANN~=2.1.0`, `PM-JPL~=1.7.0`, `PTJPLSM~=1.9.0`, `STIC-JPL~=1.4.0` | SI unit naming (`_Wm2`, `_deg`, `_m`), daylight upscaling, ET partitioning. |
| **2025-11-18** | *(inline in PGE)* | `v1.13.0` | Container `v1.7.0` / `v1.7.1`, `L2T-STARS>=1.11.0` | Modularized `JET.py` & `process_JET_table.py`; introduced `verify.py`; entered C3 production. |
| **2026-01-30** | *(extracted)* | `v1.16.0` | `AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0` | Extracted `JET3` package; locked 11-month C3 reference baseline. |
| **2026-02-18** | `v3.0.0` / `v3.0.1` | `v1.16.0` | `verma-net-radiation~=1.11.0`, `SEBAL-soil-heat-flux` | Initial standalone `JET3` commit (`ed6a1ef0`) & release with `verify()`. |
| **2026-04-28** | `v3.1.0` | `v1.16.0` | `scikit-learn`, `statsmodels` | Added OLS calibration/UQ & migrated sharpening procedures into `JET3`. |
| **2026-11-02** | `v3.1.0` | `v1.18.0` | — | Suomi NPP VIIRS (`VNP43NRT`) decommissioned; JPSS transition begins. |
| **2026-11-19** | `v3.1.0` | `v1.22.0` | `GEOS5FP~=2.24.0`, `numpy~=2.5.4`, `pandas~=3.1.1`, `rasterio~=1.5.2` | Multi-stage Docker runtime, `argparse` CLI, and smoke tests. |
| **2026-11-20** | `v3.2.0` | `v1.22.1` | `GEOS5FP>=2.24.0`, `NASADEM>=2.2.1`, `gedi-canopy-height` | Resolved `JET3` issues `#14`–`#21` (`wind_speed_mps`, `Td_K`, `elevation_m`, `water_mask` gating, table aliases, package metadata). |
| **2026-11-23** | `v3.3.0` *(planned)* | `v1.23.0` *(planned)* | `GEOS5FP>=2.24.0` | Add opt-in `bias_correct_FLiES_ANN` residual bias correction against GEOS-5 FP `SWin` (`Rg`).[cite: 9, 10] |

---

## 3. Target Scope for `JET3 v3.3.0`: Optional GEOS-5 FP Bias Correction for `FLiES-ANN` Solar Radiation (`SWin_Wm2` / `Rg`)

### 3.1. Problem Statement & Empirical Diagnosis

End-to-end reproduction testing of public ECOSTRESS Collection 3 Level-3 and Level-4 products (`L3T_ETAUX`, `L3T_JET`, `L4T_ESI`, and `L4T_WUE` for orbit `44841`, scene `1`, tile `11SPS`, `2026-06-02T18:00:12Z`) using `ECOv003-L3T-L4T-JET v1.23.0` and `JET3 v3.2.0` confirmed exact parity across meteorological downscaling (`Ta`, `SM`, `RH`) and quality masks (`cloud`, `water`) with identical GEOS-5 FP forcing (`AuxiliaryNWP match : True`), while incoming shortwave solar radiation (`Rg` / `SWin_Wm2`) exhibited a **`+74.35 W/m²` positive bias** and degraded spatial correlation (**`r = 0.38894`**) relative to public LP DAAC Collection 3 products (`BuildID` `0700`, revision `02`)[cite: 10]:

| Layer (`L3T_ETAUX`) | Status | RMSE | MAE | Bias (Local − Public) | MaxDiff | Pearson $r$ |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `Ta` | `MATCH` | `0.00000` | `0.00000` | `-0.00000` | `0.00001` | `1.00000` |
| `SM` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` |
| `RH` | `DIFF` | `0.00008` | `0.00008` | `-0.00008` | `0.00018` | `1.00000` |
| `cloud` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` |
| `water` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` |
| **`Rg`** | **`DIFF`** | **`74.75685`** | **`74.34881`** | **`+74.34881`** | **`101.00201`** | **`0.38894`** |
| `Rn` | `DIFF` | `59.23247` | `58.37636` | `+58.37636` | `100.08569` | `0.99851`[cite: 10] |

**Root Cause:**
1. `JET3/constants.py` defined `BIAS_CORRECT_FLIES_ANN = True`, but `JET3/JET.py` never wired that flag into `JET()` and unconditionally set `SWin_Wm2 = SWin_FLiES_ANN_raw`.
2. Because `ZERO_COT_CORRECTION = True` zeroes out coarse Cloud Optical Thickness (`COT = 0.0`) prior to radiative transfer, raw `FLiES-ANN` `SWin` is driven primarily by clear-sky solar zenith angle (`SZA_deg`) and surface albedo, missing sub-grid and synoptic cloud/aerosol attenuation captured in GEOS-5 FP `tavg1_2d_rad_Nx` (`SWGDN` / `SWin`).
3. Because `AuxiliaryNWP` already includes `GEOS.fp.asm.tavg1_2d_rad_Nx` (fetched for `COT`, `PAR_albedo`, and `NIR_albedo`), querying `GEOS5FP_connection.SWin(...)` reads cached local NetCDF4 files without additional downloads or changes to `AuxiliaryNWP`[cite: 10].

---

### 3.2. Technical Specification (`v3.3.0`)

#### Workstream A: `JET3` Opt-In `FLiES-ANN` Bias Correction (`JET3/constants.py`, `JET3/JET.py`)

1. **Default Flag (`JET3/constants.py`):**
   - Set `BIAS_CORRECT_FLIES_ANN = False` inside `JET3/constants.py` so standalone `JET3` users and `JET3.verify()` retain exact numerical compatibility with the frozen `ECOv002-cal-val-JET-outputs.csv` baseline (`rtol=1e-4, atol=1e-7`)[cite: 10].
2. **Function Signature (`JET3/JET.py`):**
   - Add `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` to `JET()`[cite: 10].
3. **Coarse-Scale Residual Bias Correction (`JET3/JET.py`):**
   - Execute only when `bias_correct_FLiES_ANN and processing_as_raster and not offline_mode` holds (leaving `offline_mode=True` and point-table runs untouched), applying the same two-stage spatial residual adjustment used by `sharpen_meteorology_data()` and `sharpen_soil_moisture_data()`:
     1. Reuse or compute `coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)` ($13{,}720\text{ m}$).
     2. Retrieve coarse GEOS-5 FP solar radiation:
        $$SWin_{c,\mathrm{GEOS5FP}} = \mathrm{GEOS5FP\_connection.SWin}(\text{time\_UTC}, \text{geometry}=\text{coarse\_geometry}, \text{resampling}=\text{downsampling})$$
     3. Aggregate fine `FLiES-ANN` output to the coarse grid:
        $$SWin_{c,\mathrm{FLiES}} = SWin_{f,\mathrm{raw}}.\mathrm{to\_geometry}(\text{coarse\_geometry}, \text{resampling}=\text{upsampling})$$
     4. Compute coarse residual bias and interpolate to the fine grid:
        $$E_c = SWin_{c,\mathrm{FLiES}} - SWin_{c,\mathrm{GEOS5FP}}, \qquad E_f = E_c.\mathrm{to\_geometry}(\text{geometry}, \text{resampling}=\text{downsampling})$$
     5. Apply additive residual correction with non-negative clipping:
        $$SWin_{f,\mathrm{corrected}} = \max\!\left(0,\; SWin_{f,\mathrm{raw}} - E_f\right)$$[cite: 10]

#### Workstream B: Regression & Baseline Verification (`tests/test_regressions.py`, `tests/test_verify.py`)

4. **Unit Tests (`tests/test_regressions.py`):**
   - Add `test_bias_correct_flies_ann` verifying:
     - Default `JET()` (`bias_correct_FLiES_ANN=False`) leaves `SWin_Wm2` equal to `SWin_FLiES_ANN_raw` without invoking `GEOS5FP_connection.SWin`.
     - `JET(..., bias_correct_FLiES_ANN=True)` on a `Raster` geometry invokes `GEOS5FP_connection.SWin`, subtracts the interpolated coarse bias, and clips negative values to `0.0`[cite: 10].
5. **Cal-Val Baseline Verification (`tests/test_verify.py`):**
   - Confirm `JET3.verify()` passes with zero drift across all 22 reference columns[cite: 10].

#### Workstream C: Downstream Operational Enablement (`ECOv003-L3T-L4T-JET v1.23.0`)

6. **Enable by Default in `ECOv003-L3T-L4T-JET`:**
   - Pin `"JET3~=3.3.0"` in `ECOv003-L3T-L4T-JET/pyproject.toml`.
   - Set `BIAS_CORRECT_FLIES_ANN = True` in `ECOv003_L3T_L4T_JET/constants.py`.
   - Expose `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` in `L3T_L4T_JET()` (`ECOv003_L3T_L4T_JET/ECOv003_L3T_L4T_JET.py`) and forward `bias_correct_FLiES_ANN=bias_correct_FLiES_ANN` into `JET(...)`[cite: 10].

---

## 4. Execution & Release Checklist (`v3.3.0`)

- [ ] **Step 1 — Patch `JET3`:** Update `BIAS_CORRECT_FLIES_ANN = False` in `JET3/constants.py` and wire `bias_correct_FLiES_ANN` residual bias correction into `JET3/JET.py`.
- [ ] **Step 2 — Add Regression Tests:** Add `test_bias_correct_flies_ann` to `tests/test_regressions.py` and run `make test`.
- [ ] **Step 3 — Validate Cal-Val Baseline:** Run `make verify` (`JET3.verify()`) to confirm exact numerical equivalence against `ECOv002-cal-val-JET-outputs.csv`.
- [ ] **Step 4 — Release `JET3 v3.3.0`:** Bump `version = "3.3.0"` in `pyproject.toml`, commit, tag `v3.3.0`, and publish to PyPI.
- [ ] **Step 5 — Downstream Integration & LP DAAC Parity Validation:**
  - Update `ECOv003-L3T-L4T-JET` (`pyproject.toml`, `constants.py`, `ECOv003_L3T_L4T_JET.py`) to enable `BIAS_CORRECT_FLIES_ANN = True` with `JET3~=3.3.0`.
  - Re-run `orbit=44841, scene=1, tile=11SPS` (`2026-06-02`) and confirm `L3T_ETAUX` `Rg` converges from `+74.35 W/m²` bias (`r = 0.38894`) to `MATCH` (`r ≈ 1.00000`) alongside `Rn`, `PET`, `L3T_JET`, `L4T_ESI`, and `L4T_WUE`[cite: 10].