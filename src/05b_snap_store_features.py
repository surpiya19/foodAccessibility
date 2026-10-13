# FoodPrint Score - step 5b: store-type features from USDA SNAP retailer data
# Usage: python src/05b_snap_store_features.py [region]
#
# Download "Historical SNAP Retailer Locator Data" (CSV) from
#   https://www.fns.usda.gov/snap/retailer-locator/data
# and save it in data/raw/. It lists every SNAP store since 2005 with its type,
# location, and authorization / end dates, so we can see which stores were open
# at a given date.
#
# Reads:  data/raw/Historical SNAP Retailer Locator Data*.csv, data/processed/<region>/tracts.geojson
# Writes: data/processed/<region>/store_features.csv

import numpy as np
import pandas as pd
import geopandas as gpd

from regions import ROOT, get_region

REGION = get_region()
PROCESSED = REGION["processed"]

# Stores open mid-2023, to line up with the 2023 BRFSS behind PLACES
REF_DATE = pd.Timestamp("2023-06-30")
CLOSURE_START = pd.Timestamp("2018-07-01")   # closures counted over the 5 years before REF_DATE
RADIUS = 1609                                # 1 mile, same as the fast-food ratio
DOWNLOAD_KM = REGION.get("store_radius_km", 25)  # keep stores within this distance of downtown

FULL_SERVICE = ["Supermarket", "Super Store", "Large Grocery Store"]
LIMITED = ["Convenience Store", "Combination Grocery/Other", "Small Grocery Store"]
# Medium grocery stores count toward the total but neither group

files = sorted((ROOT / "data" / "raw").glob("Historical SNAP Retailer Locator Data*.csv"))
if not files:
    raise SystemExit("SNAP retailer CSV not found in data/raw/ (see top of this file).")
snap = pd.read_csv(files[-1], usecols=["Store Type", "Latitude", "Longitude",
                                       "Authorization Date", "End Date"], low_memory=False)
snap.columns = ["type", "lat", "lon", "start", "end"]

# keep stores near downtown (rough distance in km)
lat0, lon0 = REGION["center"]
km = np.hypot((snap["lat"] - lat0) * 111, (snap["lon"] - lon0) * 111 * np.cos(np.radians(lat0)))
snap = snap[km <= DOWNLOAD_KM].copy()
snap["start"] = pd.to_datetime(snap["start"], errors="coerce")
snap["end"] = pd.to_datetime(snap["end"].str.strip().replace("", None), errors="coerce")
print("SNAP stores ever within", DOWNLOAD_KM, "km:", len(snap))

open_ref = (snap["start"] <= REF_DATE) & (snap["end"].isna() | (snap["end"] > REF_DATE))
closed = (snap["end"] > CLOSURE_START) & (snap["end"] <= REF_DATE) & snap["type"].isin(FULL_SERVICE)

tracts = gpd.read_file(PROCESSED / "tracts.geojson")
utm = tracts.estimate_utm_crs()
tracts = tracts.to_crs(utm)
centers = tracts.geometry.centroid
stores = gpd.GeoDataFrame(snap, geometry=gpd.points_from_xy(snap["lon"], snap["lat"]), crs="EPSG:4326").to_crs(utm)

now = stores[open_ref]
full = now[now["type"].isin(FULL_SERVICE)]
limited = now[now["type"].isin(LIMITED)]
gone = stores[closed]
print("Open on", REF_DATE.date(), ":", len(now), "| full-service:", len(full), "| limited:", len(limited))

rows = []
for geoid, c in zip(tracts["GEOID"], centers):
    n_full = int((full.distance(c) <= RADIUS).sum())
    n_lim = int((limited.distance(c) <= RADIUS).sum())
    n_all = int((now.distance(c) <= RADIUS).sum())
    rows.append({
        "GEOID": str(geoid),
        "snap_stores_1mi": n_all,
        "full_service_1mi": n_full,
        "limited_1mi": n_lim,
        # share of nearby SNAP stores that are convenience / combination / small grocery
        "limited_share": n_lim / n_all if n_all else np.nan,
        # distance (km) to the nearest supermarket, super store or large grocery
        "dist_full_service_km": full.distance(c).min() / 1000,
        # full-service stores within 1 mile that closed in the 5 years before mid-2023
        "full_service_closures_5yr": int((gone.distance(c) <= RADIUS).sum()),
    })
feat = pd.DataFrame(rows)
print(feat.describe().round(2))
feat.to_csv(PROCESSED / "store_features.csv", index=False)
