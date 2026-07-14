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

## Repository

- Remote: https://github.com/yohannaftali/simple_full_stack_inventory_system.git
- Platform: GitHub

## Tracked Issues
| ID | Title | Status | Last Checked |
|----|-------|--------|--------------|
| #1 | feat(infra): scaffold full-stack app with MariaDB, FastAPI, and Flet via Podman Compose | ready-for-review | 2026-07-08 |
| #2 | fix(frontend): table search bar loses focus on every keystroke | ready-for-review | 2026-07-14 |

## Big Picture

**SFSIS** is a full-stack inventory system with three services, orchestrated
locally via Podman:

- **database** — MariaDB (`Dockerfile-mariadb`), data volume mounted at
  `./database`, logs at `./logs/database`.
- **backend** — FastAPI served by Uvicorn (`Dockerfile-backend`), source in
  `./backend`. Talks to MariaDB. Exposes the HTTP API the frontend consumes
  (endpoints referenced by the frontend follow a `C_<module>` naming
  convention, e.g. `C_home/home`, `C_{module}`).
- **frontend** — a Flet desktop/web/mobile app (`Dockerfile-frontend`),
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

All three services are defined in `compose.yml` and run together with:

```
podman compose -f compose.yml up -d
```

Environment variables (`MARIADB_ROOT_PASSWORD`, `MARIADB_DATABASE`,
`JWT_SECRET`, `UVICORN_HOST`, `UVICORN_PORT`, `UVICORN_PORT_SSL`,
`FRONTEND_PORT`, `FRONTEND_PORT_SSL`, `GITHUB_TOKEN`) are read from `.env`
(see `example.env` for the template; `.env` itself must never be committed).

## Backend Architecture (FastAPI — `backend/src`)

Stack: Python 3.13, FastAPI + Uvicorn, SQLAlchemy 2.x ORM, Alembic for
migrations, PyMySQL as the MariaDB driver, `bcrypt` for password hashing,
Starlette `SessionMiddleware` (signed cookie, needs `itsdangerous`) for
login sessions, `python-multipart` for form-encoded request bodies.
Dependencies are managed via `backend/pyproject.toml` + `backend/uv.lock`
(uv — same tooling as the frontend, see Frontend Architecture below).
`Dockerfile-backend` installs `uv` then runs `uv sync --locked --no-dev`;
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
  see "Table list/pagination convention" below.
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
    `app_title` [default `"SFSIS"`], `footer` [default `""`], `created_at`,
    `updated_at`) — a **singleton** row (exactly one, seeded by
    `0016_create_app_config_table.py`) backing `home.py`'s `title`/`footer`
    fields and the `master_config` admin screen.
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
    - **Reference implementation** (verify the mechanism here before
      extending it further): `location_repository.py::list_locations` /
      `routers/master_location.py::get_detail` on the backend,
      `pages/modules/master_location/index.py`'s `code`/`name` fields
      marked `"sort": True` on the frontend. **Not yet rolled out to the
      rest of the paginated `list_*` methods above** — same mechanical
      per-endpoint change (add `sort_fields` param + `column_map` + a
      `request: Request` param) needed for each, plus marking whichever
      fields make sense `"sort": True` per module (some, like a free-text
      `remarks` column, may deliberately stay unsortable).
    - Frontend half lives entirely in `components/table/columns.py`:
      `Columns.sort_order` is an ordered `[(field_name, "ASC"|"DESC"), ...]`
      list (list order = priority, mirrors `y.form.js`'s
      `this.orderBy[table]` array). `Columns.on_sort(e)` — wired as every
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
      (`Columns._build_sort_icon()` — neutral `unfold_more`, or an
      up/down arrow once active) as part of its label, since Flet's
      `DataTable` has no multi-column sort indicator of its own (it only
      ever highlights one `sort_column_index`, which this table never
      sets) - unlike an earlier, wrong guess about a *phantom*
      Flutter-drawn icon on every sortable column regardless of active
      state (reverted - see the git history around 2026-07-13), this one
      is real and always visible for a sortable column, so
      `_SORT_ICON_WIDTH` is a correct, exact reservation, not an
      approximation. `Columns.serialize_sort()` builds the
      `&sort-fields[N][field]=...` query string
      `components/table/table.py::get_data()` appends on every request.
      `Columns.on_sort_change` (wired to `Table._handle_sort_change`)
      fires after every toggle: an instant optimistic header-only rebuild
      (icons update immediately, same split as the reference doing its
      `icon.classList` swap synchronously before the AJAX call), then
      `get_data()` re-fetches with the new sort - deliberately **not**
      resetting to page 1 (only a page-*size* change does that), matching
      `y.form.js`'s `serializePagination`/`listenerHeaderTable`. Sort
      state itself isn't persisted anywhere (matches the reference - an
      in-memory `this.orderBy[table]` there too), so it resets whenever a
      `Table`/`Columns` instance itself is torn down and rebuilt (e.g.
      navigating away and back).
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
  `0004_seed_default_superuser.py` seeds a bootstrap superuser (`admin` /
  `admin1234#` — **change this password after first login**; the migration
  is idempotent, it no-ops if a user named `admin` already exists, and
  `downgrade()` removes exactly that seeded row).
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
  module + `admin` grant.
