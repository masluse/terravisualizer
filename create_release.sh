#!/bin/bash
# Script to create a new release
# Usage: ./create_release.sh v1.0.0

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

# Check if version starts with 'v'
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format vX.Y.Z (e.g., v1.0.0)"
    exit 1
fi

echo "Creating release $VERSION..."

# Update version in __init__.py
VERSION_NUMBER="${VERSION#v}"  # Remove 'v' prefix
sed -i "s/__version__ = .*/__version__ = \"$VERSION_NUMBER\"/" terravisualizer/__init__.py

# Commit version bump
git add terravisualizer/__init__.py
git commit -m "Bump version to $VERSION"

# Create and push tag
git tag -a "$VERSION" -m "Release $VERSION"
git push origin main
git push origin "$VERSION"

echo "Release $VERSION created and pushed!"
echo "GitHub Actions will now build and publish the release."
echo "Check the Actions tab: https://github.com/masluse/terravisualizer/actions"
