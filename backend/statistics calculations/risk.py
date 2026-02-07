import numpy as np
from typing import Sequence, Dict

# Calibration: push scores lower without changing ordering too much
RISK_GAMMA: float = 1   # >1 compresses mid/high risks downwards
RISK_SCALE: float = 1  # <1 lowers overall level

def _col_idx(column_names: Sequence[str]) -> Dict[str, int]:
    return {name: i for i, name in enumerate(column_names)}


def _safe_col(a: np.ndarray, idx: int) -> np.ndarray:
    if idx < 0 or idx >= a.shape[1]:
        return np.full((a.shape[0],), np.nan, dtype=np.float64)
    return a[:, idx]


def _weathercode_baseline(code: float) -> float:
    """Map Open-Meteo weathercode -> baseline risk in [0,1]."""
    if np.isnan(code):
        return 0.2
    c = int(code)
    if c in (0, 1, 2, 3):
        return 0.05  # clear to overcast
    if c in (51, 53, 55, 61, 63, 71, 73):
        return 0.35  # drizzle / light-moderate rain/snow
    if c in (45, 48, 56, 57, 65, 66, 67, 75, 77, 80, 81, 82, 85, 86):
        return 0.70  # fog / freezing precip / heavy precip / showers
    if c in (95, 96, 99):
        return 0.90  # thunderstorm / hail
    return 0.30


def _clip01(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 0.0, 1.0)


def score_route_risk(weather_np: np.ndarray, column_names: Sequence[str]) -> int:
    """
    Return a single route risk score in the range 1..100.

    Deterministic heuristic:
      - Baseline from weathercode
      - Adds risk from gusts, precipitation, low visibility, freezing+precip, snow
      - Aggregates conservatively along the route (90th percentile)

    Assumed Open-Meteo units:
      - temps °C, precip mm, wind km/h, visibility meters, probability %
    """
    if weather_np is None or not isinstance(weather_np, np.ndarray) or weather_np.size == 0:
        return 1

    ci = _col_idx(column_names)

    temp_min = _safe_col(weather_np, ci.get("temp_min", -1))
    precip = _safe_col(weather_np, ci.get("precip_mm", -1))
    precip_prob = _safe_col(weather_np, ci.get("precip_prob_max", -1))
    snowfall = _safe_col(weather_np, ci.get("snowfall_mm", -1))
    gusts = _safe_col(weather_np, ci.get("wind_gusts_max", -1))
    visibility = _safe_col(weather_np, ci.get("visibility_min", -1))
    wcode = _safe_col(weather_np, ci.get("weathercode", -1))

    # Replace nans with benign defaults for scoring
    temp_min = np.nan_to_num(temp_min, nan=5.0)
    precip = np.nan_to_num(precip, nan=0.0)
    precip_prob = np.nan_to_num(precip_prob, nan=0.0)
    snowfall = np.nan_to_num(snowfall, nan=0.0)
    gusts = np.nan_to_num(gusts, nan=0.0)
    visibility = np.nan_to_num(visibility, nan=10000.0)

    base = np.array([_weathercode_baseline(c) for c in wcode], dtype=np.float64)

    # Gust risk: 40 km/h mild, 70 high, 100 severe
    gust_r = _clip01((gusts - 40.0) / 60.0)

    # Precip risk: 30mm heavy
    precip_r = _clip01(precip / 30.0)

    # Prob contributes mildly
    prob_r = _clip01(precip_prob / 100.0) * 0.3

    # Visibility: 10km ok -> 500m severe
    vis_r = _clip01((10000.0 - visibility) / 9500.0)

    # Ice: freezing + any precip/snow
    ice_r = np.where((temp_min <= 0.0) & ((precip > 0.2) | (snowfall > 0.0)), 0.6, 0.0)

    # Snow: 30mm heavy
    snow_r = _clip01(snowfall / 30.0) * 0.8

    # Combine per-point
    point_risk = base
    point_risk = np.maximum(point_risk, gust_r * 0.8)
    point_risk = np.maximum(point_risk, precip_r * 0.7 + prob_r)
    point_risk = np.maximum(point_risk, vis_r * 0.9)
    point_risk = np.maximum(point_risk, ice_r)
    point_risk = np.maximum(point_risk, snow_r)
    point_risk = _clip01(point_risk)

    route_risk = float(np.quantile(point_risk, 0.5))

    # Apply calibration curve to weight the final score lower
    # - gamma > 1 reduces mid/high values more than low values
    # - scale < 1 lowers everything
    calibrated = (route_risk ** RISK_GAMMA) * RISK_SCALE
    calibrated = float(np.clip(calibrated, 0.0, 1.0))

    score = int(round(1 + calibrated * 99))
    return max(1, min(100, score))

