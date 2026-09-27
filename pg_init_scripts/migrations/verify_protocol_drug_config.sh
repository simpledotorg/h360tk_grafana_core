#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIGRATION="$ROOT/pg_init_scripts/migrations/0.5.1_to_0.5.2.sql"
DB_NAME="${PROTOCOL_DRUG_VERIFY_DB:-protocol_drug_config_verify}"

if [[ ! -f "$MIGRATION" ]]; then
    echo "missing migration: $MIGRATION" >&2
    exit 1
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

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
CREATE SCHEMA heart360tk_schema AUTHORIZATION heart360tk;
SQL

echo "apply 1"
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$MIGRATION" >/dev/null

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
SET search_path TO heart360tk_schema;

DO $$
DECLARE
    v_protocol TEXT;
    v_drugs INT;
    v_tracked INT;
BEGIN
    SELECT protocol_code INTO v_protocol
    FROM programme_protocols
    WHERE country_code = 'India' AND programme_code = 'IHCI';

    IF v_protocol IS DISTINCT FROM 'AATTCC' THEN
        RAISE EXCEPTION 'India/IHCI protocol_code is %, expected AATTCC', v_protocol;
    END IF;

    SELECT COUNT(*) INTO v_drugs
    FROM protocol_drugs
    WHERE country_code = 'India' AND programme_code = 'IHCI';

    IF v_drugs <> 6 THEN
        RAISE EXCEPTION 'India/IHCI drug count is %, expected 6', v_drugs;
    END IF;

    SELECT COUNT(*) INTO v_tracked
    FROM protocol_drugs
    WHERE country_code = 'India'
      AND programme_code = 'IHCI'
      AND stock_tracked
      AND (drug_name, dosage, rxnorm_code, drug_category) IN (
          ('Amlodipine', '5 mg', '329528', 'hypertension_ccb'),
          ('Amlodipine', '10 mg', '329526', 'hypertension_ccb'),
          ('Telmisartan', '40 mg', '316764', 'hypertension_arb'),
          ('Telmisartan', '80 mg', '316765', 'hypertension_arb'),
          ('Chlorthalidone', '12.5 mg', '331132', 'hypertension_diuretic'),
          ('Chlorthalidone', '25 mg', '197499', 'hypertension_diuretic')
      );

    IF v_tracked <> 6 THEN
        RAISE EXCEPTION 'India/IHCI tracked drug set mismatch, matched % of 6', v_tracked;
    END IF;
END $$;

DO $$
BEGIN
    INSERT INTO programme_protocols (country_code, programme_code, protocol_code)
    VALUES ('India', 'OTHER', 'AATTH');
    RAISE EXCEPTION 'CHECK accepted protocol_code AATTH';
EXCEPTION
    WHEN check_violation THEN
        NULL;
END $$;

BEGIN;
INSERT INTO programme_protocols (country_code, programme_code, protocol_code)
VALUES ('India', 'ATTACC-PROBE', 'ATTACC');
ROLLBACK;
SQL

echo "apply 2"
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$MIGRATION" >/dev/null

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
SET search_path TO heart360tk_schema;

DO $$
DECLARE
    v_programmes INT;
    v_drugs INT;
BEGIN
    SELECT COUNT(*) INTO v_programmes FROM programme_protocols;
    SELECT COUNT(*) INTO v_drugs FROM protocol_drugs;
    IF v_programmes <> 1 OR v_drugs <> 6 THEN
        RAISE EXCEPTION 'second apply drifted to % programmes and % drugs', v_programmes, v_drugs;
    END IF;
END $$;

UPDATE protocol_drugs
SET stock_tracked = FALSE
WHERE country_code = 'India' AND programme_code = 'IHCI' AND rxnorm_code = '329528';

UPDATE programme_protocols
SET protocol_code = 'ATTACC'
WHERE country_code = 'India' AND programme_code = 'IHCI';
SQL

echo "apply 3"
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$MIGRATION" >/dev/null

sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
SET search_path TO heart360tk_schema;

DO $$
DECLARE
    v_protocol TEXT;
    v_tracked BOOLEAN;
    v_drugs INT;
BEGIN
    SELECT protocol_code INTO v_protocol
    FROM programme_protocols
    WHERE country_code = 'India' AND programme_code = 'IHCI';

    SELECT stock_tracked INTO v_tracked
    FROM protocol_drugs
    WHERE country_code = 'India' AND programme_code = 'IHCI' AND rxnorm_code = '329528';

    SELECT COUNT(*) INTO v_drugs FROM protocol_drugs;

    IF v_protocol IS DISTINCT FROM 'AATTCC' OR v_tracked IS DISTINCT FROM TRUE OR v_drugs <> 6 THEN
        RAISE EXCEPTION 're-seed did not converge: protocol % tracked % drugs %', v_protocol, v_tracked, v_drugs;
    END IF;
END $$;
SQL

drop_db
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${DB_NAME} OWNER heart360tk;" >/dev/null
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -c \
    "CREATE SCHEMA heart360tk_schema AUTHORIZATION heart360tk;" >/dev/null

INCLUDE_DIR="$(mktemp -d)"
chmod 755 "$INCLUDE_DIR"
cat > "$INCLUDE_DIR/01_include.sql" <<EOF
\\ir $MIGRATION
EOF
chmod 644 "$INCLUDE_DIR/01_include.sql"
echo "apply via \\ir"
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$INCLUDE_DIR/01_include.sql" >/dev/null
rm -rf "$INCLUDE_DIR"

if ! grep -q '\\ir migrations/0.5.1_to_0.5.2.sql' "$ROOT/pg_init_scripts/01_heart360_tables.sql"; then
    echo "01_heart360_tables.sql does not include the migration" >&2
    exit 1
fi

INCLUDED="$(sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -tA -c \
"SELECT country_code || '/' || programme_code || ' ' || protocol_code || ' drugs=' || (SELECT COUNT(*)::text FROM heart360tk_schema.protocol_drugs) FROM heart360tk_schema.programme_protocols;")"
if [[ "$INCLUDED" != "India/IHCI AATTCC drugs=6" ]]; then
    echo "\\ir path produced '$INCLUDED'" >&2
    exit 1
fi

drop_db
sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c "DROP ROLE IF EXISTS heart360tk;" >/dev/null

echo "protocol drug config verified"
