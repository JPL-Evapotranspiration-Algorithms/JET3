from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from rasters import Point, Raster, RasterGeometry

import JET3
from JET3 import constants
from check_distribution import BlankOutputError
from JET3.exceptions import BlankOutput
from JET3.process_JET_table import process_JET_table
from JET3.sharpen_meteorology_data import sharpen_meteorology_data
from JET3.Ta_C_error_OLS import get_ta_c_error_onnx_model_path


def _make_grid_geometry(shape=(2, 2)):
    geom = MagicMock(spec=RasterGeometry)
    geom.shape = shape
    geom.cell_size = 70.0
    coarse = MagicMock(spec=RasterGeometry)
    coarse.shape = (2, 2)
    coarse.cell_size = 13720.0
    geom.rescale.return_value = coarse
    return geom, coarse


def _mock_raster(arr, geom):
    r = MagicMock(spec=Raster)
    r.geometry = geom
    r.cell_size = geom.cell_size
    r.shape = arr.shape
    r.__array__ = lambda self=None, dtype=None: np.asarray(arr, dtype=dtype)
    r.to_geometry.return_value = _mock_raster_leaf(np.full((2, 2), float(np.nanmean(arr))))
    return r


def _mock_raster_leaf(arr):
    leaf = MagicMock(spec=Raster)
    leaf.cell_size = 13720.0
    leaf.shape = arr.shape
    leaf.__array__ = lambda self=None, dtype=None: np.asarray(arr, dtype=dtype)
    return leaf


def test_issue_18_no_duplicate_constants():
    """Issue #18: Ensure constants.py defines expected values cleanly."""
    assert constants.GEOS_IN_SENTINEL_COARSE_CELL_SIZE == 13720
    assert constants.SHARPEN_METEOROLOGY is True


def test_issue_17_ta_c_error_onnx_package_resource():
    """Issue #17: Ensure Ta_C_error_OLS resolves model path inside JET3 package."""
    model_path = get_ta_c_error_onnx_model_path()
    assert "JET3" in model_path
    assert "ECOv003_L3T_L4T_JET" not in model_path
    assert model_path.endswith("Ta_C_error_OLS.onnx")


def test_issue_20_sharpen_meteorology_uses_td_k():
    """Issue #20: sharpen_meteorology_data uses Td_K() - 273.15 rather than deprecated Td_C()."""
    geom = MagicMock(spec=RasterGeometry)
    geom.cell_size = 70.0
    coarse = MagicMock(spec=RasterGeometry)
    coarse.cell_size = 13720.0

    fine_arr = np.array([[28.0, 29.0], [30.0, 31.0]], dtype=float)
    coarse_arr = np.array([[27.0, 28.0], [29.0, 30.0]], dtype=float)

    class FakeRaster(np.ndarray):
        def __new__(cls, input_array, cell_size=70.0):
            obj = np.asarray(input_array, dtype=float).view(cls)
            obj.cell_size = cell_size
            return obj

        def __array_finalize__(self, obj):
            if obj is None:
                return
            self.cell_size = getattr(obj, "cell_size", 70.0)

        def to_geometry(self, target_geom, resampling=None):
            return FakeRaster(coarse_arr.copy(), cell_size=target_geom.cell_size)

    st_c = FakeRaster(fine_arr, cell_size=70.0)
    ndvi = FakeRaster(np.full((2, 2), 0.5), cell_size=70.0)
    albedo = FakeRaster(np.full((2, 2), 0.2), cell_size=70.0)

    mock_geos = MagicMock()
    # Explicitly ensure Td_C does NOT exist on mock_geos
    del mock_geos.Td_C
    mock_geos.Ta_C.side_effect = lambda time_UTC, geometry, resampling=None: FakeRaster(
        np.full((2, 2), 25.0), cell_size=geometry.cell_size
    )
    mock_geos.Td_K.side_effect = lambda time_UTC, geometry, resampling=None: FakeRaster(
        np.full((2, 2), 288.15), cell_size=geometry.cell_size
    )
    mock_geos.SM.side_effect = lambda time_UTC, geometry, resampling=None: FakeRaster(
        np.full((2, 2), 0.25), cell_size=geometry.cell_size
    )

    with patch("JET3.sharpen_meteorology_data.rt.where", side_effect=lambda cond, a, b: b if np.all(cond) else a):
        Ta_C, RH, Ta_C_smooth = sharpen_meteorology_data(
            ST_C=st_c,
            NDVI=ndvi,
            albedo=albedo,
            geometry=geom,
            coarse_geometry=coarse,
            time_UTC=datetime(2026, 7, 1, 18, 0),
            GEOS5FP_connection=mock_geos,
        )

    assert mock_geos.Td_K.call_count == 2
    assert Ta_C.shape == (2, 2)
    assert RH.shape == (2, 2)
    assert np.all((RH >= 0.0) & (RH <= 1.0))


