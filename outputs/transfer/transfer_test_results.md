# FoodPrint Score - Transfer Test

Plan and pass rule: [`docs/transfer_test_plan.md`](../../docs/transfer_test_plan.md). Pass = coefficient > 0 with 95% robust CI excluding 0 **and** lower leave-one-out error than income alone.

## Cities

| City | Tracts | Modeled | Mean obesity % | Mean diabetes % | Median income | Mean poverty % |
|---|---|---|---|---|---|---|
| Richmond, VA | 75 | 73 | 37.4 | 13.1 | $62,543 | 18.3 |
| Baltimore, MD | 199 | 193 | 39.4 | 15.2 | $56,723 | 21.5 |

## Score versions

| City | Outcome | Version | Coef per 1 SD (95% CI) | p | ΔR² | LOO gain | Pass |
|---|---|---|---|---|---|---|---|
| Richmond, VA | Obesity | Original | +0.60 (-0.58, +1.78) | 0.314 | +0.005 | -0.02 | no |
| Richmond, VA | Obesity | Revised | +1.71 (+0.27, +3.16) | 0.021 | +0.042 | +0.20 | yes |
| Richmond, VA | Obesity | FARA-only | +1.87 (+0.19, +3.55) | 0.029 | +0.050 | +0.22 | yes |
| Richmond, VA | Diabetes | Original | +1.06 (+0.15, +1.98) | 0.024 | +0.030 | +0.09 | yes |
| Richmond, VA | Diabetes | Revised | +2.15 (+1.14, +3.16) | 0.000 | +0.119 | +0.45 | yes |
| Richmond, VA | Diabetes | FARA-only | +2.30 (+1.17, +3.43) | 0.000 | +0.135 | +0.51 | yes |
| Baltimore, MD | Obesity | Original | -0.02 (-1.06, +1.01) | 0.964 | +0.000 | -0.05 | no |
| Baltimore, MD | Obesity | Revised | +0.40 (-0.45, +1.24) | 0.355 | +0.002 | -0.02 | no |
| Baltimore, MD | Obesity | FARA-only | +0.54 (-0.33, +1.41) | 0.223 | +0.004 | -0.01 | no |
| Baltimore, MD | Diabetes | Original | +0.26 (-0.41, +0.94) | 0.443 | +0.002 | -0.02 | no |
| Baltimore, MD | Diabetes | Revised | +0.70 (+0.23, +1.18) | 0.004 | +0.012 | +0.05 | yes |
| Baltimore, MD | Diabetes | FARA-only | +0.82 (+0.38, +1.26) | 0.000 | +0.017 | +0.07 | yes |

## Components on their own

| Feature | Outcome | Richmond, VA | Baltimore, MD |
|---|---|---|---|
| fast_food_ratio | Obesity | -0.56 (p=0.349) | -0.38 (p=0.387) |
| fast_food_ratio | Diabetes | -0.49 (p=0.401) | -0.31 (p=0.336) |
| delivery_proxy | Obesity | -2.74 (p=0.000) | -1.32 (p=0.000) |
| delivery_proxy | Diabetes | -2.76 (p=0.000) | -1.43 (p=0.000) |
| access_distance | Obesity | +1.69 (p=0.003) | +0.12 (p=0.759) |
| access_distance | Diabetes | +2.14 (p=0.000) | +0.73 (p=0.008) |
| vehicle_gap | Obesity | +0.79 (p=0.717) | +0.46 (p=0.379) |
| vehicle_gap | Diabetes | +1.59 (p=0.196) | +0.67 (p=0.006) |
| affordability_proxy | Obesity | +2.68 (p=0.003) | +0.90 (p=0.003) |
| affordability_proxy | Diabetes | +2.47 (p=0.003) | +0.91 (p=0.000) |

## Spatial clustering of residuals (Revised score, obesity)

| City | Moran's I | p |
|---|---|---|
| Richmond, VA | 0.441 | 0.001 |
| Baltimore, MD | 0.377 | 0.001 |
