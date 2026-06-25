# AGENTS.md

Top-level guide for AI coding agents working in the **FinOps Wizard** repository. Covers repository-wide rules, architecture contracts, and development processes.

---

## Mandatory: Before Writing Any Code

Every change must adhere to these three rules. Read and apply them before implementing any change.

### 1. SOLID Principles
All Python implementation code must strictly follow SOLID principles:
* **Single Responsibility (SRP):** Each module (e.g., discovery, inventory, analysis) owns exactly one concern.
* **Open/Closed (OCP):** Extend behavior using adapters, new providers, or configuration options. Do not break or invasively edit stable, tested code.
* **Liskov Substitution (LSP):** Cloud adapters must implement `BaseProviderAdapter` and conform to its interface contracts.
* **Interface Segregation (ISP):** Keep interfaces focused. Adapters should only implement the required abstract hooks.
* **Dependency Inversion (DIP):** Core FinOps logic depends on abstract base classes/interfaces (`BaseProviderAdapter`), never concrete implementations.

### 2. Test-Driven Development (TDD)
This repository encourages test-first development. Follow these guidelines:
* Write a failing test reproducing the target requirement/bug first, then make it pass.
* Write the minimum code required to make tests pass. Refactor under green tests.
* Maintain high unit and TUI integration test coverage.
* Run the test suite: `uv run pytest`.

### 3. Domain Glossaries (CONTEXT.md and CONTEXT-MAP.md)
To ensure terminology alignment across agents and developers, the project uses domain context definitions:
* **[CONTEXT.md](finops_wizard/CONTEXT.md)** defines the canonical domain vocabulary:
  * **Burn Rate:** The current monthly spend extrapolated from the cloud billing baseline.
  * **Waste Resource:** Under-utilized compute, overprovisioned memory, or orphaned storage.
  * **Savings Opportunity:** Recoverable monthly cost calculated from rightsizing or upgrading.
  * **Inference Engine:** The local (Mock, Ollama) or remote (OpenAI, Anthropic) analyzer.
* **[CONTEXT-MAP.md](finops_wizard/CONTEXT-MAP.md)** maps the structured flow of data across our 5-phase optimization lifecycle:
  ```mermaid
  flowchart TD
      Discovery[Phase 1: Discovery] -->|Detected Workloads| Inventory[Phase 2: Inventory]
      Inventory -->|Waste Metrics| Analysis[Phase 3: Analysis & Patching]
      Analysis -->|Recommendations & Diffs| Monitoring[Phase 4: SQLite Log]
      Inventory & Discovery --> Alerting[Phase 5: Alerting & Webhooks]
  ```

---

## UI Component Documentation (WIRING.md)

Every major component directory in the Textual terminal user interface (`finops_wizard/tui/`) should contain or reference a **`WIRING.md`** file describing the component layout, interactivity, and event-flow contracts.

A conforming `WIRING.md` specifies:
* **User Experience (UX):** Hotkeys (e.g. `d` for Discovery, `escape` to return, `q` to quit), layouts (Dolphie-inspired glassmorphism styles), and spinner feedback.
* **Data Flow:** Configuration variables passed down from the central `App` class (`scan_mode`, `provider`, `iac_dir`, `llm_provider`, `llm_api_key`) and callbacks emitted upon widget events.
* **State Ownership:** Which screens or models own state elements (e.g., active report objects vs history tables).
* **Bridge Dependencies:** Calls to core persistence layers (`monitoring.py`), adapters (`aws.py`, `gcp.py`, `azure.py`), or alerts evaluator (`alerting.py`).

---

## Repository Layout

* **[finops_wizard/](finops_wizard/)** - Python Package Root
  * **[cli.py](finops_wizard/cli.py)** - Typer CLI commands and headless orchestration.
  * **[core/](finops_wizard/core/)** - FinOps Engine Phases
    * `models.py` - Pydantic data schemas.
    * `discovery.py` - Billing baseline scan & workload auto-detector.
    * `inventory.py` - Resource utilization metrics compiler.
    * `analysis.py` - Modular Terraform block parser & variables patch generator.
    * `monitoring.py` - SQLite state persistence logger.
    * `alerting.py` - Governance rule evaluator & webhook trigger.
  * **[adapters/](finops_wizard/adapters/)** - Cloud provider mock APIs and dry-run CLI command loggers.
  * **[tui/](finops_wizard/tui/)** - Textual TUI Application
    * `app.py` - Main TUI runner and custom Dolphie-inspired color palette.
    * `screens.py` - UI view screens (Main Menu, Dashboard, Scan, Analysis, SaaS Bridge).
    * `styles.tcss` - Terminal styling sheet.
    * `widgets/` - Dialog modals, TopBar, and Spinner widgets.
* **[examples/iac/](examples/iac/)** - Enterprise IaC Terraform examples
  * `modules/` - compute, kubernetes, serverless module resources.
  * `environments/` - production and staging environment layouts calling modules.
* **[tests/](tests/)** - Pytest test suite (`test_finops_wizard.py`).

---

## Development Commands

Run commands from the repository root:

* **Install dependencies:** `uv pip install -e .`
* **Run test suite:** `uv run pytest`
* **Run TUI Application:** `uv run finops-wizard`
* **Run Headless CLI Scan:** `PYTHONPATH=. uv run finops-wizard --mode workloads --provider aws --phase all`
* **Run Headless CLI Analysis against IaC:** `PYTHONPATH=. uv run finops-wizard --mode workloads --provider aws --phase analysis --iac-dir examples/iac/environments/production`

---

## Process Rules

### 1. Structured Logging and Trust Building
* **Dry-Run Logging:** Cloud adapters must record the exact simulated CLI/SDK commands executed. These must be logged visually during scans (via `ScanScreen` console logs) to prove read-only safety and build end-user trust.
* **SQLite Persistence:** Scan results must be saved locally to SQLite (`monitoring.db`). Do not rely on external backend states for local history.

### 2. Prohibited Git Commands
* **`git stash` is prohibited.** It can lead to concurrent work loss when multiple agents/worktrees operate on the same repository. Commit to temporary branches instead.

### 3. Never Patch Installed Third-Party Packages
* Do not modify `.venv/` or system python packages. Rely on local wrappers, strategy overrides, or mock adapters if necessary.
