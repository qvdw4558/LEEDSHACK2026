import os
import sys
import ctypes
import numpy as np


def _default_lib_name() -> str:
    if os.name == "nt":
        return "shipping_core.dll"
    if sys.platform == "darwin":
        return "libshipping_core.dylib"
    return "libshipping_core.so"


def load_lib(path: str | None = None):
    lib_path = path or _default_lib_name()
    return ctypes.CDLL(lib_path)


def score_route_in_c(weather_np: np.ndarray, lib=None) -> tuple[int, str]:
    if lib is None:
        lib = load_lib()

    a = np.ascontiguousarray(weather_np, dtype=np.float64)
    rows, cols = a.shape

    lib.score_route_from_weather_matrix.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.c_int,
    ]
    lib.score_route_from_weather_matrix.restype = ctypes.c_int

    score = lib.score_route_from_weather_matrix(
        a.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        rows,
        cols,
    )

    # label
    lib.risk_label_from_score.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    lib.risk_label_from_score.restype = ctypes.c_int
    buf = ctypes.create_string_buffer(64)
    lib.risk_label_from_score(score, buf, 64)
    label = buf.value.decode("utf-8")

    return score, label
