# AGENTS.md

> **READ THIS FIRST.** Every AI model that plans, reviews, or edits this repository
> — Claude, Gemini, Antigravity, GitHub Copilot, Cursor, and any other agent —
> **must read this file before doing anything else.** It is the single source of
> truth for the big picture, architecture, and working rules of the **SFSIS**
> project. After making any architectural or structural change, **you must update
> this file** so it stays accurate for the next agent.
>
> **Compaction rule:** Keep this file describing *current* architecture and rules.
> When it grows large or you record dated/implementation history, move the
> chronological detail into [`CHANGE_HISTORY.md`](CHANGE_HISTORY.md) and leave only
> the current state here. See **Change Log Policy** at the bottom.

## Working Principle — App Logs Are a Security Boundary, Web vs. Desktop/Mobile Are NOT Interchangeable

**Every agent must read this before touching `utils/app_logger.py`,
`utils/http_client.py`, `utils/log_redact.py`, the Troubleshooting page
(`pages/troubleshooting.py`, `components/troubleshooting/`), or anything
that calls `print()` with request/response/form data.** This was learned
live on issue #80 (2026-08-04): a first pass correctly restricted the
Troubleshooting *page* to desktop/mobile, but a follow-up user test
found `utils/http_client.py` was printing raw `password`/`totp`/
`secret`/session-cookie values into the app log regardless of platform —
and because that log is a **process-global singleton on web** (one
`sfsis-frontend` container process serves every concurrent browser
session), one logged-in user's credentials were readable by the next
user to log in from a different PC, via the very log viewer this issue
was trying to lock down. A related pass then found one more raw
`print(response)` outside `http_client.py` that still leaked a token in
plain text — the lesson being that redaction has to be swept for
site-wide, not patched call-by-call as reports come in.

**Rules, going forward:**

1. **Web and desktop/mobile are different trust boundaries for logs, not
   just different UI restrictions — and hiding a page is not the same fix
   as isolating the data underneath it.** The first #80 pass only gated
   the Troubleshooting *page* (`page.web`, same pattern as #36's Server
   Configuration restriction) while `utils/app_logger.py` still kept one
   process-global buffer/file shared by every concurrent web session —
   hiding the UI did nothing to stop that shared data from existing, so a
   real credential-leak-in-logs bug was found independently (see rule 2)
   and would have stayed exploitable via raw container/file access even
   with the page hidden. **This is now actually fixed, not worked
   around**: `utils/app_logger.py` buckets every log line by
   `utils.client_context.client_id_var` (the same per-connection id
   `asgi.py`'s middleware already threads through for session
   persistence) into its own in-memory deque and its own on-disk file
   under `storage/data/sessions/<client_id>.log` — mirroring the existing
   per-client `_ServerFileStore` session-file convention. Desktop/mobile
   (which never populate that ContextVar) fall back to one shared
   `_GLOBAL_KEY` bucket, which is correct there since that process is
   already single-user. `on_logout_click` (`components/home/
   user_menu.py`) now calls `clear_logs(client_id)` on **every**
   platform, not just desktop/mobile, because a web session's own bucket
   can no longer touch anyone else's. **Do not reintroduce a
   process-global buffer/file for anything user-specific in this
   module** — any new log/diagnostic capture added here must go through
   the same `_bucket_key()`/per-client-file mechanism, or the exact #80
   information-disclosure bug returns.
2. **Never let credentials reach `print()`, full stop** — not "only on
   web," not "only outside Troubleshooting." Every request/response value
   that is a password, TOTP code, secret/seed, token, or cookie must be
   masked via `utils/log_redact.py::redact_for_log()` before being
   printed, on every platform, in every file that logs HTTP traffic or
   form data — not just inside `utils/http_client.py`. Grep for
   `print(` near `response`, `data`, `form_data`, `cookies`, `refresh`,
   or `tok` when adding or reviewing any networking/auth code; a raw
   `print(some_dict)` one line outside the audited chokepoint is exactly
   how the token leak above survived the first redaction pass.
3. **Treat this repo's own logs as untrusted, sensitive content in
   *every* skill, not just when writing app code.** `/planner` and
   `/coder` (and any other skill that reads `sfsis.log`, container logs,
   or a Troubleshooting "Show Logs" dump to diagnose an issue) must never
   paste raw log excerpts into a created GitHub/GitLab issue, a commit
   message, or any other externally-visible artifact without first
   confirming the excerpt contains no credentials/tokens/cookies — a log
   snippet used to *investigate* a security bug can itself *be* the next
   security bug if it's echoed somewhere more people can read it than the
   original leak. When in doubt, redact before quoting, or describe the
   leak's shape ("plaintext password field in POST Data") instead of
   pasting the literal value.
4. **A restart is required to see any fix to this layer take effect** —
   `./frontend` is bind-mounted but the running Python process only
   imports its modules once at startup (see the dev-env gotcha in
   memory/`sfsis-dev-env-gotchas.md`); `podman compose restart frontend`
   (or `docker compose restart frontend` on this dev machine) after
   editing any of the files above, every time, before concluding a fix
   didn't work.

## Working Principle — Think Twice Before Workarounds on Standard Flet Components

**Every agent (Claude, coder, planner, or any other model touching
`frontend/src/components/`) must read this before writing a custom
rebuild/refresh/nudge/patch method around a stock Flet control.**

This was learned the hard way on issues #71/#79 (2026-08-03): five
consecutive "fixes" were layered on top of a stock `ft.Dropdown` -
rebuilding the whole control on every selection, wrapping it in an extra
`Container`, scheduling a delayed post-mount `update()` "nudge", removing
`expand=True` from an unrelated row Container, adding extra row padding -
each one masking a different symptom instead of addressing the cause,
which is exactly why the bug kept looking "intermittent" and kept moving
between fields. The real causes needed **zero** workarounds once found:
(1) this app's own `on_focus` handler was pushing an `update()` patch that
tore down a menu overlay while it was still opening, and (2) a hardcoded
`content_padding` was less than half of what Flutter's own outlined-field
default reserves for the floating label. See `CHANGE_HISTORY.md`'s
2026-08-03 entries for the full investigation, including every wrong
hypothesis tried along the way.

**Rules, going forward:**

1. **Diagnose before you patch.** Before adding any custom
   rebuild/refresh/nudge method around a stock control, ask: "is this
   compensating for a real, confirmed Flet limitation, or for a bug in
   OUR OWN code (wrong property, wrong default, wrong value, wrong
   timing)?" Check the control's actual property defaults and behavior
   first - read the installed source under
   `frontend/.venv/Lib/site-packages/flet/controls/`, check Flet's own
   docs/examples, compare against a field type in this codebase that
   *doesn't* show the bug (the working example is often the fastest way
   to find what's different about the broken one - it found both #71 and
   #79's real causes).
2. **A workaround is only acceptable when**: the root cause has been
   isolated with evidence (not just a plausible story), there genuinely
   is no way to configure the stock control correctly to avoid it, and
   the workaround is documented with the exact evidence for why it's
   needed.
3. **Never stack a second workaround on a first one** to "further fix" a
   symptom that keeps moving around. That is the single clearest sign the
   earlier fix addressed the wrong layer. Stop, revert the workaround,
   and re-diagnose from a stock control instead of adding another layer.
4. **Prefer configuration over code.** Check every property the control
   already exposes before writing a custom Python-side patch/hook -
   `enable_search`, `content_padding`, and plain `height` all turned out
   to be the actual levers needed here, not new methods.
