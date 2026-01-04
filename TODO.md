# TODO - Future Improvements

## Hardware & Misc Organization

### Additional Drawer Unit for Hardware
**Priority:** Medium
**Status:** Planning

Consider purchasing another drawer unit (similar to U1/U2) for hardware and miscellaneous items:

**Items that need organization:**
- Knobs (organize by style and color in compartments)
  - Mini Chicken Head Knobs
  - Davies clones
  - Speed knobs
  - Pointer knobs
  - Different colors (black, white, cream, etc.)
- Battery snaps (9V, others)
- Mounting hardware (screws, nuts, washers, standoffs)
- Enclosure accessories (rubber feet, LED bezels)
- Wire and cable (hookup wire, shielded audio cable)
- Tools and consumables (solder, flux, desoldering braid)

**Proposed drawer unit options:**
1. Another AkroMills 60-drawer unit (U3) - matches existing system
2. Larger drawer unit for bulkier hardware items
3. Mixed unit with different drawer sizes for various hardware

**Benefits:**
- Keep electronic components separate from hardware
- Better organization for build sessions
- Easier inventory management
- Room for expansion as collection grows

**Next steps:**
- Measure available bench space
- Decide on drawer configuration
- Order dividers if needed
- Update label generation system to include U3

---

## n8n Automation Workflow
**Priority:** High
**Status:** Planned (see N8N_AUTOMATION_PLAN.md)

Full automation workflow for:
- BOM ingestion
- Purchase order creation
- Inventory management
- Picking sheet generation

**Estimated time:** 4-6 hours for basic workflows

---

## Label Improvements

### Add QR Codes to Labels
**Priority:** Low
**Status:** Future

Add QR codes to compartment labels that link directly to:
- Inventree part page
- Datasheet
- Stock level info

**Benefits:**
- Quick lookup via phone camera
- Faster inventory updates
- Easy access to datasheets while building

---

## Stock Management

### Low Stock Alerts
**Priority:** Medium
**Status:** Can be implemented in n8n

Automatically alert when components drop below min_quantity:
- Email notifications
- Auto-create purchase orders
- Track reorder frequency
- Suggest bulk ordering for frequently used parts

---

## Build Cost Tracking
**Priority:** Low
**Status:** Future

Track actual build costs:
- Link BOMs to purchase orders
- Calculate real component costs
- Compare DIY vs buying pre-built
- Track project profitability (if selling)

---

## Integration Ideas

### Supplier API Integration
**Priority:** Medium
**Status:** Future (n8n workflow)

- Auto-price checking (Mouser, Digikey, etc.)
- Availability monitoring
- Price comparison across suppliers
- Auto-cart generation

### BOM Import from DIY Sites
**Priority:** Low
**Status:** Future

Web scraping for automatic BOM import from:
- diyeffectspedals.com
- tagboardeffects.com
- madbeanpedals.com

---

## Current Status

✅ **Completed:**
- Label generation system
- Location tracking (compartment-level)
- Inventree integration
- Fuzzy matching for name variations
- Stock relocation automation
- Picking sheet generation
- GitHub repository

📋 **In Progress:**
- Building remaining drawer dividers (30 of 60 done)

🔮 **Planned:**
- Hardware drawer unit (U3)
- n8n automation workflow
- Additional organization improvements
