#!/bin/bash
# Script to test Docker image locally
# Usage: ./test-docker.sh

set -e

echo "===== Testing Terravisualizer Docker Image ====="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

echo "1. Building Docker image..."
docker build -t terravisualizer:test .

echo ""
echo "2. Testing help command..."
docker run --rm terravisualizer:test --help

echo ""
echo "3. Testing with sample files..."
if [ ! -d examples ]; then
    echo "Error: examples directory not found"
    exit 1
fi

if [ ! -f examples/sample_tfplan.json ]; then
    echo "Error: examples/sample_tfplan.json not found"
    exit 1
fi

if [ ! -f examples/sample_config.hcl ]; then
    echo "Error: examples/sample_config.hcl not found"
    exit 1
fi

(
    cd examples
    docker run --rm -v "$(pwd)":/data terravisualizer:test \
      --file sample_tfplan.json \
      --config sample_config.hcl \
      --output test_diagram.png
    
    if [ -f test_diagram.png ]; then
        echo "✓ Diagram generated successfully: test_diagram.png"
        ls -lh test_diagram.png
        rm test_diagram.png
    else
        echo "✗ Failed to generate diagram"
        exit 1
    fi
)

echo ""
echo "===== All tests passed! ====="
