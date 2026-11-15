# FoodPrint Score - static charts (matplotlib) for the PDF reports and the dashboard.
# Every function returns PNG bytes. One highlight color (blue) on grey context throughout.

import io
import json
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import numpy as np
import pandas as pd

from recommendations import FEATURES, INTERVENTIONS_ALL, alerts, fmt_value

ROOT = Path(__file__).resolve().parent.parent
BLUE, BLUE_LIGHT, GREY, GREY_LIGHT, INK, INK2 = "#2a78d6", "#cde2fb", "#9a9a94", "#dcdcd6", "#0b0b0b", "#52514e"

plt.rcParams.update({"font.size": 8, "axes.edgecolor": GREY, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 9,
                     "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left"})

UNITS = {"limited_share": "% of nearby SNAP stores", "dist_full_service_km": "km",
         "access_distance": "% of residents", "affordability_proxy": "% of households"}


def _png(fig, transparent=False):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", transparent=transparent); plt.close(fig)
    return buf.getvalue()


def _clean(ax, left=False):
    for s in ("top", "right") + (("left",) if not left else ()):
        ax.spines[s].set_visible(False)


def _vals(f, s):
    return s * 100 if f == "limited_share" else s


def factor_strips(t, place_df):
    """Score + four factors. Each row: every tract in the area (grey), median (tick), this tract (blue)."""
    sc = place_df[place_df["modeled"]]
    rows = [("foodprint_score", "FoodPrint Score (0-100)")] + \
           [(f, f"{INTERVENTIONS_ALL[f]['short']} ({UNITS[f]})") for f in FEATURES]
    fig, axes = plt.subplots(len(rows), 1, figsize=(7.2, 0.62 * len(rows) + 0.3))
    rng = np.random.default_rng(0)
    for ax, (col, label) in zip(axes, rows):
        v = _vals(col, sc[col].dropna())
        me = _vals(col, pd.Series([t[col]])).iloc[0]
        ax.scatter(v, rng.uniform(-0.25, 0.25, len(v)), s=6, color=GREY_LIGHT, lw=0)
        med = v.median()
        ax.plot([med, med], [-0.42, 0.42], color=INK2, lw=1.2)
        if pd.notna(me):
            ax.scatter([me], [0], s=70, color=BLUE, edgecolor="white", lw=1.5, zorder=3)
            txt = f"{me:.0f}" if col in ("foodprint_score",) else (f"{me:.1f}" if col != "limited_share" else f"{me:.0f}%")
            right = me > v.min() + 0.85 * (v.max() - v.min())
            ax.annotate(txt, (me, 0), xytext=(-9 if right else 9, 0), textcoords="offset points",
                        ha="right" if right else "left", va="center", fontsize=8, fontweight="bold", color=INK)
        ax.set_ylim(-0.5, 0.5); ax.set_yticks([])
        ax.set_title(label, fontsize=8, fontweight="normal", color=INK2, pad=2)
        _clean(ax)
        ax.tick_params(axis="x", labelsize=7, length=2)
    fig.suptitle("Blue dot = this tract     dark line = median tract     grey = other tracts in the area",
                 x=0.125, ha="left", y=1.0, fontsize=7, color=INK2)
    fig.subplots_adjust(hspace=1.05, top=0.9)
    return _png(fig)


