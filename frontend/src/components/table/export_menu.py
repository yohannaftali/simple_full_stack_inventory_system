"""Hamburger-icon download menu for the table toolbar - see AGENTS.md's
"Table export convention". Offers the table's full filtered/sorted result
set (not just the currently loaded page) in 6 formats, generated
server-side by the matching backend `GET C_{module}/export` endpoint and
proxied through the frontend's own `/download/{module}` route (see
`asgi.py`) so the browser gets a real `Content-Disposition: attachment`
download with the right filename - the backend call itself happens in the
Flet process, which is the only place that holds the session cookie (see
AGENTS.md's "Container networking gotcha").
"""

import flet as ft

# (format, menu label, icon) - label text matches the issue's exact wording.
_FORMAT_OPTIONS = [
    ("csv", "Download as CSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("tsv", "Download as TSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("scsv", "Download as SCSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("xlsx", "Download as XLSX", ft.Icons.GRID_ON),
    ("ods", "Download as ODS", ft.Icons.GRID_ON),
    ("pdf", "Download as PDF", ft.Icons.PICTURE_AS_PDF_OUTLINED),
]


class TableExportMenu:
    """Wraps a `PopupMenuButton` (hamburger icon) - `parent` is the owning
    `Table`, read for its current module/filter/sort/custom_param state at
    click time (not cached at build time, so it always reflects whatever
    the user has searched/sorted for)."""

    def __init__(self, page: ft.Page, parent):
        self.page = page
        self.parent = parent  # Table
        self.menu = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            tooltip="Download",
            items=[
                ft.PopupMenuItem(content=label, icon=icon, on_click=self._handler(fmt))
                for fmt, label, icon in _FORMAT_OPTIONS
            ],
        )

    def build(self):
        return self.menu

    def _handler(self, fmt: str):
        def on_click(e):
            self._download(fmt)

        return on_click

    def _download(self, fmt: str) -> None:
        table = self.parent
        query = f"format={fmt}"
        if table.filter:
            query += f"&table-keyword-filter={table.filter}"
        query += table.columns.serialize_sort()
        for key, value in table.custom_param.items():
            query += f"&{key}={value}"

        # Name this session's own server-side session file explicitly (see
        # asgi.py's download_export) - the download request comes from the
        # browser, whose sfsis_client_id cookie can lag behind or differ
        # from the id this (logged-in) Flet session actually persists
        # under; the session file named here is the one holding the login.
        client_id = None
        if isinstance(self.page.data, dict):
            client_id = self.page.data.get("client_id")
        if client_id:
            query += f"&client_id={client_id}"

        # A Content-Disposition: attachment response never navigates the
        # browser away from the app (same as clicking a plain <a download>
        # link) - no need for a popup window/new tab just to keep the
        # current page alive.
        #
        # The table's own name is part of the path because one module can
        # hold several tables (e.g. stock_in's "detail" header list on
        # index and its "items" sub-table on edit) - the proxy maps
        # /download/{module}/{name} to C_{module}/export_{name}, mirroring
        # the get_{name} convention the table's own data endpoint follows.
        url = f"/download/{table.module}/{table.name}?{query}"
        self.page.run_task(self._launch, url)

    async def _launch(self, url: str) -> None:
        # Page.launch_url is genuinely `async def`, but its @deprecated
        # wrapper (flet/utils/deprecated.py) re-wraps it in a plain sync
        # `def`, so `inspect.iscoroutinefunction(page.launch_url)` is
        # False and passing it directly to `page.run_task()` raises
        # "handler must be a coroutine function". This local wrapper is a
        # real coroutine function, so run_task's check passes; it just
        # awaits the deprecated call underneath (still triggers Flet's own
        # DeprecationWarning, which is harmless).
        await self.page.launch_url(url)
