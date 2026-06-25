"""Abstract base provider adapter interface.

Ensures all cloud adapters implement a consistent interface and follow
the Swappable Integrations pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from finops_wizard.core.models import InventoryItem, WorkloadType


class BaseProviderAdapter(ABC):
    """Abstract interface for querying cloud cost and inventory data.
    
    Provides methods for discovering baseline costs, detecting workload footprints,
    and retrieving specific resource inventory data.
    """

    @abstractmethod
    def discover_billing_baseline(self, mode: str) -> Dict[str, Any]:
        """Queries the provider's billing endpoints for a baseline.
        
        Args:
            mode: The execution mode ("cloud" or "workloads").
            
        Returns:
            A dictionary containing monthly cost, anomaly count, tag coverage,
            and other billing stats.
        """
        pass

    @abstractmethod
    def discover_workloads(self) -> List[WorkloadType]:
        """Scans the account to auto-detect active workload signatures.
        
        Returns:
            A list of detected WorkloadType values (K8S, SERVERLESS, VMS).
        """
        pass

    @abstractmethod
    def scan_inventory(self, active_workloads: List[WorkloadType]) -> List[InventoryItem]:
        """Scans utilization metrics and resources for active workloads.
        
        Args:
            active_workloads: Workloads that were detected and should be scanned.
            
        Returns:
            A list of InventoryItem objects containing resource stats.
        """
        pass

    @abstractmethod
    def get_dry_run_commands(self) -> List[str]:
        """Returns the list of auditable CLI commands executed or simulated.
        
        Returns:
            List of shell command strings.
        """
        pass

    @abstractmethod
    def clear_dry_run_commands(self) -> None:
        """Resets the accumulated dry-run commands list."""
        pass
