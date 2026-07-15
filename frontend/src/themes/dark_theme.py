"""
Dark theme configuration for the application

Color scheme from Material Theme Builder
(https://material-foundation.github.io/material-theme-builder/) with seed
color #769CDF (Material 3 standard-contrast "dark" scheme) - see
frontend/design/material-theme/ for the full exported reference (Color.kt/
Theme.kt/Type.kt). Typefaces: Lato (body/label roles), Montserrat (display/
headline/title roles), per that export's Type.kt - registered as custom
fonts in `main.py` via `page.fonts`.
"""

import flet as ft

_DISPLAY_FONT = "Montserrat"
_BODY_FONT = "Lato"


class DarkTheme:
    """Dark theme color scheme and configuration"""

    @staticmethod
    def get_theme():
        """Get the dark theme configuration"""
        return ft.Theme(
            use_material3=True,
            font_family=_BODY_FONT,
            color_scheme=ft.ColorScheme(
                # Primary colors
                primary="#AAC7FF",
                on_primary="#002F64",
                primary_container="#769CDF",
                on_primary_container="#00326A",
                # Secondary colors
                secondary="#B9C7E5",
                on_secondary="#233148",
                secondary_container="#3C4962",
                on_secondary_container="#ABB9D6",
                # Tertiary colors
                tertiary="#F2B0F5",
                on_tertiary="#4D1A55",
                tertiary_container="#C486C8",
                on_tertiary_container="#511D58",
                # Error colors
                error="#FFB4AB",
                on_error="#690005",
                error_container="#93000A",
                on_error_container="#FFDAD6",
                # Surface colors (Lengkap dengan Token M3 Flet 0.85+)
                surface="#121317",
                surface_bright="#38393E",
                surface_dim="#121317",
                on_surface="#E2E2E8",
                on_surface_variant="#C3C6D2",
                surface_container="#1E2024",
                surface_container_high="#282A2E",
                surface_container_low="#1A1C20",
                surface_container_lowest="#0C0E12",
                # Outline colors
                outline="#8D909B",
                outline_variant="#434750",
                # Other colors (Perbaikan: ft.colors huruf kecil)
                shadow="#000000",
                scrim="#000000",
                inverse_surface="#E2E2E8",
                on_inverse_surface="#2F3035",
                inverse_primary="#365E9D",
                surface_tint="#AAC7FF",
            ),
            # Typography: Montserrat for display/headline/title, Lato for
            # body/label - matches frontend/design/material-theme/ui/theme/
            # Type.kt's body/display font split.
            text_theme=ft.TextTheme(
                display_large=ft.TextStyle(font_family=_DISPLAY_FONT),
                display_medium=ft.TextStyle(font_family=_DISPLAY_FONT),
                display_small=ft.TextStyle(font_family=_DISPLAY_FONT),
                headline_large=ft.TextStyle(font_family=_DISPLAY_FONT),
                headline_medium=ft.TextStyle(font_family=_DISPLAY_FONT),
                headline_small=ft.TextStyle(font_family=_DISPLAY_FONT),
                title_large=ft.TextStyle(font_family=_DISPLAY_FONT),
                title_medium=ft.TextStyle(font_family=_DISPLAY_FONT),
                title_small=ft.TextStyle(font_family=_DISPLAY_FONT),
                body_large=ft.TextStyle(font_family=_BODY_FONT),
                body_medium=ft.TextStyle(font_family=_BODY_FONT),
                body_small=ft.TextStyle(font_family=_BODY_FONT),
                label_large=ft.TextStyle(font_family=_BODY_FONT),
                label_medium=ft.TextStyle(font_family=_BODY_FONT),
                label_small=ft.TextStyle(font_family=_BODY_FONT),
            ),
            # Scrollbar theme
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color={
                    ft.ControlState.DEFAULT: "#B9C7E5",
                    ft.ControlState.HOVERED: "#AAC7FF",
                    ft.ControlState.DRAGGED: "#AAC7FF",
                },
                track_color="#3C4962",
                track_visibility=True,
                thumb_visibility=True,
                thickness=14,
                radius=5,
                interactive=True,
            ),
        )
