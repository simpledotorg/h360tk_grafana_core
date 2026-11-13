# Path-based routing for H360 instances

Serve every H360 instance from one domain under its own URL path, instead of
giving each instance its own subdomain.

| Instance | Dashboard | File upload |
|---|---|---|
| demo | `https://toolkit.hearts360.org/demo/` | `https://toolkit.hearts360.org/demo/upload/` |
| india | `https://toolkit.hearts360.org/india/` | `https://toolkit.hearts360.org/india/upload/` |

---

## 1. What actually blocked this

Three separate things, only one of which was obvious.

### 1.1 FileBrowser ignored the base-URL setting it was given — the real blocker

Every country `docker-compose.yml` carried this:

```yaml
filebrowser:
  image: gtstef/filebrowser:stable-slim
  environment:
    - FILEBROWSER_BASEURL=/
```

`FILEBROWSER_BASEURL` **is not a FileBrowser environment variable.** FileBrowser
Quantum documents a short, fixed list of env vars (`FILEBROWSER_ADMIN_PASSWORD`,
`FILEBROWSER_CONFIG`, `FILEBROWSER_DATABASE_PATH`, `FILEBROWSER_JWT_TOKEN_SECRET`,
`FILEBROWSER_OIDC_CLIENT_SECRET`) and the base URL is not among them — there is
no generic "env var per config key" convention. The line was a no-op.

So FileBrowser always ran with its default base URL of `/` and emitted absolute
asset and API URLs rooted at `/` (`/static/...`, `/api/...`). Mount it at
`/india/upload/` and the page loads but every asset and every API call goes to
the domain root, where it hits a different instance or a 404. The only
configuration that made the upload UI work was giving it a whole hostname —
which is exactly the constraint that forced one subdomain per instance.

`docker_build/heart360.filebrowser.docker` was a stub carrying the same dead
`ENV FILEBROWSER_BASEURL=/`, never wired into the build — the fossil of an
earlier attempt at this.

The base URL can only be set in a config file, and the key **moved in Quantum
v2.0.0**: `server.baseURL` (v1) became `http.baseURL` (v2). The image is pinned
to a 2.0.x tag so a future major bump cannot silently invalidate the generated
config.

### 1.2 Grafana's sub-path config was applied inconsistently and hardcoded

`h360tk_india` and `h360tk_philippines` already had it:

```yaml
- GF_SERVER_ROOT_URL=%(protocol)s://toolkit.hearts360.org/india/
- GF_SERVER_SERVE_FROM_SUB_PATH=true
```

`h360tk_demo`, `h360tk_indonesia` and both central dashboards had neither, so
their Grafana could not be path-mounted at all. Where it was set, the domain and
path were hardcoded into the compose file, and `%(protocol)s` resolves to
Grafana's **own** protocol — `http` — so behind a TLS-terminating edge Grafana
built `http://` absolute URLs for redirects and share links.

### 1.3 There was no routing layer in version control

Nothing in any repo describes how `toolkit.hearts360.org` reaches an instance.
Each box exposes Grafana on `:3000` and FileBrowser on `:8080` directly, and the
shared ALB that fronts them is managed in the console - there is no load
balancer, listener or target group in `iac-infra/` or in any of these repos. So
the one piece that decides which instance a request reaches is the piece nobody
can review in a pull request. See [`edge-alb.md`](edge-alb.md).

---

## 2. How it works now

Two layers, with a clean split of responsibility.

```
                      toolkit.hearts360.org  (shared ALB: TLS + one rule per instance)
                                 |
            /demo/*              |              /india/*
                 +---------------+---------------+
                 |                               |
        demo EC2 box :80                 india EC2 box :80
        (heart360tk-proxy)               (heart360tk-proxy)
                 |                               |
        /demo/        -> grafana:3000    /india/        -> grafana:3000
        /demo/upload/ -> filebrowser:80  /india/upload/ -> filebrowser:80
        /demo/sftp/   -> sftpgo:8080
```

**The prefix is never stripped.** Grafana (`serve_from_sub_path`) and
FileBrowser (`http.baseURL`) are both told what prefix they live under and both
emit absolute URLs containing it, so both expect to receive it back. An edge
that stripped `/demo` would break every asset request on the next hop.

**The edge forwards, the instance routes.** Because each box owns its own
prefix, adding a service to an instance is a change to that instance's `.env`
alone. The ALB keeps one rule per instance and never changes.

