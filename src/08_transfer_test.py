# FoodPrint Score - step 8: does the score transfer to another city?
# Usage: python src/08_transfer_test.py richmond baltimore
# Score versions and pass rule are fixed in docs/transfer_test_plan.md (written before
# looking at Baltimore). Run steps 1-6 for every city first.
# Reads:  data/processed/<city>/master_tract_table.csv, tracts.geojson (optional)
# Writes: outputs/transfer/transfer_test_results.md, outputs/transfer/*.png

import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regions import ROOT, REGIONS

CITIES = sys.argv[1:] or ["richmond", "baltimore"]
OUT = ROOT / "outputs" / "transfer"
OUT.mkdir(parents=True, exist_ok=True)

ALL = ["fast_food_ratio", "delivery_proxy", "access_distance", "vehicle_gap", "affordability_proxy"]
VERSIONS = {
    "Original": ALL,
    "Revised": ["fast_food_ratio", "access_distance", "vehicle_gap", "affordability_proxy"],
    "FARA-only": ["access_distance", "vehicle_gap", "affordability_proxy"],
}
OUTCOMES = {"obesity_pct": "Obesity", "diabetes_pct": "Diabetes"}
COLORS = {"richmond": "#2a6f97", "baltimore": "#c8553d"}
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})

zs = lambda s: (s - s.mean()) / s.std()


def loo_rmse(fit):
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def load(city):
    m = pd.read_csv(ROOT / "data" / "processed" / city / "master_tract_table.csv", dtype={"tract_geoid": str})
    missing = [f for f in ALL if f not in m.columns]
    if missing:
        raise SystemExit(f"{city}: missing {missing}. Run steps 3-6 for {city}.")
    return m


def score(master, feats):
    # equal-weight z-scores within the city, rescaled 0-100 (same as step 6)
    raw = pd.concat([zs(master[f]) for f in feats], axis=1).mean(axis=1, skipna=True)
    return 100 * (raw - raw.min()) / (raw.max() - raw.min())


def sample(master):
    d = master.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct"])
    return d[d["PCTGQTRS"] < 50].copy()


def morans_i(geo_path, ids, x, perms=999):
    if not geo_path.exists():
        return None
    import geopandas as gpd
    g = gpd.read_file(geo_path)
    g["GEOID"] = g["GEOID"].astype(str)
    g = g.set_index("GEOID").loc[ids]
    W = np.array([[float(a.touches(b)) for b in g.geometry] for a in g.geometry])
    W = W / np.where(W.sum(1, keepdims=True) == 0, 1, W.sum(1, keepdims=True))
    z = np.asarray(x) - np.mean(x)
    stat = len(z) / W.sum() * (z @ W @ z) / (z @ z)
    rng = np.random.default_rng(0)
    sims = np.array([len(z) / W.sum() * (p @ W @ p) / (p @ p) for p in (rng.permutation(z) for _ in range(perms))])
    return stat, (np.sum(sims >= stat) + 1) / (perms + 1)


rows, comps, desc, moran = [], [], [], []
for city in CITIES:
    master = load(city)
    for v, feats in VERSIONS.items():
        master["score_" + v] = score(master, feats)
    d = sample(master)
    desc.append((city, len(master), len(d), d["obesity_pct"].mean(), d["diabetes_pct"].mean(),
                 d["median_hh_income"].median(), d["poverty_rate_pct"].mean()))
    for o in OUTCOMES:
        base = smf.ols(f"{o} ~ poverty_rate_pct + log_income", data=d).fit()
        for v in VERSIONS:
            dd = d.assign(s=zs(d["score_" + v]))
            full = smf.ols(f"{o} ~ poverty_rate_pct + log_income + s", data=dd).fit()
            r = full.get_robustcov_results(cov_type="HC3")
            i = list(full.params.index).index("s")
            lo, hi = r.conf_int()[i]
            gain = loo_rmse(base) - loo_rmse(full)
            rows.append({"city": city, "outcome": o, "version": v, "coef": r.params[i], "lo": lo, "hi": hi,
                         "p": r.pvalues[i], "dr2": full.rsquared - base.rsquared, "loo_gain": gain,
                         "pass": bool(lo > 0 and gain > 0)})
            if o == "obesity_pct" and v == "Revised":
                mi = morans_i(ROOT / "data" / "processed" / city / "tracts.geojson", dd["tract_geoid"], full.resid)
                if mi:
                    moran.append((city, *mi))
        for f in ALL:
            dd = d.dropna(subset=[f]).assign(x=lambda t: zs(t[f]))
            fit = smf.ols(f"{o} ~ poverty_rate_pct + log_income + x", data=dd).fit(cov_type="HC3")
            lo, hi = fit.conf_int().loc["x"]
            comps.append({"city": city, "outcome": o, "feature": f, "coef": fit.params["x"],
                          "lo": lo, "hi": hi, "p": fit.pvalues["x"]})
