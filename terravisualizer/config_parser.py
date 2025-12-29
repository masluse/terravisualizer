"""Configuration file parser for terravisualizer."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List


def parse_hcl_to_dict(content: str) -> Dict[str, Any]:
    """
    Parse a simplified HCL-like configuration format to a dictionary.
    
    This is a simplified parser that handles the specific format:
    {
        "resource_type" {
            "grouped_by" = [values.project, values.region]
            "diagram_image" = "path/to/icon"
            "name" = "value.name"
        }
    }
    """
    config = {}
    
    # Remove comments
    content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    
    # Find resource blocks
    # Pattern: "resource_type" { ... }
    block_pattern = r'"([^"]+)"\s*\{([^}]+)\}'
    
    for match in re.finditer(block_pattern, content):
        resource_type = match.group(1)
        block_content = match.group(2)
        
        resource_config = {}
        
        # Parse key-value pairs
        # Pattern for: "key" = value or "key" = [value1, value2]
        kv_pattern = r'"([^"]+)"\s*=\s*(.+?)(?=\n\s*"|$)'
        
        for kv_match in re.finditer(kv_pattern, block_content, re.DOTALL):
            key = kv_match.group(1)
            value = kv_match.group(2).strip()
            
            # Parse array values
            if value.startswith('[') and value.endswith(']'):
                # Extract array elements
                array_content = value[1:-1]
                # Split by comma, handling nested structures
                elements = [elem.strip() for elem in array_content.split(',')]
                resource_config[key] = elements
            else:
                # Remove quotes from string values
                value = value.strip('"\'')
                resource_config[key] = value
        
        config[resource_type] = resource_config
    
    return config


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and parse configuration file.
    
    Supports both HCL-like format and JSON format.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Parsed configuration dictionary
    """
    path = Path(config_path)
    
    with open(path, 'r') as f:
        content = f.read()
    
    # Try JSON first
    if path.suffix == '.json':
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    
    # Try HCL-like format
    return parse_hcl_to_dict(content)


def get_resource_config(config: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
    """
    Get configuration for a specific resource type.
    
    Args:
        config: The full configuration dictionary
        resource_type: The type of resource to get config for
        
    Returns:
        Configuration for the resource type, or empty dict if not found
    """
    return config.get(resource_type, {})
