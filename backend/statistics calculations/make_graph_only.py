import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from graph import analyze_route, plot_efficiency_vs_risk

if __name__ == "__main__":
    start = "Leeds, UK"
    end = "Rotterdam, Netherlands"
    dates = ["2026-02-08", "2026-02-09", "2026-02-10"]

    results = []
    for d in dates:
        r = analyze_route(start, end, d, speed_knots=18.0)
        results.append({"label": d, "hours": r["hours"], "risk": r["risk"]})

plot_efficiency_vs_risk(results, out_path="../static/efficiency_vs_risk.png")
print("Saved efficiency_vs_risk.png")
