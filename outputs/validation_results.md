# FoodPrint Score - Validation Results (Richmond, VA)

Tracts modeled: **73** of 75. Dropped: 51760021000, 51760040300 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.601 | 0.652 | +0.050 | +1.87 pts (+0.19, +3.55) | 0.029 | 0.002 | 5.29 | 5.07 |
| diabetes_pct | 0.397 | 0.532 | +0.135 | +2.30 pts (+1.17, +3.43) | 0.000 | 0.000 | 4.89 | 4.38 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| access_distance | +1.69 | 0.003 | 73 |
| vehicle_gap | +0.79 | 0.717 | 73 |
| affordability_proxy | +2.68 | 0.003 | 73 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 51760020100 | 94 | +4.0 | 56.0 | 58.1 | 1663 |
| 2 | 51760020200 | 73 | +4.7 | 56.9 | 57.4 | 3497 |
| 3 | 51760070901 | 53 | +8.0 | 41.4 | 7.4 | 4583 |
| 4 | 51760060700 | 55 | +4.9 | 51.6 | 44.0 | 5187 |
| 5 | 51760020400 | 63 | +2.8 | 52.5 | 43.9 | 4449 |
| 6 | 51760070700 | 54 | +4.7 | 41.1 | 11.2 | 5276 |
| 7 | 51760021100 | 53 | +4.2 | 47.2 | 28.9 | 1738 |
| 8 | 51760021200 | 48 | +5.1 | 42.3 | 10.8 | 1420 |
| 9 | 51760070804 | 53 | +2.5 | 40.3 | 14.3 | 3324 |
| 10 | 51760070902 | 44 | +4.2 | 45.3 | 23.5 | 2466 |

Tracts flagged as priority (score above median AND excess obesity > 0): 24 of 73.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
