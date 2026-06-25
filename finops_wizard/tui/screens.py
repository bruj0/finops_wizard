"""Screens definitions for FinOps Wizard TUI.

Contains MainMenu, Scan, Dashboard, Inventory, Analysis, Alerting,
and SaaS Bridge screens. Reuses Dolphie design concepts and table layouts.
"""

import os
from datetime import datetime
import asyncio
from typing import Any, List
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, Markdown, OptionList, ProgressBar, Static
from rich.text import Text

from finops_wizard.core.models import DiscoveryReport, InventoryReport, AnalysisReport, ProviderType, WorkloadType
from finops_wizard.core.discovery import run_discovery
from finops_wizard.core.inventory import run_inventory
from finops_wizard.core.analysis import run_analysis
from finops_wizard.core.monitoring import save_run, get_history, sync_to_saas
from finops_wizard.core.alerting import evaluate_alerts
from finops_wizard.tui.widgets.top_bar import TopBar
from finops_wizard.tui.widgets.spinner import SpinnerWidget
from finops_wizard.tui.widgets.command_modal import CommandModal
from finops_wizard.tui.widgets.selection_modal import SelectionModal


class MainMenuScreen(Screen):
    """The landing screen displaying setup parameters and scan launch buttons."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="[b highlight]up/down[/b highlight] to navigate | [b highlight]enter[/b highlight] to select")
        with Container(classes="container"):
            yield Label("🧙 FINOPS WIZARD MAIN MENU", classes="title")
            yield Label("Local-First Read-Only Cloud Cost Optimization", classes="subtitle")
            
            yield Label("[b]Configuration & Actions:[/b]", id="menu_header")
            yield OptionList(
                "1. Select Scan Mode: [Cloud Mode]",
                "2. Select Provider: [AWS]",
                "3. Target IaC (Terraform) Directory: [None]",
                "4. Select LLM Inference Engine: [Mock LLM]",
                "5. Configure LLM API Key: [Not Configured]",
                "--- Actions ---",
                "6. Run FinOps Scan (Discovery & Inventory)",
                "7. View Local Scan History Dashboard",
                "8. Open SaaS Trust Portal & Onboarding",
                id="menu_list"
            )
            yield Label("Press Q to exit the application.", classes="subtitle")

    def on_mount(self) -> None:
        self.update_menu_display()

    def update_menu_display(self) -> None:
        """Refreshes option list labels with current app configurations."""
        app = self.app
        opt_list = self.query_one("#menu_list", OptionList)
        
        opt_list.replace_option_prompt_at_index(0, Text.from_markup(f"1. Select Scan Mode: [b highlight][{app.scan_mode.upper()}][/b highlight]"))
        opt_list.replace_option_prompt_at_index(1, Text.from_markup(f"2. Select Provider: [b highlight][{app.provider.value.upper()}][/b highlight]"))
        
        iac_str = os.path.basename(app.iac_dir) if app.iac_dir else "None"
        opt_list.replace_option_prompt_at_index(2, Text.from_markup(f"3. Target IaC (Terraform) Directory: [b highlight][{iac_str}][/b highlight]"))
        opt_list.replace_option_prompt_at_index(3, Text.from_markup(f"4. Select LLM Inference Engine: [b highlight][{app.llm_provider.upper()}][/b highlight]"))
        
        key_str = "Configured" if app.llm_api_key else "Not Configured"
        opt_list.replace_option_prompt_at_index(4, Text.from_markup(f"5. Configure LLM API Key: [b highlight][{key_str}][/b highlight]"))
        opt_list.refresh()

    @on(OptionList.OptionSelected, "#menu_list")
    def handle_selection(self, event: OptionList.OptionSelected) -> None:
        app = self.app
        idx = event.option_index
        
        if idx == 0:
            def select_mode(val: str) -> None:
                if val:
                    app.scan_mode = val
                    self.update_menu_display()
            self.app.push_screen(
                SelectionModal(
                    "Select Scan Mode:",
                    [
                        ("Cloud Mode (Billing Baseline Scan)", "cloud"),
                        ("Workloads Mode (Container/Serverless/VM Scan)", "workloads")
                    ]
                ),
                select_mode
            )
        elif idx == 1:
            def select_provider(val: str) -> None:
                if val:
                    app.provider = ProviderType(val)
                    self.update_menu_display()
            self.app.push_screen(
                SelectionModal(
                    "Select Cloud Provider:",
                    [
                        ("Amazon Web Services (AWS)", "aws"),
                        ("Google Cloud Platform (GCP)", "gcp"),
                        ("Microsoft Azure (Azure)", "azure")
                    ]
                ),
                select_provider
            )
        elif idx == 2:
            # Get IaC folder path
            def get_iac_path(path: str) -> None:
                if path:
                    app.iac_dir = path
                    self.update_menu_display()
            self.app.push_screen(
                CommandModal("Enter path to Terraform directory:", placeholder="/path/to/terraform/code", default_val=app.iac_dir or ""),
                get_iac_path
            )
        elif idx == 3:
            def select_llm(val: str) -> None:
                if val:
                    app.llm_provider = val
                    self.update_menu_display()
            self.app.push_screen(
                SelectionModal(
                    "Select LLM Inference Engine:",
                    [
                        ("Mock LLM (Local-First Offline)", "mock"),
                        ("Ollama (Local Qwen2.5-Coder)", "ollama"),
                        ("OpenAI (GPT-4o-mini)", "openai"),
                        ("Anthropic (Claude 3.5 Sonnet)", "anthropic")
                    ]
                ),
                select_llm
            )
        elif idx == 4:
            # LLM API Key
            def get_api_key(key: str) -> None:
                if key:
                    app.llm_api_key = key
                    self.update_menu_display()
            self.app.push_screen(
                CommandModal("Enter LLM API Key:", placeholder="sk-...", default_val=app.llm_api_key or ""),
                get_api_key
            )
        elif idx == 6:
            # Run scan
            app.push_screen(ScanScreen())
        elif idx == 7:
            # Go to history dashboard
            app.push_screen(DashboardScreen())
        elif idx == 8:
            # Go to SaaS Bridge
            app.push_screen(SaaSBridgeScreen())

    def on_key(self, event: Any) -> None:
        if event.key.lower() == "q":
            self.app.exit()


class ScanScreen(Screen):
    """Performs the scan in a background thread and logs running dry-run API queries."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="Running local scan phases...")
        with Container(classes="container"):
            yield Label("🔍 SCANNING IN PROGRESS", classes="title")
            yield SpinnerWidget("Querying billing baseline & workloads...")
            yield ProgressBar(total=100, id="scan_progress")
            yield Label("[b]Auditable API Dry-Run Log (Simulated Read-Only commands):[/b]")
            yield ScrollableContainer(id="scan_log")
            yield Label("Press Esc to cancel scan.", classes="subtitle")

    def on_mount(self) -> None:
        self.query_one(ProgressBar).progress = 10
        self.run_background_scan()

    @work
    async def run_background_scan(self) -> None:
        app = self.app
        progress = self.query_one(ProgressBar)
        log_box = self.query_one("#scan_log", ScrollableContainer)

        async def log_cmd(cmd: str) -> None:
            # Safe update in thread
            log_box.mount(Static(f"[dark_gray]$ {cmd}[/dark_gray]"))
            log_box.scroll_end(animate=False)
            await asyncio.sleep(0.4)

        # Phase 1: Discovery
        await log_cmd(f"Initializing Phase 1: Discovery on provider {app.provider.value.upper()}")
        discovery_report = run_discovery(app.provider, app.scan_mode)
        progress.progress = 30
        for cmd in discovery_report.dry_run_commands:
            await log_cmd(cmd)

        if app.scan_mode == "workloads":
            detected_str = ", ".join(w.value.upper() for w in discovery_report.detected_workloads)
            await log_cmd(f"Auto-detected Workloads: [green]{detected_str}[/green]")
        await log_cmd("Phase 1 Complete.")

        # Phase 2: Inventory
        await log_cmd("Initializing Phase 2: Inventory resource utilization scan")
        inventory_report = run_inventory(discovery_report)
        progress.progress = 60
        for cmd in inventory_report.dry_run_commands:
            await log_cmd(cmd)
        await log_cmd(f"Found {inventory_report.total_resources} resources. {inventory_report.waste_resources} underutilized items.")
        await log_cmd("Phase 2 Complete.")

        # Phase 3: Analysis
        await log_cmd(f"Initializing Phase 3: Cost analysis & Terraform refactoring using LLM ({app.llm_provider})")
        analysis_report = run_analysis(
            discovery_report,
            inventory_report,
            iac_dir=app.iac_dir,
            llm_provider=app.llm_provider,
            api_key=app.llm_api_key
        )
        progress.progress = 85
        await log_cmd("Generated recommendations markdown report with Terraform code patches.")

        # Phase 4: Save Run locally
        await log_cmd("Initializing Phase 4: Storing metrics baseline to local SQLite history")
        save_run(discovery_report, inventory_report)
        await log_cmd("Phase 4 Complete.")

        # Phase 5: Alerts
        await log_cmd("Initializing Phase 5: Running governance alert checks")
        alerts = evaluate_alerts(discovery_report, inventory_report)
        progress.progress = 100
        await log_cmd("Phase 5 Complete. Governance Alert rules processed.")
        
        # Save reports in app context
        app.discovery_report = discovery_report
        app.inventory_report = inventory_report
        app.analysis_report = analysis_report
        app.alerts = alerts

        await asyncio.sleep(0.5)
        # Scan complete, switch to Dashboard screen
        self.app.switch_screen(DashboardScreen())

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(MainMenuScreen())


