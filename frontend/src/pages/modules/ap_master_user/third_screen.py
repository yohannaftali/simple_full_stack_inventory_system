import flet as ft
from components.module.view import ModuleView


class ModulePage:
    """Module screen class"""

    def __init__(self, page: ft.Page, module: str, screen=str):
        """
        Initialize Module Page

        Args:
            page: The Flet page
            module: string
            screen: string
        """
        self.page = page
        self.module = module
        self.screen = screen
        self.view = ModuleView(page, module, screen)
        self.view.header.set_title("Third Screen")

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                ft.Icon(
                    icon=ft.Icons.THREE_G_MOBILEDATA_OUTLINED,
                    size=80,
                    color=ft.Colors.SECONDARY,
                ),
                ft.Container(
                    content=ft.Text("at ap config index - 3rd Screen"),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Button(
                    content="Back to 1st Screen",
                    width=300,
                    height=50,
                    on_click=self.on_click_first_screen,
                    icon=ft.Icons.LOGIN,
                    bgcolor=ft.Colors.PRIMARY,
                    color=ft.Colors.ON_PRIMARY,
                    style=ft.ButtonStyle(
                        overlay_color=ft.Colors.SECONDARY
                    )
                ),
                ft.Button(
                    content="Back to 2nd Screen or click back",
                    width=300,
                    height=50,
                    on_click=self.on_click_second_screen,
                    icon=ft.Icons.LOGIN,
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

    def on_click_first_screen(self, e):
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/index")

    def on_click_second_screen(self, e):
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/second_screen")
