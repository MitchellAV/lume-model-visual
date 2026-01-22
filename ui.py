from trame_server import Server

from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets.vuetify3 import VContainer, VSlider, VTextField

from lume_model.models import TorchModel
from lume_model.variables import ScalarVariable

from util import sanitize_string


class UI:
    def __init__(self, server: Server, model: TorchModel) -> None:
        self.server = server
        self.model = model

        self._initialize_ui()

    def _initialize_ui(self) -> None:
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(  # pyright: ignore[reportUnknownMemberType]
                "LUME Model Visualizer"
            )

            input_variables = self.model.input_variables

            with layout.content:
                with VContainer(fluid=True):
                    for index, var in enumerate(input_variables):
                        self._create_slider_for_variable(index, var)

    def _create_slider_for_variable(self, index: int, var: ScalarVariable) -> None:
        name = var.name
        if var.default_value is None:
            raise ValueError(
                f"Cannot create slider for variable '{name}' with default value."
            )
        default_value = var.default_value
        if var.value_range is None:
            raise ValueError(
                f"Cannot create slider for variable '{name}' without value range."
            )
        value_range = var.value_range

        step = (value_range[1] - value_range[0]) / 100.0
        state_key = sanitize_string(name)

        if step <= 0:
            VTextField(
                label=f"{name}",
                v_model=(state_key, default_value),
                readonly=True,
            )
        else:
            VSlider(
                v_model=(state_key, default_value),
                label=f"{name}",
                min=value_range[0],
                max=value_range[1],
                step=step,
                thumb_label=True,
            )
