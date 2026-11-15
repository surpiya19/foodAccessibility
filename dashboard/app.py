# FoodPrint Score dashboard
# Run from the repo root:   streamlit run dashboard/app.py
#
# The app only READS files made by the pipeline (it does no modeling itself):
#   outputs/dashboard/places_summary.csv      one row per place        (src/12_final_scores.py)
#   outputs/dashboard/all_tracts.csv          one row per tract        (src/12_final_scores.py)
#   outputs/dashboard/tracts_<place>.geojson  tract shapes for the map (src/12_final_scores.py)
#   outputs/all_cities/all_cities_results.csv validation results       (src/10_all_cities.py)
# Suggestions come from src/recommendations.py (via step 12); PDFs from src/reports.py.

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "outputs" / "dashboard"
sys.path.insert(0, str(ROOT / "src"))
from recommendations import INTERVENTIONS_ALL, alerts, split_reasons  # noqa: E402  (suggestion rules, shared with step 12)
import reports  # noqa: E402  (PDF reports)
import charts  # noqa: E402  (static charts shared with the reports)

# colors: one blue ramp for the score, blue-grey-red when a value can be above or below zero
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
BLUE_RED = ["#1c5cab", "#86b6ef", "#f0efec", "#e58a8a", "#b02a2a"]
BLUE, GREY, INK = "#2a78d6", "#9a9a94", "#0b0b0b"

FEATURE_LABELS = {
    "limited_share": "Convenience / dollar / small stores (share of nearby SNAP stores)",
    "dist_full_service_km": "Distance to nearest supermarket (km)",
    "access_distance": "People far from a SNAP store (%)",
    "affordability_proxy": "SNAP households far from a store (%)",
}
FEATURES = list(FEATURE_LABELS)

st.set_page_config(page_title="FoodPrint Score", layout="wide")


# ---------- load data (cached, so it is read only once) ----------
@st.cache_data
def load_tables():
    summary = pd.read_csv(DASH / "places_summary.csv")
    tracts = pd.read_csv(DASH / "all_tracts.csv", dtype={"tract_geoid": str})
    text_cols = ["tract_name", "tier", "suggestion", "main_driver", "also_consider", "why"]
    missing = [c for c in text_cols if c not in tracts.columns]
    if missing:
        st.error("outputs/dashboard/all_tracts.csv has no suggestion columns. Run `python src/12_final_scores.py` "
                 "and restart the app.")
        st.stop()
    tracts[text_cols] = tracts[text_cols].fillna("")
    results = pd.read_csv(ROOT / "outputs" / "all_cities" / "all_cities_results.csv")
    return summary, tracts, results


@st.cache_data(show_spinner="Building the report...")
def place_pdf(place):
    info = summary[summary["place"] == place].iloc[0].to_dict()
    return reports.place_report(info, tracts[tracts["place"] == place], results)


@st.cache_data(show_spinner="Building the report...")
def tract_pdf(place, geoid):
    info = summary[summary["place"] == place].iloc[0].to_dict()
    d = tracts[tracts["place"] == place]
    return reports.tract_report(info, d[d["tract_geoid"] == geoid].iloc[0], d, results)


FACTOR_COLS = {  # column header, scale factor, number format
    "limited_share": ("Corner/dollar stores", 100, "{:.0f}%"),
    "dist_full_service_km": ("Km to supermarket", 1, "{:.1f}"),
    "access_distance": ("Residents far from SNAP store", 1, "{:.0f}%"),
    "affordability_proxy": ("SNAP homes far from store", 1, "{:.1f}%"),
}


