"""Reusable single/bulk row-remove capability for `components/table/table.py`
(issue #42), adapted from senar's `y.panel.js` (`buttonRemove` cell) and
`y.form.js` (`listenerClickClassRowRemove`/`listenerClickClassHeaderRemove`
and friends).

Opt-in via `Table(..., on_remove_row=..., on_remove_rows=...)` - when either
callback is supplied, `Table.__init__` builds a `TableRemove` and appends a
synthetic trailing `"type": "remove"` field to its own `fields` list, so no
caller ever needs to hand-author that column. `Table` has no idea what a
row-remove actually does server-side; each callback takes the row dict(s)
to remove and returns an error message string on failure, or `None` on
success - `TableRemove` then drops the row(s) from `Table.data` and asks
`Table.load()` to re-render (the same "recompute + rebuild from current
data" path every other Table interaction already uses for a sort click or a
resize tick, so no bespoke re-render logic was needed here either).

Two modes:
- **single** (default): every row shows a delete icon; clicking one asks
  for confirmation, then removes just that row.
- **multiple**: entered via one of two header buttons - "select all"
  (every row starts pre-selected) or "select none" (every row starts
  unselected, letting an admin cherry-pick). While in this mode, clicking a
  row toggles its own selected state instead of deleting immediately. Two
  header buttons are shown here too - "remove selected" (bulk-deletes
  whatever's selected, confirmed first, or silently returns to single mode
  if nothing is selected) and "cancel" (returns straight to single mode,
  no confirmation, no delete).

**Not a Shift+click modifier gesture, despite senar's own reference using
one** - the original design mirrored senar's single header button that
toggled behavior on a held Shift key (`Page.on_keyboard_event`). Confirmed
broken via live testing *and* server-side diagnostic logging: the browser
never delivered a single keyboard event to the server in this deployment
(zero `on_keyboard_event` invocations logged across three real click-only
test passes, including once after moving registration to page boot in
`main.py` to rule out a registration-timing race). Further checked whether
any click/tap/gesture event in this Flet 0.85.3 build carries a keyboard-
modifier flag as a fallback (`TapEvent`, `GestureDetector`'s pointer
events) - none do; `Page.on_keyboard_event`'s `KeyboardEvent.shift` is the
*only* modifier-key signal Flet exposes at all, and it isn't reaching the
server here (most likely because a click-only interaction flow never gives
the Flutter canvas actual DOM keyboard focus, which the browser requires
before it will forward key events to it). Rather than keep guessing at
browser-side focus/event routing with no way to verify short of another
live round-trip, replaced the single modifier-key button with two always-
visible, click-only buttons per mode - functionally identical outcomes,
zero dependency on a keyboard channel that doesn't work in this
environment. See CHANGE_HISTORY.md's 2026-07-21 entries for the full
diagnostic trail (two earlier fix attempts, both confirmed still broken by
the user before this rewrite).

Confirmation dialogs reuse this app's only existing precedent
(`components/troubleshooting/body.py`'s hard-reset confirm): a plain
`ft.AlertDialog` appended to `page.overlay`.
"""

import flet as ft

from components.button import Button

_ICON_SELECT_ALL = ft.Icons.CHECK_BOX
_ICON_SELECT_NONE = ft.Icons.CHECK_BOX_OUTLINE_BLANK
_ICON_EXECUTE_BULK = ft.Icons.DELETE
_ICON_CANCEL = ft.Icons.CLOSE
_ICON_ROW_REMOVE = ft.Icons.DELETE
# Public (no leading underscore) - reused as-is by rows.py's generic
# "checkbox" editable-cell type (issue #44) for a visually consistent
# checked/unchecked look across the whole Table component, not just this
# remove column's own per-row selection state.
ICON_CHECKBOX_CHECKED = ft.Icons.CHECK_BOX
ICON_CHECKBOX_UNCHECKED = ft.Icons.CHECK_BOX_OUTLINE_BLANK

# Compact paired header buttons (via components/button.py::Button, same
# 32dp/16-radius sizing as every other compact icon button in this app -
# see TableToolbar/ModuleToolbar) need to fit two side by side in one
# column - _EDITABLE_MIN_WIDTHS["remove"] in columns.py is sized for this.
_HEADER_BUTTON_SIZE = 28


