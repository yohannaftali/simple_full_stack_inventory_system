
# CHANGE_HISTORY.md

## [2026-07-08] — feat(infra): scaffold full-stack app with MariaDB, FastAPI, and Flet via Podman Compose
- Issue #1 created on GitHub
- Scope: infra
- Labels: enhancement, infra

## [2026-07-08] — validated issue #1 acceptance criteria
- All acceptance criteria for #1 were already satisfied by the prior scaffolding work (AGENTS.md docs, compose.yml, three Dockerfiles, existing manual server-address entry)
- Validated by building all three images with `podman build` and running the full stack with `podman compose -f compose.yml up -d`: mariadb started, backend responded `{"status":"ok"}` on `/`, frontend served the Flet web shell (HTTP 200) on `/`
- No source changes were needed; status set to ready-for-review pending user confirmation to close #1

## [2026-07-09] — feat(backend): add users table, UserRepository, and Alembic migrations
- Added SQLAlchemy `Base`/`engine`/`SessionLocal` (`backend/src/models/base.py`) and `UserModel` (`backend/src/models/user.py`, table `users`)
- Added `UserRepository` (`backend/src/repository/user_repository.py`) with CRUD, status, and password-management methods
- Added `backend/src/core/config.py` (DB URL from env) and `backend/src/core/security.py` (bcrypt password hashing helpers, not yet wired into any endpoint)
- Added Alembic setup (`backend/alembic.ini`, `backend/alembic/env.py`, initial migration `0001_create_users_table.py`)
- Added `sqlalchemy`, `alembic`, `pymysql`, `bcrypt` to `backend/requirements.txt`; set `PYTHONPATH=/usr/src/app/src` and copied `alembic.ini`/`alembic/` in `Dockerfile-backend`
- Scope: backend
- No GitHub issue filed for this change (user opted to implement directly rather than track via the planner skill)

