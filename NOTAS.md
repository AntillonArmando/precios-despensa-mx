# Notas de exploración — Proyecto Despensa

Exploración del primer archivo antes de diseñar el pipeline. Solo observaciones: todavía no se limpió nada.

## Fuente

- **Origen:** Profeco, programa Quién es Quién en los Precios (QQP), datos abiertos en datos.gob.mx.
- **Publicación:** un dataset por año, con un archivo por quincena.
- **Archivo analizado:** `prueba01.csv` (primera quincena de julio de 2026).
- **Retraso:** los datos de julio se publican meses después. La carga será por quincena, no diaria.

## Formato

- CSV en **UTF-8 con BOM** → leer con `encoding="utf-8-sig"`.
  - Con `latin-1` los acentos salen mal (`Ã³`) y la primera columna sale como `ï»¿producto`.
- 15 columnas, con encabezados.
- **665,909 filas** y **588 MB** en memoria con pandas, por una sola quincena.
  - Un año (~24 archivos) no cabe en memoria con pandas. Hace falta una base de datos.

## Qué es una fila (grain)

> El precio de un producto (producto + presentación + marca), en una tienda, en una fecha.

- No hay ID de producto.
- No hay ID de tienda.

## Columnas

| Columna | Qué contiene | Observación |
| --- | --- | --- |
| producto | Nombre genérico | "Leche" agrupa productos distintos |
| presentacion | Envase + cantidad + unidad + variante | Texto libre, sin estructura |
| marca | Marca comercial | 31.23% es `S/M` (sin marca) |
| categoria | Categoría del producto | Más detallada que catálogo |
| catalogo | Programa o grupo de Profeco | Genera duplicados (ver abajo) |
| precio | Precio en pesos | Sin ceros ni nulos |
| fecha_registro | Fecha de levantamiento | Se lee como texto; hay que convertirla |
| cadena_comercial | Cadena (ej. Bodega Aurrera) | |
| giro | Tipo de establecimiento | |
| nombre_comercial | Nombre de la tienda | |
| direccion | Dirección en texto libre | |
| estado | Entidad federativa | |
| municipio | Municipio o alcaldía | |
| latitud / longitud | Coordenadas | 0.04% nulos |

## Hallazgos

### 1. Volumen
- 665,909 filas por quincena. Pandas funciona para explorar un archivo, no para el histórico.

### 2. Nulos
- Casi no hay nulos técnicos (solo 0.04% en coordenadas).
- `S/M` en marca (31.23%) es un nulo disfrazado.

### 3. Catálogos
- Solo el 50.8% de las filas es `Básicos`.
- También hay Medicamentos (150,876), Útiles Escolares, Electrodomésticos, Tenis, etc.
- **Hay que definir el alcance de "despensa".**

| Catálogo | Filas |
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

### 4. Fechas
- Del 2026-07-01 al 2026-07-15: 15 días distintos.
- 0 fechas inválidas.
- Confirma: **un archivo = una quincena**.

### 5. CDMX
- Aparece como `Ciudad de México`: 140,141 filas (21% del total).
- Aparecen 13 de 16 alcaldías. **Faltan: Cuajimalpa, Milpa Alta y Tláhuac.**
- Inconsistencia de escritura: `Gustavo a. Madero` (con "a" minúscula).

### 6. Duplicados
- 0 filas idénticas en todas las columnas.
- **9,846 filas idénticas si se ignora `catalogo`**: el mismo precio aparece en dos catálogos (ej. `Básicos` y `PACIC`).
- Si no se resuelve, esos precios cuentan doble en promedios.

### 7. Productos y presentaciones
- **Un nombre de producto no es un producto.** "Leche" incluye ultrapasteurizada, en polvo, condensada, evaporada y pasteurizada.
- **La presentación mezcla cuatro cosas en un solo texto:**
  - Envase: `Caja`, `Lata`, `Bolsa`, `Paquete`
  - Cantidad y unidad: `1 Lt.`, `360 Gr.`, `C/18`, `1 Kg.`
  - Piezas con peso: `Bolsa 20+2 Piezas. 561 Gr.`
  - Variante: `Light`, `Azul`, `Blanco`, `Rojo`, `Jumbo`, `Amarilla`
- **Las unidades no se comparan directo:**
  - Huevo: por piezas (`C/12`, `C/18`, `C/30`) y por kilo (`1 Kg. Granel`).
  - Tortilla: por kilo y por piezas con gramos.
