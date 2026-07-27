import flet as ft

from components.table.body import TableBody
from components.table.columns import TABLE_OUTER_HORIZONTAL_PADDING, TableColumns
from components.table.filter import TableFilter
from components.table.footer import MODE_LAZY, TableFooter
from components.table.header import TableHeader
from components.table.menu import TableMenu
from components.table.remove import TableRemove
from components.table.rows import TableRows
from components.table.search_bar import TableSearchBar
from components.table.toolbar import TableToolbar
from repository.storage import Storage
from utils.http_client import HttpClient

# Used by Table._should_eagerly_load_more() to guess whether the rows
# loaded so far already fill the visible viewport, without depending on a
# client-side scroll event (Flet's on_scroll never fires at all for a
# scrollable whose content doesn't overflow its own viewport - confirmed
# empirically, there's simply no scroll gesture to report - so a short
# result set on a tall/short-viewport screen could never trigger lazy-load
# via scroll and would strand the user with unfetched rows and no way to
# reach them). Deliberately generous (errs toward "not full yet, keep
# loading") since fetching one page too many is harmless - get_data()
# stops on its own once every page is loaded - while stranding the user
# is the actual bug this exists to prevent. _MAX_ROW_HEIGHT matches
# TableBody.build()'s own `data_row_max_height`.
_ESTIMATED_CHROME_HEIGHT = 220
_MAX_ROW_HEIGHT = 44


