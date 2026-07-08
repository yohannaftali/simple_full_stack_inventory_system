"""
Body component for the application
"""

import flet as ft

from components.home.search_bar import HomeSearchBar
from components.home.module_container import ModuleContainer
from components.home.footer import Footer
from repository.storage import Storage
from utils.module_loader import ModuleLoader


class Body:
    """Body component"""

    def __init__(self, page: ft.Page):
        """
        Initialize body

        Args:
            page: The Flet page
        """
        self.page = page
        self.storage: Storage = page.data["storage"]

        self.modules = self.storage.client_data.get_modules()
        if self.modules is None or not isinstance(self.modules, list) or len(self.modules) == 0:
            self.storage.client_data.refresh()
            self.modules = self.storage.client_data.get_modules()

        if self.modules:
            implemented = ModuleLoader.list_implemented("modules")
            self.modules = [m for m in self.modules if m.get("name") in implemented]

        self.filtered_modules = self.modules.copy() if self.modules else []

        # Pull persisted search value if any
        initial_search = ""
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            initial_search = self.page.data.get("home_search", "")
        self.module_search_bar = HomeSearchBar(
            page=page,
            modules=self.modules,
            on_filter_change=self.on_filter_change,
            on_submit=self.on_module_submit,
            initial_value=initial_search
        )

        self.module_container = ModuleContainer(
            page=self.page, modules=self.filtered_modules,)

        self.footer = Footer(self.page)

        self.load()

    def build(self):
        """Build and return the body column"""
        if self.modules and not self.module_container.container.controls:
            self.module_container.update(self.filtered_modules)

        controls = []

        if self.module_search_bar:
            controls.append(self.module_search_bar.build())

        if self.module_container:
            controls.append(
                ft.Container(
                    content=self.module_container.build(),
                    expand=True,
                    bgcolor=ft.Colors.SURFACE,
                )
            )

        if self.footer:
            controls.append(self.footer.build())

        return ft.SafeArea(
            content=ft.Container(
                content=ft.Column(
                    controls,
                    spacing=0,
                    expand=True,
                ),
                alignment=ft.Alignment.CENTER,
                padding=0,
            ),
            expand=True,
        )

    def load(self):
        if self.modules is not None:
            self.module_search_bar.update_modules(self.modules)
            # Reapply filter based on persisted search value
            if self.module_search_bar.search_bar.value:
                self.module_search_bar.on_search_change(None)
            # Flet 0.85's Control.page property raises RuntimeError (instead
            # of returning None) when the control hasn't been mounted yet.
            try:
                container_mounted = self.module_container.container.page is not None
            except RuntimeError:
                container_mounted = False
            if self.page and container_mounted:
                self.module_container.update(self.filtered_modules)

    def on_filter_change(self, filtered_modules):
        """Handle filter change from search bar"""
        self.filtered_modules = filtered_modules
        self.module_container.update(self.filtered_modules)

    def on_module_submit(self, module):
        """Handle Enter key press - navigate to first module"""
        module_name = module.get("name", "")
        if module_name:
            self.page.run_task(self.page.push_route, f"/modules/{module_name}/index")