- Para comparar precios hay que extraer la cantidad y calcular **precio por kilo, litro o pieza**.

### 8. Precios
- Sin ceros, negativos ni nulos.
- Mínimo $1.31, máximo $84,999 (pantalla OLED de 77": real, no es error).
- **Promedio ($556.19) engañoso**, inflado por electrónicos. **Mediana: $59.90.** Usar mediana.
- En el top 10 hay precios repetidos del mismo producto. Pendiente saber si es la misma tienda en dos catálogos o tiendas distintas.

## Los 3 problemas principales

1. **Presentación en texto libre.** Sin extraer cantidad y unidad, no se pueden comparar precios.
2. **No hay ID de tienda ni de producto.** Hay que construir identidades a partir de varias columnas (mismo problema que los homónimos por RFC).
3. **Duplicados entre catálogos.** El mismo precio aparece más de una vez y distorsiona promedios.

## Decisiones tomadas

| # | Decisión | Por qué |
| --- | --- | --- |
| 1 | Catálogos: `Básicos`, `Frutas y Legumbres`, `Mercados`, `Pescados y Mariscos` y `PACIC` (deduplicado) | Es una despensa real y permite comparar mercado contra supermercado. PACIC tiene productos que no están en otros catálogos. |
| 2 | Capa cruda con **todo el país**; análisis de la v1 enfocado en **CDMX** | La capa cruda guarda todo; los filtros van en capas posteriores. |
| 3 | **v1: canasta fija de 15 productos** con presentación exacta | Permite comparar precios sin resolver todavía el texto libre de `presentacion`. La v2 extraerá cantidades (precio por kg/L). |
| 4 | Histórico: **todas las quincenas de 2026** | Varios millones de filas: justifica PostgreSQL y permite ver tendencias. |

### Canasta v1

Criterio de productos: compras de todos los días, mezcla de empacados (precio estable) y frescos (precio volátil), presentes en supermercados y en mercados.

Criterio de presentación: la más común en CDMX dentro del alcance, y que aparezca en al menos 4 cadenas distintas para que la comparación tenga sentido.

| Producto (nombre exacto) | Presentación elegida | Registros CDMX | Cadenas |
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

Datos: primera quincena de julio de 2026, CDMX, catálogos del alcance.

### Hallazgos al elegir la canasta

- **La búsqueda por texto trae basura:** "pan" trajo Pantiprotectores y Queso Panela; "papa" trajo Papaya; "pasta" trajo Jabón de Pasta. El pipeline usa nombres exactos.
- **Nombres que parecen iguales y no lo son:** `Frijol` (grano) contra `Frijoles`; `Jitomate` contra `Tomate` (verde); `Leche Ultrapasteurizada` contra otras leches.
- **El mismo producto aparece partido en varias presentaciones por diferencias de texto:**
  - `Paquete 200 Gr. Spaghetti No. 5` (140) y `Paquete 200 Gr. Spaghetti` (133).
  - `Bolsa 900 Gr. Negro` (182) y `Bolsa 900 Gr. Negro. Querétaro` (167). Juntos (349) superarían al Pinto (190).
  - Pollo entero aparece en dos presentaciones distintas.
  - Arroz Super Extra en 900 g, 907 g y 1 kg.
- **Los frescos ya vienen por kilo** (`1 Kg. Granel`): se comparan directo. Los empacados no.
- Conclusión: la v1 usa la presentación exacta; la **v2 debe normalizar presentaciones** (unificar variantes de texto y calcular precio por kg/L).

## Decisiones pendientes

- [ ] ¿Cómo tratar `S/M`: como nulo, como marca genérica o se excluye?
- [ ] ¿Qué columnas forman la llave de una tienda?
- [ ] ¿Qué columnas forman la llave de un producto?
- [ ] ¿Cómo deduplicar entre catálogos: quedarse con uno o guardar ambos con una bandera?

## Preguntas abiertas

- ¿Qué significa exactamente `PACIC`? (Probablemente el paquete contra la inflación del gobierno; confirmar.)
- ¿Las columnas son iguales en todos los archivos y años? Falta comparar con otro archivo.
- ¿Por qué faltan 3 alcaldías? ¿No se levantaron datos ahí o es esta quincena?
- ¿Cada cuánto se publica un archivo nuevo y con cuánto retraso exacto?