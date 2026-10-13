# Transfer test plan - Baltimore, MD

Written 2026-10-13, before any Baltimore data was downloaded or looked at.

## Why

In Richmond, the full five-feature score did not predict obesity beyond income, mainly because the
delivery proxy pointed the opposite way from what we assumed. Dropping it fixes the result in Richmond,
but we chose that change after seeing the data. Baltimore is the test of whether it holds up somewhere
the choice wasn't tuned on.

Baltimore city (FIPS 24510) is an independent city like Richmond, with a similar history of
disinvestment and food-access problems, so this is a replication test, not a generalizability test.

## Score versions (fixed now, not changed after seeing Baltimore)

| Version | Features | Status |
|---|---|---|
| Original | fast_food_ratio, delivery_proxy, access_distance, vehicle_gap, affordability_proxy | pre-specified in Richmond |
| Revised | fast_food_ratio, access_distance, vehicle_gap, affordability_proxy (drop delivery_proxy) | chosen after seeing Richmond |
| FARA-only | access_distance, vehicle_gap, affordability_proxy | chosen after seeing Richmond |

Everything else stays the same as Richmond: same feature definitions, 1/2 mile driving thresholds,
1 mile / 5 km radii, equal-weight z-scores computed within the city, same tract exclusions
(missing income, >50% group quarters), same OSM tags and 20 km download radius around downtown.

## Primary test

For each version and each outcome (obesity, diabetes):

    outcome ~ poverty_rate + log(median income) + score (per 1 SD)

**Pass** = score coefficient > 0 with a 95% HC3 confidence interval that excludes 0,
**and** leave-one-out RMSE lower than the income-only model.

The headline result is the **Revised score on obesity in Baltimore**.

## Secondary checks

- Does the delivery proxy have a negative coefficient again (beyond income)? If so, the Richmond
  finding replicates and the proxy measures urban density rather than a bad food environment.
- Each feature on its own, both outcomes, compared side by side with Richmond.
- Moran's I on the residuals. If they're clustered, p-values are optimistic in both cities.

## What would change the plan

- Revised passes in Baltimore: adopt it, report Richmond as the development city and Baltimore as the test.
- Revised fails in Baltimore: report that the score does not transfer as built. Do not tune again on Baltimore.