def tract_factor_table(rows, scored_all, outcome, rural):
    """One row per tract, one column per factor; driver cells shaded. Median tract on top."""
    gap = f"{outcome.capitalize()} gap (pts)"
    med = {"Rank": "", "Tract": "Median tract", "Score": scored_all["foodprint_score"].median(), gap: 0.0}
    out, drivers = [med], [set()]
    for _, r in rows.iterrows():
        rec = {"Rank": str(int(r["rank"])), "Tract": reports.short_name(r["tract_name"], rural),
               "Score": r["foodprint_score"], gap: r[f"excess_{outcome}"]}
        found = {f for f in FEATURES if any(x.startswith(INTERVENTIONS_ALL[f]["short"]) for x in split_reasons(r["why"]))}
        out.append(rec); drivers.append(found)
    for f, (label, mult, _) in FACTOR_COLS.items():
        out[0][label] = scored_all[f].median() * mult
        for rec, (_, r) in zip(out[1:], rows.iterrows()):
            rec[label] = r[f] * mult
    for rec, (_, r) in zip(out[1:], rows.iterrows()):
        rec["Also needs"] = r["also_consider"].replace("; ", ", ")
    out[0]["Also needs"] = ""
    table = pd.DataFrame(out)

    def shade(row):
        d = drivers[row.name]
        styles = []
        for c in row.index:
            f = next((k for k, v in FACTOR_COLS.items() if v[0] == c), None)
            if row.name == 0:
                styles.append("color: #52514e; font-style: italic")
            elif f and f in d:
                styles.append("background-color: #cde2fb; font-weight: 600")
            else:
                styles.append("")
        return styles

    fmt = {"Score": "{:.0f}", gap: "{:+.1f}"} | {v[0]: v[2] for v in FACTOR_COLS.values()}
    return table.style.apply(shade, axis=1).format(fmt, na_rep="n/a")


def map_center(shapes):
    pts = [pt for f in shapes["features"] for ring in
           (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
            else [r for poly in f["geometry"]["coordinates"] for r in poly]) for pt in ring]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    return {"lon": (min(lons) + max(lons)) / 2, "lat": (min(lats) + max(lats)) / 2}


def map_zoom():
    return 6.2 if place == "rural_va" else (9.3 if place in ["memphis", "columbus"] else 10.5)


@st.cache_data
def load_shapes(place):
    return json.load(open(DASH / f"tracts_{place}.geojson"))


summary, tracts, results = load_tables()
names = dict(zip(summary["place"], summary["place_name"]))


# ---------- sidebar: choose a place ----------
st.sidebar.title("FoodPrint Score")
st.sidebar.caption("Where is the food environment the lever, beyond income?")
place = st.sidebar.selectbox("Place", summary["place"], format_func=lambda p: names[p])
info = summary[summary["place"] == place].iloc[0]
df = tracts[tracts["place"] == place].copy()
released = bool(info["released"])
is_rural = place == "rural_va"
outcome = info.get("priority_outcome", "obesity")
far = "10 miles" if is_rural else "1/2 mile"

st.sidebar.markdown(
    "**How to read the score**\n\n"
    "0-100 for every census tract. 100 = the worst food environment in this place. "
    "It combines four things, each with the same weight:\n"
    "- share of nearby stores that are convenience / dollar / small stores\n"
    "- distance to the nearest supermarket\n"
    f"- people more than {far} from a SNAP store\n"
    f"- SNAP households more than {far} from a store\n\n"
    "**Priority tract** = score above the place median **and** more of the validated outcome "
    "(obesity or diabetes) than income predicts.\n\n"
    "Each priority tract is matched to an intervention based on the factor where it is in the worst 30% of its area."
)
st.sidebar.caption("A prioritization tool. It shows where to look first; it does not claim that "
                   "food access causes obesity.")


# ---------- header + headline numbers ----------
st.title(names[place])
if released:
    st.caption(f"The score predicts {outcome} beyond income and poverty here, so the priority list is released "
               f"and ranked on {outcome}.")
else:
    st.warning("**Priority list not released.** The score did not predict obesity or diabetes beyond "
               "income in this place, so we do not rank its tracts. The map still shows the score. "
               "See the Evidence tab.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tracts scored", f"{int(info['tracts_modeled'])}", help=f"of {int(info['tracts'])} tracts; the rest "
          "have no income estimate or are mostly dorms / prisons")
if released:
    c2.metric("Priority tracts", f"{int(info['priority_tracts'])}")
    c3.metric("People living in priority tracts", f"{int(info['priority_population']):,}")