- Because `src/` code imports as top-level packages (`from models.base import
  ...`, not `from src.models.base import ...`), `Dockerfile-backend` sets
  `ENV PYTHONPATH=/usr/src/app/src` and copies `alembic.ini` +
  `alembic/` into the image alongside `src/`.
- `Dockerfile-backend`'s `CMD` is `backend/entrypoint.sh` (copied to
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
     schema changes. If MariaDB isn't accepting connections yet when the
     backend container starts, this fails, the container exits, and
     `restart: always` retries — a crash-loop that self-heals once the DB
     is up, since `compose.yml`'s `depends_on` only orders container
     *start*, not DB readiness.
  3. Starts **two** Uvicorn processes in the background and `wait -n`s on
     either: plain HTTP on `UVICORN_PORT` (5000) and HTTPS (using the
     generated cert) on `UVICORN_PORT_SSL` (5443) — both env vars come from
     `compose.yml`, which also exposes both ports. The frontend's
     `HttpClient(verify=False)` only skips certificate *validation*, so a
     `https://` server address still needs a real TLS listener behind it —
     point the Server Config page at `https://<host>:5443` (or
     `http://<host>:5000` if you don't need TLS).
- **Bootstrap**: `alembic upgrade head` seeds `admin`/`admin1234#` as an
  active superuser (`0004`) *and* the built-in modules + grants every one
  to that account (`0006` for the original 7, `0008` for `master_supplier`)
  — a fresh instance has working home screen tiles and full admin access
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
`name` — who consumes inventory, for usage reporting), and `materials`
(`MaterialModel`: `material_code`, `material_name`, `supplier_id` — nullable
FK to `suppliers.id`, since materials created before the supplier link has
no supplier to point to), managed via the `master_location`/
`master_supplier`/`master_department`/`master_material` admin modules
(plain CRUD, same shape as `ap_module`). `master_material`'s new/edit form
renders `supplier_id` as a `select` field
(`GET C_master_material/call_supplier_id_select`), and its list/get
responses include a denormalized `supplier_name` for display — the same
pattern as `stock_in`/`stock_out`'s `material_id`/`location_id` selects,
just on master data instead of a transactional item. `UserModel` also has
an optional `department_id` (see Backend Architecture above) so a user can
represent one department's requester, separately from stock-out headers
each declaring their own department.

Transactional tables, all in `backend/src/models/`:
- `receiving_headers` / `receiving_items` (stock in): a header is just
  `date` + `description`; each item is one `material_id` + `location_id` +
  `price_buy` + `qty_received` + `remarks`. **`location_id` lives on the
  item**, not the header — inferred, not explicitly specified, since the
  `stocks` table needs a location per lot and nothing else supplies one.
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
  `qty_out` + the **captured** `price` (that material's MAP at the moment of
  issue) + `total_value` (`qty_out * price`) + `remarks`.

