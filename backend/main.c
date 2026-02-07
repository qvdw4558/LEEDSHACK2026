#include <stdio.h>
#include <string.h>
#include "models.h"

static RouteSegment make_segment(const char *region_code,
                                const char *region_name,
                                uint32_t start_utc,
                                uint32_t end_utc,
                                uint32_t distance_km,
                                uint32_t base_cost_cents,
                                int32_t temperature_c,
                                uint32_t wind_kph,
                                uint32_t precip_mm,
                                uint32_t visibility_km,
                                uint32_t flags,
                                RiskLevel risk,
                                uint32_t expected_delay_minutes)
{
    RouteSegment seg;
    memset(&seg, 0, sizeof(seg));

    region_init(&seg.region, region_code, region_name);

    seg.start_time_utc = start_utc;
    seg.end_time_utc = end_utc;
    seg.distance_km = distance_km;

    seg.weather.temperature_c = temperature_c;
    seg.weather.wind_kph = wind_kph;
    seg.weather.precipitation_mm = precip_mm;
    seg.weather.visibility_km = visibility_km;
    seg.weather.flags = flags;
    seg.weather.risk = risk;

    seg.expected_delay_minutes = expected_delay_minutes;

    /* Base cost per segment */
    seg.cost.base_cost_cents = base_cost_cents;

    return seg;
}

int main(void)
{
    Route route;
    const uint32_t delay_cost_per_minute_cents = 20u; // MVP assumption

    route_init(&route, "ROUTE-001");

    RouteSegment s1 = make_segment(
        "EU-WEST", "Western Europe",
        1700000000u, 1700003600u,
        800u, 25000u,
        8, 40u, 12u, 10u,
        WX_RAIN, RISK_MEDIUM,
        35u
    );

    RouteSegment s2 = make_segment(
        "ATL", "Atlantic Crossing",
        1700003600u, 1700014400u,
        3000u, 90000u,
        6, 85u, 25u, 4u,
        (WX_STORM | WX_HIGH_WIND), RISK_HIGH,
        180u
    );

    if (!route_add_segment(&route, &s1))
    {
        printf("Failed to add segment 1\n");
        return 1;
    }

    if (!route_add_segment(&route, &s2))
    {
        printf("Failed to add segment 2\n");
        return 1;
    }

    /* Route-level opportunity cost */
    route.cost.opportunity_cost_cents = 5000u;

    route_recalculate_totals(&route, delay_cost_per_minute_cents);
    print_route(&route);

    return 0;
}
