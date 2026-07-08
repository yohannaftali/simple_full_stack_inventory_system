"""
Light theme configuration for the application
"""
import flet as ft


class LightTheme:
    """Light theme color scheme and configuration"""

    @staticmethod
    def get_theme():
        """Get the light theme configuration"""
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                # Primary colors
                primary=ft.Colors.BLUE_900,
                on_primary=ft.Colors.BLUE_50,
                primary_container=ft.Colors.BLUE_100,
                on_primary_container=ft.Colors.BLUE_900,

                # Secondary colors
                secondary=ft.Colors.BLUE_GREY_700,
                on_secondary=ft.Colors.BLUE_GREY_50,
                secondary_container=ft.Colors.BLUE_GREY_100,
                on_secondary_container=ft.Colors.BLUE_GREY_900,

                # Tertiary colors
                tertiary=ft.Colors.DEEP_PURPLE_700,
                on_tertiary=ft.Colors.DEEP_PURPLE_50,
                tertiary_container=ft.Colors.DEEP_PURPLE_100,
                on_tertiary_container=ft.Colors.DEEP_PURPLE_900,

                # Error colors
                error=ft.Colors.RED_700,
                on_error=ft.Colors.RED_50,
                error_container=ft.Colors.RED_100,
                on_error_container=ft.Colors.RED_900,

                # Surface colors (background/surface_variant merged into
                # surface/surface_container_* in Flet 0.85's ColorScheme)
                surface=ft.Colors.BLUE_50,
                on_surface=ft.Colors.BLUE_900,
                on_surface_variant=ft.Colors.BLUE_800,
                surface_container=ft.Colors.WHITE,
                surface_container_high=ft.Colors.BLUE_50,
                surface_container_low=ft.Colors.WHITE,
                surface_container_lowest=ft.Colors.WHITE,

                # Outline colors
                outline=ft.Colors.BLUE_300,
                outline_variant=ft.Colors.BLUE_100,

                # Other colors
                shadow=ft.Colors.BLACK,
                scrim=ft.Colors.BLACK,
                inverse_surface=ft.Colors.BLUE_900,
                on_inverse_surface=ft.Colors.BLUE_50,
                inverse_primary=ft.Colors.BLUE_100,
                surface_tint=ft.Colors.BLUE_800,
            ),

            # Scrollbar theme
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color={
                    ft.ControlState.DEFAULT: ft.Colors.BLUE_GREY_700,
                    ft.ControlState.HOVERED: ft.Colors.BLUE_900,
                    ft.ControlState.DRAGGED: ft.Colors.BLUE_900,
                },
                track_color=ft.Colors.BLUE_100,
                track_visibility=True,
                thumb_visibility=True,
                thickness=10,
                radius=5,
                interactive=True,
            ),
        )
