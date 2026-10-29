<!-- Copy of h360-toolkit-internal/_bmad-output/planning-artifacts/tracks/screening-cascade-demo/IMPLEMENTATION-NOTES.md (branch screening-cascade-demo-track). Script paths are relative to that track. -->
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

- Live, for the selected place in the **latest completed month** (`${reference_month}` − 1 month; Sep 2026 in the demo):
  - Registered = `SUM(heart360_patients_registered.cumulative_number_of_patients)`
  - Under care = `SUM(nb_patients_under_care_registered_before_the_past_3_months)`
  - Controlled = `SUM(nb_patients_controlled)`
- Denominator is `${estimated_htn_population}` (14,500). **Never use 30,500 here.**
- Percents and thousands formatting are computed in SQL (`*_pct`, `*_n` columns). The template only prints.

**Patients protected:**

- `panel-1`'s **original SQL, unchanged** (controlled per `ref_month`, org filter, `isAllowed`). Only the visualisation changed.
- The headline is the last point of the same series inside the dashboard time range, so it always equals the line's last point.
- The headline is the **latest completed month** (second-to-last point). The running month is drawn dashed.
- Nationwide for Sep 2026, the cascade's controlled, the headline and the `# Controlled BP` card all read 3,901.

## Known facts a presenter should know

- Every headline on the Hypertension tab uses the latest completed month (Sep 2026). October is still running and is shown dashed.
- The cascade's "Patients under care" (6,523) uses `nb_patients_under_care_registered_before_the_past_3_months`, the same measure as the old treatment cascade. The Patients under care headline (7,363) uses `nb_patients_under_care`. Both are unchanged definitions, but the numbers differ.
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
| `panel-stc` | Removed the sub-titles, the `Denominator:` lines and the tags. Added the denominator footers. Rows read `Screened individuals` and `Suspected for hypertension`. Treatment bars use hearts360 colours. Rows line up across both halves. The target arrow sits on the dashed target line. (Custom HTML/CSS.) |
| `panel-1` | Headline and subtitle aligned with the panel title (left 12). hearts360 green. `Mon-YYYY` month labels. Y-axis ticks like `4,000`. Bottom inset 14 px. (ECharts code.) |
| `panel-outcomes` | **New (2026-10-28).** Replaces `panel-2/3/4` and the six stat blocks `panel-14…19`, which are removed. One ECharts card, `Hypertension treatment outcomes`, at x=0 w=24 h=13. It opens with `Outcomes for N patients under care (registered before D) between D to D`, the 3-month window ending in the latest completed month. Then three columns on one background, each with a coloured title, a big percent and an `N patients with …` line, above its 0–100% trend with the running month dashed. One SQL returns monthly controlled, uncontrolled, no-visit and denominator counts. The denominator is the same as the old panels: total − newly registered − 12-month LTFU. Sep 2026: 60% / 3,901, 31% / 2,025, 9% / 597 of 6,523. If any title wraps, the content below moves down 18 px. Patients under care and 12-month LTFU now sit at y=13. |
| `panel-2/3/4` (removed) | Earlier pass: per-point value labels off. Points always shown. 0–100% axis. Light fill. hearts360 colours. The dashed `Current Month` series is hidden from the legend but stays on the chart. |
| `panel-14…19` | **Latest completed month.** The SQL subtracts 1 month from `MAX(ref_month)`, which is the running month. For example, Sep 2026: 60% / 3,901, 31% / 2,025, 9% / 597. hearts360 colours. Count cards use unit `locale`. |
| `panel-7` | **Now ECharts, same SQL.** Purple headline: under care in the latest completed month. Then `N patients registered in Mon-YYYY` and `of N cumulative registered patients` (in blue). Below that, the trend: cumulative and under-care lines, monthly registration bars, and the running month dashed. Height 8 → 10. |
| `panel-8` | **Now ECharts.** The SQL adds `lost_n` and `total_n` columns; the percent is unchanged. Red headline: LTFU % for the latest completed month (one decimal under 10%). Then `N patients with no visit from Mon-YYYY to Mon-YYYY` and `of N cumulative registered patients`. 0–100% axis at 25% steps. The running month is dashed. Height 8 → 10. |
| `panel-cohort` | **Rebuilt as dynamic text (HTML/CSS), like hearts360**, with renderMode `allRows`. Slim 56 px bars, 250 px tall. Green on top. Centred white bold percents; segments under 5% have no label. Under each bar: `Q2-2026 cohort` / `1,003 patients` / grey `Result from latest visit in Q3-2026`. Legend key at the bottom right. Hover a segment to see its count. Height 12. |
| `panel-12` | Count columns use unit `locale`. Percent text uses hearts360 colours. |

**Cohort SQL** (new query, same data):

