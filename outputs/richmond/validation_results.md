# FoodPrint Score - Validation Results (Richmond, VA)

Tracts modeled: **73** of 75. Dropped: 51760021000, 51760040300 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.601 | 0.607 | +0.005 | +0.60 pts (-0.58, +1.78) | 0.314 | 0.337 | 5.29 | 5.31 |
| diabetes_pct | 0.397 | 0.427 | +0.030 | +1.06 pts (+0.15, +1.98) | 0.024 | 0.062 | 4.89 | 4.80 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| fast_food_ratio | -0.56 | 0.349 | 70 |
| delivery_proxy | -2.74 | 0.000 | 73 |
| access_distance | +1.69 | 0.003 | 73 |
| vehicle_gap | +0.79 | 0.717 | 73 |
| affordability_proxy | +2.68 | 0.003 | 73 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 51760020100 | 100 | +4.0 | 56.0 | 58.1 | 1663 |
| 2 | 51760020400 | 79 | +2.8 | 52.5 | 43.9 | 4449 |
| 3 | 51760060700 | 69 | +4.9 | 51.6 | 44.0 | 5187 |
| 4 | 51760020200 | 70 | +4.7 | 56.9 | 57.4 | 3497 |
| 5 | 51760021200 | 66 | +5.1 | 42.3 | 10.8 | 1420 |
| 6 | 51760070901 | 51 | +8.0 | 41.4 | 7.4 | 4583 |
| 7 | 51760041600 | 60 | +3.9 | 33.3 | 7.2 | 1421 |
| 8 | 51760070804 | 64 | +2.5 | 40.3 | 14.3 | 3324 |
| 9 | 51760011000 | 49 | +5.9 | 44.6 | 16.1 | 2169 |
| 10 | 51760060200 | 38 | +8.2 | 46.8 | 15.4 | 2237 |

Tracts flagged as priority (score above median AND excess obesity > 0): 22 of 73.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
