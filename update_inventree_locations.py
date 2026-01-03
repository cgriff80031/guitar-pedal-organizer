#!/usr/bin/env python3
"""
Update Inventree Stock Locations
Reads the generated label data and updates Inventree with exact compartment locations
"""

import requests
import csv
import json
from typing import Dict, List, Tuple

# Configuration
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"
LABEL_FILE = "akromills_labels_complete.csv"
LOCATION_MAPPING_FILE = "component_locations.json"

# Compartment layout for 4x drawers:
# [1] [2]  (front)
# [3] [4]  (back)

class InventreeLocationUpdater:
    """Updates component locations in Inventree"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}
        self.location_cache = {}
        self.part_cache = {}

    def create_location_hierarchy(self):
        """Create the location structure in Inventree if it doesn't exist"""
        # Check if Workshop location exists
        workshop_id = self._get_or_create_location("Workshop", None, "Main workshop storage")

        # Create Unit locations under Workshop
        u1_id = self._get_or_create_location("Unit 1 (U1)", workshop_id, "Small drawer unit - 4x compartment drawers")
        u2_id = self._get_or_create_location("Unit 2 (U2)", workshop_id, "Mixed drawer unit - Large/Tall/Medium")

        return {"U1": u1_id, "U2": u2_id}

    def _get_or_create_location(self, name: str, parent_id: int = None, description: str = "") -> int:
        """Get existing location or create if doesn't exist"""
        # Check cache first
        cache_key = f"{parent_id}:{name}"
        if cache_key in self.location_cache:
            return self.location_cache[cache_key]

        # Search for existing location
        url = f"{self.base_url}/api/stock/location/"
        params = {"name": name}
        if parent_id:
            params["parent"] = parent_id

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Handle both list and dict responses
        results = data if isinstance(data, list) else data.get('results', [])

        if results:
            location_id = results[0]['pk']
            self.location_cache[cache_key] = location_id
            return location_id

        # Create new location
        payload = {
            "name": name,
            "description": description,
            "structural": False
        }
        if parent_id:
            payload["parent"] = parent_id

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        location_id = response.json()['pk']
        self.location_cache[cache_key] = location_id
        return location_id

    def create_drawer_locations(self, unit_mapping: Dict[str, int], drawer_id: str, unit: str) -> int:
        """Create a specific drawer location (e.g., S1, M5, L1)"""
        unit_id = unit_mapping[unit]
        drawer_name = f"{drawer_id}"

        # Description based on drawer type
        if drawer_id.startswith('S'):
            desc = f"Small drawer {drawer_id} - 4x compartments"
        elif drawer_id.startswith('M'):
            desc = f"Medium drawer {drawer_id}"
        elif drawer_id.startswith('L'):
            desc = f"Large drawer {drawer_id}"
        elif drawer_id.startswith('T'):
            desc = f"Tall drawer {drawer_id}"
        else:
            desc = f"Drawer {drawer_id}"

        return self._get_or_create_location(drawer_name, unit_id, desc)

    def create_compartment_location(self, drawer_id: int, compartment: int) -> int:
        """Create a compartment location within a drawer"""
        # Compartment positions: 1=Front-Left, 2=Front-Right, 3=Back-Left, 4=Back-Right
        positions = {
            1: "Front-Left",
            2: "Front-Right",
            3: "Back-Left",
            4: "Back-Right"
        }

        comp_name = f"Compartment {compartment}"
        desc = f"{positions.get(compartment, f'Position {compartment}')}"

        return self._get_or_create_location(comp_name, drawer_id, desc)

    def find_part_by_name(self, part_name: str) -> int:
        """Find a part in Inventree by name"""
        # Check cache
        if part_name in self.part_cache:
            return self.part_cache[part_name]

        url = f"{self.base_url}/api/part/"
        params = {"search": part_name, "active": True}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Handle both list and dict responses
        results = data if isinstance(data, list) else data.get('results', [])
        if not results:
            print(f"  WARNING: Part '{part_name}' not found in Inventree")
            return None

        # Try to find exact match
        for part in results:
            if part['name'].lower() == part_name.lower():
                part_id = part['pk']
                self.part_cache[part_name] = part_id
                return part_id

        # Use first match if no exact match
        part_id = results[0]['pk']
        self.part_cache[part_name] = part_id
        return part_id

    def update_part_default_location(self, part_id: int, location_id: int):
        """Update a part's default stock location"""
        url = f"{self.base_url}/api/part/{part_id}/"

        payload = {"default_location": location_id}

        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()


