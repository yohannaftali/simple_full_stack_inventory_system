import flet as ft

from components.form.input import (
    FIELD_BORDER_RADIUS,
    HELPER_TEXT_STYLE,
    field_content_padding,
)
from utils.icon import get_icon


class IconPickerForm:
    """`"icon_picker"`-type form field: a read-only text field whose LEADING
    icon renders whatever Material icon name the field currently holds
    (e.g. "chevron_right"), falling back to a configurable default when
    blank, and which pops up `components/modal/icon_selector.py::IconSelectorModal`
    - a reusable picker built around a `"radio"` (by-column mode, issue
    #45) `Table` column - on tap, instead of being typed from memory.

    Read-only + whole-field tap-to-open mirrors
    `components/form/date.py::DateForm`'s own shape (tap anywhere on the
    field, not just a trailing button, to open the picker/calendar).

    **The stored icon-name string must go through `utils/icon.py::get_icon()`
    before ever reaching an `ft.Icon`/`ft.TextField.prefix_icon` control** -
    confirmed live in the browser (two false leads chased first: a
    `Control`-typed `suffix_icon`, and stale client caching, both ruled
    out) that handing `ft.Icon(icon=...)` a raw, unmapped string (e.g.
    `"category"`) constructs fine in Python but fails once Flutter tries
    to actually paint it, replacing the whole field with a solid gray
    box (Flutter's default error-widget background) that also blows out
    its column's layout. `get_icon()` is this codebase's existing,
    already-proven convention for this exact conversion (see
    `components/home/module_card.py`'s own module-tile icons) - resolves
    a name to a real `ft.Icons` member via `getattr`, falling back to
    `ft.Icons.APPS` for anything unrecognized, so this control never
    hands Flutter a value it can't render.

    Sample first consumer: `pages/modules/ap_module/{new,edit}.py`'s
    `"icon"` field (a module's home-tile icon, previously a plain
    `"input"` with a static, unrelated leading icon - see AGENTS.md's
    "Module-access grant flow"/Big Picture sections for `ap_module`'s own
    shape). The field's existing `"icon"` key (a static `ft.Icons` member
    already used by every other `"input"` field as its fixed leading
    icon) doubles here as `default_icon` - shown whenever the stored text
    value is blank - so no new field key was needed to satisfy "blank ->
    default icon".

    Mirrors `components/form/date.py::DateForm`'s shape exactly: its own
    `build()`/`get_value()`/`set_value()`, special-cased in
    `components/form/form.py`'s `load()`/`serialize()` via `Form.icon_picker`
    (a plain `ft.TextField`'s own `.value` can be read/written directly,
    but nothing about a bare `ft.TextField` lets its `prefix_icon` be
    swapped after construction from Form's own generic
    `isinstance(control, ft.TextField)` path - same reason `DateForm`
    needed its own `set_value()` instead of reusing that path for its
    ISO-vs-display-text split).
    """

    def __init__(self, page: ft.Page, field: dict):
        self.page = page
        self.name = field.get("name", "")
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", "e.g. chevron_right")
        self.default_icon = field.get("icon") or ft.Icons.APPS
        self.autofocus = field.get("autofocus", False)
        # Same defaults as every other field type (issue #79) - these were
        # 16/14 here, which alone made this field render taller than its
        # siblings now that heights are natural rather than forced.
        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE)
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor", ft.Colors.TRANSPARENT)

        self.value: str = field.get("default", "") or ""
        # Always present, even blank (issue #78) - see input.py's own
        # HELPER_TEXT_STYLE notes for why every field reserves this
        # space unconditionally.
        self.helper_text = field.get("helper_text", "")
        self.field: ft.TextField | None = None
        self.prefix_icon: ft.Icon | None = None

    def build(self) -> ft.TextField:
        self.prefix_icon = ft.Icon(icon=self._resolve_icon(), color=self.value_color)
        self.field = ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            value=self.value,
            prefix_icon=self.prefix_icon,
            suffix_icon=ft.Icons.ARROW_DROP_DOWN,
            # No explicit `height` (issue #79) - every field type shares the
            # same border, content padding, text size and an always-present
            # helper line, so they all size to the same height naturally.
            helper=self.helper_text,
            helper_style=HELPER_TEXT_STYLE,
            content_padding=field_content_padding(True),
            border_radius=FIELD_BORDER_RADIUS,
            border=ft.InputBorder.OUTLINE,
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
            # No `adaptive=True` (issue #73) - see main.py's `page.adaptive`
            # removal note.
            expand=True,
            on_click=self._open_picker,
        )
        return self.field

    def get_value(self) -> str:
        """The raw icon-name text, for Form.serialize()."""
        return self.value

    def set_value(self, value: str) -> None:
        """Set from a backend value (Form.load()) or a picker confirm."""
        self.value = value or ""
        if self.field is not None:
            self.field.value = self.value
            self._safe_update(self.field)
        self._refresh_prefix_icon()

    def _resolve_icon(self):
        value = self.value.strip() if self.value else ""
        return get_icon(value) if value else self.default_icon

    def _refresh_prefix_icon(self) -> None:
        if self.prefix_icon is not None:
            self.prefix_icon.icon = self._resolve_icon()
            self._safe_update(self.prefix_icon)

    def _open_picker(self, e) -> None:
        from components.modal.icon_selector import IconSelectorModal

        IconSelectorModal(
            page=self.page, current_value=self.value, on_confirm=self.set_value
        ).open()

    def _safe_update(self, control) -> None:
        """Mirrors DateForm's own `_safe_update()`: `Control.update()`
        raises `RuntimeError` (Flet 0.85+) if the control isn't attached to
        the page's control tree yet (e.g. `set_value()` called from
        `Form.load()` before `Form.build()` has ever run)."""
        try:
            control.update()
        except RuntimeError:
            pass
