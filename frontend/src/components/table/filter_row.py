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
`"is_numeric": True` — the same flags `Columns._build_data_columns()`
already reads for right-alignment) - one source of truth for "this
column is numeric," not a second flag every numeric field must
separately remember to set.

Renders as an inline row rather than trying to align pixel-for-pixel with
`Columns`' resize/sort-aware DataTable header cells — those two systems
solve different problems (fixed per-column pixel widths vs. a handful of
free-standing filter inputs), and forcing this into the same width
machinery would mean touching every hardcoded `Table`/`Columns` index
assumption for no real UX gain over a simple row above the header.
"""

import flet as ft


class FilterRow:
    def __init__(self, page: ft.Page, parent, fields: list, on_apply=None):
        self.page = page
        self.parent = parent
        self.on_apply = on_apply
        self.filterable_fields = [
            f
            for f in fields
            if f.get("name") is not None
            and f.get("type", "text") != "hidden"
            and f.get("filter", True) is not False
        ]
        self.controls: dict[str, ft.TextField] = {}
        self.visible = False
        self.container: ft.Container | None = None

    def has_filters(self) -> bool:
        return bool(self.filterable_fields)

    def build(self) -> ft.Container:
        if not self.filterable_fields:
            self.container = ft.Container()
            return self.container

        row_controls = []
        for field in self.filterable_fields:
            name = field.get("name")
            label = field.get("label", name)
            is_numeric = bool(
                field.get("numeric_filter")
                or field.get("is_numeric")
                or field.get("format") == "number"
            )
            hint_text = (
                "e.g. >=5and<=10" if is_numeric else f"Filter {label}"
            )
            text_field = ft.TextField(
                label=label,
                hint_text=hint_text,
                dense=True,
                content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                on_submit=self._on_submit,
            )
            self.controls[name] = text_field
            row_controls.append(ft.Container(content=text_field, expand=True))

        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.FILTER_ALT,
                tooltip="Apply Filters",
                on_click=self._on_submit,
            )
        )
        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.FILTER_ALT_OFF,
                tooltip="Clear Filters",
                on_click=self._on_clear,
            )
        )

        self.container = ft.Container(
            content=ft.Row(controls=row_controls, spacing=8),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            visible=self.visible,
        )
        return self.container

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.container is not None:
            self.container.visible = self.visible
            self._safe_update(self.container)

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

    def _on_submit(self, e):
        if self.on_apply:
            self.on_apply()

    def _on_clear(self, e):
        for control in self.controls.values():
            control.value = ""
            self._safe_update(control)
        if self.on_apply:
            self.on_apply()

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except RuntimeError:
            pass
