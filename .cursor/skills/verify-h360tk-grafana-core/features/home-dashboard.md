# Home dashboard

Landing Grafana dashboard for HEARTS360 in grafana_core. It is a **router**, not a lasting content page.

## Sub-features

- `home-loads` — Opening Home UID loads the Home dashboard (briefly)
- `home-redirect` — Global/admin users are redirected to Hypertension Program
- `home-nav` — Redirect lands on a program dashboard the user can navigate (tabs / further UIDs)

## How to get to it (user POV)

- Open Grafana, sign in, go to Home dashboard UID `heart360-home`
- Direct URL: `http://127.0.0.1:3000/d/heart360-home/` (slug may show as `/home`)

## Driving it with browser

Preconditions: stack launched; doctor OK; README Grafana credentials.

- Action: open login URL → sign in (Skip password change if prompted) → open `/d/heart360-home/`
- Observe:
  - Home may flash a “Loading…” text panel, then `window.top.location.replace` to `/d/heart360_drilldown` for global/admin (`UserIsGlobal=1`), or to a facility-scoped hypertension URL when facility vars resolve
  - After ~3s fallback, still on Home also redirects to hypertension
  - Final proof for admin verify is landing on **Hypertension Program**, not a persistent Home chrome
- Evidence: URL before/after redirect (or early + late screenshots); do not treat Hypertension alone as proof that Home was never opened — record the Home navigation that caused the redirect

## Gotchas

- Port `3000` may already be used by demo/central — doctor will fail; stop the other stack
- First boot can take minutes while images pull
- Source: `grafana_provisioning/dashboards/HEARTS360 Dashboards/heart360.home.json` (HTML/JS router panel)