class Table:
    def __init__(
        self,
        page: ft.Page,
        parent,
        name: str,
        fields: list,
        endpoint: str | None = None,
        limit: int = 20,
        is_inside_form: bool = False,
        edit_screen: str = "edit",
        custom_param: dict | None = None,
        fill_available_space: bool = True,
        on_remove_row=None,
        on_remove_rows=None,
    ):
        """
        Initialize Table

        Args:
            page (ft.Page): The Flet page
            parent (ModulePage): The parent module page
            name (str): The name of the table
            fields (list): The list of fields for the table
            endpoint (str, optional): The API endpoint for data fetching. Defaults to None.
            edit_screen (str, optional): Screen name a row click navigates to
                (`/modules/{module}/{edit_screen}/{id}`). Defaults to "edit" -
                override for sub-tables whose row-click target isn't the
                parent module's own edit screen (e.g. an item sub-table on a
                header's edit screen navigating to "item_edit" instead).
            custom_param (dict, optional): Extra static query params merged
                into every get_data() request (e.g. {"header_id": 3} for an
                item sub-table scoped to one header).
            fill_available_space (bool, optional): Defaults to True - the
                table (and its footer) expands to fill all remaining
                vertical space, which is the right look for a screen that's
                nothing but this one table (most module `index.py` screens).
                Set False (issue #37) for a table that shares its screen
                with a `Form` or another `Table` (e.g. `stock_in/edit.py`'s
                item sub-table, `purchase_report/index.py`'s two tables) -
                the table then sizes to whatever its caller's own wrapping
                Container gives it (still that caller's responsibility to
                provide a bounded height, same as before this flag existed;
                this only stops `Table` from *also* forcing `expand=True` on
                top of that, which is what let the footer drift to the
                bottom of the whole page instead of sitting right under the
                table's actual content).
            on_remove_row (callable, optional): opts into the single/bulk
                row-remove column (issue #42, see components/table/remove.py)
                - `(row: dict) -> str | None`, called with one row to remove;
                return an error message to abort, or None on success. Table
                has no idea what a remove actually does server-side; on
                success it just drops that row from its own rendered data.
            on_remove_rows (callable, optional): the bulk-remove counterpart
                - `(rows: list[dict]) -> str | None`, called with every
                currently-selected row when the header's remove button is
                used to delete them all in one action. Either callback alone
                is enough to opt into the remove column; both are normally
                supplied together.
        """
        self.page = page
        self.storage: Storage = page.data["storage"]
        self.parent = parent  # ModulePage
        self.name = name
        self.fields = fields

        self.module = parent.module
        self.screen = parent.screen
        self.edit_screen = edit_screen
        self.custom_param = custom_param or {}

        self.is_inside_form = is_inside_form
        self.fill_available_space = fill_available_space

        # Opt-in remove column (issue #42) - a synthetic trailing field is
        # appended to `self.fields` so no caller ever hand-authors it; see
        # components/table/remove.py's module docstring.
        self.remove: TableRemove | None = None
        if on_remove_row is not None or on_remove_rows is not None:
            self.remove = TableRemove(
                page, self, on_remove_row=on_remove_row, on_remove_rows=on_remove_rows
            )
            self.fields = [
                *self.fields,
                {"name": "_remove", "label": "", "type": "remove", "filter": False},
            ]

        self.columns: TableColumns = TableColumns(page, self.fields)
        self.columns.remove = self.remove
        # Lets TableColumns tell whether it's still the live instance for
        # the current screen or a leftover from a previously-visited one
        # whose client-side gesture widgets are still firing events - see
        # TableColumns._is_live().
        self.columns.owner = self
        self.rows: TableRows = TableRows(page, self.columns, parent=self)
        # Lets TableColumns request a full header/body/rows rebuild after every
        # resize step (drag tick or double-tap reset) - see
        # TableColumns.on_resize_commit's docstring for why a rebuild is needed
        # at all (Flutter's DataTable only ever grows a column to fit a
        # wider child, never shrinks it back down from a live property
        # patch alone).
        self.columns.on_resize_commit = self._handle_resize_commit
        # Lets TableColumns request a data re-fetch (with new sort-fields query
        # params) after a header click cycles a sortable column's state -
        # see TableColumns.on_sort()/serialize_sort().
        self.columns.on_sort_change = self._handle_sort_change
        # Lets TableColumns forward a generic "checkbox"-type column's
        # header check-all/uncheck-all click (issue #46) into a bulk update
        # of every currently-rendered row's checkbox cell.
        self.columns.on_checkbox_header_click = self._handle_checkbox_header_click

        self.limit = limit
        self.page_number = 1  # Current page
        self.total_pages = 1  # Total pages from API
        self.total_rows = 0  # Total rows from API

        self.filter = ""
        self.filter = self.storage.table_search.get(self.module, self.screen, self.name)
        self.table_search_bar = TableSearchBar(
            page=page,
            parent=self,
            on_filter_change=self.on_filter_change,
            on_submit=self.on_submit,
            initial_value=self.filter,
        )
        # Every data table gets the download menu for free - see AGENTS.md's
        # "Table export convention". Reads self.module/self.name/self.filter/
        # self.columns/self.custom_param at click time, not build time.
        # Input-mode tables (is_inside_form, e.g. stock_out item_new's
        # per-location qty-entry table) are an entry widget, not a dataset -
        # no menu, and no C_{module}/export_{name} endpoint exists for them.
        self.export_menu = TableMenu(page=page, parent=self)
        # Per-column `{field}-filter` row (issue #10) - config-driven, one
        # ft.TextField per field marked "filterable": True; collapsed by
        # default, toggled via a toolbar button only shown when at least
        # one field opts in. See components/table/filter.py.
        self.filter_row = TableFilter(
            page=page,
            parent=self,
            fields=self.fields,
            columns=self.columns,
            on_apply=self._handle_filter_apply,
        )
        toolbar_controls = [self.table_search_bar.build()]
        self.toolbar: TableToolbar | None = TableToolbar(
            page=page, parent=self, controls=toolbar_controls
        )
        if self.filter_row.has_filters():
            self.toolbar.add_filter_button(callback=self._toggle_filter_row)
        self.header: TableHeader | None = None
        self.body: TableBody | None = None
        # Sticky footer (issue #30) - row-count message + lazy-load <->
        # pagination toggle. Not built for is_inside_form tables (entry-mode
        # grids like stock_out/item_new's per-location qty-entry table): those
        # aren't a real dataset a user pages through, and never call
        # get_data() at construction, so a "Record X of Y" message would be
        # meaningless there.
        self.footer: TableFooter | None = (
            TableFooter(page=page, parent=self) if not is_inside_form else None
        )
        self.is_loading_more = False

        self.table_container: ft.Container | None = None
        self.data: list = []
        self.endpoint = (
            endpoint if endpoint is not None else f"C_{self.module}/get_{self.name}"
        )

        if "active_tables" not in page.data:
            page.data["active_tables"] = []
        page.data["active_tables"].append(self)

        if not is_inside_form:
            self.get_data()

    def build(
        self,
        padding: ft.PaddingValue = ft.Padding.symmetric(
            horizontal=TABLE_OUTER_HORIZONTAL_PADDING
        ),
    ):
        # Every module's index.py calls Table.build() with no override, so
        # this default is the app-wide table padding - small horizontal
        # breathing room instead of sitting flush against the screen edge.
        # Must match TABLE_OUTER_HORIZONTAL_PADDING, which
        # Columns.get_usable_width() subtracts from its column-width budget
        # - a caller passing a different padding value here would silently
        # desync the two and reintroduce the off-screen-column overflow bug.
        self.header = TableHeader(page=self.page, columns=self.columns)
        self.body = TableBody(
            page=self.page,
            columns=self.columns,
            rows=self.rows,
            on_scroll_end=self._handle_scroll_end,
        )

        # Build controls list, filtering out None values
        controls = []
        toolbar_control = self._build_toolbar_with_filter_row()
        if toolbar_control:
            controls.append(toolbar_control)

        if self.header:
            header_control = self._build_header_with_resize_overlay()
            if header_control:
                controls.append(header_control)

        if self.body:
            body_control = self.body.build()
            if body_control:
                controls.append(body_control)

        # Always appended last (index 3, after toolbar/header/body) - purely
        # additive, so the existing hardcoded col.controls[1]/[2] header/body
        # indices used elsewhere in this file are never shifted.
        if self.footer:
            controls.append(self.footer.build())

        self.table_container = ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=0,
                expand=self.fill_available_space,
            ),
            expand=self.fill_available_space,
            padding=padding,
        )

        # If we have pending data (from form load), render it now
        # Just load the columns/rows without calling update() since not on page yet
        if self.data and len(self.data) > 0:
            self.columns.load(self.data)
            self.rows.load(self.data, append=False)
            self.filter_row.reposition()
            # Rebuild the header and body with the loaded data
            if self.header and self.body:
                if (
                    isinstance(self.table_container.content.controls, list)
                    and len(self.table_container.content.controls) >= 2
                ):
                    # Replace header and body in the controls list
                    if self.toolbar:
                        self.table_container.content.controls[1] = (
                            self._build_header_with_resize_overlay()
                        )
                        self.table_container.content.controls[2] = self.body.build()
                    else:
                        self.table_container.content.controls[0] = (
                            self._build_header_with_resize_overlay()
                        )
                        self.table_container.content.controls[1] = self.body.build()

        return self.table_container

    def _build_toolbar_with_filter_row(self):
        """The toolbar, plus the collapsible filter row stacked directly
        beneath it when at least one field is filterable - folded into the
        SAME `controls` list slot the toolbar alone used to occupy (index
        0), not a new slot of its own. `Table.load()`/`_handle_resize_commit()`/
        `_handle_sort_change()` all hardcode `col.controls[1]`/`[2]` as
        header/body; inserting a control here would shift those indices and
        silently corrupt every one of those call sites. The footer (issue
        #30) avoids this the other way - it's appended as a brand new,
        always-last slot (index 3) instead of folded into an existing one,
        so `[1]`/`[2]` stay exactly where every other call site expects."""
        toolbar_control = self.toolbar.build() if self.toolbar else None
        if not self.filter_row.has_filters():
            return toolbar_control
        filter_control = self.filter_row.build()
        if toolbar_control is None:
            return filter_control
        return ft.Column(controls=[toolbar_control, filter_control], spacing=0)

    def _toggle_filter_row(self, e):
        self.filter_row.toggle()

    def _handle_filter_apply(self):
        self.page_number = 1
        self.get_data()

    def _build_header_with_resize_overlay(self):
        """TableHeader.build()'s DataTable, wrapped in a Stack with the
        resize-handle overlay (TableColumns.get_resize_overlay()) on top.

        Every caller that rebuilds the header (here and
        _handle_resize_commit()) must go through this, not
        `self.header.build()` directly - otherwise a rebuild silently
        drops the overlay from the tree, and the next drag has nothing to
        grab."""
        header_control = self.header.build() if self.header else None
        if header_control is None:
            return None
        # Resize handles (cached, gesture-identity-preserving) plus any
        # by-row radio group spanning-header labels (issue #45, rebuilt
        # fresh every call - see get_radio_group_overlay()'s docstring for
        # why it doesn't need the same caching the handles do).
        overlay = self.columns.get_resize_overlay() + self.columns.get_radio_group_overlay()
        return ft.Stack([header_control, *overlay]) if overlay else header_control

    def _handle_scroll_end(self):
        """Handle scroll to bottom - load next page"""
        print(
            f"Scroll end handler called - page: {self.page_number}/{self.total_pages}, loading: {self.is_loading_more}"
        )

        # Infinite-scroll-load-more is the lazy-load mode's own behavior -
        # once the footer's toggle (issue #30) switches to pagination mode,
        # paging happens only via its buttons, not by scrolling further.
        if self.footer is not None and self.footer.mode != MODE_LAZY:
            return

        if self.is_loading_more or self.page_number >= self.total_pages:
            print("Skipping load - already loading or last page reached")
            return

        print(f"Loading page {self.page_number + 1}...")
        self.is_loading_more = True
        self.page_number += 1
        self.get_data(page_no=self.page_number, append=True)
        self.is_loading_more = False

    def _should_eagerly_load_more(self) -> bool:
        """Whether the rows loaded so far probably don't fill the visible
        viewport yet, even though more pages remain on the server - see
        the module-level comment on `_ESTIMATED_CHROME_HEIGHT`/
        `_MAX_ROW_HEIGHT` for why this has to be a page-height estimate
        rather than reacting to a scroll event (there may never be one).
        Mirrors `_handle_scroll_end`'s own "only in lazy mode" guard -
        pagination mode pages via explicit buttons only, and a table with
        no footer at all (`is_inside_form`) isn't a real dataset the user
        scrolls through."""
        if self.footer is None or self.footer.mode != MODE_LAZY:
            return False
        if self.page_number >= self.total_pages:
            return False
        page_height = getattr(self.page, "height", None) or 0
        if page_height <= 0:
            return False
        available = page_height - _ESTIMATED_CHROME_HEIGHT
        if available <= 0:
            return False
        rows_needed_to_fill = available / _MAX_ROW_HEIGHT
        return len(self.data) < rows_needed_to_fill

    def get_data(self, page_no: int = 1, offset: int = 0, append: bool = False):
        if not append:
            self.data = []
        client = HttpClient(self.page)
        param = f"table-keyword-filter={self.filter}" if self.filter else ""
        param = param + f"&limit={self.limit}&page={page_no}&offset={offset}"
        for key, value in self.custom_param.items():
            param = param + f"&{key}={value}"
        param = param + self.columns.serialize_sort()
        param = param + self.filter_row.serialize()
        response = client.get(f"{self.endpoint}?{param}" if param else self.endpoint)
        if isinstance(response, dict) and "error" in response:
            print(f"Error fetching data: {response.get('error')}")
            self.parent.view.show_error(f"Failed to load data: {response.get('error')}")
            return

        if isinstance(response, list):
            # Extract pagination metadata from first row, if any - an empty
            # result set (a genuinely empty table, e.g. a freshly seeded
            # module with zero records) is a valid response, not an error.
            if response:
                first_row = response[0]
                self.total_pages = first_row.get("db_total_page", 1)
                self.total_rows = first_row.get("db_num_rows", len(response))
            else:
                self.total_pages = 1
                self.total_rows = 0

            self.data = self.data + response if append else response
            if not append and self.remove is not None:
                # A genuine new server fetch (search/sort/filter/page nav)
                # invalidates whatever was selected against the previous
                # result set - reset here, not inside TableRows.load(),
                # since that method also runs for TableRemove's OWN local
                # re-renders (mode toggle, row-select toggle, post-removal
                # refresh via Table.load()) - resetting there would wipe
                # the very mode/selection state those re-renders exist to
                # display, which is exactly why the header button appeared
                # to do nothing (issue #42 follow-up fix).
                self.remove.reset_for_reload()
            self.load(response, append=append)
            if self._should_eagerly_load_more():
                self._handle_scroll_end()
        else:
            print(f"Unexpected response format: {response}")

    def load(self, data: list, append: bool = False, rescale: bool = False) -> None:
        # Show loading indicator
        if self.body:
            if not self.is_inside_form:
                self.body.show_loading()

        # Recalculate column widths and rebuild rows. `rescale` (issue #48)
        # is only ever True from on_page_resize() below - see
        # TableColumns.load()'s own docstring for what it changes.
        self.columns.load(data, rescale=rescale)
        self.rows.load(data, append=append)
        # Keep each filter field aligned with its column - a live width
        # patch on the same mounted Containers (issue #20), safe to call on
        # every keystroke same as the comment below explains for the
        # toolbar/header/body themselves: it never rebuilds the TextField
        # instances, so it can't drop focus the way a full rebuild would.
        self.filter_row.reposition()

        # If the table has already been built (header/body DataTables exist inside
        # self.table_container), replace the DataTable controls so the new
        # DataColumn/DataRow objects (with fixed-width Containers) are used.
        # Rebuilding the DataTable controls ensures Flet lays out cells with the
        # newly-applied container widths.
        if self.table_container and hasattr(self.table_container, "content"):
            col = self.table_container.content  # ft.Column
            # Recreate header and body DataTable widgets using the header/body
            # builders which read from `self.columns` and `self.rows`.
            new_header = None
            new_body = None
            if self.header:
                # keep header.columns reference (already set on init)
                new_header = self._build_header_with_resize_overlay()
            # An append (lazy-load-more) patches the ALREADY-MOUNTED
            # scrollable Column/DataTable in place (TableBody.update())
            # instead of swapping in a brand new one - a freshly built
            # ft.Column always starts the client at scroll offset 0, which
            # used to need a corrective scroll_to() jump right after
            # (restore_scroll_position()), visible as a "jump to top, then
            # snap back down" glitch (reported after issue #39's own fix).
            # Patching the same mounted Column/DataTable never resets its
            # scroll position in the first place, so there's nothing left
            # to correct - reassigning `.columns`/`.rows` to fresh built
            # objects and calling `.update()` still gets Flutter to
            # re-layout the DataTable's cells/widths correctly (the same
            # "swap in fresh objects rather than patch a nested property"
            # principle _handle_resize_commit's own docstring relies on for
            # shrinking a column - it just doesn't also require recreating
            # the *outer* scrollable wrapper). A fresh, non-append load
            # (filter/sort/page change) is a new result set and should
            # still reset to the top, which the full self.body.build()
            # naturally does by handing the client a brand new Column.
            if append and self.body and self.body.data_table is not None:
                self.body.update()
            elif self.body:
                new_body = self.body.build()

            new_footer = self.footer.build() if self.footer else None

            # Replace header/body/footer only - never rebuild the toolbar
            # here. The toolbar holds the search bar, and this method runs
            # on every keystroke (via on_filter_change -> get_data -> load);
            # rebuilding it would replace the focused TextField with a new
            # control, dropping browser focus after each character typed.
            if isinstance(col.controls, list) and len(col.controls) >= 3:
                if new_header is not None:
                    col.controls[1] = new_header
                if new_body is not None:
                    col.controls[2] = new_body
                if new_footer is not None and len(col.controls) >= 4:
                    col.controls[3] = new_footer
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

    def get_rows_with_input_values(self) -> list[dict]:
        """Each fetched row merged with the current value of any "input"-type
        column in that row (e.g. an editable "Qty Issue" column) - lets a
        caller read back what the user typed without wiring its own
        per-row TextField bookkeeping. Row order matches self.data."""
        input_values = self.rows.get_input_values()
        merged = []
        for i, record in enumerate(self.data):
            row = dict(record)
            if i < len(input_values):
                row.update(input_values[i])
            merged.append(row)
        return merged

    def _handle_resize_commit(self, recompute: bool) -> None:
        """Rebuild TableHeader/TableBody/TableRows after every column-resize step
        (TableColumns.on_resize_commit - a drag tick, or a double-tap reset).

        Flutter's `DataTable` grows to fit a wider child during normal
        layout, but doesn't shrink a column's rendered width back down
        just because a nested Container's width property patched smaller -
        only rebuilding the DataTable's `columns`/`rows` with fresh objects
        forces that (confirmed empirically: a live-only property-patch
        version showed both columns' widths being set correctly and
        symmetrically on every tick, yet only the growing one ever
        visibly resized). Doing this on every tick is safe now because the
        resize handles live in a separate overlay Stack
        (TableColumns.get_resize_overlay(), reattached by
        _build_header_with_resize_overlay() below) entirely outside the
        DataTable being rebuilt - an earlier version embedded the handle
        inside the header's own DataColumn label and broke the drag after
        the first tick by tearing down its own GestureDetector.

        `recompute=True` (double-tap reset) additionally recomputes
        `TableColumns.widths` from content via `TableColumns.load()` first, since a
        reset changes every column's width, not just one dragged pair.
        `recompute=False` (a drag tick) keeps the widths `handle_drag()`
        already tracked, just rebuilds to render them correctly.

        Mirrors Table.load()'s "replace the built header/body controls in
        place" approach rather than TableHeader.update()/TableBody.update() (both
        dead code - nothing in this codebase calls them - so untested):
        TableRows bakes each cell's pixel width in at TableRows.load() time, not read
        live from TableColumns.widths, so this needs that re-run too, not just
        TableColumns.rebuild().
        """
        if self.data:
            if recompute:
                self.columns.load(self.data)
            self.rows.load(self.data)

        # Widths are current by this point either way - handle_drag()
        # already mutated them directly before calling here (recompute=
        # False), or columns.load() just recomputed them above (recompute=
        # True) - keep each filter field aligned either way (issue #20).
        self.filter_row.reposition()

        if self.table_container and hasattr(self.table_container, "content"):
            col = self.table_container.content  # ft.Column
            new_header = (
                self._build_header_with_resize_overlay() if self.header else None
            )
            new_body = self.body.build() if self.body else None
            # Column widths don't affect the footer's own layout, but keep
            # it wired into the same rebuild-in-place site as header/body
            # (issue #30 AC) rather than leaving it a stale reference.
            new_footer = self.footer.build() if self.footer else None

            if isinstance(col.controls, list) and len(col.controls) >= 3:
                if new_header is not None:
                    col.controls[1] = new_header
                if new_body is not None:
                    col.controls[2] = new_body
                if new_footer is not None and len(col.controls) >= 4:
                    col.controls[3] = new_footer
                col.update()
                self.table_container.update()

    def _handle_sort_change(self) -> None:
        """A header click cycled a sortable column's state
        (TableTableColumns.on_sort()). Two things need to happen, same split as the
        senar reference: (1) instant icon feedback - TableColumns.on_sort()
        already rebuilt `self.columns.columns` synchronously, so just
        swap the header control in place, same as
        _handle_resize_commit()'s header-only refresh; (2) the actual
        re-sort, which is server-side and needs a round trip - re-fetch
        with TableColumns.serialize_sort()'s new sort-fields params.
        Deliberately does *not* reset to page 1 (get_data() keeps
        self.page_number as-is) - matches y.form.js's serializePagination/
        listenerHeaderTable, where only a page-*size* change resets
        pagination, not a sort change.
        """
        if self.table_container and hasattr(self.table_container, "content"):
            col = self.table_container.content
            new_header = (
                self._build_header_with_resize_overlay() if self.header else None
            )
            if (
                new_header is not None
                and isinstance(col.controls, list)
                and len(col.controls) >= 2
            ):
                col.controls[1] = new_header
                col.update()

        self.get_data(page_no=self.page_number, offset=0)

    def _handle_checkbox_header_click(self, field_name: str, value: bool) -> None:
        """Check-all/uncheck-all header buttons for a generic "checkbox"-
        type column (issue #46, `components/table/columns.py`'s
        `TableColumns._build_checkbox_header()`) - bulk-sets every
        currently loaded row's checkbox cell in place; no data re-fetch or
        full `Table.load()` re-render needed."""
        self.rows.set_all_checkbox(field_name, value)

    def _handle_footer_mode_change(self, mode: str) -> None:
        """`TableFooter`'s toggle switched between lazy-load and pagination
        mode. Both directions restart at page 1 with a full (non-append)
        refetch - simplest way to reconcile lazy-load's accumulated
        multi-page `self.data` with pagination's single-page view, and
        matches the pre-existing "only a page-size/mode change resets to
        page 1" convention `_handle_sort_change`'s own docstring documents
        for sort. Mode state itself lives only on `self.footer.mode` - never
        persisted, resets whenever this Table is torn down and rebuilt."""
        self.page_number = 1
        self.get_data(page_no=1, offset=0, append=False)

    def _handle_footer_page_change(self, page_no: int) -> None:
        """A numbered/first/prev/next/last pagination button was clicked.
        Pagination mode always replaces the current page's data (append=
        False) - unlike lazy-load's infinite-scroll accumulation, each page
        click shows exactly one page's worth of rows."""
        self.page_number = page_no
        self.get_data(page_no=page_no, offset=(page_no - 1) * self.limit, append=False)

    def _handle_footer_limit_change(self, new_limit: int) -> None:
        """The footer's rows-per-page input committed a new value (Enter or
        blur) - matches `y.form.js`'s `#handleSetPageLimit`: resets to page
        1, same as a keyword search reset (`on_filter_change`)."""
        self.limit = new_limit
        self.page_number = 1
        self.get_data(page_no=1, offset=0, append=False)

    def on_page_resize(self) -> None:
        """Handle page resize events - called from main page resize handler.

        `rescale=True` (issue #48) - before this, a table whose columns had
        ever been manually drag-resized permanently ignored window resize
        from that point on, since TableColumns.load()'s manually_resized
        branch kept the frozen absolute-pixel widths on every reload
        including a resize one. Now a resize reload rescales those widths
        to fit the new screen width instead - see
        TableColumns._rescale_manual_widths()."""
        print(f"Table {self.name} resize triggered")
        if self.data:
            # Reload the table with new widths
            self.load(self.data, rescale=True)

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
