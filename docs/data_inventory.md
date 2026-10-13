# Data inventory - Richmond, VA pilot

Pilot area: Richmond city, Virginia (independent city, county FIPS `51760`, state FIPS `51`).
75 census tracts using 2020 boundaries.

## Sources

| Source | What we use | Release | How we get it | Script |
|---|---|---|---|---|
| CDC PLACES, census tract data | obesity and diabetes prevalence (outcomes) | 2025 release, based on 2023 BRFSS | Socrata API, dataset `cwsq-ngmh`, filtered on `countyfips='51760'` | `src/01_pull_places_acs.py` |
| Census ACS 5-year | median household income, poverty rate (controls) | 2019-2023 | Census API (needs free key) | `src/01_pull_places_acs.py` |
| Census ACS 5-year | household internet access (table B28002) | 2020-2024 | Census API | `src/03_download_osm_internet.py` |
| USDA Food Access Research Atlas (FARA) | driving distance to SNAP stores, no-vehicle households, SNAP households | 2025 release (SNAP retailers as of June 2025, 2020 tracts) | manual Excel download from ERS, no API | `src/02_extract_fara.py` |
| OpenStreetMap | fast food, restaurant and grocery locations | live | `osmnx` | `src/03_download_osm_internet.py` |
| Census TIGER/Line | 2020 tract boundaries | 2020 | direct download | `src/03_download_osm_internet.py` |

Possible later additions: USDA Food Environment Atlas (county level only, so less useful for tracts) and Google Places as a cross-check on OSM store categories (paid API).

## Data quality notes

1. **Different time windows.** PLACES uses 2023 BRFSS, the ACS controls are 2019-2023, and FARA reflects June 2025 retailers. Close, but not the same period.
2. **FARA tract vintage.** The 2019 FARA release used 2010 tracts and only 57 Richmond tracts matched. The 2025 release uses 2020 tracts, so all 75 match.
3. **Missing ACS values.** The Census API returns -666666666 when it has no estimate. One tract has this for income and is dropped from the models, along with tracts that are more than 50% group quarters.
4. **PLACES is model-based.** The tract values are small-area estimates that already use ACS demographics, which probably inflates the R² of the income-only model.
5. **Store lists lag.** FARA and OSM won't catch recent openings or closures, and OSM coverage depends on volunteer mapping.
6. **No affordability data.** There's no free food-price data at tract level. For now we use SNAP households far from a store as a proxy.
