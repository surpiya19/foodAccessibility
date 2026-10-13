# FoodPrint Score - step 9: store-type score, chosen on Richmond + Baltimore, tested on Philadelphia
# Plan: docs/store_type_test_plan.md
#
#   python src/09_store_type_test.py select richmond baltimore
#       runs candidates A-C on the development cities, applies the selection rule,
#       writes outputs/store_test/chosen.json
#   python src/09_store_type_test.py test richmond baltimore philadelphia
#       runs the chosen score (and FARA-only for comparison) in every city;
#       the last city is the held-out test city
#
# Needs steps 1-6 and 05b for every city.

import json
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regions import ROOT, REGIONS

MODE, CITIES = sys.argv[1], sys.argv[2:]
OUT = ROOT / "outputs" / "store_test"
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATES = {
    "A. Store mix": ["limited_share", "dist_full_service_km"],
    "B. Store mix + affordability": ["limited_share", "dist_full_service_km", "affordability_proxy"],
    "C. Store mix + FARA": ["limited_share", "dist_full_service_km", "access_distance", "affordability_proxy"],
}
FARA_ONLY = ["access_distance", "vehicle_gap", "affordability_proxy"]
OUTCOMES = {"obesity_pct": "Obesity", "diabetes_pct": "Diabetes"}
COMPONENTS = ["limited_share", "dist_full_service_km", "access_distance", "vehicle_gap", "affordability_proxy"]
COLORS = ["#2a6f97", "#c8553d", "#6a994e", "#8d6a9f"]
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})

zs = lambda s: (s - s.mean()) / s.std()


def loo_rmse(fit):
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def load(city):
    m = pd.read_csv(ROOT / "data" / "processed" / city / "master_tract_table.csv", dtype={"tract_geoid": str})
    if "limited_share" not in m.columns:
        raise SystemExit(f"{city}: no store features. Run src/05b_snap_store_features.py {city} then step 6.")
    return m


def sample(m):
    d = m.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct"])
    return d[d["PCTGQTRS"] < 50].copy()


def score(m, feats):
    raw = pd.concat([zs(m[f]) for f in feats], axis=1).mean(axis=1, skipna=True)
    return 100 * (raw - raw.min()) / (raw.max() - raw.min())


def test(d, s, outcome):
    base = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income", data=d).fit()
    dd = d.assign(s=zs(s))
    full = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income + s", data=dd).fit()
    r = full.get_robustcov_results(cov_type="HC3")
    i = list(full.params.index).index("s")
    lo, hi = r.conf_int()[i]
    la, lb = loo_rmse(base), loo_rmse(full)
    return {"coef": r.params[i], "lo": lo, "hi": hi, "p": r.pvalues[i],
            "dr2": full.rsquared - base.rsquared, "loo_gain": la - lb, "loo_gain_pct": 100 * (la - lb) / la,
            "pass": bool(lo > 0 and lb < la), "resid": full.resid, "ids": dd["tract_geoid"]}


def morans_i(city, ids, x, perms=999):
    path = ROOT / "data" / "processed" / city / "tracts.geojson"
    import geopandas as gpd
    g = gpd.read_file(path)
    g["GEOID"] = g["GEOID"].astype(str)
    g = g.set_index("GEOID").loc[ids]
    W = np.array([[float(a.touches(b)) for b in g.geometry] for a in g.geometry])
    W = W / np.where(W.sum(1, keepdims=True) == 0, 1, W.sum(1, keepdims=True))
    z = np.asarray(x) - np.mean(x)
    stat = len(z) / W.sum() * (z @ W @ z) / (z @ z)
    rng = np.random.default_rng(0)
    sims = np.array([len(z) / W.sum() * (p @ W @ p) / (p @ p) for p in (rng.permutation(z) for _ in range(perms))])
    return stat, (np.sum(sims >= stat) + 1) / (perms + 1)


def fmt(r):
    return (f"{r['coef']:+.2f} ({r['lo']:+.2f}, {r['hi']:+.2f}) | {r['p']:.3f} | {r['dr2']:+.3f} | "
            f"{r['loo_gain_pct']:+.1f}% | {'yes' if r['pass'] else 'no'}")


HEAD = "| Coef per 1 SD (95% CI) | p | ΔR² | LOO gain | Pass |"

