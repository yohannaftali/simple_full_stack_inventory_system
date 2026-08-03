import flet as ft

from components.scan_input import ScanInput

# The scan button lives inside the field's own suffix_icon slot, so it must
# be sized explicitly - an unconstrained IconButton there carries Flutter's
# ~48dp tap target and visibly grows the field's height (same as
# components/form/select.py's own scan button, issue #52).
SCAN_BUTTON_SIZE = 32
SCAN_ICON_SIZE = 20

# Shared corner radius (issue #79) - every field type uses the same value
# now that all are outlined; select.py previously used a deliberately
# different (square, 0) radius as part of #53's filled-style design, which
# no longer applies once every field shares one plain outlined box.
FIELD_BORDER_RADIUS = 10

# Vertical content padding, shared by every field type (issue #79).
#
# This is the single most important number in these components, and the
# root cause of the long "select label is clipped by its own border" hunt:
# on an OUTLINE border, Flutter's floating label straddles the top border
# line, and `InputDecorator` reserves the room for it out of the field's
# vertical content padding. Flutter's own default for a non-dense outlined
# field is 20; these components previously hardcoded 8, less than half of
# what the label needs, so the border stroke painted straight through the
# label text.
#
# It stayed invisible until issue #79 because the previous filled/UNDERLINE
# style (#53) has no label notch to cut and different internal metrics.
# `icon_picker.py` was the one field type that never set `content_padding`
# at all - inheriting Flutter's correct default - and was also the one
# field type never reported as clipping, which is what finally identified
# this as the cause.
#
# Do NOT lower this below ~16 while the fields use `InputBorder.OUTLINE`,
# and do NOT try to compensate for a too-small value with explicit heights,
# extra row padding, or post-mount refresh hacks - all three were tried
# and none of them fix it, because the label genuinely has nowhere to go.
FIELD_CONTENT_PADDING_VERTICAL = 16

# Horizontal content padding - slightly tighter when a leading icon is
# present, matching M3's own spec (16dp normally, 12dp with an icon).
FIELD_CONTENT_PADDING_HORIZONTAL = 16
FIELD_CONTENT_PADDING_HORIZONTAL_WITH_ICON = 12


def field_content_padding(has_icon: bool) -> ft.Padding:
    """The shared content padding every form field type uses.

    Centralized so a field type can't drift back to its own hardcoded
    (and, historically, label-clipping) vertical value.
    """
    return ft.Padding.symmetric(
        vertical=FIELD_CONTENT_PADDING_VERTICAL,
        horizontal=(
            FIELD_CONTENT_PADDING_HORIZONTAL_WITH_ICON
            if has_icon
            else FIELD_CONTENT_PADDING_HORIZONTAL
        ),
    )


# Style for the supporting/helper text line under a field. Every field type
# passes a helper string unconditionally (blank when it has nothing to say)
# so Flutter reserves the same supporting-text line on every field, keeping
# heights uniform without anyone having to force an explicit height.
HELPER_TEXT_STYLE = ft.TextStyle(size=11, color=ft.Colors.ON_SURFACE_VARIANT)

# Approximate rendered height of that reserved helper line. Only needed to
# vertically centre a sibling control (the scan button) against the input
# BOX rather than against the box-plus-helper-line: giving the sibling a
# bottom margin of this size shifts it up by half of it, which lands it on
# the box's own centre.
HELPER_TEXT_LINE_HEIGHT = 20


