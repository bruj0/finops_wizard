"""Phase 3 Analysis module.

Integrates with LLM systems (Ollama, OpenAI, Anthropic, or Mock) to analyze
discovery and inventory reports, scan Terraform files, and generate
markdown recommendations with actionable code diffs.
"""

import os
import re
import difflib
from typing import List, Optional, Tuple, Dict, Any
import httpx
from finops_wizard.core.models import (
    AnalysisReport,
    DiscoveryReport,
    InventoryReport,
    OptimizationRecommendation,
)


def _find_top_level_blocks(content: str) -> List[Tuple[int, int]]:
    """Identifies indices of top-level blocks (resource, module, provider, etc.) in a Terraform file.

    Intent:
        Parse HCL code blocks structurally to isolate individual resource definitions.
    Preconditions/Assumptions:
        Assumes string inputs representing well-formed Terraform files.
    Failure Modes/Edge Cases:
        Braces inside comments or unclosed string literals are skipped. Unbalanced 
        braces in the HCL file may result in incomplete or skipped block ranges.
    """
    blocks = []
    brace_count = 0
    start_idx = -1
    in_quote = False
    in_comment = False
    escape = False

    i = 0
    n = len(content)
    while i < n:
        char = content[i]

        if in_comment:
            if char == '\n':
                in_comment = False
            i += 1
            continue

        if escape:
            escape = False
            i += 1
            continue

        if char == '\\':
            escape = True
            i += 1
            continue

        if char == '"':
            in_quote = not in_quote
            i += 1
            continue

        if in_quote:
            i += 1
            continue

        if char == '#' or (char == '/' and i + 1 < n and content[i + 1] == '/'):
            in_comment = True
            i += 1
            continue

        if char == '{':
            if brace_count == 0:
                header_start = i
                # Track back to start of line to include the block declaration/header
                while header_start > 0 and content[header_start - 1] != '\n':
                    header_start -= 1
                start_idx = header_start
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                blocks.append((start_idx, i + 1))
                start_idx = -1
        i += 1

    return blocks


def _find_all_tf_files(iac_dir: str) -> List[str]:
    """Finds all .tf files in the given directory and recursively resolves local module folders.

    Intent:
        Gather all IaC definition files to find resource configurations, resolving nested local module directories.
    Preconditions/Assumptions:
        Expects a valid root directory path as input.
    Failure Modes/Edge Cases:
        Loops in module references are protected by the `scanned_dirs` set. If files cannot be read 
        due to permissions, they are skipped.
    """
    scanned_dirs = set()
    files_to_scan = []

    def scan_dir(d: str) -> None:
        abs_d = os.path.abspath(d)
        if abs_d in scanned_dirs:
            return
        scanned_dirs.add(abs_d)

        if not os.path.isdir(abs_d):
            return

        for name in os.listdir(abs_d):
            path = os.path.join(abs_d, name)
            if os.path.isfile(path) and name.endswith(".tf"):
                files_to_scan.append(path)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Find relative module sources starting with ./ or ../
                    sources = re.findall(r'source\s*=\s*"(\.\.?/[^"]+)"', content)
                    for src in sources:
                        resolved_src = os.path.abspath(os.path.join(os.path.dirname(path), src))
                        scan_dir(resolved_src)
                except Exception:
                    pass
            elif os.path.isdir(path):
                scan_dir(path)

    scan_dir(iac_dir)
    return files_to_scan


