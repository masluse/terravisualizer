# Terravisualizer

A Python CLI tool to visualize Terraform plans with graphically grouped resources.

## Features

- Parse Terraform plan JSON files
- Group resources based on configurable attributes (project, region, zone, etc.)
- Generate visual diagrams showing resource relationships
- Support for custom resource configurations
- Multiple output formats (PNG, SVG, PDF)

## Installation

### From source

```bash
git clone https://github.com/masluse/terravisualizer.git
cd terravisualizer
pip install -e .
```

### Prerequisites

You need to have Graphviz installed on your system:

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz
```

**macOS:**
```bash
brew install graphviz
```

**Windows:**
Download and install from [graphviz.org](https://graphviz.org/download/)

## Usage

### Basic Usage

```bash
terravisualizer --file tfplan.json
```

### With Custom Configuration

```bash
terravisualizer --file tfplan.json --config my_config.hcl --output my_diagram.png
```

### Available Options

- `--file`: Path to the Terraform plan JSON file (required)
- `--config`: Path to the configuration file (default: `terravisualizer.hcl`)
- `--output`: Output file path (default: `terraform_diagram.png`)
- `--format`: Output format - `png`, `svg`, or `pdf` (default: `png`)

### Generating Terraform Plan JSON

First, generate a Terraform plan in JSON format:

```bash
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
```

Then use terravisualizer:

```bash
terravisualizer --file tfplan.json
```

## Configuration File Format

The configuration file defines how resources should be grouped and displayed. It supports an HCL-like format:

```hcl
"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagramm_image" = "../icons/google_compute_address"
    "name" = "values.name"
}

"aws_instance" {
    "grouped_by" = [values.availability_zone]
    "diagramm_image" = "../icons/aws_instance"
    "name" = "values.tags.Name"
}
```

### Configuration Options

- `grouped_by`: Array of attribute paths to group resources by (e.g., `values.project`, `values.region`)
- `diagramm_image`: Path to an icon for the resource (optional)
- `name`: Attribute path to use as the display name (default: `name`)

### Attribute Paths

Attribute paths use dot notation to access nested values:
- `values.project` - Access the `project` field from resource values
- `values.tags.Name` - Access nested `Name` field within `tags`
- `name` - Access the resource name itself

## Example

Given a Terraform plan with Google Cloud resources:

```bash
terravisualizer --file gcp-plan.json --config terravisualizer.hcl --output gcp-diagram.png
```

This will generate a diagram with resources grouped by project and region/zone.

## Development

### Running from source

```bash
python -m terravisualizer --file tfplan.json
```

### Project Structure

```
terravisualizer/
├── terravisualizer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # CLI entry point
│   ├── config_parser.py    # Configuration file parser
│   ├── plan_parser.py      # Terraform plan parser
│   └── visualizer.py       # Diagram generation
├── setup.py
├── requirements.txt
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.