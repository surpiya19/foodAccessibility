# FoodPrint Score - step 6: build the score, validate it, rank the tracts
# Usage: python src/06_score_and_validate.py [region]
#
# Reads:
#   data/processed/<region>/places_acs.csv  from step 1 (PLACES obesity/diabetes + ACS income/poverty)
#   data/processed/<region>/fara2025.csv    from step 2 (USDA FARA 2025, 2020 tracts)
#   data/processed/<region>/construct_features.csv   OPTIONAL, from step 5 (fast-food ratio, delivery proxy)
# Writes:
#   data/processed/<region>/master_tract_table.csv   all inputs and features, one row per tract
#   outputs/<region>/foodprint_ranked_tracts.csv     tracts ranked by priority
#   outputs/<region>/validation_results.md           regression results
#   outputs/<region>/validation_plot.png
#
# Install: pip install -r requirements.txt

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regions import get_region

REGION = get_region()
PROCESSED = REGION["processed"]
OUTPUTS = REGION["outputs"]
FARA_CACHE = PROCESSED / "fara2025.csv"
CONSTRUCT = PROCESSED / "construct_features.csv"
ACS_MISSING_CODES = [-666666666, -999999999, -888888888, -222222222]  # Census "no estimate" codes


# ---------- Part 1: outcomes and income controls ----------
base = pd.read_csv(PROCESSED / "places_acs.csv", dtype={"tract_geoid": str})
base = base[["tract_geoid", "obesity_pct", "diabetes_pct", "median_hh_income", "poverty_rate_pct"]]
# -666666666 = no estimate; if left in it wrecks the income mean
base["median_hh_income"] = base["median_hh_income"].replace(ACS_MISSING_CODES, np.nan)
print("Tracts with PLACES + ACS:", len(base))
print("Tracts with missing income:", base["median_hh_income"].isna().sum())


# ---------- Part 2: FARA 2025 (2020 tract boundaries) ----------
if not FARA_CACHE.exists():
    raise SystemExit(f"Run src/02_extract_fara.py {REGION['key']} first.")
fara = pd.read_csv(FARA_CACHE, dtype={"CensusTract20": str}).rename(columns={"CensusTract20": "tract_geoid"})
fara = fara[["tract_geoid", "POP2020", "PCTGQTRS",
             "DD_SRAM_lapophalfshare", "DD_SRAM_lahunvhalfshare", "DD_SRAM_lasnaphalfshare"]]
master = base.merge(fara, on="tract_geoid", how="left")
print("Tracts matched to FARA:", master["POP2020"].notna().sum(), "of", len(master))


# ---------- Part 3: the CONSTRUCT features ----------
# all features: higher = worse food environment
# using driving distance (not straight-line) and the 1/2 mile urban threshold
master["access_distance"] = master["DD_SRAM_lapophalfshare"]    # % of people > 1/2 mile (driving) from a SNAP store
master["vehicle_gap"] = master["DD_SRAM_lahunvhalfshare"]       # % of homes with no car AND > 1/2 mile from a store
# no free price data, so affordability is proxied by SNAP households far from a store
# TODO: swap in price panel data if we collect it
master["affordability_proxy"] = master["DD_SRAM_lasnaphalfshare"]

features = ["access_distance", "vehicle_gap", "affordability_proxy"]

if CONSTRUCT.exists():
    construct = pd.read_csv(CONSTRUCT, dtype={"GEOID": str}).rename(columns={"GEOID": "tract_geoid"})
    master = master.merge(construct[["tract_geoid", "fast_food_ratio", "delivery_proxy"]],
                          on="tract_geoid", how="left")
    # more restaurants in delivery range = more prepared-food exposure (worse)
    features = ["fast_food_ratio", "delivery_proxy"] + features
    print("Using OpenStreetMap features from", CONSTRUCT)
else:
    print(f"NOTE: {CONSTRUCT} not found - run src/03, 04 and 05",
          "first to add fast_food_ratio and delivery_proxy.")


STORES = PROCESSED / "store_features.csv"
if STORES.exists():
    stores = pd.read_csv(STORES, dtype={"GEOID": str}).rename(columns={"GEOID": "tract_geoid"})
    master = master.merge(stores, on="tract_geoid", how="left")
    print("Added SNAP store-type features from", STORES)


