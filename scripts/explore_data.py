"""
Initial profiling of one Profeco "Quién es Quién en los Precios" file.

Goal: understand the data BEFORE designing the pipeline.
This script only observes: it does not clean or modify anything.

Usage (from the project root):
    python scripts/explore_data.py
"""

from pathlib import Path

import pandas as pd

# --- Configuration ----------------------------------------------------------

# The path is built from where THIS file lives, not from where the terminal is.
# parents[1] = the folder that contains scripts/ (the project root).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "prueba01.csv"  # change the name if needed

# Products to check for spelling and presentation variants
PRODUCTS_TO_CHECK = ["leche", "huevo", "tortilla"]

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def section(title):
    """Print a header to separate each part of the output."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# --- Load -------------------------------------------------------------------

# utf-8-sig: the file is UTF-8 with a BOM (found in the first test).
df = pd.read_csv(FILE_PATH, encoding="utf-8-sig")

# --- 1. Size ----------------------------------------------------------------
section("1. File size")
rows, columns = df.shape
memory_mb = df.memory_usage(deep=True).sum() / 1024**2
print(f"Rows: {rows:,}")
print(f"Columns: {columns}")
print(f"Memory used in pandas: {memory_mb:,.1f} MB")

# --- 2. Nulls ---------------------------------------------------------------
section("2. Percentage of nulls per column")
# isna() is True where a value is missing; the mean of True/False is the share.
nulls = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
print(nulls.to_string())

# "S/M" (no brand) is not a technical null, but it behaves like one.
no_brand = (df["marca"] == "S/M").mean() * 100
print(f"\nRows with brand 'S/M' (no brand): {no_brand:.2f}%")

# --- 3. Catalogs ------------------------------------------------------------
section("3. Values of 'catalogo' and rows per value")
print(df["catalogo"].value_counts(dropna=False).to_string())

# --- 4. Dates ---------------------------------------------------------------
section("4. Date range")
# errors="coerce": an unreadable date becomes NaT (empty) instead of crashing,
# so we can count how many are wrong.
dates = pd.to_datetime(df["fecha_registro"], errors="coerce")
print(f"Min date: {dates.min()}")
print(f"Max date: {dates.max()}")
print(f"Distinct dates: {dates.nunique()}")
print(f"Unreadable dates: {dates.isna().sum():,}")

# --- 5. Mexico City ---------------------------------------------------------
section("5. How Mexico City appears")
print("Values of 'estado' (all):")
print(df["estado"].value_counts().to_string())

# case=False ignores upper/lower case; na=False treats nulls as "no match".
is_cdmx = df["estado"].str.contains("ciudad de m|distrito federal|cdmx", case=False, na=False)
print(f"\nRows that look like Mexico City: {is_cdmx.sum():,}")
print("\nValues of 'municipio' within Mexico City:")
print(df.loc[is_cdmx, "municipio"].value_counts().to_string())

# --- 6. Duplicates ----------------------------------------------------------
section("6. Duplicates")
exact_duplicates = df.duplicated().sum()
duplicates_ignoring_catalog = df.drop(columns="catalogo").duplicated().sum()
print(f"Rows identical in ALL columns: {exact_duplicates:,}")
print(f"Rows identical if 'catalogo' is ignored: {duplicates_ignoring_catalog:,}")
print("(The difference = prices repeated only because they are in two catalogs)")

# --- 7. Product variants ----------------------------------------------------
section("7. Spelling and presentation variants of common products")
for name in PRODUCTS_TO_CHECK:
    matches = df["producto"].str.contains(name, case=False, na=False)
    print(f"\n--- '{name}' ---")
    print(f"Rows: {matches.sum():,}")
    print("Distinct values in 'producto':")
    print(df.loc[matches, "producto"].value_counts().head(10).to_string())
    print(f"Distinct presentations: {df.loc[matches, 'presentacion'].nunique()}")
    print("Top 10:")
    print(df.loc[matches, "presentacion"].value_counts().head(10).to_string())

# --- 8. Prices --------------------------------------------------------------
section("8. Prices")
print(df["precio"].describe().round(2).to_string())
print(f"\nZero or negative prices: {(df['precio'] <= 0).sum():,}")
print(f"Empty prices: {df['precio'].isna().sum():,}")

print("\nTop 10 prices (do they make sense?):")
context_columns = ["producto", "presentacion", "marca", "categoria", "precio"]
print(df.nlargest(10, "precio")[context_columns].to_string(index=False))

print("\nCategories with the highest average price:")
print(df.groupby("categoria")["precio"].mean().sort_values(ascending=False).head(10).round(2).to_string())
