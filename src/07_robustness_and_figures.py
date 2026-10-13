# FoodPrint Score - step 7: robustness checks and figures
# Usage: python src/07_robustness_and_figures.py [region]
# Run 06_score_and_validate.py first. Reads (from data/processed/<region>/):
#   master_tract_table.csv
#   fara2025.csv          for the 1-mile variant
#   tracts.geojson        OPTIONAL, from step 3 (map + Moran's I)
# Writes:
#   outputs/<region>/robustness_results.md
#   outputs/<region>/figures/*.png

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
FIGS = OUTPUTS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
TRACTS_GEO = PROCESSED / "tracts.geojson"

BLUE, RED, GREY = "#2a6f97", "#c8553d", "#9a9a9a"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold"})

LABELS = {"fast_food_ratio": "Fast-food ratio", "delivery_proxy": "Delivery proxy",
          "access_distance": "Access distance", "vehicle_gap": "Vehicle gap",
          "affordability_proxy": "Affordability proxy"}


# ---------- Part 1: rebuild the modeling sample (same rules as step 6) ----------
master = pd.read_csv(PROCESSED / "master_tract_table.csv", dtype={"tract_geoid": str})
features = [f for f in LABELS if f in master.columns]
print("Features in score:", features)

fara = pd.read_csv(PROCESSED / "fara2025.csv", dtype={"CensusTract20": str})
fara = fara.rename(columns={"CensusTract20": "tract_geoid"})
master = master.merge(fara[["tract_geoid", "DD_SRAM_lapop1share", "DD_SRAM_lahunv1share",
                            "DD_SRAM_lasnap1share"]], on="tract_geoid", how="left")
master["access_distance_1mi"] = master["DD_SRAM_lapop1share"]
master["vehicle_gap_1mi"] = master["DD_SRAM_lahunv1share"]
master["affordability_proxy_1mi"] = master["DD_SRAM_lasnap1share"]

df = master.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct"])
df = df[df["PCTGQTRS"] < 50].copy()
n = len(df)

zs = lambda s: (s - s.mean()) / s.std()


def make_score(data, feats):
    # same as step 6: equal-weight mean of z-scores (z computed on all 75 tracts), 0-100
    z = pd.concat([(master[f] - master[f].mean()) / master[f].std() for f in feats], axis=1)
    raw = z.mean(axis=1, skipna=True)
    score = 100 * (raw - raw.min()) / (raw.max() - raw.min())
    return score.loc[data.index]


def loo_rmse(fit):
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def test_score(data, score, outcome="obesity_pct"):
    d = data.assign(s=zs(score))
    a = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income", data=d).fit()
    b = smf.ols(f"{outcome} ~ poverty_rate_pct + log_income + s", data=d).fit()
    r = b.get_robustcov_results(cov_type="HC3")
    i = list(b.params.index).index("s")
    return {"coef": r.params[i], "lo": r.conf_int()[i][0], "hi": r.conf_int()[i][1],
            "p": r.pvalues[i], "r2_a": a.rsquared, "r2_b": b.rsquared,
            "loo_a": loo_rmse(a), "loo_b": loo_rmse(b), "fit_a": a}


def top10(data, score):
    excess = smf.ols("obesity_pct ~ poverty_rate_pct + log_income", data=data).fit().resid
    idx = zs(score) + zs(excess)
    flag = (score > score.median()) & (excess > 0)
    order = pd.DataFrame({"t": data["tract_geoid"], "f": flag, "i": idx})
    return set(order.sort_values(["f", "i"], ascending=False)["t"].head(10))


df["score"] = make_score(df, features)
main = {o: test_score(df, df["score"], o) for o in ["obesity_pct", "diabetes_pct"]}
base_top = top10(df, df["score"])


# ---------- Part 2: robustness variants ----------
variants = [("Main score", features)]
for f in features:
    variants.append((f"Drop {LABELS[f].lower()}", [g for g in features if g != f]))
variants.append(("1-mile thresholds", [f + "_1mi" if f + "_1mi" in df.columns else f for f in features]))

