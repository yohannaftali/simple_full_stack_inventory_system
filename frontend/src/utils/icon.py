
import flet as ft
from utils.fontawesome import get_fa_icon


def get_icon(icon_name):
    """Map icon name to Flet icon"""
    if not icon_name:
        return ft.Icons.APPS

    # Check if it's a FontAwesome icon (starts with "fa-")
    if icon_name.startswith("fa-"):
        return get_fa_icon(icon_name)
    else:
        # For non-FA icons, convert to uppercase with underscores
        standard_icon_name = icon_name.upper().replace("-", "_")
        # Try to get the icon from ft.Icons
        try:
            return getattr(ft.Icons, standard_icon_name, ft.Icons.APPS)
        except AttributeError:
            return ft.Icons.APPS
