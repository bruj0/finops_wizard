"""Unit tests for FinOps Wizard.

Verifies model validation, adapter factories, scan executions, alerting thresholds,
and database operations.
"""

import os
import pytest
from datetime import datetime

from finops_wizard.core.models import ProviderType, WorkloadType, DiscoveryReport, InventoryReport
from finops_wizard.adapters import get_adapter
from finops_wizard.core.discovery import run_discovery
from finops_wizard.core.inventory import run_inventory
from finops_wizard.core.alerting import evaluate_alerts
from finops_wizard.core.monitoring import save_run, get_history, DB_PATH, init_db


def test_provider_adapter_factory() -> None:
    """Verifies that the factory returns the correct adapters and raises errors for unknown ones."""
    aws_adapter = get_adapter(ProviderType.AWS)
    assert aws_adapter is not None
    
    gcp_adapter = get_adapter(ProviderType.GCP)
    assert gcp_adapter is not None

    with pytest.raises(ValueError):
        get_adapter("unknown_provider")  # type: ignore


def test_discovery_report_fields() -> None:
    """Verifies Pydantic validations on DiscoveryReport."""
    report = DiscoveryReport(
        provider=ProviderType.AWS,
        mode="cloud",
        monthly_burn_rate=1500.0,
        detected_anomalies=0,
        tag_coverage_pct=90.0,
        detected_workloads=[WorkloadType.K8S, WorkloadType.VMS]
    )
    assert report.provider == ProviderType.AWS
    assert len(report.detected_workloads) == 2
    assert report.detected_anomalies == 0


def test_run_scan_flow() -> None:
    """Verifies Phase 1 and Phase 2 scanning operations."""
    disc = run_discovery(ProviderType.AWS, "workloads")
    assert disc.provider == ProviderType.AWS
    assert len(disc.detected_workloads) > 0
    assert len(disc.dry_run_commands) > 0

    inv = run_inventory(disc)
    assert inv.total_resources > 0
    assert inv.waste_resources > 0
    assert inv.potential_savings > 0.0


def test_evaluate_alerts() -> None:
    """Verifies that governance rules trigger alert thresholds correctly."""
    disc = run_discovery(ProviderType.AWS, "workloads")
    inv = run_inventory(disc)
    
    alerts = evaluate_alerts(disc, inv)
    assert len(alerts) == 3
    # Check that high waste threshold triggers (mock potential savings is > $200)
    waste_alert = next(a for a in alerts if a.name == "High Potential Savings Waste")
    assert waste_alert.is_triggered is True


def test_sqlite_persistence() -> None:
    """Verifies saving and querying run histories using SQLite."""
    # Ensure database is clean or runs on custom path
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass
            
    init_db()
    
    disc = run_discovery(ProviderType.AWS, "cloud")
    inv = run_inventory(disc)
    
    row_id = save_run(disc, inv)
    assert row_id > 0
    
    history = get_history()
    assert len(history) > 0
    assert history[0]["provider"] == "aws"
    assert history[0]["mode"] == "cloud"


@pytest.fixture
def anyio_backend() -> str:
    """Configures the anyio backend for testing asynchronous TUI startup."""
    return "asyncio"


@pytest.mark.anyio
async def test_tui_startup() -> None:
    """Verifies that the Textual TUI launches, handles option selections via SelectionModal, and updates configuration."""
    from finops_wizard.tui.app import FinOpsWizardApp
    from finops_wizard.tui.widgets.selection_modal import SelectionModal
    from finops_wizard.core.models import ProviderType
    
    app = FinOpsWizardApp()
    async with app.run_test() as pilot:
        # Check that the main menu screen is currently active and loaded
        assert app.screen is not None
        assert app.screen.__class__.__name__ == "MainMenuScreen"
        
        opt_list = app.screen.query_one("#menu_list")
        assert opt_list is not None
        
        # Verify Option List is populated with configuration options
        opt_prompt = str(opt_list.get_option_at_index(0).prompt)
        assert "Select Scan Mode" in opt_prompt

        # 1. Toggle Scan Mode to workloads
        assert app.scan_mode == "cloud"
        opt_list.highlighted = 0
        await pilot.press("enter")
        await pilot.pause()
        
        assert isinstance(app.screen, SelectionModal)
        sel_list = app.screen.query_one("#selection_list")
        sel_list.highlighted = 1  # workloads
        await pilot.press("enter")
        await pilot.pause()
        
        assert app.scan_mode == "workloads"

        # 2. Change Provider to gcp
        assert app.provider == ProviderType.AWS
        opt_list = app.screen.query_one("#menu_list")
        opt_list.highlighted = 1
        await pilot.press("enter")
        await pilot.pause()
        
        assert isinstance(app.screen, SelectionModal)
        sel_list = app.screen.query_one("#selection_list")
        sel_list.highlighted = 1  # gcp
        await pilot.press("enter")
        await pilot.pause()
        
        assert app.provider == ProviderType.GCP

        # 3. Change LLM Inference Engine to openai
        assert app.llm_provider == "mock"
        opt_list = app.screen.query_one("#menu_list")
        opt_list.highlighted = 3
        await pilot.press("enter")
        await pilot.pause()
        
        assert isinstance(app.screen, SelectionModal)
        sel_list = app.screen.query_one("#selection_list")
        sel_list.highlighted = 2  # openai
        await pilot.press("enter")
        await pilot.pause()
        
        assert app.llm_provider == "openai"



def test_analysis_parser() -> None:
    """Verifies that run_analysis correctly scans the enterprise IaC production directory,

    resolves modules, and generates clean diff patches for VMs, Lambda functions,
    and EKS clusters.
    """
    from finops_wizard.core.analysis import run_analysis
    
    disc = run_discovery(ProviderType.AWS, "workloads")
    inv = run_inventory(disc)
    
    # Path to production environment
    iac_dir = os.path.join(os.path.dirname(__file__), "..", "examples", "iac", "environments", "production")
    
    analysis = run_analysis(
        disc,
        inv,
        iac_dir=iac_dir,
        llm_provider="mock"
    )
    
    assert analysis is not None
    assert len(analysis.recommendations) > 0
    
    # Check that we got recommendations for each resource type
    vm_rec = next(r for r in analysis.recommendations if r.resource_id == "i-08f1b623838ae62d0")
    lambda_rec = next(r for r in analysis.recommendations if r.resource_id == "arn:aws:lambda:us-east-1:123456789012:function:lambda-payment-processor")
    eks_rec = next(r for r in analysis.recommendations if r.resource_id == "arn:aws:eks:us-east-1:123456789012:cluster/eks-prod-cluster-1")
    ebs_rec = next(r for r in analysis.recommendations if r.resource_id == "vol-0e32f7902d3489812")
    
    # Ensure file references are relative
    assert vm_rec.terraform_file == "main.tf"
    assert lambda_rec.terraform_file == "main.tf"
    assert eks_rec.terraform_file == "main.tf"
    assert ebs_rec.terraform_file == "../../modules/compute/main.tf"
    
    # Verify patch diff contents
    assert vm_rec.patch is not None
    assert "instance_type" in vm_rec.patch
    assert "t3.medium" in vm_rec.patch
    
    assert lambda_rec.patch is not None
    assert "memory_size" in lambda_rec.patch
    assert "256" in lambda_rec.patch
    
    assert eks_rec.patch is not None
    assert "node_instance_type" in eks_rec.patch
    assert "t3.medium" in eks_rec.patch


