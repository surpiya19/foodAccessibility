# FoodPrint Score - step 3: tract boundaries, OSM food places, ACS internet access
# Usage: python src/03_download_osm_internet.py [region]
# Before running, create a file named .env in the repo root with one line:
#   CENSUS_KEY=your_key_here
# (.env is listed in .gitignore, so the key is never uploaded to GitHub)
# After running, you will get 3 files in data/processed/<region>/:
#   tracts.geojson            census tract boundaries
#   osm_food_places.csv       locations of fast food / grocery / restaurants
#   acs_internet.csv          share of households with internet, per tract

import os
import requests
import pandas as pd
import geopandas as gpd
import osmnx as ox
from dotenv import load_dotenv

from regions import ROOT, get_region

REGION = get_region()
PROCESSED = REGION["processed"]
STATE_FIPS = REGION["state"]
COUNTY_FIPS = REGION["county"]

# Census API key (free): sign up at https://api.census.gov/data/key_signup.html
# The key is read from the .env file, so it is not written in this script
load_dotenv(ROOT / ".env")
CENSUS_KEY = os.getenv("CENSUS_KEY")

# Stop early with a clear message if the key is missing
if CENSUS_KEY is None:
    raise SystemExit("CENSUS_KEY not found. Copy .env.example to .env and add your key.")


# ---------- Part 1: tract boundaries ----------
# Census 2020 tract boundary file for the whole state
tract_url = f"https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_{STATE_FIPS}_tract.zip"
tracts = gpd.read_file(tract_url)

# Keep only our county
tracts = tracts[tracts["COUNTYFP"] == COUNTY_FIPS]

# Keep only the columns we need: GEOID is the 11-digit tract ID
tracts = tracts[["GEOID", "NAME", "geometry"]]
tracts.to_file(PROCESSED / "tracts.geojson", driver="GeoJSON")
print("Number of tracts:", len(tracts))


# ---------- Part 2: OpenStreetMap food places ----------
# Download places within 20 km of downtown
# (wider than the city, because places just outside the city limits
#  still affect people living inside the city)
center = REGION["center"]     # (latitude, longitude)
distance = 20000              # in meters

tags = {
    "amenity": ["fast_food", "restaurant"],
    "shop": ["supermarket", "grocery", "greengrocer"],
}
places = ox.features_from_point(center, tags, dist=distance)

# Some places are mapped as a point, others as a building outline
# Take one representative point for each, to get latitude and longitude
points = places.geometry.representative_point()
places["lon"] = points.x
places["lat"] = points.y

# Make sure these columns exist (fill with empty values if missing)
for col in ["name", "amenity", "shop"]:
    if col not in places.columns:
        places[col] = None

# Assign a category to each place
places["category"] = "restaurant"
places.loc[places["amenity"] == "fast_food", "category"] = "fast_food"
places.loc[places["shop"].notna(), "category"] = "grocery"

places = places[["name", "category", "amenity", "shop", "lat", "lon"]]
places.to_csv(PROCESSED / "osm_food_places.csv", index=False)
print("Total number of places:", len(places))
print(places["category"].value_counts())


# ---------- Part 3: ACS household internet access ----------
# Table B28002: B28002_001E = total households,
#               B28002_013E = households with no internet access
acs_url = (
    "https://api.census.gov/data/2024/acs/acs5"
    "?get=B28002_001E,B28002_013E"
    "&for=tract:*"
    "&in=state:" + STATE_FIPS + "%20county:" + COUNTY_FIPS
    + "&key=" + CENSUS_KEY
)
data = requests.get(acs_url).json()

# The first row is the column names, the rest is the data
acs = pd.DataFrame(data[1:], columns=data[0])

# Build the 11-digit GEOID (state 2 digits + county 3 digits + tract 6 digits)
# Keep it as text, not a number
acs["GEOID"] = acs["state"] + acs["county"] + acs["tract"]

acs["households"] = acs["B28002_001E"].astype(float)
acs["no_internet"] = acs["B28002_013E"].astype(float)
acs["internet_share"] = 1 - acs["no_internet"] / acs["households"]

acs = acs[["GEOID", "households", "no_internet", "internet_share"]]
acs.to_csv(PROCESSED / "acs_internet.csv", index=False)
print("Number of ACS tracts:", len(acs))