else:
    c2.metric("Priority tracts", "Not released")
    c3.metric("People living in priority tracts", "-")
c4.metric("Obesity gap, worst vs best fifth", f"{info['obesity_gap_worst_vs_best_fifth']:+.1f} pts",
          help="Obesity that income does not explain: the fifth of tracts with the worst score "
               "minus the fifth with the best score")

tab_alerts, tab_map, tab_list, tab_tract, tab_evidence, tab_about = st.tabs(
    ["Recommendations", "Map", "Priority list", "Tract detail", "Evidence", "Data & limits"])


# ---------- tab 0: alerts - what each community needs ----------
with tab_alerts:
    top_l, top_r = st.columns([3, 1])
    top_r.download_button("Area report (PDF)", place_pdf(place),
                          file_name=f"foodprint_{place}_report.pdf", mime="application/pdf",
                          width="stretch")
    if not released:
        top_l.subheader("Not released")
        top_l.write("The score did not pass validation here, so tracts are not ranked and no interventions "
                    "are recommended. See the Evidence tab.")
    else:
        al = alerts(df)
        act = df[df["tier"] == "Act"]
        scored_all = df[df["modeled"]]
        top_l.subheader("Recommended interventions")
        top_l.caption(f"{len(act)} priority tracts, {int(act['POP2020'].sum()):,} residents. Each tract is "
                      f"matched to one intervention based on its worst factor. Ranked on {outcome}.")
        # residents covered by each intervention (one series, direct labels)
        bars = al.sort_values("population")
        fb = go.Figure(go.Bar(
            x=bars["population"], y=bars["suggestion"], orientation="h", marker_color=BLUE, width=0.6,
            text=[f"{p:,.0f} residents, {n} tract{'s' if n != 1 else ''}" for p, n in zip(bars["population"], bars["tracts"])],
            textposition="outside", cliponaxis=False,
            hovertemplate="%{y}<br>%{x:,} residents<extra></extra>"))
        fb.update_layout(height=60 + 46 * len(bars), margin=dict(l=0, r=160, t=10, b=0),
                         xaxis=dict(visible=False), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fb, width="stretch")

        # map: pick an intervention, its tracts light up (one hue; never five colors on one map)
        pick = st.radio("Show on map", list(al["suggestion"]), horizontal=True)
        drv = al.loc[al["suggestion"] == pick, "main_driver"].iloc[0]
        mdf = df.copy()
        mdf["hit"] = ((mdf["tier"] == "Act") & (mdf["main_driver"] == drv)).astype(int)
        shapes_r = load_shapes(place)
        fm = px.choropleth_map(
            mdf, geojson=shapes_r, locations="tract_geoid", featureidkey="properties.tract_geoid",
            color="hit", color_continuous_scale=[[0, "#ecebe6"], [1, BLUE]], range_color=(0, 1),
            map_style="carto-positron", center=map_center(shapes_r), zoom=map_zoom(), opacity=0.85,
            hover_name="tract_name", hover_data={"tract_geoid": False, "hit": False, "suggestion": True,
                                                 "foodprint_score": ":.0f"})
        fm.update_traces(marker_line_width=0.4, marker_line_color="white")
        fm.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False)
        st.plotly_chart(fm, width="stretch")

        st.markdown("##### What each intervention involves")
        for _, a in al.iterrows():
            iv = INTERVENTIONS_ALL[a["main_driver"]]
            with st.container(border=True):
                st.markdown(f"**{a['suggestion']}**  \n{iv['what']}")
                with st.expander(f"Tracts ({int(a['tracts'])})"):
                    rows = act[act["main_driver"] == a["main_driver"]].sort_values("rank")
                    st.dataframe(tract_factor_table(rows, scored_all, outcome, is_rural),
                                 hide_index=True, width="stretch")
                    st.caption("Shaded = factor in the worst 30% of the area (these drive the recommendation). "
                               "First row is the median tract for comparison. Tract reports are in the Tract detail tab.")
        mon = df[(df["tier"] == "Monitor") & (df["suggestion"] != "")]
        if len(mon):
            with st.expander(f"Watch list ({len(mon)} tracts): worst-fifth score, no excess {outcome}"):
                st.dataframe(mon.sort_values("foodprint_score", ascending=False)[
                    ["tract_name", "foodprint_score", "suggestion"]].rename(columns={
                        "tract_name": "Tract", "foodprint_score": "Score", "suggestion": "Possible step"}),
                    hide_index=True, width="stretch")


