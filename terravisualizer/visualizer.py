"""Diagram generator for Terraform resources."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

from graphviz import Digraph

from terravisualizer.config_parser import get_resource_config
from terravisualizer.plan_parser import Resource

# Constants for gray color calculation
GRAY_BASE_VALUE = 245  # Starting point (very light gray, #f5f5f5)
GRAY_REDUCTION_PER_LEVEL = 10  # How much darker per nesting level
GRAY_MIN_VALUE = 200  # Minimum gray value to prevent too dark colors (#c8c8c8)

# Constants for node box sizing
ICON_CELL_WIDTH = 64  # Width of icon cell in pixels
MIN_TEXT_CELL_WIDTH = 200  # Minimum width of text cell for uniform box sizes


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
    All values are normalized to lowercase for case-insensitive grouping.
    
    Args:
        resource: The resource
        grouping_fields: List of fields to group by
        
    Returns:
        Tuple of group values (normalized to lowercase)
    """
    key_parts = []
    for field in grouping_fields:
        value = resource.get_value(field)
        if value is not None:
            # Normalize to lowercase for case-insensitive grouping
            key_parts.append(str(value).lower())
        else:
            key_parts.append('unknown')
    return tuple(key_parts)


def group_resources_hierarchically(
    resources: List[Resource], 
    config: Dict[str, Any]
) -> Tuple[Dict[Tuple[str, ...], Dict[str, List[Resource]]], Dict[str, List[Resource]]]:
    """
    Group resources hierarchically based on configuration.
    
    Supports two grouping strategies:
    1. group_id: Creates parent-child relationships (e.g., node_pool inside cluster)
    2. grouped_by: Groups resources by attribute values (case-insensitive)
    
    When both group_id and grouped_by are defined:
    - First apply group_id to create parent-child relationships
    - Then apply grouped_by within those parent groups
    
    Args:
        resources: List of resources to group
        config: Configuration dictionary
        
    Returns:
        Tuple of:
        - Nested dictionary: outer_group_key -> sub_key -> [resources]
        - Dictionary mapping parent resource keys to their children
    """
    # Extract grouping hierarchy
    hierarchy = extract_grouping_hierarchy(resources, config)
    
    # First pass: identify resources that can be parents (have 'id' defined)
    parent_resources = {}  # Maps (resource_type, id_value) -> resource
    parent_map = {}  # Maps parent resource key -> resource object
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        if resource_config and 'id' in resource_config:
            id_field = resource_config['id']
            id_value = resource.get_value(id_field)
            if id_value:
                parent_resources[(resource.resource_type, str(id_value))] = resource
                parent_key = f"{resource.resource_type}.{resource.name}"
                parent_map[parent_key] = resource
    
    # Second pass: identify parent-child relationships
    resource_to_parent = {}  # Maps child resource -> parent resource
    parent_to_children = {}  # Maps parent resource key -> list of children
    
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        
        # Check if this resource has a parent (group_id)
        if resource_config and 'group_id' in resource_config:
            group_id_field = resource_config['group_id']
            parent_id = resource.get_value(group_id_field)
            
            if parent_id:
                # Find parent resource - normalize parent_id for comparison
                parent_id_lower = str(parent_id).lower()
                for (parent_type, parent_id_val), potential_parent in parent_resources.items():
                    # Skip if the potential parent is of the same type as the child
                    # (resources shouldn't be nested inside resources of the same type)
                    if parent_type == resource.resource_type:
                        continue
                    if parent_id_lower == parent_id_val.lower():
                        resource_to_parent[resource] = potential_parent
                        parent_key = f"{potential_parent.resource_type}.{potential_parent.name}"
                        if parent_key not in parent_to_children:
                            parent_to_children[parent_key] = []
                        parent_to_children[parent_key].append(resource)
                        break
    
    # Third pass: build groups, excluding children (they'll be rendered inside parents)
    outer_groups = {}  # Maps outer_group_key -> {sub_key -> [resources]}
    
    for resource in resources:
        # Skip resources that are children (they'll be rendered with their parent)
        if resource in resource_to_parent:
            continue
            
        resource_config = get_resource_config(config, resource.resource_type)
        
        # Determine the outer group key based on grouped_by
        if not resource_config or 'grouped_by' not in resource_config:
            # No config for this resource type, put in default group
            outer_key = ('ungrouped',)
        else:
            # Use grouped_by
            grouped_by = resource_config['grouped_by']
            
            if not grouped_by:
                outer_key = ('default',)
            else:
                # Use only the first grouping field for the outer group (lowercase)
                first_field = grouped_by[0]
                first_value = resource.get_value(first_field)
                outer_key = (str(first_value).lower() if first_value is not None else 'unknown',)
        
        # Build sub-group key
        if not resource_config or 'grouped_by' not in resource_config:
            sub_key = (resource.resource_type,)
        else:
            grouped_by = resource_config['grouped_by']
            
            if not grouped_by:
                sub_key = (resource.resource_type,)
            elif len(grouped_by) > 1:
                # Use remaining grouping values for sub-grouping
                # (first value was already used for outer group)
                sub_key_parts = []
                for field in grouped_by[1:]:
                    value = resource.get_value(field)
                    # Normalize to lowercase
                    sub_key_parts.append(str(value).lower() if value is not None else 'unknown')
                sub_key = tuple(sub_key_parts)
            else:
                # Only one grouping field, no sub-group needed
                sub_key = ('resources',)
        
        # Initialize nested structure
        if outer_key not in outer_groups:
            outer_groups[outer_key] = {}
        if sub_key not in outer_groups[outer_key]:
            outer_groups[outer_key][sub_key] = []
        
        outer_groups[outer_key][sub_key].append(resource)
    
    return outer_groups, parent_to_children


