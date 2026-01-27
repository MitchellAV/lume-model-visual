from typing import Any

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller
from trame_server.core import BackendType, ExecModeType

from trame.app import TrameApp

from lume_model.models import TorchModel

from ui import UI

from util import sanitize_string


class LUMEModelVisualApp(TrameApp):  # type: ignore[misc]
    server: Server  # pyright: ignore[reportIncompatibleMethodOverride]
    model: TorchModel

    def __init__(
        self,
        model_path: str,
    ) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            client_type="vue3",
        )

        self.load_model(model_path)
        self._initialize_state()
        self.ui = UI(self.server, self.model)

    @property
    def state(self) -> State:
        return self.server.state

    @property
    def ctrl(self) -> Controller:
        return self.server.controller

    def _initialize_state(self) -> None:
        """Initialize state values for all input variables before UI creation."""

        # _input_variables = {}

        for var in self.model.input_variables:
            if var.default_value is not None:
                self.state[f"input_variables_{sanitize_string(var.name)}"] = (
                    var.default_value
                )

        for var in self.model.output_variables:
            DEFAULT_OUTPUT_VALUE = "N/A"
            self.state[f"output_variables_{sanitize_string(var.name)}"] = (
                DEFAULT_OUTPUT_VALUE
            )

    def load_model(self, model_path: str) -> None:
        self.model = TorchModel(model_path)

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
