"""Diagram generator for Terraform resources."""

import os
import re
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
) -> Dict[Tuple[str, ...], Dict[str, List[Resource]]]:
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
        Nested dictionary: outer_group_key -> resource_type -> [resources]
    """
    # Extract grouping hierarchy
    hierarchy = extract_grouping_hierarchy(resources, config)
    
    # First pass: identify resources that can be parents (have 'id' defined)
    parent_resources = {}  # Maps (resource_type, id_value) -> resource
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        if resource_config and 'id' in resource_config:
            id_field = resource_config['id']
            id_value = resource.get_value(id_field)
            if id_value:
                parent_resources[(resource.resource_type, str(id_value))] = resource
    
    # Second pass: build groups with parent-child relationships
    outer_groups = {}  # Maps outer_group_key -> {resource_type/sub_key -> [resources]}
    resource_to_parent = {}  # Maps resource -> parent_resource
    
    for resource in resources:
        resource_config = get_resource_config(config, resource.resource_type)
        
        # Check if this resource has a parent (group_id)
        parent_resource = None
        if resource_config and 'group_id' in resource_config:
            group_id_field = resource_config['group_id']
            parent_id = resource.get_value(group_id_field)
            
            if parent_id:
                # Find parent resource - normalize parent_id for comparison
                parent_id_lower = str(parent_id).lower()
                for (parent_type, parent_id_val), potential_parent in parent_resources.items():
                    if parent_id_lower == parent_id_val.lower():
                        parent_resource = potential_parent
                        resource_to_parent[resource] = parent_resource
                        break
        
        # Determine the outer group key
        if parent_resource:
            # If has parent, outer key is based on parent's grouped_by
            parent_config = get_resource_config(config, parent_resource.resource_type)
            if parent_config and 'grouped_by' in parent_config:
                grouped_by = parent_config['grouped_by']
                if grouped_by:
                    first_field = grouped_by[0]
                    first_value = parent_resource.get_value(first_field)
                    # Normalize to lowercase
                    outer_key = (str(first_value).lower() if first_value is not None else 'unknown',)
                else:
                    outer_key = ('default',)
            else:
                outer_key = ('default',)
        elif not resource_config or 'grouped_by' not in resource_config:
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
        if parent_resource:
            # Sub-key includes parent resource identifier
            parent_display = f"{parent_resource.resource_type}:{parent_resource.name}"
            
            # If child also has grouped_by, append those values
            if resource_config and 'grouped_by' in resource_config:
                grouped_by = resource_config['grouped_by']
                if grouped_by:
                    sub_key_parts = [parent_display]
                    for field in grouped_by:
                        value = resource.get_value(field)
                        # Normalize to lowercase
                        sub_key_parts.append(str(value).lower() if value is not None else 'unknown')
                    sub_key = tuple(sub_key_parts)
                else:
                    sub_key = (parent_display,)
            else:
                sub_key = (parent_display,)
        elif not resource_config or 'grouped_by' not in resource_config:
            sub_key = (resource.resource_type,)
        else:
            grouped_by = resource_config['grouped_by']
            
            if not grouped_by:
                sub_key = (resource.resource_type,)
            elif len(grouped_by) > 1:
                # Don't include resource type in sub_key, just the grouping values
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
    
    return outer_groups


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
    
    # Create directed graph with improved layout settings
    dot = Digraph(comment='Terraform Resources', engine='dot')
    
    # Layout - Left to Right for cleaner project arrangement
    dot.attr(rankdir='LR')  # Left to Right for horizontal project flow
    dot.attr(splines='ortho')  # ortho for cleaner right angles like cloud diagrams
    dot.attr(compound='true')
    dot.attr(concentrate='false')  # Changed to false to avoid edge overlap
    dot.attr(newrank='true')
    # Note: pack and packmode attributes removed due to graphviz segfault when combining
    # these attributes with HTML table labels in nested clusters (triggers SIGSEGV 11)
    dot.attr(nodesep='0.85')  # Increased for better spacing
    dot.attr(ranksep='1.5')   # Increased for better horizontal spacing between projects
    dot.attr(pad='0.5')       # Increased padding
    dot.attr(margin='0.3')
    dot.attr(dpi='150')       # Slightly higher DPI for sharper output
    
    # Graph look
    dot.attr(bgcolor='#f8f9fa')  # Slightly lighter background
    dot.attr(fontname='Helvetica,Arial,sans-serif')
    dot.attr(fontsize='12')
    
    # Defaults
    dot.attr('node', shape='plaintext', fontname='Helvetica,Arial,sans-serif')
    dot.attr('edge', color='#5f6368', penwidth='1.5', arrowsize='0.8')
    
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
    
    # Create outer clusters for each top-level group
    for outer_key, sub_groups in sorted_groups:
        outer_cluster_name = f'cluster_outer_{abs(hash(outer_key))}'
        
        with dot.subgraph(name=outer_cluster_name) as outer_cluster:
            # Set outer cluster label with improved styling
            outer_label = _format_outer_group_label(outer_key)
            outer_cluster.attr(label=outer_label, fontsize='20', fontname='Helvetica-Bold,Arial-Bold,sans-serif-bold')
            outer_cluster.attr(style='filled,rounded', color='#4285f4', fillcolor='#e8f0fe', penwidth='2.5')
            outer_cluster.attr(margin='25')
            
            # Check if we need sub-clusters or can place resources directly
            # If there's only one sub-group and it's named 'resources', skip sub-clustering
            has_multiple_sub_groups = len(sub_groups) > 1
            has_non_resource_groups = not any('resources' == str(k) for k in sub_groups.keys())
            needs_sub_clusters = has_multiple_sub_groups or has_non_resource_groups
            
            if not needs_sub_clusters and len(sub_groups) == 1:
                # Place resources directly in the outer cluster
                sub_key, resources_in_group = list(sub_groups.items())[0]
                sub_node_ids: List[str] = []
                
                for resource in resources_in_group:
                    node_id = f'node_{node_counter}'
                    node_counter += 1
                    node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                    sub_node_ids.append(node_id)
                    
                    resource_config = get_resource_config(config, resource.resource_type)
                    display_name = get_display_name(resource, resource_config)
                    icon_path = resource_config.get('diagram_image', '')
                    
                    label = _create_node_label(resource.resource_type, display_name, icon_path)
                    outer_cluster.node(node_id, label=label)
                
                # Layout nodes in grid
                _layout_nodes_in_grid(outer_cluster, sub_node_ids, max_cols=3)
            else:
                # Create sub-clusters within the outer cluster
                for sub_key, resources_in_group in sorted(sub_groups.items()):
                    sub_cluster_name = f'cluster_sub_{abs(hash((outer_key, sub_key)))}'
                    
                    # Check if this is a parent-child relationship
                    is_parent_child = any(':' in str(k) for k in [sub_key])
                    
                    with outer_cluster.subgraph(name=sub_cluster_name) as sub_cluster:
                        sub_label = _format_sub_group_label(sub_key)
                        
                        # Different styling for parent-child relationships
                        if is_parent_child and sub_label:
                            sub_cluster.attr(label=sub_label, fontsize='15', fontname='Helvetica-Bold,Arial-Bold,sans-serif-bold')
                            sub_cluster.attr(style='filled,rounded', color='#34a853', fillcolor='#e6f4ea', penwidth='2')
                            sub_cluster.attr(margin='16')
                        elif sub_label:
                            sub_cluster.attr(label=sub_label, fontsize='14', fontname='Helvetica,Arial,sans-serif')
                            sub_cluster.attr(style='filled,rounded', color='#dadce0', fillcolor='#ffffff', penwidth='1.5')
                            sub_cluster.attr(margin='14')
                        else:
                            # No label, minimal styling
                            sub_cluster.attr(label='', fontsize='14')
                            sub_cluster.attr(style='filled,rounded', color='#e8eaed', fillcolor='#ffffff', penwidth='1')
                            sub_cluster.attr(margin='10')
                        
                        sub_node_ids: List[str] = []
                        
                        for resource in resources_in_group:
                            node_id = f'node_{node_counter}'
                            node_counter += 1
                            node_ids[f'{resource.resource_type}.{resource.name}'] = node_id
                            sub_node_ids.append(node_id)
                            
                            resource_config = get_resource_config(config, resource.resource_type)
                            display_name = get_display_name(resource, resource_config)
                            icon_path = resource_config.get('diagram_image', '')
                            
                            label = _create_node_label(resource.resource_type, display_name, icon_path)
                            sub_cluster.node(node_id, label=label)
                        
                        # Layout nodes in grid (smaller max_cols for sub-clusters)
                        _layout_nodes_in_grid(sub_cluster, sub_node_ids, max_cols=2)
    
    # Remove extension from output_path if present
    output_base = str(Path(output_path).with_suffix(''))
    
    # Render the diagram
    dot.render(output_base, format=output_format, cleanup=True)
    
    return f'{output_base}.{output_format}'


def _create_node_label(resource_type: str, display_name: str, icon_path: str = '') -> str:
    """
    Create an HTML-like label for a node with optional icon, resource type, and name.
    Styled to match Google Cloud diagram aesthetics.
    
    Args:
        resource_type: The resource type (shown as big name)
        display_name: The display name (shown as small name)
        icon_path: Path to the icon image (optional)
        
    Returns:
        HTML-like label string for Graphviz
    """
    # Escape special characters in text for HTML
    resource_type_escaped = _ellipsize(resource_type.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), 30)
    display_name_escaped = _ellipsize(display_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), 40)

    icon_cell = ''
    if icon_path:
        icon_abs_path = Path(icon_path).resolve()
        if icon_abs_path.exists():
            icon_cell = (
                f'<TD WIDTH="60" HEIGHT="60" FIXEDSIZE="TRUE">'
                f'<IMG SRC="{icon_abs_path}" SCALE="TRUE"/>'
                f'</TD>'
            )
        else:
            # Placeholder icon with better styling
            icon_cell = '<TD WIDTH="50" HEIGHT="50" FIXEDSIZE="TRUE" BGCOLOR="#e8f0fe" BORDER="1" COLOR="#4285f4"><FONT POINT-SIZE="26">📦</FONT></TD>'

    if icon_cell:
        return f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="12" BGCOLOR="white" STYLE="rounded">
  <TR>
    {icon_cell}
    <TD ALIGN="LEFT" BALIGN="LEFT">
      <FONT POINT-SIZE="15" COLOR="#202124"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="10" COLOR="#5f6368">{display_name_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''
    
    # No icon version with better styling
    return f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="14" BGCOLOR="white" STYLE="rounded">
  <TR>
    <TD ALIGN="CENTER" BALIGN="CENTER">
      <FONT POINT-SIZE="15" COLOR="#202124"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="10" COLOR="#5f6368">{display_name_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''


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
    Does not include resource type prefix - only shows grouping values.
    
    Args:
        sub_key: Tuple representing the sub-group
        
    Returns:
        Formatted label string
    """
    if not sub_key:
        return ''
    
    parts = list(sub_key)
    
    # Handle parent:child relationships (from group_id)
    if len(parts) == 1:
        part = parts[0]
        # If it's a parent resource identifier, extract just the name
        if ':' in part:
            return part.split(':', 1)[1]
        # If it's just 'resources', don't show a label
        if part == 'resources':
            return ''
        return part
    
    # For multiple parts, show them as joined values (without resource type)
    # Skip if all values are 'unknown'
    if all(v == 'unknown' for v in parts):
        return ''
    
    return ' | '.join(parts)

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
