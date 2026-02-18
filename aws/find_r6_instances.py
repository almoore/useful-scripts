#!/usr/bin/env python3
"""
Terraform R6 to R7 Instance Type Analyzer

Scans Terraform files for r6 instance types and suggests equivalent r7 instance types.
Supports JSON, YAML, and Markdown table output formats.
"""

import re
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class R6InstanceFinder:
    """Finds and analyzes r6 instance types in Terraform files."""

    # Mapping of r6 instance types to their r7 equivalents
    R6_TO_R7_MAP = {
        'r6i': 'r7i',   # Intel-based r6 to r7
        'r6a': 'r7a',   # AMD-based r6 to r7
        'r6g': 'r7g',   # Graviton r6 to r7
        'r6id': 'r7iz', # r6id with local NVMe to r7iz
        'r6idn': 'r7iz', # r6idn with networking to r7iz
        'r6in': 'r7iz',  # r6in with networking to r7iz
    }

    def __init__(self, root_dir: str, db_only: bool = False):
        self.root_dir = Path(root_dir)
        self.db_only = db_only
        self.findings: List[Dict[str, Any]] = []

    def find_r6_instances(self) -> List[Dict[str, Any]]:
        """Scan all .tf files for r6 instance types."""
        tf_files = []

        # Recursively find .tf files, excluding .terraform directories
        for tf_file in self.root_dir.rglob("*.tf"):
            # Skip files in .terraform directories
            if '.terraform' in tf_file.parts:
                continue
            tf_files.append(tf_file)

        for tf_file in tf_files:
            try:
                with open(tf_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._parse_file(tf_file, content)
            except Exception as e:
                print(f"Warning: Could not read {tf_file}: {e}")

        return self.findings

    def _parse_file(self, file_path: Path, content: str):
        """Parse a single Terraform file for r6 instances."""
        # Pattern to match r6 instance types
        # Matches: r6i.xlarge, db.r6g.large, cache.r6g.xlarge, etc.
        if self.db_only:
            # Only match database instance types (db.r6*, cache.r6*)
            r6_pattern = re.compile(r'\b(db|cache)\.(r6[a-z]*)\.([\w]+)\b', re.IGNORECASE)
        else:
            # Match all r6 instance types (with optional db./cache. prefix)
            r6_pattern = re.compile(r'\b(?:(db|cache)\.)?(r6[a-z]*)\.([\w]+)\b', re.IGNORECASE)

        # Find all r6 instances
        matches = r6_pattern.finditer(content)

        for match in matches:
            # Extract prefix (db/cache) if present
            if self.db_only:
                prefix = match.group(1).lower()
                instance_family = match.group(2).lower()
                instance_size = match.group(3)
            else:
                prefix = match.group(1).lower() if match.group(1) else None
                instance_family = match.group(2).lower()
                instance_size = match.group(3)

            # Build full instance type string
            if prefix:
                full_instance = f"{prefix}.{instance_family}.{instance_size}"
            else:
                full_instance = f"{instance_family}.{instance_size}"

            # Find the context around the match
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(content), match.end() + 200)
            context = content[start_pos:end_pos]

            # Try to extract resource/module information
            resource_info = self._extract_resource_info(content, match.start())

            # Try to find replica/count information
            replica_info = self._extract_replica_info(content, match.start())

            # Generate r7 suggestion
            r7_suggestion = self._get_r7_equivalent(instance_family, instance_size, prefix)

            # Get line number
            line_number = content[:match.start()].count('\n') + 1

            finding = {
                'file': str(file_path.relative_to(self.root_dir)),
                'line': line_number,
                'current_instance': full_instance,
                'suggested_instance': r7_suggestion,
                'resource_type': resource_info.get('type', 'Unknown'),
                'resource_name': resource_info.get('name', 'Unknown'),
                'replicas': replica_info.get('count', 1),
                'replica_config': replica_info.get('config', 'N/A'),
            }

            self.findings.append(finding)

    def _extract_resource_info(self, content: str, match_pos: int) -> Dict[str, str]:
        """Extract resource or module information from context."""
        # Look backwards from match position to find resource/module declaration
        lines_before = content[:match_pos].split('\n')

        for line in reversed(lines_before[-50:]):  # Check up to 50 lines before
            # Match resource "type" "name"
            resource_match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', line)
            if resource_match:
                return {'type': resource_match.group(1), 'name': resource_match.group(2)}

            # Match module "name"
            module_match = re.search(r'module\s+"([^"]+)"', line)
            if module_match:
                return {'type': 'module', 'name': module_match.group(1)}

        return {'type': 'Unknown', 'name': 'Unknown'}

    def _extract_replica_info(self, content: str, match_pos: int) -> Dict[str, Any]:
        """Extract replica/count information from context."""
        # Look for count, desired_capacity, min_size, max_size, etc.
        lines_around = content[max(0, match_pos-500):match_pos+500].split('\n')

        replica_info = {'count': 1, 'config': 'N/A'}

        for line in lines_around:
            # Look for various count-related configurations
            count_match = re.search(r'count\s*=\s*(\d+)', line)
            if count_match:
                replica_info['count'] = int(count_match.group(1))
                replica_info['config'] = 'count'

            desired_match = re.search(r'desired_(?:capacity|size)\s*=\s*(\d+)', line)
            if desired_match:
                replica_info['count'] = int(desired_match.group(1))
                replica_info['config'] = 'desired_capacity'

            min_match = re.search(r'min_size\s*=\s*(\d+)', line)
            max_match = re.search(r'max_size\s*=\s*(\d+)', line)
            if min_match and max_match:
                min_val = int(min_match.group(1))
                max_val = int(max_match.group(1))
                replica_info['count'] = f"{min_val}-{max_val}"
                replica_info['config'] = 'autoscaling'

        return replica_info

    def _get_r7_equivalent(self, r6_family: str, instance_size: str, prefix: str = None) -> str:
        """Map r6 instance family to r7 equivalent."""
        r7_family = self.R6_TO_R7_MAP.get(r6_family.lower(), 'r7i')  # Default to r7i

        if prefix:
            return f"{prefix}.{r7_family}.{instance_size}"
        return f"{r7_family}.{instance_size}"


