import math
import matplotlib
matplotlib.use("Agg")  # headless backend (no Qt/GUI)
import matplotlib.pyplot as plt

from route_find import city_to_coordinates, osrm_route_100_points
from route_find import osrm_route_100_points
from weather_on_route import weather_for_route_to_numpy, COLUMN_NAMES
from risk import score_route_risk


# ---------- helpers (your code only) ----------

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def polyline_distance_km(coords):
    """Sum distance along a route polyline. coords is list of (lat, lon)."""
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(coords, coords[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total


def estimate_travel_hours(distance_km, speed_knots=18.0):
    """
    Estimate travel time from distance and average vessel speed.
    1 knot = 1.852 km/h
    """
    speed_kmh = speed_knots * 1.852
    return distance_km / speed_kmh


def plot_efficiency_vs_risk(points, out_path="efficiency_vs_risk.png"):
    """
    points: list of dicts with keys: label, hours, risk
    """
    x = [p["hours"] for p in points]
    y = [p["risk"] for p in points]
    labels = [p["label"] for p in points]

    plt.figure()
    plt.scatter(x, y)

    for i, lab in enumerate(labels):
        plt.text(x[i] + 0.5, y[i], lab)

    plt.xlabel("Estimated Travel Time (hours)")
    plt.ylabel("Route Risk (1–100)")
    plt.title("Efficiency vs Risk (Lower-left is better)")
    plt.grid(True)

    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path


# ---------- main orchestration (uses teammate code unchanged) ----------

def analyze_route(start_place, end_place, date_yyyy_mm_dd, speed_knots=18.0):
    start = city_to_coordinates(start_place)
    end = city_to_coordinates(end_place)
    if start is None or end is None:
        raise ValueError("Could not geocode start or end location.")

    coords = osrm_route_100_points(start, end)  # teammate function, unchanged
    distance_km = polyline_distance_km(coords)
    hours = estimate_travel_hours(distance_km, speed_knots=speed_knots)

    weather_np = weather_for_route_to_numpy(coords, date_yyyy_mm_dd)  # teammate function
    risk_score = score_route_risk(weather_np, COLUMN_NAMES)           # teammate function

    return {"distance_km": distance_km, "hours": hours, "risk": risk_score}


if __name__ == "__main__":
    # Example: compare same route on different departure dates (weather changes risk)
    start = "Leeds, UK"
    end = "Rotterdam, Netherlands"
    dates = ["2026-02-08", "2026-02-09", "2026-02-10"]  # change as needed

    results = []
    for d in dates:
        r = analyze_route(start, end, d, speed_knots=18.0)
        results.append({"label": d, "hours": r["hours"], "risk": r["risk"]})

    out = plot_efficiency_vs_risk(results, out_path = "static/efficiency_vs_risk.png")
    print(f"Saved: {out}")
