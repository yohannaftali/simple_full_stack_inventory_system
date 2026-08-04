"""Lets a screen offer both `List` and `Table` renderings of the same
dataset, switched via one toolbar button (issue #56).

Design (documented per the issue's own acceptance criteria): `List` and
`Table` share an identical backend contract (`table_query.py`'s
pagination/filter/sort wire format - see AGENTS.md) and, in practice, an
identical `fields` list works for both unmodified - each component only
reads the keys it understands (e.g. `List` reads `"position"`, `Table`
ignores it; `Table` reads `"col"`, `List` ignores it), so `ViewToggle`
passes the SAME `fields` list to whichever component it builds rather than
requiring two parallel field lists.

Session-only mode state, never persisted - same convention as
`TableFooter`'s own lazy-load/pagination toggle (`components/table/footer.py`):
resets whenever the owning screen is torn down and rebuilt. Only the
initially active view is constructed up front; the other is built lazily on
first switch, so toggling never causes a doubled initial fetch (both `List`
and `Table` call `get_data()` from their own `__init__` when not
`is_inside_form`).

**Filter/search text carries across the switch for free**: both components
persist their free-text search through the same
`storage.table_search` key, keyed on `(module, screen, name)` - `ViewToggle`
always constructs both with the same `name`, so switching views picks up
the just-typed search term automatically.

**Sort order and pagination position do NOT carry across the switch** - this
is a deliberate, documented scope limit (per issue #56's acceptance
criteria, "call out explicitly if out of scope"): `TableColumns.sort_order`/
`ListFilter.sort_order` and each component's own `page_number` are
per-instance state with no shared persistence layer the way search text has
(`table_search` repository) - reconciling them would need a new shared
sort/pagination store this issue didn't ask for. Switching views always
resets to page 1 with whatever sort the freshly-built component starts
with (none).
"""

import flet as ft

from components.list.list import List
from components.table.table import Table

MODE_LIST = "list"
MODE_TABLE = "table"


class ViewToggle:
    def __init__(
        self,
        page: ft.Page,
        parent,
        name: str,
        fields: list,
        mode: str = MODE_LIST,
        list_kwargs: dict | None = None,
        table_kwargs: dict | None = None,
    ):
        self.page = page
        self.parent = parent
        self.name = name
        self.fields = fields
        self.mode = mode
        self.list_kwargs = list_kwargs or {}
        self.table_kwargs = table_kwargs or {}

        self.list_view: List | None = None
        self.table_view: Table | None = None
        self.container: ft.Container | None = None

        self._new_button_callback = None
        self._new_button_kwargs: dict = {}

        # Structured filters (issue #81) - unlike free-text search
        # (already carried across a switch via the shared
        # storage.table_search key) or sort/pagination (a deliberate,
        # documented scope limit - see this file's own docstring),
        # `custom_param` is set dynamically, after construction, by a
        # screen with its own filter controls (e.g. usage_report/
        # purchase_report's date-range "Apply Filters" button,
        # stock_browse's stock_by_material/stock_by_location screens).
        # Without tracking it here, lazily building the other view on
        # first toggle would silently drop whatever filter was applied,
        # since a freshly-constructed List/Table always starts with
        # custom_param=None.
        self._custom_param: dict | None = None

        self._build_active()

    @property
    def active(self):
        return self.list_view if self.mode == MODE_LIST else self.table_view

    def apply_custom_param(self, custom_param: dict, reset_page: bool = True) -> None:
        """Screen-level filter controls should call this instead of
        setting `toggle.active.custom_param` directly, so the filter
        survives a later List/Table switch."""
        self._custom_param = custom_param
        self.active.custom_param = custom_param
        if reset_page:
            self.active.page_number = 1
        self.active.get_data()

    def _build_active(self) -> None:
        # Toolbar buttons (toggle + "Add New") are only wired up the FIRST
        # time a given view is built - re-entering an already-built view
        # (list -> table -> list) must not re-append them to that view's
        # own toolbar, which is a persistent object reused across every
        # re-render of that view (only List/Table.build() is called again,
        # never List/Table.__init__), or every toggle back and forth would
        # accumulate one more duplicate button.
        newly_built = False
        if self.mode == MODE_LIST and self.list_view is None:
            self.list_view = List(self.page, self.parent, self.name, self.fields, **self.list_kwargs)
            newly_built = True
        elif self.mode == MODE_TABLE and self.table_view is None:
            self.table_view = Table(self.page, self.parent, self.name, self.fields, **self.table_kwargs)
            newly_built = True
        if newly_built:
            self._apply_toggle_button()
            self._apply_new_button()
            if self._custom_param is not None:
                self.active.custom_param = self._custom_param
                self.active.get_data()

    def _other_mode(self) -> str:
        return MODE_TABLE if self.mode == MODE_LIST else MODE_LIST

    def _apply_toggle_button(self) -> None:
        # A constant icon/tooltip (not "switch to X") is deliberate: this
        # button is only ever wired up once per view (see the newly_built
        # guard in _build_active()) - its own toolbar.add_button() has no
        # way to hand back the built control for a later icon/tooltip
        # mutation, so it can't reflect "the OTHER mode" live across
        # repeated toggles without extra bookkeeping this issue didn't ask
        # for. A neutral swap icon on both of the (up to two) buttons reads
        # correctly regardless of which one is currently visible.
        toolbar = getattr(self.active, "toolbar", None)
        if toolbar is None:
            return
        toolbar.add_button(
            position="left",
            callback=self._on_toggle_click,
            icon=ft.Icons.SWAP_HORIZ,
            tooltip="Switch Table / List view",
        )

    def add_new_button(self, callback, **kwargs) -> None:
        """Mirrors Table/List's own `toolbar.add_new_button` - stored so it
        can be re-applied to whichever view gets lazily built on the first
        switch, since a freshly-constructed Table/List's toolbar starts
        with no buttons of its own."""
        self._new_button_callback = callback
        self._new_button_kwargs = kwargs
        self._apply_new_button()

    def _apply_new_button(self) -> None:
        if self._new_button_callback is None:
            return
        toolbar = getattr(self.active, "toolbar", None)
        if toolbar is None:
            return
        toolbar.add_new_button(self._new_button_callback, **self._new_button_kwargs)

    def build(self) -> ft.Container:
        self.container = ft.Container(content=self.active.build(), expand=True)
        return self.container

    def _on_toggle_click(self, e) -> None:
        self.mode = self._other_mode()
        self._build_active()
        if self.container is not None:
            self.container.content = self.active.build()
            try:
                self.container.update()
            except RuntimeError:
                pass
