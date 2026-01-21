from typing import Any, Literal

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller
from trame_server.core import BackendType, ExecModeType

from trame.app import TrameApp
from trame.widgets import vuetify3 as v3
from trame.ui.vuetify3 import SinglePageLayout


class LUMEModelVisualApp(TrameApp):  # type: ignore[misc]
    server: Server  # pyright: ignore[reportIncompatibleMethodOverride]

    def __init__(
        self,
        name: str | Server | None = None,
        client_type: Literal["vue2", "vue3"] | None = "vue3",
        ctx_name: str | None = None,
    ) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            server=name,
            client_type=client_type,  # pyright: ignore[reportArgumentType]
            ctx_name=ctx_name,
        )

        self._initialize_state()
        self._initialize_ui()

    @property
    def state(self) -> State:
        return self.server.state

    @property
    def ctrl(self) -> Controller:
        return self.server.controller

    def _initialize_state(self) -> None:
        self.state.example_value = 42

    def _initialize_ui(self) -> None:
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(  # pyright: ignore[reportUnknownMemberType]
                "LUME Model Visualizer"
            )

            with layout.content:
                with v3.VContainer(fluid=True):
                    v3.VRangeSlider(
                        v_model="example_value",
                        min=0,
                        max=100,
                        step=1,
                        label="Example Value: {{ example_value }}",
                    )

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
