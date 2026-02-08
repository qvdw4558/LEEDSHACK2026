#include "shipping_core.h"
#include "models.h"

#include <math.h>
#include <string.h>

// Must match Python COLUMN_NAMES order
enum {
    COL_LAT = 0,
    COL_LON = 1,
    COL_TEMP_MIN = 2,
    COL_TEMP_MAX = 3,
    COL_PRECIP_MM = 4,
    COL_PRECIP_PROB = 5,
    COL_SNOW_MM = 6,
    COL_WIND_SPEED = 7,
    COL_WIND_GUSTS = 8,
    COL_VISIBILITY = 9,
    COL_WEATHERCODE = 10
};

static double clamp01(double x) {
    if (x < 0.0) return 0.0;
    if (x > 1.0) return 1.0;
    return x;
}

static double weathercode_baseline(double code) {
    if (isnan(code)) return 0.2;
    int c = (int)llround(code);

    if (c == 0 || c == 1 || c == 2 || c == 3) return 0.05;
    if (c == 51 || c == 53 || c == 55 || c == 61 || c == 63 || c == 71 || c == 73) return 0.35;
    if (c == 45 || c == 48 || c == 56 || c == 57 || c == 65 || c == 66 || c == 67 ||
        c == 75 || c == 77 || c == 80 || c == 81 || c == 82 || c == 85 || c == 86) return 0.70;
    if (c == 95 || c == 96 || c == 99) return 0.90;

    return 0.30;
}

static RiskLevel risk_level_from_point(double pr) {
    // Align to your policy bands (roughly): <50 OK, 50-69 delays, >=70 unsafe
    // Convert pr [0..1] to score [1..100], then map.
    int score = (int)llround(1.0 + clamp01(pr) * 99.0);
    if (score >= 70) return RISK_HIGH;
    if (score >= 50) return RISK_MEDIUM;
    return RISK_LOW;
}

EXPORT int score_route_from_weather_matrix(const double* weather, int rows, int cols) {
    if (!weather || rows <= 0 || cols <= COL_WEATHERCODE) return -1;
    if (rows > MAX_SEGMENTS) return -2; // your C model supports up to 32 segments

    // Per-point risk array (small)
    double prisk[ MAX_SEGMENTS ];

    // Build a Route using your existing models (optional but “uses your C files” properly)
    Route route;
    route_init(&route, "PY-ROUTE");

    for (int i = 0; i < rows; i++) {
        const double* r = weather + (i * cols);

        double temp_min = r[COL_TEMP_MIN];
        double precip   = r[COL_PRECIP_MM];
        double prob     = r[COL_PRECIP_PROB];
        double snow     = r[COL_SNOW_MM];
        double gusts    = r[COL_WIND_GUSTS];
        double vis      = r[COL_VISIBILITY];
        double wcode    = r[COL_WEATHERCODE];

        // Defaults for NaNs
        if (isnan(temp_min)) temp_min = 5.0;
        if (isnan(precip))   precip = 0.0;
        if (isnan(prob))     prob = 0.0;
        if (isnan(snow))     snow = 0.0;
        if (isnan(gusts))    gusts = 0.0;
        if (isnan(vis))      vis = 20000.0;

        // Auto unit correction
        // visibility: if looks like km, convert to meters
        if (vis > 0.0 && vis < 200.0) vis *= 1000.0;
        // gusts: if looks like m/s, convert to km/h
        if (gusts > 0.0 && gusts < 30.0) gusts *= 3.6;

        double base = weathercode_baseline(wcode);

        // Less trigger-happy thresholds (calibrated)
        double gust_r   = clamp01((gusts - 60.0) / 40.0);         // 60..100 km/h
        double precip_r = clamp01((precip - 5.0) / 20.0);         // 5..25 mm/day
        double vis_r    = clamp01((3000.0 - vis) / 2500.0);       // <3km matters
        double ice_r    = (temp_min <= 0.0 && (precip > 0.2 || snow > 0.0)) ? 1.0 : 0.0;
        double snow_r   = clamp01((snow - 5.0) / 20.0);           // 5..25 mm/day
        double prob_r   = clamp01(prob / 100.0);

        // Weighted sum (more stable than max)
        double pr =
            0.25 * base +
            0.25 * gust_r +
            0.20 * precip_r +
            0.20 * vis_r +
            0.15 * snow_r +
            0.25 * ice_r +
            0.05 * prob_r;

        pr = clamp01(pr);
        prisk[i] = pr;

        // Populate your RouteSegment (so we really use models.c/h)
        RouteSegment seg;
        memset(&seg, 0, sizeof(seg));
        region_init(&seg.region, "AUTO", "Auto Segment");
        seg.distance_km = 1;                 // placeholder (optional)
        seg.cost.base_cost_cents = 0;         // placeholder (optional)

        seg.weather.temperature_c = (int32_t)llround(temp_min);
        seg.weather.wind_kph = (uint32_t)llround(gusts);
        seg.weather.precipitation_mm = (uint32_t)llround(precip);
        seg.weather.visibility_km = (uint32_t)llround(vis / 1000.0);
        seg.weather.flags = 0;
        seg.weather.risk = risk_level_from_point(pr);

        seg.expected_delay_minutes = 0;       // optional

        route_add_segment(&route, &seg);
    }

    // Aggregate risk across route points: 75th percentile (good balance)
    // sort prisk in-place (rows <= 32 => insertion sort is fine)
    for (int i = 1; i < rows; i++) {
        double key = prisk[i];
        int j = i - 1;
        while (j >= 0 && prisk[j] > key) {
            prisk[j + 1] = prisk[j];
            j--;
        }
        prisk[j + 1] = key;
    }
    int idx = (int)floor(0.75 * (rows - 1));
    double route_risk = prisk[idx];

    // Calibration: weight the final score lower (tune here)
    const double RISK_GAMMA = 1.6;
    const double RISK_SCALE = 0.75;

    double calibrated = pow(route_risk, RISK_GAMMA) * RISK_SCALE;
    calibrated = clamp01(calibrated);

    int score = (int)llround(1.0 + calibrated * 99.0);
    if (score < 1) score = 1;
    if (score > 100) score = 100;

    // Recalculate route totals (optional; uses your model)
    route_recalculate_totals(&route, 20u);

    return score;
}

EXPORT int risk_label_from_score(int score, char* out_buf, int out_buf_len) {
    if (!out_buf || out_buf_len <= 0) return -1;

    const char* label = "OK TO TRAVEL";
    if (score >= 70) label = "NOT SAFE TO TRAVEL";
    else if (score >= 50) label = "DELAYS LIKELY";

    strncpy(out_buf, label, (size_t)out_buf_len - 1);
    out_buf[out_buf_len - 1] = '\0';
    return 0;
}
