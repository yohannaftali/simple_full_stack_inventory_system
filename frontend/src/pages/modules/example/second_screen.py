import flet as ft

from components.module.view import ModuleView


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            session: Storage instance
            module: string
            screen: string
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Second Screen")

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                ft.Icon(
                    icon=ft.Icons.TWO_WHEELER,
                    size=120,
                    color=ft.Colors.SECONDARY,
                ),
                ft.Container(
                    content=ft.Text("at ap config index - 2nd Screen"),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Button(
                    icon=ft.Icons.THREE_G_MOBILEDATA_OUTLINED,
                    content="Next Screen (to 3rd)",
                    width=300,
                    height=50,
                    on_click=self.on_click_third_screen,
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.ON_PRIMARY,
                    style=ft.ButtonStyle(
                        overlay_color=ft.Colors.SECONDARY
                    )
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def on_click_third_screen(self, e):
        print("Go to third screen")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/third_screen")
