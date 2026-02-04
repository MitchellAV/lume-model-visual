from trame_server import Server

import numpy as np
import pandas as pd

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
    VSelect,
)
import plotly.graph_objects as go
import plotly.express as px
from trame.widgets.plotly import Figure

from lume_model.models import TorchModel
from lume_model.variables import ScalarVariable

from util import sanitize_string

from pprint import pprint


class UI:
    counter: int = 0

    def __init__(self, server: Server, model: TorchModel) -> None:
        self.server = server
        self.model = model

        self.state = server.state
        self.ctrl = server.controller

        self.ctrl.update_plot = self._update_plot

        self._initialize_ui()
        self._evaluate_and_update_plot()

    def _collect_input_values(self) -> dict[str, float]:
        input_dict: dict[str, float] = {}
        for var in self.model.input_variables:
            state_key = f"input_variables_{sanitize_string(var.name)}"
            state_value = self.state[state_key]
            if state_value is not None:
                try:
                    input_dict[var.name] = float(state_value)
                except ValueError as e:
                    print(
                        f"Warning: Could not convert state value '{state_value}' for variable '{var.name}' to float: {e}"
                    )
        return input_dict

    def _update_output_values(self, output: dict[str, float]) -> None:
        output_df = pd.DataFrame.from_dict(dict(self.state["output_plot_data"]))

        # cast all columns to float
        row = {col: float(output[col]) for col in output_df.columns}
        # Create new row with same columns as existing dataframe
        new_row = pd.DataFrame([row], columns=output_df.columns)
        output_df = pd.concat([output_df, new_row], ignore_index=True)

        self.state["output_plot_data"] = output_df.to_dict(orient="list")
        self.state.dirty("output_plot_data")
        for key, value in output.items():
            state_key = f"output_variables_{sanitize_string(key)}"
            self.state[state_key] = float(value)

    def _evaluate_model(self) -> None:
        input_dict = self._collect_input_values()

        output = self.model.evaluate(input_dict)

        print("Model output:")
        pprint(output)
        self._update_output_values(output)

    def _evaluate_and_update_plot(self) -> None:
        self._evaluate_model()

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
        self.input_variables = sorted(
            self.model.input_variables, key=lambda var: var.name
        )

        self.output_variables = sorted(
            self.model.output_variables, key=lambda var: var.name
        )

        VBtn(
            "Run Model",
            click=self._evaluate_and_update_plot,
        )

        with VContainer(fluid=True):
            with VRow():
                with VCol():
                    with VDivider():
                        Div("Output Variables")
                    self._initialize_output_widgets(self.output_variables)
                with VCol():
                    with VDivider():
                        Div("Plot")
                    self._initialize_timeseries_plot()
                    self._initialize_2d_histogram_plot()

        with VDivider():
            Div("Input Variables")
        self._initialize_input_widgets(self.input_variables)

    def _initialize_2d_histogram_variables(self) -> None:
        with VContainer(fluid=True):
            # x variable
            VSelect(
                v_model=("hist_x_axis",),
                items=("x_select",),
                label="X Variable",
                update_modelValue=self.ctrl.update_plot,
            )
            # y variable
            VSelect(
                v_model=("hist_y_axis",),
                items=("y_select",),
                label="Y Variable",
                update_modelValue=self.ctrl.update_plot,
            )

    def _initialize_output_widgets(
        self, output_variables: list[ScalarVariable]
    ) -> None:
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
                            end=self._evaluate_and_update_plot,
                        )
                        Div(f"{round(max, 2)}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                    )

    def _collect_values_by_variable_name(
        self, variable_names: list[str]
    ) -> pd.DataFrame:
        output_plot_data = pd.DataFrame.from_dict(self.state["output_plot_data"]).copy(
            deep=True
        )

        # for output_var in list(output_plot_data.keys()):
        #     if output_var not in variable_names:
        #         output_plot_data.pop(output_var)
        return output_plot_data

    def _collect_plot_variables(self) -> list[str]:
        plot_variables: list[str] = []
        for var in self.model.output_variables:
            state_key = f"plot_variable_{sanitize_string(var.name)}"
            if self.state.has(state_key) and self.state[state_key]:
                plot_variables.append(var.name)

        pprint("Collecting plot variables:")
        pprint(self._collect_values_by_variable_name(plot_variables))
        return plot_variables

    def _handle_variable_plot_change(
        self,
    ) -> None:
        self._update_plot()

    def _initialize_2d_histogram_plot(self) -> None:
        with VContainer(fluid=True, style="position: relative; height: 400px;"):
            self.figure_hist = self._initialize_2d_histogram_figure()
        with VContainer(
            fluid=True,
            classes="d-flex flex-wrap",
        ):
            self._initialize_2d_histogram_variables()
            self._evaluate_and_update_plot()

    def _initialize_2d_histogram_figure(
        self, data: pd.DataFrame | None = None
    ) -> Figure:
        self.figure_hist = self._create_2d_histogram_figure(data)
        return Figure(figure=self.figure_hist, responsive=True)

    def _create_2d_histogram_figure(
        self, data: pd.DataFrame | None = None
    ) -> go.Figure:
        x_data: str
        y_data: str

        if data is None:
            data = pd.DataFrame(
                {
                    "var1": [np.random.rand() for _ in range(10)],
                    "var2": [np.random.rand() for _ in range(10)],
                }
            )
            data = pd.DataFrame(data)
            x_data = "var1"
            y_data = "var2"
        else:
            x_data = self.state["hist_x_axis"]
            y_data = self.state["hist_y_axis"]

        pprint((x_data, y_data))

        fig = px.density_heatmap(data_frame=data, x=x_data, y=y_data)
        return fig

    def _initialize_timeseries_plot(self) -> None:
        # Requires height to display properly
        with VContainer(fluid=True, style="position: relative; height: 400px;"):
            self.figure_time = self._initialize_timeseries_figure()
        with VContainer(
            fluid=True,
            classes="d-flex flex-wrap",
        ):
            self._create_variables_to_plot()

    def _create_variables_to_plot(self) -> None:
        output_variable_names = [var.name for var in self.model.output_variables]
        for var_name in output_variable_names:
            with VCol():
                VCheckbox(
                    v_model=(f"plot_variable_{sanitize_string(var_name)}", True),
                    label=var_name,
                    change=self._handle_variable_plot_change,
                )

    def _initialize_timeseries_figure(self, data: pd.DataFrame | None = None) -> Figure:
        self.figure_time = self._create_timeseries_figure(data)
        return Figure(figure=self.figure_time, responsive=True)

    def _create_timeseries_figure(
        self,
        data: pd.DataFrame | None = None,
    ) -> go.Figure:
        if data is None:
            data = {
                "var1": [np.random.rand() for _ in range(10)],
                "var2": [np.random.rand() for _ in range(10)],
            }
            data = pd.DataFrame(data)

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

    def _update_figure(self, data: pd.DataFrame | None = None) -> None:
        fig1 = self._create_timeseries_figure(data)
        fig2 = self._create_2d_histogram_figure(data)

        print("Updating figures")
        self.figure_time.update(plotly_fig=fig1)  # pyright: ignore[reportUnknownMemberType]
        self.figure_hist.update(plotly_fig=fig2)  # pyright: ignore[reportUnknownMemberType]

    def _update_plot(self) -> None:
        self.state.flush()
        output_plot_variables = self._collect_plot_variables()

        data = self._collect_values_by_variable_name(output_plot_variables)
        self._update_figure(data)
