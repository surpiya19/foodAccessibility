# FoodPrint Score - step 11: presentation figures that tell the project's story
# Usage: python src/11_story_figures.py   (after step 10)
# Writes: outputs/story/*.png

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap

from regions import ROOT, REGIONS

OUT = ROOT / "outputs" / "story"
OUT.mkdir(parents=True, exist_ok=True)
CITIES = ["richmond", "baltimore", "dc", "norfolk", "memphis", "columbus"]
DEV = ["richmond", "baltimore"]
SHORT = {"richmond": "Richmond", "baltimore": "Baltimore", "dc": "Washington DC",
         "norfolk": "Norfolk", "memphis": "Memphis*", "columbus": "Columbus*"}

# reference palette (dataviz skill): categorical, status, diverging, sequential
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#86b6ef", "#f0efec", "#f19a95", "#c03a3a"])
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "savefig.facecolor": SURF})

FEATS_C = json.load(open(ROOT / "outputs" / "store_test" / "chosen.json"))["features"]
VERSIONS = {
    "1. Restaurants + FARA\n(original idea)": ["fast_food_ratio", "delivery_proxy", "access_distance",
                                               "vehicle_gap", "affordability_proxy"],
    "2. FARA distance only": ["access_distance", "vehicle_gap", "affordability_proxy"],
    "3. Store types + FARA\n(final score)": FEATS_C,
}
ALL_FEATS = {"fast_food_ratio": "Fast-food share (OSM)", "delivery_proxy": "Restaurants in delivery range (OSM)",
             "limited_share": "Convenience/dollar-store share", "dist_full_service_km": "Distance to supermarket",
             "access_distance": "People far from a store (FARA)", "vehicle_gap": "No car + far from store (FARA)",
             "affordability_proxy": "SNAP households far from store"}
zs = lambda s: (s - s.mean()) / s.std()


def loo(fit):
    h = fit.get_influence().hat_matrix_diag
    return float(np.sqrt(np.mean((fit.resid / (1 - h)) ** 2)))


def make_score(m, feats):
    raw = pd.concat([zs(m[f]) for f in feats], axis=1).mean(axis=1, skipna=True)
    return 100 * (raw - raw.min()) / (raw.max() - raw.min())


def sample(m):
    d = m.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct"])
    return d[d["PCTGQTRS"] < 50].copy()


def test(d, s, o):
    base = smf.ols(f"{o} ~ poverty_rate_pct + log_income", data=d).fit()
    full = smf.ols(f"{o} ~ poverty_rate_pct + log_income + s", data=d.assign(s=zs(s))).fit()
    r = full.get_robustcov_results(cov_type="HC3")
    i = list(full.params.index).index("s")
    return {"pass": bool(r.conf_int()[i][0] > 0 and loo(full) < loo(base)),
            "r2a": base.rsquared, "r2b": full.rsquared, "resid": base.resid}


data = {c: pd.read_csv(ROOT / "data" / "processed" / c / "master_tract_table.csv", dtype={"tract_geoid": str})
        for c in CITIES}

# ---------- Figure 1: the journey (which score passed where) ----------
grid = np.zeros((len(VERSIONS), len(CITIES)))
for j, c in enumerate(CITIES):
    m, d = data[c], sample(data[c])
    for i, feats in enumerate(VERSIONS.values()):
        s = make_score(m, feats).loc[d.index]
        dd = d[s.notna()]
        grid[i, j] = sum(test(dd, s.loc[dd.index], o)["pass"] for o in ["obesity_pct", "diabetes_pct"])

fig, ax = plt.subplots(figsize=(11, 3.9))
cols = {0: CRIT, 1: WARN, 2: GOOD}
txt = {0: "✕  neither", 1: "◐  1 of 2", 2: "✓  both"}
for i in range(len(VERSIONS)):
    for j in range(len(CITIES)):
        v = int(grid[i, j])
        ax.add_patch(plt.Rectangle((j + 0.04, len(VERSIONS) - 1 - i + 0.06), 0.92, 0.88,
                                   color=cols[v], alpha=0.85 if v != 1 else 0.9, lw=0))
        ax.text(j + 0.5, len(VERSIONS) - 1 - i + 0.5, txt[v], ha="center", va="center",
                fontsize=10, color="white" if v != 1 else INK, fontweight="bold")
