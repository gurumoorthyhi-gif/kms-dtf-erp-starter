# KMS DTF ERP Requirements

Status: current implemented baseline plus explicitly identified future work.

## 1. Platform

- Windows 10/11 x64 desktop application.
- Python 3.12 and PySide6/Qt Widgets.
- Maximized startup.
- Local-first operation using SQLite.
- Alembic-controlled forward schema migrations.

## 2. Users, roles, and authentication

- Owner/administrator and multiple employees.
- Role-based module permissions enforced below the UI layer.
- Secure password hashing and activity records.
- Development login bypass is allowed only when `APP_ENV=development`.
- Future requirement: verified email identity and universal multi-device account
  management through a hosted backend.

## 3. Customers

- Workflow order begins with Dashboard then Customers.
- Generated customer code:
  - Local: `LO` + shared four-digit sequence.
  - Courier: `CO` + shared four-digit sequence.
- Customer table columns: customer number, name, business, phone, preferred
  courier, and customer folder action.
- Capture phone, WhatsApp, email, GST, preferred rate, delivery type, courier or
  transport, notes, billing address, and shipping address.
- Indian state completion and pincode-driven district/state lookup.
- Billing and shipping use door number, street, village/city, landmark, pincode,
  district, state, and country.
- Support create, edit, view, deactivate, and guarded permanent delete.

## 4. Customer file workspace

- **Open folder** launches a separate full-screen file window; the existing
  customer list, search, and status filter remain preserved behind it.
- The folder panel provides stepwise upward navigation: dated work folders →
  customer folder → main Customers folder.
- Adjustable pane order: Folder tree → Items → Preview.
- Customer creation creates only the stable customer root.
- A date hierarchy is created only through **Create today's folder**.
- Duplicate date creation must alert and stop before any cloud calls.
- Every date contains Design, Gangsheet, Invoice Copy, and Payment Receipt.
- Support upload, secure open, download, and replacement/new-version upload.
- Preview PNG, JPEG, TIFF, BMP, WebP, GIF, and other Qt-supported images.
- Preview PDFs with the embedded Qt PDF viewer.
- Fetch uncached previews from Backblaze without blocking the UI.

## 5. Products, pricing, orders, and artwork

- Configurable products, categories, price rules, discounts, and tax.
- Multi-item orders with calculated totals, advance, balance, and status history.
- Managed artwork originals, previews, versions, metadata, and approvals.
- Artwork Studio edits remain non-destructive.
- Gangsheet layouts use millimetres and deterministic high-resolution export.

## 6. Operations

- Production jobs, ordered stages, events, reprints, wastage, and quality checks.
- Inventory, movements, low-stock warnings, suppliers, purchases, and receipts.
- Quotations/sales, invoices, payments, credits, and balances.
- Packing, dispatch, tracking, proof files, and delivery history.
- Reports, exports, verified backup, restore, and audit records.

## 7. Backblaze B2

- Private S3-compatible bucket.
- Settings capture endpoint, bucket, key ID, and application key.
- Application key is stored in Windows Credential Manager.
- Files are cached locally before transfer.
- Uploads retain queued/failed/synced state and retry count.
- Customer uploads return immediately and synchronize in one background queue.
- Opening synchronized files uses short-lived signed URLs.

## 8. Google Drive

- One universal bottom-right connect/open button.
- OAuth uses the minimum `drive.file` scope.
- Provision DTF ERP root folders and Customer Master Sheet.
- Keep customer roots and explicitly created dates synchronized.
- Create metadata-only Drive catalogue entries for Backblaze files.
- Google failure must not invalidate a successful Backblaze upload.
- Google folder and Sheet operations are serialized, deduplicated, and backgrounded.
- Third-party shortcut opening requires a published ERP file gateway and Google
  Drive UI registration; this remains deployment work.

## 9. Performance

- Customer creation and folder opening must not make synchronous cloud calls.
- No automatic empty daily folders.
- Support at least 1,000 searchable customers without changing the UI workflow.
- Preserve responsive scrolling, selection, preview, and navigation during cloud
  work.
- Large files must be streamed or copied in bounded chunks where practical.

## 10. Security, durability, and privacy

- Never commit credentials, tokens, databases, customer files, or caches.
- Keep Backblaze private and apply least-privilege bucket keys.
- Preserve originals and version history.
- Validate managed paths against traversal.
- Keep database backups separate from the active database.
- Google Drive is a catalogue/convenience layer, not the only backup.

## 11. Future hosted backend

The repository contains `.env.backend.example` placeholders for Supabase, but the
desktop app currently uses SQLite. Future hosted work must provide:

- business/tenant isolation;
- verified email identity;
- owner and employee membership;
- centrally managed roles and permissions;
- secure server-side Backblaze signing;
- stable public file-gateway URLs;
- conflict-aware multi-device synchronization;
- audit and backup policies.

These items must not be described as implemented until code, migrations, tests,
and deployment infrastructure exist.
