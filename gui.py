from typing import Any
import asyncio

from trame_server import Server
from trame_server.core import BackendType, ExecModeType
from trame.decorators import change, life_cycle, controller

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

        self.load_model(model_path)
        self.state_manager = StateManager(self.server, self.model)
        self.ui = UI(self.state_manager)
        self.streaming_enabled = False

    def load_model(self, model_path: str) -> None:
        self.model = TorchModel(model_path)

    @controller.add_task("on_server_ready")  # type: ignore
    async def data_stream_task(self, *args: Any, **kwargs: Any) -> None:
        """Async task that simulates streaming data and updates plots."""
        print("Starting data stream task...")
        while True:
            await asyncio.sleep(self.DEFAULT_UPDATE_INTERVAL)

            if self.streaming_enabled:
                print("Updating model outputs with new streaming data...")
                # Evaluate model and update plots
                self.ui.ctrl.evaluate_and_update_plot()
                # Required to ensure UI updates are sent to the client
                self.state.flush()

    @controller.add("start_streaming")  # type: ignore
    def start_streaming(self, *args: Any, **kwargs: Any) -> None:
        print("Starting data stream...")
        self.streaming_enabled = True
        self.server.state["streaming_active"] = True
        self.server.state["streaming_status"] = "Stop Streaming"

    @controller.add("stop_streaming")  # type: ignore
    def stop_streaming(self, *args: Any, **kwargs: Any) -> None:
        print("Stopping data stream...")
        self.streaming_enabled = False
        self.server.state["streaming_active"] = False
        self.server.state["streaming_status"] = "Start Streaming"

    @change("hist_x_axis", "hist_y_axis")  # type: ignore
    def handle_hist_axis_change(self, *args: Any, **kwargs: Any) -> None:
        self.ui.update_plot()

    @life_cycle.error  # type: ignore
    def handle_error(self, error: Exception) -> None:
        raise error

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
