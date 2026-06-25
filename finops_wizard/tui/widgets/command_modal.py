"""CommandModal input screen.

Adapted from Dolphie's CommandModal.py to prompt the user for text configurations
(such as directories, API keys, or URLs).
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class CommandModal(ModalScreen[str]):
    """Modal screen displaying a dialog box with a text input field."""

    def __init__(self, message: str, placeholder: str = "", default_val: str = "") -> None:
        super().__init__()
        self.message = message
        self.placeholder = placeholder
        self.default_val = default_val

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_box"):
            yield Label(self.message)
            yield Input(
                placeholder=self.placeholder,
                value=self.default_val,
                id="modal_input"
            )
            yield Button("Submit", variant="primary", id="modal_submit")
            yield Button("Cancel", variant="error", id="modal_cancel")

    def on_mount(self) -> None:
        self.query_one("#modal_input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_submit":
            val = self.query_one("#modal_input", Input).value
            self.dismiss(val)
        else:
            self.dismiss("")