class DashboardScreen(Screen):
    """The central dashboard organizing current metrics, waste, and local history."""

    def compose(self) -> ComposeResult:
        app_title = "FinOps Scan Dashboard"
        yield TopBar(help_text="[b]d[/b] Discovery | [b]i[/b] Inventory | [b]a[/b] Analysis | [b]l[/b] Alerts | [b]m[/b] Menu | [b]s[/b] SaaS Sync")
        with Container(classes="container"):
            yield Label(f"🧙 FINOPS DASHBOARD - {self.app.provider.value.upper()}", classes="title")
            
            with Horizontal(classes="dashboard-grid"):
                # Left side: Current Baseline
                with Vertical(classes="dashboard-panel"):
                    yield Label("Baseline & Metrics", classes="dashboard-panel-header")
                    yield Label(id="lbl_baseline_details")
                    
                # Right side: Waste & Optimization
                with Vertical(classes="dashboard-panel"):
                    yield Label("Waste & Resource Health", classes="dashboard-panel-header")
                    yield Label(id="lbl_waste_details")
            
            # Bottom row: SQLite Scan History log
            yield Label("[b]Local Scan History Database (SQLite Log):[/b]")
            yield DataTable(id="history_table")
            
            yield Label("Hotkeys: [b]d[/b]: Discovery Report | [b]i[/b]: Inventory Items | [b]a[/b]: Recommendations | [b]l[/b]: Alerts", classes="subtitle")

    def on_mount(self) -> None:
        app = self.app
        # Update labels
        disc = app.discovery_report
        inv = app.inventory_report
        
        if disc and inv:
            mode_str = f"{disc.mode.upper()}"
            if disc.mode == "workloads":
                w_types = ", ".join(w.value.upper() for w in disc.detected_workloads)
                mode_str += f" ({w_types})"
                
            self.query_one("#lbl_baseline_details", Label).update(
                f"[label]Provider:[/label] {disc.provider.value.upper()}\n"
                f"[label]Mode:[/label] {mode_str}\n"
                f"[label]Monthly Burn Rate:[/label] [yellow]${disc.monthly_burn_rate:,.2f}/mo[/yellow]\n"
                f"[label]Billing Anomalies:[/label] {'[red]Yes[/red]' if disc.detected_anomalies > 0 else '[green]None[/green]'} ({disc.detected_anomalies} detected)\n"
                f"[label]Tag Coverage:[/label] {disc.tag_coverage_pct}%\n"
                f"[label]Report Timestamp:[/label] {disc.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            self.query_one("#lbl_waste_details", Label).update(
                f"[label]Total Resources Scanned:[/label] {inv.total_resources}\n"
                f"[label]Orphaned / Idle Items:[/label] [red]{inv.waste_resources} resources[/red]\n"
                f"[label]Potential Cost Savings:[/label] [green]${inv.potential_savings:,.2f}/mo[/green]\n"
                f"[label]Efficiency Ratio:[/label] {100 - (inv.waste_resources / (inv.total_resources or 1) * 100):.1f}% Health Score\n"
                f"[label]IaC Binding Directory:[/label] {app.iac_dir or 'Not Configured'}"
            )
        else:
            self.query_one("#lbl_baseline_details", Label).update("[red]No scan executed yet. Press 'm' to run a scan from the main menu.[/red]")
            self.query_one("#lbl_waste_details", Label).update("[red]N/A[/red]")

        # Populate SQLite Table
        table = self.query_one("#history_table", DataTable)
        table.add_columns("ID", "Timestamp", "Provider", "Mode", "Burn Rate", "Waste", "Savings ($)")
        history = get_history()
        for idx, row in enumerate(history):
            table.add_row(
                str(row["id"]),
                row["timestamp"][:19].replace("T", " "),
                row["provider"].upper(),
                row["mode"].upper(),
                f"${row['monthly_burn_rate']:,.2f}",
                str(row["waste_resources"]),
                f"${row['potential_savings']:,.2f}"
            )

    def on_key(self, event: Any) -> None:
        key = event.key.lower()
        if key == "m":
            self.app.switch_screen(MainMenuScreen())
        elif key == "d":
            self.app.switch_screen(DiscoveryScreen())
        elif key == "i":
            self.app.switch_screen(InventoryScreen())
        elif key == "a":
            self.app.switch_screen(AnalysisScreen())
        elif key == "l":
            self.app.switch_screen(AlertingScreen())
        elif key == "s":
            self.app.switch_screen(SaaSBridgeScreen())


