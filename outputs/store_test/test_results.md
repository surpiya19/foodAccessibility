# Store-type score - held-out test

Chosen on development cities: **C. Store mix + FARA** (limited_share, dist_full_service_km, access_distance, affordability_proxy). Test city: **Washington, DC**. Plan: [`docs/store_type_test_plan.md`](../../docs/store_type_test_plan.md).

## Cities

| City | Tracts | Modeled | Mean obesity % | Median income | Mean limited-store share | Median km to full-service store |
|---|---|---|---|---|---|---|
| Richmond, VA | 75 | 73 | 37.4 | $62,543 | 0.81 | 1.18 |
| Baltimore, MD | 199 | 193 | 39.4 | $56,723 | 0.83 | 0.87 |
| Washington, DC (test) | 206 | 198 | 25.0 | $110,896 | 0.64 | 0.65 |

## Score results

| City | Version | Outcome | Coef per 1 SD (95% CI) | p | ΔR² | LOO gain | Pass |
|---|---|---|---|---|---|---|---|
| Richmond, VA | Chosen: C. Store mix + FARA | Obesity | +2.03 (+0.89, +3.18) | 0.001 | +0.062 | +7.0% | yes |
| Richmond, VA | Chosen: C. Store mix + FARA | Diabetes | +2.17 (+1.28, +3.07) | 0.000 | +0.125 | +10.3% | yes |
| Richmond, VA | FARA-only (comparison) | Obesity | +1.87 (+0.19, +3.55) | 0.029 | +0.050 | +4.2% | yes |
| Richmond, VA | FARA-only (comparison) | Diabetes | +2.30 (+1.17, +3.43) | 0.000 | +0.135 | +10.4% | yes |
| Baltimore, MD | Chosen: C. Store mix + FARA | Obesity | +1.15 (+0.45, +1.84) | 0.001 | +0.020 | +2.7% | yes |
| Baltimore, MD | Chosen: C. Store mix + FARA | Diabetes | +1.06 (+0.54, +1.57) | 0.000 | +0.029 | +3.6% | yes |
| Baltimore, MD | FARA-only (comparison) | Obesity | +0.54 (-0.33, +1.41) | 0.223 | +0.004 | -0.1% | no |
| Baltimore, MD | FARA-only (comparison) | Diabetes | +0.82 (+0.38, +1.26) | 0.000 | +0.017 | +2.0% | yes |
| Washington, DC | Chosen: C. Store mix + FARA | Obesity | +1.51 (+0.98, +2.05) | 0.000 | +0.047 | +9.1% | yes |
| Washington, DC | Chosen: C. Store mix + FARA | Diabetes | +1.11 (+0.73, +1.48) | 0.000 | +0.072 | +9.9% | yes |
| Washington, DC | FARA-only (comparison) | Obesity | +0.65 (+0.31, +0.98) | 0.000 | +0.008 | +1.6% | yes |
| Washington, DC | FARA-only (comparison) | Diabetes | +0.51 (+0.20, +0.82) | 0.001 | +0.015 | +1.8% | yes |

## Each component on its own

| Feature | Outcome | Richmond, VA | Baltimore, MD | Washington, DC |
|---|---|---|---|---|
| limited_share | Obesity | -0.40 (p=0.455) | +1.43 (p=0.000) | +0.99 (p=0.003) |
| limited_share | Diabetes | -0.59 (p=0.210) | +0.60 (p=0.049) | +0.56 (p=0.002) |
| dist_full_service_km | Obesity | +1.25 (p=0.027) | +0.57 (p=0.118) | +1.50 (p=0.000) |
| dist_full_service_km | Diabetes | +1.45 (p=0.003) | +0.49 (p=0.119) | +1.17 (p=0.000) |
| access_distance | Obesity | +1.69 (p=0.003) | +0.12 (p=0.759) | +0.46 (p=0.032) |
| access_distance | Diabetes | +2.14 (p=0.000) | +0.73 (p=0.008) | +0.60 (p=0.004) |
| vehicle_gap | Obesity | +0.79 (p=0.717) | +0.46 (p=0.379) | +0.46 (p=0.015) |
| vehicle_gap | Diabetes | +1.59 (p=0.196) | +0.67 (p=0.006) | +0.38 (p=0.004) |
| affordability_proxy | Obesity | +2.68 (p=0.003) | +0.90 (p=0.003) | +0.85 (p=0.000) |
| affordability_proxy | Diabetes | +2.47 (p=0.003) | +0.91 (p=0.000) | +0.41 (p=0.012) |

## Spatial clustering of residuals (chosen score, obesity)

| City | Moran's I | p |
|---|---|---|
| Richmond, VA | 0.451 | 0.001 |
| Baltimore, MD | 0.334 | 0.001 |
| Washington, DC | 0.478 | 0.001 |
