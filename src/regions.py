# Study areas. Every script takes the region name as its first argument:
#   python src/01_pull_places_acs.py baltimore
# Default is richmond. Each region gets its own data/processed/<region>/ and outputs/<region>/.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REGIONS = {
    "richmond": {"name": "Richmond, VA", "state": "51", "county": "760",
                 "center": (37.5407, -77.4360)},
    "baltimore": {"name": "Baltimore, MD", "state": "24", "county": "510",
                  "center": (39.2904, -76.6122)},
    "philadelphia": {"name": "Philadelphia, PA", "state": "42", "county": "101",
                     "center": (39.9526, -75.1652)},
    "dc": {"name": "Washington, DC", "state": "11", "county": "001",
           "center": (38.9072, -77.0369)},
    "norfolk": {"name": "Norfolk, VA", "state": "51", "county": "710",
                "center": (36.8508, -76.2859)},
    # county-wide areas (city + suburbs) need a wider store search
    "memphis": {"name": "Memphis (Shelby Co.), TN", "state": "47", "county": "157",
                "center": (35.1495, -90.0490), "store_radius_km": 50},
    "columbus": {"name": "Columbus (Franklin Co.), OH", "state": "39", "county": "049",
                 "center": (39.9612, -82.9988), "store_radius_km": 45},
}


def get_region():
    key = sys.argv[1].lower() if len(sys.argv) > 1 else "richmond"
    if key not in REGIONS:
        raise SystemExit(f"Unknown region '{key}'. Options: {', '.join(REGIONS)}")
    r = dict(REGIONS[key], key=key)
    r["fips"] = r["state"] + r["county"]
    r["processed"] = ROOT / "data" / "processed" / key
    r["outputs"] = ROOT / "outputs" / key
    r["processed"].mkdir(parents=True, exist_ok=True)
    r["outputs"].mkdir(parents=True, exist_ok=True)
    print(f"Region: {r['name']} ({r['fips']})")
    return r
