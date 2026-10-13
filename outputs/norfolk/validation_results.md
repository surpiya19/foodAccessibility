# FoodPrint Score - Validation Results (Norfolk, VA)

Tracts modeled: **74** of 81. Dropped: 51710000902, 51710004700, 51710004800, 51710980100, 51710980200, 51710980300, 51710990000 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.661 | 0.684 | +0.023 | +1.05 pts (+0.02, +2.07) | 0.046 | 0.026 | 4.19 | 4.09 |
| diabetes_pct | 0.481 | 0.526 | +0.045 | +1.11 pts (+0.32, +1.90) | 0.007 | 0.012 | 3.91 | 3.79 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| access_distance | +0.21 | 0.730 | 74 |
| vehicle_gap | +1.07 | 0.059 | 74 |
| affordability_proxy | +1.56 | 0.000 | 74 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 51710004600 | 100 | +7.8 | 52.9 | 23.2 | 1991 |
| 2 | 51710003501 | 46 | +7.8 | 55.6 | 32.9 | 3256 |
| 3 | 51710006400 | 74 | +1.1 | 46.0 | 24.0 | 3192 |
| 4 | 51710003300 | 49 | +4.7 | 45.9 | 20.7 | 2593 |
| 5 | 51710004500 | 30 | +8.4 | 47.7 | 18.3 | 1377 |
| 6 | 51710003400 | 42 | +4.2 | 48.8 | 23.1 | 2101 |
| 7 | 51710005100 | 46 | +2.8 | 52.4 | 37.8 | 3897 |
| 8 | 51710005000 | 25 | +5.9 | 54.1 | 37.9 | 3164 |
| 9 | 51710005702 | 31 | +4.5 | 42.6 | 15.1 | 2624 |
| 10 | 51710007002 | 33 | +3.3 | 41.5 | 12.2 | 3443 |

Tracts flagged as priority (score above median AND excess obesity > 0): 19 of 74.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
