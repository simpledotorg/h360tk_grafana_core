# Drug Stock Google Sheet response contract (Story 1.2)

Transport-only capture pipe for leaf pull ingest (Story 1.3). This repo documents the column contract; Sheet IDs and service accounts stay in deploy secrets.

## Response tab header (row 1, exact names)

| Column | Required | Type / notes |
|--------|----------|----------------|
| `org_unit_id` | yes | Integer `org_units.id` from the Form facility question stored value |
| `reporting_month` | yes | Reporting month for the submission (Form value; ingest normalizes to `yyyy-mm-01`) |
| `drug_code` | yes | RxNorm code (`rxnorm_code`) from `heart360tk_schema.active_stock_tracked_drugs` |
| `in_stock` | yes | Numeric on-shelf count; see tri-state rules below |
| `submitted_at` | no | Timestamp when the row was captured (Form submit or Sheet `=NOW()` if ops add it) |

Canonical one-line header (tab-separated for paste):

```
org_unit_id	reporting_month	drug_code	in_stock	submitted_at
```

## Row grain

One row per **facility × reporting month × protocol drug** submission line. A single Form submit that answers six In-Stock questions produces up to six Sheet rows sharing the same `org_unit_id`, `reporting_month`, and `submitted_at`.

## `drug_code`

Always the programme’s **`rxnorm_code`** for stock-tracked protocol drugs (not display name, not internal surrogate keys). The active set comes from `heart360tk_schema.active_stock_tracked_drugs` for the leaf `active_programme` deploy setting.

## `in_stock` tri-state (storage semantics for ingest)

| Sheet / Form value | Meaning |
|--------------------|---------|
| blank (empty cell) | **Unknown** — must ingest as SQL `NULL`, never coerced to zero |
| `0` | **Explicit zero** — none on shelf |
| positive number | Count on shelf |

There are **no** `received`, **no** `consumption`, and **no** other stock columns in the MVP contract.

## Facility key

`org_unit_id` must resolve to `heart360tk_schema.org_units.id`. Display names on the Form are not stored on the Sheet.
