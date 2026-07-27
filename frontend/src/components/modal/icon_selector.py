"""Reusable icon-picker popup - a sample, first real consumer of issue
#45's `"radio"` column type (by-column/default mode: exactly one row
selectable across the whole list). An `ft.AlertDialog` (same
`page.overlay.append(...)` + `dialog.open = True` pattern as this app's
only other dialog precedent, `components/table/remove.py`'s confirm
dialogs) wrapping a plain `components/table/table.py::Table` that lists a
small static catalog of Material icon names - deliberately reusing
Table/TableColumns' own radio machinery instead of hand-rolling a bespoke
`ft.RadioGroup` for this one picker, both to exercise #45 with a real
caller and so this list gets the same searchable/filterable/scrollable
behavior every other Table in this app already has, for free.

Triggered from `components/form/icon_picker.py`'s trailing icon button,
but has no dependency on that specific caller - any screen wanting "pick
one icon name from a small catalog" can construct this directly:

    IconSelectorModal(page, current_value="chevron_right", on_confirm=fn).open()

`on_confirm(icon_name: str)` fires only when the user presses Confirm
with a row actually selected; Close (or Confirm with nothing selected)
discards the in-progress pick with no callback at all.
"""

import flet as ft

from components.table.table import Table

# A small, generically useful starter catalog - not exhaustive (Material
# Symbols has thousands), just enough common, inventory-app-relevant
# icons to make this a real, usable picker. Plain lowercase-with-
# underscore strings, matching the exact format this app's `"icon"`
# fields already store (see ap_module's "e.g. chevron_right" hint) and
# confirmed to render directly via `ft.Icon(icon="chevron_right")` with
# no enum lookup needed.
ICON_CATALOG: list[str] = [
    "apps", "home", "dashboard", "settings", "person", "group",
    "category", "inventory", "inventory_2", "warehouse", "store",
    "local_shipping", "receipt", "receipt_long", "assignment",
    "description", "folder", "label", "text_fields", "sort", "notes",
    "chevron_right", "arrow_forward", "bar_chart", "pie_chart",
    "analytics", "table_chart", "list", "grid_view", "view_list",
    "search", "filter_list", "add", "edit", "delete", "save", "close",
    "check", "check_circle", "cancel", "info", "warning", "error",
    "help", "lock", "lock_open", "visibility", "email", "phone",
    "location_on", "map", "place", "business", "account_circle",
    "admin_panel_settings", "security", "vpn_key", "shopping_cart",
    "local_mall", "payments", "attach_money", "trending_up",
    "swap_horiz", "sync", "refresh", "history", "schedule", "event",
    "calendar_month", "today", "upload", "download", "cloud", "print",
    "qr_code", "star", "favorite", "flag", "bookmark", "link", "image",
    "notifications", "menu", "more_vert", "arrow_back", "expand_more",
    "expand_less", "fullscreen",
]

# Fixed pixel widths for the picker's 3 columns (preview icon, name,
# radio) - small and constant regardless of the host page's own width, see
# the `manually_resized` note in `open()` below for why this table can't
# just size itself the normal way. `_DIALOG_WIDTH` comfortably fits their
# sum plus the same margin/spacing/padding constants
# `Columns.get_usable_width()` itself accounts for.
_COLUMN_WIDTHS = (50, 280, 60)
_DIALOG_WIDTH = 480


class _NullView:
    """Table expects `parent.view.show_error()/show_success()` for its
    own error paths (network failures, remove-column errors) - none of
    which this static, network-free picker table can ever hit, but the
    attribute must exist or Table's error-handling code would itself
    raise AttributeError instead of showing a message."""

    def show_error(self, message: str) -> None:
        pass

    def show_success(self, message: str) -> None:
        pass


class _PickerParent:
    """Minimal stand-in for the `parent` a `Table` normally expects
    (`.module`/`.screen`/`.record_id`/`.view`) - this picker is a dialog,
    not a real routed module screen, so it has none of those for real."""

    def __init__(self):
        self.module = "icon_picker"
        self.screen = "select"
        self.record_id = None
        self.view = _NullView()


class IconSelectorModal:
    def __init__(self, page: ft.Page, current_value: str, on_confirm):
        self.page = page
        self.current_value = (current_value or "").strip()
        self.on_confirm = on_confirm
        self.dialog: ft.AlertDialog | None = None
        self.table: Table | None = None

    def open(self) -> None:
        fields = [
            {"name": "preview", "label": "", "format": "icon"},
            {"name": "name", "label": "Icon"},
            {
                "name": "picked", "label": "Select",
                "type": "radio", "radio_mode": "column",
            },
        ]
        # is_inside_form=True: this table has nowhere to fetch data FROM
        # (no C_icon_picker/get_detail endpoint - the catalog above is the
        # whole dataset) - same "static local list, no initial fetch"
        # precedent as stock_out/item_new.py's per-location qty table.
        self.table = Table(
            page=self.page,
            parent=_PickerParent(),
            name="icon_picker",
            fields=fields,
            is_inside_form=True,
        )
        # TableColumns.get_usable_width() sizes columns off the PAGE's own
        # width (Columns.get_screen_width() reads self.page.width directly),
        # not this dialog's actual rendered width - inside a small
        # AlertDialog that computes columns thousands of pixels wide,
        # rendering everything far outside the dialog's own visible/clipped
        # bounds (confirmed live: an apparently-empty table, rows present
        # in the DOM but their content laid out off-screen to the right).
        # `manually_resized=True` + a pre-set `widths` list is this table's
        # own existing escape hatch for "keep these widths, don't recompute
        # from content/page size" (added for the user's own resize-drag
        # feature) - repurposed here to give this modal's table small,
        # fixed widths that actually fit `_DIALOG_WIDTH` instead.
        self.table.columns.widths = list(_COLUMN_WIDTHS)
        self.table.columns.manually_resized = True
        self.table.data = [
            {
                "preview": name,
                "name": name,
                "picked": name == self.current_value,
            }
            for name in ICON_CATALOG
        ]

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Choose an Icon"),
            content=ft.Container(
                content=self.table.build(),
                width=_DIALOG_WIDTH,
                height=480,
            ),
            actions=[
                ft.TextButton("Close", on_click=self._on_close),
                ft.Button(
                    content="Confirm",
                    on_click=self._on_confirm,
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.ON_PRIMARY,
                ),
            ],
        )
        self.page.overlay.append(self.dialog)
        self.dialog.open = True
        self._safe_update()

    def _on_close(self, e) -> None:
        self._close()

    def _on_confirm(self, e) -> None:
        picked_name = self._read_selected()
        self._close()
        if picked_name and self.on_confirm:
            self.on_confirm(picked_name)

    def _read_selected(self) -> str | None:
        for row in self.table.get_rows_with_input_values():
            if row.get("picked"):
                return row.get("name")
        return None

    def _close(self) -> None:
        if self.dialog is not None:
            self.dialog.open = False
        self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError:
            pass
