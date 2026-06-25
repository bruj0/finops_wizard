"""Phase 4 Monitoring database module.

Handles persistence of local execution histories using SQLite, and simulates
the secure upload payload of the SaaS synchronization.
"""

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List
from finops_wizard.core.models import DiscoveryReport, InventoryReport

DB_PATH = os.path.expanduser("~/.finops_wizard.db")


def init_db() -> None:
    """Initializes the local SQLite database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            mode TEXT NOT NULL,
            monthly_burn_rate REAL NOT NULL,
            total_resources INTEGER NOT NULL,
            waste_resources INTEGER NOT NULL,
            potential_savings REAL NOT NULL,
            detected_anomalies INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_run(discovery: DiscoveryReport, inventory: InventoryReport) -> int:
    """Persists a scan run into the SQLite history.
    
    Args:
        discovery: The Phase 1 DiscoveryReport.
        inventory: The Phase 2 InventoryReport.
        
    Returns:
        The database row ID of the inserted run.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp_str = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO scan_history (
            timestamp, provider, mode, monthly_burn_rate,
            total_resources, waste_resources, potential_savings, detected_anomalies
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_str,
        discovery.provider.value,
        discovery.mode,
        discovery.monthly_burn_rate,
        inventory.total_resources,
        inventory.waste_resources,
        inventory.potential_savings,
        discovery.detected_anomalies
    ))
    
    run_id = cursor.lastrowid or 0
    conn.commit()
    conn.close()
    return run_id


def get_history() -> List[Dict[str, Any]]:
    """Retrieves all past scan records from the SQLite database.
    
    Returns:
        A list of dictionaries representing historic scan records.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM scan_history ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    
    history = []
    for r in rows:
        history.append(dict(r))
        
    conn.close()
    return history


def sync_to_saas(api_key: str, discovery: DiscoveryReport, inventory: InventoryReport) -> Dict[str, Any]:
    """Simulates the SaaS upsell sync gateway.
    
    Serializes reports to show the user exactly what telemetry is being sent
    before transmission (to build trust).
    
    Args:
        api_key: User SaaS registration/API key.
        discovery: The Phase 1 DiscoveryReport.
        inventory: The Phase 2 InventoryReport.
        
    Returns:
        A dict containing status and serialized JSON payloads.
    """
    payload = {
        "sync_time": datetime.now().isoformat(),
        "api_key_masked": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***",
        "discovery": discovery.model_dump(mode="json"),
        "inventory": inventory.model_dump(mode="json")
    }
    
    # In a real SaaS application, we would make a POST request:
    # response = httpx.post("https://api.saas-finops.com/v1/sync", json=payload, headers={"X-API-Key": api_key})
    
    return {
        "success": True,
        "message": "Successfully synchronized local metrics with SaaS Control Panel.",
        "payload": payload
    }