# ---------- tab 1: map ----------
with tab_map:
    color_options = {
        "FoodPrint Score (0-100)": "foodprint_score",
        "Obesity beyond what income predicts (pts)": "excess_obesity",
        "Obesity (%)": "obesity_pct",
        "Diabetes (%)": "diabetes_pct",
    }
    left, right = st.columns([2, 1])
    choice = left.radio("Color the map by", list(color_options), horizontal=True)
    show_priority = right.checkbox("Outline priority tracts", value=released, disabled=not released)
    # the street background is downloaded from the internet; untick it if the map stays blank
    streets = right.checkbox("Street map background", value=True)
    col = color_options[choice]

    shapes = load_shapes(place)
    # center the map on the middle of the tract shapes
    lons = [pt[0] for f in shapes["features"] for ring in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [r for poly in f["geometry"]["coordinates"] for r in poly]) for pt in ring]
    lats = [pt[1] for f in shapes["features"] for ring in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [r for poly in f["geometry"]["coordinates"] for r in poly]) for pt in ring]
    center = {"lon": (min(lons) + max(lons)) / 2, "lat": (min(lats) + max(lats)) / 2}
    zoom = 6.2 if is_rural else (9.3 if place in ["memphis", "columbus"] else 10.5)

    if col == "excess_obesity":   # can be above or below zero -> two colors around a grey middle
        limit = float(df[col].abs().max())
        color_args = dict(color_continuous_scale=BLUE_RED, range_color=(-limit, limit))
    else:                         # only "how much" -> one color, light to dark
        color_args = dict(color_continuous_scale=BLUES)

    fig = px.choropleth_map(
        df, geojson=shapes, locations="tract_geoid", featureidkey="properties.tract_geoid",
        color=col, map_style="carto-positron" if streets else "white-bg", center=center, zoom=zoom, opacity=0.8,
        hover_name="tract_geoid",
        hover_data={"tract_geoid": False, "foodprint_score": ":.0f", "excess_obesity": ":+.1f",
                    "obesity_pct": ":.1f", "diabetes_pct": ":.1f", "median_hh_income": ":$,.0f",
                    "POP2020": ":,"},
        labels={"foodprint_score": "FoodPrint Score", "excess_obesity": "Obesity beyond income (pts)",
                "obesity_pct": "Obesity %", "diabetes_pct": "Diabetes %",
                "median_hh_income": "Median income", "POP2020": "Population"},
        **color_args)
    fig.update_traces(marker_line_width=0.5, marker_line_color="white")

    if show_priority:
        pri = df[df["priority_flag"]]
        # a second layer: no fill, dark outline, so priority is not shown by color alone
        fig.add_trace(go.Choroplethmap(
            geojson=shapes, locations=pri["tract_geoid"], featureidkey="properties.tract_geoid",
            z=[1] * len(pri), colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False, marker_line_width=2, marker_line_color=INK, hoverinfo="skip"))

    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0),
                      coloraxis_colorbar=dict(title="", thickness=14, len=0.6))
    st.plotly_chart(fig, width="stretch")
    st.caption("Dark outline = priority tract. Grey or missing tracts could not be scored. "
               "Hover a tract for its numbers; look it up by ID in the Tract detail tab.")