class DiscoveryScreen(Screen):
    """Renders the detailed JSON discovery structure and dry-run query commands."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="press [b]esc[/b] to return to dashboard")
        with Container(classes="container"):
            yield Label("Phase 1: Discovery Baseline Details", classes="title")
            yield Label("[b]Audited Billing / Provider CLI Queries executed:[/b]")
            yield ScrollableContainer(id="dry_run_console")
            yield Label("[b]Raw JSON Telemetry Dataset (Extracted locally):[/b]")
            yield Markdown(id="json_payload_md")

    def on_mount(self) -> None:
        app = self.app
        disc = app.discovery_report
        if disc:
            cmds_container = self.query_one("#dry_run_console", ScrollableContainer)
            for cmd in disc.dry_run_commands:
                cmds_container.mount(Static(f"[dark_gray]$ {cmd}[/dark_gray]"))
            
            # Format report metrics as code block
            payload_md = f"```json\n{disc.model_dump_json(indent=2)}\n```"
            self.query_one("#json_payload_md", Markdown).update(payload_md)

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(DashboardScreen())


class InventoryScreen(Screen):
    """Renders the detailed resources inventory showing CPU/Memory utilization waste."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="press [b]esc[/b] to return to dashboard")
        with Container(classes="container"):
            yield Label("Phase 2: Utilization Inventory Catalog", classes="title")
            yield DataTable(id="inventory_table")
            yield Label(id="inventory_summary_bar")

    def on_mount(self) -> None:
        app = self.app
        inv = app.inventory_report
        table = self.query_one("#inventory_table", DataTable)
        table.add_columns("ID", "Resource Name", "Workload", "Type", "Cost ($/mo)", "Waste Reason", "Utilization Metrics")
        
        if inv:
            for item in inv.items:
                cost_str = f"${item.monthly_cost:,.2f}"
                metrics_str = ", ".join(f"{k}={v}" for k, v in item.utilization_metrics.items())
                
                # Style row based on waste status
                id_styled = f"[red]{item.resource_id}[/red]" if item.is_waste else f"[green]{item.resource_id}[/green]"
                name_styled = f"[red]{item.resource_name}[/red]" if item.is_waste else f"[green]{item.resource_name}[/green]"
                waste_reason = f"[yellow]{item.waste_reason or 'None'}[/yellow]" if item.is_waste else "None (Healthy)"

                table.add_row(
                    id_styled,
                    name_styled,
                    item.workload_type.value.upper(),
                    item.resource_type,
                    cost_str,
                    waste_reason,
                    metrics_str
                )
            self.query_one("#inventory_summary_bar", Label).update(
                f"[green]Scanned: {inv.total_resources}[/green] | [red]Waste: {inv.waste_resources}[/red] | "
                f"[green]Recoverable Savings: ${inv.potential_savings:,.2f}/mo[/green]"
            )

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(DashboardScreen())


