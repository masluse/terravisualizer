# Docker Usage Guide

This guide explains how to use Terravisualizer with Docker.

## Quick Start

The Docker image is available at `ghcr.io/masluse/terravisualizer` and includes all dependencies (Graphviz, fonts, etc.).

### Basic Usage

```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
```

This command:
- `--rm`: Removes the container after execution
- `-v $(pwd):/data`: Mounts your current directory to `/data` in the container
- `--file tfplan.json`: Specifies the Terraform plan file to visualize

**Note:** If your directory path contains spaces or special characters, quote the path: `-v "$(pwd)":/data`

## Usage Examples

### Generate a diagram from a Terraform plan

First, create your Terraform plan JSON:
```bash
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
```

Then visualize it:
```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
```

This creates `terraform_diagram.png` in your current directory.

### Use a custom configuration file

```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest \
  --file tfplan.json \
  --config my_config.hcl \
  --output my_diagram.png
```

### Generate SVG output

```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest \
  --file tfplan.json \
  --output diagram.svg \
  --format svg
```

### Generate PDF output

```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest \
  --file tfplan.json \
  --output diagram.pdf \
  --format pdf
```

## Available Tags

- `latest`: Latest stable release (recommended for most users)
- `v1.x.x`: Specific version tags (e.g., `v1.0.0`)
- `1.x`: Major.minor version tags (e.g., `1.0`)
- `1`: Major version tags (e.g., `1`)

Example using a specific version:
```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:v1.0.0 --file tfplan.json
```

## Platform Support

The Docker image is built for multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit)

Docker will automatically pull the correct image for your platform.

## Shell Alias (Optional)

For convenience, you can create a shell alias:

### Bash/Zsh
```bash
echo 'alias terravisualizer="docker run --rm -v \$(pwd):/data ghcr.io/masluse/terravisualizer:latest"' >> ~/.bashrc
source ~/.bashrc
```

Then use it like a native command:
```bash
terravisualizer --file tfplan.json
```

### PowerShell (Windows)
```powershell
function terravisualizer { docker run --rm -v ${PWD}:/data ghcr.io/masluse/terravisualizer:latest $args }
```

## Advanced Usage

### Using with custom icon directories

If you have custom icons in a separate directory:

```bash
docker run --rm \
  -v $(pwd):/data \
  -v $(pwd)/my-icons:/icons \
  ghcr.io/masluse/terravisualizer:latest \
  --file tfplan.json \
  --config config.hcl
```

Make sure your config file references icons with paths like `/icons/my-resource.png`.

### CI/CD Integration

#### GitHub Actions
```yaml
- name: Visualize Terraform Plan
  run: |
    terraform show -json tfplan.binary > tfplan.json
    docker run --rm -v ${{ github.workspace }}:/data \
      ghcr.io/masluse/terravisualizer:latest \
      --file tfplan.json \
      --output terraform-diagram.png
    
- name: Upload diagram
  uses: actions/upload-artifact@v3
  with:
    name: terraform-diagram
    path: terraform-diagram.png
```

#### GitLab CI
```yaml
visualize:
  image: docker:latest
  services:
    - docker:dind
  script:
    - terraform show -json tfplan.binary > tfplan.json
    - docker run --rm -v $PWD:/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
  artifacts:
    paths:
      - terraform_diagram.png
```

## Troubleshooting

### Permission Denied Errors

If you encounter permission issues with the output file, it's because the container runs as a non-root user. You can work around this by:

1. Making the output directory writable:
```bash
chmod 777 .
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
```

2. Or changing the ownership after generation:
```bash
docker run --rm -v $(pwd):/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
sudo chown $USER:$USER terraform_diagram.png
```

### File Not Found

Make sure your files are in the current directory or adjust the mount path:
```bash
# If your files are in a subdirectory
docker run --rm -v $(pwd)/terraform:/data ghcr.io/masluse/terravisualizer:latest --file tfplan.json
```

## Building Locally

If you want to build the Docker image locally:

```bash
git clone https://github.com/masluse/terravisualizer.git
cd terravisualizer
docker build -t terravisualizer:local .
docker run --rm -v $(pwd):/data terravisualizer:local --file tfplan.json
```

## Why Docker?

Using Docker has several advantages:
- **No dependencies**: Graphviz and all other dependencies are included
- **Consistent environment**: Works the same on any platform (Linux, macOS, Windows)
- **Easy updates**: Just pull the latest image
- **Clean system**: No need to install packages globally
- **CI/CD ready**: Easy to integrate into pipelines

## Support

For issues or questions:
- GitHub Issues: https://github.com/masluse/terravisualizer/issues
- Documentation: https://github.com/masluse/terravisualizer
