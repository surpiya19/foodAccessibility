# FoodPrint Score - PDF reports.
#   tract_report(...)  -> bytes   one tract: recommendation, basis, profile, validation
#   place_report(...)  -> bytes   one area: interventions by tract count, ranked priority tracts
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
from recommendations import FEATURES, INTERVENTIONS_ALL, alerts, fmt_value, split_reasons

INK, BLUE, GREY, LIGHT = (11, 11, 11), (42, 120, 214), (110, 110, 105), (240, 239, 236)

DATA_SOURCES = [
    ("CDC PLACES, 2025 release", "tract obesity and diabetes prevalence (model-based estimates)"),
    ("Census ACS 5-year, 2019-2023", "median household income, poverty rate"),
    ("USDA Food Access Research Atlas, 2025", "residents and SNAP households far from a SNAP store"),
    ("USDA SNAP Retailer Locator, historical", "store type and location, stores active June 30, 2023"),
    ("Census TIGER/Line 2020", "tract boundaries"),
]
LIMITS = [
    "The score flags where to look; it does not show that food access causes obesity or diabetes. "
    "A pilot with an evaluation is the real test.",
    "Results describe tracts, not individual residents.",
    "PLACES prevalence figures are model-based estimates, not clinical counts.",
    "Affordability is approximated by SNAP households far from a store. Food prices are not measured.",
    "Store lists lag openings and closures. Confirm locally before committing funds.",
    "Distance matters less where most households have a car.",
]
METHOD = (
    "Four factors, weighted equally: share of nearby SNAP stores that are corner, dollar or small stores; "
    "distance to the nearest supermarket; share of residents far from a SNAP store; and share of "
    "households on SNAP and far from a store. Each is standardized within the area, averaged, and scaled "
    "0-100 (100 = worst in the area). The factors were selected using Richmond and Baltimore and then "
    "fixed before testing elsewhere. An area passes if, controlling for poverty and log median income, "
    "the score's coefficient in a spatial error model is positive (95% CI above zero) and it lowers "
    "leave-one-out prediction error. Priority tracts score above the area median and have higher "
    "prevalence of the validated outcome than income and poverty predict. Recommendations follow from "
    "the factors on which a tract falls in the worst 30% of its area."
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
        if self.page_no() == 1:
            self.set_font("Helvetica", "B", 18); self.set_text_color(*INK)
            self.multi_cell(0, 8, self.t, align="L", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 10); self.set_text_color(*GREY)
            self.multi_cell(0, 5, self.sub, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-13); self.set_font("Helvetica", "", 8); self.set_text_color(*GREY)
        self.cell(0, 5, clean(f"FoodPrint Score  |  {date.today():%b %d, %Y}  |  {self.page_no()}"), align="C")

    def h2(self, text):
        self.ln(2); self.set_font("Helvetica", "B", 12); self.set_text_color(*INK)
        self.cell(0, 7, clean(text), new_x="LMARGIN", new_y="NEXT")

    def para(self, text, size=10, color=INK, style=""):
        self.set_font("Helvetica", style, size); self.set_text_color(*color)
        self.multi_cell(0, 5, clean(text), align="L", new_x="LMARGIN", new_y="NEXT")

    def bullets(self, items, size=9.5):
        self.set_font("Helvetica", "", size); self.set_text_color(*INK)
        for it in items:
            self.set_x(self.l_margin + 2)
            self.multi_cell(0, 4.8, clean("-  " + it), align="L", new_x="LMARGIN", new_y="NEXT")

    def callout(self, title, body, fill=(229, 239, 251)):
        self.set_fill_color(*fill); self.set_draw_color(*BLUE)
        self.set_font("Helvetica", "B", 11); self.set_text_color(*INK)
        self.multi_cell(0, 6, clean(title), fill=True, border="LTR", padding=(2, 3, 0, 3),
                        new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, clean(body), fill=True, align="L", border="LBR", padding=(1, 3, 2, 3),
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
            self.multi_cell(self.epw - w1, 5.5, clean(v), fill=True, align="L", new_x="LMARGIN", new_y="NEXT")
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
    labels = [INTERVENTIONS_ALL[f]["short"] for f in FEATURES][::-1]
    vals = [t.get(f"pct_{f}") for f in FEATURES][::-1]
    drivers = {t.get("main_driver")} | {f for f in FEATURES
                                         if INTERVENTIONS_ALL[f]["name"] in str(t.get("also_consider", ""))}
    colors = ["#2a78d6" if f in drivers else "#c4ccd6" for f in FEATURES][::-1]
    fig, ax = plt.subplots(figsize=(7.2, 2.1), dpi=200)
    ax.barh(labels, [0 if pd.isna(v) else v for v in vals], color=colors, height=0.55)
    for i, v in enumerate(vals):
        ax.text((0 if pd.isna(v) else v) + 1.5, i, "n/a" if pd.isna(v) else f"{int(v)}", va="center", fontsize=8)
    ax.axvline(70, color="#888", ls="--", lw=0.8)
    ax.set_xlim(0, 105); ax.set_xlabel("Percentile within area (100 = worst); dashed line = worst 30%", fontsize=8)
    ax.tick_params(labelsize=8); [ax.spines[k].set_visible(False) for k in ("top", "right")]
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
        loo = (f"prediction error {x['loo_gain_pct']:.1f}% lower than income alone" if x["loo_gain_pct"] > 0
               else f"no reduction in prediction error ({x['loo_gain_pct']:+.1f}%)")
        rows.append((f"{label} ({'passed' if ok else 'not passed'})",
                     f"{x['sem_coef']:+.2f} pts per SD of score (95% CI {x['sem_lo']:.2f} to {x['sem_hi']:.2f}); {loo}"))
    return rows


def _place_role(results, place):
    r = results[results["city"] == place]
    if r.empty:
        return ""
    return ("Development area: used to select the score's factors."
            if r.iloc[0]["role"] == "development"
            else "Held-out area: the score was fixed before being tested here.")


def _common_back_matter(pdf):
    pdf.h2("Method")
    pdf.para(METHOD, size=9)
    pdf.h2("Data")
    pdf.bullets([f"{a}: {b}" for a, b in DATA_SOURCES], size=9)
    pdf.h2("Limitations")
    pdf.bullets(LIMITS, size=9)


def short_name(name, rural):
    """'Census Tract 201, Richmond city' -> 'Tract 201' in a city; keep the county when rural."""
    n = str(name).replace("Census Tract ", "Tract ")
    return n if rural else n.split(",")[0]


def tract_report(info, t, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    n_scored = int(place_df["modeled"].sum())
    pdf = Report(f"{t['tract_name']}", f"{name}  |  GEOID {t['tract_geoid']}")
    tier = t["tier"]
    excess = t[f"excess_{outcome}"]

    if tier == "Withheld":
        pdf.callout("No recommendation",
                    f"The score did not pass validation in {name}, so tracts here are not ranked. "
                    "Figures below are descriptive.", fill=(251, 236, 236))
    elif tier in ("Act", "Monitor") and t["suggestion"]:
        iv = INTERVENTIONS_ALL[t["main_driver"]]
        head = f"Recommendation: {t['suggestion']}" if tier == "Act" else f"Watch list. Possible step: {t['suggestion']}"
        body = iv["what"] + (f" Secondary: {t['also_consider']}." if t.get("also_consider") else "")
        pdf.callout(head, body)
    else:
        pdf.callout("No recommendation",
                    f"Not a priority tract. Either the score is at or below the {name} median or {outcome} "
                    "is no higher than income and poverty predict.", fill=LIGHT)

    if tier in ("Act", "Monitor") and t["suggestion"]:
        pdf.h2("Basis")
        if tier == "Act":
            lead = (f"Rank {int(t['rank'])} of {n_scored} in {name}. Score {t['foodprint_score']:.0f}/100; "
                    f"{outcome} prevalence {t[f'{outcome}_pct']:.1f}%, {excess:+.1f} pts relative to what "
                    f"income and poverty predict.")
        else:
            lead = (f"Score {t['foodprint_score']:.0f}/100, in the worst fifth of {name}, but {outcome} is "
                    f"{excess:+.1f} pts relative to the income prediction, so it is not a priority tract.")
        reasons = split_reasons(t["why"])
        if reasons:
            lead += " Factors in the worst 30% of the area:"
        else:
            lead += " " + INTERVENTIONS_ALL["general"]["why"]
        pdf.para(lead, size=9.5)
        if reasons:
            pdf.bullets(reasons)
    pdf.h2("Score components")
    pdf.image_bytes(_driver_chart(t), w=pdf.epw)

    pdf.h2("Tract profile")
    rows = [("FoodPrint Score", f"{t['foodprint_score']:.0f} / 100")]
    if pd.notna(t.get("rank")) and released:
        rows.append(("Priority rank", f"{int(t['rank'])} of {n_scored}"))
    rows += [
        ("Obesity", f"{t['obesity_pct']:.1f}%  ({t['excess_obesity']:+.1f} pts vs. income-predicted)"),
        ("Diabetes", f"{t['diabetes_pct']:.1f}%  ({t['excess_diabetes']:+.1f} pts vs. income-predicted)"),
        ("Median household income", f"${t['median_hh_income']:,.0f}" if pd.notna(t['median_hh_income']) else "n/a"),
        ("Poverty rate", f"{t['poverty_rate_pct']:.1f}%"),
        ("Population (2020)", f"{t['POP2020']:,.0f}"),
    ]
    med = place_df[place_df["modeled"]][FEATURES].median()
    for f in FEATURES:
        rows.append((INTERVENTIONS_ALL[f]["short"], f"{fmt_value(f, t[f])}  (median tract {fmt_value(f, med[f])})"))
    pdf.kv_table(rows, w1=62)

    pdf.h2(f"Validation, {name}")
    pdf.para(_place_role(results, place), size=9.5)
    pdf.kv_table(_evidence_rows(results, place), w1=48)
    if released:
        both = info.get("pass_obesity") and info.get("pass_diabetes")
        pdf.para(f"Priority ranking uses {outcome}" + ("." if both else f", the only outcome that passed here."),
                 size=9, color=GREY)
    _common_back_matter(pdf)
    return bytes(pdf.output())


def place_report(info, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    rural = place == "rural_va"
    pdf = Report(f"{name}: priority tracts and recommended interventions",
                 f"{int(info['tracts_modeled'])} tracts scored  |  ranked on {outcome}")
    if not released:
        pdf.callout("Not released",
                    f"The score did not pass validation in {name} for obesity or diabetes, so tracts are "
                    "not ranked and no interventions are recommended. Results are below.",
                    fill=(251, 236, 236))
    else:
        act = place_df[place_df["tier"] == "Act"]
        pdf.para(f"{len(act)} of {int(info['tracts_modeled'])} tracts are priority tracts, with "
                 f"{int(act['POP2020'].sum()):,} residents. A priority tract scores above the area median "
                 f"and has higher {outcome} prevalence than income and poverty predict. Each is matched to "
                 "one intervention based on its worst factor.", size=10)
        pdf.h2("Recommended interventions")
        for _, a in alerts(place_df).iterrows():
            iv = INTERVENTIONS_ALL[a["main_driver"]]
            n_t = f"{a['tracts']} tract" + ("" if a["tracts"] == 1 else "s")
            pdf.set_font("Helvetica", "B", 10.5); pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.5, clean(f"{a['suggestion']} ({n_t}, {int(a['population']):,} residents)"),
                           new_x="LMARGIN", new_y="NEXT")
            pdf.para(f"{iv['why']} {iv['what']}", size=9)
            lst = [short_name(n, rural) for n in a["tract_list"]]
            more = f"; {len(lst) - 10} more in the table" if len(lst) > 10 else ""
            pdf.para("; ".join(lst[:10]) + more, size=8.5, color=GREY)
            pdf.ln(1.5)
        pdf.add_page()
        pdf.h2("Priority tracts by rank")
        rows = []
        for _, r in act.sort_values("rank").iterrows():
            rows.append([f"{int(r['rank'])}", short_name(r["tract_name"], rural),
                         f"{r['foodprint_score']:.0f}", f"{r[f'excess_{outcome}']:+.1f}",
                         f"{int(r['POP2020']):,}", r["suggestion"]])
        pdf.grid(["Rank", "Tract", "Score", f"Excess {outcome[:4]}.", "Pop.", "Intervention"], rows,
                 [11, 42, 13, 20, 16, pdf.epw - 102])
    pdf.h2("Validation")
    pdf.para(_place_role(results, place), size=9.5)
    pdf.kv_table(_evidence_rows(results, place), w1=48)
    _common_back_matter(pdf)
    return bytes(pdf.output())


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    key = sys.argv[1] if len(sys.argv) > 1 else "richmond"
    summary = pd.read_csv(ROOT / "outputs/dashboard/places_summary.csv")
    tracts = pd.read_csv(ROOT / "outputs/dashboard/all_tracts.csv", dtype={"tract_geoid": str})
    cols = ["tract_name", "tier", "suggestion", "main_driver", "also_consider", "why"]
    tracts[cols] = tracts[cols].fillna("")
    results = pd.read_csv(ROOT / "outputs/all_cities/all_cities_results.csv")
    info = summary[summary["place"] == key].iloc[0].to_dict()
    df = tracts[tracts["place"] == key]
    out = ROOT / "outputs" / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / f"{key}_place_report.pdf").write_bytes(place_report(info, df, results))
    first = df[df["modeled"]].sort_values("rank").iloc[0]
    (out / f"{key}_tract_{first['tract_geoid']}.pdf").write_bytes(tract_report(info, first, df, results))
    print("wrote", sorted(p.name for p in out.glob(f"{key}_*.pdf")))
