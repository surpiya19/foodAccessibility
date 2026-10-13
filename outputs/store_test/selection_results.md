# Store-type score - selection on development cities

Cities: Richmond, VA, Baltimore, MD. Rule: highest average LOO gain (%), ties within 0.5 pts go to fewer features.

| City | Candidate | Outcome | Coef per 1 SD (95% CI) | p | ΔR² | LOO gain | Pass |
|---|---|---|---|---|---|---|---|
| Richmond, VA | A. Store mix | Obesity | +0.56 (-0.52, +1.64) | 0.303 | +0.005 | -0.5% | no |
| Richmond, VA | A. Store mix | Diabetes | +0.58 (-0.45, +1.62) | 0.262 | +0.009 | -0.4% | no |
| Richmond, VA | B. Store mix + affordability | Obesity | +1.71 (+0.56, +2.87) | 0.004 | +0.040 | +4.1% | yes |
| Richmond, VA | B. Store mix + affordability | Diabetes | +1.64 (+0.59, +2.69) | 0.003 | +0.065 | +4.5% | yes |
| Richmond, VA | C. Store mix + FARA | Obesity | +2.03 (+0.89, +3.18) | 0.001 | +0.062 | +7.0% | yes |
| Richmond, VA | C. Store mix + FARA | Diabetes | +2.17 (+1.28, +3.07) | 0.000 | +0.125 | +10.3% | yes |
| Baltimore, MD | A. Store mix | Obesity | +1.23 (+0.46, +2.00) | 0.002 | +0.022 | +2.8% | yes |
| Baltimore, MD | A. Store mix | Diabetes | +0.68 (+0.05, +1.31) | 0.035 | +0.011 | +0.9% | yes |
| Baltimore, MD | B. Store mix + affordability | Obesity | +1.42 (+0.73, +2.11) | 0.000 | +0.030 | +4.3% | yes |
| Baltimore, MD | B. Store mix + affordability | Diabetes | +1.01 (+0.44, +1.57) | 0.001 | +0.026 | +3.0% | yes |
| Baltimore, MD | C. Store mix + FARA | Obesity | +1.15 (+0.45, +1.84) | 0.001 | +0.020 | +2.7% | yes |
| Baltimore, MD | C. Store mix + FARA | Diabetes | +1.06 (+0.54, +1.57) | 0.000 | +0.029 | +3.6% | yes |

| Candidate | Average LOO gain |
|---|---|
| A. Store mix | +0.71% |
| B. Store mix + affordability | +4.00% |
| C. Store mix + FARA | +5.89% |

**Chosen: C. Store mix + FARA** (limited_share, dist_full_service_km, access_distance, affordability_proxy)
