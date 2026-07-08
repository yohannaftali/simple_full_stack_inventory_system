"""
FontAwesome to Material Icons mapping
Maps FontAwesome icon names to their Material Icons equivalents in Flet
"""
import flet as ft


# FontAwesome to Material Icons mapping dictionary
FA_ICON_MAP = {
    # Files and Folders
    "folder-plus": ft.Icons.CREATE_NEW_FOLDER,
    "folder": ft.Icons.FOLDER,
    "folder-open": ft.Icons.FOLDER_OPEN,
    "file": ft.Icons.INSERT_DRIVE_FILE,
    "file-invoice": ft.Icons.RECEIPT,
    "file-image": ft.Icons.IMAGE,
    "file-archive": ft.Icons.FOLDER_ZIP,
    "file-alt": ft.Icons.DESCRIPTION,

    # Money and Finance
    "money-check": ft.Icons.PAYMENT,
    "money-bill": ft.Icons.ATTACH_MONEY,
    "money-bills": ft.Icons.MONETIZATION_ON,
    "money-bill-transfer": ft.Icons.SWAP_HORIZ,
    "sack-dollar": ft.Icons.MONEY,
    "coins": ft.Icons.MONETIZATION_ON,
    "dollar-sign": ft.Icons.ATTACH_MONEY,
    "usd": ft.Icons.ATTACH_MONEY,
    "wallet": ft.Icons.ACCOUNT_BALANCE_WALLET,
    "credit-card": ft.Icons.CREDIT_CARD,
    "cash-register": ft.Icons.POINT_OF_SALE,

    # Buildings and Locations
    "building": ft.Icons.BUSINESS,
    "building-columns": ft.Icons.ACCOUNT_BALANCE,
    "warehouse": ft.Icons.WAREHOUSE,
    "store": ft.Icons.STORE,
    "amazon": ft.Icons.STORE,

    # Transportation
    "truck": ft.Icons.LOCAL_SHIPPING,
    "truck-field": ft.Icons.LOCAL_SHIPPING,
    "truck-monster": ft.Icons.LOCAL_SHIPPING,
    "truck-front": ft.Icons.LOCAL_SHIPPING,
    "shipping-fast": ft.Icons.LOCAL_SHIPPING,
    "car": ft.Icons.DIRECTIONS_CAR,
    "car-battery": ft.Icons.BATTERY_CHARGING_FULL,

    # Communication
    "bullhorn": ft.Icons.CAMPAIGN,
    "envelope": ft.Icons.EMAIL,
    "comment": ft.Icons.COMMENT,
    "comments": ft.Icons.CHAT,

    # Charts and Data
    "chart-bar": ft.Icons.BAR_CHART,
    "chart-line": ft.Icons.SHOW_CHART,
    "chart-pie": ft.Icons.PIE_CHART,
    "chart-simple": ft.Icons.SHOW_CHART,
    "database": ft.Icons.STORAGE,
    "table": ft.Icons.TABLE_CHART,
    "table-cells": ft.Icons.GRID_ON,

    # Calendar and Time
    "calendar": ft.Icons.CALENDAR_TODAY,
    "calendar-days": ft.Icons.CALENDAR_MONTH,
    "calendar-alt": ft.Icons.EVENT,
    "clock": ft.Icons.ACCESS_TIME,
    "timeline": ft.Icons.TIMELINE,

    # User and People
    "user": ft.Icons.PERSON,
    "user-tie": ft.Icons.PERSON,
    "users": ft.Icons.GROUP,
    "id-card": ft.Icons.BADGE,

    # Tools and Settings
    "hammer": ft.Icons.HANDYMAN,
    "wrench": ft.Icons.BUILD,
    "screwdriver": ft.Icons.BUILD,
    "tools": ft.Icons.BUILD,
    "cog": ft.Icons.SETTINGS,
    "cogs": ft.Icons.SETTINGS,

    # Writing and Editing
    "pen": ft.Icons.EDIT,
    "pen-nib": ft.Icons.EDIT,
    "pen-to-square": ft.Icons.EDIT_NOTE,
    "pencil": ft.Icons.EDIT,
    "eraser": ft.Icons.CLEAR,

    # Navigation and Location
    "map": ft.Icons.MAP,
    "map-pin": ft.Icons.LOCATION_ON,
    "map-marker": ft.Icons.PLACE,
    "compass": ft.Icons.EXPLORE,
    "location-dot": ft.Icons.LOCATION_ON,

    # Business and Office
    "briefcase": ft.Icons.WORK,
    "calculator": ft.Icons.CALCULATE,
    "receipt": ft.Icons.RECEIPT_LONG,
    "book": ft.Icons.MENU_BOOK,

    # Misc
    "key": ft.Icons.KEY,
    "lock": ft.Icons.LOCK,
    "unlock": ft.Icons.LOCK_OPEN,
    "camera-retro": ft.Icons.CAMERA_ALT,
    "puzzle-piece": ft.Icons.EXTENSION,
    "layer-group": ft.Icons.LAYERS,
    "scale-balanced": ft.Icons.BALANCE,
    "shopping-bag": ft.Icons.SHOPPING_BAG,
    "shopping-cart": ft.Icons.SHOPPING_CART,
    "square-check": ft.Icons.CHECK_BOX,
    "palette": ft.Icons.PALETTE,
    "pallete": ft.Icons.PALETTE,  # Common misspelling
}


def get_fa_icon(icon_name: str):
    """
    Get Material icon for FontAwesome icon name

    Args:
        icon_name: FontAwesome icon name (without 'fa-' prefix)

    Returns:
        Flet icon constant
    """
    # Remove 'fa-' prefix if present
    if icon_name.startswith("fa-"):
        icon_name = icon_name[3:]

    # Try to get from mapping
    if icon_name in FA_ICON_MAP:
        return FA_ICON_MAP[icon_name]

    # Try dynamic mapping (convert to uppercase with underscores)
    dynamic_name = icon_name.upper().replace("-", "_")
    try:
        return getattr(ft.Icons, dynamic_name, ft.Icons.APPS)
    except AttributeError:
        return ft.Icons.APPS
