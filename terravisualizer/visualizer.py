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
    
    # Layout / Packing
    dot.attr(rankdir='LR')
    dot.attr(splines='polyline')          # rechte Winkel wie GCP-Diagramme
    dot.attr(compound='true')
    dot.attr(concentrate='true')
    dot.attr(newrank='true')
    # Note: pack and packmode attributes removed due to graphviz segfault with HTML labels in nested clusters
    dot.attr(nodesep='0.55')
    dot.attr(ranksep='0.85')
    dot.attr(pad='0.35')
    dot.attr(margin='0.2')
    dot.attr(dpi='144')
    
    # Graph look
    dot.attr(bgcolor='#f5f5f5')
    dot.attr(fontname='Helvetica,Arial,sans-serif')
    dot.attr(fontsize='12')
    
    # Defaults
    dot.attr('node', shape='plaintext', fontname='Helvetica,Arial,sans-serif')
    dot.attr('edge', color='#5f6368', penwidth='1.2', arrowsize='0.7')
    
    # Track node IDs
    node_counter = 0
    node_ids = {}
    
    # Create outer clusters for each top-level group
    for outer_key, sub_groups in sorted(grouped.items()):
        outer_cluster_name = f'cluster_outer_{abs(hash(outer_key))}'
        
        with dot.subgraph(name=outer_cluster_name) as outer_cluster:
            # Set outer cluster label with improved styling
            outer_label = _format_outer_group_label(outer_key)
            outer_cluster.attr(label=outer_label, fontsize='18', fontname='Helvetica-Bold,Arial-Bold,sans-serif-bold')
            outer_cluster.attr(style='filled,rounded', color='#4285f4', fillcolor='#e8f0fe', penwidth='2')
            outer_cluster.attr(margin='20')
            
            # Create sub-clusters within the outer cluster
            for sub_key, resources_in_group in sorted(sub_groups.items()):
                sub_cluster_name = f'cluster_sub_{abs(hash((outer_key, sub_key)))}'
            
                with outer_cluster.subgraph(name=sub_cluster_name) as sub_cluster:
                    sub_label = _format_sub_group_label(sub_key)
                    sub_cluster.attr(label=sub_label, fontsize='14', fontname='Helvetica,Arial,sans-serif')
                    sub_cluster.attr(style='filled,rounded', color='#dadce0', fillcolor='#ffffff', penwidth='1.5')
                    sub_cluster.attr(margin='14')
            
                    # >>> NEU: IDs sammeln
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
            
                    # >>> NEU: Grid erzwingen (statt 1 Linie)
                    _layout_nodes_in_grid(sub_cluster, sub_node_ids)
    
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
    resource_type_escaped = _ellipsize(resource_type.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), 28)
    display_name_escaped = _ellipsize(display_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), 52)

    icon_cell = ''
    if icon_path:
        icon_abs_path = Path(icon_path).resolve()
        if icon_abs_path.exists():
            icon_cell = (
                f'<TD WIDTH="56" HEIGHT="56">'
                f'<IMG SRC="{icon_abs_path}" SCALE="TRUE"/>'
                f'</TD>'
            )
        else:
            icon_cell = '<TD WIDTH="44" HEIGHT="44" BGCOLOR="#f1f3f4" BORDER="0"><FONT POINT-SIZE="22">📦</FONT></TD>'

    if icon_cell:
        return f'''<
<TABLE BORDER="1" COLOR="#dadce0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="10" BGCOLOR="white">
  <TR>
    {icon_cell}
    <TD ALIGN="LEFT" BALIGN="LEFT">
      <FONT POINT-SIZE="14" COLOR="#202124"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#5f6368">{display_name_escaped}</FONT>
    </TD>
  </TR>
</TABLE>>'''
    return f'''<
<TABLE BORDER="1" COLOR="#dadce0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="12" BGCOLOR="white">
  <TR>
    <TD ALIGN="LEFT" BALIGN="LEFT">
      <FONT POINT-SIZE="14" COLOR="#202124"><B>{resource_type_escaped}</B></FONT><BR/>
      <FONT POINT-SIZE="11" COLOR="#5f6368">{display_name_escaped}</FONT>
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

def _layout_nodes_in_grid(g: Digraph, node_ids: List[str], max_cols: int = 4) -> None:
    """
    Force a wrapped/grid layout inside a (sub)graph by adding invisible edges
    and 'rank=same' rows. Prevents the 'everything in one line' layout.
    """
    n = len(node_ids)
    if n <= 1:
        return

    # simple heuristic: 2..max_cols columns depending on count
    cols = min(max_cols, max(2, int(n ** 0.5) + 1))

    rows = [node_ids[i:i + cols] for i in range(0, n, cols)]

    # Put nodes of each row on same rank
    for r_idx, row in enumerate(rows):
        with g.subgraph(name=f'rank_row_{r_idx}') as rg:
            rg.attr(rank='same')
            for nid in row:
                rg.node(nid)

        # Keep order inside the row
        for i in range(len(row) - 1):
            g.edge(row[i], row[i + 1], style='invis', weight='10', constraint='false')

    # Stack rows top->bottom
    for r_idx in range(len(rows) - 1):
        a = rows[r_idx][0]
        b = rows[r_idx + 1][0]
        g.edge(a, b, style='invis', weight='2')

def _ellipsize(s: str, n: int = 42) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
