import flet as ft

from components.list.layout import Layout
from utils.formatting import format_date, format_datetime, format_number, format_time

# Same "format" dispatch as components/table/rows.py's own _FORMATTERS -
# a "date"/"time"/"datetime"/"number" field value arrives over the wire as a
# raw string (e.g. an ISO date), so a List tile needs the same formatting
# a Table cell already gets, or dates/numbers render unformatted.
_FORMATTERS = {
    "number": format_number,
    "date": format_date,
    "time": format_time,
    "datetime": format_datetime,
}

# Position-based zebra stripe (issue #65, porting Table's own issue #57) -
# derived fresh from each tile's index in the CURRENT render pass (the
# `row` counter below), never stored on the record, so it's automatically
# correct after any full rebuild (search/filter/sort) with no separate
# bookkeeping. Same semantic M3 tokens Table's own TableRows.load() uses,
# for visual consistency between the two components.
_TILE_COLOR_EVEN = ft.Colors.SURFACE
_TILE_COLOR_ODD = ft.Colors.SURFACE_CONTAINER_LOW


class Tiles:
    def __init__(
        self,
        page: ft.Page,
        parent,
        layout: Layout,
        title=None,
        subtitle=None,
        leading=None,
        trailing=None,
        next_page="edit",
    ):
        self.page = page
        self.layout = layout
        self.parent = parent
        self.tiles = []
        self.leading = leading
        self.title = title
        self.subtitle = subtitle
        self.trailing = trailing
        self.next_page = next_page
        self.leading_width = leading.get("width", 80) if leading is not None else 80
        self.trailing_width = trailing.get("width", 80) if trailing is not None else 80
        self.index = []

    def build(self) -> list:
        return self.tiles

    def load(self, data: list, append: bool = False):
        """Build tiles from data (server handles pagination)

        Args:
            data: List of records to display
            append: If True, append to existing tiles. If False, replace all tiles.
        """
        if not append:
            self.tiles = []
            self.index = []

        # Continues from the last already-rendered tile's index on a
        # lazy-load append (not 0), matching TableRows.load()'s own
        # counter exactly - the stripe pattern doesn't reset/clash at the
        # page boundary. Deliberately named `tile_index`, NOT `row` - this
        # loop body already uses `row` as the per-position row-group index
        # (`for row, row_data in position_data.items()`, Layout's own
        # "row": N grouping within one leading/title/subtitle/trailing
        # slot) - a first attempt named this counter `row` too and got
        # silently shadowed by that inner loop on every iteration, which
        # is why the stripe never appeared (looked identical to a broken
        # ft.ListTile.bgcolor problem at first, until tracing the actual
        # value showed the counter was never advancing per-tile at all).
        tile_index = len(self.tiles) if append else 0

        key_field = self.layout.record_key
        for record in data:
            layout = self.layout.layout
            tile_content = {
                "leading": None,
                "title": None,
                "subtitle": None,
                "trailing": None,
            }

            for position, position_data in layout.items():
                position_content = []
                for row, row_data in position_data.items():
                    row_content = []
                    for field_data in row_data:
                        name = field_data.get("name")
                        col = field_data.get("col")
                        label_text = field_data.get("label_text")
                        icon_control = field_data.get("icon_control")
                        value = record.get(name, "")
                        formatter = _FORMATTERS.get(field_data.get("format"))
                        display_value = formatter(value) if formatter and value not in (None, "") else value

                        # The label is a hover tooltip on the value, not a
                        # permanent visible caption line (issue #65
                        # follow-up) - see layout.py's docstring for why
                        # (the same field's "label" is still needed
                        # verbatim by Table's own column header, sharing
                        # one fields list via issue #56's ViewToggle).
                        value_text = ft.Text(
                            str(display_value),
                            overflow=ft.TextOverflow.ELLIPSIS,
                            # `tooltip` is a plain property every Control
                            # has (not a separate wrapping widget) - no
                            # `ft.Tooltip(...)` class exists in this Flet
                            # version.
                            tooltip=label_text if label_text else None,
                        )

                        # Build controls list, filtering out None
                        controls_list = []
                        if icon_control is not None:
                            controls_list.append(icon_control)
                        controls_list.append(value_text)

                        # Wrap text in container with fixed width if available
                        content = ft.Column(controls=controls_list, col=col)

                        row_content.append(content)
                    position_content.append(
                        ft.ResponsiveRow(
                            controls=row_content,
                        )
                    )

                # Wrap position content in Container with constraints
                if position_content:
                    if position == "leading":
                        tile_content[position] = ft.Container(
                            content=ft.Column(controls=position_content, spacing=2),
                            width=self.leading_width,
                            alignment=self.leading.get("alignment")
                            if self.leading is not None
                            else ft.Alignment.CENTER_LEFT,
                        )
                    elif position == "trailing":
                        tile_content[position] = ft.Container(
                            content=ft.Column(controls=position_content, spacing=2),
                            width=self.trailing_width,
                            alignment=self.trailing.get("alignment")
                            if self.trailing is not None
                            else ft.Alignment.CENTER_RIGHT,
                        )
                    elif position == "title":
                        tile_content[position] = ft.Column(
                            controls=position_content,
                            spacing=2,
                            expand=True,
                            alignment=self.title.get(
                                "alignment", ft.Alignment.BOTTOM_CENTER
                            )
                            if self.title is not None
                            else ft.Alignment.BOTTOM_CENTER,
                        )
                    elif position == "subtitle":
                        tile_content[position] = ft.Column(
                            controls=position_content,
                            spacing=2,
                            expand=True,
                            alignment=self.subtitle.get(
                                "alignment", ft.Alignment.TOP_CENTER
                            )
                            if self.subtitle is not None
                            else ft.Alignment.TOP_CENTER,
                        )

            # create on_tap handler to navigate to edit page with key
            key_value = record.get(key_field) if key_field is not None else None
            on_tap_handler = None
            if key_field is not None:
                module = None
                if hasattr(self, "parent") and getattr(self.parent, "module", None):
                    module = getattr(self.parent, "module")
                elif hasattr(self.page, "data") and isinstance(self.page.data, dict):
                    module = self.page.data.get("module")

                if module:

                    def _make_tap(kf, kv, mod):
                        # Use path parameter for id: /modules/<module>/edit/<id>
                        if kv is None:
                            return lambda e: None
                        return lambda e: self.page.run_task(
                            self.page.push_route,
                            f"/modules/{mod}/{self.next_page}/{kv}",
                        )

                    on_tap_handler = _make_tap(key_field, key_value, module)

            list_tile = ft.ListTile(
                title=tile_content.get("title"),
                subtitle=tile_content.get("subtitle"),
                subtitle_text_style=self.subtitle.get("subtitle_text_style")
                if self.subtitle is not None
                else None,
                leading=tile_content.get("leading"),
                trailing=tile_content.get("trailing"),
                on_click=on_tap_handler if on_tap_handler is not None else None,
            )
            # `ft.ListTile` itself paints an opaque background regardless
            # of its own `bgcolor` property (confirmed live - setting
            # `ListTile(bgcolor=...)` directly, and separately wrapping it
            # in a padded Container with its own bgcolor, both failed to
            # show any color at all) - so the zebra color is set on this
            # wrapping Container instead, which reliably renders bgcolor
            # everywhere else in this codebase (e.g. issue #53's flush
            # table-cell TextField wrapper).
            self.tiles.append(
                ft.Container(
                    content=list_tile,
                    bgcolor=_TILE_COLOR_EVEN if tile_index % 2 == 0 else _TILE_COLOR_ODD,
                )
            )
            tile_index += 1
