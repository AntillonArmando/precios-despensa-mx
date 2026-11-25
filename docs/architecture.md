# Architecture

Design of the pipeline, the decisions behind it and the evidence that supports each one.

## Layers

```
 Profeco CSV  →   RAW            →   CLEAN              →   ANALYTICS
                  as received        typed, normalized,     star schema,
                                     deduplicated           ready for questions
```

### `raw`: as received

- Every row of every file, unchanged: **whole country, all catalogs**.
- **All columns stored as text**, so a malformed value never breaks the load. Problems are detected in the next layer.
- Two control columns on every row: `source_file` and `loaded_at`. Any value can be traced back to the file it came from.
- **Grain:** one row of a source CSV.

### `clean`: typed, normalized, deduplicated

- Correct types: price as numeric, date as date.
- Normalized text: lowercase comparisons, no accents, no extra spaces.
- Cross-catalog duplicates removed (see [Deduplication](#deduplication-across-catalogs)).
- Store identity built here (see [Store key](#store-key)).
- **Grain:** one price, of one product, in one store, on one date. No duplicates.

### `analytics`: star schema

```
                 dim_product
                      │
  dim_date ─── fact_price ─── dim_store
                      │
                 basket_v1
```

| Table | Contents |
| --- | --- |
| `fact_price` | One row per price, with keys to each dimension |
| `dim_product` | Product name, size (presentation), brand, category |
| `dim_store` | Chain, store name, address, municipality, state, coordinates, store type |
| `dim_date` | Date, fortnight, month, year |
| `basket_v1` | The 15 products in the v1 basket, with their exact size |

A star schema stores each store's details once instead of repeating them on thousands of price rows, and keeps analytical queries simple. Changing the basket only changes `basket_v1`.

## Store key

The source data has **no store ID**.

**Natural key:** `chain + store name + address + municipality + state`, each normalized before joining.

**Surrogate key:** `store_id` = first 12 characters of the MD5 hash of the natural key. The same store gets the same ID in every fortnight, and other tables reference a short ID instead of five text columns.

**Coordinates are not part of the key.** See the evidence below.

### Validation (first fortnight of July 2026)

Script: [`scripts/validate_store_key.py`](../scripts/validate_store_key.py)

| Check | Result |
| --- | --- |
| Stores identified | 1,779 |
| Hash collisions | 0 |
| Stores merged by text normalization | 0 (text is consistent within one file) |
| **Risk A:** one key, coordinates > ~100 m apart (two stores merged) | **0** |
| **Risk B:** same chain and coordinates, different keys (one store split) | 25 locations, **0 real splits** |

The 25 Risk B cases, by chain:

| Chain | Cases | Explanation |
| --- | --- | --- |
| Central de Abasto | 14 | Different stalls inside the same wholesale market |
| Tortillerías Tradicionales | 7 | Different tortilla shops, mostly inside the same market |
| Mercado Público | 2 | Different stalls inside the same market |
| Mega Soriana | 1 | Two different branches **with the same coordinates** |
| Pescados y Mariscos Miguel Hidalgo | 1 | Two fish shops inside the same market |

### Finding: coordinates are sometimes wrong

Coordinates are not only imprecise in markets (where every stall gets the market's location). **Some are assigned to the wrong store:**

- **Mega Soriana La Viga** (Iztapalapa) has the same coordinates as **Mega Soriana Tacuba** (Miguel Hidalgo), about 12 km away. The point is in Tacuba.
- **Tortillería Lupita** (Iztapalapa, Mexico City) has the same coordinates as **Tortillería Xitle** (Ecatepec, State of Mexico). The point is in Ecatepec.

**Consequences:**

1. Coordinates are a store attribute, never part of its identity.
2. A data quality rule will flag coordinates that are inconsistent with the declared municipality.
3. Flagged stores are excluded from any map.

### Pending

- **Splits across fortnights:** a store whose address is written differently in another file would get a new ID. To be checked when more files are loaded.
- **Generic names:** stores like `tortilleria sin nombre` rely entirely on the address to be told apart.

## Deduplication across catalogs

**Problem:** 9,846 rows are identical except for `catalogo`. The same price appears, for example, in both `Básicos` and `PACIC`.

**Decision:** keep **one row per price** and add an `is_pacic` flag.

| Option | Problem |
| --- | --- |
| Keep both rows | Double-counts prices in every average |
| Drop the duplicate | Loses the fact that the product is part of PACIC |
| **One row + `is_pacic` flag** | Nothing lost, nothing double-counted |

**Data quality rule:** same product, store and date with **different prices** in two catalogs is a conflict, not a duplicate. It is counted and reported, never resolved silently.

## Idempotent loads

Loading the same fortnight twice must leave exactly the same result as loading it once.

1. **Load control table:** which files were loaded, when, and how many rows each had.
2. **Reloading a file:** delete that file's rows from `raw` (using `source_file`), then insert again.
3. **Both steps in one transaction:** a failed load never leaves a half-deleted file.
4. **Safety net:** a unique constraint on the natural key of a price in `clean`. Duplicates are rejected by the database instead of stored silently.

## Data quality rules (so far)

| Rule | Layer | Origin |
| --- | --- | --- |
| Completeness of key columns ≥ 95% per file | raw | Standard practice |
| No price ≤ 0 | clean | Exploration |
| Same product, store and date with different prices across catalogs | clean | Deduplication |
| Coordinates inconsistent with the declared municipality | clean | Store key validation |
| Store present in one fortnight and missing in the next | clean | Pending (splits across fortnights) |
