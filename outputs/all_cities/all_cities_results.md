# FoodPrint Score (store-type score C) - all cities

Score: limited_share, dist_full_service_km, access_distance, affordability_proxy (chosen on Richmond, VA + Baltimore, MD). Pass = robust 95% CI above 0 and lower leave-one-out error than income + poverty.

The spatial error model lets prediction errors be correlated between neighboring tracts (queen contiguity), which corrects the overconfident p-values from ordinary regression. λ is the strength of that neighbor correlation.

| City | Role | Tracts | Outcome | Coef (95% CI) | p | ΔR² | LOO gain | Pass | Spatial coef (95% CI) | Spatial p | λ | Moran's I (resid) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Richmond, VA | development | 73 | Obesity | +2.03 (+0.89, +3.18) | 0.001 | +0.062 | +7.0% | yes | +0.83 (-0.03, +1.70) | 0.060 | 0.85 | 0.45 |
| Richmond, VA | development | 73 | Diabetes | +2.17 (+1.28, +3.07) | 0.000 | +0.125 | +10.3% | yes | +1.29 (+0.44, +2.13) | 0.003 | 0.77 | 0.44 |
| Baltimore, MD | development | 193 | Obesity | +1.15 (+0.45, +1.84) | 0.001 | +0.020 | +2.7% | yes | +0.30 (-0.25, +0.85) | 0.293 | 0.76 | 0.33 |
| Baltimore, MD | development | 193 | Diabetes | +1.06 (+0.54, +1.57) | 0.000 | +0.029 | +3.6% | yes | +0.39 (-0.07, +0.84) | 0.094 | 0.72 | 0.37 |
| Washington, DC | held-out | 198 | Obesity | +1.51 (+0.98, +2.05) | 0.000 | +0.047 | +9.1% | yes | +0.54 (+0.21, +0.87) | 0.001 | 0.90 | 0.48 |
| Washington, DC | held-out | 198 | Diabetes | +1.11 (+0.73, +1.48) | 0.000 | +0.072 | +9.9% | yes | +0.32 (+0.04, +0.60) | 0.026 | 0.82 | 0.42 |
| Norfolk, VA | held-out | 74 | Obesity | +0.51 (-0.65, +1.67) | 0.386 | +0.006 | -1.1% | no | -0.12 (-0.97, +0.73) | 0.783 | 0.62 | 0.38 |
| Norfolk, VA | held-out | 74 | Diabetes | +0.48 (-0.42, +1.37) | 0.292 | +0.008 | -0.4% | no | -0.18 (-0.99, +0.63) | 0.662 | 0.60 | 0.37 |
| Memphis (Shelby Co.), TN | held-out | 242 | Obesity | +1.35 (+0.87, +1.84) | 0.000 | +0.023 | +5.8% | yes | +0.60 (+0.17, +1.03) | 0.007 | 0.80 | 0.36 |
| Memphis (Shelby Co.), TN | held-out | 242 | Diabetes | +1.09 (+0.58, +1.60) | 0.000 | +0.025 | +4.4% | yes | +0.83 (+0.41, +1.24) | 0.000 | 0.72 | 0.32 |
| Columbus (Franklin Co.), OH | held-out | 325 | Obesity | +0.93 (+0.50, +1.35) | 0.000 | +0.019 | +2.2% | yes | +0.43 (+0.09, +0.78) | 0.014 | 0.88 | 0.51 |
| Columbus (Franklin Co.), OH | held-out | 325 | Diabetes | +0.86 (+0.45, +1.26) | 0.000 | +0.034 | +2.4% | yes | +0.35 (+0.05, +0.66) | 0.023 | 0.88 | 0.53 |

Philadelphia is excluded: CDC PLACES 2025 has no 2023-BRFSS estimates for Pennsylvania.
