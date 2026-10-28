<!-- Copy of h360-toolkit-internal/_bmad-output/planning-artifacts/tracks/screening-cascade-demo/IMPLEMENTATION-NOTES.md. Script paths are relative to that track. -->
---
title: Screening cascade demo — implementation notes (handover)
track: screening-cascade-demo
updated: 2026-10-27
status: built-locally-not-committed
---

# Implementation notes — read this before you change the Overview row

Any agent changing the Hypertension Overview row on `demo/cascade-cohort` should start here.

## Where it is

| Thing | Value |
|---|---|
| Checkout | `/Users/tony/Documents/GitHub/h360tk_grafana_core-demo` |
| Branch | `demo/cascade-cohort` (local changes, **not committed, not pushed**) |
| Rollback | `demo/screening-cascade-vertical` / `ca7c024` (vertical cards) |
| Dashboard file | `grafana_provisioning/dashboards/HEARTS360 Dashboards/heart360.hypertension-diabetes.program.json` (Grafana v2 schema: `spec.elements` + `spec.layout`) |
| Seed | `test_data/demo/seed_screening_cascade.sql` |
| Live | http://127.0.0.1:3000/d/heart360_showcase (Hypertension tab → Overview indicators) |
| Approved audit | [ux/AUDIT-overview-cascade.md](ux/AUDIT-overview-cascade.md) |
| Target sample | [ux/imports/sample-cascade-card.webp](ux/imports/sample-cascade-card.webp) |
| Result | [overview-cascade-final.png](overview-cascade-final.png), [diabetes-check.png](diabetes-check.png) |

## What the Overview row is now

| Grid | Element | Plugin | Content |
|---|---|---|---|
| x=0 w=16 h=9 | `panel-stc` | `marcusolsson-dynamictext-panel` 6.3.0 | One section titled **Screening-to-treatment cascade**. Inside it are two horizontal charts, **Screening cascade** and **Treatment cascade**, split by a thin divider. |
| x=16 w=8 h=9 | `panel-1` | `volkovlabs-echarts-panel` 7.2.5 | **Patients protected from heart attacks and strokes**: a green headline (`3,320 patients`) plus the controlled-BP trend. |

The cascade is one Grafana panel on purpose. One border and one title make the two charts read as one section. Two panels would each get their own border and title.

## Data contract

**Screening cascade:**

- Seed only, from `heart360tk_schema.demo_screening_cascade`, row `id=1`: eligible 30,500, screened 14,030 (46%), suspected 7,320 (24%), target 46.
- Nationwide. It does **not** follow the location filter. The tag `Demo data · nationwide` says so on screen.

**Treatment cascade:**

- Live, for the selected place and `${reference_month}`:
  - Registered = `SUM(heart360_patients_registered.cumulative_number_of_patients)`
  - Under care = `SUM(nb_patients_under_care_registered_before_the_past_3_months)`
  - Controlled = `SUM(nb_patients_controlled)`
- Denominator is `${estimated_htn_population}` (14,500). **Never use 30,500 here.**
- Percents and thousands formatting are computed in SQL (`*_pct`, `*_n` columns). The template only prints.

**Patients protected:**

- `panel-1`'s **original SQL, unchanged** (controlled per `ref_month`, org filter, `isAllowed`). Only the visualisation changed.
- The headline is the last point of the same series inside the dashboard time range, so it always equals the line's last point.
- Nationwide, October 2026, the cascade's controlled and the headline both read 3,320.

## Known facts a presenter should know

- Controlled drops from 3,901 (September 2026) to 3,320 (October 2026). The trend shows that dip honestly.
- Registered (8,252) is larger than suspected hypertension (7,320). They are different groups, so there is no arrow between the two charts.
- When a facility is selected, treatment percents fall near 0%. `estimated_htn_population` is a nationwide 14,500, and the old treatment cascade behaved the same way. Demo nationwide.

## How to rebuild or re-apply

1. **Load or refresh the seed** (idempotent):
   ```bash
   docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d heart360tk_database -v ON_ERROR_STOP=1' < test_data/demo/seed_screening_cascade.sql
   ```
2. **Re-apply the dashboard changes.** [scripts/apply_overview.py](scripts/apply_overview.py) holds the full SQL, HTML, CSS, and ECharts code:
   ```bash
   python3 scripts/apply_overview.py "<checkout>/grafana_provisioning/dashboards/HEARTS360 Dashboards/heart360.hypertension-diabetes.program.json"
   ```
   - Run it against the **local draft** JSON. It expects the element `panel-stc` to exist, which `ca7c024` does not have.
   - It writes `ensure_ascii=True` so unrelated `≥` escapes do not churn the diff.
3. **Reload.** Grafana re-provisions the file within about 20 s. If it does not, run `docker restart grafana`.
4. **Screenshot.** Run `screenshot-overview.cjs` (Playwright, local demo login).

## Rules to keep

- Do not change: the Diabetes tab, other Hypertension rows, `estimated_htn_population`, Docker images, `main` / 0.6.1.
- Do not copy from the Simple screenshot: the Option A/B/C strip, River District, or 250,800.
- Do not commit `.env` or `test_data/demo/out/shifted_PHC-*.xlsx`.
- Changed elements in this pass: `panel-stc`, `panel-1`, and the removal of unused `panel-screening`. `panel-cascade` (the old native treatment cascade) is still defined but not placed on the grid. It causes the harmless "conversion data loss" log line.
- Dynamic text `renderMode` must be `everyRow`. Other values render blank fields.
