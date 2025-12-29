"""Command-line interface for terravisualizer."""

import argparse
import sys
import os
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
        default=None,
        help="Path to the configuration file (default: embedded terravisualizer.hcl)",
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

    # Handle config file - use embedded default if not provided
    config_file = None
    if args.config:
        config_file = Path(args.config)
        if not config_file.exists():
            print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
    else:
        # Try to find embedded config (for PyInstaller builds)
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            bundled_hcl = Path(sys._MEIPASS) / "terravisualizer.hcl"
            bundled_json = Path(sys._MEIPASS) / "terravisualizer.json"
            if bundled_hcl.exists():
                config_file = bundled_hcl
            elif bundled_json.exists():
                config_file = bundled_json
        
        # Fallback to local files if not bundled
        if not config_file:
            if Path("terravisualizer.hcl").exists():
                config_file = Path("terravisualizer.hcl")
            elif Path("terravisualizer.json").exists():
                config_file = Path("terravisualizer.json")
        
        if not config_file:
            print(f"Error: No configuration file found. Please provide one with --config", file=sys.stderr)
            sys.exit(1)

    try:
        # Load configuration
        print(f"Loading configuration from {config_file}...")
        config = load_config(str(config_file))

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