class OutputFormatter:
    """Formats findings into various output formats."""

    @staticmethod
    def to_json(findings: List[Dict[str, Any]], indent: int = 2) -> str:
        """Format findings as JSON."""
        return json.dumps({
            'summary': {
                'total_findings': len(findings),
                'unique_r6_types': len(set(f['current_instance'] for f in findings)),
            },
            'findings': findings
        }, indent=indent)

    @staticmethod
    def to_yaml(findings: List[Dict[str, Any]]) -> str:
        """Format findings as YAML."""
        try:
            import yaml
            return yaml.dump({
                'summary': {
                    'total_findings': len(findings),
                    'unique_r6_types': len(set(f['current_instance'] for f in findings)),
                },
                'findings': findings
            }, default_flow_style=False, sort_keys=False)
        except ImportError:
            return "Error: PyYAML not installed. Use JSON or Markdown format instead."

    @staticmethod
    def to_markdown(findings: List[Dict[str, Any]]) -> str:
        """Format findings as Markdown table."""
        if not findings:
            return "# R6 to R7 Instance Analysis\n\nNo r6 instances found."

        # Summary
        unique_r6 = set(f['current_instance'] for f in findings)
        md = f"# R6 to R7 Instance Analysis\n\n"
        md += f"**Total Findings:** {len(findings)}  \n"
        md += f"**Unique R6 Instance Types:** {len(unique_r6)}\n\n"

        # Group by current instance type
        grouped = defaultdict(list)
        for finding in findings:
            grouped[finding['current_instance']].append(finding)

        md += "## Summary by Instance Type\n\n"
        md += "| Current Instance | Suggested R7 | Occurrences |\n"
        md += "|-----------------|--------------|-------------|\n"
        for instance_type in sorted(grouped.keys()):
            r7_type = findings[0]['suggested_instance'] if findings else "N/A"
            for f in grouped[instance_type]:
                if f['current_instance'] == instance_type:
                    r7_type = f['suggested_instance']
                    break
            md += f"| {instance_type} | {r7_type} | {len(grouped[instance_type])} |\n"

        # Detailed findings
        md += "\n## Detailed Findings\n\n"
        md += "| File | Line | Resource Type | Resource Name | Current Instance | Suggested R7 | Replicas | Config |\n"
        md += "|------|------|---------------|---------------|------------------|--------------|----------|--------|\n"

        for finding in findings:
            md += f"| {finding['file']} | {finding['line']} | {finding['resource_type']} | "
            md += f"{finding['resource_name']} | {finding['current_instance']} | "
            md += f"{finding['suggested_instance']} | {finding['replicas']} | {finding['replica_config']} |\n"

        return md


def main():
    parser = argparse.ArgumentParser(
        description='Find r6 instances in Terraform files and suggest r7 equivalents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Markdown table (default)
  python find_r6_instances.py

  # JSON output
  python find_r6_instances.py --format json

  # YAML output (requires PyYAML)
  python find_r6_instances.py --format yaml

  # Database instances only (db.r6*, cache.r6*)
  python find_r6_instances.py --db-only

  # Scan specific directory
  python find_r6_instances.py --root-dir /path/to/terraform

  # Save to file
  python find_r6_instances.py --format json --output results.json
        """
    )

    parser.add_argument(
        '--root-dir',
        default='.',
        help='Root directory to scan for Terraform files (default: current directory)'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'yaml', 'markdown'],
        default='markdown',
        help='Output format (default: markdown)'
    )

    parser.add_argument(
        '--output',
        '-o',
        help='Output file (default: stdout)'
    )

    parser.add_argument(
        '--db-only',
        action='store_true',
        help='Only find database instance types (db.r6*, cache.r6*)'
    )

    args = parser.parse_args()

    # Find r6 instances
    instance_type = "database" if args.db_only else "all"
    print(f"Scanning Terraform files for {instance_type} r6 instances...", flush=True)
    finder = R6InstanceFinder(args.root_dir, db_only=args.db_only)
    findings = finder.find_r6_instances()

    print(f"Found {len(findings)} r6 instance references.\n", flush=True)

    # Format output
    formatter = OutputFormatter()
    if args.format == 'json':
        output = formatter.to_json(findings)
    elif args.format == 'yaml':
        output = formatter.to_yaml(findings)
    else:  # markdown
        output = formatter.to_markdown(findings)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()

