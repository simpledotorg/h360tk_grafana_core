# File upload

Web upload surface for patient line lists into grafana_core (FileBrowser Quantum).

## Sub-features

- `upload-ui` — FileBrowser UI reachable on host port 8080
- `upload-file` — Operator can upload a sample file from `test_data/` when present

## How to get to it (user POV)

- Open `http://127.0.0.1:8080/` (README “upload file” entry)
- Login with README FileBrowser credentials if prompted (`admin` / `admin`)

## Driving it with browser

Preconditions: stack launched; doctor shows upload HTTP OK.

- Action: open `http://127.0.0.1:8080/` (may redirect to `/login`); sign in with README FileBrowser credentials if the login form appears; click **ACKNOWLEDGE** on the first-boot “new database” welcome modal if shown; open **add** → **Upload**; set the file on the Upload dialog’s `input[type=file]` (the OS filechooser event often does not fire — prefer `setInputFiles` on the dialog input). Sample: `test_data/H360_TEST_DATASET_40pts_May28 (1).xlsx`
- Observe: file browser UI loads; uploaded filename appears in the listing (and under `data/upload/` on disk)
- Evidence: screenshot of UI; if upload performed, listing showing filename

## Gotchas

- Ingest completion is asynchronous (inotify/processor); wait before asserting dashboard numbers
- Do not claim DB ingestion or graph updates from upload UI alone — use Admin · Dashboard Refresh (or wait for hourly job) plus a dashboard panel check
- Fresh FileBrowser may show a welcome modal about `server.database`; acknowledge and continue
- Re-uploading the **same filename** that already exists shows **Conflicts detected**; use a uniquely named copy (or clear/overwrite) when proving a fresh upload
