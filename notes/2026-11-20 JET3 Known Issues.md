# JET3 Known Issues

This document tracks known bugs, packaging inconsistencies, and code cleanup items identified in the `JET3` codebase (`v3.1.0`).

---

## Summary Table

| ID | Severity | Component | Summary |
| :--- | :--- | :--- | :--- |
| **ISSUE-1** | High | `JET3/JET.py` | AquaSEBS daylight ET overwrites valid land `ET_daylight_kg` when `water_mask` is `None` or `False` |
| **ISSUE-2** | High | `JET3/process_JET_table.py` | `process_JET_table` raises `AttributeError` on missing optional inputs (`Tmin_C`, online met/SM) or `'Ta'` column alias |
| **ISSUE-3** | Medium | `JET3/Ta_C_error_OLS.py`, `pyproject.toml` | Stale `ECOv003_L3T_L4T_JET` package references break standalone ONNX model loading and package metadata |
| **ISSUE-4** | Low | `JET3/JET.py` | Duplicate `BlankOutput` check inspects `LE_PTJPLSM_Wm2` twice instead of `ET_daylight_PTJPLSM_kg` |
| **ISSUE-5** | Low | `JET3/constants.py` | Duplicate constant definitions for `GEOS_IN_SENTINEL_COARSE_CELL_SIZE` and `SHARPEN_METEOROLOGY` |

---

## Detailed Issue Descriptions

### ISSUE-1: AquaSEBS daylight ET overwrites valid land `ET_daylight_kg` when `water_mask` is `None` or `False`

* **Severity:** High (silent scientific output corruption)
* **Location:** `JET3/JET.py` (lines 633–635)

#### Description
When `include_water_surface=True`, `ET_daylight_AquaSEBS_kg` is overlaid onto the land ensemble `ET_daylight_kg` wherever `ET_daylight_AquaSEBS_kg` is non-NaN, without checking `water_mask`:

```python
if include_water_surface:
    # overlay water surface evaporation on top of daylight evapotranspiration aggregate
    ET_daylight_kg = rt.where(np.isnan(ET_daylight_AquaSEBS_kg), ET_daylight_kg, ET_daylight_AquaSEBS_kg)
```

#### Impact
Unlike `LE_instantaneous_Wm2` (which properly gates on `water_mask` at line 614), `ET_daylight_kg` relies solely on `np.isnan(ET_daylight_AquaSEBS_kg)`. Whenever `AquaSEBS` returns non-NaN values for unmasked land pixels or tabular point data (`water_mask=None`), valid land ensemble `ET_daylight_kg` estimates are silently overwritten by open-water evaporation values.

#### Proposed Fix
Gate the overlay on `water_mask` (and skip when `water_mask is None`), consistent with `LE_instantaneous_Wm2`:

```python
if include_water_surface and water_mask is not None:
    ET_daylight_kg = rt.where(
        water_mask & ~np.isnan(ET_daylight_AquaSEBS_kg),
        ET_daylight_AquaSEBS_kg,
        ET_daylight_kg,
    )
```

---

### ISSUE-2: `process_JET_table` raises `AttributeError` on missing optional inputs or `'Ta'` column alias

* **Severity:** High (runtime crash on valid tabular inputs)
* **Location:** `JET3/process_JET_table.py` (lines 118–137)

#### Description
`process_JET_table` unconditionally accesses several DataFrame columns via attribute lookup (`input_df.<col>`):

```python
# Handle air temperature column name differences (Ta_C or Ta)
Ta_C = np.array(input_df.Ta_C).astype(np.float64)

Tmin_C = np.array(input_df.Tmin_C).astype(np.float64)

# Extract and typecast relative humidity, soil moisture, net radiation, Topt, and fAPARmax
RH = np.array(input_df.RH).astype(np.float64)
soil_moisture = np.array(input_df.SM).astype(np.float64)
```

1. **`Ta` vs. `Ta_C`:** Line 128 documents support for `Ta_C` or `Ta` (and `JET3/verify.py` explicitly allows `'Ta'` as an alternative to `'Ta_C'`), yet line 129 unconditionally accesses `input_df.Ta_C`.
2. **`Tmin_C`:** `JET()` accepts `Tmin_C=None` and `verify.py` does not require `Tmin_C`, yet line 131 unconditionally accesses `input_df.Tmin_C`.
3. **Meteorology and soil moisture in online mode (`offline_mode=False`):** `JET()` dynamically retrieves missing `Ta_C`, `RH`, and `soil_moisture` from GEOS-5 FP when `offline_mode=False`, whereas `process_JET_table` unconditionally requires `Ta_C`, `RH`, and `SM` to exist in `input_df`.

