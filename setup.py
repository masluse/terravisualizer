"""Setup configuration for terravisualizer."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="terravisualizer",
    version="0.1.0",
    author="masluse",
    description="A tool to visualize Terraform plan with grouped resources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/masluse/terravisualizer",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "graphviz>=0.20.0",
    ],
    entry_points={
        "console_scripts": [
            "terravisualizer=terravisualizer.cli:main",
        ],
    },
)
