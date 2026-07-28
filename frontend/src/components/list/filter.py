"""Expandable per-field search + multi-column sort panel for List (issue #55,
follow-up 2026-07-28).

`List`'s tiles are positional (leading/title/subtitle/trailing on a card),
not columnar, so there is no header row to hang Table's per-column filter
inputs or sort icons off (see `components/table/filter.py`/`columns.py`).
Instead this is a single collapsible panel, toggled from the toolbar, with
one row per opted-in field: a filter `ft.TextField` (leading filter icon,
trailing clear icon, same as `TableFilter._build_field()`) plus its own
sort-toggle `ft.IconButton` (none -> ASC -> DESC -> none, same icon set and
cycling as `TableColumns._on_header_click()`/`_build_sort_icon()`) - true
multi-column sort, same as Table, not the single active-sort-field design
this file originally shipped with.

Wire format matches Table's exactly, so the shared backend
(`backend/src/core/table_query.py`) needs no changes: `{field}-filter=value`
per filter field and `sort-fields[{index}][{field}]={ASC|DESC}` per active
sort column, in priority order.

Opt-in via `"filter": True` / `"sort": True` on a field - the reverse of
Table's opt-out-by-default (`TableFilter`'s `field.get("filter", True) is
not False`). Table's fields are already a fixed column set the user always
sees in full; List's fields are a curated subset picked for a card's
leading/title/subtitle/trailing slots, so defaulting every field into the
filter/sort panel here would surface fields the screen author never
intended as filterable/sortable.
"""

import flet as ft

ICON_SORT_NONE = ft.Icons.UNFOLD_MORE
ICON_SORT_ASC = ft.Icons.ARROW_UPWARD
ICON_SORT_DESC = ft.Icons.ARROW_DOWNWARD


class ListFilter:
    def __init__(self, page: ft.Page, parent, fields: list, on_apply=None):
        self.page = page
        self.parent = parent
        self.fields = fields
        self.on_apply = on_apply

        self.visible = False
        self.container: ft.Container | None = None
        self.filter_fields: dict[str, ft.TextField] = {}

        # Multi-column sort, same shape/priority-ordering as
        # `TableColumns.sort_order`: an ordered [(field_name, "ASC"|"DESC")]
        # list, list order = priority.
        self.sort_order: list[tuple[str, str]] = []
        self.sort_buttons: dict[str, ft.IconButton] = {}

        self._panel_rows: list[str] = [
            f["name"]
            for f in self.fields
            if f.get("name") and (f.get("filter") or f.get("sort"))
        ]

    def has_filters(self) -> bool:
        return bool(self._panel_rows)

    def _field_by_name(self, name: str) -> dict:
        for f in self.fields:
            if f.get("name") == name:
                return f
        return {}

    def build(self) -> ft.Container:
        controls: list = []

        for name in self._panel_rows:
            field = self._field_by_name(name)
            row_controls: list = []

            if field.get("filter"):
                row_controls.append(self._build_filter_field(field))

            if field.get("sort"):
                row_controls.append(self._build_sort_button(name))

            controls.append(
                ft.Row(
                    controls=row_controls,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                )
            )

        self.container = ft.Container(
            content=ft.Column(controls=controls, spacing=8),
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            visible=self.visible,
        )
        return self.container

    def _build_filter_field(self, field: dict) -> ft.TextField:
        name = field["name"]
        label = field.get("label", name)
        text_field = ft.TextField(
            label=label,
            hint_text=f"Filter {label}",
            dense=True,
            border_radius=10,
            filled=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            color=ft.Colors.ON_SURFACE,
            label_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            # Same leading filter / trailing clear icon pair as
            # TableFilter._build_field(), so a List's filter row reads
            # consistently with a Table's own.
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
            expand=True,
            on_change=self._on_field_change,
            on_submit=self._on_field_change,
        )
        self.filter_fields[name] = text_field
        return text_field

    def _build_sort_button(self, name: str) -> ft.IconButton:
        button = ft.IconButton(
            icon=self._sort_icon(name),
            icon_color=self._sort_color(name),
            tooltip="Toggle sort",
            on_click=lambda e, n=name: self._on_sort_click(n),
        )
        self.sort_buttons[name] = button
        return button

    def _find_sort_state(self, name: str) -> tuple[int | None, str | None]:
        for i, (field_name, direction) in enumerate(self.sort_order):
            if field_name == name:
                return i, direction
        return None, None

    def _sort_icon(self, name: str) -> str:
        _, direction = self._find_sort_state(name)
        if direction == "ASC":
            return ICON_SORT_ASC
        if direction == "DESC":
            return ICON_SORT_DESC
        return ICON_SORT_NONE

    def _sort_color(self, name: str) -> str:
        _, direction = self._find_sort_state(name)
        return ft.Colors.PRIMARY if direction else ft.Colors.ON_SURFACE_VARIANT

    def _on_sort_click(self, name: str) -> None:
        """none -> ASC -> DESC -> none, same cycling as
        `TableColumns._on_header_click()` - clicking a different field
        while one is already active appends it as an additional sort key
        rather than replacing it, true multi-column sort with no
        shift/ctrl modifier."""
        index, state = self._find_sort_state(name)
        if state == "ASC":
            self.sort_order[index] = (name, "DESC")
        elif state == "DESC":
            self.sort_order.pop(index)
        else:
            self.sort_order.append((name, "ASC"))

        for field_name, button in self.sort_buttons.items():
            button.icon = self._sort_icon(field_name)
            button.icon_color = self._sort_color(field_name)
        self._safe_update(self.container)

        if self.on_apply:
            self.on_apply()

    def toggle(self) -> None:
        """Mirrors `TableFilter.toggle()` - hiding the panel also clears
        every filter/sort so nothing stays silently applied server-side
        while the panel itself isn't visible."""
        self.visible = not self.visible
        if self.container is not None:
            self.container.visible = self.visible
            self._safe_update(self.container)
        if not self.visible:
            self._clear_all()

    def _clear_field(self, name: str) -> None:
        text_field = self.filter_fields.get(name)
        if text_field is not None:
            text_field.value = ""
            self._safe_update(text_field)
        if self.on_apply:
            self.on_apply()

    def _clear_all(self) -> None:
        for text_field in self.filter_fields.values():
            text_field.value = ""
        self.sort_order = []
        for field_name, button in self.sort_buttons.items():
            button.icon = self._sort_icon(field_name)
            button.icon_color = self._sort_color(field_name)
        if self.on_apply:
            self.on_apply()

    def _on_field_change(self, e) -> None:
        if self.on_apply:
            self.on_apply()

    def serialize(self) -> str:
        """`&{field}-filter=value` for every non-blank filter field, plus
        `&sort-fields[{index}][{field}]={ASC|DESC}` for every active sort
        column in priority order - same wire format Table's own
        `TableFilter.serialize()`/`TableColumns.serialize_sort()` produce,
        so the shared backend needs no changes."""
        parts = [
            f"&{name}-filter={text_field.value}"
            for name, text_field in self.filter_fields.items()
            if (text_field.value or "").strip()
        ]
        parts.extend(
            f"&sort-fields[{index}][{field_name}]={direction}"
            for index, (field_name, direction) in enumerate(self.sort_order)
        )
        return "".join(parts)

    @staticmethod
    def _safe_update(control) -> None:
        if control is None:
            return
        try:
            control.update()
        except RuntimeError:
            pass
