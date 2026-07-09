import datetime

import flet as ft


class DateForm:
    """Date field backed by a calendar popup (ft.DatePicker).

    Renders as a read-only TextField (tap to open the picker, not typed
    directly) showing an ISO "YYYY-MM-DD" string - the same format the
    backend's `date` Form fields already expect/return, so no serialize()/
    load() changes were needed elsewhere in Form: this returns a plain
    ft.TextField, same as InputForm, and gets treated identically.
    """

    def __init__(self, page: ft.Page, parent, field: dict):
        self.page = page
        self.parent = parent
        self.name = field.get("name", "")
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Select {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.value_size = field.get("value_size", 16)
        self.label_size = field.get("label_size", 14)
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE)
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)
        self.first_date = field.get("first_date", datetime.date(2000, 1, 1))
        self.last_date = field.get("last_date", datetime.date(2100, 12, 31))

        self.field: ft.TextField | None = None
        self.picker = ft.DatePicker(
            first_date=self.first_date,
            last_date=self.last_date,
            on_change=self._on_change,
        )
        self.page.overlay.append(self.picker)

    def build(self) -> ft.TextField:
        prefix_icon = (
            ft.Icon(icon=self.icon, color=self.value_color)
            if self.icon is not None else None
        )
        self.field = ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            prefix_icon=prefix_icon,
            suffix_icon=ft.Icons.CALENDAR_MONTH,
            border_radius=10,
            border_color=self.border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            read_only=True,
            color=self.value_color,
            label_style=ft.TextStyle(
                size=self.label_size,
                color=self.label_color,
            ),
            filled=self.filled,
            bgcolor=self.bgcolor,
            adaptive=True,
            expand=True,
            on_click=self._open_picker,
        )
        return self.field

    def _open_picker(self, e):
        if self.field and self.field.value:
            try:
                self.picker.value = datetime.date.fromisoformat(self.field.value)
            except ValueError:
                pass
        self.picker.open = True
        self.page.update()

    def _on_change(self, e):
        selected = self.picker.value
        if selected is not None:
            if isinstance(selected, datetime.datetime):
                selected = selected.date()
            if self.field is not None:
                self.field.value = selected.isoformat()
        self.picker.open = False
        self.page.update()