def health_gap(t, place_df, outcome):
    """Actual vs income-predicted prevalence. Above the line = worse than income explains."""
    sc = place_df[place_df["modeled"]].dropna(subset=[f"{outcome}_pct", f"excess_{outcome}"])
    actual = sc[f"{outcome}_pct"]; pred = actual - sc[f"excess_{outcome}"]
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    lo, hi = min(actual.min(), pred.min()) - 1, max(actual.max(), pred.max()) + 1
    ax.fill_between([lo, hi], [lo, hi], [hi, hi], color=BLUE_LIGHT, alpha=0.35, lw=0)
    ax.plot([lo, hi], [lo, hi], color=INK2, lw=1)
    ax.scatter(pred, actual, s=9, color=GREY, alpha=0.55, lw=0)
    me_a = t[f"{outcome}_pct"]; me_p = me_a - t[f"excess_{outcome}"]
    ax.plot([me_p, me_p], [me_p, me_a], color=BLUE, lw=1.5)
    ax.scatter([me_p], [me_a], s=70, color=BLUE, edgecolor="white", lw=1.5, zorder=3)
    ax.annotate(f"{t[f'excess_{outcome}']:+.1f} pts", (me_p, (me_p + me_a) / 2), xytext=(6, 0),
                textcoords="offset points", fontsize=8, fontweight="bold", va="center")
    ax.text(lo + 0.03 * (hi - lo), hi - 0.05 * (hi - lo), "Worse than income predicts", fontsize=7, color=INK2, va="top")
    ax.text(hi - 0.03 * (hi - lo), lo + 0.05 * (hi - lo), "Better", fontsize=7, color=INK2, ha="right")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(f"Predicted from income and poverty (%)"); ax.set_ylabel(f"Actual {outcome} (%)")
    ax.set_title(f"{outcome.capitalize()}: actual vs. predicted")
    _clean(ax, left=True)
    return _png(fig)


def forest(results, place):
    """Effect of the score beyond income, with 95% CI, for obesity and diabetes. Filled = passed."""
    r = results[results["city"] == place].set_index("outcome")
    fig, ax = plt.subplots(figsize=(3.5, 1.5))
    for i, (oc, lab) in enumerate([("diabetes_pct", "Diabetes"), ("obesity_pct", "Obesity")]):
        if oc not in r.index:
            continue
        x = r.loc[oc]; ok = (x["sem_lo"] > 0) and (x["loo_gain_pct"] > 0)
        ax.plot([x["sem_lo"], x["sem_hi"]], [i, i], color=BLUE if ok else GREY, lw=2)
        ax.scatter([x["sem_coef"]], [i], s=60, color=BLUE if ok else "white",
                   edgecolor=BLUE if ok else GREY, lw=1.8, zorder=3)
        ax.text(max(x["sem_hi"], 0) + 0.08, i, "passed" if ok else "not passed", va="center", fontsize=7.5,
                color=INK if ok else INK2)
    ax.axvline(0, color=INK2, lw=0.8, ls=":")
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Diabetes", "Obesity"]); ax.set_ylim(-0.6, 1.6)
    ax.set_xlim(-1.1, 2.9)
    ax.set_xlabel("Points of prevalence per SD of score,\nbeyond income (95% CI)", fontsize=7)
    ax.set_title("Does the score add to income?")
    _clean(ax, left=True)
    return _png(fig)


def method_flow(transparent=False):
    """Four factors -> score -> priority test -> intervention."""
    fig, ax = plt.subplots(figsize=(7.2, 2.0)); ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")

    def box(x, y, w, h, text, fill="#f0efec", bold=False, color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fill, ec="none"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.3, color=color,
                fontweight="bold" if bold else "normal", wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1))

    facs = ["Corner/dollar store share", "Distance to supermarket", "Residents far from SNAP store",
            "SNAP households far from store"]
    for i, f in enumerate(facs):
        box(0.5, 23 - i * 7.3, 27, 5, f)
        arrow(28.5, 25.5 - i * 7.3, 32, 15)
    box(32.5, 10, 17, 10, "FoodPrint Score\n0-100\n(equal weights)", fill=BLUE_LIGHT, bold=True)
    arrow(50.5, 15, 54, 15)
    box(54.5, 7, 21, 16, "Priority tract if\nscore > median\nAND health worse\nthan income predicts", fill="#f0efec")
    arrow(76.5, 15, 80, 15)
    box(80.5, 7, 19, 16, "Intervention\nmatched to the\nworst factor", fill=BLUE, bold=True, color="white")
    return _png(fig, transparent)


