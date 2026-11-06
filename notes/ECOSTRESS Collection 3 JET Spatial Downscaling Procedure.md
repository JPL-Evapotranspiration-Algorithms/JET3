# ECOSTRESS Collection 3 JET Spatial Downscaling Procedure

## 1. Purpose and scope

JET can estimate air temperature, relative humidity, and soil moisture on the fine raster grid used for a scene when those inputs were not supplied. The sharpening routines use fine-grid surface information to distribute coarse-grid GEOS-5 FP fields, then correct the fine predictions against the coarse GEOS-5 FP values.

The procedures described here are implemented in [`sharpen_meteorology_data`](../JET3/sharpen_meteorology_data.py), [`sharpen_soil_moisture_data`](../JET3/sharpen_soil_moisture_data.py), and called from [`JET`](../JET3/JET.py).

## 2. Grids, inputs, and resampling

- **Fine grid:** the `geometry` passed to JET, typically the ECOSTRESS scene grid. The routines use the supplied geometry rather than hard-coding a fine pixel size.
- **Coarse grid:** `geometry.rescale(13,720)`, where 13,720 m is `GEOS_IN_SENTINEL_COARSE_CELL_SIZE`. This is the target grid for the coarse GEOS-5 FP fields.
- **Fine predictors:** surface temperature `ST_C` (°C), NDVI, and albedo, all supplied on the fine grid.
- **Coarse target data:** GEOS-5 FP fields retrieved for the overpass timestamp and coarse geometry.
- **Resampling controls:** `upsampling` and `downsampling` are passed to the raster conversion and GEOS-5 FP retrieval calls. Defaults in `constants.py` are `"average"` and `"linear"`, respectively. These are configurable method names; the code applies them as specified and does not otherwise define their interpolation kernels.

The routines assume the rasters and geometries can be aligned by the raster library. Predictor rasters are converted to the coarse grid using `upsampling`; GEOS-5 FP fields are retrieved on the coarse grid using `downsampling`.

## 3. Shared regression-and-correction method

For each downscaled quantity (air temperature, dew-point temperature, and soil moisture), the routine:

1. Builds a table of paired coarse-grid target values and predictors. Raster arrays are flattened into samples and rows containing a NaN are dropped.
2. Fits an ordinary least-squares linear regression with an intercept, using `sklearn.linear_model.LinearRegression`. No regularization or spatially varying coefficients are applied.
3. Applies the fitted equation to the fine-grid predictors, producing a fine-grid prediction, \(P_f\).
4. Resamples \(P_f\) to the coarse grid using `upsampling`, producing \(P_c\).
5. Computes the coarse residual as **prediction minus GEOS-5 FP target**:

   \[
   E_c = P_c - Y_c
   \]

6. Converts that residual raster to the fine grid using `downsampling`, producing \(E_f\), and subtracts it from the fine prediction:

   \[
   P_{\mathrm{corrected}} = P_f - E_f
   \]

This transfers the coarse-scale prediction discrepancy back onto the fine grid. It is a residual adjustment; the code does not iterate the fit or guarantee exact conservation within every coarse cell after resampling.

The routines also resample the final fine result back to coarse resolution and calculate a final error raster. These final error rasters are diagnostic only: they are not used in another correction pass or returned by the routines.

## 4. Air temperature

### Coarse samples and fit

The routine obtains coarse GEOS-5 FP air temperature (`Ta_C_coarse`), dew-point temperature (`Td_C_coarse`), and soil moisture (`SM_coarse`). It also converts `ST_C`, NDVI, and albedo to the coarse geometry. A single complete-case sample table is made from all six fields; therefore a row is excluded if **any** of Ta_C, Td_C, SM, ST_C, NDVI, or albedo is NaN.

Using those samples, it independently fits:

\[
\widehat{Ta_C} = \beta_{0,Ta} + \beta_{1,Ta} ST_C
                 + \beta_{2,Ta} NDVI + \beta_{3,Ta} albedo
\]

The fitted equation is evaluated using fine-grid predictors. The shared residual-correction method above then produces corrected fine-grid Ta_C.

### Missing data and mask

After correction, NaNs are filled with GEOS-5 FP Ta_C retrieved/resampled directly to the fine geometry using `downsampling`. The routine then sets Ta_C to NaN wherever fine-grid `ST_C` is NaN. It applies the same surface-temperature mask to the returned `Ta_C_smooth` fallback raster.

