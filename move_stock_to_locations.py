#!/usr/bin/env python3
"""
Move Stock Items to Their Default Locations

This script moves all stock items to their part's default location.
Run this after update_inventree_locations.py to physically move stock
to the correct compartments.
"""

import requests
import json
from typing import Dict

# Configuration
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"

class StockMover:
    """Moves stock items to their default locations"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}

    def get_all_parts_with_default_locations(self):
        """Get all parts that have a default location set"""
        url = f"{self.base_url}/api/part/"
        params = {"active": True, "limit": 1000}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        results = data if isinstance(data, list) else data.get('results', [])

        # Filter to only parts with default_location set
        parts_with_locations = [
            p for p in results
            if p.get('default_location') is not None
        ]

        return parts_with_locations

    def get_stock_items_for_part(self, part_id: int):
        """Get all stock items for a specific part"""
        url = f"{self.base_url}/api/stock/"
        params = {"part": part_id}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        return data if isinstance(data, list) else data.get('results', [])

    def move_stock_item(self, stock_id: int, new_location_id: int):
        """Move a stock item to a new location"""
        url = f"{self.base_url}/api/stock/{stock_id}/"

        payload = {"location": new_location_id}

        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()

    def get_location_path(self, location_id: int):
        """Get the full path string for a location"""
        url = f"{self.base_url}/api/stock/location/{location_id}/"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json().get('pathstring', 'Unknown')


def main():
    print("Stock Item Location Mover")
    print("=" * 50)

    mover = StockMover(INVENTREE_URL, API_TOKEN)

    # Get all parts with default locations
    print("\nFinding parts with default locations...")
    parts = mover.get_all_parts_with_default_locations()
    print(f"  Found {len(parts)} parts with default locations set")

    # Process each part
    moved_count = 0
    already_correct = 0
    error_count = 0

    print("\nMoving stock items to their default locations...")
    print()

    for part in parts:
        part_id = part['pk']
        part_name = part['name']
        default_location = part['default_location']

        # Get stock items for this part
        stock_items = mover.get_stock_items_for_part(part_id)

        if not stock_items:
            continue  # No stock items for this part

        for stock in stock_items:
            stock_id = stock['pk']
            current_location = stock.get('location')
            quantity = stock.get('quantity', 0)

            # Check if already in correct location
            if current_location == default_location:
                already_correct += 1
                continue

            try:
                # Get location paths for display
                current_path = "No Location"
                if current_location:
                    current_path = mover.get_location_path(current_location)

                new_path = mover.get_location_path(default_location)

                # Move the stock item
                mover.move_stock_item(stock_id, default_location)
                moved_count += 1

                print(f"✓ {part_name} (Qty: {quantity})")
                print(f"  From: {current_path}")
                print(f"  To:   {new_path}")
                print()

            except Exception as e:
                print(f"✗ Error moving {part_name}: {e}")
                error_count += 1

    print("=" * 50)
    print(f"✓ Moved {moved_count} stock items")
    print(f"  Already correct: {already_correct}")
    if error_count > 0:
        print(f"  ⚠ Errors: {error_count}")
    print()
    print("Stock items are now in their compartment locations!")
    print("You can now search by location in Inventree.")


if __name__ == "__main__":
    main()
