"""
Exploración inicial de un archivo de Quién es Quién en los Precios (Profeco).

Objetivo: entender los datos ANTES de diseñar el pipeline.
Este script solo observa: no limpia ni modifica nada.

Uso (desde la carpeta raíz del proyecto):
    python scripts/explorar_datos.py
"""

from pathlib import Path

import pandas as pd

# --- Configuración -----------------------------------------------------------

# La ruta se calcula a partir de dónde está ESTE archivo, no de dónde corres
# la terminal. parents[1] = la carpeta que contiene a scripts/ (la raíz).
RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA = RAIZ_PROYECTO / "data" / "raw" / "prueba01.csv"  # cambia el nombre si es otro

# Productos para revisar cuántas formas distintas tienen de escribirse
PRODUCTOS_A_REVISAR = ["leche", "huevo", "tortilla"]

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def titulo(texto):
    """Imprime un encabezado para separar cada sección de la salida."""
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


# --- Carga -------------------------------------------------------------------

# utf-8-sig: el archivo es UTF-8 con BOM (lo descubrimos en la primera prueba).
df = pd.read_csv(RUTA, encoding="utf-8-sig")

# --- 1. Tamaño ---------------------------------------------------------------
titulo("1. Tamaño del archivo")
filas, columnas = df.shape
memoria_mb = df.memory_usage(deep=True).sum() / 1024**2
print(f"Filas: {filas:,}")
print(f"Columnas: {columnas}")
print(f"Memoria que ocupa en pandas: {memoria_mb:,.1f} MB")

# --- 2. Nulos ----------------------------------------------------------------
titulo("2. Porcentaje de nulos por columna")
# isna() marca True donde falta un valor; mean() de True/False = proporción.
nulos = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
print(nulos.to_string())

# "S/M" (sin marca) no es un nulo técnico, pero se comporta como uno.
sin_marca = (df["marca"] == "S/M").mean() * 100
print(f"\nFilas con marca 'S/M' (sin marca): {sin_marca:.2f}%")

# --- 3. Catálogos ------------------------------------------------------------
titulo("3. Valores de 'catalogo' y cuántas filas tiene cada uno")
print(df["catalogo"].value_counts(dropna=False).to_string())

# --- 4. Fechas ---------------------------------------------------------------
titulo("4. Rango de fechas")
# errors="coerce": si una fecha no se puede interpretar, la deja como NaT
# (fecha vacía) en lugar de tronar. Así podemos contar cuántas vienen mal.
fechas = pd.to_datetime(df["fecha_registro"], errors="coerce")
print(f"Fecha mínima: {fechas.min()}")
print(f"Fecha máxima: {fechas.max()}")
print(f"Fechas distintas: {fechas.nunique()}")
print(f"Fechas que no se pudieron leer: {fechas.isna().sum():,}")

# --- 5. Ciudad de México -----------------------------------------------------
titulo("5. Cómo aparece CDMX")
print("Valores de 'estado' (todos):")
print(df["estado"].value_counts().to_string())

# case=False ignora mayúsculas; na=False trata los nulos como "no coincide".
es_cdmx = df["estado"].str.contains("ciudad de m|distrito federal|cdmx", case=False, na=False)
print(f"\nFilas que parecen de CDMX: {es_cdmx.sum():,}")
print("\nValores de 'municipio' dentro de CDMX:")
print(df.loc[es_cdmx, "municipio"].value_counts().to_string())

# --- 6. Duplicados -----------------------------------------------------------
titulo("6. Duplicados")
duplicados_exactos = df.duplicated().sum()
duplicados_sin_catalogo = df.drop(columns="catalogo").duplicated().sum()
print(f"Filas idénticas en TODAS las columnas: {duplicados_exactos:,}")
print(f"Filas idénticas si ignoramos 'catalogo': {duplicados_sin_catalogo:,}")
print("(La diferencia = precios que se repiten solo porque están en dos catálogos)")

# --- 7. Variantes de productos comunes ---------------------------------------
titulo("7. Formas distintas de escribir productos comunes")
for nombre in PRODUCTOS_A_REVISAR:
    coincide = df["producto"].str.contains(nombre, case=False, na=False)
    print(f"\n--- '{nombre}' ---")
    print(f"Filas: {coincide.sum():,}")
    print("Valores distintos en 'producto':")
    print(df.loc[coincide, "producto"].value_counts().head(10).to_string())
    print(f"Presentaciones distintas: {df.loc[coincide, 'presentacion'].nunique()}")
    print("Las 10 más comunes:")
    print(df.loc[coincide, "presentacion"].value_counts().head(10).to_string())

# --- 8. Precios --------------------------------------------------------------
titulo("8. Precios")
print(df["precio"].describe().round(2).to_string())
print(f"\nPrecios en cero o negativos: {(df['precio'] <= 0).sum():,}")
print(f"Precios vacíos: {df['precio'].isna().sum():,}")

print("\nLos 10 precios más altos (¿tienen sentido?):")
columnas_contexto = ["producto", "presentacion", "marca", "categoria", "precio"]
print(df.nlargest(10, "precio")[columnas_contexto].to_string(index=False))

print("\nCategorías con precio más alto en promedio:")
print(df.groupby("categoria")["precio"].mean().sort_values(ascending=False).head(10).round(2).to_string())