class InputForm:

    def __init__(self, page: ft.Page, field: dict):
        self.page = page
        self.label = field.get("label", "")
        self.hint_text = field.get("hint_text", f"Please input {self.label}")
        self.icon = field.get("icon")
        self.autofocus = field.get("autofocus", False)
        self.read_only = field.get("read_only", False)
        self.value_size = field.get("value_size", 14)
        self.label_size = field.get("label_size", 13)
        # M3 outlined text field color roles (issue #79 - reverted from
        # #53's filled design per direct user reconsideration): no
        # container fill at all, a full border box around the field
        # (`ft.InputBorder.OUTLINE`) instead of just a bottom underline.
        # Input text is a constant ON_SURFACE. Focused-state colouring is
        # left entirely to Flutter/M3: `focused_border_color` recolours the
        # outline, and the theme's own `floatingLabelStyle` recolours the
        # label. Swapping those from Python via on_focus/on_blur handlers
        # was removed - see components/form/select.py's class docstring
        # (issue #71) for the bug that pattern caused.
        self.value_color = field.get("color", ft.Colors.ON_SURFACE)
        self.label_color = field.get("label_color", ft.Colors.ON_SURFACE_VARIANT)
        self.border_color = field.get("border_color", ft.Colors.ON_SURFACE_VARIANT)
        self.focused_border_color = field.get("focused_border_color", ft.Colors.PRIMARY)
        self.multiline = field.get("multiline", False)
        self.min_lines = field.get("min_lines", 1)
        self.max_lines = field.get("max_lines", 1)
        self.prefix_icon = None
        # Outlined fields have no container fill by default (issue #79) -
        # still overridable per-field for a rare caller that wants one.
        self.filled = field.get("filled", False)
        self.bgcolor = field.get("bgcolor")
        self.password = field.get("password", False)
        self.can_reveal_password = field.get("can_reveal_password", self.password)
        # Always present, even blank (issue #78) - an empty string still
        # makes Flutter reserve the helper-text line's vertical space, so
        # every field's total height stays identical whether or not it
        # actually has supporting text to show. See HELPER_TEXT_STYLE.
        self.helper_text = field.get("helper_text", "")
        # Opt-in barcode/QR scan button (issue #52 parity for plain text
        # inputs, added on request) - off unless the field dict says
        # `"qr": True`, so every existing input in the app is untouched.
        # Unlike select.py's scan button, a scanned code here isn't
        # resolved against a fixed option list - it's typed straight into
        # the field, so it lives in the field's own suffix_icon slot (no
        # sibling-control/hover-isolation concern the way Dropdown's own
        # trailing arrow had in issue #52's follow-up).
        self.qr = field.get("qr", False)
        self.scan_input: ScanInput | None = None
        self.field: ft.TextField | None = None

    def build(self):
        self.prefix_icon = (
            ft.Icon(
                icon=self.icon,
                color=ft.Colors.ON_SURFACE_VARIANT) if self.icon is not None else None
        )
        suffix_icon = None
        suffix_icon_size_constraints = None
        if self.qr:
            self.scan_input = ScanInput(
                page=self.page,
                on_scan=self.apply_scanned_code,
                title=f"Scan {self.label}" if self.label else "Scan Barcode / QR",
                tooltip=f"Scan {self.label}" if self.label else "Scan barcode / QR",
                icon_size=SCAN_ICON_SIZE,
                width=SCAN_BUTTON_SIZE,
                height=SCAN_BUTTON_SIZE,
            )
            suffix_icon = self.scan_input.build()
            suffix_icon_size_constraints = ft.BoxConstraints(
                min_width=SCAN_BUTTON_SIZE,
                max_width=SCAN_BUTTON_SIZE,
                min_height=SCAN_BUTTON_SIZE,
                max_height=SCAN_BUTTON_SIZE,
            )
        self.field = ft.TextField(
            label=self.label,
            hint_text=self.hint_text,
            hint_style=ft.TextStyle(color=ft.Colors.ON_SURFACE_VARIANT),
            prefix_icon=self.prefix_icon,
            suffix_icon=suffix_icon,
            suffix_icon_size_constraints=suffix_icon_size_constraints,
            # No explicit `height` (issue #79) - every field type shares the
            # same border, content padding, text size and an always-present
            # helper line, so they all size to the same height naturally.
            # Forcing a height instead squeezed the outlined border's
            # floating label and caused it to be painted through.
            helper=self.helper_text,
            helper_style=HELPER_TEXT_STYLE,
            border_radius=FIELD_BORDER_RADIUS,
            border=ft.InputBorder.OUTLINE,
            border_color=self.border_color,
            focused_border_color=self.focused_border_color,
            autofocus=self.autofocus,
            text_size=self.value_size,
            read_only=self.read_only,
            color=self.value_color,
            content_padding=field_content_padding(self.icon is not None),
            label_style=ft.TextStyle(size=self.label_size, color=self.label_color),
            multiline=self.multiline,
            min_lines=self.min_lines,
            max_lines=self.max_lines,
            filled=self.filled,
            bgcolor=self.bgcolor,
            password=self.password,
            can_reveal_password=self.can_reveal_password,
            # No `adaptive=True` (issue #73) - see main.py's own
            # `page.adaptive` removal note for why: this app renders
            # Material 3 uniformly, matching `SelectForm`'s Dropdown, which
            # has no Cupertino/adaptive variant at all.
            expand=True,
        )
        return self.field

    def apply_scanned_code(self, code: str) -> None:
        """A scanned code is typed straight into the field - no option list
        to resolve against here, unlike select.py's own scan handler."""
        if self.field is not None:
            self.field.value = code
            self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.field.update()
        except RuntimeError:
            pass
