# `JET3` Repository History & Ecosystem Timeline (`May 2025 – November 2026`)

The history of **`JET3`** is directly tied to the evolution of **`ECOv003-L3T-L4T-JET`** (the ECOSTRESS Collection 3 Product Generating Executable) and the standalone science algorithm repositories under **`JPL-Evapotranspiration-Algorithms`**. Originally, the ensemble orchestration, spatial downscaling, and product I/O all lived together inside `ECOv003-L3T-L4T-JET` before the core science engine was extracted into `JET3` as a standalone, mission-independent library in early 2026.

---

## 1. Architectural Relationship Across Repositories

| Layer | Repository | Role & Responsibility |
| :--- | :--- | :--- |
| **Operational PGE Wrapper** | `ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET` | Parses XML RunConfigs, reads `L2T_LSTE` and `L2T_STARS` granules, invokes `JET3`, writes COG/JSON/GeoJPEG bundles (`L3T ETAUX`, `L3T JET`, `L4T ESI`, `L4T WUE`), and runs inside the `eco-level-2-3-4-application` Docker container. |
| **Core Ensemble & Downscaling Engine** | `JPL-Evapotranspiration-Algorithms/JET3` | Orchestrates meteorological/soil-moisture sharpening, bias calibration & uncertainty quantification (UQ), radiation transfer, and the 4-model terrestrial ET ensemble + open-water model; also provides tabular processing (`process_JET_table`) and numerical verification (`verify`). |
| **Radiative Transfer & Net Radiation** | `FLiESANN`, `verma-net-radiation`, `SEBAL-soil-heat-flux` | Computes TOA/surface shortwave radiation (`FLiESANN`), net radiation (`verma-net-radiation`), and soil heat flux (`SEBAL-soil-heat-flux`). |
| **Constituent ET & Water Models** | `PTJPLSM`, `STIC-JPL`, `PM-JPL`, `BESS-JPL`, `AquaSEBS` | Individual surface energy balance, GPP, and open-water evaporation models combined by `JET3`. |

---

## 2. Chronological Timeline (`May 2025 – November 2026`)

### Phase 1: Collection 2 Port & Modularization Inside `ECOv003-L3T-L4T-JET` (`May – September 2025`)

