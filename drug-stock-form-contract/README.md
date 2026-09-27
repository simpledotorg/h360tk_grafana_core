# Drug Stock Form and Sheet contract (Story 1.2)

Ops-facing artifacts to build the Google Form and response Sheet without Grafana access. **No Google API calls from this repo** — create the live Form/Sheet in Workspace manually using these contracts.

## Data shapes

| Artifact | Shape |
|----------|--------|
| Form facility choice | `{ org_unit_id, display_name }` where `display_name` is `org_units.name` |
| Sheet row | `{ org_unit_id, reporting_month, drug_code, in_stock, submitted_at? }` with `drug_code` = `rxnorm_code` |

## Maintain the facility cohort

1. Edit `cohort_org_unit_ids.txt` — one `org_units.id` per line (comments with `#` allowed).
2. Exclude community-size sites by **omitting** their ids. There is no facility-size column on `org_units`; curation is explicit.
3. Export choices from leaf Postgres:

```bash
export PGDATABASE=your_leaf_db   # or DRUG_STOCK_FORM_PGDATABASE
./pg_init_scripts/export_drug_stock_form_choices.sh
```

4. In Google Forms, set each facility option **label** to `display_name` and **value** (if using quiz/import) to `org_unit_id`.

## Sheet setup

1. Create a response Sheet tab whose first row matches `sheet_response_header.tsv` / [SHEET_CONTRACT.md](./SHEET_CONTRACT.md).
2. Wire Form responses into long-format rows (one row per drug) per Story 1.3 ingest expectations, or use an ops script outside this repo.

## Form question order

See [FORM_SPEC.yaml](./FORM_SPEC.yaml): facility → reporting month → one optional numeric In-Stock question per row in `active_stock_tracked_drugs` (sorted CCB → ARB → Diuretic → Other).

## Verification

```bash
./pg_init_scripts/migrations/verify_drug_stock_form_sheet_contract.sh
```

## Live Google Form

Creating the hosted Form/Sheet requires Google Workspace credentials and Sheet ID — **not committed here**. Treat live Form creation as **BLOCKED** until ops supplies secrets in deploy env (Story 1.3 / demo env).
