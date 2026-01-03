# Location Tracking & Picking Sheets Guide

Complete system for tracking component locations and generating picking sheets for guitar pedal builds.

## Overview

This system provides:
1. **Automatic label generation** from Inventree inventory
2. **Precise location tracking** with compartment-level detail
3. **Inventree integration** to update stock locations
4. **Picking sheet generation** for efficient builds

## Compartment Layout

For 4x compartment drawers (U1 small drawers):
```
[1] [2]    (front)
[3] [4]    (back)
```

- **1** = Front-Left
- **2** = Front-Right
- **3** = Back-Left
- **4** = Back-Right

## Location Format

Examples:
- `U1-S5-2` = Unit 1, Small drawer 5, Compartment 2 (Front-Right)
- `U2-M10-1` = Unit 2, Medium drawer 10, Compartment 1 (Front-Left)
- `U2-L1` = Unit 2, Large drawer 1 (no compartments)

## Workflow

### Step 1: Generate Labels
```bash
python3 generate_labels.py
```

This creates:
- `akromills_labels_complete.csv` - Import to gLabels for printing
- Component organization with exact compartment assignments

### Step 2: Update Inventree Locations
```bash
python3 update_inventree_locations.py
```

This:
- Creates location hierarchy in Inventree:
  ```
  Workshop
    ├── Unit 1 (U1)
    │   ├── S1
    │   │   ├── Compartment 1
    │   │   ├── Compartment 2
    │   │   ├── Compartment 3
    │   │   └── Compartment 4
    │   ├── S2
    │   └── ...
    └── Unit 2 (U2)
        ├── M1
        ├── M2
        ├── L1
        └── ...
  ```
- Updates each part's default location in Inventree
- Generates `component_locations.json` - Location reference map

### Step 3: Generate Picking Sheets
```bash
# Interactive mode - select from list
python3 generate_picking_sheet.py

# Direct mode - specify pedal name
python3 generate_picking_sheet.py "Little Green Scream Machine"
```

## Example Picking Sheet

```
PICKING SHEET: Little Green Scream Machine
======================================================================
Total BOM items: 40

📍 LOCATION: U1-S5-1
----------------------------------------------------------------------
  [ ] R1       4.7K Resistor                   (x1)   ✓
  [ ] R3       4.7K Resistor                   (x1)   ✓

📍 LOCATION: U1-S7-2
----------------------------------------------------------------------
  [ ] R4       10K Resistor                    (x1)   ✓
  [ ] R5       10K Resistor                    (x1)   ✓

📍 LOCATION: U2-M1-2
----------------------------------------------------------------------
  [ ] IC1      JRC4558                         (x1)   ✓

📍 LOCATION: U1-S31-4
----------------------------------------------------------------------
  [ ] D1       1N4148 Silicon                  (x2)   ⚠

======================================================================
SUMMARY:
  Total items to pick: 40
  Unique locations: 15
  Items in stock: 38/40

  ⚠ WARNING: 2 items need to be ordered!

  Missing items:
    - 1N4148 Silicon: need 1 more (have 1)

✓ = In stock | ⚠ = Needs ordering
```

## Location Reference

The `component_locations.json` file maps each component to its location:

```json
{
  "100R": [
    {
      "unit": "U1",
      "drawer": "S1",
      "compartment": 1
    }
  ],
  "220R": [
    {
      "unit": "U1",
      "drawer": "S1",
      "compartment": 2
    }
  ],
  "TL072": [
    {
      "unit": "U2",
      "drawer": "M9",
      "compartment": 2
    }
  ]
}
```

## Current Drawer Allocation

### Unit 1 (U1) - Small Drawers with 4x Compartments
- **S1-S15**: Resistors (grouped by decade)
- **S17-S29**: Capacitors (Ceramic, Film, Electrolytic)
- **S31-S48**: Diodes, Transistors, LEDs
- **S49-S57**: Potentiometers (A, B, Trimmers)
- **S59-S70**: Connectors, Switches, Hardware

### Unit 2 (U2) - Mixed Size Drawers
- **L1-L2**: Large drawers (PCBs, Enclosures)
- **M1-M14**: Medium drawers (ICs, IC Sockets)
- **T1-T4**: Tall drawers (Reserved for future use)

## Maintenance

### When Inventory Changes
1. Run `generate_labels.py` to create updated labels
2. Print new labels in gLabels
3. Reorganize physical drawers
4. Run `update_inventree_locations.py` to sync with Inventree

### Adding New Components
1. Add to Inventree normally
2. Regenerate labels (script pulls from Inventree automatically)
3. Update locations in Inventree

### Modifying Location Assignments
Edit `generate_labels.py` to change:
- Component grouping (by decade, type, etc.)
- Drawer allocation
- Compartment assignments

Then re-run all three scripts.

## Tips for Efficient Picking

1. **Follow location order** - Picking sheet is sorted by Unit → Drawer → Compartment
2. **Use small containers** - One per location to avoid mixing
3. **Check off as you go** - Use the checkboxes
4. **Verify quantities** - Double-check against BOM before assembly
5. **Note shortages** - The sheet shows what needs ordering

## Troubleshooting

### "Part not found in Inventree"
- Check part naming matches between labels and Inventree
- Component value parsing might need adjustment
- Manually update location in Inventree UI

### "Location Not Set" in picking sheet
- Run `update_inventree_locations.py` to sync locations
- Check that `component_locations.json` exists

### Wrong compartment assignments
- Modify the label parsing logic in `update_inventree_locations.py`
- Compartments are assigned in order (left-to-right, top-to-bottom in label)

## Future Enhancements

Possible additions:
- Barcode scanning for pick verification
- Build progress tracking
- Batch picking for multiple builds
- Mobile-friendly picking sheets
- Auto-reorder when stock low
- Photo references for component locations

## Integration with Inventree Builds

When creating a build in Inventree:
1. Select your pedal project
2. Create build order
3. Generate picking sheet with this tool
4. Pick components
5. Allocate stock in Inventree
6. Complete build

## File Reference

- `generate_labels.py` - Main label generator
- `update_inventree_locations.py` - Sync locations to Inventree
- `generate_picking_sheet.py` - Create picking sheets from BOMs
- `guitar_pedal_components_reference.yaml` - Common component list
- `akromills_labels_complete.csv` - Generated labels (for gLabels)
- `component_locations.json` - Location mapping reference
- `README.md` - Main system documentation
- `LOCATION_TRACKING_GUIDE.md` - This file

## Support

For issues or questions:
- Check Inventree API is accessible: http://192.168.1.54:8082
- Verify API token is valid
- Review component naming in Inventree vs. labels
- Check location hierarchy exists in Inventree
