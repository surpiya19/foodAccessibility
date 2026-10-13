# FoodPrint Score - step 10: the locked store-type score (C) in every city, plus a spatial check
# Usage: python src/10_all_cities.py
# Needs steps 1, 2, 3, 05b and 6 for each city (04/05 are not used by score C).
# Score, model and pass rule: docs/store_type_test_plan.md
# Writes: outputs/all_cities/all_cities_results.md, .csv, and figures

import json
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from libpysal.weights import Queen, KNN, w_union
from spreg import ML_Error

from regions import ROOT, REGIONS

warnings.filterwarnings("ignore")
OUT = ROOT / "outputs" / "all_cities"
OUT.mkdir(parents=True, exist_ok=True)

chosen = json.load(open(ROOT / "outputs" / "store_test" / "chosen.json"))
FEATURES = chosen["features"]
DEV = chosen["dev_cities"]                       # richmond, baltimore
ORDER = ["richmond", "baltimore", "dc", "norfolk", "memphis", "columbus"]
OUTCOMES = {"obesity_pct": "Obesity", "diabetes_pct": "Diabetes"}
BLUE, ORANGE, GREY = "#2a6f97", "#d08c2f", "#9a9a9a"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})
zs = lambda s: (s - s.mean()) / s.std()


def loo_rmse(fit):
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def weights(city, ids):
    g = gpd.read_file(ROOT / "data" / "processed" / city / "tracts.geojson")
    g["GEOID"] = g["GEOID"].astype(str)
    g = g.set_index("GEOID").loc[list(ids)].reset_index()
    w = Queen.from_dataframe(g, use_index=False, silence_warnings=True)
    if w.islands:  # tracts with no touching neighbor get their nearest one
        w = w_union(w, KNN.from_dataframe(g, k=1, use_index=False, silence_warnings=True), silence_warnings=True)
    w.transform = "r"
    return w


def morans_i(w, x, perms=999):
    W = w.full()[0]
    z = np.asarray(x) - np.mean(x)
    stat = len(z) / W.sum() * (z @ W @ z) / (z @ z)
    rng = np.random.default_rng(0)
    sims = np.array([len(z) / W.sum() * (p @ W @ p) / (p @ p) for p in (rng.permutation(z) for _ in range(perms))])
    return stat, (np.sum(sims >= stat) + 1) / (perms + 1)


rows, skipped, desc = [], [], []
for city in ORDER:
    path = ROOT / "data" / "processed" / city / "master_tract_table.csv"
    if not path.exists():
        skipped.append(city)
        continue
    m = pd.read_csv(path, dtype={"tract_geoid": str})
    if not set(FEATURES) <= set(m.columns):
        skipped.append(city)
        continue
    raw = pd.concat([zs(m[f]) for f in FEATURES], axis=1).mean(axis=1, skipna=True)
    m["score"] = 100 * (raw - raw.min()) / (raw.max() - raw.min())
    d = m.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct", "score"])
    d = d[d["PCTGQTRS"] < 50].copy().reset_index(drop=True)
    d["s"] = zs(d["score"])
    w = weights(city, d["tract_geoid"])
    desc.append((city, len(m), len(d), d["obesity_pct"].mean(), d["median_hh_income"].median()))
    for o in OUTCOMES:
        base = smf.ols(f"{o} ~ poverty_rate_pct + log_income", data=d).fit()
        full = smf.ols(f"{o} ~ poverty_rate_pct + log_income + s", data=d).fit()
        r = full.get_robustcov_results(cov_type="HC3")
        i = list(full.params.index).index("s")
        lo, hi = r.conf_int()[i]
        la, lb = loo_rmse(base), loo_rmse(full)
        # spatial error model: lets errors be correlated between neighboring tracts
        X = d[["poverty_rate_pct", "log_income", "s"]].to_numpy()
        sem = ML_Error(d[[o]].to_numpy(), X, w=w, name_x=["poverty", "log_income", "score"])
        k = sem.name_x.index("score")
        b, se = float(sem.betas[k][0]), float(sem.std_err[k])
        mi, mp = morans_i(w, full.resid)
        rows.append({"city": city, "role": "development" if city in DEV else "held-out", "outcome": o,
                     "n": len(d), "coef": r.params[i], "lo": lo, "hi": hi, "p": r.pvalues[i],
                     "dr2": full.rsquared - base.rsquared, "loo_gain_pct": 100 * (la - lb) / la,
                     "pass": bool(lo > 0 and lb < la),
                     "sem_coef": b, "sem_lo": b - 1.96 * se, "sem_hi": b + 1.96 * se,
                     "sem_p": float(sem.z_stat[k][1]), "lambda": float(sem.lam),
                     "moran_resid": mi, "moran_p": mp})
    print("done", city)

res = pd.DataFrame(rows)
res.round(4).to_csv(OUT / "all_cities_results.csv", index=False)
cities = [c for c in ORDER if c in set(res["city"])]
label = {c: REGIONS[c]["name"] + ("  (dev)" if c in DEV else "") for c in cities}

