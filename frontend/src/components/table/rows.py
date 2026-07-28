import flet as ft

from components.form.date import DateForm
from components.table.columns import TableColumns
from components.table.remove import ICON_CHECKBOX_CHECKED, ICON_CHECKBOX_UNCHECKED

# "radio"-type cells (issue #45) use a real circle-with-dot radio glyph,
# not the checkbox icon pair - a radio button and a checkbox are visually
# distinct standard controls, and reusing the checkbox icon made every
# radio field look like a checkbox despite behaving like a radio (mutual
# exclusivity). See _CheckboxCellValue's `icon_pair` param below.
ICON_RADIO_CHECKED = ft.Icons.RADIO_BUTTON_CHECKED
ICON_RADIO_UNCHECKED = ft.Icons.RADIO_BUTTON_UNCHECKED
from utils.formatting import format_date, format_datetime, format_number, format_time
from utils.http_client import HttpClient
from utils.icon import get_icon

_FORMATTERS = {
    "number": format_number,
    "date": format_date,
    "time": format_time,
    "datetime": format_datetime,
}

# Field types that render an editable control instead of read-only text -
# see _build_editable_cell() for what each one builds.
_EDITABLE_TYPES = {
    "input",
    "textarea",
    "select",
    "option",
    "datepicker",
    "checkbox",
    "radio",
}

# Bounds an editable select/option cell's dropdown menu height to roughly
# this many rows (scrollable for the rest) instead of a hard option-list cap
# - see components/form/select.py's module docstring for why a hard cap +
# "show more" indicator (issue #26's original design) was abandoned in favor
# of Flutter's native, zero-round-trip enable_filter.
_MENU_VISIBLE_ROWS = 5
_MENU_ROW_HEIGHT = 48

# Position-based zebra stripe colors (issue #57, replacing the table's old
# border/divider lines) - CSS :nth-child(even/odd)-style: derived fresh from
# a row's index in the CURRENT render pass every time (the `row` counter
# below, already the same index `self.index`/`input_controls` track), never
# stored on the record. A row added/removed/reordered by any existing
# mechanism (sort, filter, TableRemove delete, lazy-load append) already
# triggers a full rebuild from this same counter, so the stripe is always
# correct with no separate bookkeeping - including the lazy-load append
# path, where `row` starts at `len(self.rows)` (the last already-rendered
# row's index + 1), not 0, so the pattern continues instead of resetting at
# the page boundary. Semantic tokens (not fixed hex) so both themes hold up.
_ROW_COLOR_EVEN = ft.Colors.SURFACE
_ROW_COLOR_ODD = ft.Colors.SURFACE_CONTAINER_LOW


class _CheckboxCellValue:
    """`value_holder` for a `"checkbox"`-type editable cell (issue #44) -
    the displayed control is a checked/unchecked icon toggle (the same
    icon pair `components/table/remove.py` uses for its own row-selection
    state), not a plain `ft.Checkbox`. `get_input_values()` reads this
    object's own `.value`, kept in sync on every click - same contract as
    every other editable cell type (a bare `bool`).

    Also reused for `"radio"`-type cells (issue #45), passing
    `icon_pair=(ICON_RADIO_CHECKED, ICON_RADIO_UNCHECKED)` instead of the
    checkbox default - a real circle-with-dot radio glyph, since a radio
    button and a checkbox are visually distinct standard controls even
    though this class's own toggle/set_value bookkeeping is identical for
    both. The only *behavioral* difference between the two cell types is
    *how* the click is wired: a checkbox's own `on_click` calls `toggle()`
    directly, while a radio cell's `on_click` goes through
    `TableRows._on_radio_click()` instead (never `toggle()`), which
    enforces exclusivity across sibling cells before calling this class's
    `set_value(True)`."""

    def __init__(
        self,
        value: bool,
        control: ft.IconButton,
        icon_pair: tuple = (ICON_CHECKBOX_CHECKED, ICON_CHECKBOX_UNCHECKED),
    ):
        self.value = value
        self._control = control
        self._icon_checked, self._icon_unchecked = icon_pair
        self._apply_icon()

    def toggle(self, e) -> None:
        self.set_value(not self.value)

    def set_value(self, value: bool) -> None:
        """Bulk-set from the header's check-all/uncheck-all buttons (issue
        #46) - same icon/color sync as toggle(), just driven externally
        instead of by this cell's own click."""
        if self.value == value:
            return
        self.value = value
        self._apply_icon()
        try:
            self._control.update()
        except RuntimeError:
            pass

    def _apply_icon(self) -> None:
        self._control.icon = self._icon_checked if self.value else self._icon_unchecked
        self._control.icon_color = (
            ft.Colors.PRIMARY if self.value else ft.Colors.ON_SURFACE_VARIANT
        )


