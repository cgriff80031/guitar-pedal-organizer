# Guitar Pedal Component Label Generator

An automated system for generating organized component labels for guitar pedal parts storage. This system integrates with Inventree, generates labels optimized for 4x compartment drawers, and syncs exact component locations for pick list generation.

## Overview

This system solves the problem of manually maintaining component labels and tracking locations by:
1. Pulling component data from your Inventree inventory
2. Merging with common guitar pedal components (even if quantity is 0)
3. Organizing components intelligently by decade/type
4. Generating CSV files ready for printing in gLabels
5. Syncing exact compartment locations back to Inventree
6. Generating picking sheets for builds with precise drawer/compartment locations

## System Files

### Core Scripts
- **`generate_labels.py`** - Main script that generates labels from Inventree + reference data
- **`update_inventree_locations.py`** - Syncs physical drawer locations to Inventree (part default locations)
- **`update_missing_locations.py`** - Fuzzy matcher to assign locations to parts that weren't matched initially
- **`move_stock_to_locations.py`** - Moves actual stock items to their default compartment locations
- **`generate_picking_sheet.py`** - Creates pick lists from BOMs with exact locations

### Data Files
- **`guitar_pedal_components_reference.yaml`** - Reference list of common guitar pedal components
- **`akromills_labels_complete.csv`** - Generated CSV output (import into gLabels)
- **`component_locations.json`** - Component-to-location mapping (auto-generated)

### Documentation
- **`README.md`** - This file
- **`LOCATION_TRACKING_GUIDE.md`** - Detailed guide for location tracking system

## Storage Configuration

### Unit 1 (U1) - Small Drawer Unit
- **60 drawers total** (S1-S60)
- **4x compartment dividers** in each drawer
- **Layout**: `[1][2]` (front), `[3][4]` (back)
- **Contents**:
  - Resistors (grouped by decade)
  - Capacitors (grouped by type)
  - Diodes
  - Transistors (NPN, PNP, JFET, MOSFET)
  - LEDs and bezels
  - Connectors and switches
  - Heat shrink (bottom drawers S57-S60)

### Unit 2 (U2) - Mixed Drawer Unit
- **3 Large drawers** (L1-L3): 5 5/8" w × 2 1/2" h × 5 3/4" d
  - PCBs and Enclosures
- **4 Tall drawers** (T1-T4): 2 3/4" w × 2 1/2" h × 5 3/4" d
  - Available for future use
- **16 Medium drawers** (M1-M16): 2 3/4" w × 1 1/4" h × 5 3/4" d
  - **4x compartment dividers** in each medium drawer
  - ICs (op-amps, charge pumps, delay chips, etc.)
  - IC Sockets
  - Potentiometers (all types combined)

## Workflow

### 1. Generate Labels

```bash
python3 generate_labels.py
```

This creates `akromills_labels_complete.csv` with optimized component organization.

**What it does:**
- Fetches components from Inventree
- Merges with reference list
- Removes redundant type suffixes (e.g., "2N5088 NPN" → "2N5088", since label already shows "Q NPN:")
- Groups by decade/type
- Packs into 4-compartment layout
- Generates CSV for gLabels

### 2. Print Labels

1. Open gLabels
2. **File → Open**, select `akromills_labels_complete.csv`
3. In import dialog: **Select ONLY comma as delimiter** (uncheck pipe, space, etc.)
4. Print labels
5. Apply to drawers

### 3. Sync Locations to Inventree

```bash
python3 update_inventree_locations.py
```

This creates the location hierarchy in Inventree and updates each part's default location with exact compartment detail.

**Location format:** `U1-S5-2` (Unit 1, Small drawer 5, Compartment 2)

### 4. Fuzzy Match Missing Parts (Optional)

```bash
python3 update_missing_locations.py
```

If some parts weren't matched by the initial script (different naming between labels and Inventree), this uses fuzzy matching to assign locations. Handles:
- Pot naming variations (A100K, B100K, Trimpot 100K → 100K)
- Capacitor types (100nF Ceramic → 100nF)
- Component suffix variations

### 5. Move Stock to Locations

```bash
python3 move_stock_to_locations.py
```

Moves actual **stock items** from "Workshop" to their specific compartments. This is separate from setting part default locations - it physically relocates your inventory in Inventree.

**Important:** Run this AFTER assigning default locations, otherwise stock won't move.

### 6. Generate Picking Sheets

```bash
python3 generate_picking_sheet.py <bom_id>
```

Creates a picking list showing exact drawer and compartment for each component needed.

## Component Organization

### Name Abbreviations

