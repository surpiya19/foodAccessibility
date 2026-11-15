# FoodPrint Score - what each tract needs, and why.
#
# One place for the suggestion rules, so step 12, the dashboard and the PDF reports
# always say the same thing. Pure pandas; no modeling happens here.
#
# How a suggestion is made, for one tract:
#   1. Each of the four score inputs is turned into a percentile within its own place (100 = worst).
#   2. An input is a "driver" if it is in the worst 30% of the place (percentile >= 70) AND clears
#      a minimum level (so "2% of people far from a store" never triggers anything on its own).
#   3. Each driver maps to one intervention type (INTERVENTIONS below). The driver with the highest
#      percentile is the main suggestion; any others are listed as secondary.
#   4. Tier: "Act" = priority tract in a place where the score passed validation;
#            "Monitor" = worst fifth of scores but not a priority tract;
#            "Withheld" = the place did not pass, so no suggestions are given;
#            "None" = nothing stands out.
# These are options for a community health needs assessment to consider, not proven effects.

import numpy as np
import pandas as pd

FEATURES = ["limited_share", "dist_full_service_km", "access_distance", "affordability_proxy"]

DRIVER_PCT = 70  # worst 30% within the place

# minimum level for an input to count as a driver: (urban, rural)
MIN_LEVEL = {
    "limited_share": (0.75, 0.75),        # share of nearby SNAP stores that are convenience/dollar/small
    "dist_full_service_km": (1.0, 8.0),   # km to the nearest supermarket
    "access_distance": (10.0, 5.0),       # % of people far from a SNAP store
    "affordability_proxy": (2.0, 0.5),    # % of households that are SNAP + far from a store
}

INTERVENTIONS = {
    "limited_share": {
        "name": "Healthy corner store program",
        "what": "Partner with the corner and dollar stores already here to carry produce and staples "
                "(cooler space, a stocking subsidy, shelf placement).",
        "why": "Most SNAP stores nearby are corner, dollar or small stores.",
        "short": "Corner/dollar/small store share",
    },
    "dist_full_service_km": {
        "name": "Grocery shuttle or transit fix",
        "what": "Run a shuttle or adjust a bus route to the nearest supermarket, or offer ride vouchers. "
                "If the gap persists, flag the area for grocery financing.",
        "why": "The nearest supermarket is farther away than for most tracts in the area.",
        "short": "Distance to nearest supermarket",
    },
    "access_distance": {
        "name": "Mobile market",
        "what": "Schedule a mobile market or produce stand that takes SNAP, at a clinic, school or church.",
        "why": "Many residents live far from any store that takes SNAP.",
        "short": "Residents far from a SNAP store",
    },
    "affordability_proxy": {
        "name": "SNAP delivery and produce prescriptions",
        "what": "Enroll SNAP households in online grocery ordering with delivery, and refer patients to "
                "produce prescription or fruit-and-vegetable incentive programs.",
        "why": "A large share of households are on SNAP and also far from a store.",
        "short": "SNAP households far from a store",
    },
}

GENERAL = {
    "name": "Local assessment",
    "what": "Talk to residents or walk the stores before picking an intervention.",
    "why": "The score is above the median and health is worse than income predicts, but no one factor is in "
           "the worst 30%.",
    "short": "",
}
INTERVENTIONS_ALL = {**INTERVENTIONS, "general": GENERAL}

FEATURE_LABELS = {
    "limited_share": "Convenience / dollar / small stores (share of nearby SNAP stores)",
    "dist_full_service_km": "Distance to nearest supermarket (km)",
    "access_distance": "People far from a SNAP store (%)",
    "affordability_proxy": "SNAP households far from a store (%)",
}


def fmt_value(feature, v):
    if pd.isna(v):
        return "no data"
    if feature == "limited_share":
        return f"{v * 100:.0f}%"
    if feature == "dist_full_service_km":
        return f"{v:.1f} km"
    return f"{v:.1f}%"


def percentiles(df):
    """Percentile of each input within the place (share of tracts with a lower value), 0-100."""
    out = pd.DataFrame(index=df.index)
    for f in FEATURES:
        vals = df[f]
        out[f] = vals.apply(lambda v: (vals < v).mean() * 100 if pd.notna(v) else np.nan)
    return out


def drivers_for(row, pct_row, medians, rural):
    """List of (feature, percentile) that count as drivers, worst first."""
    found = []
    for f in FEATURES:
        p, v = pct_row[f], row[f]
        if pd.isna(p) or pd.isna(v):
            continue
        if p >= DRIVER_PCT and v >= MIN_LEVEL[f][1 if rural else 0] and v > medians[f]:
            found.append((f, p))
    return sorted(found, key=lambda x: -x[1])


def reason_text(feature, row, medians):
    """One line of fact: this tract's value against the median tract."""
    return (f"{INTERVENTIONS[feature]['short']}: {fmt_value(feature, row[feature])} here, "
            f"{fmt_value(feature, medians[feature])} in the median tract")


SEP = " | "


def split_reasons(why):
    return [r for r in str(why).split(SEP) if r.strip()]


def add_recommendations(df, released, rural):
    """df = tracts of ONE place (modeled tracts have rank). Returns df with suggestion columns."""
    df = df.copy()
    scored = df[df["modeled"]]
    medians = scored[FEATURES].median()
    pct = percentiles(scored).reindex(df.index)
    for f in FEATURES:
        df[f"pct_{f}"] = pct[f].round(1)

    tiers, mains, mains_f, seconds, reasons = [], [], [], [], []
    for idx, row in df.iterrows():
        if not row["modeled"]:
            tiers.append("Not scored"); mains.append(""); mains_f.append(""); seconds.append(""); reasons.append("")
            continue
        drv = drivers_for(row, pct.loc[idx], medians, rural)
        if not released:
            tier = "Withheld"
        elif row["priority_flag"]:
            tier = "Act"
        elif row.get("score_quintile") == 5:
            tier = "Monitor"
        else:
            tier = "None"
        if tier in ("Withheld", "None") or (tier == "Monitor" and not drv):
            tiers.append(tier)
            mains.append(""); mains_f.append(""); seconds.append(""); reasons.append("")
            continue
        if not drv:   # priority tract, but no single input stands out
            tiers.append(tier); mains.append(GENERAL["name"]); mains_f.append("general"); seconds.append("")
            reasons.append("")
            continue
        tiers.append(tier)
        mains.append(INTERVENTIONS[drv[0][0]]["name"])
        mains_f.append(drv[0][0])
        seconds.append("; ".join(INTERVENTIONS[f]["name"] for f, _ in drv[1:]))
        reasons.append(SEP.join(reason_text(f, row, medians) for f, _ in drv))
    df["tier"] = tiers
    df["suggestion"] = mains
    df["main_driver"] = mains_f
    df["also_consider"] = seconds
    df["why"] = reasons
    return df


def alerts(df):
    """Group Act tracts by main suggestion: one alert per intervention type, biggest first."""
    act = df[df["tier"] == "Act"]
    if act.empty:
        return pd.DataFrame(columns=["suggestion", "main_driver", "tracts", "population", "tract_list"])
    g = (act.sort_values("rank")
            .groupby(["suggestion", "main_driver"])
            .agg(tracts=("tract_geoid", "count"), population=("POP2020", "sum"),
                 tract_list=("tract_name", lambda s: list(s)))
            .reset_index()
            .sort_values(["population"], ascending=False))
    return g
