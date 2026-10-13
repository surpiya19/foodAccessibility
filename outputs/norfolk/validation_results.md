# FoodPrint Score - Validation Results (Norfolk, VA)

Tracts modeled: **74** of 81. Dropped: 51710000902, 51710004700, 51710004800, 51710980100, 51710980200, 51710980300, 51710990000 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.661 | 0.675 | +0.014 | +0.82 pts (-0.23, +1.87) | 0.123 | 0.084 | 4.19 | 4.15 |
| diabetes_pct | 0.481 | 0.514 | +0.033 | +0.95 pts (+0.25, +1.65) | 0.009 | 0.032 | 3.91 | 3.82 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| fast_food_ratio | -0.73 | 0.092 | 68 |
| delivery_proxy | +0.51 | 0.214 | 74 |
| access_distance | +0.21 | 0.730 | 74 |
| vehicle_gap | +1.07 | 0.059 | 74 |
| affordability_proxy | +1.56 | 0.000 | 74 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 51710004600 | 100 | +7.8 | 52.9 | 23.2 | 1991 |
| 2 | 51710003501 | 56 | +7.8 | 55.6 | 32.9 | 3256 |
| 3 | 51710006400 | 79 | +1.1 | 46.0 | 24.0 | 3192 |
| 4 | 51710003400 | 59 | +4.2 | 48.8 | 23.1 | 2101 |
| 5 | 51710003300 | 54 | +4.7 | 45.9 | 20.7 | 2593 |
| 6 | 51710004500 | 34 | +8.4 | 47.7 | 18.3 | 1377 |
| 7 | 51710005100 | 55 | +2.8 | 52.4 | 37.8 | 3897 |
| 8 | 51710005702 | 46 | +4.5 | 42.6 | 15.1 | 2624 |
| 9 | 51710005000 | 31 | +5.9 | 54.1 | 37.9 | 3164 |
| 10 | 51710004400 | 34 | +4.8 | 50.9 | 35.0 | 1542 |

Tracts flagged as priority (score above median AND excess obesity > 0): 20 of 74.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