ax.add_patch(plt.Rectangle((0, -0.08), 2, len(VERSIONS) + 0.16, fill=False, ec=INK2, lw=1.2, ls="-"))
ax.text(1, len(VERSIONS) + 0.12, "used to build / choose the score", ha="center", fontsize=8.5, color=INK2)
ax.text(4, len(VERSIONS) + 0.12, "new cities the final score never saw", ha="center", fontsize=8.5, color=INK2)
ax.set_xlim(0, len(CITIES)); ax.set_ylim(-0.1, len(VERSIONS) + 0.45)
ax.set_xticks(np.arange(len(CITIES)) + 0.5, [SHORT[c] for c in CITIES])
ax.set_yticks(np.arange(len(VERSIONS)) + 0.5, list(VERSIONS)[::-1])
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Dropping the restaurant features is what made the score work in new cities\n"
             "Cell = outcomes (obesity, diabetes) where the score predicts health beyond income", loc="left")
fig.text(0.01, 0.01, "* Memphis = Shelby County, Columbus = Franklin County (city + suburbs). "
         "Pass = positive effect with 95% CI above 0 and better prediction of left-out tracts.",
         fontsize=7.5, color=MUTED)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig(OUT / "story1_journey.png", dpi=170)
plt.close()

# ---------- Figure 2: income explains most, store score adds a slice ----------
rows = []
for c in CITIES:
    m, d = data[c], sample(data[c])
    s = make_score(m, FEATS_C).loc[d.index]
    for o in ["obesity_pct", "diabetes_pct"]:
        t = test(d, s, o)
        rows.append((c, o, t["r2a"], t["r2b"] - t["r2a"]))
r2 = pd.DataFrame(rows, columns=["city", "outcome", "r2a", "dr2"])
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
ys = np.arange(len(CITIES))[::-1]
for ax, o, name in zip(axes, ["obesity_pct", "diabetes_pct"], ["Obesity", "Diabetes"]):
    t = r2[r2["outcome"] == o].set_index("city").loc[CITIES]
    ax.barh(ys, t["r2a"], height=0.6, color="#c9c8c3", label="Income + poverty")
    ax.barh(ys, t["dr2"], left=t["r2a"] + 0.004, height=0.6, color=BLUE, label="+ FoodPrint Score")
    for y, a, b in zip(ys, t["r2a"], t["dr2"]):
        ax.text(a + b + 0.012, y, f"+{b * 100:.1f} pts", va="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0, 1)
    ax.set_title(name, loc="left")
    ax.set_xlabel("Share of tract-to-tract variation explained (R²)")
    ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
axes[0].set_yticks(ys, [SHORT[c] for c in CITIES])
fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, ncol=2, loc="upper right", fontsize=8.5,
           bbox_to_anchor=(0.99, 0.95))
fig.suptitle("Income explains most of the differences in health; the store environment adds a real, "
             "smaller slice on top", x=0.01, ha="left", fontweight="bold", fontsize=11.5)
plt.tight_layout(rect=(0, 0, 1, 0.9))
plt.savefig(OUT / "story2_income_vs_score.png", dpi=170)
plt.close()

