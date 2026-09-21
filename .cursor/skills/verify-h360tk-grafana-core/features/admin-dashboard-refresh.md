# Admin dashboard refresh

Admin-only surface to manually refresh reporting tables so dashboards show newly ingested data without waiting for the hourly job.

## Sub-features

- `admin-refresh-loads` — Admin · Dashboard Refresh dashboard renders for admin
- `admin-refresh-gate` — Non-admin users see Access Denied (do not claim this without a non-admin session)

## How to get to it (user POV)

- Open Admin · Dashboard Refresh after login
- Direct URL: `http://127.0.0.1:3000/d/heart360-admin-refresh/` (live slug may resolve to `admin-c2b7-dashboard-refresh`; UID path is enough)

## Driving it with browser

Preconditions: stack launched; doctor OK; signed in as README Grafana **admin**.

- Action: open admin refresh UID URL
- Observe: title includes **Dashboard Refresh**; refresh controls / status panels visible for admin
- Evidence: screenshot with title visible
- Optional: click refresh only when intentionally testing ingest end-to-end (can be slow)

## Gotchas

- Upload alone does not update graphs; this page (or the hourly refresh) is required — see README
- Source: `grafana_provisioning/dashboards_admin/heart360.admin.refresh.json` (UID `heart360-admin-refresh`)
