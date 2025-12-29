# Terravisualizer

A Python CLI tool to visualize Terraform plans with graphically grouped resources.

## Features

- Parse Terraform plan JSON files
- Group resources based on configurable attributes (project, region, zone, etc.)
- Generate visual diagrams showing resource relationships
- Support for custom resource configurations
- Multiple output formats (PNG, SVG, PDF)

## Installation

### Method 1: Install from PyPI (recommended)

```bash
pip install terravisualizer
```

### Method 2: Install from GitHub releases

Download and install the latest release:

```bash
# Download the wheel file from the latest release
curl -sSL -o terravisualizer.whl https://github.com/masluse/terravisualizer/releases/latest/download/terravisualizer-*-py3-none-any.whl
pip install terravisualizer.whl
```

### Method 3: One-line installer

Run terravisualizer directly without manual installation:

```bash
curl -sSL https://github.com/masluse/terravisualizer/releases/latest/download/terravisualizer-standalone | python3 - --file tfplan.json --config config.hcl
```

Or download and run locally:

```bash
curl -sSL -o terravisualizer-standalone https://github.com/masluse/terravisualizer/releases/latest/download/terravisualizer-standalone
chmod +x terravisualizer-standalone
./terravisualizer-standalone --file tfplan.json --config config.hcl
```

### Method 4: Install from source

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

The configuration file defines how resources should be grouped and displayed. It supports both HCL-like and JSON formats:

**HCL format:**
```hcl
"google_compute_address" {
    "grouped_by" = [values.project, values.region]
    "diagram_image" = "icons/google_compute_address.png"
    "name" = "values.name"
}

"aws_instance" {
    "grouped_by" = [values.availability_zone]
    "diagram_image" = "icons/aws_instance.png"
    "name" = "values.tags.Name"
}
```

**JSON format:**
```json
{
  "google_compute_address": {
    "grouped_by": ["values.project", "values.region"],
    "diagram_image": "icons/google_compute_address.png",
    "name": "values.name"
  },
  "aws_instance": {
    "grouped_by": ["values.availability_zone"],
    "diagram_image": "icons/aws_instance.png",
    "name": "values.tags.Name"
  }
}
```

### Configuration Options

- `grouped_by`: Array of attribute paths to group resources by (e.g., `values.project`, `values.region`)
  - **The first attribute creates the outer group** - resources with the same value will be enclosed together regardless of type
  - Subsequent attributes create sub-groups within the outer group
- `diagram_image`: Path to an icon image for the resource (optional, PNG format recommended)
  - Icons are displayed on the left side of each resource in the diagram
  - Paths can be relative or absolute
  - If the icon file doesn't exist, a placeholder icon is shown
- `name`: Attribute path to use as the display name (default: `name`)
  - Displayed below the resource type in smaller text

### Resource Display Format

Each resource in the diagram is displayed with:
1. **Icon** (left side): Optional image specified in `diagram_image`
2. **Resource Type** (large bold text): e.g., "google_compute_address"
3. **Display Name** (smaller text below): The value from the `name` field

### Attribute Paths

Attribute paths use dot notation to access nested values:
- `values.project` - Access the `project` field from resource values
- `values.tags.Name` - Access nested `Name` field within `tags`
- `name` - Access the resource name itself

### Creating Custom Icons

Icons can be any PNG image file. Recommended size is 48x48 pixels. You can:
- Use provider-specific icons (AWS, GCP, Azure logos)
- Create custom icons with tools like Inkscape, GIMP, or Python (PIL/Pillow)
- Download icon packs from icon libraries

Example icon directory structure:
```
icons/
├── google_compute_address.png
├── google_compute_instance.png
├── aws_instance.png
└── aws_s3_bucket.png
```

## Example

Given a Terraform plan with Google Cloud resources:

```bash
terravisualizer --file gcp-plan.json --config terravisualizer.hcl --output gcp-diagram.png
```

This will generate a diagram with:
- Resources grouped hierarchically by project (outer group) and region/zone (inner groups)
- Each resource showing its icon, type, and display name
- Visual organization making it easy to understand your infrastructure layout

## Development

### Running from source

```bash
python -m terravisualizer --file tfplan.json
```

### Creating a Release

To create a new release:

1. Make sure all changes are committed
2. Run the release script:
   ```bash
   ./create_release.sh v1.0.0
   ```
3. The GitHub Actions workflow will automatically:
   - Build the Python package
   - Create a GitHub release with downloadable artifacts
   - Upload to PyPI (if configured)

The release will include:
- Python wheel files (`.whl`)
- Standalone installer script
- Release notes

Users can then install using any of the methods described in the Installation section.

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