# ---------- tab 2: priority list ----------
with tab_list:
    if not released:
        st.info("No priority list for this place: the score did not pass the test here.")
    else:
        pri = df[df["priority_flag"]].sort_values("rank")
        table = pri[["rank", "tract_name", "tract_geoid", "suggestion", "also_consider",
                     "foodprint_score", "excess_obesity", "obesity_pct",
                     "diabetes_pct", "poverty_rate_pct", "median_hh_income", "POP2020"] + FEATURES]
        table = table.rename(columns={
            "rank": "Rank", "tract_name": "Tract", "tract_geoid": "GEOID", "suggestion": "Intervention",
            "also_consider": "Secondary", "foodprint_score": "Score",
            "excess_obesity": "Obesity beyond income (pts)", "obesity_pct": "Obesity %",
            "diabetes_pct": "Diabetes %", "poverty_rate_pct": "Poverty %",
            "median_hh_income": "Median income", "POP2020": "Population",
            "limited_share": "Limited-store share", "dist_full_service_km": "Km to supermarket",
            "access_distance": "% people far from store", "affordability_proxy": "% SNAP homes far from store"})
        st.subheader(f"{len(table)} priority tracts, ranked")
        st.caption("Ranked by score plus obesity beyond income. This is the list a hospital would bring "
                   "to its community health needs assessment.")
        st.dataframe(table, hide_index=True, width="stretch", height=480,
                     column_config={"Rank": st.column_config.NumberColumn(format="%d"),
                                    "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                                    "Obesity beyond income (pts)": st.column_config.NumberColumn(format="%+.1f"),
                                    "Median income": st.column_config.NumberColumn(format="$%d"),
                                    "Poverty %": st.column_config.NumberColumn(format="%.1f"),
                                    "Limited-store share": st.column_config.NumberColumn(format="%.2f"),
                                    "Km to supermarket": st.column_config.NumberColumn(format="%.1f")})
        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button("Download the list (CSV)", table.to_csv(index=False),
                           file_name=f"foodprint_priority_{place}.csv", mime="text/csv")
        d2.download_button("Area report (PDF)", place_pdf(place),
                           file_name=f"foodprint_{place}_report.pdf", mime="application/pdf",
                           key="pdf_list")


