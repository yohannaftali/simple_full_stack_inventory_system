import flet as ft

from components.home.module_card import ModuleCard


class ModuleContainer:
    """Module container component for displaying grouped modules"""

    def __init__(self, page: ft.Page, modules: list = None):
        """
        Initialize module container

        Args:
            modules: List of modules to display
        """
        self.page = page
        self.modules = modules or []

        # Modules container
        self.container = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,
            scroll_interval=0,
        )

    def build(self):
        """Build and return the container control"""
        return ft.Container(
            content=self.container,
            expand=True,
        )

    def group_container(self, group_name: str):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER, color=ft.Colors.SECONDARY, size=20),
                    ft.Text(
                        group_name,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=8,
            ),
            bgcolor=ft.Colors.SURFACE,
            padding=ft.Padding.symmetric(horizontal=10, vertical=10),
            margin=ft.Margin.only(bottom=5),
            border=ft.Border.only(bottom=ft.BorderSide(2, ft.Colors.OUTLINE)),
        )

    def update(self, modules: list = None):
        """
        Build the modules UI grouped by module groups

        Args:
            modules: List of modules to display (optional, uses self.modules if not provided)
        """
        if modules is not None:
            self.modules = modules

        self.container.controls.clear()

        # Group modules by group
        grouped = {}
        for module in self.modules:
            group = module.get("group") or "Dashboard"
            if group not in grouped:
                grouped[group] = []
            grouped[group].append(module)

        # Build UI for each group
        for group_name, group_modules in grouped.items():
            # Group header
            self.container.controls.append(self.group_container(group_name))

            # Create grid of module cards
            grid_items = []
            for module in group_modules:
                card = ModuleCard(
                    page=self.page,
                    module=module,
                )
                module_card = card.build()
                grid_items.append(module_card)

            # Add grid view for modules
            grid = ft.GridView(
                runs_count=6,
                max_extent=150,
                child_aspect_ratio=1.0,
                spacing=2,
                run_spacing=2,
                padding=ft.Padding.only(left=5, right=15, top=5, bottom=5),
            )

            for item in grid_items:
                grid.controls.append(item)

            self.container.controls.append(grid)

        # Only update if already added to page. Flet 0.85's Control.page
        # property raises RuntimeError (instead of returning None) when the
        # control hasn't been mounted yet.
        try:
            mounted = self.container.page is not None
        except RuntimeError:
            mounted = False
        if mounted:
            self.container.update()
