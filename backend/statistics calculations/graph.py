from __future__ import annotations

import math
import os
import re
import threading

_ANALYZE_CACHE = {}
_CACHE_LOCK = threading.Lock()

from typing import Dict, List, Tuple, Optional, Any

import matplotlib
matplotlib.use("Agg")  # headless backend (no Qt/GUI)
import matplotlib.pyplot as plt

from route_find import city_to_coordinates, osrm_route_100_points
from weather_on_route import weather_for_route_to_numpy, COLUMN_NAMES
from risk import score_route_risk


# ----------------------------
# Helpers: geometry + time
# ----------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in km."""
    r_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2) + (math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2))
    return 2 * r_km * math.asin(math.sqrt(a))


def polyline_distance_km(coords: List[Tuple[float, float]]) -> float:
    """Sum distance along a route polyline. coords is list of (lat, lon)."""
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(coords, coords[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total


def estimate_travel_hours(distance_km: float, speed_knots: float = 18.0) -> float:
    """
    Estimate travel time given distance and average vessel speed.
    1 knot = 1.852 km/h
    """
    speed_kmh = speed_knots * 1.852
    if speed_kmh <= 0:
        raise ValueError("speed_knots must be > 0")
    return distance_km / speed_kmh


# ----------------------------
# Core analysis (with in-memory cache)
# ----------------------------

# In-memory cache: avoids redoing expensive network calls while process stays running.
# Key ignores speed on purpose (weather risk does not depend on speed).
_ANALYZE_CACHE: Dict[Tuple[str, str, str], Dict[str, float]] = {}
_CACHE_LOCK = threading.Lock()


def analyze_route(start_place, end_place, date_yyyy_mm_dd, speed_knots=18.0):
    cache_key = (start_place, end_place, date_yyyy_mm_dd)

    with _CACHE_LOCK:
        cached = _ANALYZE_CACHE.get(cache_key)

    if cached is None:
        start = city_to_coordinates(start_place)
        end = city_to_coordinates(end_place)
        if start is None or end is None:
            raise ValueError("Could not geocode start or end location.")

        coords = osrm_route_100_points(start, end)
        distance_km = polyline_distance_km(coords)

        weather_np = weather_for_route_to_numpy(coords, date_yyyy_mm_dd)
        risk_score = score_route_risk(weather_np, COLUMN_NAMES)

        cached = {"distance_km": distance_km, "risk": risk_score}

        with _CACHE_LOCK:
            _ANALYZE_CACHE[cache_key] = cached

    hours = estimate_travel_hours(cached["distance_km"], speed_knots=speed_knots)
    return {"distance_km": cached["distance_km"], "hours": hours, "risk": cached["risk"]}

# ----------------------------
# Plotting (graph look unchanged)
# ----------------------------

def choose_recommended(points: List[Dict[str, float]]) -> int:
    """
    Pick the recommended point by minimizing:
      normalized_time + normalized_risk
    """
    if not points:
        raise ValueError("No points provided.")

    times = [p["hours"] for p in points]
    risks = [p["risk"] for p in points]

    t_min, t_max = min(times), max(times)
    r_min, r_max = min(risks), max(risks)

    def norm(x: float, lo: float, hi: float) -> float:
        return 0.0 if hi == lo else (x - lo) / (hi - lo)

    best_i = 0
    best_score = float("inf")
    for i, p in enumerate(points):
        score = norm(p["hours"], t_min, t_max) + norm(p["risk"], r_min, r_max)
        if score < best_score:
            best_score = score
            best_i = i
    return best_i


def plot_efficiency_vs_risk(
    points: List[Dict[str, Any]],
    out_path: str = "efficiency_vs_risk.png",
    title: str = "Efficiency vs Risk",
) -> str:
    """
    Graph look stays the same as your cleaned version:
    - scatter plot
    - labels close to dots
    - recommended annotation
    """
    if not points:
        raise ValueError("No points to plot.")

    best_i = choose_recommended(points)

    x = [p["hours"] for p in points]
    y = [p["risk"] for p in points]
    labels = [p.get("label", "") for p in points]

    plt.figure(figsize=(8, 5))
    plt.scatter(x, y)
    plt.scatter([x[best_i]], [y[best_i]])  # highlight recommended point

    # labels next to dots
    for i, lab in enumerate(labels):
        plt.annotate(
            lab,
            (x[i], y[i]),
            textcoords="offset points",
            xytext=(6, 6),
            ha="left",
            fontsize=9,
        )

    plt.annotate(
        "Recommended",
        (x[best_i], y[best_i]),
        textcoords="offset points",
        xytext=(6, -14),
        ha="left",
        fontsize=10,
        arrowprops=dict(arrowstyle="->", lw=1),
    )

    plt.xlabel("Estimated travel time (hours)")
    plt.ylabel("Route risk score (1–100)")
    plt.title(title)
    plt.grid(True, alpha=0.3)

    # ensure folder exists
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    return out_path


# ----------------------------
# Output filename caching (by inputs)
# ----------------------------

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_output_path(
    static_dir: str,
    start: str,
    end: str,
    dates: List[str],
    speeds: Tuple[float, ...],
) -> str:
    """
    Cache-by-inputs:
    Different inputs -> different PNG filename -> auto-updates.
    """
    tag = f"{_slug(start)}_{_slug(end)}_{'-'.join(dates)}_{'-'.join(str(int(x)) for x in speeds)}"
    filename = f"efficiency_vs_risk_{tag}.png"
    return os.path.join(static_dir, filename)


# ----------------------------
# Async generation (big UX win)
# ----------------------------

# Tracks generation jobs so callers can avoid starting duplicates
_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def generate_efficiency_vs_risk_async(
    start: str,
    end: str,
    dates: List[str],
    speeds: Tuple[float, ...],
    static_dir: str = "static",
    title: str = "Route Optimisation: Efficiency vs Risk",
) -> Dict[str, Any]:
    """
    Starts background generation and returns immediately.

    Return dict includes:
      - status: "ready" | "running"
      - out_path: filesystem path of PNG
      - plot_url: URL path (for FastAPI static mount)
    """
    out_path = build_output_path(static_dir, start, end, dates, speeds)
    plot_url = "/static/" + os.path.basename(out_path)


    # Avoid spawning duplicate threads for same output path
    with _JOBS_LOCK:
        existing = _JOBS.get(out_path)
        if existing and existing.get("status") == "running":
            return {"status": "running", "out_path": out_path, "plot_url": plot_url}

        _JOBS[out_path] = {"status": "running", "error": None}

    def _worker():
        try:
            points: List[Dict[str, Any]] = []

            # Important: only do the expensive risk computation once per date,
            # then vary hours by speed cheaply (risk unchanged by speed).
            # We'll compute base distance/risk per date at speed 18, then rescale hours.
            base_speed = 18.0

            for d in dates:
                base = analyze_route(start, end, d, speed_knots=base_speed)
                base_hours = base["hours"]
                risk = base["risk"]

                for sp in speeds:
                    hours = base_hours * (base_speed / sp)
                    points.append({"label": f"{d} @ {int(sp)}kn", "hours": hours, "risk": risk})

            plot_efficiency_vs_risk(points, out_path=out_path, title=title)

            with _JOBS_LOCK:
                _JOBS[out_path] = {"status": "ready", "error": None}

        except Exception as e:
            with _JOBS_LOCK:
                _JOBS[out_path] = {"status": "error", "error": str(e)}

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    return {"status": "running", "out_path": out_path, "plot_url": plot_url}




#--------------------------------------------------------------------
#// ---------- BARCHART!!!!!: risk by date (bar chart) ----------//
#---------------------------------------------------------------------


def plot_risk_bar_chart(
    points,
    out_path="risk_by_date.png",
    title="Risk by Departure Date"
):
    """
    points: list of dicts like:
      {"label": "2026-02-08", "hours": 120.5, "risk": 62}

    Saves a bar chart PNG and returns the output path.
    """

    if not points:
        raise ValueError("No points to plot.")

    import matplotlib.pyplot as plt

    labels = [p["label"] for p in points]
    risks = [p["risk"] for p in points]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, risks)

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.xlabel("Departure date")
    plt.ylabel("Route risk score (1–100)")
    plt.title(title)
    plt.grid(axis="y", alpha=0.3)

    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    return out_path
