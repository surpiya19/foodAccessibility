# FoodPrint Score - step 12: final scores, priority lists and map data for every place
# Usage: python src/12_final_scores.py
#
# Uses the locked store-type score C (outputs/store_test/chosen.json):
#   limited_share, dist_full_service_km, access_distance, affordability_proxy
# Same score and same tract filter as src/10_all_cities.py, so the numbers match its results.
#
# Reads, for every place in src/regions.py that has been built:
#   data/processed/<place>/master_tract_table.csv
#   data/processed/<place>/tracts.geojson
#   outputs/all_cities/all_cities_results.csv   (from step 10: did the score pass here?)
# Writes:
#   outputs/<place>/foodprint_ranked_tracts.csv   final ranked list (replaces the old-score list)
#   outputs/dashboard/tracts_<place>.geojson      map layer: one shape per tract with all values
#   outputs/dashboard/all_tracts.csv              every tract of every place in one table
#   outputs/dashboard/places_summary.csv          one row per place (counts, pass/fail, released)

import json
import numpy as np
import pandas as pd
import geopandas as gpd

from regions import ROOT, REGIONS

FEATURES = json.load(open(ROOT / "outputs" / "store_test" / "chosen.json"))["features"]
DASH = ROOT / "outputs" / "dashboard"
DASH.mkdir(parents=True, exist_ok=True)
RESULTS = ROOT / "outputs" / "all_cities" / "all_cities_results.csv"


def zscore(s):
    return (s - s.mean()) / s.std()


def income_residual(d, outcome):
    # outcome ~ poverty + log(income) by least squares; the residual is what income does not explain
    X = np.column_stack([np.ones(len(d)), d["poverty_rate_pct"], d["log_income"]])
    beta = np.linalg.lstsq(X, d[outcome], rcond=None)[0]
    return d[outcome] - X @ beta


# did the score pass in each place? (step 10). A place is "released" if it passed for at least one outcome.
passed = {}
if RESULTS.exists():
    res = pd.read_csv(RESULTS)
    for city, g in res.groupby("city"):
        passed[city] = {
            "pass_obesity": bool(g.loc[g["outcome"] == "obesity_pct", "pass"].any()),
            "pass_diabetes": bool(g.loc[g["outcome"] == "diabetes_pct", "pass"].any()),
            "spatial_pass_obesity": bool((g.loc[g["outcome"] == "obesity_pct", "sem_lo"] > 0).any()),
            "spatial_pass_diabetes": bool((g.loc[g["outcome"] == "diabetes_pct", "sem_lo"] > 0).any()),
        }
else:
    print("NOTE: run src/10_all_cities.py first to fill in pass/fail.")

all_rows, summary = [], []
for key, region in REGIONS.items():
    master_path = ROOT / "data" / "processed" / key / "master_tract_table.csv"
    if not master_path.exists():
        continue
    m = pd.read_csv(master_path, dtype={"tract_geoid": str})
    if not set(FEATURES) <= set(m.columns):
        print("skip", key, "- store features missing")
        continue

    # ---------- 1. score: equal-weight mean of z-scores, rescaled 0-100 (100 = worst in this place) ----------
    raw = pd.concat([zscore(m[f]) for f in FEATURES], axis=1).mean(axis=1, skipna=True)
    m["foodprint_score"] = 100 * (raw - raw.min()) / (raw.max() - raw.min())

    # ---------- 2. tracts we can model: health + income known, <50% group quarters ----------
    ok = m.dropna(subset=["obesity_pct", "diabetes_pct", "log_income", "poverty_rate_pct", "foodprint_score"])
    ok = ok[ok["PCTGQTRS"] < 50].copy()
    ok["excess_obesity"] = income_residual(ok, "obesity_pct")
    ok["excess_diabetes"] = income_residual(ok, "diabetes_pct")
    ok["priority_index"] = zscore(ok["foodprint_score"]) + zscore(ok["excess_obesity"])
    ok["priority_flag"] = (ok["foodprint_score"] > ok["foodprint_score"].median()) & (ok["excess_obesity"] > 0)
    ok["score_quintile"] = pd.qcut(ok["foodprint_score"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    # ---------- 3. ranked list ----------
    ranked = ok.sort_values(["priority_flag", "priority_index"], ascending=[False, False])
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    cols = ["rank", "tract_geoid", "priority_flag", "priority_index", "foodprint_score", "score_quintile",
            "excess_obesity", "excess_diabetes", "obesity_pct", "diabetes_pct",
            "poverty_rate_pct", "median_hh_income", "POP2020"] + FEATURES
    out_dir = ROOT / "outputs" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    ranked[cols].round(3).to_csv(out_dir / "foodprint_ranked_tracts.csv", index=False)

    # ---------- 4. one table for the dashboard (all tracts, also the ones we could not model) ----------
    t = m[["tract_geoid", "foodprint_score", "obesity_pct", "diabetes_pct", "poverty_rate_pct",
           "median_hh_income", "POP2020"] + FEATURES].merge(
        ranked[["tract_geoid", "rank", "priority_flag", "priority_index", "score_quintile",
                "excess_obesity", "excess_diabetes"]], on="tract_geoid", how="left")
    t["modeled"] = t["rank"].notna()
    t["priority_flag"] = t["priority_flag"].fillna(False).astype(bool)
    t.insert(0, "place", key)
    t.insert(1, "place_name", region["name"])
    all_rows.append(t)

    # ---------- 5. map layer ----------
    g = gpd.read_file(ROOT / "data" / "processed" / key / "tracts.geojson")
    g["GEOID"] = g["GEOID"].astype(str)
    g = g[["GEOID", "geometry"]].rename(columns={"GEOID": "tract_geoid"}).merge(t, on="tract_geoid", how="inner")
    g = g.to_crs("EPSG:4326")
    g["geometry"] = g.geometry.simplify(0.0005)   # smaller file, still looks the same on a city map
    g.round(3).to_file(DASH / f"tracts_{key}.geojson", driver="GeoJSON")

    # ---------- 6. summary row ----------
    p = passed.get(key, {})
    released = p.get("pass_obesity", False) or p.get("pass_diabetes", False)
    top_q = ok.loc[ok["score_quintile"] == 5, "excess_obesity"].mean()
    low_q = ok.loc[ok["score_quintile"] == 1, "excess_obesity"].mean()
    summary.append({"place": key, "place_name": region["name"], "tracts": len(m), "tracts_modeled": len(ok),
                    "priority_tracts": int(ok["priority_flag"].sum()),
                    "priority_population": int(ok.loc[ok["priority_flag"], "POP2020"].sum()),
                    "obesity_gap_worst_vs_best_fifth": round(top_q - low_q, 2),
                    **p, "released": released if p else None})
    print(f"{region['name']:32s} tracts {len(ok):4d}  priority {int(ok['priority_flag'].sum()):4d}  "
          f"released {released if p else '?'}")

pd.concat(all_rows).round(3).to_csv(DASH / "all_tracts.csv", index=False)
pd.DataFrame(summary).to_csv(DASH / "places_summary.csv", index=False)
print("\nWrote outputs/<place>/foodprint_ranked_tracts.csv and", DASH)
