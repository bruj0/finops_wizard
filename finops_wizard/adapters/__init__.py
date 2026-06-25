"""Adapters package init.

Exposes provider adapter implementations.
"""

from finops_wizard.adapters.base import BaseProviderAdapter
from finops_wizard.adapters.aws import AWSProviderAdapter
from finops_wizard.adapters.gcp import GCPProviderAdapter
from finops_wizard.adapters.azure import AzureProviderAdapter
from finops_wizard.core.models import ProviderType


def get_adapter(provider: ProviderType) -> BaseProviderAdapter:
    """Helper factory to resolve provider adapters.
    
    Args:
        provider: Target cloud provider.
        
    Returns:
        Concrete BaseProviderAdapter subclass instance.
    
    Raises:
        ValueError: If provider type is not recognized.
    """
    if provider == ProviderType.AWS:
        return AWSProviderAdapter()
    elif provider == ProviderType.GCP:
        return GCPProviderAdapter()
    elif provider == ProviderType.AZURE:
        return AzureProviderAdapter()
    else:
        raise ValueError(f"Unknown provider type: {provider}")
