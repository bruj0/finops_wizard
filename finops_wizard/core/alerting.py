"""Phase 5 Alerting module.

Evaluates thresholds for cost wastes, anomalies, and tagging coverage,
and executes webhook dispatches or local alerts.
"""

from typing import Any, Dict, List, Optional
import httpx
from finops_wizard.core.models import DiscoveryReport, InventoryReport


class AlertCondition:
    """Represents an alert rule and status."""
    
    def __init__(self, name: str, value: Any, threshold: Any, is_triggered: bool, message: str) -> None:
        self.name = name
        self.value = value
        self.threshold = threshold
        self.is_triggered = is_triggered
        self.message = message


def evaluate_alerts(
    discovery: DiscoveryReport,
    inventory: InventoryReport,
    webhook_url: Optional[str] = None
) -> List[AlertCondition]:
    """Inspects reports against cost and hygiene thresholds.
    
    Args:
        discovery: The Phase 1 DiscoveryReport.
        inventory: The Phase 2 InventoryReport.
        webhook_url: Optional Webhook HTTP endpoint to post alerts to.
        
    Returns:
        List of AlertCondition evaluations.
    """
    conditions: List[AlertCondition] = []

    # 1. Check Potential Waste Savings Threshold (Trigger if > $200)
    savings_trigger = inventory.potential_savings > 200.0
    conditions.append(AlertCondition(
        name="High Potential Savings Waste",
        value=inventory.potential_savings,
        threshold=200.0,
        is_triggered=savings_trigger,
        message=(
            f"ALERT: Potential monthly savings of ${inventory.potential_savings:,.2f} "
            f"exceeds warning threshold of $200.00." if savings_trigger else "Savings waste is within acceptable limits."
        )
    ))

    # 2. Check Anomalies Threshold (Trigger if > 0)
    anomalies_trigger = discovery.detected_anomalies > 0
    conditions.append(AlertCondition(
        name="Cost Anomalies Detected",
        value=discovery.detected_anomalies,
        threshold=0,
        is_triggered=anomalies_trigger,
        message=(
            f"ALERT: {discovery.detected_anomalies} cost anomalies detected in "
            f"the last billing cycle!" if anomalies_trigger else "No cost anomalies detected."
        )
    ))

    # 3. Check Tag Coverage Hygiene (Trigger if < 70%)
    tag_trigger = discovery.tag_coverage_pct < 70.0
    conditions.append(AlertCondition(
        name="Low Tag Coverage",
        value=discovery.tag_coverage_pct,
        threshold=70.0,
        is_triggered=tag_trigger,
        message=(
            f"ALERT: Tag coverage is at {discovery.tag_coverage_pct}%, which is below the "
            f"governance target of 70%." if tag_trigger else "Tag coverage satisfies baseline policy."
        )
    ))

    # Trigger webhook if active alerts are present and webhook URL is provided
    triggered_alerts = [c for c in conditions if c.is_triggered]
    if webhook_url and triggered_alerts:
        try:
            payload = {
                "event": "finops_wizard_alert",
                "provider": discovery.provider.value,
                "mode": discovery.mode,
                "alerts": [
                    {"name": c.name, "value": str(c.value), "message": c.message}
                    for c in triggered_alerts
                ]
            }
            # Perform POST call asynchronously (mocked or fast timeout)
            with httpx.Client(timeout=2.0) as client:
                client.post(webhook_url, json=payload)
        except Exception:
            pass  # Local webhook hook handles failures gracefully without crashing CLI

    return conditions
