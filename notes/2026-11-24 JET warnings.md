# `JET3` Notebook & Codebase Warnings Report

**Date:** November 24, 2026  
**Context:** `ECOv003_JET_SATM_Reproduction.ipynb` (`JET3 v3.3.0`)

---

## 1. Summary

During execution of the `ECOv003_JET_SATM_Reproduction` notebook, repeated runtime warnings were emitted to `stderr` whenever `process_JET_table()` was invoked (in **Cell 2** for `input_df_full` and `input_df_270`, and in **Cell 6** for `processed_270_cal`). All emitted Python warnings originated from a single upstream dependency (`solar_apparent_time`) due to NumPy 2.x `datetime64` and `timedelta64` deprecations.

In addition to the notebook runtime warnings, `JET3` defines two physical unit-range `logger.warning` checks in `JET3/JET.py` and three `pytest` warning filters in `pyproject.toml`.

---

## 2. Warnings Found in Notebook Execution (`ECOv003_JET_SATM_Reproduction`)

### 2.1. `UserWarning`: Timezone-Aware Timestamp Coercion in `np.datetime64`

* **Warning Class:** `UserWarning`
* **Source File & Line:** `solar_apparent_time/solar_apparent_time.py`, line `37`
* **Code Trigger:**
  ```python
  return np.array(arr, dtype='datetime64[ns]')
  ```
* **Full Message:**
  > `UserWarning: no explicit representation of timezones available for np.datetime64`
* **Cause:** `process_JET_table()` parses the `time_UTC` column via `pd.to_datetime(input_df.time_UTC, format='mixed').tolist()`, producing timezone-aware `pandas.Timestamp` objects (`UTC`). When downstream daylight-upscaling routines pass these timestamps into `solar_apparent_time`, NumPy warns that timezone offsets are stripped when casting to `datetime64[ns]`.
* **Impact:** Benign for `UTC` timestamps (which already have a zero offset), though it generates heavy console output across repeated model runs.

---

### 2.2. `DeprecationWarning`: Implicit `'generic'` Unit in NumPy `timedelta` Arithmetic

* **Warning Class:** `DeprecationWarning`
* **Source File & Line:** `solar_apparent_time/solar_apparent_time.py`, line `212`
* **Code Trigger:**
  ```python
  doy_UTC = ((times_b.astype('datetime64[D]') - year_start.astype('datetime64[D]')) + 1).astype(int)
  ```
* **Full Message:**
  > `DeprecationWarning: The 'generic' unit for NumPy timedelta is deprecated, and will raise an error in the future. This includes implicit conversion of bare integers (e.g. '1'). Please use a specific unit instead.`
* **Cause:** Adding a bare Python integer (`+ 1`) to a `datetime64[D]` difference array (`timedelta64[D]`) relies on implicit conversion of `1` using NumPy's deprecated `'generic'` timedelta unit rather than an explicit unit (`np.timedelta64(1, 'D')`).
* **Impact:** Currently non-fatal in NumPy 2.x, but will raise an exception in a future NumPy release unless `solar_apparent_time` is updated to use `np.timedelta64(1, 'D')`.

---

### 2.3. Why Global Warning Filters Alone Were Overridden

Setting `warnings.filterwarnings(...)` at the top of the notebook was insufficient because constituent packages inside `process_JET_table()` dynamically modify `warnings.filters` during execution. Wrapping calls in a local `warnings.catch_warnings()` context manager suppresses them reliably:

```python
with open(os.devnull, "w") as fnull, \
     contextlib.redirect_stdout(fnull), \
     contextlib.redirect_stderr(fnull), \
     warnings.catch_warnings():
    warnings.simplefilter("ignore")
    processed_df = process_JET_table(input_df, use_calibration=False)
```

---

## 3. Additional Warnings Configured in the `JET3` Repository

### 3.1. Physical Unit-Range Guardrails (`JET3/JET.py`)

`JET3` (`v3.3.0`) emits `logger.warning` alerts immediately prior to running `FLiESANN` if atmospheric column inputs appear to be in unscaled `GEOS-5 FP` native units rather than CGS units:

| Variable | Trigger Condition | Warning Message |
| :--- | :--- | :--- |
| `vapor_gccm` | `np.nanmean(vapor_gccm) > 15.0` | `vapor_gccm mean (...) exceeds 15 g/cm^2; verify GEOS5FP >=2.27.0 is installed so TQV (kg/m^2) is converted to g/cm^2.` |
| `ozone_cm` | `np.nanmean(ozone_cm) > 5.0` | `ozone_cm mean (...) exceeds 5 cm; verify GEOS5FP >=2.27.0 is installed so TO3 (DU) is converted to cm.` |

### 3.2. Test-Suite Warning Filters (`pyproject.toml`)

`pyproject.toml` (`[tool.pytest.ini_options]`) suppresses three external library warnings during `pytest` runs:

1. **`RuntimeWarning`:** `numpy.ndarray size changed` (C-extension ABI compatibility notice across NumPy builds).
2. **`DeprecationWarning`:** `The 'shapely.geos' module is deprecated` (emitted by older geospatial dependencies).
3. **`RuntimeWarning`:** `invalid value encountered in divide` in `daylight_evapotranspiration` (occurs during night/polar-daylight boundary masking when daylight duration approaches zero).