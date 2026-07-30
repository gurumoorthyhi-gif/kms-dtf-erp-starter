# Database Schema

## Current database

The implemented desktop database is SQLite through SQLAlchemy 2. Alembic
revisions `0001` through `0021` create and evolve the schema. The database is
upgraded at application startup.

## Tables by domain

### Authentication and audit

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `activity_logs`
- `audit_records`
- `backup_history`

Passwords are versioned scrypt hashes. Roles map to permission codes. Activity and
audit records preserve accountable actions.

### Customers

- `customers`
- `customer_addresses`
- `customer_file_references`
- `customer_storage_dates`

Important customer fields include generated code, name, business, phone,
WhatsApp, delivery type, preferred courier/transport, preferred rate, email, GST,
notes, active state, stable Backblaze `storage_prefix`, and
`google_drive_folder_id`.

Addresses are unique by `(customer_id, address_type)` and contain door/street
fields through `line1`/`line2`, village/city, landmark, district, state, pincode,
and country.

`customer_storage_dates` has a unique `(customer_id, folder_date)` constraint.
This is the authoritative duplicate guard for **Create today's folder** and may
store the matching Google date-folder ID.

### Products, pricing, and orders

- `product_categories`
- `products`
- `price_rules`
- `discount_rules`
- `tax_configurations`
- `orders`
- `order_items`
- `order_status_history`

Money uses fixed-precision decimals. Order items snapshot prices/totals and status
history preserves workflow changes.

### Artwork and gangsheets

- `artworks`
- `artwork_versions`
- `artwork_approvals`
- `gang_sheets`
- `gang_sheet_items`

Artwork records reference managed storage; originals are preserved and each edit
or replacement is a version. Gangsheet geometry is stored in millimetres with
rotation and layer order.

### Production and quality

- `production_jobs`
- `production_events`
- `quality_checks`

Events preserve stage transitions, assignment, pause/reprint/wastage information,
quality results, and notes.

### Inventory and purchasing

- `inventory_items`
- `inventory_movements`
- `suppliers`
- `purchases`
- `purchase_items`

### Sales and payments

- `invoices`
- `invoice_items`
- `payments`
- `credit_notes`

### Packing and dispatch

- `packings`
- `dispatches`
- `dispatch_events`
- `customer_notification_events`

### Communications

- `communication_messages`
- `communication_attachments`
- `message_templates`

### Cloud files

- `cloud_files`

`cloud_files.object_key` is unique. Each record stores local cache path, original
name, content type, byte size, SHA-256 checksum, operation, transfer state,
retry/error information, timestamps, and optional Google Drive catalogue file ID.

Supported states include queued, failed, and synced. Folder markers use operation
`folder` and original name `.keep`; they are hidden from normal file lists.

## Migration history

| Revision | Purpose |
|---|---|
| 0001 | Authentication, roles, permissions, activity |
| 0002 | Customers and addresses |
| 0003 | Products and pricing |
| 0004 | Orders and status history |
| 0005 | Artwork library and approvals |
| 0006 | Gangsheets |
| 0007 | Production and quality |
| 0008 | Inventory, suppliers, purchases |
| 0009 | Invoices, payments, credits |
| 0010 | Packing and dispatch |
| 0011 | Cloud file queue |
| 0012 | Communications |
| 0013 | Reports, backup history, audit |
| 0014 | Customer delivery type |
| 0015 | Preferred courier/transport |
| 0016 | Address district |
| 0017 | Address landmark |
| 0018 | Customer preferred rate |
| 0019 | Google Drive catalogue file ID |
| 0020 | Stable customer storage prefix and Drive root ID |
| 0021 | Explicit customer date folders |

## Invariants

- UI code never performs database queries.
- Foreign keys are enabled for SQLite.
- Managed file paths must not be absolute or contain traversal.
- Customer codes and cloud object keys are unique.
- A customer/date folder can exist only once.
- Schema changes require a new forward Alembic revision and migration tests.

## Future hosted database

`.env.backend.example` describes planned Supabase/PostgreSQL configuration only.
No current desktop service reads it. A future migration must introduce tenants,
memberships, verified identities, synchronization cursors, conflict policies,
and server-side file authorization before the hosted backend is considered
implemented.