## [2026-07-09] — feat(backend): login endpoint with cookie session, ported from legacy PHP auth
- Added `totp_secret` column to `UserModel` + migration `0002_add_totp_secret_to_users.py`
- Ported the legacy PHP pre-auth token scheme (`sha1(md5(ip+user+HHmm+ip+secret))`, 2-min window) to `backend/src/core/session_token.py`
- Ported the legacy PHP `L_totp` library (RFC 6238, SHA1, 6 digits, 30s step, ±1 drift) to `backend/src/core/totp.py` — `generate_secret`, `get_totp_uri`, `verify`; QR image rendering intentionally not ported since the frontend renders its own QR from the URI
- Added `backend/src/services/auth_service.py` (`authenticate`: active check, bcrypt password verify, TOTP verify)
- Added `backend/src/routers/login.py`: `GET C_login/get_session`, `POST C_login/login` — matches the exact contract read from `frontend/src/components/login/body.py` and `utils/http_client.py` (form-encoded POST, empty-body 200 on success, 401 on failure, no redirects)
- Wired Starlette `SessionMiddleware` (signed `session` cookie, `secret_key=JWT_SECRET`) into `backend/src/main.py`
- Added `itsdangerous`, `python-multipart` to `backend/requirements.txt`
- Verified end-to-end with a `TestClient` smoke test (sqlite in-memory DB): get_session → wrong password (401) → correct login (200, empty body, `session` cookie set) → stale token (401) — all passed
- Scope: backend
- Not yet implemented: `C_home/home` and the `C_home/call_generate_totp` / `C_home/call_change_totp` TOTP-enrollment endpoints the frontend also expects post-login
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat(backend): C_home/home and TOTP-enrollment endpoints
- Added `services.auth_service.get_current_user` FastAPI dependency (reads `request.session["username"]`, 401s if missing/inactive)
- Added `UserRepository.update_user_totp_secret`
- Added `backend/src/routers/home.py` (`C_home` prefix, all routes session-gated): `GET C_home/home` → `{"username", "modules": [], "title", "footer"}`; `GET C_home/call_generate_totp` → `{"secret": "..."}`; `POST C_home/call_change_totp` (form: secret, totp) → verifies + persists the secret, `{"success"|"error": "..."}`
- Wired `home_router` into `backend/src/main.py`
- Verified end-to-end with a `TestClient` smoke test: unauthenticated `C_home/home` → 401; login → home (200, modules `[]`) → generate secret → save with wrong code (200, `error`) → save with correct code (200, `success`) → re-login without TOTP now fails (401) → re-login with correct TOTP succeeds (200) — all passed
- Scope: backend
- Not yet implemented: the module/permission system (`modules` list is always empty; the generic `GET C_{module}` permission-check endpoint the frontend's `has_permission()` expects doesn't exist)
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat(backend): module + user-module-permission tables, wired into home and permission-check endpoints
- Added `ModuleModel` (`modules` table) and `UserModulePermissionModel` (`user_module_permissions` table), adopted from the user's legacy PHP `ap_module`/`ap_auth` schema, + migration `0003_create_modules_and_permissions.py`
- Added `ModuleRepository` (`get_module_by_name`, `get_all_modules`) and `UserModulePermissionRepository` (`has_access`, `get_modules_for_user`, `grant_access`, `revoke_access`)
- `GET C_home/home` now returns the user's actually-granted modules (`{"name", "label", "module_icon", "module_description"}` per module, field names matched to `frontend/src/components/home/module_card.py`), ordered by `ModuleModel.sort`, instead of an empty list
- Added `backend/src/routers/module.py`: `GET C_{module_name}` → `{"secure": {"access": bool}}`, session-gated, matching `ClientData.has_permission()`; unknown module names return `access: False` rather than 404
- Wired `module_router` into `backend/src/main.py`
- Verified end-to-end with a `TestClient` smoke test: seeded two modules and granted one user access to only one; home listing matched exactly; permission-check endpoint returned `True`/`False`/`False` for granted/ungranted/nonexistent modules; unauthenticated permission check → 401; revoking access flipped the check back to `False` — all passed
- Scope: backend
- Not yet implemented: any admin/HTTP surface to create modules or grant/revoke permissions — rows have to be inserted directly for now
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat: module + user admin CRUD screens, permission grant UI on master user
- Backend: extended `UserRepository` (`get_user_by_id`, `list_users`, `update_user_by_id`, `delete_user_by_id`, `check_user_exists(..., exclude_id=)`) and `ModuleRepository` (`get_module_by_id`, `list_modules`, `create_module`, `update_module`, `delete_module`)
- Backend: extended `UserModulePermissionRepository` with `get_module_ids_for_user`, `set_modules_for_user` (bulk replace), `delete_permissions_for_module`/`delete_permissions_for_user` (grants have no `ON DELETE CASCADE`, so routers clear them before deleting the module/user)
- Backend: added `auth_service.require_module_access(module_name)` dependency factory — 401 if not logged in, 403 if not granted access to that module; superusers bypass the grant check (bootstrap escape hatch, does not affect `C_home/home`'s listing)
- Backend: added `routers/module_admin.py` (`C_ap_module` prefix) and `routers/user_admin.py` (`C_ap_master_user` prefix) implementing the generic list/get/submit/delete contract read from `components/table/table.py` and `components/form/form.py`, plus `get_all_modules`/`get_permissions`/`save_permissions` for the permission checklist; both wired into `main.py`
- Frontend: added `pages/modules/ap_module/{index,new,edit}.py` (module CRUD, follows the `ap_config` pattern exactly)
- Frontend: rebuilt `pages/modules/ap_master_user/index.py` (was a copy-pasted placeholder scaffold) into a real user list; added `new.py`, `edit.py`; added `permission_checklist.py` (a `Checkbox` list embedded in `edit.py`, backed by `get_all_modules`/`get_permissions`/`save_permissions`) — this is the "grant module by user" UI
- Both `ap_module/edit.py` and `ap_master_user/edit.py` add a manual delete button (`ModuleToolbar.add_button`) since the generic `Table`/`Form` framework has no delete affordance yet
- Verified end-to-end with a `TestClient` smoke test: non-granted user gets 403 on both admin routers; superuser creates the `ap_module`/`ap_master_user` module rows and a new user; grants that user access to one module via `save_permissions`; the granted user can then reach `C_ap_module` but still gets 403 on `C_ap_master_user`; user update with a blank password keeps the old one (verified by re-login); duplicate email on create is rejected; deleting a user/module cleans up its permission grants — all passed
- Scope: backend, frontend
- Left `frontend/src/pages/modules/ap_master_user/second_screen.py` and `third_screen.py` in place even though `index.py` no longer links to them (pre-existing files, not created this session — left for the user to remove if confirmed unwanted)
- Known gaps: no self-service first-superuser creation (insert that one row directly to bootstrap); `Table.get_data()` in the frontend framework indexes `response[0]` for pagination metadata and will error on a genuinely empty list — pre-existing frontend behavior, not touched here
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat(backend): seed default superuser via migration
- Added `backend/alembic/versions/0004_seed_default_superuser.py`: seeds `admin` / `admin1234#` as an active superuser on `alembic upgrade head`, resolving the "no self-service first-superuser creation" gap from the previous entry
- Idempotent (no-ops if a user named `admin` already exists) and reversible (`downgrade()` deletes exactly that seeded row); password is bcrypt-hashed via `core.security.hash_password` at migration time, never stored in plaintext
- Verified by running the migration's `upgrade()` directly against a real SQLite engine through `alembic.operations.Operations.context(...)` (the same mechanism the `alembic` CLI uses, without needing a live MariaDB): confirmed the row is created correctly (superuser, active, password hash verifies), re-running `upgrade()` doesn't duplicate it, a full login with the seeded credentials succeeds, the seeded account's superuser bypass lets it hit `C_ap_module` with zero grants, and `downgrade()` removes the row
- Scope: backend
- Reminder embedded in the migration source and AGENTS.md: change the default password after first login
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — chore(infra): run alembic upgrade head automatically on backend container start
- Changed `Dockerfile-backend`'s `CMD` to `alembic upgrade head && uvicorn ...`, so every container start/restart applies pending migrations before serving traffic — no manual migration step after `podman compose up`/`restart`
- Since `compose.yml`'s `depends_on` only orders container start (not DB readiness), a cold start where MariaDB isn't accepting connections yet will crash-loop until it is, self-healing via the existing `restart: always` policy — not a regression, just documented in AGENTS.md
- Scope: infra
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat(infra): serve HTTPS via self-signed cert, alongside plain HTTP
- Root cause of the user-reported "Failed to get token. Check connection." error: the Server Config page was pointed at `https://localhost:5000`, but the backend only ever served plain HTTP there — `verify=False` in `HttpClient` skips certificate validation, not the TLS handshake itself, so the connection failed outright (confirmed with `curl -k https://localhost:5000/` → SSL exit code 35)
- Added `backend/entrypoint.sh`: generates a self-signed cert (`backend/certs/{cert,key}.pem`, `CN=localhost`, 10-year expiry) on first run only (persisted via the existing bind mount, gitignored), runs `alembic upgrade head`, then starts two Uvicorn processes — plain HTTP on `UVICORN_PORT` (5000) and HTTPS on `UVICORN_PORT_SSL` (5443) — backgrounded with `wait -n` so either exiting stops the container
- `Dockerfile-backend`: installs `openssl`, copies `entrypoint.sh` to `/usr/local/bin/` (outside the bind-mounted `/usr/src/app`, so the dev volume mount doesn't hide it), exposes 5443, `CMD ["entrypoint.sh"]`
- `compose.yml`: added `UVICORN_PORT_SSL` env var and its port mapping to the `backend` service
- Added `.gitattributes` (`*.sh text eol=lf`) so the bash entrypoint doesn't get CRLF-mangled by Windows checkouts; added `backend/certs/` to `.gitignore`
- Verified for real against the running podman containers: rebuilt and recreated `sfsis-backend`; logs show cert generation (once) then both Uvicorn processes starting; `curl -k https://localhost:5443/` → 200, full login flow (`get_session` → `login`) over HTTPS with the seeded `admin` credentials → 200; plain `http://localhost:5000` still works unchanged; restarted the container again and confirmed the cert was *not* regenerated (persisted) and both servers came back up
- Scope: infra
- Frontend fix for the user: set the Server Config address to `https://<host>:5443` (or keep `http://<host>:5000` if TLS isn't needed) — no frontend code changes were required
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — docs: clarify containerized frontend must address the backend by compose service name, not localhost
- User still saw "Failed to get token. Check connection." after the HTTPS change, with `Server url: https://localhost:5000` in `sfsis-frontend` logs
- Diagnosed by exec-ing into the running `sfsis-frontend` container: `sfsis-frontend`'s Flet process (not the browser) executes every `HttpClient` request server-side (request logs are prefixed `sfsis-frontend |`, i.e. printed inside that container) — so `localhost` from there means the frontend container itself. Confirmed `https://localhost:5443` → connection refused, `https://backend:5443` → 200, `http://backend:5000` → 200 (podman's internal compose-network DNS resolves the `backend` service name)
- No code changed — this is a configuration/usage issue: the Server Config address must be `http://backend:5000` or `https://backend:5443` when using the containerized frontend web app. Documented the distinction in AGENTS.md (`localhost` only works for a client on the Windows host itself, e.g. native desktop Flet or `curl` from the host — not the containerized frontend)
- Scope: docs
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — fix(backend): add missing C_home/call_change_password endpoint (was 404)
- User reported HTTP 404 submitting the Change Password modal; `frontend/src/pages/modals/password/index.py` posts to `C_home/call_change_password` (form: `c`, `n`, `f`), which had never been implemented — only `call_generate_totp`/`call_change_totp` existed under `C_home`
- Added `POST C_home/call_change_password` to `backend/src/routers/home.py`: session-gated, verifies `n == f`, `c != n`, and `c` against the stored bcrypt hash via `core.security.verify_password`, then persists `hash_password(n)` via the existing `UserRepository.update_user_password`; returns `{"success"|"error": "..."}`, always HTTP 200 (same contract as `call_change_totp`)
- Verified end-to-end in a throwaway venv: old password stops working after change, new password logs in, mismatched confirmation and wrong-current-password are rejected with `error`, unauthenticated request gets 401 (not 404) — all passed. Also verified live against the running `sfsis-backend` container (bind-mounted source, restarted to pick up the change — no rebuild needed) with a deliberately-same-password request, confirming HTTP 200 with a validation error instead of 404, without touching the real admin password
- Noted in AGENTS.md: the `shift` and `token` modals call three more `C_home/call_*` endpoints that don't exist yet either (`call_shift_id_select`, `call_change_shift`, `call_change_token`) — same fix pattern applies if/when those come up
- Scope: backend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat: inventory system — stock in/out with moving-average costing, 5 new modules
- User's spec: 3 modules (stock in, stock browse, stock out) + master location + master material + an inventory-value table tracking each material's moving average price (MAP)
- Asked one clarifying question before building: when stock out needs to deduct a material that exists in multiple locations/lots, does the user pick the location (simpler, matches how stock in assigns location) or does the system auto-FIFO across locations? User chose user-picks-location; system then FIFOs within that location across whichever lots contributed to it
- **Schema** (migration `0005_create_inventory_tables.py`): `LocationModel`/`MaterialModel` (master data), `InventoryValueModel` (one row per material: qty + MAP), `ReceivingHeaderModel`/`ReceivingItemModel` (stock in; `location_id` was inferred onto the item — not explicit in the user's spec, but required since `stocks` needs a location per lot and nothing else supplies one), `StockModel` (one lot row per receiving item, unique on `(receiving_item_id, material_id, location_id)`), `StockOutHeaderModel`/`StockOutItemModel` (stock out; captures the material's MAP at time of issue). Also fixed a pre-existing gap: `alembic/env.py` only ever imported `models.user`, never `models.module`/`models.user_module_permission` from the earlier module/permission work — now imports every model module
- **`backend/src/services/inventory_service.py`**: owns its own `SessionLocal()` transaction (unlike every other service/repository here) since receive/issue must touch 3-4 tables atomically. MAP formula, edit-reversal semantics, and FIFO-within-location deduction are documented at length in both the module docstring and AGENTS.md — see there for the exact reasoning and known simplifications (edits to old receipts don't replay intervening stock-outs; stock-out items are immutable, no edit)
- **Repositories**: `location_repository.py`, `material_repository.py`, `inventory_value_repository.py` (read-only), `receiving_repository.py`, `stock_repository.py` (read-only aggregated browse view), `stock_out_repository.py`
- **Routers**: `master_location.py`, `master_material.py` (plain CRUD, delete blocked with a friendly error — not a 500 — if the row has transaction history via `IntegrityError` catch), `stock_browse.py` (read-only), `stock_in.py`, `stock_out.py` (header CRUD + separate item sub-endpoints: `get_items`, `submit_item`, plus `get_item` and item-update for stock_in only; `call_material_id_select`/`call_location_id_select` for the item forms). All gated by `require_module_access`
- **Frontend**: `master_location`, `master_material` (plain CRUD, same shape as `ap_module`), `stock_browse` (read-only list, deliberately no `"key"` field since there's no edit screen to navigate to), `stock_in`, `stock_out` (header `{index,new,edit}.py` plus a **new master-detail pattern**: a custom `ItemTable` widget, not the shared `Table` component, because `Table`'s row-click is hardcoded to `/modules/{module}/edit/{id}` which would collide with the header's own edit route; item screens use their own submit handlers instead of `Form.submit()`'s hardcoded index-redirect, navigating back to the header instead — full reasoning in AGENTS.md)
- Verified end-to-end in a throwaway venv against SQLite: two receipts compute the correct weighted-average MAP; editing an earlier receiving item's qty recalculates MAP via reverse-old/apply-new and matches hand-calculation; a dedicated FIFO test confirms deduction drains the oldest lot first, then partially drains the next, leaving the newest untouched, with the issue price captured as the pre-issue MAP; insufficient-stock and issue-from-empty-location are both rejected with a clear error; permission gating returns 403 for every one of the 5 new routers when ungranted
- Then verified for real against the live containers: rebuilt nothing (bind-mounted, just restarted `sfsis-backend` — migration 0005 applied cleanly), seeded the 5 module rows + granted `admin` via the same repository code the app uses, verified all 5 icon names (`place`, `category`, `call_received`, `call_made`, `inventory`) resolve to real `ft.Icons` constants inside the actual frontend venv, then walked the real HTTP flow end-to-end: create location + material → receive 50 @ price 10 (MAP=10) → browse shows qty 50/value 500 → issue 20 → browse shows qty 30/value 300, stock-out item shows captured price 10/total_value 200. Also imported all 18 new frontend files inside the real Flet venv (stronger than syntax-checking — catches import-path mistakes) — all succeeded
- Scope: backend, frontend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — fix(frontend): stock_in item table crash (`on_select_changed` typo)
- User reported "Module Not Found" clicking into a receiving header, with a `ft.DataRow.__init__() got an unexpected keyword argument 'on_select_changed'` traceback from the app's own error screen (that screen's title is a generic "Module Not Found" for *any* build failure — misleading given the actual cause, unrelated to this fix)
- `pages/modules/stock_in/item_table.py` used `on_select_changed`; the real Flet API is `on_select_change` (confirmed via `inspect.signature(ft.DataRow.__init__)` inside the actual frontend venv) — one-word fix
- Traced the "Module Not Found" report itself first by grepping `sfsis-frontend` logs for the route and finding nothing logged — that turned out to be a stale-websocket red herring from a container restart earlier in the same session; the *next* report (with the actual traceback pasted) was the real bug
- Scope: frontend

## [2026-07-09] — fix(frontend): stock_in item edit form fetched the wrong endpoint
- User asked "saat edit, ngga mengirim id?" (does it send the id on edit?) after item_edit fields came up empty on submit
- Root cause: `Form`'s default GET endpoint is `C_{module}/get`, which for `stock_in` is the *header* endpoint (`{id, date, description}`) — but `item_edit.py` needs the *item* endpoint (`get_item`, returning `{id, material_name, location_name, qty_received, price_buy, remarks}`). The form was silently populating itself from a header record instead, leaving qty/price/remarks blank; confirmed via the frontend logs showing the exact wrong payload (`{'id': 2, 'date': '2026-07-09', 'description': 'test'}`) and the resulting empty `form data`
- Fix: `item_edit.py` already fetched the item once (for `receiving_header_id`, needed to navigate back) — reused that instead of letting `Form` do a second, wrong fetch: `start_blank=True` + `self.form.load([item])`
- Scope: frontend

## [2026-07-09] — feat(infra): frontend HTTPS (socat TLS relay) + FRONTEND_PORT(_SSL) env vars + working default server URL
- User added `FRONTEND_PORT=8000`/`FRONTEND_PORT_SSL=8443` to `.env`/`example.env` and asked to wire them in, plus set the default server address to `http://backend:5000`
- `flet run --web` has no built-in TLS flags at all, so — unlike the backend, where Uvicorn does `--ssl-keyfile`/`--ssl-certfile` natively — added `frontend/entrypoint.sh`: generates a self-signed cert the same way `backend/entrypoint.sh` does (`frontend/certs/`, gitignored), starts `flet run --web` on `FRONTEND_PORT`, then puts a `socat OPENSSL-LISTEN` relay in front terminating TLS on `FRONTEND_PORT_SSL` and forwarding raw bytes to `FRONTEND_PORT` — works for Flet's WebSocket traffic since `socat` is L4, not HTTP-aware
- `Dockerfile-frontend`: installs `openssl`+`socat`, copies `entrypoint.sh` to `/usr/local/bin/` (outside the bind-mounted `/usr/src/app`), exposes both ports, `CMD ["entrypoint.sh"]`
- `compose.yml`: added `FRONTEND_HOST`/`FRONTEND_PORT`/`FRONTEND_PORT_SSL` env vars and both port mappings to the `frontend` service
- `repository/server_url.py`: `DEFAULT_SERVER_URL` changed from the inert placeholder `https://localhost:8000` to `http://backend:5000` (a real, working address for the containerized deployment) — updated the explanatory comments there and in `main.py`'s `_boot_navigate` (this constant doubles as the "never configured" sentinel; making it a real address means the force-to-`/server_config` behavior now effectively only fires for other deployment targets, like a native desktop build, where it doesn't resolve)
- Added `frontend/certs/` to `.gitignore`
- Verified for real: rebuilt and recreated `sfsis-frontend`; confirmed both `flet` and the new `socat` process running inside the container; `http://localhost:8000` → 200, `https://localhost:8443` → 200 (self-signed, `curl -k`); confirmed `DEFAULT_SERVER_URL` live in the container is `http://backend:5000` and that address is actually reachable from inside `sfsis-frontend`
- Scope: infra
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — fix(frontend): table and form input/label not full width on web
- User reported the shared `Table` component wasn't full width on web, and `InputForm`/`LabelForm` weren't full width like `SelectForm` already was
- Root cause of the table sizing bug: `components/table/columns.py`'s `get_screen_width()` took the *minimum* of `page.width` and `page.window.width` — on web, `page.window.width` is unreliable (observed returning a stale `400` from earlier debug logs in this session) while `page.width` correctly reflects the real browser viewport (`1653` in those same logs), so the min-clamp threw away the correct value and every column-width calculation downstream used the wrong, much smaller screen width. Fixed to prefer `page.width` whenever available, falling back to `page.window.width` only if it isn't
- `InputForm`/`LabelForm` (`components/form/input.py`, `label.py`): added `expand=True` to their `ft.TextField`, matching `SelectForm`'s `ft.Dropdown(..., expand=True)` — neither had it before, so they didn't stretch to fill their `ResponsiveRow` column the way selects already did
- Verified: re-imported all three modified files inside the actual frontend venv (no import/syntax errors), confirmed the fixes are present in the running container's bind-mounted files after a restart
- Scope: frontend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat(frontend): calendar-popup date picker field type, plus full-width fix
- User asked for the date fields (previously plain text inputs with a "YYYY-MM-DD" hint) to get a real calendar popup, and for that field to be full width like the rest
- Added `components/form/date.py` (`DateForm`): a read-only `ft.TextField` (tap to open, not typed) paired with an `ft.DatePicker` added to `page.overlay`; on selection, formats the picked date as `date.isoformat()` into the field and closes the picker; re-opening re-parses the field's current value back into the picker so it re-opens on the right date. Returns a plain `ft.TextField` (same as `InputForm`) rather than a custom composite control, specifically so `Form.serialize()`/`load()` need zero special-casing — a `"date"` field is treated exactly like an `"input"` field for value extraction once built
- Wired a new `"date"` field type into `components/form/form.py::build_elements()` (constructs `DateForm`, needs `page`/`parent` like `SelectForm` does for its popup) and into `serialize()` (added `field_type == "date"` to the existing `is_input` check)
- Switched the `date` field on all 4 stock_in/stock_out header forms (`new.py`/`edit.py` × 2) from `"type": "input"` (with a manual `hint_text: "YYYY-MM-DD"`) to `"type": "date"`
- Verified with a fake-page harness inside the real frontend venv (not just imports): built the widget standalone and drove the full open → pick → close → reopen-shows-previous-value flow; then built a real `Form` with a `"date"` field and confirmed `build_elements()` produces a plain `ft.TextField` with `expand=True` and `serialize()` correctly extracts the picked ISO date string alongside a plain input field
- Scope: frontend
- No GitHub issue filed (direct implementation, per user)
