# n8n Automation Workflow Plan

Future enhancement to automate the entire component management workflow using n8n.

## Vision

Streamline the entire process from "I want to build this pedal" to "here's your picking sheet" with minimal manual intervention.

## Setup Steps

### 1. n8n Container Setup

```bash
# Create docker-compose.yml for n8n
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  --network inventree_network \
  n8nio/n8n

# Or use docker-compose with persistence
```

**Requirements:**
- Docker/Podman installed
- Same network as Inventree container (for API access)
- Persistent volume for n8n data
- Port 5678 exposed for web UI

### 2. Inventree API Integration

**Setup n8n HTTP Request nodes for:**
- Query parts inventory
- Create/update BOMs
- Update stock locations
- Generate picking lists

**Credentials needed:**
- Inventree URL: `http://192.168.1.54:8082`
- API Token (same as current scripts)

### 3. File Monitoring Setup

**Options:**
- Watch a specific folder for BOM files (CSV/JSON)
- Monitor Inventree webhooks for new BOMs
- Email integration (forward BOM emails to n8n)

## Proposed Workflows

### Workflow 1: New Pedal BOM Ingestion

**Trigger:** BOM file added to watched folder or uploaded via webhook

**Steps:**
1. **Parse BOM**
   - Read CSV/JSON file
   - Extract component list with quantities
   - Normalize component names

2. **Inventory Check**
   - Query Inventree for each component
   - Check current stock levels
   - Compare against required quantities

3. **Generate Shopping List**
   - List components that need ordering
   - Include components below min_quantity threshold
   - Output to CSV or Inventree BOM

4. **Create Purchase Order in Inventree**
   - Create PO for missing/low stock components
   - Set status to "Pending" for review
   - Group components by supplier (Mouser, Digikey, etc.)
   - Calculate order quantities (required + min_quantity buffer)

5. **Create Build BOM in Inventree**
   - Create new BOM entry
   - Associate components with quantities
   - Tag with pedal name/project
   - Link to related Purchase Order

6. **Notification**
   - Send email/notification with shopping list
   - Link to Inventree Purchase Order for approval
   - Link to Inventree BOM
   - Summary of what's in stock vs. needs ordering
   - Estimated order cost (if supplier API available)

### Workflow 2: Component Restocking

**Trigger:** Stock level update in Inventree (webhook or scheduled check)

**Steps:**
1. **Check for New Components**
   - Compare current inventory to last label generation
   - Identify newly added component types

2. **Regenerate Labels**
   - Run `generate_labels.py` script
   - Only if new components detected

3. **Update Locations**
   - Run `update_inventree_locations.py`
   - Sync new component locations

4. **Generate Reorganization Report**
   - List drawers that need new labels
   - Highlight what changed since last run

### Workflow 3: Build Preparation

**Trigger:** User requests picking sheet (webhook/button in n8n dashboard)

**Steps:**
1. **Check Stock Availability**
   - Query Inventree for BOM components
   - Flag any out-of-stock items

2. **Generate Picking Sheet**
   - Run `generate_picking_sheet.py <bom_id>`
   - Format for printing or mobile display

3. **Optional: Reserve Stock**
   - Mark components as "allocated" in Inventree
   - Prevent double-booking for multiple builds

4. **Send to User**
   - Email PDF picking sheet
   - Push to mobile app/dashboard
   - Print directly to network printer

### Workflow 4: Purchase Order Management

**Trigger:** Purchase Order marked as "Received" in Inventree

**Steps:**
1. **Receive Stock**
   - Update stock quantities in Inventree
   - Assign to default locations from component_locations.json

2. **Check for New Component Types**
   - Identify if any received components are new to inventory
   - Trigger label regeneration if needed

3. **Update Location Tracking**
   - Run `update_inventree_locations.py` for new components
   - Verify all components have assigned locations

4. **Mark Build BOMs as Ready**
   - Check if any pending builds now have all required components
   - Send notification when build is ready to start

5. **Generate Restock Report**
   - List what was received
   - Updated stock levels
   - Which builds are now ready

### Workflow 5: Post-Build Inventory Update

**Trigger:** Build marked as complete in Inventree

**Steps:**
1. **Deduct Components**
   - Subtract used quantities from stock
   - Update Inventree stock levels

2. **Check Min Quantities**
   - Compare remaining stock vs. min_quantity
   - Generate reorder list if below threshold
   - Auto-create Purchase Order if enabled

3. **Update Build History**
   - Track which components are used most
   - Suggest bulk ordering for frequently used parts

4. **Trigger Reordering if Needed**
   - If components below min_quantity, create PO
   - Group reorders by supplier
   - Set to "Pending" for approval

## n8n Workflow Ideas

### Advanced Automation Ideas

1. **Auto-Shopping List to Suppliers**
   - Parse shopping list from Purchase Order
   - Look up prices from Mouser/Digikey APIs
   - Check component availability and lead times
   - Generate cart links or auto-order (with approval)
   - Update PO with pricing information
   - Calculate total cost including shipping

2. **Supplier Price Comparison**
   - Query multiple suppliers (Mouser, Digikey, Arrow, etc.)
   - Compare prices for same components
   - Suggest optimal supplier mix for lowest total cost
   - Factor in shipping costs and minimum order quantities
   - Update Purchase Order with best pricing