- Counts come from `HEART360_COHORT_PATIENT_DETAILS`, with the same quarters, location filter and `isAllowed` check.
- **Unfinished cohorts.** `WHERE q.q + 6 months <= reference_month + 1 month` hides cohorts whose follow-up quarter has not ended.
- **Pre-formatted text.** The SQL returns labels, heights and counts as text, so the template only prints.

**Why the cohort chart is HTML:**

- Grafana's native bar chart puts stacked labels on the segment edge.
- It draws `text.valueSize` at half size on 2× (retina) screens. This was confirmed at 1280 px, scale 2.
- It allows one line of text under a bar. Two lines and tilted labels were both tried, and both clip.
- Tony approved the HTML rebuild on 2026-10-28.

**Known limits:**

- **Panel title size** is global in Grafana and was not changed.

## Diabetes tab, hearts360 style (Story 1.6, 2026-10-29)

**Reference:** hearts360 `diabetes.html`. Script: [scripts/apply_dm_hearts360_style.py](scripts/apply_dm_hearts360_style.py). It touches only `panel-dm-*` and the Diabetes tab layout.

| Panel | Change |
|---|---|
| `panel-dm-13` | **ECharts**, titled `DM patients with controlled BP`, x=0 w=12 h=10. Shows `62%  839 patients with BP <140/90` (green), `27%  367 patients with BP <130/80` (dark green `#096301`), and grey `of 1,352 patients under care (registered before 1-Jul-2026) in Sep-2026`. Below that, a two-line trend. **Note:** in `HEART360_DM_BP_CONTROL`, the `bp_controlled_140_90` column counts only patients *not* also under 130/80, so <140/90 = `bp_controlled_140_90 + bp_controlled_130_80`. This is the same formula the old panel used. |
| `panel-dm-outcomes` | **New**, titled `DM treatment outcomes`, w=24 h=13. Replaces `panel-dm-2/3/4` and `panel-dm-7…12`, which are removed. One SQL joins `HEART360_BLOOD_SUGAR_CONTROLLED`, `…_SEVERITY` and `…_MISSED_VISITS` by month; all three share `diabetes_patients_under_care` as the denominator. It opens with `Outcomes for 1,352 patients under care (registered before …) between … to …`. Three columns: controlled (big `10%`, `141 patients with RBS <140, FBS <126 mg/dL or HbA1c <7%`); not controlled (two figure lines, `29%` moderate in amber and `31%` high in dark amber `#c08b00`, over stacked bars with the running month faded); no visit (big `30%`, `399 patients with no visit`). The denominator really does exclude patients registered in the past 3 months: the view filters `registration month + 3 months <= ref_month`. |
| `panel-dm-14` | **ECharts**, using the shared `under_care_js()` with the Diabetes columns. Sep 2026: `1,478`, `0 patients registered`, `of 1,740 cumulative registered patients`. w=16 h=10. |
| `panel-dm-15` | **ECharts**, using the shared `LTFU_JS`. The SQL gains `lost_n` and `total_n` columns. Sep 2026: `15%`, `262 patients with no visit from Oct-2025 to Sep-2026`, `of 1,740`. Width 7 → **8** (fixes the gap), h=10. |
| `panel-dm-102` | `nb_*` columns use unit `locale`. Percent colours use the hearts360 tokens. |

**Not built**, because Grafana has no matching panels or data: statins, opportunistic screening, the Diabetes quarterly cohort, drug stock, comorbidity.

**Shared code.** [scripts/h360_style_common.py](scripts/h360_style_common.py) holds:
- the hearts360 colours
- `fixed` and `set_prop`
- `ECHARTS_JS_COMMON`
- `under_care_js(cum, uc, new)`
- `LTFU_JS`

`apply_hearts360_style.py` imports it. After the refactor, its output was proven byte-identical to `dbf7984`.

**Run order:**
1. `apply_overview.py`
2. `apply_hearts360_style.py`
3. `apply_dm_hearts360_style.py`

All three are idempotent. The Diabetes script leaves every non-`panel-dm-*` element, the Hypertension tab and the Overdue tab byte-identical. This was verified.

**Console note.** One 404 on the Diabetes tab, `/apis/userstorage…/volkovlabs-table-panel:…`, is the table plugin looking up saved user preferences. It is harmless and not from these panels.

## Rules to keep

- Do not change: the Diabetes tab, `panel-dm-*`, the Overdue list, `estimated_htn_population`, Docker images, `main` / 0.6.1.
- Do not copy from the Simple screenshot: the Option A/B/C strip, River District, or 250,800.
- Do not commit `.env` or `test_data/demo/out/shifted_PHC-*.xlsx`.
- Changed elements in this pass: `panel-stc`, `panel-1`, and the removal of unused `panel-screening`. `panel-cascade` (the old native treatment cascade) is still defined but not placed on the grid. It causes the harmless "conversion data loss" log line.
- Dynamic text `renderMode` must be `everyRow`. Other values render blank fields.