def get_display_name(resource: Resource, resource_config: Dict[str, Any]) -> str:
    """
    Get the display name for a resource based on configuration.
    Supports template syntax like "${values.member}-${values.role}".
    
    Args:
        resource: The resource
        resource_config: Configuration for this resource type
        
    Returns:
        Display name string
    """
    name_template = resource_config.get('name', 'name')
    
    # Check if it's a template with ${} syntax
    if '${' in name_template and '}' in name_template:
        # Extract all ${...} patterns
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, name_template)
        
        result = name_template
        for match in matches:
            field_path = match.strip()
            value = resource.get_value(field_path)
            
            # Replace ${field} with the actual value (or empty string if not found)
            replacement = str(value) if value is not None else ''
            result = result.replace(f'${{{match}}}', replacement)
        
        # Clean up any double separators (e.g., "--" or " - ")
        result = re.sub(r'-{2,}', '-', result)
        result = re.sub(r'^-|-$', '', result)  # Remove leading/trailing dashes
        
        return result.strip() if result.strip() else resource.name
    else:
        # Legacy support: treat as direct field path
        display_name = resource.get_value(name_template)
        
        if display_name:
            return str(display_name)
        
        # Fallback to resource name
        return resource.name


def calculate_max_widths_per_type(
    resources: List[Resource],
    config: Dict[str, Any]
) -> Dict[str, int]:
    """
    Calculate the maximum text width needed for each resource type.
    This ensures all instances of a resource type have uniform box sizes.
    
    Args:
        resources: List of all resources
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping resource_type to max width in pixels
    """
    type_widths = {}
    
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        display_name = get_display_name(resource, resource_config)
        
        # Estimate width: rough approximation based on character count
        # Assume average character width of ~8px for 16pt bold font
        display_name_width = len(display_name) * 8
        resource_type_width = len(resource.resource_type) * 6  # Smaller font
        
        # Take the max of the two text elements
        estimated_width = max(display_name_width, resource_type_width)
        
        # Track maximum for this resource type
        if resource.resource_type not in type_widths:
            type_widths[resource.resource_type] = estimated_width
        else:
            type_widths[resource.resource_type] = max(
                type_widths[resource.resource_type],
                estimated_width
            )
    
    # Ensure minimum width and add padding
    for resource_type in type_widths:
        type_widths[resource_type] = max(MIN_TEXT_CELL_WIDTH, type_widths[resource_type] + 20)
    
    return type_widths


def generate_diagram(
    resources: List[Resource],
    config: Dict[str, Any],
    output_path: str,
    output_format: str = 'png',
    title: Optional[str] = None
) -> str:
    """
    Generate a visual diagram of resources.
    
    Args:
        resources: List of resources to visualize
        config: Configuration dictionary
        output_path: Path for the output file
        output_format: Output format (png, svg, pdf)
        title: Optional title for the diagram. If not provided, generates a run number based on timestamp.
        
    Returns:
        Path to the generated diagram
    """
    # Calculate max widths per resource type for uniform box sizes
    max_widths_per_type = calculate_max_widths_per_type(resources, config)
    
    # Group resources hierarchically
    grouped, parent_to_children = group_resources_hierarchically(resources, config)
    
    # Generate title and timestamp (use single datetime call)
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    if not title:
        # Generate a run number based on timestamp (unique identifier)
        run_number = now.strftime('%Y%m%d%H%M%S')
        title = f"Run #{run_number}"
    
    # Create directed graph with modern layout settings
    dot = Digraph(comment='Terraform Resources', engine='dot')
    
    # Layout - Top to Bottom with improved spacing
    dot.attr(rankdir='TB')  # Top to Bottom for better visual hierarchy
    dot.attr(splines='ortho')  # Orthogonal splines for cleaner look
    dot.attr(compound='true')
    dot.attr(concentrate='false')
    dot.attr(newrank='true')
    dot.attr(nodesep='0.4')   # Horizontal spacing between nodes
    dot.attr(ranksep='0.3')   # Vertical spacing between ranks (reduced for tighter stacking)
    dot.attr(pad='0.3')       # Reduced padding around the graph (space to image border)
    dot.attr(margin='0.2')    # Reduced margin (space between graph edge and content)
    dot.attr(dpi='300')       # Much higher DPI for crisp, professional output
    
    # Light background for outer container with title header
    dot.attr(bgcolor='#f5f5f5')  # Light gray background
    dot.attr(fontname='Inter,SF Pro Display,Helvetica Neue,Arial,sans-serif')
    dot.attr(fontsize='13')
    
    # Title at top-left, timestamp at top-right
    # GraphViz only supports one graph label, so we combine them in a table
    # Using labeljust='l' positions the table at the left, but we make the table wide enough
    # to span across and right-align the timestamp within it
    header_label = f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" WIDTH="1500">
  <TR>
    <TD ALIGN="LEFT" WIDTH="300"><B><FONT POINT-SIZE="24" COLOR="#1f2937">{title}</FONT></B></TD>
    <TD ALIGN="RIGHT" WIDTH="1200"><FONT POINT-SIZE="14" COLOR="#6b7280">{timestamp}</FONT></TD>
  </TR>