res, comp = pd.DataFrame(rows), pd.DataFrame(comps)
res.round(4).to_csv(OUT / "transfer_results.csv", index=False)
comp.round(4).to_csv(OUT / "transfer_components.csv", index=False)


# ---------- figures ----------
def forest(df, ylabels, key, fname, title):
    fig, ax = plt.subplots(1, 2, figsize=(11, 0.55 * len(ylabels) + 1.8), sharey=True)
    ys = np.arange(len(ylabels))[::-1]
    for k, o in enumerate(OUTCOMES):
        for j, city in enumerate(CITIES):
            off = 0.15 - 0.3 * j / max(1, len(CITIES) - 1)
            c = df[(df["outcome"] == o) & (df["city"] == city)].set_index(key).loc[ylabels]
            ax[k].errorbar(c["coef"], ys + off, xerr=[c["coef"] - c["lo"], c["hi"] - c["coef"]], fmt="o",
                           color=COLORS.get(city, "grey"), capsize=3, label=REGIONS[city]["name"])
        ax[k].axvline(0, color="black", lw=0.8)
        ax[k].set_title(OUTCOMES[o])
        ax[k].set_xlabel("Effect of +1 SD beyond income and poverty\n(pct pts, 95% robust CI)")
    ax[0].set_yticks(ys, ylabels)
    ax[0].legend(frameon=False, loc="best")
    fig.suptitle(title, y=1.0)
    plt.tight_layout()
    plt.savefig(OUT / fname, dpi=150, bbox_inches="tight")
    plt.close()


forest(res, list(VERSIONS), "version", "fig_transfer_scores.png", "Score effect by version and city")
labels = {"fast_food_ratio": "Fast-food ratio", "delivery_proxy": "Delivery proxy",
          "access_distance": "Access distance", "vehicle_gap": "Vehicle gap",
          "affordability_proxy": "Affordability proxy"}
forest(comp.assign(feature=comp["feature"].map(labels)), list(labels.values()), "feature",
       "fig_transfer_components.png", "Each component on its own, by city")


# ---------- results ----------
L = ["# FoodPrint Score - Transfer Test", "",
     "Plan and pass rule: [`docs/transfer_test_plan.md`](../../docs/transfer_test_plan.md). "
     "Pass = coefficient > 0 with 95% robust CI excluding 0 **and** lower leave-one-out error than income alone.", "",
     "## Cities", "", "| City | Tracts | Modeled | Mean obesity % | Mean diabetes % | Median income | Mean poverty % |",
     "|---|---|---|---|---|---|---|"]
for c, n, m, ob, di, inc, pov in desc:
    L.append(f"| {REGIONS[c]['name']} | {n} | {m} | {ob:.1f} | {di:.1f} | ${inc:,.0f} | {pov:.1f} |")
L += ["", "## Score versions", "",
      "| City | Outcome | Version | Coef per 1 SD (95% CI) | p | ΔR² | LOO gain | Pass |", "|---|---|---|---|---|---|---|---|"]
for _, r in res.iterrows():
    L.append(f"| {REGIONS[r['city']]['name']} | {OUTCOMES[r['outcome']]} | {r['version']} | {r['coef']:+.2f} "
             f"({r['lo']:+.2f}, {r['hi']:+.2f}) | {r['p']:.3f} | {r['dr2']:+.3f} | {r['loo_gain']:+.2f} | "
             f"{'yes' if r['pass'] else 'no'} |")
L += ["", "## Components on their own", "", "| Feature | Outcome | " + " | ".join(REGIONS[c]["name"] for c in CITIES) + " |",
      "|---|---|" + "---|" * len(CITIES)]
for f in ALL:
    for o in OUTCOMES:
        cells = []
        for c in CITIES:
            r = comp[(comp["city"] == c) & (comp["outcome"] == o) & (comp["feature"] == f)].iloc[0]
            cells.append(f"{r['coef']:+.2f} (p={r['p']:.3f})")
        L.append(f"| {f} | {OUTCOMES[o]} | " + " | ".join(cells) + " |")
if moran:
    L += ["", "## Spatial clustering of residuals (Revised score, obesity)", "", "| City | Moran's I | p |", "|---|---|---|"]
    L += [f"| {REGIONS[c]['name']} | {i:.3f} | {p:.3f} |" for c, i, p in moran]
(OUT / "transfer_test_results.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
