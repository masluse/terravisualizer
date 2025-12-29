"""Terraform plan JSON parser."""

import json
from pathlib import Path
from typing import Any, Dict, List


class Resource:
    """Represents a Terraform resource."""
    
    def __init__(self, resource_type: str, name: str, values: Dict[str, Any]):
        """
        Initialize a resource.
        
        Args:
            resource_type: The type of resource (e.g., "google_compute_address")
            name: The resource name
            values: The resource values/attributes
        """
        self.resource_type = resource_type
        self.name = name
        self.values = values
    
    def get_value(self, path: str) -> Any:
        """
        Get a value from the resource using a path like 'values.project'.
        
        Args:
            path: Dot-separated path to the value
            
        Returns:
            The value at the path, or None if not found
        """
        parts = path.split('.')
        current = {'values': self.values, 'name': self.name}
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
                
        return current
    
    def __repr__(self):
        return f"Resource({self.resource_type}, {self.name})"


def parse_terraform_plan(plan_path: str) -> List[Resource]:
    """
    Parse a Terraform plan JSON file and extract resources.
    
    Args:
        plan_path: Path to the Terraform plan JSON file
        
    Returns:
        List of Resource objects
    """
    with open(plan_path, 'r') as f:
        plan_data = json.load(f)
    
    resources = []
    
    # Handle different Terraform plan formats
    # Standard format has resources in planned_values.root_module.resources
    if 'planned_values' in plan_data:
        resources.extend(_extract_from_module(
            plan_data['planned_values'].get('root_module', {})
        ))
    
    # Also check resource_changes for more complete information
    if 'resource_changes' in plan_data:
        for change in plan_data['resource_changes']:
            resource_type = change.get('type', '')
            name = change.get('name', '')
            
            # Get values from after (planned state)
            values = {}
            if 'change' in change and 'after' in change['change']:
                values = change['change']['after'] or {}
            
            # Avoid duplicates
            if not any(r.resource_type == resource_type and r.name == name for r in resources):
                resources.append(Resource(resource_type, name, values))
    
    return resources


def _extract_from_module(module: Dict[str, Any]) -> List[Resource]:
    """
    Extract resources from a module (recursive for nested modules).
    
    Args:
        module: Module data from Terraform plan
        
    Returns:
        List of Resource objects
    """
    resources = []
    
    # Extract resources from current module
    if 'resources' in module:
        for resource_data in module['resources']:
            resource_type = resource_data.get('type', '')
            name = resource_data.get('name', '')
            values = resource_data.get('values', {})
            
            resources.append(Resource(resource_type, name, values))
    
    # Recursively extract from child modules
    if 'child_modules' in module:
        for child_module in module['child_modules']:
            resources.extend(_extract_from_module(child_module))
    
    return resources
