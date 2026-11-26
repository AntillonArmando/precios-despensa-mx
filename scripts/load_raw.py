"""
Load source CSV files into the raw layer (raw.prices).

For each CSV file in data/raw/:
  1. Check that its header has the 15 expected columns, in order.
  2. In ONE transaction:
       - delete any rows previously loaded from this file,
       - insert every row of the file,
       - record the load in raw.load_log.
  3. Check that the rows in the database match the rows read from the file.
     If they don't, the whole transaction is rolled back.

Loading the same file twice leaves the same result as loading it once.

Usage (from the project root, with the database running):
    python scripts/load_raw.py
"""

import csv
import os
import sys
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# --- Configuration ----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

EXPECTED_COLUMNS = [
    "producto", "presentacion", "marca", "categoria", "catalogo", "precio",
    "fecha_registro", "cadena_comercial", "giro", "nombre_comercial",
    "direccion", "estado", "municipio", "latitud", "longitud",
]

# Credentials come from .env (never written in the code).
load_dotenv(PROJECT_ROOT / ".env")

DB_SETTINGS = {
    "host": "localhost",
    "port": 5432,
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}

COPY_SQL = f"""
    COPY raw.prices ({", ".join(EXPECTED_COLUMNS)}, source_file)
    FROM STDIN
"""

LOG_SQL = """
    INSERT INTO raw.load_log (source_file, row_count)
    VALUES (%s, %s)
    ON CONFLICT (source_file)
    DO UPDATE SET row_count = EXCLUDED.row_count, loaded_at = now()
"""


def load_file(conn, csv_path):
    """Load one CSV into raw.prices. Returns the number of rows loaded."""
    source_file = csv_path.name

    # utf-8-sig removes the BOM found during exploration.
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        # 1. Schema check: fail fast if Profeco changed the columns.
        header = next(reader)
        if header != EXPECTED_COLUMNS:
            raise ValueError(
                f"{source_file}: unexpected columns.\n"
                f"  Expected: {EXPECTED_COLUMNS}\n"
                f"  Found:    {header}"
            )

        # 2. Everything below runs in a single transaction.
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("DELETE FROM raw.prices WHERE source_file = %s", (source_file,))

                rows_read = 0
                with cur.copy(COPY_SQL) as copy:
                    # Line 1 is the header, so data starts on line 2.
                    for line_number, row in enumerate(reader, start=2):
                        if len(row) != len(EXPECTED_COLUMNS):
                            raise ValueError(
                                f"{source_file}, line {line_number}: "
                                f"expected {len(EXPECTED_COLUMNS)} values, found {len(row)}"
                            )
                        # Empty strings are stored as NULL (missing value).
                        values = [value if value != "" else None for value in row]
                        copy.write_row(values + [source_file])
                        rows_read += 1

                # 3. Reconciliation: what is in the database must match the file.
                cur.execute("SELECT count(*) FROM raw.prices WHERE source_file = %s", (source_file,))
                rows_in_db = cur.fetchone()[0]
                if rows_in_db != rows_read:
                    raise ValueError(
                        f"{source_file}: read {rows_read:,} rows but found {rows_in_db:,} in the database"
                    )

                cur.execute(LOG_SQL, (source_file, rows_read))

    return rows_read


def main():
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DATA_DIR}")
        sys.exit(1)

    print(f"Files to load: {len(csv_files)}")
    # autocommit=True: nothing is committed implicitly; each conn.transaction()
    # block below is its own explicit transaction (all or nothing per file).
    with psycopg.connect(**DB_SETTINGS, autocommit=True) as conn:
        for csv_path in csv_files:
            start = time.perf_counter()
            rows = load_file(conn, csv_path)
            seconds = time.perf_counter() - start
            print(f"  {csv_path.name}: {rows:,} rows in {seconds:.1f} s")

    print("Done.")


if __name__ == "__main__":
    main()
