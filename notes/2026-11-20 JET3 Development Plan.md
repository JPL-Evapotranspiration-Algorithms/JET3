# `JET3` Integrated Development Plan (`v3.0.0` → `v3.2.0`)

- **Date:** November 20, 2026
- **Current Release:** `v3.1.0`
- **Target Release:** `v3.2.0` (resolving GitHub Issues `#14`–`#21` and aligning with `GEOS5FP >=2.24.0` and `ECOv003-L3T-L4T-JET >=1.22.1`)
- **Primary Objective:** Document the complete chronological engineering lineage of `JET3` and execute a verified, output-consistent remediation plan for all known issues while maintaining strict numerical equivalence with the ECOSTRESS Collection 3 forward-processing baseline.

---

## 1. Executive Summary & Architectural Context

`JET3` (`JPL-Evapotranspiration-Algorithms/JET3`) is the standalone, mission-independent science engine underlying the ECOSTRESS Collection 3 Level-3/4 Evapotranspiration Product Generating Executable (`ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET`) and the Surface Biology and Geology (`SBG-TIR-L4-JET`) pipeline.

Because `JET3` was extracted as its own package in **February 2026**—roughly three months *after* ECOSTRESS Collection 3 entered operational forward processing (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`, paired with `ECOv003-L3T-L4T-JET` `v1.13.0`–`v1.16.0`)—all ongoing development is governed by two core invariants:
1. **Collection 3 Baseline Output Consistency:** Default execution (`use_calibration=False`, `generate_UQ=False`) must produce scientifically consistent outputs matching the late-2025 Collection 3 baseline, enforced via the built-in `JET3.verify()` numerical tolerance suite (`rtol=1e-4, atol=1e-7`).
2. **Cross-Stack Contract Alignment (`GEOS5FP >=2.24.0` & JPSS Transition):** Following the November 2, 2026 decommissioning of Suomi NPP VIIRS (`VNP43NRT`) and the coordinated rebuild around Python 3.12+, `GEOS5FP >=2.24.0`, and JPSS (`VCD43NRT`), `JET3` must resolve all legacy `GEOS5FPConnection` method incompatibilities (`wind_speed_mps`, `Td_K`, `elevation`) and open defects (`#14`–`#21`) before advancing the downstream container stack (`ecostress-level-2-3-4`).

---

## 2. Past Development & Release History (`May 2025 – November 2026`)

### 2.1. Pre-Extraction Lineage Inside `ECOv003-L3T-L4T-JET` (`v1.0.1` – `v1.16.0`, May 2025 – January 2026)

Before `JET3` existed as a separate repository, its ensemble orchestration, spatial downscaling, and verification suite were built and validated inside `ECOv003-L3T-L4T-JET`:

- **`v1.0.1` (2025-05-21) — Initial Collection 3 Port:**
  - Duplicated `ECOv002-L3T-L4T-JET` and replaced inline model implementations with standalone `JPL-Evapotranspiration-Algorithms` packages (`BESS-JPL>=1.9.2`, `PM-JPL>=1.4.0`, `STIC-JPL`, `PTJPLSM>=1.2.0`, `FLiESANN`, `FLiESLUT`, `verma-net-radiation`, `NASADEM>=1.2.0`).
  - Consolidated three separate Collection 2 auxiliary products (`L3T SEB`, `L3T SM`, `L3T MET`) into `L3T ETAUX` (`Ta`, `RH`, `SM`, `Rg`, `Rn`) and added per-model daily ET layers alongside the ensemble median (`ETdaily`).
- **`v1.1.0` – `v1.9.0` (2025-06-24 to 2025-09-12) — Downscaling Modularization & Auxiliary Data Wiring:**
  - Extracted `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` (`v1.1.0`), wired local `GEDI`, `MODISCI`, and `SoilGrids` directories (`v1.4.0`–`v1.6.0`), and wrapped spatial downscaling calls in `try/except` fallback blocks (`v1.7.0`).
- **`v1.10.0` – `v1.11.0` (2025-10-01 to 2025-11-12) — Open-Water Evaporation & SI/Daylight Standardization:**
  - Integrated `AquaSEBS` over SRTM/NASADEM water masks (`v1.10.0`).
  - Standardized internal variable names to explicit SI unit suffixes (`SZA_deg`, `elevation_m`, `SWin_Wm2`, `LE_*_Wm2`, `Rn_Wm2`), switched to raw `FLiESANN~=2.1.0` solar radiation without GEOS-5 FP bias correction, enabled `upscale_to_daylight=True` across all models, aligned `ETdaily` and `ETuncertainty` to $\text{mm day}^{-1}$, and added canopy/soil/interception partitioning layers (`v1.11.0`).
- **`v1.13.0` – `v1.16.0` (2025-11-18 to 2026-01-30) — Pipeline Modularization, `verify.py`, & C3 Deployment:**
  - Decomposed the PGE into `JET.py`, `process_JET_table.py`, and `verify.py` (bundled with `ECOv002-cal-val-JET-inputs.csv` and `ECOv002-cal-val-JET-outputs.csv`), entering operational forward processing on November 20, 2025 (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`).
  - Locked the reference baseline in `v1.16.0` (`AquaSEBS~=1.3.0`, `BESS-JPL~=1.28.0`, `FLiESANN~=2.13.0`, `GEOS5FP~=2.19.0`, `PM-JPL~=1.11.0`, `PTJPLSM~=1.10.0`, `STIC-JPL~=1.6.0`, `verma-net-radiation~=1.11.0`) and extracted the core science modules into `JET3`.

---

### 2.2. Standalone `JET3` Release History (`v3.0.0` – `v3.1.0`, February – November 2026)

- **`v3.0.0` & `v3.0.1` (2026-02-18) — Initial Standalone Repository & Verification Suite:**
  - **Root Commit (`ed6a1ef0`, `v3.0.0`):** Created `JET3` containing `JET.py`, `process_JET_table.py`, `constants.py`, `exceptions.py`, `Ta_C_error_OLS.py`, `ECOv002_calval_JET_inputs.py`, `ECOv002_calval_JET_outputs.py`, and `verify.py` + `tests/test_verify.py`.
  - **Patch Release (`b559bae2` – `5b152d23`, `v3.0.1`):** Fixed `tests/test_verify.py` import to `from JET3 import verify`, exported `verify`, `load_ECOv002_calval_JET_inputs`, `load_ECOv002_calval_JET_outputs`, and `Ta_C_error_OLS` in `JET3/JET3.py`, and bumped version to `3.0.1`.
- **Empirical Bias Calibration & Uncertainty Quantification (`2026-02-25` – `2026-02-27`, commits `d44f912` – `8a5aae1`):**
  - Added `statsmodels` dependency and implemented empirical OLS error-correction functions (`calibrate_Ta_C.py`, `calibrate_RH.py`, `calibrate_SM.py`) and $\pm 1\sigma$ UQ generators (`generate_*_uncalibrated_UQ.py`, `generate_*_calibrated_UQ.py`) supporting scalars, NumPy arrays, and `rasters.Raster` geometries with `NaN` masking.
  - Wired opt-in `use_calibration: bool = False` and `generate_UQ: bool = False` flags into `JET()` and `process_JET_table()`, and refactored `JET()` to build its `results` dictionary incrementally across workflow stages.
  - Moved missing-parameter resolution (`SZA_deg`, `elevation_m`, `wind_speed_mps`, `canopy_height_meters`) to top-level initialization in `JET()` prior to calibration/UQ execution (inadvertently exposing `GEOS5FP_connection.wind_speed(...)` and `GEOS5FP_connection.elevation(...)` in the default call path).
- **Spatial Downscaling Migration & `v3.1.0` Release (`2026-03-27` – `2026-04-28`, commits `f489f68` – `7787e4aa`):**
  - Added `scikit-learn` dependency and migrated `sharpen_meteorology_data.py` and `sharpen_soil_moisture_data.py` from `ECOv003-L3T-L4T-JET` into `JET3`, controlled by `sharpen_meteorology: bool = SHARPEN_METEOROLOGY` and `sharpen_soil_moisture: bool = SHARPEN_SOIL_MOISTURE` in `JET()`.
  - Gated meteorology sharpening (`7787e4aa`) to run only when *both* `Ta_C is None` and `RH is None` (falling back to single-variable `GEOS5FP` retrieval when only one is missing) and bumped version to **`3.1.0`**.
- **Post-`v3.1.0` Sensitivity & Notebook Tooling (`2026-07-15` – `2026-11-19`, commits `9e80533` – `bec20d4`):**
  - Added `ECOv002-calval-tables>=1.13.0` (`2026-07-15`) and `SALib` (`2026-08-09`) to support Sobol global sensitivity, Shapley attribution, and Cal/Val benchmarking notebooks.
  - Added `notebooks/render_notebooks.py` (`2026-11-19`) for automated headless notebook execution and WebPDF rendering.
- **Cross-Repository Audit & Issue Filing (`2026-11-20`):**
  - Diagnosed `AttributeError` failures during `ECOv003-L3T-L4T-JET` DAG runs (`EcostressDAG_Col3.46000.0802.20261116T001911117`) caused by `GEOS5FP >=2.24.0` SI method renaming (`wind_speed` → `wind_speed_mps`, `Td_C` → `Td_K`).
  - Hardened `ECOv003-L3T-L4T-JET v1.22.1` (`smoke_test.py` and `tests/test_docker_smoke.py`) to assert `GEOS5FPConnection` SI method contracts and filed GitHub issues **`#14`–`#21`** on `JPL-Evapotranspiration-Algorithms/JET3`.

---

## 3. Target Scope for `JET3 v3.2.0` (Pending Tasks & Issue Resolution)

To transition cleanly from `v3.1.0` to **`v3.2.0`**, all eight open GitHub issues (`#14`–`#21`) and accompanying regression tests will be resolved across four workstreams.

> **Version Alignment Note:** Downstream `ECOv003-L3T-L4T-JET v1.22.1` currently pins `"JET3~=3.1.1"` (`>=3.1.1, <3.2.0`). Once `JET3 v3.2.0` is tagged and published, update `ECOv003-L3T-L4T-JET/pyproject.toml` to `"JET3~=3.2.0"` (or `"JET3>=3.2.0"`) so the container build (`ecostress-level-2-3-4`) resolves `v3.2.0`.

### Workstream A: `GEOS5FP >=2.24.0` & Online Retrieval Compatibility (`#19`, `#20`, `#21`)

1. **Issue [#19](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/19) (Critical) — Replace `GEOS5FP_connection.wind_speed()` with `wind_speed_mps()`:**
   - **File:** `JET3/JET.py` (line 283)
   - **Change:** Update `GEOS5FP_connection.wind_speed(...)` to `GEOS5FP_connection.wind_speed_mps(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)`.
   - **Packaging:** Declare `"GEOS5FP>=2.24.0"` in `pyproject.toml`.
2. **Issue [#20](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/20) (High) — Replace `GEOS5FP_connection.Td_C()` with `Td_K() - 273.15`:**
   - **File:** `JET3/sharpen_meteorology_data.py` (lines 57 and 156)
   - **Change:** Compute coarse and fine dew-point temperature in Celsius via `GEOS5FP_connection.Td_K(...) - 273.15` so meteorology downscaling executes cleanly instead of raising `AttributeError` and falling back silently to coarse `GEOS-5 FP` `Ta_C` and `RH`.
3. **Issue [#21](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/21) (High) — Resolve Missing `GEOS5FPConnection.elevation()` Method:**
   - **File:** `JET3/JET.py` (line 279)
   - **Change:** Replace `GEOS5FP_connection.elevation(geometry=geometry)` with a supported DEM lookup (e.g., `NASADEM` / SRTM elevation retrieval, or guard with `hasattr(GEOS5FP_connection, "elevation")` and fall back to `NASADEM` when `elevation_m is None`) so standalone `JET()` calls succeed without pre-supplied `elevation_m`.

---

### Workstream B: Scientific & Tabular Processing Bug Fixes (`#14`, `#15`, `#16`)

4. **Issue [#14](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/14) (High) — Gate `AquaSEBS` Daylight ET Overlay on `water_mask`:**
   - **File:** `JET3/JET.py` (lines 633–635)
   - **Change:** Gate the `ET_daylight_AquaSEBS_kg` overlay on `water_mask is not None` and `water_mask` truthiness—matching `LE_instantaneous_Wm2`—so land pixels and unmasked point tables (`water_mask=None`) are never overwritten by open-water evaporation:
     ```python
     if include_water_surface and water_mask is not None:
         ET_daylight_kg = rt.where(
             water_mask & ~np.isnan(ET_daylight_AquaSEBS_kg),
             ET_daylight_AquaSEBS_kg,
             ET_daylight_kg,
         )
     ```
5. **Issue [#15](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/15) (High) — Conditional Column Extraction & `'Ta'` Alias in `process_JET_table`:**
   - **File:** `JET3/process_JET_table.py` (lines 118–137)
   - **Change:** Replace unconditional attribute lookups (`input_df.Ta_C`, `input_df.Tmin_C`, `input_df.RH`, `input_df.SM`) with conditional dictionary lookups that support the documented `'Ta'` alias and default missing optional/online columns to `None` so `JET()` can retrieve them online or raise `MissingOfflineParameter` in offline mode.
6. **Issue [#16](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/16) (Low) — Fix Duplicate `BlankOutput` Check for `ET_daylight_PTJPLSM_kg`:**
   - **File:** `JET3/JET.py` (lines 485–491)
   - **Change:** Update the second `np.all(np.isnan(...))` guard to inspect `ET_daylight_PTJPLSM_kg` instead of checking `LE_PTJPLSM_Wm2` twice.

---

### Workstream C: Packaging Metadata & Code Hygiene (`#17`, `#18`)

7. **Issue [#17](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/17) (Medium) — Remove Stale `ECOv003_L3T_L4T_JET` References:**
   - **Files:** `JET3/Ta_C_error_OLS.py` (line 29) and `pyproject.toml` (lines 47–57)
   - **Change:**
     - Update `resources.files("ECOv003_L3T_L4T_JET")` to `resources.files("JET3")` in `Ta_C_error_OLS.py` and ensure `Ta_C_error_OLS.onnx` is packaged inside `JET3/`.
     - Update `[tool.setuptools.package-data]` in `pyproject.toml` to `JET3 = ["*.csv", "*.xml", "*.onnx"]`, update `[project.urls]` to `https://github.com/JPL-Evapotranspiration-Algorithms/JET3`, remove the stale `[project.scripts]` entry pointing to `ECOv003_L3T_L4T_JET`, and bump `version = "3.2.0"`.
8. **Issue [#18](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/18) (Low) — Remove Duplicate Constants:**
   - **File:** `JET3/constants.py` (lines 59 and 69)
   - **Change:** Remove duplicate definitions of `SHARPEN_METEOROLOGY = True` and `GEOS_IN_SENTINEL_COARSE_CELL_SIZE = 13720`.

---

### Workstream D: Regression Test Suite & Release Verification

Because `JET3.verify()` exercises `process_JET_table(..., offline_mode=True)` on point tables (`include_water_surface=False`), add a dedicated regression test module (`tests/test_regressions_v3_2_0.py`) covering every gridded, online, and tabular path fixed in `v3.2.0`:

| Test Case | Covers Issue(s) | Verification Assertion |
| :--- | :--- | :--- |
| `test_geos5fp_si_method_contract` | `#19`, `#20`, `#21` | `JET()` and `sharpen_meteorology_data()` invoke `wind_speed_mps` and `Td_K` (never `wind_speed` or `Td_C`) and succeed when `elevation_m=None`. |
| `test_sharpen_meteorology_no_silent_fallback` | `#20` | With a mock `GEOS5FPConnection` providing `Ta_C`, `Td_K`, and `SM`, `sharpen_meteorology_data()` returns spatially sharpened fine grids rather than flat coarse fallbacks. |
| `test_aquasebs_water_mask_gating` | `#14` | With `include_water_surface=True`, `ET_daylight_kg` equals land ensemble ET where `water_mask=False` (or `water_mask=None`) and equals `ET_daylight_AquaSEBS_kg` only where `water_mask=True`. |
| `test_process_jet_table_optional_and_alias_columns` | `#15` | `process_JET_table()` succeeds when `Ta` is used instead of `Ta_C`, when `Tmin_C` is omitted, and in online mode when `Ta_C`/`RH`/`SM` are omitted. |
| `test_ta_c_error_ols_resource_path` | `#17` | `get_ta_c_error_onnx_model_path()` resolves inside the `JET3` package without requiring `ECOv003_L3T_L4T_JET`. |
| `test_constants_no_duplicates` | `#18` | AST inspection of `JET3/constants.py` confirms no top-level constant is assigned more than once. |
| `test_verify_c3_baseline` | Baseline Invariant | Existing `tests/test_verify.py` passes with `rtol=1e-4, atol=1e-7` across all 22 Cal/Val reference variables. |

---

## 4. Execution & Release Checklist (`v3.2.0`)

- [ ] **Step 1 — Apply Code Fixes:** Patch `JET3/JET.py`, `JET3/sharpen_meteorology_data.py`, `JET3/process_JET_table.py`, `JET3/Ta_C_error_OLS.py`, `JET3/constants.py`, and `pyproject.toml` (`version = "3.2.0"`, `"GEOS5FP>=2.24.0"`).
- [ ] **Step 2 — Add Regression Tests:** Create `tests/test_regressions_v3_2_0.py` covering `#14`–`#21` and run `pytest -vv`.
- [ ] **Step 3 — Validate Collection 3 Baseline:** Run `make verify` (`JET3.verify()`) on Python 3.12 and 3.13 to confirm zero numerical drift against `ECOv002-cal-val-JET-outputs.csv`.
- [ ] **Step 4 — Commit, Tag & Publish `JET3 v3.2.0`:** Commit referencing `Closes #14, Closes #15, Closes #16, Closes #17, Closes #18, Closes #19, Closes #20, Closes #21`, tag `v3.2.0`, and publish to PyPI.
- [ ] **Step 5 — Downstream Alignment (`ECOv003-L3T-L4T-JET` & `ecostress-level-2-3-4`):**
  - Update `ECOv003-L3T-L4T-JET/pyproject.toml` dependency constraint to `"JET3~=3.2.0"`.
  - Run `ECOv003-L3T-L4T-JET test` and `make docker-smoke-test`.
  - Rebuild `ecostress-level-2-3-4` runtime container and re-drive failed DAG tiles.