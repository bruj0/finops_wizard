"""Spinner widget for progress feedback.

Adapted from Dolphie's SpinnerWidget.py.
"""

from rich.spinner import Spinner
from textual.widgets import Static


class SpinnerWidget(Static):
    """Static widget displaying a rotating text spinner during processes."""

    def __init__(self, text: str = "Scanning...") -> None:
        super().__init__("")
        self._spinner = Spinner("bouncingBar", text=f"[label]{text}", speed=0.7)

    def on_mount(self) -> None:
        self.update_render = self.set_interval(1 / 60, self.update_spinner)

    def hide(self) -> None:
        self.display = False

    def show(self) -> None:
        self.display = True

    def update_spinner(self) -> None:
        self.update(self._spinner)
