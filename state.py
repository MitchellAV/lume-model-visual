import pandas as pd

from trame_server import Server
from trame_server.state import State
from trame_server.controller import Controller

from lume_model.models import TorchModel

from util import sanitize_string


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

    def _initialize_state(self) -> None:
        """Initialize state values for all input variables before UI creation."""

        for var in self.model.input_variables:
            if var.default_value is not None:
                self.state[f"{self.PREFIX_INPUT}_{sanitize_string(var.name)}"] = (
                    var.default_value
                )
                self.input_variable_names.append(var.name)

        column_names: list[str] = []

        for var in self.model.output_variables:
            self.state[f"{self.PREFIX_OUTPUT}_{sanitize_string(var.name)}"] = (
                self.DEFAULT_OUTPUT_VALUE
            )
            self.state[f"{self.PREFIX_DISPLAY_OUTPUT}_{sanitize_string(var.name)}"] = (
                self.DEFAULT_DISPLAY_OUTPUT_VALUE
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

        self.server.state["hist_x_axis"] = x_default
        self.server.state["hist_y_axis"] = y_default

        self.server.state["x_select"] = x_items
        self.server.state["y_select"] = y_items

    @property
    def state(self) -> State:
        return self.server.state

    @property
    def ctrl(self) -> Controller:
        return self.server.controller
