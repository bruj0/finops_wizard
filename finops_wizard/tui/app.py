"""Main TUI Application module for FinOps Wizard.

Defines the FinOpsWizardApp class, registers styles, themes, and screen states,
and exposes a run_tui entrypoint.
"""

from typing import Any, List, Optional
from textual.app import App
from textual.theme import Theme as TextualTheme

from finops_wizard.core.models import DiscoveryReport, InventoryReport, AnalysisReport, ProviderType
from finops_wizard.tui.screens import MainMenuScreen


class FinOpsWizardApp(App):
    """The central Textual TUI App managing screens and data states."""
    
    TITLE = "FinOps Wizard"
    CSS_PATH = "styles.tcss"

    def __init__(self) -> None:
        super().__init__()
        
        # User configurations (configurable via menu)
        self.scan_mode: str = "cloud"
        self.provider: ProviderType = ProviderType.AWS
        self.iac_dir: Optional[str] = None
        self.llm_provider: str = "mock"
        self.llm_api_key: Optional[str] = None

        # Execution Reports Context
        self.discovery_report: Optional[DiscoveryReport] = None
        self.inventory_report: Optional[InventoryReport] = None
        self.analysis_report: Optional[AnalysisReport] = None
        self.alerts: Optional[List[Any]] = None

        # Register Dolphie-inspired color palette theme
        dolphie_theme = TextualTheme(
            name="dolphie_custom",
            primary="#bbc8e8",
            secondary="#91abec",
            accent="#54efae",
            warning="#f6ff8f",
            error="#fd8383",
            background="#0a0e1b",
            surface="#0f1525",
            panel="#192036"
        )
        self.register_theme(dolphie_theme)
        self.theme = "dolphie_custom"

        # Register Rich theme for console markup styling
        from rich.theme import Theme as RichTheme
        rich_theme = RichTheme({
            "white": "#e9e9e9",
            "light_blue": "#bbc8e8",
            "highlight": "#91abec",
            "label": "#c5c7d2",
            "recording": "#ff5e5e",
            "b_white": "b #e9e9e9",
            "b_light_blue": "b #bbc8e8",
            "b_highlight": "b #91abec",
            "b_label": "b #c5c7d2",
            "b_recording": "b #ff5e5e",
            # Also register space-separated versions just in case Rich parses them
            "b white": "b #e9e9e9",
            "b light_blue": "b #bbc8e8",
            "b highlight": "b #91abec",
            "b label": "b #c5c7d2",
            "b recording": "b #ff5e5e",
        })
        self.console.push_theme(rich_theme)

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


def run_tui() -> None:
    """Helper entry point to start the TUI application."""
    app = FinOpsWizardApp()
    app.run()


if __name__ == "__main__":
    run_tui()
