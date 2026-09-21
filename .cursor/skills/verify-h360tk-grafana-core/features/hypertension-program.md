# Hypertension program

Hypertension program dashboard (BP control / program reach).

## Sub-features

- `htn-loads` — Hypertension dashboard renders
- `htn-panels` — Key panels visible without query errors

## How to get to it (user POV)

- From Grafana after login, open Hypertension Program (also the Home redirect target for global/admin)
- Direct URL: `http://127.0.0.1:3000/d/heart360_drilldown/hypertension-program`

## Driving it with browser

Preconditions: stack launched; doctor OK; signed into Grafana.

- Action: navigate to hypertension UID URL above
- Observe: breadcrumb/title **Hypertension Program**; tabs for Diabetes / Overdue; overview panels render (empty/“No data” is OK if no upload+refresh yet; panel query errors are not)
- Evidence: screenshot showing title + at least one panel

## Gotchas

- Empty database still “works” if panels load; do not claim indicator values without uploaded+refreshed data
- UID is `heart360_drilldown`; live slug is `hypertension-program` (older bookmarks like `hearts360-hypertension-dashboard` may still resolve via UID)
- In-dashboard tab HTML still links with legacy slug suffixes (`…/hearts360-diabetes-dashboard`, `…/hearts360-overdue-patients`); prefer the UID paths in this map
- Region/District variable warnings on a fresh empty org tree are expected; they are not panel query failures