# ---------- tab 3: one tract ----------
with tab_tract:
    scored = df[df["modeled"]].sort_values("rank")
    def tract_label(geoid):
        row = scored[scored["tract_geoid"] == geoid].iloc[0]
        star = "  (priority)" if row["priority_flag"] and released else ""
        return f"{row['tract_name']}   score {row['foodprint_score']:.0f}{star}"
    geoid = st.selectbox("Tract (sorted by priority rank)", scored["tract_geoid"], format_func=tract_label)
    t = scored[scored["tract_geoid"] == geoid].iloc[0]

    a, b, c, d = st.columns(4)
    a.metric("FoodPrint Score", f"{t['foodprint_score']:.0f} / 100")
    b.metric("Obesity", f"{t['obesity_pct']:.1f}%", f"{t['excess_obesity']:+.1f} pts vs income-predicted",
             delta_color="inverse")
    c.metric("Diabetes", f"{t['diabetes_pct']:.1f}%", f"{t['excess_diabetes']:+.1f} pts vs income-predicted",
             delta_color="inverse")
    d.metric("Median household income", f"${t['median_hh_income']:,.0f}",
             f"poverty {t['poverty_rate_pct']:.0f}%", delta_color="off")

    if released and t["priority_flag"]:
        st.success(f"Priority tract, rank {int(t['rank'])} of {len(scored)} in {names[place]}.")
    elif released:
        st.info(f"Not a priority tract: the score is below the median, or {outcome} is not above "
                "what income predicts.")

    sug_col, dl_col = st.columns([3, 1])
    if t["suggestion"]:
        iv = INTERVENTIONS_ALL[t["main_driver"]]
        label = "Recommendation" if t["tier"] == "Act" else "Watch list. Possible step"
        with sug_col.container(border=True):
            st.markdown(f"**{label}: {t['suggestion']}**")
            st.write(iv["what"] + (f" Secondary: {t['also_consider']}." if t["also_consider"] else ""))
            facts = split_reasons(t["why"])
            if facts:
                st.markdown("\n".join(f"- {r}" for r in facts))
    elif t["tier"] == "Withheld":
        sug_col.caption("No recommendation. The score did not pass validation here.")
    else:
        sug_col.caption("No recommendation for this tract.")
    dl_col.download_button("Tract report (PDF)", tract_pdf(place, geoid),
                           file_name=f"foodprint_{place}_{geoid}.pdf", mime="application/pdf",
                           width="stretch")

    # each feature as a percentile within this place (100 = worst), so the four are comparable
    rows = []
    for f in FEATURES:
        pct = (scored[f] < t[f]).mean() * 100 if pd.notna(t[f]) else None
        rows.append({"Feature": FEATURE_LABELS[f], "This tract": t[f],
                     "Place median": scored[f].median(), "Percentile": pct})
    comp = pd.DataFrame(rows)
    # --- where the tract stands on the score and each factor: every tract in the area as a dot ---
    st.subheader("Where this tract stands")
    st.caption("Each dot is a tract in this area. Blue = this tract, dark line = median tract. Hover a dot for its name.")
    strip_rows = [("foodprint_score", "FoodPrint Score (0-100)", 1)] + [
        (f, f"{INTERVENTIONS_ALL[f]['short']} ({charts.UNITS[f]})", 100 if f == "limited_share" else 1) for f in FEATURES]
    fs = make_subplots(rows=len(strip_rows), cols=1, subplot_titles=[r[1] for r in strip_rows], vertical_spacing=0.1)
    rng = np.random.default_rng(0)
    for i, (col, _, mult) in enumerate(strip_rows, 1):
        d = scored[["tract_name", col]].dropna()
        fs.add_trace(go.Scatter(x=d[col] * mult, y=rng.uniform(-0.3, 0.3, len(d)), mode="markers",
                                marker=dict(size=7, color="#d6d5cf"), text=d["tract_name"],
                                hovertemplate="%{text}<br>%{x:.1f}<extra></extra>", showlegend=False), row=i, col=1)
        med = d[col].median() * mult
        fs.add_trace(go.Scatter(x=[med, med], y=[-0.45, 0.45], mode="lines", line=dict(color="#52514e", width=2),
                                hovertemplate=f"Median tract: {med:.1f}<extra></extra>", showlegend=False), row=i, col=1)
        if pd.notna(t[col]):
            v = t[col] * mult
            right = v > d[col].min() * mult + 0.85 * (d[col].max() - d[col].min()) * mult
            fs.add_trace(go.Scatter(x=[v], y=[0], mode="markers+text", text=[f"<b>{v:.1f}</b>"],
                                    textposition="middle left" if right else "middle right",
                                    marker=dict(size=14, color=BLUE, line=dict(color="white", width=2)),
                                    textfont=dict(size=12, color=INK),
                                    hovertemplate=f"{t['tract_name']}<br>%{{x:.1f}}<extra></extra>",
                                    showlegend=False), row=i, col=1)
        fs.update_yaxes(visible=False, range=[-0.5, 0.5], row=i, col=1)
        fs.update_xaxes(showgrid=False, zeroline=False, row=i, col=1)
    fs.update_layout(height=460, margin=dict(l=0, r=10, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)")
    fs.update_annotations(font_size=12, x=0, xanchor="left")
    st.plotly_chart(fs, width="stretch")

    # --- health beyond income: actual vs predicted, plus the area's validation ---
    st.subheader("Health beyond income")
    g1, g2 = st.columns([1.1, 1])
    oc = outcome
    sc2 = scored.dropna(subset=[f"{oc}_pct", f"excess_{oc}"]).copy()
    sc2["pred"] = sc2[f"{oc}_pct"] - sc2[f"excess_{oc}"]
    lo = float(min(sc2["pred"].min(), sc2[f"{oc}_pct"].min())) - 1
    hi = float(max(sc2["pred"].max(), sc2[f"{oc}_pct"].max())) + 1
    me_a = float(t[f"{oc}_pct"]); me_p = me_a - float(t[f"excess_{oc}"])
    fg = go.Figure()
    fg.add_trace(go.Scatter(x=[lo, hi, lo], y=[lo, hi, hi], fill="toself", fillcolor="rgba(205,226,251,0.4)",
                            line=dict(width=0), hoverinfo="skip", showlegend=False))
    fg.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color="#52514e", width=1),
                            hoverinfo="skip", showlegend=False))
    fg.add_trace(go.Scatter(x=sc2["pred"], y=sc2[f"{oc}_pct"], mode="markers", marker=dict(size=7, color="#b4b3ad"),
                            text=sc2["tract_name"], showlegend=False,
                            hovertemplate="%{text}<br>predicted %{x:.1f}%, actual %{y:.1f}%<extra></extra>"))
    fg.add_trace(go.Scatter(x=[me_p, me_p], y=[me_p, me_a], mode="lines", line=dict(color=BLUE, width=2),
                            hoverinfo="skip", showlegend=False))
    fg.add_trace(go.Scatter(x=[me_p], y=[me_a], mode="markers+text", text=[f"<b>{t[f'excess_{oc}']:+.1f} pts</b>"],
                            textposition="middle right", marker=dict(size=14, color=BLUE, line=dict(color="white", width=2)),
                            hovertemplate=f"{t['tract_name']}<br>predicted %{{x:.1f}}%, actual %{{y:.1f}}%<extra></extra>",
                            showlegend=False))
    fg.add_annotation(text="Worse than income predicts", x=lo, y=hi, xanchor="left", yanchor="top",
                      showarrow=False, font=dict(size=11, color="#52514e"))
    fg.update_layout(height=380, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)",
                     title=dict(text=f"{oc.capitalize()}: actual vs. predicted from income", font=dict(size=13)),
                     xaxis=dict(title="Predicted from income and poverty (%)", range=[lo, hi], showgrid=False),
                     yaxis=dict(title=f"Actual {oc} (%)", range=[lo, hi], showgrid=False))
    g1.plotly_chart(fg, width="stretch")
    g2.image(charts.forest(results, place), width="stretch")
    g2.caption("Filled dot = the score adds predictive power beyond income in this area. "
               "Open dot = it does not.")
    if t["median_hh_income"] > 150000 and t["foodprint_score"] > 70:
        st.caption("Note: this is a high-income tract with a high score. Distance-based features can "
                   "overstate the problem where most households own a car.")


