# FoodPrint Score - Robustness Checks (Baltimore, MD)

Tracts modeled: 193. Score components: fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy.

## Score effect on obesity under different choices

| Variant | Obesity coef per 1 SD (95% CI) | p | LOO RMSE gain | Diabetes coef | p | Top-10 overlap |
|---|---|---|---|---|---|---|
| Main score | -0.02 (-1.06, +1.01) | 0.964 | -0.05 | +0.26 | 0.443 | 10/10 |
| Drop fast-food ratio | +0.12 (-1.00, +1.25) | 0.828 | -0.06 | +0.39 | 0.212 | 6/10 |
| Drop delivery proxy | +0.40 (-0.45, +1.24) | 0.355 | -0.02 | +0.70 | 0.004 | 9/10 |
| Drop access distance | -0.08 (-1.16, +1.00) | 0.880 | -0.06 | +0.01 | 0.983 | 9/10 |
| Drop vehicle gap | -0.29 (-1.16, +0.58) | 0.506 | -0.03 | +0.01 | 0.989 | 9/10 |
| Drop affordability proxy | -0.52 (-1.47, +0.43) | 0.283 | -0.02 | -0.12 | 0.747 | 9/10 |
| 1-mile thresholds | -0.53 (-1.25, +0.20) | 0.153 | +0.00 | -0.40 | 0.128 | 2/10 |

LOO RMSE gain = income-only error minus income+score error (positive = score helps).

## Each component on its own (beyond income and poverty)

| Feature | Outcome | Coef per 1 SD (95% CI) | p |
|---|---|---|---|
| fast_food_ratio | obesity_pct | -0.38 (-1.23, +0.48) | 0.387 |
| fast_food_ratio | diabetes_pct | -0.31 (-0.94, +0.32) | 0.336 |
| delivery_proxy | obesity_pct | -1.32 (-2.02, -0.62) | 0.000 |
| delivery_proxy | diabetes_pct | -1.43 (-2.03, -0.83) | 0.000 |
| access_distance | obesity_pct | +0.12 (-0.65, +0.89) | 0.759 |
| access_distance | diabetes_pct | +0.73 (+0.19, +1.28) | 0.008 |
| vehicle_gap | obesity_pct | +0.46 (-0.57, +1.50) | 0.379 |
| vehicle_gap | diabetes_pct | +0.67 (+0.19, +1.15) | 0.006 |
| affordability_proxy | obesity_pct | +0.90 (+0.30, +1.50) | 0.003 |
| affordability_proxy | diabetes_pct | +0.91 (+0.55, +1.27) | 0.000 |

## Spatial autocorrelation

| Variable | Moran's I | p (permutation) |
|---|---|---|
| Obesity | 0.590 | 0.001 |
| Residuals, income-only model | 0.388 | 0.001 |
| Residuals, income + score model | 0.388 | 0.001 |

If the residuals are still clustered (p < 0.05), neighboring tracts are not independent and the p-values above are somewhat too optimistic.