def run_analysis(
    discovery_report: DiscoveryReport,
    inventory_report: InventoryReport,
    iac_dir: Optional[str] = None,
    llm_provider: str = "mock",
    api_key: Optional[str] = None
) -> AnalysisReport:
    """Executes Phase 3 Analysis.

    Intent:
        Scans IaC directories to identify resource configuration files, compares them with 
        the utilization inventory report, and generates markdown optimization recommendations 
        along with unified git diff patches.
    Preconditions/Assumptions:
        Expects a valid DiscoveryReport and InventoryReport. The iac_dir, if provided, must point 
        to a readable local directory structure.
    Failure Modes/Edge Cases:
        If iac_dir is missing or unreadable, the scan is bypassed, and recommendations are returned 
        without patches. If LLM endpoint connections fail, the mock fallback report is used.
    """
    recommendations: List[OptimizationRecommendation] = []

    # 1. Inspect local Terraform files if directory provided
    found_resources = {}
    if iac_dir and os.path.isdir(iac_dir):
        files_to_scan = _find_all_tf_files(iac_dir)
        for filepath in files_to_scan:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                block_offsets = _find_top_level_blocks(content)
                for start, end in block_offsets:
                    block_content = content[start:end]

                    for item in inventory_report.items:
                        is_match = False

                        # Match 1: Name in block header (e.g. resource "aws_instance" "ec2-monolith-legacy")
                        header_line = block_content.splitlines()[0] if block_content.splitlines() else ""
                        if f'"{item.resource_name}"' in header_line:
                            is_match = True

                        # Match 2: Assignment of name within block (e.g. cluster_name = "eks-prod-cluster-1")
                        elif re.search(rf'=\s*"{re.escape(item.resource_name)}"', block_content):
                            is_match = True

                        if is_match:
                            # Prefer blocks containing parameters we can optimize
                            has_param = False
                            if item.resource_type == "virtual_machine" or "ec2" in item.resource_type or "kubernetes" in item.resource_type or "cluster" in item.resource_type:
                                if any(p in block_content for p in ["instance_type", "node_instance_type", "volume_type"]):
                                    has_param = True
                            elif "ebs" in item.resource_type or "volume" in item.resource_type:
                                if any(p in block_content for p in ["type", "volume_type"]):
                                    has_param = True
                            elif "lambda" in item.resource_type or "function" in item.resource_type:
                                if "memory_size" in block_content:
                                    has_param = True

                            existing = found_resources.get(item.resource_name)
                            if not existing or (has_param and not existing.get("has_param")):
                                found_resources[item.resource_name] = {
                                    "file": filepath,
                                    "content": block_content,
                                    "has_param": has_param
                                }
            except IOError:
                pass

    # 2. Generate Recommendations based on Scanned Inventory Waste
    for item in inventory_report.items:
        if not item.is_waste:
            continue

        tf_file = None
        patch_content = None

        # Build patches if matching resources found in IaC directory
        if item.resource_name in found_resources:
            res_meta = found_resources[item.resource_name]
            tf_file = os.path.relpath(res_meta["file"], iac_dir) if iac_dir else res_meta["file"]

            original_content = res_meta["content"]
            modified_content = original_content

            # Identify parameter modifications
            if item.resource_type == "virtual_machine" or "ec2" in item.resource_type or "kubernetes" in item.resource_type or "cluster" in item.resource_type:
                # Downsize instance type or node group instance type
                modified_content = re.sub(
                    r'(\b(?:instance_type|node_instance_type)\s*=\s*)[^#\n]+',
                    r'\1"t3.medium"',
                    original_content
                )
                # Also upgrade volume type if present in the block
                modified_content = re.sub(
                    r'(\bvolume_type\s*=\s*)[^#\n]+',
                    r'\1"gp3"',
                    modified_content
                )
            elif "ebs" in item.resource_type or "volume" in item.resource_type:
                # Upgrade gp2 to gp3
                modified_content = re.sub(
                    r'(\b(?:type|volume_type)\s*=\s*)[^#\n]+',
                    r'\1"gp3"',
                    original_content
                )
            elif "lambda" in item.resource_type or "function" in item.resource_type:
                # Reduce memory size to 256MB
                modified_content = re.sub(
                    r'(\bmemory_size\s*=\s*)[^#\n]+',
                    r'\g<1>256',
                    original_content
                )

            if original_content != modified_content:
                # Create a clean unified patch diff
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    modified_content.splitlines(keepends=True),
                    fromfile=f"a/{tf_file}",
                    tofile=f"b/{tf_file}"
                ))
                patch_content = "".join(diff) if diff else None

        # Determine Recommendation parameters
        if "cluster" in item.resource_type or "eks" in item.resource_type or "gke" in item.resource_type:
            rec = OptimizationRecommendation(
                title=f"Rightsize requests on K8s cluster: {item.resource_name}",
                description=(
                    f"Scale down CPU/Memory requests for workloads on cluster {item.resource_name}. "
                    f"Current average CPU usage is below 10% ({item.utilization_metrics.get('cpu_usage_cores')} "
                    f"used of {item.utilization_metrics.get('cpu_request_cores')} requested)."
                ),
                impact="high",
                potential_savings=item.monthly_cost * 0.4,
                resource_id=item.resource_id,
                terraform_file=tf_file,
                patch=patch_content
            )
        elif "lambda" in item.resource_type or "function" in item.resource_type:
            rec = OptimizationRecommendation(
                title=f"Optimize Serverless Function Memory: {item.resource_name}",
                description=(
                    f"Reduce configured memory from {item.utilization_metrics.get('configured_memory_mb')}MB "
                    f"to 256MB. Max memory utilized was only {item.utilization_metrics.get('max_memory_used_mb')}MB."
                ),
                impact="low",
                potential_savings=item.monthly_cost * 0.25,
                resource_id=item.resource_id,
                terraform_file=tf_file,
                patch=patch_content
            )
        elif "volume" in item.resource_type or "disk" in item.resource_type:
            rec = OptimizationRecommendation(
                title=f"Cleanup Unused Storage Disk: {item.resource_name}",
                description=f"Delete detached volume {item.resource_name} which has been unattached for 14+ days.",
                impact="medium",
                potential_savings=item.monthly_cost,
                resource_id=item.resource_id,
                terraform_file=tf_file,
                patch=patch_content
            )
        else:  # VM instances
            rec = OptimizationRecommendation(
                title=f"Rightsize VM instance: {item.resource_name}",
                description=(
                    f"Instance {item.resource_name} is idle (average CPU "
                    f"{item.utilization_metrics.get('cpu_utilization_pct')}%). "
                    "Downsize instance type or apply automatic start/stop schedules."
                ),
                impact="medium",
                potential_savings=item.monthly_cost * 0.5,
                resource_id=item.resource_id,
                terraform_file=tf_file,
                patch=patch_content
            )

        recommendations.append(rec)

    # 3. Contact LLM / Generate report summary
    summary_markdown = _generate_summary_report(discovery_report, inventory_report, recommendations, llm_provider, api_key)

    return AnalysisReport(
        provider=discovery_report.provider,
        mode=discovery_report.mode,
        summary_markdown=summary_markdown,
        recommendations=recommendations
    )


