import flet as ft

# Bucket for the 4th+ auto-positioned field (issue #81) - shared with
# components/list/tiles.py, which renders it as the M3 "Expand & collapse"
# section rather than a fixed leading/title/subtitle/trailing slot.
OVERFLOW_POSITION = "extra"


class Layout:
    def __init__(self, page: ft.Page, fields: list):
        self.page = page
        self.fields = fields
        self.layout: dict = {}
        self.index = []
        self.record_key = "id"
        self.get()

    # Auto-assignment order for any field that doesn't set its own
    # "position" (issue #81) - 1st unhidden field with no explicit
    # position becomes the leading slot, 2nd becomes title, 3rd becomes
    # subtitle, every one after that falls into "extra" (the M3
    # expand/collapse section - see components/list/tiles.py). A field
    # that DOES set "position" explicitly is placed exactly there,
    # unaffected by this counter - existing configs (stock_in/index.py)
    # keep working unchanged, since every one of its fields already sets
    # "position" itself.
    _AUTO_POSITION_ORDER = ["leading", "title", "subtitle"]
    _OVERFLOW_POSITION = OVERFLOW_POSITION

    def get(self):
        self.layout = {
            "leading": {},
            "title": {},
            "subtitle": {},
            "trailing": {},
            self._OVERFLOW_POSITION: {},
        }
        auto_position_count = 0
        for field in self.fields:
            field_name = field.get("name")
            if field_name is None:
                continue

            field_is_key = field.get("key", False)
            if field_is_key:
                self.record_key = field_name

            field_type = field.get("type", "text")
            if field_type == "hidden":
                continue

            field_position = field.get("position", None)
            if field_position is None:
                if auto_position_count < len(self._AUTO_POSITION_ORDER):
                    field_position = self._AUTO_POSITION_ORDER[auto_position_count]
                else:
                    field_position = self._OVERFLOW_POSITION
                auto_position_count += 1

            # Ensure position exists in layout
            if field_position not in self.layout:
                self.layout[field_position] = {}

            field_label = field.get("label")
            field_icon = field.get("icon")

            # Wrap icon in Icon control if it's an Icons enum
            field_icon_control = None
            if field_icon is not None:
                if isinstance(field_icon, str) or hasattr(field_icon, 'value'):
                    # It's an Icons enum or string
                    field_icon_control = ft.Icon(field_icon)
                else:
                    # It's already a control
                    field_icon_control = field_icon

            field_row = int(field.get("row", 0))
            # Ensure row exists in position
            if field_row not in self.layout[field_position]:
                self.layout[field_position][field_row] = []

            # `label` is NOT rendered as its own visible text line here
            # (issue #65 follow-up, per direct user feedback) - a List
            # tile is dense enough without a "Supplier"/"Description"
            # caption above every value, and the label already has a
            # legitimate second job: `Table` reads this exact same field's
            # `"label"` for its own column header text (both components
            # share one `fields` list via issue #56's `ViewToggle`), so it
            # can't simply be deleted from the field configs. Instead the
            # raw text is handed to `Tiles.load()` as `label_text`, which
            # wraps the tile's *value* Text in an `ft.Tooltip` using it -
            # the label surfaces on hover, not as permanent on-screen
            # chrome. `icon_control` (unaffected) still renders visibly
            # as a prefix, same as before.
            field_data = {
                "name": field_name,
                "label_text": field_label,
                "icon_control": field_icon_control,
                "col": field.get("col"),
                "format": field.get("format"),
                # Per-field drill-down navigation (issue #81), mirroring
                # Table's own link_key_field/link_screen mechanism
                # (stock_browse/index.py's independent material_id/
                # location_id links on different cells of the same row -
                # the reason List had no navigation equivalent at all
                # until now, unlike the record-wide `next_page` tap).
                "link_key_field": field.get("link_key_field"),
                "link_screen": field.get("link_screen"),
            }
            self.layout[field_position][field_row].append(
                field_data
            )
            self.index.append(field_name)

        # Sort each position's rows by row number
        for position in ["leading", "title", "subtitle", "trailing", self._OVERFLOW_POSITION]:
            if position in self.layout and isinstance(self.layout[position], dict):
                # Convert to sorted list of (row_num, fields) tuples, then back to dict
                sorted_rows = sorted(
                    self.layout[position].items(), key=lambda x: int(x[0]))
                self.layout[position] = dict(sorted_rows)