3. **BOM Import from DIY Sites**
   - Scrape BOM from diyeffectspedals.com, tagboardeffects.com
   - Parse into Inventree format
   - Trigger inventory check workflow

4. **Label Printing Automation**
   - Detect when `akromills_labels_complete.csv` changes
   - Auto-import to gLabels
   - Send to network printer (if supported)

5. **Low Stock Alerts**
   - Scheduled daily check
   - Email/SMS when critical components below min_quantity
   - Auto-create Purchase Orders for reordering
   - Include suggested order quantities

6. **Build Cost Estimation**
   - Calculate total cost from BOM + current inventory prices
   - Compare DIY cost vs. buying pre-built
   - Track project costs over time
   - Factor in Purchase Order pricing data

## Integration Points

### With Existing Scripts

```javascript
// n8n Execute Command node examples

// Generate labels
{
  "command": "python3",
  "args": ["/path/to/generate_labels.py"]
}

// Update locations
{
  "command": "python3",
  "args": ["/path/to/update_inventree_locations.py"]
}

// Generate picking sheet
{
  "command": "python3",
  "args": ["/path/to/generate_picking_sheet.py", "{{ $json.bom_id }}"]
}
```

### With Inventree API

```javascript
// Example n8n HTTP Request node for Inventree

// Get BOM
GET http://192.168.1.54:8082/api/bom/{{ $json.bom_id }}/
Headers: { "Authorization": "Token YOUR_TOKEN" }

// Update stock location
PATCH http://192.168.1.54:8082/api/part/{{ $json.part_id }}/
Body: { "default_location": {{ $json.location_id }} }

// Check stock level
GET http://192.168.1.54:8082/api/stock/?part={{ $json.part_id }}
```

## File Structure for Automation

```
/automation/
  ├── watched_boms/          # Drop BOM files here
  ├── shopping_lists/        # Generated shopping lists
  ├── picking_sheets/        # Generated picking sheets
  ├── labels/                # Generated label CSVs
  └── logs/                  # Automation logs
```

## Configuration File for n8n

Create `n8n_config.json`:

```json
{
  "inventree": {
    "url": "http://192.168.1.54:8082",
    "token_env": "INVENTREE_API_TOKEN"
  },
  "paths": {
    "scripts": "/home/cgriffis/Dropbox/Guitar_Pedals/Organiation_Labels",
    "bom_watch": "/automation/watched_boms",
    "output": "/automation/output"
  },
  "notifications": {
    "email": "your-email@example.com",
    "smtp_server": "smtp.gmail.com"
  },
  "settings": {
    "auto_regenerate_labels": true,
    "auto_sync_locations": true,
    "min_stock_alert_enabled": true
  }
}
```

## Dashboard Concept

Create an n8n webhook-based dashboard showing:

- **Current Inventory Status**
  - Total components
  - Low stock warnings
  - Last label generation date

- **Quick Actions**
  - Upload BOM
  - Generate Picking Sheet
  - Regenerate All Labels
  - View Shopping List

- **Recent Activity**
  - Latest BOM imports
  - Recent builds
  - Stock updates

## Implementation Priority

### Phase 1 (Essential)
1. Set up n8n container
2. Create BOM ingestion workflow
3. Create picking sheet generation workflow

### Phase 2 (Nice to Have)
4. Automated label regeneration on new components
5. Low stock alerts
6. Shopping list generation

### Phase 3 (Advanced)
7. Supplier API integration
8. Build cost tracking
9. Web scraping for BOMs
10. Dashboard UI

## Testing Plan

1. **Test with sample BOM**
   - Use a known pedal BOM (e.g., Tube Screamer clone)
   - Verify component parsing
   - Check inventory matching

2. **Test label regeneration**
   - Add a new component to Inventree
   - Trigger automation
   - Verify label CSV is updated

3. **Test picking sheet**
   - Select existing BOM in Inventree
   - Generate picking sheet via n8n
   - Verify locations are accurate

## Security Considerations

- Store API token in n8n credentials vault (not in workflows)
- Use environment variables for sensitive data
- Restrict n8n container network access to Inventree only
- Enable n8n authentication for webhook endpoints
- Regular backups of n8n workflow definitions

## Resources Needed

- Docker/Podman installed
- ~500MB disk space for n8n container
- Network connectivity to Inventree
- (Optional) SMTP server for email notifications
- (Optional) Mobile app for notifications (Pushover, Telegram, etc.)

## Next Steps

When ready to implement:

1. Install n8n container
2. Access UI at http://localhost:5678
3. Import starter workflow templates
4. Configure Inventree credentials
5. Test with sample BOM file
6. Iterate and expand workflows

## Notes

- This automation layer doesn't replace the existing Python scripts
- Scripts remain the core logic; n8n orchestrates them
- Can run workflows manually or automatically
- Easy to disable/modify individual workflows without breaking the system
- n8n visual workflow editor makes it easy to maintain and extend

---

**Status:** Planning phase
**Target Start:** TBD
**Estimated Setup Time:** 4-6 hours for basic workflows
**Maintenance:** Low (once configured)
