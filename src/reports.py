# FoodPrint Score - downloadable PDF reports.
#   tract_report(...)  -> bytes   one tract: what is suggested and why
#   place_report(...)  -> bytes   one place: alerts + every "Act" tract with its suggestion
# Used by dashboard/app.py (download buttons). Also runnable for a quick check:
#   python src/reports.py richmond            writes outputs/reports/richmond_*.pdf

import io
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recommendations import FEATURES, FEATURE_LABELS, INTERVENTIONS_ALL, alerts, fmt_value

INK, BLUE, GREY, LIGHT = (11, 11, 11), (42, 120, 214), (110, 110, 105), (240, 239, 236)

DATA_SOURCES = [
    ("CDC PLACES, 2025 release", "obesity and diabetes by tract (modeled estimates, the outcomes)"),
    ("Census ACS 5-year, 2023", "median household income and poverty rate (the baseline)"),
    ("USDA Food Access Research Atlas, 2025", "people and SNAP households far from a SNAP store"),
    ("USDA SNAP retailer history", "store types; stores open on June 30, 2023"),
    ("Census TIGER 2020", "tract boundaries"),
]
LIMITS = [
    "Not causal. The score shows where to look first; a funded pilot is the real test.",
    "Tracts, not people. Results describe neighborhoods and say nothing about any one resident.",
    "Outcomes are estimates. CDC PLACES values are modeled from surveys and demographics.",
    "Affordability is a proxy: SNAP households far from a store, not real prices.",
    "Store data can lag openings and closures. Check locally before acting.",
    "Distance features can overstate the problem where most households own a car.",
    "A high score describes stores and distance, not the people who live there.",
]
METHOD = (
    "The FoodPrint Score combines four inputs with equal weight: the share of nearby SNAP stores that "
    "are convenience, dollar or small stores; distance to the nearest supermarket; the share of people "
    "far from a SNAP store; and the share of households that use SNAP and live far from a store. Each "
    "input is standardized within the place, averaged, and rescaled to 0-100 (100 = worst food "
    "environment in that place). The inputs were chosen on Richmond and Baltimore, then locked and "
    "tested on places the score had never seen. A place passes when, after controlling for poverty and "
    "income, the score's effect is above zero in a spatial regression (95% interval) AND it lowers "
    "leave-one-out prediction error compared with income and poverty alone. A priority tract has a score "
    "above the place median AND more of the validated outcome than income predicts. Suggestions come "
    "from the inputs where the tract is in the worst 30% of its place."
)


