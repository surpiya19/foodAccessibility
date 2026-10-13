# FoodPrint Score - Validation Results (Columbus (Franklin Co.), OH)

Tracts modeled: **325** of 328. Dropped: 39049001121, 39049001122, 39049980000 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.607 | 0.613 | +0.006 | +0.51 pts (+0.07, +0.95) | 0.023 | 0.030 | 4.27 | 4.25 |
| diabetes_pct | 0.355 | 0.380 | +0.025 | +0.74 pts (+0.33, +1.15) | 0.000 | 0.000 | 3.74 | 3.67 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| access_distance | +0.03 | 0.921 | 325 |
| vehicle_gap | +0.20 | 0.360 | 325 |
| affordability_proxy | +1.04 | 0.000 | 325 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 39049008730 | 100 | +4.2 | 47.3 | 40.1 | 1987 |
| 2 | 39049009323 | 62 | +7.4 | 48.9 | 35.4 | 3828 |
| 3 | 39049007552 | 62 | +6.7 | 43.5 | 30.2 | 3998 |
| 4 | 39049010300 | 80 | +0.0 | 36.0 | 12.3 | 2665 |
| 5 | 39049002750 | 59 | +3.9 | 46.7 | 38.6 | 2554 |
| 6 | 39049009498 | 51 | +5.6 | 40.1 | 20.9 | 3827 |
| 7 | 39049008380 | 61 | +2.3 | 34.3 | 8.9 | 5128 |
| 8 | 39049007512 | 44 | +6.4 | 44.1 | 16.4 | 4295 |
| 9 | 39049007532 | 49 | +4.9 | 46.2 | 28.1 | 2633 |
| 10 | 39049002730 | 51 | +4.1 | 51.1 | 57.3 | 2183 |

Tracts flagged as priority (score above median AND excess obesity > 0): 93 of 325.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
