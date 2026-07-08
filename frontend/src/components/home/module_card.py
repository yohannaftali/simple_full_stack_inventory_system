"""
Module card component for displaying module items
"""
import flet as ft

from utils.icon import get_icon


class ModuleCard:
    """Module card component"""

    def __init__(self, page: ft.Page, module: dict):
        """
        Initialize module card

        Args:
            module: Module data dict with keys: module_icon, label, name, etc.
        """
        self.page = page
        self.module = module

        self.module_name = module.get("name", 'module')
        self.icon_name = module.get("module_icon", "apps")

        self.label = module.get("label", "Unknown")
        self.module_description = module.get("module_description", self.label)

        self.module_icon = ft.Container(
            content=ft.Icon(
                icon=get_icon(self.icon_name),
                size=40,
                color=ft.Colors.ON_PRIMARY,
            ),
            width=60,
            height=60,
            bgcolor=ft.Colors.PRIMARY,
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=30,
        )

        # self.module_icon = ft.IconButton(
        #     icon=get_icon(self.icon_name),
        #     icon_size=40,
        #     style=ft.ButtonStyle(
        #         color={
        #             ft.ControlState.HOVERED: ft.Colors.PRIMARY,
        #             ft.ControlState.FOCUSED: ft.Colors.PRIMARY,
        #             ft.ControlState.DEFAULT: ft.Colors.SECONDARY,
        #         },
        #         bgcolor={
        #             ft.ControlState.HOVERED: ft.Colors.ON_PRIMARY,
        #             ft.ControlState.FOCUSED: ft.Colors.ON_PRIMARY,
        #             ft.ControlState.DEFAULT: ft.Colors.ON_SECONDARY,
        #         },
        #         shape=ft.RoundedRectangleBorder(radius=30),
        #     )
        # )

        self.module_label = ft.Container(
            content=ft.Text(
                self.label,
                size=11,
                text_align=ft.TextAlign.CENTER,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                color=ft.Colors.ON_SURFACE
            ),
            padding=ft.Padding.only(left=3, right=3, top=5),
            height=20,
        )

        self.container = ft.Container(
            content=ft.Column(
                [
                    self.module_icon,
                    self.module_label,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=2,
            ),
            padding=3,
            on_click=lambda e: self.on_click(),
            ink=True,
        )

    def build(self):
        """Build and return module card"""
        return self.container

    def on_click(self):
        """Handle module click"""
        print(
            f"Module clicked: {self.module.get('label')} ({self.module.get('name')})")
        self.page.run_task(self.page.push_route, f"/modules/{self.module_name}/index")
