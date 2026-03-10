import pprint
from typing import Any, Callable, Literal, cast

import pandas as pd

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller

from lume_model.models import TorchModel

from util import fix_out_of_range_value, sanitize_string, validate_state_key

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
    collect_and_update_plot: Callable[[], None]


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


class StateManager:
    PREFIX_INTERACTIVE_INPUT = "interactive_input_variable"
    PREFIX_INTERACTIVE_OUTPUT = "interactive_output_variable"
    PREFIX_INTERACTIVE_OUTPUT_DISPLAY = "interactive_output_display"

    PREFIX_STREAMING_INPUT = "streaming_input_variable"
    PREFIX_STREAMING_OUTPUT = "streaming_output_variable"
    PREFIX_STREAMING_OUTPUT_DISPLAY = "streaming_output_display"

    DEFAULT_OUTPUT_VALUE = "N/A"
    DEFAULT_OUTPUT_DISPLAY_VALUE = True

    interactive_history_df = pd.DataFrame()
    streaming_history_df = pd.DataFrame()

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

    def _initialize_interactive_variables(self) -> None:
        """Initialize state values for interactive mode variables."""
        # This method can be expanded to include any additional initialization logic

        # Input Variables
        for var in self.model.input_variables:
            if var.default_value is not None:
                corrected_default = fix_out_of_range_value(
                    var.default_value, var.value_range
                )

                key = f"{self.PREFIX_INTERACTIVE_INPUT}_{sanitize_string(var.name)}"

                self.set_state(
                    key,
                    corrected_default,
                )
                self.input_variable_names.append(var.name)

        column_names: list[str] = []

        # Output Variables
        for var in self.model.output_variables:
            output_key = f"{self.PREFIX_INTERACTIVE_OUTPUT}_{sanitize_string(var.name)}"

            self.set_state(
                output_key,
                self.DEFAULT_OUTPUT_VALUE,
            )

            # Display checkbox state for each output variable
            display_key = (
                f"{self.PREFIX_INTERACTIVE_OUTPUT_DISPLAY}_{sanitize_string(var.name)}"
            )

            self.set_state(
                display_key,
                self.DEFAULT_OUTPUT_DISPLAY_VALUE,
            )

            column_names.append(var.name)
            self.output_variable_names.append(var.name)

        self.interactive_history_df = pd.DataFrame(columns=column_names)
        output_dict = self.interactive_history_df.to_dict(orient="list")
        self.set_state("plot_data", output_dict)

    def _initialize_streaming_variables(self) -> None:
        """Initialize state values for streaming mode variables."""
        # Input Variables
        # No input variables for streaming mode since data is generated from PVs

        column_names: list[str] = []

        # Output Variables
        for var in PV_OUTPUT_NAMES:
            output_key = f"{self.PREFIX_STREAMING_OUTPUT}_{sanitize_string(var)}"

            self.set_state(
                output_key,
                self.DEFAULT_OUTPUT_VALUE,
            )

            # Display checkbox state for each output variable
            display_key = (
                f"{self.PREFIX_STREAMING_OUTPUT_DISPLAY}_{sanitize_string(var)}"
            )

            self.set_state(
                display_key,
                self.DEFAULT_OUTPUT_DISPLAY_VALUE,
            )

            column_names.append(var)
            self.output_variable_names.append(var)

        self.streaming_history_df = pd.DataFrame(columns=column_names)
        output_dict = self.streaming_history_df.to_dict(orient="list")
        self.set_state("plot_data", output_dict)

    def _initialize_variables(self) -> None:
        mode = cast(str, self.state["mode"])
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
        self.ctrl.on_server_ready = None  # type: ignore
        self.ctrl.start_streaming = None  # type: ignore
        self.ctrl.stop_streaming = None  # type: ignore

        self.ctrl.collect_and_update_plot = None  # type: ignore

        self.ctrl.update_plot = None  # type: ignore
        self.ctrl.evaluate_and_update_plot = None  # type: ignore
        self.ctrl.toggle_streaming = None  # type: ignore
        self.ctrl.toggle_mode = None  # type: ignore

    # def _toggle_mode(self) -> None:
    #     """Toggle between different modes (e.g., streaming vs. static)."""
    #     # This method can be expanded to include logic for toggling modes
    #     current_mode = self.state.mode
    #     if current_mode == "0":
    #         self.set_state("mode", "1")
    #     else:
    #         self.set_state("mode", "0")

    #     self.reset_state()  # Re-initialize variables for the new mode

    def stream_pv_data(self) -> None:
        """Simulate streaming data by generating random input values."""
        # https://pyepics.github.io/pyepics/advanced.html#advanced-connecting-many-label
        # for pv_name in PV_OUTPUT_NAMES:
        #     pv = epics.PV(pv_name)
        #     value = pv.get()
        #     # Update state with new PV value (this is just an example, adjust as needed)
        #     self.set_state(f"{self.PREFIX_OUTPUT}_{sanitize_string(pv_name)}", value)

        values = cast(list[float | None], epics.caget_many(PV_OUTPUT_NAMES))

        value_dict = dict(zip(PV_OUTPUT_NAMES, values))

        self.update_plot_data(value_dict)

    def update_plot_data(self, output: dict[str, float | None]) -> None:
        """Update the plot data in state with new model outputs."""
        # Append new output values to the history DataFrame
        output_df = cast(
            pd.DataFrame,
            pd.DataFrame.from_dict(self.state["plot_data"]),
        )

        row: dict[str, float | None] = {}

        for col in output_df.columns:
            if col not in output:
                output[col] = None
            value = output[col]
            if value is not None:
                value = float(value)
            row[col] = value
        print("New output row:")
        pprint.pprint(row)

        new_row = pd.DataFrame([row], columns=output_df.columns)

        print("New row DataFrame:")
        print(new_row.head())

        output_df = pd.concat([output_df, new_row], ignore_index=True)

        print("Updated output DataFrame:")
        print(output_df.head())

        prefix: str = ""

        if self.state.mode == "1":
            self.interactive_history_df = output_df
            prefix = self.PREFIX_INTERACTIVE_OUTPUT
        else:
            self.streaming_history_df = output_df
            prefix = self.PREFIX_STREAMING_OUTPUT
        self.set_state("plot_data", output_df.to_dict(orient="list"))

        print("Updated plot_data state:")
        pprint.pprint(self.state.plot_data)

        for key, value in row.items():
            state_key = f"{prefix}_{sanitize_string(key)}"
            self.set_state(state_key, value)

        self.state.dirty("plot_data")

    def reset_state(self) -> None:
        """Reset all state values to their defaults."""

        self.input_variable_names = []
        self.output_variable_names = []

        # mode = self.state.mode
        # if mode == "0":
        #     self.streaming_history_df = pd.DataFrame()
        # else:
        #     self.interactive_history_df = pd.DataFrame()

        # self.delete_variable_state(mode)

        self._initialize_variables()

    def delete_variable_state(self, mode: str) -> None:
        """Delete state values associated with a specific variable."""
        prefix = "interactive" if mode == "1" else "streaming"
        state_dict = cast(dict[str, Any], self.state.to_dict())

        keys_to_delete: list[str] = []

        for key in state_dict.keys():
            if prefix in key:
                keys_to_delete.append(key)

        for state_key in keys_to_delete:
            if self.state.has(state_key):
                del self.state[state_key]

    @property
    def state(self) -> St:
        return self.server.state  # type: ignore

    @property
    def ctrl(self) -> Ctrl:
        return self.server.controller  # type: ignore

    def get_mode_prefix(
        self, type: Literal["input", "output", "output_display"]
    ) -> str:
        """Get the appropriate state key prefix based on the current mode and variable type."""
        mode = self.state.mode
        if mode == "1":  # Interactive mode
            if type == "input":
                return self.PREFIX_INTERACTIVE_INPUT
            elif type == "output":
                return self.PREFIX_INTERACTIVE_OUTPUT
            elif type == "output_display":
                return self.PREFIX_INTERACTIVE_OUTPUT_DISPLAY
        else:  # Streaming mode
            if type == "input":
                return self.PREFIX_STREAMING_INPUT
            elif type == "output":
                return self.PREFIX_STREAMING_OUTPUT
            elif type == "output_display":
                return self.PREFIX_STREAMING_OUTPUT_DISPLAY

        raise ValueError(
            f"Invalid variable type: {type}. Must be 'input', 'output', or 'output_display'."
        )
