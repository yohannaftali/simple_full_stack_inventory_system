import flet as ft

from utils.http_client import HttpClient

from components.table.columns import Columns
from components.table.rows import Rows
from components.table.toolbar import TableToolbar
from components.table.search_bar import TableSearchBar
from components.table.header import Header
from components.table.body import Body
from repository.storage import Storage


class Table:
    def __init__(self, page: ft.Page, parent, name: str, fields: list, endpoint: str | None = None, limit: int = 20, is_inside_form: bool = False):
        """
        Initialize Table

        Args:
            page (ft.Page): The Flet page
            parent (ModulePage): The parent module page
            name (str): The name of the table
            fields (list): The list of fields for the table
            endpoint (str, optional): The API endpoint for data fetching. Defaults to None.
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.parent = parent  # ModulePage
        self.name = name
        self.fields = fields

        self.module = parent.module
        self.screen = parent.screen

        self.is_inside_form = is_inside_form

        self.columns: Columns = Columns(page, fields)
        self.rows: Rows = Rows(page, self.columns, parent=self)

        self.limit = limit
        self.page_number = 1  # Current page
        self.total_pages = 1  # Total pages from API
        self.total_rows = 0   # Total rows from API

        self.filter = ""
        self.filter = self.storage.table_search.get(
            self.module, self.screen, self.name)
        self.table_search_bar = TableSearchBar(
            page=page,
            parent=self,
            on_filter_change=self.on_filter_change,
            on_submit=self.on_submit,
            initial_value=self.filter
        )
        self.toolbar: TableToolbar | None = TableToolbar(
            page=page,
            parent=self,
            controls=[self.table_search_bar.build()]
        )
        self.header: Header | None = None
        self.body: Body | None = None
        self.is_loading_more = False

        self.table_container: ft.Container | None = None
        self.data: list = []
        self.endpoint = endpoint if endpoint is not None else f"C_{self.module}/get_{self.name}"

        if 'active_tables' not in page.data:
            page.data['active_tables'] = []
        page.data['active_tables'].append(self)

        if not is_inside_form:
            self.get_data()

    def build(self, padding: int = 0):
        self.header = Header(
            page=self.page,
            columns=self.columns
        )
        self.body = Body(
            page=self.page,
            columns=self.columns,
            rows=self.rows,
            on_scroll_end=self._handle_scroll_end
        )

        # Build controls list, filtering out None values
        controls = []
        if self.toolbar:
            toolbar_control = self.toolbar.build()
            if toolbar_control:
                controls.append(toolbar_control)

        if self.header:
            header_control = self.header.build()
            if header_control:
                controls.append(header_control)

        if self.body:
            body_control = self.body.build()
            if body_control:
                controls.append(body_control)

        self.table_container = ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=0,
                expand=True,
            ),
            expand=True,
            padding=padding,
        )

        # If we have pending data (from form load), render it now
        # Just load the columns/rows without calling update() since not on page yet
        if self.data and len(self.data) > 0:
            self.columns.load(self.data)
            self.rows.load(self.data, append=False)
            # Rebuild the header and body with the loaded data
            if self.header and self.body:
                if isinstance(self.table_container.content.controls, list) and len(self.table_container.content.controls) >= 2:
                    # Replace header and body in the controls list
                    if self.toolbar:
                        self.table_container.content.controls[1] = self.header.build(
                        )
                        self.table_container.content.controls[2] = self.body.build(
                        )
                    else:
                        self.table_container.content.controls[0] = self.header.build(
                        )
                        self.table_container.content.controls[1] = self.body.build(
                        )

        return self.table_container

    def _handle_scroll_end(self):
        """Handle scroll to bottom - load next page"""
        print(
            f"Scroll end handler called - page: {self.page_number}/{self.total_pages}, loading: {self.is_loading_more}")

        if self.is_loading_more or self.page_number >= self.total_pages:
            print("Skipping load - already loading or last page reached")
            return

        print(f"Loading page {self.page_number + 1}...")
        self.is_loading_more = True
        self.page_number += 1
        self.get_data(page_no=self.page_number, append=True)
        self.is_loading_more = False

    def get_data(self, page_no: int = 1, offset: int = 0, append: bool = False):
        self.data = []
        client = HttpClient(self.page)
        param = f"table-keyword-filter={self.filter}" if self.filter else ""
        param = param + f"&limit={self.limit}&page={page_no}&offset={offset}"
        response = client.get(
            f"{self.endpoint}?{param}" if param else self.endpoint)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            self.parent.view.show_error(
                f"Failed to load data: {response.get('error')}")
            return

        if isinstance(response, list):
            # Extract pagination metadata from first row
            first_row = response[0]
            self.total_pages = first_row.get('db_total_page', 1)
            self.total_rows = first_row.get('db_num_rows', len(response))

            self.data = response
            self.load(response, append=append)
        else:
            print(f"Unexpected response format: {response}")

    def load(self, data: list, append: bool = False) -> None:
        # Show loading indicator
        if self.body:
            if not self.is_inside_form:
                self.body.show_loading()

        # Recalculate column widths and rebuild rows
        self.columns.load(data)
        self.rows.load(data, append=append)

        # If the table has already been built (header/body DataTables exist inside
        # self.table_container), replace the DataTable controls so the new
        # DataColumn/DataRow objects (with fixed-width Containers) are used.
        # Rebuilding the DataTable controls ensures Flet lays out cells with the
        # newly-applied container widths.
        if self.table_container and hasattr(self.table_container, 'content'):
            col = self.table_container.content  # ft.Column
            # Recreate header and body DataTable widgets using the header/body
            # builders which read from `self.columns` and `self.rows`.
            new_header = None
            new_body = None
            if self.header:
                # keep header.columns reference (already set on init)
                new_header = self.header.build()
            if self.body:
                new_body = self.body.build()

            # Replace the first two controls (header, body) if present
            if isinstance(col.controls, list) and len(col.controls) >= 3:
                if new_header is not None:
                    col.controls[0] = self.toolbar.build()
                    col.controls[1] = new_header
                if new_body is not None:
                    col.controls[2] = new_body
                # Trigger update for the column container and its parent
                col.update()
                self.table_container.update()
        else:
            # If not yet built, just ensure header/body objects are updated so
            # when `build()` is eventually called they use the latest widths.
            if self.header:
                self.header.columns = self.columns
            if self.body:
                self.body.columns = self.columns
                self.body.rows = self.rows

        # Hide loading indicator
        if self.body:
            if not self.is_inside_form:
                self.body.hide_loading()

    def on_page_resize(self) -> None:
        """Handle page resize events - called from main page resize handler"""
        print(f"Table {self.name} resize triggered")
        if self.data:
            # Reload the table with new widths
            self.load(self.data)

            print(f"Table {self.name} resized for width: {self.page.width}")

    def on_filter_change(self, search_text):
        """Handle search input change from table search bar"""
        self.filter = search_text
        self.page_number = 1  # Reset to first page on search
        self.get_data()

    def on_submit(self, e):
        """Handle Enter key press in search bar"""
        # For now, just reload data
        self.page_number = 1  # Reset to first page on search
        self.get_data()
