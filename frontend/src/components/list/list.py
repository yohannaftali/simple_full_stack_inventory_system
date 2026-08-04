import flet as ft

from components.list.body import Body
from components.list.filter import ListFilter
from components.list.layout import Layout
from components.list.menu import ListMenu
from components.search_bar import SearchBar
from components.list.tiles import Tiles
from components.list.toolbar import ListToolbar
from components.table.columns import TABLE_OUTER_HORIZONTAL_PADDING
from components.table.footer import MODE_LAZY, TableFooter
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
        qr: bool = True,
        custom_param: dict | None = None,
    ):
        """
        Initialize List

        Args:
            page (ft.Page): The Flet page
            parent (ModulePage): The parent module page
            name (str): The name of the list tile
            fields (list): The list of fields for the list tile
            endpoint (str, optional): The API endpoint for data fetching. Defaults to None.
            custom_param (dict, optional): Extra static query params merged into
                every request (issue #81) - mirrors Table's own `custom_param`,
                e.g. a sub-item list scoping every request to one header id, or
                a screen-level date-range filter applied after construction.
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
        self.custom_param = custom_param or {}
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

        self.list_search_bar = SearchBar(
            page=page,
            parent=self,
            hint_text="Search in list...",
            on_filter_change=self.on_filter_change,
            on_submit=self.on_submit,
            initial_value=self.filter,
            qr=qr,
        )

        # Download menu (issue #56) - the List equivalent of Table's
        # export_menu, read by ListToolbar.build() the same way
        # TableToolbar.build() reads Table.export_menu. Not built for
        # is_inside_form lists - no C_{module}/export_{name} endpoint exists
        # for an entry-mode widget, same reasoning as TableMenu.
        self.export_menu: ListMenu | None = None if is_inside_form else ListMenu(page, self)

        self.toolbar: ListToolbar | None = ListToolbar(
            page=page, parent=self, controls=[self.list_search_bar.build()]
        )

        # Per-field search + single-field sort (issue #55) - opt-in via
        # "filter"/"sort" on a field, same wire format Table's own
        # TableFilter/TableColumns produce, so the shared backend needs no
        # changes. Toggle button only added if at least one field opts in,
        # same convention as Table's own filter-row button.
        self.filter_row = ListFilter(
            page=page, parent=self, fields=fields, on_apply=self._handle_filter_apply
        )
        if self.filter_row.has_filters() and self.toolbar is not None:
            self.toolbar.add_filter_button(callback=self._toggle_filter_row)

        self.body: Body | None = None
        self.is_loading_more = False

        # Pagination-mode toggle footer (issue #55, porting #30) - reuses
        # Table's own TableFooter unmodified: it only ever reads
        # `parent.total_rows`/`total_pages`/`page_number`/`limit`/`data`
        # and calls three `parent._handle_footer_*` callbacks, and `List`
        # already carries the exact same attribute names, so no fork was
        # needed. Not built for `is_inside_form` lists, same reasoning as
        # Table's own footer (no real dataset to page through there).
        self.footer: TableFooter | None = None if is_inside_form else TableFooter(page, parent=self)
        self._footer_index: int | None = None

        self.list_container: ft.Container | None = None
        self.data: list = []
        self.endpoint = (
            endpoint if endpoint is not None else f"C_{self.module}/get_{self.name}"
        )

        if not is_inside_form:
            self.get_data()

    def build(
        self,
        padding: ft.PaddingValue = ft.Padding.symmetric(
            horizontal=TABLE_OUTER_HORIZONTAL_PADDING
        ),
        height: int | None = None,
    ):
        self.body = Body(
            page=self.page,
            layout=self.layout,
            tiles=self.tiles,
            on_scroll_end=self._handle_scroll_end,
        )

        # Build controls list, filtering out None values. `_footer_index`
        # is recorded so `load()` can patch the footer's own slot in place
        # after every fetch (issue #55) - without this the "Record X of Y"
        # message and page buttons go stale after a filter/sort/page
        # change, same fix Table's own `load()` already applies to its
        # footer.
        controls = []
        if self.toolbar:
            toolbar_control = self.toolbar.build()
            if toolbar_control:
                controls.append(toolbar_control)

        if self.filter_row.has_filters():
            controls.append(self.filter_row.build())

        if self.body:
            body_control = self.body.build()
            if body_control:
                controls.append(body_control)

        self._footer_index = None
        if self.footer is not None:
            self._footer_index = len(controls)
            controls.append(self.footer.build())

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
        """Handle scroll to bottom - load next page.

        Only fires in lazy-load mode (issue #55, same guard as Table's own
        `_handle_scroll_end`) - once toggled to pagination mode, paging
        happens only via the footer's own buttons.
        """
        if self.footer is not None and self.footer.mode != MODE_LAZY:
            return

        if self.is_loading_more or self.page_number >= self.total_pages:
            return

        self.is_loading_more = True
        self.page_number += 1
        self.get_data(page_no=self.page_number, append=True)
        self.is_loading_more = False

    def get_data(self, page_no: int = 1, offset: int = 0, append: bool = False):
        if not append:
            self.data = []
        client = HttpClient(self.page)
        param = f"table-keyword-filter={self.filter}" if self.filter else ""
        param = param + f"&limit={self.limit}&page={page_no}&offset={offset}"
        for key, value in self.custom_param.items():
            param = param + f"&{key}={value}"
        param = param + self.filter_row.serialize()
        response = client.get(f"{self.endpoint}?{param}" if param else self.endpoint)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            self.parent.view.show_error(f"Failed to load data: {response.get('error')}")
            return

        if isinstance(response, list):
            if response:
                first_row = response[0]
                self.total_pages = first_row.get("db_total_page", 1)
                self.total_rows = first_row.get("db_num_rows", len(response))
            else:
                self.total_pages = 1
                self.total_rows = 0

            self.data = self.data + response if append else response
            self.load(response, append=append)
        else:
            print(f"Unexpected response format: {response}")

    def _toggle_filter_row(self, e=None) -> None:
        self.filter_row.toggle()

    def _handle_filter_apply(self) -> None:
        self.page_number = 1
        self.get_data()

    def _handle_footer_mode_change(self, mode) -> None:
        self.page_number = 1
        self.get_data(1, 0, False)

    def _handle_footer_page_change(self, page_no: int) -> None:
        self.page_number = page_no
        self.get_data(page_no, offset=(page_no - 1) * self.limit, append=False)

    def _handle_footer_limit_change(self, new_limit: int) -> None:
        self.limit = new_limit
        self.page_number = 1
        self.get_data(1, 0, False)

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

        # Refresh the footer's own slot in place (issue #55) - otherwise
        # "Record X of Y" and the page buttons go stale after a
        # filter/sort/page change, same fix Table's own `load()` applies.
        if (
            self.footer is not None
            and self._footer_index is not None
            and self.list_container is not None
        ):
            new_footer = self.footer.build()
            col = self.list_container.content
            if isinstance(col, ft.Column) and len(col.controls) > self._footer_index:
                col.controls[self._footer_index] = new_footer
                try:
                    col.update()
                except RuntimeError:
                    pass

    def on_filter_change(self, search_text):
        """Handle search input change from table search bar"""
        self.filter = search_text
        self.page_number = 1  # Reset to first page on search
        self.get_data()

    def on_submit(self, e):
        """Handle Enter key press in search bar"""
        self.page_number = 1  # Reset to first page on search
        self.get_data()
