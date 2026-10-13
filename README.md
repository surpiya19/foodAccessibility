# FoodPrint Score

A census-tract-level score that shows where food-access investment is most likely to reduce obesity risk, **beyond what income and poverty already explain**. Pilot: Richmond city, Virginia (75 census tracts, 2020 boundaries).

## Repo layout

```
src/                 the pipeline, run in order
  01_pull_places_acs.py      CDC PLACES obesity/diabetes + Census ACS income/poverty   (needs internet + key)
  02_extract_fara.py         Richmond rows from the USDA Food Access Research Atlas    (offline)
  03_download_osm_internet.py  tract boundaries, OpenStreetMap food places, ACS internet (needs internet + key)
  04_clean_osm.py            fix store categories, drop duplicates
  05_build_features.py       fast-food ratio + delivery-access proxy per tract
  06_score_and_validate.py   build the score, test it against income, rank tracts
data/
  raw/               large downloads, not in git (FARA Excel)
  processed/         small tract-level tables produced by the pipeline
outputs/             ranked tract list, validation results, plot
docs/                data inventory (slides and Word drafts stay local)
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your free Census API key
python src/01_pull_places_acs.py
python src/02_extract_fara.py          # needs data/raw/2025-sram-fara-data.xlsx (see the script)
python src/03_download_osm_internet.py
python src/04_clean_osm.py
python src/05_build_features.py
python src/06_score_and_validate.py
```

Steps 1, 2 and 6 are enough to reproduce the current results; the processed tables are committed, so step 6 runs on its own. Steps 3-5 add the OpenStreetMap features, and step 6 picks them up automatically when `data/processed/construct_features.csv` exists.

## Method

1. **Construct** features, each oriented so higher = worse food environment: fast-food share of nearby outlets, delivery-access proxy, share of people more than 1/2 mile (driving) from a SNAP store, households without a car and far from a store, and SNAP households far from a store (an affordability proxy until price data is collected).
2. **Score**: equal-weight average of z-scores, rescaled 0-100.
3. **Validate**: compare `outcome ~ poverty + log(income)` against the same model plus the score, for obesity and diabetes (robust standard errors, nested F-test, leave-one-out error).
4. **Rank**: priority tracts have an above-median score *and* more obesity than income predicts.

Results are in [`outputs/validation_results.md`](outputs/validation_results.md).

## Data sources

| Source | Use | Vintage |
|---|---|---|
| CDC PLACES (tract) | obesity, diabetes outcomes | 2025 release (2023 BRFSS) |
| Census ACS 5-year | income, poverty, internet access | 2019-2023 / 2020-2024 |
| USDA Food Access Research Atlas | distance to SNAP stores, vehicle access, SNAP | 2025 release (June 2025 retailers) |
| OpenStreetMap | fast food, restaurant, grocery locations | live |

More detail and known data-quality issues: [`docs/data_inventory.md`](docs/data_inventory.md).

This is a prioritization tool, not a causal or diagnostic claim.
