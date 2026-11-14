# FoodPrint Score - rural Virginia: build all inputs in one script
# Usage:
#   python src/02_extract_fara.py rural_va      (first: pulls every Virginia row from the FARA Excel)
#   python src/01r_rural_virginia.py            (then this script)
#
# Rural Virginia is every Virginia tract that USDA FARA marks as rural (Urban = 0).
# It is a whole state, not one county, so steps 01, 03, 05b and 06 (written for one county)
# are replaced by this script. It writes the SAME files as the other cities, so
# src/10_all_cities.py and src/12_final_scores.py work on it without changes.
#
# Rural rules (USDA uses 10 miles, not 1/2 mile, for rural tracts):
#   access_distance     = DD_SRAM_lapop10share   % of people > 10 miles (driving) from a SNAP store
#   vehicle_gap         = DD_SRAM_lahunv10share  % of homes with no car AND > 10 miles from a store
#   affordability_proxy = DD_SRAM_lasnap10share  % of SNAP households > 10 miles from a store
#   store mix (limited_share) is counted within 10 miles of the tract center, not 1 mile
#
# Needs:
#   internet + CENSUS_KEY in .env
#   data/processed/rural_va/fara2025.csv  (from step 02, see above)
#   data/raw/Historical SNAP Retailer Locator Data*.csv  (see src/05b_snap_store_features.py)
# Writes data/processed/rural_va/:
#   places_acs.csv, tracts.geojson, store_features.csv, master_tract_table.csv

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from dotenv import load_dotenv

from regions import ROOT, REGIONS

KEY = "rural_va"
REGION = REGIONS[KEY]
PROCESSED = ROOT / "data" / "processed" / KEY
PROCESSED.mkdir(parents=True, exist_ok=True)
STATE = REGION["state"]       # "51"
ABBR = REGION["abbr"]         # "VA"
ACS_YEAR = 2023               # same as the other cities (step 01)
RADIUS = 16093                # 10 miles in meters
REF_DATE = pd.Timestamp("2023-06-30")
CLOSURE_START = pd.Timestamp("2018-07-01")
FULL_SERVICE = ["Supermarket", "Super Store", "Large Grocery Store"]
LIMITED = ["Convenience Store", "Combination Grocery/Other", "Small Grocery Store"]
ACS_MISSING_CODES = [-666666666, -999999999, -888888888, -222222222]

load_dotenv(ROOT / ".env")
CENSUS_KEY = os.getenv("CENSUS_KEY")
if CENSUS_KEY is None:
    raise SystemExit("CENSUS_KEY not found. Copy .env.example to .env and add your key.")


# ---------- Part 1: which tracts are rural (from FARA) ----------
fara_path = PROCESSED / "fara2025.csv"
if not fara_path.exists():
    raise SystemExit("Run first: python src/02_extract_fara.py rural_va")
fara = pd.read_csv(fara_path, dtype={"CensusTract20": str})
fara = fara[fara["Urban"] == 0].copy()
rural_ids = set(fara["CensusTract20"])
print("Rural Virginia tracts in FARA:", len(rural_ids))


# ---------- Part 2: CDC PLACES obesity + diabetes (whole state) ----------
resp = requests.get("https://data.cdc.gov/resource/cwsq-ngmh.json",
                    params={"$where": f"stateabbr='{ABBR}' AND measureid in('OBESITY','DIABETES')",
                            "$limit": 20000}, timeout=120)
resp.raise_for_status()
places = pd.DataFrame(resp.json())
places["data_value"] = pd.to_numeric(places["data_value"], errors="coerce")
places = (places.pivot_table(index="locationname", columns="measureid",
                             values="data_value", aggfunc="first")
          .reset_index()
          .rename(columns={"locationname": "tract_geoid",
                           "OBESITY": "obesity_pct", "DIABETES": "diabetes_pct"}))
print("PLACES Virginia tracts:", len(places))


# ---------- Part 3: Census ACS income + poverty (whole state) ----------
resp = requests.get(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                    params={"get": "B19013_001E,B17001_002E,B17001_001E",
                            "for": "tract:*", "in": f"state:{STATE} county:*",
                            "key": CENSUS_KEY}, timeout=120)
resp.raise_for_status()
data = resp.json()
acs = pd.DataFrame(data[1:], columns=data[0])
acs["tract_geoid"] = acs["state"] + acs["county"] + acs["tract"]
acs["median_hh_income"] = pd.to_numeric(acs["B19013_001E"], errors="coerce")
acs["poverty_rate_pct"] = (pd.to_numeric(acs["B17001_002E"], errors="coerce")
                           / pd.to_numeric(acs["B17001_001E"], errors="coerce") * 100)
