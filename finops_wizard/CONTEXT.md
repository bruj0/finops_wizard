# Domain Vocabulary: FinOps Wizard

This glossary defines the canonical domain terms used across the FinOps Wizard application codebase, documentation, and tests.

---

## Terms

### Baseline Cost
* **Definition:** The initial cost profile extracted during the billing scan, representing current run-rate spend.
* **Canonical usage:** `monthly_burn_rate`, `raw_billing_metrics`.

### Discovery
* **Definition:** Phase 1 execution that detects active cloud credentials, active regions, anomalies, and active workload types.
* **Canonical usage:** `run_discovery`, `DiscoveryReport`.

### Inventory Catalog
* **Definition:** Phase 2 catalog of discovered compute hosts, clusters, serverless targets, and volumes, alongside utilization metrics.
* **Canonical usage:** `run_inventory`, `InventoryReport`.

### Waste Resource
* **Definition:** An under-utilized, overprovisioned, or orphaned cloud resource that incurs costs with zero or minimal utility.
* **Canonical usage:** `is_waste`, `waste_resources`, `waste_reason`.

### Savings Opportunity
* **Definition:** The estimated recoverable cost (monthly) achievable by applying the recommended optimizations.
* **Canonical usage:** `potential_savings`, `savings_pct`.

### Inference Engine
* **Definition:** The LLM provider (Mock, Ollama, OpenAI, Anthropic) queried to generate optimization recommendations and code diffs.
* **Canonical usage:** `llm_provider`, `api_key`.

### IaC Targeting
* **Definition:** The process of scanning a local IaC directory, resolving relative module calls, and compiling code patches.
* **Canonical usage:** `iac_dir`, `terraform_file`, `patch`.