All business logic lives in `backend/src/services/inventory_service.py`,
which — unlike every other service/repository in this codebase — manages its
own `SessionLocal()` transaction directly instead of going through
single-table repository methods, because one "receive" or "issue" call must
touch `receiving_items`/`stocks`/`inventory_values` (or `stock_out_items`)
atomically. Repositories for these tables (`receiving_repository.py`,
`stock_repository.py`, `stock_out_repository.py`) are read-only for the
transactional parts (header CRUD is plain repository methods same as
everywhere else; only item writes route through the service).

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
  today's MAP.
- `stock_in.py` / `stock_out.py`: header list/get/submit (same shape as
  master data — `stock_out.py`'s header additionally requires a non-blank
  `department_id` on submit, and its list/get responses include a
  denormalized `department_name`), plus a **separate item sub-flow** —
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
  by `stock_out.py`'s item form now, kept for parity/possible future use);
  `stock_out.py` additionally exposes `call_department_id_select` for its
  header form.

**Frontend module structure** (`frontend/src/pages/modules/`): `master_location`,
`master_supplier`, `master_department`, `master_material`, and
`master_module_group` are plain `{index,new,edit}.py` CRUD, identical in
shape to `ap_module` (`master_material`'s `new`/`edit` additionally carry a
`supplier_id` select field, `index` a read-only `supplier_name` label).
`ap_master_user`'s `new`/`edit` similarly carry a `department_id` select
field (optional — blank is valid) and `index` a read-only `department_name`
label; `stock_out`'s `new`/`edit` carry a required `department_id` select on
the header form and `index` a read-only `department_name` label. `ap_module`
itself also carries a `module_group_id` select on `new`/`edit` (optional —
blank is valid) and a read-only `module_group_name` label on `index`.
`stock_browse` and `usage_report` are `index.py` only (no `new`/`edit` — and
deliberately no field marked `"key": True` in their `Table` config, since
`Rows.py` unconditionally wires a `"key"` field to row-tap-navigates-to-
`edit/<id>`, and neither has an edit screen to navigate to).

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

`stock_in`/`stock_out` needed a **header/item master-detail pattern that
doesn't exist elsewhere in this codebase**. A road not taken, and why:
`components/form/table.py` / `list.py` (the `Form` component's `"table"`/
`"list"` field types) look like the obvious fit, but they serialize their
rows as indexed fields (`items[0]`, `items[1]`, ...) submitted together
with the parent form in **one** POST — the spec here is "click + to add
one item via its own form," a separate transaction per item, not a bulk
combined save.

