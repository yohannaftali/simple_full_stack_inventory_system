"""Hamburger-icon download menu for the List toolbar (issue #56) - the
`List` equivalent of `components/table/menu.py::TableMenu`, offering the
same 6 formats against the same already-generic
`GET C_{module}/export_{name}` backend endpoint + `/download/{module}/{name}`
proxy route, with no backend changes.

Not a literal reuse of `TableMenu`: that class builds its query string from
`table.columns.serialize_sort()` and `table.custom_param`, neither of which
`List` has. `List` instead carries `filter_row.serialize()` (issue #55's own
`ListFilter`), which already emits the same `sort-fields[...]`/
`{field}-filter` wire format after that issue's follow-up work, so this
class reads from `parent.filter`/`parent.filter_row` instead.

Upload is deliberately out of scope here (unlike `TableMenu`, which also
offers CSV/XLSX upload for tables with editable cells) - `List`'s tiles are
read-only labels today, with no editable-cell field types the way `Table`
rows can have, so there is nothing for an upload to populate.
"""

import flet as ft

# (format, menu label, icon) - same options/labels as TableMenu's own.
_FORMAT_OPTIONS = [
    ("csv", "Download as CSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("tsv", "Download as TSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("scsv", "Download as SCSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("xlsx", "Download as XLSX", ft.Icons.GRID_ON),
    ("ods", "Download as ODS", ft.Icons.GRID_ON),
    ("pdf", "Download as PDF", ft.Icons.PICTURE_AS_PDF_OUTLINED),
]


class ListMenu:
    """Wraps a `PopupMenuButton` (hamburger icon) - `parent` is the owning
    `List`, read for its current module/name/filter state at click time,
    not build time. Sized identically to `TableMenu`'s own hamburger so the
    two look consistent wherever a screen switches between the two views
    (issue #56's Table/List toggle)."""

    def __init__(self, page: ft.Page, parent):
        self.page = page
        self.parent = parent  # List

        menu_items = [
            ft.PopupMenuItem(content=label, icon=icon, on_click=self._download_handler(fmt))
            for fmt, label, icon in _FORMAT_OPTIONS
        ]

        self.menu = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            icon_size=20,
            tooltip="Download",
            items=menu_items,
            height=32,
            width=32,
            padding=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=16),
            ),
        )

    def build(self):
        return self.menu

    def _download_handler(self, fmt: str):
        def on_click(e):
            self._download(fmt)

        return on_click

    def _download(self, fmt: str) -> None:
        parent = self.parent
        query = f"format={fmt}"
        if parent.filter:
            query += f"&table-keyword-filter={parent.filter}"
        query += parent.filter_row.serialize()

        client_id = None
        if isinstance(self.page.data, dict):
            client_id = self.page.data.get("client_id")
        if client_id:
            query += f"&client_id={client_id}"

        url = f"/download/{parent.module}/{parent.name}?{query}"
        self.page.run_task(self._launch, url)

    async def _launch(self, url: str) -> None:
        await self.page.launch_url(url)