rob = []
for name, feats in variants:
    s = make_score(df, feats)
    r = test_score(df, s)
    rd = test_score(df, s, "diabetes_pct")
    rob.append({"variant": name, "coef": r["coef"], "lo": r["lo"], "hi": r["hi"], "p": r["p"],
                "loo_gain": r["loo_a"] - r["loo_b"], "diab_coef": rd["coef"], "diab_p": rd["p"],
                "top10_overlap": len(top10(df, s) & base_top)})
rob = pd.DataFrame(rob)

# each component on its own, both outcomes
comp = []
for f in features:
    d = df.dropna(subset=[f]).copy()
    d["x"] = zs(d[f])
    for o in ["obesity_pct", "diabetes_pct"]:
        fit = smf.ols(f"{o} ~ poverty_rate_pct + log_income + x", data=d).fit(cov_type="HC3")
        lo, hi = fit.conf_int().loc["x"]
        comp.append({"feature": f, "outcome": o, "coef": fit.params["x"], "lo": lo, "hi": hi,
                     "p": fit.pvalues["x"]})
comp = pd.DataFrame(comp)


# ---------- Part 3: spatial autocorrelation (needs tract boundaries from step 3) ----------
geo = None
moran_lines = [f"Skipped: {TRACTS_GEO} not found (run src/03 first)."]
if TRACTS_GEO.exists():
    import geopandas as gpd
    geo = gpd.read_file(TRACTS_GEO).rename(columns={"GEOID": "tract_geoid"})
    geo["tract_geoid"] = geo["tract_geoid"].astype(str)
    g = geo.set_index("tract_geoid").loc[df["tract_geoid"]]
    # queen contiguity: tracts that share any boundary point are neighbors
    W = np.array([[float(a.touches(b)) for b in g.geometry] for a in g.geometry])
    W = W / np.where(W.sum(1, keepdims=True) == 0, 1, W.sum(1, keepdims=True))

    def morans_i(x, perms=999, seed=0):
        z = np.asarray(x) - np.mean(x)
        stat = len(z) / W.sum() * (z @ W @ z) / (z @ z)
        rng = np.random.default_rng(seed)
        sims = [len(z) / W.sum() * (p @ W @ p) / (p @ p) for p in (rng.permutation(z) for _ in range(perms))]
        return stat, (np.sum(np.array(sims) >= stat) + 1) / (perms + 1)

    full_fit = smf.ols("obesity_pct ~ poverty_rate_pct + log_income + s",
                       data=df.assign(s=zs(df["score"]))).fit()
    moran_lines = []
    for name, x in [("Obesity", df["obesity_pct"]),
                    ("Residuals, income-only model", main["obesity_pct"]["fit_a"].resid),
                    ("Residuals, income + score model", full_fit.resid)]:
        i, p = morans_i(x)
        moran_lines.append(f"| {name} | {i:.3f} | {p:.3f} |")
    moran_lines = ["| Variable | Moran's I | p (permutation) |", "|---|---|---|"] + moran_lines


# ---------- Part 4: figures ----------
# Fig 1: does adding the score improve the model?
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
outs = ["obesity_pct", "diabetes_pct"]
x = np.arange(2)
w = 0.36
for k, (key_a, key_b, title, ylab) in enumerate([
        ("r2_a", "r2_b", "Variance explained (R²)", "R²"),
        ("loo_a", "loo_b", "Prediction error on held-out tracts", "Leave-one-out RMSE (pct pts)")]):
    va = [main[o][key_a] for o in outs]
    vb = [main[o][key_b] for o in outs]
    ax[k].bar(x - w / 2, va, w, color=GREY, label="Income + poverty")
    ax[k].bar(x + w / 2, vb, w, color=BLUE, label="+ FoodPrint Score")
    for xi, a_, b_ in zip(x, va, vb):
        ax[k].text(xi - w / 2, a_, f"{a_:.2f}", ha="center", va="bottom", fontsize=9)
        ax[k].text(xi + w / 2, b_, f"{b_:.2f}", ha="center", va="bottom", fontsize=9)
    ax[k].set_xticks(x, ["Obesity", "Diabetes"])
    ax[k].set_title(title)
    ax[k].set_ylabel(ylab)
