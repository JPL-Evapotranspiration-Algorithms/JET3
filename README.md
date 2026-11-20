# JET3: JPL Evapotranspiration Ensemble Algorithm

[![CI](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/actions/workflows/ci.yml/badge.svg)](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/actions/workflows/ci.yml)

JET3 is a Python package for computing evapotranspiration (ET), evaporative stress index (ESI), and water use efficiency (WUE) using an ensemble of four scientifically-validated models. This package provides the core algorithms used in the ECOSTRESS and Surface Biology and Geology (SBG) missions, now available as a standalone, mission-independent tool.

JET3 is part of the [JPL-Evapotranspiration-Algorithms](https://github.com/JPL-Evapotranspiration-Algorithms) organization and serves as the foundation for:
- [ECOSTRESS Collection 3 L3T/L4T JET Products](https://github.com/ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET)
- [SBG Collection 1 L4 JET Products](https://github.com/sbg-tir/SBG-TIR-L4-JET)

## Authors

[Gregory H. Halverson](https://github.com/gregory-halverson-jpl) (they/them)<br>
[gregory.h.halverson@jpl.nasa.gov](mailto:gregory.h.halverson@jpl.nasa.gov)<br>
NASA Jet Propulsion Laboratory 329G

Kerry Cawse-Nicholson (she/her)<br>
NASA Jet Propulsion Laboratory 329G

Madeleine Pascolini-Campbell (she/her)<br>
NASA Jet Propulsion Laboratory 329F

This package has been developed using open-science practices with New Technology Report (NTR) and open-source license from NASA Jet Propulsion Laboratory. The code is based on algorithms originally developed for the ECOSTRESS mission and refined for broader applications.

## Introduction 

JET3 produces estimates of:
- **Evapotranspiration (ET)**: The combined process of water evaporation from soil and transpiration from plants
- **Evaporative Stress Index (ESI)**: A measure of vegetation water stress (ratio of actual to potential ET)
- **Water Use Efficiency (WUE)**: The ratio of carbon uptake (GPP) to water loss (ET)

Accurate modeling of ET requires consideration of many environmental and biological controls including: solar radiation, atmospheric water vapor deficit, soil water availability, vegetation physiology and phenology (Brutsaert, 1982; Monteith, 1965; Penman, 1948). 

JET3 implements an ensemble approach combining four scientifically-validated models:
- **PT-JPL-SM**: Priestley-Taylor model with soil moisture sensitivity
- **STIC-JPL**: Surface Temperature Initiated Closure model
- **PM-JPL**: Penman-Monteith model (MOD16 derivative)
- **BESS-JPL**: Breathing Earth System Simulator model

The ensemble median provides robust ET estimates with reduced uncertainty compared to individual models.

### Required Inputs

JET3 requires the following core input variables:
- **Surface temperature (ST_C)**: Land surface temperature in Celsius
- **Surface emissivity (emissivity)**: Broadband thermal emissivity (0-1)
- **NDVI**: Normalized Difference Vegetation Index
- **Albedo**: Surface albedo
- **Air temperature (Ta_C)**: Near-surface air temperature in Celsius
- **Relative humidity (RH)**: Near-surface relative humidity (0-1)
- **Soil moisture (soil_moisture)**: Volumetric soil moisture (m³/m³)
- **Geometry (geometry)**: Spatial geometry object for raster or point processing
- **Time (time_UTC)**: Observation timestamp(s) in UTC

Additional meteorological and atmospheric variables can be provided explicitly, or retrieved internally when not running in offline mode.

These inputs can be derived from any appropriate remote sensing or ground-based data sources.

## Installation

Install from PyPI:
```bash
pip install JET3
```

Or install from source:
```bash
git clone [https://github.com/JPL-Evapotranspiration-Algorithms/JET3.git](https://github.com/JPL-Evapotranspiration-Algorithms/JET3.git)
cd JET3
pip install -e .
```

## Evapotranspiration Models

JET3 implements an ensemble of four evapotranspiration models, each with different strengths and theoretical foundations. The ensemble approach combines outputs to reduce uncertainty and improve overall accuracy.

### Priestley-Taylor (PT-JPL-SM) Evapotranspiration Model

The Priestley-Taylor Jet Propulsion Laboratory model with Soil Moisture (PT-JPL-SM), developed by Dr. Adam Purdy and Dr. Joshua Fisher, was designed as a soil moisture-sensitive evapotranspiration product for the Soil Moisture Active-Passive (SMAP) mission. The model estimates instantaneous canopy transpiration, leaf surface evaporation, and soil moisture evaporation using the Priestley-Taylor formula with a set of constraints. These three partitions are combined into total latent heat flux in watts per square meter for the ensemble estimate.

**Reference**: Purdy, A.J., Fisher, J.B., Goulden, M.L., Colliander, A., Halverson, G., Tu, K., Famiglietti, J.S. (2018). SMAP soil moisture improves global evapotranspiration. *Remote Sensing of Environment*, 219, 1-14. https://doi.org/10.1016/j.rse.2018.09.023

**Repository**: [PT-JPL-SM](https://github.com/JPL-Evapotranspiration-Algorithms/PT-JPL-SM)

### Surface Temperature Initiated Closure (STIC-JPL) Evapotranspiration Model

The Surface Temperature Initiated Closure-Jet Propulsion Laboratory (STIC-JPL) model, contributed by Dr. Kaniska Mallick, was designed as a surface temperature-sensitive ET model, adopted by ECOSTRESS and SBG for improved estimates of ET reflecting mid-day heat stress. The STIC-JPL model estimates total latent heat flux directly using thermal remote sensing observations. This instantaneous estimate of latent heat flux is included in the ensemble estimate.

**Reference**: Mallick, K., Trebs, I., Boegh, E., Giustarini, L., Schlerf, M., Drewry, D.T., Hoffmann, L., von Randow, C., Kruijt, B., Araùjo, A., Saleska, S., Ehleringer, J.R., Domingues, T.F., Ometto, J.P.H.B., Nobre, A.D., de Moraes, O.L.L., Hayek, M., Munger, J.W., Wofsy, S.C. (2016). Canopy-scale biophysical controls of transpiration and evaporation in the Amazon Basin. *Hydrology and Earth System Sciences*, 20, 4237-4264. https://doi.org/10.5194/hess-20-4237-2016

**Repository**: [STIC-JPL](https://github.com/JPL-Evapotranspiration-Algorithms/STIC-JPL)

### Penman Monteith (PM-JPL) Evapotranspiration Model

The Penman-Monteith-Jet Propulsion Laboratory (PM-JPL) algorithm is a derivation of the MOD16 algorithm that was originally designed as the ET product for the Moderate Resolution Imaging Spectroradiometer (MODIS) and continued as a Visible Infrared Imaging Radiometer Suite (VIIRS) product. PM-JPL uses a similar approach to PT-JPL and PT-JPL-SM to independently estimate vegetation and soil components of instantaneous ET, but using the Penman-Monteith formula instead of the Priestley-Taylor. The PM-JPL latent heat flux partitions are summed to total latent heat flux for the ensemble estimate.

**Reference**: Running, S., Mu, Q., Zhao, M., Moreno, A. (2019). MODIS Global Terrestrial Evapotranspiration (ET) Product (MOD16A2/A3 and MOD16A2GF/A3GF). NASA Earth Observing System Data and Information System (EOSDIS) Land Processes Distributed Active Archive Center (LP DAAC). https://doi.org/10.5067/MODIS/MOD16A2.061

**Repository**: [PM-JPL](https://github.com/JPL-Evapotranspiration-Algorithms/PM-JPL)

### Breathing Earth System Simulator (BESS-JPL) Gross Primary Production (GPP) Model

The Breathing Earth System Simulator Jet Propulsion Laboratory (BESS-JPL) model is a coupled surface energy balance and photosynthesis model contributed by Dr. Youngryel Ryu. The model iteratively calculates net radiation, ET, and Gross Primary Production (GPP) estimates. The latent heat flux component of BESS-JPL is included in the ensemble estimate, while the BESS-JPL net radiation is used as input to the other ET models.

**Reference**: Ryu, Y., Baldocchi, D.D., Kobayashi, H., van Ingen, C., Li, J., Black, T.A., Beringer, J., van Gorsel, E., Knohl, A., Law, B.E., Roupsard, O. (2011). Integration of MODIS land and atmosphere products with a coupled-process model to estimate gross primary productivity and evapotranspiration from 1 km to global scales. *Global Biogeochemical Cycles*, 25, GB4017. https://doi.org/10.1029/2011GB004053

**Repository**: [BESS-JPL](https://github.com/JPL-Evapotranspiration-Algorithms/BESS-JPL)

### Ensemble Processing

The ensemble ET estimate is computed as the median of total latent heat flux (in watts per square meter) from the PT-JPL-SM, STIC-JPL, PM-JPL, and BESS-JPL models. This median is then upscaled to a daily ET estimate in millimeters per day. The standard deviation between these multiple estimates represents the ensemble uncertainty.

### AquaSEBS Water Surface Evaporation

For water surface pixels, JET3 implements the AquaSEBS (Aquatic Surface Energy Balance System) model developed by Abdelrady et al. (2016) and validated by Fisher et al. (2023). Water surface evaporation is calculated using a physics-based approach that combines the equilibrium temperature model for water heat flux with the Priestley-Taylor equation for evaporation estimation.

**References**: 
- Abdelrady, A., Timmermans, J., Vekerdy, Z., Salama, M.S. (2016). Surface Energy Balance of Fresh and Saline Waters: AquaSEBS. *Remote Sensing*, 8, 583. https://doi.org/10.3390/rs8070583
- Fisher, J.B., Dohlen, M.B., Halverson, G.H., Collison, J.W., Hook, S.J., Hulley, G.C. (2023). Remotely sensed terrestrial open water evaporation. *Scientific Reports*, 13, 8217. https://doi.org/10.1038/s41598-023-34921-2

**Repository**: [AquaSEBS](https://github.com/JPL-Evapotranspiration-Algorithms/AquaSEBS)

#### Methodology

The AquaSEBS model implements the surface energy balance equation specifically adapted for water bodies:

$$R_n = LE + H + W$$

Where the water heat flux (W) is calculated using the equilibrium temperature model:

$$W = \beta \times (T_e - WST)$$

The key parameters include:
- **Temperature difference**: $T_n = 0.5 \times (WST - T_d)$ where WST is water surface temperature and $T_d$ is dew point temperature
- **Evaporation efficiency**: $\eta = 0.35 + 0.015 \times WST + 0.0012 \times T_n^2$
- **Thermal exchange coefficient**: $\beta = 4.5 + 0.05 \times WST + (\eta + 0.47) \times S$
- **Equilibrium temperature**: $T_e = T_d + \frac{SW_{net}}{\beta}$

Latent heat flux is then calculated using the Priestley-Taylor equation with α = 1.26 for water surfaces:

$$LE = \alpha \times \frac{\Delta}{\Delta + \gamma} \times (R_n - W)$$

#### Validation and Accuracy

The AquaSEBS methodology has been extensively validated against 19 in situ open water evaporation sites worldwide spanning multiple climate zones. Performance metrics include:

**Daily evaporation estimates:**
- **MODIS-based**: r² = 0.47, RMSE = 1.5 mm/day (41% of mean), Bias = 0.19 mm/day
- **Landsat-based**: r² = 0.56, RMSE = 1.2 mm/day (38% of mean), Bias = -0.8 mm/day

**Instantaneous estimates (controlled for high wind events >7.5 m/s):**
- **Correlation**: r² = 0.71
- **RMSE**: 53.7 W/m² (38% of mean)
- **Bias**: -19.1 W/m² (13% of mean)

The model demonstrates particular strength in water-limited environments and performs well across spatial scales from 30m (Landsat) to 1km (MODIS) resolution.

Water surface evaporation estimates are included in the `ET_daylight_kg` output layer (equivalent to mm over daylight), integrated from sunrise to sunset.

### Evaporative Stress Index (ESI) and Water Use Efficiency (WUE)

The PT-JPL-SM model generates estimates of both actual and potential instantaneous ET. The potential evapotranspiration (PET) estimate represents the maximum expected ET if there were no water stress to plants on the ground. The ratio of the actual ET estimate to the PET estimate forms an index representing the water stress of plants, with zero being fully stressed with no observable ET and one being non-stressed with ET reaching PET.

**Evaporative Stress Index (ESI)**: 
$$\text{ESI} = \frac{\text{ET}_{\text{actual}}}{\text{PET}}$$

Water Use Efficiency (WUE) relates the amount of carbon that plants are taking in (GPP from BESS-JPL) to the amount of water that plants are releasing (transpiration from PT-JPL-SM):

**Water Use Efficiency (WUE)**:
$$\text{WUE} = \frac{\text{GPP}}{\text{Transpiration}}$$

WUE is expressed as the ratio of grams of carbon that plants take in to kilograms of water that plants release ($\text{g C kg}^{-1} \text{H}_2\text{O}$).

## Theory

The JPL evapotranspiration (JET) ensemble provides a robust estimation of ET from multiple ET models. The ET ensemble incorporates ET data from four algorithms: Priestley Taylor-Jet Propulsion Laboratory model with soil moisture (PT-JPL-SM), the Penman Monteith-Jet Propulsion Laboratory model (PM-JPL), Surface Temperature Initiated Closure-Jet Propulsion Laboratory model (STIC-JPL), and the Breathing Earth System Simulator-Jet Propulsion Laboratory model (BESS-JPL). 

Each model brings complementary strengths:
- **PT-JPL-SM**: Incorporates soil moisture constraints and partitions ET into canopy transpiration, interception, and soil evaporation
- **STIC-JPL**: Leverages surface temperature to detect heat stress and reduced ET capacity
- **PM-JPL**: Implements the widely-used Penman-Monteith formulation with aerodynamic considerations
- **BESS-JPL**: Couples photosynthesis with ET through a comprehensive surface energy balance

The ensemble median approach reduces model-specific biases and provides more robust estimates than any individual model.

## Validation

The JET ensemble approach has been validated against flux tower measurements from the FLUXNET network as documented in Pierrat et al. (2025) and through the ECOSTRESS mission. The validation demonstrated that the ensemble evapotranspiration estimates:

- Show strong correlation with flux tower measurements (R² > 0.7) across most biomes
- Capture the diurnal and seasonal patterns of evapotranspiration effectively
- Perform well in water-limited ecosystems where thermal stress indicators are most valuable
- Benefit from the ensemble approach, with the median estimate generally outperforming individual models
- Maintain accuracy across a range of spatial scales

### Performance by Biome

The validation results indicate varying performance across different ecosystem types:

- **Croplands**: Excellent agreement during growing season, capturing irrigation and phenological patterns
- **Forests**: Good performance in temperate and boreal forests, with some challenges in dense tropical canopies
- **Grasslands**: Strong performance in both natural and managed grassland systems
- **Shrublands**: Reliable estimates in semi-arid regions where thermal stress is prevalent

The JET3 ensemble provides reliable ET estimates suitable for water resource management, agricultural monitoring, and ecosystem research applications.

## Repository History

The `JET3` codebase originated inside [`ECOv003-L3T-L4T-JET`](https://github.com/ECOSTRESS-Collection-3/ECOv003-L3T-L4T-JET) (the ECOSTRESS Collection 3 Product Generating Executable) before being extracted into a standalone, mission-independent library in early 2026 (`v3.0.0` / `v3.0.1` on February 18, 2026), roughly three months after ECOSTRESS Collection 3 entered operational forward processing (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`, paired with `ECOv003-L3T-L4T-JET v1.13.0`–`v1.16.0`). For the full chronological narrative and baseline audit, see [`notes/2026-11-20 repository history.md`](notes/2026-11-20%20repository%20history.md).

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
| **2026-11-20** | `v3.1.0` → `v3.1.1` *(planned)* | `v1.22.1` | `JET3~=3.1.1`, `GEOS5FP~=2.24.0` | Diagnosed `GEOS5FP` API mismatch (`wind_speed_mps`, `Td_K`); filed `JET3` issues `#14`–`#18`. |

### Baseline Verification & Output Consistency

Because `JET3` was extracted *after* the initial Collection 3 forward-processing deployment (`eco-level-2-3-4-application` `v1.7.0` / `v1.7.1`), `JET3` has included a built-in verification suite (`JET3/verify.py` and `tests/test_verify.py`) since its initial commit (`ed6a1ef0`, `v3.0.0`).

- **Core Physics & Tabular Ensemble (`JET3.verify()`):** Running `verify()` executes `process_JET_table(..., offline_mode=True)` on the ECOSTRESS Collection 2 Cal-Val input table (`ECOv002-cal-val-JET-inputs.csv`) and checks 22 output variables (`LE_*_Wm2`, `ET_daylight_*_kg`, `ET_daylight_kg`, `ET_uncertainty`, canopy/soil/interception fractions, `Ta_C`, `RH`, `Rn_Wm2`, `SM`, `ESI_PTJPLSM`, `PET_instantaneous_PTJPLSM_Wm2`, `WUE`, and `GPP_inst_g_m2_s`) against the frozen `ECOv002-cal-val-JET-outputs.csv` reference (`rtol=1e-4, atol=1e-7`). Passing `verify()` confirms that core radiative transfer (`FLiES-ANN`, `verma_net_radiation`, `SEBAL_soil_heat_flux`) and terrestrial ensemble calculations (`PT-JPL-SM`, `STIC-JPL`, `PM-JPL`, `BESS-JPL`) have not drifted from the initial Collection 3 deployment baseline when given pre-supplied forcing (`use_calibration=False`).
- **Gridded & Online Execution Paths:** Because `verify()` runs `process_JET_table(..., offline_mode=True)` on point geometries (`include_water_surface=False`), three gridded/online code paths added or exercised during PGE runs require separate regression coverage in `JET3 v3.1.1`:
  1. **Spatial downscaling (`sharpen_meteorology_data` / `sharpen_soil_moisture_data`):** Added in `v3.1.0`; `GEOS5FP_connection.Td_C(...)` fails against `GEOS5FP>=2.24.0` (`Td_K`), causing meteorology sharpening to fall back silently to coarse GEOS-5 FP fields on raster scenes.
  2. **Dynamic `GEOS-5 FP` retrieval (`wind_speed_mps`, `elevation`):** Added to `JET()` in `v3.1.0`; `GEOS5FP_connection.wind_speed(...)` and `GEOS5FP_connection.elevation(...)` fail against `GEOS5FP>=2.24.0` when those inputs are omitted.
  3. **Open-water overlay (`AquaSEBS` when `include_water_surface=True`):** `ET_daylight_AquaSEBS_kg` is overlaid wherever non-NaN rather than gating on `water_mask` (Issue [#14](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/14)).

## Known Issues

The following known issues are tracked in [`notes/2026-11-20 JET3 Known Issues.md`](notes/2026-11-20%20JET3%20Known%20Issues.md) and on the [GitHub Issue Tracker](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues) for `JET3 v3.1.0`:

| Issue | Severity | Component | Summary |
| :--- | :--- | :--- | :--- |
| **[#14](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/14)** | High | `JET3/JET.py` | AquaSEBS daylight ET overwrites valid land `ET_daylight_kg` when `water_mask` is `None` or `False` |
| **[#15](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/15)** | High | `JET3/process_JET_table.py` | `process_JET_table` raises `AttributeError` on missing optional inputs (`Tmin_C`, online met/SM) or `'Ta'` column alias |
| **[#16](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/16)** | Low | `JET3/JET.py` | Duplicate `BlankOutput` check inspects `LE_PTJPLSM_Wm2` twice instead of `ET_daylight_PTJPLSM_kg` |
| **[#17](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/17)** | Medium | `JET3/Ta_C_error_OLS.py`, `pyproject.toml` | Stale `ECOv003_L3T_L4T_JET` package references break standalone ONNX model loading and package metadata |
| **[#18](https://github.com/JPL-Evapotranspiration-Algorithms/JET3/issues/18)** | Low | `JET3/constants.py` | Duplicate constant definitions for `GEOS_IN_SENTINEL_COARSE_CELL_SIZE` and `SHARPEN_METEOROLOGY` |

In addition, `JET3 v3.1.0` contains legacy `GEOS5FPConnection` method calls (`wind_speed(...)`, `Td_C(...)`, and `elevation(...)`) that are incompatible with `GEOS5FP>=2.24.0` (`wind_speed_mps(...)`, `Td_K(...)`) and are scheduled for resolution in `JET3 v3.1.1`.

## Acknowledgements 

We would like to thank Joshua Fisher as the initial science lead of the ECOSTRESS mission and PI of the ROSES project to develop the JET ensemble approach.

We would like to thank Adam Purdy for developing the PT-JPL-SM model.

We would like to thank Kaniska Mallick for contributing the STIC model.

We would like to thank Youngryel Ryu for contributing the BESS-JPL model.

## References

- Abdelrady, A., Timmermans, J., Vekerdy, Z., Salama, M.S. (2016). Surface Energy Balance of Fresh and Saline Waters: AquaSEBS. *Remote Sensing*, 8, 583. https://doi.org/10.3390/rs8070583
- Allen, R.G., Tasumi, M., & Trezza, R. (2007). "Satellite-based energy balance for mapping evapotranspiration with internalized calibration (METRIC)—Model." *Journal of Irrigation and Drainage Engineering*, 133(4), 380-394. https://doi.org/10.1061/(ASCE)0733-9437(2007)133:4(380)
- Brutsaert, W. (1982). *Evaporation into the Atmosphere: Theory, History, and Applications*. Springer Netherlands. https://doi.org/10.1007/978-94-017-1497-6
- Fisher, J.B., Dohlen, M.B., Halverson, G.H., Collison, J.W., Hook, S.J., Hulley, G.C. (2023). Remotely sensed terrestrial open water evaporation. *Scientific Reports*, 13, 8217. https://doi.org/10.1038/s41598-023-34921-2
- Fisher, J.B., Tu, K.P., Baldocchi, D.D. (2008). Global estimates of the land–atmosphere water flux based on monthly AVHRR and ISLSCP-II data, validated at 16 FLUXNET sites. *Remote Sensing of Environment*, 112(3), 901-919. https://doi.org/10.1016/j.rse.2007.06.025
- Mallick, K., Trebs, I., Boegh, E., Giustarini, L., Schlerf, M., Drewry, D.T., Hoffmann, L., von Randow, C., Kruijt, B., Araùjo, A., Saleska, S., Ehleringer, J.R., Domingues, T.F., Ometto, J.P.H.B., Nobre, A.D., de Moraes, O.L.L., Hayek, M., Munger, J.W., Wofsy, S.C. (2016). Canopy-scale biophysical controls of transpiration and evaporation in the Amazon Basin. *Hydrology and Earth System Sciences*, 20, 4237-4264. https://doi.org/10.5194/hess-20-4237-2016
- Monteith, J.L. (1965). "Evaporation and Environment." *Symposia of the Society for Experimental Biology*, 19, 205-234.
- Penman, H.L. (1948). "Natural Evaporation from Open Water, Bare Soil and Grass." *Proceedings of the Royal Society of London. Series A, Mathematical and Physical Sciences*, 193(1032), 120-145. https://doi.org/10.1098/rspa.1948.0037
- Pierrat, Z., et al. (2025). "Validation of ECOSTRESS Collection 3 Evapotranspiration Products Using FLUXNET Measurements." *Remote Sensing of Environment* (in press).
- Purdy, A.J., Fisher, J.B., Goulden, M.L., Colliander, A., Halverson, G., Tu, K., Famiglietti, J.S. (2018). SMAP soil moisture improves global evapotranspiration. *Remote Sensing of Environment*, 219, 1-14. https://doi.org/10.1016/j.rse.2018.09.023
- Running, S., Mu, Q., Zhao, M., Moreno, A. (2019). MODIS Global Terrestrial Evapotranspiration (ET) Product (MOD16A2/A3 and MOD16A2GF/A3GF). NASA Earth Observing System Data and Information System (EOSDIS) Land Processes Distributed Active Archive Center (LP DAAC). https://doi.org/10.5067/MODIS/MOD16A2.061
- Ryu, Y., Baldocchi, D.D., Kobayashi, H., van Ingen, C., Li, J., Black, T.A., Beringer, J., van Gorsel, E., Knohl, A., Law, B.E., Roupsard, O. (2011). Integration of MODIS land and atmosphere products with a coupled-process model to estimate gross primary productivity and evapotranspiration from 1 km to global scales. *Global Biogeochemical Cycles*, 25, GB4017. https://doi.org/10.1029/2011GB004053
