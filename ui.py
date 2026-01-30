from trame_server import Server

import numpy as np

from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets.html import Div
from trame.widgets.vuetify3 import (
    VContainer,
    VSlider,
    VTextField,
    VBtn,
    VRow,
    VCol,
    VDivider,
    VCheckbox,
)
import plotly.graph_objects as go
from trame.widgets.plotly import Figure

from lume_model.models import TorchModel
from lume_model.variables import ScalarVariable

from util import sanitize_string

from pprint import pprint


class UI:
    counter: int = 0
    data: dict[str, list[float]] = {}

    def __init__(self, server: Server, model: TorchModel) -> None:
        self.server = server
        self.model = model

        self._initialize_ui()

    def _collect_input_values(self) -> dict[str, float]:
        input_dict: dict[str, float] = {}
        for var in self.model.input_variables:
            state_key = f"input_variables_{sanitize_string(var.name)}"
            state_value = self.server.state[state_key]
            if state_value is not None:
                try:
                    input_dict[var.name] = float(state_value)
                except ValueError as e:
                    print(
                        f"Warning: Could not convert state value '{state_value}' for variable '{var.name}' to float: {e}"
                    )
        return input_dict

    def _update_output_values(self, output: dict[str, float]) -> None:
        for key, value in output.items():
            state_key = f"output_variables_{sanitize_string(key)}"
            self.server.state[state_key] = float(value)

            prev_data_dict = self.server.state["output_plot_data"]

            for plot_key in prev_data_dict:
                if plot_key == key:
                    prev_data_dict[plot_key].append(float(value))

    def _evauate_model(self) -> None:
        input_dict = self._collect_input_values()

        output = self.model.evaluate(input_dict)

        print("Model output:")
        pprint(output)
        self._update_output_values(output)

    def _handle_update_plot(self) -> None:
        self._evauate_model()

        self._update_plot()

    def _initialize_ui(self) -> None:
        with SinglePageLayout(self.server) as layout:
            with layout.toolbar:
                pass

            with layout.icon:
                pass

            layout.title.set_text(  # pyright: ignore[reportUnknownMemberType]
                "LUME Model Visualizer"
            )

            with layout.content:
                self._initialize_content()

            with layout.footer:
                pass

    def _initialize_content(self) -> None:
        input_variables = sorted(self.model.input_variables, key=lambda var: var.name)

        output_variables = sorted(self.model.output_variables, key=lambda var: var.name)

        with VContainer(fluid=True):
            VBtn(
                "Run Model",
                click=self._handle_update_plot,
            )
            with VDivider():
                Div("Plot")
            self._initialize_plot()

            with VDivider():
                Div("Output Variables")
            with VContainer(fluid=True):
                for var in output_variables:
                    name = var.name

                    state_key = f"output_variables_{sanitize_string(name)}"

                    with VRow():
                        with VCol():
                            Div(f"{name}")
                        with VCol():
                            VTextField(
                                v_model=(state_key,),
                                readonly=True,
                            )
            with VDivider():
                Div("Input Variables")
            self._initialize_input_widgets(input_variables)

    def _initialize_input_widgets(self, input_variables: list[ScalarVariable]) -> None:
        with VContainer(fluid=True):
            for index, var in enumerate(input_variables):
                self._create_slider_for_variable(index, var)

    def _create_slider_for_variable(self, index: int, var: ScalarVariable) -> None:
        name = var.name

        if var.value_range is None:
            raise ValueError(
                f"Cannot create slider for variable '{name}' without value range."
            )
        value_range = var.value_range
        max = value_range[1]
        min = value_range[0]

        step = (max - min) / 100.0
        state_key = f"input_variables_{sanitize_string(name)}"

        print(f"Creating slider for variable '{name}' with state key '{state_key}'")

        if step <= 0:
            with VRow():
                with VCol():
                    Div(f"{name}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                        readonly=True,
                    )
        else:
            with VRow():
                with VCol():
                    Div(f"{name}")
                    with VRow(
                        style="margin: 0 auto;",
                    ):
                        Div(f"{round(min, 2)} ")
                        VSlider(
                            v_model=(state_key,),
                            min=min,
                            max=max,
                            step=step,
                            # start="flushState('input_variables')",
                            # thumb_label=True,
                            end=self._handle_update_plot,
                        )
                        Div(f"{round(max, 2)}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                    )

    def _collect_values_by_variable_name(
        self, variable_names: list[str]
    ) -> dict[str, list[float]]:
        output_plot_data: dict[str, list[float]] = self.server.state[
            "output_plot_data"
        ].copy()

        for output_var in list(output_plot_data.keys()):
            if output_var not in variable_names:
                output_plot_data.pop(output_var)
        return output_plot_data

    def _collect_plot_variables(self) -> list[str]:
        plot_variables: list[str] = []
        for var in self.model.output_variables:
            state_key = f"plot_variable_{sanitize_string(var.name)}"
            if self.server.state.has(state_key) and self.server.state[state_key]:
                plot_variables.append(var.name)

        pprint("Collecting plot variables:")
        pprint(self._collect_values_by_variable_name(plot_variables))
        return plot_variables

    def _handle_variable_plot_change(
        self,
    ) -> None:
        self._update_plot()

    def _initialize_plot(self) -> None:
        # Requires height to display properly
        with VContainer(fluid=True, style="position: relative; height: 400px;"):
            self.figure = self._initialize_figure()
        with VContainer(fluid=True):
            self._create_variables_to_plot()
            self._handle_update_plot()

    def _create_variables_to_plot(self) -> None:
        output_variable_names = [var.name for var in self.model.output_variables]
        for var_name in output_variable_names:
            VCheckbox(
                v_model=(f"plot_variable_{sanitize_string(var_name)}", True),
                label=var_name,
                change=self._handle_variable_plot_change,
            )

    def _initialize_figure(self, data: dict[str, list[float]] | None = None) -> Figure:
        self.figure = self._create_figure(data)
        return Figure(figure=self.figure, responsive=True)

    def _create_figure(
        self,
        data: dict[str, list[float]] | None = None,
    ) -> go.Figure:
        if data is None:
            data = {
                "var1": [np.random.rand() for _ in range(10)],
                "var2": [np.random.rand() for _ in range(10)],
            }

        plots = []

        for name, values in data.items():
            x_data = np.linspace(0, 1, len(values)).tolist()
            plots.append(  # pyright: ignore[reportUnknownMemberType]
                go.Scatter(
                    x=x_data,
                    y=values,
                    mode="lines+markers",
                    name=name,
                )
            )

        return go.Figure(data=plots)

    def _update_figure(self, data: dict[str, list[float]] | None = None) -> None:
        fig = self._create_figure(data)

        self.figure.update(plotly_fig=fig)  # pyright: ignore[reportUnknownMemberType]

    def _update_plot(self) -> None:
        output_plot_variables = self._collect_plot_variables()

        data: dict[str, list[float]] = self._collect_values_by_variable_name(
            output_plot_variables
        )
        self._update_figure(data)
