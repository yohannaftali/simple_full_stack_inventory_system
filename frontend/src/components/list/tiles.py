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
                        label = field_data.get("label")
                        value = record.get(name, "")
                        formatter = _FORMATTERS.get(field_data.get("format"))
                        display_value = formatter(value) if formatter and value not in (None, "") else value

                        # Build controls list, filtering out None
                        controls_list = []
                        if label is not None:
                            controls_list.append(label)
                        controls_list.append(
                            ft.Text(str(display_value), overflow=ft.TextOverflow.ELLIPSIS)
                        )

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

            self.tiles.append(
                ft.ListTile(
                    title=tile_content.get("title"),
                    subtitle=tile_content.get("subtitle"),
                    subtitle_text_style=self.subtitle.get("subtitle_text_style")
                    if self.subtitle is not None
                    else None,
                    leading=tile_content.get("leading"),
                    trailing=tile_content.get("trailing"),
                    on_click=on_tap_handler if on_tap_handler is not None else None,
                )
            )