@patch("JET3.JET.AquaSEBS")
@patch("JET3.JET.PMJPL")
@patch("JET3.JET.PTJPLSM")
@patch("JET3.JET.STIC_JPL")
@patch("JET3.JET.verma_net_radiation")
@patch("JET3.JET.BESS_JPL")
@patch("JET3.JET.FLiESANN")
def test_issues_14_16_19_21_in_jet(
    mock_flies,
    mock_bess,
    mock_verma,
    mock_stic,
    mock_ptjplsm,
    mock_pmjpl,
    mock_aquasebs,
):
    """Issues #14, #16, #19, #21: wind_speed_mps, elevation fallback, daily BlankOutput, water_mask gating."""
    shape = (2,)
    zeros = np.zeros(shape)
    ones = np.ones(shape)

    mock_flies.return_value = {
        "SWin_TOA_Wm2": ones * 1000.0,
        "SWin_Wm2": ones * 700.0,
        "UV_Wm2": ones * 30.0,
        "PAR_Wm2": ones * 300.0,
        "NIR_Wm2": ones * 370.0,
        "PAR_diffuse_Wm2": ones * 100.0,
        "NIR_diffuse_Wm2": ones * 120.0,
        "PAR_direct_Wm2": ones * 200.0,
        "NIR_direct_Wm2": ones * 250.0,
    }
    mock_bess.return_value = {
        "Rn_Wm2": ones * 450.0,
        "G_Wm2": ones * 40.0,
        "LE_Wm2": ones * 200.0,
        "ET_daylight_kg": ones * 3.0,
        "GPP": ones * 10.0,
    }
    mock_verma.return_value = {"Rn_Wm2": ones * 460.0}
    mock_stic.return_value = {
        "LE_Wm2": ones * 210.0,
        "ET_daylight_kg": ones * 3.2,
        "LE_canopy_Wm2": ones * 150.0,
        "G_Wm2": ones * 45.0,
    }
    mock_ptjplsm.return_value = {
        "LE_Wm2": ones * 220.0,
        "ET_daylight_kg": ones * 3.4,
        "G_Wm2": ones * 42.0,
        "LE_canopy_Wm2": ones * 140.0,
        "LE_soil_Wm2": ones * 60.0,
        "LE_interception_Wm2": ones * 20.0,
        "PET_Wm2": ones * 300.0,
    }
    mock_pmjpl.return_value = {
        "LE_Wm2": ones * 205.0,
        "ET_daylight_kg": ones * 3.1,
        "G_Wm2": ones * 41.0,
    }
    mock_aquasebs.return_value = {
        "LE_Wm2": ones * 500.0,
        "ET_daylight_kg": ones * 8.5,
    }

    mock_geos = MagicMock()
    del mock_geos.wind_speed
    del mock_geos.elevation
    mock_geos.filenames = []
    mock_geos.wind_speed_mps.return_value = ones * 3.5

    # Pixel 0 is land (False), Pixel 1 is water (True)
    water_mask = np.array([False, True], dtype=bool)

    with patch("NASADEM.NASADEMConnection.elevation_m", return_value=ones * 120.0):
        res = JET3.JET(
            ST_C=ones * 30.0,
            emissivity=ones * 0.98,
            NDVI=ones * 0.6,
            albedo=ones * 0.18,
            geometry=Point(-118.0, 34.0),
            time_UTC=datetime(2026, 7, 1, 18, 0),
            COT=zeros,
            AOT=ones * 0.1,
            vapor_gccm=ones * 1.5,
            ozone_cm=ones * 0.3,
            elevation_m=None,  # Issue #21
            SZA_deg=ones * 25.0,
            KG_climate=np.array(["Csa", "Csa"]),
            Ta_C=ones * 26.0,
            Tmin_C=ones * 15.0,
            RH=ones * 0.45,
            soil_moisture=ones * 0.22,
            PAR_albedo=ones * 0.08,
            NIR_albedo=ones * 0.28,
            wind_speed_mps=None,  # Issue #19
            GEOS5FP_connection=mock_geos,
            water_mask=water_mask,
            Rn_model_name="verma",
            include_water_surface=True,
        )

    # Issue #19 & #21 assertions
    mock_geos.wind_speed_mps.assert_called_once()
    assert np.allclose(res["wind_speed_mps"], 3.5)

    # Issue #14 assertion: Pixel 0 (land) keeps land median (~3.15), Pixel 1 (water) gets AquaSEBS (8.5)
    assert np.isclose(res["ET_daylight_kg"][0], 3.15)
    assert np.isclose(res["ET_daylight_kg"][1], 8.5)

    # Issue #16 assertion: all-NaN ET_daylight_PTJPLSM_kg raises BlankOutput even when LE_PTJPLSM_Wm2 is valid
    mock_ptjplsm.return_value["ET_daylight_kg"] = np.full(shape, np.nan)
    with pytest.raises((BlankOutput, BlankOutputError)):
        JET3.JET(
            ST_C=ones * 30.0,
            emissivity=ones * 0.98,
            NDVI=ones * 0.6,
            albedo=ones * 0.18,
            geometry=Point(-118.0, 34.0),
            time_UTC=datetime(2026, 7, 1, 18, 0),
            COT=zeros,
            AOT=ones * 0.1,
            vapor_gccm=ones * 1.5,
            ozone_cm=ones * 0.3,
            elevation_m=ones * 100.0,
            SZA_deg=ones * 25.0,
            KG_climate=np.array(["Csa", "Csa"]),
            Ta_C=ones * 26.0,
            Tmin_C=ones * 15.0,
            RH=ones * 0.45,
            soil_moisture=ones * 0.22,
            PAR_albedo=ones * 0.08,
            NIR_albedo=ones * 0.28,
            wind_speed_mps=ones * 3.0,
            GEOS5FP_connection=mock_geos,
            Rn_model_name="verma",
            include_water_surface=False,
        )


