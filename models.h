#ifndef MODELS_H
#define MODELS_H

#include <stddef.h>   // size_t
#include <stdint.h>   // uint32_t, int32_t

#define MAX_NAME_LEN         64
#define MAX_REGION_CODE_LEN  16
#define MAX_SEGMENTS         32

typedef enum
{
    RISK_LOW = 0,
    RISK_MEDIUM = 1,
    RISK_HIGH = 2
} RiskLevel;

typedef enum
{
    WX_NONE         = 0,
    WX_RAIN         = 1u << 0,
    WX_SNOW         = 1u << 1,
    WX_STORM        = 1u << 2,
    WX_HIGH_WIND    = 1u << 3,
    WX_EXTREME_TEMP = 1u << 4
} WeatherFlags;

typedef struct
{
    char code[MAX_REGION_CODE_LEN];  // e.g. "EU-WEST"
    char name[MAX_NAME_LEN];         // e.g. "Western Europe"
} Region;

/* Weather features per segment */
typedef struct
{
    int32_t  temperature_c;
    uint32_t wind_kph;
    uint32_t precipitation_mm;
    uint32_t visibility_km;

    uint32_t flags;      // WeatherFlags bitmask
    RiskLevel risk;      // derived or set
} WeatherSummary;

/* Cost outputs per segment */
typedef struct
{
    uint32_t base_cost_cents;
    uint32_t delay_cost_cents;
    uint32_t expected_segment_cost_cents;
} SegmentCostOutput;

typedef struct
{
    Region region;

    uint32_t start_time_utc;
    uint32_t end_time_utc;

    uint32_t distance_km;

    WeatherSummary weather;
    uint32_t expected_delay_minutes;

    SegmentCostOutput cost;
} RouteSegment;

/* Cost outputs for whole route */
typedef struct
{
    uint32_t total_base_cost_cents;
    uint32_t total_delay_cost_cents;
    uint32_t opportunity_cost_cents;
    uint32_t expected_total_cost_cents;
} RouteCostOutput;

typedef struct
{
    char route_id[32];

    RouteSegment segments[MAX_SEGMENTS];
    size_t segment_count;

    uint32_t total_distance_km;
    uint32_t total_expected_delay_minutes;

    RiskLevel overall_risk;

    RouteCostOutput cost;
} Route;

/* API */
void region_init(Region *r, const char *code, const char *name);

void route_init(Route *route, const char *route_id);
int  route_add_segment(Route *route, const RouteSegment *seg);

void segment_recalculate_cost(RouteSegment *seg, uint32_t delay_cost_per_minute_cents);
void route_recalculate_totals(Route *route, uint32_t delay_cost_per_minute_cents);

const char *risk_to_string(RiskLevel r);
void print_route(const Route *route);

#endif
