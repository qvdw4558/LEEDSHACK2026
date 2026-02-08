#ifndef SHIPPING_CORE_H
#define SHIPPING_CORE_H

#ifdef _WIN32
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Input: weather matrix (row-major) of shape [rows, cols], dtype double
// Output: route risk score 1..100 (negative on error)
EXPORT int score_route_from_weather_matrix(const double* weather, int rows, int cols);

// Output: policy label string for a score (>=70 unsafe, >=50 delays)
EXPORT int risk_label_from_score(int score, char* out_buf, int out_buf_len);

#ifdef __cplusplus
}
#endif

#endif
