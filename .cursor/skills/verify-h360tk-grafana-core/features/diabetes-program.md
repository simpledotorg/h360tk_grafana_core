# Diabetes program

Diabetes program dashboard (blood sugar control / program reach).

## Sub-features

- `dm-loads` — Diabetes dashboard renders
- `dm-panels` — Key panels visible without query errors

## How to get to it (user POV)

- From Grafana after login, open Diabetes Program (or the Diabetes Dashboard tab)
- Direct URL: `http://127.0.0.1:3000/d/heart360_drilldown_diabetes/diabetes-program`

## Driving it with browser

Preconditions: stack launched; doctor OK; signed into Grafana.

- Action: navigate to diabetes UID URL
- Observe: title **Diabetes Program**; diabetes panels load; no panel error state
- Evidence: screenshot with title visible

## Gotchas

- Do not use the hypertension UID as a substitute proof
- Live slug is `diabetes-program`; UID-only `/d/heart360_drilldown_diabetes/` also works
