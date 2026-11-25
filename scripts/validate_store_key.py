"""
Validate the proposed natural key for stores.

The source data has no store ID. The hypothesis is that a store can be
identified by: chain + store name + address + municipality + state.

This script tests that hypothesis against two risks:
  A) Two different stores MERGED into one key
     (same key, but coordinates far apart).
  B) One store SPLIT into several keys
     (same chain and same coordinates, but different keys,
     usually because the address was written differently).

Usage (from the project root):
    python scripts/validate_store_key.py
"""

import hashlib
import unicodedata
from pathlib import Path

import pandas as pd

# --- Configuration ----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "prueba01.csv"

KEY_COLUMNS = ["cadena_comercial", "nombre_comercial", "direccion", "municipio", "estado"]

# 0.001 degrees is roughly 100 meters. If the same key has coordinates further
# apart than this, it is probably two different stores sharing one key.
MAX_COORD_SPREAD = 0.001

# Rounding coordinates to 4 decimals groups points within roughly 10 meters.
COORD_DECIMALS = 4

EXAMPLES_TO_SHOW = 5

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)


def section(title):
    """Print a header to separate each part of the output."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def normalize(text):
    """
    Make text comparable: lowercase, no accents, no extra spaces.
    'Gustavo a.  Madero ' and 'GUSTAVO A. MADERO' become the same string.
    """
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    # NFKD splits 'á' into 'a' + accent mark; then we drop the accent marks.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # Collapse any run of spaces, tabs or newlines into a single space.
    return " ".join(text.split())


def make_store_id(natural_key):
    """
    Turn the long natural key into a short, stable ID.
    The same text always produces the same ID, in every fortnight.
    """
    return hashlib.md5(natural_key.encode("utf-8")).hexdigest()[:12]


# --- Load -------------------------------------------------------------------

columns_needed = KEY_COLUMNS + ["latitud", "longitud", "giro"]
df = pd.read_csv(FILE_PATH, encoding="utf-8-sig", usecols=columns_needed)

# --- 1. Build the key ---------------------------------------------------------
section("1. Building the store key")

# Raw key: columns joined as they come, without cleaning.
df["raw_key"] = df[KEY_COLUMNS].astype(str).agg("|".join, axis=1)

# Normalized key: every column cleaned first, then joined.
normalized = df[KEY_COLUMNS].apply(lambda column: column.map(normalize))
df["store_key"] = normalized.agg("|".join, axis=1)
df["store_id"] = df["store_key"].map(make_store_id)

raw_stores = df["raw_key"].nunique()
clean_stores = df["store_key"].nunique()
print(f"Rows: {len(df):,}")
print(f"Distinct stores with the raw key:        {raw_stores:,}")
print(f"Distinct stores with the normalized key: {clean_stores:,}")
print(f"Stores merged by normalization:          {raw_stores - clean_stores:,}")

ids_per_key = df.groupby("store_id")["store_key"].nunique()
print(f"Hash collisions (two keys, same ID):     {(ids_per_key > 1).sum():,}  (must be 0)")

# --- 2. One row per store -----------------------------------------------------
section("2. Store summary")

stores = df.groupby("store_id").agg(
    store_key=("store_key", "first"),
    chain=("cadena_comercial", "first"),
    store_type=("giro", "first"),
    state=("estado", "first"),
    rows=("store_key", "size"),
    lat_min=("latitud", "min"),
    lat_max=("latitud", "max"),
    lon_min=("longitud", "min"),
    lon_max=("longitud", "max"),
)
stores["lat_spread"] = stores["lat_max"] - stores["lat_min"]
stores["lon_spread"] = stores["lon_max"] - stores["lon_min"]

no_coords = stores["lat_min"].isna().sum()
print(f"Stores: {len(stores):,}")
print(f"Stores without coordinates: {no_coords:,}")
print("\nStores by type (giro):")
print(stores["store_type"].value_counts().to_string())
print(f"\nStores in Mexico City: {(stores['state'] == 'Ciudad de México').sum():,}")

# --- 3. Risk A: two stores merged into one key -------------------------------
section("3. Risk A: one key, coordinates far apart (possible MERGE)")

merged = stores[
    (stores["lat_spread"] > MAX_COORD_SPREAD) | (stores["lon_spread"] > MAX_COORD_SPREAD)
]
print(f"Keys with coordinates more than ~100 m apart: {len(merged):,} of {len(stores):,}")
if len(merged) > 0:
    print("\nExamples:")
    columns = ["chain", "store_key", "rows", "lat_spread", "lon_spread"]
    print(merged.sort_values("rows", ascending=False)[columns].head(EXAMPLES_TO_SHOW).to_string())

# --- 4. Risk B: one store split into several keys ----------------------------
section("4. Risk B: same chain and location, different keys (possible SPLIT)")

with_coords = df.dropna(subset=["latitud", "longitud"]).copy()
with_coords["lat_round"] = with_coords["latitud"].round(COORD_DECIMALS)
with_coords["lon_round"] = with_coords["longitud"].round(COORD_DECIMALS)

locations = with_coords.groupby(["cadena_comercial", "lat_round", "lon_round"]).agg(
    keys=("store_key", "nunique"),
    addresses=("direccion", lambda values: sorted(values.unique())),
)
split = locations[locations["keys"] > 1]
print(f"Locations (chain + coordinates) with more than one key: {len(split):,}")
if len(split) > 0:
    print("\nSplit locations by chain:")
    print(split.index.get_level_values("cadena_comercial").value_counts().to_string())
    print("\nExamples (look at how the addresses differ):")
    for (chain, lat, lon), row in split.head(EXAMPLES_TO_SHOW).iterrows():
        print(f"\n  {chain} at ({lat}, {lon}): {row['keys']} keys")
        for address in row["addresses"]:
            print(f"    - {address}")

# --- 5. Verdict ---------------------------------------------------------------
section("5. Summary")
print(f"Stores identified:            {len(stores):,}")
print(f"Possible merges (risk A):     {len(merged):,} ({len(merged) / len(stores):.2%} of stores)")
print(f"Possible splits (risk B):     {len(split):,} locations")
print("\nNote: this checks ONE fortnight. A store can also be split ACROSS")
print("fortnights if its address changes. That check comes when we load more files.")

# --- 6. Inspect split cases outside markets ----------------------------------
section("6. Split cases outside markets: full keys")

# Markets and wholesale centers share one location for many stalls, so they
# are expected. These chains are not, and need a manual look.
chains_to_check = ["Mega Soriana", "Pescados y Mariscos Miguel Hidalgo", "Tortillerias Tradicionales"]
chain_level = split.index.get_level_values("cadena_comercial")
suspects = split[chain_level.isin(chains_to_check)]

for (chain, lat, lon), row in suspects.iterrows():
    same_place = with_coords[
        (with_coords["cadena_comercial"] == chain)
        & (with_coords["lat_round"] == lat)
        & (with_coords["lon_round"] == lon)
    ]
    print(f"\n  {chain} at ({lat}, {lon})")
    for key in sorted(same_place["store_key"].unique()):
        print(f"    - {key}")