# ---------- Figure 3: same income, worse stores, more obesity ----------
fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharey=True)
for ax, c in zip(axes.flat, CITIES):
    m, d = data[c], sample(data[c])
    d["score"] = make_score(m, FEATS_C).loc[d.index]
    d["excess"] = smf.ols("obesity_pct ~ poverty_rate_pct + log_income", data=d).fit().resid
    d["q"] = pd.qcut(d["score"], 5, labels=False)
    g = d.groupby("q")["excess"].agg(["mean", "sem"])
    colors = [BLUE if v < 0 else ORANGE for v in g["mean"]]
    ax.bar(g.index, g["mean"], yerr=1.96 * g["sem"], color=colors, width=0.72,
           error_kw={"ecolor": MUTED, "lw": 1, "capsize": 2})
    ax.axhline(0, color=INK2, lw=0.8)
    gap = g["mean"].iloc[-1] - g["mean"].iloc[0]
    ax.set_title(f"{SHORT[c]}{'  (dev)' if c in DEV else ''}", loc="left")
    ax.text(0.98, 0.04, f"worst − best fifth: {gap:+.1f} pts", transform=ax.transAxes, ha="right",
            fontsize=8.5, color=INK2)
    ax.set_xticks(range(5), ["Best\nstores", "", "", "", "Worst\nstores"], fontsize=8.5)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
for ax in axes[:, 0]:
    ax.set_ylabel("Obesity above / below what\nincome predicts (pct pts)")
fig.suptitle("Among neighborhoods with the same income, those with the worst store environment have more obesity\n"
             "Tracts split into fifths by FoodPrint Score; bars = average obesity left over after income and poverty "
             "(±95% CI)", x=0.01, ha="left", fontsize=10.5, fontweight="bold")
plt.tight_layout(rect=(0, 0, 1, 0.92))
plt.savefig(OUT / "story3_dose_response.png", dpi=170)
plt.close()

# ---------- Figure 4: which signals are consistent ----------
coef = np.full((len(ALL_FEATS), len(CITIES)), np.nan)
sig = np.zeros_like(coef, dtype=bool)
for j, c in enumerate(CITIES):
    d = sample(data[c])
    for i, f in enumerate(ALL_FEATS):
        dd = d.dropna(subset=[f]).assign(x=lambda t: zs(t[f]))
        fit = smf.ols("obesity_pct ~ poverty_rate_pct + log_income + x", data=dd).fit(cov_type="HC3")
        coef[i, j], sig[i, j] = fit.params["x"], fit.pvalues["x"] < 0.05
fig, ax = plt.subplots(figsize=(10.5, 4.6))
lim = np.nanmax(np.abs(coef))
im = ax.imshow(coef, cmap=DIV, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
for i in range(coef.shape[0]):
    for j in range(coef.shape[1]):
        v = coef[i, j]
        ax.text(j, i, f"{v:+.1f}{'' if sig[i, j] else ''}", ha="center", va="center", fontsize=9,
                fontweight="bold" if sig[i, j] else "normal",
                color=("white" if abs(v) > 0.6 * lim else INK) if sig[i, j] else MUTED)
ax.set_xticks(range(len(CITIES)), [SHORT[c] for c in CITIES])
ax.set_yticks(range(len(ALL_FEATS)), list(ALL_FEATS.values()))
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.axhline(1.5, color=SURF, lw=4)
cb = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cb.set_label("Obesity pct pts per 1 SD, beyond income\n(red = more obesity, blue = less)", fontsize=8.5)
cb.outline.set_visible(False)
ax.set_title("Store type and affordability point the right way across cities; restaurant counts mislead\n"
             "Bold = significant (p < 0.05); grey = not significant", loc="left")
plt.tight_layout()
plt.savefig(OUT / "story4_signals.png", dpi=170)
plt.close()

# ---------- Figure 5: where (maps) ----------
fig, axes = plt.subplots(2, 3, figsize=(12, 8.2))
for ax, c in zip(axes.flat, CITIES):
    m, d = data[c], sample(data[c])
    m["score"] = make_score(m, FEATS_C)
    d["score"] = m.loc[d.index, "score"]
    d["excess"] = smf.ols("obesity_pct ~ poverty_rate_pct + log_income", data=d).fit().resid
    d["priority"] = (d["score"] > d["score"].median()) & (d["excess"] > 0)
    g = gpd.read_file(ROOT / "data" / "processed" / c / "tracts.geojson")
    g["GEOID"] = g["GEOID"].astype(str)
    g = g.merge(m[["tract_geoid", "score"]], left_on="GEOID", right_on="tract_geoid", how="left")
    g = g.merge(d[["tract_geoid", "priority"]], on="tract_geoid", how="left")
    g.plot(column="score", cmap=SEQ, vmin=0, vmax=100, ax=ax, edgecolor="white", linewidth=0.25,
           missing_kwds={"color": "#eeeeec"})
    g[g["priority"] == True].boundary.plot(ax=ax, color=ORANGE, linewidth=1.1)
    ax.set_title(f"{SHORT[c]}  ·  {int(d['priority'].sum())} priority tracts", loc="left", fontsize=10)
    ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap=SEQ, norm=plt.Normalize(0, 100))
