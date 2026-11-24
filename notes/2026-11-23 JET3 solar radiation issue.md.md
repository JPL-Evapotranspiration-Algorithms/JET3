# `JET3` Issue Report & Technical Specification: Optional GEOS-5 FP Bias Correction for `FLiES-ANN` Solar Radiation (`SWin_Wm2` / `Rg`)

* **Date:** November 23, 2026
* **Affected Repositories:**
  * `JPL-Evapotranspiration-Algorithms/JET3` (`v3.2.0` $\rightarrow$ `v3.2.1` / `v3.3.0`)
  * `ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET` (`v1.23.0`)
* **Affected Modules:**
  * `JET3/constants.py`
  * `JET3/JET.py`
  * `tests/test_regressions.py`
  * `ECOv003_L3T_L4T_JET/constants.py` & `ECOv003_L3T_L4T_JET/ECOv003_L3T_L4T_JET.py`
* **Severity:** High (Operational Collection 3 Output Consistency — `+74.35 W/m²` systematic bias and `r = 0.38894` spatial correlation in `L3T_ETAUX` `Rg` relative to public LP DAAC Collection 3 products)

---

## 1. Executive Summary

During end-to-end reproduction testing of public ECOSTRESS Collection 3 Level-3 and Level-4 products (`L3T_ETAUX`, `L3T_JET`, `L4T_ESI`, and `L4T_WUE` for orbit `44841`, scene `1`, tile `11SPS`, `2026-06-02T18:00:12Z`) using `ECOv003-L3T-L4T-JET v1.23.0` and `JET3 v3.2.0`, every meteorological downscaling variable (`Ta`, `SM`, `RH`) and quality mask (`cloud`, `water`) matched the public LP DAAC granules (`AuxiliaryNWP match : True`, `RMSE = 0.00000`, `r = 1.00000`), while incoming shortwave solar radiation (`Rg` / `SWin_Wm2`) exhibited a **`+74.35 W/m²` positive bias** and degraded spatial correlation (**`r = 0.38894`**).

This divergence accounts for the downstream discrepancies across `Rn` (`+58.38 W/m²`), `PET` (`+44.50 W/m²`), and the ensemble evapotranspiration models (`PTJPLSM`, `STICJPL`, `PMJPL`, `BESSJPL`).

### Root Cause
1. In `ECOv003-L3T-L4T-JET v1.11.0`, `FLiES-ANN` solar radiation was switched to raw model output (`SWin_FLiES_ANN_raw`) without coarse-scale bias correction against GEOS-5 FP `tavg1_2d_rad_Nx` (`SWGDN` / `SWin`).
2. When `JET` was extracted into `JET3`, `JET3/constants.py` retained `BIAS_CORRECT_FLIES_ANN = True`, but `JET3/JET.py` never wired that constant into `JET()` and hardcoded `SWin_Wm2 = SWin_FLiES_ANN_raw`.
3. Because `ZERO_COT_CORRECTION = True` zeroes out coarse Cloud Optical Thickness (`COT = 0.0`) prior to radiative transfer, raw `FLiES-ANN` `SWin` is driven primarily by clear-sky solar zenith angle (`SZA_deg`) and surface albedo, missing sub-grid and synoptic cloud/aerosol attenuation captured in GEOS-5 FP `tavg1_2d_rad_Nx`.

---

## 2. Empirical Diagnostic Evidence (`orbit=44841`, `scene=1`, `tile=11SPS`, `2026-06-02`)

Comparing locally generated `ECOv003-L3T-L4T-JET v1.23.0` outputs against public LP DAAC Collection 3 granules (`BuildID` `0700`, revision `02`) with identical GEOS-5 FP forcing (`AuxiliaryNWP match : True`):

### `L3T_ETAUX` Comparison Summary

