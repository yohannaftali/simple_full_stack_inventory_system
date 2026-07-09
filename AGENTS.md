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
Dependencies are pinned in `backend/requirements.txt` (no `pyproject.toml`).

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
  hands out the raw secret.
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
    `description`, `module_type`, `module_group_id`, `icon`, `mdi`,
    `created_at`, `updated_at`). `module_type`/`module_group_id`/`mdi` are
    carried over from the PHP schema for parity but not yet consumed by any
    backend logic or the frontend (which only reads `name`/`label`/`icon`/
    `description`).
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
    `get_user_by_id`, `list_users(keyword, limit, offset)` (paginated,
    matches/searches `username`/`email`), `update_user_by_id` (password only
    changes if a non-empty one is passed), `delete_user_by_id`, and
    `check_user_exists(..., exclude_id=None)` (the `exclude_id` param lets an
    update check uniqueness against everyone *else*).
  - `module_repository.py` → `ModuleRepository`: `get_module_by_name`,
    `get_module_by_id`, `get_all_modules`, `list_modules(keyword, limit,
    offset)` (paginated), `create_module`, `update_module`, `delete_module`.
  - `user_module_permission_repository.py` → `UserModulePermissionRepository`:
    `has_access`, `get_modules_for_user`, `grant_access`, `revoke_access`,
    `get_module_ids_for_user`, `set_modules_for_user` (replaces a user's
    entire grant set in one call — used by the permission checklist),
    `delete_permissions_for_module` / `delete_permissions_for_user` (call
    before deleting a module/user — the FKs have no `ON DELETE CASCADE`, so
    routers must clear grants first or the delete raises a FK violation).
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
    - `GET C_home/home` → `{"username", "modules": [...], "title": "SFSIS",
      "footer": ""}`. Each module dict is `{"name", "label", "module_icon",
      "module_description"}` (field names match `components/home/module_card.py`)
      — only modules the user has an explicit `user_module_permissions` grant
      for, ordered by `ModuleModel.sort`.
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
    `description`) → upsert (blank/missing `id` = create); `{"message": "..."}`
    or `{"error": "..."}`.
  - `POST C_ap_module/delete` (form: `id`) → deletes the module's permission
    grants first, then the module.

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
- **Stock out deduction is user-picks-location, then FIFO within it**: the
  stock-out form has the user pick one location (confirmed over an
  automatic-FIFO-across-locations alternative — simpler, matches how
  receiving already assigns location explicitly). Given that location, the
  service deducts oldest-lot-first (`StockModel` rows ordered by `id`
  ascending, a proxy for receiving order) until the requested qty is
  satisfied, raising `InsufficientStockError` up front (before mutating
  anything) if the location's total is short.
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
  `get_items` (list by header), `submit_item` (create, and for stock_in only,
  update), and (for stock_in) `get_item` (single, for the edit form) —
  because a receiving/issuing item is edited on its own screen, not as part
  of one combined header+items submission (see Frontend Architecture below
  for why). Each also exposes `call_material_id_select`/
  `call_location_id_select` for the item form's dropdowns; `stock_out.py`
  additionally exposes `call_department_id_select` for its header form.

**Frontend module structure** (`frontend/src/pages/modules/`): `master_location`,
`master_supplier`, `master_department`, and `master_material` are plain
`{index,new,edit}.py` CRUD, identical in shape to `ap_module`
(`master_material`'s `new`/`edit` additionally carry a `supplier_id` select
field, `index` a read-only `supplier_name` label). `ap_master_user`'s
`new`/`edit` similarly carry a `department_id` select field (optional —
blank is valid) and `index` a read-only `department_name` label;
`stock_out`'s `new`/`edit` carry a required `department_id` select on the
header form and `index` a read-only `department_name` label. `stock_browse`
and `usage_report` are `index.py` only (no `new`/`edit` — and deliberately
no field marked `"key": True` in their `Table` config, since `Rows.py`
unconditionally wires a `"key"` field to row-tap-navigates-to-`edit/<id>`,
and neither has an edit screen to navigate to).

`stock_in`/`stock_out` needed a **header/item master-detail pattern that
doesn't exist elsewhere in this codebase**. Two roads not taken, and why:
- `components/form/table.py` / `list.py` (the `Form` component's `"table"`/
  `"list"` field types) look like the obvious fit, but they serialize their
  rows as indexed fields (`items[0]`, `items[1]`, ...) submitted together
  with the parent form in **one** POST — the spec here is "click + to add
  one item via its own form," a separate transaction per item, not a bulk
  combined save.
- Reusing `components/table/table.py` (the plain list-table, as used by
  every `index.py`) for the *item* sub-list doesn't work either:
  `components/table/rows.py`'s row-tap handler is hardcoded to navigate to
  `/modules/{module}/edit/{id}` — which is already the header's own edit
  route. Using it for items would either collide with the header edit
  screen or misinterpret an item id as a header id.

  Solution: `stock_in/edit.py` and `stock_out/edit.py` embed a small custom
  `ItemTable` widget (`pages/modules/stock_in/item_table.py`,
  `pages/modules/stock_out/item_table.py` — plain `ft.DataTable`, not built
  on the shared `Table` component) with its own "+" button and (stock_in
  only) row-click, navigating to `item_new/<header_id>` and
  `item_edit/<item_id>` respectively — screen names local to each module,
  no collision. Those two screens don't use `Form.submit()` (which always
  redirects to `/modules/{module}/index`); they call `self.form.serialize()`
  themselves, POST via `HttpClient`, and redirect back to the header's
  `edit/<header_id>` screen instead. `item_new` repurposes the route's
  `record_id` slot to carry the *header* id (it only ever creates, so there's
  no item id yet); `item_edit` does a small extra GET up front to learn its
  item's `receiving_header_id` (needed to know where to navigate back to,
  since the route only carries the item id).
- Full stock-in → MAP calc across two receipts → edit-item MAP correction →
  browse → stock-out (FIFO across 3 lots, partial-lot deduction, insufficient-
  stock rejection, issue-from-empty-location rejection) → permission-gating
  flow is verified end-to-end with `TestClient` smoke tests against SQLite,
  plus a real walk against the live MariaDB container.

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
    picked by `utils/persistence.py`: native (desktop/Android/iOS) persists
    to a JSON file outside the source tree; web uses `ft.SharedPreferences`
    with retry logic (`utils/storage_compat.py`) for a known async mount
    race.

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