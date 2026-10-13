# FoodPrint Score - Validation Results (Columbus (Franklin Co.), OH)

Tracts modeled: **325** of 328. Dropped: 39049001121, 39049001122, 39049980000 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.607 | 0.612 | +0.005 | -0.47 pts (-0.91, -0.02) | 0.039 | 0.045 | 4.27 | 4.25 |
| diabetes_pct | 0.355 | 0.357 | +0.003 | -0.24 pts (-0.63, +0.14) | 0.218 | 0.237 | 3.74 | 3.74 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| fast_food_ratio | -0.66 | 0.007 | 278 |
| delivery_proxy | -2.11 | 0.000 | 325 |
| access_distance | +0.03 | 0.921 | 325 |
| vehicle_gap | +0.20 | 0.360 | 325 |
| affordability_proxy | +1.04 | 0.000 | 325 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 39049008730 | 100 | +4.2 | 47.3 | 40.1 | 1987 |
| 2 | 39049007552 | 69 | +6.7 | 43.5 | 30.2 | 3998 |
| 3 | 39049009323 | 57 | +7.4 | 48.9 | 35.4 | 3828 |
| 4 | 39049010300 | 76 | +0.0 | 36.0 | 12.3 | 2665 |
| 5 | 39049008380 | 67 | +2.3 | 34.3 | 8.9 | 5128 |
| 6 | 39049002750 | 61 | +3.9 | 46.7 | 38.6 | 2554 |
| 7 | 39049007532 | 58 | +4.9 | 46.2 | 28.1 | 2633 |
| 8 | 39049002730 | 58 | +4.1 | 51.1 | 57.3 | 2183 |
| 9 | 39049007512 | 50 | +6.4 | 44.1 | 16.4 | 4295 |
| 10 | 39049009498 | 52 | +5.6 | 40.1 | 20.9 | 3827 |

Tracts flagged as priority (score above median AND excess obesity > 0): 77 of 325.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
