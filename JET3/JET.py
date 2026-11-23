"""
JET (Joint Evapotranspiration) Module

This module contains the main JET science function that orchestrates the calculation of 
evapotranspiration using multiple models (FLiES-ANN, BESS-JPL, STIC-JPL, PTJPLSM, PMJPL, AquaSEBS).
"""

import logging
import posixpath
import warnings
from datetime import datetime
from typing import Union, Dict

import numpy as np
import rasters as rt
from rasters import Raster, RasterGeometry
from pytictoc import TicToc

from GEOS5FP import GEOS5FPConnection
from MODISCI import MODISCI

from AquaSEBS import AquaSEBS
from BESS_JPL import BESS_JPL
from PMJPL import PMJPL
from PTJPLSM import PTJPLSM
from STIC_JPL import STIC_JPL
from FLiESANN import FLiESANN
from SEBAL_soil_heat_flux import calculate_SEBAL_soil_heat_flux
from verma_net_radiation import verma_net_radiation, daylight_Rn_integration_verma
from check_distribution import check_distribution
from gedi_canopy_height import load_canopy_height

from .constants import *
from .exceptions import *
from .calibrate_SM import calibrate_SM
from .calibrate_Ta_C import calibrate_Ta_C
from .calibrate_RH import calibrate_RH
from .generate_SM_uncalibrated_UQ import generate_SM_uncalibrated_UQ
from .generate_Ta_C_uncalibrated_UQ import generate_Ta_C_uncalibrated_UQ
from .generate_RH_uncalibrated_UQ import generate_RH_uncalibrated_UQ
from .generate_SM_calibrated_UQ import generate_SM_calibrated_UQ
from .generate_Ta_C_calibrated_UQ import generate_Ta_C_calibrated_UQ
from .generate_RH_calibrated_UQ import generate_RH_calibrated_UQ
from .sharpen_soil_moisture_data import sharpen_soil_moisture_data
from .sharpen_meteorology_data import sharpen_meteorology_data

logger = logging.getLogger(__name__)


