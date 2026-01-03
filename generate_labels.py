#!/usr/bin/env python3
"""
Guitar Pedal Component Label Generator
Queries Inventree API and generates organized labels for component storage
"""

import requests
import yaml
import csv
import re
from collections import defaultdict
from typing import List, Dict, Tuple

# Configuration
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"
REFERENCE_FILE = "guitar_pedal_components_reference.yaml"
OUTPUT_FILE = "akromills_labels_complete.csv"

# Drawer configuration
# U1 = small drawers with 4x compartments
# U2 = larger drawers (can hold bigger items or more compartments)


class InventreeClient:
    """Client for Inventree API"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}
        self.categories = {}
        self._load_categories()

    def _load_categories(self):
        """Load all categories from Inventree"""
        url = f"{self.base_url}/api/part/category/?limit=1000"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json()
        for cat in data.get('results', []):
            self.categories[cat['pk']] = cat

    def get_parts(self, category_path: str = None) -> List[Dict]:
        """Get all parts, optionally filtered by category path"""
        parts = []
        limit = 100
        offset = 0

        while True:
            url = f"{self.base_url}/api/part/?limit={limit}&offset={offset}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            batch = data.get('results', [])
            if not batch:
                break

            # Filter by category path if specified
            if category_path:
                batch = [p for p in batch
                        if self._get_category_path(p['category']).startswith(category_path)]

            parts.extend(batch)
            offset += limit

            # Check if there are more results
            if not data.get('next'):
                break

        return parts

    def _get_category_path(self, category_id: int) -> str:
        """Get the full path for a category"""
        cat = self.categories.get(category_id, {})
        return cat.get('pathstring', '')

    def get_stock_quantity(self, part_id: int) -> float:
        """Get total stock for a part"""
        url = f"{self.base_url}/api/part/{part_id}/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get('total_in_stock', 0)


class ComponentOrganizer:
    """Organizes components into drawer layouts"""

    def __init__(self, reference_file: str):
        with open(reference_file, 'r') as f:
            self.reference = yaml.safe_load(f)

    def parse_resistor_value(self, name: str) -> Tuple[float, str]:
        """
        Parse resistor value from name
        Returns (numeric_value, display_value)
        Examples: '10K Resistor' -> (10000, '10K')
                  '4.7K Resistor' -> (4700, '4.7K')
                  '100R Resistor' -> (100, '100R')
        """
        name = name.upper().replace('OHM', '').strip()

        # Match patterns like '10K', '4.7K', '100R', '1M'
        match = re.search(r'(\d+\.?\d*)\s*([KMR]?)', name)
        if not match:
            return (0, name)

        value_str, multiplier = match.groups()
        value = float(value_str)

        # Convert to ohms
        if multiplier == 'K':
            numeric_value = value * 1000
            display_value = f"{value_str}K"
        elif multiplier == 'M':
            numeric_value = value * 1000000
            display_value = f"{value_str}M"
        elif multiplier == 'R' or multiplier == '':
            numeric_value = value
            # Use R notation for values under 1K
            if value < 1000:
                display_value = f"{int(value)}R" if value == int(value) else f"{value}R"
            else:
                display_value = f"{value_str}"
        else:
            numeric_value = value
            display_value = value_str

        return (numeric_value, display_value)

    def parse_capacitor_value(self, name: str) -> Tuple[float, str, str]:
        """
        Parse capacitor value and type from name
        Returns (numeric_value_in_pF, display_value, type)
        """
        name_lower = name.lower()

        # Determine type
        cap_type = 'ceramic'
        if 'film' in name_lower:
            cap_type = 'film'
        elif 'electrolytic' in name_lower or 'elec' in name_lower:
            cap_type = 'electrolytic'

        # Match patterns like '100nF', '1uF', '22pF'
        match = re.search(r'(\d+\.?\d*)\s*([pnum]F)', name, re.IGNORECASE)
        if not match:
            return (0, name, cap_type)

        value_str, unit = match.groups()
        value = float(value_str)

        # Convert to pF
        unit_lower = unit.lower()
        if unit_lower == 'pf':
            numeric_value = value
        elif unit_lower == 'nf':
            numeric_value = value * 1000
        elif unit_lower == 'uf' or unit_lower == 'µf':
            numeric_value = value * 1000000
        else:
            numeric_value = value

        # Create display value
        if numeric_value < 1000:
            display_value = f"{int(value) if value == int(value) else value}pF"
        elif numeric_value < 1000000:
            display_value = f"{value_str}nF"
        else:
            display_value = f"{value_str}uF"

        return (numeric_value, display_value, cap_type)

    def group_resistors_by_decade(self, resistors: List[Tuple[float, str, Dict]]) -> List[List[Tuple[float, str, Dict]]]:
        """
        Group resistors by decade for 4x compartment drawers
        Each group will have up to 4 values
        """
        # Sort by value
        sorted_resistors = sorted(resistors, key=lambda x: x[0])

        # Group by decade (1-10, 10-100, 100-1K, 1K-10K, 10K-100K, 100K-1M, 1M+)
        decades = defaultdict(list)

        for value, display, data in sorted_resistors:
            if value < 10:
                decade = "0.1-10"
            elif value < 100:
                decade = "10-100"
            elif value < 1000:
                decade = "100-1K"
            elif value < 10000:
                decade = "1K-10K"
            elif value < 100000:
                decade = "10K-100K"
            elif value < 1000000:
                decade = "100K-1M"
            else:
                decade = "1M+"

            decades[decade].append((value, display, data))

        # Split each decade into groups of 4 for compartment drawers
        groups = []
        for decade in sorted(decades.keys()):
            items = decades[decade]
            # Split into groups of 4
            for i in range(0, len(items), 4):
                groups.append(items[i:i+4])

        return groups

    def group_capacitors_by_type_and_value(self, capacitors: List[Tuple[float, str, str, Dict]]) -> Dict[str, List[List[Tuple[float, str, str, Dict]]]]:
        """
        Group capacitors by type (ceramic, film, electrolytic) and then by value ranges
        Returns dict with type as key and list of groups as value
        """
        by_type = defaultdict(list)

        for value, display, cap_type, data in capacitors:
            by_type[cap_type].append((value, display, cap_type, data))

        grouped = {}
        for cap_type, items in by_type.items():
            # Sort by value
            sorted_items = sorted(items, key=lambda x: x[0])

            # Group into sets of 4 for compartment drawers
            groups = []
            for i in range(0, len(sorted_items), 4):
                groups.append(sorted_items[i:i+4])

            grouped[cap_type] = groups

        return grouped


class LabelGenerator:
    """Generates labels in gLabels CSV format"""

    def __init__(self):
        self.labels = []
        self.u1_drawer_num = 1  # Small drawers (S1, S2, ...)
        # U2 has three drawer sizes:
        # - 3 Large (L1-L3): 5 5/8" w x 2 1/2" h x 5 3/4" d
        # - 4 Tall (T1-T4): 2 3/4" w x 2 1/2" h x 5 3/4" d
        # - 16 Medium (M1-M16): 2 3/4" w x 1 1/4" h x 5 3/4" d
        self.u2_large_num = 1   # L1, L2, L3
        self.u2_tall_num = 1    # T1, T2, T3, T4
        self.u2_medium_num = 1  # M1-M16

    def add_label_pair(self, unit: str, drawer_top: str, drawer_bottom: str,
                      label_top: str, label_bottom: str):
        """Add a label pair (2 drawers per label)"""
        self.labels.append({
            'Unit': unit,
            'Bin_Top': drawer_top,
            'Bin_Bottom': drawer_bottom,
            'Label_Top': label_top,
            'Label_Bottom': label_bottom
        })

    def get_next_u1_drawer_pair(self) -> Tuple[str, str]:
        """Get next pair of U1 drawer IDs"""
        top = f"S{self.u1_drawer_num}"
        bottom = f"S{self.u1_drawer_num + 1}"
        self.u1_drawer_num += 2
        return (top, bottom)

    def get_next_u2_large_pair(self) -> Tuple[str, str]:
        """Get next pair of U2 Large drawer IDs (L1-L3)"""
        top = f"L{self.u2_large_num}"
        bottom = f"L{self.u2_large_num + 1}" if self.u2_large_num + 1 <= 3 else ""
        if bottom:
            self.u2_large_num += 2
        else:
            self.u2_large_num += 1
        return (top, bottom)

    def get_next_u2_tall_pair(self) -> Tuple[str, str]:
        """Get next pair of U2 Tall drawer IDs (T1-T4)"""
        top = f"T{self.u2_tall_num}"
        bottom = f"T{self.u2_tall_num + 1}" if self.u2_tall_num + 1 <= 4 else ""
        if bottom:
            self.u2_tall_num += 2
        else:
            self.u2_tall_num += 1
        return (top, bottom)

    def get_next_u2_medium_pair(self) -> Tuple[str, str]:
        """Get next pair of U2 Medium drawer IDs (M1-M16)"""
        top = f"M{self.u2_medium_num}"
        bottom = f"M{self.u2_medium_num + 1}" if self.u2_medium_num + 1 <= 16 else ""
        if bottom:
            self.u2_medium_num += 2
        else:
            self.u2_medium_num += 1
        return (top, bottom)

    def format_4x_compartment_label(self, items: List[str]) -> str:
        """Format label for 4x compartment drawer"""
        # Join with  |  separator
        return "  |  ".join(items)

    def write_csv(self, filename: str):
        """Write labels to CSV file"""
        with open(filename, 'w', newline='') as f:
            # Use standard writer instead of DictWriter for simpler formatting
            writer = csv.writer(f)

            # Write header
            writer.writerow(['Unit', 'Bin_Top', 'Bin_Bottom', 'Label_Top', 'Label_Bottom',
                           '', '', '', '', '', '', ''])

            # Write data
            for label in self.labels:
                writer.writerow([
                    label['Unit'],
                    label['Bin_Top'],
                    label['Bin_Bottom'],
                    label['Label_Top'],
                    label['Label_Bottom'],
                    '', '', '', '', '', '', ''  # Empty columns
                ])


def main():
    """Main function"""
    print("Guitar Pedal Component Label Generator")
    print("=" * 50)

    # Initialize clients
    print("Connecting to Inventree...")
    inventree = InventreeClient(INVENTREE_URL, API_TOKEN)

    print("Loading component reference data...")
    organizer = ComponentOrganizer(REFERENCE_FILE)

    print("Fetching parts from Inventree...")
    all_parts = inventree.get_parts()
    print(f"Found {len(all_parts)} parts in Inventree")

    # Initialize label generator
    generator = LabelGenerator()

    # Process resistors
    print("\nProcessing resistors...")
    resistors = []
    resistor_parts = [p for p in all_parts if 'resistor' in p['name'].lower()]

    for part in resistor_parts:
        value, display = organizer.parse_resistor_value(part['name'])
        if value > 0:
            resistors.append((value, display, part))

    print(f"  Found {len(resistors)} resistor values")

    # Add common resistors from reference if not in inventory
    ref_resistors = organizer.reference['resistors']['values']
    for ref in ref_resistors:
        # Check if we already have this value
        ref_value_clean = ref['value'].replace('R', 'Ω').replace('Ω', '')
        found = False
        for _, display, _ in resistors:
            if ref['value'] == display or ref_value_clean in display:
                found = True
                break

        if not found:
            # Parse the reference value
            value, display = organizer.parse_resistor_value(ref['value'] + ' Resistor')
            resistors.append((value, display, {'name': f"{display} Resistor", 'total_in_stock': 0}))

    # Deduplicate resistors by display value
    seen_displays = set()
    resistors_deduped = []
    for value, display, part in resistors:
        if display not in seen_displays:
            seen_displays.add(display)
            resistors_deduped.append((value, display, part))
    resistors = resistors_deduped
    print(f"  After deduplication: {len(resistors)} unique resistor values")

    # Group resistors by decade
    resistor_groups = organizer.group_resistors_by_decade(resistors)
    print(f"  Organized into {len(resistor_groups)} drawer groups")

    # Generate resistor labels (U1 small drawers with 4x compartments)
    # Each group = one drawer (up to 4 values)
    # Pair groups together for top/bottom labels (2 drawers per physical label)
    for i in range(0, len(resistor_groups), 2):
        top_group = resistor_groups[i]
        bottom_group = resistor_groups[i+1] if i+1 < len(resistor_groups) else None

        if len(top_group) == 0:
            continue

        top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()

        # Top label (one group = one drawer)
        top_items = [display for _, display, _ in top_group]
        top_label = generator.format_4x_compartment_label(top_items)

        # Bottom label (if we have another group)
        if bottom_group and len(bottom_group) > 0:
            bottom_items = [display for _, display, _ in bottom_group]
            bottom_label = generator.format_4x_compartment_label(bottom_items)
        else:
            bottom_drawer = ""
            bottom_label = ""

        generator.add_label_pair("U1", top_drawer, bottom_drawer,
                               f"R: {top_label}",
                               f"R: {bottom_label}" if bottom_label else "")

    # Process capacitors
    print("\nProcessing capacitors...")
    capacitors = []
    cap_parts = [p for p in all_parts if 'capacitor' in p['name'].lower() or 'cap' in p['name'].lower()]

    for part in cap_parts:
        value, display, cap_type = organizer.parse_capacitor_value(part['name'])
        if value > 0:
            capacitors.append((value, display, cap_type, part))

    print(f"  Found {len(capacitors)} capacitor values")

    # Add common capacitors from reference
    for cap_type in ['ceramic', 'film', 'electrolytic']:
        ref_caps = organizer.reference['capacitors'][cap_type]['values']
        for ref in ref_caps:
            # Check if we already have this value
            found = any(display == ref['value'] for _, display, _, _ in capacitors)
            if not found:
                value, display, _ = organizer.parse_capacitor_value(ref['value'] + ' Capacitor')
                capacitors.append((value, display, cap_type,
                                 {'name': f"{display} {cap_type.title()} Capacitor",
                                  'total_in_stock': 0}))

    # Deduplicate capacitors by display value and type
    seen_caps = set()
    capacitors_deduped = []
    for value, display, cap_type, part in capacitors:
        key = (display, cap_type)
        if key not in seen_caps:
            seen_caps.add(key)
            capacitors_deduped.append((value, display, cap_type, part))
    capacitors = capacitors_deduped
    print(f"  After deduplication: {len(capacitors)} unique capacitor values")

    # Group capacitors
    cap_groups = organizer.group_capacitors_by_type_and_value(capacitors)

    # Generate capacitor labels
    for cap_type in ['ceramic', 'film', 'electrolytic']:
        if cap_type not in cap_groups:
            continue

        groups = cap_groups[cap_type]
        print(f"  {cap_type.title()}: {len(groups)} drawer groups")

        type_abbrev = {
            'ceramic': 'Cer',
            'film': 'Film',
            'electrolytic': 'Elect'
        }[cap_type]

        # Generate labels for this type
        for i in range(0, len(groups), 2):
            top_group = groups[i]
            bottom_group = groups[i+1] if i+1 < len(groups) else []

            top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()

            top_items = [display for _, display, _, _ in top_group]
            top_label = generator.format_4x_compartment_label(top_items)

            if bottom_group:
                bottom_items = [display for _, display, _, _ in bottom_group]
                bottom_label = generator.format_4x_compartment_label(bottom_items)
            else:
                bottom_drawer = ""
                bottom_label = ""

            generator.add_label_pair("U1", top_drawer, bottom_drawer,
                                   f"Caps {type_abbrev}: {top_label}",
                                   f"Caps {type_abbrev}: {bottom_label}" if bottom_label else "")

    # Clean diode names - remove verbose type suffixes
    def clean_diode_name(name):
        # Remove common suffixes to save space on labels
        name = name.replace(' Rectifier', '').replace(' Germanium', '').replace(' Silicon', '')
        name = name.replace(' Schottky', '').replace(' Zener Diode', '').replace(' Zener', '')
        name = name.replace(' Diode', '').replace(' Germanium Diode', '')
        return name.strip()

    # Process diodes
    print("\nProcessing diodes...")
    diode_parts = [p for p in all_parts if 'diode' in inventree._get_category_path(p['category']).lower()]

    # Add LEDs
    led_parts = [p for p in all_parts if 'led' in p['name'].lower()]

    diode_labels = []
    for part in diode_parts:
        if 'led' not in part['name'].lower():  # Skip LEDs, handle separately
            diode_labels.append(clean_diode_name(part['name']))

    # Add common diodes from reference (skip LEDs)
    ref_diodes = organizer.reference['diodes']['values']
    for ref in ref_diodes:
        if 'led' not in ref['type'].lower():  # Skip LEDs, handle separately
            clean_ref = clean_diode_name(ref['type'])
            if not any(clean_ref.lower() in label.lower() for label in diode_labels):
                diode_labels.append(clean_ref)

    # Group diodes into 4x compartments
    diode_groups = [diode_labels[i:i+4] for i in range(0, len(diode_labels), 4)]

    for i in range(0, len(diode_groups), 2):
        top_group = diode_groups[i]
        bottom_group = diode_groups[i+1] if i+1 < len(diode_groups) else []

        top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()

        top_label = generator.format_4x_compartment_label(top_group)
        bottom_label = generator.format_4x_compartment_label(bottom_group) if bottom_group else ""

        generator.add_label_pair("U1", top_drawer, bottom_drawer if bottom_group else "",
                               f"Diodes: {top_label}",
                               f"Diodes: {bottom_label}" if bottom_label else "")

    # Clean transistor names - remove redundant type suffixes
    def clean_transistor_name(name):
        # Remove type suffixes since we already label by type (Q NPN:, Q PNP:, etc.)
        name = name.replace(' NPN', '').replace(' PNP', '').replace(' JFET', '').replace(' MOSFET', '')
        return name.strip()

    # Process transistors (use U1 small drawers)
    print("\nProcessing transistors...")
    transistor_parts = [p for p in all_parts if 'transistor' in inventree._get_category_path(p['category']).lower()]

    trans_by_type = defaultdict(list)
    for part in transistor_parts:
        path = inventree._get_category_path(part['category'])
        clean_name = clean_transistor_name(part['name'])
        if 'jfet' in path.lower():
            trans_by_type['JFET'].append(clean_name)
        elif 'npn' in path.lower():
            trans_by_type['NPN'].append(clean_name)
        elif 'pnp' in path.lower():
            trans_by_type['PNP'].append(clean_name)
        elif 'mosfet' in path.lower():
            trans_by_type['MOSFET'].append(clean_name)

    # Add reference transistors
    for trans_type, ref_key in [('JFET', 'jfet'), ('NPN', 'npn'), ('PNP', 'pnp'), ('MOSFET', 'mosfet')]:
        if ref_key in organizer.reference['transistors']:
            for ref in organizer.reference['transistors'][ref_key]['values']:
                clean_ref = clean_transistor_name(ref['type'])
                if not any(clean_ref.lower() in t.lower() for t in trans_by_type[trans_type]):
                    trans_by_type[trans_type].append(clean_ref)

    # Generate transistor labels
    for trans_type, parts in trans_by_type.items():
        groups = [parts[i:i+4] for i in range(0, len(parts), 4)]

        for i in range(0, len(groups), 2):
            top_group = groups[i]
            bottom_group = groups[i+1] if i+1 < len(groups) else []

            top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()

            top_label = generator.format_4x_compartment_label(top_group)
            bottom_label = generator.format_4x_compartment_label(bottom_group) if bottom_group else ""

            generator.add_label_pair("U1", top_drawer, bottom_drawer if bottom_group else "",
                                   f"Q {trans_type}: {top_label}",
                                   f"Q {trans_type}: {bottom_label}" if bottom_label else "")

    # Process ICs (use U2 Medium drawers)
    print("\nProcessing ICs...")
    # Filter for actual ICs, not capacitors - check category path starts with "ICs/" or "Active/ICs"
    ic_parts = [p for p in all_parts
                if inventree._get_category_path(p['category']).startswith('ICs') or
                   inventree._get_category_path(p['category']).startswith('Active/ICs')]

    # Clean IC names - remove verbose suffixes
    def clean_ic_name(name):
        # Remove common suffixes to save space
        name = name.replace(' Dual Op-Amp', '').replace(' Quad Op-Amp', '').replace(' Single Op-Amp', '')
        name = name.replace(' Op-Amp', '').replace(' IC', '').replace(' Charge Pump', '')
        name = name.replace(' Regulator', '').replace(' Audio Amp', '').replace(' Hex Inverter', '')
        name = name.replace(' Delay', '').replace(' EEPROM', '').replace(' DSP', '')
        return name.strip()

    ic_labels = [clean_ic_name(p['name']) for p in ic_parts]

    # Add reference ICs
    for ref in organizer.reference['ics']['values']:
        if not any(ref['type'].lower() in label.lower() for label in ic_labels):
            ic_labels.append(ref['type'])

    # Deduplicate ICs
    ic_labels = list(set(ic_labels))
    ic_labels.sort()

    print(f"  Found {len(ic_labels)} unique ICs")

    # Group ICs (4 per drawer for medium drawers with 4x compartments)
    ic_groups = [ic_labels[i:i+4] for i in range(0, len(ic_labels), 4)]

    for i in range(0, len(ic_groups), 2):
        top_group = ic_groups[i]
        bottom_group = ic_groups[i+1] if i+1 < len(ic_groups) else []

        top_drawer, bottom_drawer = generator.get_next_u2_medium_pair()

        top_label = generator.format_4x_compartment_label(top_group)
        bottom_label = generator.format_4x_compartment_label(bottom_group) if bottom_group else ""

        generator.add_label_pair("U2", top_drawer, bottom_drawer if bottom_group else "",
                               f"IC: {top_label}",
                               f"IC: {bottom_label}" if bottom_label else "")

    # IC Sockets (use U2 Medium drawer)
    socket_types = ["8-pin", "14-pin", "16-pin"]
    top_drawer, bottom_drawer = generator.get_next_u2_medium_pair()
    socket_label = generator.format_4x_compartment_label(socket_types)
    generator.add_label_pair("U2", top_drawer, "", f"IC Socket: {socket_label}", "")

    # Process potentiometers (use U2 Medium drawers)
    print("\nProcessing potentiometers...")
    pot_parts = [p for p in all_parts if 'pot' in p['name'].lower() or 'potentiometer' in p['name'].lower()]

    # Filter out accessories (nuts, washers, dust seals, etc.)
    pot_accessories_keywords = ['nut', 'washer', 'dust', 'seal', 'knob', 'cap', 'shaft']

    pots_by_type = defaultdict(list)
    for part in pot_parts:
        name = part['name']

        # Skip accessories
        if any(keyword in name.lower() for keyword in pot_accessories_keywords):
            continue

        if 'trim' in name.lower():
            # Extract value only for trim pots
            match = re.search(r'(\d+\.?\d*)\s*([KM]?)', name)
            if match:
                value, mult = match.groups()
                display = f"{value}{mult}" if mult else value
                pots_by_type['Trim Pots'].append(display)
        elif name.startswith('A') or name.startswith('C') or name.startswith('W'):
            # Extract value only (remove "A100K Pot" -> "100K")
            match = re.search(r'[ACW]?(\d+\.?\d*[KM]?)', name)
            if match:
                value = match.group(1)
                pots_by_type['Pots A'].append(value)
        elif name.startswith('B'):
            # Extract value only (remove "B100K Pot" -> "100K")
            match = re.search(r'B?(\d+\.?\d*[KM]?)', name)
            if match:
                value = match.group(1)
                pots_by_type['Pots B'].append(value)

    # Add reference pots (just values, no prefixes)
    for pot_type, pot_list in [('audio_log', 'Pots A'), ('linear', 'Pots B')]:
        for ref in organizer.reference['potentiometers'][pot_type]['values']:
            # Extract just the value from reference (A100K -> 100K)
            ref_value = ref['value'].replace('A', '').replace('B', '').replace('C', '').replace('W', '')
            if not any(ref_value.lower() in p.lower() for p in pots_by_type[pot_list]):
                pots_by_type[pot_list].append(ref_value)

    # Add trim pots from reference
    for ref in organizer.reference['potentiometers']['trimmers']['values']:
        if not any(ref['value'].lower() in p.lower() for p in pots_by_type['Trim Pots']):
            pots_by_type['Trim Pots'].append(ref['value'])

    # Generate pot labels (use U2 Medium drawers with 4x compartments)
    # Consolidate ALL pots together (A, B, Trim) to minimize drawer usage
    all_pots_values = []

    # Collect all unique pot values regardless of type
    for pot_type in ['Pots A', 'Pots B', 'Trim Pots']:
        if pot_type in pots_by_type:
            all_pots_values.extend(pots_by_type[pot_type])

    # Deduplicate and sort
    all_pots_values = sorted(list(set(all_pots_values)))

    # Group into 4x compartments for U2 Medium drawers
    pot_groups = [all_pots_values[i:i+4] for i in range(0, len(all_pots_values), 4)]

    for i in range(0, len(pot_groups), 2):
        top_group = pot_groups[i]
        bottom_group = pot_groups[i+1] if i+1 < len(pot_groups) else []

        top_drawer, bottom_drawer = generator.get_next_u2_medium_pair()

        top_label = "  |  ".join(top_group)
        bottom_label = "  |  ".join(bottom_group) if bottom_group else ""

        generator.add_label_pair("U2", top_drawer, bottom_drawer if bottom_group else "",
                               f"Pots: {top_label}",
                               f"Pots: {bottom_label}" if bottom_label else "")

    # LEDs
    print("\nProcessing LEDs...")
    led_colors = ["Red", "Blue", "Green", "Orange"]

    # LEDs - 3mm and 5mm
    top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()
    led_3mm = [f"{color}" for color in led_colors]
    led_5mm = [f"{color}" for color in led_colors]

    generator.add_label_pair("U1", top_drawer, bottom_drawer,
                           f"LEDs 3mm: {generator.format_4x_compartment_label(led_3mm)}",
                           f"LEDs 5mm: {generator.format_4x_compartment_label(led_5mm)}")

    # LED Bezels
    top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()
    bezels = ["3mm", "5mm", "Spacers"]
    generator.add_label_pair("U1", top_drawer, "",
                           f"LED Bezels: {generator.format_4x_compartment_label(bezels)}", "")

    # Connectors
    print("\nProcessing connectors...")
    top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()
    generator.add_label_pair("U1", top_drawer, bottom_drawer,
                           '1/4" Jacks: Mono | Stereo',
                           'DC Jacks: 2.1PNL  |  2.5PNL  | 2.1PCB  | 2.5PCB')

    # Switches
    print("\nProcessing switches...")
    top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()
    generator.add_label_pair("U1", top_drawer, "",
                           "Switches: 3PDT  |  SPDT", "")

    # Heat shrink (use U1 drawers at the end)
    print("\nProcessing heat shrink...")
    heat_shrink_sizes = ['3/32"', '1/8"', '3/16"', '1/4"', '3/8"', '1/2"', '3/4"']
    hs_groups = [heat_shrink_sizes[i:i+2] for i in range(0, len(heat_shrink_sizes), 2)]

    for i in range(0, len(hs_groups), 2):
        top_group = hs_groups[i]
        bottom_group = hs_groups[i+1] if i+1 < len(hs_groups) else []

        top_drawer, bottom_drawer = generator.get_next_u1_drawer_pair()

        top_label = " | ".join(top_group)
        bottom_label = " | ".join(bottom_group) if bottom_group else ""

        generator.add_label_pair("U1", top_drawer, bottom_drawer if bottom_group else "",
                               f'H-shrink-4x: {top_label}',
                               f'H-shrink-4x: {bottom_label}' if bottom_label else "")

    # PCBs and Enclosures (use U2 Large drawers - they're big!)
    print("\nProcessing PCBs and enclosures...")
    top_drawer, bottom_drawer = generator.get_next_u2_large_pair()
    generator.add_label_pair("U2", top_drawer, bottom_drawer, "PCBs", "Enclosures")

    # Write output
    print(f"\nGenerating {len(generator.labels)} labels...")
    generator.write_csv(OUTPUT_FILE)

    print(f"\n✓ Labels written to: {OUTPUT_FILE}")
    print(f"  Total labels: {len(generator.labels)}")
    print(f"  U1 drawers used: S1-S{generator.u1_drawer_num-1}")
    print(f"  U2 Large drawers used: L1-L{generator.u2_large_num-1}")
    print(f"  U2 Medium drawers used: M1-M{generator.u2_medium_num-1}")
    if generator.u2_medium_num > 17:
        print(f"  WARNING: Using {generator.u2_medium_num-1} medium drawers but only 16 available!")
    print("\nImport this CSV into gLabels to print your labels!")


if __name__ == "__main__":
    main()
