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
7. [Setting up master location](#7-setting-up-master-location)
8. [Setting up master department](#8-setting-up-master-department)
9. [Stock in (receiving)](#9-stock-in-receiving)
10. [Stock out (issuing)](#10-stock-out-issuing)
11. [Browsing current stock](#11-browsing-current-stock)
12. [Checking usage](#12-checking-usage)
13. [Download and Upload Features](#13-download-and-upload-features)

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
| `GITHUB_TOKEN`           | Optional — only used by this repo's AI coding-agent skills to read/write GitHub issues, not needed to run the app |

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

### 2.1 Server Configuration (first run only)

The very first time you open the app it forces you to the **Server
Configuration** screen, asking for the backend's address. The containerized
setup already defaults this correctly out of the box
(`http://backend:5000`, the internal Docker/Podman network name), so on a
normal `podman compose up` deployment **you usually don't need to change
anything** — just proceed to login.

If you do need to open Server Config again later (e.g. pointing at a
different backend), the field is labeled **Server URL**. Enter the address
and click **Save Configuration**. Important: because the frontend container
itself makes the HTTP calls (not your browser), the address must be the
backend's *container network name* (`http://backend:5000` or
`https://backend:5443`), **not** `http://localhost:5000` — `localhost`
inside the frontend container refers to the frontend container itself.

### 2.2 Log in

On the login screen, fill in:

- **Username**: `admin`
- **Password**: `admin1234#`
- **Authenticator**: a 6-digit code — since the seeded admin account has no
  TOTP secret set up yet, any 6-digit value is accepted the first time, e.g.
  `000000`

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
  Access** checklist below the form — one checkbox per module. Check every
  module this user should be able to open, then click **Save Permissions**.
  There's no group/role concept here: every module a non-superuser needs
  must be checked explicitly, including basic ones like Stock In/Stock Out.
- **Delete a user**: the trash icon on the edit screen. This also removes
  all of that user's module grants.

Superusers bypass the permission check entirely — a normal safeguard for
the very first admin, since someone has to be able to grant permissions
before any exist.

## 6. Setting up master material

Open the **Materials** module. Click **Add New** and fill in:

- **Code** — a unique material code
- **Name** — the material's display name
- **Supplier** — optional, pick from your suppliers list (set up suppliers
  first via the **Suppliers** module if you want to link one)

Click **Submit**. Edit or delete existing materials from the list the same
way as users. A material can't be deleted once it has any receiving/stock/
issue history — you'll get a clear error instead of a broken delete.

## 7. Setting up master location

Open the **Locations** module (e.g. warehouse zones, shelves, or storage
areas). Click **Add New** and fill in **Code** and **Name**, then
**Submit**. Same edit/delete pattern, same delete-history protection as
material.

## 8. Setting up master department

Open the **Departments** module (who *consumes* inventory — used later for
usage reporting). Click **Add New**, fill in **Code** and **Name**, then
**Submit**. Same edit/delete pattern and delete-history protection.

## 9. Stock in (receiving)

1. Open the **Stock In** module and click **Add New**. Fill in the header:
   **Date** and **Description** (e.g. a PO/DO reference), then **Submit** —
   this takes you to the header's edit screen.
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

## 10. Stock out (issuing)

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

## 11. Browsing current stock

Open the **Stock Browse** module — a read-only list of current on-hand
quantity per material + location, along with each material's moving
average price and total value (`qty × average price`). No add/edit here;
it's a live snapshot for reference.

## 12. Checking usage

Open the **Usage Report** module — a read-only summary of total quantity
issued and total cost per department + material, aggregated across every
Stock Out transaction. Use it to answer "how much of what has each
department consumed, and at what cost." No add/edit here either.

## 13. Download and Upload Features

Most list screens (Users, Materials, Stock In, etc.) have a hamburger menu icon (☰) on the right side of their toolbar. This menu provides options for downloading the current data or uploading new data.

### 13.1 Downloading Data

Click the hamburger menu and select one of the "Download as..." options (CSV, XLSX, etc.). This will download a file containing **all** records that match the current search filter and sort order, not just the rows currently visible on the page.

### 13.2 Uploading Data into a Table

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

### 13.3 Bulk Creating New Records

On screens where you create new records (like "Add New User" or "Add New Material"), the toolbar on the "New" screen has its own hamburger menu (☰). This allows you to create many records at once from a file.

1.  **Prepare your file**: Create a CSV or XLSX file where the column headers match the labels or field names of the form. For example, a user bulk-upload file would have columns like "Username", "Email", and "Password".
2.  **Upload**:
    -   Navigate to the "New" screen for the module (e.g., Users -> Add New).
    -   Click the hamburger menu (☰) on the toolbar.
    -   Select "Upload bulk from CSV/XLSX".
    -   Choose your prepared file.
3.  **Creation**: The system will process the file and attempt to create a new record for each row.
    -   The entire upload is **all or nothing**. If any single row fails validation (e.g., a duplicate username, a missing required field), the entire operation is rolled back, and no records are created. An error message will indicate which row and what the error was.
    -   If all rows are valid, they will all be created in the database.
