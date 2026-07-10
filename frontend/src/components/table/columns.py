import flet as ft


class Columns:
    def __init__(self, page: ft.Page, fields: list):
        self.page = page
        self.fields = fields
        self.fields_by_name = {f.get("name"): f for f in fields if f.get("name") is not None}
        self.columns: list = []
        self.index = []
        self.widths: list[int] | None = None
        self.record_key = "id"
        self.parse_field(self.fields)

    def build(self) -> list:
        # Build and return a FRESH list of DataColumn objects each call.
        # This avoids shared-list aliasing between header/body consumers
        # while keeping `self.widths` as the source-of-truth for sizes.
        print("Columns.build (fresh)")
        print(self.widths)
        cols: list = []
        visible_idx = 0

        for field in self.fields:
            name = field.get("name")
            if name is None:
                continue
            field_type = field.get("type", "text")
            if field_type == "hidden":
                continue

            label = field.get("label")
            icon = field.get("icon")
            is_numeric = field.get("is_numeric") or field.get("format") == "number"

            text = ft.Text(label) if label is not None else None

            label_content = None
            if text is not None and icon is None:
                label_content = text
            elif text is not None and icon is not None:
                label_content = ft.Row([icon, text])
            elif text is None and icon is not None:
                label_content = icon

            # Apply width if available (use integer pixel values)
            if self.widths and visible_idx < len(self.widths):
                w = int(self.widths[visible_idx])
                label_content = ft.Container(
                    content=label_content,
                    width=w,
                    padding=5,
                )

            cols.append(
                ft.DataColumn(
                    label=label_content, numeric=is_numeric, on_sort=self.on_sort
                )
            )
            visible_idx += 1

        return cols

    def parse_field(self, fields) -> None:
        self.columns = []
        self.index = []

        for field in fields:
            field_name = field.get("name")
            if field_name is None:
                continue

            field_is_key = field.get("key", False)
            if field_is_key:
                self.record_key = field_name

            field_type = field.get("type", "text")
            if field_type == "hidden":
                continue

            field_label = field.get("label")
            field_icon = field.get("icon")

            text = ft.Text(field_label) if field_label is not None else None

            content = None
            if text is not None and field_icon is None:
                content = text
            elif text is not None and field_icon is not None:
                content = ft.Row([field_icon, text])
            elif text is None and field_icon is not None:
                content = field_icon

            self.columns.append(
                ft.DataColumn(label=content, numeric=False, on_sort=self.on_sort)
            )
            self.index.append(field_name)

    def on_sort(self, e) -> None:
        print(f"Sort column {e.column_index}, ascending: {e.ascending}")

    def rebuild(self) -> None:
        """Rebuild columns with new widths"""
        self.columns = []  # Reset before rebuilding
        visible_idx = 0
        for field in self.fields:
            name = field.get("name")
            if name is None:
                continue
            field_type = field.get("type", "text")
            if field_type == "hidden":
                continue

            label = field.get("label")
            icon = field.get("icon")
            is_numeric = field.get("is_numeric") or field.get("format") == "number"

            text = ft.Text(label) if label is not None else None

            label_content = None
            if text is not None and icon is None:
                label_content = text
            elif text is not None and icon is not None:
                label_content = ft.Row([icon, text])
            elif text is None and icon is not None:
                label_content = icon

            # Apply width if available (use integer pixel values)
            if self.widths and visible_idx < len(self.widths):
                w = int(self.widths[visible_idx])
                label_content = ft.Container(
                    content=label_content,
                    width=w,
                    padding=5,
                )

            self.columns.append(
                ft.DataColumn(
                    label=label_content, numeric=is_numeric, on_sort=self.on_sort
                )
            )
            visible_idx += 1

    def get_screen_width(self) -> int:
        # page.width is the actual rendered viewport width on web (and desktop);
        # page.window.width applies to desktop OS windows and is unreliable on
        # web - it was observed returning a small stale default (e.g. 400)
        # while page.width correctly reported the real browser width (e.g.
        # 1653), which made tables render far narrower than the page on web.
        # Prefer page.width whenever it's available; only fall back to
        # window.width (then a hardcoded default) if it isn't.
        if hasattr(self.page, "width") and self.page.width:
            print(f"page.width: {self.page.width}")
            return self.page.width

        if (
            hasattr(self.page, "window")
            and hasattr(self.page.window, "width")
            and self.page.window.width
        ):
            print(f"page.window_width: {self.page.window.width}")
            return self.page.window.width

        return 1200

    def get_usable_width(self, num_columns: int) -> int:
        """Calculate usable width for columns based on page/window size"""
        screen_width = self.get_screen_width()
        print(f"Screen width: {screen_width}")
        scrollbar_width = 10  # typical Windows scrollbar width
        horizontal_margin = 10
        column_spacing = 15
        total_spacing = (num_columns - 1) * column_spacing
        safety_buffer = horizontal_margin
        # subtract both left and right margins
        usable_width = (
            screen_width
            - scrollbar_width
            - (horizontal_margin * 2)
            - total_spacing
            - safety_buffer
        )
        print(f"Usable width: {usable_width}")
        return usable_width

    def load(self, data: list) -> None:
        """Calculate column widths based on content and available screen width"""
        min_width = 40
        num_columns = len(self.index)
        if num_columns == 0:
            return []

        usable_width = self.get_usable_width(num_columns)
        if num_columns == 1:
            return [usable_width]

        widths = self._get_widths(num_columns, usable_width, min_width, data)
        # ensure integer widths
        self.widths = [int(w) for w in widths]
        print("Columns.load: columns width")
        print(self.widths)
        self.rebuild()

    def _get_widths(self, num_columns, usable_width, min_width, data: list):
        content_widths, total_content_width = self._get_initial_widths(data)

        # Adjust widths proportionally if total exceeds usable width
        if total_content_width > usable_width:
            # Scale down proportionally
            prop = usable_width / total_content_width
            widths = [max(int(w * prop), min_width) for w in content_widths]

            # Recalculate total after applying min_width
            total_scaled = sum(widths)
            if total_scaled > usable_width:
                # Apply max constraints more aggressively
                excess = total_scaled - usable_width
                for i, width in enumerate(widths):
                    if excess <= 0:
                        break
                    reduction = min(width - min_width, excess)
                    widths[i] -= reduction
                    excess -= reduction
        else:
            # Use content widths as-is
            widths = content_widths
            total_width = sum(widths)
            # Distribute remaining space evenly if we have room
            if total_width < usable_width:
                extra_per_column = (usable_width - total_width) // num_columns
                widths = [w + extra_per_column for w in widths]

        return widths

    def _get_initial_widths(self, data: list) -> tuple[list[int], int]:
        # Calculate initial widths based on content
        content_widths: list[int] = []
        total_content_width: int = 0

        for i, field_name in enumerate(self.index):
            # Start with header label length
            field = next((f for f in self.fields if f.get("name") == field_name), {})
            header_label = field.get("label", field_name)
            max_length = len(str(header_label))

            # Check all data rows (sample first 20 for performance)
            for record in data[:20]:
                value = str(record.get(field_name, ""))
                max_length = max(max_length, len(value))

            # Convert character length to pixel width
            # Using average character width for typical UI fonts (7-9px at default size)
            # Plus padding for cell spacing (20px each side)
            char_width = 8  # Average width per character in pixels
            cell_padding = 40  # Left + right padding
            width = max_length * char_width + cell_padding
            content_widths.append(width)
            total_content_width += width

        return content_widths, total_content_width
