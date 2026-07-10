"""
Light theme configuration for the application

Color scheme from Material Theme Builder
(https://material-foundation.github.io/material-theme-builder/) with seed
color #769CDF (Material 3 standard-contrast "light" scheme) - see
frontend/design/material-theme/ for the full exported reference (Color.kt/
Theme.kt/Type.kt). Typefaces: Lato (body/label roles), Montserrat (display/
headline/title roles), per that export's Type.kt - registered as custom
fonts in `main.py` via `page.fonts`.
"""
import flet as ft

_DISPLAY_FONT = "Montserrat"
_BODY_FONT = "Lato"


class LightTheme:
    """Light theme color scheme and configuration"""

    @staticmethod
    def get_theme():
        """Get the light theme configuration"""
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                # Primary colors
                primary="#365E9D",
                on_primary="#FFFFFF",
                primary_container="#769CDF",
                on_primary_container="#00326A",

                # Secondary colors
                secondary="#515F79",
                on_secondary="#FFFFFF",
                secondary_container="#D2E0FF",
                on_secondary_container="#55637D",

                # Tertiary colors
                tertiary="#814A87",
                on_tertiary="#FFFFFF",
                tertiary_container="#C486C8",
                on_tertiary_container="#511D58",

                # Error colors
                error="#BA1A1A",
                on_error="#FFFFFF",
                error_container="#FFDAD6",
                on_error_container="#93000A",

                # Surface colors (background/surface_variant merged into
                # surface/surface_container_* in Flet 0.85's ColorScheme)
                surface="#F9F9FF",
                on_surface="#1A1C20",
                on_surface_variant="#434750",
                surface_container="#EEEDF3",
                surface_container_high="#E8E7ED",
                surface_container_low="#F3F3F9",
                surface_container_lowest="#FFFFFF",

                # Outline colors
                outline="#737781",
                outline_variant="#C3C6D2",

                # Other colors
                shadow=ft.Colors.BLACK,
                scrim=ft.Colors.BLACK,
                inverse_surface="#2F3035",
                on_inverse_surface="#F1F0F6",
                inverse_primary="#AAC7FF",
                surface_tint="#365E9D",
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
                    ft.ControlState.DEFAULT: "#515F79",
                    ft.ControlState.HOVERED: "#365E9D",
                    ft.ControlState.DRAGGED: "#365E9D",
                },
                track_color="#D2E0FF",
                track_visibility=True,
                thumb_visibility=True,
                thickness=10,
                radius=5,
                interactive=True,
            ),
        )
