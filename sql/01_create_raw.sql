-- Raw layer: source data exactly as received, plus load metadata.

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per row of a source CSV. Every column is TEXT on purpose:
-- a malformed value must never break the load. Types are fixed in `clean`.
CREATE TABLE IF NOT EXISTS raw.prices (
    producto          TEXT,
    presentacion      TEXT,
    marca             TEXT,
    categoria         TEXT,
    catalogo          TEXT,
    precio            TEXT,
    fecha_registro    TEXT,
    cadena_comercial  TEXT,
    giro              TEXT,
    nombre_comercial  TEXT,
    direccion         TEXT,
    estado            TEXT,
    municipio         TEXT,
    latitud           TEXT,
    longitud          TEXT,
    source_file       TEXT        NOT NULL,
    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Speeds up deleting one file's rows when it is reloaded.
CREATE INDEX IF NOT EXISTS idx_raw_prices_source_file
    ON raw.prices (source_file);

-- Load control: which files were loaded, when, and how many rows.
CREATE TABLE IF NOT EXISTS raw.load_log (
    source_file  TEXT        PRIMARY KEY,
    row_count    INTEGER     NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);