# Kemendagri administrative codes

This toolkit can capture the Indonesian **Kemendagri** administrative codes
alongside each geography level, so every org unit (and every record rolled up
from it) carries its official code. Codes flow **end to end automatically**:
leaf-node ingestion → `org_units.code` → `orgunit.csv` in the export zip →
central-node importer → central `org_units.code`.

## Input columns

Add these **optional** columns to your uploaded CSV/Excel line-list. Each code is
attached to the matching hierarchy level.

| Column name  | Attached to level        | Example        |
| ------------ | ------------------------ | -------------- |
| `kode prov`  | Level 1 — Region         | `34`           |
| `kode kab`   | Level 2 — District       | `3403`         |
| `kode kec`   | Level 3 — Facility       | `340314`       |
| `kode desa`  | Level 4 — Sub-Facility   | `3403142006`   |

Column names are matched case-sensitively as written above. Missing or empty
cells are simply skipped — the codes are optional and never block ingestion.

## How it works

1. **Leaf ingestion** (`inotify_scripts/ingest_file_h360tk.py`) reads the code
   for each level via `HIERARCHY_LEVELS[*]['code_column']` and passes them to the
   `upsert_org_unit_chain(names, levels, codes)` overload, which stores each code
   on the corresponding `org_units` row.
2. **Export** (`exporter_scripts/exporter.py`) includes the `code` column in
   `orgunit.csv` when it exists, so it travels inside the export zip.
3. **Central import** (`importer_scripts/import_versions/base.py`) reads the
   `code` column from `orgunit.csv` and stores it on the central `org_units`
   via `upsert_org_unit(name, level, parent, code)`.

## Database

`org_units` gains a nullable `code VARCHAR(32)` column plus two additive function
overloads:

- `upsert_org_unit(name, level, parent, code)`
- `upsert_org_unit_chain(names[], levels[], codes[])`

The original 3-/2-argument functions are left untouched, so nothing that does not
supply codes changes behaviour.

- **Fresh install:** applied automatically by `pg_init_scripts/03_kemendagri_codes.sql`.
- **Existing database:** run `pg_init_scripts/migrations/0.5.1_add_kemendagri_codes.sql`.

Every layer degrades gracefully: if the column/overloads are not present (older
DB image), ingestion, export, and import fall back to the previous behaviour and
simply skip the codes.
