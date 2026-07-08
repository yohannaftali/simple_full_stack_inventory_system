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
| #1 | feat(infra): scaffold full-stack app with MariaDB, FastAPI, and Flet via Podman Compose | open | 2026-07-08 |

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
  source in `./frontend/src`. Connects to the backend over HTTP using a
  server address the user enters manually at runtime (see below) — there is
  no baked-in backend URL.

All three services are defined in `compose.yml` and run together with:

```
podman compose -f compose.yml up -d
```

Environment variables (`MARIADB_ROOT_PASSWORD`, `MARIADB_DATABASE`,
`JWT_SECRET`, `UVICORN_HOST`, `UVICORN_PORT`, `UVICORN_PORT_SSL`,
`GITHUB_TOKEN`) are read from `.env` (see `example.env` for the template;
`.env` itself must never be committed).

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
  `ModalPage` class).

- **Components** (`src/components/`): reusable, presentational Flet control
  builders grouped by domain — `form/`, `home/`, `login/`, `server_config/`
  (server-URL `TextField` + save button), `troubleshooting/`, `list/` and
  `table/` (shared grid/table + search/toolbar), `modal/` and `module/`
  (shared chrome for dynamically-loaded screens), plus page-level
  `loading_overlay.py` and `splash_screen.py`.

- **Repositories / state & persistence** (`src/repository/`): each repo
  wraps `page.data` (in-memory cache) plus an optional persistence `store`.
  - Persistent (loaded once at boot via `Storage.load_persistent()`):
    `server_url.py` (`ServerURL`, key `"server_url"`, default
    `DEFAULT_SERVER_URL = "https://localhost:8000"`), `http_cookies.py`,
    `user_session.py`, `theme_mode.py`.
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

- **Module loading** (`src/utils/module_loader.py`): `ModuleLoader(page,
  target)` (`target` is `"modules"` or `"modals"`) preloads every screen
  under `pages/<target>/*/*.py`, caches them, and dynamically imports/builds
  the `ModulePage`/`ModalPage` class matching a parsed route.

- **Theming** (`src/themes/`): `light_theme.py` / `dark_theme.py` expose
  `ft.Theme`s; `repository/theme_mode.py` applies `page.theme_mode`
  (LIGHT/DARK/SYSTEM) from the persisted preference.