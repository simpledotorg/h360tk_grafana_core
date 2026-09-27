#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COHORT_FILE="${DRUG_STOCK_FORM_COHORT_FILE:-$ROOT/drug-stock-form-contract/cohort_org_unit_ids.txt}"
DB="${DRUG_STOCK_FORM_PGDATABASE:-${PGDATABASE:-}}"

if [[ -z "$DB" ]]; then
    echo "set DRUG_STOCK_FORM_PGDATABASE or PGDATABASE" >&2
    exit 1
fi

if [[ ! -f "$COHORT_FILE" ]]; then
    echo "missing cohort file: $COHORT_FILE" >&2
    exit 1
fi

mapfile -t COHORT_IDS < <(
    awk -F'#' '{ gsub(/^[ \t]+|[ \t]+$/, "", $1); if (length($1)) print $1 }' "$COHORT_FILE"
)

if [[ ${#COHORT_IDS[@]} -eq 0 ]]; then
    echo "cohort list is empty in $COHORT_FILE" >&2
    exit 1
fi

IN_LIST="$(printf '%s,' "${COHORT_IDS[@]}")"
IN_LIST="${IN_LIST%,}"

PSQL=(sudo -u postgres psql -d "$DB" -v ON_ERROR_STOP=1)

echo "org_unit_id,display_name"

"${PSQL[@]}" --csv -c "
COPY (
    SELECT ou.id AS org_unit_id, ou.name AS display_name
    FROM heart360tk_schema.org_units ou
    WHERE ou.id IN (${IN_LIST})
    ORDER BY ou.name, ou.id
) TO STDOUT WITH (FORMAT csv, HEADER false);
"

MISSING="$("${PSQL[@]}" -tA <<SQL
SELECT cid
FROM unnest(ARRAY[${IN_LIST}]::integer[]) AS cid
WHERE NOT EXISTS (
    SELECT 1 FROM heart360tk_schema.org_units ou WHERE ou.id = cid
);
SQL
)"

if [[ -n "${MISSING//[$'\n' ]/}" ]]; then
    echo "cohort ids not found in org_units: ${MISSING//$'\n'/ }" >&2
    exit 1
fi
