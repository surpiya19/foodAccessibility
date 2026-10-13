# FoodPrint Score - step 1: pull health outcomes and income controls (Richmond city, Virginia)
# Replaces the old notebook 02_pull_and_join_richmond_data.ipynb (kept in archive/).
#
# Pulls:
#   CDC PLACES 2025 (tract level): obesity and diabetes prevalence      -> the outcomes
#   Census ACS 5-year:             median household income, poverty rate -> the income controls
# Writes:
#   data/processed/places_acs_richmond.csv   one row per tract (75 tracts)
#
# Needs internet and a free Census API key in .env (CENSUS_KEY=...).
# Get one at https://api.census.gov/data/key_signup.html

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

STATE_FIPS = "51"          # Virginia
COUNTY_FIPS = "760"        # Richmond city (3 digits, no state prefix)
COUNTY_FIPS_FULL = "51760" # as used by PLACES
ACS_YEAR = 2023

load_dotenv(ROOT / ".env")
CENSUS_KEY = os.getenv("CENSUS_KEY")
if CENSUS_KEY is None:
    raise SystemExit("CENSUS_KEY not found. Copy .env.example to .env and add your key.")


def safe_get_json(url, params=None, timeout=60):
    # the Census API sends back an HTML page (not JSON) when the key is bad
    resp = requests.get(url, params=params, timeout=timeout)
    if "json" not in resp.headers.get("Content-Type", "").lower():
        raise RuntimeError(f"Expected JSON from {resp.url} (HTTP {resp.status_code}): "
                           f"{resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()


# ---------- Part 1: CDC PLACES (Socrata API, no key needed) ----------
# Dataset cwsq-ngmh = PLACES Census Tract Data, 2025 release (one row per tract per measure)
data = safe_get_json(
    "https://data.cdc.gov/resource/cwsq-ngmh.json",
    params={
        "$where": f"countyfips='{COUNTY_FIPS_FULL}' AND measureid in('OBESITY','DIABETES')",
        "$limit": 5000,
    },
)
places = pd.DataFrame(data)
places["data_value"] = pd.to_numeric(places["data_value"], errors="coerce")
# long to wide: one row per tract
places = (places.pivot_table(index="locationname", columns="measureid",
                             values="data_value", aggfunc="first")
          .reset_index()
          .rename(columns={"locationname": "tract_geoid",
                           "OBESITY": "obesity_pct", "DIABETES": "diabetes_pct"}))
print("PLACES tracts:", len(places))


# ---------- Part 2: Census ACS income and poverty ----------
# B19013_001E = median household income
# B17001_002E / B17001_001E = people below poverty / people with poverty status known
data = safe_get_json(
    f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
    params={
        "get": "B19013_001E,B17001_002E,B17001_001E",
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
        "key": CENSUS_KEY,
    },
)
acs = pd.DataFrame(data[1:], columns=data[0])
acs["tract_geoid"] = acs["state"] + acs["county"] + acs["tract"]
acs["median_hh_income"] = pd.to_numeric(acs["B19013_001E"], errors="coerce")
acs["poverty_rate_pct"] = (pd.to_numeric(acs["B17001_002E"], errors="coerce")
                           / pd.to_numeric(acs["B17001_001E"], errors="coerce") * 100)
acs = acs[["tract_geoid", "median_hh_income", "poverty_rate_pct"]]
print("ACS tracts:", len(acs))


# ---------- Part 3: join and save ----------
# -666666666 (Census "no estimate") is left in here and set to NaN in step 6
merged = places.merge(acs, on="tract_geoid", how="outer")
print("Joined tracts:", len(merged), "(expect 75)")
PROCESSED.mkdir(parents=True, exist_ok=True)
merged.to_csv(PROCESSED / "places_acs_richmond.csv", index=False)
