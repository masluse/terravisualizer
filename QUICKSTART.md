# Terravisualizer Quick Start Guide

## Installation

```bash
# Install from PyPI (once released)
pip install terravisualizer

# OR download from GitHub releases
curl -sSL https://github.com/masluse/terravisualizer/releases/latest/download/terravisualizer-standalone | python3 - --file tfplan.json
```

## Usage

### 1. Generate Terraform Plan JSON

```bash
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
```

### 2. Create Configuration File

Save as `config.hcl`:

```hcl
"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "values.name"
}

"google_compute_instance" {
    "grouped_by" = [values.project, values.zone]
    "diagram_image" = "icons/google_compute_instance.png"
    "name" = "values.name"
}
```

Or as `config.json`:

```json
{
  "google_compute_address": {
    "grouped_by": ["values.project", "values.region"],
    "diagram_image": "icons/google_compute_address.png",
    "name": "values.name"
  }
}
```

### 3. Generate Diagram

```bash
terravisualizer --file tfplan.json --config config.hcl --output diagram.png
```

## Configuration Options

| Option | Description | Example |
|--------|-------------|---------|
| `--file` | Terraform plan JSON file (required) | `tfplan.json` |
| `--config` | Configuration file (default: `terravisualizer.hcl`) | `config.hcl` |
| `--output` | Output file (default: `terraform_diagram.png`) | `diagram.png` |
| `--format` | Output format (default: `png`) | `png`, `svg`, `pdf` |

## Configuration File Options

| Field | Description | Example |
|-------|-------------|---------|
| `grouped_by` | Array of attributes for grouping | `[values.project, values.region]` |
| `diagram_image` | Path to icon image (optional) | `icons/my_resource.png` |
| `name` | Attribute path for display name | `values.name` |

## Grouping Behavior

The **first attribute** in `grouped_by` creates the outer group that encloses all resources with the same value, regardless of their type.

Example:
```hcl
"google_compute_address" {
    "grouped_by" = [values.project, values.region]
}

"google_compute_instance" {
    "grouped_by" = [values.project, values.zone]
}
```

Result:
- Outer box: Groups by `values.project` (both resource types together if same project)
- Inner boxes: Sub-groups by `values.region` or `values.zone`

## Icon Support

- Icons are displayed on the left side of each resource
- Recommended size: 48x48 pixels PNG
- Paths can be relative or absolute
- Placeholder shown if icon not found

## Examples

### Basic Usage
```bash
terravisualizer --file tfplan.json
```

### Custom Output
```bash
terravisualizer --file tfplan.json --output my-infra.svg --format svg
```

### Different Config
```bash
terravisualizer --file tfplan.json --config aws-config.json
```

## Troubleshooting

### "Graphviz not found"
Install Graphviz:
```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz
```

### "Configuration file not found"
Make sure the config file path is correct:
```bash
terravisualizer --file tfplan.json --config ./my-config.hcl
```

### "No resources found"
Ensure your Terraform plan JSON is properly formatted:
```bash
terraform show -json tfplan.binary > tfplan.json
cat tfplan.json | jq '.planned_values.root_module.resources'
```

## Creating a Release (Maintainers)

```bash
./create_release.sh v1.0.0
```

This triggers GitHub Actions to:
1. Build the package
2. Create GitHub release
3. Upload artifacts
4. Publish to PyPI

## Support

- GitHub Issues: https://github.com/masluse/terravisualizer/issues
- Documentation: https://github.com/masluse/terravisualizer/blob/main/README.md