The final coarse-grid error is calculated after this mask. If the final Ta_C raster is entirely NaN, the routine raises `BlankOutputError`.

## 5. Dew point and relative humidity

RH is **not** downscaled by fitting RH directly. The routine instead fits a coarse-grid dew-point regression with the same three predictors:

\[
\widehat{Td_C} = \beta_{0,Td} + \beta_{1,Td} ST_C
                 + \beta_{2,Td} NDVI + \beta_{3,Td} albedo
\]

It evaluates this relationship at fine resolution, applies the same coarse residual correction against `Td_C_coarse`, fills NaNs with GEOS-5 FP Td_C resampled to the fine grid, and masks locations where fine-grid `ST_C` is NaN.

It then calculates RH from the corrected dew point and corrected air temperature using the Magnus-form saturation-vapor-pressure ratio:

\[
RH = \operatorname{clip}_{[0,1]}
\left(
\frac{\exp\left(17.625\,Td_C/(243.04+Td_C)\right)}
     {\exp\left(17.625\,Ta_C/(243.04+Ta_C)\right)}
\right)
\]

Thus RH is a fraction from 0 to 1, not a percent. If the resulting RH raster is entirely NaN, the routine raises `BlankOutputError`. Dew point itself is not returned.

## 6. Soil moisture

### Coarse samples and fit

The soil-moisture routine builds its own complete-case table from coarse GEOS-5 FP soil moisture (`SM_coarse`) and coarse-grid ST_C, NDVI, and albedo. It fits:

\[
\widehat{SM} = \beta_{0,SM} + \beta_{1,SM} ST_C
              + \beta_{2,SM} NDVI + \beta_{3,SM} albedo
\]

The fit is applied to the fine-grid predictors. The initial fine prediction is clipped to \([0,1]\), corrected against `SM_coarse` by the shared residual method, and clipped again to \([0,1]\).

### Missing data and water mask

NaN values remaining after correction are filled with GEOS-5 FP soil moisture retrieved/resampled directly to the fine geometry using `downsampling`. The filled result is clipped to \([0,1]\), then pixels where `water_mask` is true are set to NaN. The water mask is applied at this stage; there is no corresponding water-mask operation in the meteorology sharpening routine.

The routine computes a final coarse-grid soil-moisture error raster after water masking, but does not feed that error back into the returned soil moisture. If the returned soil-moisture raster is entirely NaN, it raises `BlankOutputError`.

## 7. Invocation, fallback, and processing order

Sharpening flags default to enabled (`SHARPEN_METEOROLOGY` and `SHARPEN_SOIL_MOISTURE` are true). JET invokes these procedures only for raster processing and only when the corresponding input was not supplied:

- **Meteorology:** sharpening is attempted only when both `Ta_C` and `RH` are missing. If only one is missing, JET retrieves that field directly from GEOS-5 FP on the fine geometry; it does not sharpen just the missing member.
- **Soil moisture:** sharpening is attempted when `soil_moisture` is missing.
- **Failure:** exceptions during a sharpening attempt are logged, and JET falls back to retrieving the missing field(s) directly from GEOS-5 FP on the fine geometry. This fallback is spatial resampling, not regression-based sharpening.
- **Order:** meteorology sharpening runs before soil-moisture sharpening. The same coarse geometry is reused when already created.

After these retrieval/sharpening steps, JET may perform separate calibration or uncertainty-quantification operations if configured. Those are downstream procedures, not part of spatial downscaling.

## 8. Implementation notes and limitations

- The coarse regression coefficients are fitted for the particular scene/time from the available coarse samples; they are not fixed coefficients loaded from calibration files.
- The predictors are restricted to ST_C, NDVI, and albedo. The routines do not use elevation or explicitly model terrain, time-varying atmospheric structure, or spatial dependence.
- Meteorology's shared sample table includes `SM_coarse` as a column and drops any row with a NaN in any column, even though soil moisture is not a regression predictor or response in either meteorology fit. This means missing coarse soil moisture can reduce meteorology's training sample set.
- The code checks for an empty complete-case table and for entirely blank final output. It does not impose a minimum sample count beyond what the regression library requires, nor does it clip temperature or dew-point predictions.
- Soil moisture is bounded to [0,1], and RH is bounded to [0,1]. Air temperature and dew-point temperature are not clipped.
- `check_distribution` calls log/check raster distributions during processing; they do not alter the described fit or correction equations.