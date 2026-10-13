# Store-type test plan - held-out city (Washington, DC)

Written 2026-10-13, after building the SNAP store-type features for Richmond and Baltimore but
before looking at how they relate to obesity or diabetes in any city, and before downloading
anything for Philadelphia.

## Why

The Baltimore test ([transfer_test_plan.md](transfer_test_plan.md)) showed the original score does not
transfer for obesity. The OSM restaurant features either did nothing (fast-food ratio) or pointed the
wrong way (delivery proxy). The one feature that held up in both cities was the affordability proxy.
This round replaces the restaurant features with the *type* of food stores nearby, from USDA's
historical SNAP retailer list (store type, location, open/close dates).

## New features (src/05b_snap_store_features.py)

Stores open on 2023-06-30 (to match the 2023 BRFSS behind PLACES), within 1 mile of the tract center.

- `limited_share` - share of nearby SNAP stores that are convenience, combination grocery/other
  (dollar stores, pharmacies) or small grocery stores. Higher = worse.
- `dist_full_service_km` - distance to the nearest supermarket, super store or large grocery. Higher = worse.
- `full_service_closures_5yr` - descriptive only, not used in any score (too sparse: mean 0.17 per tract in Richmond).

## Candidate scores

Equal-weight z-scores within each city, same as before.

| Candidate | Features |
|---|---|
| A. Store mix | limited_share, dist_full_service_km |
| B. Store mix + affordability | limited_share, dist_full_service_km, affordability_proxy |
| C. Store mix + FARA | limited_share, dist_full_service_km, access_distance, affordability_proxy |

The FARA-only score from the last round is also reported in Philadelphia as a comparison, but cannot be selected.

## Selection rule (development cities: Richmond, Baltimore)

For each candidate, compute the leave-one-out RMSE gain over income + poverty, as a percent of the
income-only RMSE, for obesity and diabetes in both cities. Pick the candidate with the **highest
average of those four numbers**. If two are within 0.5 percentage points, pick the one with fewer features.

The chosen score is then fixed and written into this file before Philadelphia data is downloaded.

## Change of test city (2026-10-13, before any outcome data was seen)

Philadelphia was the planned test city, but CDC's 2025 PLACES release has no 2023-BRFSS estimates
(including obesity and diabetes) for Pennsylvania or Kentucky, so step 1 returned no rows. No Philadelphia
health data was ever downloaded or looked at. Rather than mixing in an older PLACES release for one
city, the test city is switched to **Washington, DC** (FIPS 11001), which has every data source in the
same vintage as Richmond and Baltimore. The chosen score, model and pass rule are unchanged.

## Test (Washington, DC)

Same model and pass rule as before: coefficient > 0 with a 95% HC3 CI that excludes 0, **and**
lower leave-one-out RMSE than income + poverty alone.

Headline: the chosen score on **obesity** in Philadelphia. Diabetes is secondary.
No further changes to the score after Philadelphia, whatever the result.

## Additional held-out cities (added 2026-10-13, after the DC result, before any data for these cities)

Score C is applied unchanged to three more cities from the original shortlist, as further held-out tests:
Norfolk, VA (51710), Memphis / Shelby County, TN (47157) and Columbus / Franklin County, OH (39049).
Memphis and Columbus are whole counties (city plus suburbs), so the SNAP store search radius is widened
to 50 and 45 km to cover the county; nothing else changes. Philadelphia stays excluded (no 2023 PLACES
estimates for Pennsylvania). Every city is also re-estimated with a spatial error model as a check on
the clustering of neighboring tracts. Same pass rule.

## Chosen score

Selection run 2026-10-13 (`python src/09_store_type_test.py select richmond baltimore`,
full table in [`outputs/store_test/selection_results.md`](../outputs/store_test/selection_results.md)).

| Candidate | Average LOO gain (Richmond + Baltimore, obesity + diabetes) |
|---|---|
| A. Store mix | +0.71% |
| B. Store mix + affordability | +4.00% |
| C. Store mix + FARA | +5.89% |

**Chosen: C. Store mix + FARA** - limited_share, dist_full_service_km, access_distance, affordability_proxy.

Note: B and C both passed all four development checks. C's lead comes mostly from Richmond; B was more
even across the two cities. The rule picks C, so C is what gets tested. Fixed from here on.