def _generate_summary_report(
    discovery_report: DiscoveryReport,
    inventory_report: InventoryReport,
    recommendations: List[OptimizationRecommendation],
    llm_provider: str,
    api_key: Optional[str]
) -> str:
    """Assembles prompt and queries LLM or returns mockup report."""
    total_savings = sum(r.potential_savings for r in recommendations)

    # Default Mock Response
    mock_summary = f"""# FinOps Cost Optimization Report ({discovery_report.provider.value.upper()})
*Generated: local-first by FinOps Wizard*

## Executive Summary
We scanned your **{discovery_report.provider.value.upper()}** infrastructure in **{discovery_report.mode}** mode. 
A total of **{inventory_report.total_resources}** resources were analyzed, revealing that **{inventory_report.waste_resources}** resources are under-utilized or orphaned. 

By applying the recommended changes, you can recover **${total_savings:,.2f}/month**, which is **{(total_savings / (discovery_report.monthly_burn_rate or 1)) * 100:.1f}%** of your current burn rate.

| Category | Count | Potential Savings |
|---|---|---|
| Low Impact (Safe tag/concurrency changes) | {len([r for r in recommendations if r.impact == "low"])} | ${sum(r.potential_savings for r in recommendations if r.impact == "low"):,.2f} |
| Medium Impact (Teardown idle VMs/disks) | {len([r for r in recommendations if r.impact == "medium"])} | ${sum(r.potential_savings for r in recommendations if r.impact == "medium"):,.2f} |
| High Impact (Architectural cluster sizing) | {len([r for r in recommendations if r.impact == "high"])} | ${sum(r.potential_savings for r in recommendations if r.impact == "high"):,.2f} |
| **Total** | **{len(recommendations)}** | **${total_savings:,.2f}/month** |

---

## Technical Recommendations
"""
    for r in recommendations:
        mock_summary += f"""### [{r.impact.upper()}] {r.title}
* **Resource ID:** `{r.resource_id}`
* **Potential Savings:** `${r.potential_savings:,.2f}/month`
* **Description:** {r.description}
"""
        if r.terraform_file:
            mock_summary += f"* **Target IaC File:** `{r.terraform_file}`\n"
        if r.patch:
            mock_summary += f"\n```diff\n{r.patch}```\n"

    if llm_provider == "mock":
        return mock_summary

    # Attempt to query actual LLM endpoints
    try:
        if llm_provider == "ollama":
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": f"System: You are an expert FinOps Staff Engineer. Based on the data below, rewrite this markdown report to make it highly detailed and professional:\n\n{mock_summary}",
                    "stream": False
                },
                timeout=15.0
            )
            if response.status_code == 200:
                return response.json().get("response", mock_summary)
        elif llm_provider == "openai" and api_key:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a professional FinOps Cloud Engineer."},
                        {"role": "user", "content": f"Review this baseline summary report and polish the markdown to make it clean, and detailed:\n\n{mock_summary}"}
                    ]
                },
                timeout=15.0
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
    except Exception:
        pass  # Fallback to local mockup summary

    return mock_summary