def intervention_bars(place_df):
    """Residents covered by each intervention (priority tracts only)."""
    a = alerts(place_df).sort_values("population")
    fig, ax = plt.subplots(figsize=(7.2, 0.45 * len(a) + 0.5))
    ax.barh(a["suggestion"], a["population"], color=BLUE, height=0.6)
    for i, (p, n) in enumerate(zip(a["population"], a["tracts"])):
        ax.text(p + a["population"].max() * 0.01, i, f"{p:,.0f} residents, {n} tract{'s' if n != 1 else ''}",
                va="center", fontsize=7.5, color=INK)
    ax.set_xlim(0, a["population"].max() * 1.45); ax.set_xticks([])
    ax.tick_params(axis="y", length=0, labelsize=8)
    _clean(ax, left=False); ax.spines["bottom"].set_visible(False)
    return _png(fig)


def _patches(geo):
    out = {}
    for f in geo["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[str(f["properties"]["tract_geoid"])] = [np.array(p[0]) for p in polys]
    return out


def intervention_maps(place_df, place):
    """Small multiples: one map per intervention, its tracts in blue, all others light grey."""
    geo = json.load(open(ROOT / "outputs" / "dashboard" / f"tracts_{place}.geojson"))
    shapes = _patches(geo)
    a = alerts(place_df)
    act = place_df[place_df["tier"] == "Act"]
    n = len(a); cols = 3 if n > 4 else max(n, 1); rows = math.ceil(n / cols)
    allpts = np.vstack([r for rings in shapes.values() for r in rings])
    lat = allpts[:, 1].mean()
    fig, axes = plt.subplots(rows, cols, figsize=(7.2, 2.5 * rows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, (_, row) in zip(axes.flat, a.iterrows()):
        ids = set(act.loc[act["main_driver"] == row["main_driver"], "tract_geoid"].astype(str))
        base, hit = [], []
        for gid, rings in shapes.items():
            for ring in rings:
                (hit if gid in ids else base).append(MplPolygon(ring, closed=True))
        ax.add_collection(PatchCollection(base, fc="#ecebe6", ec="white", lw=0.2))
        ax.add_collection(PatchCollection(hit, fc=BLUE, ec="white", lw=0.2))
        ax.set_xlim(allpts[:, 0].min(), allpts[:, 0].max()); ax.set_ylim(allpts[:, 1].min(), allpts[:, 1].max())
        ax.set_aspect(1 / math.cos(math.radians(lat)))
        ax.set_title(f"{textwrap.fill(row['suggestion'], 26)}\n{row['tracts']} tract{'s' if row['tracts'] != 1 else ''}",
                     fontsize=7.5, fontweight="bold", loc="left", color=INK)
    fig.tight_layout()
    return _png(fig)


def all_areas_forest(results, names):
    """Effect of the score beyond income in every area, obesity and diabetes side by side."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True)
    order = list(names)[::-1]
    for ax, (oc, lab) in zip(axes, [("obesity_pct", "Obesity"), ("diabetes_pct", "Diabetes")]):
        r = results[results["outcome"] == oc].set_index("city")
        for i, c in enumerate(order):
            if c not in r.index:
                continue
            x = r.loc[c]; ok = (x["sem_lo"] > 0) and (x["loo_gain_pct"] > 0)
            ax.plot([x["sem_lo"], x["sem_hi"]], [i, i], color=BLUE if ok else GREY, lw=2)
            ax.scatter([x["sem_coef"]], [i], s=45, color=BLUE if ok else "white",
                       edgecolor=BLUE if ok else GREY, lw=1.6, zorder=3)
        ax.axvline(0, color=INK2, lw=0.8, ls=":")
        ax.set_yticks(range(len(order))); ax.set_yticklabels([names[c] for c in order])
        ax.set_title(lab); ax.set_xlabel("Points per SD of score, beyond income (95% CI)", fontsize=7)
        _clean(ax, left=True)
    fig.text(0.99, 0.01, "Filled = passed  |  open = not passed", ha="right", fontsize=7, color=INK2)
    fig.tight_layout()
    return _png(fig)