class AnalysisScreen(Screen):
    """Displays the markdown LLM suggestions and git patches side-by-side."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="press [b]esc[/b] to return to dashboard")
        with Container(classes="container"):
            yield Label("Phase 3: Cost Optimization Recommendations", classes="title")
            with ScrollableContainer(id="markdown_scroller"):
                yield Markdown(id="analysis_markdown")

    def on_mount(self) -> None:
        app = self.app
        analysis = app.analysis_report
        if analysis:
            self.query_one("#analysis_markdown", Markdown).update(analysis.summary_markdown)
        else:
            self.query_one("#analysis_markdown", Markdown).update("No analysis run exists.")

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(DashboardScreen())


class AlertingScreen(Screen):
    """Displays the Phase 5 alerting governance check status."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="press [b]esc[/b] to return to dashboard")
        with Container(classes="container"):
            yield Label("Phase 5: Governance Alerts", classes="title")
            yield DataTable(id="alerts_table")

    def on_mount(self) -> None:
        app = self.app
        table = self.query_one("#alerts_table", DataTable)
        table.add_columns("Alert Name", "Value", "Threshold", "Triggered?", "Alert Warning Message")
        
        if app.alerts:
            for alert in app.alerts:
                status_styled = "[red]TRIGGERED[/red]" if alert.is_triggered else "[green]OK[/green]"
                table.add_row(
                    alert.name,
                    str(alert.value),
                    str(alert.threshold),
                    status_styled,
                    alert.message
                )

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(DashboardScreen())


