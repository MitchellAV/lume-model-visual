from trame_server import Server

from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets.html import P
from trame.widgets.vuetify3 import (
    VContainer,
    VSlider,
    VTextField,
    VBtn,
    VRow,
    VCol,
    VDivider,
)

from lume_model.models import TorchModel
from lume_model.variables import ScalarVariable

from util import sanitize_string


class UI:
    def __init__(self, server: Server, model: TorchModel) -> None:
        self.server = server
        self.model = model

        self._initialize_ui()

    def _handle_click(self) -> None:
        input_dict: dict[str, float] = {}
        for var in self.model.input_variables:
            state_key = f"input_variables_{sanitize_string(var.name)}"
            state_value = self.server.state[state_key]
            if state_value is not None:
                input_dict[var.name] = float(state_value)

        output = self.model.evaluate(input_dict)

        print("Model output:")
        for key, value in output.items():
            print(f"  {key}: {value}")
            state_key = f"output_variables_{sanitize_string(key)}"
            self.server.state[state_key] = float(value)

    def _initialize_ui(self) -> None:
        with SinglePageLayout(self.server) as layout:
            input_variables = sorted(
                self.model.input_variables, key=lambda var: var.name
            )

            output_variables = sorted(
                self.model.output_variables, key=lambda var: var.name
            )

            with layout.toolbar:
                pass

            with layout.icon:
                pass

            layout.title.set_text(  # pyright: ignore[reportUnknownMemberType]
                "LUME Model Visualizer"
            )

            with layout.content:
                VBtn(
                    "Run Model",
                    click=self._handle_click,
                )
                with VDivider():
                    P("Output Variables")
                with VContainer(fluid=True):
                    for var in output_variables:
                        name = var.name

                        state_key = f"output_variables_{sanitize_string(name)}"

                        with VRow():
                            with VCol():
                                P(f"{name}")
                            with VCol():
                                VTextField(
                                    v_model=(state_key,),
                                    readonly=True,
                                )
                with VDivider():
                    P("Input Variables")
                with VContainer(fluid=True):
                    for index, var in enumerate(input_variables):
                        self._create_slider_for_variable(index, var)

            with layout.footer:
                pass

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
                    P(f"{name}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                        readonly=True,
                    )
        else:
            with VRow():
                with VCol():
                    P(f"{name}")
                    with VRow():
                        P(f"{round(min, 2)} ")
                        VSlider(
                            v_model=(state_key,),
                            min=min,
                            max=max,
                            step=step,
                            # start="flushState('input_variables')",
                            # thumb_label=True,
                        )
                        P(f"{round(max, 2)}")
                with VCol():
                    VTextField(
                        v_model=(state_key,),
                    )
