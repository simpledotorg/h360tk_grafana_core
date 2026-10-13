# Demo PHC upload data

Deterministic synthetic and date-shifted PHC spreadsheets for local demo ingest.

## Regenerate

From the repository root:

```bash
python3 test_data/demo/build_demo_data.py
```

Optional as-of date (defaults to today when run in October 2026, otherwise `2026-10-13`):

```bash
python3 test_data/demo/build_demo_data.py --as-of 2026-10-13
```

## Outputs

- `out/shifted_*.xlsx` — source PHC files shifted so the latest visit falls in the as-of month.
- `demo_generated.xlsx` — ~1500 synthetic HTN patients with multi-visit rows.
- `verify_demo.sql` — post-ingest assertions for cascade and cohort reporting tables.

After ingest and a reporting refresh, run:

```bash
psql "$DATABASE_URL" -f test_data/demo/verify_demo.sql
```
