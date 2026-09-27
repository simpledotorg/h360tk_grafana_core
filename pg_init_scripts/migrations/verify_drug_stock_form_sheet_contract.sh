#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIGRATION="$ROOT/pg_init_scripts/migrations/0.5.1_to_0.5.2.sql"
DB_NAME="${DRUG_STOCK_FORM_VERIFY_DB:-drug_stock_form_contract_verify}"
CONTRACT_DIR="$ROOT/drug-stock-form-contract"
HEADER_FILE="$CONTRACT_DIR/sheet_response_header.tsv"
EXPORT_SCRIPT="$ROOT/pg_init_scripts/export_drug_stock_form_choices.sh"

if [[ ! -f "$MIGRATION" ]]; then
    echo "missing migration: $MIGRATION" >&2
    exit 1
fi

EXPECTED_HEADER='org_unit_id	reporting_month	drug_code	in_stock	submitted_at'
ACTUAL_HEADER="$(tr -d '\r' < "$HEADER_FILE" | head -n1)"
if [[ "$ACTUAL_HEADER" != "$EXPECTED_HEADER" ]]; then
    echo "sheet header mismatch: got '$ACTUAL_HEADER'" >&2
    exit 1
fi

if grep -qiE 'received|consumption' "$CONTRACT_DIR/SHEET_CONTRACT.md"; then
    if grep -qiE 'no.*received|no.*consumption|not.*received' "$CONTRACT_DIR/SHEET_CONTRACT.md"; then
        :
    else
        echo "SHEET_CONTRACT must not add received/consumption columns" >&2
        exit 1
    fi
fi

drop_db() {
    sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \
        "DROP DATABASE IF EXISTS ${DB_NAME};" >/dev/null
}

drop_db
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 <<SQL
DROP ROLE IF EXISTS heart360tk;
CREATE ROLE heart360tk LOGIN;
CREATE DATABASE ${DB_NAME} OWNER heart360tk;
SQL

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA heart360tk_schema AUTHORIZATION heart360tk;

CREATE TABLE heart360tk_schema.org_units (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    level       INTEGER NOT NULL,
    parent_id   INTEGER REFERENCES heart360tk_schema.org_units(id)
);
SQL

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$MIGRATION" >/dev/null

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
SET search_path TO heart360tk_schema;

INSERT INTO org_units (name, level, parent_id) VALUES
    ('Prototype District A', 2, NULL),
    ('UHC Alpha', 4, NULL),
    ('UHC Beta', 4, NULL);

DO $$
DECLARE
    v_drugs INT;
BEGIN
    SELECT COUNT(*) INTO v_drugs FROM active_stock_tracked_drugs;
    IF v_drugs <> 6 THEN
        RAISE EXCEPTION 'expected 6 active_stock_tracked_drugs, got %', v_drugs;
    END IF;
END $$;
SQL

COHORT_FIXTURE="$(mktemp)"
chmod 644 "$COHORT_FIXTURE"
# Cohort includes two facilities; community site omitted intentionally.
sudo -u postgres psql -d "$DB_NAME" -tA -c \
    "SELECT id FROM heart360tk_schema.org_units WHERE name IN ('UHC Alpha', 'UHC Beta') ORDER BY name;" \
    | while read -r id; do echo "$id"; done > "$COHORT_FIXTURE"

chmod +x "$EXPORT_SCRIPT"
EXPORT_OUT="$(mktemp)"
DRUG_STOCK_FORM_PGDATABASE="$DB_NAME" DRUG_STOCK_FORM_COHORT_FILE="$COHORT_FIXTURE" \
    "$EXPORT_SCRIPT" > "$EXPORT_OUT"

HEAD_LINE="$(head -n1 "$EXPORT_OUT")"
if [[ "$HEAD_LINE" != "org_unit_id,display_name" ]]; then
    echo "export header mismatch: $HEAD_LINE" >&2
    exit 1
fi

ROUNDTRIP_ID="$(awk -F',' 'NR==2 { print $1 }' "$EXPORT_OUT")"
ROUNDTRIP_NAME="$(awk -F',' 'NR==2 { print $2 }' "$EXPORT_OUT")"
DB_PAIR="$(sudo -u postgres psql -d "$DB_NAME" -tA -c \
    "SELECT id::text || '|' || name FROM heart360tk_schema.org_units WHERE id = ${ROUNDTRIP_ID};")"

if [[ "$DB_PAIR" != "${ROUNDTRIP_ID}|${ROUNDTRIP_NAME}" ]]; then
    echo "cohort round-trip failed: export ($ROUNDTRIP_ID,$ROUNDTRIP_NAME) vs db ($DB_PAIR)" >&2
    exit 1
fi

rm -f "$COHORT_FIXTURE" "$EXPORT_OUT"
drop_db
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c "DROP ROLE IF EXISTS heart360tk;" >/dev/null

echo "drug stock form/sheet contract verified"
