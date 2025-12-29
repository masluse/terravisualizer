"""Command-line interface for terravisualizer."""

import argparse
import sys
from pathlib import Path

from terravisualizer.config_parser import load_config
from terravisualizer.plan_parser import parse_terraform_plan
from terravisualizer.visualizer import generate_diagram


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Generate visual diagrams from Terraform plan files with grouped resources"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the Terraform plan JSON file",
    )
    parser.add_argument(
        "--config",
        default="terravisualizer.hcl",
        help="Path to the configuration file (default: terravisualizer.hcl)",
    )
    parser.add_argument(
        "--output",
        default="terraform_diagram.png",
        help="Output file path (default: terraform_diagram.png)",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "svg", "pdf"],
        help="Output format (default: png)",
    )

    args = parser.parse_args()

    # Validate input file
    plan_file = Path(args.file)
    if not plan_file.exists():
        print(f"Error: Terraform plan file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    # Validate config file
    config_file = Path(args.config)
    if not config_file.exists():
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load configuration
        print(f"Loading configuration from {args.config}...")
        config = load_config(args.config)

        # Parse Terraform plan
        print(f"Parsing Terraform plan from {args.file}...")
        resources = parse_terraform_plan(args.file)

        # Generate diagram
        print(f"Generating diagram...")
        output_path = generate_diagram(resources, config, args.output, args.format)

        print(f"Diagram generated successfully: {output_path}")

    except Exception as e:
        import traceback
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
