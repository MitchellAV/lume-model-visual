from trame_server.state import State
from trame_server.controller import Controller

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

from state import StateManager

from util import sanitize_string


class UI:
    counter: int = 0

    def __init__(self, state_manager: StateManager) -> None:
        self.state_manager = state_manager

        self._initialize_event_listeners()
        self._initialize_ui()
        self.evaluate_and_update_plot()

    @property
    def model(self) -> TorchModel:
        return self.state_manager.model

    @property
    def state(self) -> State:
        return self.state_manager.state

    @property
    def ctrl(self) -> Controller:
        return self.state_manager.ctrl

    def _initialize_event_listeners(self) -> None:
        self.ctrl.update_plot = self.update_plot
        self.ctrl.evaluate_and_update_plot = self.evaluate_and_update_plot
        self.ctrl.toggle_streaming = self.toggle_streaming

    def toggle_streaming(self) -> None:
        if self.state["streaming_active"]:
            self.ctrl.stop_streaming()
        else:
            self.ctrl.start_streaming()

    def _collect_input_values(self) -> dict[str, float]:
        input_dict: dict[str, float] = {}
        for var in self.model.input_variables:
            state_key = f"input_variables_{sanitize_string(var.name)}"
            state_value = self.state[state_key]
            bad_values = [None, "", "."]
            if state_value not in bad_values:
                try:
                    input_dict[var.name] = float(state_value)
                except ValueError as e:
                    print(
                        f"Warning: Could not convert state value '{state_value}' for variable '{var.name}' to float: {e}"
                    )
        return input_dict

    def _update_output_values(self, output: dict[str, float]) -> None:
        output_df = pd.DataFrame.from_dict(self.state["output_plot_data"])

        # cast all columns to float
        row = {col: float(output[col]) for col in output_df.columns}
        # Create new row with same columns as existing dataframe
        new_row = pd.DataFrame([row], columns=output_df.columns)
        output_df = pd.concat([output_df, new_row], ignore_index=True)

        self.state["output_plot_data"] = output_df.to_dict(orient="list")
        self.state.dirty("output_plot_data")

        for key, value in output.items():
            state_key = f"{self.state_manager.PREFIX_OUTPUT}_{sanitize_string(key)}"
            self.state[state_key] = float(value)

    def evaluate_model(self) -> None:
        input_dict = self._collect_input_values()
        output = self.model.evaluate(input_dict)
        self._update_output_values(output)

    def evaluate_and_update_plot(self) -> None:
        self.evaluate_model()
        self.update_plot()

    def _initialize_ui(self) -> None:
        with SinglePageLayout(self.state_manager.server) as layout:
            with layout.toolbar:
                pass

            with layout.icon:
                pass

            layout.title.set_text(  # pyright: ignore[reportUnknownMemberType]
                "LUME Model Visualizer"
            )

            with layout.content:
                layout.content.style = "max-height: 90vh;"
                self._initialize_content()

            with layout.footer:
                pass

    def _initialize_content(self) -> None:
        VBtn(
            "{{ streaming_status }}",
            position="fixed",
            style="z-index: 1000;",
            click=self.ctrl.toggle_streaming,
        )

        with VContainer(fluid=True):
            with VDivider():
                Div("Plot")
            with VRow():
                with VCol():
                    self._initialize_timeseries_plot()

                with VCol():
                    self._initialize_2d_histogram_plot()
        with VContainer(fluid=True):
            with VRow():
                with VCol():
                    with VDivider():
                        Div("Input Variables")
                    self._initialize_input_widgets()
                with VCol():
                    with VDivider():
                        Div("Output Variables")
                    self._initialize_output_widgets()

    def _initialize_2d_histogram_variables(self) -> None:
        with VContainer(fluid=True):
            # x variable
            VSelect(
                v_model=("hist_x_axis", "1:4"),
                items=("x_select",),
                label="X Variable",
                # update_modelValue=self.ctrl.update_plot,
            )
            # y variable
            VSelect(
                v_model=("hist_y_axis",),
                items=("y_select",),
                label="Y Variable",
                # update_modelValue=self.ctrl.update_plot,
            )

    def _initialize_output_widgets(self) -> None:
        with VContainer(fluid=True):
            for name in self.state_manager.output_variable_names:
                state_key = (
                    f"{self.state_manager.PREFIX_OUTPUT}_{sanitize_string(name)}"
                )
                with VRow():
                    with VCol():
                        Div(f"{name}")
                    with VCol():
                        VTextField(
                            v_model=(state_key,),
                            readonly=True,
                        )

    def _initialize_input_widgets(self) -> None:
        with VContainer(fluid=True, max_height="500px", style="overflow-y: auto;"):
            for var in self.model.input_variables:
                self._create_slider_for_variable(var)

    def _create_slider_for_variable(self, var: ScalarVariable) -> None:
        name = var.name

        if var.value_range is None:
            raise ValueError(
                f"Cannot create slider for variable '{name}' without value range."
            )
        value_range = var.value_range
        max = value_range[1]
        min = value_range[0]

        step = (max - min) / 100.0
        state_key = f"{self.state_manager.PREFIX_INPUT}_{sanitize_string(name)}"

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
                            end=self.evaluate_and_update_plot,
                        )
                        Div(f"{round(max, 2)}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                    )

    def _collect_values_by_variable_name(
        self, variable_names: list[str]
    ) -> pd.DataFrame:
        output_df = pd.DataFrame.from_dict(self.state["output_plot_data"]).copy()

        # Remove any columns not in variable_names
        output_df = output_df[variable_names]

        return output_df

    def _collect_plot_variables(self) -> list[str]:
        plot_variables: list[str] = []
        for name in self.state_manager.output_variable_names:
            state_key = (
                f"{self.state_manager.PREFIX_DISPLAY_OUTPUT}_{sanitize_string(name)}"
            )
            if self.state.has(state_key) and self.state[state_key]:
                plot_variables.append(name)
        return plot_variables

    def _initialize_2d_histogram_plot(self) -> None:
        with VContainer(fluid=True, style="position: relative; height: 400px;"):
            self.figure_hist = self._initialize_2d_histogram_figure()
        with VContainer(
            fluid=True,
            classes="d-flex flex-wrap",
        ):
            self._initialize_2d_histogram_variables()

    def _initialize_2d_histogram_figure(self) -> Figure:
        self.figure_hist = self._create_2d_histogram_figure()
        return Figure(figure=self.figure_hist, responsive=True)

    def _create_2d_histogram_figure(
        self,
    ) -> go.Figure:
        data = pd.DataFrame.from_dict(self.state["output_plot_data"])

        x_data = self.state["hist_x_axis"]
        y_data = self.state["hist_y_axis"]

        HISTOGRAM_BINS = None  # Use default binning strategy of plotly

        fig = px.density_heatmap(
            data_frame=data,
            x=x_data,
            y=y_data,
            nbinsx=HISTOGRAM_BINS,
            nbinsy=HISTOGRAM_BINS,
        )
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
        for var_name in self.state_manager.output_variable_names:
            with VCol():
                VCheckbox(
                    v_model=(
                        f"{self.state_manager.PREFIX_DISPLAY_OUTPUT}_{sanitize_string(var_name)}",
                    ),
                    label=var_name,
                    change=self.ctrl.update_plot,
                )

    def _initialize_timeseries_figure(self) -> Figure:
        self.figure_time = self._create_timeseries_figure()
        return Figure(figure=self.figure_time, responsive=True)

    def _create_timeseries_figure(
        self,
    ) -> go.Figure:
        output_plot_variables = self._collect_plot_variables()
        data = self._collect_values_by_variable_name(output_plot_variables)

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

    def _update_figure(self) -> None:
        fig1 = self._create_timeseries_figure()
        fig2 = self._create_2d_histogram_figure()

        self.figure_time.update(  # pyright: ignore[reportUnknownMemberType]
            plotly_fig=fig1
        )
        self.figure_hist.update(  # pyright: ignore[reportUnknownMemberType]
            plotly_fig=fig2
        )

    def update_plot(self) -> None:
        self._update_figure()
