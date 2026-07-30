# UI Design System

## Visual language

KMS DTF ERP uses premium glassmorphism in dark and light modes.

- Rounded translucent glass surfaces.
- Thin semi-transparent borders and internal highlights.
- Soft shadows and controlled violet/blue/cyan neon.
- Dark: navy, royal blue, violet, pale blue-white text.
- Light: icy white, pale blue, lavender, dark blue-grey text.
- Theme changes animate for approximately 350 ms and persist through `QSettings`.

## Navigation rail

- Fixed width: 78 px.
- Permanently collapsed; it never expands.
- No pin/unpin mode.
- Transparent 46 × 46 px icon hit areas with no coloured background boxes.
- Selected icon keeps a permanent neon glow.
- Hovered icon brightens, scales, lifts, and receives stronger temporary glow.
- One reusable glass tooltip displays only the hovered item's label.
- Bottom control toggles dark/light mode.

Current navigation:

Dashboard, Customers, Orders, Artwork Studio, Image Editor, Inventory, Purchase, Sales,
Invoices, Payments, Products, Artwork Library, Suppliers, Packing, Dispatch,
WhatsApp, Mail, AI Tools, Cloud Storage, Reports & Backup, Settings, and Users.

The Image Editor uses an unnumbered, clickable tool rail and a neutral
checkerboard canvas to indicate transparent pixels. Its canvas command bar
shows the current zoom percentage; the mouse wheel zooms and middle-button
dragging pans the canvas. The command bar also reports the source image width
and height using a selectable physical or pixel unit. Width and Height are
editable and resample the working image before it is saved.

Trim removes transparent edge pixels. When Crop is selected, Width and Height
change the canvas bounds instead of scaling the artwork, so the page can be
extended with transparency or reduced around its centre.

The canvas has two visually distinct spaces: a dark, non-image pasteboard and
checkerboard transparency constrained to the editable image bounds.

Production Studio is not a separate navigation item.

## Application shell

- Application opens maximized.
- Sidebar remains at the left; top bar contains page title and user/logout state.
- Routed content fills the workspace.
- Universal Google Drive button appears at the bottom-right and is not tied to
  Customers.
- Pages are hidden according to permissions and services enforce permissions
  again.

## Customers

### List

- Search by name, business, phone, or customer code.
- Active/inactive/all filter.
- Columns: Customer No., Customer Name, Business, Phone, Preferred Courier,
  Customer Folder.
- Row action: **Open folder**.
- Additional actions: View, Edit, Deactivate, Delete.

### Customer form

- Two-column layout: customer details and billing/shipping details.
- Delivery type: Courier or Local.
- Preferred courier: ST, Professional, DTDC, Bus, Train, or Other Transport.
- Local delivery hides courier fields.
- WhatsApp can copy phone.
- Shipping can copy billing.
- Address order: door number, street, village/city, landmark, pincode, district,
  state, country.
- Six-digit pincode lookup fills district/state while preserving village/city.
- India-only editable state completion.

### Customer file workspace

The workspace opens as a separate full-screen window. The customer list remains
preserved behind it.

```text
Folder tree | File items | Preview
```

- Both separators are adjustable.
- The folder-panel **Back** control moves from dated folders to the customer
  folder, then to the main Customers folder.
- Closing the full-screen window returns to the preserved customer list.
- **Create today's folder** creates the date exactly once.
- Date children: Design, Gangsheet, Invoice Copy, Payment Receipt.
- File actions: Upload, Open, Download, Replace/New Version.
- Queued status refreshes automatically.
- Images scale with aspect ratio using Qt image plugins.
- PDFs render with `QPdfDocument` and `QPdfView`.
- Unsupported types remain available through Open/Download.
- Uncached previews download asynchronously and cannot overwrite a newer
  selection.

## Performance rules

- Never make Backblaze or Google calls on customer creation/folder-navigation UI
  paths.
- Never block the UI while loading remote previews or synchronizing files.
- Avoid rebuilding the customer list when opening or closing the file window.
- Do not create empty date folders during navigation.

## Accessibility and consistency

- Buttons use explicit verbs.
- Destructive delete requires confirmation and may be rejected for linked data.
- Empty, queued, unavailable, and error states use visible explanatory text.
- Standard Qt focus and keyboard selection behavior must remain functional.
