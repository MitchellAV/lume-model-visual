from typing import Callable

import pandas as pd

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller

from lume_model.models import TorchModel

from util import sanitize_string, validate_state_key

import epics

PV_OUTPUT_NAMES = [
    "OTRS:IN20:571:XRMS_CU_HXR_LUME",
    "OTRS:IN20:571:YRMS_CU_HXR_LUME",
    "OTRS:IN20:571:EMITN_X_CU_HXR_LUME",
    "OTRS:IN20:571:EMITN_Y_CU_HXR_LUME",
    "OTRS:IN20:571:EMIT_X_CU_HXR_LUME",
    "OTRS:IN20:571:EMIT_Y_CU_HXR_LUME",
    "OTRS:IN20:571:ZRMS_CU_HXR_LUME",
]


class Ctrl(Controller):  # type: ignore[misc]
    on_server_ready: Callable[[], None]
    start_streaming: Callable[[], None]
    stop_streaming: Callable[[], None]
    update_plot: Callable[[], None]
    evaluate_and_update_plot: Callable[[], None]
    toggle_streaming: Callable[[], None]
    toggle_mode: Callable[[], None]
    stream_pv_data: Callable[[], None]


class St(State):  # type: ignore[misc]
    streaming_active: bool
    streaming_status: str
    hist_x_axis: str
    hist_y_axis: str
    x_select: list[dict[str, str]]
    y_select: list[dict[str, str]]
    output_plot_data: dict[str, list[float]]


class StateManager:
    PREFIX_INPUT = "input_variables"
    PREFIX_OUTPUT = "output_variables"
    PREFIX_DISPLAY_OUTPUT = "display_output_variables"
    DEFAULT_OUTPUT_VALUE = "N/A"
    DEFAULT_DISPLAY_OUTPUT_VALUE = True

    input_variable_names: list[str] = []
    output_variable_names: list[str] = []

    def __init__(self, server: Server, model: TorchModel) -> None:
        self.server = server
        self.model = model

        self._initialize_state()
        self._initialize_event_handlers()

    def set_state(self, key: str, value: object) -> None:
        """Set a state value with server-side key validation.

        This validates the key before setting it in trame state, catching
        invalid characters (like ':') that would cause silent client-side
        JavaScript errors.

        Args:
            key: The state key (must be a valid JavaScript identifier).
            value: The value to set.
        Raises:
            ValueError: If the key is not a valid JavaScript identifier.
        """
        validate_state_key(key)
        self.state[key] = value

    def _initialize_state(self) -> None:
        """Initialize state values for all input variables before UI creation."""

        for var in self.model.input_variables:
            if var.default_value is not None:
                min_range = var.value_range[0] if var.value_range is not None else None
                max_range = var.value_range[1] if var.value_range is not None else None

                # Ensure default value is within specified range if range is defined
                corrected_default = var.default_value
                if min_range is not None and max_range is not None:
                    if var.default_value < min_range:
                        corrected_default = min_range
                    elif var.default_value > max_range:
                        corrected_default = max_range

                corrected_default = round(corrected_default, 2)

                print(
                    f'Initializing input variable "{var.name}" with default value: {corrected_default}'
                )

                self.set_state(
                    f"{self.PREFIX_INPUT}_{sanitize_string(var.name)}",
                    corrected_default,
                )
                self.input_variable_names.append(var.name)

        column_names: list[str] = []

        for var in self.model.output_variables:
            self.set_state(
                f"{self.PREFIX_OUTPUT}_{sanitize_string(var.name)}",
                self.DEFAULT_OUTPUT_VALUE,
            )
            self.set_state(
                f"{self.PREFIX_DISPLAY_OUTPUT}_{sanitize_string(var.name)}",
                self.DEFAULT_DISPLAY_OUTPUT_VALUE,
            )

            column_names.append(var.name)
            self.output_variable_names.append(var.name)

        output_df = pd.DataFrame(columns=column_names)
        output_dict = output_df.to_dict(orient="list")
        self.state["output_plot_data"] = output_dict

        x_items = [
            {"title": name, "value": name} for name in self.output_variable_names
        ]
        y_items = [
            {"title": name, "value": name} for name in self.output_variable_names
        ]

        DEFAULT_X = 0
        DEFAULT_Y = 1 if len(self.output_variable_names) > 1 else 0
        x_default = self.output_variable_names[DEFAULT_X]
        y_default = self.output_variable_names[DEFAULT_Y]

        self.set_state("hist_x_axis", x_default)
        self.set_state("hist_y_axis", y_default)

        self.set_state("x_select", x_items)
        self.set_state("y_select", y_items)

        # Initialize streaming state
        self.set_state("streaming_active", False)
        self.set_state("streaming_status", "Start Streaming")

        # Initialize mode state (if needed)
        self.set_state("mode", "0")  # Default to "Streaming Mode"
        self.set_state(
            "mode_options",
            [
                {"title": "Streaming Mode", "value": "0"},
                {"title": "Interactive Mode", "value": "1"},
            ],
        )

    def _initialize_event_handlers(self) -> None:
        """Initialize event handlers for streaming and plot updates."""
        # Event handlers are registered in the main app class using decorators
        self.ctrl.on_server_ready = None  # type: ignore
        self.ctrl.start_streaming = None  # type: ignore
        self.ctrl.stop_streaming = None  # type: ignore

        self.ctrl.stream_pv_data = self._stream_pv_data

        self.ctrl.update_plot = None  # type: ignore
        self.ctrl.evaluate_and_update_plot = None  # type: ignore
        self.ctrl.toggle_streaming = None  # type: ignore
        self.ctrl.toggle_mode = self._toggle_mode

    def _toggle_mode(self) -> None:
        """Toggle between different modes (e.g., streaming vs. static)."""
        # This method can be expanded to include logic for toggling modes
        current_mode = str(self.state["mode"])
        if current_mode == "0":
            self.set_state("mode", "1")
        else:
            self.set_state("mode", "0")

    def _stream_pv_data(self) -> None:
        """Simulate streaming data by generating random input values."""
        # https://pyepics.github.io/pyepics/advanced.html#advanced-connecting-many-label
        # for pv_name in PV_OUTPUT_NAMES:
        #     pv = epics.PV(pv_name)
        #     value = pv.get()
        #     # Update state with new PV value (this is just an example, adjust as needed)
        #     self.set_state(f"{self.PREFIX_OUTPUT}_{sanitize_string(pv_name)}", value)

        values = epics.caget_many(PV_OUTPUT_NAMES)
        for pv_name, value in zip(PV_OUTPUT_NAMES, values):
            self.set_state(f"{self.PREFIX_OUTPUT}_{sanitize_string(pv_name)}", value)

    @property
    def state(self) -> St:
        return self.server.state  # type: ignore

    @property
    def ctrl(self) -> Ctrl:
        return self.server.controller  # type: ignore