* **May 21, 2025 — `ECOv003-L3T-L4T-JET v1.0.1` (Initial Collection 3 Port):**
  * Ported the ECOSTRESS Collection 2 `ECOv002-L3T-L4T-JET` codebase to Collection 3.
  * Replaced inline legacy model code with standalone `JPL-Evapotranspiration-Algorithms` dependencies: `BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `STIC-JPL`, `PTJPLSM>=1.2.0`, `FLiESANN`, `FLiESLUT`, and `verma-net-radiation` (alongside `GEOS5FP`, `rasters>=1.5.0`, `ECOv002-granules>=1.1.1`, `ECOv003-granules>=1.3.0`, and `NASADEM>=1.2.0`).
  * Consolidated Collection 2's three separate auxiliary products (`L3T SEB`, `L3T SM`, `L3T MET`) into a single unified **`L3T ETAUX`** product (`Ta`, `RH`, `SM`, `Rg`, `Rn`) and added individual daily ET outputs alongside the ensemble daily median (`ETdaily`).
* **June 24, 2025 — `ECOv003-L3T-L4T-JET v1.1.0`:**
  * Extracted meteorological and soil-moisture regression downscaling out of the main PGE script into `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` (calling `GEOS5FP_connection.Td_C(...)`), and adopted `ECOv003-exit-codes`.
* **July 1 – July 30, 2025 — `ECOv003-L3T-L4T-JET v1.2.0` through `v1.6.6`:**
  * Wired auxiliary data directories and updated constituent model interfaces across rapid iterations:
    * `v1.2.0`–`v1.2.1` (Jul 1–3): Bumped `BESS-JPL>=1.12.0` (soil heat flux fix) and passed `GEOS5FP_connection` into `FLiESANN`.
    * `v1.4.0`–`v1.6.1` (Jul 3–28): Wired `GEDI` canopy height and `MODISCI` clumping index into `BESS-JPL>=1.13.0` → `>=1.15.0` (with `FLiESLUT>=1.0.3`), wired `SoilGrids` field capacity/wilting point and `GEDI` into `PTJPLSM>=1.3.0` → `>=1.5.3`, and updated `PM-JPL>=1.4.1` and `verma-net-radiation`.
    * `v1.6.5`–`v1.6.6` (Jul 30): Introduced upper version bounds (`BESS-JPL>=1.15.0,<1.16.0`, `GEOS5FP>=1.2.2,<1.3.0`, `rasters>=1.8.0,<1.9.0`, `verma-net-radiation>=1.3.0,<1.4.0`, `ECOv003-granules>=1.5.0,<1.6.0`) and passed `GEOS5FP_connection` into `PM-JPL>=1.4.1,<1.5.0`.
* **August 11 – September 12, 2025 — `ECOv003-L3T-L4T-JET v1.7.0` through `v1.9.0`:**
  * `v1.7.0` (Aug 11): Wrapped `sharpen_meteorology_data` and `sharpen_soil_moisture_data` in `try/except` fallback blocks so scenes with insufficient coarse pixels gracefully fall back to unsharpened `GEOS5FP` meteorology; updated pins (`FLiESANN>=1.6.0,<1.7.0`, `GEOS5FP>=1.2.3,<1.3.0`, `PTJPLSM>=1.7.0,<1.8.0`, `rasters>=1.9.0,<1.10.0`).
  * `v1.7.1`–`v1.9.0` (Aug 18 – Sep 12): Standardized on tilde (`~=`) pins (`BESS-JPL~=1.16.0` → `~=1.17.0`, `PM-JPL~=1.5.0`, `PTJPLSM~=1.8.0`, `ECOv003-granules~=1.6.0` → `~=1.8.0`) and masked sharpened meteorology rasters to valid ECOSTRESS LST swath pixels.

---

### Phase 2: Open-Water Evaporation, Daylight Standardization & C3 Baseline (`October – December 2025`)

* **October 1, 2025 — `ECOv003-L3T-L4T-JET v1.10.0`:**
  * Integrated **`AquaSEBS`** for open-water evaporation over SRTM/NASADEM water masks (introducing `GEOS5FP_connection.wind_speed(...)`), added dual `ECOv002` (`ECOv002-granules~=1.2.1`) and `ECOv003` (`ECOv003-granules~=1.10.0`) input support, and compiled the initial Collection 3 ATBD and User Guide.
* **November 12, 2025 — `ECOv003-L3T-L4T-JET v1.11.0`:**
  * Standardized internal variable names to explicit SI unit suffixes (`SZA_deg`, `elevation_m`, `SWin_Wm2`, `LE_*_Wm2`, `Rn_Wm2`) across bumped model releases (`AquaSEBS~=1.1.0`, `BESS-JPL~=1.20.0`, `FLiESANN~=2.1.0`, `GEOS5FP~=1.3.0`, `PM-JPL~=1.7.0`, `PTJPLSM~=1.9.0`, `STIC-JPL~=1.4.0`, `verma-net-radiation~=1.8.0`).
  * Switched to raw `FLiESANN~=2.1.0` solar radiation without GEOS-5 FP bias correction, enabled `upscale_to_daylight=True` across all four ET models, aligned `ETdaily` and `ETuncertainty` to daily units ($\text{mm day}^{-1}$), and added canopy/soil/interception partitioning layers.
* **November 18 – December 3, 2025 — `ECOv003-L3T-L4T-JET v1.13.0` & Production Container `v1.7.0` / `v1.7.1`:**
  * Decomposed the PGE into `read_ECOv003_configuration.py`, `read_ECOv003_inputs.py`, `JET.py`, `process_JET_table.py`, and `write_ECOv003_products.py`, bundling the ECOSTRESS Collection 2 Cal-Val reference dataset.
  * Deployed into the operational ECOSTRESS Science Data System (SDS) container (`eco-level-2-3-4-application` `v1.7.0` on Nov 20, `v1.7.1` on Dec 3), paired with `ECOv003-L2T-STARS>=1.11.0` ingesting Suomi NPP VIIRS (`VNP43NRT`).

---

### Phase 3: Extraction of Standalone `JET3` & Calibration/UQ Development (`January – August 2026`)

* **January 24 – January 30, 2026 — `ECOv003-L3T-L4T-JET v1.14.0` through `v1.16.0`:**
  * Extracted the core `JET` science function, `process_JET_table`, sharpening modules, and Cal-Val tables (`ECOv002-calval-tables~=1.13.0`) out of `ECOv003-L3T-L4T-JET` into the new standalone **`JET3`** package, leaving `ECOv003-L3T-L4T-JET` as a clean PGE wrapper.
  * Updated model dependencies for Collection 3 validation in `v1.16.0` (`AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0`, `verma-net-radiation~=1.11.0`), establishing the reference output baseline maintained across an 11-month uninterrupted forward-processing run.
* **February 18, 2026 — `JET3 v3.0.1` (Initial Standalone Release):**
  * Published the first standalone release of `JET3` (`v3.0.1`), containing the complete 4-model ensemble (`PTJPLSM`, `STIC_JPL`, `PMJPL`, `BESS_JPL`), `AquaSEBS` water-surface evaporation, `FLiESANN` + `verma_net_radiation` + `SEBAL_soil_heat_flux`, tabular processing (`process_JET_table`), and numerical verification (`verify()`).
* **February 25 – February 27, 2026 — Meteorology Calibration & UQ (`JET3` commits `d44f912` – `8a5aae1`):**
  * Added empirical OLS bias-correction functions (`calibrate_Ta_C`, `calibrate_RH`, `calibrate_SM`) and $\pm 1\sigma$ uncertainty quantification functions (`generate_*_uncalibrated_UQ` and `generate_*_calibrated_UQ`) supporting `Raster`, `np.ndarray`, and scalar inputs with `NaN` masking.
  * Refactored `JET()` to construct its output `results` dictionary incrementally and wired `use_calibration` and `generate_UQ` into both `JET()` and `process_JET_table()`.
* **March 27 – April 8, 2026 — Spatial Downscaling Migration into `JET3` (`JET3` commits `f489f68` – `2a8f060`):**
  * Migrated `sharpen_meteorology_data` and `sharpen_soil_moisture_data` into `JET3` (adding `scikit-learn`), simplified their signatures, and wired automatic raster sharpening into `JET()` (`sharpen_meteorology=True`, `sharpen_soil_moisture=True`).
* **April 28, 2026 — `JET3 v3.1.0`:**
  * Refined meteorology sharpening so it triggers only when both `Ta_C` and `RH` are `None` (falling back to single-variable GEOS-5 FP retrieval when only one is missing) and released **`JET3 v3.1.0`**.
* **April 29 – October 12, 2026 — `ECOv003-L3T-L4T-JET v1.17.0` through `v1.18.0` & `JET3` Sensitivity Analyses:**
  * While the `v1.7.1` production container ran continuously, `ECOv003-L3T-L4T-JET` separated PGE vs. SAS documentation and fixed `StandardMetadata/InputPointer` formatting (`v1.17.0`–`v1.18.0`).
  * In `JET3`, added `ECOv002-calval-tables>=1.13.0` (Jul 15) and `SALib` (Aug 9) to support Sobol global sensitivity, Shapley attribution, and Cal-Val benchmarking notebooks.

---

### Phase 4: JPSS Transition, Container Rebuild & `GEOS5FP` Contract Hardening (`November 2026`)

* **November 2, 2026 — Suomi NPP VIIRS Decommissioning:**
  * Upstream Suomi NPP VIIRS (`VNP43NRT`) coarse surface reflectance/albedo inputs terminated, halting `L2T_STARS` forward processing until cutover to JPSS (`VCD43NRT`).
* **November 11 – November 19, 2026 — `ECOv003-L3T-L4T-JET v1.19.0` through `v1.22.0` & Container `v1.9.0` – `v1.13.0`:**
  * Co-updated `ECOv003-L3T-L4T-JET` alongside `ECOv003-L2T-STARS` (`v1.14.0`–`v1.18.0`, Rust migration + JPSS `VCD43NRT`) on a unified Python 3.12 + `conda-forge` geospatial stack (`GEOS5FP~=2.24.0`, `numpy~=2.5.4`, `pandas~=3.1.1`, `rasterio~=1.5.2`, `scikit-learn~=1.9.1`, `onnxruntime~=1.31.1`).
  * In `v1.21.0`–`v1.22.0` (Nov 19), refactored the CLI to `argparse`, added `smoke_test.py` (`ECOv003-L3T-L4T-JET test`), added a multi-stage `Dockerfile` + `tests/test_docker_smoke.py`, and bumped `JET3~=3.0.1` → `JET3~=3.1.0`.
* **November 19 – November 20, 2026 — `JET3 v3.1.0` Audit, `ECOv003-L3T-L4T-JET v1.22.1` & `JET3` Issues `#14`–`#18`:**
  * **Nov 19:** Added `notebooks/render_notebooks.py` in `JET3` for automated notebook execution and PDF rendering.
  * **Nov 20:**
    * Diagnosed a runtime `AttributeError` in `JET3 v3.1.0` triggered when `ECOv003-L3T-L4T-JET v1.22.0` upgraded to `JET3~=3.1.0` alongside `GEOS5FP~=2.24.0`: `JET3/JET.py` eagerly called legacy `GEOS5FP_connection.wind_speed(...)` (renamed to `wind_speed_mps(...)` in `GEOS5FP>=2.24.0`), alongside latent `.elevation(...)` and `.Td_C(...)` (renamed to `Td_K(...)`) mismatches.
    * Updated **`ECOv003-L3T-L4T-JET v1.22.1`** (`pyproject.toml`) to require **`JET3~=3.1.1`** and expanded `smoke_test.py` and `test_docker_smoke.py` to enforce the `GEOS5FPConnection` SI method contract (`wind_speed_mps`, `Td_K`, `Ta_C`, `RH`, `SM`) ahead of building `eco-level-2-3-4-application v1.13.1`.
    * Audited `JET3 v3.1.0` and filed GitHub issues **`#14`–`#18`** on `JPL-Evapotranspiration-Algorithms/JET3` (tracking the `AquaSEBS` `water_mask` daylight ET overwrite, `process_JET_table` missing/alias columns, duplicate `BlankOutput` check, stale `ECOv003_L3T_L4T_JET` package references, and duplicate constants) in `notes/2026-11-20 JET3 Known Issues.md` ahead of the `JET3 v3.1.1` release.

