# Overdue patients

Overdue patients line-list style dashboard for follow-up outreach.

## Sub-features

- `overdue-loads` — Overdue dashboard renders
- `overdue-list` — List/table panels present (may be empty without PII-bearing data or without facility scope)

## How to get to it (user POV)

- From Grafana after login, open Overdue Patients (or the Overdue Patient List tab)
- Direct URL: `http://127.0.0.1:3000/d/heart360_drilldown_overdue/overdue-patients`

## Driving it with browser

Preconditions: stack launched; doctor OK; signed into Grafana.

- Action: open overdue UID URL
- Observe: **Overdue Patients** dashboard chrome; panels load; banner may state list is only available at facility / sub-facility levels when those vars are unset
- Evidence: screenshot with title visible

## Gotchas

- Useful overdue lists need facility-level filters and optional PII fields in source data; empty list ≠ broken dashboard
- Live slug is `overdue-patients`
