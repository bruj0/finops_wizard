"""SelectionModal input screen.

Displays a dialog box allowing the user to select from a list of options.
"""

from typing import List, Tuple
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList


class SelectionModal(ModalScreen[str]):
    """Modal screen displaying a dialog box with an OptionList selection."""

    def __init__(self, message: str, choices: List[Tuple[str, str]]) -> None:
        super().__init__()
        self.message = message
        self.choices = choices

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_box"):
            yield Label(self.message)
            yield OptionList(
                *[display for display, _ in self.choices],
                id="selection_list"
            )
            yield Button("Cancel", variant="error", id="modal_cancel")

    def on_mount(self) -> None:
        self.query_one("#selection_list").focus()

    @on(OptionList.OptionSelected, "#selection_list")
    def on_selection(self, event: OptionList.OptionSelected) -> None:
        val = self.choices[event.option_index][1]
        self.dismiss(val)

    @on(Button.Pressed, "#modal_cancel")
    def on_cancel(self) -> None:
        self.dismiss("")