| Layer | Status | RMSE | MAE | Bias (Local − Public) | MaxDiff | Pearson $r$ | Local NaN% | Public NaN% |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Ta` | `MATCH` | `0.00000` | `0.00000` | `-0.00000` | `0.00001` | `1.00000` | `85.31%` | `85.31%` |
| `SM` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` | `6.08%` | `6.08%` |
| `RH` | `DIFF` | `0.00008` | `0.00008` | `-0.00008` | `0.00018` | `1.00000` | `85.31%` | `85.31%` |
| `cloud` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` | `0.00%` | `0.00%` |
| `water` | `MATCH` | `0.00000` | `0.00000` | `0.00000` | `0.00000` | `1.00000` | `0.00%` | `0.00%` |
| **`Rg`** | **`DIFF`** | **`74.75685`** | **`74.34881`** | **`+74.34881`** | **`101.00201`** | **`0.38894`** | **`0.00%`** | **`0.00%`** |
| `Rn` | `DIFF` | `59.23247` | `58.37636` | `+58.37636` | `100.08569` | `0.99851` | `85.31%` | `85.31%` |

### Key Diagnostic Observations
1. **No Additional GEOS-5 FP Downloads Required:** `AuxiliaryNWP` in the public `.json` metadata already includes `GEOS.fp.asm.tavg1_2d_rad_Nx.20260602_1730.V01.nc4` and `GEOS.fp.asm.tavg1_2d_rad_Nx.20260602_1830.V01.nc4` (fetched for `COT`, `PAR_albedo`, and `NIR_albedo`), so querying `GEOS5FP_connection.SWin(...)` reads cached local NetCDF4 files without changing `AuxiliaryNWP`.
2. **Downstream Error Propagation:** Restoring `Rg` (`SWin_Wm2`) directly eliminates the `+58.38 W/m²` bias in `Rn` (`verma_net_radiation`), the `+44.50 W/m²` bias in `PET`, and the proportional positive biases across `PTJPLSM`, `STICJPL`, `PMJPL`, `BESSJPL`, and `ETdaily`.

---

## 3. Architectural & Functional Requirements

To restore operational Collection 3 `Rg` parity in `ECOv003-L3T-L4T-JET` **without** breaking `JET3`'s standalone verification suite (`JET3.verify()`), the implementation must satisfy five strict requirements:

### Requirement 1 — Configurable Opt-In Flag in `JET3` (`bias_correct_FLiES_ANN: bool = False`)
* `JET3.JET()` must accept an explicit boolean keyword parameter:
  ```python
  bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN
  ```
* In `JET3/constants.py`, `BIAS_CORRECT_FLIES_ANN` **must default to `False`**.
* **Rationale:** `JET3` is a mission-independent library whose built-in numerical verification suite (`JET3.verify()` and `tests/test_verify.py`) compares outputs against the frozen `ECOv002-cal-val-JET-outputs.csv` baseline (`rtol=1e-4, atol=1e-7`) generated from un-bias-corrected `FLiES-ANN` `SWin_Wm2`. Keeping the default `False` inside `JET3` guarantees 100% backward compatibility for standalone `JET3` users and `JET3.verify()`.

### Requirement 2 — Preserving `JET3.verify()` & Tabular/Offline Behavior
* The `FLiES-ANN` bias-correction block inside `JET3/JET.py` must execute **only** when:
  1. `bias_correct_FLiES_ANN` is `True`,
  2. `processing_as_raster` is `True` (`isinstance(ST_C, Raster)`), and
  3. `offline_mode` is `False`.
* When `bias_correct_FLiES_ANN=False`, `offline_mode=True`, or inputs are point tables (`MultiPoint` / `np.ndarray`), `JET()` must preserve the exact existing behavior (`SWin_Wm2 = SWin_FLiES_ANN_raw`).

### Requirement 3 — Coarse-Scale Residual Bias Correction Formulation
When `bias_correct_FLiES_ANN and processing_as_raster and not offline_mode` holds, `JET()` must apply the same two-stage spatial residual adjustment used by `sharpen_meteorology_data()` and `sharpen_soil_moisture_data()` (documented in `notes/ECOSTRESS Collection 3 JET Spatial Downscaling Procedure.md` and `ECOv003_L3_L4_JET_User_Guide.md` Section 2.5):

1. **Coarse Grid Target:** Reuse `coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)` ($13{,}720\text{ m}$).
2. **Retrieve Coarse GEOS-5 FP Solar Radiation:**
   $$SWin_{c,\mathrm{GEOS5FP}} = \mathrm{GEOS5FP\_connection.SWin}(\text{time\_UTC}, \text{geometry}=\text{coarse\_geometry}, \text{resampling}=\text{downsampling})$$
3. **Aggregate Fine `FLiES-ANN` Output to Coarse Grid:**
   $$SWin_{c,\mathrm{FLiES}} = SWin_{f,\mathrm{raw}}.\mathrm{to\_geometry}(\text{coarse\_geometry}, \text{resampling}=\text{upsampling})$$
4. **Compute Coarse Residual Bias & Interpolate to Fine Grid:**
   $$E_c = SWin_{c,\mathrm{FLiES}} - SWin_{c,\mathrm{GEOS5FP}}$$
   $$E_f = E_c.\mathrm{to\_geometry}(\text{geometry}, \text{resampling}=\text{downsampling})$$
5. **Apply Additive Residual Correction with Non-Negative Clipping:**
   $$SWin_{f,\mathrm{corrected}} = \max\!\left(0,\; SWin_{f,\mathrm{raw}} - E_f\right)$$

### Requirement 4 — Enable by Default in `ECOv003-L3T-L4T-JET`
* `ECOv003_L3T_L4T_JET/constants.py` must define `BIAS_CORRECT_FLIES_ANN = True`.
* `ECOv003_L3T_L4T_JET/ECOv003_L3T_L4T_JET.py` (`L3T_L4T_JET()`) must expose `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` and forward `bias_correct_FLiES_ANN=bias_correct_FLiES_ANN` into `JET(...)`.
* This ensures operational Collection 3 forward-processing and reprocessing runs automatically produce bias-corrected `L3T_ETAUX` `Rg` matching the public LP DAAC Collection 3 archive.

### Requirement 5 — Regression & Integration Verification
* `JET3` must include unit tests in `tests/test_regressions.py` verifying both `bias_correct_FLiES_ANN=False` (default, no `GEOS5FP_connection.SWin` call) and `bias_correct_FLiES_ANN=True` (applies `GEOS5FP_connection.SWin` coarse residual correction and clips at `0.0`).
* `tests/test_verify.py` (`JET3.verify()`) must continue to pass without modification.

---

## 4. Detailed Code Specification

### 4.1. `JET3/constants.py`

Update `BIAS_CORRECT_FLIES_ANN` from `True` to `False` so `JET3` defaults to un-bias-corrected `FLiES-ANN` solar radiation:

```python
STRIP_CONSOLE = False
SAVE_INTERMEDIATE = False
SHOW_DISTRIBUTION = True
INCLUDE_SEB_DIAGNOSTICS = False
INCLUDE_JET_DIAGNOSTICS = False
BIAS_CORRECT_FLIES_ANN = False
ZERO_COT_CORRECTION = True
SHARPEN_METEOROLOGY = True
SHARPEN_SOIL_MOISTURE = True
```

### 4.2. `JET3/JET.py`

1. **Function Signature:**
   ```python
   def JET(
           ...
           offline_mode: bool = False,
           include_water_surface: bool = True,
           generate_UQ: bool = False,
           use_calibration: bool = False,
           sharpen_soil_moisture: bool = SHARPEN_SOIL_MOISTURE,
           sharpen_meteorology: bool = SHARPEN_METEOROLOGY,
           bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN) -> Dict[str, Union[Raster, np.ndarray]]:
   ```

2. **Bias Correction Block (replacing lines 402–404 of `JET3/JET.py`):**
   ```python
   if bias_correct_FLiES_ANN and processing_as_raster and not offline_mode:
       logger.info("bias-correcting FLiES-ANN solar radiation to GEOS-5 FP")
       if coarse_geometry is None:
           coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)

       SWin_coarse_GEOS5FP = GEOS5FP_connection.SWin(
           time_UTC=time_UTC,
           geometry=coarse_geometry,
           resampling=downsampling,
       )
       check_distribution(SWin_coarse_GEOS5FP, "SWin_coarse_GEOS5FP")

       SWin_coarse_FLiES = SWin_FLiES_ANN_raw.to_geometry(coarse_geometry, resampling=upsampling)
       check_distribution(SWin_coarse_FLiES, "SWin_coarse_FLiES")

       SWin_bias_coarse = SWin_coarse_FLiES - SWin_coarse_GEOS5FP
       check_distribution(SWin_bias_coarse, "SWin_bias_coarse")

       SWin_bias_smooth = SWin_bias_coarse.to_geometry(geometry, resampling=downsampling)
       check_distribution(SWin_bias_smooth, "SWin_bias_smooth")

       SWin_Wm2 = rt.clip(SWin_FLiES_ANN_raw - SWin_bias_smooth, 0, None)
       check_distribution(SWin_Wm2, "SWin_FLiES_ANN_bias_corrected")
   else:
       # Use raw FLiES-ANN output directly without bias correction
       SWin_Wm2 = SWin_FLiES_ANN_raw
       check_distribution(SWin_Wm2, "SWin_FLiES_ANN")
   ```

### 4.3. `ECOv003-L3T-L4T-JET` Integration (`ECOv003_L3T_L4T_JET/constants.py` & `ECOv003_L3T_L4T_JET.py`)

1. **`ECOv003_L3T_L4T_JET/constants.py`:**
   ```python
   BIAS_CORRECT_FLIES_ANN = True
   ZERO_COT_CORRECTION = True
   SHARPEN_METEOROLOGY = True
   SHARPEN_SOIL_MOISTURE = True
   ```

2. **`ECOv003_L3T_L4T_JET/ECOv003_L3T_L4T_JET.py`:**
   ```python
   def L3T_L4T_JET(
           runconfig_filename: str,
           upsampling: str = None,
           downsampling: str = None,
           Rn_model_name: str = RN_MODEL_NAME,
           bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN,
           zero_COT_correction: bool = ZERO_COT_CORRECTION,
           sharpen_meteorology: bool = SHARPEN_METEOROLOGY,
           sharpen_soil_moisture: bool = SHARPEN_SOIL_MOISTURE,
           ...
   ```
   Pass `bias_correct_FLiES_ANN=bias_correct_FLiES_ANN` in the `results = JET(...)` call.

---

## 5. Verification & Release Checklist

* [ ] **Step 1 (`JET3`):** Set `BIAS_CORRECT_FLIES_ANN = False` in `JET3/constants.py` and wire `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` into `JET3/JET.py`.
* [ ] **Step 2 (`JET3` Tests):** Add unit tests in `tests/test_regressions.py` verifying:
  * Default `JET()` (`bias_correct_FLiES_ANN=False`) leaves `SWin_Wm2` equal to `SWin_FLiES_ANN_raw` without invoking `GEOS5FP_connection.SWin`.
  * `JET(..., bias_correct_FLiES_ANN=True)` on a `Raster` geometry invokes `GEOS5FP_connection.SWin`, subtracts the interpolated coarse bias, and clips negative values to `0.0`.
* [ ] **Step 3 (`JET3` Baseline Check):** Run `pytest -vv` and `make verify` (`JET3.verify()`) to confirm 100% pass rate against `ECOv002-cal-val-JET-outputs.csv`.
* [ ] **Step 4 (`JET3` Release):** Bump `JET3/pyproject.toml` version (e.g., `3.2.1` or `3.3.0`), tag, and publish.
* [ ] **Step 5 (`ECOv003-L3T-L4T-JET` Update & End-to-End Validation):**
  * Update `ECOv003-L3T-L4T-JET/pyproject.toml` to require the updated `JET3` release.
  * Set `BIAS_CORRECT_FLIES_ANN = True` in `ECOv003_L3T_L4T_JET/constants.py` and pass `bias_correct_FLiES_ANN=bias_correct_FLiES_ANN` into `JET(...)`.
  * Re-run `python examples/example_L3T_L4T_JET_run_with_download.py` on `orbit=44841, scene=1, tile=11SPS` (`2026-06-02`) and verify that `L3T_ETAUX` `Rg` converges from `+74.35 W/m²` bias (`r = 0.38894`) to `MATCH` (`r ≈ 1.00000`) alongside `Rn`, `PET`, `L3T_JET`, `L4T_ESI`, and `L4T_WUE`.