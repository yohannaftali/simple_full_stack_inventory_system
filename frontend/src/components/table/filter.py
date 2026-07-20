"""Per-column `{field}-filter` filter row (issue #10), ported from senar's
`L_database::filter()`/`y.form.js`'s `row-y-filter-{table}` — one
`ft.TextField` per visible field, collapsed by default and toggled via a
toolbar button (`Table._toggle_filter_row`). **On by default for every
non-hidden field** (opt out per-field with `"filter": False"`) — every
table gets this for free, matching the ported PHP where every column
`L_database::filter()` was given got its own filter, not an opt-in per
column. A field is treated as numeric-operator (hint pointing at the
`>=5and<=10` syntax `core/table_query.py::_parse_numeric_filter`
understands) when marked `"numeric_filter": True`, or automatically when
its own display config already says so (`"format": "number"` /
`"is_numeric": True` — the same flags `TableColumns._build_data_columns()`
already reads for right-alignment) - one source of truth for "this
column is numeric," not a second flag every numeric field must
separately remember to set.

Aligned to the table body's actual column positions/widths (issue #20) -
one fixed-width `ft.Container` per **visible** column (not just the
filterable ones, so a non-filterable column still reserves its slot and
every filter field after it stays aligned), using the exact same
`TABLE_HORIZONTAL_MARGIN`/`TABLE_COLUMN_SPACING` constants and
`TableColumns.widths` list the header/body DataTables and the resize-handle
overlay already position themselves from (see
`TableColumns._reposition_handles()`) - a plain `ft.Row` with matching
left-padding and inter-item spacing lines up pixel-for-pixel with
`ft.DataTable`'s own `horizontal_margin`/`column_spacing` layout, no
absolute positioning needed the way the resize handles require (those sit
in a separate overlay Stack on top of the header; this is a normal Row
underneath it). `Table` calls `reposition()` after every place
`TableColumns.widths` can change (initial/reloaded data, a resize drag tick, a
double-tap reset) to patch each field's `Container.width` in place -
cheap, since (unlike the header's `ft.DataTable`) a plain `Container`
genuinely does shrink on a live width patch, no rebuild required.

Filtering is live (per-keystroke `on_change`, no separate "Apply
Filters"/"Clear Filters" step) - each field also gets its own trailing
clear icon that unfilters just that column. Hiding the row via the
toolbar's toggle always clears every active filter too, so a hidden row
never leaves a filter silently still applied server-side.
"""

import flet as ft

from components.table.columns import TABLE_COLUMN_SPACING, TABLE_HORIZONTAL_MARGIN, TableColumns


class TableFilter:
    def __init__(self, page: ft.Page, parent, fields: list, columns: TableColumns, on_apply=None):
        self.page = page
        self.parent = parent
        self.columns = columns
        self.on_apply = on_apply
        # Every visible column, in the same order as TableColumns.index/.widths -
        # needed so each field (filterable or not) gets a same-width slot
        # and the row stays aligned with the table body.
        self.visible_fields = [
            f
            for f in fields
            if f.get("name") is not None and f.get("type", "text") != "hidden"
        ]
        self.controls: dict[str, ft.TextField] = {}
        self.field_containers: list[ft.Container] = []
        self.visible = False
        self.container: ft.Container | None = None

    def has_filters(self) -> bool:
        return any(
            f.get("filter", True) is not False for f in self.visible_fields
        )

    def build(self) -> ft.Container:
        if not self.has_filters():
            self.container = ft.Container()
            return self.container

        row_controls = []
        self.field_containers = []
        for i, field in enumerate(self.visible_fields):
            width = (
                int(self.columns.widths[i])
                if self.columns.widths and i < len(self.columns.widths)
                else None
            )
            is_filterable = field.get("filter", True) is not False

            content = self._build_field(field) if is_filterable else None
            field_container = ft.Container(content=content, width=width)
            self.field_containers.append(field_container)
            row_controls.append(field_container)

        self.container = ft.Container(
            content=ft.Row(controls=row_controls, spacing=TABLE_COLUMN_SPACING),
            padding=ft.Padding.only(
                left=TABLE_HORIZONTAL_MARGIN,
                right=TABLE_HORIZONTAL_MARGIN,
                top=8,
                bottom=8,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            visible=self.visible,
        )
        return self.container

    def _build_field(self, field: dict) -> ft.TextField:
        name = field.get("name")
        label = field.get("label", name)
        is_numeric = bool(
            field.get("numeric_filter")
            or field.get("is_numeric")
            or field.get("format") == "number"
        )
        hint_text = "e.g. >=5and<=10" if is_numeric else f"Filter {label}"
        text_field = ft.TextField(
            label=label,
            hint_text=hint_text,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=10,  # Matches the table search bar (issue #19)
            # Must be set explicitly (issue #35) - same theme-aware-color
            # gap as every other bare TextField in components/table/.
            color=ft.Colors.ON_SURFACE,
            border_color=ft.Colors.OUTLINE_VARIANT,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            prefix_icon=ft.Icon(
                ft.Icons.FILTER_ALT, size=14, color=ft.Colors.ON_SURFACE_VARIANT
            ),
            suffix_icon=ft.IconButton(
                icon=ft.Icons.CLEAR,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                icon_size=14,
                width=24,
                height=24,
                padding=0,
                tooltip=f"Clear {label} filter",
                on_click=lambda e, n=name: self._clear_field(n),
            ),
            suffix_icon_size_constraints=ft.BoxConstraints(
                min_width=24, max_width=24, min_height=24, max_height=24
            ),
            on_change=self._on_field_change,
            on_submit=self._on_field_change,
        )
        self.controls[name] = text_field
        return text_field

    def reposition(self) -> None:
        """Patch each field's Container.width from the current
        `TableColumns.widths` - called by `Table` after every place column
        widths can change (data load, resize drag, double-tap reset), same
        trigger points as `TableColumns._reposition_handles()`."""
        if not self.columns.widths or not self.field_containers:
            return
        for i, container in enumerate(self.field_containers):
            if i < len(self.columns.widths):
                container.width = int(self.columns.widths[i])
                self._safe_update(container)

    def toggle(self) -> None:
        was_visible = self.visible
        self.visible = not self.visible
        if self.container is not None:
            self.container.visible = self.visible
            self._safe_update(self.container)
        if was_visible and not self.visible:
            # Hiding the row always means "no column filters active" -
            # clear everything so a hidden row never leaves a filter
            # silently still applied server-side (issue #20).
            self._clear_all()

    def serialize(self) -> str:
        """`&{field}-filter=value` query string for every non-blank field —
        same wire-format convention `Table.get_data()` already appends
        `table-keyword-filter`/`sort-fields[...]` params with."""
        parts = []
        for name, control in self.controls.items():
            value = (control.value or "").strip()
            if value:
                parts.append(f"&{name}-filter={value}")
        return "".join(parts)

    def has_active_filters(self) -> bool:
        return any((control.value or "").strip() for control in self.controls.values())

    def _on_field_change(self, e):
        if self.on_apply:
            self.on_apply()

    def _clear_field(self, name: str) -> None:
        control = self.controls.get(name)
        if control is None:
            return
        control.value = ""
        self._safe_update(control)
        if self.on_apply:
            self.on_apply()

    def _clear_all(self) -> None:
        changed = False
        for control in self.controls.values():
            if control.value:
                control.value = ""
                changed = True
                self._safe_update(control)
        if changed and self.on_apply:
            self.on_apply()

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass
