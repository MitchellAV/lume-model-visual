from typing import Any, Callable, Literal, cast
import asyncio

import pandas as pd

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller

from lume_model.models import TorchModel

from util import (
    fix_out_of_range_value,
    sanitize_string,
    validate_state_key,
    initialize_logger,
)

import epics

logger = initialize_logger(__name__)


class Ctrl(Controller):  # type: ignore[misc]
    on_server_ready: Callable[[], None]
    update_plot: Callable[[], None]
    evaluate_and_update_plot: Callable[[], None]
    collect_and_update_plot: Callable[[], None]
    reinitialize_ui: Callable[[], None]
    toggle_streaming: Callable[[], None]
    toggle_mode: Callable[[], None]


class St(State):  # type: ignore[misc]
    streaming_active: bool
    streaming_status: str
    hist_x_axis: str
    hist_y_axis: str
    x_select: list[dict[str, str]]
    y_select: list[dict[str, str]]
    plot_data: dict[str, list[float]]
    mode: str
    mode_options: list[dict[str, str]]
    interactive_input_variables: dict[str, float]
    interactive_output_variables: dict[str, float | str]
    interactive_output_checkboxes: dict[str, bool]
    streaming_input_variables: dict[str, float]
    streaming_output_variables: dict[str, float | str]
    streaming_output_checkboxes: dict[str, bool]