def parse_label_data(csv_file: str) -> Dict[str, List[Tuple[str, int]]]:
    """
    Parse the label CSV and extract component-to-location mappings
    Returns: dict of {component_name: [(drawer_id, compartment_num), ...]}
    """
    component_locations = {}

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            unit = row['Unit']
            drawer_top = row['Bin_Top']
            drawer_bottom = row['Bin_Bottom']
            label_top = row['Label_Top']
            label_bottom = row['Label_Bottom']

            # Parse top drawer label
            if label_top and drawer_top:
                components = parse_label_components(label_top)
                for i, comp in enumerate(components, start=1):
                    if comp not in component_locations:
                        component_locations[comp] = []
                    component_locations[comp].append((unit, drawer_top, i))

            # Parse bottom drawer label
            if label_bottom and drawer_bottom:
                components = parse_label_components(label_bottom)
                for i, comp in enumerate(components, start=1):
                    if comp not in component_locations:
                        component_locations[comp] = []
                    component_locations[comp].append((unit, drawer_bottom, i))

    return component_locations


def parse_label_components(label: str) -> List[str]:
    """
    Extract individual component values from a label
    Example: "R: 100R  |  220R  |  470R" -> ["100R", "220R", "470R"]
    """
    # Remove the prefix (e.g., "R: ", "IC: ", "Pots A: ")
    if ':' in label:
        _, values = label.split(':', 1)
    else:
        values = label

    # Split by | and clean
    components = [c.strip() for c in values.split('|') if c.strip()]

    return components


def generate_location_map(component_locations: Dict, output_file: str):
    """Save the location mapping to a JSON file for reference"""
    # Convert to serializable format
    serializable = {}
    for comp, locations in component_locations.items():
        serializable[comp] = [
            {"unit": unit, "drawer": drawer, "compartment": comp_num}
            for unit, drawer, comp_num in locations
        ]

    with open(output_file, 'w') as f:
        json.dump(serializable, f, indent=2)

    print(f"Location mapping saved to: {output_file}")


def main():
    print("Inventree Location Updater")
    print("=" * 50)

    # Initialize updater
    updater = InventreeLocationUpdater(INVENTREE_URL, API_TOKEN)

    # Step 1: Create location hierarchy
    print("\n1. Creating location hierarchy in Inventree...")
    unit_mapping = updater.create_location_hierarchy()
    print(f"   Created/verified Unit locations: {unit_mapping}")

    # Step 2: Parse label data
    print("\n2. Parsing label data...")
    component_locations = parse_label_data(LABEL_FILE)
    print(f"   Found {len(component_locations)} unique component types")

    # Step 3: Generate location map file
    generate_location_map(component_locations, LOCATION_MAPPING_FILE)

    # Step 4: Update Inventree
    print("\n3. Updating Inventree locations...")
    update_count = 0
    error_count = 0

    for component, locations in component_locations.items():
        # Each component might be in multiple locations, use the first one as default
        unit, drawer_id, compartment = locations[0]

        try:
            # Create drawer location
            drawer_loc_id = updater.create_drawer_locations(unit_mapping, drawer_id, unit)

            # Create compartment location
            compartment_loc_id = updater.create_compartment_location(drawer_loc_id, compartment)

            # Find the part in Inventree
            # For resistors/caps, we need to match the value
            part_name = component_to_part_name(component)
            part_id = updater.find_part_by_name(part_name)

            if part_id:
                # Update the part's default location
                updater.update_part_default_location(part_id, compartment_loc_id)
                update_count += 1
                print(f"   ✓ {part_name} → {unit}-{drawer_id}-{compartment}")
            else:
                error_count += 1

        except Exception as e:
            print(f"   ✗ Error updating {component}: {e}")
            error_count += 1

    print(f"\n✓ Updated {update_count} component locations")
    if error_count > 0:
        print(f"  ⚠ {error_count} components had errors")


def component_to_part_name(component: str) -> str:
    """
    Convert a component value to Inventree part name
    Examples:
      "100R" -> "100R Resistor"
      "10K" -> "10K Resistor"
      "TL072" -> "TL072"
      "100nF" -> "100nF Capacitor"
    """
    # Check if it's a resistor value
    if component.endswith('R') or component.endswith('K') or component.endswith('M'):
        # Check if it's just a number or has R/K/M
        if any(c.isdigit() for c in component):
            return f"{component} Resistor"

    # Check if it's a capacitor value
    if any(unit in component.lower() for unit in ['pf', 'nf', 'uf', 'µf']):
        return f"{component} Capacitor"

    # Otherwise return as-is (ICs, etc.)
    return component


if __name__ == "__main__":
    main()
