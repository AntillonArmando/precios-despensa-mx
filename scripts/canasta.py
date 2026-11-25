from pathlib import Path
import pandas as pd

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA = RAIZ_PROYECTO / "data" / "raw" / "prueba01.csv"

CATALOGOS = ["Básicos", "Frutas y Legumbres", "Mercados", "Pescados y Mariscos", "PACIC"]

df = pd.read_csv(RUTA, encoding="utf-8-sig")
print(f"Filas totales: {len(df):,}")

en_alcance = df["catalogo"].isin(CATALOGOS)
df = df[en_alcance]
print(f"Filas en catálogos de despensa: {len(df):,}")

es_cdmx = df["estado"] == "Ciudad de México"
cdmx = df[es_cdmx]
print(f"Filas de despensa en CDMX: {len(cdmx):,}")

CANASTA = [
    "Huevo", "Leche Ultrapasteurizada", "Tortilla de Maíz", "Frijol", "Arroz",
    "Aceite", "Azúcar", "Pasta para Sopa", "Pan de Caja", "Atún",
    "Carne Pollo", "Jitomate", "Cebolla", "Papa", "Plátano",
]

for producto in CANASTA:
    filas = cdmx[cdmx["producto"] == producto]
    resumen = (
        filas.groupby("presentacion")
        .agg(registros=("precio", "size"), cadenas=("cadena_comercial", "nunique"))
        .sort_values("registros", ascending=False)
    )
    print(f"\n--- {producto} ---")
    print(resumen.head(5).to_string())