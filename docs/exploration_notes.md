# Exploration notes

Profiling of the first source file before designing the pipeline. Observations only: nothing was cleaned at this stage.

Design decisions that came out of these notes are in [`architecture.md`](architecture.md).

## Source

- **Origin:** Profeco, *Quién es Quién en los Precios* (QQP) program, open data on datos.gob.mx.
- **Publication:** one dataset per year, one file per fortnight.
- **File analyzed:** `prueba01.csv` (first fortnight of July 2026).
- **Lag:** July data is published months later. Loads will run per fortnight, not daily.

## Format

- CSV in **UTF-8 with BOM** → read with `encoding="utf-8-sig"`.
  - Read as `latin-1`, accents break (`Ã³`) and the first column becomes `ï»¿producto`.
- 15 columns, with headers.
- **665,909 rows** and **588 MB** in pandas memory, for a single fortnight.
  - A full year (~24 files) does not fit in memory with pandas. A database is needed.

## Grain

> The price of one product (product + presentation + brand), in one store, on one date.

- No product ID.
- No store ID.

## Columns

| Column | Contents | Notes |
| --- | --- | --- |
| producto | Generic product name | "Leche" groups different products |
| presentacion | Package + quantity + unit + variant | Free text, no structure |
| marca | Brand | 31.23% is `S/M` (no brand) |
| categoria | Product category | More detailed than `catalogo` |
| catalogo | Profeco program or group | Causes duplicates (see below) |
| precio | Price in MXN | No zeros or nulls |
| fecha_registro | Collection date | Read as text; must be converted |
| cadena_comercial | Chain (e.g. Bodega Aurrera) | |
| giro | Store type | |
| nombre_comercial | Store name | |
| direccion | Free-text address | |
| estado | State | |
| municipio | Municipality or borough | |
| latitud / longitud | Coordinates | 0.04% nulls; sometimes wrong (see architecture) |

## Findings

### 1. Volume
- 665,909 rows per fortnight. Pandas works for exploring one file, not for the full history.

### 2. Nulls
- Almost no technical nulls (0.04%, coordinates only).
- `S/M` in `marca` (31.23%) is a disguised null.

### 3. Catalogs
- Only 50.8% of rows are `Básicos`.
- The file also includes medicines (150,876 rows), school supplies, appliances, sneakers, etc.
- **The scope of "groceries" has to be defined.**

| Catalog | Rows |
| --- | --- |
| Básicos | 338,043 |
| Medicamentos | 150,876 |
| Útiles Escolares | 58,240 |
| Electrodomésticos | 38,753 |
| Frutas y Legumbres | 33,998 |
| PACIC | 24,739 |
| Mercados | 12,220 |
| Especial | 6,720 |
| Pescados y Mariscos | 2,033 |
| Tenis | 287 |

### 4. Dates
- From 2026-07-01 to 2026-07-15: 15 distinct days.
- 0 invalid dates.
- Confirms: **one file = one fortnight**.

### 5. Mexico City
- Appears as `Ciudad de México`: 140,141 rows (21% of the total).
- 13 of 16 boroughs appear. **Missing: Cuajimalpa, Milpa Alta and Tláhuac.**
- Inconsistent spelling: `Gustavo a. Madero` (lowercase "a").

### 6. Duplicates
- 0 rows identical across all columns.
- **9,846 rows identical when `catalogo` is ignored:** the same price appears in two catalogs (e.g. `Básicos` and `PACIC`).
- Left unresolved, those prices are double-counted in averages.

### 7. Products and presentations
- **A product name is not a product.** "Leche" includes UHT, powdered, condensed, evaporated and pasteurized milk.
- **`presentacion` mixes four things in one string:**
  - Package: `Caja`, `Lata`, `Bolsa`, `Paquete`
  - Quantity and unit: `1 Lt.`, `360 Gr.`, `C/18`, `1 Kg.`
  - Pieces with weight: `Bolsa 20+2 Piezas. 561 Gr.`
  - Variant: `Light`, `Azul`, `Blanco`, `Rojo`, `Jumbo`, `Amarilla`
- **Units are not directly comparable:**
  - Eggs: by count (`C/12`, `C/18`, `C/30`) and by kilo (`1 Kg. Granel`).
  - Tortillas: by kilo and by count with grams.
- Comparing prices requires extracting the quantity and computing **price per kilo, liter or piece**.

