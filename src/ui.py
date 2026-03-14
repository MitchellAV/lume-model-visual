from typing import Any


from lume_model.models import TorchModel

from state import Ctrl, St, StateManager

from layout import UILayout

from utils import initialize_logger, logger_debug

logger = initialize_logger(__name__)


class UI:
    counter: int = 0

    def __init__(self, state_manager: StateManager) -> None:
        self.state_manager = state_manager

        self.layout = UILayout(state_manager)

        self._initialize_event_listeners()

    @property
    def model(self) -> TorchModel:
        return self.state_manager.model

    @property
    def state(self) -> St:
        return self.state_manager.state

    @property
    def ctrl(self) -> Ctrl:
        return self.state_manager.ctrl

    # Event handlers
    def _initialize_event_listeners(self) -> None:
        self.ctrl.update_plot = self.update_plot
        self.ctrl.evaluate_and_update_plot = self.evaluate_and_update_plot
        self.ctrl.collect_and_update_plot = self.collect_and_update_plot
        self.ctrl.reinitialize_ui = self.reinitialize_ui

    @logger_debug(logger)
    def collect_and_update_plot(self, *args: Any, **kwargs: Any) -> None:
        self.state_manager.stream_pv_data()
        self.update_plot()

    @logger_debug(logger)
    def evaluate_and_update_plot(self, *args: Any, **kwargs: Any) -> None:
        self.state_manager.evaluate_model()
        self.update_plot()

    @logger_debug(logger)
    def update_plot(self, *args: Any, **kwargs: Any) -> None:
        self.layout.update_figure()

    @logger_debug(logger)
    def reinitialize_ui(self, *args: Any, **kwargs: Any) -> None:
        """Reinitialize the UI, for example after loading a new model."""
        self.layout.initialize_ui()
