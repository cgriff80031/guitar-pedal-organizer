#!/usr/bin/env python3
"""
Generate Picking Sheet for Guitar Pedal Build
Queries Inventree BOM and generates an organized picking list with exact locations
"""

import requests
import json
import sys
from collections import defaultdict
from typing import List, Dict, Tuple

# Configuration
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"
LOCATION_MAPPING_FILE = "component_locations.json"


class PickingSheetGenerator:
    """Generates organized picking sheets from Inventree BOMs"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}
        self.location_map = self._load_location_map()

    def _load_location_map(self) -> Dict:
        """Load the component location mapping"""
        try:
            with open(LOCATION_MAPPING_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"WARNING: Location map file '{LOCATION_MAPPING_FILE}' not found.")
            print("Run update_inventree_locations.py first to generate location data.")
            return {}

    def list_guitar_pedals(self) -> List[Dict]:
        """Get all guitar pedal projects"""
        url = f"{self.base_url}/api/part/"
        params = {"category": 45}  # Guitar Pedals category

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, list):
            return data
        return data.get('results', [])

    def get_bom(self, part_id: int) -> List[Dict]:
        """Get the BOM for a specific pedal"""
        url = f"{self.base_url}/api/bom/"
        params = {"part": part_id, "limit": 1000}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        return response.json().get('results', [])

    def get_part_details(self, part_id: int) -> Dict:
        """Get details for a specific part"""
        url = f"{self.base_url}/api/part/{part_id}/"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def get_part_location(self, part_id: int) -> str:
        """Get the storage location for a part"""
        # First try to get from part's default location
        part = self.get_part_details(part_id)

        if part.get('default_location'):
            # Get location details
            loc_id = part['default_location']
            url = f"{self.base_url}/api/stock/location/{loc_id}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            location = response.json()

            # Build full path
            return location.get('pathstring', 'Unknown')

        # Fallback to our location map
        part_name = part['name']
        for comp_value, locations in self.location_map.items():
            if comp_value in part_name or part_name in comp_value:
                if locations:
                    loc = locations[0]
                    return f"{loc['unit']}-{loc['drawer']}-{loc['compartment']}"

        return "Location Not Set"

    def generate_picking_sheet(self, pedal_name: str = None, part_id: int = None):
        """Generate a picking sheet for a specific pedal"""

        # Find the pedal
        if not part_id:
            pedals = self.list_guitar_pedals()
            if pedal_name:
                matching = [p for p in pedals if pedal_name.lower() in p['name'].lower()]
                if not matching:
                    print(f"ERROR: No pedal found matching '{pedal_name}'")
                    return
                part_id = matching[0]['pk']
                actual_name = matching[0]['name']
            else:
                print("Available pedals:")
                for i, pedal in enumerate(pedals, 1):
                    print(f"  {i}. {pedal['name']}")
                choice = int(input("\nSelect pedal number: ")) - 1
                part_id = pedals[choice]['pk']
                actual_name = pedals[choice]['name']
        else:
            part = self.get_part_details(part_id)
            actual_name = part['name']

        # Get BOM
        print(f"\nGenerating picking sheet for: {actual_name}")
        print("=" * 70)

        bom_items = self.get_bom(part_id)

        if not bom_items:
            print("No BOM items found for this pedal.")
            return

        # Group by location for efficient picking
        by_location = defaultdict(list)

        for item in bom_items:
            sub_part_id = item['sub_part']
            reference = item['reference']
            quantity = int(item['quantity'])

            # Get part details
            part = self.get_part_details(sub_part_id)
            part_name = part['name']
            location = self.get_part_location(sub_part_id)
            available = part.get('total_in_stock', 0)

            # Add to location group
            by_location[location].append({
                'reference': reference,
                'name': part_name,
                'quantity': quantity,
                'available': available,
                'location': location
            })

        # Print organized picking sheet
        print(f"\nPICKING SHEET: {actual_name}")
        print("=" * 70)
        print(f"Total BOM items: {len(bom_items)}\n")

        # Sort locations for organized picking
        sorted_locations = sorted(by_location.keys(), key=self._location_sort_key)

        for location in sorted_locations:
            items = by_location[location]

            print(f"\n📍 LOCATION: {location}")
            print("-" * 70)

            for item in items:
                qty_str = f"(x{item['quantity']})" if item['quantity'] > 1 else ""
                stock_indicator = "✓" if item['available'] >= item['quantity'] else "⚠"

                # Format: [ ] Reference: Part Name (xQty) - Stock indicator
                print(f"  [ ] {item['reference']:8} {item['name']:30} {qty_str:6} {stock_indicator}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY:")
        total_items = len(bom_items)
        total_unique_locations = len(by_location)
        items_with_stock = sum(1 for items in by_location.values()
                              for item in items if item['available'] >= item['quantity'])

        print(f"  Total items to pick: {total_items}")
        print(f"  Unique locations: {total_unique_locations}")
        print(f"  Items in stock: {items_with_stock}/{total_items}")

        if items_with_stock < total_items:
            print(f"\n  ⚠ WARNING: {total_items - items_with_stock} items need to be ordered!")

            # Show what's missing
            print("\n  Missing items:")
            for location, items in by_location.items():
                for item in items:
                    if item['available'] < item['quantity']:
                        needed = item['quantity'] - item['available']
                        print(f"    - {item['name']}: need {needed} more (have {item['available']})")

        print("\n✓ = In stock | ⚠ = Needs ordering")

    def _location_sort_key(self, location: str) -> Tuple:
        """Sort key for locations to group by unit/drawer"""
        if location == "Location Not Set":
            return (999, 999, 999)

        # Parse location like "U1-S5-2" or "Workshop/Unit 1/S5/Compartment 2"
        if '-' in location:
            parts = location.split('-')
            if len(parts) >= 3:
                unit = parts[0]
                drawer = parts[1]
                comp = parts[2]

                # Extract numbers for sorting
                unit_num = 1 if 'U1' in unit else 2
                drawer_num = int(''.join(c for c in drawer if c.isdigit()))
                comp_num = int(comp) if comp.isdigit() else 0

                return (unit_num, drawer_num, comp_num)

        return (999, 999, 999)

    def export_to_text(self, pedal_name: str, output_file: str):
        """Export picking sheet to a text file"""
        # Redirect stdout to file
        import sys
        original_stdout = sys.stdout

        with open(output_file, 'w') as f:
            sys.stdout = f
            self.generate_picking_sheet(pedal_name)
            sys.stdout = original_stdout

        print(f"\n✓ Picking sheet exported to: {output_file}")


def main():
    """Main entry point"""
    print("Guitar Pedal Picking Sheet Generator")
    print("=" * 50)

    generator = PickingSheetGenerator(INVENTREE_URL, API_TOKEN)

    # Check for command line arguments
    if len(sys.argv) > 1:
        pedal_name = ' '.join(sys.argv[1:])
        generator.generate_picking_sheet(pedal_name)
    else:
        # Interactive mode
        generator.generate_picking_sheet()


if __name__ == "__main__":
    main()
