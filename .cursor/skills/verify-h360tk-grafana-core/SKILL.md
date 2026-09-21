---
name: verify-h360tk-grafana-core
description: Verify the HEARTS360 grafana_core stack (Grafana dashboards + file upload) by launching Docker Compose, driving the real UI surfaces, and capturing evidence. Use when proving dashboard or ingest behavior in h360tk_grafana_core.
---

# Verify h360tk_grafana_core

Agent-facing control skill for the **main HEARTS360 code** repository. Drive the real containers; do not pretend via unit tests alone.

## Launch

From the repo root:

```bash
docker compose up -d
```

Ready when:

- `curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/login` returns `200` (or Grafana login HTML).
- `curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/` returns a success HTTP code for FileBrowser.

Default surfaces (see README):

- Grafana: `http://127.0.0.1:3000`
- Upload UI: `http://127.0.0.1:8080/`

Auth: use the admin credentials documented in this repo’s README (do not invent new ones). Prefer reading README over hardcoding in chat logs. First Grafana login may show **Update your password** — choose **Skip** for routine verify.

Teardown:

```bash
docker compose down
```

Do not `docker compose down -v` during routine verify unless the recipe explicitly needs a clean DB (destroys data).

## Doctor

Run after launch (or when anything looks off):

```bash
docker compose ps
curl -sf -o /dev/null -w "grafana:%{http_code}\n" http://127.0.0.1:3000/login
curl -sf -o /dev/null -w "upload:%{http_code}\n" http://127.0.0.1:8080/
```

Require: `grafana` and upload containers Up; both HTTP checks not connection-refused. If ports collide with another H360 stack (demo/central/poc), stop that other stack first — this compose binds host `3000` and `8080`. Fixed `container_name` values (`grafana`, `postgres`, `filebrowser-quantum`, …) also collide across H360 compose projects even when ports differ; free those names before `up`.

Importer/exporter may restart when leaf env vars are unset; that does not block dashboard or upload doctor checks.

## Drive

Primary harness: **browser** (Playwright/CDP or Cursor browser tools) against Grafana and FileBrowser.

Stable entry URLs (dashboard UIDs from provisioning; slugs from live Grafana search API):

| Feature | URL path |
|---------|----------|
| Home (router) | `/d/heart360-home/` |
| Hypertension | `/d/heart360_drilldown/hypertension-program` |
| Diabetes | `/d/heart360_drilldown_diabetes/diabetes-program` |
| Overdue | `/d/heart360_drilldown_overdue/overdue-patients` |
| Admin refresh | `/d/heart360-admin-refresh/` |

Login to Grafana via the login form, then open the path. Prefer role/name selectors on Grafana chrome; treat panel titles as observable proof. UID-only paths (`/d/<uid>/`) also work.

Upload path: open FileBrowser at `:8080` (login with README credentials if redirected), ACKNOWLEDGE the welcome modal if shown, then **add → Upload** and set a file from `test_data/` on the dialog’s file input (see `features/file-upload.md`).

## Evidence

Store under `.cursor/skills/verify-h360tk-grafana-core/evidence/<run-id>/` (create as needed). Keep after cleanup.

Proof standards:

- Real user path (browser login → dashboard or upload → visible result).
- Capture action + resulting state (screenshot of dashboard with title visible; HTTP status alone is insufficient for UI claims).
- For ingest claims: show file accepted and a dashboard panel or DB row reflecting data (not only upload 200). After upload, numbers still need Admin · Dashboard Refresh (or the hourly job) before graphs update.

## Cleanup

```bash
docker compose down
```

Never delete the `evidence/` directory. Kill only compose projects started for this run (`docker compose down` in this repo).

## Helpers

None shipped yet. Prefer `docker` / `curl` / browser tools as above.

## Feature map

See [features/README.md](features/README.md).
