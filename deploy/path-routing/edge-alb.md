# The shared edge: ALB listener rules

`toolkit.hearts360.org` is served by one Application Load Balancer with each
instance's EC2 box behind it as a target. This file describes what that ALB
needs in order to route by path.

> **None of this is tracked.** The ALB is managed in the console — there is no
> load balancer, listener or target group anywhere in `iac-infra/` or in these
> repos. This file says what the routing needs, not what is currently
> configured. Check the console before relying on any of it.

---

## The model

One listener rule per instance, forwarding to that instance's target group on
the **proxy's** port. The ALB forwards the path unchanged — a forward action
does not rewrite the URI — which is exactly what the instance needs, because
`heart360tk-proxy`, Grafana and FileBrowser all expect the prefix to arrive
intact.

```
HTTPS :443 listener  (ACM cert for toolkit.hearts360.org)
  ├─ rule 10  path is /demo  or /demo/*         -> tg-h360tk-demo        :80
  ├─ rule 20  path is /india or /india/*        -> tg-h360tk-india       :80
  ├─ rule 30  path is /philippines , /philippines/*  -> tg-h360tk-philippines :80
  └─ default                                    -> fixed 404
```

Adding an instance is one target group plus one rule. Nothing else changes —
the instance's own proxy decides what answers inside its prefix, so a new
service on an instance never touches the ALB.

---

## Three details that will bite

**1. Point the target group at the proxy, not at Grafana.**
These instances have historically been registered on **port 3000**, straight to
Grafana. Left that way, the ALB routes past the proxy entirely: the dashboard
still works, `/<instance>/upload/` 404s, and the proxy sits there doing nothing.
The target group must point at the proxy's port (`H360TK_PROXY_PORT`, normally
80).

Safest switch: create a second target group on port 80, register the same
instance, wait for it to pass health checks, then change the rule's forward
action to it. Reverting is changing the rule back.

**2. Health check path must be `/healthz`.**
On the proxy, `/` returns a **302** to the instance prefix, and ALB health
checks expect `200` by default — so a target checked on `/` is marked unhealthy
and pulled out of service. `/healthz` returns a plain `200` and is served
outside the instance prefix on purpose, so it stays valid no matter what
`H360TK_BASE_PATH` is set to.

| Setting | Value |
|---|---|
| Protocol / port | HTTP / traffic port |
| Path | `/healthz` |
| Success codes | `200` |

**3. `/demo/*` does not match `/demo`.**
ALB path patterns are literal with wildcards, so a rule conditioned only on
`/demo/*` will miss the bare `/demo` that people actually type. Put **both**
values in the one path condition. The proxy redirects `/demo` to `/demo/`, but
only for requests that reach it.

---

## Also worth setting

* **Idle timeout.** The default is 60 seconds. The proxy allows 3600s for
  uploads, but the ALB closes first regardless, so a large line-list upload can
  be cut mid-transfer. Raise it on the load balancer if that bites.
* **Default action.** Give the listener a `fixed-response` 404 (or a small
  landing page) so an unmatched path fails at the edge rather than landing on
  whichever target group happens to be the default.
* **TLS.** One certificate on the listener covering `toolkit.hearts360.org`
  serves every instance. This is the main saving over subdomains, which needed
  a certificate (or a wildcard) and a DNS record per country.
* **`X-Forwarded-Proto`.** The ALB sets it to `https` and the proxy passes it
  through, which is what lets Grafana and FileBrowser build `https://` links
  while speaking plain HTTP to the target.

---

## Verifying a rule

```sh
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' https://toolkit.hearts360.org/demo
curl -sS -o /dev/null -w '%{http_code}\n'                 https://toolkit.hearts360.org/demo/
curl -sS -o /dev/null -w '%{http_code}\n'                 https://toolkit.hearts360.org/demo/upload/
```

Then load `/demo/` in a browser with devtools open: no request may 404, and
none may go to the domain root. An asset fetched from `/` rather than `/demo/`
means a base URL is wrong on the instance, not at the ALB.
