from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import requests
from math import radians, sin, cos, asin, sqrt
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

Coord = Tuple[float, float]  # (lat, lon)


# --- New: record type + builder (from earlier) ---
@dataclass
class RoutePointRecord:
    index: int
    lat: float
    lon: float
    weather: Optional[Dict] = None


def build_route_point_records(coordinates: List[Coord]) -> List[RoutePointRecord]:
    """
    Iterates through a list of (lat, lon) coordinates and returns a list of
    RoutePointRecord objects, one per coordinate.
    """
    records: List[RoutePointRecord] = []
    for idx, (lat, lon) in enumerate(coordinates):
        records.append(RoutePointRecord(index=idx, lat=lat, lon=lon, weather=None))
    return records


def main():
    start_city = input("Enter start city: ")
    start_country = input("Enter start country: ")
    end_city = input("Enter end city: ")
    end_country = input("Enter end country: ")

    start_query = f"{start_city}, {start_country}"
    end_query = f"{end_city}, {end_country}"

    start_coords = city_to_coordinates(start_query)
    if start_coords is None:
        print(f"Could not geocode start location: {start_query}")
        return

    end_coords = city_to_coordinates(end_query)
    if end_coords is None:
        print(f"Could not geocode end location: {end_query}")
        return

    # route_points is already List[Coord] in (lat, lon) format ✅
    route_points: List[Coord] = osrm_route_25_points(start_coords, end_coords, n_points=25)

    # --- New: convert coords -> records (format the earlier code accepts) ---
    route_point_records: List[RoutePointRecord] = build_route_point_records(route_points)

    print("\n100 route point records:")
    for rec in route_point_records:
        print(f"{rec.index:03d}: {rec.lat:.6f}, {rec.lon:.6f} | weather={rec.weather}")


def city_to_coordinates(city_name: str) -> Optional[Coord]:
    """
    Convert a city name to (latitude, longitude).
    Returns None if not found / error.
    """
    geolocator = Nominatim(user_agent="city_to_coords_app")

    try:
        location = geolocator.geocode(city_name)
        if location is None:
            return None
        return (location.latitude, location.longitude)

    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    R = 6371008.8
    phi1, lam1 = radians(lat1), radians(lon1)
    phi2, lam2 = radians(lat2), radians(lon2)
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _resample_polyline_evenly(coords: List[Coord], n: int) -> List[Coord]:
    """
    Resample a polyline (lat,lon) into n points evenly spaced by along-track distance.
    Linear interpolation is done in lat/lon for each segment.
    """
    if n <= 0:
        raise ValueError("n must be >= 1")
    if not coords:
        raise ValueError("coords must be a non-empty list")
    if len(coords) == 1:
        return [coords[0]] * n

    # Build cumulative distance array (meters)
    cum = [0.0]
    for i in range(1, len(coords)):
        lat0, lon0 = coords[i - 1]
        lat1, lon1 = coords[i]
        cum.append(cum[-1] + _haversine_m(lat0, lon0, lat1, lon1))

    total = cum[-1]
    if total == 0:
        return [coords[0]] * n

    # Target distances
    step = total / (n - 1) if n > 1 else 0.0
    targets = [i * step for i in range(n)]
    targets[-1] = total  # guard against floating error

    # Walk along the polyline and interpolate
    out: List[Coord] = []
    seg_i = 0

    for t in targets:
        while seg_i < len(cum) - 2 and cum[seg_i + 1] < t:
            seg_i += 1

        d0, d1 = cum[seg_i], cum[seg_i + 1]
        lat0, lon0 = coords[seg_i]
        lat1, lon1 = coords[seg_i + 1]

        if d1 == d0:
            out.append((lat0, lon0))
            continue

        frac = (t - d0) / (d1 - d0)
        lat = lat0 + frac * (lat1 - lat0)
        lon = lon0 + frac * (lon1 - lon0)
        out.append((lat, lon))

    return out


def osrm_route_100_points(
    start: Coord,
    end: Coord,
    n_points: int = 100,
    profile: str = "driving",
    base_url: str = "https://router.project-osrm.org",
    timeout: float = 20.0,
    overview: str = "full",
    geometries: str = "geojson",
) -> List[Coord]:
    """
    Use OSRM to find a route between two coordinates and return n_points evenly
    distributed along that route.
    """
    if overview == "false":
        raise ValueError("overview cannot be 'false' because we need route geometry.")
    if n_points < 1:
        raise ValueError("n_points must be >= 1")

    s_lat, s_lon = start
    e_lat, e_lon = end

    # OSRM expects lon,lat order in the URL
    url = f"{base_url.rstrip('/')}/route/v1/{profile}/{s_lon},{s_lat};{e_lon},{e_lat}"
    params = {
        "overview": overview,
        "geometries": geometries,
        "steps": "false",
    }

    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        msg = data.get("message", "OSRM did not return a valid route.")
        raise RuntimeError(f"OSRM error: {msg}")

    geom = data["routes"][0]["geometry"]
    if geometries != "geojson":
        raise ValueError("This function currently supports geometries='geojson' only.")

    # GeoJSON coordinates are [lon, lat]
    route_coords_lonlat = geom["coordinates"]
    route_coords: List[Coord] = [(lat, lon) for lon, lat in route_coords_lonlat]

    return _resample_polyline_evenly(route_coords, n_points)


if __name__ == "__main__":
    main()