---

## 3. Summary Milestone Table

| Date | `JET3` Version | `ECOv003-L3T-L4T-JET` | Key Constituent Model / Infra Versions | Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **2025-05-21** | *(inline in PGE)* | `v1.0.1` | `BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `PTJPLSM>=1.2.0`, `STIC-JPL`, `FLiESANN`, `verma-net-radiation` | Initial Collection 3 port; unified `L3T ETAUX` product. |
| **2025-06-24** | *(inline in PGE)* | `v1.1.0` | `ECOv003-exit-codes` | Extracted `sharpen_meteorology_data` & `sharpen_soil_moisture_data`. |
| **2025-07-28** | *(inline in PGE)* | `v1.6.0` | `BESS-JPL>=1.15.0`, `PTJPLSM>=1.3.0`, `FLiESLUT>=1.0.3` | Wired `GEDI`, `MODISCI`, and `SoilGrids` auxiliary data directories. |
| **2025-10-01** | *(inline in PGE)* | `v1.10.0` | `AquaSEBS`, `ECOv002-granules~=1.2.1`, `ECOv003-granules~=1.10.0` | Integrated `AquaSEBS` open-water evaporation & dual-collection input. |
| **2025-11-12** | *(inline in PGE)* | `v1.11.0` | `AquaSEBS~=1.1.0`, `BESS-JPL~=1.20.0`, `FLiESANN~=2.1.0`, `PM-JPL~=1.7.0`, `PTJPLSM~=1.9.0`, `STIC-JPL~=1.4.0` | SI unit naming (`_Wm2`, `_deg`, `_m`), daylight upscaling, ET partitioning. |
| **2025-11-18** | *(inline in PGE)* | `v1.13.0` | Container `v1.7.0` / `v1.7.1`, `L2T-STARS>=1.11.0` | Modularized `JET.py` & `process_JET_table.py`; entered C3 production. |
| **2026-01-30** | *(extracted)* | `v1.16.0` | `AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0` | Extracted `JET3` package; locked 11-month C3 reference baseline. |
| **2026-02-18** | `v3.0.1` | `v1.16.0` | `verma-net-radiation~=1.11.0`, `SEBAL-soil-heat-flux` | First standalone `JET3` release on GitHub/PyPI. |
| **2026-04-28** | `v3.1.0` | `v1.16.0` | `scikit-learn`, `statsmodels` | Added OLS calibration/UQ & migrated sharpening procedures into `JET3`. |
| **2026-11-02** | `v3.1.0` | `v1.18.0` | — | Suomi NPP VIIRS (`VNP43NRT`) decommissioned; JPSS transition begins. |
| **2026-11-19** | `v3.1.0` | `v1.22.0` | `GEOS5FP~=2.24.0`, `numpy~=2.5.4`, `pandas~=3.1.1`, `rasterio~=1.5.2` | Multi-stage Docker runtime, `argparse` CLI, and smoke tests. |
| **2026-11-20** | `v3.1.0` → `v3.1.1` *(planned)* | `v1.22.1` | `JET3~=3.1.1`, `GEOS5FP~=2.24.0` | Diagnosed `GEOS5FP` API mismatch (`wind_speed_mps`, `Td_K`); filed `JET3` issues `#14`–`#18`. |