</TABLE>>'''
    dot.attr(label=header_label, labelloc='t', labeljust='l')
    
    # Modern node defaults with shadow effect
    dot.attr('node', shape='plaintext', fontname='Inter,SF Pro Display,Helvetica Neue,Arial,sans-serif')
    
    # Modern edge styling - thinner, more subtle
    dot.attr('edge', color='#8b92a8', penwidth='2.0', arrowsize='0.9')
    
    # Track node IDs
    node_counter = 0
    node_ids = {}
    
    # Sort groups: ungrouped first, then alphabetically
    def sort_key(item):
        key, _ = item
        if key == ('ungrouped',):
            return (0, '')  # Put ungrouped first
        return (1, str(key))  # Then sort alphabetically
    
    sorted_groups = sorted(grouped.items(), key=sort_key)
    
    # Create the main diagram container
    # Note: Graphviz doesn't support true dotted/textured backgrounds natively
    # Using a subtle light gray fill to provide visual distinction
    with dot.subgraph(name='cluster_diagram_container') as container:
        container.attr(label='', labeljust='l', labelloc='t')
        # Solid border with subtle gray fill for the container background
        container.attr(style='filled,rounded', fillcolor='#e9e9e9', color='#cccccc', penwidth='2.0')
        container.attr(margin='50')  # Padding inside the container
        
        # Nesting depth for gray transparency calculation
        depth = 0
        
        # Create outer clusters for each top-level group
        for outer_key, sub_groups in sorted_groups:
            outer_cluster_name = f'cluster_outer_{abs(hash(outer_key))}'
            
            with container.subgraph(name=outer_cluster_name) as outer_cluster:
                # Set outer cluster label with modern styling (left-aligned)
                outer_label = _format_outer_group_label(outer_key)
                # Use DejaVu Sans Bold which is definitely available on Linux
                outer_cluster.attr(label=outer_label, fontsize='22', fontname='DejaVu Sans Bold', labeljust='l')
                # Gray styling with slight transparency (level 1: ~10% gray)
                gray_level_outer = _get_gray_color(depth=1)
                outer_cluster.attr(style='filled,rounded', color='#a0a0a0', fillcolor=gray_level_outer, penwidth='2.0')
                outer_cluster.attr(margin='40')  # Margin for better spacing
                
                # Check if we need sub-clusters or can place resources directly
                has_only_resources_key = len(sub_groups) == 1 and ('resources',) in sub_groups
                
                # Check if 'resources' sub-group exists and should be merged into outer cluster
                resources_subgroup = sub_groups.get(('resources',), [])
                other_subgroups = {k: v for k, v in sub_groups.items() if k != ('resources',)}
                
                # If we only have a 'resources' group, place directly in outer cluster
                if has_only_resources_key:
                    needs_sub_clusters = False
                else:
                    needs_sub_clusters = len(other_subgroups) > 0
                
                if not needs_sub_clusters and len(sub_groups) == 1:
                    # Place resources directly in the outer cluster
                    sub_key, resources_in_group = list(sub_groups.items())[0]
                    sub_node_ids: List[str] = []
                    sub_node_types: Dict[str, str] = {}  # Track node types for layout
                    
                    for resource in resources_in_group:
                        parent_key = f"{resource.resource_type}.{resource.name}"
                        
                        # Check if this resource has children
                        if parent_key in parent_to_children:
                            # Create a sub-cluster for this parent and its children
                            parent_cluster_name = f'cluster_parent_{abs(hash(parent_key))}'
                            
                            with outer_cluster.subgraph(name=parent_cluster_name) as parent_cluster:
                                # Get parent display info
                                resource_config = get_resource_config(config, resource.resource_type)
                                display_name = get_display_name(resource, resource_config)
                                
                                # Apply consistent parent cluster styling (gray, level 2)
                                _apply_parent_cluster_style(parent_cluster, display_name, depth=2)
                                
                                # Group children by grouped_by if configured
                                children = parent_to_children[parent_key]
                                grouped_children = _group_children_by_config(children, config)
                                
                                # Render children (potentially grouped)
                                child_node_ids: List[str] = []
                                child_node_types: Dict[str, str] = {}
                                node_counter = _render_grouped_children(
                                    parent_cluster, grouped_children, config, 
                                    node_ids, child_node_ids, node_counter, 
                                    max_widths_per_type, depth=3,
                                    node_types=child_node_types
                                )
                                
                                # Layout children by type (same type vertical, different types horizontal)
                                if child_node_ids:
                                    _layout_nodes_by_type(parent_cluster, child_node_ids, child_node_types)
                        else:
                            # Regular node without children
                            node_id = f'node_{node_counter}'
                            node_counter += 1
                            node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                            sub_node_ids.append(node_id)
                            sub_node_types[node_id] = resource.resource_type  # Track type
                            
                            resource_config = get_resource_config(config, resource.resource_type)
                            display_name = get_display_name(resource, resource_config)
                            icon_path = resource_config.get('diagram_image', '')
                            
                            text_width = max_widths_per_type.get(resource.resource_type)
                            label = _create_node_label(resource.resource_type, display_name, icon_path, text_width)
                            outer_cluster.node(node_id, label=label)
                    
                    # Layout nodes by type (same type vertical, different types horizontal)
                    if sub_node_ids:
                        _layout_nodes_by_type(outer_cluster, sub_node_ids, sub_node_types)
                else:
                    # Create sub-clusters within the outer cluster
                    resources_subgroup = sub_groups.get(('resources',), [])
                    other_subgroups = {k: v for k, v in sub_groups.items() if k != ('resources',)}
                    
                    # Track anchor nodes from sub-clusters for grid layout
                    sub_cluster_anchor_nodes: List[str] = []
                    
                    # Process 'resources' subgroup - place parent resources directly in outer cluster
                    direct_node_ids: List[str] = []
                    direct_node_types: Dict[str, str] = {}  # Track node types
                    for resource in resources_subgroup:
                        parent_key = f"{resource.resource_type}.{resource.name}"
                        
                        if parent_key in parent_to_children:
                            # Create parent cluster directly in outer cluster
                            parent_cluster_name = f'cluster_parent_{abs(hash(parent_key))}'
                            
                            with outer_cluster.subgraph(name=parent_cluster_name) as parent_cluster:
                                resource_config = get_resource_config(config, resource.resource_type)
                                display_name = get_display_name(resource, resource_config)
                                _apply_parent_cluster_style(parent_cluster, display_name, depth=2)
                                
                                # Group children by grouped_by if configured
                                children = parent_to_children[parent_key]
                                grouped_children = _group_children_by_config(children, config)
                                
                                child_node_ids: List[str] = []
                                child_node_types: Dict[str, str] = {}
                                node_counter = _render_grouped_children(
                                    parent_cluster, grouped_children, config,
                                    node_ids, child_node_ids, node_counter,
                                    max_widths_per_type, depth=3,
                                    node_types=child_node_types
                                )
                                
                                if child_node_ids:
                                    _layout_nodes_by_type(parent_cluster, child_node_ids, child_node_types)
                                    # Track first child as anchor for this parent cluster
                                    sub_cluster_anchor_nodes.append(child_node_ids[0])
                        else:
                            # Regular node without children - place directly in outer cluster
                            node_id = f'node_{node_counter}'
                            node_counter += 1
                            node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                            direct_node_ids.append(node_id)
                            direct_node_types[node_id] = resource.resource_type
                            
                            resource_config = get_resource_config(config, resource.resource_type)
                            display_name = get_display_name(resource, resource_config)
                            icon_path = resource_config.get('diagram_image', '')
                            
                            text_width = max_widths_per_type.get(resource.resource_type)
                            label = _create_node_label(resource.resource_type, display_name, icon_path, text_width)
                            outer_cluster.node(node_id, label=label)
                    
                    # Layout direct nodes by type
                    if direct_node_ids:
                        _layout_nodes_by_type(outer_cluster, direct_node_ids, direct_node_types)
                        # Track first direct node as anchor
                        sub_cluster_anchor_nodes.append(direct_node_ids[0])
                    
                    # Now process other sub-groups
                    for sub_key, resources_in_group in sorted(other_subgroups.items()):
                        sub_cluster_name = f'cluster_sub_{abs(hash((outer_key, sub_key)))}'
                        
                        with outer_cluster.subgraph(name=sub_cluster_name) as sub_cluster:
                            sub_label = _format_sub_group_label(sub_key)
                            # Gray styling (level 2: ~20% gray)
                            gray_level_sub = _get_gray_color(depth=2)
                            
                            if sub_label:
                                # Use DejaVu Sans Bold which is definitely available on Linux
                                sub_cluster.attr(label=sub_label, fontsize='16', fontname='DejaVu Sans Bold', labeljust='l')
                                sub_cluster.attr(style='filled,rounded', color='#909090', fillcolor=gray_level_sub, penwidth='1.5')
                                sub_cluster.attr(margin='22')
                            else:
                                sub_cluster.attr(label='', fontsize='14', labeljust='l')
                                sub_cluster.attr(style='filled,rounded', color='#b0b0b0', fillcolor=gray_level_sub, penwidth='1.0')
                                sub_cluster.attr(margin='16')
                            
                            sub_node_ids: List[str] = []
                            sub_node_types: Dict[str, str] = {}  # Track node types
                            parent_cluster_nodes: List[str] = []  # Track nodes from parent clusters
                            
                            for resource in resources_in_group:
                                parent_key = f"{resource.resource_type}.{resource.name}"
                                
                                # Check if this resource has children
                                if parent_key in parent_to_children:
                                    # Create a nested cluster for this parent and its children
                                    parent_cluster_name = f'cluster_parent_{abs(hash(parent_key))}'
                                    
                                    with sub_cluster.subgraph(name=parent_cluster_name) as parent_cluster:
                                        resource_config = get_resource_config(config, resource.resource_type)
                                        display_name = get_display_name(resource, resource_config)
                                        
                                        # Apply consistent parent cluster styling (gray, level 3)
                                        _apply_parent_cluster_style(parent_cluster, display_name, depth=3)
                                        
                                        # Group children by grouped_by if configured
                                        children = parent_to_children[parent_key]
                                        grouped_children = _group_children_by_config(children, config)
                                        
                                        child_node_ids: List[str] = []
                                        child_node_types: Dict[str, str] = {}
                                        node_counter = _render_grouped_children(
                                            parent_cluster, grouped_children, config,
                                            node_ids, child_node_ids, node_counter,
                                            max_widths_per_type, depth=4,
                                            node_types=child_node_types
                                        )
                                        
                                        if child_node_ids:
                                            _layout_nodes_by_type(parent_cluster, child_node_ids, child_node_types)
                                            # Track first child node for layout
                                            parent_cluster_nodes.append(child_node_ids[0])
                                else:
                                    # Regular node without children
                                    node_id = f'node_{node_counter}'
                                    node_counter += 1
                                    node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                                    sub_node_ids.append(node_id)
                                    sub_node_types[node_id] = resource.resource_type
                                    
                                    resource_config = get_resource_config(config, resource.resource_type)
                                    display_name = get_display_name(resource, resource_config)
                                    icon_path = resource_config.get('diagram_image', '')
                                    
                                    text_width = max_widths_per_type.get(resource.resource_type)
                                    label = _create_node_label(resource.resource_type, display_name, icon_path, text_width)
                                    sub_cluster.node(node_id, label=label)
                            
                            # Layout nodes by type
                            if sub_node_ids:
                                _layout_nodes_by_type(sub_cluster, sub_node_ids, sub_node_types)
                                # Track first node as anchor for this sub-cluster
                                sub_cluster_anchor_nodes.append(sub_node_ids[0])
                            elif parent_cluster_nodes:
                                # If no direct nodes but has parent clusters, use first parent cluster node
                                sub_cluster_anchor_nodes.append(parent_cluster_nodes[0])
                    
                    # Apply grid layout to sub-clusters using anchor nodes (groups side by side)
                    if len(sub_cluster_anchor_nodes) > 1:
                        # Groups on same level should be side by side (horizontal)
                        with outer_cluster.subgraph(name=f'rank_groups_{abs(hash(tuple(sub_cluster_anchor_nodes)))}') as rg:
                            rg.attr(rank='same')
                            for nid in sub_cluster_anchor_nodes:
                                rg.node(nid)
                        # Add invisible edges to maintain order
                        for i in range(len(sub_cluster_anchor_nodes) - 1):
                            outer_cluster.edge(sub_cluster_anchor_nodes[i], sub_cluster_anchor_nodes[i + 1], style='invis', weight='15')
    
    # Remove extension from output_path if present
    output_base = str(Path(output_path).with_suffix(''))
    
    # Render the diagram
    dot.render(output_base, format=output_format, cleanup=True)
    
    return f'{output_base}.{output_format}'


def _get_gray_color(depth: int) -> str:
    """
    Get a gray color based on nesting depth.
    Each level adds ~10% more gray (darker).
    
    Args:
        depth: Nesting depth (0 = lightest, higher = darker)
        
    Returns:
        Hex color string
    """
    # Use module constants for gray color calculation
    value = max(GRAY_MIN_VALUE, GRAY_BASE_VALUE - (depth * GRAY_REDUCTION_PER_LEVEL))
    hex_value = format(value, '02x')
    return f'#{hex_value}{hex_value}{hex_value}'


def _group_children_by_config(
    children: List[Resource], 
    config: Dict[str, Any]
) -> Dict[str, List[Resource]]:
    """
    Group children resources by their grouped_by configuration.
    
    Args:
        children: List of child resources
        config: Configuration dictionary
        
    Returns:
        Dictionary mapping group key to list of resources
    """
    grouped: Dict[str, List[Resource]] = {}
    
    for child in children:
        child_config = get_resource_config(config, child.resource_type)
        
        if child_config and 'grouped_by' in child_config:
            grouped_by = child_config['grouped_by']
            if grouped_by:
                # Build group key from first grouped_by field
                first_field = grouped_by[0]
                value = child.get_value(first_field)
                group_key = str(value).lower() if value is not None else 'unknown'
            else:
                group_key = 'default'
        else:
            group_key = 'default'
        
        if group_key not in grouped:
            grouped[group_key] = []
        grouped[group_key].append(child)
    
    return grouped


def _render_grouped_children(
    parent_graph,
    grouped_children: Dict[str, List[Resource]],
    config: Dict[str, Any],
    node_ids: Dict[str, str],
    all_child_node_ids: List[str],
    node_counter: int,
    max_widths_per_type: Dict[str, int],
    depth: int = 2,
    node_types: Optional[Dict[str, str]] = None
) -> int:
    """
    Render grouped children, creating sub-clusters if there are multiple groups.
    
    Args:
        parent_graph: The parent graph/cluster to render into
        grouped_children: Dictionary of group_key -> resources
        config: Configuration dictionary
        node_ids: Dictionary to track node IDs
        all_child_node_ids: List to collect all child node IDs for layout
        node_counter: Current node counter
        max_widths_per_type: Dictionary of resource_type -> max width
        depth: Current nesting depth for gray color
        node_types: Optional dictionary to track node_id -> resource_type mapping
        
    Returns:
        Updated node counter
    """
    # If only one group (or all 'default'), render directly without sub-clustering
    if len(grouped_children) == 1:
        group_key, children = list(grouped_children.items())[0]
        for child in children:
            child_node_id = f'node_{node_counter}'
            node_counter += 1
            node_ids[f'{child.resource_type}.{child.name}'] = child_node_id
            all_child_node_ids.append(child_node_id)
            if node_types is not None:
                node_types[child_node_id] = child.resource_type
            
            child_config = get_resource_config(config, child.resource_type)
            child_display_name = get_display_name(child, child_config)
            child_icon_path = child_config.get('diagram_image', '')
            
            text_width = max_widths_per_type.get(child.resource_type)
            child_label = _create_node_label(child.resource_type, child_display_name, child_icon_path, text_width)
            parent_graph.node(child_node_id, label=child_label)
    else:
        # Multiple groups - create sub-clusters for each
        for group_key, children in sorted(grouped_children.items()):
            if group_key == 'default' or group_key == 'unknown':
                # Render default/unknown directly without a sub-cluster
                for child in children:
                    child_node_id = f'node_{node_counter}'
                    node_counter += 1
                    node_ids[f'{child.resource_type}.{child.name}'] = child_node_id
                    all_child_node_ids.append(child_node_id)
                    if node_types is not None:
                        node_types[child_node_id] = child.resource_type
                    
                    child_config = get_resource_config(config, child.resource_type)
                    child_display_name = get_display_name(child, child_config)
                    child_icon_path = child_config.get('diagram_image', '')
                    
                    text_width = max_widths_per_type.get(child.resource_type)
                    child_label = _create_node_label(child.resource_type, child_display_name, child_icon_path, text_width)
                    parent_graph.node(child_node_id, label=child_label)
            else:
                # Create a sub-cluster for this group
                sub_cluster_name = f'cluster_grouped_{abs(hash(group_key))}'
                
                with parent_graph.subgraph(name=sub_cluster_name) as sub_cluster:
                    # Format the group label nicely with bold styling
                    group_label_text = _shorten_path_name(group_key)
                    gray_color = _get_gray_color(depth)
                    
                    # Use plain text label - bold styling applied via fontname
                    # Use DejaVu Sans Bold which is definitely available on Linux
                    sub_cluster.attr(label=group_label_text, fontsize='14', 
                                   fontname='DejaVu Sans Bold',
                                   labeljust='l')
                    sub_cluster.attr(style='filled,rounded', color='#a0a0a0', 
                                   fillcolor=gray_color, penwidth='1.0')
                    sub_cluster.attr(margin='16')
                    
                    group_node_ids: List[str] = []
                    group_node_types: Dict[str, str] = {}
                    for child in children:
                        child_node_id = f'node_{node_counter}'
                        node_counter += 1
                        node_ids[f'{child.resource_type}.{child.name}'] = child_node_id
                        group_node_ids.append(child_node_id)
                        all_child_node_ids.append(child_node_id)
                        if node_types is not None:
                            node_types[child_node_id] = child.resource_type
                        group_node_types[child_node_id] = child.resource_type
                        
                        child_config = get_resource_config(config, child.resource_type)
                        child_display_name = get_display_name(child, child_config)
                        child_icon_path = child_config.get('diagram_image', '')
                        
                        text_width = max_widths_per_type.get(child.resource_type)
                        child_label = _create_node_label(child.resource_type, child_display_name, child_icon_path, text_width)
                        sub_cluster.node(child_node_id, label=child_label)
                    
                    # Layout by type (same type vertical, different types horizontal)
                    if group_node_ids:
                        _layout_nodes_by_type(sub_cluster, group_node_ids, group_node_types)
    
    return node_counter


def _apply_parent_cluster_style(cluster, label: str, depth: int = 2) -> None:
    """
    Apply consistent styling to parent resource clusters (for parent-child relationships).
    Uses gray colors with transparency based on depth.
    
    Args:
        cluster: The Graphviz cluster/subgraph to style
        label: The label text for the cluster
        depth: Nesting depth for gray color calculation
    """
    # Shorten label if it contains "/"
    shortened_label = _shorten_path_name(label)
    # Use plain text label - bold styling applied via fontname
    # Use DejaVu Sans Bold which is definitely available on Linux
    cluster.attr(label=shortened_label, fontsize='16', 
                fontname='DejaVu Sans Bold',
                labeljust='l')
    # Gray theme for parent-child groups (based on depth)
    gray_color = _get_gray_color(depth)
    cluster.attr(style='filled,rounded', color='#909090', 
                fillcolor=gray_color, penwidth='1.5')
    cluster.attr(margin='24')  # Increased margin for better spacing


def _escape_html(text: str) -> str:
    """
    Escape special characters in text for HTML/Graphviz labels.
    
    Args:
        text: Text to escape
        
    Returns:
        HTML-escaped text
    """
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _create_node_label(resource_type: str, display_name: str, icon_path: str = '', text_width: Optional[int] = None) -> str:
    """
    Create an HTML-like label for a node with optional icon, resource type, and name.
    Modern cloud diagram aesthetics with shadows and depth.
    All nodes have a fixed minimum width for uniform alignment.
    
    NOTE: display_name is shown as the main (big, bold) name at the top,
    resource_type is shown as the smaller subtitle below.
    
    Args:
        resource_type: The resource type (shown as small subtitle)
        display_name: The display name (shown as big bold name)
        icon_path: Path to the icon image (optional)
        text_width: Optional custom width for text cell (for uniform sizing per type)
        
    Returns:
        HTML-like label string for Graphviz
    """
    # Use provided width or fallback to default
    cell_width = text_width if text_width is not None else MIN_TEXT_CELL_WIDTH
    
    # Escape special characters in text for HTML
    # Don't truncate resource type and display name - show full names
    resource_type_escaped = _escape_html(resource_type)
    display_name_escaped = _escape_html(display_name)

    icon_cell = ''
    if icon_path:
        icon_abs_path = Path(icon_path).resolve()
        if icon_abs_path.exists():
            # Use WIDTH and HEIGHT without FIXEDSIZE to allow content to expand if needed
            icon_cell = (
                f'<TD WIDTH="{ICON_CELL_WIDTH}" HEIGHT="{ICON_CELL_WIDTH}" BGCOLOR="#f5f5f5">'
                f'<IMG SRC="{icon_abs_path}" SCALE="TRUE"/>'
                f'</TD>'
            )
        else:
            # If icon doesn't exist, don't show a placeholder - just skip the icon cell
            # This avoids issues with emoji rendering in Graphviz
            icon_cell = ''

    if icon_cell:
        # Node with icon - modern card-like appearance
        # display_name (big, bold) on top, resource_type (small) below
        # Fixed WIDTH on text cell ensures uniform box sizes for alignment
        return f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="12" BGCOLOR="white" STYLE="rounded">
  <TR>
    {icon_cell}
    <TD WIDTH="{cell_width}" ALIGN="LEFT" BALIGN="LEFT" CELLPADDING="8">
      <FONT POINT-SIZE="16" COLOR="#1f2937"><B>{display_name_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#6b7280">{resource_type_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''
    
    # No icon version - clean, modern card
    # display_name (big, bold) on top, resource_type (small) below
    # Fixed WIDTH ensures uniform box sizes for alignment
    return f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="16" BGCOLOR="white" STYLE="rounded">
  <TR>
    <TD WIDTH="{cell_width + ICON_CELL_WIDTH}" ALIGN="CENTER" BALIGN="CENTER">
      <FONT POINT-SIZE="16" COLOR="#1f2937"><B>{display_name_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#6b7280">{resource_type_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''


def _shorten_path_name(name: str) -> str:
    """
    Shorten a path-like name by keeping only the part after the last '/'.
    
    If the string contains brackets [...], extract the content from within the brackets first.
    Then, apply shortening logic only if there's no '@' in the extracted/remaining part.
    
    Examples:
        "serviceAccount:prj-k8s@example.com[kubexporter/kubexporter-job]" -> "kubexporter-job"
        "path/to/resource" -> "resource"
        "user@example.com" -> "user@example.com" (no shortening)
    
    Args:
        name: The name to shorten (may contain '/' characters and brackets)
        
    Returns:
        The shortened name
    """
    # Extract content from brackets if present
    if '[' in name and ']' in name:
        start = name.find('[')
        end = name.find(']', start)
        if end > start:
            # Extract content from brackets
            name = name[start + 1:end]
    
    # Now apply the shortening logic
    # Don't shorten if the string contains '@' (email addresses, service accounts, etc.)
    if '@' in name:
        return name
    if '/' in name:
        return name.rsplit('/', 1)[-1]
    return name


def _format_outer_group_label(group_key: Tuple[str, ...]) -> str:
    """
    Format an outer group key into a readable label.
    Note: Bold styling is applied via fontname attribute, not HTML tags.
    
    Args:
        group_key: Tuple representing the outer group
        
    Returns:
        Formatted label string
    """
    if not group_key:
        return 'Resources'
    elif group_key == ('ungrouped',):
        return 'Ungrouped Resources'
    elif group_key == ('default',):
        return 'Default Group'
    else:
        # For outer groups, shorten path-like values and join
        shortened_parts = [_shorten_path_name(part) for part in group_key]
        return ' | '.join(shortened_parts)


def _format_sub_group_label(sub_key: Tuple[str, ...]) -> str:
    """
    Format a sub-group key into a readable label.
    Does not include resource type prefix - only shows grouping values.
    Note: Bold styling is applied via fontname attribute, not HTML tags.
    
    Args:
        sub_key: Tuple representing the sub-group
        
    Returns:
        Formatted label string, or empty string
    """
    if not sub_key:
        return ''
    
    parts = list(sub_key)
    
    # Handle parent:child relationships (from group_id)
    if len(parts) == 1:
        part = parts[0]
        # If it's a parent resource identifier, extract just the name
        if ':' in part:
            return _shorten_path_name(part.split(':', 1)[1])
        # If it's just 'resources', don't show a label
        elif part == 'resources':
            return ''
        else:
            return _shorten_path_name(part)
    
    # For multiple parts, show them as joined values (without resource type)
    # Skip if all values are 'unknown'
    if all(v == 'unknown' for v in parts):
        return ''
    
    # Shorten path-like values
    shortened_parts = [_shorten_path_name(p) for p in parts]
    return ' | '.join(shortened_parts)

def _layout_nodes_by_type(g: Digraph, node_ids: List[str], node_types: Dict[str, str]) -> None:
    """
    Layout nodes so that resources of the same type are stacked vertically,
    and different types are placed side by side (horizontally).
    
    Args:
        g: The graph/subgraph to layout
        node_ids: List of node IDs to arrange
        node_types: Dictionary mapping node_id to resource_type
    """
    n = len(node_ids)
    if n <= 1:
        return
    
    # Group nodes by resource type
    type_groups: Dict[str, List[str]] = {}
    for node_id in node_ids:
        resource_type = node_types.get(node_id, 'unknown')
        if resource_type not in type_groups:
            type_groups[resource_type] = []
        type_groups[resource_type].append(node_id)
    
    # Sort type groups for consistent ordering
    sorted_types = sorted(type_groups.keys())
    
    # If all nodes are the same type, stack them vertically
    if len(sorted_types) == 1:
        nodes = type_groups[sorted_types[0]]
        # Stack vertically with invisible edges
        for i in range(len(nodes) - 1):
            g.edge(nodes[i], nodes[i + 1], style='invis', weight='10')
        return
    
    # Multiple types: place different types side by side (horizontally)
    # and same-type resources stacked vertically within each column
    
    # Get first node of each type for horizontal alignment
    first_nodes = [type_groups[t][0] for t in sorted_types]
    
    # Put first nodes of each type on the same rank (horizontal alignment)
    with g.subgraph(name=f'rank_types_{abs(hash(tuple(first_nodes)))}') as rg:
        rg.attr(rank='same')
        for nid in first_nodes:
            rg.node(nid)
    
    # Add invisible edges between first nodes to maintain horizontal order
    for i in range(len(first_nodes) - 1):
        g.edge(first_nodes[i], first_nodes[i + 1], style='invis', weight='15')
    
    # Stack nodes of the same type vertically
    for resource_type in sorted_types:
        nodes = type_groups[resource_type]
        for i in range(len(nodes) - 1):
            g.edge(nodes[i], nodes[i + 1], style='invis', weight='10')

def _layout_nodes_in_grid(g: Digraph, node_ids: List[str], max_cols: int = 3) -> None:
    """
    Force a wrapped/grid layout inside a (sub)graph by adding invisible edges
    and 'rank=same' rows. Prevents the 'everything in one line' layout.
    Creates a more cloud-provider-like grid arrangement.
    
    Args:
        g: The graph/subgraph to layout
        node_ids: List of node IDs to arrange
        max_cols: Maximum columns per row (default 3 for better cloud-like layout)
    """
    n = len(node_ids)
    if n <= 1:
        return

    # Calculate optimal columns: prefer 2-3 columns for cleaner look
    if n <= 3:
        cols = n  # Single row
    elif n <= 6:
        cols = 2  # 2 columns
    else:
        cols = min(max_cols, max(2, int(n ** 0.5)))

    rows = [node_ids[i:i + cols] for i in range(0, n, cols)]

    # Put nodes of each row on same rank
    for r_idx, row in enumerate(rows):
        with g.subgraph(name=f'rank_row_{abs(hash(tuple(row)))}') as rg:
            rg.attr(rank='same')
            for nid in row:
                rg.node(nid)

        # Keep order inside the row with invisible edges
        for i in range(len(row) - 1):
            g.edge(row[i], row[i + 1], style='invis', weight='15')

    # Stack rows top->bottom with invisible edges for proper alignment
    for r_idx in range(len(rows) - 1):
        a = rows[r_idx][0]
        b = rows[r_idx + 1][0]
        g.edge(a, b, style='invis', weight='5')

def _ellipsize(s: str, n: int = 42) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
