# Domain Context Map: FinOps Wizard Subsystems

This document maps how data flows across the core subsystems of the FinOps Wizard.

```mermaid
flowchart TD
    Discovery[core/discovery.py] -->|DiscoveryReport| Inventory[core/inventory.py]
    Inventory -->|InventoryReport| Analysis[core/analysis.py]
    
    subgraph Data Adapters
        adapters_base[adapters/base.py] --> adapters_aws[adapters/aws.py]
        adapters_base --> adapters_gcp[adapters/gcp.py]
        adapters_base --> adapters_azure[adapters/azure.py]
    end
    
    adapters_aws & adapters_gcp & adapters_azure -->|Mock APIs / Dry-Run Log| Discovery & Inventory
    
    Analysis -->|AnalysisReport with Diffs| Monitoring[core/monitoring.py]
    
    Inventory & Discovery -->|Reports Context| Alerting[core/alerting.py]
    
    Monitoring -->|Local History SQL log| SQLite[monitoring.db]
    Alerting -->|JSON Payload| Webhook[HTTP Webhook Endpoint]
    
    subgraph User Interfaces
        tui_app[tui/app.py] --> tui_screens[tui/screens.py]
        cli_runner[cli.py] --> tui_app
    end
    
    Discovery & Inventory & Analysis & Alerting -->|UI rendering| tui_screens
    cli_runner -->|Headless Exec| Discovery & Inventory & Analysis & Monitoring & Alerting
```

## Lifecycle States and Data Contracts

1. **Discovery (Phase 1):** Scans the billing adapter and outputs `DiscoveryReport`.
2. **Inventory (Phase 2):** Queries compute and storage resources using `DiscoveryReport.detected_workloads` and compiles them into `InventoryReport` containing `InventoryItem` listings.
3. **Analysis & Patching (Phase 3):** Inspects the target `iac_dir`, parses Terraform blocks, and matches inventory items to generate `AnalysisReport` with markdown text and unified diff patches.
4. **Monitoring (Phase 4):** Stores `DiscoveryReport` and `InventoryReport` in a local SQLite file using `save_run`.
5. **Alerting (Phase 5):** Evaluates metric thresholds and triggers target HTTP webhooks for active alerts.