# ---------- tab 4: evidence ----------
with tab_evidence:
    st.subheader("Does the score add anything beyond income? Place by place")
    st.caption("The score was chosen on Richmond and Baltimore, then locked and tested on places it had "
               "never seen. Pass = effect above zero in the spatial model (95% CI) AND lower "
               "leave-one-out error than income + poverty alone.")
    r = results.copy()
    r["strict_pass"] = (r["sem_lo"] > 0) & (r["loo_gain_pct"] > 0)
    r["Place"] = r["city"].map(names)
    r["Outcome"] = r["outcome"].map({"obesity_pct": "Obesity", "diabetes_pct": "Diabetes"})

    held = r[r["role"] == "held-out"]
    k1, k2, k3 = st.columns(3)
    k1.metric("Held-out checks passed", f"{int(held['strict_pass'].sum())} of {len(held)}")
    k2.metric("Held-out places", held["city"].nunique())
    k3.metric("Tracts tested, all places", f"{int(summary['tracts_modeled'].sum()):,}")

    # table: one row per place, a word and a mark for each outcome (never color alone)
    def verdict(x):
        return "✓ pass" if x else "✗ fail"
    grid = r.pivot(index="city", columns="Outcome", values="strict_pass").reindex(summary["place"])
    eff = r.pivot(index="city", columns="Outcome", values="sem_coef").reindex(summary["place"])
    loo = r.pivot(index="city", columns="Outcome", values="loo_gain_pct").reindex(summary["place"])
    role = r.drop_duplicates("city").set_index("city")["role"].reindex(summary["place"])
    evidence = pd.DataFrame({
        "Place": [names[p] for p in grid.index],
        "Role": ["used to build the score" if x == "development" else "held-out test" for x in role],
        "Tracts": summary["tracts_modeled"].values,
        "Obesity": [f"{verdict(p)}  ({e:+.2f})" for p, e in zip(grid["Obesity"], eff["Obesity"])],
        "Diabetes": [f"{verdict(p)}  ({e:+.2f})" for p, e in zip(grid["Diabetes"], eff["Diabetes"])],
        "Error cut, obesity": [f"{v:+.1f}%" for v in loo["Obesity"]],
        "Error cut, diabetes": [f"{v:+.1f}%" for v in loo["Diabetes"]],
    })
    st.dataframe(evidence, hide_index=True, width="stretch")
    st.caption("Numbers in brackets: percentage points of the outcome per 1 SD of score, beyond income, "
               "from the spatial model. Error cut: leave-one-out RMSE reduction vs income + poverty alone.")

    # chart: effect and 95% CI, one panel per outcome (same x axis in both)
    st.subheader("Effect size with 95% interval (spatial model)")
    order = [names[p] for p in summary["place"]][::-1]
    panels = st.columns(2)
    for panel, outcome in zip(panels, ["Obesity", "Diabetes"]):
        d = r[r["Outcome"] == outcome].set_index("Place").loc[order].reset_index()
        f2 = go.Figure()
        for passed, label, symbol in [(True, "Pass", "circle"), (False, "Fail", "circle-open")]:
            s = d[d["strict_pass"] == passed]
            f2.add_trace(go.Scatter(
                x=s["sem_coef"], y=s["Place"], mode="markers", name=label,
                marker=dict(size=11, color=BLUE if passed else GREY, symbol=symbol, line_width=2),
                error_x=dict(type="data", symmetric=False, array=s["sem_hi"] - s["sem_coef"],
                             arrayminus=s["sem_coef"] - s["sem_lo"], thickness=2, width=0,
                             color=BLUE if passed else GREY),
                hovertemplate="%{y}<br>%{x:+.2f} pts per 1 SD<extra>" + label + "</extra>"))
        f2.add_vline(x=0, line_color="#c3c2b7")
        f2.update_layout(title=outcome, height=330, margin=dict(l=0, r=10, t=40, b=0),
                         xaxis_title="pts per 1 SD of score, beyond income", xaxis_range=[-1.1, 2.3],
                         yaxis=dict(categoryorder="array", categoryarray=order),
                         legend=dict(orientation="h", y=-0.3), plot_bgcolor="rgba(0,0,0,0)")
        f2.update_xaxes(gridcolor="#e1e0d9")
        panel.plotly_chart(f2, width="stretch")
    st.caption("Filled dot = pass, open dot = fail. Norfolk fails: a third of its tracts have only "
               "convenience, dollar or small stores nearby, so the store mix barely varies. "
               "Baltimore and Richmond obesity pass in ordinary regression but not the stricter spatial model.")