### 8. Prices
- No zero, negative or null prices.
- Min $1.31, max $84,999 (a 77" OLED TV: real, not an error).
- **The mean ($556.19) is misleading**, inflated by electronics. **Median: $59.90.** Use the median.
- The top 10 contains repeated prices for the same product. Same store in two catalogs, or different stores? Pending.

## Top 3 problems

1. **Free-text presentation.** Prices cannot be compared without extracting quantity and unit.
2. **No store or product ID.** Identities must be built from several columns.
3. **Duplicates across catalogs.** The same price appears more than once and skews averages.

## Scope decisions

| # | Decision | Why |
| --- | --- | --- |
| 1 | Catalogs: `Básicos`, `Frutas y Legumbres`, `Mercados`, `Pescados y Mariscos` and `PACIC` (deduplicated) | A real grocery basket, and it allows comparing markets with supermarkets. PACIC has products not found in other catalogs. |
| 2 | Raw layer with the **whole country**; v1 analysis focused on **Mexico City** | The raw layer keeps everything; filters belong to later layers. |
| 3 | **v1: fixed basket of 15 products** with an exact presentation | Allows comparing prices without solving free-text presentations yet. v2 will extract quantities (price per kg/L). |
| 4 | History: **all 2026 fortnights** | Several million rows: justifies PostgreSQL and shows trends. |

### v1 basket

Product criteria: everyday purchases, a mix of packaged goods (stable prices) and fresh produce (volatile prices), sold in both supermarkets and markets.

Presentation criteria: the most common in Mexico City within scope, sold by at least 4 different chains so the comparison is meaningful.

| Product (exact name) | Presentation | Rows (Mexico City) | Chains |
| --- | --- | --- | --- |
| Huevo | Paquete C/18 Blanco | 797 | 13 |
| Leche Ultrapasteurizada | Caja 1 Lt. Entera | 472 | 17 |
| Tortilla de Maíz | 1 Kg. Granel | 390 | 16 |
| Frijol | Bolsa 900 Gr. Pinto | 190 | 11 |
| Arroz | Bolsa 900 Gr. Super Extra | 186 | 13 |
| Aceite | Botella 850 Ml. Vegetal | 203 | 11 |
| Azúcar | Bolsa Plástico 900 Gr. Estándar | 358 | 11 |
| Pasta para Sopa | Paquete 200 Gr. Spaghetti No. 5 | 140 | 13 |
| Pan de Caja | Paquete Grande 620 Gr. Rebanado Blanco | 243 | 19 |
| Atún | Lata 130 Gr. Aleta Amarilla en Hojuelas en Agua | 151 | 15 |
| Carne Pollo | 1 Kg. Granel. Entero | 192 | 11 |
| Jitomate | 1 Kg. Granel. Saladette/huaje o Tomate Saladette/huaje | 263 | 15 |
| Cebolla | 1 Kg. Granel. Blanca Sin Rabo | 265 | 15 |
| Papa | 1 Kg. Granel. Alfa/blanca | 247 | 15 |
| Plátano | 1 Kg. Granel. Tabasco/chiapas/roatán/portalimón | 265 | 15 |

Data: first fortnight of July 2026, Mexico City, in-scope catalogs. Selected with [`scripts/canasta.py`](../scripts/canasta.py).

### Findings while choosing the basket

- **Text search returns noise:** "pan" (bread) matched panty liners and panela cheese; "papa" (potato) matched papaya; "pasta" matched bar soap (`Jabón de Pasta`). The pipeline uses exact names.
- **Names that look alike but are different products:** `Frijol` (dry beans) vs `Frijoles`; `Jitomate` (red tomato) vs `Tomate` (green tomatillo); UHT milk vs other milks.
- **The same product is split across presentations by spelling:**
  - `Paquete 200 Gr. Spaghetti No. 5` (140) and `Paquete 200 Gr. Spaghetti` (133).
  - `Bolsa 900 Gr. Negro` (182) and `Bolsa 900 Gr. Negro. Querétaro` (167). Together (349) they would beat Pinto (190).
  - Whole chicken appears under two presentations.
  - Super Extra rice in 900 g, 907 g and 1 kg.
- **Fresh produce is already priced per kilo** (`1 Kg. Granel`) and compares directly. Packaged goods do not.
- Conclusion: v1 uses exact presentations; **v2 must normalize presentations** (merge spelling variants and compute price per kg/L).

## Open decisions

- [ ] How to treat `S/M`: as null, as a generic brand, or excluded?
- [ ] Which columns form the product key?
- [x] Which columns form the store key? → see [architecture](architecture.md#store-key)
- [x] How to deduplicate across catalogs? → see [architecture](architecture.md#deduplication-across-catalogs)

## Open questions

- What exactly is `PACIC`? (Probably the government's anti-inflation package; to be confirmed.)
- Are columns identical across all files and years? Another file must be compared.
- Why are 3 boroughs missing? No data collected there, or just this fortnight?
- How often is a new file published, and with how much lag exactly?
