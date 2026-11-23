from datetime import date, datetime
import logging

import numpy as np
import pandas as pd
import rasters as rt
import sklearn
from check_distribution import check_distribution
from GEOS5FP import GEOS5FPConnection
from rasters import Raster, RasterGeometry

from .constants import *
from .exceptions import BlankOutputError

logger = logging.getLogger(__name__)


def sharpen_meteorology_data(
    ST_C: Raster,
    NDVI: Raster,
    albedo: Raster,
    geometry: RasterGeometry,
    coarse_geometry: RasterGeometry,
    time_UTC: datetime,
    upsampling: str = UPSAMPLING,
    downsampling: str = DOWNSAMPLING,
    GEOS5FP_connection: GEOS5FPConnection = None,
) -> tuple[Raster, Raster, Raster]:
    """
    Sharpens air temperature and relative humidity using a linear regression model.
    """
    if GEOS5FP_connection is None:
        GEOS5FP_connection = GEOS5FPConnection()

    ST_C_coarse = ST_C.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(ST_C_coarse, "ST_C_coarse")
    NDVI_coarse = NDVI.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(NDVI_coarse, "NDVI_coarse")
    albedo_coarse = albedo.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(albedo_coarse, "albedo_coarse")

    Ta_C_coarse = GEOS5FP_connection.Ta_C(
        time_UTC=time_UTC, geometry=coarse_geometry, resampling=downsampling
    )
    check_distribution(Ta_C_coarse, "Ta_C_coarse")
    Td_C_coarse = GEOS5FP_connection.Td_K(
        time_UTC=time_UTC, geometry=coarse_geometry, resampling=downsampling
    ) - 273.15
    check_distribution(Td_C_coarse, "Td_C_coarse")
    SM_coarse = GEOS5FP_connection.SM(
        time_UTC=time_UTC, geometry=coarse_geometry, resampling=downsampling
    )
    check_distribution(SM_coarse, "SM_coarse")

    coarse_samples = pd.DataFrame(
        {
            "Ta_C": np.array(Ta_C_coarse).ravel(),
            "Td_C": np.array(Td_C_coarse).ravel(),
            "SM": np.array(SM_coarse).ravel(),
            "ST_C": np.array(ST_C_coarse).ravel(),
            "NDVI": np.array(NDVI_coarse).ravel(),
            "albedo": np.array(albedo_coarse).ravel(),
        }
    ).dropna()

    if len(coarse_samples) == 0:
        raise ValueError(
            f"unable to retrieve coarse samples for downscaling {time_UTC} UTC"
        )

    Ta_C_model = sklearn.linear_model.LinearRegression()
    Ta_C_model.fit(coarse_samples[["ST_C", "NDVI", "albedo"]], coarse_samples["Ta_C"])
    Ta_C_intercept = Ta_C_model.intercept_
    ST_C_Ta_C_coef, NDVI_Ta_C_coef, albedo_Ta_C_coef = Ta_C_model.coef_
    logger.info(
        f"air temperature regression: Ta_C = {Ta_C_intercept:0.2f} + {ST_C_Ta_C_coef:0.2f} * ST_C + {NDVI_Ta_C_coef:0.2f} * NDVI + {albedo_Ta_C_coef:0.2f} * albedo"
    )

    Ta_C_prediction = ST_C * ST_C_Ta_C_coef + NDVI * NDVI_Ta_C_coef + albedo * albedo_Ta_C_coef + Ta_C_intercept
    check_distribution(Ta_C_prediction, "Ta_C_prediction")

    logger.info(
        f"up-sampling predicted air temperature from {int(Ta_C_prediction.cell_size)}m to {int(coarse_geometry.cell_size)}m with {upsampling} method"
    )
    Ta_C_prediction_coarse = Ta_C_prediction.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(Ta_C_prediction_coarse, "Ta_C_prediction_coarse")
    Ta_C_bias_coarse = Ta_C_prediction_coarse - Ta_C_coarse
    check_distribution(Ta_C_bias_coarse, "Ta_C_bias_coarse")

    logger.info(
        f"down-sampling air temperature bias from {int(Ta_C_bias_coarse.cell_size)}m to {int(geometry.cell_size)}m with {downsampling} method"
    )
    Ta_C_bias_smooth = Ta_C_bias_coarse.to_geometry(geometry, resampling=downsampling)
    check_distribution(Ta_C_bias_smooth, "Ta_C_bias_smooth")
    logger.info("bias-correcting air temperature")
    Ta_C = Ta_C_prediction - Ta_C_bias_smooth
    check_distribution(Ta_C, "Ta_C")

    Ta_C_smooth = GEOS5FP_connection.Ta_C(time_UTC=time_UTC, geometry=geometry, resampling=downsampling)
    check_distribution(Ta_C_smooth, "Ta_C_smooth")
    logger.info("gap-filling air temperature")
    Ta_C = rt.where(np.isnan(Ta_C), Ta_C_smooth, Ta_C)
    check_distribution(Ta_C, "Ta_C")

    LST_mask = np.isnan(ST_C)
    Ta_C[LST_mask] = np.nan
    check_distribution(Ta_C, "Ta_C")
    Ta_C_smooth[LST_mask] = np.nan
    check_distribution(Ta_C_smooth, "Ta_C_smooth")

    logger.info(
        f"up-sampling final air temperature from {int(Ta_C.cell_size)}m to {int(coarse_geometry.cell_size)}m with {upsampling} method"
    )
    Ta_C_final_coarse = Ta_C.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(Ta_C_final_coarse, "Ta_C_final_coarse")
    Ta_C_error_coarse = Ta_C_final_coarse - Ta_C_coarse
    check_distribution(Ta_C_error_coarse, "Ta_C_error_coarse")
    logger.info(
        f"down-sampling air temperature error from {int(Ta_C_error_coarse.cell_size)}m to {int(geometry.cell_size)}m with {downsampling} method"
    )
    Ta_C_error = Ta_C_error_coarse.to_geometry(geometry, resampling=downsampling)
    check_distribution(Ta_C_error, "Ta_C_error")

    if np.all(np.isnan(Ta_C)):
        raise BlankOutputError(
            f"blank air temperature output for {time_UTC} UTC"
        )

    Td_C_model = sklearn.linear_model.LinearRegression()
    Td_C_model.fit(coarse_samples[["ST_C", "NDVI", "albedo"]], coarse_samples["Td_C"])
    Td_C_intercept = Td_C_model.intercept_
    ST_C_Td_C_coef, NDVI_Td_C_coef, albedo_Td_C_coef = Td_C_model.coef_

    logger.info(
        f"dew-point temperature regression: Td_C = {Td_C_intercept:0.2f} + {ST_C_Td_C_coef:0.2f} * ST_C + {NDVI_Td_C_coef:0.2f} * NDVI + {albedo_Td_C_coef:0.2f} * albedo"
    )
    Td_C_prediction = ST_C * ST_C_Td_C_coef + NDVI * NDVI_Td_C_coef + albedo * albedo_Td_C_coef + Td_C_intercept
    check_distribution(Td_C_prediction, "Td_C_prediction")
    logger.info(
        f"up-sampling predicted dew-point temperature from {int(Td_C_prediction.cell_size)}m to {int(coarse_geometry.cell_size)}m with {upsampling} method"
    )
    Td_C_prediction_coarse = Td_C_prediction.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(Td_C_prediction_coarse, "Td_C_prediction_coarse")
    Td_C_bias_coarse = Td_C_prediction_coarse - Td_C_coarse
    check_distribution(Td_C_bias_coarse, "Td_C_bias_coarse")
    logger.info(
        f"down-sampling dew-point temperature bias from {int(Td_C_bias_coarse.cell_size)}m to {int(geometry.cell_size)}m with {downsampling} method"
    )
    Td_C_bias_smooth = Td_C_bias_coarse.to_geometry(geometry, resampling=downsampling)
    check_distribution(Td_C_bias_smooth, "Td_C_bias_smooth")
    logger.info("bias-correcting dew-point temperature")
    Td_C = Td_C_prediction - Td_C_bias_smooth
    check_distribution(Td_C, "Td_C")
    Td_C_smooth = GEOS5FP_connection.Td_K(time_UTC=time_UTC, geometry=geometry, resampling=downsampling) - 273.15
    check_distribution(Td_C_smooth, "Td_C_smooth")
    logger.info("gap-filling dew-point temperature")
    Td_C = rt.where(np.isnan(Td_C), Td_C_smooth, Td_C)
    check_distribution(Td_C, "Td_C")

    Td_C[LST_mask] = np.nan
    check_distribution(Td_C, "Td_C")

    logger.info(
        f"up-sampling final dew-point temperature from {int(Td_C.cell_size)}m to {int(coarse_geometry.cell_size)}m with {upsampling} method"
    )
    Td_C_final_coarse = Td_C.to_geometry(coarse_geometry, resampling=upsampling)
    check_distribution(Td_C_final_coarse, "Td_C_final_coarse")
    Td_C_error_coarse = Td_C_final_coarse - Td_C_coarse
    check_distribution(Td_C_error_coarse, "Td_C_error_coarse")
    logger.info(
        f"down-sampling dew-point temperature error from {int(Td_C_error_coarse.cell_size)}m to {int(geometry.cell_size)}m with {downsampling} method"
    )
    Td_C_error = Td_C_error_coarse.to_geometry(geometry, resampling=downsampling)
    check_distribution(Td_C_error, "Td_C_error")

    RH = rt.clip(np.exp((17.625 * Td_C) / (243.04 + Td_C)) / np.exp((17.625 * Ta_C) / (243.04 + Ta_C)), 0, 1)

    if np.all(np.isnan(RH)):
        raise BlankOutputError(
            f"blank humidity output for {time_UTC} UTC"
        )

    return Ta_C, RH, Ta_C_smooth
