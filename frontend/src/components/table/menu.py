"""Hamburger-icon download/upload menu for the table toolbar - see AGENTS.md's
"Table export convention" and issue #4. Offers:
1. Download: the table's full filtered/sorted result set (not just the loaded
   page) in 6 formats, generated server-side by the matching backend
   `GET C_{module}/export_{name}` and proxied via `/download/{module}/{name}`.
2. Upload: client-side CSV/XLSX parsed in this Flet process, populating the
   table's editable input cells - key-column matching when the file carries
   label-column headers, sequential row-by-row otherwise. Only rows currently
   loaded on the client are populated (lazy-loaded pages are ignored).

Download entries are suppressed for input-mode tables (is_inside_form).
Upload entries are only shown when the table has at least one editable
column (input/textarea/select/option/datepicker/checkbox) - a purely
read-only list table has nothing for an upload to populate; bulk record
creation for those goes through the "Add New" screen's own bulk-upload
menu instead (issue #5, components/form/menu.py::MenuForm).
"""

import csv
import io
import os

import flet as ft
import openpyxl

# (format, menu label, icon) - label text matches the issue's exact wording.
_FORMAT_OPTIONS = [
    ("csv", "Download as CSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("tsv", "Download as TSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("scsv", "Download as SCSV", ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
    ("xlsx", "Download as XLSX", ft.Icons.GRID_ON),
    ("ods", "Download as ODS", ft.Icons.GRID_ON),
    ("pdf", "Download as PDF", ft.Icons.PICTURE_AS_PDF_OUTLINED),
]

_EDITABLE_TYPES = {"input", "textarea", "select", "option", "datepicker", "checkbox"}


def parse_csv_bytes(data: bytes) -> list[list[str]]:
    """Parse CSV/SCSV/TSV content into rows, sniffing the delimiter -
    comma, semicolon, or tab - so a file produced by this table's own
    SCSV/TSV download round-trips back in unchanged."""
    text = data.decode("utf-8-sig")
    sample = "\n".join(text.splitlines()[:5])

    delimiter = ","
    if sample:
        commas = sample.count(",")
        semicolons = sample.count(";")
        tabs = sample.count("\t")
        if semicolons > commas and semicolons > tabs:
            delimiter = ";"
        elif tabs > commas and tabs > semicolons:
            delimiter = "\t"

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [row for row in reader if any(str(cell).strip() for cell in row)]


def parse_xlsx_bytes(data: bytes) -> list[list[str]]:
    """Parse XLSX content (first sheet) into rows of strings, skipping
    fully-blank rows."""
    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.active
    rows = []
    for row in sheet.iter_rows(values_only=True):
        row_vals = [str(cell) if cell is not None else "" for cell in row]
        if any(v.strip() for v in row_vals):
            rows.append(row_vals)
    return rows


class TableMenu:
    """Wraps a `PopupMenuButton` (hamburger icon) - `parent` is the owning
    `Table`, read for its current module/name/filter/sort/custom_param state
    at click time, not build time.

    Deliberately touches NOTHING page-related in __init__: this constructor
    runs inside `Table.__init__` -> `ModulePage.__init__`, which main.py's
    route_change() executes via `asyncio.to_thread(modules.build, ...)` -
    off the event loop, and at a moment when `page.views` has just been
    cleared (module_loader.build() only appends the new view after the
    constructor returns). `page.services` resolves through the root view
    (`views[0]`) and raises RuntimeError while views is empty - registering
    the FilePicker here is what broke every module screen with an
    ErrorPage. It's also pointless: services live on the root view, which
    the next navigation clears. So the picker is created and registered
    lazily in the async click handler instead - on the event loop, with a
    live root view to attach to.
    """

    def __init__(self, page: ft.Page, parent):
        self.page = page
        self.parent = parent  # Table
        self.file_picker: ft.FilePicker | None = None

        menu_items = []
        if not self.parent.is_inside_form:
            for fmt, label, icon in _FORMAT_OPTIONS:
                menu_items.append(
                    ft.PopupMenuItem(
                        content=label, icon=icon, on_click=self._download_handler(fmt)
                    )
                )

        # Upload only makes sense when the table has somewhere to put the
        # uploaded values - a purely read-only list table (no "input"/
        # "select"/etc. field) has nothing for it to populate. Bulk record
        # creation for those tables already goes through the "Add New"
        # screen's own bulk-upload menu (issue #5, components/form/menu.py::MenuForm).
        has_editable_fields = any(
            field.get("type") in _EDITABLE_TYPES for field in self.parent.fields
        )
        if has_editable_fields:
            if menu_items:
                # Separator between the download and upload sections.
                menu_items.append(ft.PopupMenuItem())
            menu_items.append(
                ft.PopupMenuItem(
                    content="Upload from CSV",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._upload_handler("csv"),
                )
            )
            menu_items.append(
                ft.PopupMenuItem(
                    content="Upload from XLSX",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._upload_handler("xlsx"),
                )
            )

        # Sized/padded to match the compact 32dp toolbar buttons
        # (components/button.py::Button's `size=32, radius=16`) - the
        # default PopupMenuButton's own ~48dp size and 8px padding didn't
        # fit inside the 48dp toolbar bar's 32px content height (after its
        # 8px vertical padding), so the hamburger rendered low/off-center
        # next to the other toolbar buttons rather than sharing their
        # vertical center.
        self.menu = ft.PopupMenuButton(
            icon=ft.Icons.MENU,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            icon_size=20,
            tooltip="Actions" if self.parent.is_inside_form else "Download",
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

    # ------------------------------------------------------------- download

    def _download_handler(self, fmt: str):
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

        client_id = None
        if isinstance(self.page.data, dict):
            client_id = self.page.data.get("client_id")
        if client_id:
            query += f"&client_id={client_id}"

        url = f"/download/{table.module}/{table.name}?{query}"
        self.page.run_task(self._launch, url)

    async def _launch(self, url: str) -> None:
        await self.page.launch_url(url)

    # --------------------------------------------------------------- upload

    def _upload_handler(self, fmt: str):
        # Must return a real `async def` closure - Flet's dispatcher only
        # awaits a handler that IS a coroutine function
        # (inspect.iscoroutinefunction). A plain `lambda e: self._x(e, fmt)`
        # is itself synchronous even though its body calls an async method,
        # so Flet would invoke it synchronously, get back an unused
        # coroutine object, and drop it - the "coroutine was never awaited"
        # RuntimeWarning, with the handler silently never running.
        async def on_click(e):
            await self._pick_and_populate(fmt)

        return on_click

    async def _pick_and_populate(self, fmt: str):
        # Lazy picker creation/registration - see the class docstring for
        # why this must not happen in __init__. Here we're on the event
        # loop inside an event handler: the current screen's root view
        # exists, page.update() is legal, and the websocket delivers the
        # registration patch before the pick_files invoke that follows it.
        # FilePicker is a `Service` (not a visual Control), so it goes in
        # `page.services` - `page.overlay` renders it as "Unknown control".
        # The `not in` re-check handles a picker orphaned by navigation
        # having replaced the root view its registration lived on.
        if self.file_picker is None:
            self.file_picker = ft.FilePicker()
        if self.file_picker not in self.page.services:
            self.page.services.append(self.file_picker)
            self.page.update()

        allowed = ["csv"] if fmt == "csv" else ["xlsx", "xls"]
        # with_data=True returns each file's content in
        # FilePickerFile.bytes directly - on web AND desktop - which makes
        # the whole upload_url/FLET_UPLOAD_DIR/on_upload-progress flow
        # unnecessary for reading a spreadsheet: no server-side upload dir,
        # no completion-event bookkeeping, no temp-file cleanup.
        files = await self.file_picker.pick_files(
            allowed_extensions=allowed,
            file_type=ft.FilePickerFileType.CUSTOM,
            with_data=True,
        )
        if not files:
            return

        file_info = files[0]
        data = file_info.bytes
        if data is None and file_info.path:
            # Native fallback: some platforms may hand back a path only.
            try:
                with open(file_info.path, "rb") as f:
                    data = f.read()
            except OSError as ex:
                self._show_error(f"Could not read file: {ex}")
                return
        if data is None:
            self._show_error("Could not read the selected file.")
            return

        try:
            ext = os.path.splitext(file_info.name)[1].lower()
            if ext in (".xlsx", ".xls"):
                rows = parse_xlsx_bytes(data)
            else:
                rows = parse_csv_bytes(data)
        except Exception as ex:
            self._show_error(f"Failed to parse {file_info.name}: {ex}")
            return

        if not rows:
            self._show_error("No rows found in the selected file.")
            return

        self._populate_table_fields(rows)

    def _populate_table_fields(self, rows: list[list[str]]):
        table = self.parent
        if not table.data:
            self._show_error("No table rows loaded to populate.")
            return

        headers = [str(h).strip() for h in rows[0]]
        data_rows = rows[1:]

        if not data_rows:
            self._show_error("No data rows found in the file.")
            return

        # Match file headers to table fields by visible label or field
        # name, case-insensitive. Unmatched file columns are ignored.
        header_to_field = {}  # file column index -> field dict
        for i, header in enumerate(headers):
            h_norm = header.lower().strip()
            for field in table.fields:
                label = str(field.get("label", ""))
                name = str(field.get("name", ""))
                if label.lower().strip() == h_norm or name.lower().strip() == h_norm:
                    header_to_field[i] = field
                    break

        # Label (read-only) columns present in the file act as a possibly-
        # composite key; editable columns receive values.
        key_fields_in_file = {}  # field_name -> file column index
        editable_fields_in_file = {}  # field_name -> file column index
        for file_idx, field in header_to_field.items():
            if field.get("type") in _EDITABLE_TYPES:
                editable_fields_in_file[field.get("name")] = file_idx
            else:
                key_fields_in_file[field.get("name")] = file_idx

        if not editable_fields_in_file:
            self._show_error("No editable columns in the file matched the table fields.")
            return

        def normalize_val(v):
            return "" if v is None else str(v).strip().lower()

        def cell(file_row, idx):
            return file_row[idx] if idx < len(file_row) else ""

        matched_count = 0
        if key_fields_in_file:
            table_lookup = {}  # key tuple -> table row index
            for idx, record in enumerate(table.data):
                key = tuple(
                    normalize_val(record.get(k)) for k in key_fields_in_file
                )
                table_lookup.setdefault(key, idx)

            for file_row in data_rows:
                key = tuple(
                    normalize_val(cell(file_row, i))
                    for i in key_fields_in_file.values()
                )
                if key not in table_lookup:
                    continue
                row_inputs = table.rows.input_controls[table_lookup[key]]
                for field_name, file_idx in editable_fields_in_file.items():
                    if field_name in row_inputs:
                        self._set_control_value(
                            row_inputs[field_name], cell(file_row, file_idx)
                        )
                matched_count += 1
        else:
            # No key columns in the file: populate visible rows in order.
            for i, file_row in enumerate(data_rows):
                if i >= len(table.rows.input_controls):
                    break
                row_inputs = table.rows.input_controls[i]
                for field_name, file_idx in editable_fields_in_file.items():
                    if field_name in row_inputs:
                        self._set_control_value(
                            row_inputs[field_name], cell(file_row, file_idx)
                        )
                matched_count += 1

        self._show_success(f"Populated {matched_count} row(s) from the file.")

    def _set_control_value(self, entry: dict, val):
        field_type = entry["type"]
        control = entry["control"]
        val_str = str(val).strip() if val is not None else ""

        if field_type == "datepicker":
            control.set_value(val_str)
            control._safe_update()
            return

        if field_type == "checkbox":
            control.value = val_str.lower() in ("1", "true", "yes")
        elif field_type in ("select", "option"):
            # Resolve against the dropdown's options by key or visible text.
            matched_key = None
            if val_str:
                for option in control.options:
                    key = str(option.key or "")
                    text = str(option.text or "")
                    if (
                        key.lower().strip() == val_str.lower()
                        or text.lower().strip() == val_str.lower()
                    ):
                        matched_key = option.key
                        break
            if val_str and matched_key is None:
                return  # unresolvable value: leave the cell as-is
            control.value = matched_key
        else:
            # input / textarea
            control.value = val_str

        try:
            control.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------- feedback

    def _show_error(self, message: str):
        # `self.parent` is the owning `Table`; `Table.parent` is either a
        # ModulePage (which has `.view` directly) or an ItemTable wrapper
        # (which exposes a `.view` property delegating to the header page's
        # view for exactly this purpose) - one level, same as
        # `Table.get_data()`'s own `self.parent.view.show_error(...)`.
        if hasattr(self.parent.parent, "view") and self.parent.parent.view:
            self.parent.parent.view.show_error(message)
        else:
            print(f"Error: {message}")

    def _show_success(self, message: str):
        if hasattr(self.parent.parent, "view") and self.parent.parent.view:
            self.parent.parent.view.show_success(message)
        else:
            print(f"Success: {message}")
