"""Diagram generator for Terraform resources."""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set

from graphviz import Digraph

from terravisualizer.config_parser import get_resource_config
from terravisualizer.plan_parser import Resource


def extract_grouping_hierarchy(
    resources: List[Resource],
    config: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Extract the grouping hierarchy from all resource configurations.
    
    Args:
        resources: List of resources
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping resource types to their grouping fields
    """
    hierarchy = {}
    
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        if resource_config and 'grouped_by' in resource_config:
            grouped_by = resource_config['grouped_by']
            if grouped_by and resource.resource_type not in hierarchy:
                hierarchy[resource.resource_type] = grouped_by
    
    return hierarchy


def build_group_key(resource: Resource, grouping_fields: List[str]) -> Tuple[str, ...]:
    """
    Build a group key for a resource based on grouping fields.
    
    Args:
        resource: The resource
        grouping_fields: List of fields to group by
        
    Returns:
        Tuple of group values
    """
    key_parts = []
    for field in grouping_fields:
        value = resource.get_value(field)
        if value is not None:
            key_parts.append(str(value))
        else:
            key_parts.append('unknown')
    return tuple(key_parts)


def group_resources_hierarchically(
    resources: List[Resource], 
    config: Dict[str, Any]
) -> Dict[Tuple[str, ...], Dict[str, List[Resource]]]:
    """
    Group resources hierarchically based on configuration.
    The first grouping field creates the outer group, subsequent fields create sub-groups.
    
    Args:
        resources: List of resources to group
        config: Configuration dictionary
        
    Returns:
        Nested dictionary: outer_group_key -> resource_type -> [resources]
    """
    # Extract grouping hierarchy
    hierarchy = extract_grouping_hierarchy(resources, config)
    
    # Find common grouping prefix across all configured resource types
    # The first group in grouped_by should enclose resources with the same value
    outer_groups = {}  # Maps outer_group_key -> {resource_type -> [resources]}
    
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        
        if not resource_config or 'grouped_by' not in resource_config:
            # No config for this resource type, put in default group
            outer_key = ('ungrouped',)
            if outer_key not in outer_groups:
                outer_groups[outer_key] = {}
            if resource.resource_type not in outer_groups[outer_key]:
                outer_groups[outer_key][resource.resource_type] = []
            outer_groups[outer_key][resource.resource_type].append(resource)
            continue
        
        grouped_by = resource_config['grouped_by']
        
        if not grouped_by:
            # No grouping specified
            outer_key = ('default',)
            if outer_key not in outer_groups:
                outer_groups[outer_key] = {}
            if resource.resource_type not in outer_groups[outer_key]:
                outer_groups[outer_key][resource.resource_type] = []
            outer_groups[outer_key][resource.resource_type].append(resource)
        else:
            # Use only the first grouping field for the outer group
            first_field = grouped_by[0]
            first_value = resource.get_value(first_field)
            outer_key = (str(first_value) if first_value is not None else 'unknown',)
            
            # Build sub-group key from remaining fields
            if len(grouped_by) > 1:
                sub_key_parts = [resource.resource_type]
                for field in grouped_by[1:]:
                    value = resource.get_value(field)
                    sub_key_parts.append(str(value) if value is not None else 'unknown')
                sub_key = tuple(sub_key_parts)
            else:
                sub_key = (resource.resource_type,)
            
            # Initialize nested structure
            if outer_key not in outer_groups:
                outer_groups[outer_key] = {}
            if sub_key not in outer_groups[outer_key]:
                outer_groups[outer_key][sub_key] = []
            
            outer_groups[outer_key][sub_key].append(resource)
    
    return outer_groups


def get_display_name(resource: Resource, resource_config: Dict[str, Any]) -> str:
    """
    Get the display name for a resource based on configuration.
    
    Args:
        resource: The resource
        resource_config: Configuration for this resource type
        
    Returns:
        Display name string
    """
    name_field = resource_config.get('name', 'name')
    
    # Try to get the configured name field
    display_name = resource.get_value(name_field)
    
    if display_name:
        return str(display_name)
    
    # Fallback to resource name
    return resource.name


def generate_diagram(
    resources: List[Resource],
    config: Dict[str, Any],
    output_path: str,
    output_format: str = 'png'
) -> str:
    """
    Generate a visual diagram of resources.
    
    Args:
        resources: List of resources to visualize
        config: Configuration dictionary
        output_path: Path for the output file
        output_format: Output format (png, svg, pdf)
        
    Returns:
        Path to the generated diagram
    """
    # Group resources hierarchically
    grouped = group_resources_hierarchically(resources, config)
    
    # Create directed graph
    dot = Digraph(comment='Terraform Resources')
    dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='0.8')
    dot.attr('node', shape='plaintext')  # Use plaintext for HTML-like labels
    
    # Track node IDs
    node_counter = 0
    node_ids = {}
    
    # Create outer clusters for each top-level group
    for outer_key, sub_groups in sorted(grouped.items()):
        outer_cluster_name = f'cluster_outer_{abs(hash(outer_key))}'
        
        with dot.subgraph(name=outer_cluster_name) as outer_cluster:
            # Set outer cluster label
            outer_label = _format_outer_group_label(outer_key)
            outer_cluster.attr(label=outer_label, fontsize='16', fontname='bold')
            outer_cluster.attr(style='filled,rounded', color='blue', fillcolor='#e6f2ff')
            
            # Create sub-clusters within the outer cluster
            for sub_key, resources_in_group in sorted(sub_groups.items()):
                sub_cluster_name = f'cluster_sub_{abs(hash((outer_key, sub_key)))}'
                
                with outer_cluster.subgraph(name=sub_cluster_name) as sub_cluster:
                    sub_label = _format_sub_group_label(sub_key)
                    sub_cluster.attr(label=sub_label, fontsize='12')
                    sub_cluster.attr(style='filled,rounded', color='darkgrey', fillcolor='white')
                    
                    # Add resources to the sub-cluster
                    for resource in resources_in_group:
                        node_id = f'node_{node_counter}'
                        node_counter += 1
                        node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                        
                        resource_config = get_resource_config(config, resource.resource_type)
                        display_name = get_display_name(resource, resource_config)
                        icon_path = resource_config.get('diagram_image', '')
                        
                        # Create HTML-like label with icon and formatted text
                        label = _create_node_label(resource.resource_type, display_name, icon_path)
                        sub_cluster.node(node_id, label=label)
    
    # Remove extension from output_path if present
    output_base = str(Path(output_path).with_suffix(''))
    
    # Render the diagram
    dot.render(output_base, format=output_format, cleanup=True)
    
    return f'{output_base}.{output_format}'


def _create_node_label(resource_type: str, display_name: str, icon_path: str = '') -> str:
    """
    Create an HTML-like label for a node with optional icon, resource type, and name.
    
    Args:
        resource_type: The resource type (shown as big name)
        display_name: The display name (shown as small name)
        icon_path: Path to the icon image (optional)
        
    Returns:
        HTML-like label string for Graphviz
    """
    # Escape special characters in text for HTML
    resource_type_escaped = resource_type.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    display_name_escaped = display_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Check if icon exists and convert to absolute path
    icon_cell = ''
    if icon_path:
        # Convert to absolute path
        icon_abs_path = Path(icon_path).resolve()
        
        if icon_abs_path.exists():
            # Icon with fixed size - use absolute path
            icon_cell = f'<TD WIDTH="48" HEIGHT="48" FIXEDSIZE="TRUE"><IMG SRC="{icon_abs_path}"/></TD>'
        else:
            # If icon path is specified but doesn't exist, show a placeholder
            # Use a simple emoji or text as fallback
            icon_cell = '<TD WIDTH="48" HEIGHT="48" FIXEDSIZE="TRUE" BGCOLOR="#e0e0e0" BORDER="0">📦</TD>'
    
    # Build HTML table
    if icon_cell:
        label = f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6" BGCOLOR="lightblue">
  <TR>
    {icon_cell}
    <TD ALIGN="LEFT" BALIGN="LEFT">
      <FONT POINT-SIZE="13"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#555555">{display_name_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''
    else:
        # No icon, simpler layout
        label = f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8" BGCOLOR="lightblue">
  <TR>
    <TD ALIGN="LEFT" BALIGN="LEFT">
      <FONT POINT-SIZE="13"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#555555">{display_name_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''
    
    return label


def _format_outer_group_label(group_key: Tuple[str, ...]) -> str:
    """
    Format an outer group key into a readable label.
    
    Args:
        group_key: Tuple representing the outer group
        
    Returns:
        Formatted label string
    """
    if not group_key:
        return 'Resources'
    
    if group_key == ('ungrouped',):
        return 'Ungrouped Resources'
    
    if group_key == ('default',):
        return 'Default Group'
    
    # For outer groups, just show the value
    return ' | '.join(group_key)


def _format_sub_group_label(sub_key: Tuple[str, ...]) -> str:
    """
    Format a sub-group key into a readable label.
    
    Args:
        sub_key: Tuple representing the sub-group
        
    Returns:
        Formatted label string
    """
    if not sub_key:
        return 'Resources'
    
    # First element is usually the resource type
    parts = list(sub_key)
    
    if len(parts) == 1:
        return parts[0]
    
    # Format as "Type: value1, value2"
    resource_type = parts[0]
    values = parts[1:]
    
    if all(v == 'unknown' for v in values):
        return resource_type
    
    return f"{resource_type}\\n{' | '.join(values)}"

