from route_find import city_to_coordinates, osrm_route_100_points
from weather_on_route import weather_for_route_to_numpy, COLUMN_NAMES
from risk import score_route_risk


def risk_level(score: int) -> str:
    if score <= 33:
        return "low"
    if score <= 66:
        return "medium"
    return "high"


def run_analysis(ship_from_city: str, ship_to_city: str, ship_date: str) -> dict:
    # Add country to reduce geocoding ambiguity
    start_q = f"{ship_from_city}, United Kingdom"
    end_q = f"{ship_to_city}, United Kingdom"

    start = city_to_coordinates(start_q)
    if start is None:
        raise ValueError(f"Could not geocode start city: {start_q}")

    end = city_to_coordinates(end_q)
    if end is None:
        raise ValueError(f"Could not geocode destination city: {end_q}")

    route_points = osrm_route_100_points(start, end, n_points=100)

    weather_np = weather_for_route_to_numpy(route_points, ship_date)

    score = score_route_risk(weather_np, COLUMN_NAMES)

    return {
        "risk_score": int(score),
        "risk_level": risk_level(int(score)),
    }