def clean(s):
    """Core PDF fonts are latin-1 only."""
    s = str(s)
    for a, b in {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
                 "≥": ">=", "≤": "<=", "±": "+/-", "…": "...", "•": "-"}.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class Report(FPDF):
    def __init__(self, title, subtitle):
        super().__init__(format="Letter")
        self.t, self.sub = clean(title), clean(subtitle)
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, 18)
        self.add_page()

    def header(self):
        self.set_font("Helvetica", "B", 9); self.set_text_color(*BLUE)
        self.cell(0, 5, "FOODPRINT SCORE", new_x="LMARGIN", new_y="NEXT")
        if self.page_no() == 1:
            self.set_font("Helvetica", "B", 18); self.set_text_color(*INK)
            self.multi_cell(0, 8, self.t, new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 10); self.set_text_color(*GREY)
            self.multi_cell(0, 5, self.sub, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-13); self.set_font("Helvetica", "", 8); self.set_text_color(*GREY)
        self.cell(0, 5, clean(f"Generated {date.today():%B %d, %Y}. A prioritization tool, not a diagnosis "
                              f"or causal claim.   Page {self.page_no()}"), align="C")

    def h2(self, text):
        self.ln(2); self.set_font("Helvetica", "B", 12); self.set_text_color(*INK)
        self.cell(0, 7, clean(text), new_x="LMARGIN", new_y="NEXT")

    def para(self, text, size=10, color=INK, style=""):
        self.set_font("Helvetica", style, size); self.set_text_color(*color)
        self.multi_cell(0, 5, clean(text), new_x="LMARGIN", new_y="NEXT")

    def bullets(self, items, size=9.5):
        self.set_font("Helvetica", "", size); self.set_text_color(*INK)
        for it in items:
            self.set_x(self.l_margin + 2)
            self.multi_cell(0, 4.8, clean("-  " + it), new_x="LMARGIN", new_y="NEXT")

    def callout(self, title, body, fill=(229, 239, 251)):
        self.set_fill_color(*fill); self.set_draw_color(*BLUE)
        self.set_font("Helvetica", "B", 11); self.set_text_color(*INK)
        self.multi_cell(0, 6, clean(title), fill=True, border="LTR", padding=(2, 3, 0, 3),
                        new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, clean(body), fill=True, border="LBR", padding=(1, 3, 2, 3),
                        new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def kv_table(self, rows, w1=70):
        self.set_font("Helvetica", "", 9.5)
        for i, (k, v) in enumerate(rows):
            fill = LIGHT if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*fill)
            lines = self.multi_cell(self.epw - w1, 5.5, clean(v), dry_run=True, output="LINES")
            h = 5.5 * max(1, len(lines)) + 0.5
            if self.get_y() + h > self.h - 20:
                self.add_page()
            y = self.get_y()
            self.set_text_color(*GREY); self.multi_cell(w1, h, clean(k), fill=True, new_x="RIGHT", new_y="TOP")
            self.set_xy(self.l_margin + w1, y)
            self.set_text_color(*INK)
            self.multi_cell(self.epw - w1, 5.5, clean(v), fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_y(y + h)

    def grid(self, header, rows, widths, size=8.5):
        self.set_font("Helvetica", "B", size); self.set_fill_color(*INK); self.set_text_color(255, 255, 255)
        for h, w in zip(header, widths):
            self.cell(w, 6, clean(h), fill=True)
        self.ln()
        self.set_font("Helvetica", "", size); self.set_text_color(*INK)
        for i, r in enumerate(rows):
            if self.get_y() > self.h - 28:
                self.add_page()
            self.set_fill_color(*(LIGHT if i % 2 == 0 else (255, 255, 255)))
            for v, w in zip(r, widths):
                self.cell(w, 5.5, clean(v)[: int(w / 1.6)], fill=True)
            self.ln()

    def image_bytes(self, png, w):
        self.image(io.BytesIO(png), w=w); self.ln(1)


def _driver_chart(t):
    labels = [FEATURE_LABELS[f] for f in FEATURES][::-1]
    vals = [t.get(f"pct_{f}") for f in FEATURES][::-1]
    drivers = {t.get("main_driver")} | {f for f in FEATURES if pd.notna(t.get(f"pct_{f}")) and
                                         INTERVENTIONS_ALL[f]["name"] in str(t.get("also_consider", ""))}
    colors = ["#2a78d6" if f in drivers else "#b9c9dd" for f in FEATURES][::-1]
    fig, ax = plt.subplots(figsize=(7.2, 2.3), dpi=200)
    ax.barh(labels, [0 if pd.isna(v) else v for v in vals], color=colors, height=0.55)
    for i, v in enumerate(vals):
        ax.text((0 if pd.isna(v) else v) + 1.5, i, "no data" if pd.isna(v) else f"{int(v)}", va="center", fontsize=8)
    ax.axvline(50, color="#9a9a94", ls=":", lw=1); ax.axvline(70, color="#b02a2a", ls="--", lw=0.8)
    ax.text(70.5, len(vals) - 0.45, "driver line (70)", fontsize=7, color="#b02a2a")
    ax.set_xlim(0, 108); ax.set_xlabel("Percentile within this place (100 = worst)", fontsize=8)
    ax.tick_params(labelsize=8); [ax.spines[s].set_visible(False) for s in ("top", "right")]
    fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
    return buf.getvalue()


def _evidence_rows(results, place):
    r = results[results["city"] == place]
    rows = []
    for oc, label in [("obesity_pct", "Obesity"), ("diabetes_pct", "Diabetes")]:
        x = r[r["outcome"] == oc]
        if x.empty:
            continue
        x = x.iloc[0]
        ok = (x["sem_lo"] > 0) and (x["loo_gain_pct"] > 0)
        rows.append((f"{label}: {'PASS' if ok else 'did not pass'}",
                     f"{x['sem_coef']:+.2f} pts per 1 SD of score beyond income "
                     f"(95% CI {x['sem_lo']:+.2f} to {x['sem_hi']:+.2f}). "
                     + (f"Cuts prediction error by {x['loo_gain_pct']:.1f}% vs income alone."
                        if x["loo_gain_pct"] > 0 else
                        f"Does not cut prediction error vs income alone ({x['loo_gain_pct']:+.1f}%).")))
    return rows


def _place_role(results, place):
    r = results[results["city"] == place]
    if r.empty:
        return ""
    return ("one of the two places used to build the score" if r.iloc[0]["role"] == "development"
            else "a held-out test place (the score was locked before it was tested here)")


def _common_back_matter(pdf):
    pdf.h2("How the score works")
    pdf.para(METHOD, size=9.5)
    pdf.h2("Data")
    pdf.bullets([f"{a}: {b}" for a, b in DATA_SOURCES])
    pdf.h2("Limits and responsible use")
    pdf.bullets(LIMITS)


def tract_report(info, t, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    n_scored = int(place_df["modeled"].sum())
    pdf = Report(f"{t['tract_name']}", f"{name}   |   Tract ID {t['tract_geoid']}")

    tier = t["tier"]
    if tier == "Withheld":
        pdf.callout("No suggestion for this tract",
                    f"The score did not predict obesity or diabetes beyond income in {name}, so we do not "
                    "rank tracts or suggest interventions here. The numbers below are descriptive only.",
                    fill=(251, 236, 236))
    elif tier in ("Act", "Monitor") and t["suggestion"]:
        iv = INTERVENTIONS_ALL[t["main_driver"]]
        head = (f"Suggested action: {t['suggestion']}" if tier == "Act"
                else f"Monitor. If resources allow: {t['suggestion']}")
        body = iv["what"]
        if t.get("also_consider"):
            body += f"\nAlso consider: {t['also_consider']}."
        pdf.callout(head, body)
    else:
        pdf.callout("No action suggested",
                    "This tract is not a priority tract: its score is at or below the place median, or "
                    f"{outcome} is not higher than income predicts. Nothing stands out enough to suggest "
                    "an intervention.", fill=LIGHT)

    if tier in ("Act", "Monitor") and t["suggestion"]:
        pdf.h2("Why this suggestion")
        if tier == "Act":
            pdf.para(f"This is a priority tract (rank {int(t['rank'])} of {n_scored} in {name}): its FoodPrint "
                     f"Score is above the place median and {outcome} is higher than income and poverty "
                     f"predict. The suggestion follows the input(s) where this tract is among the worst 30% "
                     f"of {name}:", size=9.5)
        else:
            pdf.para(f"This tract's score is in the worst fifth of {name}, but {outcome} is not higher than "
                     "income predicts, so it is not a priority tract. The input(s) that stand out:", size=9.5)
        pdf.bullets(_split_reasons(t["why"]))
    pdf.h2("What drives this tract's score")
    pdf.image_bytes(_driver_chart(t), w=pdf.epw)

    pdf.h2("The numbers")
    rows = [("FoodPrint Score", f"{t['foodprint_score']:.0f} / 100 (100 = worst in {name})")]
    if pd.notna(t.get("rank")):
        rows.append(("Priority rank", f"{int(t['rank'])} of {n_scored}" + ("" if released else " (not released)")))
    rows += [
        ("Obesity", f"{t['obesity_pct']:.1f}%  ({t['excess_obesity']:+.1f} pts vs what income predicts)"),
        ("Diabetes", f"{t['diabetes_pct']:.1f}%  ({t['excess_diabetes']:+.1f} pts vs what income predicts)"),
        ("Median household income", f"${t['median_hh_income']:,.0f}" if pd.notna(t['median_hh_income']) else "no data"),
        ("Poverty rate", f"{t['poverty_rate_pct']:.1f}%"),
        ("Population (2020)", f"{t['POP2020']:,.0f}"),
    ]
    med = place_df[place_df["modeled"]][FEATURES].median()
    for f in FEATURES:
        rows.append((FEATURE_LABELS[f].split(" (")[0], f"{fmt_value(f, t[f])}   (place median {fmt_value(f, med[f])})"))
    pdf.kv_table(rows, w1=62)

    pdf.h2(f"Is the score trustworthy in {name}?")
    pdf.para(f"{name} is {_place_role(results, place)}. Test results, after controlling for income and poverty:",
             size=9.5)
    pdf.kv_table(_evidence_rows(results, place), w1=42)
    if released:
        pdf.para(f"The priority list here ranks on {outcome}, the outcome the score passed for"
                 + (" (it passed for both)." if info.get("pass_obesity") and info.get("pass_diabetes") else "."),
                 size=9, color=GREY)
    _common_back_matter(pdf)
    return bytes(pdf.output())


def _split_reasons(why):
    # each driver's reason ends with "(place median ...)." - split there
    why = str(why).strip()
    if not why.endswith(")."):
        return [why]
    return [c.strip() + ")." for c in why[:-2].split(").") if c.strip()]


def short_name(name, rural):
    """'Census Tract 201, Richmond city' -> 'Tract 201' in a city; keep the county when rural."""
    n = str(name).replace("Census Tract ", "Tract ")
    return n if rural else n.split(",")[0]


def place_report(info, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    rural = place == "rural_va"
    pdf = Report(f"{name}: what communities need",
                 f"{int(info['tracts_modeled'])} tracts scored   |   priority list ranked on {outcome}")
    if not released:
        pdf.callout("Priority list not released",
                    f"The score did not pass the validation test in {name} for obesity or diabetes, so we do "
                    "not rank its tracts or suggest interventions. See the test results below.",
                    fill=(251, 236, 236))
    else:
        act = place_df[place_df["tier"] == "Act"]
        pdf.callout(f"{len(act)} priority tracts, {int(act['POP2020'].sum()):,} residents",
                    f"Priority = FoodPrint Score above the place median AND {outcome} higher than income and "
                    "poverty predict. Each priority tract gets one main suggestion from the input where it is "
                    "worst; they are grouped below.")
        pdf.h2("Alerts: what is needed, and where")
        for _, a in alerts(place_df).iterrows():
            iv = INTERVENTIONS_ALL[a["main_driver"]]
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(*INK)
            n_t = f"{a['tracts']} tract" + ("" if a["tracts"] == 1 else "s")
            pdf.multi_cell(0, 5.5, clean(f"{a['suggestion']}  -  {n_t}, {int(a['population']):,} residents"),
                           new_x="LMARGIN", new_y="NEXT")
            pdf.para(f"Why: {iv['why']}", size=9, color=GREY)
            pdf.para(f"What: {iv['what']}", size=9)
            lst = [short_name(n, rural) for n in a["tract_list"]]
            top = "; ".join(lst[:6]) + (f" and {len(lst) - 6} more" if len(lst) > 6 else "")
            pdf.para(f"Highest-ranked: {top}", size=8.5, color=GREY)
            pdf.ln(1.5)
        pdf.add_page()
        pdf.h2("Every priority tract")
        rows = []
        for _, r in act.sort_values("rank").iterrows():
            rows.append([f"{int(r['rank'])}", short_name(r["tract_name"], rural),
                         f"{r['foodprint_score']:.0f}", f"{r[f'excess_{outcome}']:+.1f}",
                         f"{int(r['POP2020']):,}", r["suggestion"]])
        pdf.grid(["Rank", "Tract", "Score", f"Excess {outcome[:4]}.", "People", "Main suggestion"], rows,
                 [11, 42, 13, 20, 16, pdf.epw - 102])
    pdf.h2(f"Is the score trustworthy in {name}?")
    pdf.para(f"{name} is {_place_role(results, place)}.", size=9.5)
    pdf.kv_table(_evidence_rows(results, place), w1=42)
    _common_back_matter(pdf)
    return bytes(pdf.output())


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    key = sys.argv[1] if len(sys.argv) > 1 else "richmond"
    summary = pd.read_csv(ROOT / "outputs/dashboard/places_summary.csv")
    tracts = pd.read_csv(ROOT / "outputs/dashboard/all_tracts.csv", dtype={"tract_geoid": str}, keep_default_na=True)
    tracts[["suggestion", "also_consider", "why", "main_driver"]] = tracts[["suggestion", "also_consider", "why", "main_driver"]].fillna("")
    results = pd.read_csv(ROOT / "outputs/all_cities/all_cities_results.csv")
    info = summary[summary["place"] == key].iloc[0].to_dict()
    df = tracts[tracts["place"] == key]
    out = ROOT / "outputs" / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / f"{key}_place_report.pdf").write_bytes(place_report(info, df, results))
    first = df[df["modeled"]].sort_values("rank").iloc[0]
    (out / f"{key}_tract_{first['tract_geoid']}.pdf").write_bytes(tract_report(info, first, df, results))
    print("wrote", sorted(p.name for p in out.glob(f"{key}_*.pdf")))
