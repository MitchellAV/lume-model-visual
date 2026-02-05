from typing import Any

from trame_server import Server
from trame_server.core import BackendType, ExecModeType
from trame.decorators import change

from trame.app import TrameApp

from lume_model.models import TorchModel

from state import StateManager


from ui import UI


class LUMEModelVisualApp(TrameApp):  # type: ignore[misc]
    server: Server  # pyright: ignore[reportIncompatibleMethodOverride]
    model: TorchModel

    DEFAULT_UPDATE_INTERVAL = 1.0  # seconds

    def __init__(
        self,
        model_path: str,
    ) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            client_type="vue3",
        )

        self.server.hot_reload = True

        self.load_model(model_path)
        self.state_manager = StateManager(self.server, self.model)
        self.ui = UI(self.state_manager)
        # self.start_clock()

    def load_model(self, model_path: str) -> None:
        self.model = TorchModel(model_path)

    # @self.server.controller.add_task()
    # async def update_loop():
    #     pass

    @change("hist_x_axis", "hist_y_axis")  # type: ignore
    def handle_hist_axis_change(self, *args: Any, **kwargs: Any) -> None:
        print("Axis changed, updating plot...")
        self.ui.update_plot()

    def start(
        self,
        port: int | None = None,
        thread: bool = False,
        open_browser: bool | None = None,
        show_connection_info: bool = True,
        disable_logging: bool = False,
        backend: BackendType | None = None,
        follow_symlinks: bool | None = None,
        exec_mode: ExecModeType = "main",
        timeout: int | None = None,
        host: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.server.start(  # pyright: ignore[reportUnknownMemberType]
            port=port,
            thread=thread,
            open_browser=open_browser,
            show_connection_info=show_connection_info,
            disable_logging=disable_logging,
            backend=backend,
            follow_symlinks=follow_symlinks,
            exec_mode=exec_mode,
            timeout=timeout,
            host=host,
            **kwargs,
        )