To fit on narrow (~2") drawer labels, component names are abbreviated:

- **Resistors**: Value only (e.g., "10K", "4.7K")
- **Capacitors**: Value only (e.g., "100nF", "22uF")
- **Diodes**: Type removed (e.g., "1N4148" not "1N4148 Silicon")
- **Transistors**: Type removed (e.g., "2N5088" not "2N5088 NPN" - label prefix shows "Q NPN:")
- **ICs**: Cleaned (e.g., "TL072" not "TL072 Dual Op-Amp")
- **Pots**: All types combined, value only (e.g., "100K", "10K")

### Grouping Logic

**Resistors** - Grouped by decade:
- 0.1-10Ω, 10-100Ω, 100Ω-1KΩ, 1K-10KΩ, 10K-100KΩ, 100K-1MΩ, 1M+
- Up to 4 values per drawer (4 compartments)

**Capacitors** - Grouped by type, then value:
- Ceramic (Cer), Film, Electrolytic (Elect)
- Up to 4 values per drawer

**Diodes** - All types together, sorted by part number

**Transistors** - Separated by type (NPN, PNP, JFET, MOSFET)

**ICs** - Alphabetically sorted, 4 per U2 Medium drawer

**Potentiometers** - All types combined (Audio, Linear, Trim), 4 per U2 Medium drawer

**LEDs** - Separated by size (3mm, 5mm), 4 colors per drawer (Red, Blue, Green, Orange)

## Current Layout Summary

As of last generation:
- **U1 drawers used**: S1-S58 (2 spare!)
- **U2 Large**: L1-L2 (1 spare)
- **U2 Medium**: M1-M14 (2 spare!)
- **U2 Tall**: T1-T4 (all available for future use)

## Configuration

### Inventree Connection

Edit these variables in all three Python scripts:

```python
INVENTREE_URL = "http://192.168.1.54:8082"
API_TOKEN = "inv-310ac487a4b2c8a4a9bfc79acb4fd6595c7928f0-20251222"
```

**Security Note:** The API token is currently hardcoded in the scripts. Since this accesses a local-only Inventree instance (192.168.1.54), the token is only valid on your local network. However, best practice is to use environment variables:

```python
import os
API_TOKEN = os.getenv('INVENTREE_API_TOKEN', 'your-token-here')
```

This allows you to keep the token out of version control while still having a fallback for local use.

### Component Reference

Edit `guitar_pedal_components_reference.yaml`:

```yaml
resistors:
  min_quantity: 10
  values:
    - { value: "10K", uses: 1546, priority: 1 }
    - { value: "4.7K", uses: 823, priority: 1 }
```

- **value**: Component value
- **uses**: Number of times used in 457 analyzed guitar pedal builds
- **priority**: 1 = essential, 2 = nice to have

## Features

### Location Tracking
- Exact compartment-level tracking (front-left, front-right, back-left, back-right)
- Synced to Inventree for automated picking sheets
- Format: `U1-S35-2` = Unit 1, Small drawer 35, Compartment 2

### Automatic Deduplication
- Removes duplicate components across Inventree and reference data
- Ensures each value appears only once

### Smart Abbreviation
- Strips redundant type suffixes to fit narrow labels
- Preserves essential information in label prefix

### Picking Sheet Integration
- Query BOM from Inventree
- Generate organized pick list by location
- Shows stock status (✓ in stock, ⚠ needs ordering)

## Component Reference Data

Based on analysis of **457 DIY guitar pedal PCBs** from:
https://diyeffectspedals.com/common-diy-guitar-effects-pedal-components/

### Most Common Components

**Resistors:**
- 10K (1,546 uses) - Most common!
- 4.7K (823 uses)
- 1M (807 uses)
- 1K (721 uses)
- 100K (663 uses)

**Capacitors:**
- 100nF (949 uses)
- 1µF (742 uses)
- 10µF (568 uses)
- 100µF (395 uses)
- 22nF (372 uses)

**Transistors:**
- J201 (127 uses) - JFET
- 2N5088 (84 uses) - NPN
- BC549C (71 uses) - NPN
- 2N3904 (67 uses) - NPN
- BS170 (57 uses) - MOSFET

**ICs:**
- TL072 (257 uses) - Dual op-amp
- JRC4558 (56 uses) - Dual op-amp
- TC1044 (47 uses) - Charge pump
- L78L33 (28 uses) - 3.3V regulator

**Diodes:**
- 1N5817 (513 uses) - Schottky
- 1N4148 (449 uses) - Signal
- 1N34A (70 uses) - Germanium

## Troubleshooting

### gLabels displays data in too many columns
- Use **File → Open** instead of double-clicking CSV
- In import dialog, select **ONLY comma** as delimiter
- Uncheck all other delimiters (Tab, Space, Pipe, Semicolon)

### Blank labels in gLabels output
- This is normal - gLabels won't compact labels automatically
- Label positions are fixed on the sheet
- Empty bottom drawers create blank labels (just discard them)

### Script fails to connect to Inventree
- Check Inventree is running: `http://192.168.1.54:8082`
- Verify API token is valid
- Check network connectivity

### Missing components in output
- Ensure components are properly categorized in Inventree
- Add missing components to `guitar_pedal_components_reference.yaml`

### Location sync fails
- Run `generate_labels.py` first to create the CSV
- Check Inventree API permissions
- Verify part names match between Inventree and reference

## Tips for Manual Breadboarding

Even though decade grouping creates some sparse drawers (single resistor per drawer), Inventree location tracking makes manual lookup easy:

1. Search Inventree for "2.2K resistor"
2. See location "U1-S9-3"
3. Go directly to drawer S9, compartment 3

The exact location tracking eliminates the need to memorize organization patterns.

## Future Improvements

- Web UI for easier label generation
- QR codes on labels for quick Inventree lookup
- Barcode scanning for stock updates
- Low stock alerts based on min quantities
- Build cost estimation from BOMs

## Credits

- Component usage data: https://diyeffectspedals.com/
- Analysis based on 457 guitar pedal PCBs
- Built for organizing AkroMills drawer systems
- Inventree integration for inventory management
