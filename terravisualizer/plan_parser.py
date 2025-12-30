"""Terraform plan JSON parser."""

import json
from typing import Any, Dict, List


class Resource:
    """Represents a Terraform resource."""

    def __init__(self, resource_type: str, name: str, values: Dict[str, Any], address: str = None):
        """
        Initialize a resource.

        Args:
            resource_type: The type of resource (e.g., "google_compute_address")
            name: The resource name (may include index, e.g., "default[0]")
            values: The resource values/attributes
            address: The unique Terraform address (e.g., "google_compute_address.static_ip_1").
                     If not provided, defaults to "{resource_type}.{name}".
                     The address from Terraform plan JSON is always well-formed and safe to use.
        """
        self.resource_type = resource_type
        self.name = name
        self.values = values
        # Use provided address (from Terraform JSON) or construct from type and name
        self.address = address if address else f"{resource_type}.{name}"

    def get_value(self, path: str) -> Any:
        """
        Get a value from the resource using a path like 'values.project'.

        Args:
            path: Dot-separated path to the value

        Returns:
            The value at the path, or None if not found
        """
        parts = path.split(".")
        current = {"values": self.values, "name": self.name, "address": self.address}

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def __repr__(self):
        return f"Resource({self.resource_type}, {self.name})"


def _dedup_by_address_strict(resources: List[Resource]) -> List[Resource]:
    """
    Option B: Deduplicate exactly once by Terraform address.

    - Trusts the plan structure (we collect everything we see)
    - Enforces address uniqueness
    - Fails fast if duplicates are encountered (signals double-parsing)
    """
    by_addr: Dict[str, Resource] = {}
    for r in resources:
        addr = r.address or f"{r.resource_type}.{r.name}"
        r.address = addr  # normalize back

        if addr in by_addr:
            # Fail fast instead of silently dropping/overwriting
            raise ValueError(
                f"Duplicate Terraform address encountered: {addr}\n"
                f"Existing: {by_addr[addr].resource_type}.{by_addr[addr].name}\n"
                f"New:      {r.resource_type}.{r.name}"
            )

        by_addr[addr] = r

    return list(by_addr.values())


def parse_terraform_plan(plan_path: str) -> List[Resource]:
    """
    Parse a Terraform plan JSON file and extract resources.

    Args:
        plan_path: Path to the Terraform plan JSON file

    Returns:
        List of Resource objects (deduped once by address)
    """
    with open(plan_path, "r") as f:
        plan_data = json.load(f)

    resources: List[Resource] = []

    # 1) planned_values: best for structure
    if "planned_values" in plan_data:
        resources.extend(_extract_from_module(plan_data["planned_values"].get("root_module", {})))

    # 2) resource_changes: often contains additional data, but may overlap with planned_values
    if "resource_changes" in plan_data:
        for change in plan_data["resource_changes"]:
            resource_type = change.get("type", "")
            name = change.get("name", "")
            address = change.get("address", "")

            # If resource has an index, append it to name to make it unique for display/debugging
            index = change.get("index")
            if index is not None:
                name = f"{name}[{index}]"

            # Get values from after (planned state)
            values: Dict[str, Any] = {}
            after = change.get("change", {}).get("after")
            if after is not None:
                values = after or {}

            # IMPORTANT: no dedup here (trust plan structure)
            resources.append(Resource(resource_type, name, values, address))

    # Option B: dedup once at the end by address (strict)
    return _dedup_by_address_strict(resources)


def _extract_from_module(module: Dict[str, Any]) -> List[Resource]:
    """
    Extract resources from a module (recursive for nested modules).

    Args:
        module: Module data from Terraform plan

    Returns:
        List of Resource objects
    """
    resources: List[Resource] = []

    # Extract resources from current module
    for resource_data in module.get("resources", []):
        resource_type = resource_data.get("type", "")
        name = resource_data.get("name", "")
        address = resource_data.get("address", "")

        # If resource has an index, append it to name to make it unique for display/debugging
        index = resource_data.get("index")
        if index is not None:
            name = f"{name}[{index}]"

        values = resource_data.get("values", {}) or {}

        # IMPORTANT: no dedup here (trust plan structure)
        resources.append(Resource(resource_type, name, values, address))

    # Recursively extract from child modules
    for child_module in module.get("child_modules", []):
        resources.extend(_extract_from_module(child_module))

    return resources
