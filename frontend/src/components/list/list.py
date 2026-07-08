import flet as ft

from components.list.body import Body
from components.list.layout import Layout
from components.list.search_bar import ListSearchBar
from components.list.tiles import Tiles
from components.list.toolbar import ListToolbar
from repository.storage import Storage
from utils.http_client import HttpClient


class List:
    def __init__(
        self,
        page: ft.Page,
        parent,
        name: str,
        fields: list,
        endpoint: str | None = None,
        limit: int = 20,
        is_inside_form: bool = False,
        title=None,
        subtitle=None,
        leading=None,
        trailing=None,
        next_page="edit",
    ):
        """
        Initialize List

        Args:
            page (ft.Page): The Flet page
            parent (ModulePage): The parent module page
            name (str): The name of the list tile
            fields (list): The list of fields for the list tile
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

        self.limit = limit
        self.page_number = 1  # Current page
        self.total_pages = 1  # Total pages from API
        self.total_rows = 0  # Total rows from API

        self.layout: Layout = Layout(page, fields)
        self.tiles: Tiles = Tiles(
            page=page,
            parent=self,
            layout=self.layout,
            title=title,
            subtitle=subtitle,
            leading=leading,
            trailing=trailing,
            next_page=next_page,
        )

        self.filter = self.storage.table_search.get(
            module=self.module, screen=self.screen, name=self.name
        )

        self.list_search_bar = ListSearchBar(
            page=page,
            parent=self,
            on_filter_change=self.on_filter_change,
            on_submit=self.on_submit,
            initial_value=self.filter,
        )

        self.toolbar: ListToolbar | None = ListToolbar(
            page=page, parent=self, controls=[self.list_search_bar.build()]
        )

        self.body: Body | None = None
        self.is_loading_more = False

        self.list_container: ft.Container | None = None
        self.data: list = []
        self.endpoint = (
            endpoint if endpoint is not None else f"C_{self.module}/get_{self.name}"
        )

        if not is_inside_form:
            self.get_data()

    def build(self, padding: int = 0, height: int | None = None):
        self.body = Body(
            page=self.page,
            layout=self.layout,
            tiles=self.tiles,
            on_scroll_end=self._handle_scroll_end,
        )

        # Build controls list, filtering out None values
        controls = []
        if self.toolbar:
            toolbar_control = self.toolbar.build()
            if toolbar_control:
                controls.append(toolbar_control)

        if self.body:
            body_control = self.body.build()
            if body_control:
                controls.append(body_control)

        self.list_container = ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=0,
                expand=True if height is None else False,
            ),
            expand=True if height is None else False,
            height=height,
            padding=padding,
        )

        # If we have pending data (from form load), render it now
        # Just load the tiles without calling update() since not on page yet
        if self.data and len(self.data) > 0:
            self.tiles.load(self.data, append=False)
            if self.body and self.body.list_view:
                self.body.list_view.controls = self.tiles.build()

        return self.list_container

    def _handle_scroll_end(self):
        """Handle scroll to bottom - load next page"""
        print(
            f"Scroll end handler called - page: {self.page_number}/{self.total_pages}, loading: {self.is_loading_more}"
        )

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
        response = client.get(f"{self.endpoint}?{param}" if param else self.endpoint)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            self.parent.view.show_error(f"Failed to load data: {response.get('error')}")
            return

        if isinstance(response, list) and len(response) > 0:
            # Extract pagination metadata from first row
            first_row = response[0]
            self.total_pages = first_row.get("db_total_page", 1)
            self.total_rows = first_row.get("db_num_rows", len(response))

            self.data = response
            self.load(response, append=append)
        else:
            print(f"Unexpected response format: {response}")

    def load(self, data: list, append: bool = False) -> None:
        # Load tiles (append if loading more pages)
        self.tiles.load(data, append=append)

        # Update the ListView controls with new tiles if body exists
        if self.body and self.body.list_view:
            if not self.is_inside_form:
                # Show loading indicator
                self.body.show_loading()

            self.body.list_view.controls = self.tiles.build()
            self.body.list_view.update()

            if not self.is_inside_form:
                # Hide loading indicator
                self.body.hide_loading()
        elif self.body:
            if not self.is_inside_form:
                # Body exists but list_view not ready, just hide loading
                self.body.hide_loading()

    def on_filter_change(self, search_text):
        """Handle search input change from table search bar"""
        self.filter = search_text
        self.page_number = 1  # Reset to first page on search
        self.get_data()

    def on_submit(self, e):
        """Handle Enter key press in search bar"""
        self.page_number = 1  # Reset to first page on search
        self.get_data()
