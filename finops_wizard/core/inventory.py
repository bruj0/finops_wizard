"""Phase 2 Inventory module.

Gathers resource inventories and compiles utilization profiles to
identify wasted expenses.
"""

from finops_wizard.adapters import get_adapter
from finops_wizard.core.models import DiscoveryReport, InventoryReport


def run_inventory(discovery_report: DiscoveryReport) -> InventoryReport:
    """Executes the Phase 2 Inventory scan.
    
    Crawls resources and utilization patterns, highlights potential wastes,
    and returns a structured InventoryReport.
    
    Args:
        discovery_report: The Phase 1 DiscoveryReport to guide the inventory scan.
        
    Returns:
        InventoryReport mapping resource waste statistics and dry-run outputs.
    """
    adapter = get_adapter(discovery_report.provider)
    adapter.clear_dry_run_commands()

    # Step 1: Scan inventory items based on mode
    if discovery_report.mode == "cloud":
        # Cloud mode scans standard base infrastructure types
        active_workloads = list(adapter.discover_workloads())  # Fallback: scan all workloads
    else:
        active_workloads = discovery_report.detected_workloads

    items = adapter.scan_inventory(active_workloads)

    # Step 2: Compute summary stats
    waste_resources = 0
    potential_savings = 0.0

    for item in items:
        if item.is_waste:
            waste_resources += 1
            potential_savings += item.monthly_cost

    report = InventoryReport(
        provider=discovery_report.provider,
        mode=discovery_report.mode,
        total_resources=len(items),
        waste_resources=waste_resources,
        potential_savings=potential_savings,
        items=items,
        dry_run_commands=adapter.get_dry_run_commands().copy()
    )

    return report
