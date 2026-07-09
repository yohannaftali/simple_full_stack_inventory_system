
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
