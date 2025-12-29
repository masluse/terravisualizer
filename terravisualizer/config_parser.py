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
    
    # Find resource blocks - use a more careful approach
    # Pattern: "resource_type" { ... }
    # We need to handle nested braces properly
    
    resource_pattern = r'"([^"]+)"\s*\{'
    
    matches = list(re.finditer(resource_pattern, content))
    
    for i, match in enumerate(matches):
        resource_type = match.group(1)
        start_pos = match.end()
        
        # Find the matching closing brace
        brace_count = 1
        pos = start_pos
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                # Check if it's inside a string
                # Simple check: look back for quote
                in_string = False
                look_back = pos - 1
                quote_count = 0
                while look_back >= start_pos:
                    if content[look_back] == '"' and (look_back == 0 or content[look_back-1] != '\\'):
                        quote_count += 1
                    look_back -= 1
                if quote_count % 2 == 0:  # Even number of quotes means we're outside strings
                    brace_count += 1
            elif content[pos] == '}':
                # Check if it's inside a string
                in_string = False
                look_back = pos - 1
                quote_count = 0
                while look_back >= start_pos:
                    if content[look_back] == '"' and (look_back == 0 or content[look_back-1] != '\\'):
                        quote_count += 1
                    look_back -= 1
                if quote_count % 2 == 0:  # Even number of quotes means we're outside strings
                    brace_count -= 1
            pos += 1
        
        block_content = content[start_pos:pos-1]
        
        resource_config = {}
        
        # Parse key-value pairs line by line
        lines = block_content.strip().split('\n')
        j = 0
        while j < len(lines):
            line = lines[j].strip()
            
            # Skip empty lines
            if not line:
                j += 1
                continue
            
            # Match key = value pattern
            kv_match = re.match(r'"([^"]+)"\s*=\s*(.+)', line)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).strip()
                
                # Parse array values
                if value.startswith('['):
                    # Check if array is complete on this line
                    if not value.endswith(']'):
                        # Multi-line array (unlikely in our case, but handle it)
                        j += 1
                        while j < len(lines) and not value.endswith(']'):
                            value += ' ' + lines[j].strip()
                            j += 1
                    
                    # Extract array elements
                    array_content = value[1:-1]
                    # Split by comma, handling nested structures
                    elements = [elem.strip() for elem in array_content.split(',')]
                    resource_config[key] = elements
                else:
                    # Remove quotes from string values
                    value = value.strip('"\'')
                    resource_config[key] = value
            
            j += 1
        
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
