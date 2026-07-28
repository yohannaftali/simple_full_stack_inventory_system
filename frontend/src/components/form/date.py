import datetime

import flet as ft

from utils.formatting import format_date


class DateForm:
    """Date field backed by a calendar popup (ft.DatePicker).

    Renders as a read-only TextField (tap to open the picker, not typed
    directly) displaying "dd Mon yyyy" (house date format), while
    internally tracking the raw ISO "YYYY-MM-DD" value the backend's `date`
    Form fields expect/return in `self.value`. Because the displayed text
    and the submitted value differ, `components/form/form.py`'s
    `load()`/`serialize()` special-case any field present in `Form.date`
    (i.e. every `"type": "date"` field) to go through `set_value()`/
    `get_value()` here instead of reading/writing `TextField.value`
    directly like a plain input.
    """

    def __init__(self, page: ft.Page, parent, field: dict):
        self.page = page
        self.parent = parent
        self.name = field.get("name", "")
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Select {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 filled text field color roles - see components/form/input.py's
        # class docstring for the full spec-correction rationale (issue #53
        # follow-up). Fill/text are constant; only the label turns PRIMARY
        # on focus.
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_label_color = field.get("focused_label_color", ft.Colors.PRIMARY)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.filled = field.get("filled", True)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE_CONTAINER_HIGHEST)
        self.first_date = field.get("first_date", datetime.date(2000, 1, 1))
        self.last_date = field.get("last_date", datetime.date(2100, 12, 31))

        default = field.get("default")
        if default == "today":
            default = datetime.date.today().isoformat()
        self.value: str = default or ""  # raw ISO "YYYY-MM-DD" - the source of truth
        self.field: ft.TextField | None = None
        self.picker = ft.DatePicker(
            first_date=self.first_date,
            last_date=self.last_date,
            on_change=self._on_change,
        )

    def build(self) -> ft.TextField:
        prefix_icon = (
            ft.Icon(icon=self.icon, color=ft.Colors.ON_SURFACE_VARIANT)
            if self.icon is not None else None
        )
        self.field = ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            hint_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            value=format_date(self.value) if self.value else "",
            prefix_icon=prefix_icon,
            suffix_icon=ft.Icons.CALENDAR_MONTH,
            border_radius=10,
            border=ft.InputBorder.UNDERLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            # The whole field opens the picker (on_click below), so the
            # cursor should read as clickable everywhere over it, including
            # the trailing calendar icon - consistent with every other
            # trailing icon button in the app, which are real IconButtons
            # and get a pointer cursor for free. A plain `suffix_icon`
            # string like this one has no click handling/cursor of its own,
            # so it's set explicitly here instead.
            mouse_cursor=ft.MouseCursor.CLICK,
            autofocus=self.autofocus,
            text_size=self.value_size,
            read_only=True,
            color=self.value_color,
            content_padding=ft.Padding.only(left=12, right=12, top=8, bottom=8),
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            filled=self.filled,
            bgcolor=self.bgcolor,
            adaptive=True,
            expand=True,
            on_click=self._open_picker,
            on_focus=self._on_focus,
            on_blur=self._on_blur,
        )
        return self.field

    def _on_focus(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.focused_label_color)
        self._safe_update()

    def _on_blur(self, e=None) -> None:
        self.field.label_style = ft.TextStyle(size=self.label_size, color=self.label_color)
        self._safe_update()

    def get_value(self) -> str:
        """The raw ISO "YYYY-MM-DD" value, for Form.serialize()."""
        return self.value

    def set_value(self, iso_value: str) -> None:
        """Set from a backend ISO value (Form.load()), displaying it as
        "dd Mon yyyy" in the field."""
        self.value = iso_value or ""
        if self.field is not None:
            self.field.value = format_date(self.value) if self.value else ""

    def _open_picker(self, e):
        if self.value:
            try:
                self.picker.value = datetime.date.fromisoformat(self.value)
            except ValueError:
                pass
        # DatePicker is a DialogControl in this Flet version - it must be
        # shown via page.show_dialog() (which tracks it on page._dialogs and
        # wires its dismissal), not the older overlay.append()+`.open = True`
        # pattern, which doesn't properly register/track the dialog.
        self.page.show_dialog(self.picker)

    def _on_change(self, e):
        # Prefer the event's own `data` payload over `self.picker.value`:
        # DatePicker.value isn't a continuously two-way-bound property like
        # TextField.value, so it isn't guaranteed to be patched from the
        # client before this handler runs. The wire payload for this event
        # is documented to carry the selected date directly (see
        # ft.DatePicker.on_change docstring).
        selected = self._parse_date(getattr(e, "data", None)) or self._parse_date(
            self.picker.value
        )
        if selected is not None:
            self.set_value(selected.isoformat())
            self._safe_update()

    @staticmethod
    def _parse_date(value):
        """Parse a DatePicker value/event payload into the calendar date the
        user actually tapped.

        The picker represents a selection as local midnight of the tapped
        day, which gets serialized to UTC for the wire. For any positive UTC
        offset (e.g. this deployment's Asia/Jakarta, UTC+7) that rolls the
        UTC clock back onto the *previous* calendar day at a late hour - e.g.
        10 Jul 00:00 +07:00 becomes 09 Jul 17:00 UTC. Taking the date part of
        that UTC value naively is off by one. A UTC hour of noon or later is
        the tell that this rollback happened, so the date is rolled forward
        a day to recover the originally-tapped one. (This assumes a positive,
        sub-12-hour deployment offset, true for this project's Indonesia
        deployment - it isn't a general timezone-safe conversion.)
        """
        if value is None:
            return None
        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            return value

        dt = value if isinstance(value, datetime.datetime) else None
        if dt is None:
            try:
                dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None

        date_part = dt.date()
        if dt.hour >= 12:
            date_part += datetime.timedelta(days=1)
        return date_part

    def _safe_update(self):
        """Update the field if it's already mounted on the page.

        Mirrors components/form/select.py's _safe_update(): Control.update()
        raises RuntimeError (Flet 0.85+) if the control hasn't been attached
        to the page's control tree yet.
        """
        try:
            self.field.update()
        except RuntimeError:
            pass