# Figure 1: effect of score C in every city, ordinary vs spatial model
fig, ax = plt.subplots(1, 2, figsize=(11.5, 0.75 * len(cities) + 2), sharey=True)
ys = np.arange(len(cities))[::-1]
for k, o in enumerate(OUTCOMES):
    t = res[res["outcome"] == o].set_index("city").loc[cities]
    ax[k].errorbar(t["coef"], ys + 0.13, xerr=[t["coef"] - t["lo"], t["hi"] - t["coef"]], fmt="o",
                   color=BLUE, capsize=3, label="Regression (robust SE)")
    ax[k].errorbar(t["sem_coef"], ys - 0.13, xerr=[t["sem_coef"] - t["sem_lo"], t["sem_hi"] - t["sem_coef"]],
                   fmt="s", color=ORANGE, capsize=3, label="Spatial error model")
    ax[k].axvline(0, color="black", lw=0.8)
    n_dev = sum(c in DEV for c in cities)
    ax[k].axhspan(ys[n_dev - 1] - 0.5, ys[0] + 0.5, color=GREY, alpha=0.12)
    ax[k].set_title(OUTCOMES[o])
    ax[k].set_xlabel("Effect of +1 SD FoodPrint Score beyond income and poverty\n(pct pts, 95% CI)")
ax[0].set_yticks(ys, [label[c] for c in cities])
h = res[res["role"] == "held-out"]
n_test, n_pass, n_sem = len(h), int(h["pass"].sum()), int((h["sem_lo"] > 0).sum())
fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, -0.06))
fig.suptitle("Store-type score in every city (grey band = cities used to choose it)\n"
             f"Held-out city-outcome checks passed: {n_pass} of {n_test} (regression), "
             f"{n_sem} of {n_test} (spatial model)", y=1.04)
plt.tight_layout()
plt.savefig(OUT / "fig_all_cities_effect.png", dpi=150, bbox_inches="tight")
plt.close()

# Figure 2: how much better the score predicts held-out tracts
fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.arange(len(cities))
wd = 0.38
for j, (o, col) in enumerate([("obesity_pct", BLUE), ("diabetes_pct", "#c8553d")]):
    t = res[res["outcome"] == o].set_index("city").loc[cities]
    bars = ax.bar(x + (j - 0.5) * wd, t["loo_gain_pct"], wd, color=col, label=OUTCOMES[o])
    for xb, v in zip(x + (j - 0.5) * wd, t["loo_gain_pct"]):
        ax.text(xb, v + (0.2 if v >= 0 else -0.6), f"{v:.1f}", ha="center", fontsize=8)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x, [label[c].replace("  (dev)", "\n(dev)").replace(" (", "\n(", 1) if "Co." in label[c] else label[c].replace("  (dev)", "\n(dev)") for c in cities], fontsize=8.5)
ax.set_ylabel("Leave-one-out error reduction vs\nincome + poverty alone (%)")
ax.set_title("How much the score improves prediction of unseen tracts")
ax.legend(frameon=False)
plt.tight_layout()
plt.savefig(OUT / "fig_all_cities_loo.png", dpi=150)
plt.close()

# results table
L = ["# FoodPrint Score (store-type score C) - all cities", "",
     f"Score: {', '.join(FEATURES)} (chosen on {' + '.join(REGIONS[c]['name'] for c in DEV)}). "
     "Pass = robust 95% CI above 0 and lower leave-one-out error than income + poverty.", "",
     "The spatial error model lets prediction errors be correlated between neighboring tracts "
     "(queen contiguity), which corrects the overconfident p-values from ordinary regression. "
     "λ is the strength of that neighbor correlation.", "",
     "| City | Role | Tracts | Outcome | Coef (95% CI) | p | ΔR² | LOO gain | Pass | Spatial coef (95% CI) | Spatial p | λ | Moran's I (resid) |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for _, r in res.iterrows():
    L.append(f"| {REGIONS[r['city']]['name']} | {r['role']} | {r['n']} | {OUTCOMES[r['outcome']]} | "
             f"{r['coef']:+.2f} ({r['lo']:+.2f}, {r['hi']:+.2f}) | {r['p']:.3f} | {r['dr2']:+.3f} | "
             f"{r['loo_gain_pct']:+.1f}% | {'yes' if r['pass'] else 'no'} | "
             f"{r['sem_coef']:+.2f} ({r['sem_lo']:+.2f}, {r['sem_hi']:+.2f}) | {r['sem_p']:.3f} | "
             f"{r['lambda']:.2f} | {r['moran_resid']:.2f} |")
if skipped:
    L += ["", f"Not run (data missing): {', '.join(skipped)}."]
L += ["", "Philadelphia is excluded: CDC PLACES 2025 has no 2023-BRFSS estimates for Pennsylvania."]
(OUT / "all_cities_results.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
