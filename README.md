# How much does a grocery basket really cost in Mexico?

A data pipeline that turns Profeco's public retail price data into answers anyone can use: **where is my grocery list cheapest, and how much have prices really gone up?**

> **Status:** 🚧 In progress. Data exploration and scope are done; the pipeline is being designed. See the [roadmap](#roadmap).

## The problem

Every two weeks, Mexico's consumer protection agency (Profeco) publishes hundreds of thousands of retail prices through its *Quién es Quién en los Precios* program. The data is public, but it is hard to use:

- One file per fortnight, **~666,000 rows and ~590 MB in memory**, published months after the prices were collected.
- **No product or store IDs.** Products and stores must be identified by combining several free-text columns.
- **Free-text product sizes** (`"Bolsa 20+2 Piezas. 561 Gr."`, `"Paquete C/18 Blanco"`), so prices cannot be compared directly.
- **The same price appears in more than one catalog**, which double-counts it in averages.

This project builds a pipeline that ingests, cleans and models that data so the questions above can be answered reliably.

## Questions it will answer

1. Which store chain has the cheapest basket in Mexico City?
2. How do supermarkets compare with traditional markets (*mercados*)?
3. How has the price of each product changed across 2026?
4. Did my basket go up more or less than official inflation?

## Scope (v1)

| Decision | Choice |
| --- | --- |
| Data | Profeco *Quién es Quién en los Precios*, open data from datos.gob.mx |
| Period | All 2026 fortnights |
| Geography | Whole country stored; analysis focused on Mexico City |
| Catalogs | Basic goods, fruits and vegetables, markets, fish and seafood, PACIC |
| Basket | 15 everyday products with a fixed size (eggs, milk, tortillas, beans, rice, oil, sugar, pasta, sliced bread, tuna, chicken, tomato, onion, potato, banana) |

v2 will normalize product sizes to compare prices per kilo or liter.

## Key findings so far

From exploring the first fortnight of July 2026 (full notes in [`docs/exploration_notes.md`](docs/exploration_notes.md)):

- **Text search is unreliable:** searching "pan" (bread) returns panty liners and panela cheese; "papa" (potato) returns papaya.
- **The same product is split by spelling:** `Spaghetti No. 5` and `Spaghetti` are likely the same item, which skews any "most common" metric.
- **9,846 rows are duplicated across catalogs.**
- **31% of rows have no brand** (`S/M`): technically filled, effectively null.
- **Store coordinates are sometimes wrong:** two Mega Soriana branches 12 km apart share the same coordinates.
- **The mean price ($556 MXN) is misleading**, inflated by TVs and appliances; the median is $59.90.

## Roadmap

- [x] Explore the source data and document its problems
- [x] Define scope and the v1 basket
- [x] Design the architecture (layers, keys, deduplication) → [`docs/architecture.md`](docs/architecture.md)
- [x] Validate the store key against the data
- [ ] Load raw data into PostgreSQL running in Docker
- [ ] Build the clean and analytical layers (star schema)
- [ ] Incremental loads per fortnight
- [ ] Automated data quality checks
- [ ] Orchestration
- [ ] Public dashboard
- [ ] v2: normalize product sizes (price per kg/L)

## Planned architecture

```
datos.gob.mx  →  raw  →  clean  →  analytics  →  dashboard
 (CSV files)     (as-is)  (typed,     (star
                          deduped)    schema)
```

Details and the evidence behind each decision: [`docs/architecture.md`](docs/architecture.md).

Tools: Python (pandas), PostgreSQL, Docker. More will be added only when there is a concrete reason to.

## Repository structure

```
├── data/raw/              # source CSVs (not versioned, see below)
├── docs/
│   ├── exploration_notes.md   # data profiling findings and scope decisions
│   └── architecture.md        # layers, keys, deduplication, data quality rules
├── scripts/
│   ├── explorar_datos.py      # data profiling: nulls, duplicates, dates, prices
│   ├── canasta.py             # picks the v1 basket from the data
│   └── validate_store_key.py  # tests the store key against merge/split risks
└── README.md
```

## How to run it

1. Download a fortnight file from the *Programa Quién es quién en los precios* dataset on datos.gob.mx.
2. Save it as `data/raw/prueba01.csv`.
3. Install dependencies and run:

```bash
pip install pandas
python scripts/explorar_datos.py
python scripts/canasta.py
python scripts/validate_store_key.py
```

Data files are not included in the repository: they are hundreds of MB each and are published by Profeco.

## Author

**Armando Antillón Pérez** · Computer Engineer (UNAM) · [LinkedIn](https://www.linkedin.com/in/armando-antillon-perez-98741b287)
