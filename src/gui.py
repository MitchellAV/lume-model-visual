from typing import Any

from trame.app import TrameApp
from trame.decorators import life_cycle
from trame_server import Server
from trame_server.core import BackendType, ExecModeType

from lume_model.models import TorchModel

from state import StateManager
from ui import UI

from util import initialize_logger

logger = initialize_logger(__name__)


class LUMEModelVisualApp(TrameApp):  # type: ignore[misc]
    server: Server  # pyright: ignore[reportIncompatibleMethodOverride]
    model: TorchModel

    def __init__(
        self,
        model_path: str,
        pv_output_names: list[str] | None = None,
    ) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            client_type="vue3",
        )

        if pv_output_names is None:
            pv_output_names = []

        self.load_model(model_path)
        self.state_manager = StateManager(self.server, self.model, pv_output_names)
        self.ui = UI(self.state_manager)
        self.streaming_enabled = False

    def load_model(self, model_path: str) -> None:
        self.model = TorchModel(model_path)
        logger.info(f"Model loaded from {model_path}")

    @life_cycle.error  # type: ignore
    def on_error(self, error: Exception) -> None:
        logger.error(f"An error occurred: {error}")
        raise error

    @life_cycle.exception  # type: ignore
    def on_exception(self, exception: Exception) -> None:
        logger.exception(f"An exception occurred: {exception}")
        raise exception

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