class StateManager:
    DEFAULT_UPDATE_INTERVAL = 1.0  # seconds

    INTERACTIVE_INPUT_VARIABLES = "interactive_input_variables"
    INTERACTIVE_OUTPUT_VARIABLES = "interactive_output_variables"
    INTERACTIVE_OUTPUT_CHECKBOXES = "interactive_output_checkboxes"

    STREAMING_INPUT_VARIABLES = "streaming_input_variables"
    STREAMING_OUTPUT_VARIABLES = "streaming_output_variables"
    STREAMING_OUTPUT_CHECKBOXES = "streaming_output_checkboxes"

    DEFAULT_OUTPUT_VALUE = "N/A"
    DEFAULT_OUTPUT_CHECKBOX_VALUE = True

    interactive_history_df = pd.DataFrame()
    streaming_history_df = pd.DataFrame()

    input_variable_names: list[str] = []
    output_variable_names: list[str] = []

    def __init__(
        self,
        server: Server,
        model_path: str,
        pv_output_names: list[str],
    ) -> None:
        self.server = server
        self.pv_output_names = pv_output_names

        self.load_model(model_path)

        self._initialize_state()
        self._initialize_event_handlers()

        self._initialize_coroutines()

    @property
    def state(self) -> St:
        return self.server.state  # type: ignore

    @property
    def ctrl(self) -> Ctrl:
        return self.server.controller  # type: ignore

    def load_model(self, model_path: str) -> None:
        self.model = TorchModel(model_path)
        logger.info(f"Model loaded from {model_path}")

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

    def _initialize_interactive_variables(self) -> None:
        """Initialize state values for interactive mode variables."""
        # This method can be expanded to include any additional initialization logic

        # Input Variables
        interactive_input_variables_dict: dict[str, float] = {}

        for var in self.model.input_variables:
            if var.default_value is not None:
                corrected_default = fix_out_of_range_value(
                    var.default_value, var.value_range
                )

                dict_key = sanitize_string(var.name)

                interactive_input_variables_dict[dict_key] = corrected_default
                self.input_variable_names.append(var.name)

        state_key = self.INTERACTIVE_INPUT_VARIABLES

        self.set_state(
            state_key,
            interactive_input_variables_dict,
        )

        # Output Variables

        interactive_output_variables_dict: dict[str, float | str] = {}
        interactive_output_checkboxes_dict: dict[str, bool] = {}

        column_names: list[str] = []

        for var in self.model.output_variables:
            s_var_name = sanitize_string(var.name)

            interactive_output_variables_dict[s_var_name] = self.DEFAULT_OUTPUT_VALUE

            interactive_output_checkboxes_dict[s_var_name] = (
                self.DEFAULT_OUTPUT_CHECKBOX_VALUE
            )

            column_names.append(var.name)
            self.output_variable_names.append(var.name)

        state_key = f"{self.INTERACTIVE_OUTPUT_VARIABLES}"

        self.set_state(
            state_key,
            interactive_output_variables_dict,
        )

        # Display checkbox state for each output variable
        display_key = f"{self.INTERACTIVE_OUTPUT_CHECKBOXES}"

        self.set_state(
            display_key,
            interactive_output_checkboxes_dict,
        )

        self.interactive_history_df = pd.DataFrame(columns=column_names)
        output_dict = self.interactive_history_df.to_dict(orient="list")
        self.set_state("plot_data", output_dict)

    def _initialize_streaming_variables(self) -> None:
        """Initialize state values for streaming mode variables."""
        # Input Variables
        streaming_input_variables_dict: dict[str, float] = {}
        self.set_state(self.STREAMING_INPUT_VARIABLES, streaming_input_variables_dict)
        # No input variables for streaming mode since data is generated from PVs

        column_names: list[str] = []

        # Output Variables

        streaming_output_variables_dict: dict[str, float | str] = {}
        streaming_output_checkboxes_dict: dict[str, bool] = {}

        for var in self.pv_output_names:
            s_var_name = sanitize_string(var)

            streaming_output_variables_dict[s_var_name] = self.DEFAULT_OUTPUT_VALUE

            streaming_output_checkboxes_dict[s_var_name] = (
                self.DEFAULT_OUTPUT_CHECKBOX_VALUE
            )

            column_names.append(var)
            self.output_variable_names.append(var)

        state_key = f"{self.STREAMING_OUTPUT_VARIABLES}"

        self.set_state(
            state_key,
            streaming_output_variables_dict,
        )

        # Display checkbox state for each output variable
        display_key = f"{self.STREAMING_OUTPUT_CHECKBOXES}"

        self.set_state(
            display_key,
            streaming_output_checkboxes_dict,
        )

        self.streaming_history_df = pd.DataFrame(columns=column_names)
        output_dict = self.streaming_history_df.to_dict(orient="list")
        self.set_state("plot_data", output_dict)

    def _initialize_variables(self) -> None:
        mode = self.state.mode
        if mode == "0":
            self._initialize_streaming_variables()
        else:
            self._initialize_interactive_variables()

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

    def _initialize_state(self) -> None:
        """Initialize state values for all input variables before UI creation."""

        # Initialize mode state (0 = Streaming Mode, 1 = Interactive Mode)
        self.set_state("mode", "1")  # Default to "Interactive Mode"
        self.set_state(
            "mode_options",
            [
                {"title": "Streaming Mode", "value": "0"},
                {"title": "Interactive Mode", "value": "1"},
            ],
        )

        # Initialize streaming state
        self.set_state("streaming_active", False)
        self.set_state("streaming_status", "Start Streaming")

        self._initialize_variables()

    def _initialize_event_handlers(self) -> None:
        """Initialize event handlers for streaming and plot updates."""
        # Event handlers are registered in the main app class using decorators
        self.ctrl.toggle_streaming = self._toggle_streaming
        self.ctrl.toggle_mode = self._toggle_mode

        # Set in ui.py after UI is initialized
        self.ctrl.collect_and_update_plot = None  # type: ignore
        self.ctrl.update_plot = None  # type: ignore
        self.ctrl.reinitialize_ui = None  # type: ignore
        self.ctrl.evaluate_and_update_plot = None  # type: ignore

    def _initialize_coroutines(self) -> None:
        """Initialize any background coroutines (like data streaming)."""
        # Coroutines are registered in the main app class using decorators
        self.ctrl.on_server_ready.add_task(self._data_stream_task)  # type: ignore

    def initialize_state_handlers(self) -> None:
        """Initialize state change handlers for interactive variables."""
        # State change handlers are registered in the main app class using decorators

        self.state.change("hist_x_axis", "hist_y_axis")(self._handle_hist_axis_change)
        self.state.change(
            self.INTERACTIVE_OUTPUT_CHECKBOXES, self.STREAMING_OUTPUT_CHECKBOXES
        )(self.ctrl.update_plot)
        # self.state.change(
        #     self.INTERACTIVE_INPUT_VARIABLES,
        #     self.STREAMING_INPUT_VARIABLES,
        # )(self.ctrl.evaluate_and_update_plot)

    async def _data_stream_task(self, *args: Any, **kwargs: Any) -> None:
        """Async task that simulates streaming data and updates plots."""
        logger.info("Starting data stream task...")
        while True:
            await asyncio.sleep(self.DEFAULT_UPDATE_INTERVAL)

            is_streaming_active = self.state.streaming_active
            if is_streaming_active:
                mode = self.state.mode

                if mode == "0":  # Streaming Mode
                    # Simulate streaming data by generating random input values
                    self.ctrl.collect_and_update_plot()
                elif mode == "1":  # Manual Mode
                    # Evaluate model and update plots
                    self.ctrl.evaluate_and_update_plot()
                # Required to ensure UI updates are sent to the client
                self.state.flush()

    def _handle_hist_axis_change(self, *args: Any, **kwargs: Any) -> None:
        self.ctrl.update_plot()

    def _toggle_mode(self, *args: Any, **kwargs: Any) -> None:
        current_mode = self.state.mode
        if current_mode == "0":
            self.set_state("mode", "1")
        else:
            self.set_state("mode", "0")

        self.reset_state()  # Re-initialize variables for the new mode
        self.ctrl.reinitialize_ui()

    def _toggle_streaming(self) -> None:
        if self.state.streaming_active:
            self.set_state("streaming_active", False)
            self.set_state("streaming_status", "Start Streaming")
        else:
            self.set_state("streaming_active", True)
            self.set_state("streaming_status", "Stop Streaming")

    def stream_pv_data(self) -> None:
        """Simulate streaming data by generating random input values."""
        # https://pyepics.github.io/pyepics/advanced.html#advanced-connecting-many-label

        # for pv_name in self.pv_output_names:
        #     pv = epics.PV(pv_name)
        #     value = pv.get()
        #     # Update state with new PV value (this is just an example, adjust as needed)
        #     self.set_state(f"{self.PREFIX_OUTPUT}_{sanitize_string(pv_name)}", value)

        values = cast(list[float | None], epics.caget_many(self.pv_output_names))

        value_dict = dict(zip(self.pv_output_names, values))

        self.update_plot_data(value_dict)

    def update_plot_data(self, output: dict[str, float | None]) -> None:
        """Update the plot data in state with new model outputs."""
        # Append new output values to the history DataFrame
        output_df = cast(
            pd.DataFrame,
            pd.DataFrame.from_dict(self.state.plot_data),
        )

        row: dict[str, float | None] = {}

        for col in output_df.columns:
            if col not in output:
                output[col] = None
            value = output[col]
            if value is not None:
                value = float(value)
            row[col] = value

        new_row = pd.DataFrame([row], columns=output_df.columns)

        output_df = pd.concat([output_df, new_row], ignore_index=True)

        prefix: str = ""

        if self.state.mode == "1":
            self.interactive_history_df = output_df
            prefix = self.INTERACTIVE_OUTPUT_VARIABLES
        else:
            self.streaming_history_df = output_df
            prefix = self.STREAMING_OUTPUT_VARIABLES
        self.set_state("plot_data", output_df.to_dict(orient="list"))

        row_dict: dict[str, float | str] = {}

        for key, value in row.items():
            state_key = f"{sanitize_string(key)}"
            v: float | str = (
                value if value is not None else str(self.DEFAULT_OUTPUT_VALUE)
            )
            row_dict[state_key] = v

        self.set_state(prefix, row_dict)

        self.state.dirty("plot_data")

    def reset_state(self) -> None:
        """Reset all state values to their defaults."""

        self.input_variable_names = []
        self.output_variable_names = []

        self._initialize_variables()

    def get_mode_prefix(
        self, type: Literal["input", "output", "output_display"]
    ) -> str:
        """Get the appropriate state key prefix based on the current mode and variable type."""
        mode = self.state.mode
        if mode == "1":  # Interactive mode
            if type == "input":
                return self.INTERACTIVE_INPUT_VARIABLES
            elif type == "output":
                return self.INTERACTIVE_OUTPUT_VARIABLES
            elif type == "output_display":
                return self.INTERACTIVE_OUTPUT_CHECKBOXES
        else:  # Streaming mode
            if type == "input":
                return self.STREAMING_INPUT_VARIABLES
            elif type == "output":
                return self.STREAMING_OUTPUT_VARIABLES
            elif type == "output_display":
                return self.STREAMING_OUTPUT_CHECKBOXES

        raise ValueError(
            f"Invalid variable type: {type}. Must be 'input', 'output', or 'output_display'."
        )