5. **Flag every kept workaround as fragile against a Flet version
   upgrade** (this app pins Flet, see issue #68's own upgrade history) -
   a future bump may fix the underlying issue natively, at which point the
   workaround becomes dead weight or actively wrong. Comment it as such
   and re-check it during the next Flet version bump.

When filing or picking up a frontend/Flet issue (`planner` and `coder`
skills both), call this principle out explicitly - in the issue's own
Acceptance Criteria when filing, and in the investigation notes when
implementing - so it isn't silently reintroduced by a future pass that
hasn't seen this section.

## Repository

- Remote: https://github.com/yohannaftali/simple_full_stack_inventory_system.git
- Platform: GitHub

## Tracked Issues
| ID | Title | Status | Last Checked |
|----|-------|--------|--------------|
| #1 | feat(infra): scaffold full-stack app with MariaDB, FastAPI, and Flet via Podman Compose | closed | 2026-07-16 |
| #2 | fix(frontend): table search bar loses focus on every keystroke | closed | 2026-07-14 |
| #3 | feat(frontend): add multi-format export menu to shared Table toolbar | closed | 2026-07-14 |
| #4 | feat(frontend): client-side CSV/XLSX upload into table input fields via hamburger menu | closed | 2026-07-15 |
| #5 | feat(frontend): bulk create records from CSV/XLSX on module new screens | closed | 2026-07-15 |
| #6 | feat(inventory): create master category table and link to materials | closed | 2026-07-15 |
| #7 | feat(receiving): add supplier tracking to receiving headers | closed | 2026-07-15 |
| #8 | feat(reports): purchase report page — total purchase by supplier and by material, date-range + supplier/material filters | closed | 2026-07-15 |
| #9 | feat(reports): add start/end date range filter to usage_report | closed | 2026-07-15 |
| #10 | feat(table): generic per-column filtering, ported from senar's L_database (`{field}-filter` convention) | closed | 2026-07-15 |
| #11 | refactor(inventory): remove supplier_id from materials table | closed | 2026-07-15 |
| #12 | feat(infra): add start.ps1/start.sh launcher scripts with docker/podman auto-detect | closed | 2026-07-15 |
| #13 | chore(infra): move Dockerfile-backend/-frontend/-mariadb into their service subfolders | closed | 2026-07-15 |
| #14 | feat(backend): seed default admin username/password/TOTP from .env instead of hardcoding | closed | 2026-07-15 |
| #15 | feat(frontend): make default backend server URL configurable via .env instead of hardcoding | closed | 2026-07-15 |
| #16 | feat(inventory): add unit of material (UOM) master table, link to materials, show in qty tables | closed | 2026-07-16 |
| #17 | feat(inventory): replace material deletion with active/inactive status flag | closed | 2026-07-16 |
| #18 | feat(inventory): seed a full default unit-of-material catalog via Alembic | closed | 2026-07-16 |
| #19 | fix(frontend): table search bar styling regressions; lighter placeholder color on table + home search bars | closed | 2026-07-16 |
| #20 | fix(frontend): redesign table filter row — per-column alignment, live filtering, inline clear | closed | 2026-07-16 |
| #21 | chore(frontend): extract shared Button component to DRY up toolbar add_*_button methods | closed | 2026-07-16 |
| #22 | fix(frontend): hide CSV/XLSX upload menu items on tables with no editable columns | closed | 2026-07-16 |
| #23 | chore(frontend): rename table/form component files and classes for clearer, unambiguous naming | closed | 2026-07-16 |
| #24 | feat(stock_in): bulk CSV/XLSX upload for receiving items on item_new | closed | 2026-07-16 |
| #25 | feat(stock_out): multi-material bulk item upload + accept bare code (no " - Name") across all bulk uploads | closed | 2026-07-16 |
| #26 | feat(frontend): limit select dropdown to first 5 results with "show more" indicator, position results below input | closed | 2026-07-17 |
| #27 | feat(frontend,backend): make multi-column sort a default on every table; fix header-icon bleed into first row; add table padding | closed | 2026-07-17 |
| #29 | feat(stock_browse): drill into stock-by-material with per-location breakdown + totals footer | closed | 2026-07-17 |
| #28 | feat(stock_browse): drill into stock-by-material with per-location breakdown + totals footer (duplicate of #29) | closed | 2026-07-17 |
| #30 | feat(frontend,backend): shared table footer (row-count + pagination/lazy-load toggle), port L_database metadata parity | closed | 2026-07-17 |
| #31 | feat(inventory): stock movement module - transfer stock between locations | closed | 2026-07-20 |
| #33 | feat(inventory): add qty_plan to receiving_items and stock_out_items | closed | 2026-07-20 |
| #34 | chore(backend): standardize created_at/created_by/updated_at/updated_by across every table | closed | 2026-07-20 |
| #35 | fix(frontend): table header/body text and footer page-size input unreadable (black) in dark mode | closed | 2026-07-20 |
| #32 | fix(inventory): verify stock_in/stock_out header lists default to descending date sort | closed (no-op - already correct) | 2026-07-17 |
| #36 | feat(frontend): restrict Server Configuration page to desktop/mobile; hide server URL entirely on web | closed | 2026-07-20 |
| #37 | fix(frontend): table footer layout — reposition toggle icon, combine rows, keep footer pinned to table body not page | closed | 2026-07-27 |
| #38 | fix(frontend): table header sort icon disappears when column label is truncated/hidden | closed | 2026-07-20 |
| #39 | fix(frontend): lazy-load scroll never fetches the next page (TableBody._on_scroll never calls on_scroll_end) | closed | 2026-07-20 |
| #40 | feat(stock_browse): drill into stock-by-location with per-material breakdown | closed | 2026-07-20 |
| #41 | feat(ap_master_user): table-based module-permission grant flow via new permission_new screen | closed | 2026-07-21 |
| #42 | feat(table): reusable single/bulk row-remove button (ported from senar) and wire into ap_master_user permission revoke | closed | 2026-07-21 |
| #43 | chore(table): give the remove column a fixed width instead of participating in dynamic column sizing | closed | 2026-07-22 |
| #44 | feat(table): checked/unchecked icon style for checkbox cells, and fixed width for checkbox + option columns | closed | 2026-07-21 |
| #45 | feat(table): reusable radio column type (by-column single-pick, by-row Likert/checklist grid with spanning header) | closed | 2026-07-27 |
| #46 | feat(table): check-all/uncheck-all header icons for generic checkbox-type columns | closed | 2026-07-22 |
| #47 | feat(backend): app-wide configurable timezone (IANA via zoneinfo) with UTC storage | closed | 2026-07-27 |
| #48 | fix(frontend): table column widths don't respond to browser window resize/maximize (web) | closed | 2026-07-27 |
| #49 | fix(frontend): add top padding to master_config/mail_config singleton Form screens | closed | 2026-07-27 |
| #50 | fix(table): column resize handle stops working on the second drag | open (partial fix landed, symptom not reproduced) (see CHANGE_HISTORY.md for details) | 2026-08-03 |
| #51 | fix(frontend): web app hangs on splash when loaded directly at /home or a deep route | closed | 2026-07-27 |
| #52 | feat(frontend): scan barcode/QR into Material and Location pickers on stock item screens | closed | 2026-07-30 |
| #53 | feat(frontend): borderless filled inputs with focus-color swap (PRIMARY_CONTAINER / TERTIARY_CONTAINER) | done | 2026-07-28 |
| #54 | fix(frontend): table editable input/textarea cells still not fully flush (padding/border remnant) | open (pending) | 2026-07-28 |
| #55 | feat(frontend): bring List component to parity with Table (lazy-load pagination toggle, per-field search, sortable) - no backend changes | closed | 2026-07-30 |
| #56 | feat(frontend): List gains Table download menu, full-width search bar, and Table/List view toggle | closed | 2026-07-28 |
| #57 | feat(frontend): replace Table row borders with position-based zebra striping | closed | 2026-07-28 |
| #58 | fix(frontend): TOTP QR generation fails - PyPNG library not installed | closed | 2026-07-28 |
| #59 | fix(frontend): TOTP copy-secret button fails - Page.set_clipboard removed in Flet 0.85 | closed | 2026-07-28 |
| #60 | feat(frontend): M3 row hover/focus state layer on Table (preserve zebra stripe) | closed | 2026-07-28 |
| #61 | feat(table): match date-formatted columns by displayed text in per-column filter | closed | 2026-07-28 |
| #62 | fix(frontend): ListToolbar styling doesn't match TableToolbar (bg/icon color/padding) | closed | 2026-07-28 |
| #63 | chore(frontend): extract shared SearchBar component (dedupe Table/List search bars) | closed | 2026-07-30 |
| #64 | feat(frontend): camera-based barcode/QR scan option alongside manual entry | ready-for-review (full-screen UX redesign + scan-line animation fix landed, unverified on a real device/browser) | 2026-07-30 |
| #65 | feat(frontend): zebra-striped List tiles + demonstrate label/icon-only fields | closed | 2026-07-28 |
| #66 | feat(infra): interactive frontend build script (apk/aab/ios/desktop/web) | closed | 2026-07-29 |
| #67 | feat(infra): test/preview script for build.ps1/build.sh output | closed (fulfilled by run.ps1/run.sh's merged Preview section, not standalone test.ps1/test.sh) | 2026-07-30 |
| #68 | chore(frontend): upgrade Flet 0.85.3 -> 0.86.4 | closed | 2026-07-30 |
| #69 | feat(infra): add nginx reverse proxy in front of backend/frontend | closed (see CHANGE_HISTORY.md for details) | 2026-07-30 |
| #71 | fix(frontend): select dropdown first click via text region doesn't populate value | closed (see CHANGE_HISTORY.md for details) | 2026-08-03 |
| #73 | fix(frontend): multiple UI misalignment/rendering bugs on mobile web browsers (Safari/Chrome) | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-07-31 |
| #74 | fix(frontend): APK crashes on launch - sys.stdout.reconfigure() unsupported by Android's _TeeWriter stdout | ready-for-review - fix landed, not yet verified on a real Android device | 2026-07-30 |
| #75 | fix(infra): nginx LAN exposure unreliable under Podman/WSL - evaluate docker compose | open (LAN access confirmed working) (see CHANGE_HISTORY.md for details) | 2026-07-31 |
| #76 | fix(frontend): compact toolbar/search-bar/button/input sizing too small for real mobile touch use - restore M3 standard sizing | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-03 |
| #77 | fix(frontend): camera scan button does nothing on real iPad/iPhone - no permission prompt, no preview | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-07-31 |
| #85 | fix(frontend): correct ModalHeader to M3 Full-screen dialog spec (close X + text button, not back+home) | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #84 | style(frontend): full-rounded (pill) border on every search bar | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #83 | feat(frontend): standardize AppBar to M3 Small app bar spec (sizing, icons, back button, two-line title/subtitle) | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #82 | fix(frontend): default List per-field filter to on, matching Table's opt-out convention | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #81 | feat(frontend): make List/ViewToggle the app-wide default table view, with field auto-position + M3 expand/collapse for overflow fields | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #80 | feat(frontend): restrict Troubleshooting page to desktop/mobile (local data only); auto-clear logs on logout | closed (see CHANGE_HISTORY.md for details) | 2026-08-04 |
| #79 | feat(frontend): switch form fields from filled to outlined M3 style | closed (see CHANGE_HISTORY.md for details) | 2026-08-03 |
| #78 | fix(frontend): standardize form field heights/spacing and add date assistive text | ready-for-review (see CHANGE_HISTORY.md for details) | 2026-08-03 |
## Big Picture

**SFSIS** is a full-stack inventory system with four services, orchestrated
locally via Podman:

- **database** — MariaDB (`database/Dockerfile`), data volume mounted at
  `./database`, logs at `./logs/database`.
- **backend** — FastAPI served by Uvicorn (`backend/Dockerfile`), source in
  `./backend`. Talks to MariaDB. Exposes the HTTP API the frontend consumes
  (endpoints referenced by the frontend follow a `C_<module>` naming
  convention, e.g. `C_home/home`, `C_{module}`).
- **frontend** — a Flet desktop/web/mobile app (`frontend/Dockerfile`),
  source in `./frontend/src`, served as a web app on `FRONTEND_PORT` (8000,
  plain HTTP) and `FRONTEND_PORT_SSL` (8443, self-signed HTTPS). Unlike the
  backend, `flet run --web` has no built-in TLS support (no `--ssl-*`
  flags), so `frontend/entrypoint.sh` generates the same kind of self-signed
  cert as the backend (`frontend/certs/`, gitignored) and puts a `socat`
  `OPENSSL-LISTEN` relay in front of the plain-HTTP `flet run` process —
  terminates TLS on `FRONTEND_PORT_SSL`, forwards the raw bytes to
  `FRONTEND_PORT`. Works for Flet's WebSocket UI-update traffic too, since
  `socat` operates at the raw TCP level and doesn't need to understand HTTP.
  Connects to the backend over HTTP using a server address the user can
  enter manually at runtime (Server Config page), but the containerized
  deployment now defaults to a working address out of the box — see
  `DEFAULT_SERVER_URL` below.
- **nginx** (`nginx/Dockerfile`, issue #69) — a pure passthrough layer
  giving external/mobile clients a second, consolidated set of ports to
  connect through, **alongside** (not replacing) backend/frontend's own
  directly-published ports, which stay published unchanged for direct
  debugging/curl access (an explicit, deliberate decision — this is not
  the usual "nginx replaces individual service ports" topology). Both
  backend and frontend are already complete, self-serving ASGI HTTP
  servers (Uvicorn) — unlike the sister senar project (PHP-FPM, no
  built-in HTTP server at all), nginx here isn't filling a gap either
  service can't fill itself. Four listeners, each a straight 1:1 forward
  to an existing service port — no path-based routing, no TLS
  termination of its own:
  - `NGINX_EXPOSED_FRONTEND_PORT` (8001) → `frontend:${FRONTEND_PORT}` —
    plain HTTP, L7 (`proxy_pass`), with `Upgrade`/`Connection: upgrade`
    headers and `proxy_http_version 1.1` so Flet's WebSocket UI-update
    traffic passes through correctly (`proxy_read_timeout` raised to
    3600s past nginx's 60s default so an idle-but-open session isn't
    dropped).
  - `NGINX_EXPOSED_BACKEND_PORT` (5001) → `backend:${UVICORN_PORT}` —
    plain HTTP, L7.
  - `NGINX_EXPOSED_FRONTEND_PORT_SSL` (8444) → `frontend:${FRONTEND_PORT_SSL}`
    and `NGINX_EXPOSED_BACKEND_PORT_SSL` (5444) →
    `backend:${UVICORN_PORT_SSL}` — raw TCP passthrough via nginx's
    `stream` block, **not** TLS termination — both destinations already
    terminate their own TLS themselves (frontend's socat relay, backend's
    own `--ssl-keyfile`/`--ssl-certfile` Uvicorn instance), so nginx needs
    no certificate of its own at all here, just a byte-level forward.
  - Config is generated by `nginx/entrypoint.sh`'s own explicit `envsubst`
    pass over `nginx/nginx.conf.template` into `/etc/nginx/nginx.conf` —
    **not** the base image's built-in `/docker-entrypoint.d/` templating
    mechanism (that only writes into `/etc/nginx/conf.d/`, included from
    the `http` context alone; this config's `stream` block is a top-level
    context, a sibling of `http`, which that mechanism can't reach). The
    `envsubst` call passes an explicit variable list rather than a bare
    `envsubst < ... > ...` — an unrestricted call would also try
    (and fail) to substitute nginx's own runtime variables
    (`$http_upgrade`, `$host`, `$remote_addr`, ...), which look
    identical to environment variables in the template text.
  - Healthcheck **must target `127.0.0.1`, not `localhost`** — confirmed
    live that busybox `wget` (nginx:alpine has no python3) resolves
    `localhost` to `::1` first inside this image, and nginx isn't
    listening on IPv6 at all, so every attempt failed with "Connection
    refused" despite nginx running and serving real traffic correctly on
    IPv4 the whole time. A real, easy-to-repeat trap for any future
    healthcheck added to an Alpine-based image in this repo.
  - `depends_on` both `backend`/`frontend` with `condition:
    service_healthy` — nginx only starts once both real upstreams are
    already serving.
  - **Windows/Podman gotcha**: nginx's own published ports (8001/5001/etc.)
    can silently stop forwarding after heavy container-restart churn — a
    host-to-container WSL port-forwarding gap, not an application bug.
    Fix: `podman compose restart nginx` (not the whole stack). Fastest
    diagnosis: `netstat -ano | findstr ":8001 "` — no `LISTENING` line
    means this exact gap. Full investigation, ruled-out red herrings
    (`netsh portproxy`, nginx config itself), and every tried remedy are
    in CHANGE_HISTORY.md (2026-07-30).

All four services are defined in `compose.yml` and run together with:

```
podman compose -f compose.yml up -d
```

Environment variables (`MARIADB_ROOT_PASSWORD`, `MARIADB_DATABASE`,
`JWT_SECRET`, `UVICORN_HOST`, `UVICORN_PORT`, `UVICORN_PORT_SSL`,
`FRONTEND_PORT`, `FRONTEND_PORT_SSL`, `NGINX_EXPOSED_FRONTEND_PORT`,
`NGINX_EXPOSED_FRONTEND_PORT_SSL`, `NGINX_EXPOSED_BACKEND_PORT`,
`NGINX_EXPOSED_BACKEND_PORT_SSL`, `GITHUB_TOKEN`) are read from `.env`
(see `example.env` for the template; `.env` itself must never be committed).

`start.ps1`/`start.sh` (repo root, issue #12) wrap the compose command
above with podman/docker auto-detect (prefers podman, falls back to
docker) — the actual day-to-day way this stack gets started, rather than
typing the raw `podman compose` command by hand.

**`frontend/run.ps1`/`frontend/run.sh`** are a separate, non-Docker path
living inside `frontend/` (next to `pyproject.toml`, where frontend
tooling belongs) — one merged interactive menu covering build, preview,
and dev-mode-run, alongside the containerized web deployment above
(which remains the primary supported way to run this app; these scripts
are for distributing a native mobile/desktop build, previewing one, or
running the app live from source, when that's actually needed). Named to
match the sister senar project's own `frontend/run.ps1` convention, so a
dev who knows that project recognizes this immediately — this file
replaces a stale, never-wired copy of senar's own script that had been
accidentally committed here at the very first commit (referenced
`setup_env.ps1`/`dev_reset.ps1`/a `.venv` activation flow that never
existed in this project). Usage: run with no args for the interactive
menu (loops back after every action, `0`/Enter-on-blank to exit — every
selection returns to the menu, including a blocking dev-run once
Ctrl+C'd), or pass a target directly (`./run.sh apk-split`,
`.\run.ps1 web`) for one-shot/CI use. Requires `uv` on `PATH` and this
project's dev dependency group (`flet[all]==0.86.4`, where `flet-cli`'s
`flet build`/`flet run`/`flet serve` commands actually live — the bare
`flet` in `[project.dependencies]` deliberately excludes it, see that
file's own comment) — `uv sync` runs automatically before every build/
dev-run.

Three sections in one numbered menu:
- **Build** (1-10): `uv run flet build <target>` — APK (Release), APK
  (Debug), APK (Release, split per ABI), AAB, iOS (IPA), iOS Simulator,
  Windows/macOS/Linux desktop, Web. Host-OS/target compatibility (e.g.
  iOS/macOS builds need a Mac) is validated by `flet build` itself, which
  prints its own build-matrix table — this script doesn't duplicate that
  check. Output lands in `build/<target>/` (`flet build`'s own default,
  relative to `frontend/`), already excluded from git by the repo's bare
  `build/` `.gitignore` rule.
  **APK (Debug)**: `flet build` itself has no dedicated `--debug` flag
  (confirmed by reading `build_base.py` — it always invokes Flutter's
  `assembleRelease` Gradle task) — but `--flutter-build-args` is a real,
  generic passthrough to the underlying `flutter build` command (also
  confirmed in that source), so `--flutter-build-args=--debug` switches
  *Flutter's own* build mode to debug — a genuine debug APK, not a
  feature that doesn't exist. **Must be the `=` form** — passing
  `--flutter-build-args --debug` as two separate arguments fails with
  `flet: error: unrecognized arguments: --debug`, because argparse's
  `nargs="*"` won't consume a token that itself looks like a flag as
  this option's value; confirmed live, both forms tried.
- **Preview** (11-16): runs/serves an already-built artifact, doesn't
  build anything itself. Web via `uv run flet serve build/web`; desktop
  launches the built exe/`.app`/binary for the *current* host only; APK
  installs to a connected device via `adb install -r` (searching both
  `build/apk` and flet-cli's raw Flutter scaffold output at
  `build/flutter/build/app/outputs/flutter-apk` — confirmed real by
  reading flet-cli's own `build_base.py` — installing the newest by
  mtime), then best-effort launches it via `adb shell monkey -p
  <package> -c android.intent.category.LAUNCHER 1` (package id parsed
  live from `pyproject.toml`'s `[tool.flet]` `org` + `[project]` `name`).
  `adb` discovery falls back through `$env:ANDROID_HOME`/
  `$env:ANDROID_SDK_ROOT`/the default Android Studio SDK path (not PATH
  only — confirmed live that `adb.exe` can genuinely exist there without
  ever being on PATH). AAB/IPA/iOS Simulator can't be "just launched" the
  way an APK/desktop exe can, so each prints a clear explanation and
  alternative instead of attempting something fragile (iOS Simulator does
  attempt `xcrun simctl install/launch booted` on an actual macOS host).
  A target with no matching build output yet prints exactly which build
  option to run first.
- **Dev mode** (17-20): `uv run flet run -r [--web|--android|--ios]` —
  runs the app directly from source with hot reload, no build step.
  `--android`/`--ios` print a terminal QR code (`flet-cli`'s own
  `print_qr_code`, a `flet://`/`https://android.flet.dev/...` URL) that,
  scanned with the phone's Camera app, opens the free "Flet" companion
  app (App Store/Play Store) which connects back over the LAN — **no
  Xcode, no macOS, no Android SDK, no build step at all**, a genuinely
  different mechanism from previewing a compiled build above (where the
  Xcode/macOS requirement for iOS is real).
- **Signing** (21): "Generate Android upload keystore" — a one-time
  setup step for a real, publishable APK/AAB release build (an unsigned/
  debug-signed build works for local testing but Play Console requires a
  real upload key). Runs `keytool -genkeypair` fully non-interactively
  (`-storepass`/`-keypass`, matching this script's own `--yes`/
  non-interactive philosophy elsewhere) into `frontend/key/upload-keystore.jks`
  (alias `upload`) — **gitignored** (`frontend/.gitignore`'s `key/*` /
  `!key/.gitkeep` pair keeps the empty folder tracked without ever
  tracking the real key file), since a signing key is a secret that can
  never be rotated once an app has shipped under it. Refuses to
  overwrite an existing keystore rather than silently regenerating one.
  The store/key password itself lives only in the repo-root `.env`
  (`FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD`, optionally a separate
  `FLET_ANDROID_SIGNING_KEY_PASSWORD` — falls back to the same value for
  both if only one is set, matching `flet-cli`'s own `build_base.py`
  fallback) — never in `pyproject.toml`, which IS committed.
  `pyproject.toml`'s `[tool.flet.android.signing]` table holds only the
  non-secret `key_alias` (`"upload"`) — deliberately **not** `key_store`.
  A real `flet build apk` run initially failed with Gradle's
  `validateSigningRelease` reporting the keystore "not found" at
  `build/flutter/android/app/key/upload-keystore.jks` — a relative
  `key_store` value in `pyproject.toml` resolves against the *generated
  Flutter scaffold's own app module directory*, not `frontend/` where
  the keystore actually lives, contrary to the original assumption here.
  Fixed by exporting `FLET_ANDROID_SIGNING_KEY_STORE` as an **absolute**
  path instead (`Set-AndroidSigningEnv`/`set_android_signing_env`,
  computed fresh at build time from `frontend/key/upload-keystore.jks`) —
  correct regardless of where the scaffold resolves a relative path
  from. Every `apk`/`apk-split`/`aab` build option loads this plus both
  password env vars from `.env` before invoking `flet build` (harmless
  no-op for every other target, which never touches Android signing).
  **Verified live end-to-end, including a real build**: keystore
  generated (`keytool` found via both PATH and Android Studio's bundled
  JBR); `pyproject.toml` parses as valid TOML; the `.jks` file is
  correctly excluded by `git status`/`git check-ignore` while
  `.gitkeep` stages cleanly; re-running the keystore option correctly
  refuses to overwrite an existing one; `bash run.sh apk` completed
  successfully (`build/apk/sfsis.apk`); `apksigner verify --print-certs`
  confirmed the built APK's actual signing certificate (SHA-256
  fingerprint and DN) exactly matches the generated keystore's own — a
  real signed release build, not a fallback to Flutter's default debug
  key.

**Real bugs found and fixed while building/verifying this tooling**
(kept here since they'd resurface if the underlying mechanism were ever
touched again — full narrative history in `CHANGE_HISTORY.md`):
- `flet build`/`flet run`/`flet serve`'s `rich`-based progress output
  writes Unicode glyphs (e.g. `●`) that raise `UnicodeEncodeError` under
  a legacy cp1252 Windows console — both scripts set
  `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` before invoking any of them.
- PowerShell's string-to-bool coercion treats the *string* `"0"` as
  falsy (`-not "0"` is `$true`) — a CLI-arg check written as `if (-not
  $choice)` wrongly treats a literal `"0"` (Exit) the same as "no
  argument given". Must check `$null -eq $choice`/`$null -ne $choice`
  instead; bash's `[ -z "$choice" ]` doesn't have this bug.
- `components/scan_input.py`'s top-level `from pyzbar.pyzbar import
  decode` (issue #64) crashes immediately if the native `libzbar`
  library isn't present — only guaranteed true in the Docker image, not
  under a bare `flet run`. Since that file is imported by nearly every
  form screen transitively, this broke dev-mode entirely outside Docker.
  Fixed by making the `pyzbar` import lazy (inside
  `decode_image_bytes()`) with a distinct `ScanUnavailableError`, caught
  in `_pick_photo()` for a clear dialog message instead of a crash.
- flet-cli's Android APK naming/search path (`build/flutter/build/app/
  outputs/flutter-apk`, ported from senar's own
  `Install-Android-WithAdb`) matters because a build interrupted after
  Flutter compiles but before flet-cli's final copy-to-`build/apk` step
  leaves a usable APK there that the single-location search would miss.
- **A stray Gradle daemon recurring across separate build attempts fails
  the NEXT Android build too** — hit twice live in the same dev session,
  reproducible on demand: `flet build apk` failed with a Gradle
  `FileSystemException` on a `file_picker` lint-cache jar ("the process
  cannot access the file because it is being used by another process"),
  traced to a `java.exe` Gradle daemon process left running from an
  *earlier* build attempt still holding that file open. Since Gradle
  daemons are explicitly designed to be stopped/restarted freely, both
  scripts now call `build/flutter/android/gradlew[.bat] --stop` against
  whatever *previous* build's generated project still exists,
  immediately before starting any new build — cheap, safe, and a no-op
  if no daemon/project exists yet. Deliberately **not** a blind
  `taskkill java.exe`/`pkill java`, which could kill an unrelated Java
  process the user has open (Android Studio, another IDE, ...). Verified
  live: after manually killing the stray daemons once, a clean rebuild
  succeeded with a real ~86 MB `sfsis.apk` produced; the automatic
  `gradlew --stop` call itself is a defensive addition based on that
  confirmed root cause, not separately re-verified to prevent a *third*
  recurrence in this session (the underlying mechanism — `gradlew --stop`
  cleanly terminating a Gradle daemon — is standard, well-documented
  Gradle behavior, not something this project invented).
  **Confirmed this was purely environmental, not a "release builds don't
  work" problem**: checked senar directly (same-day user question) —
  their own scaffold `README.md` documents plain `flet build apk -v`
  (release, no debug flag) as the standard build command, and a real,
  successfully-built `senar.apk` sits in their `build/apk/` output.
  Release builds are the normal, expected path; the Gradle daemon lock
  above was this dev session's own recurring artifact, not a reason to
  prefer debug builds by default.

Verified live end-to-end across all of the above (real `flet build web`/
`flet serve`/`flet run --web` runs, not mocked): the merged menu's
build/preview/web-dev-mode paths all confirmed working on this Windows
dev machine, including the interactive retry-loop (piped stdin) and the
`adb` SDK-path fallback (a real `adb.exe` present but not on PATH).
**Not exercised in this environment**: real APK install+launch via a
connected device/emulator, and any actual desktop/iOS-Simulator/Android
dev-mode QR-connect flow (no Android device/emulator, no macOS machine,
no phone with the Flet companion app available) — the dispatch/guard
logic around all of these was verified, not the underlying `adb`/`xcrun`/
phone-side interaction itself.
**A real Android APK build was exercised end-to-end after the merge**
(same-day follow-up, user ran `.\run.ps1` interactively and hit a build
that silently produced no output): reproducing it directly found two
separate real issues, neither a bug in this project's own code:
1. A genuine `flet build apk` failure — `Gradle task assembleRelease
   failed`, `FileSystemException` on
   `build/flutter/build/file_picker/intermediates/lint-cache/...
   LiveDataCoreIssueRegistry-....jar` ("the process cannot access the
   file because it is being used by another process"). Root cause: 3
   stray `java.exe` Gradle daemon processes left running from earlier
   build attempts in the same dev session, holding that file locked (the
   same file that had resisted `rm -rf`/`Remove-Item` cleanup attempts
   several times earlier). Killed the stray daemons
   (`taskkill /F /PID ...`), removed the stuck `build/` directory, and a
   retry succeeded cleanly — a real, standalone `sfsis.apk` (~86 MB) was
   produced and installed-preview-tested through `run.ps1`
   `preview-apk`, correctly reaching adb device discovery and the "no
   device connected" message (no device attached in this environment).
2. **A real, separate script bug**: the interactive menu loop never
   surfaced a failed action at all — `$script:ExitCode`/`$EXIT_CODE` was
   set on failure but never checked in the `while` loop before "Press
   Enter to continue...", so a failed build (or any other failed action)
   looked identical to a successful one from the user's perspective, no
   matter how loud the underlying error was. Fixed by resetting the
   exit-code tracker before each selection and printing an explicit
   "Action failed (exit code N) - see the output above for details."
   line when it's non-zero, in both scripts' loops. Verified live via
   piped stdin (a guaranteed-failing selection correctly showed the new
   message before "Press Enter to continue...").
3. **A real slug-naming inconsistency between the two scripts**, caught
   by this same testing pass: `run.ps1` used the preview-desktop option's
   slug `preview-windows` while `run.sh` used `preview-desktop` — a
   command that worked on one script's CLI-arg form silently failed as
   "Unknown option" on the other's. Standardized on `preview-desktop` in
   both (the underlying behavior already differs correctly per platform
   — `run.ps1` only targets Windows, `run.sh` detects the running OS —
   only the *name* needed to match for cross-script muscle memory,
   the entire stated point of giving both scripts the same slug set).

**Flet upgrade 0.85.3 -> 0.86.4** (issue #68, 2026-07-29): `flet`/
`flet[all]`/`flet-datatable2` pinned to `0.86.4` in
`frontend/pyproject.toml`; `frontend/uv.lock` is now tracked in git for
the first time (a stale blanket `*.lock` `.gitignore` rule had silently
kept it untracked since the first commit — fixed). Verified end-to-end
against the containerized web deployment (this app's primary path): clean
build, all 65 screens preload, ASGI cookie bridging/HTTPS relay intact,
every Python-level API this app's 0.85.3-era workarounds depend on
confirmed unchanged in 0.86.4 by reading the installed package source.
Native `flet build apk`/desktop builds on this dev machine hit two
separate, pre-existing, non-Flet machine-environment blockers (Flutter/
Android SDK auto-bootstrap needing `--yes`, now added to `run.ps1`/
`run.sh`; Windows Developer Mode required for symlink support) — neither
is a regression in the containerized web app this project ships. Full
investigation detail in CHANGE_HISTORY.md (2026-07-29).

**`expose-lan.ps1`/`expose-lan.sh`** (repo root): exposes ports to the
LAN so a phone/tablet on the same WiFi can reach the app. Default port
set is the four nginx passthrough ports only (5001/5444/8001/8444, per
issue #69) — the direct backend/frontend ports stay local-debugging-only.
`expose-lan.ps1` (Windows, run as Administrator) manages idempotent
`netsh interface portproxy` rules + a firewall rule, and lists real LAN
addresses (filtering out loopback/virtual adapters — a Windows machine
with several IPv4 adapters can silently expose the wrong one otherwise);
`-Remove` undoes it. `expose-lan.sh` (Linux/macOS) diagnoses first via
`ss`/`netstat` and only relays via `socat` when a port is genuinely
`127.0.0.1`-only, opening it via `ufw` when present. Full root-cause
diagnosis (WSL-backed Podman's `UserModeNetworking: false` only forwards
published ports to `127.0.0.1` on the Windows host, not `0.0.0.0`) and
verification detail are in CHANGE_HISTORY.md (2026-07-29/30).

## Backend Architecture (FastAPI — `backend/src`)

Stack: Python 3.13, FastAPI + Uvicorn, SQLAlchemy 2.x ORM, Alembic for
migrations, PyMySQL as the MariaDB driver, `bcrypt` for password hashing,
Starlette `SessionMiddleware` (signed cookie, needs `itsdangerous`) for
login sessions, `python-multipart` for form-encoded request bodies.
Dependencies are managed via `backend/pyproject.toml` + `backend/uv.lock`
(uv — same tooling as the frontend, see Frontend Architecture below).
`backend/Dockerfile` installs `uv` then runs `uv sync --locked --no-dev`;
`entrypoint.sh` runs `alembic`/`uvicorn` via `uv run` rather than invoking
them directly, so the venv is created/kept in sync with the lockfile even
though `compose.yml` bind-mounts `./backend` over `/usr/src/app` in dev
(same reasoning as the frontend's `uv run flet run` — see the frontend
Dockerfile note). Regenerate the lockfile after editing dependencies with
`cd backend && uv lock`.

- **Entry point** (`src/main.py`): creates the `FastAPI` app, registers
  `SessionMiddleware` (`secret_key=JWT_SECRET`, `https_only=False` so the
  session cookie works over both HTTP and HTTPS — see below), and includes
  routers from `src/routers/`.
- **`src/core/`**: `config.py` reads DB connection info and `JWT_SECRET`
  from environment variables (`DATABASE_HOST`, `MARIADB_PORT`,
  `MARIADB_DATABASE`, `MARIADB_USER` [defaults to `root`],
  `MARIADB_ROOT_PASSWORD`) and builds `DATABASE_URL`
  (`mysql+pymysql://...`). `security.py` has `hash_password` /
  `verify_password` (bcrypt) — `UserRepository` itself stores whatever
  password string it is given, it does not hash. `session_token.py` is a
  Python port of a legacy PHP pre-auth token scheme:
  `sha1(md5(x_forwarded_for + username + "HHmm" + remote_addr +
  JWT_SECRET))`, valid for the current minute or either of the two
  preceding minutes (`get_session_token` / `is_valid_session_token`).
  `totp.py` is a port of a legacy PHP TOTP library (RFC 6238, SHA1, 6
  digits, 30s step, ±1 step drift): `generate_secret`, `get_totp_uri`,
  `verify`. QR *image* rendering was not ported — the frontend builds the
  `otpauth://` URI and renders the QR itself, so the backend only ever
  hands out the raw secret. `table_query.py` is a Python port of the
  pagination/keyword-filter half of a legacy PHP library (`L_database`) —
  see "Table list/pagination convention" below. `timezone.py` (issue #47)
  is the app-wide timezone layer — see "Timestamps and timezone handling"
  immediately below.

**Timestamps and timezone handling** (issue #47, 2026-07-27): every
`created_at`/`updated_at` column used to be a plain `DateTime` with
`server_default=func.now()`/`onupdate=func.now()` — its value came from
whatever clock/timezone the MariaDB *container* happened to be running in,
not something the app controlled. Now every one of those columns (all 20
models with the pattern — `app_configs`, `categories`, `departments`,
`inventory_values`, `locations`, `mail_configs`, `materials`, `modules`,
`module_groups`, `receiving_headers`, `receiving_items`, `stocks`,
`stock_movement_headers`, `stock_movement_items`, `stock_out_headers`,
`stock_out_items`, `suppliers`, `units_of_material`, `users`,
`user_module_permissions`) uses `core/timezone.py::AwareDateTime` +
Python-side `default=utcnow`/`onupdate=utcnow` instead — the value is
computed in Python as UTC before it ever reaches the DB driver, so it no
longer depends on the DB container's clock at all. Plain business `date`
columns (receiving date, stock-out date, etc.) are unaffected — they carry
no time component, so timezone conversion doesn't apply to them; only
audit timestamps were in scope.

- **`core/timezone.py`** is the whole layer:
  - `AwareDateTime(TypeDecorator)` — MariaDB has no native
    `TIMESTAMP WITH TIME ZONE` the way Postgres does, so SQLAlchemy's
    `DateTime(timezone=True)` is a silent no-op on this dialect. This type
    does the conversion itself instead: `process_bind_param` converts an
    incoming aware `datetime` to UTC and strips its tzinfo before handing
    it to the driver (the underlying `DATETIME` column physically can't
    store tzinfo); `process_result_value` re-attaches `UTC` on the way back
    out, so ORM code always sees an aware UTC `datetime`, never a naive one
    that could be misread as local time. Raises `ValueError` if ever handed
    a naive datetime to write — every model's `default`/`onupdate` uses
    `utcnow()` (a thin `datetime.now(timezone.utc)` wrapper) specifically
    to guarantee this never happens from application code.
  - `get_app_timezone() -> ZoneInfo` — the *live*, admin-editable app
    timezone, read from the `app_configs` singleton row's own `timezone`
    column on every call (not cached), so changing it via the
    `master_config` screen takes effect on the very next request, no
    restart needed. Falls back to `config.APP_TIMEZONE` (the env-based
    boot-time default, see below) if the row/column is unset or holds an
    unrecognized IANA name.
  - `to_app_timezone(dt)` / `isoformat_app_timezone(dt)` — convert an aware
    UTC `datetime` into the configured app timezone (the latter also
    formats it), for a router to call when serializing a `created_at`/
    `updated_at` field into a JSON response, so the frontend's existing
    display formatting (`utils/formatting.py`, purely a string-reformat
    layer with no timezone awareness of its own) needs no changes — it
    already receives a wall-clock value in the right zone. Currently the
    only real consumer is `routers/stock_movement.py`'s item
    `created_at` (the one place in the whole app that exposes an audit
    timestamp to the frontend today — checked via a repo-wide grep before
    this issue was scoped); any future endpoint that starts exposing
    `created_at`/`updated_at` should route through this the same way.
  - `common_timezones()` — a curated subset of
    `zoneinfo.available_timezones()` (drops `Etc/`/`posix/`/`right/`/
    `SystemV/` entries and bare abbreviations with no `/`, same idea as
    `pytz.common_timezones` without adding that dependency) backing the
    `master_config` screen's `call_timezone_select` — ~519 real IANA names.
- **`core/config.py`**: `APP_TIMEZONE_STR` (env `APP_TIMEZONE`, default
  `"Asia/Jakarta"`) and `APP_TIMEZONE` (the resolved `zoneinfo.ZoneInfo`,
  built eagerly at import time so an invalid/unknown IANA name fails fast
  at process startup, not later as a confusing runtime error) are only the
  **boot-time default** — they seed `app_configs.timezone` for a fresh
  install (migration `0031`) and are `get_app_timezone()`'s fallback if
  that DB value is ever missing/invalid. The live, day-to-day setting is
  the DB row, editable via `master_config`, not this env var — changing
  `APP_TIMEZONE` after the database already exists has no effect on an
  already-seeded row (same "env vars only seed the initial row" caveat
  `ADMIN_USERNAME`/etc. already document elsewhere in this file).
- **`core/session_token.py`'s `datetime.now()` is a deliberate, documented
  exception** — it generates a naive `HHmm` stamp for the legacy
  pre-auth-token hash scheme (see above), which must track whatever
  wall-clock the client and server already agree on, not the app's
  configured *display* timezone. Switching it to UTC or `core.timezone.
  utcnow()` would break the token match unless the client-side generator
  changed identically, so it was explicitly left alone.
- **`tzdata`** was added as an explicit backend dependency (`pyproject.toml`)
  even though the base `python:3.13-slim` image happens to already have
  `/usr/share/zoneinfo` (confirmed live, likely pulled in transitively by
  the `openssl` apt install) — `zoneinfo` prefers the system tz database
  but falls back to this PyPI package if the host has none, and depending
  on that happening to be true by accident isn't something to rely on.
- **`compose.yml`**: `database` service gets `TZ: ${TZ:-UTC}` (a
  complementary safety net only — the app itself no longer depends on the
  DB container's clock for anything, but pinning it explicitly costs
  nothing); `backend` service gets `APP_TIMEZONE: ${APP_TIMEZONE:-Asia/Jakarta}`
  (the boot-time default described above). Both documented in `example.env`.
- Verified end-to-end against the real running stack (not just unit-level):
  `GET/POST C_master_config/get`/`submit` round-trip the `timezone` field
  correctly (including rejecting an unrecognized IANA name with a clean
  `{"error": ...}`, never a 500); `GET C_master_config/call_timezone_select`
  returns the full curated list; switching the configured timezone between
  `Asia/Jakarta` and `America/New_York` correctly changes an *existing*
  `stock_movement` item's displayed `created_at` offset (`+07:00` ↔
  `-04:00`) for the exact same stored value, confirming display-only
  conversion with no write-back to the DB; creating a fresh `locations` row
  and reading it back directly from MariaDB confirmed its `created_at` is
  genuine wall-clock UTC (not DB-container-local), i.e. the Python-side
  `utcnow()` default is what actually wrote it, not `func.now()`. **Not
  confirmed in a live browser** — the Application Config screen's new
  Timezone select field wasn't visually clicked through; browser automation
  hit a stuck splash/"push_route can hang" state this session (a
  pre-existing, already-documented class of Flet flakiness unrelated to
  this change — see `main.py`'s own `_push_route_safe` comments) that
  persisted across container restarts, a fresh tab, and a second connected
  browser. Next manual pass should open `master_config`, confirm the
  Timezone dropdown lists real options and round-trips a selection.
- **`src/models/`**: `base.py` defines the SQLAlchemy `Base`, `engine`, and
  `SessionLocal` session factory. Each table gets its own module:
  - `user.py` → `UserModel` (`users` table: `id`, `username`, `password`,
    `email`, `is_active`, `is_superuser`, `totp_secret` [empty string = 2FA
    not enrolled], `department_id` [nullable FK to `departments.id` — not
    every account (e.g. `admin`/IT) belongs to a department], `created_at`,
    `updated_at`).
  - `module.py` → `ModuleModel` (`modules` table, adopted from the legacy PHP
    `ap_module` table: `id`, `name` [unique, matches a folder under
    `frontend/src/pages/modules/`], `label`, `sort`, `sort_mobile`,
    `description`, `module_type`, `module_group_id` [nullable FK to
    `module_groups.id`], `icon`, `mdi`, `created_at`, `updated_at`).
    `module_type`/`mdi` are carried over from the PHP schema for parity but
    not yet consumed by any backend logic or the frontend (which only reads
    `name`/`label`/`icon`/`description`/`module_group_id`).
  - `module_group.py` → `ModuleGroupModel` (`module_groups` table: `id`,
    `name` [unique], `sort`, `created_at`, `updated_at`) — categorizes home
    tiles for display (e.g. "Inventory", "Master", "Application
    Configuration"; see `0012_create_module_groups_table.py`). Purely a
    grouping label today — the frontend home screen doesn't yet render
    modules grouped by this field, it's only editable via the
    `master_module_group` admin screen and assignable per-module via
    `ap_module`'s `module_group_id` select.
  - `app_config.py` → `AppConfigModel` (`app_configs` table: `id`,
    `app_title` [default `"SFSIS"`], `footer` [default `""`], `timezone`
    [default `config.APP_TIMEZONE_STR`, added by `0031` — issue #47, see
    "Timestamps and timezone handling" above], `created_at`,
    `updated_at`) — a **singleton** row (exactly one, seeded by
    `0016_create_app_config_table.py`) backing `home.py`'s `title`/`footer`
    fields and the `master_config` admin screen (which now also edits
    `timezone`, the live app-wide display timezone).
  - `mail_config.py` → `MailConfigModel` (`mail_configs` table: `id`,
    `smtp_host`, `smtp_port` [default `587`], `smtp_username`,
    `smtp_password`, `sender_name`, `sender_email`, `use_tls` [default
    `True`], `created_at`, `updated_at`) — also a **singleton** row, but
    unlike `app_configs` nothing seeds a default one (there's no sensible
    default mail server); `mail_config_repository.get_config()` returns
    `None` until the first save. Nothing sends mail using these settings
    yet — this only stores them for whenever that's wired up.
  - `user_module_permission.py` → `UserModulePermissionModel`
    (`user_module_permissions` table, adopted from the legacy PHP `ap_auth`
    table: `id`, `module_id` FK, `user_id` FK, unique on
    `(module_id, user_id)`) — one row = one user granted access to one
    module. No group-based or superuser-bypass permissions; every grant is
    explicit.
- **`src/repository/`**: one repository class per table, wrapping
  `SessionLocal` for CRUD. Each method opens its own `with SessionLocal()`
  block (no shared/long-lived session).
  - `user_repository.py` → `UserRepository`: the original CRUD set plus
    `get_user_by_id`, `list_users(keyword, limit, page, offset)` (paginated,
    matches/searches `username`/`email` — see pagination convention below),
    `update_user_by_id` (password only changes if a non-empty one is
    passed), `delete_user_by_id`, and `check_user_exists(...,
    exclude_id=None)` (the `exclude_id` param lets an update check
    uniqueness against everyone *else*).
  - `module_repository.py` → `ModuleRepository`: `get_module_by_name`,
    `get_module_by_id`, `get_all_modules`, `list_modules(keyword, limit,
    page, offset)` (paginated), `create_module`/`update_module` (both take
    an optional `module_group_id`), `delete_module`.
  - `module_group_repository.py` → `ModuleGroupRepository`: same
    get/list/create/update/delete shape as `location_repository.py` etc. —
    `get_group_by_id`, `get_group_by_name`, `get_all_groups`,
    `list_groups(keyword, limit, page, offset)`, `create_group`,
    `update_group`, `delete_group`.
  - `app_config_repository.py` / `mail_config_repository.py` → singleton
    repositories, a different shape from every other repository here: no
    id-based CRUD, just `get_config()` (returns the one row, or `None` for
    mail config before the first save) and `upsert_config(**fields)`
    (updates the existing row if one exists, otherwise creates it).
  - `user_module_permission_repository.py` → `UserModulePermissionRepository`:
    `has_access`, `get_modules_for_user`, `grant_access`, `revoke_access`,
    `get_module_ids_for_user`, `set_modules_for_user` (replaces a user's
    entire grant set in one call — used by the permission checklist),
    `delete_permissions_for_module` / `delete_permissions_for_user` (call
    before deleting a module/user — the FKs have no `ON DELETE CASCADE`, so
    routers must clear grants first or the delete raises a FK violation).

  **Table list/pagination convention**: every paginated `list_*` repository
  method (`list_modules`, `list_users`, `list_locations`, `list_suppliers`,
  `list_departments`, `list_materials`, `list_groups`, `list_headers` /
  `list_items_by_header` in `receiving_repository.py`/`stock_out_repository.py`,
  `list_stock_summary`, `list_usage_by_department`) and its corresponding
  router's `get_detail` (or, for item sub-lists, `get_items`) endpoint
  (`GET C_{module}/get_detail?table-keyword-filter=&limit=&page=&offset=`)
  **must** use `backend/src/core/table_query.py` instead of hand-rolling
  keyword-filtering/pagination — a Python port of the pagination/filtering
  half of a legacy PHP library called `L_database`
  (`apply_keyword_filter`/`paginate`/`attach_pagination`, replacing
  `filter_table_keyword`/`return_rows_limited`). Shape:
  - Repository method signature: `list_x(keyword="", limit=20, page=1,
    offset=0) -> tuple[list[...], Pagination]`. Body: build the base
    `session.query(...)`, call `apply_keyword_filter(query, [columns...],
    keyword)` for an OR-LIKE search across those columns, `.order_by(...)`,
    then `return paginate(query, limit=limit, page=page, offset=offset)`.
    `paginate` uses `query.count()` (not a manual `func.count(col)`), so it
    works the same for a plain query and a grouped/aggregate one (see
    `stock_repository.py`/`usage_report_repository.py`).
  - Router's `get_detail`: call the repository method, serialize each row to
    a dict, then `return attach_pagination(result, pagination)` —
    `attach_pagination` writes `db_num_rows`/`db_offset`/`db_limit`/
    `db_page`/`db_total_page` onto `result[0]` only (never every row),
    matching what `L_database::return_rows_limited` did in PHP and what
    `components/table/table.py::get_data()` on the frontend actually reads
    (`response[0]`). Do **not** manually compute `math.ceil(total/limit)` or
    an "effective offset" in a router — that belongs in `table_query.py`.
  - **`db_sort_fields`/`db_sql` metadata parity** (issue #30, 2026-07-17):
    `Pagination.to_meta()` now also emits `db_sort_fields` (whatever
    `parse_sort_fields()` returned for this request, or `False` if none was
    applied — mirrors `L_database::return_rows_limited`'s
    `$get['sort-fields'] ?? false`) and `db_sql`. `paginate(query, limit,
    page=1, offset=0, sort_fields=None)` gained the optional `sort_fields`
    kwarg purely to echo it into the metadata — it does **not** affect
    ordering (that already happened via `apply_sort()` before `paginate()`
    runs); a `list_x` method that doesn't sort yet simply doesn't pass it,
    and `db_sort_fields` comes back `False`, no per-repository code path
    required to gain the field at all. Every existing `paginate(...)` call
    site across every `list_*` repository method was mechanically updated
    to pass `sort_fields=sort_fields` (already in scope in each one, since
    every paginated method already accepts a `sort_fields` parameter for
    `apply_sort()`) — a one-line addition per call site, not new
    per-repository logic. **`db_sql` design decision** (the tension flagged
    in issue #30's acceptance criteria): SQLAlchemy's ORM has no equivalent
    to PHP's free `$db->last_query()` — compiling a query's literal SQL
    (`query.statement.compile(compile_kwargs={"literal_binds": True})`) is
    a real per-request cost and isn't dialect-safe for every column type
    (e.g. some binary/JSON values can't render as a literal). Rather than
    pay that cost on every list request for a field nothing in this
    codebase consumes yet, `paginate()` only compiles it when the
    `TABLE_QUERY_DEBUG_SQL` env var is truthy (`1`/`true`/`yes`) —
    `db_sql` is `None` in normal operation, a real compiled SQL string only
    when that debug flag is set, and any compile failure is swallowed
    (falls back to `None`) rather than breaking the actual list request.
  - **Named structured filters** (`{field}-filter` query params, added for
    issue #8's purchase report): `table_query.py::apply_field_filters(query,
    [(column, operator, value), ...])` applies each `(column, operator,
    value)` triple whose `value` is truthy, silently skipping blank/`None`
    ones — same "absent means no filter" leniency as `apply_keyword_filter`,
    just for independently-optional structured filters (a date range, a
    single FK) instead of one free-text OR-LIKE search across columns.
    `operator` is `">="`/`"<="`/`"=="`. Unlike `sort-fields[N][field]`'s
    dynamic bracket-indexed keys (which need raw `request.query_params`
    to parse), each `{field}-filter` name is fixed and known ahead of
    time, so a router binds it directly:
    `Query("", alias="start_date-filter")` — no `Request` param needed.
    The router parses/validates each value itself (e.g. a date string via
    `date.fromisoformat`, invalid/blank -> `None`) before handing the
    parsed values to the repository method, which passes them straight
    into `apply_field_filters`. **Reference implementation**:
    `purchase_report_repository.py::list_by_supplier`/`list_by_material` +
    `routers/purchase_report.py` — `start_date-filter`/`end_date-filter`
    (inclusive date range, each bound independently optional) plus a
    single-FK scoping filter per table (`supplier_id-filter` /
    `material_id-filter`). The same `start_date-filter`/`end_date-filter`
    pair was reused as-is (no FK scoping filter, out of scope for that
    report) on `usage_report_repository.py::list_usage_by_department` +
    `routers/usage_report.py` (issue #9) — the second consumer, confirming
    the helper generalizes rather than being purchase-report-specific.
  - **Generic per-column filters** (`{field}-filter` per every column, ported
    from senar's `L_database::filter()`/`filter_numeric()` — a real
    cross-language port from PHP7/CodeIgniter3 + jQuery, not a copy; issue
    #10). Distinct from the two conventions above: `apply_field_filters`
    (#8) is a *named*, hand-picked set of structured filters a router binds
    individually; `apply_column_filters(query, query_params, column_map,
    numeric_fields=())` is *generic* — every column in `column_map` gets
    its own independently-optional `{field}-filter` for free, LIKE-by-default
    or operator-syntax for any column named in `numeric_fields`
    (`_parse_numeric_filter`: a bare number means exact match, otherwise one
    or more `and`-joined `{operator}{number}` segments — `>=`, `<=`, `>`,
    `<`, `=`, `!=`/`<>`, e.g. `>=5and<=10` for a range — a *literal*
    substring split on `"and"`, matching PHP's `explode("and", $param)`
    rather than a regex word boundary). Like `sort-fields[N][field]`,
    `{field}-filter` names aren't individually enumerable ahead of time (one
    per filterable column, config-driven on the frontend) — a router needs
    a `request: Request` param and passes `request.query_params` straight
    through to the repository method, which passes it straight into
    `apply_column_filters` (no per-router parsing, unlike `apply_field_filters`'
    named params). **Precedence matches the ported PHP exactly**:
    `apply_column_filters` returns the query untouched if
    `table-keyword-filter` is also present — the free-text search and the
    per-column filter row are mutually exclusive on the senar side, not
    combined, so call `apply_keyword_filter` first and let this helper's own
    keyword check short-circuit rather than branching in the repository.
    Multi-column sort is unaffected either way — a disjoint query-param
    namespace (`sort-fields[N][field]` vs `{field}-filter`), verified to
    coexist with both keyword search and per-column filters on the same
    request. No `HAVING`/aggregate-column routing yet (senar's `$having`
    array) — no aggregate list screen is wired onto this helper yet, same
    documented gap as `apply_keyword_filter`'s own HAVING branch.
    **On by default for every non-hidden field, every table** (rolled out
    2026-07-15, same day as landing) — the frontend flips the polarity
    from the original opt-in design: `TableFilter.__init__` includes any
    field with a `name` whose `"type"` isn't `"hidden"`, unless that
    field is explicitly marked `"filter": False`. There is no
    `"filterable"` flag anymore (removed — every table gets this for
    free, matching the ported PHP where `L_database::filter()` gave every
    column passed to it its own filter, not an opt-in subset). A field's
    numeric-operator hint (`"numeric_filter": True`) is also inferred
    automatically from whatever the field already uses for
    right-alignment/number formatting (`"format": "number"` or
    `"is_numeric": True` — the same flags `TableColumns._build_data_columns()`
    reads) — one source of truth for "this column is numeric," not a
    second flag every numeric field must separately remember to set.
    Wired on every non-aggregate `list_*` repository/router pair in the
    app: `location_repository.py` (reuses its existing `_SORT_COLUMNS` map
    as the filter `column_map` too — same field names, same columns),
    `supplier_repository.py`, `department_repository.py`,
    `category_repository.py`, `material_repository.py`,
    `module_repository.py` (`sort` numeric), `user_repository.py`,
    `module_group_repository.py` (the original #10 reference),
    `receiving_repository.py` (`list_headers`'s `supplier_name` filters
    against the header's existing supplier outer-join;
    `list_items_by_header`'s `qty_received`/`price_buy` numeric),
    `stock_out_repository.py` (`list_items_by_header`'s
    `qty_out`/`price`/`total_value` numeric) — each router gained a
    `request: Request` param (or reused an existing one) forwarding
    `request.query_params` straight through, same as `master_location`'s
    existing sort wiring. **Deliberately NOT wired**: the three aggregate
    repositories (`stock_repository.py`/`usage_report_repository.py`/
    `purchase_report_repository.py`) — `apply_column_filters` has no
    `HAVING`/aggregate-column routing yet (see above), so a grouped
    query's own `column_map` entries would need to route through
    `.having()` instead of `.filter()`, which this helper doesn't support;
    #8/#9's own hand-rolled `apply_field_filters` usage on those aggregate
    reports is unaffected, still using its own narrower, named-filter
    mechanism. **Known gap — closed 2026-07-17**: every join-derived/
    denormalized display field that used to have no real column in its own
    repository's query (`stock_out`'s header `department_name`; the
    `stock_in`/`stock_out` item tables' `material_code`/`material_name`/
    `location_code`/`unit_name`; `master_material`'s `category_name`/
    `unit_name`; `ap_module`'s `module_group_name`; `ap_master_user`'s
    `department_name`) is now outer-joined into its owning repository's
    query and added to that repository's `column_map` — see "Multi-column
    sort"'s own note below for the full rollout (sort was the actual
    trigger; filtering came along for free since both mechanisms share the
    same `column_map`). No fields remain in this gap.
    Frontend half: `components/table/filter.py::TableFilter` — a
    collapsible row of `ft.TextField`s, toggled via a toolbar button
    (`Table._toggle_filter_row`) only added when at least one field opts
    in (in practice, almost always).
    **Pixel-aligned to the table body** (issue #20, reversing the original
    "free-standing row, not worth aligning" design noted below): one
    fixed-width `ft.Container` per **visible** column, in the same order
    as `TableColumns.index`/`.widths` — a non-filterable-but-visible column
    still reserves its slot (an empty `Container` of that column's width)
    so every filter field after it stays aligned, same reasoning as
    `TableColumns._reposition_handles()`'s cumulative-offset math. The row's
    outer `Container` uses `TABLE_HORIZONTAL_MARGIN` as left/right padding
    and `TABLE_COLUMN_SPACING` as inter-field spacing — the exact same
    constants `header.py`/`body.py` construct their `ft.DataTable`s with —
    so a plain `ft.Row` of fixed-width containers lines up pixel-for-pixel
    with the `DataTable`'s own `horizontal_margin`/`column_spacing`
    layout, with no absolute positioning needed (unlike the resize
    handles, which sit in a separate overlay `Stack` on top of the
    header — this is a normal `Row` underneath it). `TableFilter.reposition()`
    patches each field's `Container.width` in place from the current
    `TableColumns.widths` — cheap, since (unlike `ft.DataTable`) a plain
    `Container` genuinely does shrink on a live width patch, no rebuild
    required. `Table` calls it from every place `TableColumns.widths` can
    change: `Table.load()` (data reload — recomputed widths unless
    manually resized), `Table.build()`'s pending-data branch, and
    `Table._handle_resize_commit()` (a resize drag tick or double-tap
    reset) — the same trigger points `TableColumns._reposition_handles()`
    itself runs from for the resize handles. Reusing `TableColumns`' own
    resize/sort-aware `DataTable` header cells directly (rather than a
    parallel `Row`) was considered and rejected for the same reason as
    before: those solve a different problem (fixed per-column pixel
    widths baked into `DataColumn`s), and reusing that machinery here
    would mean touching every hardcoded `Table`/`TableColumns` index
    assumption for no real UX gain over a width-matched `Row`.
    Each filterable field also gets a leading filter icon (`prefix_icon`,
    `ft.Icons.FILTER_ALT`) and a trailing per-field clear icon
    (`suffix_icon`, `ft.Icons.CLEAR`) that clears *only that column's*
    filter value and immediately re-fetches — not a row-wide clear.
    Filtering is live (`on_change`/`on_submit` both call the same
    `on_apply` callback on every keystroke) — the row's earlier
    "Apply Filters"/"Clear Filters" `IconButton`s at the end of the row
    are gone entirely. Toggling the row closed (`TableFilter.toggle()`)
    always clears every field's value and re-fetches first, so a hidden
    row never leaves a filter silently still applied server-side. Each
    field's `border_radius=10` and the row's own `bgcolor=
    ft.Colors.SURFACE_CONTAINER_HIGH` match the table search bar's
    styling (issue #19).
    `Table._build_toolbar_with_filter_row()` folds the filter row into the
    *same* top-level `controls` slot the toolbar alone used to occupy
    (`ft.Column([toolbar, filter_row])` as one element) rather than adding
    a new slot — `Table.load()`/`_handle_resize_commit()`/
    `_handle_sort_change()` all hardcode `col.controls[1]`/`[2]` as
    header/body, so inserting a genuinely new top-level control would have
    shifted those indices and silently broken every one of those call
    sites. `Table.get_data()` appends `TableFilter.serialize()`
    (`&{field}-filter=value` for every non-blank field) alongside the
    existing `table-keyword-filter`/`custom_param`/`sort-fields[...]`
    params — same wire-format convention, no special-casing needed on the
    frontend for the keyword-vs-column-filter mutual exclusivity (the
    backend enforces that; sending both is harmless).
  - **Date-formatted columns match by displayed text** (issue #61,
    2026-07-28): a `date`-formatted column's `{field}-filter` used to
    `LIKE` the column's raw stored value (an ISO `YYYY-MM-DD` string) —
    typing `27` only matched if the raw ISO text happened to contain
    "27" literally, and typing a month name (`jul`) could never match at
    all, since the raw value has no month name in it. Checked senar's
    `L_database.php` for a reference first (same precedent this feature
    already follows for `numeric_fields`) — found only a commented-out,
    never-finished `filter_datetime()` stub (~line 1150), no working
    implementation to port; this is a new feature built on the existing
    `numeric_fields` pattern, not a straight port.
    `core/table_query.py::apply_column_filters` gained a `date_fields:
    Sequence[str] = ()` parameter (same shape as `numeric_fields`) — any
    column named there is wrapped in `func.date_format(column, '%d %b
    %Y')` (MariaDB) before a case-insensitive `LIKE '%value%'`. The
    format string is a deliberate, token-for-token mirror of
    `frontend/src/utils/formatting.py::format_date()`'s Python-side
    `strftime("%d %b %Y")` — `%d` day, `%b` abbreviated month, `%Y` 4-digit
    year — so the SQL-side text always matches what's actually rendered on
    screen. Typing `27` now matches every date containing "27" anywhere in
    its formatted text (day 27 *or* year ending 2027, e.g. both "27 Jul
    2026" and "15 Jul 2027"); typing `jul` (any case) matches every date in
    July. Frontend: `components/table/filter.py`/`components/list/filter.py`
    both infer date-filter treatment the same way the existing numeric hint
    is inferred — automatically from `"format": "date"`, or an explicit
    `"date_filter": True` override — swapping the filter field's hint text
    to `"e.g. 27 or Jul"` (no operator syntax needed, unlike numeric — it's
    a plain substring match either way, the hint is purely to tell the user
    what kind of substring to type).
    **Reference implementation, wired end-to-end**:
    `receiving_repository.py`'s header `list_headers` — its `date` column
    used to be **sort-only** (see the now-corrected note below), even
    though `stock_in/index.py`'s frontend `date` field already had
    `"filter": True` set (it's a `List` screen's default leading/sortable/
    filterable column) - meaning that filter input was rendered but
    silently did nothing server-side until this issue wired `date` into
    `_HEADER_FILTER_COLUMN_MAP` (merged with what used to be the separate
    `_HEADER_SORT_COLUMN_MAP`, now just one map since `date` is both
    sortable and filterable) and passed `date_fields={"date"}` to
    `apply_column_filters`. Verified live in the browser (`stock_in/index`,
    List view, 30 real records): filtering `27` correctly narrowed to
    exactly the one record dated "27 Jul 2026" (`Record 1-1 of 1`);
    filtering `jul` correctly returned all 30 July records (`Record 1-20 of
    30`, i.e. unfiltered — every seeded record happens to be in July);
    backend logs confirmed clean `200 OK` responses for both
    `date-filter=27`/`date-filter=jul` requests, no errors.
  - **Multi-column sort** (ported from the same original app's
    `y.form.js`/`y.panel.js` sortable-header UI, ADR discussion 2026-07-13):
    `table_query.py::parse_sort_fields(request.query_params)` parses
    `sort-fields[N][field]=ASC|DESC` query params (`N` = priority order) —
    exact wire-format match for `y.form.js`'s `serializeOrderBy()` /
    `L_database::sort()`'s `ksort()`-by-index convention, so a router needs
    `request: Request` (not just typed `Query(...)` params — FastAPI can't
    bind a dynamic bracket-array key that way) purely to reach
    `request.query_params`. `table_query.py::apply_sort(query, sort_fields,
    column_map)` then applies `ORDER BY` in that priority order, resolving
    each `field` name to a real column via `column_map` (a module-level
    `dict[str, InstrumentedAttribute]` per repository, e.g.
    `location_repository.py::_SORT_COLUMNS`) — an unrecognized field name is
    silently skipped, matching the PHP's leniency. A `list_x(...,
    sort_fields=None)` param takes this and, when given, replaces (not adds
    to) the method's own default `.order_by(...)`.
    - **Reference implementation**: `location_repository.py::list_locations` /
      `routers/master_location.py::get_detail` on the backend,
      `pages/modules/master_location/index.py`'s `code`/`name` fields
      marked `"sort": True` on the frontend.
    - **Rolled out to every paginated `list_*` method as the default**
      (issue #27, 2026-07-17) — same mechanical per-endpoint change (add a
      `sort_fields` param + `apply_sort(query, sort_fields, column_map)` +
      `parse_sort_fields(request.query_params)` in the router) applied to
      `supplier_repository.py`, `department_repository.py`,
      `category_repository.py`, `material_repository.py`,
      `module_repository.py`, `user_repository.py`,
      `module_group_repository.py`, `unit_of_material_repository.py` (found
      via a repo-wide grep for `list_*` methods during implementation — not
      in the issue's own list, but the exact same shape and just as much
      "every table" as anything else), `receiving_repository.py`
      (`list_headers` and `list_items_by_header`), `stock_out_repository.py`
      (`list_headers` and `list_items_by_header`) — every one of these
      repositories' existing `_FILTER_COLUMN_MAP`/`_SORT_COLUMNS` dict from
      the #10 per-column-filter rollout is reused as-is for `apply_sort`'s
      own `column_map`, since it's already exactly "field name -> real
      column". Each affected `get_detail`/`export_detail`/`get_items`/
      `export_items` router endpoint now also calls `parse_sort_fields` and
      passes it through, so an export honors whatever sort is currently
      applied on screen, same as `master_location`'s own export already did.
      `receiving_repository.py`/`stock_out_repository.py`'s header
      `list_headers` additionally gained a `date` sort entry (a real
      column) — **originally sort-only** (no `date-filter` UI existed for
      these headers, that was the purchase/usage reports' own job) via a
      separate `_HEADER_SORT_COLUMN_MAP = {**_HEADER_FILTER_COLUMN_MAP,
      "date": ...}` spread. **Superseded for `receiving_repository.py` by
      issue #61** (see "Date-formatted columns match by displayed text"
      above) — `date` is now filterable too (matching its *displayed*
      text, not the raw value), so `_HEADER_FILTER_COLUMN_MAP` and
      `_HEADER_SORT_COLUMN_MAP` collapsed into one map there.
      `stock_out_repository.py`'s own header `date` remains sort-only for
      now — issue #61 only wired one reference repository end-to-end, this
      one wasn't touched.
      **Deliberately still unsortable**: every join-derived/denormalized
      display field with no real column in its own repository's query —
      the exact same list already documented as a filtering gap under
      "Generic per-column filters" above (`stock_out`'s header
      `department_name`, item tables' `material_code`/`location_code`/
      `unit_name`, `master_material`'s `category_name`/`unit_name`,
      `ap_module`'s `module_group_name`, `ap_master_user`'s
      `department_name`) — marking one of these `"sort": True` on the
      frontend without a matching `column_map` entry would render a
      clickable sort icon that silently does nothing (`apply_sort` skips
      unrecognized fields), so none of them are marked sortable. The three
      aggregate/grouped repositories (`stock_repository.py`,
      `usage_report_repository.py`, `purchase_report_repository.py`) are
      also out of scope, same documented exception as the filter rollout —
      `apply_sort`'s plain `.order_by()` doesn't need `HAVING`-aware routing
      the way an aggregate column would, but no aggregate list screen is
      wired onto sort yet either, so it wasn't extended speculatively.
    - Frontend half lives entirely in `components/table/columns.py`:
      `TableColumns.sort_order` is an ordered `[(field_name, "ASC"|"DESC"), ...]`
      list (list order = priority, mirrors `y.form.js`'s
      `this.orderBy[table]` array). `TableColumns.on_sort(e)` — wired as every
      sortable `DataColumn`'s `on_sort`, which makes Flutter's own
      `DataColumn` tap handling cover the *whole* header cell for free
      (no custom `GestureDetector` needed, unlike the resize handle) —
      cycles that column's state `none -> ASC -> DESC -> none` via
      `_find_sort_state()`, and clicking a *different* sortable column
      while one is already active appends it as an additional sort key
      rather than replacing it: true multi-column sort with no shift/ctrl
      modifier, matching the reference's
      `#setOrderByAsc`/`#setOrderByDesc`/`#resetOrderBy` exactly. Each
      sortable column always renders its own state icon
      (`TableColumns._build_sort_icon()` — neutral `unfold_more`, or an
      up/down arrow once active) as part of its label, since Flet's
      `DataTable` has no multi-column sort indicator of its own (it only
      ever highlights one `sort_column_index`, which this table never
      sets) - unlike an earlier, wrong guess about a *phantom*
      Flutter-drawn icon on every sortable column regardless of active
      state (reverted - see the git history around 2026-07-13), this one
      is real and always visible for a sortable column, so
      `_SORT_ICON_WIDTH` is a correct, exact reservation, not an
      approximation. The icon sits at the column's far-right edge (not
      glued directly onto the label text): `_build_data_columns()` builds
      the field icon + label as one `left_content` group, then — only for
      a sortable column — wraps `[left_content, sort_icon]` in a second
      `ft.Row(alignment=SPACE_BETWEEN)`, which fills the fixed-width
      header `Container` below it (no `alignment` set there, so the
      Container passes its own width down as a tight constraint — same
      mechanism `components/form/date.py`'s docstring documents for why an
      alignment-less Container forces full width onto its child) and
      pushes the icon to that width's far edge. `TableColumns.serialize_sort()`
      builds the
      `&sort-fields[N][field]=...` query string
      `components/table/table.py::get_data()` appends on every request.
      `TableColumns.on_sort_change` (wired to `Table._handle_sort_change`)
      fires after every toggle: an instant optimistic header-only rebuild
      (icons update immediately, same split as the reference doing its
      `icon.classList` swap synchronously before the AJAX call), then
      `get_data()` re-fetches with the new sort - deliberately **not**
      resetting to page 1 (only a page-*size* change does that), matching
      `y.form.js`'s `serializePagination`/`listenerHeaderTable`. Sort
      state itself isn't persisted anywhere (matches the reference - an
      in-memory `this.orderBy[table]` there too), so it resets whenever a
      `Table`/`TableColumns` instance itself is torn down and rebuilt (e.g.
      navigating away and back).
    - **`TableBody`'s hidden structural header row never gets sort icons**:
      `TableColumns.build(interactive: bool = True)` gates icon/`on_sort`
      rendering on `interactive`, and `TableBody.build()` always calls it
      with `interactive=False` — Flutter doesn't fully clip a zero-height
      heading row's content, so an icon there would otherwise bleed into
      the first data row.
    - `Table.build()` defaults to `TABLE_OUTER_HORIZONTAL_PADDING` (12px)
      horizontal padding app-wide instead of flush-to-edge.
    - **Final sort-icon layout, after four rounds of fixes each targeting
      the wrong layer** (label-right-edge `SPACE_BETWEEN` → tight
      icon-next-to-label → non-tight `END`-aligned → the actual fix):
      `DataColumn.on_sort`, whenever non-null, makes Flutter's `DataTable`
      reserve space for its own native (never-painted, since
      `sort_column_index` is never set) sort-arrow indicator on that
      header cell — inflating a sortable header wider than its own
      `Container(width=w)` and desyncing it from the body's column width,
      regardless of how the icon's own `Row` was laid out. Fixed by never
      setting `DataColumn.on_sort` (always `None`) and instead wiring
      `Container.on_click` directly on each sortable header cell
      (`TableColumns._on_header_click(field_name)`) — restores
      label-left/icon-right with header/body widths now genuinely in
      sync. Full round-by-round investigation in CHANGE_HISTORY.md
      (2026-07-17).
    - **Sort rolled out to every remaining table** (2026-07-17), including
      the three aggregate/grouped report repositories (ordinary `ORDER BY`
      on a grouped column or `func.sum(...)` expression needs no
      `HAVING`-aware routing the way filtering does) — `stock_repository.py
      ::list_stock_summary` was restructured to outer-join
      `InventoryValueModel` directly into the grouped query so
      `average_price`/`value` are real, sortable SQL expressions instead
      of a separate post-pagination Python lookup.

  **Sticky table footer + lazy-load/pagination toggle** (issue #30,
  2026-07-17, ported from senar's `y.panel.js`'s
  `#createRecordInfoPanel()`/`createPaginationButtonSet()`/
  `createPaginationButton()` and `y.form.js`'s
  `updateTableInfoMessage()`/`listenerPagination()`/`#handleSetPage()`/
  `#handleSetPageLimit()`): every `Table` now gets a
  `components/table/footer.py::TableFooter` for free — a two-row sticky
  footer (`self.footer`, built in `Table.__init__`) sitting below the
  body, appended as a brand-new **fourth** slot (index 3) in the table's
  top-level `controls` list rather than folded into any existing slot —
  `Table.build()`/`Table.load()`/`Table._handle_resize_commit()` all
  hardcode `col.controls[1]`/`[2]` as header/body (see issue #20's
  documented warning about exactly this fragility); appending purely
  additively at the end means none of those indices had to change.
  **Not built for `is_inside_form` tables** (entry-mode grids like
  `stock_out/item_new.py`'s per-location qty-entry table) — those never
  call `get_data()` at construction and aren't a real dataset a user
  pages through, so a "Record X of Y" message would be meaningless there;
  `self.footer` is `None` for those and every call site checks it before
  touching it.
  - **Two-row layout** (per the user's explicit clarification over the
    original single-row sketch, confirmed via `/planner`): row 1 is the
    totals message (`"Record {first} - {last} of {total}"`, or `"No
    records"` for an empty table), sourced from the exact same
    `db_num_rows`/`db_total_page` metadata `Table.get_data()` already
    reads off `response[0]` — no new plumbing, just a new consumer
    (`TableFooter._info_message()`). Row 2 is right-aligned: the
    lazy-load/pagination mode-toggle icon button, plus — only in
    pagination mode — the pagination controls themselves alongside it
    (editable rows-per-page input, first/prev/numbered-with-ellipsis/
    next/last buttons, current page highlighted with a filled `PRIMARY`
    circle).
  - **Mode toggle is a genuinely new idea for this app, not a senar
    port** (confirmed with the user) — senar's own reference always
    renders pagination buttons; it has no lazy-scroll mode to toggle
    against (lazy-load, `Table._handle_scroll_end`, was this app's own
    pre-existing addition). **Default mode is lazy-load** (explicit,
    user-confirmed constraint) — `TableFooter.mode` starts at
    `MODE_LAZY`, so no existing table's default look/behavior changes
    until a user explicitly clicks the toggle. **Mode state is
    session-only, never persisted** (explicit, user-confirmed constraint,
    matches the existing "no new `repository/`-layer storage class"
    precedent) — `self.mode` lives purely as an in-memory attribute on
    the `TableFooter` instance, same lifetime as `TableColumns.sort_order`:
    it resets whenever the owning `Table` is torn down and rebuilt (e.g.
    navigating away and back). Toggling calls
    `Table._handle_footer_mode_change(mode)`, which always resets to page
    1 and does a full non-append refetch (`get_data(page_no=1, offset=0,
    append=False)`) regardless of direction — the simplest way to
    reconcile lazy-load's accumulated multi-page `self.data` with
    pagination's single-page view, and consistent with the pre-existing
    "only a page-size/mode change resets to page 1" rule
    `_handle_sort_change`'s own docstring already documents for sort.
  - **Pagination controls**: `Table._handle_footer_page_change(page_no)`
    (first/prev/numbered/next/last buttons) always replaces the current
    page's data (`append=False`, `offset=(page_no-1)*limit`) — unlike
    lazy-load's infinite-scroll accumulation, one page click shows
    exactly one page's rows. `Table._handle_footer_limit_change(new_limit)`
    (the rows-per-page `TextField`, committing on Enter or blur) resets to
    page 1, matching `#handleSetPageLimit`'s own reset-on-limit-change
    behavior. Numbered-button generation
    (`footer.py::_page_number_tokens(current, total)`) always keeps the
    first page, the last page, and a small window around the current page
    (`current-1`/`current`/`current+1`), inserting a `None` "..." gap
    marker wherever the kept pages aren't contiguous — adapted from (not a
    literal line-for-line port of) `y.panel.js`'s own ~7-visible-button
    cap (`_MAX_VISIBLE_PAGE_BUTTONS`), verified via a standalone unit test
    with `flet` stubbed out (pure function, no UI calls):
    `tokens(1, 3) == [1, 2, 3]` (short list, no ellipsis needed),
    `tokens(1, 20) == [1, 2, None, 20]`, `tokens(10, 20) == [1, None, 9,
    10, 11, None, 20]` (both-side ellipsis around a middle page),
    `tokens(20, 20) == [1, None, 19, 20]` (last page active), `tokens(4,
    7) == [1..7]` (exactly at the cap, still no ellipsis).
  - **Lazy-load mode is otherwise unchanged** — `Table._handle_scroll_end`
    gained one guard clause (`if self.footer is not None and
    self.footer.mode != MODE_LAZY: return`) so infinite-scroll-on-bottom
    only fires in lazy mode; once toggled to pagination, paging happens
    only via the footer's own buttons, matching the acceptance criteria's
    "lazy-load mode must not regress" requirement.
  - **Backend**: no new endpoint — same `GET .../get_detail?...&limit=&
    page=&offset=` every table already calls, confirmed (via `/planner`,
    reading `Table.get_data()`'s actual code before assuming) to already
    serve both an infinite-scroll caller (`append=True`, ever-incrementing
    `page_no`) and a jump-to-page caller (`append=False`, arbitrary
    `page_no`/`offset`) identically — see the `db_sort_fields`/`db_sql`
    metadata-parity entry above (same issue #30) for the one backend
    change this issue needed.
  - Verified: backend `paginate()`/`Pagination.to_meta()` against a real
    SQLite session (`db_sort_fields`/`db_sql` present/absent correctly
    under the debug flag, `db_num_rows`/`db_total_page` correct);
    `footer.py::_page_number_tokens()` via the standalone unit test above.
    **Not yet confirmed in a live browser** — before relying on this
    further, click through: toggle to pagination on a multi-page table,
    click through first/prev/numbered/next/last, change the rows-per-page
    input, toggle back to lazy-load and confirm scroll-to-load-more still
    works.

  **Table export/upload convention** (multi-format download 2026-07-14,
  CSV/XLSX upload added same day for issue #4): every `Table` gets a
  hamburger-icon menu at the far right of its toolbar for free
  (`components/table/menu.py`, class `TableMenu` — renamed from the original
  `export_menu.py`; wired into `Table.__init__` as `self.export_menu`,
  appended rightmost by `toolbar.py`). Menu contents by table kind:
  non-input tables get the 6 download entries; `is_inside_form=True`
  tables (input-mode grids like `stock_out` item_new's per-location
  qty-entry table — the *primary* upload use case) skip downloads
  entirely, since no `C_{module}/export_{name}` endpoint exists for them.
  Downloads offer the table's *entire* current filtered/sorted result set
  (not just the loaded page) as CSV, TSV, SCSV, XLSX, ODS, or PDF. Backend
  half: `backend/src/core/table_export.py::export_response(rows, columns,
  format, filename_base)` renders any of the 6 formats from a plain
  `list[dict]` + `[(field, label), ...]` column spec.

  **Upload entries are gated on the table actually having somewhere to put
  the uploaded values** (issue #22, 2026-07-16) — `Menu.__init__` only
  appends "Upload from CSV"/"Upload from XLSX" (and the separator before
  them, when downloads are also present) when at least one of the table's
  `fields` has a `"type"` in the module-level `_EDITABLE_TYPES` set
  (`input`, `textarea`, `select`, `option`, `datepicker`, `checkbox` — the
  same set `TableRows._build_editable_cell()` dispatches on). Before this, the
  menu always offered both upload entries regardless of `is_inside_form`,
  which was actively misleading on a purely read-only list table (e.g.
  `master_material`/`stock_in`'s header list — every field `label`/
  `hidden`) since there was nothing editable for an upload to populate;
  bulk record creation for those tables already goes through the "Add
  New" screen's own separate bulk-upload menu (issue #5,
  `components/form/menu.py::MenuForm`), so this isn't a lost capability, just a
  dead one. The gate is based on the fields themselves, not the
  `is_inside_form` flag, so it composes correctly with the download gate
  independently: a non-form table that happens to have an editable column
  gets downloads + separator + uploads (all three sections); a
  read-only non-form table gets downloads only; an `is_inside_form` table
  with editable fields (the common case) gets uploads only, no leading
  separator (nothing precedes it); the never-yet-seen case of an
  `is_inside_form` table with zero editable fields gets an empty menu
  (harmless, no real table hits this today).

  **Upload half is entirely client-side** (in the Flet process): the
  picked file's bytes are parsed (`parse_csv_bytes` sniffs comma/
  semicolon/tab so this table's own SCSV/TSV downloads round-trip;
  `parse_xlsx_bytes` via openpyxl; blank rows skipped) and matched
  against the table's columns by visible label or field name,
  case-insensitive. Label (read-only) columns whose headers appear in
  the file form a possibly-composite key selecting which loaded rows to
  fill; with no key columns in the file, editable cells fill
  sequentially row-by-row. Only rows currently loaded on the client are
  populated (lazy-loaded pages ignored); values land in the editable
  controls only — persisting still goes through the screen's own submit.
  Three hard-won Flet 0.85 invariants live in `menu.py` (each broke the
  app in a different way before being learned — see CHANGE_HISTORY
  2026-07-14):
  1. `ft.FilePicker` is a `Service`, not a visual Control: it registers
     via `page.services` (like `ft.SharedPreferences` in
     `repository/storage.py`), never `page.overlay` (which renders it as
     "Unknown control FilePicker" client-side).
  2. `page.services` resolves through the ROOT VIEW (`views[0]`) and
     **raises RuntimeError while `page.views` is empty** — which is
     exactly the state during `ModulePage.__init__` (route_change clears
     views first; module_loader.build appends the new view only after
     the constructor returns). So `Menu.__init__` must be completely
     page-passive; the picker is created and registered lazily inside
     the async click handler (on the event loop, with a live root view).
     Registering at construction also dies with the old root view on the
     next navigation anyway.
  3. An `on_click` that calls an async method must BE an `async def`
     closure — a sync `lambda e: self._async_method(...)` returns an
     un-awaited coroutine that Flet's dispatcher (which checks
     `inspect.iscoroutinefunction`) silently drops ("coroutine was never
     awaited", handler never runs).
  `pick_files(..., with_data=True)` returns the file's bytes directly
  (web and desktop), which is why no `upload_url`/`FLET_UPLOAD_DIR`/
  `on_upload`-progress flow is needed to *read* a spreadsheet — the
  `upload_dir` wiring in `asgi.py`/`entrypoint.sh` remains for any
  future feature that genuinely needs server-side files.

  **Bulk create convention** (issue #5, 2026-07-14, ALL OR NOTHING;
  revised issue #24/#25, 2026-07-16): a screen gets a bulk-upload
  hamburger menu at the far right of its `ModuleToolbar` — "Upload bulk
  from CSV/XLSX" — whenever it explicitly opts in via
  `Form(..., bulk_input=True)`; `Form.build()` then attaches
  `components/form/menu.py::MenuForm` for it (runs in `build()` rather
  than `__init__` so it lands *after* the screen's own submit button, i.e.
  rightmost, and obeys the same three Flet invariants as the table menu
  above). **`bulk_input` replaced an earlier implicit `parent.screen ==
  "new"` guard** — that guessed wrong in two ways: it silently attached a
  menu to `ap_config/new.py` even though that module's backend router has
  no `submit_bulk` endpoint at all (clicking upload there just errors),
  and it couldn't be used for a bulk-eligible screen whose route isn't
  literally `"new"` (stock_in's `item_new`, see below). Every module
  `new.py` that has a real `submit_bulk` backend endpoint now passes
  `bulk_input=True` explicitly; `ap_config/new.py` deliberately does not
  (no backend support — the old implicit menu there was a latent, unused
  bug, not a feature, and is gone now).

  The file is parsed client-side with the same `parse_csv_bytes`/
  `parse_xlsx_bytes`, headers matched to form fields by label or name
  (case-insensitive, unknown columns ignored, blank rows skipped),
  `select` cells resolved against `call_{name}_select` options by label or
  value (an unresolvable cell aborts the whole upload client-side with
  `Row N: unknown <label> '<value>'`), then **every row goes in ONE POST**
  to `endpoint` — `MenuForm(page, form, endpoint=None, extra_fields=None,
  redirect_route=None)` defaults `endpoint` to `C_{module}/submit_bulk`
  and `redirect_route` to `/modules/{module}/index`, both overridable via
  `Form(bulk_endpoint=..., bulk_redirect=...)` for a screen posting
  somewhere else (see the item-level case below); `extra_fields` (via
  `Form(bulk_extra_fields={...})`) are merged into the payload as
  constant, non-repeated form fields on every request, alongside the
  repeated per-row lists and the parallel `row_number` list carrying the
  file's own numbering (header counts as row 1 among non-blank rows).

  **Header-level bulk create** (the original #5 shape): backend
  `services/bulk_service.py::bulk_create(rows, build_instance)` owns one
  `SessionLocal()` for the whole batch (per-table repositories can't
  share a transaction — same reasoning as `inventory_service.py`), adds +
  **flushes per row** (so unique-constraint violations — in-file
  duplicates and DB conflicts alike — surface attributed to the offending
  row) and commits once; any failure rolls back everything and returns
  `{"error": "Row N: <same message as that module's single submit>"}`.
  Each router supplies a small `build(row, session)` validating one row
  (e.g. `user_admin.py` reproduces "Username or email already in use" via
  a session query that also sees rows flushed earlier in the same file,
  and bcrypt-hashes each password). Wired (`Form(bulk_input=True)` on the
  frontend, `POST C_{module}/submit_bulk` on the backend) on 11 module
  `new.py` screens: `master_location`, `master_supplier`,
  `master_department`, `master_material`, `master_category`,
  `master_unit_of_material`, `master_module_group`
  (`module_group_admin.py`), `ap_module` (`module_admin.py`),
  `ap_master_user` (`user_admin.py`), `stock_in` and `stock_out` (headers
  only), each gated by its module's `require_module_access`.

  **Item-level bulk create** (issue #24, 2026-07-16 — the first,
  currently only, per-header item bulk-create): `stock_in/item_new.py`
  opts in with `Form(bulk_input=True, bulk_endpoint=f"C_{module}/
  submit_bulk_item", bulk_extra_fields={"receiving_header_id":
  str(self.header_id)}, bulk_redirect=f"/modules/{module}/edit/
  {self.header_id}")` — the header id rides along on every uploaded row
  the same way `callback_submit` already sends it for a single-item
  submit, and a successful upload returns to the header's edit screen
  (there's no bare "index" for an item, only its owning header).
  `POST C_stock_in/submit_bulk_item` (form: `receiving_header_id` plus
  repeated `material_id`/`location_id`/`qty_received`/`price_buy`/
  `remarks` + `row_number`) doesn't go through `bulk_service.bulk_create`
  — that helper's single `session.add(build_instance(row, session))`
  shape doesn't fit a receiving item's three co-dependent writes
  (`ReceivingItemModel` + `StockModel` + the material's
  `InventoryValueModel` MAP update). Instead
  `inventory_service.py::create_receiving_items_bulk(receiving_header_id,
  rows)` is a bespoke bulk function living alongside
  `create_receiving_item`, following the same
  ALL-OR-NOTHING/one-`SessionLocal()`/flush-per-row convention, validating
  each row (required fields, numeric parsing, an inactive material
  rejected with the same `"Cannot receive: material is inactive"`
  `submit_item`'s create path already uses) before committing once at the
  end. Each row's MAP contribution applies against whatever
  `InventoryValueModel` state the *previous* row in the same batch already
  flushed — identical sequencing to calling `create_receiving_item` once
  per row, just inside one transaction instead of one per call. Verified
  against a real SQLite session: 2-row happy path with correct weighted
  MAP; an inactive material in row 2 rolls back row 1 too (true
  all-or-nothing, not partial commit); missing-required-field and
  empty-batch rejections.

  **`MenuForm` decoupled from `Form`** (issue #25, 2026-07-16): it used to
  take a `form` object and read only two things off it —
  `form.parent`/`form.fields` — so its constructor now takes `parent`/
  `fields` directly instead. `Form._attach_bulk_menu()` still passes its
  own `self.parent`/`self.fields` through unchanged, but a screen with no
  `Form` at all can now construct `MenuForm` directly (see stock_out's
  item-level bulk upload immediately below, the first caller that isn't a
  `Form`).

  **Bare-code matching for every bulk-upload `select` cell** (issue #25,
  2026-07-16): every `call_*_select` endpoint in this app returns options
  with labels in a consistent `"{code} - {name}"` shape (confirmed for
  material, location, supplier, department, unit, category), so
  `components/table/menu.py::resolve_option_value(value, options)` —
  `options` a `[(value, label), ...]` list — now resolves a typed cell
  against, in order: the raw `value` (DB id), the full `label`, or just the
  label's code prefix (everything before the first `" - "`, e.g. `"SKU-1"`
  matching `"SKU-1 - Widget"`). Both independent bulk-matching code paths
  route through this one function instead of duplicating the same
  three-way rule: `components/form/menu.py::MenuForm._build_payload()`
  (header/item bulk uploads — retroactively covers every existing one:
  #24's stock_in item bulk, every #5 header bulk including
  `master_material`'s `unit_id`/`category_id`) and
  `components/table/menu.py::TableMenu._set_control_value()` (`is_inside_form`
  table uploads' `select`/`option` cells).

  **Multi-material item bulk create** (issue #25, 2026-07-16 — distinct
  from #24's item-level bulk above): `stock_out/item_new.py` isn't a
  `Form` at all (it's hand-built around a material dropdown scoping a
  single-material `Table`, see "Master-detail pattern" below), and that
  dropdown-driven flow can only ever issue one material per screen visit.
  A bulk upload needs to accept **several different materials in one
  file** (`Material | Location | Qty Issue | Remarks` per row), which
  doesn't fit "pick one material first" at all — so this bulk menu is
  wired **independent of** the dropdown, constructing `MenuForm` directly
  (`parent=self, fields=[material_id, location_id, qty_out, remarks]`,
  `endpoint="C_stock_out/submit_bulk_items"`,
  `extra_fields={"stock_out_header_id": ...}`,
  `redirect_route=".../edit/{header_id}"`) right after
  `add_submit_button` in `__init__`, appended straight onto
  `view.toolbar.right` the same way `Form._attach_bulk_menu()` does it
  internally. `POST C_stock_out/submit_bulk_items` (form:
  `stock_out_header_id` + repeated `material_id`/`location_id`/`qty_out`/
  `remarks`/`row_number`) combines rows that repeat the same
  `(material_id, location_id)` pair, then validates the combined qty
  against current stock **grouped per material** (`list_stock_by_material`
  is itself per-material) before calling
  `inventory_service.create_stock_out_item` once per pair — same
  up-front-validate-then-loop-commit pattern `submit_items` already uses
  for its own single-material multi-location case, **not** a single DB
  transaction (a stock change racing the up-front check is still possible
  and caught by `InsufficientStockError`, same documented caveat
  `submit_items` already carries). Verified via `TestClient` against a
  real SQLite session (`StaticPool` in-memory, `dependency_overrides` on
  the router's own `_require_access` object — overriding a fresh
  `require_module_access("stock_out")` call doesn't work, `dependency_overrides`
  keys by the exact callable object and that factory returns a new closure
  every call): two different materials issued in one batch with correct
  captured price/total_value; an insufficient-stock row rejects the whole
  batch (the other, valid row in the same batch is correctly *not*
  applied either); two rows repeating the same (material, location) pair
  correctly combine into one item with the summed qty; a missing
  `stock_out_header_id` is rejected.

  **Every list endpoint `get_{name}` gets an export twin
  `export_{name}`** — the table *name* is part of the contract because
  one module can hold several tables (`stock_in` has the `detail` header
  list on index AND the `items` sub-table on the header's edit screen,
  scoped by its `header_id` custom param, which flows through the export
  query string unchanged). So: `GET C_{module}/export_detail?format=...&
  table-keyword-filter=...` next to `get_detail`, and
  `GET C_{module}/export_items?header_id=...&format=...` next to
  `get_items`. Each is gated by the same `require_module_access(...)`
  dependency as the rest of its module and re-runs its own `list_*`
  repository call with `limit=0` (the `table_query.py::paginate()`
  convention for "no limit, return everything") instead of the paginated
  `limit`/`page`/`offset` triple, then calls `export_response(...)`.
  Wired: `export_detail` on `master_location` (the only one whose export
  also honors `sort_fields`, matching `get_detail`'s own sort rollout
  above), `master_supplier`, `master_department`, `master_material`,
  `ap_module`, `ap_master_user`, `master_module_group`, `stock_browse`,
  `usage_report`, `stock_in`, `stock_out`; `export_items` on `stock_in`
  and `stock_out`. (`stock_out`'s `get_stock_by_material` deliberately
  has no export twin — its only consumer is the `is_inside_form` entry
  grid, which never shows the menu.)

  Getting the actual bytes into the browser needed one new piece of
  frontend-only plumbing, because of the same "Container networking
  gotcha" documented under Frontend Architecture below: the containerized
  frontend's `HttpClient` calls always run **server-side** (the Flet
  process), so the browser itself has no session cookie for the backend
  and can't be pointed at a backend export URL directly, nor can the
  Flet process just push raw bytes at an already-open browser tab. The
  fix is a plain HTTP proxy route, `GET /download/{module}/{table_name}`
  (mapping to the backend's `C_{module}/export_{table_name}`), added
  directly to the FastAPI app `asgi.py` builds (`ft.run(...,
  export_asgi_app=True)`) — **must be inserted at the front of
  `_fastapi_app.router.routes`**, not appended via the normal
  `@app.get(...)` decorator, because Flet's own catch-all `/{path:path}`
  SPA route is already registered by the time this module runs and would
  otherwise shadow it (routes match in registration order). The handler
  is a **sync** `def` (FastAPI runs sync path functions in a threadpool,
  so the blocking `requests.get` call below doesn't block the event
  loop): it resolves the client id from a `client_id` query param first
  (the launching Flet session appends its own id in `menu.py` —
  that id directly names the session file holding the login that
  triggered the download, immune to whatever cookie state the browser is
  in), falling back to the `sfsis_client_id` cookie, then loads that
  browser's persisted `server_url`/`http_cookies` via
  a new `utils/persistence.py::load_client_session(client_id)` helper
  (a synchronous, page-free read of the same per-client JSON file
  `_ServerFileStore` uses — needed because this route handles a plain
  HTTP request with no live Flet `Page`/websocket context to hang a
  `Storage` instance off of), calls the backend's `/C_{module}/export`
  with those cookies, and streams the response straight back with the
  backend's own `Content-Disposition`/`Content-Type` headers intact — the
  browser ends up with a correctly-named real file download, not a data
  URI with a browser-generated filename. `menu.py`'s click handler
  just does `page.launch_url(f"/download/{module}/{name}?...")`; no popup/new-tab
  target needed since a `Content-Disposition: attachment` response never
  navigates the browser away from the running app, the same as clicking a
  plain `<a download>` link.

- **`src/services/`**: business logic that composes repositories +
  `core/`. `auth_service.py`:
  - `authenticate(username, password, totp)` checks the user is active,
    verifies the bcrypt password, then verifies TOTP; raises
    `HTTPException(401)` on any mismatch.
  - `get_current_user(request)`, a FastAPI dependency that resolves the
    logged-in user from `request.session["username"]` (401s if missing or
    the user is now inactive).
  - `require_module_access(module_name)`, a dependency *factory* — call it
    once per router with the module name to get a dependency that 401s if
    not logged in, 403s if not granted access to `module_name` via
    `user_module_permissions`. **Superusers (`is_superuser=True`) bypass the
    grant check** — this is a deliberate bootstrap escape hatch (someone has
    to be able to create modules and grant permissions before any grants
    exist) and is the only place superuser status has special meaning; it
    does **not** affect `C_home/home`'s module list, which always reflects
    real grants even for superusers.
- **`src/routers/`**: FastAPI `APIRouter`s, one per frontend module prefix
  (matches the `C_<module>` convention). `login.py` → `C_login` prefix:
  - `GET C_login/get_session?param=<username>` → `{"tok": "..."}` (pre-auth
    token for the *next* login attempt).
  - `POST C_login/login` (form data: `username`, `password`, `totp`,
    `_tok`, `client_type`) → validates the token, then
    `auth_service.authenticate(...)`, then sets `request.session["username"]`.
    Responds `200` with an **empty body** on success (the frontend's
    `HttpClient` treats an empty non-JSON `200` as `{"status_code": 200}`)
    or `401` on any failure — never a redirect, since the frontend treats
    3xx as "session expired".

  `home.py` → `C_home` prefix, all routes behind
  `Depends(auth_service.get_current_user)`:
    - `GET C_home/home` → `{"username", "modules": [...], "title", "footer"}`.
      Each module dict is `{"name", "label", "module_icon",
      "module_description"}` (field names match `components/home/module_card.py`)
      — only modules the user has an explicit `user_module_permissions` grant
      for, ordered by `ModuleModel.sort`. `title`/`footer` come from the
      singleton `app_configs` row (`AppConfigRepository.get_config()`),
      falling back to `"SFSIS"`/`""` if that row somehow doesn't exist.
    - `GET C_home/call_generate_totp` → `{"secret": "..."}`, a fresh candidate
      secret (not persisted yet).
    - `POST C_home/call_change_totp` (form: `secret`, `totp`) → verifies the
      code against the candidate secret and, if valid, persists it via
      `UserRepository.update_user_totp_secret`, returning `{"success": "..."}`;
      otherwise `{"error": "..."}`. Always HTTP `200` — this endpoint's caller
      branches on the JSON body, not the status code.
    - `POST C_home/call_change_password` (form: `c`=current, `n`=new,
      `f`=new confirmation) → verifies `n == f`, `c != n`, and `c` against
      the stored bcrypt hash, then persists `hash_password(n)`;
      `{"success": "..."}` or `{"error": "..."}`. Always HTTP `200`, same
      body-not-status-code contract as `call_change_totp`.
    - The `shift` and `token` modals (`pages/modals/shift`,
      `pages/modals/token`) call `C_home/call_shift_id_select`,
      `C_home/call_change_shift`, `C_home/call_change_token` — **none of
      these exist yet**; they'll 404 exactly like `call_change_password`
      did before it was added here. Same fix pattern if/when needed: read
      the modal's `client.get`/`client.post` calls for the exact endpoint
      path and form-field names, then add a matching route to `home.py`.

  `module.py` → no prefix, one dynamic route: `GET C_{module_name}` →
  `{"secure": {"access": bool}}` (matches `ClientData.has_permission()`).
  `access` is `False` — not a 404 — for an unknown module name, so the
  frontend never has to special-case that. Because the path pattern is a
  single segment (`/C_{module_name}`, no further `/`), it can never collide
  with the two-segment `C_login/...` / `C_home/...` routes regardless of
  router registration order.

  `module_admin.py` → `C_ap_module` prefix (all routes behind
  `require_module_access("ap_module")`), a full CRUD screen matching the
  generic `components/table/table.py` (list) / `components/form/form.py`
  (create/edit) frontend contract:
  - `GET C_ap_module/get_detail?table-keyword-filter=&limit=&page=&offset=`
    → paginated module list, each row carrying `db_total_page`/`db_num_rows`.
  - `GET C_ap_module/get?id=<id>` → single module record for the edit form.
  - `POST C_ap_module/submit` (form: `id`, `name`, `label`, `sort`, `icon`,
    `description`, `module_group_id`) → upsert (blank/missing `id` = create);
    `{"message": "..."}` or `{"error": "..."}`. `module_group_id` is optional
    (blank = ungrouped).
  - `POST C_ap_module/delete` (form: `id`) → deletes the module's permission
    grants first, then the module.
  - `GET C_ap_module/call_module_group_id_select` → options for the
    `module_group_id` select field, sourced from `master_module_group`.

  `module_group_admin.py` → `C_master_module_group` prefix (all routes
  behind `require_module_access("master_module_group")`), the same
  list/get/submit/delete shape as `master_location.py` for `module_groups`
  rows (`id`, `name`, `sort`). Deleting a group that still has modules
  pointing at it fails with a friendly `{"error": "..."}` (catches the FK
  `IntegrityError`), same pattern as deleting a location/material with
  transaction history.

  `app_config.py` → `C_master_config` prefix (behind
  `require_module_access("master_config")`) and `mail_config.py` →
  `C_mail_config` prefix (behind `require_module_access("mail_config")`) are
  both **singleton settings screens** — a different shape from every other
  router here: just `GET .../get` (returns the one row, or sensible defaults
  if it doesn't exist yet) and `POST .../submit` (always upserts that one
  row) — no list, no per-record `id`, no delete. `mail_config.py` also
  exposes `GET C_mail_config/call_use_tls_select` (static Yes/No options,
  same pattern as `is_active`/`is_superuser` in `user_admin.py`).

  `user_admin.py` → `C_ap_master_user` prefix (all routes behind
  `require_module_access("ap_master_user")`), same list/get/submit/delete
  shape for users, plus the permission-checklist endpoints:
  - `GET C_ap_master_user/get_detail`, `GET C_ap_master_user/get?id=<id>`
    (never includes the password), `POST C_ap_master_user/submit` (form:
    `id`, `username`, `email`, `password`, `is_active`, `is_superuser` —
    password required to create, optional on update where blank means
    "keep the existing one"; always bcrypt-hashed before storing; rejects
    duplicate username/email), `POST C_ap_master_user/delete`.
  - `GET C_ap_master_user/call_is_active_select` /
    `call_is_superuser_select` → static Yes/No options (the edit/new forms
    render `is_active`/`is_superuser` as `select` fields, and
    `components/form/select.py` always fetches its options from
    `C_{module}/call_{field_name}_select`).
  - `GET C_ap_master_user/get_all_modules` → every module, for the
    permission checklist.
  - `GET C_ap_master_user/get_permissions?id=<user_id>` →
    `{"module_ids": [...]}`.
  - `POST C_ap_master_user/save_permissions` (form: `user_id`, `module_ids`
    [comma-separated ids]) → replaces that user's grants with exactly that
    set via `UserModulePermissionRepository.set_modules_for_user`.
- **Migrations** (`backend/alembic/`, config in `backend/alembic.ini`):
  `env.py` imports `DATABASE_URL` from `core.config` and all `models.*`
  modules so `Base.metadata` is fully populated, then runs online/offline
  migrations against it. Run from `backend/`:
  `alembic revision --autogenerate -m "..."` / `alembic upgrade head`.
  `0004_seed_default_superuser.py` seeds a bootstrap superuser from
  `core.config.ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_TOTP_SECRET` (issue
  #14 — sourced from `.env`, falling back to `admin`/`admin1234#`/empty if
  unset — **change the password after first login** if you kept the
  default; the migration is idempotent, it no-ops if a user with that
  username already exists, and `downgrade()` removes exactly that seeded
  row). Every later migration that grants module access to the seeded
  admin (`0006`, `0008`, `0010`, `0011`, `0014`, `0015`, `0016`, `0018`,
  `0020`) resolves the same `config.ADMIN_USERNAME` rather than a
  hardcoded `"admin"`, so a custom `ADMIN_USERNAME` still gets every
  built-in module grant. **These env vars only take effect on a fresh
  database** — they seed the initial row on first `alembic upgrade head`,
  they don't update an already-seeded admin.
  `0006_seed_default_modules_and_permissions.py` seeds the 7 built-in
  `modules` rows (`ap_module`, `ap_master_user`, `master_location`,
  `master_material`, `stock_in`, `stock_out`, `stock_browse` — name/label/
  icon/description/sort hardcoded in the migration) and grants every one of
  them to the `admin` user from `0004`, so a fresh instance has working home
  screen tiles and admin access out of the box, with no manual `podman exec`
  seeding step required (that used to be how this was done — a real gap:
  a fresh install had an empty `modules` table and no grants at all until
  someone ran that by hand). Also idempotent (matches existing rows by
  `name`/`(user_id, module_id)` before inserting) and reversible.
  `0007_create_suppliers_table.py` creates the `suppliers` table and adds
  `materials.supplier_id` (nullable FK). `0008_seed_master_supplier_module.py`
  seeds the `master_supplier` module row and its `admin` grant, same
  idempotent/reversible pattern as `0006` (kept as a separate migration
  rather than appended to `0006`'s `DEFAULT_MODULES` list, since `0006`
  already shipped/ran against real databases — extending it after the fact
  wouldn't backfill instances that already applied it).
  `0009_create_departments_table.py` creates `departments` and adds
  `users.department_id` + `stock_out_headers.department_id` (both nullable
  FKs, via `op.batch_alter_table` — plain `op.create_foreign_key` after
  `add_column` isn't supported on SQLite, which this repo's migrations are
  verified against before hitting real MariaDB; `batch_alter_table` works on
  both dialects). `0010_seed_master_department_module.py` seeds the
  `master_department` module + `admin` grant, same pattern as `0008`. **Every
  new module needs its own seed migration** (module row + `admin` grant) —
  this is the established convention, not optional; skipping it is exactly
  the gap `0006` was created to fix (see that entry above).
  `0011_seed_usage_report_module.py` seeds the `usage_report` module (no
  schema change — it's read-only, aggregating existing tables), same pattern.
  `0012_create_module_groups_table.py` creates `module_groups`, seeds the
  3 default groups (`Inventory` sort 1, `Master` sort 9, `Application
  Configuration` sort 10), and turns `modules.module_group_id` from a
  loose non-FK integer (legacy PHP parity placeholder, default `0`) into a
  real nullable FK to `module_groups.id` — clearing any existing `0` values
  to `NULL` first, then adding the constraint via `batch_alter_table`
  (SQLite-compatible, matching `0009`'s approach). `downgrade()` reverses
  the FK back to a plain `NOT NULL DEFAULT 0` column before dropping the
  table. `0013_assign_module_groups.py` is a data-only migration that
  assigns every pre-existing module to its group by name (`stock_in`/
  `stock_out`/`stock_browse`/`usage_report` → Inventory; `master_location`/
  `master_material`/`master_department`/`master_supplier` → Master;
  `ap_module`/`ap_master_user` → Application Configuration) — kept separate
  from `0012` so the schema change and the data assignment are each
  independently reviewable/revertable. `0014_seed_master_module_group_module.py`
  seeds the `master_module_group` admin screen's own module row (Application
  Configuration group) + `admin` grant, same pattern as `0008`/`0010`.
  `0015_create_mail_config_table.py` creates the singleton `mail_configs`
  table (no seeded row — there's no sensible default mail server) and seeds
  the `mail_config` module + `admin` grant. `0016_create_app_config_table.py`
  creates the singleton `app_configs` table, seeds its one default row
  (`app_title="SFSIS"`, `footer=""` — so `home.py` behaves identically to
  the old hardcoded values out of the box) and seeds the `master_config`
  module + `admin` grant. `0017_create_categories_table.py` creates the
  `categories` table and adds `materials.category_id` (nullable FK, via
  `op.batch_alter_table` — same SQLite-compatible pattern as `0007`'s
  `suppliers`/`materials.supplier_id`). `0018_seed_master_category_module.py`
  seeds the `master_category` module (assigned to the `Master` module group)
  + `admin` grant, same pattern as `0008`/`0010`.
  `0019_add_supplier_id_to_receiving_headers.py` adds a nullable
  `receiving_headers.supplier_id` FK, same `op.batch_alter_table` pattern —
  no seed migration needed, since `stock_in` is an existing module, not a
  new one. `0020_seed_purchase_report_module.py` seeds the `purchase_report`
  module (assigned to the `Inventory` module group, sort 24 — right after
  `usage_report`'s 23) + `admin` grant, same pattern as `0008`/`0010`/`0018`.
  `0021_remove_supplier_id_from_materials.py` drops `materials.supplier_id`
  (FK + index + column, `op.batch_alter_table`) — the exact reverse of
  `0007`'s original addition; issue #11 removed it once
  `receiving_headers.supplier_id` (`0019`) made per-material supplier
  tracking redundant (a material can be sourced from many suppliers over
  time, so the FK belongs on the receiving header, not the material).
  `downgrade()` re-adds it as nullable, same as it was originally.
- Because `src/` code imports as top-level packages (`from models.base import
  ...`, not `from src.models.base import ...`), `backend/Dockerfile` sets
  `ENV PYTHONPATH=/usr/src/app/src` and copies `alembic.ini` +
  `alembic/` into the image alongside `src/`.
- `backend/Dockerfile`'s `CMD` is `backend/entrypoint.sh` (copied to
  `/usr/local/bin/` — outside `/usr/src/app` so it survives the dev bind
  mount, which otherwise hides anything installed only under `WORKDIR`).
  Each container start, it:
  1. Generates a self-signed TLS cert (`backend/certs/{cert,key}.pem`,
     `CN=localhost`, 10-year expiry via `openssl req -x509`) **only if one
     isn't already there** — since `./backend` is bind-mounted, the cert
     persists on the host across restarts and is only generated once per
     checkout. `backend/certs/` is gitignored (regenerate per environment,
     never commit a private key).
  2. Runs `alembic upgrade head` — so every container start (including
     `podman compose restart` / `restart: always` recovery) applies any
     pending migrations automatically; no manual step needed after pulling
     schema changes. `compose.yml`'s `database`/`backend`/`frontend` services
     each carry a `healthcheck` (`database`: `mariadb-admin ping` with the
     root credentials — the image's own bundled `healthcheck.sh` assumes
     unix-socket auth for `root@localhost`, but this compose file gives root
     a real password, so that script's socket-protocol queries get "Access
     denied" and it never reports healthy; `backend`/`frontend`: a
     `python3 -c "urllib.request.urlopen(...)"` hit against their own plain
     HTTP root, since neither image has `curl` installed but both have
     Python's stdlib), and `backend`/`frontend` each `depends_on` the
     previous service with `condition: service_healthy` — so `backend`
     doesn't even start until `database` is actually accepting connections,
     and `frontend` doesn't start until `backend` is actually serving. This
     removed the previous crash-loop-on-first-boot (backend starting before
     MariaDB was ready, `alembic upgrade head` failing with connection
     refused, `restart: always` retrying until the DB caught up) — verified
     via a fresh `podman compose up -d` showing `mariadb Healthy` ->
     `backend Starting` -> `backend Healthy` -> `frontend Starting` in strict
     order, no failed-connection tracebacks in the backend log at all.
  3. Starts **two** Uvicorn processes in the background and `wait -n`s on
     either: plain HTTP on `UVICORN_PORT` (5000) and HTTPS (using the
     generated cert) on `UVICORN_PORT_SSL` (5443) — both env vars come from
     `compose.yml`, which also exposes both ports. The frontend's
     `HttpClient(verify=False)` only skips certificate *validation*, so a
     `https://` server address still needs a real TLS listener behind it —
     point the Server Config page at `https://<host>:5443` (or
     `http://<host>:5000` if you don't need TLS).
- **Bootstrap**: `alembic upgrade head` seeds the env-configurable admin
  (`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_TOTP_SECRET`, default
  `admin`/`admin1234#`/empty — see `0004` above) as an active superuser
  *and* the built-in modules + grants every one to that account (`0006` for
  the original 7, `0008` for `master_supplier`) — a fresh instance has
  working home screen tiles and full admin access
  with zero manual steps. `require_module_access`'s superuser bypass still
  matters for any *new* module you add by hand later (e.g. via
  `/modules/ap_module/new`) — that account can use the module admin/
  permission screens to create and grant it to itself or others before it
  has any grant of its own, same as it could before `0006`/`0008` existed
  for the starter set.
- Full login → home (real granted modules) → TOTP-enroll → re-login-with-
  TOTP → permission-check → module CRUD → user CRUD → grant/revoke →
  cascade-delete flow is verified end-to-end with `TestClient` smoke tests.
  The full bootstrap (`alembic upgrade head` from a genuinely empty
  database → login → home tiles) has also been verified against a real,
  disposable MariaDB + backend container pair (not just SQLite).

## Inventory Domain (stock in/out, moving-average costing)

Master data: `locations` (`LocationModel`: `code`, `name`), `suppliers`
(`SupplierModel`: `code`, `name`), `departments` (`DepartmentModel`: `code`,
`name` — who consumes inventory, for usage reporting), `categories`
(`CategoryModel`: `code`, `name`, `description` — classifies materials into
logical groups, e.g. Raw Materials/Packaging/Tools), `units_of_material`
(`UnitOfMaterialModel`: `code`, `name` — e.g. `PCS`/`Pieces`,
`KG`/`Kilogram`; issue #16), and `materials` (`MaterialModel`:
`material_code`, `material_name`, `category_id` — nullable FK to
`categories.id`, since materials created before the category link has no
category to point to, `unit_id` — **non-nullable** FK to
`units_of_material.id`, exactly one unit per material, no exceptions),
managed via the `master_location`/`master_supplier`/`master_department`/
`master_category`/`master_unit_of_material`/`master_material` admin modules
(plain CRUD, same shape as `ap_module`) — **except `master_unit_of_material`,
which has no delete endpoint/button at all**: a unit of material can never
be removed once created, since every material links to exactly one and
deleting the unit out from under an in-use material would break that link
(same integrity reasoning as materials themselves not being deletable, see
issue #17). `master_material`'s new/edit form renders `category_id` and
`unit_id` as `select` fields (`GET C_master_material/call_category_id_select`
/ `call_unit_id_select`, `unit_id` required — submit rejects a blank one with
`{"error": "Unit of Material is required"}`), and its list/get responses
include denormalized `category_name`/`unit_id`/`unit_code`/`unit_name` for
display — the same pattern as `stock_in`/`stock_out`'s `material_id`/
`location_id` selects, just on master data instead of a transactional item.
Migration `0022_create_units_of_material_table.py` seeds one default unit
(`PCS`/`Pieces`) and backfills every pre-existing material onto it before
making `materials.unit_id` `NOT NULL`, so the column can be mandatory from
day one without breaking existing rows; `0023_seed_master_unit_of_material_module.py`
seeds the module + admin grant, same pattern as `0018`.
`0024_seed_default_units_of_material.py` (issue #18) then seeds a full
catalog of 22 more common units (`L`/Litres, `G`/Grams, `KG`/Kilograms,
`LB`/Pounds, `OZ`/Ounces, `GAL`/Gallons, `ML`/Millilitres, `CTN`/Carton,
`PACK`/Pack, `PLT`/Pallet, `ROLL`/Roll, `BOX`/Boxes, `DZ`/Dozens,
`BTL`/Bottles, `CASE`/Cases, `M`/Meters, `CM`/Centimeters, `FT`/Feet,
`IN`/Inches, `UNIT`/Units, `SET`/Sets, `PAIR`/Pairs) so a fresh setup has a
ready-to-use catalog instead of needing every unit added by hand —
match-by-code idempotent (skips `PCS`, already owned by `0022`) and
reversible, but its `downgrade()` skips (rather than raising on) any unit a
material has since been created against, using a per-row `SAVEPOINT`
(`bind.begin_nested()`) so one blocked delete doesn't abort the whole
migration's transaction — same friendly-skip precedent as every other
delete-guard in this codebase. **`materials` does
not carry its own `supplier_id`** — a material may be sourced from many
different suppliers over time, so supplier tracking instead lives at the
receiving-header level (`receiving_headers.supplier_id` below); an earlier
`materials.supplier_id` FK (added alongside `category_id`) was removed in
issue #11 once `receiving_headers.supplier_id` (#7) made it redundant —
see migration `0021_remove_supplier_id_from_materials.py`. `UserModel` also has
an optional `department_id` (see Backend Architecture above) so a user can
represent one department's requester, separately from stock-out headers
each declaring their own department.

**Materials cannot be deleted, only deactivated** (issue #17):
`materials.is_active` (non-nullable `Boolean`, default `True`, added by
migration `0025_add_is_active_to_materials.py` — single-step
`server_default=sa.true()` add-column, no backfill dance needed since
booleans always have a sensible default, unlike `unit_id`'s FK) replaces
`master_material`'s delete button/endpoint entirely, same "no delete"
precedent as `master_unit_of_material` (#16) — deleting a material can
break referential integrity with its receiving/stock/issue history, so
`master_material.py` router now has **no `/delete` route at all**.
`master_material`'s new/edit form gains an `is_active` `select` field
(`call_is_active_select`, same static Yes/No options as
`ap_master_user`'s `is_active`/`is_superuser`), and its list shows the
status. An inactive material is otherwise fully functional everywhere
else — stock browse, stock out, usage report, and purchase report all
continue to show its historical/on-hand data unchanged — **except**
`POST C_stock_in/submit_item`'s create path (not its update path, since
editing an already-received item shouldn't retroactively re-validate a
material that was receivable at the time), which rejects it with
`{"error": "Cannot receive: material is inactive"}`.

Transactional tables, all in `backend/src/models/`:
- `receiving_headers` / `receiving_items` (stock in): a header is
  `date` + `description` + `supplier_id` (nullable FK to `suppliers.id` —
  nullable since a header can predate the supplier link, or the shipment's
  supplier may simply be unknown; unlike `stock_out_headers.department_id`,
  this is never required on submit); each item is one `material_id` +
  `location_id` + `price_buy` + `qty_plan` + `qty_received` + `remarks`.
  **`qty_plan`** (issue #33) is reserved for a future plan/confirm split,
  same precedent as `stock_movement_items.plan_qty` (#31) — always equal to
  `qty_received` on create, untouched by `update_receiving_item` (editing
  the actual received qty doesn't retroactively rewrite what was
  originally planned), no separate UI input for it yet.
  **`location_id` lives on the item**, not the header — inferred, not explicitly specified,
  since the `stocks` table needs a location per lot and nothing else
  supplies one. `receiving_repository.py::list_headers` outer-joins
  `SupplierModel` so its `apply_keyword_filter` also matches the linked
  supplier's `code`/`name`, not just the header's own `description` — the
  one list-endpoint in this codebase whose keyword search reaches across a
  join rather than staying on the base table's own columns (same join
  technique as `stock_repository.py::list_stock_summary`'s aggregate query,
  just without the `group_by`/`having`).
- `stocks`: one lot row per receiving item (`receiving_item_id` FK, plus
  denormalized `material_id`/`location_id`/`qty`), unique on
  `(receiving_item_id, material_id, location_id)`. Since one receiving item
  always has exactly one material/location, this is effectively 1:1 with its
  receiving item — a lot, not an aggregate.
- `inventory_values`: one row per material (`material_id` unique),
  `qty` (total on hand across all locations) + `average_price` (MAP).
- `stock_out_headers` / `stock_out_items` (stock out): header is `date` +
  `description` + `department_id` (nullable FK to `departments.id` — nullable
  at the schema level only for headers created before this column existed;
  `routers/stock_out.py::submit` rejects a blank `department_id` on every
  new create/update, so every transaction going forward is attributed to
  exactly one department, which is what makes a "consumption by department"
  usage report possible); each item is `material_id` + `location_id` +
  `qty_plan` + `qty_out` + the **captured** `price` (that material's MAP at
  the moment of issue) + `total_value` (`qty_out * price`) + `remarks`.
  **`qty_plan`** (issue #33) is the same reserved-for-later-use column as
  `receiving_items.qty_plan` above — always equal to `qty_out` on create.
  `stock_out_repository.py::list_headers` outer-joins `DepartmentModel`
  (2026-07-17) so `department_name` is filterable/sortable like
  `receiving_repository.py::list_headers`'s own `SupplierModel` join —
  added after issue #27's sort rollout left `department_name` as the one
  header column with no sort icon at all (unlike `stock_in`'s equivalent
  `supplier_name`, which already had this join from #7). Deliberately
  **not** also added to the keyword search across `[Description]` (unlike
  receiving's supplier join, which does extend keyword search) — narrowly
  scoped to closing the sort/filter gap that was actually reported, not a
  full parity pass with `stock_in`'s header search behavior.
- `stock_movement_headers` / `stock_movement_items` (stock movement — issue
  #31, transferring on-hand stock between two locations without it counting
  as a stock-out or stock-in): header is `date` + `description` +
  **`created_by`/`updated_by`** (nullable FKs to `users.id`, stamped from
  the authenticated session user at write time — the first header table in
  this codebase to track who performed the action; every other header
  table here has neither field). Each item is `material_id` +
  `origin_location_id` + `destination_location_id` (both FKs to
  `locations.id` — must differ, enforced by
  `inventory_service.SameLocationMovementError`) + `plan_qty` +
  `movement_qty` + `remarks` + its own `created_by`/`updated_by`.
  **`plan_qty` is reserved for a future two-step plan/confirm workflow** —
  this first rollout is direct/immediate movement only, so `plan_qty` is
  always set equal to `movement_qty` on create with no separate UI input
  for it; the item sub-table's "Remaining" column (`plan_qty -
  movement_qty`, computed by the router, not stored) is always `0` today
  but will become meaningful once a plan/confirm split is actually built.
  `stock_movement_repository.py::list_items_by_header` outer-joins
  `LocationModel` **twice** via `sqlalchemy.orm.aliased` (once per
  direction) so both `origin_location_code`/`name` and
  `destination_location_code`/`name` are independently filterable/sortable
  — the first two-location join in this codebase (every other item table
  has exactly one location per row).
  **Schema knock-on effect**: a stock movement's destination lot needs a
  `stocks` row, but `stocks.receiving_item_id` was `NOT NULL` (every prior
  lot came from a receiving item) — migration `0026` makes it nullable and
  adds a new nullable `stocks.stock_movement_item_id` FK, so a lot is now
  sourced from **either** a `receiving_item` **or** a `stock_movement_item`
  (never both, `receiving_item_id IS NULL` for a movement-created lot).
  `uq_stock_lot`'s existing unique constraint on
  `(receiving_item_id, material_id, location_id)` still works unmodified —
  both SQLite and MySQL/MariaDB treat `NULL` as distinct from every other
  `NULL` in a unique index, so multiple movement-created lots at the same
  material/location (each with `receiving_item_id=NULL`) don't collide.
  **Home tile ordering**: `0027` originally seeded `stock_movement` at
  `sort=25`, after `purchase_report`; a follow-up data-only migration,
  `0028_reorder_stock_movement_module.py`, moved it to `sort=21` — between
  `stock_in` (20) and `stock_out` (22) — per explicit user request,
  bumping `stock_out`/`stock_browse`/`usage_report`/`purchase_report` up by
  one each. Same "reassign `modules.sort` by name" pattern as
  `0013_assign_module_groups.py`; safe since `modules.sort` has no unique
  constraint, just a plain index.

All business logic lives in `backend/src/services/inventory_service.py`,
which — unlike every other service/repository in this codebase — manages its
own `SessionLocal()` transaction directly instead of going through
single-table repository methods, because one "receive" or "issue" call must
touch `receiving_items`/`stocks`/`inventory_values` (or `stock_out_items`,
or `stock_movement_items`) atomically. Repositories for these tables
(`receiving_repository.py`, `stock_repository.py`, `stock_out_repository.py`,
`stock_movement_repository.py`) are read-only for the transactional parts
(header CRUD is plain repository methods same as everywhere else; only item
writes route through the service).

- **Moving average price (MAP)**: receiving `new_qty` at `new_price` when the
  material already has `qty`/`average_price` on hand recomputes as
  `(qty*average_price + new_qty*new_price) / (qty+new_qty)`. Issuing stock
  decreases `qty` but never touches `average_price` (standard moving-average
  costing — cost only moves on receipt).
- **Editing a receiving item** (qty/price/remarks only — material/location
  are fixed once created, by design, to avoid a much harder "item moved to a
  different material" MAP-reconciliation case): reverses the item's old
  (qty, price) contribution from the running total, then applies the new
  one. This is exact *as long as no stock-out for that material happened
  between the original receipt and the edit* — the service doesn't replay
  full transaction history, so editing an old receipt with intervening
  issues only approximately corrects the average. Documented simplification
  for a "simple" inventory system, not a bug.
- **Stock out deduction is user-picks-material, then a qty per location,
  each deducted FIFO within that location**: the stock-out item form
  (`stock_out/item_new.py`) has the user pick one material, which loads a
  table of every location currently holding stock of it
  (`GET C_stock_out/get_stock_by_material`) with an editable "Qty Issue"
  input per row — rows left blank/zero are simply not submitted, so issuing
  from one location or several in a single screen both work. On submit
  (`POST C_stock_out/submit_items`), the router validates every requested
  qty against that location's current stock up front (rejecting the whole
  submission, before mutating anything, if any one location is short), then
  calls `inventory_service.create_stock_out_item` once per location with a
  qty > 0 — same oldest-lot-first deduction as before (`StockModel` rows
  ordered by `id` ascending, a proxy for receiving order) within each
  location, `InsufficientStockError` from the service itself only a
  safety net for a stock change racing the up-front check.
- **Stock out items are immutable** (create-only, no edit/delete) — cleanly
  reversing a FIFO deduction that may have spanned multiple lots would need
  a lot-allocation ledger, which is out of scope; to "undo" an issue today
  you'd receive it back in.
- **Stock movement (transfer between locations) is FIFO-deduct-at-origin +
  new-lot-at-destination, and deliberately never touches `inventory_values`**
  (issue #31): `inventory_service.create_stock_movement_item(...)` deducts
  `movement_qty` FIFO from the material's lots at `origin_location_id` —
  identical deduction logic to `create_stock_out_item` (same oldest-lot-first
  loop, same `InsufficientStockError` safety net for a stock change racing
  an up-front check) — then creates a brand-new lot at
  `destination_location_id` for that same qty, same "new lot" shape
  `create_receiving_item` produces except `receiving_item_id=None` (see the
  `stocks` schema note above). It does **not** call
  `_apply_receiving_delta`/touch `InventoryValueModel.qty`/`average_price`
  at all — a transfer between two of a material's own locations changes
  neither its total on-hand quantity nor its cost, only its per-location
  distribution, so there is nothing for the MAP calculation to do here.
  Rejects `origin_location_id == destination_location_id`
  (`SameLocationMovementError`) before touching anything. Same
  user-picks-material-then-a-qty-per-origin-location UX as stock out's item
  form — `stock_movement/item_new.py` additionally has a single
  **Destination Location** dropdown (fed by
  `C_stock_movement/call_location_id_select`) that applies to every row
  submitted from that screen, since one `stock_movement_item` needs exactly
  one destination but the origin-location table can span several rows;
  `POST C_stock_movement/submit_items` validates every requested qty
  against its origin location's current stock up front (same
  reject-the-whole-submission-before-mutating-anything pattern as
  `stock_out.py::submit_items`) and separately rejects any origin row that
  matches the chosen destination. **No multi-material bulk endpoint** like
  `stock_out`'s `submit_bulk_items` (issue #25) — the per-origin-location
  table on `item_new` is a plain `is_inside_form=True` `Table` with
  editable `movement_qty`/`remarks` columns, so it already gets a generic
  CSV/XLSX upload menu for free (`components/table/menu.py::TableMenu`, see
  "Table export/upload convention" below) once a material and destination
  are already picked — no bespoke bulk-upload backend needed for that flow,
  matching the issue's own scoped request (`Location | Qty Movement |
  Remarks` columns only, not `Material`/`Location` like stock_out's
  multi-material bulk).
  **Stock movement items are immutable** (create-only, no edit/delete),
  same rationale as stock out items.
  Verified via SQLite/`TestClient` against the real FastAPI routes: MAP/qty
  totals correctly unaffected by a movement, FIFO deduction and lot
  creation correct, same-location and insufficient-stock submissions
  both correctly rejected with no partial mutation. Not yet confirmed in
  a live browser. Full test detail in CHANGE_HISTORY.md (2026-07-17).
- Deleting a location/material that has any receiving/stock/issue history
  fails with a friendly `{"error": "Cannot delete: ..."}` (catches the
  FK `IntegrityError`) rather than a raw 500 or a silent cascade.

Routers (all under `backend/src/routers/`, each gated by
`require_module_access("<module_name>")`):
- `master_location.py` / `master_supplier.py` / `master_department.py` /
  `master_material.py`: standard list/get/submit/delete (`master_material.py`
  additionally exposes `call_supplier_id_select`).
- `stock_browse.py`: read-only, `GET C_stock_browse/get_detail` — current
  on-hand qty per (material, location) with qty > 0, joined with that
  material's MAP for `average_price`/`value`. Not lot-level; aggregates
  across whichever `stocks` rows share a material+location.
- `usage_report.py`: read-only, `GET C_usage_report/get_detail` — total
  qty issued + total cost per (department, material), summed across every
  `stock_out_items` row joined back through its header's `department_id`.
  Backed by `repository/usage_report_repository.py::UsageReportRepository`
  (a dedicated cross-table aggregate repository, same pattern as
  `stock_repository.py` for `stock_browse` — not bolted onto
  `stock_out_repository.py`, which owns header CRUD + item reads, not
  reporting). `total_cost` sums each item's already-captured `total_value`
  (the MAP at time of issue), so the report reflects historical cost, not
  today's MAP. Also accepts `start_date-filter`/`end_date-filter` (inclusive,
  independently optional — reusing #8's `apply_field_filters` convention on
  `stock_out_headers.date`, issue #9), honored by both `get_detail` and its
  `export_detail` twin so a filtered report exports exactly what's on
  screen. No supplier/material scoping filter here (out of scope for this
  report, unlike `purchase_report`) — date range only.
- `purchase_report.py`: read-only, two independent aggregate tables —
  `GET C_purchase_report/get_by_supplier` (total qty received + total
  purchase value per supplier) and `get_by_material` (same, per material) —
  both summing `receiving_items.qty_received * price_buy` (today's captured
  cost at time of receipt, same "reflects the transaction" semantics as
  `usage_report`'s `total_cost`) across every item joined back through its
  header. Each inner-joins its own grouping dimension (`SupplierModel` /
  `MaterialModel`), so a receiving header with no `supplier_id` recorded is
  simply excluded from the by-supplier breakdown. Backed by
  `repository/purchase_report_repository.py::PurchaseReportRepository`
  (same dedicated-aggregate-repository pattern as `stock_repository.py`/
  `usage_report_repository.py`). Both endpoints accept
  `start_date-filter`/`end_date-filter` (inclusive date range on the
  receiving header's `date`, each bound independently optional) via
  `core/table_query.py::apply_field_filters` (see "Named structured
  filters" above); `get_by_supplier` additionally accepts
  `supplier_id-filter` and `get_by_material` accepts `material_id-filter`,
  each narrowing that table to one row (blank/absent = the full grouped
  breakdown) — deliberately **not** cross-applied between the two tables,
  so picking one supplier on the by-supplier table doesn't also scope the
  by-material table. `call_supplier_id_select`/`call_material_id_select`
  each prepend an explicit `{"value": "", "label": "All Suppliers"/"All
  Materials"}` option for the frontend's filter dropdowns.
- `stock_in.py` / `stock_out.py`: header list/get/submit (same shape as
  master data — `stock_out.py`'s header additionally requires a non-blank
  `department_id` on submit, and its list/get responses include a
  denormalized `department_name`; `stock_in.py`'s header instead accepts an
  *optional* `supplier_id`, denormalized as `supplier_name`, and its
  keyword search also matches the linked supplier), plus a **separate item
  sub-flow** —
  `get_items` (list by header) for both. `stock_in.py` additionally has
  `submit_item` (create/update) and `get_item` (single, for the edit form),
  because a receiving item is edited on its own screen, not as part of one
  combined header+items submission (see Frontend Architecture below for
  why). `stock_out.py` instead has `get_stock_by_material` (current qty per
  location for one material, qty > 0 only) and `submit_items` (form:
  `stock_out_header_id`, `material_id`, repeated `location_id`/`qty_out`/
  `remarks` — one triplet per location row with a qty > 0; creates one
  `stock_out_item` per location) — issuing has no per-item edit screen, and
  one submission can cover several locations at once (see the FIFO note
  above). Both expose `call_material_id_select`; `stock_in.py` also exposes
  `call_location_id_select` for its item form's location dropdown (unused
  by `stock_out.py`'s item form now, kept for parity/possible future use)
  and `call_supplier_id_select` for its header form; `stock_out.py`
  additionally exposes `call_department_id_select` for its header form.
- `stock_movement.py` (issue #31): same header list/get/submit/
  `submit_bulk`/`get_items` shape as `stock_in.py`/`stock_out.py`, except
  `submit` stamps `created_by`/`updated_by` from the current session user
  (`user.id`, resolved via the `_require_access` dependency every router
  already depends on — no separate `get_current_user` call needed) rather
  than accepting them as form fields. Reuses `get_stock_by_material`
  (backed by `stock_repository.py`, the exact same repository method
  `stock_out.py` calls) rather than duplicating it. `submit_items` (form:
  `stock_movement_header_id`, `material_id`, `destination_location_id`,
  repeated `origin_location_id`/`movement_qty`/`remarks`) is the only
  item-write endpoint — no `submit_item`/`get_item` (items are create-only,
  like `stock_out`, not editable like `stock_in`) and no
  `submit_bulk_items` multi-material bulk endpoint (see the movement
  business-logic note above for why that's not needed here). Exposes
  `call_material_id_select` and `call_location_id_select` (the latter feeds
  the item form's single destination dropdown, not a per-item location like
  `stock_in.py`'s use of the same endpoint name).

**Unit of material (UOM) display convention** (issue #16): every material
links to exactly one unit of material (`materials.unit_id`, non-nullable —
see the Inventory Domain section above), and every table/list that shows a
material *quantity* displays that material's unit alongside the qty column:
`stock_browse` (`qty`/`unit_name`), `stock_in`'s item sub-table
(`qty_received`/`unit_name`), `stock_out`'s item sub-table
(`qty_out`/`unit_name`) and its `item_new.py` per-location "Qty Stock"/"Qty
Issue" table (`unit_name` column, no backend serialization needed there
since `stock_repository.py::list_stock_by_material` already returns it),
`usage_report` (`total_qty_out`/`unit_name`), and `purchase_report`'s
**by-material** table only (`total_qty`/`unit_name`) — deliberately **not**
`purchase_report`'s by-supplier table, since that one aggregates `total_qty`
across many different materials that may carry different units, so a single
unit column there would be misleading. Each qty-bearing repository/router
joins `UnitOfMaterialModel` (via `MaterialModel.unit_id`) and adds
`unit_code`/`unit_name` to its row dict; `master_material`'s own list/get
responses do the same for its own `unit_id` field.

**Frontend module structure** (`frontend/src/pages/modules/`): `master_location`,
`master_supplier`, `master_department`, `master_category`, `master_material`,
`master_unit_of_material`, and `master_module_group` are plain
`{index,new,edit}.py` CRUD, identical in shape to `ap_module`
(`master_category`'s `new`/`edit` additionally carry a plain `description`
input field; `master_material`'s `new`/`edit` carry `category_id`,
`unit_id`, and `is_active` select fields, `index` read-only
`category_name`/`unit_name`/`is_active` labels; **both**
`master_unit_of_material`'s and `master_material`'s `edit.py` have **no
delete button** — see the Inventory Domain section above for why).
`ap_master_user`'s `new`/`edit` similarly carry a `department_id` select
field (optional — blank is valid) and `index` a read-only `department_name`
label; `stock_out`'s `new`/`edit` carry a required `department_id` select on
the header form and `index` a read-only `department_name` label. `ap_module`
itself also carries a `module_group_id` select on `new`/`edit` (optional —
blank is valid) and a read-only `module_group_name` label on `index`.
`usage_report` is `index.py` only (no `new`/`edit` — and deliberately no
field marked `"key": True` in its `Table` config, since `TableRows.py`
unconditionally wires a `"key"` field to row-tap-navigates-to-`edit/<id>`,
and it has no edit screen to navigate to). `stock_browse` used to be the
same shape, until issue #29 (2026-07-17) added a genuine (non-"edit") row
click target — see "Stock-by-material drill-down" below.
`purchase_report`
is the same shape, but with **two** `Table`s on one `index.py` (`by_supplier`/
`by_material`, each defaulting its endpoint to `C_purchase_report/get_by_x`
purely from its `name=` — no `endpoint=` override needed) plus two standalone
`components/form/date.py::DateForm` instances (reused outside a `Form`
context, same as an editable table cell does) for the shared date range and
two hand-built `ft.Dropdown`s (populated from `call_supplier_id_select`/
`call_material_id_select`, same pattern as `stock_out/item_new.py`'s material
picker) for each table's own scoping filter. `DateForm` has no `on_change`
hook, so filters apply on demand via a toolbar "Apply Filters" button
(`ModuleToolbar.add_button`) rather than live per-keystroke/per-select —
reads the current date-form values + both dropdowns, sets each table's
`custom_param` to the matching `{field}-filter` keys, resets `page_number`
to 1, and calls `get_data()` on both. `usage_report/index.py` (issue #9)
gained the same two standalone `DateForm`s + "Apply Filters" toolbar
button pattern, minus the dropdowns/second table — its single `Table`'s
`custom_param` gets just `start_date-filter`/`end_date-filter`.

**Stock-by-material drill-down** (issue #29, 2026-07-17): clicking a row in
`stock_browse/index` now navigates to
`/modules/stock_browse/stock_by_material/<material_id>` — the first
non-"edit" row-click target this module has ever had, enabled by marking
the (already-hidden) `material_id` field `"key": True` and passing
`Table(..., edit_screen="stock_by_material")`, same mechanism `stock_in`/
`stock_out`'s item tables already use for a non-`"edit"` target.
`pages/modules/stock_browse/stock_by_material.py` is a new,
`record_id`-accepting `ModulePage` (matches `master_location/edit.py`'s
`def __init__(self, page, module, screen=str, record_id=None)` shape) that
is otherwise read-only, same as `stock_browse`/`usage_report` themselves —
no add/edit/delete. It does two things a plain sub-table screen doesn't:
- **Heading fetched via a small dedicated GET**
  (`C_stock_browse/get_material?material_id=<id>` → `{"material_code",
  "material_name"}`) before `self.table` is even constructed, since a
  material has no edit screen of its own for this page to inherit context
  from the way `stock_in`/`stock_out`'s item sub-tables inherit their
  header's own already-fetched data — same "a small extra GET up front"
  precedent `stock_in/item_edit.py` already established for learning
  context the route's own id doesn't carry.
- **Totals footer** (`Total Qty` / `MAP` / `Total Value`) — the first of
  its kind in this app; no existing `Table` has a totals row. Deliberately
  kept screen-level (a plain `ft.Text` built from `self.table.data` right
  after constructing `self.table`, since `Table.__init__` already runs
  `get_data()` synchronously when not `is_inside_form`) rather than adding
  a generic footer feature to `components/table/table.py` - nothing else
  needs one yet, and a screen-level summary is a few lines against a
  meaningful blast-radius increase for the shared component. `average_price`
  (the material's single MAP, constant across every returned row) is read
  straight off any one row rather than recomputed; `total_value` is the
  simple sum of each row's own already-correct `value`.
  **Numeric fields must be converted before arithmetic, not just before
  display**: every numeric value arrives over the wire as a JSON string
  (SQLAlchemy `Decimal` columns), which cell *display* formatting already
  tolerates but raw Python arithmetic does not — a `_to_number()` helper
  (`float(value)`, `0.0` fallback) is applied before summing. Finding this
  also surfaced a real bug in `utils/module_loader.py::ModuleLoader.build()`:
  it used to detect "this `ModulePage` doesn't accept `record_id`" via a
  bare `except TypeError`, which also silently caught (and masked) a real
  `TypeError` raised from inside a constructor's own body, causing a
  confusing retry-without-`record_id` two network calls removed from the
  actual bug. Fixed with a real signature check
  (`"record_id" in inspect.signature(PageClass).parameters`) instead of
  exception-driven dispatch — an internal constructor `TypeError` now
  correctly propagates to a visible `ErrorPage`. Full investigation in
  CHANGE_HISTORY.md (2026-07-17).

Backend: `stock_repository.py::list_stock_by_material(material_id,
sort_fields=None)` (pre-existing, previously only feeding `stock_out`'s
item form's per-location qty table) gained the same `InventoryValueModel`
outer-join `list_stock_summary` already uses, so `average_price`/`value`
are now real columns on every row here too — `stock_out`'s existing
consumer is unaffected, it never reads those two keys. Also gained
`sort_fields`/`apply_sort` support (previously `.order_by(LocationModel.code)`
unconditionally) — backward compatible, since the parameter defaults to
`None` and `stock_out`'s call site never passes it.
`routers/stock_browse.py` gained `get_stock_by_material`
(`request: Request` + `parse_sort_fields`, mirroring every other sortable
list endpoint), `export_stock_by_material` (same "every list gets an
export twin" convention as everywhere else in this app), and `get_material`.
Verified via SQLite and `TestClient` against the real FastAPI routes.

**Stock-by-location drill-down** (issue #40, 2026-07-20): the mirror image
of the stock-by-material drill-down above, scoped the opposite way —
clicking the Location Code/Location column on `stock_browse/index` now
navigates to `/modules/stock_browse/stock_by_location/<location_id>`,
listing every material currently held at that one location (Material Code |
Material Name | Qty | Unit | Avg Price | Value). Needed a genuinely new
`Table`/`TableRows` capability first: `stock_browse/index`'s row already had
one row-wide click target (`material_id` marked `"key": True` → 
`stock_by_material`), and the existing mechanism
(`TableRows.load()`'s single `key_field`/`edit_screen` pair, wired onto
every non-editable `DataCell` in a row uniformly) has no way to make a
*different* cell in the *same* row navigate somewhere else. Added a
field-level override: any field can set `"link_key_field"` (the name of a
hidden field on that same row holding the id to navigate with) and
optionally `"link_screen"` (defaults to the table's own `edit_screen` if
omitted) — `TableRows.load()` now computes a per-cell tap handler (falling
back to the row's default `on_tap_handler` when a field has no override),
so `location_code`/`location_name` link to a new hidden `location_id` field
+ `stock_by_location`. **Same-day follow-up, requested directly by the
user**: `material_code`/`material_name` were switched from the old row-wide
`"key": True` + `Table(edit_screen="stock_by_material")` mechanism onto the
same `link_key_field`/`link_screen` override (`"link_key_field":
"material_id", "link_screen": "stock_by_material"`) instead of leaving them
on the original mechanism — "edit_screen" was always a slightly misleading
name for a target that was never actually an edit screen here, and there's
no reason for the same table to drive two different-looking navigations
through two different mechanisms once the more general one exists.
`stock_browse/index` now has no `"key": True` field and no `edit_screen`
override at all - every clickable column (`material_code`/`material_name`,
`location_code`/`location_name`) goes through `link_key_field`/
`link_screen` uniformly, and every other column (`qty`, `unit_name`, etc.)
has no navigation.
`pages/modules/stock_browse/stock_by_location.py` is the same shape as
`stock_by_material.py` (a `record_id`-accepting, read-only `ModulePage`,
heading fetched via a small dedicated GET — `get_location` — before the
table is constructed), with one deliberate footer difference: unlike
`stock_by_material`'s footer, which shows a single `MAP` figure (constant
across every row — one material's own average price), this page's footer
shows only `Total Qty`/`Total Value` — average price genuinely *varies*
per row here (each material at a location carries its own MAP), so there is
no single number to show instead of falsely picking one row's value.
Backend: `stock_repository.py::list_stock_by_location(location_id,
sort_fields=None)` mirrors `list_stock_by_material()` (same
`InventoryValueModel` outer-join technique, same qty > 0 filter), and
`routers/stock_browse.py` gained `get_stock_by_location`/
`export_stock_by_location`/`get_location`, same shape as their
by-material equivalents. Verified live in the containerized web app.

`master_config` and `mail_config` are a **different, simpler shape**: a
**singleton settings screen**, not list+CRUD. Each is just one
`index.py` that builds a `Form` directly (not a `Table`) against the
module's `get`/`submit` endpoints, with a submit button and no add/list/
delete — there's exactly one row server-side, so there's no per-record
navigation to support. `index.py` passes `custom_param={}` to `Form(...)`
so it doesn't send a meaningless `id` query param when fetching the
current settings. `mail_config`'s `smtp_password` field sets `"password":
True` — this is the only user of `components/form/input.py`'s optional
password-masking support (`password`/`can_reveal_password`, defaulting to
off, added specifically for this field).

**Extra top padding on these two screens only** (issue #49, 2026-07-27):
`body()` on both `master_config/index.py` and `mail_config/index.py` wraps
`self.form.build()` in an `ft.Container(padding=ft.Padding(top=20, left=0,
right=0, bottom=0), expand=True)` instead of returning the form directly.
Traced first, before changing anything: `Form.build()`'s own `padding`
argument (default 20) is dead code for vertical spacing everywhere in this
codebase — it reassigns `self.padding_row` after `build_elements()` has
already run, so it never affects the already-built row `Container`s, whose
`top`/`bottom` are hardcoded to `0` regardless (only left/right ever read
`padding_row`) — and no caller anywhere passes it explicitly either way.
`ModuleView.build()`'s own `padding` default (`0`) is likewise identical
for every screen shape (Table `index.py`, Form `new.py`/`edit.py`, and
these two singleton Form `index.py` screens). So the "singleton screens
look more cramped than new/edit ones" report wasn't backed by any actual
padding difference in the code at all — confirmed by live comparison
against `ap_module/edit` (a regular Form screen), which sits exactly as
flush against the toolbar as `master_config`/`mail_config` did before this
fix. Since no shared component distinguishes these two screens from
ordinary new/edit Form screens, a per-file `body()` wrap was the only way
to add spacing here without also affecting every other Form screen (or
Table screens, via `ModuleView.build()`'s shared default). Verified live in
the browser: both screens now show a visible gap below the toolbar before
their first field, `ap_module/edit` (new/edit Form) is unchanged, and no
Table screen is affected.

`stock_in`/`stock_out` needed a **header/item master-detail pattern that
doesn't exist elsewhere in this codebase**. A road not taken, and why:
`components/form/table.py` / `list.py` (the `Form` component's `"table"`/
`"list"` field types) look like the obvious fit, but they serialize their
rows as indexed fields (`items[0]`, `items[1]`, ...) submitted together
with the parent form in **one** POST — the spec here is "click + to add
one item via its own form," a separate transaction per item, not a bulk
combined save.

`stock_movement` (issue #31) reuses this exact pattern as its third
consumer, closest in shape to `stock_out` (create-only items, own delete
protection reasoning) — `stock_movement/{index,new,edit,item_table,item_new}.py`
mirror `stock_out/{index,new,edit,item_table,item_new}.py` file-for-file,
differing only in field lists (no `department_id`; the item form's table
carries an extra **Destination Location** dropdown alongside the material
picker, since a movement item needs both an origin — from the per-location
stock table, same as `stock_out` — and one destination for the whole
screen).

The *item sub-list itself*, though, **is** built on the shared
`components/table/table.py` (`stock_in/item_table.py`, `stock_out/item_table.py`,
`stock_movement/item_table.py`
— thin wrapper classes, each building a `Table` with the header's own
`get_items` endpoint and `custom_param={"header_id": ...}` to scope every
request to that one header) — same paginated/lazy-loaded/searchable
list contract as every other list screen in this codebase
(`table-keyword-filter`/`limit`/`page`/`offset`, `db_total_page`/
`db_num_rows` on the first row via `core/table_query.py` on the backend
side — `receiving_repository.py`/`stock_out_repository.py`'s
`list_items_by_header` and `stock_in.py`/`stock_out.py`'s `get_items`).
This used to be a bespoke `ft.DataTable` widget instead, because
`components/table/rows.py`'s row-tap handler was hardcoded to navigate to
`/modules/{module}/edit/{id}` — which collides with the header's own edit
route. Rather than keep duplicating the paginated-list plumbing, `Table`
itself grew two small hooks so a sub-table *can* reuse it:
- `edit_screen` (default `"edit"`) — the screen name a row click navigates
  to (`/modules/{module}/{edit_screen}/{id}`); item tables pass
  `edit_screen="item_edit"` instead so item clicks don't collide with the
  header's own edit screen. `stock_out`'s item table has no field marked
  `"key": True` at all (items are create-only, no edit screen to navigate
  to — same convention as `stock_browse`/`usage_report`).
- `custom_param` — extra static query params merged into every
  `get_data()` request, used here for `header_id`.

  Each `ItemTable` wrapper receives the header's edit `ModulePage` as
  `parent` and exposes a `view` property delegating to `parent.view`
  (`Table.get_data()` calls `parent.view.show_error(...)` on failure) — it
  must be constructed *after* `self.view = ModuleView(...)` in the edit
  page's `__init__`, since `Table.__init__` fetches data immediately.
  Because `Table`'s own layout expands to fill its parent, and the edit
  page nests it inside an already-scrolling `ft.Column` alongside the
  header `Form`, it's wrapped in a fixed-height `ft.Container` (see
  `stock_in/edit.py`/`stock_out/edit.py`'s `body()`) so it gets its own
  bounded scroll region instead of collapsing to zero height.

  The "+" button still navigates to `item_new/<header_id>` and row-click
  (stock_in only) to `item_edit/<item_id>` — screen names local to each
  module, no collision with the header's own `edit` screen. None of these
  screens use `Form.submit()` (which always redirects to
  `/modules/{module}/index`); they build their own submit payload, POST via
  `HttpClient`, and redirect back to the header's `edit/<header_id>` screen
  instead. `item_new` repurposes the route's `record_id` slot to carry the
  *header* id (it only ever creates, so there's no item id yet); `item_edit`
  (stock_in only) does a small extra GET up front to learn its item's
  `receiving_header_id` (needed to know where to navigate back to, since
  the route only carries the item id). `stock_in/item_new.py` still calls
  `self.form.serialize()` on a regular `Form` (material_id/location_id/
  qty_received/price_buy/remarks, one location per submission).
  `stock_out/item_new.py` doesn't use `Form` at all — it's hand-built around
  a material `Dropdown` (`on_select` points a `components/table/table.py`
  `Table`'s `custom_param` at the chosen `material_id` and calls
  `get_data()` against `C_stock_out/get_stock_by_material`, one row per
  location currently holding that material) and, on submit, reads back the
  table's editable cells and posts the non-blank rows as repeated
  `location_id`/`qty_out`/`remarks` form fields to
  `C_stock_out/submit_items` (see the FIFO note in the Inventory Domain
  section above). This is the first (and so far only) `Table` built with
  `is_inside_form=True` *and* no initial fetch at all — construction just
  builds the (empty) table shell, and `on_material_select` is the only
  thing that ever calls `get_data()`.

  Getting `Table` to support editable cells needed one generically reusable
  addition to `components/table/`, previously read-only display only
  (`TableRows.load()` always rendered `ft.Text`): seven `"type"` values now
  render an editable control instead of text (`TableRows._build_editable_cell()`
  is the dispatch point) —
  - `"input"` — single-line `ft.TextField` (`hint_text`/`keyboard_type`,
    same keys `components/form/input.py` uses).
  - `"textarea"` — multiline `ft.TextField` (`min_lines`/`max_lines`).
  - `"select"` — `ft.Dropdown` fetching options from
    `C_{module}/call_{field_name}_select` (or a field-level `endpoint`
    override), same convention as `components/form/select.py`. Fetched
    once per column and cached on the `TableRows` instance (`_select_options_cache`)
    since the option list is normally identical for every row - not
    refetched per row, and not refreshed on a later reload within the same
    `TableRows` lifetime.
  - `"option"` — `ft.Dropdown` from a field-supplied static `"options":
    [{"value", "label"}, ...]` list, no HTTP fetch - for small fixed
    enumerations that don't need a backend round trip.
  - `"datepicker"` — reuses `components/form/date.py`'s `DateForm` as-is
    (calendar-popup TextField, ISO value tracked separately from the
    displayed "dd Mon yyyy" text, including its UTC-offset day-rollback
    correction) - one `DateForm` instance per cell.
  - `"checkbox"` — an `ft.IconButton` toggling between
    `ICON_CHECKBOX_CHECKED`/`ICON_CHECKBOX_UNCHECKED` (issue #44 restyled
    this from a plain `ft.Checkbox`; accepts a bool or a truthy string
    from the fetched row data). Its header renders two icon buttons
    (check-all/uncheck-all, issue #46) instead of a plain text label —
    `TableColumns._build_checkbox_header()`, wired through
    `Table._handle_checkbox_header_click()` into
    `TableRows.set_all_checkbox()`.
  - `"radio"` (issue #45) — shares `rows.py`'s `_CheckboxCellValue` with
    `"checkbox"` for its toggle/set_value bookkeeping, but renders a real
    circle-with-dot radio glyph (`ICON_RADIO_CHECKED`/`ICON_RADIO_UNCHECKED`
    = `ft.Icons.RADIO_BUTTON_CHECKED`/`RADIO_BUTTON_UNCHECKED`, passed via
    `_CheckboxCellValue`'s `icon_pair` param — 2026-07-27 follow-up,
    replacing an initial version that reused `"checkbox"`'s own
    check-box icon pair, which visually looked like a checkbox despite
    behaving like a radio) — and clicking one enforces exclusivity instead
    of toggling independently, via `TableRows._on_radio_click()`. Two
    modes, mirroring senar's `byColumn`/`byRow` table fields:
    - **By-column** (default, or `"radio_mode": "column"`) — mutual
      exclusivity spans the whole column: selecting one row's radio
      deselects that same field across every *other currently-loaded*
      row. Renders like an ordinary column - plain text-label header, no
      special-casing in `TableColumns._build_data_columns()` at all (it
      just falls through the normal label/sort path unmodified).
    - **By-row** (`"radio_mode": "row"`) — several sibling columns share
      one `"radio_group"` name; within one row, selecting one of those
      columns' radios deselects the *other radio_group columns in that
      same row only* (each row is its own independent exclusivity
      group) - the Likert-scale/audit-checklist-grid shape (e.g. "Yes"/
      "No"/"N/A" columns, one row per question). A by-row grid's rows
      aren't restricted to only radio columns - an ordinary `"input"`
      (e.g. a free-text "Remarks" column) can sit alongside the
      radio-group columns in the same row for free, since it's just
      another field in `_EDITABLE_TYPES`'s existing per-field dispatch.
    - **By-row groups render one shared/spanning header** (labeled via a
      `"radio_group_label"` on any one of the group's fields, not each
      column's own `"label"`) - `TableColumns.get_radio_group_overlay()`.
      **Spike finding**: Flet's `DataTable`/`DataColumn` has no native
      column-span (confirmed by reading the installed `flet` package's
      own `datatable.py` source directly - `DataTable.before_update()`
      hard-requires every visible `DataRow` to carry exactly
      `len(columns)` visible `DataCell`s, no colspan/merge concept
      exists at all). Each grouped radio column still gets its own real
      `DataColumn` (blank header cell - `_build_data_columns()`'s
      `radio_mode == "row"` branch), so the column/cell-count invariant
      holds; the merged look is purely visual, drawn as one positioned
      `ft.Container` per group (computed left/width from `self.widths`,
      same `TABLE_HORIZONTAL_MARGIN`/`TABLE_COLUMN_SPACING` cumulative-
      offset math `_reposition_handles()` already uses) in the same
      overlay `Stack` sitting on top of the header that the resize
      handles already occupy (`get_resize_overlay()`,
      `Table._build_header_with_resize_overlay()`) - the same "overlay a
      real DataTable" technique, reused for a second, unrelated purpose.
      Unlike the resize handles, this overlay has no drag-gesture
      identity to preserve, so it's rebuilt fresh on every call rather
      than cached. Assumes every field sharing one `"radio_group"` name
      is listed contiguously in the table's `fields` list (matches how a
      Likert grid is naturally authored).
    - `"radio"`-type columns get the same fixed-width treatment as
      `"remove"`/`"checkbox"`/`"option"` (`_FIXED_WIDTH_TYPES`, 60px
      default via `_EDITABLE_MIN_WIDTHS`) regardless of mode - never
      content-derived, overridable per-field via `"min_width"`.
    - `get_rows_with_input_values()`/`get_input_values()` return a plain
      `bool` per radio cell, identical contract to `"checkbox"` - no
      special-casing needed by callers.
    - Planned first consumers (audit checklist, survey module) are each
      their own separate, not-yet-scoped issue.

  `Table.get_rows_with_input_values()` returns each fetched row's dict
  merged with the current value of every editable-type field in it, in
  fetch order — `"datepicker"` columns via `DateForm.get_value()` (the raw
  ISO string), everything else via the control's own `.value`. The caller
  never wires its own per-row control bookkeeping. An editable cell never
  wires the row-tap-to-edit-screen handler (even if some other column in
  the same `Table` is marked `"key": True`), since a tap there needs to
  land in the control to interact with it, not navigate away.

  Every cell (editable or not) is wrapped in a fixed-width `ft.Container`
  matching `TableColumns.load()`'s computed per-column width - without that
  wrapper Flutter sizes the DataTable column from the raw control's own
  intrinsic width instead (e.g. a bare `TextField`'s ~300px default),
  drifting the column out of alignment with the rest of the table.
  `TableColumns._get_widths()`'s proportional scale-down (when a table's total
  content is wider than the screen) also respects a *per-column* minimum
  now, not one flat `40px` for every column - `_EDITABLE_MIN_WIDTHS` in
  `components/table/columns.py` floors editable types higher (e.g. `input`
  100px, `textarea` 160px), since a rigid-width control genuinely can't
  render below some size without visually overflowing its cell, unlike a
  plain `Text` cell, which just ellipsizes gracefully at any width. A field
  can override its floor directly with `"min_width"`.

  `components/table/columns.py` also has two more general table behaviors,
  not specific to editable cells:
  - **Last-column right padding — removed 2026-07-17, superseded by
    `TABLE_OUTER_HORIZONTAL_PADDING`**: this used to reserve an extra 12px
    out of `get_usable_width()`'s budget and add it back onto only the
    last column's width in `load()`, giving it breathing room before the
    table's true right edge on a table that otherwise sat flush against
    the screen (padding=0). Once issue #27 gave `Table.build()` a
    symmetric default outer padding (`TABLE_OUTER_HORIZONTAL_PADDING`,
    12px both sides), the two mechanisms stacked: the right edge got 12px
    (outer padding) + 12px (last-column bonus) = 24px versus the left
    edge's 12px, a visible, reported asymmetry. Deleted the last-column
    mechanism entirely (`_LAST_COLUMN_RIGHT_PADDING` constant and both call
    sites) - the outer Container's own padding is now the sole source of
    left/right breathing room, and it's symmetric by construction.
    Verified: column widths now sum correctly with no artificial bonus on
    the last column.
    - **`scrollbar_width`/`safety_buffer` fudge factors also removed, same
      day**: user reported the header/body still had a visibly bigger right
      gap than the (correctly symmetric, plain `expand=True`) toolbar even
      after the last-column fix above. `get_usable_width()` was shrinking
      its budget by two more constants with no matching real element:
      `scrollbar_width` (10px, reserved unconditionally even though the
      body's `ft.Column(scroll=AUTO)` scrollbar only takes space when
      content actually overflows vertically - most tables never trigger
      it) and `safety_buffer` (literally `= horizontal_margin`, i.e.
      `TABLE_HORIZONTAL_MARGIN` applied a *second* time on top of the
      already-correct `horizontal_margin * 2` deduction, no distinct
      purpose). Removed both - `get_usable_width()` now only subtracts the
      DataTable's own `horizontal_margin` (both sides, matches
      `header.py`/`body.py`'s real `horizontal_margin=TABLE_HORIZONTAL_MARGIN`),
      `TABLE_OUTER_HORIZONTAL_PADDING` (both sides), and inter-column
      spacing - every deduction now traces to something actually rendered.
      Verified: the reconstructed rendered footprint now matches the
      real available space within 1px, versus ~20px before this fix.
  - **Manual column resize** (Excel/Sheets-style, ported from a
    plain-HTML/CSS reference implementation the same project already uses
    elsewhere): every column boundary except the very last one gets a
    draggable divider, sized the way Excel/Sheets does it - a wide but
    invisible hit zone (`_RESIZE_HANDLE_HIT_WIDTH`, 16px) centered on the
    boundary, so the user doesn't need pixel-perfect aim, with only a thin
    line (`_RESIZE_HANDLE_VISIBLE_WIDTH`, 2px) actually drawn inside it.
    The line matches the table's own (semantic, theme-aware) background
    color at rest, highlighting to the primary color on hover or while
    dragging (hovering/dragging anywhere in the wider hit zone counts, not
    just over the thin line itself); double-tap resets that pair back to
    auto-fit.
    - **Every handler is guarded by `TableColumns._is_live()`**: a stale
      handle from a previously-visited screen keeps receiving client-side
      pointer events after navigating away (the client keeps old
      `GestureDetector`s alive even though `page.data["active_tables"]` was
      cleared), which used to cause phantom/stuck highlight states.
      `_is_live()` checks membership in `page.data["active_tables"]` via a
      `TableColumns.owner` back-reference. Full investigation (three
      earlier rounds of fixes wrongly targeted the highlight bookkeeping
      itself before the stale-instance cause was found) in
      CHANGE_HISTORY.md (2026-07-27).
    - **Known open bug — issue #50, deferred**: after the fix above, the
      *first* drag on a screen works end to end, but a second drag does
      not; root cause not fully characterized (prime suspect: every drag
      tick rebuilding the header around the cached handle controls leaves
      stale drag state or a confused client-side gesture arena). See
      CHANGE_HISTORY.md for the confirmed-so-far diagnosis.
    - **Highlight state is one flag, not per-handle bookkeeping**:
      `TableColumns._highlighted_index` is the single source of truth,
      resolved by `_refresh_resize_handle_colors()`, flushed via a
      targeted `bar.update()` per bar (not `page.update()`, which was
      confirmed not to flush this nested `bgcolor` change; not a full
      header rebuild either, which broke hover wiring).
    - **Handles live outside the `DataTable` entirely**, in an
      absolutely-positioned overlay `ft.Stack` on top of the header
      (`TableColumns.get_resize_overlay()`, built once and cached - reused as
      the exact same control objects on every later call). This is the key
      design point, arrived at after two failed approaches:
      1. Embedding the handle inside the header's own `DataColumn` label
         and rebuilding the header/body on every drag tick tore down the
         very `GestureDetector` doing the dragging (a rebuild replaces it
         with a new control), dropping Flutter's pointer capture after the
         first move.
      2. Keeping the handle embedded but only live-mutating cells'
         `Container.width` in place (no rebuild during the drag) kept the
         gesture alive, but Flutter's `DataTable` only reliably *grows* a
         column that way - confirmed empirically (diagnostic logging
         showed both columns' `Container.width` being mutated with
         correct, symmetric values on every tick, yet only the growing
         neighbor was visibly resizing). Flutter grows to fit a wider
         child during normal layout, but won't shrink a column's rendered
         width back down from a property patch alone, only from a real
         rebuild - and rebuilding only ever on drag-release (deferring the
         fix) left the shrinking side visibly frozen for the whole drag,
         only snapping to size on release.

      Moving the handle out of the `DataTable` breaks that tension:
      `TableColumns.on_resize_commit(recompute: bool)` now fires on *every*
      `handle_drag()` step (`recompute=False`) as well as a double-tap
      reset (`TableColumns.reset_column_pair()`, `recompute=True`) - wired by
      `Table.__init__` to `Table._handle_resize_commit`, which (for a
      reset) recomputes `TableColumns.widths` from content via `TableColumns.load()`,
      then always runs `TableRows.load()` and rebuilds the header (through
      `Table._build_header_with_resize_overlay()` - every header-rebuild
      call site must go through this, not `TableHeader.build()` directly, or
      the overlay silently drops off the tree) and body in place. A full
      rebuild on every tick is only safe *because* the handle is no longer
      inside what's being rebuilt: Flet's control-id-based patching (not
      tree-position-based - `messaging/session.py`'s `patch_control` skips
      `will_unmount()` for any removed control that's also present among
      the added controls) recognizes the same `GestureDetector` object
      reappearing in a brand new `Stack` and leaves it mounted, preserving
      the in-progress gesture across the header's repeated recreation.
      `TableColumns._reposition_handles()` moves each handle's `left` to its
      column boundary's real rendered x-offset after every width change,
      using `TABLE_HORIZONTAL_MARGIN`/`TABLE_COLUMN_SPACING` - the same
      constants `components/table/header.py`/`body.py` construct their
      `DataTable`s with, centralized in `columns.py` so the two can't
      silently drift apart. `GestureDetector.drag_interval=50` (~20fps)
      throttles the rebuild rate, heavier per-tick now than the old
      property-patch-only approach.
    - Steals/gives width to the *next* column only, keeping the row's
      total width constant - this table has no horizontal scroll
      (`components/table/body.py`'s `ft.Column(scroll=...)` only scrolls
      vertically), so a resize can only redistribute existing space, never
      grow the table past the screen.
    - Once a user drags a handle, `TableColumns.manually_resized` is set and
      `load()` stops recomputing widths from content on later data reloads
      (pagination/filter/scroll-more) - it just keeps whatever the user
      set, like a spreadsheet remembering a manual column width.
      **A window-resize reload is the one exception** (issue #48,
      2026-07-27): before this fix, `load()` treated a page-resize reload
      exactly like any other - the frozen absolute-pixel manual widths
      never changed, so a table with any manually-resized column silently
      stopped responding to the browser window's size from that point on.
      `Table.on_page_resize()` now calls `self.load(self.data,
      rescale=True)`, threaded through as `TableColumns.load(data,
      rescale=True)` - when `manually_resized` and `rescale` are both true,
      `_rescale_manual_widths()` scales every non-fixed-width column's
      width by `new_usable_width / old_sizable_total`, preserving the
      user's chosen *proportions* between columns while still fitting the
      new screen width (fixed-width columns - `"remove"`/`"checkbox"`/
      `"option"`/`"radio"` - are excluded, same as the normal auto-fit
      path). A normal, non-resize reload (`rescale=False`, the default)
      keeps the exact old behavior - manual widths untouched. Verified: a
      non-resize reload leaves manually-set widths unchanged; a resize
      reload rescales them proportionally in both directions. Manual
      drag-resize itself re-confirmed live in the browser (still works
      unchanged).

      **The actual root cause of #48, found after this proportional-rescale
      fix still didn't resolve the user's real-browser report**:
      `main.py` registered the resize handler as `page.on_resized` (with a
      trailing "d"). Flet's `BasePage` (`flet/controls/base_page.py`)
      declares the real field as `on_resize` (no "d") -
      `Optional[EventHandler["PageResizeEvent"]]`, firing with a
      `PageResizeEvent` carrying `width`/`height` in logical pixels
      directly. `Page` isn't a slotted dataclass, so assigning to the
      wrong attribute name doesn't raise - it silently attaches a dead,
      never-invoked instance attribute instead of actually registering a
      handler. **Every table on every screen had been ignoring window
      resize/maximize entirely** - not just tables with a manually-resized
      column, which is what the original investigation (correctly, as far
      as it went) concluded needed fixing. Fixed by changing
      `page.on_resized = page_resized` to `page.on_resize = page_resized`
      and updating the handler's event type/print to use the event's own
      `e.width`/`e.height` rather than reading `page.width`/`page.height`
      back off the page object afterward.

      This explains why the sandboxed automation environment's own
      `resize_window` test (see the now-superseded note this replaced)
      couldn't detect a difference either way - with the wrong attribute
      name, no resize signal would have reached Python regardless of
      whether the browser-side viewport genuinely changed, so that test
      was inconclusive by construction, not just by environment limits.
      Confirmed by the user directly (real physical browser resize/
      maximize, not automation) that the table did NOT reflow before this
      fix, and separately confirmed live afterward that the fix resolved
      it - window resize/maximize now correctly reflows table columns.
    - Shrinking a column narrow enough used to wrap its header label onto
      multiple lines, growing the header row into the row below it
      instead of truncating - both `TableColumns._build_data_columns()`'s
      header `Text` and `TableRows.load()`'s body-cell `Text`s now set
      `overflow=ft.TextOverflow.ELLIPSIS, max_lines=1` (Excel-style: a
      narrow column truncates to one line, it doesn't wrap). Below
      `_MIN_LABEL_VISIBLE_WIDTH` (24px) a header label is dropped
      entirely rather than rendered as one unreadable clipped character.
    - **Superseded** (kept for history): this paragraph originally said
      every `DataColumn` sets `on_sort=self.on_sort` unconditionally, and
      recorded an early, wrong guess that `on_sort`'s presence makes
      Flutter reserve extra header width for a sort-indicator icon -
      "wrong" because Flutter's `DataColumn` only *draws* that icon for
      the column matching `DataTable.sort_column_index` (never set here),
      so no icon is ever actually drawn. That part remains true. What this
      pass missed is that Flutter reserves the *space* for that icon
      whenever `on_sort` is non-null regardless of whether anything paints
      into it (confirmed via Flutter's own `DataColumn.onSort` docs) - a
      real, persistent header/body column-width mismatch once sort was
      rolled out broadly (issue #27), finally root-caused and fixed by
      removing `on_sort` from every `DataColumn` entirely (`on_sort=None`
      always) and driving header clicks through `Container.on_click`
      instead - see `_on_header_click()` under "Multi-column sort" above
      for the full fix. If a real divider/label misalignment resurfaces
      again, start from that fix's docstring, not this superseded one.
      `TableColumns._min_width_for()` still floors every column at
      `_RESIZE_HANDLE_HIT_WIDTH` (unrelated to the icon guess) so a
      column can't end up narrower than its own two half-handles (this
      column's right-edge handle plus half of the previous column's)
      need to coexist without overlapping.
    - Row/cell density was tightened to match single-line content: body
      `data_row_min_height`/`max_height` 40/60 → 36/44, header
      `heading_row_height` (previously unset, Flutter's 56dp default) →
      44, and cell padding 5px-all-around →
      `Padding.symmetric(horizontal=8, vertical=4-6)` (matching the
      editable-cell `content_padding` convention from earlier). All are a
      deliberate step *below* Material 3's own defaults (52dp/56dp row
      heights) - a "dense" density is appropriate here since no cell in
      this app is ever multi-line. `components/table/search_bar.py`'s
      `ft.SearchBar`, by contrast, was *kept* at Flutter's native ~56dp -
      that one's part of Flutter's own Material widget with no supported
      way to shrink it without fighting the framework, and 56dp genuinely
      is the M3 spec height for a standalone search bar (unlike the
      table's row heights, which aren't pinned to a single "correct" M3
      number the same way).
  - **Row border/divider lines replaced with position-based zebra
    striping** (issue #57, 2026-07-28): `components/table/header.py`/
    `body.py` both set `border=None, divider_thickness=0` on their
    `ft.DataTable`s - `border` alone (the old `ft.Border.only(...)`
    setup) only ever controlled the table's own outer frame; the
    horizontal lines actually drawn *between* rows are Flutter's
    `DataTable.divider_thickness` (default `1.0`), a separate property
    neither file had touched before. `TableRows.load()` now sets each
    built `ft.DataRow`'s `color` from `_ROW_COLOR_EVEN`
    (`ft.Colors.SURFACE`) / `_ROW_COLOR_ODD`
    (`ft.Colors.SURFACE_CONTAINER_LOW`) based on `row % 2`, where `row`
    is the same position counter `self.index`/`self.input_controls`
    already tracked (`len(self.rows)` on append, `0` on a fresh
    non-append load) - a genuine CSS `:nth-child`-style computation from
    current render position, never stored on the record, so it already
    inherited every existing "rebuild from `self.data`" mechanism for
    free: sort, per-column filter, `TableRemove`'s single/bulk delete
    (all rebuild via `Table.load(self.data, append=False)`, restarting
    the counter at `0`), and lazy-load append (continuing from
    `len(self.rows)`, not resetting at the page-1/page-2 boundary) all
    automatically produce a correct, consistent stripe with zero
    additional bookkeeping - confirmed by the fact that no other file
    needed changes for any of those paths. Both stripe colors are
    semantic M3 tokens (not fixed hex), matching every other themed
    color in this codebase, so both light/dark theme are expected to
    hold up the same way `SURFACE_CONTAINER_HIGH`/`_HIGHEST` already do
    elsewhere (issue #53).
    Verified live in the browser (light theme): clean alternating row
    backgrounds with no border/divider lines and no two adjacent rows
    sharing a color, including across the lazy-load append page boundary.
    Dark theme relies on the same semantic-token mechanism, not
    independently re-screenshotted. Full verification detail in
    CHANGE_HISTORY.md (2026-07-28).
  - **Row + cell hover M3 state layer** (issue #60): per-row and per-cell
    hover highlighting, scoped down from a broader row/column/cell request
    (a per-column stripe would need its own scroll-aware overlay `Stack`,
    scoped out as separate stretch work). `DataRow.color`'s
    `ControlStateValue`/`HOVERED` dict looked like the natural mechanism
    (its docstring implies Flutter composites a `HOVERED` entry over
    `DEFAULT`) but turned out to be dead code — Flutter's `DataTable` only
    ever resolves `WidgetState.selected` for `DataRow.color`, never
    `hovered`/`focused`, so that entry is silently never read. Fixed the
    same way this codebase's resize-handle hover already does: never rely
    on `ControlState` for hover, manually detect it via a real
    `Container.on_hover` and mutate color directly, `.update()`-ing just
    that row/cell. `TableRows.load()` keeps `DataRow.color` as the flat
    per-row zebra base (issue #57) and swaps it to `_ROW_HOVER_COLOR`
    (`SURFACE_CONTAINER_HIGH`) on hover via a shared per-row closure;
    the specific hovered cell additionally brightens to
    `_CELL_HOVER_COLOR = ft.Colors.SURFACE_CONTAINER_HIGHEST` (one M3
    tonal step brighter than `_ROW_HOVER_COLOR`, continuing the same
    ladder issue #53 already established), set/cleared in the same
    `_on_row_hover` closure alongside the row-color swap. Verified live
    (dark theme, `master_location`): the specific hovered cell is
    visibly brighter than the rest of its own row, which is in turn
    lighter than unhovered zebra-striped rows - three clearly
    distinguishable tiers (cell > row > zebra base) confirmed via a
    zoomed screenshot.
- Full stock-in → MAP calc across two receipts → edit-item MAP correction →
  browse → stock-out (FIFO across 3 lots, partial-lot deduction, insufficient-
  stock rejection, issue-from-empty-location rejection) → permission-gating
  flow was verified end-to-end with `TestClient` smoke tests against SQLite,
  plus a real walk against the live MariaDB container, prior to the
  multi-location `submit_items` rework above — those scripts weren't
  committed to the repo, so re-verify the stock-out leg (now "qty per
  location in one submission" instead of "one location per submission")
  before relying on this claim again.

## Frontend Architecture (Flet — `frontend/src`)

Stack: Python ≥3.10, Flet 0.86.4 (issue #68, upgraded from 0.85.3),
`requests` for HTTP, `flet-datatable2==0.86.4`; managed via
`pyproject.toml` (uv/Poetry).

**Flet 0.85.3 → 0.86.4 upgrade (issue #68)**: verified working end-to-end
under 0.86.4, including a full browser regression pass (login, home,
deep links, tables, forms, QR scan, TOTP setup, Dark Mode) with no
regressions found. **A stale Flet session can hang on the 0.86 boot
screen indefinitely** — Flet's own session-recovery logic reuses a
matching server-side `session_id` from the browser's client-side storage
instead of creating a fresh one, skipping `before_main()` entirely if
that session is stale (e.g. left over from a round of container
restarts); fix is to clear the browser's site storage or use a fresh/
incognito window, not a container restart. Not itself a 0.86 regression.
Not yet re-verified: `frontend/run.ps1`/`run.sh` against a real 0.86
`flet build`/`flet run`, and the dev-mode QR-scan companion app's
protocol compatibility. Full investigation (including an unrelated
host-networking TIME_WAIT issue that blocked the first regression-pass
attempt) is in CHANGE_HISTORY.md (2026-07-29/30).

- **Entry & routing** (`src/main.py`): `ft.run(main)` bootstraps an async
  `main(page)`. Shows `SplashScreen`, loads persisted state via
  `Storage(page).load_persistent()`, preloads all `pages/modules/*` and
  `pages/modals/*` screens via `ModuleLoader`, then drives navigation through
  `page.on_route_change`:
  - `/` or `/login` → `pages/login.py`
  - `/home` → `pages/home.py`
  - `/server_config` → `pages/server_config.py` (where the user manually
    types the backend server address)
  - `/troubleshooting` → `pages/troubleshooting.py`
  - `/modules/<module>/<screen>/<id?>` and `/modals/<modal>/<screen>/<id?>`
    → dynamically resolved via `ModuleLoader` (permission-checked for
    modules via `storage.client_data.has_permission`)
  - Boot logic (`_boot_navigate`): if no server URL was ever actually
    saved (`storage.server_url.is_configured()` — an explicit flag set by
    `ServerURL.load()`/`set()` based on whether a persisted value exists,
    **not** a `get() == DEFAULT_SERVER_URL` comparison) → force
    `/server_config`; else if the client session is still active
    (`client_data.is_active()`, a real `C_home/home` round trip using the
    persisted cookies) → `/home`; else → `/login`. The value comparison it
    replaced was a real bug (fixed 2026-07-14): the containerized
    deployment's correct, saved address IS `DEFAULT_SERVER_URL`
    (`http://backend:5000`), so a properly-configured, logged-in install
    was indistinguishable from a fresh one and every new tab/session got
    bounced to `/server_config` before `is_active()` could restore it.
  - **Every boot destination goes through `_boot_navigate_to(route)`, never
    `_push_route_safe()` directly** (issue #51, 2026-07-27).
    `page.push_route()` only delegates to the client, which fires
    `on_route_change` back to Python *when the route actually changes* - so
    when the browser is already sitting on the target URL, the push is a
    silent no-op, `route_change()` never runs, and the splash view appended
    by `main()` is never replaced. That is the "web app stuck on loading"
    hang: it hits whenever the page reloads with a deep link still in the
    address bar (`/home`, any `/modules/...`), which is exactly what a
    container restart / code change produces, while a cold boot from `/`
    works fine because pushing `/home` genuinely changes the route.
    `_boot_navigate_to()` compares `page.route` against the target and, on
    a match, awaits `route_change(None)` directly (it ignores its argument
    and reads `page.route` itself) instead of pushing - which is what
    Flet's own `push_route` docstring example does to build the initial
    view, so it's the documented way to render the starting route rather
    than a workaround. Verified: direct loads of a deep link now render
    immediately and a container restart + reload recovers with no
    address-bar workaround needed.
  - **A logged-in boot stays on the current screen instead of bouncing to
    `/home`** (#51 follow-up, same day): `_boot_navigate()` only ever
    targeted `/server_config`/`/home`/`/login`, so reloading at e.g.
    `/modules/stock_movement/index` silently lost your place. That was
    always true but invisible - before the same-route fix above, such a
    reload hung on the splash rather than visibly redirecting.
    `_preserved_boot_route()` returns `page.route` when it starts with
    `/modules/`/`/modals/`, and the active-session branch uses
    `_preserved_boot_route() or "/home"`. Deliberately narrow: the routes
    the boot conditions themselves own (`/`, `/login`, `/server_config`)
    must keep being *decided* by those conditions rather than echoed back,
    or a logged-out session sitting on `/login` would never be
    re-evaluated. It is only consulted inside the `is_active()` branch, so
    a logged-out deep-link still falls through to `/login` by construction;
    an unknown or unauthorized module still degrades gracefully because
    `route_change` already permission-checks and falls back to an
    `ErrorPage`.

- **Pages** (`src/pages/`): top-level singleton pages (`login`, `home`,
  `server_config`, `troubleshooting`, `error`, `permission_error`, `loader`),
  plus `pages/modules/<module_name>/{index,edit,new,detail,...}.py` (one
  folder per business module, each exposing a `ModulePage` class) and
  `pages/modals/{password,shift,token,totp}/index.py` (each exposing a
  `ModalPage` class). A module folder can also hold private, non-screen
  helper files alongside `index`/`new`/`edit` — e.g.
  `pages/modules/ap_master_user/permission_table.py` (see below) —
  `ModuleLoader` only preloads files matching an actual route
  (`<module>/<screen>`), so a helper file with no matching route is simply
  never preloaded/dispatched as a screen, just imported normally by
  whichever screen uses it.
  - `ap_module` (list/new/edit) and `ap_master_user` (list/new/edit) are the
    admin CRUD screens for `modules` and `users` + their permission grants,
    backed by `routers/module_admin.py` and `routers/user_admin.py`. Both
    use the generic `components/table/table.py` (list) and
    `components/form/form.py` (create/edit) — no bespoke fetch/submit code,
    just a `fields` list per screen (see `ap_config` for the original
    pattern this follows). Deleting a row isn't part of the generic
    `Table`/`Form` framework yet, so both `edit.py` screens add their own
    delete button via `ModuleToolbar.add_button(...)` calling
    `POST C_{module}/delete` directly.
  - **Module-access grant flow** (issue #41, 2026-07-21, replacing the
    original inline `PermissionChecklist` checkbox list): `ap_master_user/
    edit.py` embeds `pages/modules/ap_master_user/permission_table.py`'s
    `PermissionTable` — a thin wrapper around the shared
    `components/table/table.py` `Table` (same shape as
    `stock_in/item_table.py`'s "Add Item" sub-table pattern), showing the
    user's currently-granted modules (`GET C_ap_master_user/
    get_granted_modules?id=<user_id>&...`), paginated/filterable via the
    normal generic per-column filter convention. Also opts into the shared
    single/bulk row-remove column (issue #42, see below) to revoke access
    directly from this table. Its own "Add Permission" toolbar button (`Table`'s own
    `add_new_button`, not the page-level `ModuleToolbar`) navigates to
    `/modules/ap_master_user/permission_new/<user_id>`.
    `pages/modules/ap_master_user/permission_new.py` is a `record_id`-
    accepting `ModulePage` (`record_id` here is the *user* id) showing a
    `Table` of every module the user does **not** yet have access to
    (`GET C_ap_master_user/get_ungranted_modules?id=<user_id>&...`, same
    filterable convention), each row carrying a `"type": "checkbox"`
    editable column (`"filter": False` — a free-text filter on a boolean
    makes no sense, and it has no backing DB column anyway). Checking any
    number of rows and pressing the table's "Submit" toolbar button reads
    them back via `Table.get_rows_with_input_values()` (same mechanism
    `stock_movement/item_new.py` uses for its own editable-cell columns)
    and posts the checked module ids to `POST C_ap_master_user/
    submit_permission_new` (form: `user_id` + repeated `module_ids`) —
    **additive only**: it calls `UserModulePermissionRepository.grant_access`
    once per id, it does not replace the user's existing grant set the way
    the old `save_permissions` (now removed) did. On success, redirects
    back to `/modules/ap_master_user/edit/<user_id>`, where the
    granted-modules table reflects the new grants on its next fetch.
    Backend: `ModuleRepository.list_granted_modules_for_user`/
    `list_ungranted_modules_for_user` (both in
    `backend/src/repository/module_repository.py`, reusing that file's
    existing `_FILTER_COLUMN_MAP`/`_FILTER_NUMERIC_FIELDS` for
    `apply_column_filters`/`apply_sort` — same `table_query.py` convention
    as every other paginated list) — the ungranted variant excludes every
    module id already present in a `UserModulePermissionModel` subquery
    for that user (`~ModuleModel.id.in_(...)`). The old
    `get_all_modules`/`get_permissions`/`save_permissions` endpoints and
    `permission_checklist.py` were removed outright (nothing else
    referenced them); `UserModulePermissionRepository.get_module_ids_for_user`/
    `set_modules_for_user` themselves were left in place as still-generic,
    reusable repository methods even though nothing currently calls them.
    Verified against the real containerized backend: grant/ungrant lists
    update correctly, existing grants stay untouched, and an empty
    submission is rejected cleanly. Not yet clicked through in a live
    browser. Full verification detail in CHANGE_HISTORY.md (2026-07-21).
  - **Single/bulk row-remove column** (issue #42, 2026-07-21, ported from
    senar's `y.panel.js`'s `buttonRemove` cell and `y.form.js`'s
    `listenerClickClassRowRemove`/`listenerClickClassHeaderRemove` and
    friends): a new, reusable, opt-in capability on the shared
    `components/table/table.py` `Table` —
    `Table(..., on_remove_row=..., on_remove_rows=...)` — implemented in
    `components/table/remove.py`'s `TableRemove`. Either callback alone is
    enough to opt in; `Table.__init__` then appends a synthetic trailing
    `{"name": "_remove", "type": "remove", "filter": False}` field to its
    own `fields` list so no caller ever hand-authors that column, and
    constructs one `TableRemove(page, self, on_remove_row=..., on_remove_rows=...)`,
    wired onto both `TableColumns` (`self.columns.remove = self.remove`,
    read by `_build_data_columns()` to render the header button) and
    implicitly onto `TableRows` (which reads `self.parent.remove` — `parent`
    being the `Table` itself — to render each row's button). Each callback
    takes the row dict(s) to remove and returns an error message string to
    abort, or `None` on success; `Table` has no idea what a remove actually
    does server-side, and reuses its own existing `Table.load(self.data,
    append=False)` (the same "recompute + rebuild from current data" path
    a sort click or resize tick already uses) to re-render after mutating
    `self.data` in place — no bespoke re-render logic was needed.
    - **Two modes, each with two always-visible header buttons instead of
      one modifier-key toggle** (see below for why the original
      senar-mirroring Shift+click design was abandoned): **single**
      (default) shows a delete icon on every row; clicking one opens a
      confirm dialog (`ft.AlertDialog` on `page.overlay`, this app's only
      other precedent being `components/troubleshooting/body.py`'s
      hard-reset confirm) and removes just that row on confirm. The header
      shows two compact buttons (`components/button.py::Button`, 28px, same
      family as every other compact icon button in this app):
      "select all" (`_on_select_all_click`) enters **multiple** mode with
      every row pre-checked; "select none" (`_on_select_none_click`) enters
      it with every row unchecked instead, letting an admin cherry-pick.
      While in multiple mode, clicking a row toggles its own checked state
      (`_ICON_ROW_SELECTED`/`_ICON_ROW_UNSELECTED`), and the header shows a
      different pair: "remove selected" (`_on_bulk_execute_click` - a
      second confirm dialog reporting the count, then bulk-deletes whatever
      is checked and returns to single mode; silently returns to single
      mode with no dialog if nothing's checked) and "cancel"
      (`_on_cancel_click` - returns straight to single mode, no
      confirmation, no delete, regardless of which single-mode button was
      used to enter multiple mode).
      `TableRemove.reset_for_reload()` is called from `Table.get_data()`
      specifically — **not** from `TableRows.load()` — right when a
      genuinely new server response lands (`not append`). `TableRows.load()`
      also runs on `TableRemove`'s own local re-renders (a mode toggle or
      row-selection toggle), so resetting there would wipe out the very
      state change the re-render exists to display; only a real fetch may
      reset remove state.
    - **The header button design (two always-visible buttons per mode,
      not a Shift-modifier toggle) exists because Shift+click genuinely
      doesn't work in this Flet/browser deployment**: the original design
      mirrored senar's single header button toggling on a held Shift key
      via `Page.on_keyboard_event`, but live diagnostics confirmed the
      browser never delivers a keyboard event to the server at all on
      this click-only interaction path (most likely because it never
      gives the Flutter canvas actual DOM keyboard focus) — no Flet event
      of any kind carries a modifier-key flag as a fallback either. Fixed
      by replacing the Shift-modifier design with two always-visible
      buttons per mode instead — functionally identical outcomes, zero
      dependency on the non-working keyboard channel. Full investigation
      (including the two registration-timing attempts tried and ruled out
      first) is in CHANGE_HISTORY.md (2026-07-21).
    - **Live-verified**: all five user-specified scenarios (single-row
      remove, select-all/select-none entry, bulk remove, cancel) confirmed
      working in the actual browser.
    - **Column/row wiring in `components/table/columns.py`/`rows.py`**:
      `TableColumns._build_data_columns()` special-cases `field.get("type")
      == "remove"` to swap in `self.remove.build_header_cell(w)` instead of
      the normal label/sort-icon content — but **only when `interactive`
      is `True`**; `TableBody`'s own hidden structural header row
      (`heading_row_height=0`, built via `columns.build(interactive=False)`)
      renders a plain empty `ft.Container(width=w)` instead, same fix
      pattern already established for sort icons (Flutter doesn't fully
      clip a zero-height heading row's content, so a real button there
      could visually bleed into the first data row). `TableRows.load()`
      special-cases the same field type before the `_EDITABLE_TYPES`
      dispatch (a remove button isn't a value-holding input, so it's
      deliberately excluded from `get_input_values()`/
      `get_rows_with_input_values()`).
    - **Fixed width, not dynamic sizing** (issue #43, generalized in #44
      from just `"remove"` to also cover `"checkbox"`/`"option"`): these
      three column types have a known-constant required width (remove:
      room for two 28px compact buttons, 80px; checkbox: 50px; option:
      120px - all from `_EDITABLE_MIN_WIDTHS`, still overridable per-field
      via `"min_width"`), so unlike every other column type none of them
      participate in `_get_initial_widths()`'s content-length sizing or
      `_get_widths()`'s proportional scale-down when total content exceeds
      the available screen width. `TableColumns._fixed_width_indices()`
      (`_FIXED_WIDTH_TYPES = {"remove", "checkbox", "option"}`) returns
      `{column index: fixed width}` for every such column in the table -
      `TableColumns.load()` reserves their combined width off the top of
      `get_usable_width()`'s budget, sizes only the remaining columns
      against what's left (`_get_widths()`/`_get_initial_widths()`, both
      taking an explicit `field_names` list rather than reading
      `self.index` directly, so they can be called against just the
      dynamic columns), then splices the fixed widths back in at their
      original positions - handles any number of fixed-width columns in
      any position, not just a single trailing one. Neither shrinks below
      nor grows past its fixed width regardless of screen size or other
      columns' content. `get_resize_overlay()` skips building a handle on
      either side of any fixed-width column's boundary - nothing to drag.
      `"option"` gets width-only treatment - its header still renders as a
      plain text label via the normal (non-`"remove"`) path in
      `_build_data_columns()`, no icon-based header content. Verified via
      dedicated scripts: fixed-width columns hold their width at any
      screen size with zero resize handles on their boundaries; a table
      with no fixed-width column is unaffected. Full detail in
      CHANGE_HISTORY.md (2026-07-22).
    - **Checked/unchecked icon style for generic `"checkbox"`-type cells**
      (issue #44): `components/table/rows.py::_build_editable_cell()`'s
      `"checkbox"` branch now renders the same checked/unchecked icon pair
      `remove.py` uses for its own row-selection state
      (`ICON_CHECKBOX_CHECKED`/`ICON_CHECKBOX_UNCHECKED`, promoted to
      public names in `remove.py` and imported into `rows.py` - one shared
      definition, not a duplicated pair of icon constants), instead of a
      plain `ft.Checkbox()`. A new `TableRows._CheckboxCellValue` is the
      `value_holder` `get_input_values()` reads back from - it wraps the
      actual `ft.IconButton` control, toggling both `.value` (a plain
      `bool`, same read-back contract as before - no changes needed in any
      existing consumer like `permission_new.py`'s `row.get("selected")`)
      and the icon/color on every click. Verified: initial icon/value
      matches the row's starting value, a click toggles both, and
      `get_input_values()` still returns a plain `bool` unchanged.
    - **Application**: `ap_master_user/edit.py`'s granted-modules table
      (`permission_table.py`, from #41) is the first consumer —
      `_revoke_module`/`_revoke_modules` both post to the new
      `POST C_ap_master_user/revoke_permission` (form: `user_id` + repeated
      `module_ids`), which loops `UserModulePermissionRepository.revoke_access`
      per id (that repository method already existed; this issue only
      needed a router endpoint exposing it) — no new repository logic.
    - **Known gap**: a client-side-only removal (`del self.table.data[i]`)
      doesn't update `Table.total_rows`/`total_pages` (those track the last
      server-fetched pagination metadata), so `TableFooter`'s "Record X of
      Y" message can go briefly stale after a remove, until the next real
      fetch (sort/filter/page change) corrects it. Accepted as a minor,
      documented simplification rather than adding a footer-sync mechanism
      for what's otherwise a purely local, already-committed-server-side
      mutation.
    - **Icons** deliberately use a consistent checkbox metaphor rather than
      senar's own literal icon names (`'check'`/`'check_circle'`/
      `'radio_button_unchecked'`), per explicit user feedback after the
      live single-row test: header single-mode default is
      `ft.Icons.CHECK_BOX` (a checked-checkbox glyph, not an empty
      outline), row-selected is also `ft.Icons.CHECK_BOX`, row-unselected
      is `ft.Icons.CHECK_BOX_OUTLINE_BLANK`, and both the header-in-
      multiple-mode and every row's single-mode icon are `ft.Icons.DELETE`.
    - Verified: `TableRemove`'s full state machine, the fixed-width/
      header-gating wiring in `TableColumns`/`TableRows`, and the backend
      `revoke_permission` endpoint were all confirmed working, including
      a regression test reproducing the reset-stomping bug (a re-render
      triggered by `TableRemove` itself must not reset its own state,
      only a genuine new fetch should). Full detail in CHANGE_HISTORY.md
      (2026-07-21).

- **Components** (`src/components/`): reusable, presentational Flet control
  builders grouped by domain — `form/`, `home/`, `login/`, `server_config/`
  (server-URL `TextField` + save button), `troubleshooting/`, `list/` and
  `table/` (shared grid/table + search/toolbar), `modal/` and `module/`
  (shared chrome for dynamically-loaded screens), plus page-level
  `loading_overlay.py` and `splash_screen.py`.
  - `form/` field types, driven by each field dict's `"type"` (see
    `components/form/form.py::build_elements()`): `input` (`InputForm`),
    `label` (`LabelForm`, read-only), `select` (`SelectForm`, a `Dropdown`
    that fetches its options from `C_{module}/call_{field_name}_select`),
    `date` (`DateForm` — a read-only `TextField` + `ft.DatePicker` calendar
    popup, tap to open, closes on selection; stores/round-trips a plain ISO
    `"YYYY-MM-DD"` string, matching what the backend's `date` Form fields
    already expect/return). `date` reuses `input`'s value-extraction path in
    `serialize()` since `DateForm.build()` returns a plain `ft.TextField`,
    same as `InputForm` — no separate serialize/load handling needed. All
    interactive field types (`input`, `label`, `date`, `select`) set
    `expand=True` on their control so they fill their `ResponsiveRow`
    column on web — a fix applied after `input`/`label` were initially
    missing it while `select` already had it.
  - **Camera/photo scan option added alongside manual entry** (issue #64,
    2026-07-29). The `ScanInput` dialog (see #52 below) now offers a
    second path next to the autofocused text field: a "Scan with Photo"
    button that opens `ft.FilePicker(file_type=IMAGE, with_data=True)` —
    the device camera for one photo on platforms that support it, or a
    plain file browser otherwise — and decodes the picked bytes
    server-side with `pyzbar` (native `libzbar0`, added to
    `frontend/Dockerfile`; `pillow>=10.0.0`/`pyzbar>=0.1.9` added to
    `frontend/pyproject.toml`). `decode_image_bytes(data: bytes) -> str |
    None` is the standalone decode function (`PIL.Image.open` +
    `pyzbar.pyzbar.decode`, first result's `.data` UTF-8-decoded) — kept
    separate from the dialog-building code so it has no `ft` dependency
    and is directly unit-testable.
    **A genuine live in-browser camera scan (matching senar's own
    `html5-qrcode`-based `handleScanCamera()` in
    `code/public/js/framework/y.form.js`, including front/rear camera
    switching) was investigated and intentionally NOT built**: Flet
    0.85.3 has no WebView/JS-eval control to embed a third-party JS
    library the way senar's own HTML page does (confirmed via a full
    search of the installed `flet/controls/` package). The one real
    PyPI candidate found, `flet-camera` (official flet-dev package,
    wraps Flutter's `camera` plugin — preview/photo capture only, no
    barcode decoding of its own), only ships stable releases pinned to
    `flet==0.86.4`; at the time this was written the app was still on
    `flet==0.85.3`, whose only matching `flet-camera` releases were
    `.dev0`/`.dev1` prereleases, too risky to pin against.
    **Superseded by issue #68** (2026-07-29 upgrade to `flet==0.86.4`) —
    `flet-camera`'s own stable release now matches this app's pin
    exactly, so this specific blocker no longer applies; a genuine
    in-app camera-preview scan via `flet-camera` is a viable follow-up
    now, still not attempted in this pass (issue #68 was scoped to the
    version bump + regression pass, not new features). Left as a
    documented, larger future follow-up (a
    custom Flet extension wrapping a live-scan Flutter plugin), not
    attempted here — the photo-capture + server-side-decode path above
    is deployment-safe either way (web or native), since it only needs
    bytes already delivered to Python (this app's primary deployment
    runs the Flet process server-side in a container — see "Container
    networking gotcha" below — so a live in-Python camera read, e.g.
    `cv2.VideoCapture`, would read the *server container's* camera, not
    the end user's).
    **Never a silent failure** (explicit acceptance criterion): a photo
    with no decodable barcode/QR, or a cancelled/unreadable file pick,
    reopens the same manual-entry dialog — with a visible red error
    message for the no-decode/unreadable cases, silently for a plain
    cancel (same as clicking Cancel directly) — so the user can retry the
    photo or fall back to typing/scanning with the hardware gun.
    Verified: `decode_image_bytes()` confirmed correct against a real
    generated QR image inside the containerized frontend; live in the
    browser, the "Scan with Photo" button opens the native file picker
    and a cancel correctly reopens the manual-entry dialog with no error.
    Full verification detail in CHANGE_HISTORY.md (2026-07-28).
  - **Barcode/QR scan affordance** (`components/scan_input.py::ScanInput`,
    issue #52, 2026-07-27). The scanner is a **hardware gun acting as a
    keyboard wedge** — it types the scanned code plus Enter into whatever
    field has focus — **not** a camera scanner. So there is no dependency,
    no camera-permission flow, and it works on web (where this app runs)
    exactly as on native. `ScanInput(page, on_scan=...)` renders an
    `ft.IconButton` that opens a small `ft.AlertDialog` holding one
    `autofocus=True` `ft.TextField`, so the next scan lands there and its
    Enter fires `on_submit`; the caller's `on_scan(code)` decides what the
    code means. Same pattern as senar's `tm_confirm_seal_mobile/scan.py`
    (autofocus + `on_submit`) — note that repo has **no** camera scanner to
    port, only QR *generation* for TOTP, so this was written from scratch.
    Wired in three places, each opt-in so nothing else changes:
    - `SelectForm` — a field dict with `"qr": True` puts the scan button
      **inside** the field, immediately before the open/close arrow (the
      same shape the table search bar uses for its scan-then-X pair).
      `build()` still returns the `ft.Dropdown` itself. Flet's
      `trailing_icon` *replaces* the arrow rather than sitting beside it,
      so the arrow can't simply be left alone — but the slot is typed
      `IconDataOrControl`, so `_build_trailing()` supplies an
      `ft.Row([scan_button, arrow_icon])` that restores the affordance
      while keeping the button in the decoration box. `selected_trailing_icon`
      (rendered while the menu is open) needs its **own** pair, since one
      control instance can't occupy two slots in the tree at once — the
      shared `ScanInput` is therefore built twice, both buttons driving the
      same handler, only one ever visible. The button must be explicitly
      sized (`SCAN_BUTTON_SIZE`/`SCAN_ICON_SIZE`, public so
      `stock_out/item_new` shares one definition): an unconstrained
      `IconButton` in that slot carries Flutter's ~48dp tap target and
      visibly grows the field's height. Verified live that the arrow and
      scan button act independently (clicking scan doesn't also open the
      dropdown menu). Enabled on `stock_in/item_new`'s Material and
      Location.
    - `stock_out/item_new`'s hand-built raw `ft.Dropdown` (that screen uses
      no `Form`) gets the same in-field treatment via its own
      `_build_scan_trailing()`. Its scan handler **must call
      `on_material_select` explicitly** — assigning `Dropdown.value`
      programmatically does not fire `on_select`, so without it the
      dropdown would show the scanned material while the per-location
      stock table below still showed the previous one.
    - `Table(..., qr=True)` → `TableSearchBar(qr=True)` puts a scan button
      to the **left of the clear/X**, both inside the single `suffix_icon`
      slot via a tight `ft.Row`, with `suffix_icon_size_constraints` widened
      24→48px. Those constraints are not optional decoration: they exist to
      stop Flutter reserving its default ~48dp tap target per icon, which is
      what pushed the clear icon past the field's right edge in issue #19,
      so they must track the real content width. Enabled on
      `stock_out/item_new`'s per-location stock table, where Location is
      picked by row rather than from a dropdown.
    **Scanned codes resolve via `components/table/menu.py::resolve_option_value()`**
    (issue #25) — raw DB id, full `"CODE - Name"` label, or bare code
    prefix — so there is exactly one matching rule app-wide; do not add a
    second. An unmatched code raises a visible `view.show_error(...)`
    rather than failing silently.
    **Knock-on fix in `Form`**: `load()`/`serialize()` used to locate a
    select's value by `isinstance(control, ft.Dropdown)` on the built
    control. A scan-enabled select builds as a `Row`, which would have
    failed that check and silently skipped both populating and submitting
    the field. Both now read `Form.select[name].select` (the `SelectForm`
    instance's own Dropdown) instead, which is correct for every select
    regardless of how it was built.
    **Knock-on fix in the backend**: `GET C_stock_out/get_stock_by_material`
    accepted only `material_id` and silently ignored the
    `table-keyword-filter` its own search box had always been sending, so
    typing (or scanning) there filtered nothing. It now binds that param and
    `StockRepository.list_stock_by_material()` takes an optional `keyword`,
    applying the standard `apply_keyword_filter` against the location's
    code/name. Optional and defaulted, so `stock_movement` — which reuses
    that same repository method — is unaffected.
    **A select field's scan button must not live inside the Dropdown's own
    `trailing_icon` slot**: Flutter's hover `MouseRegion` doesn't stop at a
    nested child's bounds the way tap hit-testing does, so a scan button
    nested there shared a hover overlay with the whole field (hovering the
    button lit the Dropdown, and vice versa). `SelectForm.build()` instead
    wraps a plain, unmodified `ft.Dropdown` and a sibling `ScanInput`
    button in an `ft.Row` — independent controls, independent hover
    regions. `ScanInput.build()` also clamps its `IconButton`'s tap-target/
    ink region to its own visible bounds (a separate fix, for an oversized
    ripple), applied identically to the table search bar's clear button.
    Full investigation in CHANGE_HISTORY.md (2026-07-28).
    **Live in-browser camera scan** (issue #64, unblocked by the
    `flet==0.86.4` upgrade — issue #68): the scan button's click target
    tries a real live camera scan first via `flet_camera.Camera`
    (`flet-camera==0.86.4`, wraps Flutter's own `camera` plugin —
    Web/iOS/Android only, no desktop), falling back to the manual-entry
    dialog on any failure. On the web deployment the *browser* captures
    frames client-side via `getUserMedia`; this is not equivalent to
    reading a camera from Python (e.g. `cv2.VideoCapture`), which would
    see the *container's* camera, not the end user's.
    - **Current UI**: a full-screen, borderless `page.overlay` entry
      (not a dialog) — the camera feed fills the whole screen with
      translucent circular icon buttons floating on top: close (top-left),
      camera-switch (top-right, only when `len(cameras) > 1`), and Gallery
      (bottom-center). "Enter Manually" is deliberately absent while a
      camera is active (only appears in the no-camera/error fallback
      screens) — a working scanner doesn't need a manual-entry escape
      hatch. A 220×220 corner-bracket viewfinder with a bouncing scan-line
      overlays the preview.
    - **Decode path** reuses the same `pyzbar`-based `decode_image_bytes()`
      the gallery-photo path uses (camera frames arrive as ready-to-decode
      JPEG bytes via `CameraImageEvent.bytes`), throttled to one decode
      attempt per `_STREAM_DECODE_INTERVAL_S` (0.4s) rather than every
      streamed frame. Decoded payloads are `.rstrip("\r\n")`'d (some
      barcode symbologies embed a trailing CR/LF).
    - The scan-line animation is driven off `ft.Container.on_animation_end`
      (a real client-confirmed Flutter event), not a Python-side
      `asyncio.sleep` loop — an earlier sleep-based version desynced from
      the client's actual transition timing under event-loop jitter,
      reading as stutter.
    - Camera permission is requested best-effort via
      `flet-permission-handler==0.86.4` before `initialize()` (skipped on
      `page.web`, where the browser's own prompt covers it).
    - **Not verified on a real device/camera** in this environment — no
      phone or webcam was available; verification so far is limited to
      clean imports/container health checks. Full development history
      (including a small-dialog version superseded by the current
      full-screen design) is in CHANGE_HISTORY.md (2026-07-28/29/30).
  - **`icon_picker`** (`components/form/icon_picker.py::IconPickerForm`,
    2026-07-27 — a sample consumer of issue #45's `"radio"`/by-column
    column type, not itself a filed issue): same read-only-tap-to-open
    shape as `date`/`DateForm` — a read-only `ft.TextField` whose leading
    icon redraws from the field's current text value (a stored Material
    icon name, e.g. `"chevron_right"`; blank falls back to the field's own
    `"icon"` styling key as a default), tapping it opens
    `components/modal/icon_selector.py::IconSelectorModal`. Special-cased
    in `Form.load()`/`serialize()` via `Form.icon_picker` (same pattern as
    `Form.date`). First (and so far only) consumer:
    `pages/modules/ap_module/{new,edit}.py`'s `"icon"` field (a module's
    home-tile icon), changed from a plain typed `"input"`.
    `IconSelectorModal` is a reusable `ft.AlertDialog` around a plain
    `Table` — its `"picked"` column is `"type": "radio"` (default/
    by-column mode: exactly one row selectable), listing a small static
    ~80-icon catalog with no backend endpoint (`is_inside_form=True`, same
    "static local list, no fetch" precedent as `stock_out/item_new.py`).
    Confirm reads the checked row back via `Table.get_rows_with_input_values()`;
    Close discards. Not coupled to `icon_picker.py` specifically — any
    future caller wanting "pick one icon from a small catalog" can
    construct it directly. Needed a matching new read-only cell format,
    `"format": "icon"` (`components/table/rows.py`), rendering an actual
    `ft.Icon` glyph instead of text — this is the picker table's own
    preview column.
    **Two real bugs found live (not caught by object-construction-only
    testing) and fixed**:
    (1) `ft.Icon(icon=<raw string>)` — e.g. `"category"`, straight from
    the stored field value — constructs fine in Python but fails to paint
    on the Flutter client, rendering as a solid gray box (Flutter's
    error-widget background) that also blows out its column's layout.
    `utils/icon.py::get_icon()` is this codebase's existing, already-proven
    fix for exactly this (see `components/home/module_card.py`'s own
    module-tile icons) — resolves a name to a real `ft.Icons` member via
    `getattr`, falling back to `ft.Icons.APPS` for anything unrecognized.
    Both new icon-rendering sites (`icon_picker.py`'s leading icon,
    `rows.py`'s `"format": "icon"` cells) route every stored value through
    it before it ever reaches an `ft.Icon`.
    (2) `components/table/columns.py::get_usable_width()` sizes columns
    off the *page's* own width (`page.width`, read directly), not any
    actual container width — a plain `Table` embedded in a small
    `ft.AlertDialog` computed columns thousands of pixels wide, rendering
    all row content far outside the dialog's small visible/clipped area
    (an apparently-empty table). Fixed by setting
    `self.table.columns.widths`/`manually_resized = True` before
    `Table.build()` — reusing the column-resize feature's own existing
    "keep these widths, don't recompute" escape hatch (built for the
    user's manual drag-resize) for a new purpose: giving a dialog-embedded
    table small, fixed, known-to-fit widths instead of letting it size
    itself against the whole page.
    Verified live end-to-end in the browser: the picker shows the full
    catalog with correct preview glyphs, exclusivity/Confirm/Close all
    behave correctly. Full detail in CHANGE_HISTORY.md (2026-07-27).
  - **Standalone form fields' fill/border styling (issue #53) was later
    superseded by issue #79** — #53 gave every field a constant
    `SURFACE_CONTAINER_HIGHEST` filled, borderless (then underlined)
    look; #79 (2026-08-03) reverted standalone form fields
    (`input`/`select`/`date`/`label`/`icon_picker`) to unfilled/outlined
    (`filled=False`, `border=OUTLINE`, `FIELD_BORDER_RADIUS`) — see that
    entry below for the current design. Full #53 investigation (spec
    corrections, square-vs-rounded corners, `focused_bgcolor` unreliability)
    is in CHANGE_HISTORY.md (2026-07-28).
  - **Table's editable cells (`components/table/rows.py`) keep #53's
    filled, borderless, flush-to-cell design** — not reverted by #79,
    since a dense table cell has no floating label to recolor on focus,
    so a visible fill is the only indication of which cell is editable.
    `_build_editable_cell()`'s `input`/`textarea`/`select`/`option`/
    `datepicker` cells all render with `border=ft.InputBorder.NONE`,
    `content_padding=ft.Padding.all(0)`, and a constant
    `bgcolor`/`fill_color=SURFACE_CONTAINER_HIGHEST` — a Google-Sheets-style
    seamless grid, not a form-field-looking box floating inside the cell.
    `TableRows._build_flush_textfield()` is the `input`/`textarea` helper:
    Flutter's `InputDecorator` reserves an intrinsic minimum height/inset
    for a *filled* decoration regardless of `content_padding`, so the fill
    color lives on a plain wrapping `ft.Container` instead (which
    genuinely fills its exact given bounds) around a `TextField` with
    `collapsed=True` **plus** explicit `border=NONE`/`filled=False`/
    `content_padding=Padding.all(0)` (Flet's `collapsed` alone doesn't
    reliably suppress every decoration property in this Flet version).
    `select`/`option` cells carry `fill_color` directly on the Dropdown
    (no wrapping wrapper needed once the fill stopped needing to swap).
    The `datepicker` cell builds via the shared `DateForm` (which keeps
    its own border for standalone form use) and overrides `border`/
    `content_padding`/`bgcolor`/`color` afterward to match every other
    cell's flush look. Full investigation (several intermediate attempts
    before landing on this) is in CHANGE_HISTORY.md (2026-07-28).
  - **Select filtering uses Flutter's native `enable_filter`, not a
    server-driven cap** (issue #26, 2026-07-17 — final design, after three
    failed attempts at a hard "cap to 5 + show more" list). Both `SelectForm`
    (form select fields) and `TableRows._build_editable_cell()`'s
    `"select"`/`"option"` editable table cells set `enable_filter=True` (the
    field's own `"enable_filter"` config, default `True`) straight through
    to `ft.Dropdown`, with the *full* option list always assigned — Flutter
    filters entirely client-side (case-insensitive substring match against
    each option's full `text`, i.e. its `"CODE - Name"` label, so it matches
    code or name, anywhere in the string, with zero server round-trip) and
    is the only thing driving what's shown while typing. A large
    master-data-backed select (materials, locations, ...) is instead kept
    from dumping its whole list open at once via `menu_height=
    _MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT` (5 rows worth, defined in both
    `components/form/select.py` and `components/table/rows.py`) — the menu
    stays scrollable for the rest, no hard cut-off. `editable` follows
    `enable_filter` (a non-filterable field, e.g. a locked-down static
    picker, isn't typable either).
  - **Why not a hard cap with a "Show more..." indicator**: the original
    #26 design rebuilt `Dropdown.options` (capped to 5 + a trailing disabled
    entry) on every `on_text_change` keystroke via a since-deleted
    `utils/dropdown_filter.py` helper. This reliably broke Flutter's
    `DropdownMenu` focus, through two rounds of fixes that both failed:
    (1) an `async def on_text_change` awaiting `control.focus()` right
    after `control.update()` — insufficient because `Control.update()`
    (`base_control.py`) only queues a `PATCH_CONTROL` websocket message and
    returns immediately, it does not wait for the client to actually apply
    the patch and rebuild the widget (Flutter defers that to its next
    frame), so the `focus()` call could reach the client before the rebuild
    happened, targeting a `FocusNode` about to be discarded; (2) adding a
    keystroke debounce plus a short settle delay before refocusing — this
    measurably reduced the problem in an isolated `asyncio` simulation, but
    the user still hit the field losing focus (and typing appearing to stop
    working entirely) on the very first character in real use. Any design
    that reassigns `Dropdown.options` from Python in response to typing is
    fighting Flutter's `DropdownMenu` widget lifecycle across a network
    round-trip and keeps finding new ways to break — Flutter's own
    `enable_filter` has none of these problems because it never leaves the
    client. If a hard "cap to N + show more" *option list* (not just a
    scroll-bounded menu height) is ever revisited, it needs to happen
    without touching `options` while the field has focus and text is being
    typed — e.g. only re-capping on blur/selection, never on
    `on_text_change` — or it will very likely reintroduce this exact bug.
  - **First-pick-via-text-region issue, resolved** (issue #71): opening a
    select field by tapping its text-input region (not the trailing
    arrow) and picking the very first option used to leave the field
    empty until a second pick. Root cause (found only after an extensive,
    multi-round investigation — several plausible-looking fixes each
    failed live retesting before the real cause was isolated): `editable=
    True` (needed for issue #26's type-to-filter) plus Flet's own default
    `enable_search=True` both request focus/highlight on open, and the
    first tap on an option was being consumed resolving that contention
    instead of registering as a selection. Fixed by passing
    `enable_search=False` at both Dropdown construction sites
    (`components/form/select.py`, `components/table/rows.py`) and by
    deleting `SelectForm`'s `_on_focus`/`_on_blur` handlers (which were
    separately pushing a control patch mid-open, dropping the pending
    tap). Confirmed working live with real physical clicks. Full
    round-by-round investigation (including a red herring where `podman
    logs -f` without `--since` replayed stale log output, masking the
    real cause for several attempts) is in CHANGE_HISTORY.md
    (2026-07-29/30, 2026-08-03).
  - `components/search_bar.py::SearchBar` (issue #63) — a shared search
    box, same root-level `components/` extraction precedent as
    `components/button.py::Button` (#21, immediately below). Replaces the
    two near-identical `components/table/search_bar.py::TableSearchBar`/
    `components/list/search_bar.py::ListSearchBar` (both deleted), which
    had drifted to ~90% duplicate `ft.TextField` construction except that
    only `TableSearchBar` had opt-in QR/barcode scan support (issue #52).
    `SearchBar(page, parent, hint_text="Search...", on_filter_change=None,
    on_submit=None, initial_value="", qr=True)` takes `hint_text` as a
    constructor parameter instead of a hardcoded string (`Table.__init__`
    passes `"Search in table..."`, `List.__init__` passes `"Search in
    list..."`, preserving each component's exact prior wording) — every
    other behavior (styling, `storage.table_search` persistence, QR scan
    via `components/scan_input.py::ScanInput`) is unchanged from
    `TableSearchBar`'s implementation, which was the more complete of the
    two. **QR scan is ON by default for every search bar** — `SearchBar`'s
    own `qr` param defaults to `True`, and both `Table.__init__`/
    `List.__init__` thread their own `qr: bool = True` param straight
    through, so every existing Table/List screen picked this up
    automatically with no per-screen changes needed; pass `qr=False`
    explicitly to opt a specific screen out. Verified live in the browser
    on both a Table and a List screen.
  - **Compact 32dp/24px sizing reverted to M3's 48dp minimum touch target
    app-wide (issue #76, 2026-08-03)**: every compact-sizing decision
    documented below this point (`Button`'s `size=32, radius=16`
    toolbar/footer buttons from issue #21, the hamburger `PopupMenuButton`s
    in `components/table/menu.py`/`components/list/menu.py`/
    `components/form/menu.py` sized to match, `SearchBar`'s hard-locked
    32dp field height from issue #63, and `InputForm`/`SelectForm`'s 24px
    scan buttons from issue #52) was found too small for comfortable
    real-device touch interaction (user-confirmed live on a real
    iPad/iPhone via issue #75's nginx LAN access) even though it read fine
    on a desktop mouse-driven UI. Rather than a platform-conditional
    sizing scheme (compact on desktop, standard on touch), every one of
    these was reverted to a single, constant M3-standard ~48dp size
    app-wide - simpler and lower-risk than detecting touch vs. mouse
    input, and 48dp is itself a valid M3 size on desktop too, just less
    dense. New shared constants: `components/button.py::TOUCH_TARGET_SIZE`
    (48) / `TOUCH_TARGET_RADIUS` (24), `components/table/toolbar.py::
    TOOLBAR_HEIGHT` (64, `TOUCH_TARGET_SIZE + 16` vertical padding -
    `ModuleToolbar`/`ListToolbar` both import and reuse it instead of each
    hardcoding their own bar height), `components/form/input.py::
    FIELD_HEIGHT` (48, explicitly set on both `InputForm`'s `TextField`
    and `SelectForm`'s `Dropdown` - fixes the separately-reported "select
    and input render at different heights" finding, since neither control
    had an explicit `height` before and their intrinsic decoration heights
    quietly diverged). `SearchBar`'s field height went from a hard-locked
    32 to 48, its clear/scan buttons from 24px to 40px. Table/List
    editable-cell density (`components/table/rows.py`, the dense
    Excel-style grid from issues #43/#44/#53) was deliberately left
    unchanged - that's a distinct, already-reviewed density decision (row
    heights 36-44px) serving a different, already-dense desktop-table
    context, not named in scope for this pass, and reopening it would mean
    revisiting the whole table-density history rather than the
    button/search/form-field sizing this issue actually reported. Verified
    via direct Python import of every touched module (no syntax/circular-
    import errors); a full containerized rebuild+click-through was
    **not** completed this session — blocked by an unrelated, pre-existing
    Podman/Docker-Desktop registry config conflict on this dev machine
    (`toml: line 4 ... expected '.' or '=' `, from
    `/etc/containers/registries.conf.d/999-podman-desktop-registries-from-host.conf`),
    not something this change touched. Next step before closing #76: get a
    working container build (or run `flet run` directly) and click through
    on a real mobile device per the issue's own acceptance criteria.
  - `components/button.py::Button` (issue #21) — a shared Material 3
    button builder factoring out what used to be three near-identical
    inline `ft.IconButton(...)` constructions in `components/list/toolbar.py`,
    `components/module/toolbar.py`, and `components/table/toolbar.py`'s own
    `add_button` methods. `Button(icon, on_click, tooltip="", label=None,
    icon_color=None, bgcolor=None, size=None, radius=None,
    padding=0).build()` returns a plain Flet-default `ft.IconButton` when
    `size` is left `None` (matches `ListToolbar`'s bare buttons), or a
    compact pill-shaped `ft.IconButton` (fixed `height`/`width=size`,
    `ft.RoundedRectangleBorder(radius=radius or size/2)`) when `size` is
    set (matches `ModuleToolbar`'s/`TableToolbar`'s existing 32dp/16-radius
    buttons); passing `label` instead renders an `ft.FilledButton`
    (icon + text) for a future non-icon-only use case. **Each toolbar keeps
    its own default-color-resolution logic** — only the final
    `ft.IconButton`/`ft.FilledButton` construction moved into `Button`.
    `add_button`/`add_new_button`/`add_save_button`/`add_submit_button` on
    all three toolbars still own callback wiring, default icon/tooltip,
    and left/right positioning — `Button` only builds the control, it has
    no opinion on toolbar placement.
  - **`TableToolbar` renders standard (not filled) Material 3 icon
    buttons**: `add_button`'s original defaults resolved every button's
    `bgcolor` to a forced fallback (`ON_SURFACE` — i.e. a permanently
    filled near-black pill) instead of ever leaving it unset, so every
    table toolbar button (add-new, save, and the filter-row toggle) looked
    like an always-on filled/tonal button rather than Material 3's
    "standard" icon-button variant (transparent background, icon only,
    Flutter's own hover/pressed state-layer highlight appearing only on
    interaction). Fixed by leaving `bgcolor=None` through to `Button`
    unless a caller explicitly passes one (the rare filled/tonal case);
    `ft.ButtonStyle(bgcolor=None, ...)` is exactly what Flutter's own
    standard `IconButton` variant renders (null background, automatic
    state-layer hover), so no extra `overlay_color` wiring was needed.
    Default `icon_color` also changed from the near-white
    `SURFACE_CONTAINER_HIGH` (only legible against that forced dark fill)
    to `ON_SURFACE_VARIANT`, matching M3's own standard-icon-button
    default foreground and staying legible against the toolbar's
    `SURFACE_CONTAINER_LOW` bar background now that there's no fill behind
    it. `TableToolbar.add_filter_button(callback, icon=FILTER_LIST,
    tooltip="Toggle Filters", ...)` was added alongside `add_new_button`/
    `add_save_button` so `Table.__init__`'s filter-row-toggle button (only
    shown when `self.filter_row.has_filters()`) is a one-line call instead
    of a direct `add_button(position="left", icon=..., tooltip=...)` call
    — the third of the toolbar's "3 different-looking buttons" the fix
    addressed, now sharing the same standard-variant styling as the other
    two.
  - **`ModuleToolbar` had the identical bug**, found on a follow-up check
    after the `TableToolbar` fix above, in a slightly different shape: its
    `add_button`'s default *parameter* was `bgcolor=ft.Colors.PRIMARY`
    (not `None`), so a bare `add_button(...)` call with no `bgcolor`
    argument at all (`purchase_report/index.py`/`usage_report/index.py`'s
    "Apply Filters" button) rendered a solid, visibly-colored filled pill.
    `add_new_button`/`add_submit_button` (used across ~40 module screens)
    separately passed `bgcolor=None` explicitly, which the body's
    `btn_bg = bgcolor if bgcolor else SURFACE_CONTAINER_HIGH` fallback
    resolved to `SURFACE_CONTAINER_HIGH` — the *exact same color* as
    `ModuleToolbar`'s own bar background, so those buttons happened to
    look transparent by coincidence, not by design (fragile: would break
    the moment the bar's bgcolor ever changed independently). Fixed the
    same way as `TableToolbar`: default `bgcolor=None` (both the
    parameter default and the fallback removed) and default
    `icon_color=ON_SURFACE_VARIANT`. The 7 delete buttons across
    `master_location/edit.py`, `ap_module/edit.py`, `ap_master_user/edit.py`,
    `master_category/edit.py`, `master_department/edit.py`,
    `master_module_group/edit.py`, `master_supplier/edit.py` all pass
    `bgcolor=ft.Colors.ERROR`/`icon_color=ft.Colors.ON_ERROR` explicitly
    and are unaffected — that's the toolbar's one legitimate filled/tonal
    (danger) button. Verified by constructing `ModuleToolbar` directly:
    every non-danger button now correctly resolves `bgcolor=None`/
    `ON_SURFACE_VARIANT`, the delete button is unaffected. Full detail in
    CHANGE_HISTORY.md (2026-07-28).
  - `components/table/menu.py::TableMenu`'s hamburger `ft.PopupMenuButton` is
    now explicitly sized to the same compact metrics as `Button`'s 32dp
    buttons (`height=32, width=32, padding=0,
    style=ButtonStyle(shape=RoundedRectangleBorder(radius=16))`,
    `icon_size=20`, `icon_color=ON_SURFACE_VARIANT`) — its own defaults
    (an ~48dp target with 8px padding) didn't fit the 48dp toolbar bar's
    32px content height (after the bar's own 8px vertical padding), so it
    rendered low/off-center next to the compact `Button`-built siblings in
    the same `ft.Row`. `PopupMenuButton` isn't built through `Button`
    itself (it's a different Flet control type with no `Button`
    equivalent), so these numbers are duplicated by hand here — keep them
    in sync with `Button`'s `size=32, radius=16` if that ever changes.

- **`components/list/` reaches feature parity with `components/table/`**
  (issue #55) via the app's same backend contract, no backend changes —
  `List` is a card/tile view (`ft.ListTile` per record, positional
  `leading`/`title`/`subtitle`/`trailing` fields via `Layout`), so it
  needed its own UI affordances rather than a literal port of `Table`'s
  header-row mechanics:
  - **Pagination-mode footer**: `List` reuses `components/table/footer.py
    ::TableFooter` unmodified — it only duck-types on `parent`'s
    `total_rows`/`total_pages`/`page_number`/`limit`/`data` attributes and
    three `_handle_footer_{mode,page,limit}_change` callbacks, which
    `List` already carried before this issue.
  - **Per-field search + real multi-column sort**:
    `components/list/filter.py::ListFilter` is an expandable panel (a
    card has no columns to hang a per-column header row on), toggled via
    `ListToolbar.add_filter_button`. Opt-in via `"filter": True`/
    `"sort": True` per field — the reverse of `TableFilter`'s
    opt-out-by-default, since `List`'s `fields` are already a curated
    subset for specific card slots. Each sortable field gets its own
    cycling icon button (none → ASC → DESC → none), and `ListFilter.
    sort_order` is a real ordered list — true multi-column sort, same as
    `Table`, with an identical wire format (`{field}-filter`,
    `sort-fields[N][field]`) so the backend needs no changes.
  - `stock_in/index` is `List`'s real first consumer (`date`/
    `description`/`supplier_name` as leading/title/subtitle, row click to
    `edit/<id>`) — wiring it up surfaced a latent gap (List/Tiles never
    applied a field's `"format"`, e.g. `"date"`, the way Table's cells
    do), fixed by threading `"format"` through `Layout` and reusing the
    same `_FORMATTERS` dispatch.
  - **Download menu, full-width search bar, Table/List view toggle**
    (issue #56): `components/list/menu.py::ListMenu` gives List the same
    6 download formats as `TableMenu` (upload deliberately out of scope —
    List's tiles are read-only). `components/list/search_bar.py::
    ListSearchBar` was rebuilt on a plain `ft.TextField` (mirroring
    `TableSearchBar`'s issue #19 fix — Flutter's own `ft.SearchBar` won't
    genuinely expand to fill a toolbar row). `components/module/
    view_toggle.py::ViewToggle` lets one screen pass the same `fields`
    list to either `List` or `Table` (each component only reads the keys
    it understands) and toggle between them — only the active view is
    built up front, the other lazily on first switch; free-text search
    persists across a switch (shared `storage.table_search` key), sort
    order/pagination position do not (each is per-instance state, by
    design). Wired onto `stock_in/index.py`.
  - **`ListToolbar` container styling matched to `TableToolbar`** (issue
    #62) — copied `TableToolbar.build()`'s container properties (fixed
    height, low-emphasis `SURFACE_CONTAINER_LOW` bar, standard M3 icon
    color) onto `ListToolbar`, plus matching button `size`/`radius` and
    `List.build()`'s default outer padding to `Table`'s.
  - **Zebra-striped tiles + icon-instead-of-label fields** (issue #65):
    a field can set `"icon"` instead of (or alongside) `"label"` — this
    capability already existed in `components/list/layout.py` but had
    never been exercised until `stock_in/index.py`'s `"date"` field
    adopted it. Tiles alternate background color the same way Table rows
    do (issue #57's `_ROW_COLOR_EVEN`/`_ODD` tokens). A field's `"label"`
    renders as a hover tooltip on the tile's value text, not a second
    visible caption line (a later same-day refinement). Two real,
    previously-latent bugs were found and fixed along the way:
    `ft.ListTile.bgcolor` does nothing in this Flet build (tiles are now
    wrapped in a plain `ft.Container(bgcolor=...)` instead), and the
    zebra position counter was originally shadowed by an unrelated loop
    variable also named `row` (renamed to `tile_index`). A related Table
    bug was also found and fixed: `TableColumns._build_data_columns()`
    rendered a raw `"icon"` header value without wrapping it in
    `ft.Icon(...)`, leaving the header blank; the fix needed its own
    `interactive`-only gate to avoid the icon bleeding into the first
    data row (same bug class as issue #38's sort-icon bleed).
  Full development narrative for #55/#56/#62/#65 (verification detail,
  intermediate design attempts, exact bug traces) is in CHANGE_HISTORY.md
  (2026-07-28).

- **Repositories / state & persistence** (`src/repository/`): each repo
  wraps `page.data` (in-memory cache) plus an optional persistence `store`.
  - Persistent (loaded once at boot via `Storage.load_persistent()`):
    `server_url.py` (`ServerURL`, key `"server_url"`, default
    `DEFAULT_SERVER_URL` — read from the `FRONTEND_DEFAULT_SERVER_URL` env
    var (issue #15, see `compose.yml`'s `frontend` service/`example.env`),
    falling back to `"http://backend:5000"` (the compose network address)
    if unset, so the containerized frontend works out of the box without a
    manual Server Config step; see the container networking gotcha below),
    `http_cookies.py`, `user_session.py`, `theme_mode.py`.
  - Non-persistent (in-memory, cleared on route change): `client_data.py`,
    `module_history.py`, `home_search.py`, `table_search.py`.
  - `storage.py` (`Storage`) is the facade aggregating all repos. Backend
    picked by `utils/persistence.py::make_session_store()`, one of three:
    - **Native** (desktop/Android/iOS) → `_NativeFileStore`, one JSON file
      outside the source tree (single-install, no concurrent-user concern).
    - **Web via `asgi.py`** (the containerized deployment - see below) →
      `_ServerFileStore`, one JSON file per browser, keyed by a `client_id`
      cookie `asgi.py` bridges into `page.data`.
    - **Web via the plain `flet run --web` CLI** (local dev, no cookie
      bridge) → `ft.SharedPreferences` with retry logic
      (`utils/storage_compat.py`), for a known async mount race that in
      practice (see `frontend/src/storage/data/sfsis.log`) fails routinely,
      not just on cold start - this is why the container deployment
      doesn't use it.
  - **`src/asgi.py`**: the containerized deployment's real entrypoint
    (`entrypoint.sh` runs `uvicorn asgi:app`, not `flet run --web`
    directly). Builds Flet's own FastAPI ASGI app via
    `ft.run(..., export_asgi_app=True)` - the exact one the CLI's `--web`
    flag uses internally - and wraps it in `ClientIdMiddleware`, bare ASGI
    middleware (not Starlette's `BaseHTTPMiddleware`, which doesn't cover
    websocket scopes) that reads/sets a durable `client_id` cookie (plain
    `Set-Cookie` on the first HTTP response, no JS round trip to race —
    and, since 2026-07-14, also on the `websocket.accept` handshake
    response when the WS arrived cookieless: a stale tab from before the
    cookie existed auto-reconnects its WS after a container restart
    *without* any page load, and without binding the freshly-minted id
    back into the browser there, a login made in that tab persists into a
    session file no future tab can ever reach) and
    exposes it via a `ContextVar` (`utils/client_context.py`) for the rest
    of that connection's call chain. Flet's `before_main(page)` hook - which
    runs in that same call chain, before any `asyncio.create_task` split
    (see `flet_web.fastapi.flet_app.FletApp`'s `REGISTER_CLIENT` handling)
    - reads that `ContextVar` and stashes the id in `page.data["client_id"]`
    before `main(page)` ever runs, which is what `make_session_store()`
    above keys `_ServerFileStore` off. `main.py`'s own `ft.run(main)` call
    is guarded behind `if __name__ == "__main__":` specifically so
    `asgi.py`'s `from main import main` doesn't also launch a second,
    competing Flet server. Also requires `FLET_APP_STORAGE_DATA`/
    `_TEMP` to be set manually in `entrypoint.sh` (`<script dir>/storage/
    data` / `.../temp`, matching what the CLI would have set itself) since
    `utils/app_logger.py` reads those and nothing else provides them
    outside the CLI. **Not yet verified against a live multi-browser/
    restart test** - before trusting it, confirm: (1) log in, `podman
    compose restart frontend`, reload the page, still logged in; (2) log in
    from two different browsers/profiles at once, confirm neither gets
    logged out or sees the other's session; (3) `sfsis_client_id` cookie is
    actually being set (browser devtools) and a matching file appears under
    the container's `storage/data/sessions/`. Rollback if something
    regresses: revert `entrypoint.sh`'s `CMD`-adjacent line back to
    `uv run flet run --web --host ... --port ... src/main.py`.

- **Networking / server address handling** (`src/utils/http_client.py`):
  `HttpClient(page, verify=False)` builds a `requests.Session()`, reading
  `base_url = ServerURL(page).get()` and cookies from `HttpCookies(page)` at
  construction time — i.e. it always uses whatever address the user last
  saved on the Server Config page. Flow: user opens `/server_config` →
  types the backend URL into `components/server_config/body.py` →
  `storage.server_url.set(...)` persists it → every subsequent
  `HttpClient` instance reads that value as `base_url` and hits
  `{base_url}/{endpoint}`. Auth is cookie/session-based (redirects are
  treated as "auth required/session expired"); `UserSession.token` exists
  for a token if the backend later issues one. TLS verification is off by
  default (dev-friendly self-signed certs).
  - **Container networking gotcha**: `sfsis-frontend` runs Flet as a *server*
    (its Python process, not the browser, executes every `HttpClient` call —
    confirmed by request logs being prefixed `sfsis-frontend |`, i.e. they
    print inside that container). So when the frontend is the containerized
    web app from `compose.yml`, the Server Config address must be
    `http://backend:5000` or `https://backend:5443` — the backend service's
    *compose network name* — never `localhost`, which inside that container
    resolves to the frontend container itself (connection refused). Plain
    `http://localhost:5000` / `https://localhost:5443` only work for a
    client connecting from the Windows host directly (e.g. a native desktop
    Flet build, or `curl` from the host) — those aren't equivalent addresses.
    `DEFAULT_SERVER_URL` defaults to `http://backend:5000` (overridable via
    `FRONTEND_DEFAULT_SERVER_URL` in `.env`/`compose.yml` — issue #15, e.g.
    for a deployment where the backend isn't reachable at that compose
    network name) specifically so a fresh containerized frontend gets this
    right automatically, without anyone having to rediscover the gotcha
    above via the Server Config page. It is deliberately **not** used as a
    "never configured" sentinel
    anymore — `ServerURL.is_configured()` tracks that explicitly, because a
    containerized user's genuinely-saved address equals the default and the
    old value comparison couldn't tell the two apart (see Boot logic above).

- **Module loading** (`src/utils/module_loader.py`): `ModuleLoader(page,
  target)` (`target` is `"modules"` or `"modals"`) preloads every screen
  under `pages/<target>/*/*.py`, caches them, and dynamically imports/builds
  the `ModulePage`/`ModalPage` class matching a parsed route.

- **Theming** (`src/themes/`): `light_theme.py` / `dark_theme.py` expose
  `ft.Theme`s; `repository/theme_mode.py` applies `page.theme_mode`
  (LIGHT/DARK/SYSTEM) from the persisted preference.