# ---------- Part 4: combine into one FoodPrint Score ----------
# equal-weight mean of z-scores, rescaled to 0-100
# (not fitting weights - with ~75 tracts that would overfit and make validation circular)
for f in features:
    master["z_" + f] = (master[f] - master[f].mean()) / master[f].std()
z_cols = ["z_" + f for f in features]
master["score_raw"] = master[z_cols].mean(axis=1, skipna=True)
lo, hi = master["score_raw"].min(), master["score_raw"].max()
master["foodprint_score"] = 100 * (master["score_raw"] - lo) / (hi - lo)

master["log_income"] = np.log(master["median_hh_income"])
master.to_csv(PROCESSED / "master_tract_table.csv", index=False)


# ---------- Part 5: validate against income-only model ----------
# drop tracts with missing income or >50% group quarters (dorms, prisons)
model_df = master.dropna(subset=["obesity_pct", "diabetes_pct", "log_income",
                                 "poverty_rate_pct", "foodprint_score"])
model_df = model_df[model_df["PCTGQTRS"] < 50].copy()
dropped = sorted(set(master["tract_geoid"]) - set(model_df["tract_geoid"]))
n = len(model_df)

# standardize so the coef is per 1 SD of score
model_df["score_sd"] = (model_df["foodprint_score"] - model_df["foodprint_score"].mean()) / model_df["foodprint_score"].std()


def loo_rmse(fit):
    # leave-one-out RMSE via hat matrix (PRESS), no refitting needed
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def validate(outcome):
    control = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income", data=model_df).fit()
    full = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income + score_sd", data=model_df).fit()
    robust = full.get_robustcov_results(cov_type="HC3")
    i = list(full.params.index).index("score_sd")
    f_test = full.compare_f_test(control)
    return {
        "outcome": outcome,
        "r2_income_only": control.rsquared,
        "r2_with_score": full.rsquared,
        "delta_r2": full.rsquared - control.rsquared,
        "score_coef": robust.params[i],
        "ci_low": robust.conf_int()[i][0],
        "ci_high": robust.conf_int()[i][1],
        "p_robust": robust.pvalues[i],
        "f_test_p": f_test[1],
        "loo_rmse_income_only": loo_rmse(control),
        "loo_rmse_with_score": loo_rmse(full),
        "control_fit": control,
        "full_fit": full,
    }

results = [validate("obesity_pct"), validate("diabetes_pct")]

# each feature on its own, controlling for income
component_rows = []
for f in features:
    d = model_df.dropna(subset=[f]).copy()
    d["f_sd"] = (d[f] - d[f].mean()) / d[f].std()
    fit = smf.ols("obesity_pct ~ poverty_rate_pct + log_income + f_sd", data=d).fit(cov_type="HC3")
    component_rows.append((f, fit.params["f_sd"], fit.pvalues["f_sd"], len(d)))


# ---------- Part 6: rank tracts ----------
# priority = high score AND obesity above what income predicts (residual of income-only model)
ob = results[0]["control_fit"]
model_df["excess_obesity"] = ob.resid
zs = lambda s: (s - s.mean()) / s.std()
model_df["priority_index"] = zs(model_df["foodprint_score"]) + zs(model_df["excess_obesity"])
model_df["priority_flag"] = (model_df["foodprint_score"] > model_df["foodprint_score"].median()) & \
                            (model_df["excess_obesity"] > 0)
# flagged tracts first
ranked = model_df.sort_values(["priority_flag", "priority_index"], ascending=[False, False])
ranked.insert(0, "rank", range(1, len(ranked) + 1))
out_cols = ["rank", "tract_geoid", "priority_index", "priority_flag", "foodprint_score",
            "excess_obesity", "obesity_pct", "diabetes_pct", "poverty_rate_pct",
            "median_hh_income", "POP2020"] + features
ranked[out_cols].round(3).to_csv(OUTPUTS / "foodprint_ranked_tracts.csv", index=False)