if MODE == "select":
    rows = []
    for city in CITIES:
        m = load(city)
        d = sample(m)
        for name, feats in CANDIDATES.items():
            s = score(m, feats).loc[d.index]
            for o in OUTCOMES:
                rows.append({"city": city, "candidate": name, "outcome": o, **{k: v for k, v in test(d, s, o).items()
                                                                                if k not in ("resid", "ids")}})
    res = pd.DataFrame(rows)
    avg = res.groupby("candidate")["loo_gain_pct"].mean().reindex(list(CANDIDATES))
    best = avg.max()
    # within 0.5 pts of the best -> take the one with fewest features
    close = [c for c in CANDIDATES if avg[c] >= best - 0.5]
    chosen = min(close, key=lambda c: len(CANDIDATES[c]))
    json.dump({"chosen": chosen, "features": CANDIDATES[chosen], "dev_cities": CITIES,
               "avg_loo_gain_pct": avg.round(3).to_dict()}, open(OUT / "chosen.json", "w"), indent=2)
    L = ["# Store-type score - selection on development cities", "",
         f"Cities: {', '.join(REGIONS[c]['name'] for c in CITIES)}. Rule: highest average LOO gain (%), "
         "ties within 0.5 pts go to fewer features.", "",
         "| City | Candidate | Outcome " + HEAD, "|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        L.append(f"| {REGIONS[r['city']]['name']} | {r['candidate']} | {OUTCOMES[r['outcome']]} | {fmt(r)} |")
    L += ["", "| Candidate | Average LOO gain |", "|---|---|"]
    L += [f"| {c} | {avg[c]:+.2f}% |" for c in CANDIDATES]
    L += ["", f"**Chosen: {chosen}** ({', '.join(CANDIDATES[chosen])})"]
    (OUT / "selection_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))

elif MODE == "test":
    chosen = json.load(open(OUT / "chosen.json"))
    versions = {"Chosen: " + chosen["chosen"]: chosen["features"], "FARA-only (comparison)": FARA_ONLY}
    test_city = CITIES[-1]
    rows, comps, moran, desc = [], [], [], []
    for city in CITIES:
        m = load(city)
        d = sample(m)
        desc.append((city, len(m), len(d), d["obesity_pct"].mean(), d["median_hh_income"].median(),
                     d["limited_share"].mean(), d["dist_full_service_km"].median()))
        for name, feats in versions.items():
            s = score(m, feats).loc[d.index]
            for o in OUTCOMES:
                r = test(d, s, o)
                if name.startswith("Chosen") and o == "obesity_pct":
                    moran.append((city, *morans_i(city, r["ids"], r["resid"])))
                rows.append({"city": city, "version": name, "outcome": o,
                             **{k: v for k, v in r.items() if k not in ("resid", "ids")}})
        for f in COMPONENTS:
            dd = d.dropna(subset=[f]).assign(x=lambda t: zs(t[f]))
            for o in OUTCOMES:
                fit = smf.ols(f"{o} ~ poverty_rate_pct + log_income + x", data=dd).fit(cov_type="HC3")
                lo, hi = fit.conf_int().loc["x"]
                comps.append({"city": city, "feature": f, "outcome": o, "coef": fit.params["x"],
                              "lo": lo, "hi": hi, "p": fit.pvalues["x"]})
    res, comp = pd.DataFrame(rows), pd.DataFrame(comps)
    res.round(4).to_csv(OUT / "test_results.csv", index=False)
    comp.round(4).to_csv(OUT / "test_components.csv", index=False)

    # figure: chosen score by city, both outcomes, test city highlighted
    fig, ax = plt.subplots(1, 2, figsize=(11, 0.6 * len(CITIES) * 2 + 1.8), sharey=True)
    labels = [f"{REGIONS[c]['name']}{' (test)' if c == test_city else ''}" for c in CITIES]
    ys = np.arange(len(CITIES))[::-1]
    for k, o in enumerate(OUTCOMES):
        for j, (v, col, off) in enumerate([(list(versions)[0], "#2a6f97", 0.12), (list(versions)[1], "#9a9a9a", -0.12)]):
            c = res[(res["version"] == v) & (res["outcome"] == o)].set_index("city").loc[CITIES]
            ax[k].errorbar(c["coef"], ys + off, xerr=[c["coef"] - c["lo"], c["hi"] - c["coef"]], fmt="o",
                           color=col, capsize=3, label=v)
        ax[k].axvline(0, color="black", lw=0.8)
        ax[k].axhspan(ys[-1] - 0.4, ys[-1] + 0.4, color="#c8553d", alpha=0.08)
        ax[k].set_title(OUTCOMES[o])
        ax[k].set_xlabel("Score effect per 1 SD beyond income and poverty\n(pct pts, 95% robust CI)")
    ax[0].set_yticks(ys, labels)
    ax[0].legend(frameon=False, fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(OUT / "fig_store_score_by_city.png", dpi=150, bbox_inches="tight")
    plt.close()

    # figure: each component by city
    nice = {"limited_share": "Limited-store share", "dist_full_service_km": "Distance to full-service store",
            "access_distance": "Access distance (FARA)", "vehicle_gap": "Vehicle gap",
            "affordability_proxy": "Affordability proxy"}
    fig, ax = plt.subplots(1, 2, figsize=(11, 0.7 * len(COMPONENTS) + 1.8), sharey=True)
    ys = np.arange(len(COMPONENTS))[::-1]
    for k, o in enumerate(OUTCOMES):
        for j, city in enumerate(CITIES):
            off = 0.2 - 0.4 * j / max(1, len(CITIES) - 1)
            c = comp[(comp["city"] == city) & (comp["outcome"] == o)].set_index("feature").loc[COMPONENTS]
            ax[k].errorbar(c["coef"], ys + off, xerr=[c["coef"] - c["lo"], c["hi"] - c["coef"]], fmt="o",
                           color=COLORS[j % len(COLORS)], capsize=2, label=REGIONS[city]["name"])
        ax[k].axvline(0, color="black", lw=0.8)
        ax[k].set_title(OUTCOMES[o])
        ax[k].set_xlabel("Effect per 1 SD beyond income and poverty\n(pct pts, 95% robust CI)")
    ax[0].set_yticks(ys, [nice[f] for f in COMPONENTS])
    ax[0].legend(frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig_store_components.png", dpi=150, bbox_inches="tight")
    plt.close()

    L = ["# Store-type score - held-out test", "",
         f"Chosen on development cities: **{chosen['chosen']}** ({', '.join(chosen['features'])}). "
         f"Test city: **{REGIONS[test_city]['name']}**. Plan: [`docs/store_type_test_plan.md`](../../docs/store_type_test_plan.md).", "",
         "## Cities", "", "| City | Tracts | Modeled | Mean obesity % | Median income | Mean limited-store share | Median km to full-service store |",
         "|---|---|---|---|---|---|---|"]
    for c, n, k, ob, inc, ls, dist in desc:
        L.append(f"| {REGIONS[c]['name']}{' (test)' if c == test_city else ''} | {n} | {k} | {ob:.1f} | ${inc:,.0f} | {ls:.2f} | {dist:.2f} |")
    L += ["", "## Score results", "", "| City | Version | Outcome " + HEAD, "|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        L.append(f"| {REGIONS[r['city']]['name']} | {r['version']} | {OUTCOMES[r['outcome']]} | {fmt(r)} |")
    L += ["", "## Each component on its own", "", "| Feature | Outcome | " + " | ".join(REGIONS[c]["name"] for c in CITIES) + " |",
          "|---|---|" + "---|" * len(CITIES)]
    for f in COMPONENTS:
        for o in OUTCOMES:
            cells = [comp[(comp["city"] == c) & (comp["feature"] == f) & (comp["outcome"] == o)].iloc[0] for c in CITIES]
            L.append(f"| {f} | {OUTCOMES[o]} | " + " | ".join(f"{r['coef']:+.2f} (p={r['p']:.3f})" for r in cells) + " |")
    L += ["", "## Spatial clustering of residuals (chosen score, obesity)", "", "| City | Moran's I | p |", "|---|---|---|"]
    L += [f"| {REGIONS[c]['name']} | {i:.3f} | {p:.3f} |" for c, i, p in moran]
    (OUT / "test_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
else:
    raise SystemExit("Mode must be 'select' or 'test'.")