class SaaSBridgeScreen(Screen):
    """Onboarding center to convert local user to the SaaS platform securely."""

    def compose(self) -> ComposeResult:
        yield TopBar(help_text="press [b]esc[/b] to return to dashboard")
        with Container(classes="container"):
            yield Label("SaaS Cloud Governance Platform", classes="title")
            with Vertical(id="saas_card"):
                yield Label("[bold white]Connect to SaaS Continuous Optimization[/bold white]")
                yield Label(
                    "While this open-source CLI scans locally, the SaaS platform runs automated monitoring "
                    "across all accounts to manage cloud waste in the background:\n\n"
                    "✔️ Centralized glassmorphism dashboards for 100+ accounts\n"
                    "✔️ Continuous background scanning & anomaly alerting (no manual cron setup)\n"
                    "✔️ Machine learning-driven prediction engine\n"
                    "✔️ Automated PR creations (Click 'Approve' on Slack to resize VMs)\n"
                    "✔️ strict Telemetry Isolation: only aggregated metrics are uploaded; IaC remains local"
                )
                yield Button("Sync local baseline report with SaaS panel now", variant="primary", id="btn_saas_sync")
                yield Label(id="lbl_sync_status", classes="subtitle")

    @on(Button.Pressed, "#btn_saas_sync")
    def trigger_sync(self, event: Button.Pressed) -> None:
        app = self.app
        disc = app.discovery_report
        inv = app.inventory_report
        
        if not disc or not inv:
            self.query_one("#lbl_sync_status", Label).update("[red]Error: Run a local scan baseline first.[/red]")
            return

        def perform_sync(saas_key: str) -> None:
            if not saas_key:
                return
            # Sync payload
            res = sync_to_saas(saas_key, disc, inv)
            self.query_one("#lbl_sync_status", Label).update(
                f"[green]{res['message']}[/green]\n"
                f"[dark_gray]Masked Sync API Key: {res['payload']['api_key_masked']}[/dark_gray]"
            )
            
        self.app.push_screen(
            CommandModal("Enter SaaS API key (or 'mock_key' for demo):", placeholder="finops-..."),
            perform_sync
        )

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.app.switch_screen(DashboardScreen())