The *item sub-list itself*, though, **is** built on the shared
`components/table/table.py` (`stock_in/item_table.py`, `stock_out/item_table.py`
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
  (`Rows.load()` always rendered `ft.Text`): six `"type"` values now
  render an editable control instead of text (`Rows._build_editable_cell()`
  is the dispatch point) —
  - `"input"` — single-line `ft.TextField` (`hint_text`/`keyboard_type`,
    same keys `components/form/input.py` uses).
  - `"textarea"` — multiline `ft.TextField` (`min_lines`/`max_lines`).
  - `"select"` — `ft.Dropdown` fetching options from
    `C_{module}/call_{field_name}_select` (or a field-level `endpoint`
    override), same convention as `components/form/select.py`. Fetched
    once per column and cached on the `Rows` instance (`_select_options_cache`)
    since the option list is normally identical for every row - not
    refetched per row, and not refreshed on a later reload within the same
    `Rows` lifetime.
  - `"option"` — `ft.Dropdown` from a field-supplied static `"options":
    [{"value", "label"}, ...]` list, no HTTP fetch - for small fixed
    enumerations that don't need a backend round trip.
  - `"datepicker"` — reuses `components/form/date.py`'s `DateForm` as-is
    (calendar-popup TextField, ISO value tracked separately from the
    displayed "dd Mon yyyy" text, including its UTC-offset day-rollback
    correction) - one `DateForm` instance per cell.
  - `"checkbox"` — `ft.Checkbox` (accepts a bool or a truthy string from
    the fetched row data).

  `Table.get_rows_with_input_values()` returns each fetched row's dict
  merged with the current value of every editable-type field in it, in
  fetch order — `"datepicker"` columns via `DateForm.get_value()` (the raw
  ISO string), everything else via the control's own `.value`. The caller
  never wires its own per-row control bookkeeping. An editable cell never
  wires the row-tap-to-edit-screen handler (even if some other column in
  the same `Table` is marked `"key": True`), since a tap there needs to
  land in the control to interact with it, not navigate away.

  Every cell (editable or not) is wrapped in a fixed-width `ft.Container`
  matching `Columns.load()`'s computed per-column width - without that
  wrapper Flutter sizes the DataTable column from the raw control's own
  intrinsic width instead (e.g. a bare `TextField`'s ~300px default),
  drifting the column out of alignment with the rest of the table.
  `Columns._get_widths()`'s proportional scale-down (when a table's total
  content is wider than the screen) also respects a *per-column* minimum
  now, not one flat `40px` for every column - `_EDITABLE_MIN_WIDTHS` in
  `components/table/columns.py` floors editable types higher (e.g. `input`
  100px, `textarea` 160px), since a rigid-width control genuinely can't
  render below some size without visually overflowing its cell, unlike a
  plain `Text` cell, which just ellipsizes gracefully at any width. A field
  can override its floor directly with `"min_width"`.

  `components/table/columns.py` also has two more general table behaviors,
  not specific to editable cells:
  - **Last-column right padding**: `_LAST_COLUMN_RIGHT_PADDING` (12px) is
    reserved out of `get_usable_width()`'s budget and added back onto only
    the last column's width in `load()`, so its content gets breathing
    room before the table's true right edge instead of butting up against
    it (`get_widths()`'s "distribute extra space evenly" branch alone
    wasn't enough - it can leave the last column exactly flush right).
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
    - **Handles live outside the `DataTable` entirely**, in an
      absolutely-positioned overlay `ft.Stack` on top of the header
      (`Columns.get_resize_overlay()`, built once and cached - reused as
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
      `Columns.on_resize_commit(recompute: bool)` now fires on *every*
      `handle_drag()` step (`recompute=False`) as well as a double-tap
      reset (`Columns.reset_column_pair()`, `recompute=True`) - wired by
      `Table.__init__` to `Table._handle_resize_commit`, which (for a
      reset) recomputes `Columns.widths` from content via `Columns.load()`,
      then always runs `Rows.load()` and rebuilds the header (through
      `Table._build_header_with_resize_overlay()` - every header-rebuild
      call site must go through this, not `Header.build()` directly, or
      the overlay silently drops off the tree) and body in place. A full
      rebuild on every tick is only safe *because* the handle is no longer
      inside what's being rebuilt: Flet's control-id-based patching (not
      tree-position-based - `messaging/session.py`'s `patch_control` skips
      `will_unmount()` for any removed control that's also present among
      the added controls) recognizes the same `GestureDetector` object
      reappearing in a brand new `Stack` and leaves it mounted, preserving
      the in-progress gesture across the header's repeated recreation.
      `Columns._reposition_handles()` moves each handle's `left` to its
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
    - Once a user drags a handle, `Columns.manually_resized` is set and
      `load()` stops recomputing widths from content on later data reloads
      (pagination/filter/scroll-more/page-resize) - it just keeps whatever
      the user set, like a spreadsheet remembering a manual column width.
    - Shrinking a column narrow enough used to wrap its header label onto
      multiple lines, growing the header row into the row below it
      instead of truncating - both `Columns._build_data_columns()`'s
      header `Text` and `Rows.load()`'s body-cell `Text`s now set
      `overflow=ft.TextOverflow.ELLIPSIS, max_lines=1` (Excel-style: a
      narrow column truncates to one line, it doesn't wrap). Below
      `_MIN_LABEL_VISIBLE_WIDTH` (24px) a header label is dropped
      entirely rather than rendered as one unreadable clipped character.
    - Every `DataColumn` sets `on_sort=self.on_sort` unconditionally -
      sorting itself isn't implemented yet (`Columns.on_sort()` is a
      `print()`-only stub, kept intentionally for whenever that lands).
      An earlier pass here guessed that `on_sort`'s presence makes
      Flutter reserve extra width for a sort-indicator icon on *every*
      sortable column regardless of active sort state, and shrank every
      header label `Container` by an assumed icon footprint to
      compensate - that guess was wrong (Flutter's `DataColumn` only
      draws the icon for the column matching `DataTable.sort_column_index`,
      which this app never sets, so no icon is ever actually drawn) and
      visibly shrank every header label for nothing; reverted. If a real
      divider/label misalignment resurfaces, re-diagnose from scratch
      rather than reapplying that fix.
      `Columns._min_width_for()` still floors every column at
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

Stack: Python ≥3.10, Flet 0.85.3, `requests` for HTTP, `flet-datatable2`;
managed via `pyproject.toml` (uv/Poetry).

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
  - Boot logic (`_boot_navigate`): if the server URL is still the
    placeholder default → force `/server_config`; else if the client session
    is active → `/home`; else → `/login`.

- **Pages** (`src/pages/`): top-level singleton pages (`login`, `home`,
  `server_config`, `troubleshooting`, `error`, `permission_error`, `loader`),
  plus `pages/modules/<module_name>/{index,edit,new,detail,...}.py` (one
  folder per business module, each exposing a `ModulePage` class) and
  `pages/modals/{password,shift,token,totp}/index.py` (each exposing a
  `ModalPage` class). A module folder can also hold private, non-screen
  helper files alongside `index`/`new`/`edit` — e.g.
  `pages/modules/ap_master_user/permission_checklist.py` (a `Checkbox` list
  for granting/revoking `user_module_permissions`, embedded in that module's
  `edit.py` body) — `ModuleLoader` only preloads files matching an actual
  route (`<module>/<screen>`), so a helper file with no matching route is
  simply never preloaded/dispatched as a screen, just imported normally by
  whichever screen uses it.
  - `ap_module` (list/new/edit) and `ap_master_user` (list/new/edit) are the
    admin CRUD screens for `modules` and `users` + their permission grants,
    backed by `routers/module_admin.py` and `routers/user_admin.py`. Both
    use the generic `components/table/table.py` (list) and
    `components/form/form.py` (create/edit) — no bespoke fetch/submit code,
    just a `fields` list per screen (see `ap_config` for the original
    pattern this follows). `ap_master_user/edit.py` additionally embeds
    `PermissionChecklist` below the user form. Deleting a row isn't part of
    the generic `Table`/`Form` framework yet, so both `edit.py` screens add
    their own delete button via `ModuleToolbar.add_button(...)` calling
    `POST C_{module}/delete` directly.

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

- **Repositories / state & persistence** (`src/repository/`): each repo
  wraps `page.data` (in-memory cache) plus an optional persistence `store`.
  - Persistent (loaded once at boot via `Storage.load_persistent()`):
    `server_url.py` (`ServerURL`, key `"server_url"`, default
    `DEFAULT_SERVER_URL = "http://backend:5000"` — the compose network
    address, so the containerized frontend works out of the box without a
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
    `Set-Cookie` on the first HTTP response, no JS round trip to race) and
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
    `DEFAULT_SERVER_URL` is now `http://backend:5000` specifically so a
    fresh containerized frontend gets this right automatically, without
    anyone having to rediscover the gotcha above via the Server Config page.
    Note this doubles as the "never configured, force `/server_config`"
    sentinel in `main.py`'s `_boot_navigate` (see the comment there) — it's
    a real working address for *this* deployment target now, not a pure
    placeholder, so that force-to-config behavior effectively only fires for
    other deployment targets (native desktop, etc.) where it doesn't resolve.

- **Module loading** (`src/utils/module_loader.py`): `ModuleLoader(page,
  target)` (`target` is `"modules"` or `"modals"`) preloads every screen
  under `pages/<target>/*/*.py`, caches them, and dynamically imports/builds
  the `ModulePage`/`ModalPage` class matching a parsed route.

- **Theming** (`src/themes/`): `light_theme.py` / `dark_theme.py` expose
  `ft.Theme`s; `repository/theme_mode.py` applies `page.theme_mode`
  (LIGHT/DARK/SYSTEM) from the persisted preference.