cb = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.03, pad=0.03, aspect=50)
cb.set_label("FoodPrint Score (0 = best store environment in the city, 100 = worst)   ·   "
             "orange outline = priority tract (score above median AND more obesity than income predicts)",
             fontsize=8.5)
cb.outline.set_visible(False)
fig.suptitle("Where the store environment is worst, and where it lines up with unexplained obesity",
             x=0.01, ha="left", fontweight="bold", fontsize=12)
plt.savefig(OUT / "story5_maps.png", dpi=170, bbox_inches="tight")
plt.close()
# ---------- Figure 6: what the store-type data adds over FARA alone ----------
rows = []
for c in CITIES:
    m, d = data[c], sample(data[c])
    for name, feats in [("FARA distance only", VERSIONS["2. FARA distance only"]), ("Store types + FARA (final)", FEATS_C)]:
        s = make_score(m, feats).loc[d.index]
        for o in ["obesity_pct", "diabetes_pct"]:
            base = smf.ols(f"{o} ~ poverty_rate_pct + log_income", data=d).fit()
            full = smf.ols(f"{o} ~ poverty_rate_pct + log_income + s", data=d.assign(s=zs(s))).fit()
            rows.append((c, name, o, 100 * (loo(base) - loo(full)) / loo(base)))
g6 = pd.DataFrame(rows, columns=["city", "version", "outcome", "gain"])
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
x = np.arange(len(CITIES))
for ax, o, name in zip(axes, ["obesity_pct", "diabetes_pct"], ["Obesity", "Diabetes"]):
    for k, (v, col) in enumerate([("FARA distance only", "#9a9994"), ("Store types + FARA (final)", BLUE)]):
        t = g6[(g6["outcome"] == o) & (g6["version"] == v)].set_index("city").loc[CITIES]
        ax.bar(x + (k - 0.5) * 0.38, t["gain"], 0.36, color=col, label=v)
        for xb, val in zip(x + (k - 0.5) * 0.38, t["gain"]):
            ax.text(xb, val + (0.25 if val >= 0 else -0.25), f"{val:.1f}", ha="center",
                    va="bottom" if val >= 0 else "top", fontsize=7.5, color=INK2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvspan(-0.5, 1.5, color="#efeeea", zorder=0)
    ax.set_xticks(x, [SHORT[c] for c in CITIES], fontsize=8.5, rotation=0)
    ax.set_xlim(-0.5, len(CITIES) - 0.5)
    ax.set_title(name, loc="left")
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
axes[0].set_ylabel("Better prediction of left-out tracts\nvs income + poverty alone (%)")
axes[0].text(0.5, axes[0].get_ylim()[1] * 0.93, "dev cities", ha="center", fontsize=8, color=MUTED)
fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, ncol=2, loc="upper right",
           bbox_to_anchor=(0.99, 0.93), fontsize=8.5)
fig.suptitle("Adding store-type data multiplies the score's value in DC, Memphis and Columbus, but not Norfolk",
             x=0.01, ha="left", fontweight="bold", fontsize=11.5)
plt.tight_layout(rect=(0, 0, 1, 0.88))
plt.savefig(OUT / "story6_store_types_add.png", dpi=170)
plt.close()

print("wrote", sorted(p.name for p in OUT.glob("*.png")))
