#!/usr/bin/env fish

set repo "JPL-Evapotranspiration-Algorithms/JET3"
set title "Feature/Bug: Add opt-in GEOS-5 FP bias correction for FLiES-ANN solar radiation (SWin_Wm2 / Rg)"
set spec_file "notes/2026-11-23 JET3 solar radiation issue.md"

if test -f "$spec_file"
    gh issue create \
        --repo "$repo" \
        --title "$title" \
        --body-file "$spec_file" \
        --label "enhancement"
else
    set body_file (mktemp /tmp/jet3_issue.XXXXXX.md)
    printf '%s\n' \
'### Summary' \
'During end-to-end reproduction testing of public ECOSTRESS Collection 3 Level-3 and Level-4 products (`L3T_ETAUX`, `L3T_JET`, `L4T_ESI`, and `L4T_WUE` for orbit `44841`, scene `1`, tile `11SPS`, `2026-06-02T18:00:12Z`) using `ECOv003-L3T-L4T-JET v1.23.0` and `JET3 v3.2.0`, meteorological downscaling (`Ta`, `SM`, `RH`) and masks (`cloud`, `water`) matched the public LP DAAC granules (`AuxiliaryNWP match : True`, `r = 1.00000`), while incoming shortwave solar radiation (`Rg` / `SWin_Wm2`) exhibited a **`+74.35 W/m²` positive bias** and degraded spatial correlation (`r = 0.38894`), propagating into `Rn` (`+58.38 W/m²`), `PET` (`+44.50 W/m²`), and the ensemble ET models.' \
'' \
'### Root Cause' \
'1. `JET3/constants.py` defines `BIAS_CORRECT_FLIES_ANN = True`, but `JET3/JET.py` never wired that constant into `JET()` and unconditionally set `SWin_Wm2 = SWin_FLiES_ANN_raw`.' \
'2. Because `ZERO_COT_CORRECTION = True` zeroes out coarse Cloud Optical Thickness (`COT = 0.0`), raw `FLiES-ANN` misses sub-grid and synoptic cloud/aerosol attenuation captured in GEOS-5 FP `tavg1_2d_rad_Nx` (`SWGDN` / `SWin`).' \
'3. Because `AuxiliaryNWP` already includes `GEOS.fp.asm.tavg1_2d_rad_Nx` (fetched for `COT`, `PAR_albedo`, and `NIR_albedo`), querying `GEOS5FP_connection.SWin(...)` reads cached local NetCDF4 files without additional downloads or changes to `AuxiliaryNWP`.' \
'' \
'### Locations' \
'- `JET3/constants.py`' \
'- `JET3/JET.py`' \
'- `tests/test_regressions.py`' \
'' \
'### Proposed Fix (`v3.3.0`)' \
'1. **`JET3/constants.py`:** Set `BIAS_CORRECT_FLIES_ANN = False` as the standalone default so `JET3.verify()` retains exact numerical compatibility with the frozen `ECOv002-cal-val-JET-outputs.csv` baseline (`rtol=1e-4, atol=1e-7`).' \
'2. **`JET3/JET.py`:** Add `bias_correct_FLiES_ANN: bool = BIAS_CORRECT_FLIES_ANN` to `JET()`. When `bias_correct_FLiES_ANN and processing_as_raster and not offline_mode` holds, apply coarse-scale residual bias correction against `GEOS5FP_connection.SWin(...)` on `coarse_geometry` (`13,720 m`) and clip at `0.0`:' \
'```python' \
'if bias_correct_FLiES_ANN and processing_as_raster and not offline_mode:' \
'    logger.info("bias-correcting FLiES-ANN solar radiation to GEOS-5 FP")' \
'    if coarse_geometry is None:' \
'        coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)' \
'' \
'    SWin_coarse_GEOS5FP = GEOS5FP_connection.SWin(' \
'        time_UTC=time_UTC,' \
'        geometry=coarse_geometry,' \
'        resampling=downsampling,' \
'    )' \
'    check_distribution(SWin_coarse_GEOS5FP, "SWin_coarse_GEOS5FP")' \
'' \
'    SWin_coarse_FLiES = SWin_FLiES_ANN_raw.to_geometry(coarse_geometry, resampling=upsampling)' \
'    check_distribution(SWin_coarse_FLiES, "SWin_coarse_FLiES")' \
'' \
'    SWin_bias_coarse = SWin_coarse_FLiES - SWin_coarse_GEOS5FP' \
'    check_distribution(SWin_bias_coarse, "SWin_bias_coarse")' \
'' \
'    SWin_bias_smooth = SWin_bias_coarse.to_geometry(geometry, resampling=downsampling)' \
'    check_distribution(SWin_bias_smooth, "SWin_bias_smooth")' \
'' \
'    SWin_Wm2 = rt.clip(SWin_FLiES_ANN_raw - SWin_bias_smooth, 0, None)' \
'    check_distribution(SWin_Wm2, "SWin_FLiES_ANN_bias_corrected")' \
'else:' \
'    SWin_Wm2 = SWin_FLiES_ANN_raw' \
'    check_distribution(SWin_Wm2, "SWin_FLiES_ANN")' \
'```' \
'3. **`tests/test_regressions.py`:** Add unit tests verifying both `bias_correct_FLiES_ANN=False` (default) and `bias_correct_FLiES_ANN=True` on a `Raster` geometry, and confirm `make verify` passes.' > "$body_file"

    gh issue create \
        --repo "$repo" \
        --title "$title" \
        --body-file "$body_file" \
        --label "enhancement"

    rm -f "$body_file"
end
