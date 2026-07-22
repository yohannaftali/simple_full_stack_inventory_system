# SFSIS — Simple Full Stack Inventory System

A small inventory system with three services — **MariaDB**, a **FastAPI**
backend, and a **Flet** (web/desktop) frontend — orchestrated locally with
Podman. It tracks material master data, stock in (receiving), stock out
(issuing to departments), moving-average costing, current stock levels, and
department usage/cost reporting.

> Looking for architecture details or contribution conventions? See
> [AGENTS.md](AGENTS.md). This README is for running and using the app.

## Table of contents

1. [Deploying the application](#1-deploying-the-application)
   - [Alternative: Docker Desktop on Windows 11](#alternative-docker-desktop-on-windows-11)
   - [Updating (`git pull`)](#15-updating-git-pull)
2. [Accessing the frontend and logging in](#2-accessing-the-frontend-and-logging-in)
3. [Changing the admin password](#3-changing-the-admin-password-first-time)
4. [Setting up TOTP (2FA)](#4-setting-up-totp-2fa)
5. [Setting up users and permissions](#5-setting-up-users-and-permissions)
6. [Setting up master material](#6-setting-up-master-material)
7. [Setting up master supplier](#7-setting-up-master-supplier)
8. [Setting up master location](#8-setting-up-master-location)
9. [Setting up master department](#9-setting-up-master-department)
10. [Stock in (receiving)](#10-stock-in-receiving)
11. [Stock out (issuing)](#11-stock-out-issuing)
12. [Browsing current stock](#12-browsing-current-stock)
13. [Checking usage](#13-checking-usage)
14. [Filtering and searching table data](#14-filtering-and-searching-table-data)
15. [Download and Upload Features](#15-download-and-upload-features)
16. [Paging through table data (lazy-load vs. pagination)](#16-paging-through-table-data-lazy-load-vs-pagination)

## 1. Deploying the application

### 1.1 Install Podman

Install **Podman** (and `podman-compose`, or Podman Desktop which bundles a
compose provider):

- **Windows**: `winget install RedHat.Podman-Desktop`, or `scoop install podman`
- **macOS**: `brew install podman podman-compose`
- **Linux**: use your distro's package manager, e.g. `sudo apt install podman podman-compose`

Verify it works:

```bash
podman --version
podman compose version
```

#### Alternative: Docker Desktop on Windows 11

If Podman gives you trouble (a common one on Windows is the machine/VM
failing to start, or `podman compose` not finding a compose provider),
**Docker Desktop** is a drop-in alternative — this project's `compose.yml`
and Dockerfiles work unchanged with either engine.

1. Install Docker Desktop:
   ```powershell
   winget install Docker.DockerDesktop
   ```
   or download it from https://www.docker.com/products/docker-desktop/.
2. Launch **Docker Desktop** once from the Start menu and let it finish
   starting up (it needs WSL2 — the installer will prompt you to enable it
   and reboot if it isn't already set up).
3. Verify it works:
   ```powershell
   docker --version
   docker compose version
   ```
4. Everywhere this README says `podman compose ...` or `podman ...`,
   substitute `docker compose ...` / `docker ...` instead — the commands
   and flags are otherwise identical (e.g. `docker compose -f compose.yml
   up -d`, `docker logs sfsis-backend --tail 30`).

### 1.2 Get the code

```bash
git clone https://github.com/yohannaftali/simple_full_stack_inventory_system.git
cd simple_full_stack_inventory_system
```

(If you already have a clone, just `git pull` instead of cloning.)

### 1.3 Create your `.env` file

Copy the template and edit it:

```bash
cp example.env .env
```

`.env` fields:

| Variable                 | Purpose                                                            |
|---------------------------|---------------------------------------------------------------------|
| `MARIADB_ROOT_PASSWORD`  | Password for the MariaDB `root` user                               |
| `MARIADB_DATABASE`       | Database name (default `sfsis`)                                    |
| `JWT_SECRET`             | Secret key signing the backend's login session cookie — see below  |
| `UVICORN_HOST`           | Backend bind host (leave as `127.0.0.1`/`0.0.0.0`, don't change unless you know why) |
| `UVICORN_PORT` / `UVICORN_PORT_SSL` | Backend HTTP/HTTPS ports (defaults `5000`/`5443`)        |
| `FRONTEND_PORT` / `FRONTEND_PORT_SSL` | Frontend HTTP/HTTPS ports (defaults `8000`/`8443`) |
| `ADMIN_USERNAME`         | Username for the seeded bootstrap superuser (default `admin`)      |
| `ADMIN_PASSWORD`         | Password for the seeded bootstrap superuser (default `admin1234#` — change this before deploying anywhere real) |
| `ADMIN_TOTP_SECRET`      | Optional — pre-provision the bootstrap superuser's TOTP secret so 2FA is already enrolled on first boot. Leave blank to enroll via the UI instead (see [Setting up TOTP](#4-setting-up-totp-2fa)) |
| `GITHUB_TOKEN`           | Optional — only used by this repo's AI coding-agent skills to read/write GitHub issues, not needed to run the app |

`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_TOTP_SECRET` only take effect the
*first* time the backend's `alembic upgrade head` runs (i.e. on a fresh
database) — they seed the initial superuser row, they don't update an
existing one. Changing them in `.env` later has no effect until you drop
the `users` table or start from a fresh database volume.

**Generate a `JWT_SECRET`** (any long random string works — this is what
signs the login session cookie, so treat it like a password):

```bash
# Linux/macOS
openssl rand -hex 32

# Windows PowerShell
[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Paste the result into `.env` as `JWT_SECRET=...`. Pick a strong password for
`MARIADB_ROOT_PASSWORD` too. **Never commit `.env`** (it's already
gitignored).

### 1.4 Start the stack

Run the launcher script for your platform — it detects whether you have
Podman or Docker installed (preferring Podman) and runs the matching
`compose up -d --build` for you, so you don't need to remember which engine
command to type:

```bash
# Linux/macOS
./start.sh
```

```powershell
# Windows
.\start.ps1
```

Under the hood this just runs `<engine> compose -f compose.yml up -d
--build` with whichever of `podman`/`docker` it found on `PATH` — you can
always run that command directly instead if you prefer:

```bash
podman compose -f compose.yml up -d
```

This builds and starts all three containers (`sfsis-mariadb`,
`sfsis-backend`, `sfsis-frontend`). On first start, the backend
automatically runs its database migrations and seeds a default admin
account — no manual database setup needed. Check everything is up:

```bash
podman compose -f compose.yml ps
podman logs sfsis-backend --tail 30
```

To stop the stack: `podman compose -f compose.yml down` (add `-v` only if
you also want to wipe the database volume — this deletes all data).

### 1.5 Updating (`git pull`)

Pulling new code is **not enough by itself** — the backend only applies
database migrations (`alembic upgrade head`) once, at container *start*
(see `backend/entrypoint.sh`), not on a live/running container. After every
`git pull` that could contain backend changes:

```bash
git pull
podman compose -f compose.yml up -d --build
```

`--build` picks up any dependency/Dockerfile changes, and recreating the
`backend` container re-runs its startup script, which runs `alembic upgrade
head` before starting Uvicorn. If you only need the migration to run and
don't want a full rebuild (e.g. you didn't change dependencies), a plain
restart is enough:

```bash
podman compose -f compose.yml restart backend
```

To confirm the migration actually ran, check the logs for the Alembic
lines near the top of a fresh start:

```bash
podman logs sfsis-backend --tail 40
```

If you'd rather trigger it manually without restarting the container at
all (e.g. to check for pending migrations first), run Alembic directly
inside the running container:

```bash
podman exec sfsis-backend uv run alembic upgrade head
```

Restart `sfsis-frontend` the same way (`podman compose -f compose.yml
restart frontend`) whenever frontend code changes — it has no migrations
to worry about, but the running process won't pick up new source files on
its own either.

## 2. Accessing the frontend and logging in

Open a browser to:

- `http://localhost:8000` (plain HTTP), or
- `https://localhost:8443` (HTTPS, self-signed certificate — your browser
  will warn about this the first time; that's expected for local dev)

### 2.1 First run

On this containerized (web) deployment there's no setup step before login —
opening the app connects straight to the backend automatically
(`http://backend:5000`, the internal Docker/Podman network name) and takes
you directly to the **Login** screen. There's no Server Configuration
screen at all on web, and no way to reach one — the address isn't
user-editable here, so it's simply not shown. Just proceed to
[log in](#22-log-in) below.

(A native desktop/mobile build of the frontend still has a one-time
**Server Configuration** screen for entering the backend's address, since
that build genuinely lets you point it at a different backend. That's a
separate build from the one `podman compose up` runs, so it doesn't apply
to the setup this README walks through.)

### 2.2 Log in

On the login screen, fill in:

- **Username**: your `.env`'s `ADMIN_USERNAME` (default `admin`)
- **Password**: your `.env`'s `ADMIN_PASSWORD` (default `admin1234#`)
- **Authenticator**: a 6-digit code — if you left `ADMIN_TOTP_SECRET` blank
  in `.env`, the seeded admin account has no TOTP secret set up yet, so any
  6-digit value is accepted the first time, e.g. `000000`. If you set
  `ADMIN_TOTP_SECRET`, enter the real current code from that secret instead.

Click **Login**.

**Change this password immediately after your first login** — see
[section 3](#3-changing-the-admin-password-first-time) — and set up real
TOTP as soon as convenient — see [section 4](#4-setting-up-totp-2fa).

## 3. Changing the admin password (first time)

From the Home screen, click the **gear (settings) icon** in the top-right
corner, then **Change Password**. Fill in:

- **Current Password**
- **New Password**
- **New Password Confirmation**

Click **Submit**. The new password must differ from the current one, and
the confirmation must match.

## 4. Setting up TOTP (2FA)

From the Home screen's gear menu, click **Setup TOTP**. Then:

1. Click **Generate** — a QR code appears, plus a **Secret Key** text field
   (with a copy button) as a fallback if you can't scan the QR.
2. Open an authenticator app (Google Authenticator, Authy, 1Password, etc.)
   and either scan the QR code or manually add an account using the secret
   key.
3. Enter the current 6-digit code from your authenticator app into
   **Verification Code**.
4. Click **Save**.

From then on, every login requires the live 6-digit code from your
authenticator app instead of an arbitrary placeholder.

## 5. Setting up users and permissions

Open the **Users** module from Home (search or click its card). This screen
is only visible to users who already have access to it — the seeded
`admin` superuser always does.

- **Add a user**: click **Add New**, fill in Username, Email, Password,
  Active (Yes/No), Superuser (Yes/No), and optionally Department, then
  submit.
- **Edit a user**: click a row in the list. On the edit screen you can
  update the same fields (leave Password blank to keep the existing one).
- **Grant module access**: still on the edit screen, scroll to the **Module
  Access** table below the form — it lists every module this user already
  has access to. Click **Add Permission** (the toolbar button above that
  table) to open a new screen listing every module the user does *not* yet
  have — check as many as you need (the list is filterable), or use the
  **Select** column's two header icons to check or uncheck every listed
  module at once, then click **Submit**. You're returned to the edit screen
  with the new modules added to the access table. There's no group/role
  concept here: every module a
  non-superuser needs must be granted explicitly, including basic ones like
  Stock In/Stock Out.
- **Revoke module access**: on that same Module Access table, each row has
  a delete icon — click it, confirm, and that one module's access is
  revoked immediately. To revoke several at once, click the **Select All**
  button above the table (every row gets a checkbox, all pre-checked) or
  **Select None** (same checkboxes, but starting unchecked so you can pick
  which ones to remove) — check/uncheck rows as needed, then click **Remove
  Selected** and confirm. **Cancel** backs out of that mode without
  removing anything.
- **Delete a user**: the trash icon on the edit screen. This also removes
  all of that user's module grants.

Superusers bypass the permission check entirely — a normal safeguard for
the very first admin, since someone has to be able to grant permissions
before any exist.

## 6. Setting up master material

Materials link to two other master lists, so it's easiest to set those up
first:

- **Unit of Material** (e.g. `PCS`/Pieces, `KG`/Kilogram, `L`/Litres) — open
  the **Unit of Material** module and add any units you need. A large
  starter catalog (22 common units) is already seeded out of the box, so
  you often won't need to add any. **Units can't be deleted** once created
  — there's no delete button on this screen at all — since every material
  must always point at exactly one valid unit.
- **Category** (optional, e.g. Raw Materials, Packaging, Tools) — open the
  **Categories** module and add your own if you want materials grouped by
  category; this link is optional and can be left blank.

Then open the **Materials** module, click **Add New**, and fill in:

- **Code** — a unique material code
- **Name** — the material's display name
- **Category** — optional, pick from your categories list
- **Unit of Material** — **required**, pick from your units list; every
  material has exactly one unit, shown alongside its quantity everywhere
  the app displays a qty for that material (stock browse, stock in/out
  items, usage report)
- **Active** — Yes/No, defaults to Yes

Materials don't carry their own supplier — a material can come from many
different suppliers over time, so supplier is instead recorded per
receiving batch (see [Stock in](#10-stock-in-receiving) below).

Click **Submit**. Edit existing materials from the list the same way as
users. **Materials can't be deleted** — the edit screen has no delete
button at all, since removing a material could break its receiving/stock/
issue history. To retire a material instead of deleting it, edit it and set
**Active** to **No**: an inactive material still shows up everywhere with
its full historical/on-hand data, it just can't be selected as the material
on a *new* Stock In receiving line going forward (editing an existing
receiving line for it is still allowed).

## 7. Setting up master supplier

Open the **Suppliers** module. Click **Add New**, fill in **Code** and
**Name**, then **Submit**. Same edit/delete pattern and delete-history
protection as location/department below. Suppliers are picked per receiving
batch on the Stock In header (see [Stock in](#10-stock-in-receiving) below)
rather than per material, since one material can be sourced from several
different suppliers over time.

## 8. Setting up master location

Open the **Locations** module (e.g. warehouse zones, shelves, or storage
areas). Click **Add New** and fill in **Code** and **Name**, then
**Submit**. Same edit/delete pattern, same delete-history protection as
material.

## 9. Setting up master department

Open the **Departments** module (who *consumes* inventory — used later for
usage reporting). Click **Add New**, fill in **Code** and **Name**, then
**Submit**. Same edit/delete pattern and delete-history protection.

## 10. Stock in (receiving)

1. Open the **Stock In** module and click **Add New**. Fill in the header:
   **Date**, **Description** (e.g. a PO/DO reference), and **Supplier**
   (optional, pick from your suppliers list), then **Submit** — this takes
   you to the header's edit screen.
2. On that screen, under **Items**, click the **+** button to add a
   receiving line. Fill in:
   - **Material** (select)
   - **Location** (select — where this batch is stored)
   - **Qty Received**
   - **Price** — the buy price for this batch
   - **Remarks** (optional)

   Submit to return to the header screen; repeat **+** for each additional
   item/material received under this same header.
3. Click any existing item row to edit its qty/price/remarks (material and
   location are fixed once created).

Each receipt recalculates that material's **moving average price** and adds
to its on-hand quantity — you don't need to do anything else; it's
automatic.

## 11. Stock out (issuing)

1. Open the **Stock Out** module and click **Add New**. Fill in the header:
   **Date**, **Department** (required — every issue must be attributed to a
   department for usage reporting), and **Description**, then **Submit**.
2. On the header's edit screen, under **Items**, click **+** to add an
   issue line. Fill in:
   - **Material** (select)
   - **Location** (select — where to deduct from)
   - **Qty Out**
   - **Remarks** (optional)

   The price/value is captured automatically from that material's current
   moving average price — there's no price field to fill in.
3. Repeat **+** for each material/location issued under this header.

Stock is deducted oldest-lot-first from the chosen location. If there
isn't enough stock at that location, you'll get an "insufficient stock"
error before anything is changed. Stock out items can't be edited or
deleted once created (to "undo" one, receive the quantity back in via
Stock In).

## 12. Browsing current stock

Open the **Stock Browse** module — a read-only list of current on-hand
quantity (with its unit, e.g. `50 PCS`) per material + location, along with
each material's moving average price and total value (`qty × average
price`). No add/edit here; it's a live snapshot for reference.

## 13. Checking usage

Open the **Usage Report** module — a read-only summary of total quantity
issued (with unit) and total cost per department + material, aggregated
across every Stock Out transaction. Use it to answer "how much of what has
each department consumed, and at what cost." No add/edit here either. Use
the **Start Date**/**End Date** fields and **Apply Filters** button above
the table to narrow the report to a date range.

## 14. Filtering and searching table data

Every list screen (Users, Materials, Stock In, etc.) offers two ways to
narrow down what's showing, in addition to the sortable column headers:

### 14.1 Keyword search

The search bar in the table's toolbar searches across that table's main
text columns at once (e.g. code and name) — type a few characters and the
list updates as you type.

### 14.2 Per-column filters

Click the **filter icon** in the table's toolbar to open a **filter row**
just below the column headers, with one input aligned under each column.

- Each field filters **live** — the list updates on every keystroke, no
  "Apply" button to click.
- A field's leading funnel icon marks it as filterable; its trailing **✕**
  clears just that one column's filter and re-fetches immediately.
- Numeric columns (like quantities or prices) accept operator syntax, not
  just a plain number:
  - `50` — exact match
  - `>=50` — greater than or equal
  - `<=50` — less than or equal
  - `>50`, `<50`, `!=50` — greater/less than, not equal
  - `>=10and<=50` — a range (join multiple conditions with `and`)
- Keyword search and per-column filters are **mutually exclusive** — using
  one clears the other, since they can't be combined on the same request.
- Closing the filter row (click the filter icon again) clears every active
  column filter, so a hidden row never leaves a filter silently applied.

## 15. Download and Upload Features

Most list screens (Users, Materials, Stock In, etc.) have a hamburger menu icon (☰) on the right side of their toolbar. This menu provides options for downloading the current data or uploading new data.

### 15.1 Downloading Data

Click the hamburger menu and select one of the "Download as..." options (CSV, XLSX, etc.). This will download a file containing **all** records that match the current search filter and sort order, not just the rows currently visible on the page.

### 15.2 Uploading Data into a Table

This feature allows you to populate editable fields in a table (like the item entry grid when issuing stock) directly from a CSV or XLSX file.

1.  **Prepare your file**: Create a CSV or XLSX file where the column headers match the labels or field names of the table you want to fill.
    -   Include columns for any key fields (like "Material" or "Location") to identify which rows to update.
    -   Include columns for the editable fields you want to populate (like "Qty Issue").
2.  **Upload**:
    -   Click the hamburger menu (☰) on the table's toolbar.
    -   Select "Upload from CSV" or "Upload from XLSX".
    -   Choose your prepared file.
3.  **Population**: The system will read the file and populate the values into the matching editable cells on the screen.
    -   If your file includes key columns, it will match rows based on those keys.
    -   If no key columns are found, it will populate rows sequentially.
    -   The data is only populated on the screen; you still need to click the main **Submit** button for the screen to save the changes.

### 15.3 Bulk Creating New Records

On screens where you create new records (like "Add New User" or "Add New Material"), the toolbar on the "New" screen has its own hamburger menu (☰). This allows you to create many records at once from a file. It's available on every one of these "Add New" screens: **Locations**, **Suppliers**, **Departments**, **Categories**, **Materials**, **Unit of Material**, **Module Groups**, **Modules**, **Users**, **Stock In** (headers), and **Stock Out** (headers).

1.  **Prepare your file**: Create a CSV or XLSX file where the column headers match the labels or field names of the form. For example, a user bulk-upload file would have columns like "Username", "Email", and "Password".
    -   For a column that picks from another list (e.g. Materials' "Category" or "Unit of Material", or Stock In's "Supplier"), you can type either the full `"CODE - Name"` text shown in that dropdown, or just the bare **code** on its own — e.g. `PCS` works just as well as `PCS - Pieces`.
2.  **Upload**:
    -   Navigate to the "New" screen for the module (e.g., Users -> Add New).
    -   Click the hamburger menu (☰) on the toolbar.
    -   Select "Upload bulk from CSV/XLSX".
    -   Choose your prepared file.
3.  **Creation**: The system will process the file and attempt to create a new record for each row.
    -   The entire upload is **all or nothing**. If any single row fails validation (e.g., a duplicate username, a missing required field, or a code that doesn't match anything), the entire operation is rolled back, and no records are created. An error message will indicate which row and what the error was.
    -   If all rows are valid, they will all be created in the database.

### 15.4 Bulk Uploading Items into a Stock In or Stock Out Header

Beyond bulk-creating headers (above), the item-entry screens under a Stock In or Stock Out header also each have their own hamburger menu (☰) for bulk-adding line items — a faster alternative to clicking **+** and filling in one item at a time, and unlike the header bulk-create, **one file can list several different materials** in the same upload.

- **Stock In** (`Stock In` → open a header → **+ Add Item** → ☰): columns **Material | Location | Qty Received | Price | Remarks**.
- **Stock Out** (`Stock Out` → open a header → **Issue Stock** → ☰, next to the Material dropdown — the bulk upload here is independent of that dropdown, so you don't need to select a material first): columns **Material | Location | Qty Issue | Remarks**.

Material and Location accept either the full `"CODE - Name"` text or just the bare code — e.g. both `SKU-1 - Widget` and `SKU-1` are accepted for Material, and both `A1 - A1` and `A1` for Location. Like every other bulk upload, this is **all or nothing**: for Stock Out specifically, if any row would exceed what's currently on hand at that material/location, the whole batch is rejected before anything is deducted.

## 16. Paging through table data (lazy-load vs. pagination)

Every list screen shows a small footer strip below the table with a
**"Record X - Y of Z"** count on the left, and a **mode toggle** button on
the right. There are two ways to page through a long list:

### 16.1 Lazy load (the default)

By default, a table simply loads more rows automatically as you scroll
down — no page numbers, no clicking. This is how every list screen has
always worked, and nothing changes here unless you switch modes yourself.

### 16.2 Pagination

Click the toggle button in the footer's bottom-right corner to switch to
classic numbered pagination instead. Once switched, the footer shows:

- An editable **rows-per-page** box — type a new number and press Enter
  (or click away) to apply it; this also jumps you back to page 1.
- **First / Previous / [page numbers] / Next / Last** buttons — the
  current page is highlighted. On a long list, only a handful of page
  numbers are shown around the current page (with `...` gaps), not every
  page number at once.

Click the toggle again to switch back to lazy-load scrolling at any time.

**The mode you pick isn't saved** — it only applies to the screen you're
currently on. Navigating away and back (or reloading the page) always
starts fresh in lazy-load mode.