#### Proposed Fix
Extract these columns conditionally (defaulting to `None` when absent so `JET()` can handle online retrieval or raise `MissingOfflineParameter` in offline mode), and fall back from `Ta_C` to `Ta`:

```python
if "Ta_C" in input_df:
    Ta_C = np.array(input_df["Ta_C"], dtype=np.float64)
elif "Ta" in input_df:
    Ta_C = np.array(input_df["Ta"], dtype=np.float64)
else:
    Ta_C = None

Tmin_C = np.array(input_df["Tmin_C"], dtype=np.float64) if "Tmin_C" in input_df else None
RH = np.array(input_df["RH"], dtype=np.float64) if "RH" in input_df else None
soil_moisture = np.array(input_df["SM"], dtype=np.float64) if "SM" in input_df else None
```

---

### ISSUE-3: Stale `ECOv003_L3T_L4T_JET` package references in `Ta_C_error_OLS.py` and `pyproject.toml`

* **Severity:** Medium (broken standalone ONNX inference and packaging metadata)
* **Locations:**
  * `JET3/Ta_C_error_OLS.py` (line 29)
  * `pyproject.toml` (lines 47–57)

#### Description
Several resource lookup paths and package configuration sections still reference the upstream `ECOv003_L3T_L4T_JET` package name rather than `JET3`:

* In `JET3/Ta_C_error_OLS.py`:
  ```python
  def get_ta_c_error_onnx_model_path() -> str:
      model_path = resources.files("ECOv003_L3T_L4T_JET") / DEFAULT_ONNX_MODEL_FILENAME
      return str(model_path)
  ```
  Calling `Ta_C_error_OLS()` in a standalone `JET3` installation raises `ModuleNotFoundError: No module named 'ECOv003_L3T_L4T_JET'`.
* In `pyproject.toml`:
  ```toml
  [tool.setuptools.package-data]
  ECOv003_L3T_L4T_JET = ["*.xml", "*.onnx"]

  [project.scripts]
  ECOv003-L3T-L4T-JET = "ECOv003_L3T_L4T_JET.ECOv003_L3T_L4T_JET:main"
  ```

#### Proposed Fix
* Update `resources.files(...)` in `JET3/Ta_C_error_OLS.py` to `"JET3"` and include `Ta_C_error_OLS.onnx` inside `JET3/`.
* Update `[tool.setuptools.package-data]` in `pyproject.toml` to target `JET3 = ["*.csv", "*.xml", "*.onnx"]` and remove or update the stale `[project.scripts]` entry.

---

### ISSUE-4: Duplicate `BlankOutput` check in `JET.py` inspects `LE_PTJPLSM_Wm2` twice

* **Severity:** Low (missed validation guard)
* **Location:** `JET3/JET.py` (lines 485–491)

#### Description
Two consecutive `if np.all(np.isnan(...))` checks both evaluate `LE_PTJPLSM_Wm2`, leaving `ET_daylight_PTJPLSM_kg` unchecked:

```python
if np.all(np.isnan(LE_PTJPLSM_Wm2)):
    raise BlankOutput(
        f"blank PT-JPL-SM instantaneous ET output for")

if np.all(np.isnan(LE_PTJPLSM_Wm2)):
    raise BlankOutput(
        f"blank daily ET output for")
```

#### Proposed Fix
Update the second guard to check `ET_daylight_PTJPLSM_kg`:

```python
if np.all(np.isnan(ET_daylight_PTJPLSM_kg)):
    raise BlankOutput("blank PT-JPL-SM daily ET output")
```

---

### ISSUE-5: Duplicate constant definitions in `JET3/constants.py`

* **Severity:** Low (code hygiene)
* **Location:** `JET3/constants.py` (lines 48, 57, 59, 69)

#### Description
Two constants are assigned twice in `JET3/constants.py`:

* `GEOS_IN_SENTINEL_COARSE_CELL_SIZE = 13720` (lines 48 and 69)
* `SHARPEN_METEOROLOGY = True` (lines 57 and 59)

#### Proposed Fix
Remove the duplicate definitions at lines 59 and 69.