acs = acs[["tract_geoid", "median_hh_income", "poverty_rate_pct"]]

base = places.merge(acs, on="tract_geoid", how="outer")
base = base[base["tract_geoid"].isin(rural_ids)]
base.to_csv(PROCESSED / "places_acs.csv", index=False)
print("Rural tracts with PLACES + ACS:", len(base))


# ---------- Part 4: tract boundaries (rural tracts only) ----------
tracts = gpd.read_file(f"https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_{STATE}_tract.zip")
tracts = tracts[tracts["GEOID"].isin(rural_ids)][["GEOID", "NAME", "geometry"]]
tracts.to_file(PROCESSED / "tracts.geojson", driver="GeoJSON")
print("Rural tract boundaries:", len(tracts))


# ---------- Part 5: store mix within 10 miles (USDA SNAP retailers) ----------
files = sorted((ROOT / "data" / "raw").glob("Historical SNAP Retailer Locator Data*.csv"))
if not files:
    raise SystemExit("SNAP retailer CSV not found in data/raw/ (see src/05b_snap_store_features.py).")
snap = pd.read_csv(files[-1], usecols=["Store Type", "Latitude", "Longitude",
                                       "Authorization Date", "End Date"], low_memory=False)
snap.columns = ["type", "lat", "lon", "start", "end"]

# keep stores inside Virginia's box plus a margin, so border tracts see stores in nearby states
minx, miny, maxx, maxy = tracts.to_crs("EPSG:4326").total_bounds
snap = snap[snap["lat"].between(miny - 0.3, maxy + 0.3) & snap["lon"].between(minx - 0.3, maxx + 0.3)].copy()
snap["start"] = pd.to_datetime(snap["start"], errors="coerce")
snap["end"] = pd.to_datetime(snap["end"].astype(str).str.strip().replace({"": None, "nan": None}),
                             errors="coerce")
open_ref = (snap["start"] <= REF_DATE) & (snap["end"].isna() | (snap["end"] > REF_DATE))
closed = (snap["end"] > CLOSURE_START) & (snap["end"] <= REF_DATE) & snap["type"].isin(FULL_SERVICE)

utm = tracts.estimate_utm_crs()
tr = tracts.to_crs(utm)
centers = tr.geometry.centroid
stores = gpd.GeoDataFrame(snap, geometry=gpd.points_from_xy(snap["lon"], snap["lat"]),
                          crs="EPSG:4326").to_crs(utm)
now = stores[open_ref]
full = now[now["type"].isin(FULL_SERVICE)]
limited = now[now["type"].isin(LIMITED)]
gone = stores[closed]
print("SNAP stores open on", REF_DATE.date(), ":", len(now))

rows = []
for geoid, c in zip(tr["GEOID"], centers):
    n_all = int((now.distance(c) <= RADIUS).sum())
    n_lim = int((limited.distance(c) <= RADIUS).sum())
    rows.append({
        "tract_geoid": str(geoid),
        "snap_stores_10mi": n_all,
        "full_service_10mi": int((full.distance(c) <= RADIUS).sum()),
        "limited_10mi": n_lim,
        "limited_share": n_lim / n_all if n_all else np.nan,
        "dist_full_service_km": full.distance(c).min() / 1000,
        "full_service_closures_5yr": int((gone.distance(c) <= RADIUS).sum()),
    })
stores_feat = pd.DataFrame(rows)
stores_feat.rename(columns={"tract_geoid": "GEOID"}).to_csv(PROCESSED / "store_features.csv", index=False)


# ---------- Part 6: master table (same columns the other cities use) ----------
base["median_hh_income"] = base["median_hh_income"].replace(ACS_MISSING_CODES, np.nan)
f = fara.rename(columns={"CensusTract20": "tract_geoid"})
f = f[["tract_geoid", "POP2020", "PCTGQTRS",
       "DD_SRAM_lapop10share", "DD_SRAM_lahunv10share", "DD_SRAM_lasnap10share"]]
master = base.merge(f, on="tract_geoid", how="left")
master["access_distance"] = master["DD_SRAM_lapop10share"]
master["vehicle_gap"] = master["DD_SRAM_lahunv10share"]
master["affordability_proxy"] = master["DD_SRAM_lasnap10share"]
master = master.merge(stores_feat, on="tract_geoid", how="left")
master["log_income"] = np.log(master["median_hh_income"])
master.to_csv(PROCESSED / "master_tract_table.csv", index=False)

print("Wrote", PROCESSED / "master_tract_table.csv", "-", len(master), "tracts")
print(master[["obesity_pct", "access_distance", "affordability_proxy",
              "limited_share", "dist_full_service_km"]].describe().round(2))