**Country repos ship no routing files.** Both new images read `H360TK_*`
variables and generate their own config at container start, so a prefix cannot
drift out of sync between nginx, Grafana and FileBrowser.

### Two images, built here like everything else

| Image | Built from | Generates |
|---|---|---|
| `simpledotorg/heart360tk-proxy` | `docker_build/heart360.proxy.docker` | `/etc/nginx/conf.d/default.conf`, via [`docker_build/proxy/h360tk-render-conf.sh`](../../docker_build/proxy/h360tk-render-conf.sh) |
| `simpledotorg/heart360tk-filebrowser` | `docker_build/heart360.filebrowser.docker` | FileBrowser's `config.yaml`, via [`docker_build/filebrowser/h360tk-filebrowser-entrypoint.sh`](../../docker_build/filebrowser/h360tk-filebrowser-entrypoint.sh) |

Both are tagged and pushed by the component list in
`.github/workflows/getenv.sh`, and country repos pin them with
`HEART360TK_VERSION` like every other component. A routing fix therefore ships
the same way an application fix does: release in core, bump the version.

### Environment variables

Read by `heart360tk-proxy`:

| Variable | Default | Meaning |
|---|---|---|
| `H360TK_BASE_PATH` | `""` | Instance prefix, e.g. `/demo`. Empty or `/` serves at the domain root. Accepts `demo` too. |
| `H360TK_ROUTES` | `""` | Space-separated `<segment>=<host>:<port>`, e.g. `upload=filebrowser:80 sftp=sftpgo:8080` |
| `H360TK_UPSTREAM_DASHBOARD` | `grafana:3000` | What answers at the prefix root |
| `H360TK_MAX_BODY_SIZE` | `2g` | `client_max_body_size` |
| `H360TK_RESOLVER` | `127.0.0.11` | Docker's embedded DNS |

Read by `heart360tk-filebrowser`:

| Variable | Default | Meaning |
|---|---|---|
| `H360TK_BASE_PATH` | `""` | Same prefix as the proxy |
| `H360TK_UPLOAD_SEGMENT` | `upload` | Must match the segment used in `H360TK_ROUTES` |
| `H360TK_FILEBROWSER_SOURCE` | `/srv` | In-container directory to serve; must match the `.upload` bind mount |

### Why upstreams resolve at request time

Every `proxy_pass` in the generated config goes through a variable, with a
`resolver` directive. nginx resolves a literal upstream name when it *parses*
the config, so a single baked-in config naming `filebrowser` would refuse to
start on a central-dashboard box that does not run one, and could lose a race
against a slow-starting service. With a variable, an absent service means that
one route returns 502 and the rest of the instance keeps serving.

---

## 3. Putting an instance on a path

1. In the country repo's `.env`:

   ```sh
   H360TK_BASE_PATH=/india          # no trailing slash
   H360TK_PUBLIC_DOMAIN=toolkit.hearts360.org
   H360TK_PUBLIC_SCHEME=https
   H360TK_PROXY_PORT=80             # host port for the proxy service
   ```

2. Add the `proxy` service and the Grafana / FileBrowser settings to
   `docker-compose.yml` — copy a country repo that already has them. There are
   no config files to copy.

3. On the shared ALB, add a target group on the proxy's port with health check
   path `/healthz`, and one listener rule matching `/<instance>` and
   `/<instance>/*`. See [`edge-alb.md`](edge-alb.md) - there are three details
   there that will otherwise bite, including that a target group left pointing
   at Grafana on 3000 routes straight past the proxy.

4. Verify:

   ```sh
   curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' https://toolkit.hearts360.org/india
   curl -sS -o /dev/null -w '%{http_code}\n'                 https://toolkit.hearts360.org/india/
   curl -sS -o /dev/null -w '%{http_code}\n'                 https://toolkit.hearts360.org/india/upload/
   ```

   Then load `/india/` in a browser with devtools open: **no request may 404,
   and none may be issued to the domain root.** An asset requested from `/`
   instead of `/india/` means a base URL is still wrong somewhere.

### Inspecting what was generated

```sh
docker compose exec proxy       cat /etc/nginx/conf.d/default.conf
docker compose exec filebrowser cat /home/filebrowser/data/config.yaml
docker compose logs proxy filebrowser | grep h360tk-
```

