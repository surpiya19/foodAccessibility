# FoodPrint Score - Validation Results (Memphis (Shelby Co.), TN)

Tracts modeled: **242** of 249. Dropped: 47157011402, 47157021200, 47157980100, 47157980200, 47157980300, 47157980401, 47157980402 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.807 | 0.822 | +0.014 | +1.05 pts (+0.57, +1.53) | 0.000 | 0.000 | 3.82 | 3.70 |
| diabetes_pct | 0.744 | 0.754 | +0.010 | +0.69 pts (+0.02, +1.36) | 0.044 | 0.002 | 3.38 | 3.35 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| access_distance | +0.87 | 0.019 | 242 |
| vehicle_gap | +0.39 | 0.179 | 242 |
| affordability_proxy | +1.55 | 0.000 | 242 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 47157007500 | 77 | +8.0 | 53.0 | 19.9 | 1342 |
| 2 | 47157020523 | 100 | +1.8 | 52.0 | 46.5 | 3156 |
| 3 | 47157020521 | 65 | +5.7 | 50.8 | 21.3 | 3364 |
| 4 | 47157022210 | 65 | +4.5 | 48.3 | 16.2 | 4280 |
| 5 | 47157020544 | 72 | +1.3 | 50.1 | 36.2 | 2295 |
| 6 | 47157009700 | 59 | +4.4 | 44.7 | 17.3 | 3065 |
| 7 | 47157021755 | 74 | +0.4 | 45.8 | 24.1 | 1763 |
| 8 | 47157022410 | 54 | +4.2 | 45.8 | 24.9 | 5592 |
| 9 | 47157021751 | 40 | +7.3 | 41.0 | 9.1 | 7520 |
| 10 | 47157021620 | 55 | +3.5 | 41.9 | 16.5 | 3067 |

Tracts flagged as priority (score above median AND excess obesity > 0): 70 of 242.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