def test_issue_15_process_jet_table_aliases_and_missing_optional_cols():
    """Issue #15: process_JET_table supports 'Ta' alias and missing Tmin_C / online columns."""
    df = pd.DataFrame(
        {
            "ST_C": [30.0],
            "emissivity": [0.98],
            "NDVI": [0.55],
            "albedo": [0.20],
            "Ta": [25.0],  # Alias for Ta_C; Tmin_C, RH, SM intentionally omitted
            "lat": [34.0],
            "lon": [-118.0],
            "time_UTC": ["2026-07-01T18:00:00Z"],
        }
    )

    with patch("JET3.process_JET_table.JET", return_value={"ET_daylight_kg": np.array([3.5])}) as mock_jet:
        out = process_JET_table(df, offline_mode=False)

    kwargs = mock_jet.call_args.kwargs
    assert np.allclose(kwargs["Ta_C"], [25.0])
    assert kwargs["Tmin_C"] is None
    assert kwargs["RH"] is None
    assert kwargs["soil_moisture"] is None
    assert np.isclose(out["ET_daylight_kg"].iloc[0], 3.5)


@patch("JET3.JET.PMJPL")
@patch("JET3.JET.PTJPLSM")
@patch("JET3.JET.STIC_JPL")
@patch("JET3.JET.verma_net_radiation")
@patch("JET3.JET.BESS_JPL")
@patch("JET3.JET.FLiESANN")
def test_issue_23_bias_correct_flies_ann(
    mock_flies,
    mock_bess,
    mock_verma,
    mock_stic,
    mock_ptjplsm,
    mock_pmjpl,
):
    """Issue #23: Verify optional GEOS-5 FP residual bias correction for FLiES-ANN SWin_Wm2."""
    from rasters import RasterGrid

    assert constants.BIAS_CORRECT_FLIES_ANN is False

    fine_geom = RasterGrid.from_bbox(xmin=400000.0, ymin=3760000.0, xmax=428000.0, ymax=3788000.0, cell_size=70.0, crs="EPSG:32611")
    ones = Raster(np.ones(fine_geom.shape, dtype=float), geometry=fine_geom)
    zeros = Raster(np.zeros(fine_geom.shape, dtype=float), geometry=fine_geom)

    # Raw FLiES-ANN predicts 800 W/m2 everywhere
    mock_flies.return_value = {
        "SWin_TOA_Wm2": ones * 1000.0,
        "SWin_Wm2": ones * 800.0,
        "UV_Wm2": ones * 30.0,
        "PAR_Wm2": ones * 350.0,
        "NIR_Wm2": ones * 420.0,
        "PAR_diffuse_Wm2": ones * 100.0,
        "NIR_diffuse_Wm2": ones * 120.0,
        "PAR_direct_Wm2": ones * 250.0,
        "NIR_direct_Wm2": ones * 300.0,
    }
    mock_bess.return_value = {
        "Rn_Wm2": ones * 450.0,
        "G_Wm2": ones * 40.0,
        "LE_Wm2": ones * 200.0,
        "ET_daylight_kg": ones * 3.0,
        "GPP": ones * 10.0,
    }
    mock_verma.return_value = {"Rn_Wm2": ones * 460.0}
    mock_stic.return_value = {
        "LE_Wm2": ones * 210.0,
        "ET_daylight_kg": ones * 3.2,
        "LE_canopy_Wm2": ones * 150.0,
        "G_Wm2": ones * 45.0,
    }
    mock_ptjplsm.return_value = {
        "LE_Wm2": ones * 220.0,
        "ET_daylight_kg": ones * 3.4,
        "G_Wm2": ones * 42.0,
        "LE_canopy_Wm2": ones * 140.0,
        "LE_soil_Wm2": ones * 60.0,
        "LE_interception_Wm2": ones * 20.0,
        "PET_Wm2": ones * 300.0,
    }
    mock_pmjpl.return_value = {
        "LE_Wm2": ones * 205.0,
        "ET_daylight_kg": ones * 3.1,
        "G_Wm2": ones * 41.0,
    }

    mock_geos = MagicMock()
    mock_geos.filenames = []
    # GEOS-5 FP coarse SWin is 725 W/m2 (+75 W/m2 FLiES-ANN bias)
    mock_geos.SWin.side_effect = lambda time_UTC, geometry, resampling=None: Raster(
        np.full(geometry.shape, 725.0, dtype=float), geometry=geometry
    )

    common_kwargs = dict(
        ST_C=ones * 30.0,
        emissivity=ones * 0.98,
        NDVI=ones * 0.6,
        albedo=ones * 0.18,
        geometry=fine_geom,
        time_UTC=datetime(2026, 6, 2, 18, 0),
        COT=zeros,
        AOT=ones * 0.1,
        vapor_gccm=ones * 1.5,
        ozone_cm=ones * 0.3,
        elevation_m=ones * 100.0,
        SZA_deg=ones * 25.0,
        KG_climate=Raster(np.full(fine_geom.shape, 4), geometry=fine_geom),
        Ta_C=ones * 26.0,
        Tmin_C=ones * 15.0,
        RH=ones * 0.45,
        soil_moisture=ones * 0.22,
        PAR_albedo=ones * 0.08,
        NIR_albedo=ones * 0.28,
        wind_speed_mps=ones * 3.0,
        GEOS5FP_connection=mock_geos,
        Rn_model_name="verma",
        include_water_surface=False,
    )

    # 1. Default (bias_correct_FLiES_ANN=False): raw FLiES-ANN output preserved, SWin not queried
    res_raw = JET3.JET(**common_kwargs)
    mock_geos.SWin.assert_not_called()
    assert np.allclose(res_raw["SWin_Wm2"], 800.0)

    # 2. Enabled (bias_correct_FLiES_ANN=True): +75 W/m2 bias removed -> 725 W/m2
    res_corr = JET3.JET(**common_kwargs, bias_correct_FLiES_ANN=True)
    mock_geos.SWin.assert_called_once()
    assert np.allclose(res_corr["SWin_Wm2"], 725.0)