# ---------- tab 5: data and limits ----------
with tab_about:
    st.subheader("How the score works")
    st.image(charts.method_flow(), width="stretch")
    left, right = st.columns(2)
    left.subheader("Data (all public, no patient data)")
    left.markdown(
        "| Source | Used for |\n|---|---|\n"
        "| CDC PLACES 2025 | obesity and diabetes by tract (outcomes) |\n"
        "| Census ACS 5-year | income and poverty (the baseline) |\n"
        "| USDA Food Access Research Atlas 2025 | distance to SNAP stores |\n"
        "| USDA SNAP retailer history | store type; stores open on June 30, 2023 |\n"
        "| Census TIGER 2020 | tract boundaries |\n")
    left.markdown("**Baseline:** health % ~ poverty rate + log(median income).  \n"
                  "**Our model:** baseline + FoodPrint Score. We report only what the score adds.")
    right.subheader("Limits and responsible use")
    right.markdown(
        "- **Not causal.** The score shows where to look first. A funded pilot is the real test.\n"
        "- **Tracts, not people.** Results describe neighborhoods and say nothing about any one resident.\n"
        "- **Outcomes are estimates.** CDC PLACES values are modeled from surveys and demographics.\n"
        "- **Affordability is a proxy.** We use SNAP households far from a store, not real prices.\n"
        "- **Known failure: Norfolk.** No release where the score does not pass.\n"
        "- **Coverage gaps.** No CDC data for Pennsylvania; rural test is Virginia only.\n"
        "- **Labeling risk.** A high score describes stores and distance, not the people who live there.")