def JET(
        ST_C: Union[Raster, np.ndarray, float],
        emissivity: Union[Raster, np.ndarray, float],
        NDVI: Union[Raster, np.ndarray, float],
        albedo: Union[Raster, np.ndarray, float],
        geometry: RasterGeometry,
        time_UTC: datetime,
        COT: Union[Raster, np.ndarray, float] = None,
        AOT: Union[Raster, np.ndarray, float] = None,
        vapor_gccm: Union[Raster, np.ndarray, float] = None,
        ozone_cm: Union[Raster, np.ndarray, float] = None,
        elevation_m: Union[Raster, np.ndarray, float] = None,
        SZA_deg: Union[Raster, np.ndarray, float] = None,
        KG_climate: Union[Raster, np.ndarray, str] = None,
        Ta_C: Union[Raster, np.ndarray, float] = None,
        Tmin_C: Union[Raster, np.ndarray, float] = None,
        RH: Union[Raster, np.ndarray, float] = None,
        soil_moisture: Union[Raster, np.ndarray, float] = None,
        PAR_albedo: Union[Raster, np.ndarray, float] = None,
        NIR_albedo: Union[Raster, np.ndarray, float] = None,
        Topt_C: Union[Raster, np.ndarray, float] = None,
        fAPARmax: Union[Raster, np.ndarray, float] = None,
        field_capacity: Union[Raster, np.ndarray, float] = None,
        wilting_point: Union[Raster, np.ndarray, float] = None,
        IGBP: Union[Raster, np.ndarray, int] = None,
        canopy_height_meters: Union[Raster, np.ndarray, float] = None,
        NDVI_minimum: Union[Raster, np.ndarray, float] = None,
        NDVI_maximum: Union[Raster, np.ndarray, float] = None,
        Ca: Union[Raster, np.ndarray, float] = None,
        CI: Union[Raster, np.ndarray, float] = None,
        wind_speed_mps: Union[Raster, np.ndarray, float] = None,
        canopy_temperature_C: Union[Raster, np.ndarray] = None,  # canopy temperature in Celsius (initialized to surface temperature if left as None)
        soil_temperature_C: Union[Raster, np.ndarray] = None,  # soil temperature in Celsius (initialized to surface temperature if left as None)
        ST_C_UQ: Union[Raster, np.ndarray, float] = None,  # surface temperature uncertainty (K)
        NDVI_UQ: Union[Raster, np.ndarray, float] = None,  # NDVI uncertainty (dimensionless)
        albedo_UQ: Union[Raster, np.ndarray, float] = None,  # albedo uncertainty (dimensionless)
        Ta_C_UQ: Union[Raster, np.ndarray, float] = None,  # air temperature uncertainty (K)
        RH_UQ: Union[Raster, np.ndarray, float] = None,  # relative humidity uncertainty (fraction or %)
        SM_UQ: Union[Raster, np.ndarray, float] = None,  # soil moisture uncertainty (m³/m³)
        C4_fraction: Union[Raster, np.ndarray] = None,  # fraction of C4 plants
        carbon_uptake_efficiency: Union[Raster, np.ndarray] = None,  # intrinsic quantum efficiency for carbon uptake
        kn: np.ndarray = None,
        ball_berry_intercept_C3: np.ndarray = None,  # Ball-Berry intercept for C3 plants
        ball_berry_intercept_C4: Union[np.ndarray, float] = BALL_BERRY_INTERCEPT_C4,  # Ball-Berry intercept for C4 plants
        ball_berry_slope_C3: np.ndarray = None,  # Ball-Berry slope for C3 plants
        ball_berry_slope_C4: np.ndarray = None,  # Ball-Berry slope for C4 plants
        peakVCmax_C3_μmolm2s1: np.ndarray = None,  # peak maximum carboxylation rate for C3 plants
        peakVCmax_C4_μmolm2s1: np.ndarray = None,  # peak maximum carboxylation rate for C4 plants
        MODISCI_connection: MODISCI = None,
        soil_grids_directory: str = None,
        GEDI_directory: str = None,
        Rn_model_name: str = None,
        GEOS5FP_connection: GEOS5FPConnection = None,
        water_mask: Union[Raster, np.ndarray, bool] = None,
        upsampling: str = UPSAMPLING,
        downsampling: str = DOWNSAMPLING,
        offline_mode: bool = False,
        include_water_surface: bool = True,
        generate_UQ: bool = False,
        use_calibration: bool = False,
        sharpen_soil_moisture: bool = SHARPEN_SOIL_MOISTURE,
        sharpen_meteorology: bool = SHARPEN_METEOROLOGY) -> Dict[str, Union[Raster, np.ndarray]]:
    """
    Main science function for JET (JPL Evapotranspiration Ensemble).

    This function orchestrates the calculation of evapotranspiration using multiple models
    including FLiES-ANN for solar radiation, BESS-JPL for GPP and ET, STIC-JPL for ET partitioning,
    PTJPLSM for ET with soil moisture, PMJPL for Penman-Monteith ET, and AquaSEBS for water surface
    evaporation.

    Returns:
        Dictionary containing all output variables including ET, GPP, WUE, and intermediate results

    Raises:
        BlankOutput: If critical output variables are all NaN or zero
    """
    # Initialize empty results dictionary to be populated throughout the workflow
    results = {}

    if offline_mode:
        offline_vars = []

        if AOT is None:
            offline_vars.append('AOT')

        if COT is None:
            offline_vars.append('COT')

        if Ca is None:
            Ca = 400

        if NIR_albedo is None:
            offline_vars.append('NIR_albedo')

        if PAR_albedo is None:
            offline_vars.append('PAR_albedo')

        if RH is None:
            offline_vars.append('RH')

        if soil_moisture is None:
            offline_vars.append('soil_moisture')

        if Ta_C is None:
            offline_vars.append('Ta_C')

        if Tmin_C is None:
            offline_vars.append('Tmin_C')

        if ozone_cm is None:
            offline_vars.append('ozone_cm')

        if vapor_gccm is None:
            offline_vars.append('vapor_gccm')

        if wind_speed_mps is None:
            offline_vars.append('wind_speed_mps')

        if offline_vars:
            raise MissingOfflineParameter(f"in offline mode, the following parameters must be provided: {', '.join(offline_vars)}")

    processing_as_raster = isinstance(ST_C, Raster)
    coarse_geometry = None
    Ta_C_smooth = Ta_C

    # Create GEOS5FP connection if not provided
    if GEOS5FP_connection is None:
        GEOS5FP_connection = GEOS5FPConnection()

    # Retrieve meteorological variables only when they were not supplied.
    if Ta_C is None or RH is None:
        # Sharpen meteorological variables if enabled and both variables are missing.
        if sharpen_meteorology and processing_as_raster and Ta_C is None and RH is None:
            try:
                coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)

                Ta_C, RH, Ta_C_smooth = sharpen_meteorology_data(
                    ST_C=ST_C,
                    NDVI=NDVI,
                    albedo=albedo,
                    geometry=geometry,
                    coarse_geometry=coarse_geometry,
                    time_UTC=time_UTC,
                    upsampling=upsampling,
                    downsampling=downsampling,
                    GEOS5FP_connection=GEOS5FP_connection
                )
            except Exception as e:
                logger.error(e)
                logger.warning("unable to sharpen meteorology")
                if Ta_C is None:
                    Ta_C = GEOS5FP_connection.Ta_C(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
                    Ta_C_smooth = Ta_C
                if RH is None:
                    RH = GEOS5FP_connection.RH(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
        else:
            if Ta_C is None:
                Ta_C = GEOS5FP_connection.Ta_C(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
                Ta_C_smooth = Ta_C
            if RH is None:
                RH = GEOS5FP_connection.RH(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)

    # Sharpen soil moisture if enabled
    if soil_moisture is None:
        if sharpen_soil_moisture and processing_as_raster:
            try:
                if coarse_geometry is None:
                    coarse_geometry = geometry.rescale(GEOS_IN_SENTINEL_COARSE_CELL_SIZE)

                soil_moisture = sharpen_soil_moisture_data(
                    ST_C=ST_C,
                    NDVI=NDVI,
                    albedo=albedo,
                    water_mask=water_mask,
                    geometry=geometry,
                    coarse_geometry=coarse_geometry,
                    time_UTC=time_UTC,
                    upsampling=upsampling,
                    downsampling=downsampling,
                    GEOS5FP_connection=GEOS5FP_connection
                )
            except Exception as e:
                logger.error(e)
                logger.warning("unable to sharpen soil moisture")
                soil_moisture = GEOS5FP_connection.SM(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
        else:
            soil_moisture = GEOS5FP_connection.SM(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)

    # Dynamically retrieve missing optional parameters needed for UQ and models
    if SZA_deg is None:
        logger.info("retrieving solar zenith angle")
        SZA_deg = rt.solar_zenith(geometry=geometry, time_UTC=time_UTC)

    if elevation_m is None:
        if hasattr(GEOS5FP_connection, "elevation_m"):
            logger.info("retrieving elevation_m from GEOS-5 FP")
            elevation_m = GEOS5FP_connection.elevation_m(geometry=geometry)
        elif hasattr(GEOS5FP_connection, "elevation"):
            logger.info("retrieving elevation from GEOS-5 FP")
            elevation_m = GEOS5FP_connection.elevation(geometry=geometry)
        else:
            logger.info("retrieving elevation from NASADEM")
            from NASADEM import NASADEM
            elevation_m = NASADEM.elevation_m(geometry=geometry)

    if wind_speed_mps is None:
        logger.info("retrieving wind speed from GEOS-5 FP")
        if hasattr(GEOS5FP_connection, "wind_speed_mps"):
            wind_speed_mps = GEOS5FP_connection.wind_speed_mps(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
        else:
            wind_speed_mps = GEOS5FP_connection.wind_speed(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)

    if canopy_height_meters is None and GEDI_directory is not None:
        logger.info("loading canopy height")
        canopy_height_meters = load_canopy_height(
            geometry=geometry,
            source_directory=GEDI_directory,
            resampling=downsampling
        )

    # include optional calibration and UQ generation for air temperature, relative humidity, and soil moisture
    # Generate uncalibrated UQ if requested (independent of calibration)
    if generate_UQ:
        logger.info("generating uncertainty quantification")

        if Ta_C is not None:
            logger.info("generating uncalibrated Ta_C UQ")
            Ta_C_UQ = generate_Ta_C_uncalibrated_UQ(
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

        if RH is not None:
            logger.info("generating uncalibrated RH UQ")
            RH_UQ = generate_RH_uncalibrated_UQ(
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

        if soil_moisture is not None:
            logger.info("generating uncalibrated SM UQ")
            SM_UQ = generate_SM_uncalibrated_UQ(
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

    # Apply calibration if requested (independent of UQ generation)
    if use_calibration:
        logger.info("applying calibration")

        if Ta_C is not None:
            logger.info("calibrating Ta_C")
            Ta_C = calibrate_Ta_C(
                Ta_C=Ta_C,
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

        if RH is not None:
            logger.info("calibrating RH")
            RH = calibrate_RH(
                RH=RH,
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

        if soil_moisture is not None:
            logger.info("calibrating soil moisture")
            soil_moisture = calibrate_SM(
                SM=soil_moisture,
                NDVI=NDVI,
                ST_C=ST_C,
                SZA_deg=SZA_deg,
                albedo=albedo,
                canopy_height_meters=canopy_height_meters,
                elevation_m=elevation_m,
                emissivity=emissivity,
                wind_speed_mps=wind_speed_mps
            )

        # Generate calibrated UQ if also generating UQ
        if generate_UQ:
            logger.info("generating calibrated UQ")

            if Ta_C is not None:
                logger.info("generating calibrated Ta_C UQ")
                Ta_C_UQ = generate_Ta_C_calibrated_UQ(
                    NDVI=NDVI,
                    ST_C=ST_C,
                    SZA_deg=SZA_deg,
                    albedo=albedo,
                    canopy_height_meters=canopy_height_meters,
                    elevation_m=elevation_m,
                    emissivity=emissivity,
                    wind_speed_mps=wind_speed_mps
                )

            if RH is not None:
                logger.info("generating calibrated RH UQ")
                RH_UQ = generate_RH_calibrated_UQ(
                    NDVI=NDVI,
                    ST_C=ST_C,
                    SZA_deg=SZA_deg,
                    albedo=albedo,
                    canopy_height_meters=canopy_height_meters,
                    elevation_m=elevation_m,
                    emissivity=emissivity,
                    wind_speed_mps=wind_speed_mps
                )

            if soil_moisture is not None:
                logger.info("generating calibrated SM UQ")
                SM_UQ = generate_SM_calibrated_UQ(
                    NDVI=NDVI,
                    ST_C=ST_C,
                    SZA_deg=SZA_deg,
                    albedo=albedo,
                    canopy_height_meters=canopy_height_meters,
                    elevation_m=elevation_m,
                    emissivity=emissivity,
                    wind_speed_mps=wind_speed_mps
                )

    # Add meteorology variables and their UQ to results after calibration/UQ generation
    if Ta_C is not None:
        results['Ta_C'] = Ta_C
        if generate_UQ and Ta_C_UQ is not None:
            results['Ta_C_UQ'] = Ta_C_UQ

    if RH is not None:
        results['RH'] = RH
        if generate_UQ and RH_UQ is not None:
            results['RH_UQ'] = RH_UQ

    if soil_moisture is not None:
        results['SM'] = soil_moisture
        if generate_UQ and SM_UQ is not None:
            results['SM_UQ'] = SM_UQ

    # Add optional input UQ if provided
    if ST_C_UQ is not None:
        results['ST_C_UQ'] = ST_C_UQ
    if NDVI_UQ is not None:
        results['NDVI_UQ'] = NDVI_UQ
    if albedo_UQ is not None:
        results['albedo_UQ'] = albedo_UQ

    # Run FLiES-ANN
    logger.info(f"running Forest Light Environmental Simulator")

    timer_flies = TicToc()
    timer_flies.tic()

    FLiES_results = FLiESANN(
        albedo=albedo,
        geometry=geometry,
        time_UTC=time_UTC,
        COT=COT,
        AOT=AOT,
        vapor_gccm=vapor_gccm,
        ozone_cm=ozone_cm,
        elevation_m=elevation_m,
        SZA_deg=SZA_deg,
        KG_climate=KG_climate,
        GEOS5FP_connection=GEOS5FP_connection,
        offline_mode=offline_mode
    )

    elapsed_time = timer_flies.tocvalue()
    logger.info(f"completed processing FLiES-ANN in {elapsed_time:.2f} seconds")

    # Extract FLiES-ANN results with updated variable names
    SWin_TOA_Wm2 = FLiES_results["SWin_TOA_Wm2"]
    SWin_FLiES_ANN_raw = FLiES_results["SWin_Wm2"]
    UV_Wm2 = FLiES_results["UV_Wm2"]
    PAR_Wm2 = FLiES_results["PAR_Wm2"]
    NIR_Wm2 = FLiES_results["NIR_Wm2"]
    PAR_diffuse_Wm2 = FLiES_results["PAR_diffuse_Wm2"]
    NIR_diffuse_Wm2 = FLiES_results["NIR_diffuse_Wm2"]
    PAR_direct_Wm2 = FLiES_results["PAR_direct_Wm2"]
    NIR_direct_Wm2 = FLiES_results["NIR_direct_Wm2"]

    # Add FLiES-ANN results to output
    results['SWin_TOA_Wm2'] = SWin_TOA_Wm2
    results['SWin_FLiES_ANN_raw'] = SWin_FLiES_ANN_raw
    results['UV_Wm2'] = UV_Wm2
    results['PAR_Wm2'] = PAR_Wm2
    results['NIR_Wm2'] = NIR_Wm2
    results['PAR_diffuse_Wm2'] = PAR_diffuse_Wm2
    results['NIR_diffuse_Wm2'] = NIR_diffuse_Wm2
    results['PAR_direct_Wm2'] = PAR_direct_Wm2
    results['NIR_direct_Wm2'] = NIR_direct_Wm2

    if PAR_albedo is None:
        if offline_mode:
            raise MissingOfflineParameter("PAR_albedo must be provided in offline mode")

        # Calculate PAR albedo
        albedo_NWP = GEOS5FP_connection.ALBEDO(time_UTC=time_UTC, geometry=geometry)
        RVIS_NWP = GEOS5FP_connection.ALBVISDR(time_UTC=time_UTC, geometry=geometry)
        PAR_albedo = rt.clip(albedo * (RVIS_NWP / albedo_NWP), 0, 1)

    check_distribution(PAR_albedo, "PAR_albedo")

    if NIR_albedo is None:
        if offline_mode:
            raise MissingOfflineParameter("NIR_albedo must be provided in offline mode")

        albedo_NWP = GEOS5FP_connection.ALBEDO(time_UTC=time_UTC, geometry=geometry)
        RNIR_NWP = GEOS5FP_connection.ALBNIRDR(time_UTC=time_UTC, geometry=geometry)
        NIR_albedo = rt.clip(albedo * (RNIR_NWP / albedo_NWP), 0, 1)

    check_distribution(NIR_albedo, "NIR_albedo")

    check_distribution(PAR_direct_Wm2, "PAR_direct_Wm2")

    # Use raw FLiES-ANN output directly without bias correction
    SWin_Wm2 = SWin_FLiES_ANN_raw
    check_distribution(SWin_Wm2, "SWin_FLiES_ANN")

    # Use FLiES-ANN solar radiation exclusively
    SWin = SWin_Wm2
    SWin = rt.where(np.isnan(ST_C), np.nan, SWin)

    # Check for blank output
    if np.all(np.isnan(SWin)) or np.all(SWin == 0):
        raise BlankOutput("blank solar radiation output")

    # Add finalized SWin to results
    results['SWin_Wm2'] = SWin_Wm2

    logger.info(f"running Breathing Earth System Simulator")

    timer_bess = TicToc()
    timer_bess.tic()

    BESS_results = BESS_JPL(
        ST_C=ST_C,
        NDVI=NDVI,
        albedo=albedo,
        elevation_m=elevation_m,
        geometry=geometry,
        time_UTC=time_UTC,
        GEOS5FP_connection=GEOS5FP_connection,
        MODISCI_connection=MODISCI_connection,
        Ta_C=Ta_C,
        RH=RH,
        COT=COT,
        AOT=AOT,
        SWin_Wm2=SWin_Wm2,
        PAR_diffuse_Wm2=PAR_diffuse_Wm2,
        PAR_direct_Wm2=PAR_direct_Wm2,
        NIR_diffuse_Wm2=NIR_diffuse_Wm2,
        NIR_direct_Wm2=NIR_direct_Wm2,
        UV_Wm2=UV_Wm2,
        PAR_albedo=PAR_albedo,
        NIR_albedo=NIR_albedo,
        vapor_gccm=vapor_gccm,
        ozone_cm=ozone_cm,
        KG_climate=KG_climate,
        canopy_height_meters=canopy_height_meters,
        NDVI_minimum=NDVI_minimum,
        NDVI_maximum=NDVI_maximum,
        Ca=Ca,
        wind_speed_mps=wind_speed_mps,
        SZA_deg=SZA_deg,
        canopy_temperature_C=canopy_temperature_C,
        soil_temperature_C=soil_temperature_C,
        C4_fraction=C4_fraction,
        carbon_uptake_efficiency=carbon_uptake_efficiency,
        kn=kn,
        ball_berry_intercept_C3=ball_berry_intercept_C3,
        ball_berry_intercept_C4=ball_berry_intercept_C4,
        ball_berry_slope_C3=ball_berry_slope_C3,
        ball_berry_slope_C4=ball_berry_slope_C4,
        peakVCmax_C3_μmolm2s1=peakVCmax_C3_μmolm2s1,
        peakVCmax_C4_μmolm2s1=peakVCmax_C4_μmolm2s1,
        CI=CI,
        GEDI_download_directory=GEDI_directory,
        upscale_to_daylight=True,
        offline_mode=offline_mode
    )

    elapsed_time = timer_bess.tocvalue()
    logger.info(f"completed processing BESS-JPL in {elapsed_time:.2f} seconds")

    Rn_BESS_Wm2 = BESS_results["Rn_Wm2"]
    check_distribution(Rn_BESS_Wm2, "Rn_BESS_Wm2")
    G_BESS_Wm2 = BESS_results["G_Wm2"]
    check_distribution(G_BESS_Wm2, "G_BESS_Wm2")

    LE_BESS_Wm2 = BESS_results["LE_Wm2"]
    check_distribution(LE_BESS_Wm2, "LE_BESS_Wm2")

    ET_daylight_BESS_kg = BESS_results["ET_daylight_kg"]

    EF_BESS = rt.where((LE_BESS_Wm2 == 0) | ((Rn_BESS_Wm2 - G_BESS_Wm2) == 0), 0, LE_BESS_Wm2 / (Rn_BESS_Wm2 - G_BESS_Wm2))

    Rn_daily_BESS = daylight_Rn_integration_verma(
        Rn_Wm2=Rn_BESS_Wm2,
        time_UTC=time_UTC,
        geometry=geometry
    )

    LE_daily_BESS = rt.clip(EF_BESS * Rn_daily_BESS, 0, None)

    if water_mask is not None:
        LE_BESS_Wm2 = rt.where(water_mask, np.nan, LE_BESS_Wm2)

    check_distribution(LE_BESS_Wm2, "LE_BESS_Wm2")

    GPP_inst_umol_m2_s = BESS_results["GPP"]

    if water_mask is not None:
        GPP_inst_umol_m2_s = rt.where(water_mask, np.nan, GPP_inst_umol_m2_s)

    check_distribution(GPP_inst_umol_m2_s, "GPP_inst_umol_m2_s")

    if np.all(np.isnan(GPP_inst_umol_m2_s)):
        raise BlankOutput("blank GPP output")

    NWP_filenames = sorted([posixpath.basename(filename) for filename in GEOS5FP_connection.filenames])
    AuxiliaryNWP = ",".join(NWP_filenames)

    # Add BESS results to output
    results['Rn_BESS_Wm2'] = Rn_BESS_Wm2
    results['LE_BESS_Wm2'] = LE_BESS_Wm2
    results['ET_daylight_BESS_kg'] = ET_daylight_BESS_kg
    results['EF_BESS'] = EF_BESS
    results['Rn_daily_BESS'] = Rn_daily_BESS
    results['LE_daily_BESS'] = LE_daily_BESS
    results['GPP_inst_umol_m2_s'] = GPP_inst_umol_m2_s
    results['AuxiliaryNWP'] = AuxiliaryNWP

    verma_results = verma_net_radiation(
        SWin_Wm2=SWin_Wm2,
        albedo=albedo,
        ST_C=ST_C,
        emissivity=emissivity,
        Ta_C=Ta_C,
        RH=RH,
        offline_mode=offline_mode
    )

    Rn_verma_Wm2 = verma_results["Rn_Wm2"]

    if Rn_model_name == "verma":
        Rn_Wm2 = Rn_verma_Wm2
    elif Rn_model_name == "BESS":
        Rn_Wm2 = Rn_BESS_Wm2
    else:
        raise ValueError(f"unrecognized net radiation model: {Rn_model_name}")

    if np.all(np.isnan(Rn_Wm2)) or np.all(Rn_Wm2 == 0):
        raise BlankOutput("blank net radiation output")

    # Add net radiation results to output
    results['Rn_verma_Wm2'] = Rn_verma_Wm2
    results['Rn_Wm2'] = Rn_Wm2

    logger.info(f"running Surface Temperature Initiated Closure")

    timer_stic = TicToc()
    timer_stic.tic()

    STIC_results = STIC_JPL(
        geometry=geometry,
        time_UTC=time_UTC,
        Rn_Wm2=Rn_Wm2,
        RH=RH,
        Ta_C=Ta_C,
        ST_C=ST_C,
        albedo=albedo,
        emissivity=emissivity,
        NDVI=NDVI,
        max_iterations=3,
        upscale_to_daylight=True,
        offline_mode=offline_mode
    )

    elapsed_time = timer_stic.tocvalue()
    logger.info(f"completed processing STIC-JPL in {elapsed_time:.2f} seconds")

    LE_STIC_Wm2 = STIC_results["LE_Wm2"]
    check_distribution(LE_STIC_Wm2, "LE_STIC_Wm2")

    ET_daylight_STIC_kg = STIC_results["ET_daylight_kg"]
    check_distribution(ET_daylight_STIC_kg, "ET_daylight_STIC_kg")

    LE_canopy_STIC_Wm2 = STIC_results["LE_canopy_Wm2"]
    check_distribution(LE_canopy_STIC_Wm2, "LE_canopy_STIC_Wm2")

    G_STIC_Wm2 = STIC_results["G_Wm2"]
    check_distribution(G_STIC_Wm2, "G_STIC_Wm2")

    # Suppress expected divide warnings - rt.where handles the division safely
    with np.errstate(divide='ignore', invalid='ignore'):
        LE_canopy_fraction_STIC = rt.clip(rt.where((LE_canopy_STIC_Wm2 == 0) | (LE_STIC_Wm2 == 0), 0, LE_canopy_STIC_Wm2 / LE_STIC_Wm2), 0, 1)
    check_distribution(LE_canopy_fraction_STIC, "LE_canopy_fraction_STIC")

    with np.errstate(divide='ignore', invalid='ignore'):
        EF_STIC = rt.where((LE_STIC_Wm2 == 0) | ((Rn_Wm2 - G_STIC_Wm2) == 0), 0, LE_STIC_Wm2 / (Rn_Wm2 - G_STIC_Wm2))

    # Add STIC results to output
    results['LE_STIC_Wm2'] = LE_STIC_Wm2
    results['ET_daylight_STIC_kg'] = ET_daylight_STIC_kg
    results['LE_canopy_STIC_Wm2'] = LE_canopy_STIC_Wm2
    results['G_STIC_Wm2'] = G_STIC_Wm2
    results['LE_canopy_fraction_STIC'] = LE_canopy_fraction_STIC
    results['EF_STIC'] = EF_STIC

    G_SEBAL_Wm2 = calculate_SEBAL_soil_heat_flux(
        Rn=Rn_Wm2,
        ST_C=ST_C,
        NDVI=NDVI,
        albedo=albedo
    )

    logger.info(f"running Priestley-Taylor JPL with Soil Moisture")

    timer_ptjplsm = TicToc()
    timer_ptjplsm.tic()

    PTJPLSM_results = PTJPLSM(
        geometry=geometry,
        time_UTC=time_UTC,
        ST_C=ST_C,
        emissivity=emissivity,
        NDVI=NDVI,
        albedo=albedo,
        G_Wm2=G_SEBAL_Wm2,
        Rn_Wm2=Rn_Wm2,
        Ta_C=Ta_C,
        RH=RH,
        soil_moisture=soil_moisture,
        Topt_C=Topt_C,
        fAPARmax=fAPARmax,
        field_capacity=field_capacity,
        field_capacity_directory=soil_grids_directory,
        wilting_point=wilting_point,
        wilting_point_directory=soil_grids_directory,
        canopy_height_meters=canopy_height_meters,
        canopy_height_directory=GEDI_directory,
        upscale_to_daylight=True,
        offline_mode=offline_mode
    )

    elapsed_time = timer_ptjplsm.tocvalue()
    logger.info(f"completed processing PT-JPL-SM in {elapsed_time:.2f} seconds")

    LE_PTJPLSM_Wm2 = rt.clip(PTJPLSM_results["LE_Wm2"], 0, None)
    check_distribution(LE_PTJPLSM_Wm2, "LE_PTJPLSM_Wm2")

    ET_daylight_PTJPLSM_kg = PTJPLSM_results["ET_daylight_kg"]
    check_distribution(ET_daylight_PTJPLSM_kg, "ET_daylight_PTJPLSM_kg")

    G_PTJPLSM = PTJPLSM_results["G_Wm2"]
    check_distribution(G_PTJPLSM, "G_PTJPLSM")

    with np.errstate(divide='ignore', invalid='ignore'):
        EF_PTJPLSM = rt.where((LE_PTJPLSM_Wm2 == 0) | ((Rn_Wm2 - G_PTJPLSM) == 0), 0, LE_PTJPLSM_Wm2 / (Rn_Wm2 - G_PTJPLSM))
    check_distribution(EF_PTJPLSM, "EF_PTJPLSM")

    if np.all(np.isnan(LE_PTJPLSM_Wm2)):
        raise BlankOutput("blank PT-JPL-SM instantaneous ET output")

    if np.all(np.isnan(ET_daylight_PTJPLSM_kg)):
        raise BlankOutput("blank PT-JPL-SM daily ET output")

    LE_canopy_PTJPLSM_Wm2 = rt.clip(PTJPLSM_results["LE_canopy_Wm2"], 0, None)
    check_distribution(LE_canopy_PTJPLSM_Wm2, "LE_canopy_PTJPLSM_Wm2")

    with np.errstate(divide='ignore', invalid='ignore'):
        LE_canopy_fraction_PTJPLSM = rt.clip(LE_canopy_PTJPLSM_Wm2 / LE_PTJPLSM_Wm2, 0, 1)
    check_distribution(LE_canopy_fraction_PTJPLSM, "LE_canopy_fraction_PTJPLSM")

    if water_mask is not None:
        LE_canopy_fraction_PTJPLSM = rt.where(water_mask, np.nan, LE_canopy_fraction_PTJPLSM)

    LE_soil_PTJPLSM_Wm2 = rt.clip(PTJPLSM_results["LE_soil_Wm2"], 0, None)
    check_distribution(LE_soil_PTJPLSM_Wm2, "LE_soil_PTJPLSM_Wm2")

    with np.errstate(divide='ignore', invalid='ignore'):
        LE_soil_fraction_PTJPLSM = rt.clip(LE_soil_PTJPLSM_Wm2 / LE_PTJPLSM_Wm2, 0, 1)

    if water_mask is not None:
        LE_soil_fraction_PTJPLSM = rt.where(water_mask, np.nan, LE_soil_fraction_PTJPLSM)

    check_distribution(LE_soil_fraction_PTJPLSM, "LE_soil_fraction_PTJPLSM")

    LE_interception_PTJPLSM_Wm2 = rt.clip(PTJPLSM_results["LE_interception_Wm2"], 0, None)
    check_distribution(LE_interception_PTJPLSM_Wm2, "LE_interception_PTJPLSM_Wm2")

    with np.errstate(divide='ignore', invalid='ignore'):
        LE_interception_fraction_PTJPLSM = rt.clip(LE_interception_PTJPLSM_Wm2 / LE_PTJPLSM_Wm2, 0, 1)

    if water_mask is not None:
        LE_interception_fraction_PTJPLSM = rt.where(water_mask, np.nan, LE_interception_fraction_PTJPLSM)

    check_distribution(LE_interception_fraction_PTJPLSM, "LE_interception_fraction_PTJPLSM")

    PET_instantaneous_PTJPLSM_Wm2 = rt.clip(PTJPLSM_results["PET_Wm2"], 0, None)
    check_distribution(PET_instantaneous_PTJPLSM_Wm2, "PET_instantaneous_PTJPLSM_Wm2")

    with np.errstate(divide='ignore', invalid='ignore'):
        ESI_PTJPLSM = rt.clip(LE_PTJPLSM_Wm2 / PET_instantaneous_PTJPLSM_Wm2, 0, 1)

    if water_mask is not None:
        ESI_PTJPLSM = rt.where(water_mask, np.nan, ESI_PTJPLSM)

    check_distribution(ESI_PTJPLSM, "ESI_PTJPLSM")

    if np.all(np.isnan(ESI_PTJPLSM)):
        raise BlankOutput("blank ESI output")

    # Add PTJPLSM results to output
    results['LE_PTJPLSM_Wm2'] = LE_PTJPLSM_Wm2
    results['ET_daylight_PTJPLSM_kg'] = ET_daylight_PTJPLSM_kg
    results['G_PTJPLSM'] = G_PTJPLSM
    results['EF_PTJPLSM'] = EF_PTJPLSM
    results['LE_canopy_PTJPLSM_Wm2'] = LE_canopy_PTJPLSM_Wm2
    results['LE_canopy_fraction_PTJPLSM'] = LE_canopy_fraction_PTJPLSM
    results['LE_soil_PTJPLSM_Wm2'] = LE_soil_PTJPLSM_Wm2
    results['LE_soil_fraction_PTJPLSM'] = LE_soil_fraction_PTJPLSM
    results['LE_interception_PTJPLSM_Wm2'] = LE_interception_PTJPLSM_Wm2
    results['LE_interception_fraction_PTJPLSM'] = LE_interception_fraction_PTJPLSM
    results['PET_instantaneous_PTJPLSM_Wm2'] = PET_instantaneous_PTJPLSM_Wm2
    results['ESI_PTJPLSM'] = ESI_PTJPLSM

    logger.info(f"running Penman-Monteith JPL")

    timer_pmjpl = TicToc()
    timer_pmjpl.tic()

    PMJPL_results = PMJPL(
        geometry=geometry,
        time_UTC=time_UTC,
        ST_C=ST_C,
        emissivity=emissivity,
        NDVI=NDVI,
        albedo=albedo,
        Ta_C=Ta_C,
        Tmin_C=Tmin_C,
        RH=RH,
        elevation_m=elevation_m,
        IGBP=IGBP,
        Rn_Wm2=Rn_Wm2,
        G_Wm2=G_SEBAL_Wm2,
        GEOS5FP_connection=GEOS5FP_connection,
        upscale_to_daylight=True,
        offline_mode=offline_mode
    )

    elapsed_time = timer_pmjpl.tocvalue()
    logger.info(f"completed processing PM-JPL in {elapsed_time:.2f} seconds")

    LE_PMJPL_Wm2 = PMJPL_results["LE_Wm2"]
    check_distribution(LE_PMJPL_Wm2, "LE_PMJPL_Wm2")

    ET_daylight_PMJPL_kg = PMJPL_results["ET_daylight_kg"]
    check_distribution(ET_daylight_PMJPL_kg, "ET_daylight_PMJPL_kg")

    G_PMJPL_Wm2 = PMJPL_results["G_Wm2"]
    check_distribution(G_PMJPL_Wm2, "G_PMJPL_Wm2")

    # Add PMJPL results to output
    results['LE_PMJPL_Wm2'] = LE_PMJPL_Wm2
    results['ET_daylight_PMJPL_kg'] = ET_daylight_PMJPL_kg
    results['G_PMJPL_Wm2'] = G_PMJPL_Wm2

    # Suppress expected RuntimeWarning for all-NaN slices in median calculations
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
        G_Wm2 = np.nanmedian([np.array(G_BESS_Wm2), np.array(G_STIC_Wm2), np.array(G_SEBAL_Wm2)], axis=0)
        LE_instantaneous_Wm2 = np.nanmedian([np.array(LE_PTJPLSM_Wm2), np.array(LE_BESS_Wm2), np.array(LE_PMJPL_Wm2), np.array(LE_STIC_Wm2)], axis=0)

    LE_Wm2 = LE_instantaneous_Wm2

    H_Wm2 = Rn_Wm2 - G_Wm2 - LE_Wm2

    if processing_as_raster:
        LE_instantaneous_Wm2 = rt.Raster(LE_instantaneous_Wm2, geometry=geometry)

    # Add aggregated energy balance results to output
    results['G_Wm2'] = G_Wm2
    results['LE_instantaneous_Wm2'] = LE_instantaneous_Wm2
    results['LE_Wm2'] = LE_Wm2
    results['H_Wm2'] = H_Wm2
    results['wind_speed_mps'] = wind_speed_mps

    if include_water_surface:
        if wind_speed_mps is None:
            raise MissingOfflineParameter("wind_speed_mps must be provided in offline mode")

        check_distribution(wind_speed_mps, "wind_speed_mps")

        SWnet_Wm2 = SWin_Wm2 * (1 - albedo)
        check_distribution(SWnet_Wm2, "SWnet_Wm2")

        logger.info("checking input distributions for AquaSEBS")
        check_distribution(ST_C, "ST_C")
        check_distribution(emissivity, "emissivity")
        check_distribution(albedo, "albedo")
        check_distribution(Ta_C, "Ta_C")
        check_distribution(RH, "RH")
        check_distribution(wind_speed_mps, "windspeed_mps")
        check_distribution(SWnet_Wm2, "SWnet")
        check_distribution(Rn_Wm2, "Rn_Wm2")
        check_distribution(SWin_Wm2, "SWin_Wm2")

        logger.info(f"running AquaSEBS")

        timer_aquasebs = TicToc()
        timer_aquasebs.tic()

        AquaSEBS_results = AquaSEBS(
            WST_C=ST_C,
            emissivity=emissivity,
            albedo=albedo,
            Ta_C=Ta_C,
            RH=RH,
            windspeed_mps=wind_speed_mps,
            SWnet=SWnet_Wm2,
            Rn_Wm2=Rn_Wm2,
            SWin_Wm2=SWin_Wm2,
            geometry=geometry,
            time_UTC=time_UTC,
            water=water_mask,
            GEOS5FP_connection=GEOS5FP_connection,
            upscale_to_daylight=True,
            offline_mode=offline_mode
        )

        elapsed_time = timer_aquasebs.tocvalue()
        logger.info(f"completed processing AquaSEBS in {elapsed_time:.2f} seconds")

        for key, value in AquaSEBS_results.items():
            check_distribution(value, key)

        LE_AquaSEBS_Wm2 = AquaSEBS_results["LE_Wm2"]
        check_distribution(LE_AquaSEBS_Wm2, "LE_AquaSEBS_Wm2")

        if water_mask is not None:
            LE_instantaneous_Wm2 = rt.where(water_mask, LE_AquaSEBS_Wm2, LE_instantaneous_Wm2)
        check_distribution(LE_instantaneous_Wm2, "LE_instantaneous_Wm2")

        ET_daylight_AquaSEBS_kg = AquaSEBS_results["ET_daylight_kg"]
        check_distribution(ET_daylight_AquaSEBS_kg, "ET_daylight_AquaSEBS_kg")

        # Add AquaSEBS results to output
        results['LE_AquaSEBS_Wm2'] = LE_AquaSEBS_Wm2
        results['ET_daylight_AquaSEBS_kg'] = ET_daylight_AquaSEBS_kg
        results['SWnet_Wm2'] = SWnet_Wm2

        # Update aggregated LE with water surface values
        results['LE_instantaneous_Wm2'] = LE_instantaneous_Wm2

    # Suppress expected RuntimeWarning for all-NaN slices in median calculation
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
        ET_daylight_kg = np.nanmedian([
            np.array(ET_daylight_PTJPLSM_kg),
            np.array(ET_daylight_BESS_kg),
            np.array(ET_daylight_PMJPL_kg),
            np.array(ET_daylight_STIC_kg)
        ], axis=0)

    if isinstance(geometry, RasterGeometry):
        ET_daylight_kg = rt.Raster(ET_daylight_kg, geometry=geometry)

    if include_water_surface and water_mask is not None:
        # overlay water surface evaporation on top of daylight evapotranspiration aggregate only for masked water pixels
        ET_daylight_kg = rt.where(
            water_mask & ~np.isnan(ET_daylight_AquaSEBS_kg),
            ET_daylight_AquaSEBS_kg,
            ET_daylight_kg,
        )

    check_distribution(ET_daylight_kg, "ET_daylight_kg")

    # Suppress expected RuntimeWarning for all-NaN slices in uncertainty calculation
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
        ET_uncertainty = np.nanstd([
            np.array(ET_daylight_PTJPLSM_kg),
            np.array(ET_daylight_BESS_kg),
            np.array(ET_daylight_PMJPL_kg),
            np.array(ET_daylight_STIC_kg)
        ], axis=0)

    if isinstance(geometry, RasterGeometry):
        ET_uncertainty = rt.Raster(ET_uncertainty, geometry=geometry)

    GPP_inst_g_m2_s = GPP_inst_umol_m2_s / 1000000 * 12.011
    ET_canopy_inst_kg_m2_s = LE_canopy_PTJPLSM_Wm2 / LATENT_VAPORIZATION_JOULES_PER_KILOGRAM
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        WUE = np.divide(GPP_inst_g_m2_s, ET_canopy_inst_kg_m2_s)
    # Mask cases with no canopy latent energy (undefined WUE), then cap large ratios
    WUE = rt.where(np.isnan(LE_canopy_PTJPLSM_Wm2) | (LE_canopy_PTJPLSM_Wm2 <= 0), np.nan, WUE)
    WUE = rt.clip(WUE, 0, 10)

    # Add final aggregated results to output
    results['ET_daylight_kg'] = ET_daylight_kg
    results['ET_uncertainty'] = ET_uncertainty
    results['GPP_inst_g_m2_s'] = GPP_inst_g_m2_s
    results['ET_canopy_inst_kg_m2_s'] = ET_canopy_inst_kg_m2_s
    results['WUE'] = WUE

    return results
