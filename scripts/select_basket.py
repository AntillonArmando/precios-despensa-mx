"""
Select the v1 basket: for each product, find the most common presentation
in Mexico City within the in-scope catalogs.

Column names and product names stay in Spanish because they are values
from the source data, not our own naming.

Usage (from the project root):
    python scripts/select_basket.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = PROJECT_ROOT / "data" / "raw" / "prueba01.csv"

# Scope decision 1: catalogs that count as groceries
CATALOGS = ["Básicos", "Frutas y Legumbres", "Mercados", "Pescados y Mariscos", "PACIC"]

# Exact product names, as they appear in the data
BASKET = [
    "Huevo", "Leche Ultrapasteurizada", "Tortilla de Maíz", "Frijol", "Arroz",
    "Aceite", "Azúcar", "Pasta para Sopa", "Pan de Caja", "Atún",
    "Carne Pollo", "Jitomate", "Cebolla", "Papa", "Plátano",
]

df = pd.read_csv(FILE_PATH, encoding="utf-8-sig")
print(f"Total rows: {len(df):,}")

in_scope = df["catalogo"].isin(CATALOGS)
df = df[in_scope]
print(f"Rows in grocery catalogs: {len(df):,}")

is_cdmx = df["estado"] == "Ciudad de México"
cdmx = df[is_cdmx]
print(f"Grocery rows in Mexico City: {len(cdmx):,}")

for product in BASKET:
    product_rows = cdmx[cdmx["producto"] == product]
    summary = (
        product_rows.groupby("presentacion")
        .agg(rows=("precio", "size"), chains=("cadena_comercial", "nunique"))
        .sort_values("rows", ascending=False)
    )
    print(f"\n--- {product} ---")
    print(summary.head(5).to_string())