ax[0].legend(frameon=False, loc="upper right")
helps = all(main[o]["loo_b"] < main[o]["loo_a"] for o in outs)
fig.suptitle("Adding the FoodPrint Score to income + poverty" + (" lowers held-out error for both outcomes" if helps else ""), y=1.02)
plt.tight_layout()
plt.savefig(FIGS / "fig1_model_comparison.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 2: which components carry the signal?
fig, ax = plt.subplots(figsize=(7, 0.6 * len(features) + 1.6))
ys = np.arange(len(features))[::-1]
for j, (o, col, off) in enumerate([("obesity_pct", BLUE, 0.15), ("diabetes_pct", RED, -0.15)]):
    c = comp[comp["outcome"] == o].set_index("feature").loc[features]
    ax.errorbar(c["coef"], ys + off, xerr=[c["coef"] - c["lo"], c["hi"] - c["coef"]], fmt="o",
                color=col, capsize=3, label=o.replace("_pct", "").capitalize())
ax.axvline(0, color="black", lw=0.8)
ax.set_yticks(ys, [LABELS[f] for f in features])
ax.set_xlabel("Effect of +1 SD, beyond income and poverty (pct pts, 95% robust CI)")
ax.set_title("Each component on its own, beyond income and poverty")
ax.legend(frameon=False)
plt.tight_layout()
plt.savefig(FIGS / "fig2_components.png", dpi=150)
plt.close()

# Fig 3: added-variable plot for the score (obesity)
ctrl = "poverty_rate_pct + log_income"
ry = smf.ols(f"obesity_pct ~ {ctrl}", data=df).fit().resid
rx = smf.ols(f"score ~ {ctrl}", data=df).fit().resid
flag = (df["score"] > df["score"].median()) & (ry > 0)
fig, ax = plt.subplots(figsize=(6.5, 4.8))
ax.scatter(rx, ry, s=30, alpha=0.8, c=np.where(flag, RED, BLUE))
b = np.polyfit(rx, ry, 1)
xs = np.linspace(rx.min(), rx.max(), 50)
ax.plot(xs, b[0] * xs + b[1], color="#333333", lw=1.2)
ax.axhline(0, color=GREY, lw=0.6)
ax.axvline(0, color=GREY, lw=0.6)
for t in pd.read_csv(OUTPUTS / "foodprint_ranked_tracts.csv", dtype={"tract_geoid": str})["tract_geoid"].head(3):
    m = df["tract_geoid"] == t
    if m.any():
        ax.annotate(t[-6:], (rx[m].iloc[0], ry[m].iloc[0]), xytext=(5, 4),
                    textcoords="offset points", fontsize=8)
ax.set_xlabel("FoodPrint Score not explained by income/poverty")
ax.set_ylabel("Obesity not explained by income/poverty (pct pts)")
ax.set_title(f"Score vs obesity, holding income fixed (slope p = {main['obesity_pct']['p']:.3f})")
ax.scatter([], [], c=RED, label="Priority tract"); ax.scatter([], [], c=BLUE, label="Other")
ax.legend(frameon=False, loc="upper left")
plt.tight_layout()
plt.savefig(FIGS / "fig3_added_variable.png", dpi=150)
plt.close()

# Fig 4: access distance only shows up once income is controlled for
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
r_raw = df["access_distance"].corr(df["obesity_pct"])
ax[0].scatter(df["access_distance"], df["obesity_pct"], s=25, alpha=0.75, color=GREY)
ax[0].set_xlabel("% of people > 1/2 mile (driving) from a SNAP store")
ax[0].set_ylabel("Obesity %")
ax[0].set_title(f"Raw relationship (r = {r_raw:.2f})")
rxa = smf.ols(f"access_distance ~ {ctrl}", data=df).fit().resid
r_part = np.corrcoef(rxa, ry)[0, 1]
ax[1].scatter(rxa, ry, s=25, alpha=0.75, color=BLUE)
b = np.polyfit(rxa, ry, 1)
xs = np.linspace(rxa.min(), rxa.max(), 50)
ax[1].plot(xs, b[0] * xs + b[1], color="#333333", lw=1.2)
ax[1].axhline(0, color=GREY, lw=0.6)
ax[1].set_xlabel("Access distance not explained by income/poverty")
ax[1].set_ylabel("Obesity not explained by income/poverty")
ax[1].set_title(f"Holding income and poverty fixed (partial r = {r_part:.2f})")
plt.tight_layout()
plt.savefig(FIGS / "fig4_access_income_masking.png", dpi=150)
plt.close()

# Fig 5: robustness of the score effect
fig, ax = plt.subplots(figsize=(7.5, 0.5 * len(rob) + 1.6))
ys = np.arange(len(rob))[::-1]
ax.errorbar(rob["coef"], ys, xerr=[rob["coef"] - rob["lo"], rob["hi"] - rob["coef"]], fmt="o",
            color=BLUE, capsize=3)
ax.axvline(0, color="black", lw=0.8)
ax.set_yticks(ys, rob["variant"])
for y, (_, r) in zip(ys, rob.iterrows()):
    ax.text(ax.get_xlim()[1], y, f"  top-10 overlap {r['top10_overlap']}/10", va="center", fontsize=8)
ax.set_xlabel("Score effect on obesity, per 1 SD (pct pts, 95% robust CI)")
ax.set_title("How much the result depends on each choice")
plt.tight_layout()
plt.savefig(FIGS / "fig5_robustness.png", dpi=150, bbox_inches="tight")
plt.close()

# Fig 6: map (only if tract boundaries exist)
if geo is not None:
    gm = geo.merge(df[["tract_geoid", "score"]].assign(flag=flag.values), on="tract_geoid", how="left")
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.5))
    gm.plot(column="score", cmap="YlOrRd", ax=ax[0], edgecolor="white", linewidth=0.4,
            legend=True, missing_kwds={"color": "#eeeeee"},
            legend_kwds={"label": "FoodPrint Score (0-100)", "shrink": 0.6})
    ax[0].set_title("FoodPrint Score by tract")
    gm.plot(color=np.where(gm["flag"] == True, RED, "#dddddd"), ax=ax[1], edgecolor="white", linewidth=0.4)
    ax[1].set_title(f"Priority tracts ({int(flag.sum())} of {n})")
    for a in ax:
        a.set_axis_off()
    plt.tight_layout()
    plt.savefig(FIGS / "fig6_priority_map.png", dpi=150)
    plt.close()