class TableRemove:
    MODE_SINGLE = "single"
    MODE_MULTIPLE = "multiple"

    def __init__(self, page: ft.Page, table, on_remove_row=None, on_remove_rows=None):
        self.page = page
        self.table = table  # owning Table instance
        self.on_remove_row = on_remove_row
        self.on_remove_rows = on_remove_rows
        self.mode = self.MODE_SINGLE
        self.selected: set[int] = set()

    def build_header_cell(self, width: int | None) -> ft.Control:
        if self.mode == self.MODE_SINGLE:
            buttons = [
                Button(
                    icon=_ICON_SELECT_ALL,
                    on_click=self._on_select_all_click,
                    tooltip="Select all rows to remove",
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    size=_HEADER_BUTTON_SIZE,
                ).build(),
                Button(
                    icon=_ICON_SELECT_NONE,
                    on_click=self._on_select_none_click,
                    tooltip="Choose rows to remove",
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    size=_HEADER_BUTTON_SIZE,
                ).build(),
            ]
        else:
            buttons = [
                Button(
                    icon=_ICON_EXECUTE_BULK,
                    on_click=self._on_bulk_execute_click,
                    tooltip="Remove selected rows",
                    icon_color=ft.Colors.ERROR,
                    size=_HEADER_BUTTON_SIZE,
                ).build(),
                Button(
                    icon=_ICON_CANCEL,
                    on_click=self._on_cancel_click,
                    tooltip="Cancel",
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    size=_HEADER_BUTTON_SIZE,
                ).build(),
            ]
        row = ft.Row(buttons, spacing=0, alignment=ft.MainAxisAlignment.CENTER, tight=True)
        return ft.Container(content=row, width=width, alignment=ft.Alignment.CENTER)

    def build_row_cell(self, row_index: int, width: int | None) -> ft.Control:
        if self.mode == self.MODE_SINGLE:
            icon, tooltip, color = _ICON_ROW_REMOVE, "Remove", ft.Colors.ERROR
        elif row_index in self.selected:
            icon, tooltip, color = ICON_CHECKBOX_CHECKED, "Selected", ft.Colors.PRIMARY
        else:
            icon, tooltip, color = (
                ICON_CHECKBOX_UNCHECKED,
                "Select",
                ft.Colors.ON_SURFACE_VARIANT,
            )
        control = ft.IconButton(
            icon=icon,
            icon_color=color,
            tooltip=tooltip,
            on_click=lambda e, i=row_index: self._on_row_click(i),
        )
        return ft.Container(
            content=control,
            width=width,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(horizontal=4),
        )

    def reset_for_reload(self) -> None:
        """Called by `Table.get_data()` right before rendering a genuinely
        new server response (not appended) - a sort/filter/page change
        invalidates whatever was selected against the previous result set.
        Deliberately NOT called from `TableRows.load()` itself (issue #42
        follow-up fix) - that method also runs for `TableRemove`'s own
        local re-renders (mode toggle, row-select toggle, post-removal
        refresh via `_rerender()`), and resetting there would wipe the very
        mode/selection state those re-renders exist to display."""
        self.mode = self.MODE_SINGLE
        self.selected = set()

    def _on_select_all_click(self, e) -> None:
        self.mode = self.MODE_MULTIPLE
        self.selected = set(range(len(self.table.data)))
        self._rerender()

    def _on_select_none_click(self, e) -> None:
        self.mode = self.MODE_MULTIPLE
        self.selected = set()
        self._rerender()

    def _on_bulk_execute_click(self, e) -> None:
        if not self.selected:
            self.mode = self.MODE_SINGLE
            self._rerender()
            return
        self._confirm_bulk_remove()

    def _on_cancel_click(self, e) -> None:
        self.mode = self.MODE_SINGLE
        self.selected = set()
        self._rerender()

    def _on_row_click(self, row_index: int) -> None:
        if self.mode == self.MODE_SINGLE:
            self._confirm_single_remove(row_index)
            return

        if row_index in self.selected:
            self.selected.discard(row_index)
        else:
            self.selected.add(row_index)
        self._rerender()

    def _rerender(self) -> None:
        self.table.load(self.table.data, append=False)

    def _confirm_single_remove(self, row_index: int) -> None:
        def _cancel(e):
            self._close_dialog()

        def _confirm(e):
            self._close_dialog()
            self._do_remove_single(row_index)

        dialog = ft.AlertDialog(
            title=ft.Text("Remove row?"),
            content=ft.Text("This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.Button(
                    "Remove", on_click=_confirm, bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR
                ),
            ],
        )
        self._open_dialog(dialog)

    def _do_remove_single(self, row_index: int) -> None:
        row = self.table.data[row_index]
        error = (
            self.on_remove_row(row)
            if self.on_remove_row
            else "Remove is not configured for this table"
        )
        if error:
            self.table.parent.view.show_error(error)
            return
        del self.table.data[row_index]
        self._rerender()
        self.table.parent.view.show_success("Removed successfully")

    def _confirm_bulk_remove(self) -> None:
        count = len(self.selected)

        def _cancel(e):
            self._close_dialog()

        def _confirm(e):
            self._close_dialog()
            self._do_remove_bulk()

        dialog = ft.AlertDialog(
            title=ft.Text("Remove selected rows?"),
            content=ft.Text(f"Remove {count} selected row(s)? This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.Button(
                    "Remove", on_click=_confirm, bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR
                ),
            ],
        )
        self._open_dialog(dialog)

    def _do_remove_bulk(self) -> None:
        indices = sorted(self.selected)
        rows = [self.table.data[i] for i in indices]
        error = (
            self.on_remove_rows(rows)
            if self.on_remove_rows
            else "Bulk remove is not configured for this table"
        )
        if error:
            self.table.parent.view.show_error(error)
            return
        for i in reversed(indices):
            del self.table.data[i]
        self.mode = self.MODE_SINGLE
        self.selected = set()
        self._rerender()
        self.table.parent.view.show_success(f"Removed {len(rows)} row(s) successfully")

    def _open_dialog(self, dialog: ft.AlertDialog) -> None:
        self.page.overlay.append(dialog)
        dialog.open = True
        self._safe_page_update()

    def _close_dialog(self) -> None:
        for control in self.page.overlay:
            if isinstance(control, ft.AlertDialog):
                control.open = False
        self._safe_page_update()

    def _safe_page_update(self) -> None:
        try:
            self.page.update()
        except RuntimeError:
            pass
