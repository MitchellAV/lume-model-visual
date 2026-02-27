from trame.app import TrameApp
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3


class MyApp(TrameApp):
    def __init__(self, server=None):
        super().__init__(server=server)
        self._build_ui()

    def _build_ui(self):
        with SinglePageLayout(self.server) as layout:
            with layout.content:
                v3.VContainer(
                    "Hello, World!",
                    class_="fill-height",
                    align="center",
                    justify="center",
                )


def main():
    app = MyApp()
    app.server.start()


if __name__ == "__main__":
    main()
