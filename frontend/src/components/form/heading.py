import flet as ft


class HeadingForm:
    def __init__(self, field: dict):
        self.label = field.get("label")
        self.icon = field.get("icon")
        self.label_size = field.get("label_size", 14)
        self.label_color = field.get("color", ft.Colors.ON_SECONDARY_CONTAINER)
        self.bgcolor = field.get("bgcolor", ft.Colors.SURFACE_CONTAINER_LOW)
        self.weight = field.get("weight", ft.FontWeight.BOLD)
        self.max_lines = field.get("max_lines", 1)
        self.italic = field.get("italic", False)

        self.left = []
        self.right = []

    def build(self):
        left_controls = []
        if not self.left:
            if self.icon:
                # Mengatur ukuran ikon agar pas di dalam toolbar kecil (sekitar 18-20dp)
                left_controls.append(
                    ft.Icon(name=self.icon, color=self.label_color, size=18)
                )
            if self.label:
                left_controls.append(
                    ft.Text(
                        value=self.label,
                        size=self.label_size,
                        color=self.label_color,
                        weight=self.weight,
                        max_lines=self.max_lines,
                        italic=self.italic,
                    )
                )
        else:
            left_controls = self.left

        # Contoh Tombol Compact Ukuran 32dp x 32dp di sisi kanan jika belum diisi
        right_controls = (
            self.right
            if self.right
            else [
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    icon_size=16,
                    width=32,
                    height=32,
                    style=ft.ButtonStyle(
                        padding=0,  # Hapus padding bawaan tombol agar pas 32dp
                        shape=ft.RoundedRectangleBorder(radius=4),
                    ),
                    tooltip="Pengaturan",
                )
            ]
        )

        text = (
            ft.Text(
                value=self.label,
                size=self.label_size,
                color=self.label_color,
                bgcolor=self.bgcolor,
                weight=self.weight,
                selectable=False,
                max_lines=self.max_lines,
                italic=self.italic,
            )
            if self.label is not None
            else None
        )
        if text is not None:
            left_controls.append(text)

        return ft.Container(
            height=38,
            padding=ft.Padding.Symmetric(horizontal=12, vertical=3),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        controls=left_controls,
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=right_controls,
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
        )