class TableRows:
    def __init__(self, page: ft.Page, columns: TableColumns, parent=None):
        self.page = page
        self.columns = columns
        self.parent = parent
        self.rows = []
        self.index = []
        # One dict per row (same order as self.rows/self.index), mapping
        # field_name -> {"type": field_type, "control": control} for every
        # editable-type column in that row - lets a caller read back what
        # the user entered via Rows.get_input_values()/
        # Table.get_rows_with_input_values().
        self.input_controls: list[dict] = []
        # "select"-type columns fetch their options once (same list for
        # every row, like components/form/select.py) and cache them here,
        # keyed by field name, for the lifetime of this Rows instance.
        self._select_options_cache: dict[str, list[dict]] = {}

    def build(self):
        print("TableRows.build")
        print(self.columns.widths)
        return self.rows

    def load(self, data: list, append: bool = False):
        columns_widths: list[int] | None = self.columns.widths
        print("TableRows.load: coloumns width")
        print(columns_widths)
        row = len(self.rows) if append else 0
        if not append:
            self.rows = []
            self.index = []
            self.input_controls = []
        # determine key field name (field with 'key': True)
        key_field = None
        try:
            for f in getattr(self.columns, "fields", []):
                if f.get("key"):
                    key_field = f.get("name")
                    break
        except Exception:
            key_field = None
        module = None
        if hasattr(self, "parent") and getattr(self.parent, "module", None):
            module = getattr(self.parent, "module")
        elif hasattr(self.page, "data") and isinstance(self.page.data, dict):
            module = self.page.data.get("module")

        # Table's own `edit_screen` (default "edit") lets a sub-table (e.g.
        # an item list on a header's edit screen) navigate somewhere other
        # than the parent module's own edit route, avoiding a route
        # collision.
        edit_screen = getattr(self.parent, "edit_screen", "edit")

        def _make_tap(kv, mod, screen):
            # Use path parameter for id: /modules/<module>/<screen>/<id>
            if kv is None:
                return lambda e: None
            return lambda e: self.page.run_task(
                self.page.push_route, f"/modules/{mod}/{screen}/{kv}"
            )

        for record in data:
            # determine key value for this row (if key_field defined)
            key_value = record.get(key_field) if key_field is not None else None

            # create on_tap handler to navigate to edit page with key
            on_tap_handler = (
                _make_tap(key_value, module, edit_screen)
                if key_field is not None and module
                else None
            )

            cells = []
            row_inputs: dict = {}
            for i, name in enumerate(self.columns.index):
                raw_value = record.get(name, "")
                field = self.columns.fields_by_name.get(name, {})
                field_type = field.get("type")

                if field_type == "remove":
                    remove_component = getattr(self.parent, "remove", None)
                    w = (
                        int(columns_widths[i])
                        if columns_widths is not None and i < len(columns_widths)
                        else None
                    )
                    cell_content = (
                        remove_component.build_row_cell(row, w)
                        if remove_component is not None
                        else ft.Container(width=w)
                    )
                    cells.append(ft.DataCell(content=cell_content))
                    continue

                if field_type in _EDITABLE_TYPES:
                    w = (
                        int(columns_widths[i])
                        if columns_widths is not None and i < len(columns_widths)
                        else None
                    )
                    control, value_holder = self._build_editable_cell(
                        field_type, field, name, raw_value, w, row_index=row
                    )
                    row_inputs[name] = {"type": field_type, "control": value_holder}
                    # Wrap in a fixed-width Container, same as the read-only
                    # text cells below - without it, Flet/Flutter sizes the
                    # DataTable column from the control's own intrinsic
                    # width (e.g. a TextField's ~300px default) instead of
                    # the width Columns.load() computed, so editable
                    # columns drift out of alignment with the rest of the
                    # table.
                    # No extra padding here (unlike the read-only Text
                    # cells below) - the control already carries the same
                    # `w` as its own width plus its own internal
                    # content_padding, so an outer padding would shrink its
                    # available space below what it's sized for.
                    cell_content = (
                        ft.Container(content=control, width=w)
                        if w is not None
                        else control
                    )
                    # Editable cells never navigate, even if some other
                    # column in this row is marked "key" - a tap needs to
                    # land in the field to interact, not push a route.
                    cells.append(ft.DataCell(content=cell_content))
                    continue

                if field.get("format") == "icon":
                    # Read-only preview of a stored Material icon-name
                    # string (e.g. "chevron_right") as an actual glyph
                    # instead of raw text - first consumer:
                    # components/modal/icon_selector.py's picker list.
                    # `raw_value` blank -> the field's own default (falls
                    # back to a generic app icon), same "blank means
                    # default" rule components/form/icon_picker.py uses
                    # for its leading icon. MUST go through get_icon() -
                    # ft.Icon(icon=<raw unmapped string>) constructs fine
                    # in Python but fails to paint client-side (Flutter
                    # renders its gray error-widget box in place, which
                    # also blows out the cell's layout) - confirmed live,
                    # see icon_picker.py's docstring for the full story.
                    icon_value = (
                        get_icon(raw_value)
                        if raw_value
                        else field.get("default_icon", ft.Icons.APPS)
                    )
                    w = (
                        int(columns_widths[i])
                        if columns_widths is not None and i < len(columns_widths)
                        else None
                    )
                    content = ft.Container(
                        content=ft.Icon(icon=icon_value, color=ft.Colors.ON_SURFACE),
                        width=w,
                        alignment=ft.Alignment.CENTER,
                    )
                else:
                    formatter = _FORMATTERS.get(field.get("format"))
                    value = formatter(raw_value) if formatter else raw_value
                    is_numeric = field.get("format") == "number"
                    text_align = ft.TextAlign.RIGHT if is_numeric else None

                    # Wrap text in container with fixed width if available.
                    # max_lines=1 (alongside overflow=ELLIPSIS) guarantees a
                    # single truncated line rather than wrapping onto a second
                    # one when the column is narrow - same fix as the header
                    # label in Columns._build_data_columns(). `color` must be
                    # set explicitly (issue #35) - Flet's plain Text doesn't
                    # inherit a theme-aware color inside a DataTable cell.
                    content = ft.Text(
                        str(value),
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                        text_align=text_align,
                        color=ft.Colors.ON_SURFACE,
                    )
                    if columns_widths is not None and i < len(columns_widths):
                        # Ensure integer pixel widths (Flet expects integers)
                        w = int(columns_widths[i])
                        content = ft.Container(
                            content=ft.Text(
                                str(value),
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                                text_align=text_align,
                                color=ft.Colors.ON_SURFACE,
                            ),
                            width=w,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            alignment=ft.Alignment.CENTER_RIGHT if is_numeric else None,
                        )

                # A field-level link override (link_key_field, optionally
                # paired with link_screen) lets this ONE cell navigate
                # somewhere different from the row's own default
                # key/edit_screen - e.g. stock_browse's location columns
                # link to a location drill-down while every other cell in
                # the same row still links to the row's own material
                # drill-down (issue #40). Falls back to the row-wide
                # on_tap_handler when no override is set, same as before.
                link_key_field = field.get("link_key_field")
                if link_key_field is not None and module:
                    cell_tap_handler = _make_tap(
                        record.get(link_key_field),
                        module,
                        field.get("link_screen", edit_screen),
                    )
                else:
                    cell_tap_handler = on_tap_handler

                # attach on_tap to each DataCell so clicking any cell navigates
                if cell_tap_handler is not None:
                    cell = ft.DataCell(content=content, on_tap=cell_tap_handler)
                else:
                    cell = ft.DataCell(content=content)

                cells.append(cell)

            row_color = _ROW_COLOR_EVEN if row % 2 == 0 else _ROW_COLOR_ODD
            self.rows.append(ft.DataRow(cells=cells, color=row_color))
            self.index.append(row)
            self.input_controls.append(row_inputs)
            row += 1

    def _build_editable_cell(
        self, field_type: str, field: dict, name: str, raw_value, width, row_index=None
    ):
        """Build one editable table cell.

        Returns (control, value_holder): `control` is what goes in the
        DataCell; `value_holder` is what get_input_values() reads back from
        (usually `control` itself, except "datepicker" - see below).

        `row_index` is only used by `"radio"` (issue #45) - its click
        handler needs to know which row it's in to enforce exclusivity
        against sibling cells via `_on_radio_click()`.
        """
        has_value = raw_value not in (None, "")

        if field_type == "textarea":
            return self._build_flush_textfield(
                value=str(raw_value) if has_value else "",
                hint_text=field.get("hint_text", ""),
                multiline=True,
                min_lines=field.get("min_lines", 2),
                max_lines=field.get("max_lines", 4),
                width=width,
            )

        if field_type == "checkbox":
            value = (
                raw_value
                if isinstance(raw_value, bool)
                else str(raw_value).strip().lower() in ("1", "true", "yes")
            )
            control = ft.IconButton()
            holder = _CheckboxCellValue(value, control)
            control.on_click = holder.toggle
            return control, holder

        if field_type == "radio":
            value = (
                raw_value
                if isinstance(raw_value, bool)
                else str(raw_value).strip().lower() in ("1", "true", "yes")
            )
            control = ft.IconButton()
            holder = _CheckboxCellValue(
                value, control, icon_pair=(ICON_RADIO_CHECKED, ICON_RADIO_UNCHECKED)
            )
            # Deliberately NOT holder.toggle (unlike "checkbox" above) - a
            # radio cell's click must enforce exclusivity against its
            # siblings first, see _on_radio_click().
            control.on_click = lambda e, n=name, ri=row_index: self._on_radio_click(n, ri)
            return control, holder

        if field_type in ("select", "option"):
            options = (
                field.get("options", [])
                if field_type == "option"
                else self._get_select_options(field, name)
            )
            enable_filter = field.get("enable_filter", True)
            # No wrapping Container needed here (unlike the earlier
            # background-swap design, issue #53) - the fill is now constant,
            # so `ft.Dropdown` can carry its own `fill_color` directly. No
            # border and no padding, same "seamless with the table grid"
            # reasoning as every other editable cell type here.
            control = ft.Dropdown(
                options=[
                    ft.DropdownOption(
                        key=opt.get("value", ""),
                        text=opt.get("label", opt.get("value", "")),
                    )
                    for opt in options
                ],
                value=str(raw_value) if has_value else None,
                hint_text=field.get("hint_text", ""),
                dense=True,
                content_padding=ft.Padding.all(0),
                enable_filter=enable_filter,
                editable=field.get("editable", True) if enable_filter else False,
                menu_height=_MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT,
                width=width,
                color=ft.Colors.ON_SURFACE,
                border=ft.InputBorder.NONE,
                filled=True,
                fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            )
            return control, control

        if field_type == "datepicker":
            date_form = DateForm(page=self.page, parent=self.parent, field=field)
            control = date_form.build()
            if width is not None:
                control.width = width
            if has_value:
                date_form.set_value(str(raw_value))
            # DateForm.build() applies the standalone-form styling (M3
            # active indicator border, padding) - override it here for the
            # same borderless/paddingless/constant-fill table-cell look as
            # every other editable cell type, since a table cell always has
            # the grid's own borders to lean on instead.
            control.border = ft.InputBorder.NONE
            control.content_padding = ft.Padding.all(0)
            control.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
            control.color = ft.Colors.ON_SURFACE
            # get_input_values() needs get_value() (raw ISO), not the
            # displayed "dd Mon yyyy" text - hand back the DateForm itself.
            return control, date_form

        # Default: "input" - a single-line text field.
        return self._build_flush_textfield(
            value=str(raw_value) if has_value else "",
            hint_text=field.get("hint_text", ""),
            keyboard_type=field.get("keyboard_type"),
            width=width,
        )

    @staticmethod
    def _build_flush_textfield(
        value: str,
        hint_text: str,
        width,
        multiline: bool = False,
        min_lines: int | None = None,
        max_lines: int | None = None,
        keyboard_type=None,
    ):
        """A single-/multi-line TextField that fills its cell edge-to-edge,
        with the M3 fill color as the ONLY visible thing (issue #53
        follow-up: `content_padding=Padding.all(0)` alone still left a
        visible gap top/bottom/left, because Flutter's `InputDecorator`
        reserves its own intrinsic minimum height/inset for a *filled*
        decoration regardless of content_padding - `filled`/`bgcolor` on
        the TextField itself always renders a shorter, inset pill rather
        than filling the full cell.

        The fix is the standard Flutter escape hatch for a truly
        chrome-free field: `collapsed=True` (maps to Flutter's
        `InputDecoration.collapsed`, which drops the decoration entirely -
        no fill, no minimum height, sized tightly to the text) with the
        actual M3 fill color moved onto a plain wrapping `ft.Container`
        instead, which - unlike the InputDecorator - genuinely does fill
        its exact given bounds.

        Returns `(wrapper, field)` - `wrapper` is what goes in the
        `DataCell`; `field` is the raw `ft.TextField` `get_input_values()`
        reads `.value` from.
        """
        field = ft.TextField(
            value=value,
            hint_text=hint_text,
            keyboard_type=keyboard_type,
            multiline=multiline,
            min_lines=min_lines,
            max_lines=max_lines,
            color=ft.Colors.ON_SURFACE,
            # `collapsed=True` alone left a visible bordered box - Flet's
            # `collapsed` doesn't appear to map to Flutter's dedicated
            # `InputDecoration.collapsed()` factory (which forces
            # `border: InputBorder.none`), just an `isCollapsed` flag on an
            # otherwise-regular decoration - so `FormFieldControl.border`'s
            # own default (OUTLINE) was still being drawn. Every
            # decoration-suppressing property is now set explicitly rather
            # than relying on `collapsed` to imply them.
            collapsed=True,
            border=ft.InputBorder.NONE,
            filled=False,
            content_padding=ft.Padding.all(0),
            expand=True,
        )
        wrapper = ft.Container(
            content=field,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=0,
            width=width,
        )
        return wrapper, field

    def _on_radio_click(self, field_name: str, row_index: int) -> None:
        """Exclusivity handler for a `"radio"`-type cell (issue #45).
        Clicking an already-selected radio is a no-op - standard
        radio-button semantics, unlike `"checkbox"`'s toggle. Selecting an
        unselected one first deselects its exclusivity siblings:
        - `"radio_mode": "row"` - every OTHER `"radio"` column sharing this
          field's `"radio_group"` name, but only within this same row (a
          by-row Likert/checklist grid - each row is its own independent
          group).
        - default / `"radio_mode": "column"` - this same field/column
          across every OTHER currently-loaded row (mutual exclusivity
          spans the whole column).
        Only touches rows currently rendered client-side, same
        "lazy-loaded pages aren't retroactively updated" scope every other
        cross-row Table mechanic in this codebase already has (e.g. #46's
        checkbox header check-all)."""
        if row_index is None or row_index >= len(self.input_controls):
            return
        entry = self.input_controls[row_index].get(field_name)
        if entry is None:
            return
        holder = entry["control"]
        if holder.value:
            return

        field = self.columns.fields_by_name.get(field_name, {})
        if field.get("radio_mode") == "row":
            group = field.get("radio_group")
            for name, other in self.input_controls[row_index].items():
                if name == field_name or other.get("type") != "radio":
                    continue
                if self.columns.fields_by_name.get(name, {}).get("radio_group") == group:
                    other["control"].set_value(False)
        else:
            for row_inputs in self.input_controls:
                other = row_inputs.get(field_name)
                if other is not None and other is not entry:
                    other["control"].set_value(False)

        holder.set_value(True)

    def _get_select_options(self, field: dict, name: str) -> list[dict]:
        """Fetch (and cache) a "select"-type column's options, same shape as
        components/form/select.py: C_{module}/call_{field_name}_select
        unless the field overrides `endpoint`."""
        if name in self._select_options_cache:
            return self._select_options_cache[name]

        module = getattr(self.parent, "module", None)
        endpoint = field.get("endpoint") or (
            f"C_{module}/call_{name}_select" if module else None
        )
        options: list[dict] = []
        if endpoint:
            response = HttpClient(self.page).get(endpoint)
            if isinstance(response, list):
                options = response

        self._select_options_cache[name] = options
        return options

    def set_all_checkbox(self, field_name: str, value: bool) -> None:
        """Bulk check-all/uncheck-all a `"checkbox"`-type column (issue
        #46) - called from the header's check-all/uncheck-all buttons
        (`TableColumns._on_checkbox_header_click` ->
        `Table._handle_checkbox_header_click`). Patches each already-
        rendered row's `_CheckboxCellValue` directly, same "update what's
        already mounted" approach as every other in-place Table
        interaction (e.g. `TableRemove`'s own row-selection toggling) - no
        full `Table.load()` re-render needed."""
        for row_inputs in self.input_controls:
            entry = row_inputs.get(field_name)
            if entry and entry["type"] == "checkbox":
                entry["control"].set_value(value)

    def get_input_values(self) -> list[dict]:
        """Current value of every editable-type column, one dict per row in
        load() order (empty dict for rows with no editable columns).
        "datepicker" columns return their raw ISO value; everything else
        returns its control's `.value` (bool for "checkbox")."""
        result = []
        for row_inputs in self.input_controls:
            row = {}
            for name, entry in row_inputs.items():
                if entry["type"] == "datepicker":
                    row[name] = entry["control"].get_value()
                else:
                    row[name] = entry["control"].value
            result.append(row)
        return result
