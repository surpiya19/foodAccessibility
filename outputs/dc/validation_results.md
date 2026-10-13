# FoodPrint Score - Validation Results (Washington, DC)

Tracts modeled: **198** of 206. Dropped: 11001000201, 11001000903, 11001006804, 11001007401, 11001007804, 11001009511, 11001010800, 11001980000 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.744 | 0.752 | +0.007 | -0.60 pts (-1.35, +0.15) | 0.116 | 0.017 | 3.55 | 3.54 |
| diabetes_pct | 0.634 | 0.645 | +0.011 | -0.42 pts (-0.85, -0.00) | 0.050 | 0.016 | 2.47 | 2.46 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| fast_food_ratio | -1.13 | 0.000 | 197 |
| delivery_proxy | -2.82 | 0.000 | 198 |
| access_distance | +0.46 | 0.032 | 198 |
| vehicle_gap | +0.46 | 0.015 | 198 |
| affordability_proxy | +0.85 | 0.000 | 198 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 11001010900 | 100 | +3.0 | 38.4 | 25.5 | 3333 |
| 2 | 11001009601 | 96 | +3.0 | 33.2 | 16.2 | 2086 |
| 3 | 11001006400 | 85 | +2.3 | 32.3 | 31.4 | 2481 |
| 4 | 11001009602 | 66 | +2.5 | 41.0 | 40.2 | 4481 |
| 5 | 11001007404 | 65 | +1.9 | 33.2 | 18.8 | 3637 |
| 6 | 11001001500 | 54 | +2.9 | 18.8 | 1.2 | 6156 |
| 7 | 11001000902 | 56 | +1.8 | 18.7 | 3.1 | 2317 |
| 8 | 11001009905 | 48 | +4.3 | 34.5 | 24.0 | 2790 |
| 9 | 11001002600 | 43 | +5.4 | 22.0 | 5.3 | 2592 |
| 10 | 11001010400 | 40 | +6.2 | 35.0 | 29.6 | 4616 |

Tracts flagged as priority (score above median AND excess obesity > 0): 37 of 198.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
