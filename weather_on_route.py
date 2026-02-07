import time
import requests
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from route_find import city_to_coordinates, osrm_route_100_points


Coord = Tuple[float, float]  # (lat, lon)

# Daily variables we agreed earlier (Open-Meteo daily)
DAILY_VARS = [
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "snowfall_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "visibility_min",
    "weathercode",
]

# Output column order (you can change / extend this)
COLUMN_NAMES = [
    "lat",
    "lon",
    "temp_min",
    "temp_max",
    "precip_mm",
    "precip_prob_max",
    "snowfall_mm",
    "wind_speed_max",
    "wind_gusts_max",
    "visibility_min",
    "weathercode",
]


def fetch_daily_weather_open_meteo(
    lat: float,
    lon: float,
    date_yyyy_mm_dd: str,
    *,
    base_url: str = "https://api.open-meteo.com/v1/forecast",
    timeout: float = 20.0,
    retries: int = 2,
    # Per-request throttling. Set to 0.0 for fastest runtime.
    sleep_between: float = 0.0,
) -> Dict[str, Any]:
    """
    Fetch one-day daily weather for a single lat/lon from Open-Meteo.
    Returns a dict with keys matching DAILY_VARS, plus lat/lon.
    Missing values become np.nan in later processing.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DAILY_VARS),
        "start_date": date_yyyy_mm_dd,
        "end_date": date_yyyy_mm_dd,
        "timezone": "UTC",
    }

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(base_url, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()

            daily = data.get("daily", {})
            # daily values come back as arrays (length 1 because start=end)
            out = {"lat": lat, "lon": lon}
            for k in DAILY_VARS:
                arr = daily.get(k)
                out[k] = arr[0] if isinstance(arr, list) and len(arr) > 0 else None

            return out

        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
            else:
                raise

        finally:
            if sleep_between and sleep_between > 0:
                time.sleep(sleep_between)

    # Should never hit here
    raise RuntimeError(f"Weather fetch failed: {last_exc}")


def weather_for_route_to_numpy(
    coords: List[Coord],
    date_yyyy_mm_dd: str,
) -> np.ndarray:
    """
    Given a list of (lat, lon), fetch daily weather for each coordinate for one day,
    and return a numpy array of shape (len(coords), len(COLUMN_NAMES)).

    Column order is defined by COLUMN_NAMES.
    """
    n = len(coords)
    m = len(COLUMN_NAMES)
    out = np.full((n, m), np.nan, dtype=np.float64)

    # weathercode is categorical-ish, but we still store as float for a single numeric array.
    # If you want mixed types, use a structured array instead.

    for i, (lat, lon) in enumerate(coords):
        w = fetch_daily_weather_open_meteo(lat, lon, date_yyyy_mm_dd)

        # Fill row
        out[i, 0] = lat
        out[i, 1] = lon
        out[i, 2] = _to_float(w.get("temperature_2m_min"))
        out[i, 3] = _to_float(w.get("temperature_2m_max"))
        out[i, 4] = _to_float(w.get("precipitation_sum"))
        out[i, 5] = _to_float(w.get("precipitation_probability_max"))
        out[i, 6] = _to_float(w.get("snowfall_sum"))
        out[i, 7] = _to_float(w.get("wind_speed_10m_max"))
        out[i, 8] = _to_float(w.get("wind_gusts_10m_max"))
        out[i, 9] = _to_float(w.get("visibility_min"))
        out[i, 10] = _to_float(w.get("weathercode"))

    return out


def _to_float(x: Any) -> float:
    if x is None:
        return float("nan")
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def weather_on_route():
    start_city = input("Enter start city: ").strip()
    start_country = input("Enter start country: ").strip()
    end_city = input("Enter end city: ").strip()
    end_country = input("Enter end country: ").strip()
    date = input("Enter date (YYYY-MM-DD): ").strip()

    start_query = f"{start_city}, {start_country}"
    end_query = f"{end_city}, {end_country}"

    start_coords = city_to_coordinates(start_query)
    if start_coords is None:
        print(f"Could not geocode start location: {start_query}")
        return None

    end_coords = city_to_coordinates(end_query)
    if end_coords is None:
        print(f"Could not geocode end location: {end_query}")
        return None

    # Get 100 points along the route (List[Tuple[lat, lon]])
    route_points = osrm_route_100_points(start_coords, end_coords, n_points=100)

    # Fetch daily weather for each point -> numpy array
    weather_np = weather_for_route_to_numpy(route_points, date)

    print("\nNumPy array shape:", weather_np.shape)
    print("Column order:", COLUMN_NAMES)
    print("\nFull array:\n", weather_np)

    return weather_np


if __name__ == "__main__":
    weather_on_route()

