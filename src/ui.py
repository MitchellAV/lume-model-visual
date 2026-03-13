from typing import cast

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

from state import Ctrl, St, StateManager

from util import sanitize_string, initialize_logger

logger = initialize_logger(__name__)


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
    def state(self) -> St:
        return self.state_manager.state

    @property
    def ctrl(self) -> Ctrl:
        return self.state_manager.ctrl

    def _initialize_event_listeners(self) -> None:
        self.ctrl.update_plot = self.update_plot
        self.ctrl.evaluate_and_update_plot = self.evaluate_and_update_plot
        self.ctrl.collect_and_update_plot = self.collect_and_update_plot
        self.ctrl.reinitialize_ui = self.reinitialize_ui

    def collect_and_update_plot(self) -> None:
        self.state_manager.stream_pv_data()
        self.update_plot()

    def evaluate_and_update_plot(self) -> None:
        self.evaluate_model()
        self.update_plot()

    def _collect_input_values(self) -> dict[str, float]:
        input_dict: dict[str, float] = {}
        prefix = self.state_manager.get_mode_prefix("input")
        for var in self.model.input_variables:
            state_key = f"{prefix}_{sanitize_string(var.name)}"
            if not self.state.has(state_key):
                continue
            state_value = self.state[state_key]
            bad_values: list[object] = [None, "", "."]
            if state_value not in bad_values:
                try:
                    input_dict[var.name] = float(state_value)
                except ValueError as e:
                    logger.warning(
                        f"Could not convert state value '{state_value}' for variable '{var.name}' to float: {e}"
                    )
        return input_dict

    def evaluate_model(self) -> None:
        input_dict = self._collect_input_values()
        output = self.model.evaluate(input_dict)
        self.state_manager.update_plot_data(output)

    def reinitialize_ui(self) -> None:
        """Reinitialize the UI, for example after loading a new model."""
        self._initialize_ui()

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
            position="left",
            style="z-index: 1000;",
            click=self.ctrl.toggle_streaming,
        )

        with VContainer(fluid=True):
            VBtn(
                "{{ mode_options[mode].title }}",
                position="right",
                style="z-index: 1000;",
                click=self.ctrl.toggle_mode,
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
                v_model=("hist_x_axis",),
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
        prefix = self.state_manager.get_mode_prefix("output")
        with VContainer(fluid=True):
            for name in self.state_manager.output_variable_names:
                state_key = f"{prefix}_{sanitize_string(name)}"
                with VRow():
                    with VCol():
                        Div(f"{name}")
                    with VCol():
                        VTextField(
                            v_model=(state_key,),
                            readonly=True,
                        )

    def _initialize_input_widgets(self) -> None:
        mode = self.state_manager.state.mode
        if mode == "1":
            with VContainer(fluid=True, max_height="500px", style="overflow-y: auto;"):
                for var in self.model.input_variables:
                    self._create_slider_for_variable(var)

    def _create_slider_for_variable(self, var: ScalarVariable) -> None:
        name = var.name

        if var.value_range is None:
            raise ValueError(
                f"Cannot create slider for variable '{name}' without value range."
            )
        min_value, max_value = var.value_range

        step = (max_value - min_value) / 100.0

        prefix = self.state_manager.get_mode_prefix("input")

        state_key = f"{prefix}_{sanitize_string(name)}"

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
                        Div(f"{round(min_value, 2)} ")
                        VSlider(
                            v_model=(state_key,),
                            min=min_value,
                            max=max_value,
                            step=step,
                            end=self.evaluate_and_update_plot,
                        )
                        Div(f"{round(max_value, 2)}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                    )

    def _collect_values_by_variable_name(
        self, variable_names: list[str]
    ) -> pd.DataFrame:
        output_df = cast(pd.DataFrame, pd.DataFrame.from_dict(self.state.plot_data))  # pyright: ignore[reportUnknownMemberType]

        # Remove any columns not in variable_names
        output_df = cast(pd.DataFrame, output_df[variable_names])

        return output_df

    def _collect_plot_variables(self) -> list[str]:
        plot_variables: list[str] = []
        prefix = self.state_manager.get_mode_prefix("output_display")
        for name in self.state_manager.output_variable_names:
            state_key = f"{prefix}_{sanitize_string(name)}"
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
        data = cast(pd.DataFrame, pd.DataFrame.from_dict(self.state.plot_data))  # pyright: ignore[reportUnknownMemberType]

        x_axis_variable = self.state.hist_x_axis
        y_axis_variable = self.state.hist_y_axis

        HISTOGRAM_BINS = 10

        fig = px.density_heatmap(
            data_frame=data,
            x=x_axis_variable,
            y=y_axis_variable,
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
        prefix = self.state_manager.get_mode_prefix("output_display")
        for var_name in self.state_manager.output_variable_names:
            with VCol():
                VCheckbox(
                    v_model=(f"{prefix}_{sanitize_string(var_name)}",),
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
