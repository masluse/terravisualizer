# Terravisualizer - Release Summary

## Overview
Terravisualizer is a Python CLI tool that generates visual diagrams from Terraform plan JSON files with hierarchically grouped resources.

## Key Features Implemented

### 1. CLI Tool
- Command-line interface with argparse
- Options for input file, config file, output file, and format
- Help documentation
- Entry point: `terravisualizer`

### 2. Configuration System
- Support for HCL-like configuration format
- Support for JSON configuration format
- Configuration options:
  - `grouped_by`: Array of attributes for hierarchical grouping
  - `diagram_image`: Path to icon for resource type
  - `name`: Attribute path for display name

### 3. Hierarchical Grouping
- **First grouping attribute creates outer enclosure** - all resources with the same value are grouped together regardless of type
- Subsequent attributes create sub-groups within the outer group
- Example: Resources with same `values.project` are grouped together, then sub-grouped by `values.region`

### 4. Visual Diagram Features
- **Icons**: Display custom icons on the left side of each resource
- **Resource Type**: Large bold text showing the resource type
- **Display Name**: Smaller text below showing the resource name
- **Nested Groups**: Visual boxes showing hierarchical relationships
- **Multiple Formats**: PNG, SVG, PDF output support

### 5. Terraform Plan Parser
- Parses Terraform plan JSON format
- Handles both `planned_values` and `resource_changes` sections
- Supports nested modules
- Extracts resource type, name, and all attributes

### 6. Icon System
- Supports PNG icons (48x48 recommended)
- Absolute and relative path support
- Placeholder icons when image not found
- Sample icons included for:
  - Google Compute Address
  - Google Compute Instance
  - AWS Instance
  - AWS S3 Bucket

### 7. GitHub Actions Pipelines

#### Release Pipeline (`.github/workflows/release.yml`)
Triggers on version tags (e.g., `v1.0.0`):
- Builds Python package (wheel)
- Creates standalone installer script
- Generates release notes
- Uploads to GitHub Releases
- Optional PyPI upload

#### Test Pipeline (`.github/workflows/test.yml`)
Runs on pull requests and pushes:
- Tests on Python 3.8-3.12
- Installs system dependencies
- Runs CLI tests
- Tests multiple output formats

### 8. Installation Methods

Users can install via:
1. **PyPI**: `pip install terravisualizer`
2. **GitHub Release Wheel**: Download and install `.whl` file
3. **One-line Installer**: `curl -sSL ... | python3 -`
4. **Standalone Script**: Download and run directly
5. **From Source**: Clone and `pip install -e .`

## Usage Examples

### Basic Usage
```bash
terravisualizer --file tfplan.json
```

### With Custom Config
```bash
terravisualizer --file tfplan.json --config my_config.hcl --output diagram.png
```

### Generate Terraform Plan JSON
```bash
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
terravisualizer --file tfplan.json
```

## Configuration Example

```hcl
"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "values.name"
}
```

## Project Structure

```
terravisualizer/
├── .github/workflows/
│   ├── release.yml          # Release automation
│   └── test.yml             # CI testing
├── terravisualizer/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Python -m entry point
│   ├── cli.py               # CLI interface
│   ├── config_parser.py     # Config file parser
│   ├── plan_parser.py       # Terraform plan parser
│   └── visualizer.py        # Diagram generator
├── examples/
│   ├── sample_tfplan.json   # Example plan
│   ├── sample_config.hcl    # Example HCL config
│   └── sample_config.json   # Example JSON config
├── icons/                   # Sample icons
├── setup.py                 # Package setup
├── requirements.txt         # Dependencies
├── create_release.sh        # Release helper script
└── README.md                # Documentation
```

## Security Considerations

✅ **Passed Security Checks:**
- No use of `eval()` or `exec()`
- No `shell=True` in subprocess calls
- No pickle deserialization
- No hardcoded secrets
- Dependencies checked for vulnerabilities
- Proper path resolution for file access
- HTML escaping in generated labels

## Dependencies

- **graphviz** (>= 0.20.0): Python wrapper for Graphviz
- **System**: Graphviz must be installed on the system

## Release Process

1. Update version in `terravisualizer/__init__.py`
2. Run `./create_release.sh v1.0.0`
3. GitHub Actions automatically:
   - Builds package
   - Creates release
   - Uploads artifacts
   - Publishes to PyPI (if configured)

## Testing

Included tests verify:
- CLI help functionality
- Diagram generation with sample data
- HCL and JSON config formats
- Multiple output formats (PNG, SVG)
- Cross-platform compatibility (Python 3.8-3.12)

## Future Enhancements (Not Implemented)

Potential future features:
- Resource dependencies/relationships visualization
- Interactive HTML output
- Custom color schemes
- More icon packs
- Terraform module visualization
- Resource count statistics
- Filter by resource type

## Documentation

Complete documentation available in:
- README.md - User guide and installation
- Configuration examples
- Sample data for testing
- Inline code documentation

## Summary

This implementation provides a complete, production-ready CLI tool for visualizing Terraform infrastructure with the following highlights:

1. ✅ Hierarchical grouping as requested
2. ✅ Icon support for resources
3. ✅ Formatted node display
4. ✅ Multiple configuration formats
5. ✅ Automated release pipeline
6. ✅ Multiple installation methods
7. ✅ Comprehensive documentation
8. ✅ Security validated
9. ✅ Cross-platform tested
10. ✅ Easy to use and extend