Both renderers log the prefix and routes they resolved at startup. To patch a
box during an incident without a rebuild, bind-mount over the generated file
and restart that one container — but fix it in core afterwards, because the
next deploy regenerates it.

---

## 4. Known caveats

* **SFTPGo's web UI is the one piece not verified end to end.** SFTPGo exposes
  `httpd.web_root` ("Base URL for the web admin and client interfaces"), which
  maps to `SFTPGO_HTTPD__WEB_ROOT` by SFTPGo's documented `SFTPGO_` + `__`
  naming rule. The docs describe the value as "an absolute URI or it will be
  ignored" and give no example for this key; the sibling WebDAV `prefix` option
  uses the same wording with the example `/dav`, so a leading-slash path is the
  reading taken here. SFTPGo publishes no reverse-proxy guide to check against.
  Confirm `/<instance>/sftp/` loads on the demo box before relying on it. SFTP
  and FTP ingress are unaffected either way — they are not HTTP.
* **Redirects are relative on purpose.** The proxy sets `absolute_redirect off`,
  so a `Location` header is `/demo/` rather than an absolute URL. nginx would
  otherwise build one from the `Host` header and its own listening port — plain
  HTTP on 80 inside the container — and every redirect behind the
  TLS-terminating edge would point at `http://`.
* **Shell scripts must stay LF.** `.gitattributes` pins `*.sh` to `eol=lf`
  because these repos use `core.autocrlf=true`. Without it a Windows checkout
  gives the entrypoints CRLF endings and the built image dies on the shebang.
* **The direct host ports still exist.** `3000`, `8080` and `8090` remain
  published for debugging. Once path routing is confirmed, drop them from
  `docker-compose.yml` and close them in the security group — FileBrowser
  trusts `X-Forwarded-*` headers now, so anything that can reach `:8080`
  directly can spoof a client IP. Note that `http://<box>:8080/` will already
  redirect into the sub-path and no longer serve the UI from the root.
* **`FILEBROWSER_ADMIN_PASSWORD=admin` does nothing.** FileBrowser treats the
  literal value `admin` as unset and generates a random password, logged once at
  first start (`docker compose logs filebrowser | grep -i password`).
  Pre-existing, untouched here, worth fixing separately.
* **FileBrowser's config is rewritten on every start.** Users, shares and
  sessions live in its database and survive; declarative settings do not.
* **Grafana dashboard JSON with hardcoded links** to `/d/...` will still work;
  links written as full `http://host:3000/...` URLs will not.

---

## 5. What was verified

Both images were built and run as a stack (stock Grafana standing in for
`heart360tk-grafana` — same `serve_from_sub_path` mechanism, no Postgres
needed), with the real proxy and FileBrowser images on `H360TK_BASE_PATH=/demo`:

| Check | Result |
|---|---|
| `nginx -t` on the generated config, for the prefixed, root and no-sub-route shapes | passes |
| `/demo/`, `/demo/login`, `/demo/upload/` | 200 |
| `/`, `/demo`, `/demo/upload` | 302/301 to the slashed path, query string preserved |
| `/healthz`, an unknown path | 200, 404 with the instance message |
| FileBrowser asset and API URLs in the served HTML | **every one** under `/demo/upload/`, none at the domain root |
| A real asset fetched through the proxy | 200 `application/javascript` |
| Grafana `/demo/api/health` through the proxy | 200 |
| `/demo/sftp/` with no SFTPGo running | 502 on that route only; the rest of the instance kept serving |
| Proxy and FileBrowser healthchecks | both report healthy |

The FileBrowser asset check is the one that matters: emitting `/static/...` at
the domain root was the original blocker, and those URLs are now prefixed.

The run also found two bugs, both fixed: redirects were absolute (so they would
have pointed at `http://` behind the HTTPS edge), and the renderer's progress
`echo` was landing inside the generated config file.

### Still unproven

* SFTPGo's `httpd.web_root` — the 502 above came from SFTPGo not running at all,
  which says nothing about whether it serves under a sub-path. Check
  `/<instance>/sftp/` on the demo box after the first deploy.
* The real `heart360tk-grafana` image with the H360 Postgres behind it, and the
  shared edge in front. The sub-path mechanism is Grafana's own and is proven
  here, but the full chain has not run.
