"""GCP provider adapter implementation.

Simulates GCP billing and resource configurations.
"""

from typing import Any, Dict, List
from finops_wizard.adapters.base import BaseProviderAdapter
from finops_wizard.core.models import InventoryItem, ProviderType, WorkloadType


class GCPProviderAdapter(BaseProviderAdapter):
    """Adapter for GCP resources and billing APIs."""

    def __init__(self) -> None:
        self.dry_run_commands: List[str] = []

    def discover_billing_baseline(self, mode: str) -> Dict[str, Any]:
        self.dry_run_commands.extend([
            "gcloud beta billing accounts list",
            "gcloud billing budgets list --billing-account=01A2B3-4C5D6E-7F8G9H",
            "gcloud asset search-all-resources --query=\"tagKeys:*\""
        ])
        
        return {
            "monthly_burn_rate": 3520.10 if mode == "cloud" else 1580.40,
            "detected_anomalies": 1,
            "tag_coverage_pct": 54.0,
            "raw_billing_metrics": {
                "Cost": "3520.10",
                "Currency": "USD"
            }
        }

    def discover_workloads(self) -> List[WorkloadType]:
        self.dry_run_commands.extend([
            "gcloud container clusters list",
            "gcloud functions list",
            "gcloud compute instances list --filter=\"status=RUNNING\""
        ])
        return [WorkloadType.K8S, WorkloadType.SERVERLESS, WorkloadType.VMS]

    def scan_inventory(self, active_workloads: List[WorkloadType]) -> List[InventoryItem]:
        items: List[InventoryItem] = []
        
        if WorkloadType.K8S in active_workloads:
            self.dry_run_commands.extend([
                "gcloud container clusters describe gke-prod-cluster --zone=us-central1-a",
                "kubectl get pods -A"
            ])
            items.append(InventoryItem(
                resource_id="//container.googleapis.com/projects/my-finops-project/zones/us-central1-a/clusters/gke-prod-cluster",
                resource_name="gke-prod-cluster",
                resource_type="gke_cluster",
                workload_type=WorkloadType.K8S,
                monthly_cost=620.00,
                utilization_metrics={"cpu_request_cores": 16, "cpu_usage_cores": 1.1, "mem_request_gb": 64, "mem_usage_gb": 9.2},
                tags={"env": "prod"},
                is_waste=True,
                waste_reason="Cluster requests far exceed actual usage. Average CPU load <8%."
            ))
            
        if WorkloadType.SERVERLESS in active_workloads:
            self.dry_run_commands.extend([
                "gcloud functions describe gcf-image-resizer",
                "gcloud logging read \"resource.type=cloud_function AND resource.labels.function_name=gcf-image-resizer\""
            ])
            items.append(InventoryItem(
                resource_id="//cloudfunctions.googleapis.com/projects/my-finops-project/locations/us-central1/functions/gcf-image-resizer",
                resource_name="gcf-image-resizer",
                resource_type="cloud_function",
                workload_type=WorkloadType.SERVERLESS,
                monthly_cost=150.00,
                utilization_metrics={"configured_memory_mb": 1024, "max_memory_used_mb": 75},
                tags={"env": "prod"},
                is_waste=True,
                waste_reason="Overprovisioned memory limit. Peak usage 75MB out of 1024MB."
            ))

        if WorkloadType.VMS in active_workloads:
            self.dry_run_commands.extend([
                "gcloud compute instances describe gce-test-db --zone=us-central1-a",
                "gcloud compute disks list --filter=\"-users:*\""
            ])
            items.append(InventoryItem(
                resource_id="gce-test-db-18239082",
                resource_name="gce-test-db",
                resource_type="gce_instance",
                workload_type=WorkloadType.VMS,
                monthly_cost=190.00,
                utilization_metrics={"cpu_utilization_pct": 0.8},
                tags={"env": "staging", "team": "devs"},
                is_waste=True,
                waste_reason="Idle Compute Engine instance. Average CPU utilization is 0.8%."
            ))

        return items

    def get_dry_run_commands(self) -> List[str]:
        return self.dry_run_commands

    def clear_dry_run_commands(self) -> None:
        self.dry_run_commands = []
