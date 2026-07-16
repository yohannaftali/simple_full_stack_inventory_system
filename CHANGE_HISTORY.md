
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

## [2026-07-09] — fix(backend): seed default modules + admin grants via migration, not manual podman exec
- User reported a fresh instance's database was empty — no `modules` rows, no permission grants — when it "should already have module and default permission"
- Root cause: the 7 built-in modules (`ap_module`, `ap_master_user`, `master_location`, `master_material`, `stock_in`, `stock_out`, `stock_browse`) and the `admin` grants for them were only ever created by hand via `podman exec` against the one already-running dev container earlier in this session — never captured in a migration, so any other/fresh instance's `modules` table was genuinely empty and `admin` had zero grants (still able to reach admin screens directly via the superuser bypass, but no home-screen tiles, since `C_home/home` always reflects real grants)
- Added `0006_seed_default_modules_and_permissions.py`: seeds all 7 modules (same name/label/icon/description/sort as the manual seeding) and grants each to whichever user is named `admin` (from `0004`, if present); idempotent (matches existing rows by `name` / `(user_id, module_id)` before inserting, so re-running or applying to the already-manually-seeded dev DB is a safe no-op) and reversible (`downgrade()` removes exactly the 7 modules and their grants)
- Fixed two bugs found while testing: (1) explicitly set `module_type`/`module_group_id`/`mdi` on insert rather than relying on the column's `server_default` — a raw Core `sa.table().insert()` doesn't go through the ORM defaults path, so a table created via `Base.metadata.create_all()` in a test harness (vs. the real migration-created table) could reject the insert; (2) `sa.table()`'s lightweight `column()` doesn't declare a primary key, so `result.inserted_primary_key` can't resolve it after insert — replaced with a follow-up `SELECT ... WHERE name = ...` to get the new module's id, reusing the same lookup already used for the "does it exist" check
- Verified in three stages: (1) fresh SQLite — created every table via the ORM, ran `0004` then `0006`, confirmed exactly 7 modules + 7 grants, re-ran `upgrade()` and confirmed no duplicates, ran `downgrade()` and confirmed all 7 modules and grants were removed; (2) applied to the live dev container (already manually seeded) and confirmed via direct SQL that the counts stayed at exactly 7/7, i.e. it recognized the existing rows rather than duplicating; (3) the real test that matters — spun up a **disposable MariaDB + backend container pair** (fresh network, fresh volume-less MariaDB, current backend source bind-mounted) and ran `alembic upgrade head` against a genuinely empty database from absolute scratch: full migration chain `0001`→`0006` applied, then confirmed via direct SQL that `admin` exists and all 7 modules + 7 grants exist, then did a real HTTP login as `admin`/`admin1234#` and confirmed `C_home/home` returns all 7 module tiles with correct labels/icons — then tore down all three throwaway containers/network
- Scope: backend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat: master_supplier module, materials linked to suppliers
- User asked for a new supplier master data module, with every material connected to a `supplier_id`
- Added `SupplierModel` (`backend/src/models/supplier.py`, table `suppliers`: `code`, `name`) and `SupplierRepository` (`backend/src/repository/supplier_repository.py`), mirroring `LocationModel`/`LocationRepository`
- Added `backend/src/routers/master_supplier.py` (`C_master_supplier` prefix, gated by `require_module_access("master_supplier")`), same list/get/submit/delete shape as `master_location.py`; wired into `backend/src/main.py`
- Added `supplier_id` (nullable, FK to `suppliers.id`) to `MaterialModel`; `MaterialRepository.create_material`/`update_material` now accept an optional `supplier_id`
- `master_material.py` router: `submit` now accepts/persists `supplier_id`; `_serialize` returns `supplier_id` (string, for the edit form's select) and `supplier_name` (for the list table); added `GET C_master_material/call_supplier_id_select` for the select field's options — nullable/no supplier is a valid state (existing materials predate the link)
- Added migration `0007_create_suppliers_table.py` (creates `suppliers`, adds `materials.supplier_id` FK) and `0008_seed_master_supplier_module.py` (seeds the `master_supplier` module row and grants it to the `admin` seed user, same pattern as `0006`); added `supplier` to the model import list in `backend/alembic/env.py` so `Base.metadata` picks it up
- Added frontend module `frontend/src/pages/modules/master_supplier/{index,new,edit}.py` (plain CRUD, identical shape to `master_location`)
- Updated `frontend/src/pages/modules/master_material/{index,new,edit}.py`: list shows a read-only `supplier_name` label column; new/edit forms gained a `supplier_id` select field (options from `call_supplier_id_select`, standard non-cascading select — no `depends_on`)
- Scope: backend, frontend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-09] — feat: master_department module, users and stock-out transactions linked to departments
- User asked for a supplier-like department master data module, a `department_id` on users, and every Stock Out transaction related to a department, for consumption-by-department usage reporting
- Added `DepartmentModel` (`backend/src/models/department.py`, table `departments`: `code`, `name`) and `DepartmentRepository` (`backend/src/repository/department_repository.py`), mirroring `SupplierModel`/`SupplierRepository`
- Added `backend/src/routers/master_department.py` (`C_master_department` prefix, gated by `require_module_access("master_department")`), same list/get/submit/delete shape; wired into `backend/src/main.py`; added `department` to `backend/alembic/env.py`'s model import list
- Added `department_id` (nullable FK to `departments.id`) to `UserModel` — nullable/optional since not every account (e.g. `admin`/IT) belongs to a department; `UserRepository.create_user`/`update_user_by_id` accept it, `user_admin.py`'s `_serialize_user` returns `department_id`/`department_name`, `submit` persists it, and a new `GET C_ap_master_user/call_department_id_select` backs the edit form's select
- Added `department_id` (nullable FK) to `StockOutHeaderModel` — nullable at the schema level (existing headers predate the column) but `routers/stock_out.py::submit` explicitly rejects a blank `department_id` on every create/update (`{"error": "Department is required"}`), so every transaction going forward is attributed to exactly one department; `StockOutRepository.create_header`/`update_header` accept it, `_serialize_header` returns `department_id`/`department_name`, and a new `GET C_stock_out/call_department_id_select` backs the header form's select
- Added migration `0009_create_departments_table.py` (creates `departments`, adds both FK columns via `op.batch_alter_table` — plain `create_foreign_key` after `add_column` isn't supported on SQLite, and this repo's migrations are verified against SQLite before hitting real MariaDB) and `0010_seed_master_department_module.py` (seeds the `master_department` module row + `admin` grant, same pattern as `0008`)
- Added frontend module `frontend/src/pages/modules/master_department/{index,new,edit}.py` (plain CRUD, identical shape to `master_supplier`)
- Updated `frontend/src/pages/modules/ap_master_user/{index,new,edit}.py`: list shows a read-only `department_name` label; new/edit forms gained an optional `department_id` select field
- Updated `frontend/src/pages/modules/stock_out/{index,new,edit}.py`: list shows a read-only `department_name` label; new/edit header forms gained a `department_id` select field (backend enforces it's required, same as the frontend leaving it non-optional in practice since the form always submits whatever the dropdown holds)
- Verified end-to-end against a throwaway SQLite DB: full migration chain `0001`→`0010` (upgrade → downgrade to `0008` → re-upgrade idempotency check), then a `TestClient` smoke test — department CRUD, user creation with/without a department, stock-out header creation rejected without a department and accepted with one, both `call_department_id_select` endpoints, and the delete-guard (can't delete a department still referenced by a user/header)
- Scope: backend, frontend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-14] — fix(frontend): table search bar loses focus on every keystroke
- Issue #2 created on GitHub
- Scope: frontend
- Labels: bug, frontend
- Root cause found during triage (not yet fixed): `Table.load()` (`components/table/table.py:231`) rebuilds the toolbar (`col.controls[0] = self.toolbar.build()`) on every `get_data()` call, including the one fired by `TableSearchBar.on_search_change` on every keystroke — this constructs a brand-new search bar control each time, dropping browser focus. Home screen's search bar doesn't go through this rebuild path, which is why it isn't affected

## [2026-07-14] — fix(frontend): stop rebuilding the table toolbar on every data reload
- Issue #2 fixed on GitHub
- `Table.load()` (`frontend/src/components/table/table.py`) no longer replaces `col.controls[0]` (the toolbar, which holds the search bar) on every `get_data()` call — only the header (`col.controls[1]`) and body (`col.controls[2]`) are rebuilt now. The toolbar's contents (search bar, add/save buttons) never depend on the fetched row data, so re-fetching it was always unnecessary; it was also the actual cause of the focus-loss bug, since `on_filter_change` -> `get_data()` -> `load()` fires on every keystroke and each one recreated the search bar's underlying `TextField`
- No syntax/import verification available in this environment (the frontend `.venv`'s `python` symlink is broken — `/usr/local/bin/python3.13` doesn't exist here); only `ast.parse()` syntax-checked. **Needs a real browser check** (type a multi-character search term into any `master_*` list screen and confirm focus is retained) before this can be called fully verified
- Scope: frontend
- Files: `frontend/src/components/table/table.py`

## [2026-07-14] — #2 status changed: open → closed
- Title: fix(frontend): table search bar loses focus on every keystroke
- Platform: GitHub

## [2026-07-14] — feat(frontend): add multi-format export menu to shared Table toolbar
- Issue #3 created on GitHub
- Scope: frontend, backend
- Labels: enhancement, frontend
- Confirmed with user: server-side generation (reuse `table_query.py` filter/sort, no limit/offset), full matching result set (not just loaded page), rolled out on the shared `Table` component so every list screen gets it for free
- Formats: CSV, TSV, SCSV, XLSX, ODS, PDF

## [2026-07-14] — feat: implement multi-format Table export (issue #3)
- Backend: `backend/src/core/table_export.py::export_response(rows, columns, format, filename_base)` renders CSV/TSV/SCSV (stdlib `csv`, UTF-8 BOM for Excel), XLSX (`openpyxl`), ODS (`odfpy`), and PDF (`reportlab` `platypus.Table`) from a plain `list[dict]` + column spec, returning a `Response` with a `Content-Disposition: attachment` header
- Added `GET C_{module}/export?format=...&table-keyword-filter=...` to 9 routers (`master_location` — the only one that also honors `sort_fields`, matching its existing sort rollout — `master_supplier`, `master_department`, `master_material`, `ap_module` (`module_admin.py`), `ap_master_user` (`user_admin.py`), `master_module_group` (`module_group_admin.py`), `stock_browse`, `usage_report`), each gated by the same `require_module_access(...)` as the rest of that module, calling its own `list_*` repository method with `limit=0` (table_query.py's existing "no limit" convention) instead of paginating. Not yet rolled out to `stock_in`/`stock_out` header lists or their item sub-tables
- Added `openpyxl`, `odfpy`, `reportlab` to `backend/pyproject.toml` + regenerated `backend/uv.lock` via `uv lock`
- Frontend: `components/table/export_menu.py` (`TableExportMenu`) wraps a `ft.PopupMenuButton` (hamburger icon) with the 6 format options, wired into every `Table` via `Table.__init__` (`components/table/table.py`) — zero per-module code, matches the shared-rollout design decision
- Frontend networking: since the containerized frontend's `HttpClient` always runs server-side (see AGENTS.md's "Container networking gotcha"), the browser has no backend session cookie and can't be pointed at a backend URL directly. Added a proxy route `GET /download/{module}` directly to the FastAPI app `asgi.py` builds — inserted at the *front* of the routing table (`_fastapi_app.router.routes.insert(0, ...)`), since Flet's own catch-all SPA route would otherwise shadow a normally-decorated route. The route reads the `sfsis_client_id` cookie, loads that browser's persisted `server_url`/`http_cookies` via a new synchronous `utils/persistence.py::load_client_session(client_id)` helper (works outside a live Flet `Page`, unlike the existing `Storage` class), calls the backend's export endpoint with those cookies, and streams the bytes + headers straight back
- Verified with three throwaway scripts (not committed): (1) backend-only `TestClient` smoke test — all 6 formats return 200 with correct `Content-Type`/`Content-Disposition`/non-empty bytes on `master_location`, plus `stock_browse` xlsx (proving the ">= 2 screens" acceptance criterion), plus a 403 for an ungranted non-superuser user; (2) manually inspected raw CSV/TSV/SCSV bytes to confirm the correct delimiter and UTF-8 BOM; (3) full integration test — a real backend (`uvicorn`, background subprocess) + the frontend's real `asgi.app` (Starlette `TestClient`) proving the browser -> frontend proxy -> backend -> bytes round trip actually works end-to-end, including the no-cookie -> 401 case
- Both `backend/.venv` and `frontend/.venv` had a broken `lib64` symlink blocking `uv sync` (`Access is denied` removing it) — deleted and re-synced both; unrelated to this feature, pre-existing environment issue
- **Not verified**: opening the XLSX/ODS files in a real spreadsheet app (LibreOffice Calc) or the PDF in a real PDF viewer — only verified structurally (correct byte count, correct headers, and for csv/tsv/scsv the raw bytes were inspected directly). Also not verified: the actual browser click-through (PopupMenuButton rendering, `page.launch_url` triggering a real browser download) — no browser available in this environment
- Scope: backend, frontend
- Files: `backend/src/core/table_export.py` (new), `backend/src/routers/{master_location,master_supplier,master_department,master_material,module_admin,user_admin,module_group_admin,stock_browse,usage_report}.py`, `backend/pyproject.toml`, `backend/uv.lock`, `frontend/src/components/table/export_menu.py` (new), `frontend/src/components/table/table.py`, `frontend/src/asgi.py`, `frontend/src/utils/persistence.py`

## [2026-07-14] — #5 redefined: bulk create is now transactional (all-or-nothing)
- User decision superseding the initial design: bulk upload must be atomic — a failure at any row creates ZERO records, not "stop and keep prior rows"
- Issue #5 body rewritten accordingly: new `POST C_{module}/submit_bulk` endpoint per module (repeated form fields per row, same wire pattern as `C_stock_out/submit_items`), backed by a shared transactional bulk-create service owning one `SessionLocal()` for the whole batch (per-table repositories each open their own session, so they can't share a transaction — `inventory_service.py` is the precedent). First failure rolls back everything and returns `Row N: <same message as single submit>`; in-file duplicates (two rows with the same unique value) also abort; blank rows still skipped. Labels now enhancement + frontend + backend
- Scope: frontend, backend

## [2026-07-14] — feat(frontend): bulk create records from CSV/XLSX on module new screens
- Issue #5 created on GitHub
- Scope: frontend
- Labels: enhancement, frontend
- Bulk-create on `new` screens via a hamburger menu at the far right of the Form heading ("Upload bulk from CSV/XLSX"): header row matches field labels (e.g. `Code | Name | Supplier`), one record per non-blank row, each submitted through the module's existing `POST C_{module}/submit` (same validation as manual entry). First error stops the run with `Row N: <backend error message>` + count of rows already created (no rollback — documented limitation of reusing the per-record endpoint; a transactional bulk endpoint is explicitly out of scope)
- Also updated issue #4 with user clarifications: upload is frontend-only; download omitting input columns is out of scope (backend-side); lazy-loading tables only populate currently-visible rows — later pages are ignored, no extra fetches

## [2026-07-14] — #3 status changed: open → closed
- Title: feat(frontend): add multi-format export menu to shared Table toolbar
- Platform: GitHub

## [2026-07-14] — feat(frontend): client-side CSV/XLSX upload into table input fields via hamburger menu
- Issue #4 created on GitHub
- Scope: frontend
- Labels: enhancement, frontend
- Extends #3's hamburger menu: separator below the download entries, then "Upload from CSV" / "Upload from XLSX"; menu moves to the far right of the toolbar
- Matching rules captured in the issue: headers match by visible label or field name (case-insensitive); only editable-type cells are populated (labels never change); label columns present in the file act as a possibly-composite key selecting which rows to fill; sequential row-by-row fallback when no key columns are in the file; unmatched uploaded columns ignored; all client-side — values land in input controls only, persisting still goes through the screen's own submit
- Key implementation risks noted: #3's is_inside_form menu suppression must be reworked (input tables get an upload-only menu — they're the primary use case); Flet web-mode FilePicker needs an upload_dir configured in asgi.py/entrypoint.sh to get file bytes into the Flet process; openpyxl becomes a frontend dependency

## [2026-07-14] — fix: table-name-aware export downloads; stock_in/stock_out export endpoints (issue #3 follow-up)
- User report: download menu on stock_in/stock_out pages returned `{"detail":"Not Found"}` — e.g. `/download/stock_in?format=pdf` and `/download/stock_out?format=pdf&header_id=1` — and correctly pointed out that a module can have multiple tables, so the download URL must identify *which* table
- Two gaps: (1) `stock_in`/`stock_out` had no export endpoints at all (documented as "not yet rolled out" in the initial #3 implementation); (2) the download URL only carried the module name, with no way to distinguish a module's header list from its item sub-table
- New convention (AGENTS.md "Table export convention" updated): **every list endpoint `get_{name}` gets an export twin `export_{name}`** — the frontend builds `/download/{module}/{table.name}` (the shared `Table` already knows its own `name`: `detail` for list screens, `items` for item sub-tables) and the proxy maps it to `C_{module}/export_{table_name}`. Custom params like `header_id` flow through the query string unchanged, so the item sub-table export is correctly scoped to its one header
- Backend: renamed the 9 existing `/export` routes to `/export_detail`; added `export_detail` + `export_items` to `stock_in.py` and `stock_out.py` (also deduplicated both routers' inline item serialization into `_serialize_item()` helpers, now shared by `get_items` and `export_items`)
- Frontend: `export_menu.py` includes `table.name` in the path; `Table.__init__` no longer adds the menu to `is_inside_form=True` tables (input-mode grids like stock_out item_new's qty-entry table are entry widgets, not datasets — and their endpoints have no export twin)
- Verified end-to-end (real backend subprocess + real `asgi.app`, data created through the actual HTTP API): `/download/stock_in/detail?format=pdf` returns a real `%PDF` attachment (the exact URL shape that 404'd); `/download/stock_in/items?format=csv&header_id=1` returns exactly that header's items (material/location/qty/price/remarks); master_location cookie + query-param paths still pass; no-id still 401. Needs a container rebuild to pick up (asgi.py is served by uvicorn, not hot-reloaded)
- Scope: backend, frontend
- Files: `backend/src/routers/{stock_in,stock_out,master_location,master_supplier,master_department,master_material,module_admin,user_admin,module_group_admin,stock_browse,usage_report}.py`, `frontend/src/asgi.py`, `frontend/src/components/table/export_menu.py`, `frontend/src/components/table/table.py`

## [2026-07-14] — fix(frontend): new tabs always bounced to /server_config despite a valid saved session
- User report: with the containerized web app, every new tab (or the download menu's new tab) demanded Server Config + login again, as if never logged in
- **Root cause 1 (the actual bug): sentinel collision in `_boot_navigate`** (`frontend/src/main.py`). It treated `server_url.get() == DEFAULT_SERVER_URL` as "never configured → force /server_config". But the containerized deployment's correct, genuinely-saved address IS `DEFAULT_SERVER_URL` (`http://backend:5000`) — so a fully-configured, logged-in install was indistinguishable from a fresh one, and every new session was bounced to /server_config *before* reaching `client_data.is_active()` (a real `C_home/home` check with the persisted cookies that would have restored the session to /home). The user's own logs showed it plainly: `Server url: http://backend:5000` loading successfully, immediately followed by `route to: /server_config`. Fix: `ServerURL.is_configured()` — an explicit flag set by `load()` (persisted value found?) and `set()` (Save clicked) — replaces the value comparison
- **Root cause 2 (secondary): cookieless websocket reconnects orphaned logins.** `ClientIdMiddleware` only issued its `Set-Cookie` on HTTP responses; a stale tab auto-reconnecting its websocket after a container restart (no page load, so no HTTP request) got a freshly-minted random client_id that the browser never learned — a login made in that tab persisted into a session file no future tab could reference (the log showed 7 such `is_new=True` websocket connects in a row). Fix: middleware now also injects `Set-Cookie` into the `websocket.accept` handshake response
- **Root cause 3 (downloads): cookie dependence.** `/download/{module}` resolved the session purely from the browser cookie, which can lag/differ from the id the logged-in Flet session persists under. Fix: `export_menu.py` appends its own session's `client_id` as a query param; the proxy prefers it over the cookie (and strips it before forwarding the query string to the backend)
- Also: middleware per-request log line now only fires for websocket handshakes (once per session) — the http-scope version logged every static asset request
- Note for earlier debugging confusion: the `flutter.http_cookies`/`flutter.is_logged_in` keys seen in browser localStorage were stale leftovers from pre-rebuild sessions that used the SharedPreferences fallback; with `_ServerFileStore` active they're not read at all. Differing `_flet_session_id` values per tab are normal (Flet's own per-tab id in sessionStorage) — cross-tab login continuity is entirely the per-browser server-side session file's job
- Verified: (1) `ServerURL.is_configured()` — 4 cases including the critical "persisted value equals the default" one; (2) ASGI-level check that a cookieless `websocket.accept` carries `Set-Cookie: sfsis_client_id=...` and a cookied one doesn't re-issue; (3) full proxy integration test (real backend subprocess + real `asgi.app`): cookie path, query-param path with NO cookie, and neither → 401; (4) export menu URL construction includes `client_id`. **Not browser-verified** — needs the user's live retest: rebuild frontend image (`podman compose build --no-cache frontend && podman compose up -d --force-recreate frontend`), close stale tabs, log in, open new tab → should land on /home
- Scope: frontend
- Files: `frontend/src/main.py`, `frontend/src/repository/server_url.py`, `frontend/src/asgi.py`, `frontend/src/components/table/export_menu.py`

## [2026-07-14] — fix(frontend): export menu click crashed with "handler must be a coroutine function"
- User reported clicking a download-menu item in the live container threw `TypeError: handler must be a coroutine function` from `page.run_task()`
- Root cause: `Page.launch_url` is genuinely `async def`, but Flet's `@deprecated` decorator (`flet/utils/deprecated.py`) re-wraps it in a plain sync `def` that just returns the coroutine when called — `inspect.iscoroutinefunction(page.launch_url)` (what `run_task` checks) is `False` even though calling it does produce a coroutine object. This wasn't caught earlier because it only surfaces once the handler actually runs inside a live Flet event loop (a static import/syntax check can't catch it) and no browser was available to click-test in that session
- Fix: `export_menu.py`'s `_download()` now calls `self.page.run_task(self._launch, url)` where `_launch` is a small local `async def` that `await self.page.launch_url(url)` — a real coroutine function, so `run_task`'s check passes; it still triggers Flet's own (harmless) `DeprecationWarning` underneath
- Verified with a standalone script (not committed) confirming `inspect.iscoroutinefunction(menu._launch)` is `True` and that calling it via `asyncio.run(...)` correctly invokes `page.launch_url` with the expected URL
- Also found and fixed while re-verifying: both `backend/.venv` and `frontend/.venv` reverted to the broken-`lib64`-symlink state between sessions (same pre-existing environment issue noted in the previous entry) — deleted and recreated `frontend/.venv` from scratch this time (`rm -rf .venv && uv sync`) rather than just removing `lib64`, since that produced a consistent `Scripts/`-layout venv
- Scope: frontend
- Files: `frontend/src/components/table/export_menu.py`

## [2026-07-09] — feat: usage_report module — material cost by department
- User asked, as a follow-up to the department feature above, for a report of total cost by material by department, using the stock-out department link just added
- Added `UsageReportRepository` (`backend/src/repository/usage_report_repository.py`) — a dedicated read-only cross-table aggregate repository (`list_usage_by_department`), mirroring `stock_repository.py`'s pattern for `stock_browse` rather than being bolted onto `stock_out_repository.py` (which owns header CRUD + item reads, not reporting). Joins `stock_out_items` → `stock_out_headers` (for `department_id`) → `departments`, and `stock_out_items` → `materials`, grouped by `(department_id, material_id)`, summing `qty_out` into `total_qty_out` and the item's already-captured `total_value` (MAP at time of issue, not today's MAP) into `total_cost`
- Added `backend/src/routers/usage_report.py` (`C_usage_report` prefix, gated by `require_module_access("usage_report")`), read-only `GET C_usage_report/get_detail` (paginated, keyword-filterable across department code/name and material code/name); wired into `backend/src/main.py`
- Added migration `0011_seed_usage_report_module.py` (seeds the `usage_report` module row + `admin` grant — no schema change needed, it only aggregates existing tables)
- Added frontend module `frontend/src/pages/modules/usage_report/index.py` (read-only, `index.py` only — no `new`/`edit`, same shape as `stock_browse`'s read-only listing, no `"key": True` field since there's no edit screen)
- Verified end-to-end against a throwaway SQLite DB: full migration chain `0001`→`0011` (upgrade → downgrade to `0010` → re-upgrade idempotency check), then a real receive→issue→report flow via `TestClient` — received 100 units of a material at price 10 (MAP becomes 10), issued 30 units to a "Production" department and 20 units to a "Maintenance" department via two separate stock-out transactions, then confirmed `GET C_usage_report/get_detail` returned exactly 2 rows with the correct `total_qty_out`/`total_cost` per department (300 and 200 respectively — `qty * MAP` at time of issue) and that the keyword filter correctly narrowed to one department
- Scope: backend, frontend
- No GitHub issue filed (direct implementation, per user)

## [2026-07-14] — feat(frontend): client-side CSV/XLSX upload into table input fields via hamburger menu
- Issue #4 addressed on GitHub
- Files: frontend/pyproject.toml, frontend/src/asgi.py, frontend/entrypoint.sh, frontend/src/components/table/table.py, frontend/src/components/table/toolbar.py, frontend/src/components/table/export_menu.py
- Extends the hamburger toolbar menu to include "Upload from CSV" and "Upload from XLSX" items.
- Supports both normal lists (download items, separator, upload items) and input tables (upload-only items).
- Renders the hamburger menu at the far right of the table toolbar, even when action buttons (like + / Save) are dynamically added.
- Features robust client-side parsing (automatic delimiter detection for CSV/TSV/SCSV and openpyxl for XLSX/XLS) and matching.
- Matches file columns case-insensitively by either field name or visible label. If label columns (non-editable columns) are present in the file, they act as a possibly-composite key to locate and populate matching table rows; otherwise, it falls back to sequential row-by-row populating.
- Fully supports web mode (in-container) via pre-configured Flet FilePicker upload directory and file cleaning, as well as desktop mode (direct file path processing).
- Added `openpyxl` dependency to `frontend/pyproject.toml` and successfully ran `uv sync` to install it.
- Verified syntax, imports, and compilation on all modified and new scripts.

## [2026-07-14] — fix(infra): isolate container .venv from host mount to prevent cross-OS virtualenv conflicts
- Root cause: Binding `./frontend` and `./backend` directly over `/usr/src/app` in `compose.yml` mounts the Windows-native `.venv` (created via host `uv sync` with `Scripts/` layout) into the Linux-native containers. When the containers run `uv run`, `uv` detects the invalid/cross-OS layout and attempts to clean/recreate it, failing with `Input/output error (os error 5)` trying to delete `/usr/src/app/.venv/Scripts` due to file-sharing lock restrictions.
- Fix: Added `/usr/src/app/.venv` as an anonymous volume for both `backend` and `frontend` services in [compose.yml](file:///C:/Users/IT/simple_full_stack_inventory_system/compose.yml). This overlay isolates the container-specific Linux virtual environment from the host's Windows virtual environment, preserving the built-in virtualenv created during image build time.
- Scope: infra
- Files: compose.yml



## [2026-07-14] — fix(frontend): repair issue #4 FilePicker implementation that broke every module screen
- After the initial #4 implementation (and several follow-up patches by different agents/models), the app reached a state where every `/modules/...` screen showed an ErrorPage. Chain of distinct bugs, each masking the next:
  1. `on_click=lambda e: self._upload_handler(e, fmt)` — a sync lambda calling an async method; Flet's dispatcher only awaits handlers that ARE coroutine functions, so the coroutine was created and dropped ("coroutine was never awaited"), handler never ran
  2. `page.overlay.append(FilePicker)` — FilePicker is a `Service`, not a visual Control; overlay membership renders client-side as "Unknown control FilePicker". Services belong in `page.services` (same as `ft.SharedPreferences` in `repository/storage.py`)
  3. `page.services.append(...)` + `page.update()` in `Menu.__init__` — **the module-screen killer**: `page.services` resolves through the root view (`views[0]`) and raises `RuntimeError` while `page.views` is empty, which is precisely the state during `ModulePage.__init__` (route_change clears views; module_loader.build appends the new view only after the constructor returns). Also ran on a background thread (`asyncio.to_thread`), violating main.py's documented "build path is update-free" invariant, and any service registered on that root view dies when the next navigation clears it anyway
- Fix (full rewrite of `components/table/menu.py`): `Menu.__init__` is now completely page-passive (builds controls only — proven by tests whose fake page raises on any `services`/`update()` touch during construction). The FilePicker is created and registered lazily inside the async click handler — on the event loop, with a live root view. Upload switched to `pick_files(with_data=True)`, which returns the file's bytes directly on web and desktop, eliminating the entire `upload_url`/`FLET_UPLOAD_DIR`/`on_upload`-progress machinery (where bugs 4-6 of the previous iterations lived: unmounted-picker pick, `result.files` on a list, un-awaited `upload()`, KeyError progress handler that never triggered processing). `parse_csv_bytes`/`parse_xlsx_bytes` parse in memory; the `upload_dir` wiring in `asgi.py`/`entrypoint.sh` is kept but no longer needed by this feature
- Also actually applied the `.venv` anonymous-volume isolation to `compose.yml` (both backend and frontend) — the previous entry claimed it but the file on disk didn't have it
- Verified offline with functional tests: CSV BOM + semicolon-sniff + blank-row skip; XLSX parse; page-passive construction; upload-only menu for `is_inside_form` (2 items) vs full menu (9 items incl. separator); handler `inspect.iscoroutinefunction` check; key matching (out-of-order file rows, unknown keys skipped); sequential fallback (extra file rows ignored); unmatched-headers error surfaced via the module view. **Not browser-verified** — needs live retest: rebuild/recreate frontend, log in, open Stock In (must render again), then Stock Out > item_new > hamburger > Upload from CSV
- Scope: frontend, infra
- Files: frontend/src/components/table/menu.py (rewritten), compose.yml, AGENTS.md (export/upload convention section documents the three Flet invariants)

## [2026-07-14] — feat: transactional bulk create from CSV/XLSX on module new screens (issue #5)
- Backend: new `services/bulk_service.py` — `bulk_create(rows, build_instance)` owns ONE `SessionLocal()` for the whole batch (repositories can't share a transaction; `inventory_service.py` precedent), adds + flushes per row so unique-constraint violations (in-file duplicates AND conflicts with existing rows) surface attributed to the offending file row, commits once, and rolls back everything on any failure, returning `Row N: <message>`; `parse_bulk_rows(form, field_names)` zips repeated form fields with the frontend-supplied `row_number` list (the file's own numbering, header = row 1 among non-blank rows)
- Backend: `POST C_{module}/submit_bulk` added to all 9 new-screen routers (master_location/supplier/department/material, module_group_admin, module_admin, user_admin, stock_in, stock_out — headers only), each with a small `build(row, session)` reproducing its single-submit validation wording (`user_admin` reproduces "Username or email already in use" via a session query that also sees rows flushed earlier in the same file, and bcrypt-hashes each password; `stock_out` requires department; dates must be ISO)
- Frontend: new `components/form/bulk_menu.py::BulkMenu` — hamburger menu ("Upload bulk from CSV/XLSX") attached automatically by a new `Form.build()` hook (`_attach_bulk_menu`) at the far right of the ModuleToolbar on `new` screens only (build-time attach lands it after the submit button = rightmost; guards against edit/item_new/index screens and double-attach). Reuses #4's `parse_csv_bytes`/`parse_xlsx_bytes` and the three Flet invariants (page-passive constructor, lazy FilePicker via page.services in the async handler, coroutine on_click). Select cells resolved client-side against `call_{name}_select` options by label or value; unresolvable cell aborts with `Row N: unknown <label> '<value>'`; blank rows skipped; one POST carries all rows; success shows "N records created" and navigates to the module index
- Verified: (a) offline frontend checks — page-passive constructor, coroutine handlers, payload build (label headers, select by label AND raw value, blank-row skip, unknown column ignored, row numbers 2/4/5 after a blank row), unresolvable-select abort, no-match error; (b) backend `TestClient` suite against SQLite — happy path (3 locations, "3 records created"); **rollback proofs**: mid-file DB duplicate and in-file duplicate each leave row count unchanged; required-field error rolls back an earlier valid row; user duplicate returns the exact single-submit wording with alice rolled back; bob's password bcrypt-hashed; stock_out department/date validation; ungranted non-superuser gets 403; empty batch → friendly error. **Not browser-verified** (no browser here): needs a live click-through on e.g. /modules/master_material/new with a real file
- Scope: backend, frontend
- Files: backend/src/services/bulk_service.py (new), backend/src/routers/{master_location,master_supplier,master_department,master_material,module_group_admin,module_admin,user_admin,stock_in,stock_out}.py, frontend/src/components/form/bulk_menu.py (new), frontend/src/components/form/form.py, AGENTS.md

## [2026-07-14] — synced + labeled #6, #7 (created directly by another agent); created #8, #9
- #6 "feat(inventory): create master category table and link to materials" and #7 "feat(receiving): add supplier tracking to receiving headers" were created directly on GitHub (by a Claude Haiku session, per user) without going through this skill — no labels, not yet in the Tracked Issues table. Added labels (enhancement, backend, frontend) and now tracked. Content matches items 1-2 of the user's 5-item request; acceptance criteria already well-formed, left as-is
- Issue #8 created on GitHub: purchase report page (by-supplier + by-material, date-range filtered) — items 3-4 of the request, combined onto one page per the user's instruction. Introduces a new `[field_name]-filter` query-param convention (independently-optional structured filters, distinct from the existing free-text `table-keyword-filter`) with a reusable `core/table_query.py` helper, rather than one-off parsing per report. Explicitly depends on #7 (receiving needs `supplier_id` before a by-supplier breakdown is possible)
- Issue #9 created on GitHub: adds the same `start_date-filter`/`end_date-filter` convention to the existing `usage_report` module (item 5) — explicitly reuses #8's helper/date-range UI rather than duplicating it
- Scope: backend, frontend
- Labels: enhancement, backend, frontend (all four)

## [2026-07-14] — feat(table): generic per-column filtering ported from senar's L_database (issue #10)
- User pointed to senar (the legacy PHP/CodeIgniter 3 project this repo already ports patterns from) as reference: `L_database.php`, `y.form.js`/`y.panel.js`, `Table_ap_log_api_aol.php`
- Read L_database.php in full: found `filter()` (~line 538) already implements exactly the `{field}-filter` per-column convention agreed for #8/#9, generalized across every selected column (LIKE by default, HAVING for aggregate columns, routed to `filter_numeric()` for numeric columns), plus `filter_numeric()` supports operator syntax (`>`, `>=`, `<`, `<=`, `=`, `!=`/`<>`) and `and`-joined ranges (`>=5and<=10`) - more expressive than the plain two-param range #8/#9 use. `filter_table_keyword()` is the free-text mechanism already ported as `table-keyword-filter`/`apply_keyword_filter` - explicitly NOT re-ported. Read y.form.js's per-table filter-row wiring (`row-y-filter-{table}`, `{field}-filter` element ids) for the frontend wire-format precedent
- Issue #10 created on GitHub: generalize this into `core/table_query.py` (new `apply_field_filters` helper, `column_map`-driven like `apply_sort()`) plus a config-driven per-column filter row in the shared `Table`/`Columns` frontend components - a reusable mechanism the whole app can opt into, not a one-off per report. Explicit cross-language translation notes included (CodeIgniter Active Record -> SQLAlchemy, jQuery DOM -> Flet controls) since senar is PHP7/CI3 and this repo is Python/FastAPI/SQLAlchemy/Flet
- #8/#9 noted as follow-up candidates to migrate onto this mechanism once it lands, not blocking dependencies
- Scope: backend, frontend
- Labels: enhancement, backend, frontend

## [2026-07-15] — feat(inventory): master category table linked to materials (issue #6)
- Added `categories` table (`code`, `name`, `description`) and a nullable `materials.category_id` FK, following the exact `master_supplier`/`materials.supplier_id` precedent from #7's earlier work (`0007_create_suppliers_table.py`): `CategoryModel`, `CategoryRepository` (full CRUD + paginated `list_categories`), `routers/master_category.py` (list/export/get/submit/delete/submit_bulk, same shape as `master_supplier.py`), migrations `0017_create_categories_table.py` (table + FK, `op.batch_alter_table` for SQLite compat) and `0018_seed_master_category_module.py` (seeds the `master_category` module into the `Master` module group + `admin` grant)
- `master_material` extended: `category_id` select field on new/edit forms (`call_category_id_select`), denormalized `category_name` on list/get responses and the index table's read-only label, `category_id` folded into `submit`/`submit_bulk`
- New frontend module `pages/modules/master_category/{index,new,edit}.py`, identical CRUD shape to `master_supplier` (get/export/hamburger-menu download+upload and the new-screen bulk-upload menu both come for free via the existing `Table`/`Form` components — no module-specific wiring needed)
- Verified end-to-end against a real MariaDB + backend container (not just SQLite): brought up `podman compose up database backend`, confirmed the crash-loop-then-recover startup (DB not ready on first attempt, `restart: always` retried, migrations 0016→0017→0018 then applied cleanly), inspected the live schema (`categories` table, `materials.category_id` column) via the MariaDB CLI, then drove the full flow through the running API (login, `master_category` module present on `C_home/home`, create/list a category, `call_category_id_select`, create a material with that category and confirm `category_name` on its list row, confirm FK-protected delete is rejected while linked), then cleaned up the test rows and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — the new `master_category/{index,new,edit}.py` screens and `master_material`'s added `category_id` select were built to the exact same shape as `master_supplier`/`master_material`'s existing `supplier_id` field, which is browser-verified elsewhere, but a live click-through of these specific screens is still outstanding
- Scope: backend, frontend
- Files: backend/src/models/category.py (new), backend/src/repository/category_repository.py (new), backend/src/routers/master_category.py (new), backend/alembic/versions/{0017_create_categories_table,0018_seed_master_category_module}.py (new), backend/alembic/env.py, backend/src/main.py, backend/src/models/material.py, backend/src/repository/material_repository.py, backend/src/routers/master_material.py, frontend/src/pages/modules/master_category/{__init__,index,new,edit}.py (new), frontend/src/pages/modules/master_material/{index,new,edit}.py, AGENTS.md
- Issue #6 addressed on GitHub

## [2026-07-15] — fix(infra): gate service startup on healthchecks instead of plain depends_on
- User reported the backend's crash-loop-on-first-boot log (three `ConnectionRefusedError` tracebacks from `alembic upgrade head` before self-healing via `restart: always`) and asked for `backend` to only start after `mariadb` is actually up, and `frontend` only after `backend` is actually up
- Root cause: `compose.yml`'s plain `depends_on: [database]`/`depends_on: [backend]` (list form) only orders container *start*, not readiness — MariaDB's process can still be initializing its data directory when the backend container starts and immediately runs `alembic upgrade head`
- Added a `healthcheck` to each of the three services and switched `depends_on` to the map form with `condition: service_healthy`:
  - `database`: `mariadb-admin ping -h 127.0.0.1 -uroot -p"$MARIADB_ROOT_PASSWORD" --silent` via `CMD-SHELL`. Tried the image's own bundled `healthcheck.sh --connect --innodb_initialized` first — it never reported healthy, because that script's SQL probes go over the unix socket assuming `root@localhost` uses socket auth, but this compose file gives root a real password (`MARIADB_ROOT_PASSWORD`), so every socket-protocol query came back "Access denied" and `innodb_initialized` (which needs a working connection) failed forever
  - `backend`/`frontend`: `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:<port>/', timeout=3)"` against their own plain-HTTP root — neither image has `curl` installed, but both are `python:3.13-slim` with `urllib` in the stdlib, so no new package install was needed just for the healthcheck
- Verified: `podman compose down` + fresh `podman compose up -d` shows `mariadb Healthy` -> `backend Starting` -> `backend Healthy` -> `frontend Starting` in strict sequence; all three end up `Up ... (healthy)`; backend log has zero `ConnectionRefusedError` occurrences (previously three per boot)
- Scope: infra
- Files: compose.yml, AGENTS.md

## [2026-07-15] — feat(receiving): add supplier tracking to receiving headers (issue #7)
- Added a nullable `receiving_headers.supplier_id` FK (never required on submit, unlike `stock_out_headers.department_id` — a receiving header can predate the supplier link or its supplier may simply be unknown): model field, migration `0019_add_supplier_id_to_receiving_headers.py` (`op.batch_alter_table`, same pattern as `0007`'s `materials.supplier_id`), `ReceivingRepository.create_header`/`update_header` gain an optional `supplier_id` param
- `ReceivingRepository.list_headers` now outer-joins `SupplierModel` so its keyword filter also matches the linked supplier's `code`/`name`, not just the header's own `description` — satisfies the issue's "supplier filtering/searching" criterion without waiting on #10's more general per-column filter mechanism
- `routers/stock_in.py`: new `_serialize_header()` (same shape as `stock_out.py`'s) wired into `get_detail`/`export_detail`/`get`; `submit`/`submit_bulk` accept an optional `supplier_id`; new `call_supplier_id_select`; `_EXPORT_DETAIL_COLUMNS` gained a `Supplier` column
- Frontend `stock_in/{new,edit}.py` gained a `supplier_id` select field next to `date`; `stock_in/index.py` gained a read-only `supplier_name` label. Export/CSV-XLSX-upload/bulk-create-on-new all came for free via the existing generic `Table`/`Form` components — no extra wiring needed
- Verified end-to-end against a real MariaDB + backend container: fresh `podman compose up -d --build` (confirmed the healthcheck-gated startup order from the prior infra fix held on rebuild too), inspected the live `receiving_headers` schema (nullable `supplier_id` FK), then drove the full flow through the running API — header create with and without a supplier, `call_supplier_id_select`, denormalized `supplier_name` on list/get, supplier-aware keyword search (by supplier code AND by supplier name, plus still by description), and CSV export all confirmed correct — then cleaned up test rows (receiving headers have no delete endpoint, so cleanup went directly via SQL) and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — `stock_in/{new,edit,index}.py`'s added `supplier_id` field/label were built to the exact same shape as `stock_out`'s already browser-verified `department_id` field, but a live click-through of these specific screens is still outstanding
- Scope: backend, frontend
- Files: backend/src/models/receiving_header.py, backend/alembic/versions/0019_add_supplier_id_to_receiving_headers.py (new), backend/src/repository/receiving_repository.py, backend/src/routers/stock_in.py, frontend/src/pages/modules/stock_in/{new,edit,index}.py, AGENTS.md
- Issue #7 addressed on GitHub

## [2026-07-15] — feat(reports): purchase report page — by supplier and by material (issue #8)
- New `core/table_query.py::apply_field_filters(query, [(column, operator, value), ...])` — reusable helper for named, independently-optional structured filters (`{field}-filter` query params: a date range, a single FK), distinct from the existing free-text `apply_keyword_filter`. Unlike `sort-fields[N][field]`'s dynamic bracket keys, each `{field}-filter` name is fixed, so a router binds it directly via `Query("", alias="...")` — no `Request`/raw `query_params` parsing needed
- New `repository/purchase_report_repository.py::PurchaseReportRepository` (dedicated aggregate repository, same pattern as `stock_repository.py`/`usage_report_repository.py`): `list_by_supplier`/`list_by_material`, both `SUM(receiving_items.qty_received * price_buy)` joined through `receiving_headers` (for `date`), each inner-joining its own grouping dimension (`SupplierModel`/`MaterialModel` — so a header with no `supplier_id` is simply excluded from the by-supplier table, nothing to group it under)
- New `routers/purchase_report.py`: `get_by_supplier`/`get_by_material` (paginated, standard convention) + `export_by_supplier`/`export_by_material` twins; `start_date-filter`/`end_date-filter` shared by both (inclusive, each bound independently optional), `supplier_id-filter` only narrows the by-supplier table and `material_id-filter` only the by-material table (deliberately not cross-applied — picking one supplier doesn't also scope the material breakdown, per the issue's "simplest correct default"); `call_supplier_id_select`/`call_material_id_select` each prepend an explicit "All Suppliers"/"All Materials" option. Gated by `require_module_access("purchase_report")`
- Migration `0020_seed_purchase_report_module.py` seeds the module (Inventory group, sort 24) + `admin` grant, same pattern as prior seed migrations
- New frontend module `pages/modules/purchase_report/index.py`: two `Table`s (`by_supplier`/`by_material`, endpoints inferred from `name=`) stacked on one page, a shared date-range pair via two standalone `DateForm` instances (reused outside a `Form` context), and a per-table `ft.Dropdown` scoping select (built the same hand-rolled way as `stock_out/item_new.py`'s material picker). Since `DateForm` has no `on_change` hook, filters apply via an explicit toolbar "Apply Filters" button rather than live-per-keystroke - reads current date/dropdown state, sets each table's `custom_param`, resets to page 1, refetches both
- Verified end-to-end against a real MariaDB + backend container: fresh `podman compose up -d --build` (migration 0020 applied cleanly on top of #7's 0019), then created 2 suppliers / 2 materials / 3 receiving headers with items spanning 3 different months, and confirmed by hand-calculation: unfiltered totals correct for both tables; date-range filter (Jan only) correctly narrows to just the one January header; open-ended `start_date-filter` (>= Feb) correctly includes Feb+Mar headers only; `supplier_id-filter`/`material_id-filter` each correctly narrow to exactly one row while leaving the other table's grouping unaffected; omitting all filters reproduces the full unfiltered aggregate. Cleaned up all test rows (in FK order: stocks -> receiving_items -> receiving_headers -> inventory_values -> materials -> suppliers) and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment), and the CSV/XLSX export endpoints specifically (verified via the identical, already-established `export_response` mechanism used by every other report/list screen, but not re-clicked through for this module)
- Scope: backend, frontend
- Files: backend/src/core/table_query.py, backend/src/repository/purchase_report_repository.py (new), backend/src/routers/purchase_report.py (new), backend/alembic/versions/0020_seed_purchase_report_module.py (new), backend/src/main.py, frontend/src/pages/modules/purchase_report/{__init__,index}.py (new), AGENTS.md
- Issue #8 addressed on GitHub

## [2026-07-15] — feat(reports): add start/end date range filter to usage_report (issue #9)
- Reused #8's `core/table_query.py::apply_field_filters` convention verbatim, no new helper needed: `usage_report_repository.py::list_usage_by_department` gained `start_date`/`end_date` params, filtering `StockOutHeaderModel.date` via `apply_field_filters(query, [(date, ">=", start_date), (date, "<=", end_date)])`, applied after the existing `apply_keyword_filter`
- `routers/usage_report.py`: both `get_detail` and its `export_detail` twin now accept `start_date-filter`/`end_date-filter` (same `_parse_date` blank/invalid-tolerant parsing as `purchase_report.py`), so a filtered report exports exactly what's on screen — matching the Table export convention's existing behavior for `table-keyword-filter`/sort
- `usage_report/index.py` gained the same two-standalone-`DateForm` + toolbar "Apply Filters" button pattern #8 introduced (minus the dropdowns/second table, since this report has no supplier/material scoping filter, out of scope per the issue) — reads both date values, sets the single `Table`'s `custom_param`, resets to page 1, refetches
- Verified end-to-end against a real MariaDB + backend container: created one department, one material, received 100 units, then issued 10 units on 2026-01-15 and 5 units on 2026-03-15 under that department. Confirmed by hand-calculation: unfiltered totals (qty15/cost45) correct; both-bound Jan-only range narrows to qty10/cost30; open-ended `start_date-filter` (>=Feb) narrows to qty5/cost15 (excludes Jan); open-ended `end_date-filter` (<=Jan 31) narrows to qty10/cost30 (excludes March); a range excluding both transactions returns no row for that department; `export_detail` with the same Jan filter produces a CSV with exactly the filtered row. Cleaned up all test rows and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — the added `DateForm`/toolbar-button UI mirrors #8's already-hand-verified `purchase_report` pattern exactly
- Scope: backend, frontend
- Files: backend/src/repository/usage_report_repository.py, backend/src/routers/usage_report.py, frontend/src/pages/modules/usage_report/index.py, AGENTS.md
- Issue #9 addressed on GitHub

## [2026-07-15] — feat(table): generic per-column filtering ported from senar's L_database (issue #10)
- Read senar's `L_database.php` (`filter()` ~line 538, `filter_numeric()` ~line 1078, `filter_table_keyword()` already-ported), `y.form.js` (per-table `row-y-filter-{table}` filter row, `{field}-filter` element ids), and `Table_ap_log_api_aol.php` (a real `$select`/`$having`/`$numeric` wiring example) as reference material — cross-language port (PHP7/CI3 Active Record + jQuery -> Python/SQLAlchemy + Flet), not a copy
- New `core/table_query.py::apply_column_filters(query, query_params, column_map, numeric_fields=())` — every column in `column_map` gets an independently-optional `{field}-filter`, LIKE-by-default or routed to `_parse_numeric_filter` (ported `filter_numeric()`: bare number = exact match, else `and`-joined `{operator}{number}` segments — `>=`, `<=`, `>`, `<`, `=`, `!=`/`<>`, e.g. `>=5and<=10`; a literal `"and"` substring split matching PHP's `explode()`, not a regex word boundary) for columns named in `numeric_fields`. Matches senar's own precedence exactly: returns the query untouched if `table-keyword-filter` is present (free-text search and per-column filters are mutually exclusive on the PHP side). `_FIELD_FILTER_OPS` (from #8) extended with `>`, `<`, `!=` to cover the new operators
- Reference implementation, same rollout pattern as multi-column sort's `master_location`: `module_group_repository.py::list_groups` (`name` text/LIKE, `sort` numeric/operator-syntax — one simple, non-aggregate list exercising both code paths) + `routers/module_group_admin.py` (`get_detail`/`export_detail` both gained a `request: Request` param, forwarding `request.query_params` straight through — `{field}-filter` names aren't individually enumerable ahead of time, same reason `parse_sort_fields` needs raw query params for `sort-fields[N][field]`)
- New frontend `components/table/filter_row.py::FilterRow` — collapsible row of `ft.TextField`s, one per field marked `"filterable": True` (`"numeric_filter": True` swaps in an operator-syntax hint), toggled via a toolbar button only added when at least one field opts in. Wired into `components/table/table.py`: `Table._build_toolbar_with_filter_row()` folds the filter row into the *same* top-level `controls` slot the toolbar alone occupied (as `ft.Column([toolbar, filter_row])`), rather than adding a new slot that would have shifted the hardcoded `col.controls[1]`/`[2]` header/body indices `Table.load()`/`_handle_resize_commit()`/`_handle_sort_change()` all rely on; `Table.get_data()` appends `FilterRow.serialize()` alongside the existing params. `master_module_group/index.py`'s `name`/`sort` fields marked filterable as the reference screen
- Verified end-to-end against a real MariaDB + backend container: created 4 test module groups spanning distinct `sort` values, confirmed every numeric operator (exact match, `>=`, `<=`, `>`, `<`, `!=`, `<>`, an `and`-joined range) and the LIKE `name-filter` each produce correct results; blank/absent filters reproduce the unfiltered list; a `table-keyword-filter` present alongside `sort-filter` correctly ignores the per-column filter (matching the ported PHP precedence); an unrelated `sort-fields[...]` param alongside `sort-filter` doesn't interfere; `master_location`'s existing multi-column sort still works unmodified (no regression from the `table_query.py` changes); `export_detail` honors the same `name-filter` as `get_detail`. Cleaned up test rows and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — `FilterRow`'s toggle/apply/clear interactions were built to the same proven page-passive-construction/safe-update patterns already used elsewhere in `components/table/`, but a live click-through is still outstanding
- Not required by this issue (explicitly deferred, per the issue's own scope note): migrating #8/#9's hand-rolled `apply_field_filters` usage onto this generic mechanism, or rolling `filterable`/`numeric_filter` out to any other existing list screen
- Scope: backend, frontend
- Files: backend/src/core/table_query.py, backend/src/repository/module_group_repository.py, backend/src/routers/module_group_admin.py, frontend/src/components/table/filter_row.py (new), frontend/src/components/table/table.py, frontend/src/pages/modules/master_module_group/index.py, AGENTS.md
- Issue #10 addressed on GitHub

## [2026-07-15] — fix(table): sort icon to the right of the label; default-on per-column filters everywhere
- User feedback on #10: (1) sort icon should sit at the column's right edge, not glued to the label text; (2) per-column filtering should be the default on every table, opt-out via `"filter": False`, rather than opt-in
- `components/table/columns.py::_build_data_columns()`: field icon + label build as one `left_content` group; a sortable column additionally wraps `[left_content, sort_icon]` in a second `ft.Row(alignment=SPACE_BETWEEN)` that fills the fixed-width header Container, pushing the sort icon to the column's far-right edge instead of immediately after the text
- `components/table/filter_row.py::FilterRow`: flipped from opt-in (`"filterable": True`) to opt-out (`"filter": False`) — every field with a `name` and a non-hidden `"type"` gets a filter box by default. Numeric-operator detection is now automatic too, reusing whatever a field already sets for right-alignment (`"format": "number"` / `"is_numeric"`) instead of a second, separately-remembered `"numeric_filter"` flag (kept as an optional override). `master_module_group/index.py`'s now-redundant explicit `"filterable"` markers removed
- Backend rollout: wired `apply_column_filters` onto every non-aggregate `list_*` repository/router pair in the app — `location_repository.py` (reusing its existing sort `column_map`), `supplier_repository.py`, `department_repository.py`, `category_repository.py`, `material_repository.py`, `module_repository.py`, `user_repository.py`, `receiving_repository.py` (both `list_headers`, including its existing supplier outer-join, and `list_items_by_header`), `stock_out_repository.py` (both `list_headers` and `list_items_by_header`) — each router gained (or reused) a `request: Request` param forwarding `request.query_params` through. Deliberately left the three aggregate repositories (`stock_repository`/`usage_report_repository`/`purchase_report_repository`) unwired — `apply_column_filters` has no `HAVING`/aggregate-column routing yet; #8/#9's own `apply_field_filters` usage on those reports is unaffected
- Documented known gap: a handful of fields are join-derived/denormalized values with no real column in their own repository's query (`stock_out` header `department_name`, item sub-tables' `material_code`/`location_code`, `master_material`'s `supplier_name`/`category_name`) — the filter box still renders for these (the frontend can't know a field has no backend mapping), but `apply_column_filters` silently skips any field not in `column_map`, so the box is currently inert rather than wrong
- Verified end-to-end against a real MariaDB + backend container: LIKE and numeric-operator filters confirmed correct on `master_supplier`, `master_department`, `master_category`, `master_module_group`, `master_location`, `ap_module`, `ap_master_user`, `master_material`, `stock_out` items (numeric `qty_out`, LIKE `remarks`, an out-of-range numeric filter correctly returning empty), and `stock_in` headers' joined `supplier_name`; regression-checked that `master_location`'s existing multi-column sort and `master_supplier`'s keyword search still work unchanged. Cleaned up all test rows and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — the sort-icon repositioning and the now-ubiquitous filter toggle button are built on the same proven patterns already exercised elsewhere, but a live visual check is still outstanding
- Scope: backend, frontend
- Files: backend/src/core/table_query.py (unchanged, reused as-is), backend/src/repository/{location,supplier,department,category,material,module,user,receiving,stock_out}_repository.py, backend/src/routers/{master_location,master_supplier,master_department,master_category,master_material,module_admin,user_admin,stock_in,stock_out}.py, frontend/src/components/table/{columns,filter_row}.py, frontend/src/pages/modules/master_module_group/index.py, AGENTS.md

## [2026-07-15] — refactor(inventory): remove supplier_id from materials table
- Issue #11 created on GitHub
- Scope: backend, frontend
- Labels: enhancement, backend, frontend

## [2026-07-15] — #4, #5 status synced: ready-for-review → closed
- Title: feat(frontend): client-side CSV/XLSX upload into table input fields via hamburger menu (#4)
- Title: feat(frontend): bulk create records from CSV/XLSX on module new screens (#5)
- Platform: GitHub

## [2026-07-15] — refactor(inventory): remove supplier_id from materials table (issue #11)
- A material can be sourced from many different suppliers over time; supplier tracking already lives at the receiving-header level (`receiving_headers.supplier_id`, added in #7), so `materials.supplier_id` (added alongside `category_id` in #6) was redundant and removed entirely
- `models/material.py`: dropped the `supplier_id` column. New migration `0021_remove_supplier_id_from_materials.py` drops the FK/index/column (`op.batch_alter_table`, exact reverse of `0007`'s original addition); `downgrade()` re-adds it nullable
- `repository/material_repository.py`: `create_material`/`update_material` drop the `supplier_id` parameter
- `routers/master_material.py`: dropped `supplier_id` from `_serialize`/`submit`/`submit_bulk`, removed the now-unused `call_supplier_id_select` endpoint and the unused `SupplierRepository` import, dropped the "Supplier" export column
- Frontend `master_material/{new,edit}.py`: removed the `supplier_id` select field; `master_material/index.py`: removed the `supplier_name` label column
- Confirmed `receiving_headers.supplier_id` (#7) and every one of its usages (`stock_in` header form/select, `purchase_report`'s by-supplier breakdown) are completely untouched — this only removed the material-level link
- Verified end-to-end against a real MariaDB + backend container: migration 0021 applied cleanly on a fresh boot, live schema confirms `materials.supplier_id` gone and `receiving_headers.supplier_id` intact, `call_supplier_id_select` on `master_material` now 404s, creating a material with only `category_id` works and its list/get responses carry no `supplier_id`/`supplier_name` keys, and both the `stock_in` receiving-header supplier flow and `purchase_report`'s `call_supplier_id_select` continue to work unchanged. Cleaned up test rows and tore the stack back down
- Not verified: the Flet UI in an actual browser (no browser available in this environment) — the removed field/label mirror the already browser-verified pattern elsewhere in this module
- Scope: backend, frontend
- Files: backend/src/models/material.py, backend/src/repository/material_repository.py, backend/src/routers/master_material.py, backend/alembic/versions/0021_remove_supplier_id_from_materials.py (new), frontend/src/pages/modules/master_material/{new,edit,index}.py, AGENTS.md
- Issue #11 addressed on GitHub

## [2026-07-15] — docs: sync README.md with issue #11 (materials no longer carry supplier_id)
- Section 6 (Setting up master material): swapped the stale "Supplier" field bullet for "Category" (the field that actually exists on the form since #6), and added a note pointing to per-receiving-batch supplier tracking
- Section 9 (Stock in): documented the header's **Supplier** field (added by #7), which the README had never mentioned
- Scope: docs
- Files: README.md

## [2026-07-15] — feat(infra): add start.ps1/start.sh launcher scripts with docker/podman auto-detect
- Issue #12 created on GitHub
- Scope: infra
- Labels: enhancement, infra

## [2026-07-15] — chore(infra): move Dockerfile-backend/-frontend/-mariadb into their service subfolders
- Issue #13 created on GitHub
- Scope: infra
- Labels: chore, infra

## [2026-07-15] — feat(backend): seed default admin username/password/TOTP from .env instead of hardcoding
- Issue #14 created on GitHub
- Scope: backend
- Labels: enhancement, backend

## [2026-07-15] — feat(frontend): make default backend server URL configurable via .env instead of hardcoding
- Issue #15 created on GitHub
- Scope: frontend
- Labels: enhancement, frontend

## [2026-07-15] — chore(infra): move Dockerfile-backend/-frontend/-mariadb into their service subfolders (issue #13)
- Moved `Dockerfile-backend` → `backend/Dockerfile`, `Dockerfile-frontend` → `frontend/Dockerfile`, `Dockerfile-mariadb` → `database/Dockerfile` (`git mv`, preserving history)
- `compose.yml`'s three `build.dockerfile` paths updated to match; `build.context` stays `.` (repo root) for all three since each Dockerfile's `COPY` instructions already reference `backend/...`/`frontend/...`/`database/...` relative to that context — no COPY paths needed to change
- Updated every `AGENTS.md` reference to the old root-level filenames
- Verified: `podman compose -f compose.yml build` rebuilt all three images successfully from the new paths (cache hits confirm identical build content, just relocated)
- Scope: infra
- Files: backend/Dockerfile (moved), frontend/Dockerfile (moved), database/Dockerfile (moved), compose.yml, AGENTS.md
- Issue #13 addressed on GitHub

## [2026-07-15] — feat(infra): add start.ps1/start.sh launcher scripts with docker/podman auto-detect (issue #12)
- Added `start.sh` (POSIX) and `start.ps1` (PowerShell): both detect `podman` first, falling back to `docker` if podman isn't on PATH, then run `<engine> compose -f compose.yml up -d --build`; exit with a clear error if neither is found
- `README.md`'s "Start the stack" section now leads with `./start.sh`/`.\start.ps1`, keeping the raw `podman compose ...` command documented as what the script runs under the hood
- Verified: ran both `./start.sh` and `.\start.ps1` against the real local Podman install — both correctly detected `podman`, built all three images, and brought the stack up healthy (`sfsis-mariadb`/`sfsis-backend` confirmed `Healthy`, backend/frontend HTTP roots returned 200)
- Scope: infra
- Files: start.sh (new), start.ps1 (new), README.md
- Issue #12 addressed on GitHub

## [2026-07-15] — feat(backend): seed default admin username/password/TOTP from .env instead of hardcoding (issue #14)
- `core/config.py` gained `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_TOTP_SECRET`, read from env with the original hardcoded values (`admin`/`admin1234#`/empty) as fallback defaults
- `0004_seed_default_superuser.py` now seeds from these instead of hardcoded module-level constants, and seeds `users.totp_secret` from `ADMIN_TOTP_SECRET` when set (previously always seeded as `""`)
- Every later migration that grants built-in module access to the seeded admin by username (`0006`, `0008`, `0010`, `0011`, `0014`, `0015`, `0016`, `0018`, `0020`) now resolves `config.ADMIN_USERNAME` instead of a hardcoded `"admin"` literal, so a custom `ADMIN_USERNAME` still receives every grant
- `compose.yml`'s `backend` service `environment:` block passes through `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_TOTP_SECRET`; `example.env`/`.env` already declared these (added ahead of this issue) — now actually wired up
- `README.md`/`AGENTS.md` updated: `.env` fields table, login walkthrough, and the Bootstrap/migration-0004 description now describe env-driven seeding instead of a fixed `admin`/`admin1234#`. Documented explicitly that these vars only take effect on a fresh database (first `alembic upgrade head`), not on an already-seeded install
- Verified end-to-end against a real, fully fresh MariaDB (isolated bind mount, not the persistent dev `./database` — that data was left untouched) with `ADMIN_USERNAME=testadmin`/`ADMIN_PASSWORD=TestPass123!`: `testadmin` logged in successfully (200) and had every expected module tile on its home screen (confirming grants from 0006/0008/etc. followed the custom username); the old hardcoded `admin`/`admin1234#` login correctly failed (401, no such user seeded)
- Scope: backend
- Files: backend/src/core/config.py, backend/alembic/versions/{0004_seed_default_superuser,0006_seed_default_modules_and_permissions,0008_seed_master_supplier_module,0010_seed_master_department_module,0011_seed_usage_report_module,0014_seed_master_module_group_module,0015_create_mail_config_table,0016_create_app_config_table,0018_seed_master_category_module,0020_seed_purchase_report_module}.py, compose.yml, README.md, AGENTS.md
- Issue #14 addressed on GitHub

## [2026-07-15] — feat(frontend): make default backend server URL configurable via .env instead of hardcoding (issue #15)
- `frontend/src/repository/server_url.py`'s `DEFAULT_SERVER_URL` now reads from `FRONTEND_DEFAULT_SERVER_URL` at import time (`os.getenv`), falling back to the existing `"http://backend:5000"` literal if unset — behavior unchanged for anyone not using the new var
- `compose.yml`'s `frontend` service `environment:` block passes through `${FRONTEND_DEFAULT_SERVER_URL:-http://backend:5000}` (inline compose-level default, so existing `.env` files without the var still work); added to `example.env`/`.env`
- The existing `ServerURL.is_configured()` "never configured vs. genuinely saved" tracking is untouched by this change — it only affects what the *default* resolves to
- `AGENTS.md`'s repository/persistence and "Networking / server address handling" sections updated to document the override
- Verified inside the running `sfsis-frontend` container: with `FRONTEND_DEFAULT_SERVER_URL=http://custom-backend:9999` injected, `DEFAULT_SERVER_URL` resolved to that value; with the var unset, it correctly fell back to `http://backend:5000`
- Scope: frontend
- Files: frontend/src/repository/server_url.py, compose.yml, example.env, AGENTS.md
- Issue #15 addressed on GitHub

## [2026-07-16] — feat(inventory): add unit of material (UOM) master table, link to materials, show in qty tables
- Issue #16 created on GitHub
- Scope: backend, frontend
- Labels: enhancement, backend, frontend

## [2026-07-16] — feat(inventory): replace material deletion with active/inactive status flag
- Issue #17 created on GitHub
- Scope: backend, frontend
- Labels: enhancement, backend, frontend

## [2026-07-16] — feat(inventory): unit of material (UOM) master table, required on every material, shown in every qty table (issue #16)
- Backend: new `UnitOfMaterialModel`/`UnitOfMaterialRepository` (`units_of_material` table: `code`, `name`) — **no delete method/endpoint**, per the issue's explicit "no delete UOM" requirement; a unit can never be removed once created since every material links to exactly one
- Backend: new `master_unit_of_material` router (`C_master_unit_of_material` prefix, gated by `require_module_access`) — `get_detail`/`export_detail`/`get`/`submit`/`submit_bulk`, deliberately no `/delete` route; wired into `main.py`
- Backend: `materials.unit_id` added as a **non-nullable** FK to `units_of_material.id` (migration `0022_create_units_of_material_table.py` — creates the table, seeds one default unit `PCS`/`Pieces`, adds the column nullable, backfills every pre-existing material onto the default unit, then sets it `NOT NULL` + FK via `op.batch_alter_table`); `0023_seed_master_unit_of_material_module.py` seeds the module (Master group, sort 14) + admin grant, same pattern as `0018`
- Backend: `material_repository.py`'s `create_material`/`update_material` now require `unit_id`; `master_material.py` router's `submit` rejects a blank `unit_id` with `{"error": "Unit of Material is required"}`, `_serialize` returns `unit_id`/`unit_code`/`unit_name`, new `call_unit_id_select` endpoint, `submit_bulk` validates the Unit column same as Category
- Backend: every qty-bearing repository/router now joins `UnitOfMaterialModel` (via `MaterialModel.unit_id`) and returns `unit_code`/`unit_name`: `stock_repository.py` (`list_stock_summary`, `list_stock_by_material`), `stock_in.py`/`stock_out.py`'s `_serialize_item`, `usage_report_repository.py`, `purchase_report_repository.py::list_by_material`. Deliberately **not** wired on `purchase_report_repository.py::list_by_supplier` — that table aggregates qty across many different materials that may carry different units, so a single unit column there would misrepresent the total
- Frontend: new `master_unit_of_material` module (`{index,new,edit}.py`, same shape as `master_category` but `edit.py` has no delete button); `master_material`'s `new.py`/`edit.py` gained a required `unit_id` select field, `index.py` a read-only `unit_name` column; every qty-showing table/screen gained a `unit_name` column: `stock_browse/index.py`, `stock_in/item_table.py`, `stock_out/item_table.py`, `stock_out/item_new.py`'s per-location Qty Issue table, `usage_report/index.py`, `purchase_report/index.py`'s by-material table only (by-supplier table intentionally unchanged, matching the backend decision above)
- `AGENTS.md` updated: Inventory Domain section documents the new master table/migrations/non-nullable FK, and a new "Unit of material (UOM) display convention" paragraph documents which qty tables carry the unit column and why by-supplier doesn't
- Verified: full migration chain `0001` → `0023` run from a genuinely empty SQLite database (via a throwaway script monkeypatching `core.config.DATABASE_URL` before import, `uv run --no-project --with <deps>` since both `backend/.venv` and `frontend/.venv` are still fought over by the container per the known dev-env gotcha), confirmed the seeded default unit (`PCS`) is present; then a full `TestClient` HTTP walk: login → UOM list shows seeded `PCS` → create a `KG` unit → `POST .../delete` on the UOM router correctly 404s (no such route) → material submit without `unit_id` rejected → material submit with `unit_id` succeeds and list returns `unit_code`/`unit_name` → receive stock → `stock_in` items list, `stock_browse`, `get_stock_by_material` all return `unit_code: "KG"` → issue stock → `stock_out` items list, `usage_report`, `purchase_report`'s by-material table all return `unit_code: "KG"` → `purchase_report`'s by-supplier table still 200 (correctly has no unit field). All modified/new frontend and backend files also syntax-checked with `py_compile`. **Not verified**: the actual browser UI (no live frontend venv/browser in this environment) — the select field, table columns, and bulk-upload Unit column should get a quick visual check before this is considered fully done
- Scope: backend, frontend
- Files: `backend/src/models/unit_of_material.py` (new), `backend/src/repository/unit_of_material_repository.py` (new), `backend/src/routers/master_unit_of_material.py` (new), `backend/src/models/material.py`, `backend/src/repository/material_repository.py`, `backend/src/routers/master_material.py`, `backend/src/repository/stock_repository.py`, `backend/src/routers/{stock_in,stock_out,stock_browse,usage_report,purchase_report}.py`, `backend/src/repository/{usage_report_repository,purchase_report_repository}.py`, `backend/src/main.py`, `backend/alembic/env.py`, `backend/alembic/versions/{0022_create_units_of_material_table,0023_seed_master_unit_of_material_module}.py`, `frontend/src/pages/modules/master_unit_of_material/{__init__,index,new,edit}.py` (new), `frontend/src/pages/modules/master_material/{index,new,edit}.py`, `frontend/src/pages/modules/{stock_browse/index,stock_in/item_table,stock_out/item_table,stock_out/item_new,usage_report/index,purchase_report/index}.py`, `AGENTS.md`
- Issue #16 addressed on GitHub

## [2026-07-16] — feat(inventory): seed a full default unit-of-material catalog via Alembic
- Issue #18 created on GitHub, follow-up to #16 (user opted for a separate tracked issue rather than amending #16, since #16's own migration `0022` only seeds `PCS` as a bootstrap-backfill default, not a full catalog)
- Scope: backend
- Labels: enhancement, backend

## [2026-07-16] — feat(inventory): implement issue #18, seed 22 more default units of material
- New migration `backend/alembic/versions/0024_seed_default_units_of_material.py` seeds L/Litres, G/Grams, KG/Kilograms, LB/Pounds, OZ/Ounces, GAL/Gallons, ML/Millilitres, CTN/Carton, PACK/Pack, PLT/Pallet, ROLL/Roll, BOX/Boxes, DZ/Dozens, BTL/Bottles, CASE/Cases, M/Meters, CM/Centimeters, FT/Feet, IN/Inches, UNIT/Units, SET/Sets, PAIR/Pairs — `PCS` deliberately excluded from this migration's own list since it's already seeded by `0022` (kept that row's ownership unambiguous rather than re-listing it here)
- Match-by-code idempotent (`SELECT` before `INSERT`, same guard as `0022`); `downgrade()` removes exactly the rows this migration added, using a per-row `SAVEPOINT` (`bind.begin_nested()`) around each delete so a unit a material has since been created against (FK-blocked) is silently skipped rather than aborting the whole downgrade — a plain `bind.rollback()` was tried first and rejected during verification, since it would have ended the *entire* migration transaction on the first blocked row instead of just that one delete
- Verified against a fresh SQLite database (`uv run --no-project --with <deps>`, same workaround as #16 since both `.venv`s are still fought over by the container per the known dev-env gotcha): full chain `0001`→`0024` applies cleanly; all 23 expected codes present (22 new + the `PCS` from `0022`); re-running `upgrade()` doesn't duplicate; `downgrade()` to `0023` removes all 22 and leaves only `PCS`. The FK-skip path specifically needed SQLite's foreign-key enforcement pragma enabled by hand in the test script (`PRAGMA foreign_keys=ON` via a global `Engine` connect-event listener) — neither this app's own engine (`models/base.py`) nor alembic's migration connection ever enable it, which is a pre-existing gap in how this repo's SQLite verification exercises FK guards generally, not something introduced or fixed here; created a material against a seeded unit, re-ran `downgrade()`, confirmed that one unit was skipped while every other unseeded-by-materials unit was still removed
- Scope: backend
- Files: `backend/alembic/versions/0024_seed_default_units_of_material.py` (new), `AGENTS.md`
- Issue #18 addressed on GitHub

## [2026-07-16] — feat(inventory): replace material deletion with active/inactive status (issue #17)
- Backend: `materials.is_active` (non-nullable `Boolean`, default `True`) added via migration `0025_add_is_active_to_materials.py` — single-step `add_column(..., nullable=False, server_default=sa.true())`, no backfill needed since a boolean default applies to existing rows at ALTER time (unlike `unit_id`'s FK, which needed a real row to point at first)
- Backend: `master_material.py` router's `/delete` endpoint **removed entirely** (matching `master_unit_of_material`'s "no delete" precedent from #16) — `material_repository.py`'s `delete_material` method removed too, `IntegrityError` import dropped since nothing catches it anymore; `submit` gained an `is_active` form field (`_parse_bool`, same helper/convention as `user_admin.py`), `_serialize` returns `"true"/"false"`, new `call_is_active_select` returns the same static Yes/No options as `ap_master_user`'s, `submit_bulk` and `_EXPORT_COLUMNS` updated to include it
- Backend: `stock_in.py::submit_item`'s **create path only** now looks up the target material and rejects with `{"error": "Cannot receive: material is inactive"}` if `is_active` is `False`; the update path (editing an already-received item) is untouched, since that material was receivable at the time it was first received and retroactively re-validating it would be surprising
- Frontend: `master_material/new.py` and `edit.py` gained an `is_active` select field (icon `CHECK_CIRCLE`, same as `ap_master_user`'s); `edit.py`'s delete button + `callback_delete` + its now-unused `HttpClient` import removed entirely; `index.py` gained a read-only `is_active` label column
- Verified against a fresh SQLite database (`uv run --no-project --with <deps>`, same workaround as #16/#18): full migration chain `0001`→`0025` applies cleanly; `POST C_master_material/delete` returns 404 (route genuinely gone, not just erroring); `call_is_active_select` returns the expected Yes/No options; a newly created material defaults to `is_active: "true"`; deactivating it and attempting `POST C_stock_in/submit_item` (create) returns the exact `"Cannot receive: material is inactive"` error; reactivating lets receiving succeed; **editing** an already-received item for a since-deactivated material still succeeds (update path correctly unaffected); `stock_browse` still returns the inactive material's on-hand qty/value unchanged. All touched files also pass `py_compile`
- Scope: backend, frontend
- Files: `backend/src/models/material.py`, `backend/src/repository/material_repository.py`, `backend/src/routers/master_material.py`, `backend/src/routers/stock_in.py`, `backend/alembic/versions/0025_add_is_active_to_materials.py` (new), `frontend/src/pages/modules/master_material/{new,edit,index}.py`, `AGENTS.md`
- Issue #17 addressed on GitHub

## [2026-07-16] — #17 status changed: open → closed
- Title: feat(inventory): replace material deletion with active/inactive status flag
- Platform: GitHub

## [2026-07-16] — #1 status changed: open → closed
- Title: feat(infra): scaffold full-stack app with MariaDB, FastAPI, and Flet via Podman Compose
- Platform: GitHub

## [2026-07-16] — fix(frontend): table search bar styling regressions; lighter placeholder color on table + home search bars
- Issue #19 created on GitHub
- Scope: frontend
- Labels: bug, frontend
- User-reported regressions in the compact `TextField`-based table search bar (rebuilt for #2): search/clear icons only show while focused (should always show), clear icon padding/position too far right, text not vertically centered, border radius smaller than every other input in the app (8 vs. the established 10). Also: placeholder text on both the table search bar and the home module search bar is too close in contrast to real typed text

## [2026-07-16] — fix(frontend): table search bar styling regressions; lighter placeholder color (issue #19)
- Root cause of the icon-visibility bug: `components/table/search_bar.py`'s `TextField` used Flet's `prefix`/`suffix` slots (`FormFieldControl.prefix`/`.suffix`) for the search/clear icons — per Flutter's `InputDecoration`, those inline affix slots only render once the field is focused or non-empty, unlike `prefix_icon`/`suffix_icon`, which always render. `components/form/input.py`'s leading icon already correctly used `prefix_icon` and never had this bug — confirmed by reading Flet 0.85.3's own `form_field_control.py` source (`prefix`: "A Control to place on the line before the input" vs. `prefix_icon`: "An icon that appears before the editable part... within the decoration's container", no focus caveat)
- Fix: swapped `prefix`→`prefix_icon` and `suffix`→`suffix_icon` (still the same clickable `ft.IconButton` for clear) — both now render unconditionally
- Fix: clear icon's "too far right" gap was Flutter reserving its default ~48dp tap-target for the suffix slot; added `suffix_icon_size_constraints=ft.BoxConstraints(min/max width/height=24)` to match the icon's own compact size, eliminating the extra gap
- Fix: vertical centering — added explicit `text_vertical_align=ft.VerticalAlignment.CENTER` and a small non-zero vertical `content_padding` (was `0`)
- Fix: `border_radius` changed `8` → `10`, matching every other input in the app (`components/form/input.py`/`date.py`/`label.py`/`select.py`)
- Fix: placeholder contrast — added `hint_style=ft.TextStyle(color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE), size=13)` to the table search bar and the equivalent `bar_hint_text_style` (same opacity/color) to `components/home/search_bar.py`'s `ft.SearchBar`, so the hint text ("Search in table..."/"Search modules...") is now visibly lighter than real typed text (`color`/`bar_text_style` stay full-opacity `ON_SURFACE`)
- Verified by constructing the actual, unmodified `TableSearchBar`/`HomeSearchBar` classes (not just isolated snippets) inside a real Flet 0.85.3 environment (`uv run --no-project --with flet==0.85.3 --with requests --with flet-datatable2`, working around the known bind-mounted-venv dev gotcha) with a fake `Page`/`Storage` harness — both build without error, and the resulting `prefix_icon`/`suffix_icon`/`suffix_icon_size_constraints`/`text_vertical_align`/`hint_style`/`bar_hint_text_style` attributes all hold the expected values. **Not verified in a real browser** — no browser available in this environment; the user should do a quick visual check (unfocused state shows both icons, clear icon sits flush with the edge, text centered, radius matches other inputs, placeholder visibly lighter on both bars)
- Scope: frontend
- Files: `frontend/src/components/table/search_bar.py`, `frontend/src/components/home/search_bar.py`
- Issue #19 addressed on GitHub

## [2026-07-16] — fix(frontend): redesign table filter row — per-column alignment, live filtering, inline clear
- Issue #20 created on GitHub
- Scope: frontend
- Labels: bug, frontend
- User-reported gaps in the per-column filter row (#10): fields don't align with the table body's actual column positions/widths and don't track resizing; needs a leading filter icon + trailing per-field clear icon (auto-unfilters just that column); the row-level "Apply Filters"/"Clear Filters" buttons should be removed in favor of live per-keystroke filtering; hiding the filter row should also clear every active column filter; background/border-radius should match the table search bar (`SURFACE_CONTAINER_HIGH`, radius 10, per #19)

## [2026-07-16] — fix(frontend): redesign table filter row — per-column alignment, live filtering, inline clear (issue #20)
- `filter_row.py::FilterRow` rebuilt around one fixed-width `ft.Container` per **visible** column (not just filterable ones — a non-filterable column still reserves its slot as an empty `Container`, so every filter field after it stays aligned), using `Columns.widths` + the same `TABLE_HORIZONTAL_MARGIN`/`TABLE_COLUMN_SPACING` constants `header.py`/`body.py`'s `ft.DataTable`s are built with — a plain `ft.Row` of these lines up pixel-for-pixel with the real table body, no absolute positioning needed (`Table` now passes `columns=self.columns` into `FilterRow.__init__`)
- New `FilterRow.reposition()` patches each field's `Container.width` in place from the current `Columns.widths` (cheap — unlike `ft.DataTable`, a plain `Container` genuinely shrinks on a live width patch, no rebuild). `table.py` calls it from every place `Columns.widths` can change: `Table.load()`, `Table.build()`'s pending-data branch, and `Table._handle_resize_commit()` (resize drag tick / double-tap reset) — the same trigger points `Columns._reposition_handles()` already uses for the resize handles
- Each filterable field gained a leading filter icon (`prefix_icon=ft.Icons.FILTER_ALT`) and a trailing per-field clear icon (`suffix_icon=ft.Icons.CLEAR`, `suffix_icon_size_constraints` to avoid the same oversized-tap-target gap issue #19 fixed on the search bar) that clears only that column's own filter value and immediately re-fetches; `border_radius=10` and `bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH` now match the table search bar (was `SURFACE_CONTAINER_LOW`, radius unset)
- Filtering is now live: every field's `on_change`/`on_submit` call the same `on_apply` callback (a keystroke re-fetches immediately, same pattern the table search bar already used) — the row's trailing "Apply Filters"/"Clear Filters" `IconButton`s are gone entirely
- `FilterRow.toggle()` now clears every field's value and re-fetches (only) when transitioning from visible→hidden, so a hidden filter row never leaves a column filter silently still applied server-side
- Verified by constructing the real, unmodified `Table`/`FilterRow`/`Columns` classes end-to-end (not isolated snippets) in a real Flet 0.85.3 environment with a fake `Page`/`Storage`/`HttpClient` harness (`uv run --no-project --with flet==0.85.3 --with requests --with flet-datatable2 --with openpyxl`): initial field-container widths exactly match `Columns.widths`; a resize drag (`handle_drag`) changes widths and every filter field followed via `reposition()`; each field's `border_radius`/icons/row `bgcolor` hold the expected values; the row contains exactly one container per visible field (no leftover Apply/Clear-all buttons); typing into a field triggers exactly one refetch; clearing one field only clears that field (not others) and still refetches; toggling the row from visible to hidden clears every field and refetches. `BaseControl.update()` was stubbed out in the test harness only (this script never attaches controls to a real live Page, which `.update()` requires) — `FilterRow`'s own control updates already go through its pre-existing `RuntimeError`-safe `_safe_update` pattern, so this doesn't mask anything. **Not verified in a real browser** — no browser available in this environment; a visual check (fields sit exactly under their header/body columns, follow a live drag-resize, icons/colors match the search bar) is still worth doing before merging
- `AGENTS.md`'s per-column-filter documentation updated to describe the new alignment/live-filter/clear/hide-clears-all design in place of the old "free-standing row, not worth aligning" rationale
- Scope: frontend
- Files: `frontend/src/components/table/filter_row.py`, `frontend/src/components/table/table.py`, `AGENTS.md`
- Issue #20 addressed on GitHub

## [2026-07-16] — #16 status changed: ready-for-review → closed
- Title: feat(inventory): add unit of material (UOM) master table, link to materials, show in qty tables
- Platform: GitHub

## [2026-07-16] — #18 status changed: ready-for-review → closed
- Title: feat(inventory): seed a full default unit-of-material catalog via Alembic
- Platform: GitHub

## [2026-07-16] — chore(frontend): extract shared Button component to DRY up toolbar add_*_button methods
- Issue #21 created on GitHub
- Scope: frontend
- Labels: chore, frontend
- User noticed `add_button`/`add_new_button`/`add_save_button`/`add_submit_button` are each independently duplicated across `components/list/toolbar.py`, `components/module/toolbar.py`, and `components/table/toolbar.py` — proposed a shared Button component under `components/` (configurable position/icon/title/tooltip/color/size, Material 3 defaults) so future buttons (back, submit, menu, search) can reuse the same standard

## [2026-07-16] — docs: document unit of material, suppliers, material active/inactive, and table filtering in README.md
- README.md was last updated before UOM (#16/#18), suppliers (#7), material active/inactive (#17), and per-column table filtering (#10/#19/#20) landed — brought it up to date before starting #21
- Section 6 (master material) now documents the required Unit of Material select, the seeded 22-unit starter catalog, that units can't be deleted, and that materials can't be deleted either — only deactivated via the Active select (an inactive material stays fully visible/historical, just can't be picked on a *new* Stock In line)
- Added new Section 7 (master supplier) — this master list existed in the backend/frontend but was never documented in the README; renumbered every following section (location/department/stock in/out/browse/usage/download-upload) by one
- Added new Section 14 (filtering and searching table data) covering the toolbar keyword search and the per-column filter row (live filtering, per-field clear, numeric operator syntax `>=`/`<=`/`>`/`<`/`!=`/`and`-joined ranges, keyword-vs-column-filter mutual exclusivity, hide-clears-all)
- Scope: docs
- Files: `README.md`

## [2026-07-16] — chore(frontend): extract shared Button component to DRY up toolbar add_*_button methods
- Issue #21 addressed on GitHub
- Added `frontend/src/components/button.py::Button` — a shared Material 3 button builder (`icon`, `on_click`, `tooltip`, optional `label`, `icon_color`, `bgcolor`, `size`, `radius`, `padding`) replacing three near-identical inline `ft.IconButton(...)` constructions. Renders a plain Flet-default `IconButton` when `size` is `None`, a compact pill-shaped `IconButton` when `size` is set, or an `ft.FilledButton` (icon + text) when `label` is given
- Rewired `components/list/toolbar.py`, `components/module/toolbar.py`, and `components/table/toolbar.py`'s `add_button` methods to call `Button(...).build()` instead of constructing `ft.IconButton` inline — each toolbar still owns its own default-color-resolution logic (`ModuleToolbar`: bg `SURFACE_CONTAINER_HIGH`/fg `ON_SURFACE`; `TableToolbar`: the inverse, bg `ON_SURFACE`/fg `SURFACE_CONTAINER_HIGH`; `ListToolbar`: plain default button, fg `ON_PRIMARY`) so no default look changed — only the final control construction moved into the shared component
- Verified in a real Flet 0.85.3 environment (`uv run --no-project --with flet==0.85.3 ...`): `Button.build()` returns the expected `IconButton`/`FilledButton` shape for both the plain and compact-pill paths; constructed all three toolbars' `add_new_button`/`add_save_button`/`add_submit_button` and confirmed every resolved `bgcolor`/`icon_color`/`height`/`width` matches its pre-refactor value exactly; imported `components/table/table.py`, `components/module/view.py`, and `components/list/list.py` (the modules that actually consume these toolbars) to catch any downstream import breakage — none found. **Not verified in a real browser** — no browser available in this environment
- Updated AGENTS.md's Frontend Architecture / Components section to document `Button` and each toolbar's preserved default color semantics
- Scope: frontend
- Files: `frontend/src/components/button.py`, `frontend/src/components/list/toolbar.py`, `frontend/src/components/module/toolbar.py`, `frontend/src/components/table/toolbar.py`, `AGENTS.md`

## [2026-07-16] — fix(frontend): TableToolbar buttons weren't standard Material 3 icon buttons; standardized hamburger menu alignment
- User-reported: `components/table/toolbar.py`'s buttons (Add New, Save, and the filter-row toggle) rendered as permanently-filled black pills instead of Material 3's "standard" icon button (transparent, icon only, hover highlight); also asked for a dedicated `add_filter_button` so `table.py` doesn't call `add_button` directly for the filter toggle, and flagged `components/table/menu.py`'s hamburger icon as vertically off-center in the toolbar
- Root cause of the black-pill look: `TableToolbar.add_button`'s old fallback always resolved `bgcolor` to `ft.Colors.ON_SURFACE` (never left it unset), forcing a permanently-filled dark background on every button rather than the transparent one Flutter's own standard `IconButton` variant renders by default (which also supplies its own hover/pressed state-layer highlight automatically, with no `overlay_color` needed)
- Fix: `add_button` now leaves `bgcolor=None` through to `Button` unless a caller explicitly passes one; default `icon_color` changed from the near-white `SURFACE_CONTAINER_HIGH` (only legible against the old forced dark fill) to `ON_SURFACE_VARIANT` (M3's own standard-icon-button default foreground), legible directly against the toolbar's `SURFACE_CONTAINER_LOW` bar with no fill behind it
- Added `TableToolbar.add_filter_button(callback, icon=FILTER_LIST, tooltip="Toggle Filters", ...)`; `Table.__init__`'s filter-row-toggle button is now `self.toolbar.add_filter_button(callback=self._toggle_filter_row)` instead of a direct `add_button(position="left", icon=..., tooltip=...)` call
- Root cause of the hamburger misalignment: `Menu`'s `ft.PopupMenuButton` used Flet's own defaults (~48dp target, 8px padding), which don't fit inside the 48dp toolbar bar's 32px content height (after the bar's own 8px vertical padding) the way the compact 32dp `Button`-built siblings do — it rendered low/off-center in the same `ft.Row`. Fixed by explicitly sizing it to the same metrics (`height=32, width=32, padding=0, icon_size=20, icon_color=ON_SURFACE_VARIANT, style=ButtonStyle(shape=RoundedRectangleBorder(radius=16))`) — duplicated by hand since `PopupMenuButton` isn't built through `Button` (different Flet control type)
- Deliberately left `ModuleToolbar` untouched — its filled/tonal `SURFACE_CONTAINER_HIGH`/`ON_SURFACE` look wasn't the reported problem; moving it to the standard variant too is a separate, explicit follow-up if wanted
- Verified in a real Flet 0.85.3 environment: constructed `TableToolbar` and called `add_filter_button`/`add_new_button`/`add_save_button`, confirming every button now resolves `style.bgcolor=None`, `icon_color=Colors.ON_SURFACE_VARIANT`, `height=width=32`; constructed `Menu` directly and confirmed its `PopupMenuButton` resolves `height=width=32`, `padding=0`, `icon_size=20`, `icon_color=ON_SURFACE_VARIANT`, `style.shape=RoundedRectangleBorder(radius=16)`; re-imported `components/table/table.py` to confirm the `add_filter_button` call site still builds cleanly. **Not verified in a real browser** — no browser available in this environment
- Updated AGENTS.md's Components section with the corrected `TableToolbar`/`Menu` styling notes (replacing the now-outdated "deliberate higher-contrast pill" reasoning from the #21 entry above)
- Scope: frontend
- Files: `frontend/src/components/table/toolbar.py`, `frontend/src/components/table/table.py`, `frontend/src/components/table/menu.py`, `AGENTS.md`
- No GitHub issue filed (direct implementation, per user, following on from the #21 discussion)

## [2026-07-16] — fix(frontend): ModuleToolbar had the same forced-fill button bug as TableToolbar
- User asked to check whether `components/module/toolbar.py` had the same "not standard Material 3" bug just fixed on `TableToolbar` — it did, in a slightly different shape
- Root cause: `add_button`'s default *parameter* was `bgcolor=ft.Colors.PRIMARY` (never `None`), so `purchase_report/index.py`'s and `usage_report/index.py`'s bare `add_button(...)` calls for "Apply Filters" (no `bgcolor` passed at all) rendered a solid, visibly-colored filled pill. Separately, `add_new_button`/`add_submit_button` (used across ~40 module screens) passed `bgcolor=None` explicitly, which the body's fallback resolved to `SURFACE_CONTAINER_HIGH` — coincidentally the exact same color as `ModuleToolbar`'s own bar background, so those buttons only looked transparent by luck, not by design
- Fix: same pattern as the `TableToolbar` fix — default `bgcolor=None` (both the parameter default and the fallback substitution removed) and default `icon_color=ON_SURFACE_VARIANT`
- The 7 delete buttons (`master_location/edit.py`, `ap_module/edit.py`, `ap_master_user/edit.py`, `master_category/edit.py`, `master_department/edit.py`, `master_module_group/edit.py`, `master_supplier/edit.py`) all pass `bgcolor=ft.Colors.ERROR`/`icon_color=ft.Colors.ON_ERROR` explicitly and are unaffected — the toolbar's one legitimate filled/tonal (danger) button
- Verified in a real Flet 0.85.3 environment: constructed `ModuleToolbar` directly, called `add_new_button`/`add_submit_button`/an explicit red delete `add_button`/a bare "Apply Filters"-style `add_button` — confirmed the first three now resolve `bgcolor=None`/`icon_color=ON_SURFACE_VARIANT`, the delete button still resolves `bgcolor=Colors.ERROR`/`icon_color=Colors.ON_ERROR` unchanged, and the bare call now resolves `bgcolor=None` instead of `PRIMARY`; also imported `components/module/view.py` plus `purchase_report/index.py`, `usage_report/index.py`, `master_location/edit.py`, `ap_module/edit.py` to confirm no downstream breakage. **Not verified in a real browser** — no browser available in this environment
- Updated AGENTS.md's Components section with this second finding
- Scope: frontend
- Files: `frontend/src/components/module/toolbar.py`, `AGENTS.md`
- No GitHub issue filed (direct implementation, per user, following on from the TableToolbar fix above)

## [2026-07-16] — fix(frontend): hide CSV/XLSX upload menu items on tables with no editable columns
- Issue #22 created on GitHub
- Scope: frontend
- Labels: bug, frontend
- User noticed `components/table/menu.py`'s hamburger menu always shows "Upload from CSV"/"Upload from XLSX", even on purely read-only list tables where there's nothing editable to populate — asked for the menu to check whether the table actually contains any editable column type (input/textarea/select/option/datepicker/checkbox) and only show the upload entries when it does, since bulk record creation for ordinary list tables already goes through the "Add New" screen's own bulk-upload menu (issue #5)

## [2026-07-16] — fix(frontend): hide CSV/XLSX upload menu items on tables with no editable columns (issue #22)
- `Menu.__init__` now computes `has_editable_fields = any(field.get("type") in _EDITABLE_TYPES for field in self.parent.fields)` and only appends the "Upload from CSV"/"Upload from XLSX" items (plus the separator before them, only when download items are also present) when that's true — previously upload was unconditional regardless of whether the table had any editable cell to populate
- Restructured the separator logic so it's added only between two actually-present sections, not unconditionally whenever downloads were shown: a non-form table with an editable column now correctly gets downloads + separator + uploads; a non-form table with none gets downloads only (no dangling trailing separator); an `is_inside_form` table with editable fields (the common case, e.g. `stock_out/item_new.py`) gets uploads only, same as before
- Updated the class docstring and AGENTS.md's "Table export/upload convention" section to describe the new gating rule in place of the old "upload entries are always present" note
- Verified in a real Flet 0.85.3 environment: constructed `Menu` against four fake parent shapes (read-only list, `is_inside_form` with editable fields, non-form with an editable field, `is_inside_form` with zero editable fields) and confirmed each produced exactly the expected item set (download-only, upload-only, download+separator+upload, and empty, respectively); cross-checked against two real modules' actual field configs — `master_material/index.py` (all `label`/`hidden` fields, confirming its upload entries now correctly disappear) and `stock_out/item_new.py` (`input` fields, confirming its upload entries are unaffected); imported `components/table/table.py` plus `master_material/index.py`, `stock_in/index.py`, `stock_out/item_new.py` to confirm no downstream breakage. **Not verified in a real browser** — no browser available in this environment
- Scope: frontend
- Files: `frontend/src/components/table/menu.py`, `AGENTS.md`
