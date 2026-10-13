# FoodPrint Score

A census-tract-level score that shows where food-access investment is most likely to reduce obesity risk, **beyond what income and poverty already explain**. Pilot: Richmond city, Virginia (75 census tracts, 2020 boundaries). Test cities: Baltimore, Maryland (199 tracts) and Washington, DC (206 tracts).

## Repo layout

```
src/                 the pipeline, run in order
  regions.py                 study areas (FIPS codes, map center)
  01_pull_places_acs.py      CDC PLACES obesity/diabetes + Census ACS income/poverty   (needs internet + key)
  02_extract_fara.py         Richmond rows from the USDA Food Access Research Atlas    (offline)
  03_download_osm_internet.py  tract boundaries, OpenStreetMap food places, ACS internet (needs internet + key)
  04_clean_osm.py            fix store categories, drop duplicates
  05_build_features.py       fast-food ratio + delivery-access proxy per tract
  05b_snap_store_features.py store-type mix + distance to full-service store (USDA SNAP retailers)
  06_score_and_validate.py   build the score, test it against income, rank tracts
  07_robustness_and_figures.py  robustness checks, spatial check, figures
  08_transfer_test.py        compare score versions across cities
  09_store_type_test.py      store-type score: select on Richmond + Baltimore, test on a held-out city (DC)
data/
  raw/               large downloads, not in git (FARA Excel)
  processed/<city>/  small tract-level tables produced by the pipeline
outputs/<city>/      ranked tract list, validation and robustness results, figures/
outputs/transfer/    cross-city comparison
docs/                data inventory, transfer test plan (slides and Word drafts stay local)
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your free Census API key
python src/01_pull_places_acs.py richmond
python src/02_extract_fara.py richmond      # needs data/raw/2025-sram-fara-data.xlsx (see the script)
python src/03_download_osm_internet.py richmond
python src/04_clean_osm.py richmond
python src/05_build_features.py richmond
python src/06_score_and_validate.py richmond
python src/07_robustness_and_figures.py richmond
```

Every script takes the city as its argument (`richmond` or `baltimore`, see `src/regions.py`). After running both cities:

```bash
python src/08_transfer_test.py richmond baltimore
```

Steps 1, 2 and 6 are enough to reproduce the current results; the processed tables are committed, so step 6 runs on its own. Steps 3-5 add the OpenStreetMap features, and step 6 picks them up automatically when `data/processed/<city>/construct_features.csv` exists.

## Method

1. **Construct** features, each oriented so higher = worse food environment: fast-food share of nearby outlets, delivery-access proxy, share of people more than 1/2 mile (driving) from a SNAP store, households without a car and far from a store, and SNAP households far from a store (an affordability proxy until price data is collected).
2. **Score**: equal-weight average of z-scores, rescaled 0-100.
3. **Validate**: compare `outcome ~ poverty + log(income)` against the same model plus the score, for obesity and diabetes (robust standard errors, nested F-test, leave-one-out error).
4. **Rank**: priority tracts have an above-median score *and* more obesity than income predicts.

Results are in [`outputs/richmond/validation_results.md`](outputs/richmond/validation_results.md) and [`outputs/richmond/robustness_results.md`](outputs/richmond/robustness_results.md), with figures in `outputs/richmond/figures/`. Test plans: [`docs/transfer_test_plan.md`](docs/transfer_test_plan.md) (Baltimore) and [`docs/store_type_test_plan.md`](docs/store_type_test_plan.md) (held-out city).

## Data sources

| Source | Use | Vintage |
|---|---|---|
| CDC PLACES (tract) | obesity, diabetes outcomes | 2025 release (2023 BRFSS) |
| Census ACS 5-year | income, poverty, internet access | 2019-2023 / 2020-2024 |
| USDA Food Access Research Atlas | distance to SNAP stores, vehicle access, SNAP | 2025 release (June 2025 retailers) |
| OpenStreetMap | fast food, restaurant, grocery locations | live |
| USDA SNAP retailer locator (historical) | store type, location, open/close dates | 2005-2025 (stores open mid-2023 used) |

More detail and known data-quality issues: [`docs/data_inventory.md`](docs/data_inventory.md).

This is a prioritization tool, not a causal or diagnostic claim.
