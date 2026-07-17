import flet as ft

from components.form.date import DateForm
from components.table.columns import TableColumns
from utils.formatting import format_date, format_datetime, format_number, format_time
from utils.http_client import HttpClient

_FORMATTERS = {
    "number": format_number,
    "date": format_date,
    "time": format_time,
    "datetime": format_datetime,
}

# Field types that render an editable control instead of read-only text -
# see _build_editable_cell() for what each one builds.
_EDITABLE_TYPES = {"input", "textarea", "select", "option", "datepicker", "checkbox"}

# Bounds an editable select/option cell's dropdown menu height to roughly
# this many rows (scrollable for the rest) instead of a hard option-list cap
# - see components/form/select.py's module docstring for why a hard cap +
# "show more" indicator (issue #26's original design) was abandoned in favor
# of Flutter's native, zero-round-trip enable_filter.
_MENU_VISIBLE_ROWS = 5
_MENU_ROW_HEIGHT = 48


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
        for record in data:
            # determine key value for this row (if key_field defined)
            key_value = record.get(key_field) if key_field is not None else None

            # create on_tap handler to navigate to edit page with key
            on_tap_handler = None
            if key_field is not None:
                module = None
                if hasattr(self, "parent") and getattr(self.parent, "module", None):
                    module = getattr(self.parent, "module")
                elif hasattr(self.page, "data") and isinstance(self.page.data, dict):
                    module = self.page.data.get("module")

                if module:
                    # Table's own `edit_screen` (default "edit") lets a
                    # sub-table (e.g. an item list on a header's edit
                    # screen) navigate somewhere other than the parent
                    # module's own edit route, avoiding a route collision.
                    edit_screen = getattr(self.parent, "edit_screen", "edit")

                    def _make_tap(kf, kv, mod, screen):
                        # Use path parameter for id: /modules/<module>/<screen>/<id>
                        if kv is None:
                            return lambda e: None
                        return lambda e: self.page.run_task(
                            self.page.push_route, f"/modules/{mod}/{screen}/{kv}"
                        )

                    on_tap_handler = _make_tap(
                        key_field, key_value, module, edit_screen
                    )

            cells = []
            row_inputs: dict = {}
            for i, name in enumerate(self.columns.index):
                raw_value = record.get(name, "")
                field = self.columns.fields_by_name.get(name, {})
                field_type = field.get("type")

                if field_type in _EDITABLE_TYPES:
                    w = (
                        int(columns_widths[i])
                        if columns_widths is not None and i < len(columns_widths)
                        else None
                    )
                    control, value_holder = self._build_editable_cell(
                        field_type, field, name, raw_value, w
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

                formatter = _FORMATTERS.get(field.get("format"))
                value = formatter(raw_value) if formatter else raw_value
                is_numeric = field.get("format") == "number"
                text_align = ft.TextAlign.RIGHT if is_numeric else None

                # Wrap text in container with fixed width if available.
                # max_lines=1 (alongside overflow=ELLIPSIS) guarantees a
                # single truncated line rather than wrapping onto a second
                # one when the column is narrow - same fix as the header
                # label in Columns._build_data_columns().
                content = ft.Text(
                    str(value),
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                    text_align=text_align,
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
                        ),
                        width=w,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                        alignment=ft.Alignment.CENTER_RIGHT if is_numeric else None,
                    )

                # attach on_tap to each DataCell so clicking any cell navigates
                if on_tap_handler is not None:
                    cell = ft.DataCell(content=content, on_tap=on_tap_handler)
                else:
                    cell = ft.DataCell(content=content)

                cells.append(cell)

            self.rows.append(ft.DataRow(cells=cells))
            self.index.append(row)
            self.input_controls.append(row_inputs)
            row += 1

    def _build_editable_cell(
        self, field_type: str, field: dict, name: str, raw_value, width
    ):
        """Build one editable table cell.

        Returns (control, value_holder): `control` is what goes in the
        DataCell; `value_holder` is what get_input_values() reads back from
        (usually `control` itself, except "datepicker" - see below).
        """
        has_value = raw_value not in (None, "")

        if field_type == "textarea":
            control = ft.TextField(
                value=str(raw_value) if has_value else "",
                hint_text=field.get("hint_text", ""),
                multiline=True,
                min_lines=field.get("min_lines", 2),
                max_lines=field.get("max_lines", 4),
                dense=True,
                content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                width=width,
            )
            return control, control

        if field_type == "checkbox":
            value = (
                raw_value
                if isinstance(raw_value, bool)
                else str(raw_value).strip().lower() in ("1", "true", "yes")
            )
            control = ft.Checkbox(value=value)
            return control, control

        if field_type in ("select", "option"):
            options = (
                field.get("options", [])
                if field_type == "option"
                else self._get_select_options(field, name)
            )
            enable_filter = field.get("enable_filter", True)
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
                enable_filter=enable_filter,
                editable=field.get("editable", True) if enable_filter else False,
                menu_height=_MENU_VISIBLE_ROWS * _MENU_ROW_HEIGHT,
                width=width,
            )
            return control, control

        if field_type == "datepicker":
            date_form = DateForm(page=self.page, parent=self.parent, field=field)
            control = date_form.build()
            if width is not None:
                control.width = width
            if has_value:
                date_form.set_value(str(raw_value))
            # get_input_values() needs get_value() (raw ISO), not the
            # displayed "dd Mon yyyy" text - hand back the DateForm itself.
            return control, date_form

        # Default: "input" - a single-line text field.
        control = ft.TextField(
            value=str(raw_value) if has_value else "",
            hint_text=field.get("hint_text", ""),
            keyboard_type=field.get("keyboard_type"),
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            width=width,
        )
        return control, control

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
