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
import charts

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
        lh = 5.5
        for i, (k, v) in enumerate(rows):
            fill = LIGHT if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*fill)
            nk = len(self.multi_cell(w1 - 2, lh, clean(k), dry_run=True, output="LINES"))
            nv = len(self.multi_cell(self.epw - w1, lh, clean(v), dry_run=True, output="LINES"))
            h = lh * max(nk, nv, 1) + 1
            if self.get_y() + h > self.h - 20:
                self.add_page()
            y = self.get_y()
            self.rect(self.l_margin, y, self.epw, h, style="F")
            self.set_xy(self.l_margin, y + 0.5); self.set_text_color(*GREY)
            self.multi_cell(w1 - 2, lh, clean(k), align="L")
            self.set_xy(self.l_margin + w1, y + 0.5); self.set_text_color(*INK)
            self.multi_cell(self.epw - w1, lh, clean(v), align="L")
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


def _two_up(pdf, png_left, png_right, w_left=0.45):
    """Two images side by side, top-aligned; cursor moves below the taller one."""
    y = pdf.get_y(); wl = pdf.epw * w_left - 2; wr = pdf.epw * (1 - w_left) - 2
    a = pdf.image(io.BytesIO(png_left), x=pdf.l_margin, y=y, w=wl)
    b = pdf.image(io.BytesIO(png_right), x=pdf.l_margin + wl + 4, y=y, w=wr)
    pdf.set_y(y + max(a.rendered_height, b.rendered_height) + 2)


def _back_matter(pdf):
    pdf.h2("How the score works")
    pdf.image_bytes(charts.method_flow(), w=pdf.epw)
    pdf.para("Each factor is standardized within the area before averaging, so a score of 100 means "
             "worst in this area, not nationally.", size=8.5, color=GREY)
    pdf.h2("Data and limitations")
    pdf.bullets([f"{a}: {b}" for a, b in DATA_SOURCES], size=8.5)
    pdf.ln(1)
    pdf.bullets(LIMITS, size=8.5)


def tract_report(info, t, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    n_scored = int(place_df["modeled"].sum())
    rank = f"Rank {int(t['rank'])} of {n_scored}  |  " if pd.notna(t.get("rank")) and released else ""
    pdf = Report(f"{t['tract_name']}",
                 f"{name}  |  {rank}{t['POP2020']:,.0f} residents  |  median income "
                 + (f"${t['median_hh_income']:,.0f}" if pd.notna(t['median_hh_income']) else "n/a")
                 + f"  |  poverty {t['poverty_rate_pct']:.0f}%")
    tier = t["tier"]
    if tier == "Withheld":
        pdf.callout("No recommendation", f"The score did not pass validation in {name}. Charts are descriptive only.",
                    fill=(251, 236, 236))
    elif tier in ("Act", "Monitor") and t["suggestion"]:
        iv = INTERVENTIONS_ALL[t["main_driver"]]
        head = f"Recommendation: {t['suggestion']}" if tier == "Act" else f"Watch list. Possible step: {t['suggestion']}"
        pdf.callout(head, iv["what"] + (f" Secondary: {t['also_consider']}." if t.get("also_consider") else ""))
    else:
        pdf.callout("No recommendation", "Not a priority tract.", fill=LIGHT)

    pdf.h2("Where this tract stands")
    pdf.image_bytes(charts.factor_strips(t, place_df), w=pdf.epw)
    pdf.para("Factors on which the tract is in the worst 30% of the area drive the recommendation.",
             size=8.5, color=GREY)

    pdf.h2("Health beyond income")
    _two_up(pdf, charts.health_gap(t, place_df, outcome), charts.forest(results, place))
    pdf.para(f"Left: each dot is a tract; this tract has {abs(t[f'excess_{outcome}']):.1f} pts "
             f"{'more' if t[f'excess_{outcome}'] > 0 else 'less'} {outcome} than income and poverty predict. "
             f"Right: across {name}, the score " + ("adds" if released else "does not reliably add")
             + f" predictive power beyond income ({_place_role(results, place).split(':')[0].lower()}).",
             size=8.5, color=GREY)
    pdf.add_page()
    _back_matter(pdf)
    return bytes(pdf.output())


def place_report(info, place_df, results):
    place, name = info["place"], info["place_name"]
    released = bool(info["released"])
    outcome = info.get("priority_outcome", "obesity")
    rural = place == "rural_va"
    pdf = Report(f"{name}: priority tracts and recommended interventions",
                 f"{int(info['tracts_modeled'])} tracts scored  |  ranked on {outcome}")
    if not released:
        pdf.callout("Not released", f"The score did not pass validation in {name}, so tracts are not ranked.",
                    fill=(251, 236, 236))
        pdf.image_bytes(charts.forest(results, place), w=pdf.epw * 0.55)
    else:
        act = place_df[place_df["tier"] == "Act"]
        pdf.callout(f"{len(act)} priority tracts  |  {int(act['POP2020'].sum()):,} residents",
                    f"Score above the area median and {outcome} higher than income and poverty predict.")
        pdf.h2("Residents covered by each intervention")
        pdf.image_bytes(charts.intervention_bars(place_df), w=pdf.epw)
        pdf.h2("Where")
        pdf.image_bytes(charts.intervention_maps(place_df, place), w=pdf.epw)
        pdf.add_page()
        pdf.h2("What each intervention involves")
        rows = []
        for _, a in alerts(place_df).iterrows():
            iv = INTERVENTIONS_ALL[a["main_driver"]]
            rows.append((a["suggestion"], iv["what"]))
        pdf.kv_table(rows, w1=55)
        pdf.h2("Priority tracts by rank")
        rows = []
        for _, r in act.sort_values("rank").iterrows():
            rows.append([f"{int(r['rank'])}", short_name(r["tract_name"], rural),
                         f"{r['foodprint_score']:.0f}", f"{r[f'excess_{outcome}']:+.1f}",
                         f"{int(r['POP2020']):,}", r["suggestion"]])
        pdf.grid(["Rank", "Tract", "Score", f"Excess {outcome[:4]}.", "Pop.", "Intervention"], rows,
                 [11, 42, 13, 20, 16, pdf.epw - 102])
        pdf.h2("Validation")
        pdf.image_bytes(charts.forest(results, place), w=pdf.epw * 0.55)
    pdf.para(_place_role(results, place), size=8.5, color=GREY)
    pdf.add_page()
    _back_matter(pdf)
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
