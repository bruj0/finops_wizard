"""Phase 1 Discovery module.

Orchestrates baseline billing checks and auto-detects workloads
utilizing the provider adapters.
"""

from typing import List
from finops_wizard.adapters import get_adapter
from finops_wizard.core.models import DiscoveryReport, ProviderType, WorkloadType


def run_discovery(provider: ProviderType, mode: str) -> DiscoveryReport:
    """Executes the Phase 1 Discovery scan.
    
    Queries the corresponding provider billing endpoints, detects workloads,
    and returns a structured report.
    
    Args:
        provider: Cloud provider to target (AWS, GCP, Azure).
        mode: Scan scope ("cloud" or "workloads").
        
    Returns:
        DiscoveryReport populated with detected configurations and dry-run logs.
    """
    adapter = get_adapter(provider)
    adapter.clear_dry_run_commands()

    # Step 1: Query Billing Baseline
    billing_data = adapter.discover_billing_baseline(mode)

    # Step 2: Auto-detect Workloads
    detected_workloads: List[WorkloadType] = []
    if mode == "workloads":
        detected_workloads = adapter.discover_workloads()

    # Create Discovery Report
    report = DiscoveryReport(
        provider=provider,
        mode=mode,
        monthly_burn_rate=billing_data["monthly_burn_rate"],
        detected_anomalies=billing_data["detected_anomalies"],
        tag_coverage_pct=billing_data["tag_coverage_pct"],
        detected_workloads=detected_workloads,
        raw_billing_metrics=billing_data["raw_billing_metrics"],
        dry_run_commands=adapter.get_dry_run_commands().copy()
    )

    return report
