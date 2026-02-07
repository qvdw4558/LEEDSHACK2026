#include "models.h"

#include <stdio.h>
#include <string.h>

static void copy_str(char *dst, size_t dst_size, const char *src)
{
    if (dst == NULL || dst_size == 0) return;

    if (src == NULL)
    {
        dst[0] = '\0';
        return;
    }

    strncpy(dst, src, dst_size - 1);
    dst[dst_size - 1] = '\0';
}

static void print_money_cents(uint32_t cents)
{
    uint32_t pounds = cents / 100;
    uint32_t rem = cents % 100;
    printf("%u.%02u", pounds, rem);
}

void region_init(Region *r, const char *code, const char *name)
{
    if (r == NULL) return;
    copy_str(r->code, sizeof(r->code), code);
    copy_str(r->name, sizeof(r->name), name);
}

void route_init(Route *route, const char *route_id)
{
    if (route == NULL) return;

    memset(route, 0, sizeof(*route));
    copy_str(route->route_id, sizeof(route->route_id), route_id);
    route->overall_risk = RISK_LOW;
}

int route_add_segment(Route *route, const RouteSegment *seg)
{
    if (route == NULL || seg == NULL) return 0;
    if (route->segment_count >= MAX_SEGMENTS) return 0;

    route->segments[route->segment_count] = *seg;
    route->segment_count++;
    return 1;
}

void segment_recalculate_cost(RouteSegment *seg, uint32_t delay_cost_per_minute_cents)
{
    if (seg == NULL) return;

    seg->cost.delay_cost_cents = seg->expected_delay_minutes * delay_cost_per_minute_cents;
    seg->cost.expected_segment_cost_cents =
        seg->cost.base_cost_cents + seg->cost.delay_cost_cents;
}

void route_recalculate_totals(Route *route, uint32_t delay_cost_per_minute_cents)
{
    size_t i;
    RiskLevel max_risk = RISK_LOW;

    if (route == NULL) return;

    route->total_distance_km = 0;
    route->total_expected_delay_minutes = 0;

    route->cost.total_base_cost_cents = 0;
    route->cost.total_delay_cost_cents = 0;

    for (i = 0; i < route->segment_count; i++)
    {
        RouteSegment *s = &route->segments[i];

        /* Ensure segment cost outputs are up to date */
        segment_recalculate_cost(s, delay_cost_per_minute_cents);

        route->total_distance_km += s->distance_km;
        route->total_expected_delay_minutes += s->expected_delay_minutes;

        route->cost.total_base_cost_cents += s->cost.base_cost_cents;
        route->cost.total_delay_cost_cents += s->cost.delay_cost_cents;

        if (s->weather.risk > max_risk)
            max_risk = s->weather.risk;
    }

    route->overall_risk = max_risk;

    route->cost.expected_total_cost_cents =
        route->cost.total_base_cost_cents +
        route->cost.total_delay_cost_cents +
        route->cost.opportunity_cost_cents;
}

const char *risk_to_string(RiskLevel r)
{
    switch (r)
    {
        case RISK_LOW:    return "LOW";
        case RISK_MEDIUM: return "MEDIUM";
        case RISK_HIGH:   return "HIGH";
        default:          return "UNKNOWN";
    }
}

void print_route(const Route *route)
{
    size_t i;
    if (route == NULL) return;

    printf("=== Route %s ===\n", route->route_id);
    printf("Segments: %u\n", (unsigned)route->segment_count);

    for (i = 0; i < route->segment_count; i++)
    {
        const RouteSegment *s = &route->segments[i];

        printf("\nSegment %u\n", (unsigned)(i + 1));
        printf("  Region: %s (%s)\n", s->region.name, s->region.code);
        printf("  Time:   %u -> %u (UTC unix)\n", s->start_time_utc, s->end_time_utc);
        printf("  Dist:   %u km\n", (unsigned)s->distance_km);

        printf("  Weather: temp=%dC wind=%ukph precip=%umm vis=%ukm flags=%u risk=%s\n",
               (int)s->weather.temperature_c,
               (unsigned)s->weather.wind_kph,
               (unsigned)s->weather.precipitation_mm,
               (unsigned)s->weather.visibility_km,
               (unsigned)s->weather.flags,
               risk_to_string(s->weather.risk));

        printf("  Expected delay: %u minutes\n", (unsigned)s->expected_delay_minutes);

        printf("  Segment costs:\n");
        printf("    Base:  "); print_money_cents(s->cost.base_cost_cents); printf("\n");
        printf("    Delay: "); print_money_cents(s->cost.delay_cost_cents); printf("\n");
        printf("    Expected segment total: ");
        print_money_cents(s->cost.expected_segment_cost_cents);
        printf("\n");
    }

    printf("\n--- Route Totals ---\n");
    printf("Total distance: %u km\n", (unsigned)route->total_distance_km);
    printf("Total delay:    %u minutes\n", (unsigned)route->total_expected_delay_minutes);
    printf("Overall risk:   %s\n", risk_to_string(route->overall_risk));

    printf("Costs:\n");
    printf("  Base total:       "); print_money_cents(route->cost.total_base_cost_cents); printf("\n");
    printf("  Delay total:      "); print_money_cents(route->cost.total_delay_cost_cents); printf("\n");
    printf("  Opportunity cost: "); print_money_cents(route->cost.opportunity_cost_cents); printf("\n");
    printf("  Expected total:   "); print_money_cents(route->cost.expected_total_cost_cents); printf("\n");
}
