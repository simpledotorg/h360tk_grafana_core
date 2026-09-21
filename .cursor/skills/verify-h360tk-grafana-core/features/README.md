# h360tk_grafana_core verification map

Maintained source for verifying user-facing behavior of the **main code** stack. Read this index, then the matching feature file.

## Baseline preconditions

- Repo root: `h360tk_grafana_core`
- `docker compose up -d` succeeded; doctor checks pass
- No other compose stack bound to host ports `3000` / `8080`, and no foreign containers holding fixed names `grafana` / `postgres` / `filebrowser-quantum`
- Grafana admin credentials from this repo’s README
- Evidence dir: `.cursor/skills/verify-h360tk-grafana-core/evidence/<run-id>/`

## Driving conventions

- Start from Grafana login unless a feature says otherwise
- Prefer dashboard UID URLs over hunting the sidebar
- Do not report a different dashboard as proof for a skipped one (Home is a special case: it intentionally redirects — see home-dashboard.md)

## Features

- [Home dashboard](./home-dashboard.md)
- [Hypertension program](./hypertension-program.md)
- [Diabetes program](./diabetes-program.md)
- [Overdue patients](./overdue-patients.md)
- [Admin dashboard refresh](./admin-dashboard-refresh.md)
- [File upload](./file-upload.md)
