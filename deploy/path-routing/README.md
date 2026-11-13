# Path-based routing for H360 instances

Every instance is served from one domain under its own URL path, rather than
needing a subdomain of its own:

| Instance | Dashboard | File upload |
|---|---|---|
| demo | `https://toolkit.hearts360.org/demo/` | `https://toolkit.hearts360.org/demo/upload/` |
| india | `https://toolkit.hearts360.org/india/` | `https://toolkit.hearts360.org/india/upload/` |

---

## 1. What blocked this

**FileBrowser ignored the setting it was given.** Every country compose file
carried `FILEBROWSER_BASEURL=/`, which is not a FileBrowser environment
variable — Quantum documents a short fixed list and the base URL is not among
them. It can only be set in a config file. So FileBrowser ran at its default
base URL of `/` and emitted every asset and API URL at the domain root
(`/static/…`, `/api/…`). Mounted under `/india/upload/` the page loads but
nothing on it works, and the only configuration that worked was giving it a
whole hostname. (`heart360.filebrowser.docker` was a stub carrying the same
dead variable, never wired into the build.)

Two smaller things: Grafana's `GF_SERVER_ROOT_URL` /
`GF_SERVER_SERVE_FROM_SUB_PATH` were set in only two of six country repos and
hardcoded where present, and nothing in version control described the routing
layer at all — see [`edge-alb.md`](edge-alb.md), which is still true of the ALB.

---

## 2. How it works

```
                 toolkit.hearts360.org   (shared ALB: TLS, one rule per instance)
                              |
       /demo/*                |                /india/*
            +-----------------+-----------------+
            |                                   |
   demo box :80                          india box :80
   (heart360tk-proxy)                    (heart360tk-proxy)
            |                                   |
   /demo/        -> grafana:3000        /india/        -> grafana:3000
   /demo/upload/ -> filebrowser:80      /india/upload/ -> filebrowser:80
   /demo/sftp/   -> sftpgo:8080
```

**The prefix is never stripped.** Grafana (`serve_from_sub_path`) and
FileBrowser (`http.baseURL`) both emit absolute URLs containing it and expect
it back, so nothing in front may rewrite the path.

**The ALB forwards, the instance routes.** Each box owns its whole prefix, so
adding a service to an instance is a change to that instance's `.env` alone and
the ALB keeps one rule per instance.

**Country repos ship no routing files.** Both images generate their own config
at container start from `H360TK_*`, so a prefix cannot drift out of sync
between nginx, Grafana and FileBrowser.

### Two images, built here like everything else

| Image | Built from | Generates |
|---|---|---|
| `simpledotorg/heart360tk-proxy` | `docker_build/heart360.proxy.docker` | `/etc/nginx/conf.d/default.conf`, via [`h360tk-render-conf.sh`](../../docker_build/proxy/h360tk-render-conf.sh) |
| `simpledotorg/heart360tk-filebrowser` | `docker_build/heart360.filebrowser.docker` | FileBrowser's `config.yaml`, via [`h360tk-filebrowser-entrypoint.sh`](../../docker_build/filebrowser/h360tk-filebrowser-entrypoint.sh) |

Both are tagged and pushed from the `COMPONENTS` list in
`.github/workflows/getenv.sh`, and country repos pin them with
`HEART360TK_VERSION`. A routing fix ships like any application fix: release in
core, bump the version.

### Environment variables

`heart360tk-proxy`:

| Variable | Default | Meaning |
|---|---|---|
| `H360TK_BASE_PATH` | `""` | Instance prefix, e.g. `/demo`. Empty or `/` serves at the domain root. Accepts `demo` too. |
| `H360TK_ROUTES` | `""` | Space-separated `<segment>=<host>:<port>`, e.g. `upload=filebrowser:80 sftp=sftpgo:8080` |
| `H360TK_UPSTREAM_DASHBOARD` | `grafana:3000` | What answers at the prefix root |
| `H360TK_MAX_BODY_SIZE` | `2g` | `client_max_body_size` |
| `H360TK_RESOLVER` | `127.0.0.11` | Docker's embedded DNS |

`heart360tk-filebrowser`:

| Variable | Default | Meaning |
|---|---|---|
| `H360TK_BASE_PATH` | `""` | Same prefix as the proxy |
| `H360TK_UPLOAD_SEGMENT` | `upload` | Must match the segment in `H360TK_ROUTES` |
| `H360TK_FILEBROWSER_SOURCE` | `/srv` | Directory to serve; must match the `.upload` bind mount |

**Upstreams resolve per request, not at startup.** nginx resolves a literal
upstream name when it parses the config, so one baked-in config naming
`filebrowser` would refuse to start on a central-dashboard box that runs none,
and could lose a race against a slow-starting service. Going through a variable
plus a `resolver` means an absent service 502s that one route and the instance
keeps serving.

---

## 3. Putting an instance on a path

1. In the country repo's `.env`:

   ```sh
   H360TK_BASE_PATH=/india          # no trailing slash
   H360TK_PUBLIC_DOMAIN=toolkit.hearts360.org
   H360TK_PUBLIC_SCHEME=https
   H360TK_PROXY_PORT=80             # the port the ALB target group points at
   ```

2. Copy the `proxy` service and the Grafana / FileBrowser settings from a
   country repo that already has them. There are no config files to copy.

3. On the ALB, add a target group on the proxy's port with health check path
   `/healthz`, and one listener rule matching `/<instance>` and `/<instance>/*`.
   [`edge-alb.md`](edge-alb.md) has three details that will otherwise bite.

4. Load `/india/` in a browser with devtools open: **no request may 404, and
   none may go to the domain root.** An asset fetched from `/` rather than
   `/india/` means a base URL is wrong on the instance.

To see what was generated:

```sh
docker compose exec proxy       cat /etc/nginx/conf.d/default.conf
docker compose exec filebrowser cat /home/filebrowser/data/config.yaml
docker compose logs proxy filebrowser | grep h360tk-
```

---

## 4. Caveats

* **SFTPGo needs `SFTPGO_HTTPD__WEB_ROOT`** set to the same `<prefix>/sftp`
  the proxy routes there, or its web UI serves from the domain root. The docs
  describe `web_root` with no example and publish no reverse-proxy guide, so it
  was worth checking: confirmed on a real instance, URLs and assets all come
  back under the prefix. SFTP and FTP ingress do not go through here at all.
* **Direct host ports are still published.** `3000`, `8080` and `8090` remain
  open for debugging. Close them once routing is confirmed: FileBrowser trusts
  `X-Forwarded-*` now, so anything reaching `:8080` directly can spoof a client
  IP. Note `http://<box>:8080/` already redirects into the sub-path.
* **Redirects are relative on purpose.** The proxy sets `absolute_redirect off`,
  or nginx would build absolute URLs from the `Host` header and its own port 80
  and send `http://` redirects back through the TLS-terminating ALB.
* **Shell scripts must stay LF.** `.gitattributes` pins `*.sh` to `eol=lf`;
  these repos use `core.autocrlf=true`, and a CRLF entrypoint kills the image on
  its shebang.
* **FileBrowser's config is rewritten every start.** Users, shares and sessions
  live in its database and survive; declarative settings do not.
* **`FILEBROWSER_ADMIN_PASSWORD=admin` does nothing.** FileBrowser treats the
  literal value `admin` as unset and logs a generated password once at first
  start. Pre-existing; worth fixing separately.
