# FoodPrint Score - Validation Results (Baltimore, MD)

Tracts modeled: **193** of 199. Dropped: 24510080500, 24510100300, 24510200100, 24510250600, 24510271102, 24510271801 (missing ACS income or >50% group quarters).

Score components (equal-weight z-scores, higher = worse): fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy

## Does the score predict health beyond income and poverty?

Model A: outcome ~ poverty rate + log(median income)  
Model B: Model A + FoodPrint Score (per 1 SD)

| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |
|---|---|---|---|---|---|---|---|---|
| obesity_pct | 0.685 | 0.685 | +0.000 | -0.02 pts (-1.06, +1.01) | 0.964 | 0.943 | 4.46 | 4.52 |
| diabetes_pct | 0.641 | 0.643 | +0.002 | +0.26 pts (-0.41, +0.94) | 0.443 | 0.327 | 3.70 | 3.72 |

Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).

## Each component on its own (obesity, beyond income)

| Feature | Coef per 1 SD | p (robust) | n |
|---|---|---|---|
| fast_food_ratio | -0.38 | 0.387 | 191 |
| delivery_proxy | -1.32 | 0.000 | 193 |
| access_distance | +0.12 | 0.759 | 193 |
| vehicle_gap | +0.46 | 0.379 | 193 |
| affordability_proxy | +0.90 | 0.003 | 193 |

## Top 10 priority tracts

| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |
|---|---|---|---|---|---|---|
| 1 | 24510280302 | 100 | +10.1 | 44.4 | 10.7 | 2121 |
| 2 | 24510130805 | 96 | +2.9 | 39.2 | 11.0 | 1108 |
| 3 | 24510270902 | 60 | +1.7 | 36.8 | 7.3 | 3794 |
| 4 | 24510270901 | 56 | +2.7 | 41.4 | 12.3 | 3808 |
| 5 | 24510270803 | 49 | +1.9 | 40.8 | 11.0 | 5697 |
| 6 | 24510280301 | 49 | +0.6 | 39.1 | 16.3 | 3672 |
| 7 | 24510280401 | 40 | +3.1 | 41.8 | 13.9 | 3393 |
| 8 | 24510080101 | 35 | +4.6 | 41.3 | 10.0 | 3336 |
| 9 | 24510250102 | 35 | +4.1 | 42.7 | 14.6 | 2860 |
| 10 | 24510250101 | 37 | +3.0 | 39.1 | 7.3 | 3874 |

Tracts flagged as priority (score above median AND excess obesity > 0): 50 of 193.

## Caveats

- Cross-sectional and n is small: this is association beyond income, not causation.
- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.
- Affordability is a proxy (SNAP households far from a store) until real price data is collected.
- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023.
