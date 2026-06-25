"""AWS provider adapter implementation.

Simulates AWS CLI commands and API endpoints while generating realistic,
under-utilized resources to demonstrate optimization opportunities.
"""

from typing import Any, Dict, List
from finops_wizard.adapters.base import BaseProviderAdapter
from finops_wizard.core.models import InventoryItem, ProviderType, WorkloadType


class AWSProviderAdapter(BaseProviderAdapter):
    """Adapter for AWS resources and billing APIs."""

    def __init__(self) -> None:
        self.dry_run_commands: List[str] = []

    def discover_billing_baseline(self, mode: str) -> Dict[str, Any]:
        self.dry_run_commands.extend([
            "aws ce get-cost-and-usage --time-period Start=2026-05-26,End=2026-06-25 --granularity MONTHLY --metrics \"UnblendedCost\"",
            "aws ce get-anomaly-monitors",
            "aws resourcegroupstaggingapi get-resources --resources-per-page 100"
        ])
        
        # Simulate base metrics
        return {
            "monthly_burn_rate": 4820.50 if mode == "cloud" else 2150.10,
            "detected_anomalies": 3,
            "tag_coverage_pct": 68.5,
            "raw_billing_metrics": {
                "UnblendedCost": "4820.50",
                "Currency": "USD",
                "TaxAmount": "210.00"
            }
        }

    def discover_workloads(self) -> List[WorkloadType]:
        self.dry_run_commands.extend([
            "aws eks list-clusters --max-items 50",
            "aws lambda list-functions --max-items 100",
            "aws ec2 describe-instances --filters \"Name=instance-state-name,Values=running\""
        ])
        # Returns all three types to simulate a hybrid environment
        return [WorkloadType.K8S, WorkloadType.SERVERLESS, WorkloadType.VMS]

    def scan_inventory(self, active_workloads: List[WorkloadType]) -> List[InventoryItem]:
        items: List[InventoryItem] = []
        
        if WorkloadType.K8S in active_workloads:
            self.dry_run_commands.extend([
                "kubectl get nodes -o json",
                "kubectl get pods --all-namespaces -o json"
            ])
            items.append(InventoryItem(
                resource_id="arn:aws:eks:us-east-1:123456789012:cluster/eks-prod-cluster-1",
                resource_name="eks-prod-cluster-1",
                resource_type="kubernetes_cluster",
                workload_type=WorkloadType.K8S,
                monthly_cost=850.00,
                utilization_metrics={"cpu_request_cores": 32, "cpu_usage_cores": 3.2, "mem_request_gb": 128, "mem_usage_gb": 18.5},
                tags={"Environment": "production", "Team": "core-api"},
                is_waste=True,
                waste_reason="CPU utilization is below 10% (32 cores requested, only 3.2 cores used average)."
            ))
            
        if WorkloadType.SERVERLESS in active_workloads:
            self.dry_run_commands.extend([
                "aws lambda list-functions",
                "aws cloudwatch get-metric-data --metric-data-queries file://queries.json"
            ])
            items.append(InventoryItem(
                resource_id="arn:aws:lambda:us-east-1:123456789012:function:lambda-payment-processor",
                resource_name="lambda-payment-processor",
                resource_type="lambda_function",
                workload_type=WorkloadType.SERVERLESS,
                monthly_cost=310.00,
                utilization_metrics={"configured_memory_mb": 2048, "max_memory_used_mb": 118, "avg_duration_ms": 250},
                tags={"Environment": "production", "Service": "billing"},
                is_waste=True,
                waste_reason="Overprovisioned memory. Max memory used is 118MB out of 2048MB configured."
            ))

        if WorkloadType.VMS in active_workloads:
            self.dry_run_commands.extend([
                "aws ec2 describe-instances",
                "aws ec2 describe-volumes --filters \"Name=status,Values=available\""
            ])
            # Idle VM instance
            items.append(InventoryItem(
                resource_id="i-08f1b623838ae62d0",
                resource_name="ec2-monolith-legacy",
                resource_type="virtual_machine",
                workload_type=WorkloadType.VMS,
                monthly_cost=288.00,
                utilization_metrics={"cpu_utilization_pct": 1.2, "disk_iops": 5},
                tags={"Environment": "staging", "Owner": "devops"},
                is_waste=True,
                waste_reason="Idle VM. Average CPU utilization is 1.2% over 14 days."
            ))
            # Unattached Disk volume
            items.append(InventoryItem(
                resource_id="vol-0e32f7902d3489812",
                resource_name="ebs-unused-temp",
                resource_type="ebs_volume",
                workload_type=WorkloadType.VMS,
                monthly_cost=120.00,
                utilization_metrics={"attachment_state": "detached", "size_gb": 1000, "volume_type": "gp2"},
                tags={"Project": "migration-test"},
                is_waste=True,
                waste_reason="Unattached EBS volume. Currently costing $120/month with zero utilization."
            ))

        return items

    def get_dry_run_commands(self) -> List[str]:
        return self.dry_run_commands

    def clear_dry_run_commands(self) -> None:
        self.dry_run_commands = []
