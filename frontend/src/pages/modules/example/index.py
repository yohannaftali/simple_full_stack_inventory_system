import flet as ft

from components.module.view import ModuleView


class ModulePage:
    """Module page class"""

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

    def build(self):
        """Build and return the module screen page UI"""
        return self.view.build(self.body())

    def body(self):
        return ft.Column(
            controls=[
                ft.Icon(
                    icon=ft.Icons.STAR,
                    size=80,
                    color=ft.Colors.SECONDARY,
                ),
                ft.Container(
                    content=ft.Text("at ap config index"),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Button(
                    content="Next Screen (to 2nd)",
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

    def on_click_second_screen(self, e):
        print("Go to second screen (internal navigation)")
        self.page.run_task(self.page.push_route, f"/modules/{self.module}/second_screen")
