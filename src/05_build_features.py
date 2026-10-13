# FoodPrint Score - step 5: build the CONSTRUCT indicators (Richmond city, Virginia)
# Run 03_download_osm_internet.py and 04_clean_osm.py first. This script reads (from data/processed/):
#   richmond_tracts.geojson, osm_food_places_clean.csv, acs_internet.csv
# It writes:
#   construct_features.csv   one row per tract, with the two indicators:
#                            fast_food_ratio and delivery_proxy

import pandas as pd
import geopandas as gpd
from pathlib import Path

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


RATIO_RADIUS = 1609     # 1 mile in meters, used for the fast-food:grocery ratio
DELIVERY_RADIUS = 5000  # 5 km in meters, used for the delivery-access proxy


# ---------- Part 1: read the files ----------
# Read GEOID as text so the 11-digit ID is not turned into a number
tracts = gpd.read_file(PROCESSED / "richmond_tracts.geojson")
places = pd.read_csv(PROCESSED / "osm_food_places_clean.csv")
acs = pd.read_csv(PROCESSED / "acs_internet.csv", dtype={"GEOID": str})

print("Tracts:", len(tracts))
print("Places:", len(places))


# ---------- Part 2: prepare the map data ----------
# Turn the places table into map points
places_map = gpd.GeoDataFrame(
    places,
    geometry=gpd.points_from_xy(places["lon"], places["lat"]),
    crs="EPSG:4326",
)

# Convert both layers to a coordinate system measured in meters
# (EPSG:32618 = UTM zone 18N, which covers Virginia)
# so that distances come out in meters
tracts = tracts.to_crs("EPSG:32618")
places_map = places_map.to_crs("EPSG:32618")

# Center point of each tract
tracts["center"] = tracts.geometry.centroid

# Split the places by category
fast_food = places_map[places_map["category"] == "fast_food"]
grocery = places_map[places_map["category"] == "grocery"]
# Restaurants and fast food together = places that could deliver
eating = places_map[places_map["category"] != "grocery"]


# ---------- Part 3: count places around each tract ----------
# We count places near the tract center instead of inside the tract,
# because tracts are small and most have no store inside their borders
ff_counts = []
groc_counts = []
eat_counts = []

for center in tracts["center"]:
    # Distance in meters from this tract center to every place
    ff_dist = fast_food.distance(center)
    groc_dist = grocery.distance(center)
    eat_dist = eating.distance(center)

    # Count how many are within the radius
    ff_counts.append((ff_dist <= RATIO_RADIUS).sum())
    groc_counts.append((groc_dist <= RATIO_RADIUS).sum())
    eat_counts.append((eat_dist <= DELIVERY_RADIUS).sum())

tracts["ff_count_1mi"] = ff_counts
tracts["groc_count_1mi"] = groc_counts
tracts["restaurants_5km"] = eat_counts


# ---------- Part 4: indicator 1, fast-food ratio ----------
# Fast-food share of nearby food outlets (0 to 1)
# Closer to 1 = fast food dominates. We use ff / (ff + grocery) instead of
# ff / grocery so that tracts with 0 grocery stores do not divide by zero.
total = tracts["ff_count_1mi"] + tracts["groc_count_1mi"]
tracts["fast_food_ratio"] = tracts["ff_count_1mi"] / total
# If a tract has no fast food and no grocery nearby, total is 0 and the
# ratio becomes empty (NaN). We leave it empty on purpose, not 0.


# ---------- Part 5: indicator 2, delivery-access proxy ----------
# Merge in the internet share by GEOID, then multiply
features = tracts[["GEOID", "ff_count_1mi", "groc_count_1mi",
                   "fast_food_ratio", "restaurants_5km"]]
features = features.merge(acs[["GEOID", "internet_share"]], on="GEOID", how="left")
features["delivery_proxy"] = features["restaurants_5km"] * features["internet_share"]


# ---------- Part 6: check and save ----------
print("Rows in final table:", len(features))
print("Missing values in each column:")
print(features.isna().sum())
print(features[["fast_food_ratio", "delivery_proxy"]].describe())

features.to_csv(PROCESSED / "construct_features.csv", index=False)