# ---------- Part 5: write the results ----------
lines = [f"# FoodPrint Score - Robustness Checks ({REGION['name']})", "",
         f"Tracts modeled: {n}. Score components: {', '.join(features)}.", "",
         "## Score effect on obesity under different choices", "",
         "| Variant | Obesity coef per 1 SD (95% CI) | p | LOO RMSE gain | Diabetes coef | p | Top-10 overlap |",
         "|---|---|---|---|---|---|---|"]
for _, r in rob.iterrows():
    lines.append(f"| {r['variant']} | {r['coef']:+.2f} ({r['lo']:+.2f}, {r['hi']:+.2f}) | {r['p']:.3f} | "
                 f"{r['loo_gain']:+.2f} | {r['diab_coef']:+.2f} | {r['diab_p']:.3f} | {r['top10_overlap']}/10 |")
lines += ["", "LOO RMSE gain = income-only error minus income+score error (positive = score helps).", "",
          "## Each component on its own (beyond income and poverty)", "",
          "| Feature | Outcome | Coef per 1 SD (95% CI) | p |", "|---|---|---|---|"]
for _, r in comp.iterrows():
    lines.append(f"| {r['feature']} | {r['outcome']} | {r['coef']:+.2f} ({r['lo']:+.2f}, {r['hi']:+.2f}) | {r['p']:.3f} |")
lines += ["", "## Spatial autocorrelation", ""] + moran_lines + ["",
          "If the residuals are still clustered (p < 0.05), neighboring tracts are not independent "
          "and the p-values above are somewhat too optimistic."]
(OUTPUTS / "robustness_results.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
print("\nFigures written to", FIGS)
