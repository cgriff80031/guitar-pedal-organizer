#!/usr/bin/env python3
"""
Update Missing Inventree Locations with Fuzzy Matching

This script uses intelligent fuzzy matching to assign default locations
to parts that weren't matched by the original script.
"""

import requests
import json
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

# Configuration
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"
LABEL_FILE = "akromills_labels_complete.csv"
LOCATION_MAPPING_FILE = "component_locations.json"

class FuzzyLocationUpdater:
    """Updates locations using fuzzy matching"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}
        self.location_cache = {}
        self.part_cache = {}

    def normalize_name(self, name: str) -> str:
        """Normalize a component name for matching"""
        # Convert to lowercase
        name = name.lower().strip()

        # Remove common suffixes
        suffixes = [
            ' capacitor', ' resistor', ' pot', ' potentiometer',
            ' ceramic', ' film', ' electrolytic', ' axial',
            ' npn', ' pnp', ' jfet', ' mosfet', ' diode',
            ' schottky', ' germanium', ' silicon', ' zener',
            ' rectifier', ' switch', ' jack', ' footswitch'
        ]

        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()

        return name

    def extract_pot_value(self, name: str) -> Optional[str]:
        """Extract pot value from various formats"""
        name = name.lower()

        # Handle A100K, B100K, C100K formats
        if name.startswith(('a', 'b', 'c')) and any(c.isdigit() for c in name):
            # Extract value after the letter
            value = name[1:].replace(' pot', '').replace('potentiometer', '').strip()
            return value

        # Handle Trimpot formats
        if 'trimpot' in name or 'trimmer' in name:
            # Extract the value
            parts = name.replace('trimpot', '').replace('trimmer', '').strip().split()
            for part in parts:
                if any(c.isdigit() for c in part):
                    return part

        return None

    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_best_match(self, component_name: str, inventree_parts: List[Dict]) -> Optional[Dict]:
        """Find the best matching part in Inventree"""

        # Strategy 1: Exact match
        for part in inventree_parts:
            if part['name'].lower() == component_name.lower():
                return part

        # Strategy 2: Normalized match
        normalized_component = self.normalize_name(component_name)
        for part in inventree_parts:
            normalized_part = self.normalize_name(part['name'])
            if normalized_component == normalized_part:
                return part

        # Strategy 3: Pot value extraction
        pot_value = self.extract_pot_value(component_name)
        if pot_value:
            for part in inventree_parts:
                part_value = self.extract_pot_value(part['name'])
                if part_value and pot_value == part_value:
                    return part

        # Strategy 4: Fuzzy matching (only if similarity > 0.8)
        best_match = None
        best_score = 0.8  # Minimum threshold

        for part in inventree_parts:
            score = self.similarity(component_name, part['name'])
            if score > best_score:
                best_score = score
                best_match = part

        if best_match:
            return best_match

        # Strategy 5: Check if component name is contained in part name or vice versa
        for part in inventree_parts:
            part_name = part['name'].lower()
            comp_name = component_name.lower()

            # Remove common words for better matching
            clean_part = self.normalize_name(part_name)
            clean_comp = self.normalize_name(comp_name)

            if clean_comp in clean_part or clean_part in clean_comp:
                return part

        return None

    def get_all_parts(self) -> List[Dict]:
        """Get all parts from Inventree"""
        url = f"{self.base_url}/api/part/"
        params = {"active": True, "limit": 1000}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        return data if isinstance(data, list) else data.get('results', [])

    def get_parts_without_default_location(self) -> List[Dict]:
        """Get all parts that don't have a default location set"""
        all_parts = self.get_all_parts()
        return [p for p in all_parts if not p.get('default_location')]

    def load_component_locations(self) -> Dict:
        """Load component locations from JSON file"""
        with open(LOCATION_MAPPING_FILE, 'r') as f:
            return json.load(f)

    def get_location_id_from_path(self, unit: str, drawer: str, compartment: int) -> Optional[int]:
        """Get location ID from unit/drawer/compartment path"""
        # Build the expected path - match exact Inventree format
        unit_name = "Unit 1 (U1)" if unit == "U1" else "Unit 2 (U2)"
        expected_path = f"Workshop/{unit_name}/{drawer}/Compartment {compartment}"

        # Search for this location
        url = f"{self.base_url}/api/stock/location/"
        params = {"limit": 1000}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        locations = data if isinstance(data, list) else data.get('results', [])

        for loc in locations:
            if loc.get('pathstring') == expected_path:
                return loc['pk']

        return None

    def update_part_default_location(self, part_id: int, location_id: int):
        """Update a part's default stock location"""
        url = f"{self.base_url}/api/part/{part_id}/"
        payload = {"default_location": location_id}

        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()


def main():
    print("Fuzzy Location Matcher")
    print("=" * 60)

    updater = FuzzyLocationUpdater(INVENTREE_URL, API_TOKEN)

    # Get parts without default locations
    print("\n1. Finding parts without default locations...")
    parts_without_location = updater.get_parts_without_default_location()
    print(f"   Found {len(parts_without_location)} parts without default locations")

    # Load component location mapping
    print("\n2. Loading component location mapping...")
    component_locations = updater.load_component_locations()
    print(f"   Loaded {len(component_locations)} component mappings")

    # Get all parts for fuzzy matching
    print("\n3. Loading all Inventree parts for matching...")
    all_parts = updater.get_all_parts()
    print(f"   Loaded {len(all_parts)} parts from Inventree")

    # Try to match and update
    print("\n4. Attempting fuzzy matching and updates...")
    print()

    matched_count = 0
    updated_count = 0
    failed_matches = []

    for component_name, locations in component_locations.items():
        # Skip if no location data
        if not locations:
            continue

        # Get first location for this component
        first_loc = locations[0]
        unit = first_loc['unit']
        drawer = first_loc['drawer']
        compartment = first_loc['compartment']

        # Try to find matching part in Inventree
        matched_part = updater.find_best_match(component_name, parts_without_location)

        if matched_part:
            matched_count += 1
            part_name = matched_part['name']
            part_id = matched_part['pk']

            # Get location ID
            location_id = updater.get_location_id_from_path(unit, drawer, compartment)

            if location_id:
                try:
                    # Update the part's default location
                    updater.update_part_default_location(part_id, location_id)
                    updated_count += 1
                    print(f"✓ {component_name:30} → {part_name:35} @ {unit}-{drawer}-{compartment}")
                except Exception as e:
                    print(f"✗ Error updating {part_name}: {e}")
            else:
                print(f"⚠ Location not found: {unit}-{drawer}-{compartment} for {component_name}")
        else:
            # Only report failures for components that might have inventory
            failed_matches.append(component_name)

    print()
    print("=" * 60)
    print(f"✓ Matched {matched_count} components")
    print(f"✓ Updated {updated_count} default locations")

    if failed_matches:
        print(f"\n⚠ Could not match {len(failed_matches)} components:")
        for comp in failed_matches[:10]:  # Show first 10
            print(f"   - {comp}")
        if len(failed_matches) > 10:
            print(f"   ... and {len(failed_matches) - 10} more")

    print()
    print("Now run: python3 move_stock_to_locations.py")
    print("to move the actual stock items to their new locations!")


if __name__ == "__main__":
    main()
