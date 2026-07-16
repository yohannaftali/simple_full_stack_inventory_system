import flet as ft

from components.form.heading import HeadingForm
from components.form.label import LabelForm
from components.form.input import InputForm
from components.form.date import DateForm
from components.form.select import SelectForm
from components.form.table import TableForm
from components.form.list import ListForm
from components.form.button import ButtonForm
from utils.http_client import HttpClient


class Form:
    def __init__(
        self,
        page: ft.Page,
        parent,
        name: str,
        fields: list,
        custom_param: str = None,
        endpoint_get: str | None = None,
        endpoint_submit: str | None = None,
        start_blank: bool = False,
        bulk_input: bool = False,
        bulk_endpoint: str | None = None,
        bulk_extra_fields: dict | None = None,
        bulk_redirect: str | None = None,
    ):
        """
        Initialize Table

        Args:
            page (ft.Page): The Flet page
            parent (ModulePage): The parent module page
            name (str): The name of the table
            fields (list): The list of fields for the table
            endpoint (str, optional): The API endpoint for data fetching. Defaults to None.
            bulk_input (bool, optional): Explicitly opt this screen into the
                CSV/XLSX bulk-upload hamburger menu (issue #5/#24/#25) -
                replaces the old implicit "attach whenever screen == 'new'"
                guard, which silently broke on any `new` screen whose
                backend router has no `submit_bulk` endpoint (e.g.
                `ap_config`) and couldn't be used at all for non-`new`
                screens with their own bulk-eligible flow (e.g. stock_in's
                `item_new`). Defaults to False - every screen must opt in.
            bulk_endpoint (str, optional): Override the endpoint the bulk
                upload POSTs to. Defaults to `C_{module}/submit_bulk`.
            bulk_extra_fields (dict, optional): Static fields merged into
                every row's payload (e.g. `{"receiving_header_id": "3"}` for
                an item-level bulk upload scoped to one header).
            bulk_redirect (str, optional): Route to navigate to after a
                successful bulk upload. Defaults to `/modules/{module}/index`.
        """
        self.page = page
        self.parent = parent  # ModulePage
        self.name = name
        self.fields = fields
        self.record_key = "id"
        self.record_id = parent.record_id
        self.bulk_input = bulk_input
        self.bulk_endpoint = bulk_endpoint
        self.bulk_extra_fields = bulk_extra_fields
        self.bulk_redirect = bulk_redirect

        self.index = []

        self.custom_param = custom_param

        self.module = parent.module
        self.screen = parent.screen

        self.elements: dict = {}
        self.rows = []
        self.map_type = {}

        self.controls = []

        self.heading = {}
        self.label = {}
        self.input = {}
        self.date = {}
        self.select = {}
        self.table = {}
        self.list = {}
        self.custom = {}

        self.form_container: ft.Container | None = None
        self.data: list = []
        self.endpoint_get = (
            endpoint_get if endpoint_get is not None else f"C_{self.module}/get"
        )
        self.endpoint_submit = (
            endpoint_submit
            if endpoint_submit is not None
            else f"C_{self.module}/submit"
        )
        self.padding_row = 20
        self.group_by_row()
        self.build_elements()
        if not start_blank:
            self.get_data()

    def build(self, padding: int = 20):
        self.padding_row = padding
        self._attach_bulk_menu()
        self.form_container = ft.Container(
            content=ft.Column(
                controls=self.controls,
                spacing=10,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
            padding=0,
        )

        # After building, update any list/table components with their data
        for element in self.list.values():
            element.rebuild()

        for element in self.table.values():
            element.rebuild()

        for element in self.select.values():
            element.rebuild()

        # Set up cascading select dependencies
        self.setup_cascading_selects()

        # Trigger dependent selects with current form values in case form was pre-populated
        form_data = self.serialize(self.fields)
        for field_name, select_form in self.select.items():
            if select_form.depends_on and form_data.get(select_form.depends_on):
                select_form.refresh_with_values(form_data)

        return self.form_container

    def _attach_bulk_menu(self):
        """Give a screen a bulk-upload hamburger menu at the far right of
        its ModuleToolbar (issue #5/#24/#25) whenever it opted in via
        `bulk_input=True` - explicit per-screen, not inferred from `screen
        == "new"` (that guessed wrong for `ap_config`, whose backend router
        has no `submit_bulk` endpoint, and couldn't be used at all for a
        bulk-eligible non-`new` screen like stock_in's `item_new`). Runs in
        build() (not __init__) deliberately: new.py/item_new.py screens add
        their submit button between Form construction and body()/build(),
        so appending here lands the menu rightmost. The double-attach flag
        covers any repeated build() call."""
        if not self.bulk_input or getattr(self, "_bulk_menu_attached", False):
            return
        view = getattr(self.parent, "view", None)
        if view is None or not hasattr(view, "toolbar"):
            return

        from components.form.menu import MenuForm

        self.bulk_menu = MenuForm(
            page=self.page,
            form=self,
            endpoint=self.bulk_endpoint,
            extra_fields=self.bulk_extra_fields,
            redirect_route=self.bulk_redirect,
        )
        if view.toolbar.right is None:
            view.toolbar.right = []
        view.toolbar.right.append(self.bulk_menu.build())
        self._bulk_menu_attached = True

    def setup_cascading_selects(self):
        """Set up on_change handlers for parent fields that have dependent selects"""

        # Find all select fields that have depends_on
        for field_name, select_form in self.select.items():
            depends_on = select_form.depends_on

            if not depends_on:
                continue

            # Normalize to list
            parent_fields = [depends_on] if isinstance(depends_on, str) else depends_on

            for parent_field in parent_fields:
                # Check if parent field is a select
                if parent_field not in self.select:
                    continue

                parent_select_form = self.select[parent_field]

                # Create on_change handler for parent
                def create_handler(child_select):
                    def handler(e, child=child_select):  # Capture by value using default param
                        # Only serialize simple values to avoid overhead/recursion
                        # We need current values of all fields to pass to the child
                        form_data = self.serialize(self.fields)

                        # Update the child with all form values
                        child.refresh_with_values(form_data)

                        # Also handle linked fields update if any
                        # Note: we don't need to manually call link handler here because we chain it below
                        pass

                    return handler

                # Set on_select on parent dropdown (Flet 0.85 renamed
                # Dropdown.on_change to on_select)
                if parent_select_form.select:
                    # Store original handler if exists
                    original_handler = parent_select_form.select.on_select

                    def chained_handler(e, child_sel=select_form):  # Capture by value
                        if original_handler:
                            original_handler(e)
                        create_handler(child_sel)(e)

                    parent_select_form.select.on_select = chained_handler


    def build_elements(self):
        """Build UI elements from parsed fields and loaded data"""
        self.elements = {}
        self.controls = []

        for row in self.rows:
            row_elements: list = []
            for field in row:
                field_name = field.get("name")
                if field_name is None:
                    self.map_type[field_name] = "None"
                    continue

                field_is_key = field.get("key", False)
                if field_is_key:
                    self.record_key = field_name

                field_type = field.get("type", "input")

                if field_type == "hidden":
                    continue
                field_col = field.get("col", {"sm": 12})

                is_custom = field.get(
                    "custom", False) or field_type == "custom"
                is_input = field.get("input", False) or field_type == "input"
                is_label = field.get(
                    "label_info", False) or field_type == "label"
                is_heading = field.get(
                    "heading", False) or field_type == "heading"
                is_table = field.get("table", False) or field_type == "table"
                is_list = field.get("list", False) or field_type == "list"
                is_button = field.get(
                    "button", False) or field_type == "button"

                control = None
                if is_heading:
                    self.map_type[field_name] = "heading"
                    self.heading[field_name] = HeadingForm(field)
                    control = self.heading[field_name].build()
                elif is_label:
                    self.map_type[field_name] = "label"
                    self.label[field_name] = LabelForm(field)
                    control = self.label[field_name].build()
                elif is_input:
                    self.map_type[field_name] = "input"
                    self.input[field_name] = InputForm(field)
                    control = self.input[field_name].build()
                elif field_type == "date":
                    self.map_type[field_name] = "date"
                    self.date[field_name] = DateForm(
                        page=self.page,
                        parent=self.parent,
                        field=field)
                    control = self.date[field_name].build()
                elif field_type == "select":
                    self.map_type[field_name] = "select"
                    self.select[field_name] = SelectForm(
                        page=self.page,
                        parent=self.parent,
                        field=field)
                    control = self.select[field_name].build()
                elif is_table:
                    self.map_type[field_name] = "table"
                    self.table[field_name] = TableForm(
                        page=self.page,
                        parent=self.parent,
                        field=field,
                    )
                    control = self.table[field_name].build()
                elif is_list:
                    self.map_type[field_name] = "list"
                    self.list[field_name] = ListForm(
                        page=self.page,
                        parent=self.parent,
                        field=field
                    )
                    control = self.list[field_name].build()
                elif is_button:
                    self.map_type[field_name] = "button"
                    button_form = ButtonForm(field)
                    control = button_form.build()
                elif is_custom:
                    self.map_type[field_name] = "custom"
                    self.custom[field_name] = field.get("control") or None
                    control = self.custom[field_name]

                self.elements[field_name] = control
                self.index.append(field_name)

                # wrap control in a responsive column and add to the row
                row_elements.append(
                    ft.Column(
                        col=field_col,
                        controls=[self.elements[field_name]]
                        if self.elements[field_name] is not None
                        else [],
                    )
                )

            self.controls.append(
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=row_elements,
                        run_spacing={"xs": 10},
                    ),
                    expand=True,
                    padding=ft.Padding(
                        left=self.padding_row, right=self.padding_row, top=0, bottom=0
                    ),
                )
            )

    def group_by_row(self):
        # Group fields by their `row` index and produce a sorted list
        rows_map: dict[int, list] = {}
        for field in self.fields:
            try:
                row_idx = int(field.get("row", 0) or 0)
            except Exception:
                row_idx = 0
            rows_map.setdefault(row_idx, []).append(field)

        # Convert to a list sorted by row index so `self.rows[0]` is the first row, etc.
        self.rows = [rows_map[k] for k in sorted(rows_map.keys())]

    def get_data(self):
        self.data = []
        client = HttpClient(self.page)
        params = (
            self.custom_param
            if self.custom_param is not None
            else {self.record_key: self.record_id}
        )
        response = client.get(self.endpoint_get, params)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            return
        # Normalize response to a payload dict for populating the form.
        payload = {}
        if isinstance(response, dict):
            # Some APIs wrap the actual record under a `master` key
            if "master" in response and isinstance(response["master"], dict):
                payload = response["master"]
            else:
                # Otherwise assume the dict itself is the payload (may include message keys)
                payload = response
        elif (
            isinstance(response, list)
            and len(response) > 0
            and isinstance(response[0], dict)
        ):
            # Some APIs return a list with a single dict payload
            payload = response[0]

        # If payload contains only meta (e.g., msg/error) and no real fields,
        # try to detect and show messages instead of populating the form.
        # Consider a payload 'real' if it shares any field names with self.fields
        has_real_fields = False
        if isinstance(payload, dict) and payload:
            field_names = {f.get("name") for f in self.fields if f.get("name")}
            # If any key in payload matches a configured field name, treat it as data
            if any(k in field_names for k in payload.keys()):
                has_real_fields = True

        if has_real_fields:
            self.data = [payload]
            try:
                self.load(self.data)
            except Exception as e:
                print(f"Error loading form data: {e}")
        else:
            # Fall back to message handling when no data fields detected
            message_text = self.extract_message(response)
            print(f"Response message: {message_text or str(response)}")

    def load(self, data: list) -> None:
        """Populate form fields with data

        Args:
            data (list): List containing form data dictionary
        """
        if not data or len(data) == 0:
            return

        # Update TextField elements
        for field_name, control in self.elements.items():
            print(f"Field name: {field_name}")
            if field_name in self.date:
                # DateForm displays "dd Mon yyyy" but stores/submits the raw
                # ISO value separately (see DateForm.set_value) - assigning
                # the ISO value straight to control.value here would show
                # the unformatted ISO string instead.
                self.date[field_name].set_value(data[0].get(field_name, ""))
            elif isinstance(control, ft.TextField):
                self.elements[field_name].value = data[0].get(field_name, "")

            if isinstance(control, ft.Dropdown):
                field_value = data[0].get(field_name, "")
                self.elements[field_name].value = field_value if field_value not in [
                    None, ""] else None

            if isinstance(control, ft.Container):
                list_data = data[0].get(field_name, [])
                print(list_data)
                if field_name in self.table:
                    if isinstance(list_data, list):
                        self.load_table(field_name, list_data)
                if field_name in self.list:
                    print(f"list field name {field_name}")
                    if isinstance(list_data, list):
                        self.load_list(field_name, list_data)

        # After loading all form fields, trigger dependent selects refresh
        form_data = self.serialize(self.fields)
        for field_name, select_form in self.select.items():
            if select_form.depends_on and form_data.get(select_form.depends_on):
                select_form.refresh_with_values(form_data)

    def load_table(self, field_name: str, data: list) -> None:
        """Populate table field with data

        Args:
            field_name (str): The name of the table field
            data (list): List of records to populate the table
        """
        if field_name in self.table:
            # Just store the data - it will be rendered when form.build() is called
            self.table[field_name].set_data(data)

    def load_list(self, field_name: str, data: list) -> None:
        """Populate list field with data

        Args:
            field_name (str): The name of the list field
            data (list): List of records to populate the list
        """
        if field_name in self.list:
            # Just store the data - it will be rendered when form.build() is called
            self.list[field_name].set_data(data)

    def serialize_list(self, fields: list, list_data: list) -> dict:
        form_data = {}

        for row_index, row_data in enumerate(list_data):
            if not isinstance(row_data, dict):
                continue

            for field in fields:
                field_name = field.get("name", "")
                if field_name == "":
                    continue

                is_serialized = field.get("serialized", True)
                if not is_serialized:
                    continue

                field_type = field.get("type", "label")

                is_key = field.get("key", False) or field_type == "key"
                is_input = field.get("input", False) or field_type == "input"
                is_select = field.get(
                    "select", False) or field_type == "select"

                if not (is_key or is_input or is_select):
                    continue

                indexed_key = f"{field_name}[{row_index}]"
                field_value = row_data.get(field_name, "")
                form_data[indexed_key] = field_value

        return form_data

    def serialize(self, fields: list | None = None) -> dict:
        form_data = {}

        fields = fields if fields is not None else self.fields
        for field in fields:
            field_name = field.get("name", "")
            if field_name == "":
                continue

            is_serialized = field.get("serialized", True)
            if not is_serialized:
                continue

            field_type = field.get("type", "input")
            if field_type == "label":
                continue

            is_key = field.get("key", False) or field_type == "key"
            is_input = (
                field.get("input", False)
                or field_type == "input"
                or field_type == "date"
            )
            is_select = field.get("select", False) or field_type == "select"
            is_table = field.get("table", False) or field_type == "table"
            is_list = field.get("list", False) or field_type == "list"

            if is_key:
                self.record_key = field_name
                form_data[self.record_key] = self.record_id
            elif field_name in self.date:
                # Submit the true ISO value, not the "dd Mon yyyy" text
                # displayed in the field - see DateForm.get_value().
                form_data[field_name] = self.date[field_name].get_value()
            elif is_input:
                control = self.elements.get(field_name)
                if isinstance(control, ft.TextField):
                    form_data[field_name] = control.value
            elif is_select:
                control = self.elements.get(field_name)
                if isinstance(control, ft.Dropdown):
                    form_data[field_name] = control.value
            elif is_table or is_list:
                content_fields = field.get("content", [])
                if not isinstance(content_fields, list):
                    continue

                # Get the data for this table/list
                list_data = self.table[field_name].get_data(
                ) if field_type == "table" else self.list[field_name].get_data()
                if not isinstance(list_data, list):
                    continue

                form_data_list = self.serialize_list(content_fields, list_data)
                form_data.update(form_data_list)

        if self.custom_param and isinstance(self.custom_param, dict):
            form_data.update(self.custom_param)

        print("form data:")
        print(form_data)

        return form_data

    def reset(self) -> None:
        """Reset text fields only"""
        try:
            for field_name, control in self.elements.items():
                if isinstance(control, ft.TextField):
                    control.value = ""
            
            if self.page:
                self.page.update()
        except Exception as e:
            print(f"Error resetting form: {e}")

    def submit(self) -> None:
        """Submit form data to the endpoint"""
        form_data = self.serialize(self.fields)
        client = HttpClient(self.page)
        response = client.post(self.endpoint_submit, data=form_data)

        if isinstance(response, dict) and "error" in response:
            print(f"Submit error: {response['error']}")
            self.parent.view.show_error(response['error'])
            return

        message_text = self.extract_message(response)
        print(f"Submit response: {message_text or str(response)}")
        if "error" in message_text.lower():
            self.parent.view.show_error(message_text)
        else:
            self.parent.view.show_success(
                message_text or "Form submitted successfully."
            )
            # Redirect to index page after successful submit
            # Using go() to navigate back
            if self.page:
                # Construct index route: /modules/{module}/index
                index_route = f"/modules/{self.module}/index"
                print(f"Redirecting to: {index_route}")
                self.page.run_task(self.page.push_route, index_route)

    def extract_message(self, obj) -> str:
        # Try common keys used by the API, fall back to string representation
        if isinstance(obj, dict):
            for key in ("msg", "message", "success", "error", "status"):
                if key in obj and obj[key] is not None:
                    return str(obj[key])
            return str(obj)
        if isinstance(obj, list):
            if len(obj) == 0:
                return ""
            return self.extract_message(obj[0])
        return str(obj)
