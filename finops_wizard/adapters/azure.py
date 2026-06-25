"""Azure provider adapter implementation.

Simulates Azure billing metrics and resource utilization details.
"""

from typing import Any, Dict, List
from finops_wizard.adapters.base import BaseProviderAdapter
from finops_wizard.core.models import InventoryItem, ProviderType, WorkloadType


class AzureProviderAdapter(BaseProviderAdapter):
    """Adapter for Azure resources and billing APIs."""

    def __init__(self) -> None:
        self.dry_run_commands: List[str] = []

    def discover_billing_baseline(self, mode: str) -> Dict[str, Any]:
        self.dry_run_commands.extend([
            "az consumption usage details list --query \"[?pretaxCost!='' ]\"",
            "az monitor scheduled-query create --help",
            "az resource list --tag 'Environment'"
        ])
        
        return {
            "monthly_burn_rate": 5120.00 if mode == "cloud" else 2410.50,
            "detected_anomalies": 2,
            "tag_coverage_pct": 71.2,
            "raw_billing_metrics": {
                "PretaxCost": "5120.00",
                "Currency": "USD"
            }
        }

    def discover_workloads(self) -> List[WorkloadType]:
        self.dry_run_commands.extend([
            "az aks list",
            "az functionapp list",
            "az vm list --show-details --query \"[?powerState=='VM running']\""
        ])
        return [WorkloadType.K8S, WorkloadType.SERVERLESS, WorkloadType.VMS]

    def scan_inventory(self, active_workloads: List[WorkloadType]) -> List[InventoryItem]:
        items: List[InventoryItem] = []
        
        if WorkloadType.K8S in active_workloads:
            self.dry_run_commands.extend([
                "az aks show --name aks-core-prod --resource-group rg-prod",
                "kubectl get pods -A"
            ])
            items.append(InventoryItem(
                resource_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-prod/providers/Microsoft.ContainerService/managedClusters/aks-core-prod",
                resource_name="aks-core-prod",
                resource_type="aks_cluster",
                workload_type=WorkloadType.K8S,
                monthly_cost=910.00,
                utilization_metrics={"cpu_request_cores": 24, "cpu_usage_cores": 2.8, "mem_request_gb": 96, "mem_usage_gb": 22.0},
                tags={"environment": "production"},
                is_waste=True,
                waste_reason="AKS node requests exceed usage thresholds. Average CPU usage <12%."
            ))
            
        if WorkloadType.SERVERLESS in active_workloads:
            self.dry_run_commands.extend([
                "az functionapp show --name func-etl-trigger --resource-group rg-prod",
                "az monitor metrics list --resource func-etl-trigger --metric MemoryWorkingSet"
            ])
            items.append(InventoryItem(
                resource_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-prod/providers/Microsoft.Web/sites/func-etl-trigger",
                resource_name="func-etl-trigger",
                resource_type="function_app",
                workload_type=WorkloadType.SERVERLESS,
                monthly_cost=210.00,
                utilization_metrics={"allocated_memory_mb": 1536, "max_memory_used_mb": 140},
                tags={"environment": "production"},
                is_waste=True,
                waste_reason="Function app scale limits are overprovisioned. Peak memory usage is 140MB."
            ))

        if WorkloadType.VMS in active_workloads:
            self.dry_run_commands.extend([
                "az vm show --name vm-windows-server --resource-group rg-staging",
                "az disk list --query \"[?diskState=='Unattached']\""
            ])
            items.append(InventoryItem(
                resource_id="/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-staging/providers/Microsoft.Compute/virtualMachines/vm-windows-server",
                resource_name="vm-windows-server",
                resource_type="virtual_machine",
                workload_type=WorkloadType.VMS,
                monthly_cost=340.00,
                utilization_metrics={"cpu_utilization_pct": 2.1},
                tags={"environment": "staging"},
                is_waste=True,
                waste_reason="Staging VM is running 24/7 with under 3% CPU utilization."
            ))

        return items

    def get_dry_run_commands(self) -> List[str]:
        return self.dry_run_commands

    def clear_dry_run_commands(self) -> None:
        self.dry_run_commands = []