# ---------- Part 7: write the results ----------
lines = [f"# FoodPrint Score - Validation Results ({REGION['name']})", "",
         f"Tracts modeled: **{n}** of {len(master)}. Dropped: {', '.join(dropped) or 'none'} "
         "(missing ACS income or >50% group quarters).", "",
         f"Score components (equal-weight z-scores, higher = worse): {', '.join(features)}", "",
         "## Does the score predict health beyond income and poverty?", "",
         "Model A: outcome ~ poverty rate + log(median income)  ",
         "Model B: Model A + FoodPrint Score (per 1 SD)", "",
         "| Outcome | R² A | R² B | ΔR² | Score coef (95% CI, robust) | p (robust) | p (F-test) | LOO RMSE A | LOO RMSE B |",
         "|---|---|---|---|---|---|---|---|---|"]
for r in results:
    lines.append(f"| {r['outcome']} | {r['r2_income_only']:.3f} | {r['r2_with_score']:.3f} | "
                 f"{r['delta_r2']:+.3f} | {r['score_coef']:+.2f} pts ({r['ci_low']:+.2f}, {r['ci_high']:+.2f}) | "
                 f"{r['p_robust']:.3f} | {r['f_test_p']:.3f} | {r['loo_rmse_income_only']:.2f} | "
                 f"{r['loo_rmse_with_score']:.2f} |")
lines += ["", "Reading it: the score 'passes' if its coefficient is positive with a CI that excludes 0, "
          "and the leave-one-out (LOO) error of Model B is lower than Model A's (it predicts held-out tracts better).",
          "", "## Each component on its own (obesity, beyond income)", "",
          "| Feature | Coef per 1 SD | p (robust) | n |", "|---|---|---|---|"]
for f, c, p, k in component_rows:
    lines.append(f"| {f} | {c:+.2f} | {p:.3f} | {k} |")
top = ranked.head(10)
lines += ["", "## Top 10 priority tracts", "",
          "| Rank | Tract | Score (0-100) | Excess obesity (pts) | Obesity % | Poverty % | Pop 2020 |",
          "|---|---|---|---|---|---|---|"]
for _, t in top.iterrows():
    lines.append(f"| {t['rank']} | {t['tract_geoid']} | {t['foodprint_score']:.0f} | {t['excess_obesity']:+.1f} | "
                 f"{t['obesity_pct']:.1f} | {t['poverty_rate_pct']:.1f} | {t['POP2020']:.0f} |")
lines += ["", f"Tracts flagged as priority (score above median AND excess obesity > 0): "
          f"{int(model_df['priority_flag'].sum())} of {n}.", "",
          "## Caveats", "",
          "- Cross-sectional and n is small: this is association beyond income, not causation.",
          "- PLACES values are model-based estimates that already use ACS demographics, which can inflate R² for the income-only model.",
          "- Affordability is a proxy (SNAP households far from a store) until real price data is collected.",
          "- FARA reflects SNAP retailers as of June 2025; PLACES uses 2023 BRFSS; ACS is 2019-2023."]
(OUTPUTS / "validation_results.md").write_text("\n".join(lines) + "\n")


# plot
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
ax[0].scatter(model_df["foodprint_score"], model_df["excess_obesity"], s=28, alpha=.75,
              c=np.where(model_df["priority_flag"], "#c8553d", "#2a6f97"))
b = np.polyfit(model_df["foodprint_score"], model_df["excess_obesity"], 1)
xs = np.linspace(0, 100, 50)
ax[0].plot(xs, b[0] * xs + b[1], color="#333333", lw=1.2)
ax[0].axhline(0, color="grey", lw=.6)
ax[0].set_xlabel("FoodPrint Score (0-100, higher = worse food environment)")
ax[0].set_ylabel("Obesity beyond income/poverty (pct pts)")
ax[0].set_title("Does the score explain what income doesn't?")
t10 = ranked.head(10)[::-1]
ax[1].barh("Tract " + t10["tract_geoid"].str[-6:], t10["priority_index"], color="#2a6f97")
ax[1].set_xlabel("Priority index (score + excess obesity)")
ax[1].set_title("Top 10 priority tracts")
for a in ax:
    a.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig(OUTPUTS / "validation_plot.png", dpi=150)

print("\n".join(lines[:20]))
print(f"\nWrote {PROCESSED / 'master_tract_table.csv'} and {OUTPUTS}/")
