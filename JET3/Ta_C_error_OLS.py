from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

try:
    import rasters
    from rasters import Raster
except Exception:  # pragma: no cover - optional dependency behavior
    rasters = None
    Raster = None  # type: ignore

import onnxruntime as ort
from importlib import resources


DEFAULT_ONNX_MODEL_FILENAME = "Ta_C_error_OLS.onnx"


@dataclass(frozen=True)
class OnnxModelInfo:
    model_path: str
    feature_names: Optional[Sequence[str]] = None


def get_ta_c_error_onnx_model_path() -> str:
    model_path = resources.files("JET3") / DEFAULT_ONNX_MODEL_FILENAME
    return str(model_path)


def load_ta_c_error_onnx_model() -> ort.InferenceSession:
    return ort.InferenceSession(get_ta_c_error_onnx_model_path())


def _to_numpy_array(value) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, pd.Series):
        return value.values
    if hasattr(value, "values"):
        return np.asarray(value.values)
    if hasattr(value, "data"):
        return np.asarray(value.data)
    return np.asarray(value)


def _normalize_feature_arrays(
    feature_values: Mapping[str, object],
    feature_order: Optional[Sequence[str]] = None,
) -> Tuple[List[str], List[np.ndarray], object]:
    if feature_order is None:
        feature_names = list(feature_values.keys())
    else:
        feature_names = list(feature_order)

    arrays: List[np.ndarray] = []
    template = None
    for name in feature_names:
        if name not in feature_values:
            raise ValueError(f"Missing feature '{name}' in inputs.")
        value = feature_values[name]
        if template is None:
            template = value
        arrays.append(_to_numpy_array(value))

    if not arrays:
        raise ValueError("No features provided for prediction.")

    first_shape = arrays[0].shape
    for idx, arr in enumerate(arrays):
        if arr.shape != first_shape:
            raise ValueError(
                f"Feature '{feature_names[idx]}' has shape {arr.shape}, expected {first_shape}."
            )

    return feature_names, arrays, template


def _restore_output(prediction: np.ndarray, template: object):
    if isinstance(template, pd.Series):
        return pd.Series(prediction.reshape(template.shape), index=template.index, name="Ta_C_error")
    if isinstance(template, pd.DataFrame):
        return pd.Series(prediction.reshape((len(template),)), index=template.index, name="Ta_C_error")
    if Raster is not None and isinstance(template, Raster):
        try:
            output = template.copy()
            output.data = prediction
            return output
        except Exception:
            return prediction
    if hasattr(template, "copy") and hasattr(template, "data"):
        try:
            output = template.copy()
            output.data = prediction
            return output
        except Exception:
            return prediction
    return prediction


def Ta_C_error_OLS(
    *,
    data: Optional[pd.DataFrame] = None,
    feature_order: Optional[Sequence[str]] = None,
    **features: object,
):
    """
    Predict Ta_C_error using the embedded OLS ONNX model.
    """
    if data is not None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame if provided.")
        if features:
            raise ValueError("Provide either data or keyword features, not both.")
        feature_values = {name: data[name] for name in data.columns}
    else:
        feature_values = features

    feature_names, arrays, template = _normalize_feature_arrays(feature_values, feature_order)

    flat_features = [arr.reshape(-1) for arr in arrays]
    input_matrix = np.column_stack(flat_features).astype(np.float32)

    session = load_ta_c_error_onnx_model()
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    prediction = session.run([output_name], {input_name: input_matrix})[0]
    prediction = prediction.reshape(arrays[0].shape)

    return _restore_output(prediction, template)
