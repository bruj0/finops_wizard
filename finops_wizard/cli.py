"""CLI entrypoint for FinOps Wizard.

Parses command-line arguments using Typer, executes headless scans,
and launches the Textual TUI when invoked without arguments.
"""

import sys
from typing import Optional
import typer
from rich.console import Console

from finops_wizard.core.models import ProviderType
from finops_wizard.core.discovery import run_discovery
from finops_wizard.core.inventory import run_inventory
from finops_wizard.core.analysis import run_analysis
from finops_wizard.core.monitoring import save_run
from finops_wizard.core.alerting import evaluate_alerts

app = typer.Typer(help="FinOps Wizard CLI and TUI tool.")
console = Console()


@app.callback(invoke_without_command=True)
def default_run(
    ctx: typer.Context,
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Scan mode: 'cloud' or 'workloads'"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Provider: 'aws', 'gcp', 'azure'"),
    phase: str = typer.Option("all", "--phase", help="Target phase: 'all', 'discovery', 'inventory', 'analysis', 'monitoring', 'alerting'"),
    iac_dir: Optional[str] = typer.Option(None, "--iac-dir", help="Path to local Terraform/IaC directory"),
    llm: str = typer.Option("mock", "--llm", help="LLM Provider: 'mock', 'ollama', 'openai', 'anthropic'"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API Key for OpenAI/Anthropic"),
    webhook: Optional[str] = typer.Option(None, "--webhook", help="Webhook URL for Phase 5 alerts"),
) -> None:
    """Entry point check.
    
    Launches interactive TUI if no args are specified, otherwise runs headlessly.
    """
    if ctx.invoked_subcommand is not None:
        return

    # If no mode or provider is provided, run the TUI
    if mode is None or provider is None:
        from finops_wizard.tui.app import run_tui
        run_tui()
        return

    # Headless CLI Execution Flow
    try:
        prov_enum = ProviderType(provider.lower())
    except ValueError:
        console.print(f"[red]Error: Invalid provider '{provider}'. Must be aws, gcp, or azure.[/red]")
        sys.exit(1)

    if mode not in ("cloud", "workloads"):
        console.print(f"[red]Error: Invalid mode '{mode}'. Must be cloud or workloads.[/red]")
        sys.exit(1)

    console.print(f"[bold light_blue]Starting Headless FinOps Wizard ({prov_enum.value.upper()} | {mode})[/bold light_blue]")

    # Run Phase 1: Discovery
    discovery_report = run_discovery(prov_enum, mode)
    if phase == "discovery":
        console.print(discovery_report.model_dump_json(indent=2))
        return

    # Run Phase 2: Inventory
    inventory_report = run_inventory(discovery_report)
    if phase == "inventory":
        console.print(inventory_report.model_dump_json(indent=2))
        return

    # Run Phase 3: Analysis
    analysis_report = run_analysis(
        discovery_report,
        inventory_report,
        iac_dir=iac_dir,
        llm_provider=llm,
        api_key=api_key
    )
    if phase == "analysis":
        console.print(analysis_report.summary_markdown)
        return

    # Run Phase 4: Monitoring
    run_id = save_run(discovery_report, inventory_report)
    console.print(f"[green]Saved execution run ID {run_id} to local history db.[/green]")
    if phase == "monitoring":
        return

    # Run Phase 5: Alerting
    alerts = evaluate_alerts(discovery_report, inventory_report, webhook_url=webhook)
    console.print("\n[bold]Alerting Checks Status:[/bold]")
    for alert in alerts:
        status_color = "red" if alert.is_triggered else "green"
        console.print(f" - [{status_color}]{alert.name}[/{status_color}]: {alert.message}")


def main() -> None:
    """Wrapper entry point for python packaging."""
    app()


if __name__ == "__main__":
    main()
