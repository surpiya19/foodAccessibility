# FoodPrint Score - Robustness Checks (Richmond, VA)

Tracts modeled: 73. Score components: fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy.

## Score effect on obesity under different choices

| Variant | Obesity coef per 1 SD (95% CI) | p | LOO RMSE gain | Diabetes coef | p | Top-10 overlap |
|---|---|---|---|---|---|---|
| Main score | +0.60 (-0.58, +1.78) | 0.314 | -0.02 | +1.06 | 0.024 | 10/10 |
| Drop fast-food ratio | +0.83 (-0.61, +2.26) | 0.254 | -0.02 | +1.28 | 0.012 | 8/10 |
| Drop delivery proxy | +1.71 (+0.27, +3.16) | 0.021 | +0.20 | +2.15 | 0.000 | 8/10 |
| Drop access distance | -0.23 (-1.29, +0.83) | 0.663 | -0.04 | +0.13 | 0.795 | 7/10 |
| Drop vehicle gap | +0.38 (-0.58, +1.34) | 0.435 | -0.02 | +0.56 | 0.243 | 9/10 |
| Drop affordability proxy | -0.42 (-1.36, +0.52) | 0.379 | -0.03 | +0.26 | 0.586 | 6/10 |
| 1-mile thresholds | -0.29 (-1.18, +0.60) | 0.518 | -0.03 | +0.28 | 0.443 | 5/10 |

LOO RMSE gain = income-only error minus income+score error (positive = score helps).

## Each component on its own (beyond income and poverty)

| Feature | Outcome | Coef per 1 SD (95% CI) | p |
|---|---|---|---|
| fast_food_ratio | obesity_pct | -0.56 (-1.73, +0.61) | 0.349 |
| fast_food_ratio | diabetes_pct | -0.49 (-1.63, +0.65) | 0.401 |
| delivery_proxy | obesity_pct | -2.74 (-3.82, -1.66) | 0.000 |
| delivery_proxy | diabetes_pct | -2.76 (-3.65, -1.88) | 0.000 |
| access_distance | obesity_pct | +1.69 (+0.59, +2.79) | 0.003 |
| access_distance | diabetes_pct | +2.14 (+1.28, +3.01) | 0.000 |
| vehicle_gap | obesity_pct | +0.79 (-3.46, +5.04) | 0.717 |
| vehicle_gap | diabetes_pct | +1.59 (-0.82, +4.00) | 0.196 |
| affordability_proxy | obesity_pct | +2.68 (+0.90, +4.46) | 0.003 |
| affordability_proxy | diabetes_pct | +2.47 (+0.86, +4.08) | 0.003 |

## Spatial autocorrelation

| Variable | Moran's I | p (permutation) |
|---|---|---|
| Obesity | 0.597 | 0.001 |
| Residuals, income-only model | 0.522 | 0.001 |
| Residuals, income + score model | 0.516 | 0.001 |

If the residuals are still clustered (p < 0.05), neighboring tracts are not independent and the p-values above are somewhat too optimistic.
