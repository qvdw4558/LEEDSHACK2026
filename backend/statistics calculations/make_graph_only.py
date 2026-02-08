from graph import analyze_route, plot_efficiency_vs_risk

def build_points_fast(start, end, dates, speeds=(18.0, 22.0), base_speed=18.0):
    points = []
    for d in dates:
        base = analyze_route(start, end, d, speed_knots=base_speed)  # expensive once per date
        base_hours = base["hours"]
        risk = base["risk"]

        for sp in speeds:
            hours = base_hours * (base_speed / sp)
            points.append({"label": f"{d} @ {int(sp)}kn", "hours": hours, "risk": risk})

    return points

if __name__ == "__main__":
    start = "Leeds, UK"
    end = "Rotterdam, Netherlands"
    dates = ["2026-02-08", "2026-02-09"]
    speeds = (18.0, 22.0)

    points = build_points_fast(start, end, dates, speeds)

    out = plot_efficiency_vs_risk(
        points,
        out_path="../static/efficiency_vs_risk.png",
        title="Route Optimisation: Efficiency vs Risk"
    )
    print("Saved:", out)
