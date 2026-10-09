# FoodPrint Score - step 2: clean the data (Richmond city, Virginia)
# Run download_data.py first. This script reads:
#   osm_food_places.csv
# It writes:
#   osm_food_places_clean.csv   cleaned list of food places
# Next step: build_features.py

import pandas as pd


# ---------- Part 1: read the file ----------
places = pd.read_csv("osm_food_places.csv")
print("Places before cleaning:", len(places))


# ---------- Part 2: fix the categories ----------
# The download script labeled every place with any "shop" tag as grocery,
# which wrongly included bakeries, snack shops, etc.
# New rule:
#   shop is supermarket / grocery / greengrocer  -> grocery
#   otherwise amenity is fast_food               -> fast_food
#   otherwise amenity is restaurant              -> restaurant
#   anything else                                -> removed
grocery_shops = ["supermarket", "grocery", "greengrocer"]

places["category"] = "other"
places.loc[places["amenity"] == "restaurant", "category"] = "restaurant"
places.loc[places["amenity"] == "fast_food", "category"] = "fast_food"
places.loc[places["shop"].isin(grocery_shops), "category"] = "grocery"

places = places[places["category"] != "other"]
print("Places after fixing categories:", len(places))


# ---------- Part 3: remove places without a location ----------
places = places.dropna(subset=["lat", "lon"])
print("Places after removing missing locations:", len(places))


# ---------- Part 4: remove duplicates ----------
# Same name, same category, almost the same location
# (rounding to 3 decimals is about 100 meters)
places["lat_round"] = places["lat"].round(3)
places["lon_round"] = places["lon"].round(3)
places = places.drop_duplicates(subset=["name", "category", "lat_round", "lon_round"])
places = places.drop(columns=["lat_round", "lon_round"])
print("Places after removing duplicates:", len(places))


# ---------- Part 5: check and save ----------
print(places["category"].value_counts())
places.to_csv("osm_food_places_clean.csv", index=False)
