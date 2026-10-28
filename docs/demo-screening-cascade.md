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
| x=0 w=16 h=9 | `panel-stc` | `marcusolsson-dynamictext-panel` 6.3.0 | One section titled **Screening-to-treatment cascade**. It holds two horizontal cascades (screening on the left, treatment on the right), split by a thin divider. They have no sub-titles. Each half ends with a denominator footer: `100% = 30,500 eligible adults aged 15+` and `100% = 14,500 estimated adults with hypertension`. |
| x=16 w=8 h=9 | `panel-1` | `volkovlabs-echarts-panel` 7.2.5 | **Patients protected from heart attacks and strokes**: a green headline (`3,320 patients`) plus the controlled-BP trend. |

The cascade is one Grafana panel on purpose. One border and one title make the two charts read as one section. Two panels would each get their own border and title.

## Data contract

**Screening cascade:**

- Seed only, from `heart360tk_schema.demo_screening_cascade`, row `id=1`: eligible 30,500, screened 14,030 (46%), suspected 7,320 (24%), target 46.
- Nationwide. It does **not** follow the location filter. Tony asked to remove the on-screen `Demo data · nationwide` tag, so this is now stated only in the panel description (i).

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
2. **Re-apply the dashboard changes.** Run both scripts, in this order:
   ```bash
   python3 scripts/apply_overview.py "<dashboard json>"
   python3 scripts/apply_hearts360_style.py "<dashboard json>"
   ```
   - `apply_overview.py` builds the Overview row: the cascade SQL, HTML and CSS, and the Patients protected ECharts code.
   - `apply_hearts360_style.py` applies the hearts360 look to the rest of the Hypertension tab. Every change uses native Grafana options (see below).
   - Both are idempotent. Run them on a dashboard that already has `panel-stc`: commit `8c4f5ef` or later. `ca7c024` does not have it.
   - Both write `ensure_ascii=True` so unrelated `≥` escapes do not churn the diff.
3. **Reload.** Grafana re-provisions the file within about 20 s. If it does not, run `docker restart grafana`.
4. **Screenshot.** Run `screenshot-overview.cjs` (Playwright, local demo login).

## hearts360 style pass (Story 1.5, 2026-10-28)

**Reference:** https://github.com/simpledotorg/hearts360 (`css/template.css`, `index.html`).

**Colour tokens** (one map at the top of `apply_hearts360_style.py`):

| Measure | Hex |
|---|---|
| Controlled | `#3bb231` |
| Uncontrolled | `#eeab00` |
| No visit (3 months) | `#ed6300` |
| 12-month LTFU | `#ff3355` |
| Under care | `#b51bdc` |
| Registrations | `#007ee4` |
| Estimated | `#dae0e1` |

| Panel | Change (native options unless noted) |
|---|---|
| `panel-stc` | Removed the sub-titles, the `Denominator:` lines and the tags. Added the denominator footers. Treatment bars use hearts360 colours. Rows line up across both halves. (Custom HTML/CSS.) |
| `panel-1` | Headline and subtitle aligned with the panel title (left 12). hearts360 green. `Mon-YYYY` month labels. Y-axis ticks like `4,000`. (ECharts code.) |
| `panel-2/3/4` | Per-point value labels off. Points always shown. 0–100% axis. Light fill. hearts360 colours. The dashed `Current Month` series is hidden from the legend but stays on the chart. |
| `panel-14…19` | hearts360 colours. Count cards use unit `locale` (`3,320`). |
| `panel-7` | Value labels off. Unit `locale`. Registrations blue, under care purple. |
| `panel-8` | Value labels off. 0–100%. `#ff3355`. |
| `panel-cohort` | Renamed `Quarterly cohort reports`. hearts360 colours. Value labels always on, at 14 px. Value axis hidden and scaled 0–1. Bars wider. Legend reads `BP controlled` / `BP uncontrolled` / `No visit in quarter`. (SQL: see below.) |
| `panel-12` | Count columns use unit `locale`. Percent text uses hearts360 colours. |

**Cohort SQL changes:**

- **Label.** Each cohort label is `Q2-2026 · n=1,003`, where n is the number of patients registered in that quarter.
  - A two-line label was tried: Grafana clips the second line.
  - A label with the full word "patients" was tried: it clips at the right edge.
- **Unfinished cohorts.** `WHERE q.q + 6 months <= reference_month + 1 month` hides cohorts whose follow-up quarter has not ended. Before this, Q4-2026 showed a false 100% "no visit".

**Known native limits:**

- **Cohort labels.** Grafana places stacked-bar value labels at the top edge of each segment and draws them in the theme text colour (not white). A very small segment collides with its neighbour's label, for example `6%` and `35%` on Q2-2026.
- **Panel title size** is global in Grafana and was not changed.

## Rules to keep

- Do not change: the Diabetes tab, `panel-dm-*`, the Overdue list, `estimated_htn_population`, Docker images, `main` / 0.6.1.
- Do not copy from the Simple screenshot: the Option A/B/C strip, River District, or 250,800.
- Do not commit `.env` or `test_data/demo/out/shifted_PHC-*.xlsx`.
- Changed elements in this pass: `panel-stc`, `panel-1`, and the removal of unused `panel-screening`. `panel-cascade` (the old native treatment cascade) is still defined but not placed on the grid. It causes the harmless "conversion data loss" log line.
- Dynamic text `renderMode` must be `everyRow`. Other values render blank fields.
