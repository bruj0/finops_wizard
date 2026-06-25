"""TopBar widget for FinOps Wizard.

Adapted from Dolphie's TopBar.py to display application status, target profiles,
and navigation help at the top of the terminal screen.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Label


class TopBar(Container):
    """Horizontal header bar containing application info and navigation keys."""
    
    status_text = reactive("", always_update=True)

    def __init__(self, app_version: str = "0.1.0", help_text: str = "press [b highlight]q[/b highlight] to quit") -> None:
        super().__init__()
        self.app_title = Text.from_markup(f"🧙 [b light_blue]FinOps Wizard[/b light_blue] [light_blue]v{app_version}")
        
        self.lbl_title = Label(self.app_title, id="topbar_title")
        self.lbl_status = Label("", id="topbar_status")
        self.lbl_help = Label(Text.from_markup(help_text), id="topbar_help")

    def watch_status_text(self, new_text: str) -> None:
        """Reactive watcher to update the center status label."""
        self.lbl_status.update(Text.from_markup(new_text))

    def compose(self) -> ComposeResult:
        yield self.lbl_title
        yield self.lbl_status
        yield self.lbl_help