@patch("JET3.JET.PMJPL")
@patch("JET3.JET.PTJPLSM")
@patch("JET3.JET.STIC_JPL")
@patch("JET3.JET.verma_net_radiation")
@patch("JET3.JET.BESS_JPL")
@patch("JET3.JET.FLiESANN")
def test_unscaled_vapor_and_ozone_unit_warnings(
    mock_flies,
    mock_bess,
    mock_verma,
    mock_stic,
    mock_ptjplsm,
    mock_pmjpl,
    caplog,
):
    """Verify JET() logs warnings when unscaled vapor_gccm (>15) or ozone_cm (>5) is passed."""
    ones = np.ones((2,))
    zeros = np.zeros((2,))
    mock_flies.return_value = {
        "SWin_TOA_Wm2": ones * 1000.0,
        "SWin_Wm2": ones * 750.0,
        "UV_Wm2": ones * 30.0,
        "PAR_Wm2": ones * 320.0,
        "NIR_Wm2": ones * 400.0,
        "PAR_diffuse_Wm2": ones * 100.0,
        "NIR_diffuse_Wm2": ones * 120.0,
        "PAR_direct_Wm2": ones * 220.0,
        "NIR_direct_Wm2": ones * 280.0,
    }
    mock_bess.return_value = {
        "Rn_Wm2": ones * 450.0,
        "G_Wm2": ones * 40.0,
        "LE_Wm2": ones * 200.0,
        "ET_daylight_kg": ones * 3.0,
        "GPP": ones * 10.0,
    }
    mock_verma.return_value = {"Rn_Wm2": ones * 460.0}
    mock_stic.return_value = {
        "LE_Wm2": ones * 210.0,
        "ET_daylight_kg": ones * 3.2,
        "LE_canopy_Wm2": ones * 150.0,
        "G_Wm2": ones * 45.0,
    }
    mock_ptjplsm.return_value = {
        "LE_Wm2": ones * 220.0,
        "ET_daylight_kg": ones * 3.4,
        "G_Wm2": ones * 42.0,
        "LE_canopy_Wm2": ones * 140.0,
        "LE_soil_Wm2": ones * 60.0,
        "LE_interception_Wm2": ones * 20.0,
        "PET_Wm2": ones * 300.0,
    }
    mock_pmjpl.return_value = {
        "LE_Wm2": ones * 205.0,
        "ET_daylight_kg": ones * 3.1,
        "G_Wm2": ones * 41.0,
    }
    mock_geos = MagicMock()
    mock_geos.filenames = []

    with caplog.at_level("WARNING"):
        JET3.JET(
            ST_C=ones * 30.0,
            emissivity=ones * 0.98,
            NDVI=ones * 0.6,
            albedo=ones * 0.18,
            geometry=Point(-118.0, 34.0),
            time_UTC=datetime(2026, 6, 2, 18, 0),
            COT=zeros,
            AOT=ones * 0.1,
            vapor_gccm=ones * 20.0,
            ozone_cm=ones * 330.0,
            elevation_m=ones * 100.0,
            SZA_deg=ones * 25.0,
            KG_climate=np.array(["Csa", "Csa"]),
            Ta_C=ones * 26.0,
            Tmin_C=ones * 15.0,
            RH=ones * 0.45,
            soil_moisture=ones * 0.22,
            PAR_albedo=ones * 0.08,
            NIR_albedo=ones * 0.28,
            wind_speed_mps=ones * 3.0,
            GEOS5FP_connection=mock_geos,
            Rn_model_name="verma",
            include_water_surface=False,
        )

    assert "vapor_gccm mean" in caplog.text
    assert "ozone_cm mean" in caplog.text
