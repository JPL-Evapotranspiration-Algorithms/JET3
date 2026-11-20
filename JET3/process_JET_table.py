"""
Module: process_JET_table.py

This module provides a function to process input data for the JET (JPL Evapotranspiration Ensemble) model.
It prepares the required variables from a pandas DataFrame, handles missing or alternative column names, computes derived variables as needed, and runs the JET ensemble to generate output variables, which are appended to the input DataFrame.
"""
import logging

import numpy as np
import pandas as pd
from pandas import DataFrame
from shapely.geometry import Point
from dateutil import parser
from pytictoc import TicToc

from rasters import MultiPoint, WGS84
from SEBAL_soil_heat_flux import calculate_SEBAL_soil_heat_flux
from PTJPL import load_Topt, load_fAPARmax

from .constants import *
from .JET import JET

logger = logging.getLogger(__name__)

def process_JET_table(
        input_df: DataFrame,
        upscale_to_daylight: bool = UPSCALE_TO_DAYLIGHT,
        regenerate_net_radiation: bool = False,
        GEOS5FP_connection=None,
        MODISCI_connection=None,
        soil_grids_directory: str = None,
        GEDI_directory: str = None,
        Rn_model_name: str = "verma",
        downsampling: str = "average",
        offline_mode: bool = False,
        include_water_surface: bool = False,
        generate_UQ: bool = False,
        use_calibration: bool = False
        ) -> DataFrame:
    """
    Processes an input DataFrame to prepare all required variables for the JET model ensemble,
    runs the model, and returns a DataFrame with the model outputs appended as new columns.
    """
    logger.info("starting JET table processing")
    timer = TicToc()
    timer.tic()

    # Extract and typecast surface temperature (ST_C) and NDVI
    ST_C = np.array(input_df["ST_C"]).astype(np.float64)
    emissivity = np.array(input_df["emissivity"]).astype(np.float64)
    NDVI = np.array(input_df["NDVI"]).astype(np.float64)

    # Mask NDVI values below threshold (0.06) as NaN
    NDVI = np.where(NDVI > 0.06, NDVI, np.nan).astype(np.float64)

    # Extract and typecast albedo
    albedo = np.array(input_df["albedo"]).astype(np.float64)

    # Handle air temperature column name differences (Ta_C or Ta) and optional online columns
    if "Ta_C" in input_df:
        Ta_C = np.array(input_df["Ta_C"], dtype=np.float64)
    elif "Ta" in input_df:
        Ta_C = np.array(input_df["Ta"], dtype=np.float64)
    else:
        Ta_C = None

    Tmin_C = np.array(input_df["Tmin_C"], dtype=np.float64) if "Tmin_C" in input_df else None

    # Extract and typecast relative humidity and soil moisture if present
    RH = np.array(input_df["RH"], dtype=np.float64) if "RH" in input_df else None
    soil_moisture = np.array(input_df["SM"], dtype=np.float64) if "SM" in input_df else None

    def parse_value(val):
        """Parse a value that might be a string representation of an array or a direct number."""
        if isinstance(val, str):
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                # Parse string array like '[48.49867191]'
                val = val.strip('[]')
                return float(val)
        return float(val)
    
    # Extract optional atmospheric and environmental variables (default to None if not present)
    COT = np.array([parse_value(v) for v in input_df.COT]).astype(np.float64) if "COT" in input_df else None
    AOT = np.array([parse_value(v) for v in input_df.AOT]).astype(np.float64) if "AOT" in input_df else None
    vapor_gccm = np.array([parse_value(v) for v in input_df.vapor_gccm]).astype(np.float64) if "vapor_gccm" in input_df else None
    ozone_cm = np.array([parse_value(v) for v in input_df.ozone_cm]).astype(np.float64) if "ozone_cm" in input_df else None
    elevation_m = np.array([parse_value(v) for v in input_df.elevation_m]).astype(np.float64) if "elevation_m" in input_df else None
    SZA_deg = np.array([parse_value(v) for v in input_df.SZA_deg]).astype(np.float64) if "SZA_deg" in input_df else None
    KG_climate = np.array([parse_value(v) for v in input_df.KG_climate]).astype(np.float64) if "KG_climate" in input_df else None
    Ca = np.array([parse_value(v) for v in input_df.Ca]).astype(np.float64) if "Ca" in input_df else None
    PAR_albedo = np.array([parse_value(v) for v in input_df.PAR_albedo]).astype(np.float64) if "PAR_albedo" in input_df else None 
    NIR_albedo = np.array([parse_value(v) for v in input_df.NIR_albedo]).astype(np.float64) if "NIR_albedo" in input_df else None
    water_mask = np.array(input_df.water_mask).astype(bool) if "water_mask" in input_df else None    
    wind_speed_mps = np.array([parse_value(v) for v in input_df.wind_speed_mps]).astype(np.float64) if "wind_speed_mps" in input_df else None
    CI = np.array([parse_value(v) for v in input_df.CI]).astype(np.float64) if "CI" in input_df else None
    canopy_temperature_C = np.array([parse_value(v) for v in input_df.canopy_temperature_C]).astype(np.float64) if "canopy_temperature_C" in input_df else None
    soil_temperature_C = np.array([parse_value(v) for v in input_df.soil_temperature_C]).astype(np.float64) if "soil_temperature_C" in input_df else None
    C4_fraction = np.array([parse_value(v) for v in input_df.C4_fraction]).astype(np.float64) if "C4_fraction" in input_df else None
    carbon_uptake_efficiency = np.array([parse_value(v) for v in input_df.carbon_uptake_efficiency]).astype(np.float64) if "carbon_uptake_efficiency" in input_df else None
    kn = np.array([parse_value(v) for v in input_df.kn]).astype(np.float64) if "kn" in input_df else None
    ball_berry_intercept_C3 = np.array([parse_value(v) for v in input_df.ball_berry_intercept_C3]).astype(np.float64) if "ball_berry_intercept_C3" in input_df else None
    ball_berry_intercept_C4 = np.array([parse_value(v) for v in input_df.ball_berry_intercept_C4]).astype(np.float64) if "ball_berry_intercept_C4" in input_df else None
    ball_berry_slope_C3 = np.array([parse_value(v) for v in input_df.ball_berry_slope_C3]).astype(np.float64) if "ball_berry_slope_C3" in input_df else None                          
    ball_berry_slope_C4 = np.array([parse_value(v) for v in input_df.ball_berry_slope_C4]).astype(np.float64) if "ball_berry_slope_C4" in input_df else None
    
    peakVCmax_C3_μmolm2s1 = np.array([parse_value(v) for v in (input_df.peakVCmax_C3_μmolm2s1 if "peakVCmax_C3_μmolm2s1" in input_df else input_df.peakVCmax_C3)]).astype(np.float64) if ("peakVCmax_C3_μmolm2s1" in input_df or "peakVCmax_C3" in input_df) else None
    
    peakVCmax_C4_μmolm2s1 = np.array([parse_value(v) for v in (input_df.peakVCmax_C4_μmolm2s1 if "peakVCmax_C4_μmolm2s1" in input_df else input_df.peakVCmax_C4)]).astype(np.float64) if ("peakVCmax_C4_μmolm2s1" in input_df or "peakVCmax_C4" in input_df) else None
    
    Topt_C = np.array([parse_value(v) for v in input_df.Topt_C]).astype(np.float64) if "Topt_C" in input_df else None
    fAPARmax = np.array([parse_value(v) for v in input_df.fAPARmax]).astype(np.float64) if "fAPARmax" in input_df else None
    field_capacity = np.array([parse_value(v) for v in input_df.field_capacity]).astype(np.float64) if "field_capacity" in input_df else None
    wilting_point = np.array([parse_value(v) for v in input_df.wilting_point]).astype(np.float64) if "wilting_point" in input_df else None
    
    # Handle NaN values before casting to int8
    if "IGBP" in input_df:
        # First convert to float64 to handle NaN properly
        igbp_array = np.array(input_df.IGBP, dtype=np.float64)
        # Replace NaN with -1 (invalid IGBP code) before converting to int8
        IGBP = np.where(np.isnan(igbp_array), -1, igbp_array).astype(np.int8)
    else:
        IGBP = None
    
    canopy_height_meters = np.array(input_df.canopy_height_meters).astype(np.float64) if "canopy_height_meters" in input_df else None
    NDVI_minimum = np.array(input_df.NDVI_minimum).astype(np.float64) if "NDVI_minimum" in input_df else None
    NDVI_maximum = np.array(input_df.NDVI_maximum).astype(np.float64) if "NDVI_maximum" in input_df else None

    def ensure_geometry(df):
        if "geometry" in df:
            if isinstance(df.geometry.iloc[0], str):
                def parse_geom(s):
                    s = s.strip()
                    if s.startswith("POINT"):
                        coords = s.replace("POINT", "").replace("(", "").replace(")", "").strip().split()
                        return Point(float(coords[0]), float(coords[1]))
                    elif "," in s:
                        coords = [float(c) for c in s.split(",")]
                        return Point(coords[0], coords[1])
                    else:
                        coords = [float(c) for c in s.split()]
                        return Point(coords[0], coords[1])
                df = df.copy()
                df['geometry'] = df['geometry'].apply(parse_geom)
        return df

    input_df = ensure_geometry(input_df)

    logger.info("started extracting geometry from JET input table")
    geometry_timer = TicToc()
    geometry_timer.tic()

    if "geometry" in input_df:
        # Convert Point objects to coordinate tuples for MultiPoint
        if hasattr(input_df.geometry.iloc[0], "x") and hasattr(input_df.geometry.iloc[0], "y"):
            coords = [(pt.x, pt.y) for pt in input_df.geometry]
            geometry = MultiPoint(coords, crs=WGS84)
        else:
            geometry = MultiPoint(input_df.geometry, crs=WGS84)
    elif "lat" in input_df and "lon" in input_df:
        lat = np.array(input_df.lat).astype(np.float64)
        lon = np.array(input_df.lon).astype(np.float64)
        geometry = MultiPoint(x=lon, y=lat, crs=WGS84)
    else:
        raise KeyError("Input DataFrame must contain either 'geometry' or both 'lat' and 'lon' columns.")

    geometry_elapsed = geometry_timer.tocvalue()
    logger.info(f"completed extracting geometry from JET input table ({geometry_elapsed:.3f} seconds)")

    logger.info("started extracting time from JET input table")
    time_timer = TicToc()
    time_timer.tic()
    # Parse datetime with mixed format support (pandas 2.0+)
    time_UTC = pd.to_datetime(input_df.time_UTC, format='mixed').tolist()
    time_elapsed = time_timer.tocvalue()
    logger.info(f"completed extracting time from JET input table ({time_elapsed:.3f} seconds)")

    results = JET(
        ST_C=ST_C,
        emissivity=emissivity,
        NDVI=NDVI,
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
        Ta_C=Ta_C,
        Tmin_C=Tmin_C,
        RH=RH,
        soil_moisture=soil_moisture,
        PAR_albedo=PAR_albedo,
        NIR_albedo=NIR_albedo,
        Topt_C=Topt_C,
        fAPARmax=fAPARmax,
        field_capacity=field_capacity,
        wilting_point=wilting_point,
        IGBP=IGBP,
        canopy_height_meters=canopy_height_meters,
        Ca=Ca,
        CI=CI,
        wind_speed_mps=wind_speed_mps,
        canopy_temperature_C=canopy_temperature_C,
        NDVI_minimum=NDVI_minimum,
        NDVI_maximum=NDVI_maximum,
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
        water_mask=water_mask,
        GEOS5FP_connection=GEOS5FP_connection,
        MODISCI_connection=MODISCI_connection,
        soil_grids_directory=soil_grids_directory,
        GEDI_directory=GEDI_directory,
        Rn_model_name=Rn_model_name,
        downsampling=downsampling,
        offline_mode=offline_mode,
        include_water_surface=include_water_surface,
        generate_UQ=generate_UQ,
        use_calibration=use_calibration
    )

    output_df = input_df.copy()
    for key, value in results.items():
        output_df[key] = value

    total_elapsed = timer.tocvalue()
    logger.info(f"JET table processing complete ({total_elapsed:.3f} seconds)")

    return output_df
